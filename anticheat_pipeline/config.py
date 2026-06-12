"""Load and validate detection configuration."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any
import tomllib


CHEAT_CATEGORIES = frozenset(
    {"autoclicker", "reach", "aim_assist", "bot_behavior", "macro_farming"}
)
SCORING_CATEGORIES = CHEAT_CATEGORIES | {"multi_signal"}
RULE_KEYS = {
    "autoclicker": {
        "cps_soft",
        "cps_hard",
        "cps_weight",
        "consistency_soft",
        "consistency_hard",
        "consistency_weight",
    },
    "reach": {"soft", "hard"},
    "aim_assist": {
        "snap_soft",
        "snap_hard",
        "snap_weight",
        "tracking_soft",
        "tracking_hard",
        "tracking_weight",
        "switches_soft",
        "switches_hard",
        "switches_weight",
    },
    "bot_behavior": {
        "path_efficiency_soft",
        "path_efficiency_hard",
        "path_efficiency_weight",
        "repeated_path_soft",
        "repeated_path_hard",
        "repeated_path_weight",
        "actions_soft",
        "actions_hard",
        "actions_weight",
    },
    "macro_farming": {
        "resources_soft",
        "resources_hard",
        "resources_weight",
        "repeated_path_soft",
        "repeated_path_hard",
        "repeated_path_weight",
        "duration_soft",
        "duration_hard",
        "duration_weight",
        "overnight_weight",
    },
}
THRESHOLD_PAIRS = {
    "autoclicker": (("cps_soft", "cps_hard"), ("consistency_soft", "consistency_hard")),
    "reach": (("soft", "hard"),),
    "aim_assist": (
        ("snap_soft", "snap_hard"),
        ("tracking_soft", "tracking_hard"),
        ("switches_soft", "switches_hard"),
    ),
    "bot_behavior": (
        ("path_efficiency_soft", "path_efficiency_hard"),
        ("repeated_path_soft", "repeated_path_hard"),
    ),
    "macro_farming": (
        ("resources_soft", "resources_hard"),
        ("repeated_path_soft", "repeated_path_hard"),
        ("duration_soft", "duration_hard"),
    ),
}
INVERSE_THRESHOLD_PAIRS = {
    "bot_behavior": (("actions_soft", "actions_hard"),),
}

_REPOSITORY_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "detection.toml"
)
DEFAULT_CONFIG_PATH = (
    _REPOSITORY_CONFIG_PATH
    if _REPOSITORY_CONFIG_PATH.exists()
    else Path(__file__).with_name("default_detection.toml")
)


@dataclass(frozen=True)
class Thresholds:
    """Thresholds controlling risk tiers and category aggregation."""

    flag: float
    high: float
    critical: float
    category_active: float
    multi_signal_bonus: float


@dataclass(frozen=True)
class ModelConfig:
    """Settings for the interpretable logistic risk model."""

    learning_rate: float
    epochs: int


@dataclass(frozen=True)
class AggregationConfig:
    """Weights used to combine independent detection layers."""

    rules: float
    outliers: float
    model: float


@dataclass(frozen=True)
class DetectionConfig:
    """Complete runtime configuration for the analysis pipeline."""

    thresholds: Thresholds
    model: ModelConfig
    aggregation: AggregationConfig
    rules: dict[str, dict[str, float]]
    category_weights: dict[str, float]


def _section(raw: dict[str, Any], name: str) -> dict[str, Any]:
    """Return a required TOML table with a clear validation error."""

    value = raw.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"Missing or invalid [{name}] configuration section")
    return value


def _finite_float(value: Any, name: str) -> float:
    """Parse a finite numeric configuration value."""

    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Configuration value must be numeric: {name}") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"Configuration value must be finite: {name}")
    return parsed


def _required_float(section: dict[str, Any], key: str, section_name: str) -> float:
    """Read one required numeric setting."""

    if key not in section:
        raise ValueError(f"Missing configuration value: {section_name}.{key}")
    return _finite_float(section[key], f"{section_name}.{key}")


def _parse_rules(raw_rules: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Parse and validate every category rule table."""

    missing_categories = CHEAT_CATEGORIES.difference(raw_rules)
    if missing_categories:
        raise ValueError(
            f"Missing rule configuration for: {', '.join(sorted(missing_categories))}"
        )

    rules: dict[str, dict[str, float]] = {}
    for category in CHEAT_CATEGORIES:
        settings = raw_rules.get(category)
        if not isinstance(settings, dict):
            raise ValueError(f"Invalid rule configuration: rules.{category}")
        missing_keys = RULE_KEYS[category].difference(settings)
        if missing_keys:
            missing = ", ".join(f"rules.{category}.{key}" for key in sorted(missing_keys))
            raise ValueError(f"Missing configuration value(s): {missing}")
        rules[category] = {
            key: _finite_float(value, f"rules.{category}.{key}")
            for key, value in settings.items()
        }

        for soft_key, hard_key in THRESHOLD_PAIRS[category]:
            if rules[category][soft_key] >= rules[category][hard_key]:
                raise ValueError(
                    f"Expected rules.{category}.{soft_key} to be less than "
                    f"rules.{category}.{hard_key}"
                )
        for soft_key, hard_key in INVERSE_THRESHOLD_PAIRS.get(category, ()):
            if rules[category][soft_key] <= rules[category][hard_key]:
                raise ValueError(
                    f"Expected rules.{category}.{soft_key} to be greater than "
                    f"rules.{category}.{hard_key}"
                )
        weight_values = [
            value for key, value in rules[category].items() if key.endswith("_weight")
        ]
        if any(value < 0 for value in weight_values) or (
            weight_values and sum(weight_values) <= 0
        ):
            raise ValueError(f"Rule weights must be non-negative for: {category}")
    return rules


def load_config(path: str | Path | None = None) -> DetectionConfig:
    """Load detection settings from TOML and validate required sections."""

    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    # utf-8-sig accepts regular UTF-8 and strips BOMs added by Windows editors.
    raw: dict[str, Any] = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))

    raw_category_weights = _section(raw, "category_weights")
    missing_weights = SCORING_CATEGORIES.difference(raw_category_weights)
    extra_weights = set(raw_category_weights).difference(SCORING_CATEGORIES)
    if missing_weights or extra_weights:
        details = []
        if missing_weights:
            details.append(f"missing: {', '.join(sorted(missing_weights))}")
        if extra_weights:
            details.append(f"unknown: {', '.join(sorted(extra_weights))}")
        raise ValueError(f"Invalid category weights ({'; '.join(details)})")
    category_weights = {
        key: _finite_float(value, f"category_weights.{key}")
        for key, value in raw_category_weights.items()
    }
    if any(value < 0 for value in category_weights.values()) or not any(
        value > 0 for value in category_weights.values()
    ):
        raise ValueError("Category weights must be non-negative with at least one positive value")

    thresholds = _section(raw, "thresholds")
    model = _section(raw, "model")
    aggregation = _section(raw, "aggregation")
    aggregation_config = AggregationConfig(
        rules=_required_float(aggregation, "rules", "aggregation"),
        outliers=_required_float(aggregation, "outliers", "aggregation"),
        model=_required_float(aggregation, "model", "aggregation"),
    )
    aggregation_total = (
        aggregation_config.rules + aggregation_config.outliers + aggregation_config.model
    )
    if min(
        aggregation_config.rules,
        aggregation_config.outliers,
        aggregation_config.model,
    ) < 0:
        raise ValueError("Aggregation weights must be non-negative")
    if abs(aggregation_total - 1.0) > 0.0001:
        raise ValueError("Aggregation weights must sum to 1.0")

    parsed_thresholds = Thresholds(
        flag=_required_float(thresholds, "flag", "thresholds"),
        high=_required_float(thresholds, "high", "thresholds"),
        critical=_required_float(thresholds, "critical", "thresholds"),
        category_active=_required_float(thresholds, "category_active", "thresholds"),
        multi_signal_bonus=_required_float(thresholds, "multi_signal_bonus", "thresholds"),
    )
    if not 0 <= parsed_thresholds.flag < parsed_thresholds.high < parsed_thresholds.critical <= 100:
        raise ValueError("Risk thresholds must satisfy 0 <= flag < high < critical <= 100")
    if not 0 <= parsed_thresholds.category_active <= 100:
        raise ValueError("thresholds.category_active must be between 0 and 100")
    if parsed_thresholds.multi_signal_bonus < 0:
        raise ValueError("thresholds.multi_signal_bonus must be non-negative")

    learning_rate = _required_float(model, "learning_rate", "model")
    epochs = _required_float(model, "epochs", "model")
    if learning_rate <= 0 or not epochs.is_integer() or epochs <= 0:
        raise ValueError("model.learning_rate and model.epochs must be positive")

    return DetectionConfig(
        thresholds=parsed_thresholds,
        model=ModelConfig(
            learning_rate=learning_rate,
            epochs=int(epochs),
        ),
        aggregation=aggregation_config,
        rules=_parse_rules(_section(raw, "rules")),
        category_weights=category_weights,
    )
