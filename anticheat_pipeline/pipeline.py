"""Orchestrate feature, rule, statistical, model, and reporting stages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from anticheat_pipeline.config import DetectionConfig, load_config
from anticheat_pipeline.io import load_sessions, write_assessments_csv
from anticheat_pipeline.model import LogisticRiskModel, train_model
from anticheat_pipeline.outliers import fit_profile, outlier_score
from anticheat_pipeline.reports import write_category_csv, write_html_report
from anticheat_pipeline.schemas import PlayerAssessment
from anticheat_pipeline.scoring import score_session
from anticheat_pipeline.simulator import generate_demo_rows
from anticheat_pipeline.features import engineer_features


@dataclass(frozen=True)
class AnalysisResult:
    """Artifacts and assessments produced by one analysis run."""

    assessments: tuple[PlayerAssessment, ...]
    report_path: Path
    assessment_csv_path: Path
    category_csv_path: Path
    model: LogisticRiskModel


def _tier(score: float, config: DetectionConfig) -> str:
    if score >= config.thresholds.critical:
        return "critical"
    if score >= config.thresholds.high:
        return "high"
    if score >= config.thresholds.flag:
        return "review"
    return "low"


def run_analysis(
    input_path: str | Path,
    output_dir: str | Path,
    config_path: str | Path | None = None,
) -> AnalysisResult:
    """Run the complete portfolio analysis and write report artifacts."""

    config = load_config(config_path)
    sessions = load_sessions(input_path)
    profile = fit_profile(sessions)
    # The input is inference data and may have no labels. Train the portfolio
    # model on a separate deterministic simulated reference corpus instead.
    demo_training_sessions = [
        engineer_features({key: str(value) for key, value in row.items()})
        for row in generate_demo_rows()
    ]
    model = train_model(
        demo_training_sessions,
        learning_rate=config.model.learning_rate,
        epochs=config.model.epochs,
    )

    assessments: list[PlayerAssessment] = []
    for session in sessions:
        assessment = score_session(session, config)
        assessment.outlier_score = outlier_score(session, profile)
        assessment.model_probability = model.predict_probability(session)
        assessment.risk_score = round(
            assessment.rule_score * config.aggregation.rules
            + assessment.outlier_score * config.aggregation.outliers
            + assessment.model_probability * 100.0 * config.aggregation.model,
            2,
        )
        assessment.risk_tier = _tier(assessment.risk_score, config)

        if assessment.risk_score >= config.thresholds.flag:
            active_evidence = [
                explanation
                for risk in assessment.categories.values()
                if risk.score >= config.thresholds.category_active
                for explanation in risk.explanations
            ]
            assessment.explanations = active_evidence[:5]
            if assessment.outlier_score >= 55:
                assessment.explanations.append(
                    f"Statistical outlier score was {assessment.outlier_score:.0f}/100"
                )
            if assessment.model_probability >= 0.65:
                assessment.explanations.append(
                    f"Demo model estimated {assessment.model_probability:.0%} suspicious probability"
                )
        assessments.append(assessment)

    assessments.sort(key=lambda item: item.risk_score, reverse=True)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    assessment_csv = write_assessments_csv(assessments, output / "player_assessments.csv")
    category_csv = write_category_csv(assessments, output / "category_summary.csv", config)
    report = write_html_report(assessments, output / "anti_cheat_report.html", config)
    return AnalysisResult(
        assessments=tuple(assessments),
        report_path=report,
        assessment_csv_path=assessment_csv,
        category_csv_path=category_csv,
        model=model,
    )
