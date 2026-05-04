"""Zone classification and summarization."""

from __future__ import annotations

import math
from typing import Iterable

from .constants import METERS_TO_MILES
from .types import Zone

ZONE_COLORS: dict[str, str] = {
    "slowdown": "#d73027",
    "steady": "#fdae61",
    "speed-up": "#1a9850",
}


def classify_pace_zone(speed_mph: float, baseline_mph: float) -> tuple[str, str]:
    """Rough labels vs training-data mean; superseded later by apply_quantile_zone_refinement."""
    if speed_mph <= baseline_mph * 0.8:
        return "slowdown", ZONE_COLORS["slowdown"]
    if speed_mph >= baseline_mph * 1.15:
        return "speed-up", ZONE_COLORS["speed-up"]
    return "steady", ZONE_COLORS["steady"]


def percentile(values: Iterable[float], q: float) -> float:
    """Linear interpolation between sorted order statistics (q in [0, 1])."""
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
    """Assign slowdown / steady / speed-up from this hike's speed distribution (p25, p75)."""
    speeds = [float(r["recommended_speed_mph"]) for r in rows]
    p25 = percentile(speeds, 0.25)
    p75 = percentile(speeds, 0.75)

    for row in rows:
        speed = float(row["recommended_speed_mph"])
        if speed <= p25:
            row["zone"] = "slowdown"
            row["zone_color"] = ZONE_COLORS["slowdown"]
        elif speed >= p75:
            row["zone"] = "speed-up"
            row["zone_color"] = ZONE_COLORS["speed-up"]
        else:
            row["zone"] = "steady"
            row["zone_color"] = ZONE_COLORS["steady"]


def merge_short_zone_runs(
    rows: list[dict[str, float | str]],
    min_run_distance_m: float = 200.0,
    max_passes: int = 12,
) -> None:
    """
    Collapse visually noisy zone labels by merging contiguous runs shorter than
    min_run_distance_m into the surrounding dominant zone (e.g. a brief steady
    blip sandwiched by speed-up becomes speed-up).

    Runs at the trail ends merge into the single adjacent neighbor. When sandwiched
    between different zones, the longer neighbor wins.
    """

    if not rows or min_run_distance_m <= 0:
        return

    def run_boundaries() -> list[tuple[int, int, str, float]]:
        bounds: list[tuple[int, int, str, float]] = []
        i = 0
        n = len(rows)
        while i < n:
            zone = str(rows[i]["zone"])
            dist_sum = float(rows[i]["distance_m"])
            j = i + 1
            while j < n and str(rows[j]["zone"]) == zone:
                dist_sum += float(rows[j]["distance_m"])
                j += 1
            bounds.append((i, j - 1, zone, dist_sum))
            i = j
        return bounds

    for _ in range(max_passes):
        runs = run_boundaries()
        if len(runs) <= 1:
            return

        new_labels = [str(r["zone"]) for r in rows]
        changed = False

        # Relabel short interior runs to match a neighbor (prefer longer adjacent run).
        for k, (start, end, zone, dist_m) in enumerate(runs):
            if dist_m >= min_run_distance_m:
                continue

            prev = runs[k - 1] if k > 0 else None
            nxt = runs[k + 1] if k + 1 < len(runs) else None

            target: str | None = None
            if prev is not None and nxt is not None:
                _, _, pz, pd = prev
                _, _, nz, nd = nxt
                if pz == nz:
                    target = pz
                else:
                    target = pz if pd >= nd else nz
            elif prev is not None:
                target = prev[2]
            elif nxt is not None:
                target = nxt[2]

            if target is None or target == zone:
                continue

            for idx in range(start, end + 1):
                new_labels[idx] = target
            changed = True

        if not changed:
            break

        for idx, row in enumerate(rows):
            z = new_labels[idx]
            row["zone"] = z
            row["zone_color"] = ZONE_COLORS.get(z, str(row["zone_color"]))


def summarize_zones(
    segment_recommendations: list[dict[str, float | str]],
    min_zone_distance_m: float = 120.0,
) -> list[Zone]:
    """Merge adjacent segments with the same zone into mile-ranged summaries for CLI printout."""
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
