"""Robust statistical outlier detection for session features."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from anticheat_pipeline.schemas import SessionFeatures


@dataclass(frozen=True)
class RobustProfile:
    """Median and median absolute deviation for each model feature."""

    medians: tuple[float, ...]
    deviations: tuple[float, ...]


def fit_profile(sessions: list[SessionFeatures]) -> RobustProfile:
    """Fit robust population statistics that resist extreme sessions."""

    if not sessions:
        raise ValueError("Cannot fit an outlier profile without sessions")
    columns = list(zip(*(session.model_vector() for session in sessions), strict=True))
    medians = tuple(median(column) for column in columns)
    deviations = tuple(
        max(median(abs(value - center) for value in column), 0.01)
        for column, center in zip(columns, medians, strict=True)
    )
    return RobustProfile(medians=medians, deviations=deviations)


def outlier_score(session: SessionFeatures, profile: RobustProfile) -> float:
    """Score a session from 0-100 using its three strongest robust z-scores."""

    z_scores = [
        abs(value - center) / (1.4826 * deviation)
        for value, center, deviation in zip(
            session.model_vector(),
            profile.medians,
            profile.deviations,
            strict=True,
        )
    ]
    strongest = sorted(z_scores, reverse=True)[:3]
    # A robust z-score of six is treated as maximally anomalous for this demo.
    return round(100.0 * sum(min(value / 6.0, 1.0) for value in strongest) / 3.0, 2)
