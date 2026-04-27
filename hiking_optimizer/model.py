"""Regression model and feature engineering for pace prediction."""

from __future__ import annotations

import random
import statistics

from .types import Segment


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
        self.weights = [0.0] * (n_features + 1)
        n = len(x)

        for _ in range(self.epochs):
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
    g = segment.grade_pct
    return [g, abs(g), g * g, weight_lbs, weight_lbs * weight_lbs, g * weight_lbs]


def _synthetic_true_speed_mph(grade_pct: float, weight_lbs: float) -> float:
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
