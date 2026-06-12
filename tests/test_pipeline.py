"""End-to-end pipeline contract test."""

from __future__ import annotations

import csv
from pathlib import Path

from anticheat_pipeline.pipeline import run_analysis
from anticheat_pipeline.simulator import generate_demo_csv, generate_demo_rows


def test_packaged_and_repository_configs_match() -> None:
    repository = Path(__file__).parent.parent / "config" / "detection.toml"
    packaged = (
        Path(__file__).parent.parent / "anticheat_pipeline" / "default_detection.toml"
    )

    assert repository.read_text(encoding="utf-8").splitlines()[3:] == packaged.read_text(
        encoding="utf-8"
    ).splitlines()[2:]


def test_pipeline_writes_all_review_artifacts(tmp_path) -> None:
    input_path = generate_demo_csv(tmp_path / "sessions.csv")

    result = run_analysis(input_path, tmp_path / "reports")

    assert len(result.assessments) == 198
    assert result.report_path.exists()
    assert result.assessment_csv_path.exists()
    assert result.category_csv_path.exists()
    assert result.assessments[0].risk_score >= result.assessments[-1].risk_score


def test_pipeline_accepts_unlabeled_inference_data(tmp_path) -> None:
    rows = generate_demo_rows()[:5]
    for row in rows:
        row.pop("label")
        row.pop("simulated_archetype")
    input_path = tmp_path / "unlabeled.csv"
    with input_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    result = run_analysis(input_path, tmp_path / "reports")

    assert len(result.assessments) == 5
    assert result.report_path.exists()
