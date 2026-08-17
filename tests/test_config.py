"""Tests for sofer.config — metadata-core tool-wide config keys.

Covers the Phase 1 (WU1) additions: semantic priors, inference thresholds,
profile sample cap, and confidence rounding precision. Each new key must be
readable from ``[tool.sofer]`` in ``pyproject.toml`` and fall back to a sane
default when absent.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sofer.config import (
    CONFIDENCE_ROUND_DIGITS,
    CONFIRM_THRESHOLD,
    DETECT_THRESHOLD,
    MIN_THRESHOLD,
    PROFILE_MAX_SAMPLE,
    SEMANTIC_PRIORS,
    _load_tool_config,
)


class TestMetadataCoreDefaults:
    """Default values and types for the new config constants."""

    def test_semantic_priors_default(self):
        """SEMANTIC_PRIORS defaults to the email prior of 0.98."""
        assert SEMANTIC_PRIORS == {"email": 0.98}

    def test_semantic_priors_is_dict(self):
        """SEMANTIC_PRIORS must be a dict (mapping detector name -> prior)."""
        assert isinstance(SEMANTIC_PRIORS, dict)

    def test_confirm_threshold_default(self):
        """CONFIRM_THRESHOLD defaults to 0.8."""
        assert CONFIRM_THRESHOLD == 0.8

    def test_min_threshold_default(self):
        """MIN_THRESHOLD defaults to 0.5."""
        assert MIN_THRESHOLD == 0.5

    def test_detect_threshold_default(self):
        """DETECT_THRESHOLD defaults to 0.5."""
        assert DETECT_THRESHOLD == 0.5

    def test_confidence_round_digits_default(self):
        """CONFIDENCE_ROUND_DIGITS defaults to 4."""
        assert CONFIDENCE_ROUND_DIGITS == 4

    def test_profile_max_sample_default(self):
        """PROFILE_MAX_SAMPLE defaults to 100_000 (matches codebook_max_sample)."""
        assert PROFILE_MAX_SAMPLE == 100_000

    def test_thresholds_are_floats(self):
        """The three thresholds must be floats for the confidence comparison."""
        assert isinstance(CONFIRM_THRESHOLD, float)
        assert isinstance(MIN_THRESHOLD, float)
        assert isinstance(DETECT_THRESHOLD, float)

    def test_round_digits_is_int(self):
        """CONFIDENCE_ROUND_DIGITS must be an int."""
        assert isinstance(CONFIDENCE_ROUND_DIGITS, int)


class TestMetadataCoreTomlOverride:
    """New keys must be overridable from ``[tool.sofer]`` in pyproject.toml."""

    def _load_with_toml(self, monkeypatch, tmp_path: Path, toml: str) -> dict[str, Any]:
        """Point config at a temp pyproject.toml and load the tool section."""
        (tmp_path / "pyproject.toml").write_text(toml, encoding="utf-8")
        monkeypatch.setattr("sofer.config._find_project_root", lambda: tmp_path)
        return _load_tool_config()

    def test_toml_overrides_semantic_priors(self, monkeypatch, tmp_path):
        """A custom semantic_priors dict should replace the default."""
        toml = "[tool.sofer]\nsemantic_priors = { email = 0.95, phone = 0.9 }\n"
        cfg = self._load_with_toml(monkeypatch, tmp_path, toml)
        assert cfg["semantic_priors"] == {"email": 0.95, "phone": 0.9}

    def test_toml_overrides_thresholds(self, monkeypatch, tmp_path):
        """Custom thresholds should replace the defaults."""
        toml = (
            "[tool.sofer]\n"
            "confirm_threshold = 0.9\n"
            "min_threshold = 0.6\n"
            "detect_threshold = 0.55\n"
            "confidence_round_digits = 2\n"
            "profile_max_sample = 5000\n"
        )
        cfg = self._load_with_toml(monkeypatch, tmp_path, toml)
        assert cfg["confirm_threshold"] == 0.9
        assert cfg["min_threshold"] == 0.6
        assert cfg["detect_threshold"] == 0.55
        assert cfg["confidence_round_digits"] == 2
        assert cfg["profile_max_sample"] == 5000

    def test_missing_toml_uses_defaults(self, monkeypatch, tmp_path):
        """With no [tool.sofer] section, defaults are preserved."""
        cfg = self._load_with_toml(monkeypatch, tmp_path, '[project]\nname = "x"\n')
        assert cfg["semantic_priors"] == {"email": 0.98}
        assert cfg["confirm_threshold"] == 0.8


class TestSemanticPriorsValidation:
    """semantic_priors must reject a non-dict value (config contract)."""

    def _load_with_toml(self, monkeypatch, tmp_path: Path, toml: str) -> dict[str, Any]:
        (tmp_path / "pyproject.toml").write_text(toml, encoding="utf-8")
        monkeypatch.setattr("sofer.config._find_project_root", lambda: tmp_path)
        return _load_tool_config()

    def test_semantic_priors_rejects_non_dict(self, monkeypatch, tmp_path):
        """A non-dict semantic_priors value must raise a clear ValueError."""
        toml = '[tool.sofer]\nsemantic_priors = "email: 0.98"\n'
        with pytest.raises(ValueError, match="semantic_priors"):
            self._load_with_toml(monkeypatch, tmp_path, toml)

    def test_semantic_priors_accepts_valid_dict(self, monkeypatch, tmp_path):
        """A valid dict value must load without error."""
        toml = "[tool.sofer]\nsemantic_priors = { email = 0.98 }\n"
        cfg = self._load_with_toml(monkeypatch, tmp_path, toml)
        assert cfg["semantic_priors"] == {"email": 0.98}
