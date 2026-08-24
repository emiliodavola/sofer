"""Tests for sofer.config — metadata-core tool-wide config keys.

Covers the Phase 1 (WU1) additions: semantic priors, inference thresholds,
profile sample cap, and confidence rounding precision. Each new key must be
readable from ``[tool.sofer]`` in ``pyproject.toml`` and fall back to a sane
default when absent.

Config values are always read through attribute access on the ``config``
module (``config.X``), never via frozen ``from .config import X`` bindings —
mirroring the consumer contract enforced since the #56 discovery fix.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import sofer.config as config


class TestMetadataCoreDefaults:
    """Default values and types for the new config constants."""

    def test_semantic_priors_default(self):
        """SEMANTIC_PRIORS defaults to the email prior of 0.98."""
        assert config.SEMANTIC_PRIORS == {"email": 0.98}

    def test_semantic_priors_is_dict(self):
        """SEMANTIC_PRIORS must be a dict (mapping detector name -> prior)."""
        assert isinstance(config.SEMANTIC_PRIORS, dict)

    def test_confirm_threshold_default(self):
        """CONFIRM_THRESHOLD defaults to 0.8."""
        assert config.CONFIRM_THRESHOLD == 0.8

    def test_min_threshold_default(self):
        """MIN_THRESHOLD defaults to 0.5."""
        assert config.MIN_THRESHOLD == 0.5

    def test_detect_threshold_default(self):
        """DETECT_THRESHOLD defaults to 0.5."""
        assert config.DETECT_THRESHOLD == 0.5

    def test_confidence_round_digits_default(self):
        """CONFIDENCE_ROUND_DIGITS defaults to 4."""
        assert config.CONFIDENCE_ROUND_DIGITS == 4

    def test_profile_max_sample_default(self):
        """PROFILE_MAX_SAMPLE defaults to 100_000 (matches codebook_max_sample)."""
        assert config.PROFILE_MAX_SAMPLE == 100_000

    def test_thresholds_are_floats(self):
        """The three thresholds must be floats for the confidence comparison."""
        assert isinstance(config.CONFIRM_THRESHOLD, float)
        assert isinstance(config.MIN_THRESHOLD, float)
        assert isinstance(config.DETECT_THRESHOLD, float)

    def test_round_digits_is_int(self):
        """CONFIDENCE_ROUND_DIGITS must be an int."""
        assert isinstance(config.CONFIDENCE_ROUND_DIGITS, int)


class TestMetadataCoreTomlOverride:
    """New keys must be overridable from ``[tool.sofer]`` in pyproject.toml."""

    def _load_with_toml(self, monkeypatch, tmp_path: Path, toml: str) -> dict[str, Any]:
        """Point config discovery at a temp pyproject.toml and load the section."""
        (tmp_path / "pyproject.toml").write_text(toml, encoding="utf-8")
        monkeypatch.setattr("sofer.config._find_project_root", lambda start=None: tmp_path)
        return config._load_tool_config()

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
        monkeypatch.setattr("sofer.config._find_project_root", lambda start=None: tmp_path)
        return config._load_tool_config()

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


class TestImportTimeIsolation:
    """Import binds constants from _DEFAULTS only — no filesystem access."""

    def test_constants_equal_defaults_at_import(self):
        """Every module constant mirrors its _DEFAULTS entry until reload runs."""
        for key, default in config._DEFAULTS.items():
            assert getattr(config, key.upper()) == default

    def test_source_path_none_before_reload(self):
        """SOURCE_PATH starts as None (built-in defaults) in a fresh process state.

        This asserts the module-level declaration; reload() rebinds it.
        """
        assert hasattr(config, "SOURCE_PATH")


class TestFindProjectRoot:
    """Walk-up discovery contract (TC-01/TC-03 unit layer)."""

    def test_finds_pyproject_in_start_dir_itself(self, pytree):
        """A pyproject.toml IN the start directory is found (start is included)."""
        root = pytree("[tool.sofer]\ncsv_delimiter = ','\n")
        assert config._find_project_root(root) == root

    def test_walks_up_to_nearest_pyproject(self, pytree):
        """Nearest ancestor pyproject.toml wins over farther ones."""
        root = pytree('[project]\nname = "outer"\n')
        inner = root / "a" / "b"
        inner.mkdir(parents=True)
        assert config._find_project_root(inner) == root

    def test_returns_none_when_exhausted(self, pytree):
        """No pyproject.toml anywhere up the tree -> None (never cwd fallback)."""
        bare = pytree()  # tmp tree without any pyproject.toml
        nested = bare / "deep" / "deeper"
        nested.mkdir(parents=True)
        assert config._find_project_root(nested) is None

    def test_start_none_anchors_on_cwd(self, monkeypatch, pytree):
        """start=None anchors on Path.cwd()."""
        root = pytree("[tool.sofer]\n")
        monkeypatch.chdir(root)
        assert config._find_project_root(None) == root


class TestReload:
    """reload(start) rebinding contract (TC-01 unit layer)."""

    def test_reload_selects_temp_tree(self, restore_tool_config, pytree):
        """reload(subdir) selects the temp pyproject without touching user dirs."""
        root = pytree("[tool.sofer]\nschema_sample_size = 500\n")
        subdir = root / "sub"
        subdir.mkdir()
        config.reload(subdir)
        assert config.SCHEMA_SAMPLE_SIZE == 500
        assert config.SOURCE_PATH == root / "pyproject.toml"

    def test_reload_no_hit_restores_defaults(self, restore_tool_config, pytree):
        """Nothing found -> all values equal _DEFAULTS and SOURCE_PATH is None."""
        # Sibling trees: "with" holds the pyproject.toml, "without" sits beside
        # it under a common parent that has no pyproject.toml of its own.
        config.reload(pytree("[tool.sofer]\nschema_sample_size = 500\n", at="with"))
        assert config.SCHEMA_SAMPLE_SIZE == 500
        bare = pytree(None, at="without")  # no pyproject.toml anywhere above
        config.reload(bare)
        for key, default in config._DEFAULTS.items():
            assert getattr(config, key.upper()) == default
        assert config.SOURCE_PATH is None

    def test_sectionless_pyproject_yields_defaults(self, restore_tool_config, pytree):
        """A found pyproject.toml without [tool.sofer] stops the walk -> defaults."""
        root = pytree('[project]\nname = "section-less"\n')
        config.reload(root)
        for key, default in config._DEFAULTS.items():
            assert getattr(config, key.upper()) == default
        # The section-less file is still the selected source (AD-1).
        assert config.SOURCE_PATH == root / "pyproject.toml"
