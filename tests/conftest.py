"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from anticheat_pipeline.features import engineer_features
from anticheat_pipeline.schemas import SessionFeatures


def session_row(**overrides: object) -> dict[str, str]:
    """Return a valid normal-looking raw session row."""

    row: dict[str, object] = {
        "session_id": "S-test",
        "player_id": "test_player",
        "mode": "Duels",
        "duration_minutes": 10,
        "click_count": 4200,
        "click_interval_std_ms": 60,
        "max_reach_blocks": 2.9,
        "aim_snap_rate": 0.18,
        "perfect_tracking_ratio": 0.22,
        "target_switches": 16,
        "path_efficiency": 0.67,
        "repeated_path_ratio": 0.20,
        "idle_ratio": 0.10,
        "resources_collected": 30,
        "unique_actions": 90,
        "chat_messages": 2,
        "session_hour": 18,
        "label": 0,
    }
    row.update(overrides)
    return {key: str(value) for key, value in row.items()}


@pytest.fixture
def normal_session() -> SessionFeatures:
    """Provide a normal engineered session."""

    return engineer_features(session_row())


@pytest.fixture
def row_factory() -> Mapping[str, str]:
    """Expose a representative raw row for validation tests."""

    return session_row()
