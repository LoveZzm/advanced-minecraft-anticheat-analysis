"""Command-line interface for the anti-cheat analysis pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from anticheat_pipeline import __version__
from anticheat_pipeline.pipeline import run_analysis
from anticheat_pipeline.simulator import generate_demo_csv


def build_parser() -> argparse.ArgumentParser:
    """Build the public command-line argument parser."""

    parser = argparse.ArgumentParser(
        prog="python -m anticheat_pipeline",
        description=(
            "Analyze aggregate Minecraft-style gameplay telemetry and generate "
            "an explainable integrity review report."
        ),
    )
    parser.add_argument("--input", type=Path, help="Input gameplay session CSV")
    parser.add_argument(
        "--output", type=Path, default=Path("reports"), help="Report output directory"
    )
    parser.add_argument("--config", type=Path, help="Optional detection TOML config")
    parser.add_argument(
        "--generate-sample",
        type=Path,
        metavar="CSV_PATH",
        help="Generate deterministic simulated demo data before analysis",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)
    input_path: Path | None = args.input
    if args.generate_sample:
        generate_demo_csv(args.generate_sample)
        input_path = input_path or args.generate_sample
        print(f"Generated simulated gameplay data: {args.generate_sample}")
    if input_path is None:
        parser.error("--input is required unless --generate-sample is provided")

    try:
        result = run_analysis(input_path, args.output, args.config)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"Analysis failed: {exc}", file=sys.stderr)
        return 2

    review_count = sum(item.risk_tier != "low" for item in result.assessments)
    print(f"Analyzed {len(result.assessments)} simulated gameplay sessions.")
    print(f"Queued {review_count} sessions for review.")
    print(f"HTML report: {result.report_path}")
    print(f"Assessment CSV: {result.assessment_csv_path}")
    print(f"Category CSV: {result.category_csv_path}")
    return 0
