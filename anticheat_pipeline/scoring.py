"""Explainable, category-specific rule scoring."""

from __future__ import annotations

from collections.abc import Callable

from anticheat_pipeline.config import DetectionConfig
from anticheat_pipeline.schemas import CategoryRisk, PlayerAssessment, SessionFeatures


def _above(value: float, soft: float, hard: float) -> float:
    """Return 0-1 severity for a value above configured thresholds."""

    if value <= soft:
        return 0.0
    return min(1.0, (value - soft) / max(hard - soft, 0.0001))


def _below(value: float, soft: float, hard: float) -> float:
    """Return 0-1 severity for a value below configured thresholds."""

    if value >= soft:
        return 0.0
    return min(1.0, (soft - value) / max(soft - hard, 0.0001))


def _category_score(
    checks: list[tuple[float, float, str]],
) -> CategoryRisk:
    """Combine weighted check severities and retain triggered explanations."""

    total_weight = sum(weight for _, weight, _ in checks)
    if total_weight <= 0:
        raise ValueError("Category rule weights must include a positive value")
    weighted = sum(severity * weight for severity, weight, _ in checks)
    explanations = tuple(text for severity, _, text in checks if severity > 0.0)
    return CategoryRisk(
        score=round(100.0 * weighted / total_weight, 2),
        explanations=explanations,
    )


def _autoclicker(features: SessionFeatures, rules: dict[str, float]) -> CategoryRisk:
    return _category_score(
        [
            (
                _above(features.clicks_per_second, rules["cps_soft"], rules["cps_hard"]),
                rules["cps_weight"],
                f"Sustained click rate reached {features.clicks_per_second:.1f} CPS",
            ),
            (
                _above(
                    features.click_consistency,
                    rules["consistency_soft"],
                    rules["consistency_hard"],
                ),
                rules["consistency_weight"],
                f"Click timing consistency was {features.click_consistency:.0%}",
            ),
        ]
    )


def _reach(features: SessionFeatures, rules: dict[str, float]) -> CategoryRisk:
    return _category_score(
        [
            (
                _above(features.max_reach_blocks, rules["soft"], rules["hard"]),
                1.0,
                f"Maximum observed reach was {features.max_reach_blocks:.2f} blocks",
            )
        ]
    )


def _aim_assist(features: SessionFeatures, rules: dict[str, float]) -> CategoryRisk:
    return _category_score(
        [
            (
                _above(features.aim_snap_rate, rules["snap_soft"], rules["snap_hard"]),
                rules["snap_weight"],
                f"Aim snap rate was {features.aim_snap_rate:.0%}",
            ),
            (
                _above(
                    features.perfect_tracking_ratio,
                    rules["tracking_soft"],
                    rules["tracking_hard"],
                ),
                rules["tracking_weight"],
                f"Perfect tracking ratio was {features.perfect_tracking_ratio:.0%}",
            ),
            (
                _above(
                    features.target_switches_per_minute,
                    rules["switches_soft"],
                    rules["switches_hard"],
                ),
                rules["switches_weight"],
                f"Target switching reached {features.target_switches_per_minute:.1f}/min",
            ),
        ]
    )


def _bot_behavior(features: SessionFeatures, rules: dict[str, float]) -> CategoryRisk:
    return _category_score(
        [
            (
                _above(
                    features.path_efficiency,
                    rules["path_efficiency_soft"],
                    rules["path_efficiency_hard"],
                ),
                rules["path_efficiency_weight"],
                f"Path efficiency was unusually high at {features.path_efficiency:.0%}",
            ),
            (
                _above(
                    features.repeated_path_ratio,
                    rules["repeated_path_soft"],
                    rules["repeated_path_hard"],
                ),
                rules["repeated_path_weight"],
                f"Repeated path ratio was {features.repeated_path_ratio:.0%}",
            ),
            (
                _below(
                    features.actions_per_minute,
                    rules["actions_soft"],
                    rules["actions_hard"],
                ),
                rules["actions_weight"],
                f"Action diversity was low at {features.actions_per_minute:.1f}/min",
            ),
        ]
    )


def _macro_farming(features: SessionFeatures, rules: dict[str, float]) -> CategoryRisk:
    return _category_score(
        [
            (
                _above(
                    features.resources_per_minute,
                    rules["resources_soft"],
                    rules["resources_hard"],
                ),
                rules["resources_weight"],
                f"Resource collection reached {features.resources_per_minute:.1f}/min",
            ),
            (
                _above(
                    features.repeated_path_ratio,
                    rules["repeated_path_soft"],
                    rules["repeated_path_hard"],
                ),
                rules["repeated_path_weight"],
                f"Farming route repetition was {features.repeated_path_ratio:.0%}",
            ),
            (
                _above(
                    features.duration_minutes,
                    rules["duration_soft"],
                    rules["duration_hard"],
                ),
                rules["duration_weight"],
                f"Session duration was {features.duration_minutes:.0f} minutes",
            ),
            (
                features.overnight_activity,
                rules["overnight_weight"],
                "Session occurred during overnight hours",
            ),
        ]
    )


CATEGORY_SCORERS: dict[
    str, Callable[[SessionFeatures, dict[str, float]], CategoryRisk]
] = {
    "autoclicker": _autoclicker,
    "reach": _reach,
    "aim_assist": _aim_assist,
    "bot_behavior": _bot_behavior,
    "macro_farming": _macro_farming,
}


def score_session(features: SessionFeatures, config: DetectionConfig) -> PlayerAssessment:
    """Produce category risks and an explainable aggregate rule score."""

    categories = {
        name: scorer(features, config.rules[name])
        for name, scorer in CATEGORY_SCORERS.items()
    }
    active = [
        name
        for name, risk in categories.items()
        if risk.score >= config.thresholds.category_active
    ]
    multi_score = min(
        100.0,
        max(0, len(active) - 1) * config.thresholds.multi_signal_bonus,
    )
    multi_explanations = (
        (f"Multiple independent categories triggered: {', '.join(active)}",)
        if len(active) > 1
        else ()
    )
    categories["multi_signal"] = CategoryRisk(multi_score, multi_explanations)

    weighted_scores = sorted(
        (
            categories[name].score * config.category_weights[name]
            for name in config.category_weights
        ),
        reverse=True,
    )
    # Strongest evidence leads; supporting independent signals increase confidence.
    rule_score = min(
        100.0,
        weighted_scores[0] + 0.25 * weighted_scores[1] + 0.10 * weighted_scores[2],
    )
    primary = max(CATEGORY_SCORERS, key=lambda name: categories[name].score)
    explanations = list(categories[primary].explanations)

    return PlayerAssessment(
        features=features,
        categories=categories,
        rule_score=round(rule_score, 2),
        primary_category=primary if categories[primary].score > 0 else "none",
        explanations=explanations,
    )
