"""Shared pytest fixtures (sample GPX, repo paths)."""

from __future__ import annotations

from pathlib import Path

import pytest

# Repository root is one level above tests/
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def repo_root() -> Path:
    return ROOT


@pytest.fixture()
def minimal_gpx_path(tmp_path: Path) -> Path:
    """
    A tiny GPX with points ~150 m apart horizontally so segments survive the <0.5 m skip.
    Enough elevation change to yield sensible grades across several segments.
    """
    # Three points along roughly the same latitude: ~167 m between first and third (safe > 0.5 m per leg).
    gpx_xml = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="pytest" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata><name>MiniTrail</name></metadata>
  <trk><name>MiniTrail</name><trkseg>
    <trkpt lat="45.0000" lon="-73.0000"><ele>100.0</ele></trkpt>
    <trkpt lat="45.0005" lon="-73.0000"><ele>102.0</ele></trkpt>
    <trkpt lat="45.0010" lon="-73.0000"><ele>105.0</ele></trkpt>
    <trkpt lat="45.0015" lon="-73.0000"><ele>103.0</ele></trkpt>
  </trkseg></trk>
</gpx>
"""
    path = tmp_path / "minimal.gpx"
    path.write_text(gpx_xml, encoding="utf-8")
    return path
