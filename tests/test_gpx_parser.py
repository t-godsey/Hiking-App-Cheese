"""Tests covering GPX parsing and segment preprocessing."""

from __future__ import annotations

import pytest

from hiking_optimizer.gpx_parser import build_segments, gpx_title, parse_gpx_points


def test_gpx_title_prefers_track_name(minimal_gpx_path) -> None:
    """Readers should reuse <trk><name> when present instead of filenames."""
    assert gpx_title(minimal_gpx_path) == "MiniTrail"


def test_parse_gpx_points_requires_ele(minimal_gpx_path) -> None:
    """Each kept point must expose lat/lon/ele triples consumed by grading logic."""
    pts = parse_gpx_points(minimal_gpx_path)
    assert len(pts) == 4
    assert pts[0].ele_m == 100.0


def test_skips_near_duplicate_points_for_grade(minimal_gpx_path) -> None:
    """Sub-half-meter skips avoid divide-by-zero style grade blowups."""

    pts = parse_gpx_points(minimal_gpx_path)
    segs = build_segments(pts)
    assert all(s.distance_m >= 0.5 for s in segs)


def test_parse_rejects_sparse_points(tmp_path) -> None:
    sparse = tmp_path / "bad.gpx"
    sparse.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1"><trk><trkseg>
<trkpt lat="0" lon="0"><ele>1</ele></trkpt>
</trkseg></trk></gpx>
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="insufficient"):
        parse_gpx_points(sparse)
