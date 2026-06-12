"""Feature engineering for aggregate gameplay session telemetry."""

from __future__ import annotations

from collections.abc import Mapping
import math

from anticheat_pipeline.schemas import SessionFeatures


REQUIRED_COLUMNS = {
    "session_id",
    "player_id",
    "mode",
    "duration_minutes",
    "click_count",
    "click_interval_std_ms",
    "max_reach_blocks",
    "aim_snap_rate",
    "perfect_tracking_ratio",
    "target_switches",
    "path_efficiency",
    "repeated_path_ratio",
    "idle_ratio",
    "resources_collected",
    "unique_actions",
    "chat_messages",
    "session_hour",
}


def _number(row: Mapping[str, str], key: str) -> float:
    """Parse a finite numeric field and provide a useful validation error."""

    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid or missing numeric field: {key}") from exc
    if not math.isfinite(value):
        raise ValueError(f"Field must be finite: {key}")
    return value


def engineer_features(row: Mapping[str, str]) -> SessionFeatures:
    """Convert one raw session row into normalized detection features."""

    missing = REQUIRED_COLUMNS.difference(row)
    if missing:
        raise ValueError(f"Missing input columns: {', '.join(sorted(missing))}")

    duration = _number(row, "duration_minutes")
    if duration <= 0:
        raise ValueError("duration_minutes must be greater than zero")

    interval_std = max(_number(row, "click_interval_std_ms"), 0.0)
    hour = int(_number(row, "session_hour")) % 24
    raw_label = row.get("label")
    label = 0 if raw_label is None or not raw_label.strip() else int(float(raw_label))
    return SessionFeatures(
        session_id=row["session_id"],
        player_id=row["player_id"],
        mode=row["mode"],
        duration_minutes=duration,
        clicks_per_second=_number(row, "click_count") / (duration * 60.0),
        click_consistency=1.0 / (1.0 + interval_std / 40.0),
        max_reach_blocks=_number(row, "max_reach_blocks"),
        aim_snap_rate=_number(row, "aim_snap_rate"),
        perfect_tracking_ratio=_number(row, "perfect_tracking_ratio"),
        target_switches_per_minute=_number(row, "target_switches") / duration,
        path_efficiency=_number(row, "path_efficiency"),
        repeated_path_ratio=_number(row, "repeated_path_ratio"),
        idle_ratio=_number(row, "idle_ratio"),
        resources_per_minute=_number(row, "resources_collected") / duration,
        actions_per_minute=_number(row, "unique_actions") / duration,
        chat_messages=_number(row, "chat_messages"),
        overnight_activity=1.0 if hour < 5 else 0.0,
        label=label,
    )
