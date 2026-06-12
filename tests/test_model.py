"""Tests for the lightweight logistic risk model."""

from __future__ import annotations

import pytest

from anticheat_pipeline.features import engineer_features
from anticheat_pipeline.model import train_model
from tests.conftest import session_row


def test_model_ranks_suspicious_session_above_normal_session() -> None:
    normal = [
        engineer_features(
            session_row(
                session_id=f"N{index}",
                click_count=(6 + index * 0.1) * 10 * 60,
                max_reach_blocks=2.8 + index * 0.01,
                label=0,
            )
        )
        for index in range(8)
    ]
    suspicious = [
        engineer_features(
            session_row(
                session_id=f"C{index}",
                click_count=(17 + index * 0.2) * 10 * 60,
                click_interval_std_ms=6,
                max_reach_blocks=3.7,
                aim_snap_rate=0.85,
                perfect_tracking_ratio=0.9,
                label=1,
            )
        )
        for index in range(8)
    ]

    model = train_model(normal + suspicious, learning_rate=0.05, epochs=400)

    assert model.predict_probability(suspicious[0]) > 0.9
    assert model.predict_probability(normal[0]) < 0.1


def test_model_requires_both_label_classes(normal_session) -> None:
    with pytest.raises(ValueError, match="both normal and suspicious"):
        train_model([normal_session, normal_session])


def test_model_rejects_non_binary_labels() -> None:
    sessions = [
        engineer_features(session_row(session_id="normal", label=0)),
        engineer_features(session_row(session_id="invalid", label=2)),
    ]

    with pytest.raises(ValueError, match="0 or 1"):
        train_model(sessions)
