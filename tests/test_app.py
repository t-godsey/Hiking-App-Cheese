"""Lightweight Flask route smoke checks and artifact-path guards."""

from __future__ import annotations

import pytest

import app as app_module


def test_index_get_ok() -> None:
    """Home page should render the upload shell."""

    cli = app_module.app.test_client()
    resp = cli.get("/")
    assert resp.status_code == 200
    assert b"Elevation-Aware Hiking Optimizer" in resp.data


def test_optimize_requires_gpx_returns_400() -> None:
    """Missing upload must short-circuit before touching the filesystem."""

    cli = app_module.app.test_client()
    resp = cli.post("/optimize", data={"weight_lbs": "22", "max_speed_mph": "3"})
    assert resp.status_code == 400


def test_resolve_web_run_blocks_non_artifacts(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Resolver only acknowledges whitelisted artifact extensions under each run sandbox."""

    monkeypatch.setattr(app_module, "WEB_RUNS_DIR", tmp_path)

    run_id = "cleanrun"

    safe_dir = tmp_path / run_id
    safe_dir.mkdir(parents=True, exist_ok=True)
    html_doc = safe_dir / "trail_pace_map.html"
    html_doc.write_text("<html></html>", encoding="utf-8")

    resolved = app_module._resolve_web_run_file(run_id, "trail_pace_map.html")
    assert resolved == html_doc.resolve()

    assert app_module._resolve_web_run_file(run_id, "trail.gpx") is None


