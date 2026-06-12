"""Tests for analyst-facing report generation."""

from __future__ import annotations

from anticheat_pipeline.config import load_config
from anticheat_pipeline.reports import write_category_csv, write_html_report
from anticheat_pipeline.scoring import score_session


def test_html_report_contains_required_sections_and_escapes_player(
    normal_session, tmp_path
) -> None:
    assessment = score_session(normal_session, load_config())
    assessment.features = assessment.features.__class__(
        **{**assessment.features.__dict__, "player_id": "<script>alert(1)</script>"}
    )
    assessment.risk_score = 80
    assessment.risk_tier = "high"
    assessment.explanations = ["Synthetic review reason"]

    output = write_html_report([assessment], tmp_path / "report.html", load_config())
    content = output.read_text(encoding="utf-8")

    assert "Risk distribution" in content
    assert "Cheat category breakdown" in content
    assert "Top suspicious sessions" in content
    assert "Synthetic review reason" in content
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content
    assert "<script>alert(1)</script>" not in content


def test_category_csv_contains_all_categories(normal_session, tmp_path) -> None:
    assessment = score_session(normal_session, load_config())

    output = write_category_csv([assessment], tmp_path / "categories.csv", load_config())
    content = output.read_text(encoding="utf-8")

    assert "Autoclicker" in content
    assert "Macro Farming" in content
    assert "Multi-signal" in content
