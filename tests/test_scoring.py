"""Tests for explainable category risk scoring."""

from __future__ import annotations

from anticheat_pipeline.config import load_config
from anticheat_pipeline.features import engineer_features
from anticheat_pipeline.scoring import score_session
from tests.conftest import session_row


def test_autoclicker_signal_is_scored_separately() -> None:
    session = engineer_features(
        session_row(click_count=20 * 10 * 60, click_interval_std_ms=4)
    )

    assessment = score_session(session, load_config())

    assert assessment.categories["autoclicker"].score > 90
    assert assessment.categories["reach"].score == 0
    assert assessment.primary_category == "autoclicker"
    assert any("click rate" in text for text in assessment.explanations)


def test_multi_signal_score_increases_for_independent_categories() -> None:
    session = engineer_features(
        session_row(
            click_count=20 * 10 * 60,
            click_interval_std_ms=4,
            max_reach_blocks=4.0,
            aim_snap_rate=0.95,
            perfect_tracking_ratio=0.97,
            target_switches=90,
        )
    )

    assessment = score_session(session, load_config())

    assert assessment.categories["multi_signal"].score >= 60
    assert assessment.rule_score == 100
    assert "Multiple independent categories" in assessment.categories[
        "multi_signal"
    ].explanations[0]


def test_normal_session_has_low_rule_score(normal_session) -> None:
    assessment = score_session(normal_session, load_config())

    assert assessment.rule_score < 10
    assert assessment.primary_category == "none"
