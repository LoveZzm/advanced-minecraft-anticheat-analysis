"""Tests for gameplay feature engineering."""

from __future__ import annotations

import pytest

from anticheat_pipeline.features import engineer_features
from tests.conftest import session_row


def test_engineer_features_calculates_normalized_rates() -> None:
    features = engineer_features(
        session_row(
            duration_minutes=20,
            click_count=12000,
            target_switches=80,
            resources_collected=200,
            unique_actions=160,
            click_interval_std_ms=40,
            session_hour=2,
        )
    )

    assert features.clicks_per_second == pytest.approx(10.0)
    assert features.target_switches_per_minute == pytest.approx(4.0)
    assert features.resources_per_minute == pytest.approx(10.0)
    assert features.actions_per_minute == pytest.approx(8.0)
    assert features.click_consistency == pytest.approx(0.5)
    assert features.overnight_activity == 1.0


def test_engineer_features_rejects_zero_duration() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        engineer_features(session_row(duration_minutes=0))


def test_engineer_features_reports_missing_columns() -> None:
    row = session_row()
    del row["max_reach_blocks"]

    with pytest.raises(ValueError, match="max_reach_blocks"):
        engineer_features(row)


def test_engineer_features_accepts_blank_optional_label() -> None:
    features = engineer_features(session_row(label=""))

    assert features.label == 0
