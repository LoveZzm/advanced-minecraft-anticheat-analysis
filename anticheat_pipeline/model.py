"""Small interpretable logistic model used as a secondary risk signal."""

from __future__ import annotations

from dataclasses import dataclass
import math

from anticheat_pipeline.schemas import SessionFeatures


def _sigmoid(value: float) -> float:
    bounded = max(-35.0, min(35.0, value))
    return 1.0 / (1.0 + math.exp(-bounded))


@dataclass(frozen=True)
class LogisticRiskModel:
    """Dependency-free logistic regression with standardized inputs."""

    means: tuple[float, ...]
    scales: tuple[float, ...]
    weights: tuple[float, ...]
    bias: float

    def predict_probability(self, session: SessionFeatures) -> float:
        """Return the estimated probability of suspicious behavior."""

        standardized = [
            (value - mean) / scale
            for value, mean, scale in zip(
                session.model_vector(), self.means, self.scales, strict=True
            )
        ]
        logit = self.bias + sum(
            value * weight for value, weight in zip(standardized, self.weights, strict=True)
        )
        return _sigmoid(logit)


def train_model(
    sessions: list[SessionFeatures],
    learning_rate: float = 0.05,
    epochs: int = 500,
) -> LogisticRiskModel:
    """Train logistic regression on demo labels with batch gradient descent."""

    if len(sessions) < 2:
        raise ValueError("At least two sessions are required to train the model")
    labels = [session.label for session in sessions]
    if not set(labels).issubset({0, 1}):
        raise ValueError("Training labels must be 0 or 1")
    if len(set(labels)) < 2:
        raise ValueError("Training data must contain both normal and suspicious labels")

    vectors = [session.model_vector() for session in sessions]
    columns = list(zip(*vectors, strict=True))
    means = tuple(sum(column) / len(column) for column in columns)
    scales = tuple(
        max(
            math.sqrt(sum((value - mean) ** 2 for value in column) / len(column)),
            0.01,
        )
        for column, mean in zip(columns, means, strict=True)
    )
    standardized = [
        [(value - mean) / scale for value, mean, scale in zip(row, means, scales, strict=True)]
        for row in vectors
    ]

    weights = [0.0] * len(means)
    suspicious_rate = sum(labels) / len(labels)
    bias = math.log(suspicious_rate / (1.0 - suspicious_rate))
    for _ in range(epochs):
        predictions = [
            _sigmoid(bias + sum(value * weight for value, weight in zip(row, weights, strict=True)))
            for row in standardized
        ]
        errors = [prediction - label for prediction, label in zip(predictions, labels, strict=True)]
        bias -= learning_rate * sum(errors) / len(errors)
        for index in range(len(weights)):
            gradient = sum(
                error * row[index] for error, row in zip(errors, standardized, strict=True)
            ) / len(errors)
            weights[index] -= learning_rate * gradient

    return LogisticRiskModel(means, scales, tuple(weights), bias)
