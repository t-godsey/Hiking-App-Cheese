"""GPX parsing and segment construction."""

from __future__ import annotations

import math
from pathlib import Path
import xml.etree.ElementTree as ET

from .constants import GPX_NS
from .types import Segment, TrackPoint


def parse_gpx_points(gpx_path: Path) -> list[TrackPoint]:
    try:
        tree = ET.parse(gpx_path)
    except FileNotFoundError:
        raise ValueError(f"GPX file not found: {gpx_path}") from None
    except ET.ParseError as exc:
        raise ValueError(f"Could not parse GPX XML: {exc}") from None

    root = tree.getroot()
    points: list[TrackPoint] = []
    for trkpt in root.iter(f"{{{GPX_NS}}}trkpt"):
        lat_text = trkpt.attrib.get("lat")
        lon_text = trkpt.attrib.get("lon")
        ele_elem = trkpt.find(f"{{{GPX_NS}}}ele")
        if not lat_text or not lon_text or ele_elem is None or not ele_elem.text:
            continue
        points.append(
            TrackPoint(lat=float(lat_text), lon=float(lon_text), ele_m=float(ele_elem.text))
        )

    if len(points) < 2:
        raise ValueError("GPX has insufficient valid track points.")
    return points


def gpx_title(gpx_path: Path) -> str:
    try:
        tree = ET.parse(gpx_path)
    except Exception:
        return gpx_path.stem
    root = tree.getroot()
    name_elem = root.find(f".//{{{GPX_NS}}}trk/{{{GPX_NS}}}name")
    if name_elem is None:
        name_elem = root.find(f".//{{{GPX_NS}}}metadata/{{{GPX_NS}}}name")
    if name_elem is not None and name_elem.text:
        return name_elem.text.strip()
    return gpx_path.stem


def build_segments(points: list[TrackPoint]) -> list[Segment]:
    segments: list[Segment] = []
    cumulative = 0.0

    for idx in range(1, len(points)):
        start, end = points[idx - 1], points[idx]
        dist_m = _haversine_distance_m(start, end)
        if dist_m < 0.5:
            # Skip near-duplicate points that can explode grade values.
            continue

        elev_delta = end.ele_m - start.ele_m
        grade_pct = (elev_delta / dist_m) * 100.0
        cumulative += dist_m
        segments.append(
            Segment(
                idx=len(segments),
                start=start,
                end=end,
                distance_m=dist_m,
                elev_delta_m=elev_delta,
                grade_pct=grade_pct,
                grade_abs_pct=abs(grade_pct),
                cumulative_distance_m=cumulative,
            )
        )

    if not segments:
        raise ValueError("No usable trail segments found after preprocessing.")
    return segments


def _haversine_distance_m(p1: TrackPoint, p2: TrackPoint) -> float:
    earth_radius_m = 6371000.0
    lat1 = math.radians(p1.lat)
    lat2 = math.radians(p2.lat)
    dlat = lat2 - lat1
    dlon = math.radians(p2.lon - p1.lon)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_m * c
