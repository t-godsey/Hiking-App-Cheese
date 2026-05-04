"""Tests around CSV/GeoJSON writers and mph legend bookkeeping."""

from __future__ import annotations

import json
from typing import cast

from hiking_optimizer.exporters import pace_zone_mph_ranges, write_csv, write_geojson


def test_pace_zone_mph_ranges_reflects_buckets() -> None:
    """Legend helper should tighten to actual min/max per zone label."""

    rows = cast(
        list[dict[str, float | str]],
        [
            {"zone": "slowdown", "recommended_speed_mph": 1.5},
            {"zone": "slowdown", "recommended_speed_mph": 2.0},
            {"zone": "steady", "recommended_speed_mph": 2.2},
        ],
    )
    r = pace_zone_mph_ranges(rows)
    assert r["slowdown"] == (1.5, 2.0)
    assert r["steady"] == (2.2, 2.2)


def test_geojson_writes_feature_collection_schema(tmp_path) -> None:
    """Smoke check that GeoJSON is valid RFC-style FeatureCollection wrapping LineStrings."""

    rows = [
        {
            "segment_index": 0,
            "start_lat": 0.0,
            "start_lon": 0.0,
            "end_lat": 1.0,
            "end_lon": 0.0,
            "distance_m": 111.0,
            "elev_delta_m": 0.0,
            "grade_pct": 0.0,
            "recommended_speed_mph": 3.0,
            "zone": "steady",
            "zone_color": "#fdae61",
            "start_m": 0.0,
            "end_m": 111.0,
        }
    ]

    outp = tmp_path / "trail_pace.geojson"
    write_geojson(outp, rows)
    blob = json.loads(outp.read_text(encoding="utf-8"))

    assert blob["type"] == "FeatureCollection"
    assert blob["features"][0]["geometry"]["type"] == "LineString"


def test_csv_writes_header_aligned_with_rows(tmp_path) -> None:
    """DictWriter ought to serialize every mandated column key."""

    rows = [
        {
            "segment_index": 0,
            "start_lat": 0.0,
            "start_lon": 0.0,
            "end_lat": 0.01,
            "end_lon": 0.01,
            "distance_m": 100.0,
            "elev_delta_m": 0.0,
            "grade_pct": 0.0,
            "recommended_speed_mph": 3.14,
            "zone": "steady",
            "zone_color": "#ccc",
            "start_m": 0.0,
            "end_m": 100.0,
        }
    ]

    outp = tmp_path / "trail.csv"
    write_csv(outp, rows)
    hdr = outp.read_text(encoding="utf-8").splitlines()[0]
    assert "recommended_speed_mph" in hdr
    assert outp.stat().st_size > len(hdr)
