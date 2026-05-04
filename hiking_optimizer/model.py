"""Regression model and feature engineering for pace prediction."""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

from .types import Segment

# Bump when training data, hyperparameters, or architecture changes (invalidates on-disk cache).
PACE_MODEL_SPEC_VERSION = 1
PACE_MODEL_LEARNING_RATE = 0.006
PACE_MODEL_EPOCHS = 3200


def default_pace_model_path() -> Path:
    """On-disk weights next to this module (commit-friendly to skip training in production)."""
    return Path(__file__).resolve().parent / "pace_model.json"


def load_or_train_pace_model(cache_path: Path | None = None) -> tuple[LinearRegressionGD, float]:
    """Load fitted weights from disk if valid; otherwise train once and persist."""
    path = cache_path or default_pace_model_path()
    train_x, train_y = build_training_data()
    baseline = statistics.mean(train_y)

    loaded = _try_load_pace_model(path)
    if loaded is not None:
        return loaded

    model = LinearRegressionGD(learning_rate=PACE_MODEL_LEARNING_RATE, epochs=PACE_MODEL_EPOCHS)
    model.fit(train_x, train_y)
    _save_pace_model(path, model, baseline)
    return model, baseline


def _try_load_pace_model(path: Path) -> tuple[LinearRegressionGD, float] | None:
    """Return model + baseline if JSON matches current spec and tensor shapes."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if data.get("spec_version") != PACE_MODEL_SPEC_VERSION:
        return None
    if data.get("learning_rate") != PACE_MODEL_LEARNING_RATE or data.get("epochs") != PACE_MODEL_EPOCHS:
        return None

    weights = data.get("weights")
    means = data.get("feature_means")
    stds = data.get("feature_stds")
    baseline = data.get("baseline_mph")
    if not isinstance(weights, list) or not isinstance(means, list) or not isinstance(stds, list):
        return None
    if baseline is None or len(weights) != len(means) + 1 or len(means) != len(stds):
        return None

    model = LinearRegressionGD(learning_rate=PACE_MODEL_LEARNING_RATE, epochs=PACE_MODEL_EPOCHS)
    model.weights = [float(w) for w in weights]
    model.feature_means = [float(m) for m in means]
    model.feature_stds = [float(s) for s in stds]
    return model, float(baseline)


def _save_pace_model(path: Path, model: LinearRegressionGD, baseline_mph: float) -> None:
    """Persist scaler + intercept/weights so the next process can predict without fitting."""
    payload = {
        "spec_version": PACE_MODEL_SPEC_VERSION,
        "learning_rate": PACE_MODEL_LEARNING_RATE,
        "epochs": PACE_MODEL_EPOCHS,
        "weights": model.weights,
        "feature_means": model.feature_means,
        "feature_stds": model.feature_stds,
        "baseline_mph": baseline_mph,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class LinearRegressionGD:
    """Small dependency-free linear regression using gradient descent."""

    def __init__(self, learning_rate: float = 0.01, epochs: int = 2200) -> None:
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.weights: list[float] = []
        self.feature_means: list[float] = []
        self.feature_stds: list[float] = []

    def fit(self, x: list[list[float]], y: list[float]) -> None:
        if not x or not y:
            raise ValueError("Training data is empty.")
        if len(x) != len(y):
            raise ValueError("Feature and label lengths do not match.")

        n_features = len(x[0])
        self.feature_means = []
        self.feature_stds = []
        for i in range(n_features):
            col = [row[i] for row in x]
            mean = statistics.mean(col)
            stdev = statistics.pstdev(col)
            self.feature_means.append(mean)
            self.feature_stds.append(stdev if stdev > 1e-12 else 1.0)

        x_scaled = [self._scale_row(row) for row in x]
        # weights[0] = bias; weights[1:] line up with scaled features.
        self.weights = [0.0] * (n_features + 1)
        n = len(x)

        for _ in range(self.epochs):
            # Full-batch MSE gradient for linear regression.
            grad = [0.0] * (n_features + 1)
            for row, y_true in zip(x_scaled, y):
                y_pred = self.weights[0] + sum(
                    w * feature for w, feature in zip(self.weights[1:], row)
                )
                error = y_pred - y_true
                grad[0] += error
                for j, feature in enumerate(row, start=1):
                    grad[j] += error * feature

            scale = 2.0 / n
            for j in range(len(self.weights)):
                self.weights[j] -= self.learning_rate * scale * grad[j]

    def predict(self, row: list[float]) -> float:
        if not self.weights:
            raise ValueError("Model has not been fitted.")
        row_scaled = self._scale_row(row)
        return self.weights[0] + sum(
            w * feature for w, feature in zip(self.weights[1:], row_scaled)
        )

    def _scale_row(self, row: list[float]) -> list[float]:
        if not self.feature_means or not self.feature_stds:
            raise ValueError("Feature scaler has not been fitted.")
        return [
            (value - mean) / std
            for value, mean, std in zip(row, self.feature_means, self.feature_stds)
        ]


def build_training_data() -> tuple[list[list[float]], list[float]]:
    """Synthetic (grade, weight) → speed pairs; fixed seed for reproducible cache files."""
    random.seed(42)
    x: list[list[float]] = []
    y: list[float] = []

    for _ in range(1800):
        grade = random.uniform(-20.0, 20.0)
        weight = random.uniform(5.0, 60.0)
        speed = _synthetic_true_speed_mph(grade, weight)
        noisy_speed = max(0.7, speed + random.gauss(0, 0.12))

        x.append([grade, abs(grade), grade * grade, weight, weight * weight, grade * weight])
        y.append(noisy_speed)

    return x, y


def segment_features(segment: Segment, weight_lbs: float) -> list[float]:
    """Feature vector aligned with columns used in build_training_data."""
    g = segment.grade_pct
    return [g, abs(g), g * g, weight_lbs, weight_lbs * weight_lbs, g * weight_lbs]


def _synthetic_true_speed_mph(grade_pct: float, weight_lbs: float) -> float:
    """Hand-tuned hill + load response; regression learns to approximate this surface."""
    base = 3.0
    uphill_penalty = max(0.0, grade_pct) * 0.11
    downhill_bonus = max(0.0, -grade_pct) * 0.035
    steep_downhill_penalty = max(0.0, -grade_pct - 8.0) * 0.08
    weight_penalty = 0.013 * max(0.0, weight_lbs - 10.0)
    nonlinear_weight_penalty = 0.00008 * max(0.0, weight_lbs - 10.0) ** 2
    speed = (
        base
        - uphill_penalty
        + downhill_bonus
        - steep_downhill_penalty
        - weight_penalty
        - nonlinear_weight_penalty
    )
    return max(0.8, min(4.4, speed))
