"""Generate review-oriented CSV and standalone HTML reports."""

from __future__ import annotations

from collections import Counter
import csv
from html import escape
from pathlib import Path

from anticheat_pipeline.config import DetectionConfig
from anticheat_pipeline.schemas import PlayerAssessment


CATEGORY_LABELS = {
    "autoclicker": "Autoclicker",
    "reach": "Reach",
    "aim_assist": "Aim Assist",
    "bot_behavior": "Bot Behavior",
    "macro_farming": "Macro Farming",
    "multi_signal": "Multi-signal",
}


def _flagged(
    assessments: list[PlayerAssessment], config: DetectionConfig
) -> list[PlayerAssessment]:
    return [
        assessment
        for assessment in assessments
        if assessment.risk_score >= config.thresholds.flag
    ]


def write_category_csv(
    assessments: list[PlayerAssessment],
    output_path: str | Path,
    config: DetectionConfig,
) -> Path:
    """Write category-level review counts and average scores."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for category, label in CATEGORY_LABELS.items():
        scores = [assessment.categories[category].score for assessment in assessments]
        rows.append(
            {
                "category": label,
                "review_count": sum(
                    score >= config.thresholds.category_active for score in scores
                ),
                "average_score": round(sum(scores) / len(scores), 2),
                "maximum_score": round(max(scores), 2),
            }
        )
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _bar_chart(items: list[tuple[str, int]], maximum: int) -> str:
    bars = []
    for label, value in items:
        width = 0 if maximum == 0 else value / maximum * 100
        bars.append(
            f'<div class="bar-row"><span>{escape(label)}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{width:.1f}%"></div></div>'
            f"<strong>{value}</strong></div>"
        )
    return "".join(bars)


def _category_cells(assessment: PlayerAssessment) -> str:
    cells = []
    for category in CATEGORY_LABELS:
        score = assessment.categories[category].score
        cells.append(
            f'<div class="category-score"><span>{escape(CATEGORY_LABELS[category])}</span>'
            f"<strong>{score:.0f}</strong></div>"
        )
    return "".join(cells)


def _player_cards(
    flagged: list[PlayerAssessment],
) -> str:
    cards = []
    for assessment in flagged[:12]:
        explanations = "".join(
            f"<li>{escape(explanation)}</li>" for explanation in assessment.explanations
        )
        cards.append(
            f"""
            <article class="player-card">
              <div class="player-heading">
                <div><span class="eyebrow">{escape(assessment.features.mode)}</span>
                <h3>{escape(assessment.features.player_id)}</h3>
                <p>{escape(assessment.features.session_id)}</p></div>
                <div class="risk-badge {escape(assessment.risk_tier)}">
                  <strong>{assessment.risk_score:.0f}</strong><span>{escape(assessment.risk_tier)}</span>
                </div>
              </div>
              <div class="category-grid">{_category_cells(assessment)}</div>
              <ul class="evidence">{explanations}</ul>
              <div class="signal-row">
                <span>Rules <strong>{assessment.rule_score:.0f}</strong></span>
                <span>Outlier <strong>{assessment.outlier_score:.0f}</strong></span>
                <span>Model <strong>{assessment.model_probability:.0%}</strong></span>
              </div>
            </article>
            """
        )
    return "".join(cards) or '<div class="empty">No sessions crossed the configured review threshold.</div>'


def write_html_report(
    assessments: list[PlayerAssessment],
    output_path: str | Path,
    config: DetectionConfig,
) -> Path:
    """Write a polished standalone HTML report for analyst review."""

    if not assessments:
        raise ValueError("Cannot generate a report without assessments")
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flagged = _flagged(assessments, config)
    average_risk = sum(item.risk_score for item in assessments) / len(assessments)
    tiers = Counter(item.risk_tier for item in assessments)
    category_counts = [
        (
            label,
            sum(
                item.categories[category].score >= config.thresholds.category_active
                for item in assessments
            ),
        )
        for category, label in CATEGORY_LABELS.items()
    ]
    tier_items = [
        ("Low", tiers["low"]),
        ("Review", tiers["review"]),
        ("High", tiers["high"]),
        ("Critical", tiers["critical"]),
    ]

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Session Integrity Review</title>
<style>
:root{{--ink:#172033;--muted:#68728a;--line:#e7eaf0;--paper:#fff;--bg:#f4f6fa;--navy:#111a2f;--blue:#4f6df5;--cyan:#18a7a7;--amber:#e19a25;--red:#d9545d}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 Inter,Segoe UI,Arial,sans-serif}}
.shell{{max-width:1240px;margin:auto;padding:34px 24px 64px}} .hero{{background:var(--navy);color:white;border-radius:20px;padding:34px;position:relative;overflow:hidden}}
.hero:after{{content:"";position:absolute;width:420px;height:420px;border-radius:50%;right:-180px;top:-230px;background:linear-gradient(135deg,#4f6df5,#1bc3b0);opacity:.35}}
.eyebrow{{text-transform:uppercase;letter-spacing:.14em;font-size:11px;font-weight:700;color:#9aa9d2}} h1{{font-size:34px;line-height:1.15;margin:10px 0 8px}} .hero p{{color:#bdc7df;max-width:680px;margin:0}}
.notice{{margin-top:20px;padding:11px 14px;border:1px solid #34405d;border-radius:9px;color:#cbd3e6;background:#17233d;max-width:760px}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0}} .metric,.panel,.player-card{{background:var(--paper);border:1px solid var(--line);box-shadow:0 8px 24px rgba(26,39,70,.05)}}
.metric{{border-radius:14px;padding:18px}} .metric span{{color:var(--muted);font-size:12px}} .metric strong{{display:block;font-size:27px;margin-top:3px}} .grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.panel{{border-radius:16px;padding:22px}} h2{{font-size:18px;margin:0 0 18px}} .bar-row{{display:grid;grid-template-columns:112px 1fr 30px;gap:11px;align-items:center;margin:13px 0;color:var(--muted);font-size:12px}}
.bar-track{{height:8px;background:#eef0f5;border-radius:99px;overflow:hidden}} .bar-fill{{height:100%;background:linear-gradient(90deg,var(--blue),var(--cyan));border-radius:99px}} .bar-row strong{{color:var(--ink);text-align:right}}
.section-heading{{display:flex;justify-content:space-between;align-items:end;margin:34px 0 14px}} .section-heading h2{{margin:0;font-size:22px}} .section-heading p{{margin:0;color:var(--muted)}}
.cards{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}} .player-card{{padding:20px;border-radius:16px}} .player-heading{{display:flex;justify-content:space-between;gap:20px}} h3{{font-size:20px;margin:3px 0 0}} .player-heading p{{margin:0;color:var(--muted);font-size:12px}}
.risk-badge{{width:62px;height:62px;border-radius:13px;display:grid;place-content:center;text-align:center;background:#eef1f7}} .risk-badge strong{{font-size:21px;line-height:1}} .risk-badge span{{text-transform:uppercase;font-size:8px;letter-spacing:.1em;margin-top:5px}}
.risk-badge.review{{background:#fff4da;color:#9a6300}} .risk-badge.high,.risk-badge.critical{{background:#fee9ea;color:#a62d37}} .category-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:17px 0}}
.category-score{{background:#f6f7fa;padding:8px;border-radius:8px}} .category-score span{{display:block;color:var(--muted);font-size:9px;text-transform:uppercase;letter-spacing:.05em}} .category-score strong{{font-size:15px}}
.evidence{{padding-left:18px;color:#44506a;min-height:64px}} .evidence li{{margin:3px 0}} .signal-row{{display:flex;gap:18px;border-top:1px solid var(--line);padding-top:12px;color:var(--muted);font-size:11px}} .signal-row strong{{color:var(--ink)}}
.empty{{padding:30px;background:white;border:1px dashed #ccd2df;border-radius:14px;color:var(--muted)}} footer{{margin-top:34px;color:var(--muted);font-size:11px}}
@media(max-width:850px){{.metrics,.grid,.cards{{grid-template-columns:1fr 1fr}}}} @media(max-width:580px){{.metrics,.grid,.cards{{grid-template-columns:1fr}}.shell{{padding:14px}}.hero{{padding:24px}}}}
</style>
</head>
<body><main class="shell">
<section class="hero"><span class="eyebrow">Integrity analytics / portfolio demonstration</span>
<h1>Session Integrity Review</h1>
<p>Explainable triage across combat, automation, statistical, and learned behavior signals.</p>
<div class="notice">This report analyzes simulated gameplay data. Scores indicate sessions for human review; they are not proof of cheating and must not be used as automatic ban decisions.</div>
</section>
<section class="metrics">
<div class="metric"><span>Sessions analyzed</span><strong>{len(assessments)}</strong></div>
<div class="metric"><span>Queued for review</span><strong>{len(flagged)}</strong></div>
<div class="metric"><span>Average risk</span><strong>{average_risk:.1f}</strong></div>
<div class="metric"><span>Critical sessions</span><strong>{tiers["critical"]}</strong></div>
</section>
<section class="grid">
<div class="panel"><h2>Risk distribution</h2>{_bar_chart(tier_items, max(tiers.values(), default=0))}</div>
<div class="panel"><h2>Cheat category breakdown</h2>{_bar_chart(category_counts, max((value for _, value in category_counts), default=0))}</div>
</section>
<div class="section-heading"><div><span class="eyebrow">Review queue</span><h2>Top suspicious sessions</h2></div><p>Threshold: {config.thresholds.flag:.0f}/100</p></div>
<section class="cards">{_player_cards(flagged)}</section>
<footer>Generated by the Data-Driven Anti-Cheat Portfolio Pipeline. Simulated telemetry, configurable heuristic thresholds, robust outlier analysis, and a lightweight logistic model.</footer>
</main></body></html>"""
    path.write_text(html, encoding="utf-8")
    return path
