"""Deterministic simulated gameplay data for the portfolio demonstration."""

from __future__ import annotations

import csv
from pathlib import Path
import random
from typing import Any


FIELDNAMES = [
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
    "label",
    "simulated_archetype",
]


def _bounded(rng: random.Random, center: float, spread: float, low: float, high: float) -> float:
    return max(low, min(high, rng.gauss(center, spread)))


def _normal_row(rng: random.Random, index: int) -> dict[str, Any]:
    duration = _bounded(rng, 24, 10, 5, 65)
    cps = _bounded(rng, 7.0, 1.6, 2.0, 11.0)
    resources_per_minute = _bounded(rng, 3.8, 1.1, 0.2, 7.0)
    actions_per_minute = _bounded(rng, 8.5, 2.2, 3.5, 15.0)
    return {
        "session_id": f"S{index:04d}",
        "player_id": f"player_{index:03d}",
        "mode": rng.choice(["Bed Wars", "SkyWars", "Duels", "SkyBlock"]),
        "duration_minutes": round(duration, 2),
        "click_count": round(cps * duration * 60),
        "click_interval_std_ms": round(_bounded(rng, 58, 17, 28, 110), 2),
        "max_reach_blocks": round(_bounded(rng, 2.86, 0.16, 2.3, 3.18), 3),
        "aim_snap_rate": round(_bounded(rng, 0.19, 0.09, 0.01, 0.42), 3),
        "perfect_tracking_ratio": round(_bounded(rng, 0.25, 0.10, 0.03, 0.52), 3),
        "target_switches": round(_bounded(rng, 1.7, 0.7, 0.2, 3.8) * duration),
        "path_efficiency": round(_bounded(rng, 0.69, 0.11, 0.35, 0.88), 3),
        "repeated_path_ratio": round(_bounded(rng, 0.24, 0.12, 0.02, 0.54), 3),
        "idle_ratio": round(_bounded(rng, 0.12, 0.07, 0.01, 0.35), 3),
        "resources_collected": round(resources_per_minute * duration),
        "unique_actions": round(actions_per_minute * duration),
        "chat_messages": rng.randint(0, 12),
        "session_hour": rng.randint(7, 23),
        "label": 0,
        "simulated_archetype": "normal",
    }


def _apply_archetype(
    row: dict[str, Any], archetype: str, rng: random.Random
) -> dict[str, Any]:
    duration = float(row["duration_minutes"])
    if archetype in {"autoclicker", "multi_signal"}:
        row["click_count"] = round(_bounded(rng, 18.2, 1.1, 15.5, 21.0) * duration * 60)
        row["click_interval_std_ms"] = round(_bounded(rng, 8, 2, 3, 13), 2)
    if archetype in {"reach", "multi_signal"}:
        row["max_reach_blocks"] = round(_bounded(rng, 3.72, 0.18, 3.35, 4.2), 3)
    if archetype in {"aim_assist", "multi_signal"}:
        row["aim_snap_rate"] = round(_bounded(rng, 0.80, 0.07, 0.63, 0.96), 3)
        row["perfect_tracking_ratio"] = round(_bounded(rng, 0.87, 0.05, 0.74, 0.98), 3)
        row["target_switches"] = round(_bounded(rng, 7.3, 0.8, 5.6, 9.2) * duration)
    if archetype == "bot_behavior":
        row["path_efficiency"] = round(_bounded(rng, 0.97, 0.01, 0.94, 0.99), 3)
        row["repeated_path_ratio"] = round(_bounded(rng, 0.91, 0.04, 0.82, 0.98), 3)
        row["unique_actions"] = round(_bounded(rng, 1.8, 0.4, 0.8, 2.7) * duration)
    if archetype in {"macro_farming", "multi_signal"}:
        duration = _bounded(rng, 160, 25, 115, 220)
        row["duration_minutes"] = round(duration, 2)
        row["resources_collected"] = round(_bounded(rng, 16, 2, 12, 21) * duration)
        row["repeated_path_ratio"] = round(_bounded(rng, 0.91, 0.04, 0.80, 0.98), 3)
        row["session_hour"] = rng.randint(0, 4)
    row["label"] = 1
    row["simulated_archetype"] = archetype
    return row


def generate_demo_rows(seed: int = 2026) -> list[dict[str, Any]]:
    """Create a balanced-enough simulated population with known archetypes."""

    rng = random.Random(seed)
    rows = [_normal_row(rng, index) for index in range(1, 151)]
    archetypes = [
        "autoclicker",
        "reach",
        "aim_assist",
        "bot_behavior",
        "macro_farming",
        "multi_signal",
    ]
    index = len(rows) + 1
    for archetype in archetypes:
        for _ in range(8):
            rows.append(_apply_archetype(_normal_row(rng, index), archetype, rng))
            index += 1
    return rows


def generate_demo_csv(path: str | Path, seed: int = 2026) -> Path:
    """Write deterministic simulated sessions to a CSV file."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(generate_demo_rows(seed))
    return output
