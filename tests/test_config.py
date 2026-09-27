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

import sys
from pathlib import Path
from typing import Any

import pytest

import sofer.config as config
from sofer._csv_reader import stream_csv
from sofer.codebook import generate as generate_codebook
from sofer.model import DatasetConfig


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
        monkeypatch.setattr(
            "sofer.config._find_project_root", lambda start=None, stop_at=None: tmp_path
        )
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
        monkeypatch.setattr(
            "sofer.config._find_project_root", lambda start=None, stop_at=None: tmp_path
        )
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

    # -- TC-13: [tool.sofer] typed-key validation (fix-dataset-config-type-validation)

    def test_tool_config_rejects_wrong_type_for_int_key(self, monkeypatch, tmp_path):
        """output_max_bytes = "huge" must raise a stable diagnostic instead of
        reaching the module constant as a str."""
        toml = '[tool.sofer]\noutput_max_bytes = "huge"\n'
        with pytest.raises(ValueError, match=r"output_max_bytes.*integer"):
            self._load_with_toml(monkeypatch, tmp_path, toml)

    def test_tool_config_rejects_wrong_type_for_str_key(self, monkeypatch, tmp_path):
        """A numeric csv_delimiter in [tool.sofer] must be rejected."""
        toml = "[tool.sofer]\ncsv_delimiter = 5\n"
        with pytest.raises(ValueError, match=r"csv_delimiter.*string"):
            self._load_with_toml(monkeypatch, tmp_path, toml)

    def test_tool_config_rejects_wrong_type_for_float_key(self, monkeypatch, tmp_path):
        """codebook_numeric_threshold must be a number."""
        toml = '[tool.sofer]\ncodebook_numeric_threshold = "high"\n'
        with pytest.raises(ValueError, match=r"codebook_numeric_threshold.*number"):
            self._load_with_toml(monkeypatch, tmp_path, toml)

    def test_tool_config_rejects_bool_for_int_key(self, monkeypatch, tmp_path):
        """bool is not an int: output_max_bytes = true must be rejected."""
        toml = "[tool.sofer]\noutput_max_bytes = true\n"
        with pytest.raises(ValueError, match=r"output_max_bytes.*integer"):
            self._load_with_toml(monkeypatch, tmp_path, toml)

    def test_tool_config_keeps_string_to_list_coercion(self, monkeypatch, tmp_path):
        """A bare string for a list key keeps the documented [val] coercion."""
        toml = '[tool.sofer]\ncard_modality_tags = "tabular"\n'
        cfg = self._load_with_toml(monkeypatch, tmp_path, toml)
        assert cfg["card_modality_tags"] == ["tabular"]

    def test_tool_config_rejects_empty_failure_report_dir(self, monkeypatch, tmp_path):
        """An empty failure_report_dir would scatter reports in the state home."""
        toml = '[tool.sofer]\nfailure_report_dir = "   "\n'
        with pytest.raises(ValueError, match=r"failure_report_dir.*non-empty"):
            self._load_with_toml(monkeypatch, tmp_path, toml)

    def test_tool_config_rejects_non_positive_failure_report_bound(self, monkeypatch, tmp_path):
        """A non-positive gh timeout is meaningless and must be rejected."""
        toml = "[tool.sofer]\nfailure_report_gh_timeout_seconds = 0\n"
        with pytest.raises(ValueError, match=r"failure_report_gh_timeout_seconds.*positive"):
            self._load_with_toml(monkeypatch, tmp_path, toml)


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

    def test_reload_no_hit_restores_defaults(self, restore_tool_config, monkeypatch, pytree):
        """Nothing found -> all values equal _DEFAULTS and SOURCE_PATH is None."""
        # Sibling trees under a common parent with no pyproject.toml of its
        # own; chdir into the bare tree so the cwd fallback also finds nothing.
        config.reload(pytree("[tool.sofer]\nschema_sample_size = 500\n", at="with"))
        assert config.SCHEMA_SAMPLE_SIZE == 500
        bare = pytree(None, at="without")  # no pyproject.toml anywhere above
        monkeypatch.chdir(bare)
        config.reload(bare)
        for key, default in config._DEFAULTS.items():
            assert getattr(config, key.upper()) == default
        assert config.SOURCE_PATH is None

    def test_cwd_fallback_when_dataset_anchor_misses(
        self, restore_tool_config, monkeypatch, pytree
    ):
        """Dataset-anchor miss falls back to the cwd tree (precedence step 2)."""
        cwd_tree = pytree("[tool.sofer]\nschema_sample_size = 1000\n", at="cwd")
        monkeypatch.chdir(cwd_tree)
        dataset_dir = pytree(None, at="dataset")  # nothing above it but tmp root
        config.reload(dataset_dir)
        assert config.SCHEMA_SAMPLE_SIZE == 1000
        assert config.SOURCE_PATH == cwd_tree / "pyproject.toml"

    def test_sectionless_pyproject_yields_defaults(self, restore_tool_config, pytree):
        """A found pyproject.toml without [tool.sofer] stops the walk -> defaults."""
        root = pytree('[project]\nname = "section-less"\n')
        config.reload(root)
        for key, default in config._DEFAULTS.items():
            assert getattr(config, key.upper()) == default
        # The section-less file is still the selected source (AD-1).
        assert config.SOURCE_PATH == root / "pyproject.toml"


# ---------------------------------------------------------------------------
#  Phase 4 — one test class per spec requirement (TC-01 … TC-08)
# ---------------------------------------------------------------------------


class TestTc01DatasetDirAnchoring:
    """Discovery anchors on the dataset TOML directory."""

    def test_pyproject_two_levels_above_dataset_honored(self, restore_tool_config, pytree):
        """A pyproject.toml two levels above the dataset dir sets the value."""
        root = pytree("[tool.sofer]\nschema_sample_size = 500\n")
        dataset_dir = root / "lvl1" / "mydata"
        dataset_dir.mkdir(parents=True)
        (dataset_dir / "dataset.toml").write_text(
            '[dataset]\nname = "x"\nrepo_id = "u/x"\nlicense = "mit"\n',
            encoding="utf-8",
        )
        config.reload(dataset_dir)  # anchor = the dataset TOML's directory
        assert config.SCHEMA_SAMPLE_SIZE == 500

    def test_start_dir_itself_included_in_walk(self, pytree):
        """The start directory itself is part of the walk-up search."""
        root = pytree("[tool.sofer]\n")
        assert config._find_project_root(root) == root

    def test_reload_selects_temp_tree_without_user_dirs(self, restore_tool_config, pytree):
        """reload(temp_tree) never consults real user directories."""
        root = pytree("[tool.sofer]\ncsv_delimiter = ','\n")
        subdir = root / "deep" / "deeper"
        subdir.mkdir(parents=True)
        config.reload(subdir)
        assert config.SOURCE_PATH == root / "pyproject.toml"
        assert config.CSV_DELIMITER == ","


class TestTc02Precedence:
    """Dataset-dir result beats cwd; nothing found falls back to defaults."""

    def test_dataset_dir_wins_over_cwd(self, restore_tool_config, monkeypatch, pytree):
        """schema_sample_size: dataset tree (500) beats cwd tree (1000)."""
        cwd_tree = pytree("[tool.sofer]\nschema_sample_size = 1000\n", at="cwd")
        monkeypatch.chdir(cwd_tree)
        dataset_tree = pytree("[tool.sofer]\nschema_sample_size = 500\n", at="proj")
        dataset_dir = dataset_tree / "mydata"
        dataset_dir.mkdir()
        config.reload(dataset_dir)
        assert config.SCHEMA_SAMPLE_SIZE == 500

    def test_nothing_found_falls_back_to_defaults(self, restore_tool_config, monkeypatch, tmp_path):
        """No pyproject above dataset dir or cwd -> all values equal _DEFAULTS."""
        bare_cwd = tmp_path / "empty"
        bare_cwd.mkdir()
        monkeypatch.chdir(bare_cwd)
        dataset_dir = tmp_path / "ds"
        dataset_dir.mkdir()
        config.reload(dataset_dir)
        for key, default in config._DEFAULTS.items():
            assert getattr(config, key.upper()) == default


class TestTc03RuntimeIsolation:
    """sofer's own package/repo location is never consulted at runtime."""

    def test_editable_install_simulation(self, restore_tool_config, monkeypatch, pytree):
        """Package dir outside the user tree is never selected as source."""
        import sofer

        pkg_dir = Path(sofer.__file__).resolve().parent
        user_tree = pytree("[tool.sofer]\ncodebook_max_sample = 42\n", at="user")
        user_leaf = user_tree / "sub"
        user_leaf.mkdir()

        # The discovered source must be inside the user tree, never near the
        # installed package (editable-install simulation).
        root = config._find_project_root(user_leaf)
        assert root == user_tree
        assert not Path(sofer.__file__).is_relative_to(user_tree)

        config.reload(user_leaf)
        assert config.CODEBOOK_MAX_SAMPLE == 42
        assert config.SOURCE_PATH == user_tree / "pyproject.toml"
        assert pkg_dir.name != "user"

    def test_package_anchor_removed_from_source(self):
        """_find_project_root's source contains no Path(__file__) anchor."""
        import inspect

        source = inspect.getsource(config._find_project_root)
        assert "__file__" not in source


def _invoke_main(argv: list[str], monkeypatch) -> SystemExit | None:
    """Run ``sofer.cli.main()`` with *argv* and swallow SystemExit.

    Returns:
        The caught :class:`SystemExit` instance, or ``None`` if main returned
        without raising (should not happen — main always sys.exit()s).
    """
    import sofer.cli

    monkeypatch.setattr(sys, "argv", ["sofer", *argv])
    exc: SystemExit | None = None
    try:
        sofer.cli.main()
    except SystemExit as e:
        exc = e
    return exc


class TestTc04CliReloadHooks:
    """One reload per CLI invocation after the config path resolves."""

    def test_exactly_one_phase1_reload_per_invocation(
        self, restore_tool_config, monkeypatch, pytree
    ):
        """main([...]) fires one Phase-0 (cwd) and one Phase-1 (dataset) reload."""
        root = pytree("[tool.sofer]\nreport_line_width = 77\n")
        csv_path = root / "d.csv"
        csv_path.write_text("k\n1\n2\n", encoding="utf-8-sig")
        toml_path = root / "dataset.toml"
        toml_path.write_text(
            '[dataset]\nname = "test"\nrepo_id = "u/test"\nlicense = "mit"\n'
            '\n[[file]]\nlocal = "d.csv"\nremote = "d.csv"\n',
            encoding="utf-8",
        )

        calls: list[Path | None] = []
        real_reload = config.reload

        def counting_reload(start=None):
            calls.append(Path(start).resolve() if start is not None else None)
            return real_reload(start)

        monkeypatch.setattr(config, "reload", counting_reload)

        exc = _invoke_main(["codebook", "--all-files", "--config", str(toml_path)], monkeypatch)
        assert exc is not None and exc.code == 0

        phase1 = [c for c in calls if c == root.resolve()]
        phase0 = [c for c in calls if c is None]
        assert len(phase1) == 1, f"expected exactly one Phase-1 reload, got {calls}"
        assert len(phase0) == 1, f"expected exactly one Phase-0 reload, got {calls}"

    def test_single_file_codebook_without_config_anchors_cwd(
        self, restore_tool_config, monkeypatch, pytree
    ):
        """`sofer codebook FILE` with no --config anchors discovery on cwd."""
        root = pytree("[tool.sofer]\ncodebook_max_sample = 7\n")
        rows = "\n".join(str(i) for i in range(20))
        csv_path = root / "t.csv"
        csv_path.write_text(f"v\n{rows}\n", encoding="utf-8")
        monkeypatch.chdir(root)

        exc = _invoke_main(["codebook", str(csv_path)], monkeypatch)
        assert exc is not None and exc.code == 0
        # Phase-0 reload(None) picked up the cwd-tree override.
        assert config.CODEBOOK_MAX_SAMPLE == 7

    def test_csv_delimiter_override_effective_same_invocation(
        self, restore_tool_config, monkeypatch, pytree
    ):
        """Sibling-tree csv_delimiter=',' is honored within the same invocation.

        Note: prepare/validate read CSVs with the DATASET-level
        ``cfg.csv_delimiter`` ([meta] key), so the tool-wide consumer exercised
        here is ``sofer profile`` via :func:`stream_csv` defaults.
        """
        root = pytree("[tool.sofer]\ncsv_delimiter = ','\n")
        csv_path = root / "data.csv"
        csv_path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
        monkeypatch.chdir(root)

        exc = _invoke_main(["profile", str(csv_path)], monkeypatch)
        assert exc is not None and exc.code == 0

        metadata_path = root / "metadata.yaml"
        assert metadata_path.exists()
        content = metadata_path.read_text(encoding="utf-8")
        # With ';' (unreloaded default) the header would stay a single column.
        assert ", b" in content or "\n  b" in content or '"b"' in content or "- b" in content


class TestTc05LibraryFromToml:
    """Library callers resolve via DatasetConfig.from_toml."""

    def test_from_toml_triggers_dataset_anchored_reload(self, restore_tool_config, pytree):
        """from_toml on a tmp tree sets SCHEMA_SAMPLE_SIZE from sibling pyproject."""
        root = pytree("[tool.sofer]\nschema_sample_size = 250\n")
        data_dir = root / "proj" / "data"
        data_dir.mkdir(parents=True)
        toml_path = data_dir / "dataset.toml"
        toml_path.write_text('[dataset]\nname = "x"\nrepo_id = "u/x"\n', encoding="utf-8")

        cfg = DatasetConfig.from_toml(toml_path)  # library call, no CLI involved
        assert cfg.name == "x"
        assert config.SCHEMA_SAMPLE_SIZE == 250


class TestTc06PostReloadVisibility:
    """Consumers see reloaded values — no stale import-time copies."""

    def test_generate_sentinel_follows_reload(self, restore_tool_config, pytree):
        """generate(max_sample omitted) resolves through config at call time."""
        rows = "\n".join(str(i) for i in range(10))
        csv_path = pytree() / "t.csv"
        csv_path.write_text(f"v\n{rows}\n", encoding="utf-8")

        root = pytree("[tool.sofer]\ncodebook_max_sample = 5\n", at="cfg5")
        config.reload(root)
        md = generate_codebook(
            str(csv_path),
            delimiter=config.CSV_DELIMITER,
            encoding=config.CSV_ENCODING,
        )
        assert "**Analysed rows:** 5" in md

        # Sequential operation after a second reload sees the new value too.
        (root / "pyproject.toml").write_text(
            "[tool.sofer]\ncodebook_max_sample = 3\n", encoding="utf-8"
        )
        config.reload(root)
        md2 = generate_codebook(
            str(csv_path),
            delimiter=config.CSV_DELIMITER,
            encoding=config.CSV_ENCODING,
        )
        assert "**Analysed rows:** 3" in md2

    def test_stream_csv_reader_sentinel_follows_reload(self, restore_tool_config, pytree):
        """stream_csv with no max_sample yields at most the reloaded cap."""
        rows = "\n".join(str(i) for i in range(10))
        csv_path = pytree() / "t.csv"
        csv_path.write_text(f"v\n{rows}\n", encoding="utf-8")

        root = pytree("[tool.sofer]\ncodebook_max_sample = 4\n", at="cfg4")
        config.reload(root)
        results = list(stream_csv(csv_path))
        assert len(results) == 1 + 4  # header row + capped data rows

    def test_repeated_reads_consistent_after_reload(self, restore_tool_config, pytree):
        """Two sequential reads of the same constant agree post-reload."""
        root = pytree("[tool.sofer]\nreport_sub_line_width = 11\n")
        config.reload(root)
        first = config.REPORT_SUB_LINE_WIDTH
        second = config.REPORT_SUB_LINE_WIDTH
        assert first == second == 11


class TestTc07BootstrapKeys:
    """Bootstrap keys anchor on cwd until a dataset config exists."""

    def test_cwd_pyproject_supplies_default_config_name(
        self, restore_tool_config, monkeypatch, pytree
    ):
        """cwd-tree default_config_name flows into parser defaults after reload."""
        from sofer.cli import _build_parser

        tree = pytree('[tool.sofer]\ndefault_config_name = "my.toml"\n', at="proj")
        monkeypatch.chdir(tree)
        config.reload(None)

        scan_args = _build_parser().parse_args(["scan"])
        assert scan_args.config == "my.toml"
        codebook_args = _build_parser().parse_args(["codebook"])
        assert codebook_args.config == "my.toml"


# ---------------------------------------------------------------------------
#  TC-10 / TC-07-raw_dir — raw_dir bootstrap (delta 2026-08-29)
# ---------------------------------------------------------------------------


class TestTc10RawDirBootstrap:
    """Raw directory bootstrap key (TC-10) — reload(None) walk-up contract."""

    def test_default_raw_dir_is_raw(self, restore_tool_config, monkeypatch, pytree):
        """No pyproject raw_dir -> RAW_DIR == 'raw' (built-in default)."""
        bare = pytree(None, at="bare-default-raw")
        monkeypatch.chdir(bare)
        config.reload(None)
        assert config.RAW_DIR == "raw"
        assert config._DEFAULTS["raw_dir"] == "raw"

    def test_pyproject_overrides_raw_dir_via_reload_none(
        self, restore_tool_config, monkeypatch, pytree
    ):
        """cwd pyproject raw_dir='data-raw' -> reload(None) rebinds RAW_DIR."""
        tree = pytree('[tool.sofer]\nraw_dir = "data-raw"\n', at="override-raw")
        monkeypatch.chdir(tree)
        config.reload(None)
        assert config.RAW_DIR == "data-raw"
        assert config.SOURCE_PATH == tree / "pyproject.toml"

    def test_dataset_dir_wins_over_cwd_for_raw_dir(self, restore_tool_config, monkeypatch, pytree):
        """Dataset-dir raw_dir beats cwd raw_dir (precedence step 1 > step 2)."""
        cwd_tree = pytree('[tool.sofer]\nraw_dir = "inputs"\n', at="cwd-inputs")
        monkeypatch.chdir(cwd_tree)
        dataset_tree = pytree('[tool.sofer]\nraw_dir = "raw"\n', at="ds-raw")
        dataset_dir = dataset_tree / "mydata"
        dataset_dir.mkdir(parents=True)
        config.reload(dataset_dir)
        assert config.RAW_DIR == "raw"
        assert config.SOURCE_PATH == dataset_tree / "pyproject.toml"

    def test_cwd_pyproject_supplies_raw_dir(self, restore_tool_config, monkeypatch, pytree):
        """cwd-tree raw_dir='inputs' flows into RAW_DIR and init scaffolds inputs/."""
        from argparse import Namespace

        from sofer.cli import _cmd_init

        tree = pytree('[tool.sofer]\nraw_dir = "inputs"\n', at="cwd-raw-inputs")
        monkeypatch.chdir(tree)
        config.reload(None)
        assert config.RAW_DIR == "inputs"
        rc = _cmd_init(
            Namespace(
                name="my-ds",
                user="testuser",
                move_existing=False,
                dry_run=False,
                force=False,
            )
        )
        assert rc == 0
        assert (tree / "inputs").is_dir()
        assert not (tree / "raw").exists()
        # reset RAW_DIR for later tests that assume default
        config.reload(tree)

    def test_reload_none_walk_up_from_subdir_overrides_raw_dir(
        self, restore_tool_config, monkeypatch, pytree
    ):
        """reload(None) walks up from cwd subdir to find ancestor raw_dir."""
        root = pytree('[tool.sofer]\nraw_dir = "data-raw"\n', at="walkup-raw")
        sub = root / "a" / "b"
        sub.mkdir(parents=True)
        monkeypatch.chdir(sub)
        config.reload(None)
        assert config.RAW_DIR == "data-raw"

    def test_bootstrap_limitation_documented(self):
        """docs/configuration.md lists raw_dir as cwd-only bootstrap key."""
        docs = Path("docs/configuration.md").read_text(encoding="utf-8")
        assert "raw_dir" in docs
        # bootstrap keys section must name all three cwd-only keys
        assert "default_config_name" in docs
        assert "output_dir" in docs or "OUTPUT_DIR" in docs

    def test_pyproject_declares_full_default_surface(self):
        """Repo pyproject.toml [tool.sofer] matches config._DEFAULTS exactly.

        Set parity both ways plus value parity: every tunable default must
        be declared (AGENTS.md rule 1, #213) and no declared key may drift
        from its default. A new _DEFAULTS entry without a [tool.sofer]
        declaration fails here by construction.
        """
        try:
            import tomli as _tomli
        except ImportError:
            import tomllib as _tomli

        with open("pyproject.toml", "rb") as fh:
            data = _tomli.load(fh)
        declared = data["tool"]["sofer"]
        assert set(declared) == set(config._DEFAULTS), (
            f"undeclared={sorted(set(config._DEFAULTS) - set(declared))} "
            f"unknown={sorted(set(declared) - set(config._DEFAULTS))}"
        )
        for key, default in config._DEFAULTS.items():
            assert declared[key] == default, f"{key}: {declared[key]!r} != {default!r}"


class TestTc08SourceVisibility:
    """SOFER_VERBOSE reports the resolved source on stderr; silent by default."""

    def test_verbose_reports_absolute_source_path(
        self, restore_tool_config, monkeypatch, capsys, pytree
    ):
        monkeypatch.setenv("SOFER_VERBOSE", "1")
        root = pytree("[tool.sofer]\n")
        config.reload(root)
        captured = capsys.readouterr()
        assert str((root / "pyproject.toml").resolve()) in captured.err
        assert captured.out == ""

    def test_verbose_reports_built_in_defaults(
        self, restore_tool_config, monkeypatch, capsys, pytree
    ):
        monkeypatch.setenv("SOFER_VERBOSE", "1")
        bare = pytree(None, at="bare")
        monkeypatch.chdir(bare)
        config.reload(bare)
        captured = capsys.readouterr()
        assert "built-in defaults" in captured.err
        assert captured.out == ""

    @pytest.mark.parametrize("value", ["0", "", None])
    def test_silent_by_default(self, restore_tool_config, monkeypatch, capsys, pytree, value):
        """Without truthy SOFER_VERBOSE no source line appears anywhere."""
        if value is None:
            monkeypatch.delenv("SOFER_VERBOSE", raising=False)
        else:
            monkeypatch.setenv("SOFER_VERBOSE", value)
        root = pytree("[tool.sofer]\nreport_line_width = 9\n")
        config.reload(root)
        captured = capsys.readouterr()
        assert "[tool.sofer] source:" not in captured.err
        assert "[tool.sofer] source:" not in captured.out


# ---------------------------------------------------------------------------
#  TC-13 — profile_dir / render_dir (feat-profile-render-all-files)
# ---------------------------------------------------------------------------


class TestTc11ProfileRenderDir:
    """TC-13 defaults, overrides, reload rebinding, and no-hardcode contract."""

    def test_defaults_are_profiles_renders(self, restore_tool_config, monkeypatch, tmp_path):
        """No pyproject -> PROFILE_DIR=profiles, RENDER_DIR=renders."""
        bare = tmp_path / "bare-defaults"
        bare.mkdir()
        monkeypatch.chdir(bare)
        config.reload(bare)
        assert config.PROFILE_DIR == "profiles"
        assert config.RENDER_DIR == "renders"
        assert config._DEFAULTS["profile_dir"] == "profiles"
        assert config._DEFAULTS["render_dir"] == "renders"

    def test_pyproject_overrides_profile_dir(self, restore_tool_config, pytree):
        """pyproject profile_dir=docs/profiles -> PROFILE_DIR rebinds."""
        root = pytree('[tool.sofer]\nprofile_dir = "docs/profiles"\n')
        config.reload(root)
        assert config.PROFILE_DIR == "docs/profiles"
        assert config.SOURCE_PATH == root / "pyproject.toml"

    def test_pyproject_overrides_render_dir(self, restore_tool_config, pytree):
        """pyproject render_dir=docs/renders -> RENDER_DIR rebinds."""
        root = pytree('[tool.sofer]\nrender_dir = "docs/renders"\n')
        config.reload(root)
        assert config.RENDER_DIR == "docs/renders"

    def test_reload_rebinding(self, restore_tool_config, pytree):
        """Sequential reloads rebind both dirs without residue."""
        root_a = pytree('[tool.sofer]\nprofile_dir = "a"\nrender_dir = "ra"\n', at="a")
        config.reload(root_a)
        assert config.PROFILE_DIR == "a"
        assert config.RENDER_DIR == "ra"
        root_b = pytree('[tool.sofer]\nprofile_dir = "b"\nrender_dir = "rb"\n', at="b")
        config.reload(root_b)
        assert config.PROFILE_DIR == "b"
        assert config.RENDER_DIR == "rb"
        # fallback to defaults when pyproject has no section
        root_c = pytree('[project]\nname = "x"\n', at="c")
        config.reload(root_c)
        assert config.PROFILE_DIR == "profiles"
        assert config.RENDER_DIR == "renders"

    def test_empty_string_rejected(self, monkeypatch, tmp_path):
        """Empty profile_dir/render_dir must raise ValueError."""
        (tmp_path / "pyproject.toml").write_text(
            '[tool.sofer]\nprofile_dir = ""\n', encoding="utf-8"
        )
        monkeypatch.setattr(
            "sofer.config._find_project_root", lambda start=None, stop_at=None: tmp_path
        )
        with pytest.raises(ValueError, match="profile_dir"):
            config._load_tool_config()
        (tmp_path / "pyproject.toml").write_text(
            '[tool.sofer]\nrender_dir = "  "\n', encoding="utf-8"
        )
        with pytest.raises(ValueError, match="render_dir"):
            config._load_tool_config()

    def test_no_hardcodes_in_profile_and_render(self):
        """profile.py/render.py must not contain hardcoded \"profiles\"/\"renders\"."""
        profile_src = Path("src/sofer/profile.py").read_text(encoding="utf-8")
        render_src = Path("src/sofer/render.py").read_text(encoding="utf-8")
        assert '"profiles"' not in profile_src
        assert "'profiles'" not in profile_src
        assert '"renders"' not in render_src
        assert "'renders'" not in render_src
        # consumers must read through config
        assert "config.PROFILE_DIR" in profile_src
        assert "config.RENDER_DIR" in render_src
        assert "config.PROFILE_DIR" in render_src

    def test_pyproject_has_profile_render_keys(self):
        """Repository pyproject.toml declares profile_dir/render_dir under [tool.sofer]."""
        try:
            import tomli as _tomli
        except ImportError:
            import tomllib as _tomli

        with open("pyproject.toml", "rb") as fh:
            data = _tomli.load(fh)
        assert data["tool"]["sofer"]["profile_dir"] == "profiles"
        assert data["tool"]["sofer"]["render_dir"] == "renders"

    def test_mcp_containment_covers_new_dirs(self, tmp_path, restore_tool_config):
        """profile_dir/render_dir escaping the root must be rejected."""
        from sofer.mcp_server import _validate_output_targets

        root = tmp_path / "root"
        root.mkdir()
        (root / "pyproject.toml").write_text(
            '[tool.sofer]\nprofile_dir = "../../evil"\n', encoding="utf-8"
        )
        config.reload(root, stop_at=root)
        errors = _validate_output_targets(None, root=root, base=root)
        assert any("profile_dir" in e and "outside" in e for e in errors)

        (root / "pyproject.toml").write_text(
            '[tool.sofer]\nrender_dir = "../../evil"\n', encoding="utf-8"
        )
        config.reload(root, stop_at=root)
        errors = _validate_output_targets(None, root=root, base=root)
        assert any("render_dir" in e and "outside" in e for e in errors)


class TestReportTruncationLimitsConfig:
    """Issue #189 — quality/splits truncation caps are ``[tool.sofer]`` keys."""

    def test_quality_value_preview_len_default(self):
        """Distinct quality values truncate to 50 chars by default."""
        assert config._DEFAULTS["quality_value_preview_len"] == 50
        assert config.QUALITY_VALUE_PREVIEW_LEN == 50

    def test_splits_max_unclassified_names_default(self):
        """validate_layout lists 5 unclassified names by default."""
        assert config._DEFAULTS["splits_max_unclassified_names"] == 5
        assert config.SPLITS_MAX_UNCLASSIFIED_NAMES == 5

    def test_toml_overrides_new_keys(self, monkeypatch, tmp_path):
        """Both caps are overridable from ``[tool.sofer]``."""
        (tmp_path / "pyproject.toml").write_text(
            "[tool.sofer]\nquality_value_preview_len = 12\nsplits_max_unclassified_names = 2\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "sofer.config._find_project_root", lambda start=None, stop_at=None: tmp_path
        )
        merged = config._load_tool_config()
        assert merged["quality_value_preview_len"] == 12
        assert merged["splits_max_unclassified_names"] == 2

    def test_reload_rebinds_new_keys(self, restore_tool_config, pytree):
        """reload() rebinds both caps as module constants."""
        root = pytree(
            "[tool.sofer]\nquality_value_preview_len = 12\nsplits_max_unclassified_names = 2\n"
        )
        config.reload(root)
        assert config.QUALITY_VALUE_PREVIEW_LEN == 12
        assert config.SPLITS_MAX_UNCLASSIFIED_NAMES == 2

    def test_repo_pyproject_declares_every_default_key(self):
        """Total parity: every ``_DEFAULTS`` key is declared in ``[tool.sofer]``."""
        try:
            import tomli as _tomli
        except ImportError:
            import tomllib as _tomli

        with open("pyproject.toml", "rb") as fh:
            data = _tomli.load(fh)
        section = data["tool"]["sofer"]
        missing = [key for key in config._DEFAULTS if key not in section]
        assert missing == []
