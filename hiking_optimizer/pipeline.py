"""High-level orchestration for the backend flow."""

from __future__ import annotations

from pathlib import Path

from .constants import METERS_TO_FEET, METERS_TO_MILES
from .exporters import pace_zone_mph_ranges, write_csv, write_geojson, write_html_map
from .gpx_parser import build_segments, gpx_title, parse_gpx_points
from .model import load_or_train_pace_model, segment_features
from .zones import (
    apply_quantile_zone_refinement,
    classify_pace_zone,
    merge_short_zone_runs,
    summarize_zones,
)


def run_backend_job(
    gpx_path: Path,
    weight_lbs: float,
    max_speed_mph: float,
    out_dir: Path,
    min_zone_run_m: float = 200.0,
) -> dict[str, float | int | str | Path]:
    """End-to-end optimize: parse GPX → predict speeds → refine zones → write artifacts; returns summary dict."""
    if weight_lbs <= 0:
        raise ValueError("weight-lbs must be positive.")
    if max_speed_mph <= 0:
        raise ValueError("max-speed-mph must be positive.")

    title = gpx_title(gpx_path)
    points = parse_gpx_points(gpx_path)
    segments = build_segments(points)

    # Cached linear model + training-label mean (used before quantile refinement for initial colors).
    model, baseline = load_or_train_pace_model()

    segment_rows: list[dict[str, float | str]] = []
    total_distance = 0.0
    weighted_speed_sum = 0.0
    total_gain = 0.0
    prev_end_m = 0.0

    for seg in segments:
        raw_pred = model.predict(segment_features(seg, weight_lbs))
        # Floor/cap keeps predictions in a plausible hiking range and respects user max speed.
        recommended_speed = max(0.7, min(max_speed_mph, raw_pred))
        zone_type, zone_color = classify_pace_zone(recommended_speed, baseline)

        start_m = prev_end_m
        end_m = seg.cumulative_distance_m
        prev_end_m = end_m

        segment_rows.append(
            {
                "segment_index": seg.idx,
                "start_lat": seg.start.lat,
                "start_lon": seg.start.lon,
                "end_lat": seg.end.lat,
                "end_lon": seg.end.lon,
                "distance_m": seg.distance_m,
                "elev_delta_m": seg.elev_delta_m,
                "grade_pct": seg.grade_pct,
                "recommended_speed_mph": recommended_speed,
                "zone": zone_type,
                "zone_color": zone_color,
                "start_m": start_m,
                "end_m": end_m,
            }
        )

        total_distance += seg.distance_m
        weighted_speed_sum += recommended_speed * seg.distance_m
        if seg.elev_delta_m > 0:
            total_gain += seg.elev_delta_m

    # Trail-relative buckets (p25 / p75) replace baseline-based zone tags for map colors.
    apply_quantile_zone_refinement(segment_rows)
    merge_short_zone_runs(segment_rows, min_run_distance_m=min_zone_run_m)
    zones = summarize_zones(segment_rows)

    avg_speed = weighted_speed_sum / total_distance if total_distance > 0 else 0.0
    slowdown_count = sum(1 for z in segment_rows if z["zone"] == "slowdown")
    speedup_count = sum(1 for z in segment_rows if z["zone"] == "speed-up")

    slug = gpx_path.stem.replace(" ", "_")
    csv_path = out_dir / f"{slug}_speed_profile.csv"
    geojson_path = out_dir / f"{slug}_pace_map.geojson"
    html_path = out_dir / f"{slug}_pace_map.html"

    write_csv(csv_path, segment_rows)
    write_geojson(geojson_path, segment_rows)
    write_html_map(
        html_path,
        geojson_path.name,
        title=title,
        zone_mph_ranges=pace_zone_mph_ranges(segment_rows),
    )

    return {
        "title": title,
        "gpx_path": gpx_path,
        "weight_lbs": weight_lbs,
        "max_speed_mph": max_speed_mph,
        "total_distance_m": total_distance,
        "total_gain_m": total_gain,
        "avg_speed_mph": avg_speed,
        "segment_count": len(segment_rows),
        "slowdown_count": slowdown_count,
        "speedup_count": speedup_count,
        "zones_count": len(zones),
        "zones": zones,
        "csv_path": csv_path,
        "geojson_path": geojson_path,
        "html_path": html_path,
    }


def run_backend(
    gpx_path: Path,
    weight_lbs: float,
    max_speed_mph: float,
    out_dir: Path,
    min_zone_run_m: float = 200.0,
) -> None:
    """CLI wrapper around run_backend_job: same work, formatted stdout summary."""
    result = run_backend_job(
        gpx_path, weight_lbs, max_speed_mph, out_dir, min_zone_run_m=min_zone_run_m
    )
    title = str(result["title"])
    total_distance = float(result["total_distance_m"])
    total_gain = float(result["total_gain_m"])
    avg_speed = float(result["avg_speed_mph"])
    segment_count = int(result["segment_count"])
    slowdown_count = int(result["slowdown_count"])
    speedup_count = int(result["speedup_count"])
    csv_path = Path(result["csv_path"])
    geojson_path = Path(result["geojson_path"])
    html_path = Path(result["html_path"])
    zones = result["zones"]

    print("=" * 62)
    print("Elevation-Aware Hiking Optimization (Backend CLI)")
    print("=" * 62)
    print(f"Trail:                 {title}")
    print(f"GPX file:              {gpx_path}")
    print(f"Backpack weight:       {weight_lbs:.1f} lbs")
    print(f"User max speed cap:    {max_speed_mph:.2f} mph")
    print(f"Total distance:        {total_distance * METERS_TO_MILES:.2f} mi")
    print(f"Total elevation gain:  {total_gain:,.0f} m / {total_gain * METERS_TO_FEET:,.0f} ft")
    print(f"Recommended avg speed: {avg_speed:.2f} mph")
    print(f"Segment count:         {segment_count}")
    print(f"Slowdown segments:     {slowdown_count}")
    print(f"Speed-up segments:     {speedup_count}")
    print()
    print("Highlighted zones")
    if not zones:
        print("  (No zones exceeded minimum length threshold.)")
    else:
        for zone in zones[:12]:
            print(
                f"  - {zone.zone_type:8s} | mile {zone.start_mile:5.2f} -> {zone.end_mile:5.2f} | "
                f"avg {zone.avg_speed_mph:4.2f} mph"
            )
        if len(zones) > 12:
            print(f"  ... and {len(zones) - 12} more zones")
    print()
    print("Artifacts")
    print(f"  - CSV profile:       {csv_path}")
    print(f"  - GeoJSON pace map:  {geojson_path}")
    print(f"  - HTML map viewer:   {html_path}")
    print("=" * 62)
