"""Shared data structures used by pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SessionFeatures:
    """Engineered metrics for one gameplay session."""

    session_id: str
    player_id: str
    mode: str
    duration_minutes: float
    clicks_per_second: float
    click_consistency: float
    max_reach_blocks: float
    aim_snap_rate: float
    perfect_tracking_ratio: float
    target_switches_per_minute: float
    path_efficiency: float
    repeated_path_ratio: float
    idle_ratio: float
    resources_per_minute: float
    actions_per_minute: float
    chat_messages: float
    overnight_activity: float
    label: int

    def model_vector(self) -> list[float]:
        """Return the stable feature order consumed by the model."""

        return [
            self.clicks_per_second,
            self.click_consistency,
            self.max_reach_blocks,
            self.aim_snap_rate,
            self.perfect_tracking_ratio,
            self.target_switches_per_minute,
            self.path_efficiency,
            self.repeated_path_ratio,
            self.idle_ratio,
            self.resources_per_minute,
            self.actions_per_minute,
            self.overnight_activity,
        ]


@dataclass(frozen=True)
class CategoryRisk:
    """Risk score and human-readable evidence for a cheat category."""

    score: float
    explanations: tuple[str, ...] = ()


@dataclass
class PlayerAssessment:
    """Combined assessment produced for one gameplay session."""

    features: SessionFeatures
    categories: dict[str, CategoryRisk]
    rule_score: float
    outlier_score: float = 0.0
    model_probability: float = 0.0
    risk_score: float = 0.0
    risk_tier: str = "low"
    primary_category: str = "none"
    explanations: list[str] = field(default_factory=list)

    def to_row(self) -> dict[str, Any]:
        """Flatten the assessment for CSV output."""

        row: dict[str, Any] = {
            "session_id": self.features.session_id,
            "player_id": self.features.player_id,
            "mode": self.features.mode,
            "risk_score": round(self.risk_score, 2),
            "risk_tier": self.risk_tier,
            "primary_category": self.primary_category,
            "rule_score": round(self.rule_score, 2),
            "outlier_score": round(self.outlier_score, 2),
            "model_probability": round(self.model_probability, 4),
            "explanation": " | ".join(self.explanations),
        }
        for category, risk in self.categories.items():
            row[f"{category}_score"] = round(risk.score, 2)
        return row
