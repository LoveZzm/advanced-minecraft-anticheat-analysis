"""Input and output helpers for gameplay session data."""

from __future__ import annotations

import csv
from pathlib import Path

from anticheat_pipeline.features import engineer_features
from anticheat_pipeline.schemas import PlayerAssessment, SessionFeatures


def load_sessions(path: str | Path) -> list[SessionFeatures]:
    """Load and validate gameplay sessions from a CSV file."""

    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    # utf-8-sig accepts regular UTF-8 and strips the BOM emitted by Excel.
    with input_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        sessions = [engineer_features(row) for row in csv.DictReader(csv_file)]
    if not sessions:
        raise ValueError("Input file contains no gameplay sessions")
    return sessions


def write_assessments_csv(
    assessments: list[PlayerAssessment], output_path: str | Path
) -> Path:
    """Write flattened player assessments to CSV."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [assessment.to_row() for assessment in assessments]
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
