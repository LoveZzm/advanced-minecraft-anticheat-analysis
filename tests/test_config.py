"""Tests for detection configuration validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from anticheat_pipeline.config import load_config


DEFAULT_CONFIG = Path(__file__).parent.parent / "config" / "detection.toml"


def test_config_rejects_missing_category_weight(tmp_path) -> None:
    content = DEFAULT_CONFIG.read_text(encoding="utf-8").replace(
        "multi_signal = 0.75\n", ""
    )
    config_path = tmp_path / "missing-weight.toml"
    config_path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="missing: multi_signal"):
        load_config(config_path)


def test_config_rejects_invalid_risk_threshold_order(tmp_path) -> None:
    content = DEFAULT_CONFIG.read_text(encoding="utf-8").replace("high = 70", "high = 90")
    config_path = tmp_path / "invalid-thresholds.toml"
    config_path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="flag < high < critical"):
        load_config(config_path)


def test_config_rejects_invalid_inverse_threshold_order(tmp_path) -> None:
    content = DEFAULT_CONFIG.read_text(encoding="utf-8").replace(
        "actions_hard = 1.0", "actions_hard = 5.0"
    )
    config_path = tmp_path / "invalid-actions-threshold.toml"
    config_path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="actions_soft.*greater than.*actions_hard"):
        load_config(config_path)


def test_config_accepts_utf8_bom(tmp_path) -> None:
    config_path = tmp_path / "windows-editor-config.toml"
    config_path.write_text(DEFAULT_CONFIG.read_text(encoding="utf-8"), encoding="utf-8-sig")

    config = load_config(config_path)

    assert config.thresholds.flag == 52
