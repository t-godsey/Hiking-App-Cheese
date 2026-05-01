from __future__ import annotations

import os
import uuid
from pathlib import Path

from flask import Flask, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from hiking_optimizer import run_backend_job


BASE_DIR = Path(__file__).resolve().parent
WEB_RUNS_DIR = BASE_DIR / "web_runs"
ALLOWED_EXTENSIONS = {".gpx"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


def _is_allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/optimize")
def optimize():
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

    return render_template(
        "index.html",
        map_url=map_url,
        trail_name=result["title"],
        segment_count=int(result["segment_count"]),
        avg_speed=f"{float(result['avg_speed_mph']):.2f}",
        total_distance_miles=f"{float(result['total_distance_m']) * 0.000621371:.2f}",
    )


@app.get("/artifacts/<run_id>/<path:filename>")
def artifact(run_id: str, filename: str):
    return send_from_directory(WEB_RUNS_DIR / run_id, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
