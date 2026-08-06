"""Tests for sofer.cli — argument parsing and command dispatch.

The upload and validate commands depend on Hugging Face credentials and real
filesystem state, so they are integration-level.  Here we test everything
that can be verified without network calls or real data.
"""

import csv
import sys
from argparse import Namespace

from sofer import cli

# ── Argument parsing ──────────────────────────────────────────────────────────


class TestParser:
    def test_init_command(self):
        """`sofer init my-dataset` should parse to the init command."""
        args = cli._build_parser().parse_args(["init", "my-dataset"])
        assert args.command == "init"
        assert args.name == "my-dataset"
        assert callable(args.func)

    def test_validate_command(self):
        """`sofer validate path/to/file.toml` should parse correctly."""
        args = cli._build_parser().parse_args(["validate", "config.toml"])
        assert args.command == "validate"
        assert args.config == "config.toml"

    def test_upload_command(self):
        """`sofer upload config.toml` should parse correctly."""
        args = cli._build_parser().parse_args(["upload", "some.toml"])
        assert args.command == "upload"
        assert args.config == "some.toml"

    def test_codebook_command_no_output(self):
        """`sofer codebook data.csv` (stdout) should parse."""
        args = cli._build_parser().parse_args(["codebook", "data.csv"])
        assert args.command == "codebook"
        assert args.csv == "data.csv"
        assert args.output is None

    def test_codebook_command_with_output(self):
        """`sofer codebook data.csv -o out.md` should parse."""
        args = cli._build_parser().parse_args(["codebook", "data.csv", "-o", "out.md"])
        assert args.command == "codebook"
        assert args.csv == "data.csv"
        assert args.output == "out.md"

    def test_version(self):
        """`sofer --version` should print version and exit."""
        try:
            cli._build_parser().parse_args(["--version"])
        except SystemExit as e:
            assert e.code == 0


# ── init command ──────────────────────────────────────────────────────────────


class TestInitCommand:
    def test_init_creates_toml(self, tmp_path, monkeypatch):
        """`sofer init <name>` should write a .toml file."""
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_init(Namespace(name="my-dataset"))
        assert rc == 0
        assert (tmp_path / "my-dataset.toml").exists()

    def test_init_refuses_overwrite(self, tmp_path, monkeypatch):
        """`sofer init <name>` on an existing file should fail."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "existing.toml").write_text("hello", encoding="utf-8")
        rc = cli._cmd_init(Namespace(name="existing"))
        assert rc == 1  # refuses to overwrite

    def test_init_content_is_valid_toml(self, tmp_path, monkeypatch):
        """The generated template should parse as valid TOML."""
        try:
            import tomli as _tomli
        except ImportError:
            import tomllib as _tomli

        monkeypatch.chdir(tmp_path)
        cli._cmd_init(Namespace(name="test-ds"))
        content = (tmp_path / "test-ds.toml").read_text(encoding="utf-8")
        parsed = _tomli.loads(content)
        assert parsed["dataset"]["name"] == "test-ds"
        assert parsed["dataset"]["repo_id"] == "YOUR_USER/test-ds"

    def test_init_content_has_placeholders(self, tmp_path, monkeypatch):
        """The template should contain TODO markers to guide the user."""
        monkeypatch.chdir(tmp_path)
        cli._cmd_init(Namespace(name="ds"))
        content = (tmp_path / "ds.toml").read_text(encoding="utf-8")
        assert "TODO" in content

    def test_init_template_has_build_dir(self, tmp_path, monkeypatch):
        """The template declares ``[dataset] build_dir = "build"`` so the
        default prepare/publish output directory is explicit."""
        try:
            import tomli as _tomli
        except ImportError:
            import tomllib as _tomli

        monkeypatch.chdir(tmp_path)
        cli._cmd_init(Namespace(name="build-ds"))
        content = (tmp_path / "build-ds.toml").read_text(encoding="utf-8")
        parsed = _tomli.loads(content)
        assert parsed["dataset"]["build_dir"] == "build"


# ─── Entry point smoke test ────────────────────────────────────────────────────


def test_main_help_prints(monkeypatch):
    """`sofer --help` should print usage and exit 0."""
    monkeypatch.setattr(sys, "argv", ["sofer", "--help"])
    try:
        cli.main()
    except SystemExit as e:
        assert e.code == 0


# ── upload subparser ─────────────────────────────────────────────────


class TestUploadForceFlag:
    def test_force_flag_defaults_to_false(self):
        """--force should default to False when not passed."""
        args = cli._build_parser().parse_args(["upload", "config.toml"])
        assert args.force is False

    def test_force_flag_explicit(self):
        """--force should be True when passed."""
        args = cli._build_parser().parse_args(["upload", "config.toml", "--force"])
        assert args.force is True

    def test_dry_run_flag_defaults_to_false(self):
        """--dry-run should default to False when not passed."""
        args = cli._build_parser().parse_args(["upload", "config.toml"])
        assert args.dry_run is False

    def test_dry_run_flag_explicit(self):
        """--dry-run should be True when passed."""
        args = cli._build_parser().parse_args(["upload", "config.toml", "--dry-run"])
        assert args.dry_run is True

    def test_force_and_keep_csv_together(self):
        """--force and --keep-csv can be combined."""
        args = cli._build_parser().parse_args(["upload", "config.toml", "--force", "--keep-csv"])
        assert args.force is True
        assert args.keep_csv is True


# ── prepare subparser ───────────────────────────────────────────────


class TestPrepareParser:
    """Argument parsing for the ``prepare`` subcommand (PR 2 scope)."""

    def test_prepare_command_defaults(self):
        """`prepare config.toml` parses with all flags defaulting."""
        args = cli._build_parser().parse_args(["prepare", "config.toml"])
        assert args.command == "prepare"
        assert args.config == "config.toml"
        assert args.output is None
        assert args.all_files is False
        assert args.no_checks is False
        assert args.force is False
        assert args.verify is False
        assert callable(args.func)

    def test_prepare_flags_parse(self):
        """All prepare flags parse together."""
        args = cli._build_parser().parse_args(
            [
                "prepare",
                "c.toml",
                "--output",
                "out/",
                "--all-files",
                "--no-checks",
                "--force",
                "--verify",
            ]
        )
        assert args.output == "out/"
        assert args.all_files is True
        assert args.no_checks is True
        assert args.force is True
        assert args.verify is True


# ── publish subparser ───────────────────────────────────────────────


class TestPublishParser:
    """Argument parsing for the ``publish`` subcommand (PR 3 scope)."""

    def test_publish_command_defaults(self):
        """`publish config.toml` parses with all flags defaulting."""
        args = cli._build_parser().parse_args(["publish", "config.toml"])
        assert args.command == "publish"
        assert args.config == "config.toml"
        assert args.target == "hf"
        assert args.output is None
        assert args.force is False
        assert args.keep_csv is False
        assert args.dry_run is False
        assert callable(args.func)

    def test_publish_flags_parse(self):
        """All publish flags parse together."""
        args = cli._build_parser().parse_args(
            [
                "publish",
                "c.toml",
                "--target",
                "local",
                "--output",
                "out/",
                "--force",
                "--keep-csv",
                "--dry-run",
            ]
        )
        assert args.target == "local"
        assert args.output == "out/"
        assert args.force is True
        assert args.keep_csv is True
        assert args.dry_run is True

    def test_publish_invalid_target_rejected(self):
        """An unsupported --target value raises SystemExit."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["publish", "c.toml", "--target", "s3"])


# ── codebook placeholder validation ──────────────────────────────────────────


class TestCodebookPlaceholderValidation:
    """RED — placeholder validation not yet wired in _cmd_codebook."""

    def test_placeholder_toml_exits_with_error(self, tmp_path, monkeypatch, capsys):
        """TOML with YOUR_USER placeholder should exit 1 with error message."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "data").mkdir(exist_ok=True)
        (tmp_path / "data" / "f.csv").write_text("col\n1\n", encoding="utf-8")

        toml_path = tmp_path / "test.toml"
        toml_path.write_text(
            '[dataset]\nname = "test"\nrepo_id = "YOUR_USER/test-ds"\n\n'
            '[[file]]\nlocal = "data/f.csv"\nremote = "data/f.csv"\n',
            encoding="utf-8",
        )

        rc = cli._cmd_codebook(Namespace(all_files=True, config=str(toml_path), csv=None))
        assert rc == 1
        captured = capsys.readouterr()
        assert "placeholder" in captured.err.lower()
        assert "YOUR_USER" in captured.err

    def test_valid_toml_generates_codebook(self, tmp_path, monkeypatch):
        """Valid TOML with real user should generate codebook successfully."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "data").mkdir(exist_ok=True)
        (tmp_path / "data" / "f.csv").write_text("col\n1\n", encoding="utf-8")

        toml_path = tmp_path / "test.toml"
        toml_path.write_text(
            '[dataset]\nname = "test"\nrepo_id = "alice/my-dataset"\n\n'
            '[[file]]\nlocal = "data/f.csv"\nremote = "data/f.csv"\n',
            encoding="utf-8",
        )

        rc = cli._cmd_codebook(
            Namespace(all_files=True, config=str(toml_path), csv=None, output=None)
        )
        assert rc == 0
        root = tmp_path / "codebook.md"
        assert root.exists()


# ── scan subparser ──────────────────────────────────────────────────────────────


class TestScanParser:
    """Argument parsing tests for the ``scan`` subcommand."""

    def test_default_config(self):
        """`scan` with no positional argument defaults to dataset.toml."""
        args = cli._build_parser().parse_args(["scan"])
        assert args.command == "scan"
        assert args.config == "dataset.toml"
        assert args.dry_run is False
        assert args.force is False
        assert args.ext is None
        assert callable(args.func)

    def test_explicit_config_path(self):
        """`scan my-config.toml` should set config positionally."""
        args = cli._build_parser().parse_args(["scan", "my-config.toml"])
        assert args.config == "my-config.toml"

    def test_dry_run_flag(self):
        """`--dry-run` should be True when passed."""
        args = cli._build_parser().parse_args(["scan", "--dry-run"])
        assert args.dry_run is True

    def test_force_flag(self):
        """`--force` should be True when passed."""
        args = cli._build_parser().parse_args(["scan", "--force"])
        assert args.force is True

    def test_ext_single(self):
        """`--ext .csv` restricts to one extension."""
        args = cli._build_parser().parse_args(["scan", "--ext", ".csv"])
        assert args.ext == [".csv"]

    def test_ext_repeatable(self):
        """`--ext .csv --ext .parquet` accumulates."""
        args = cli._build_parser().parse_args(["scan", "--ext", ".csv", "--ext", ".parquet"])
        assert args.ext == [".csv", ".parquet"]

    def test_ext_invalid_is_rejected(self):
        """An unsupported --ext value raises SystemExit."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["scan", "--ext", ".xml"])

    def test_combined_flags(self):
        """`scan --dry-run --force --ext .csv` all parse together."""
        args = cli._build_parser().parse_args(["scan", "--dry-run", "--force", "--ext", ".csv"])
        assert args.dry_run is True
        assert args.force is True
        assert args.ext == [".csv"]


# ── Fix 1: ran_checks propagation ─────────────────────────────────────────


class TestValidateRanChecks:
    """RED — ran_checks NOT propagated yet, _count_passed_quality returns 0."""

    def test_validate_reports_passed_gt_zero(self, tmp_path, monkeypatch, capsys):
        """After validate with real data, the summary shows passed > 0."""
        monkeypatch.chdir(tmp_path)

        csv_path = tmp_path / "data.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            # Row 2 is completely empty → triggers empty_rows finding.
            # All other checks (duplicates, format_consistency, corrupt_records,
            # encoding_validation, cross_file_types) should pass.
            # With ran_checks populated: 8 checks run - 1 finding = 7 passed.
            # Without ran_checks (the bug): passed = 0.
            writer.writerows([["id", "name"], ["1", "Alice"], ["", ""], ["2", "Bob"]])

        toml_path = tmp_path / "test.toml"
        toml_path.write_text(
            '[dataset]\nname = "test"\nrepo_id = "u/test"\n\n'
            '[[file]]\nlocal = "data.csv"\nremote = "data.csv"\n',
            encoding="utf-8",
        )

        rc = cli._cmd_validate(Namespace(config=str(toml_path)))
        assert rc == 0
        captured = capsys.readouterr()
        # The quality section must be printed because empty_rows produced a finding
        assert "Quality checks" in captured.out, f"Quality section missing:\n{captured.out}"
        # Key assertion: "passed" should appear with a number > 0
        import re

        m = re.search(r"(\d+)\s+passed", captured.out)
        assert m is not None, f"No 'N passed' found in output:\n{captured.out}"
        passed_count = int(m.group(1))
        assert passed_count > 0, (
            f"Expected passed > 0 but got {passed_count}. "
            f"ran_checks is likely empty (bug).\nOutput:\n{captured.out}"
        )
