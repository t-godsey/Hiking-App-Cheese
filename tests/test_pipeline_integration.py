"""End-to-end orchestration exercised on the tiny pytest GPX fixture."""

from __future__ import annotations

from pathlib import Path

from hiking_optimizer.pipeline import run_backend_job


def test_run_backend_writes_three_artifacts(minimal_gpx_path: Path, tmp_path: Path) -> None:
    """
    Pipeline should hydrate CSV / GeoJSON / HTML without callers wiring writers manually.

    Committed pace_model.json keeps load_or_train_pace_model fast in CI/dev.
    """

    result = run_backend_job(
        gpx_path=minimal_gpx_path,
        weight_lbs=20.0,
        max_speed_mph=3.5,
        out_dir=tmp_path,
        min_zone_run_m=150.0,
    )

    assert Path(result["csv_path"]).is_file()
    assert Path(result["geojson_path"]).is_file()
    assert Path(result["html_path"]).is_file()


def test_runner_summary_counts_nonempty(minimal_gpx_path: Path, tmp_path: Path) -> None:
    """Sanity-check analytics fields relied on by the CLI/UI stay numeric and positive."""

    summary = run_backend_job(
        gpx_path=minimal_gpx_path,
        weight_lbs=18.0,
        max_speed_mph=3.0,
        out_dir=tmp_path,
        min_zone_run_m=150.0,
    )

    assert int(summary["segment_count"]) >= 2
    assert float(summary["total_distance_m"]) > 0
