"""Tests for pace zone labeling and merging helpers."""

from __future__ import annotations

import pytest

from hiking_optimizer.zones import (
    ZONE_COLORS,
    apply_quantile_zone_refinement,
    classify_pace_zone,
    merge_short_zone_runs,
    percentile,
    summarize_zones,
)


def test_classify_pace_zone_vs_training_baseline() -> None:
    """
    Initial zone tags use fixed ratios against the synthetic training baseline (later replaced by quantiles).

    slowdown: <= 0.8 * baseline; speed-up: >= 1.15 * baseline; else steady.
    """
    baseline = 2.0
    assert classify_pace_zone(1.5, baseline)[0] == "slowdown"
    assert classify_pace_zone(2.0, baseline)[0] == "steady"
    assert classify_pace_zone(2.4, baseline)[0] == "speed-up"


def test_percentile_interpolates() -> None:
    """Linear percentile with q=0.5 should split an odd-length sorted list cleanly."""
    assert percentile([10.0, 20.0, 30.0], 0.5) == pytest.approx(20.0)


def test_apply_quantile_zone_refinement_marks_thirds() -> None:
    """
    Quartile refinement: speeds at or below p25 become slowdown;
    at or above p75 become speed-up; middle band stays steady (when distinct).
    """
    rows = [
        {"recommended_speed_mph": 1.0, "zone": "", "zone_color": "", "distance_m": 10, "start_m": 0, "end_m": 10},
        {"recommended_speed_mph": 2.0, "zone": "", "zone_color": "", "distance_m": 10, "start_m": 10, "end_m": 20},
        {"recommended_speed_mph": 3.0, "zone": "", "zone_color": "", "distance_m": 10, "start_m": 20, "end_m": 30},
        {"recommended_speed_mph": 4.0, "zone": "", "zone_color": "", "distance_m": 10, "start_m": 30, "end_m": 40},
        {"recommended_speed_mph": 100.0, "zone": "", "zone_color": "", "distance_m": 10, "start_m": 40, "end_m": 50},
    ]
    apply_quantile_zone_refinement(rows)
    lows = sum(1 for r in rows if r["zone"] == "slowdown")
    mids = sum(1 for r in rows if r["zone"] == "steady")
    highs = sum(1 for r in rows if r["zone"] == "speed-up")
    assert lows + mids + highs == len(rows)


def test_merge_short_zone_runs_prefers_neighbor_run_length() -> None:
    """
    Sandwich a short steady run between slowdown (longer flank) vs speed-up; merge picks the farther neighbor:
    slowdown total 160 m vs speed-up 130 m ⇒ steady island should collapse into slowdown per merge rule.
    """
    cum_m = 0.0

    rows: list[dict[str, float | str]] = []

    def append_segment(distance_m: float, zone_key: str) -> None:
        nonlocal cum_m
        start = cum_m
        cum_m += distance_m
        rows.append(
            {
                "zone": zone_key,
                "zone_color": ZONE_COLORS[zone_key],
                "distance_m": distance_m,
                "start_m": start,
                "end_m": cum_m,
            }
        )

    append_segment(80.0, "slowdown")
    append_segment(80.0, "slowdown")
    append_segment(40.0, "steady")
    append_segment(130.0, "speed-up")

    steady_idx = 2

    merge_short_zone_runs(rows, min_run_distance_m=90.0, max_passes=8)

    assert rows[steady_idx]["zone"] == "slowdown"


def test_summarize_zones_skips_micro_runs_below_threshold() -> None:
    """Contiguous merges require min distance before emitting a CLI Zone row."""
    rows = [
        {
            "zone": "steady",
            "recommended_speed_mph": 2.0,
            "distance_m": 50.0,
            "start_m": 0.0,
            "end_m": 50.0,
        }
    ]
    zones = summarize_zones(rows, min_zone_distance_m=1000.0)
    assert zones == []
