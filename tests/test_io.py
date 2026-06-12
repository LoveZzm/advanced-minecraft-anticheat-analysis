"""Tests for gameplay CSV input handling."""

from __future__ import annotations

import csv

from anticheat_pipeline.io import load_sessions
from tests.conftest import session_row


def test_load_sessions_accepts_utf8_bom(tmp_path) -> None:
    input_path = tmp_path / "excel-export.csv"
    row = session_row()
    with input_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)

    sessions = load_sessions(input_path)

    assert sessions[0].session_id == "S-test"
