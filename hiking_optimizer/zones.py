"""Zone classification and summarization."""

from __future__ import annotations

import math
from typing import Iterable

from .constants import METERS_TO_MILES
from .types import Zone


def classify_pace_zone(speed_mph: float, baseline_mph: float) -> tuple[str, str]:
    if speed_mph <= baseline_mph * 0.8:
        return "slowdown", "#d73027"
    if speed_mph >= baseline_mph * 1.15:
        return "speed-up", "#1a9850"
    return "steady", "#fdae61"


def percentile(values: Iterable[float], q: float) -> float:
    vals = sorted(values)
    if not vals:
        raise ValueError("Cannot compute percentile of empty values.")
    idx = q * (len(vals) - 1)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return vals[lo]
    frac = idx - lo
    return vals[lo] + (vals[hi] - vals[lo]) * frac


def apply_quantile_zone_refinement(rows: list[dict[str, float | str]]) -> None:
    speeds = [float(r["recommended_speed_mph"]) for r in rows]
    p25 = percentile(speeds, 0.25)
    p75 = percentile(speeds, 0.75)

    for row in rows:
        speed = float(row["recommended_speed_mph"])
        if speed <= p25:
            row["zone"] = "slowdown"
            row["zone_color"] = "#d73027"
        elif speed >= p75:
            row["zone"] = "speed-up"
            row["zone_color"] = "#1a9850"
        else:
            row["zone"] = "steady"
            row["zone_color"] = "#fdae61"


def summarize_zones(
    segment_recommendations: list[dict[str, float | str]],
    min_zone_distance_m: float = 120.0,
) -> list[Zone]:
    zones: list[Zone] = []
    current_type = None
    zone_start_m = 0.0
    zone_end_m = 0.0
    weighted_speed = 0.0
    total_dist = 0.0

    def close_zone() -> None:
        nonlocal zone_start_m, zone_end_m, weighted_speed, total_dist, current_type
        if current_type is None or total_dist < min_zone_distance_m:
            return
        zones.append(
            Zone(
                start_mile=zone_start_m * METERS_TO_MILES,
                end_mile=zone_end_m * METERS_TO_MILES,
                zone_type=current_type,
                avg_speed_mph=weighted_speed / total_dist,
            )
        )

    for rec in segment_recommendations:
        zone_type = str(rec["zone"])
        start_m = float(rec["start_m"])
        end_m = float(rec["end_m"])
        dist_m = float(rec["distance_m"])
        speed_mph = float(rec["recommended_speed_mph"])

        if current_type != zone_type:
            close_zone()
            current_type = zone_type
            zone_start_m = start_m
            zone_end_m = end_m
            weighted_speed = speed_mph * dist_m
            total_dist = dist_m
        else:
            zone_end_m = end_m
            weighted_speed += speed_mph * dist_m
            total_dist += dist_m

    close_zone()
    return zones
