"""Tests for the lightweight regression learner and cached model persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from hiking_optimizer.model import (
    LinearRegressionGD,
    _save_pace_model,
    _try_load_pace_model,
    build_training_data,
    segment_features,
)
from hiking_optimizer.types import Segment, TrackPoint


def test_linear_regression_fit_converges_on_synthetic_problem() -> None:
    """Enough GD epochs should drag mean predictions close to noisy synthetic mph labels."""
    x, y = build_training_data()
    model_fast = LinearRegressionGD(learning_rate=0.02, epochs=400)
    model_fast.fit(x, y)

    pred0 = sum(model_fast.predict(row) for row in x[:80]) / 80
    err0 = abs(pred0 - sum(y[:80]) / 80)

    assert err0 < 0.85, "mean prediction should drift toward noisy target band"


def test_segment_features_mirror_training_columns_order() -> None:
    """Segment feature vector stays aligned with build_training_data feature layout."""
    seg = Segment(
        idx=0,
        start=TrackPoint(0.0, 0.0, 0.0),
        end=TrackPoint(1.0, 1.0, 1.0),
        distance_m=100.0,
        elev_delta_m=5.0,
        grade_pct=5.0,
        grade_abs_pct=5.0,
        cumulative_distance_m=100.0,
    )
    feats = segment_features(seg, weight_lbs=30.0)
    assert len(feats) == 6
    assert feats[1] == abs(feats[0])


def test_pace_model_json_roundtrip_matches_predictions(tmp_path: Path) -> None:
    """Disk cache serializes scaler + bias/weights so load skips refit but preserves predict()."""

    tiny_x = [[g, abs(g), g * g, w, w * w, g * w] for g, w in ((0.0, 25.0), (5.0, 22.0), (-3.0, 30.0))]
    tiny_y = [2.1, 1.9, 2.2]
    m = LinearRegressionGD(learning_rate=0.1, epochs=900)
    m.fit(tiny_x, tiny_y)

    tmp = tmp_path / "model.json"
    baseline = sum(tiny_y) / len(tiny_y)
    _save_pace_model(tmp, m, baseline)

    restored = _try_load_pace_model(tmp)
    assert restored is not None
    loaded, loaded_baseline = restored
    assert loaded_baseline == pytest.approx(baseline)

    sample = [-2.0, 2.0, 4.0, 20.0, 400.0, -40.0]
    assert loaded.predict(sample) == pytest.approx(m.predict(sample))
