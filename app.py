"""Flask web UI: GPX upload, pace optimization, artifact serving, optional PDF export."""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from flask import Flask, abort, render_template, request, Response, send_from_directory, url_for
from werkzeug.utils import secure_filename

from hiking_optimizer import run_backend_job

try:
    from playwright.sync_api import sync_playwright

    _HAS_PLAYWRIGHT = True
except ImportError:
    # PDF download link is omitted if playwright is not installed.
    sync_playwright = None  # type: ignore[misc, assignment]
    _HAS_PLAYWRIGHT = False

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
# Each optimization run writes under web_runs/<run_id>/ (HTML, GeoJSON, CSV, uploaded GPX).
WEB_RUNS_DIR = BASE_DIR / "web_runs"
ALLOWED_EXTENSIONS = {".gpx"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


def _is_allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def _resolve_web_run_file(run_id: str, filename: str) -> Path | None:
    """Resolve a served artifact path; rejects traversal and unexpected extensions."""
    raw_root = WEB_RUNS_DIR / run_id
    try:
        run_root = raw_root.resolve()
    except OSError:
        return None
    if not raw_root.exists() or not run_root.is_dir():
        return None
    suffix = Path(filename).suffix.lower()
    if suffix not in {".html", ".geojson", ".csv"}:
        return None

    stem = Path(filename).name.replace("\x00", "")
    candidate = (run_root / stem).resolve()
    try:
        candidate.relative_to(run_root)
    except ValueError:
        return None

    return candidate if candidate.is_file() else None


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/optimize")
def optimize():
    # Save upload, run pipeline, redirect context is re-rendered with map iframe + artifact URLs.
    gpx_file = request.files.get("gpx_file")
    weight_text = (request.form.get("weight_lbs") or "").strip()
    max_speed_text = (request.form.get("max_speed_mph") or "").strip()

    error = None
    if gpx_file is None or not gpx_file.filename:
        error = "Please upload a GPX file."
    elif not _is_allowed_file(gpx_file.filename):
        error = "Only .gpx files are supported."

    try:
        weight_lbs = float(weight_text)
        max_speed_mph = float(max_speed_text)
        if weight_lbs <= 0 or max_speed_mph <= 0:
            raise ValueError
    except ValueError:
        if error is None:
            error = "Backpack weight and max speed must be positive numbers."

    if error:
        return render_template("index.html", error=error), 400

    run_id = uuid.uuid4().hex[:10]
    run_dir = WEB_RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    safe_name = secure_filename(gpx_file.filename) or "uploaded.gpx"
    gpx_path = run_dir / safe_name
    gpx_file.save(gpx_path)

    try:
        result = run_backend_job(
            gpx_path=gpx_path,
            weight_lbs=weight_lbs,
            max_speed_mph=max_speed_mph,
            out_dir=run_dir,
        )
    except ValueError as exc:
        return render_template("index.html", error=str(exc)), 400

    html_name = Path(result["html_path"]).name
    map_url = url_for("artifact", run_id=run_id, filename=html_name)
    pdf_url = (
        url_for("download_pace_map_pdf", run_id=run_id, filename=html_name)
        if _HAS_PLAYWRIGHT
        else None
    )

    return render_template(
        "index.html",
        map_url=map_url,
        pdf_download_url=pdf_url,
        run_id=run_id,
        map_html_filename=html_name,
        trail_name=result["title"],
        segment_count=int(result["segment_count"]),
        avg_speed=f"{float(result['avg_speed_mph']):.2f}",
        total_distance_miles=f"{float(result['total_distance_m']) * 0.000621371:.2f}",
    )


@app.get("/artifacts/<run_id>/<path:filename>")
def artifact(run_id: str, filename: str):
    path = _resolve_web_run_file(run_id, filename)
    if path is None:
        abort(404)
    return send_from_directory(path.parent, path.name)


@app.get("/download_pdf/<run_id>/<path:filename>")
def download_pace_map_pdf(run_id: str, filename: str):
    """Render the pace-map HTML page and return a PDF attachment."""
    if not _HAS_PLAYWRIGHT:
        abort(503)

    path = _resolve_web_run_file(run_id, filename)
    if path is None or Path(filename).suffix.lower() != ".html":
        abort(404)

    # Chromium loads the live map URL so tiles and GeoJSON resolve like a normal browser.
    base = request.url_root.rstrip("/")
    artifact_path = url_for("artifact", run_id=run_id, filename=Path(filename).name)
    viewer_url = f"{base}{artifact_path}"
    pdf_stem = Path(filename).stem
    disposition = f'attachment; filename="{pdf_stem}.pdf"'

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(viewer_url, wait_until="networkidle", timeout=120_000)
                page.wait_for_timeout(3500)
                pdf_bytes = page.pdf(
                    print_background=True,
                    format="Letter",
                    landscape=True,
                    margin={"top": "16px", "right": "16px", "bottom": "16px", "left": "16px"},
                )
            finally:
                browser.close()
    except Exception:
        logger.exception("Playwright PDF failed for run_id=%s file=%s", run_id, filename)
        abort(503)

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": disposition},
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
