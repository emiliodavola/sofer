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

    def test_upload_command_removed(self):
        """`sofer upload config.toml` should be rejected with exit code 2 (CLI-R01)."""
        import pytest

        with pytest.raises(SystemExit) as excinfo:
            cli._build_parser().parse_args(["upload", "some.toml"])
        assert excinfo.value.code == 2

    def test_help_shows_prepare_publish_not_upload(self, capsys):
        """`sofer --help` lists prepare + publish and never mentions upload."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["--help"])
        out = capsys.readouterr().out
        assert "prepare" in out
        assert "publish" in out
        assert "upload" not in out

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

    def test_version(self, capsys):
        """`sofer --version` prints `sofer v<resolved version>` and exits 0 (CLI-R05)."""
        import pytest

        from sofer._version import get_version

        with pytest.raises(SystemExit) as excinfo:
            cli._build_parser().parse_args(["--version"])
        assert excinfo.value.code == 0
        out = capsys.readouterr().out.strip()
        assert out == f"sofer v{get_version()}"


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


# ── init template: prepare/publish, no upload (CLI-R02) ───────────────────────


class TestInitTemplateCommands:
    def test_init_template_uses_prepare_publish(self, tmp_path, monkeypatch):
        """_INIT_TEMPLATE usage comments reference prepare/publish, never upload."""
        monkeypatch.chdir(tmp_path)
        cli._cmd_init(Namespace(name="ds"))
        content = (tmp_path / "ds.toml").read_text(encoding="utf-8")
        assert "sofer upload" not in content
        assert "sofer prepare" in content
        assert "sofer publish" in content

    def test_init_prints_prepare_publish(self, tmp_path, monkeypatch, capsys):
        """_cmd_init success prints prepare + publish hints, never upload."""
        monkeypatch.chdir(tmp_path)
        cli._cmd_init(Namespace(name="ds"))
        captured = capsys.readouterr()
        assert "sofer upload" not in captured.out
        assert "sofer prepare" in captured.out
        assert "sofer publish" in captured.out


# ── shared _load_and_validate prologue (Phase 5.2) ────────────────────────────


class TestLoadAndValidate:
    """The shared validate/prepare/publish prologue rejects invalid configs."""

    def _placeholder_toml(self, tmp_path):
        """A TOML whose repo_id still carries the YOUR_USER placeholder."""
        toml_path = tmp_path / "test.toml"
        toml_path.write_text(
            '[dataset]\nname = "test"\nrepo_id = "YOUR_USER/test-ds"\n\n'
            '[[file]]\nlocal = "missing.csv"\nremote = "missing.csv"\n',
            encoding="utf-8",
        )
        return str(toml_path)

    def test_validate_config_errors_return_1(self, tmp_path, capsys):
        rc = cli._cmd_validate(Namespace(config=self._placeholder_toml(tmp_path)))
        assert rc == 1
        assert "Configuration errors" in capsys.readouterr().out

    def test_prepare_config_errors_return_1(self, tmp_path, capsys):
        rc = cli._cmd_prepare(
            Namespace(
                config=self._placeholder_toml(tmp_path),
                output=None,
                all_files=False,
                no_checks=False,
                force=False,
                verify=False,
            )
        )
        assert rc == 1
        assert "fix before preparing" in capsys.readouterr().out

    def test_publish_config_errors_return_1(self, tmp_path, capsys):
        rc = cli._cmd_publish(
            Namespace(
                config=self._placeholder_toml(tmp_path),
                target="hf",
                output=None,
                force=False,
                keep_csv=False,
                dry_run=False,
            )
        )
        assert rc == 1
        assert "fix before publishing" in capsys.readouterr().out

    def test_prepare_case_collision_refuses_no_output(self, tmp_path, monkeypatch, capsys):
        """RC-R16 S5: case-differing .csv remotes make prepare exit 1 with no
        staging output directory created."""
        (tmp_path / "data").mkdir(exist_ok=True)
        (tmp_path / "data" / "a.csv").write_text("x\n1\n", encoding="utf-8")
        (tmp_path / "data" / "b.csv").write_text("x\n2\n", encoding="utf-8")

        toml_path = tmp_path / "test.toml"
        toml_path.write_text(
            '[dataset]\nname = "test"\nrepo_id = "u/test"\nbuild_dir = "build"\n\n'
            '[[file]]\nlocal = "data/a.csv"\nremote = "Data/a.csv"\n'
            '[[file]]\nlocal = "data/b.csv"\nremote = "data/a.csv"\n',
            encoding="utf-8",
        )

        rc = cli._cmd_prepare(
            Namespace(
                config=str(toml_path),
                output=None,
                all_files=False,
                no_checks=False,
                force=False,
                verify=False,
            )
        )
        assert rc == 1
        assert "Case-fold collision" in capsys.readouterr().out
        # The staging output directory must never be created (S5).
        assert not (tmp_path / "build").exists()


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
        root = tmp_path / "cache" / "codebook.md"
        assert root.exists()
        assert not (tmp_path / "codebook.md").exists()


# ── raw-folder organization: init + --move-existing (CLI-R07 / CLI-R08) ────────


class TestInitRawFolder:
    """CLI-R07: init creates raw/ and --move-existing depth-1 SUPPORTED_FORMATS."""

    def test_init_creates_raw_dir(self, tmp_path, monkeypatch):
        """sofer init creates raw/ and TOML contains raw/ guidance (SCN-07 template)."""
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_init(Namespace(name="my-ds", move_existing=False, dry_run=False, force=False))
        assert rc == 0
        assert (tmp_path / "raw").is_dir()
        assert (tmp_path / "my-ds.toml").exists()
        content = (tmp_path / "my-ds.toml").read_text(encoding="utf-8")
        assert "raw/" in content
        assert "scan copies to cache" in content.lower() or "Source files -> raw/" in content

    def test_init_idempotent(self, tmp_path, monkeypatch):
        """Second init succeeds when raw/ already exists with files."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "raw").mkdir()
        (tmp_path / "raw" / "keep.csv").write_text("a\n1\n", encoding="utf-8")
        rc = cli._cmd_init(Namespace(name="my-ds", move_existing=False, dry_run=False, force=False))
        assert rc == 0
        rc2 = cli._cmd_init(
            Namespace(name="other", move_existing=False, dry_run=False, force=False)
        )
        assert rc2 == 0
        assert (tmp_path / "raw").is_dir()
        assert (tmp_path / "raw" / "keep.csv").exists()

    def test_move_existing_depth1_only_supported(self, tmp_path, monkeypatch):
        """Only depth-1 SUPPORTED_FORMATS move; subdirs, .txt, cache/ stay."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "b.csv").write_text("x\n1\n", encoding="utf-8")
        (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
        (tmp_path / "cache").mkdir()
        (tmp_path / "cache" / "c.csv").write_text("x\n1\n", encoding="utf-8")
        rc = cli._cmd_init(Namespace(name="my-ds", move_existing=True, dry_run=False, force=True))
        assert rc == 0
        assert (tmp_path / "raw" / "a.csv").exists()
        assert not (tmp_path / "a.csv").exists()
        assert (tmp_path / "subdir" / "b.csv").exists()
        assert (tmp_path / "notes.txt").exists()
        assert (tmp_path / "cache" / "c.csv").exists()

    def test_move_existing_collision_guard(self, tmp_path, monkeypatch, capsys):
        """Collision with existing raw/ content fails naming both sources."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "raw").mkdir()
        (tmp_path / "raw" / "a.csv").write_text("existing\n", encoding="utf-8")
        (tmp_path / "a.csv").write_text("loose\n", encoding="utf-8")
        rc = cli._cmd_init(Namespace(name="my-ds", move_existing=True, dry_run=False, force=True))
        assert rc == 1
        err = capsys.readouterr().err.lower()
        assert "collision" in err
        assert "a.csv" in err
        # no move happened
        assert (tmp_path / "a.csv").exists()
        assert (tmp_path / "raw" / "a.csv").exists()

    def test_move_existing_dry_run_no_mutation(self, tmp_path, monkeypatch, capsys):
        """--dry-run previews moves, creates TOML, but not raw/ when absent nor moves."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        (tmp_path / "b.xlsx").write_text("x", encoding="utf-8")
        rc = cli._cmd_init(Namespace(name="my-ds", move_existing=True, dry_run=True, force=False))
        assert rc == 0
        out = capsys.readouterr().out
        assert "dry run" in out.lower()
        assert "a.csv" in out
        assert (tmp_path / "my-ds.toml").exists()
        # raw/ not created when absent under dry-run
        assert not (tmp_path / "raw").exists()
        assert (tmp_path / "a.csv").exists()
        assert (tmp_path / "b.xlsx").exists()

    def test_move_existing_non_interactive_guard(self, tmp_path, monkeypatch, capsys):
        """not isatty without --force skips move, creates raw/, hints --force."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        rc = cli._cmd_init(Namespace(name="my-ds", move_existing=True, dry_run=False, force=False))
        assert rc == 0
        err = capsys.readouterr().err
        assert "Skipping move" in err
        assert "--force" in err
        assert (tmp_path / "raw").is_dir()
        assert (tmp_path / "a.csv").exists()
        assert (tmp_path / "my-ds.toml").exists()

    def test_move_existing_prompt_n_aborts(self, tmp_path, monkeypatch, capsys):
        """TTY + N at prompt aborts move, still creates raw/ and TOML, exit 0."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        monkeypatch.setattr("builtins.input", lambda _p="": "N")
        rc = cli._cmd_init(Namespace(name="my-ds", move_existing=True, dry_run=False, force=False))
        assert rc == 0
        out = capsys.readouterr().out
        assert "Aborted" in out
        assert (tmp_path / "raw").is_dir()
        assert (tmp_path / "a.csv").exists()

    def test_move_existing_prompt_y_moves(self, tmp_path, monkeypatch):
        """TTY + y at prompt moves files into raw/."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        monkeypatch.setattr("builtins.input", lambda _p="": "y")
        rc = cli._cmd_init(Namespace(name="my-ds", move_existing=True, dry_run=False, force=False))
        assert rc == 0
        assert (tmp_path / "raw" / "a.csv").exists()
        assert not (tmp_path / "a.csv").exists()

    def test_template_mentions_raw_no_stale_path(self, tmp_path, monkeypatch):
        """Generated TOML mentions raw/ guidance and no stale path/to hint."""
        monkeypatch.chdir(tmp_path)
        cli._cmd_init(Namespace(name="my-ds", move_existing=False, dry_run=False, force=False))
        content = (tmp_path / "my-ds.toml").read_text(encoding="utf-8")
        assert "raw/" in content
        assert "path/to" not in content


class TestInitHelp:
    """CLI-R08: sofer init --help documents --move-existing, --dry-run, --force."""

    def test_help_lists_flags(self, capsys):
        """Help shows --move-existing, --dry-run, --force and pipeline."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["init", "--help"])
        out = capsys.readouterr().out
        assert "--move-existing" in out
        assert "--dry-run" in out
        assert "--force" in out
        assert "raw/" in out

    def test_help_mentions_pipeline(self, capsys):
        """Help description mentions raw/ -> cache/ -> build/ pipeline."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["init", "--help"])
        out = capsys.readouterr().out
        assert "cache" in out.lower()
        assert "build" in out.lower()


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


class TestScanMoveCLI:
    """SCN-07 MOVE e2e via _cmd_scan: tree, dry-run, collision, prompt, ext filter."""

    def test_e2e_move_tree(self, tmp_path, monkeypatch):
        """a.csv + sub/b.xlsx → raw/a.csv + raw/sub/b.xlsx, originals gone."""
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "b.xlsx").write_text("x", encoding="utf-8")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_scan(Namespace(config=str(cfg), dry_run=False, force=True, ext=None))
        assert rc == 0
        assert (tmp_path / "raw" / "a.csv").exists()
        assert (tmp_path / "raw" / "sub" / "b.xlsx").exists()
        assert not (tmp_path / "a.csv").exists()
        assert not (tmp_path / "sub" / "b.xlsx").exists()
        assert (tmp_path / "cache" / "a.csv").exists()

    def test_dry_run_no_fs_or_toml(self, tmp_path, monkeypatch, capsys):
        """--dry-run prints -> raw/... without FS or TOML mutation."""
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "b.xlsx").write_text("x", encoding="utf-8")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        original = cfg.read_text(encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_scan(Namespace(config=str(cfg), dry_run=True, force=False, ext=None))
        assert rc == 0
        out = capsys.readouterr().out
        assert "-> raw/a.csv" in out
        assert "-> raw/sub/b.xlsx" in out
        assert (tmp_path / "a.csv").exists()
        assert not (tmp_path / "raw").exists()
        assert not (tmp_path / "cache").exists()
        assert cfg.read_text(encoding="utf-8") == original

    def test_collision_fails_atomically(self, tmp_path, monkeypatch, capsys):
        """Existing raw/a.csv + loose a.csv → exit 1, names both, no move."""
        (tmp_path / "raw").mkdir()
        (tmp_path / "raw" / "a.csv").write_text("existing", encoding="utf-8")
        (tmp_path / "a.csv").write_text("loose", encoding="utf-8")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_scan(Namespace(config=str(cfg), dry_run=False, force=True, ext=None))
        assert rc == 1
        err = capsys.readouterr().err
        assert "a.csv" in err
        assert (tmp_path / "a.csv").exists()

    def test_prompt_n_aborts_atomically(self, tmp_path, monkeypatch):
        """Prompt N aborts before move, no FS change."""
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        (tmp_path / "b.csv").write_text("y\n2\n", encoding="utf-8")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("builtins.input", lambda _p="": "n")
        rc = cli._cmd_scan(Namespace(config=str(cfg), dry_run=False, force=False, ext=None))
        assert rc == 0
        assert (tmp_path / "a.csv").exists()
        assert (tmp_path / "b.csv").exists()
        assert not (tmp_path / "raw" / "a.csv").exists()

    def test_five_exts_vs_txt(self, tmp_path, monkeypatch):
        """Only 5 exts moved, f.txt stays."""
        for name in ["a.csv", "b.tsv", "c.xlsx", "d.jsonl", "e.parquet", "f.txt"]:
            (tmp_path / name).write_text("x", encoding="utf-8")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_scan(Namespace(config=str(cfg), dry_run=False, force=True, ext=None))
        assert rc == 0
        for name in ["a.csv", "b.tsv", "c.xlsx", "d.jsonl", "e.parquet"]:
            assert (tmp_path / "raw" / name).exists()
            assert not (tmp_path / name).exists()
        assert (tmp_path / "f.txt").exists()
        assert not (tmp_path / "raw" / "f.txt").exists()


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


# ── PUB-11 / PRP-09 — CLI publish --clean / --clean-cache / --all ───────────────


class TestPublishCleanParser:
    """publish --help contains --clean/--clean-cache/--all and plumbs correctly."""

    def test_help_contains_clean_flags(self, capsys):
        """publish --help lists --clean, --clean-cache and --all."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["publish", "--help"])
        out = capsys.readouterr().out
        assert "--clean" in out
        assert "--clean-cache" in out
        assert "--all" in out
        assert "cache" in out.lower()

    def test_clean_defaults_off(self):
        """--clean and --clean-cache default to False."""
        args = cli._build_parser().parse_args(["publish", "config.toml"])
        assert args.clean is False
        assert args.clean_cache is False

    def test_clean_flag_sets_clean(self):
        """--clean sets clean=True."""
        args = cli._build_parser().parse_args(["publish", "config.toml", "--clean"])
        assert args.clean is True
        assert args.clean_cache is False

    def test_clean_cache_sets_cache(self):
        """--clean-cache sets clean_cache=True."""
        args = cli._build_parser().parse_args(
            ["publish", "config.toml", "--clean", "--clean-cache"]
        )
        assert args.clean is True
        assert args.clean_cache is True

    def test_all_alias_sets_cache(self):
        """--all is an alias for --clean-cache."""
        args = cli._build_parser().parse_args(["publish", "config.toml", "--clean", "--all"])
        assert args.clean_cache is True

    def test_publish_plumbs_flags(self, tmp_path, monkeypatch):
        """_cmd_publish plumbs --clean/--clean-cache into publish()."""
        toml_path = tmp_path / "test.toml"
        toml_content = (
            '[dataset]\nname = "test"\nrepo_id = "u/test"\n\n'
            '[[file]]\nlocal = "a.csv"\nremote = "a.csv"\n'
        )
        toml_path.write_text(toml_content, encoding="utf-8")
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        from sofer import publish as publish_mod

        captured: dict[str, object] = {}

        def fake_publish(cfg, **kw):  # type: ignore[no-untyped-def]
            captured.update(kw)
            return 0

        monkeypatch.setattr(publish_mod, "publish", fake_publish)
        # Also patch the cli's run_publish reference
        import sofer.cli as cli_mod

        orig = cli_mod.run_publish
        monkeypatch.setattr(cli_mod, "run_publish", fake_publish)

        args = cli._build_parser().parse_args(["publish", str(toml_path), "--clean", "--all"])
        rc = cli._cmd_publish(args)
        assert rc == 0
        assert captured.get("clean") is True
        assert captured.get("clean_cache") is True
        monkeypatch.setattr(cli_mod, "run_publish", orig)


# ---------------------------------------------------------------------------
#  CLI-R03 / CLI-R04 — profile / render flags, batch dispatch, help (feat)
# ---------------------------------------------------------------------------


class TestProfileRenderCliFlags:
    """CLI-R03/R04 profile/render parser and dispatch."""

    def test_profile_flags_present(self):
        """profile parser exposes --output/--all-files/--force/--config."""
        args = cli._build_parser().parse_args(["profile", "data.csv"])
        assert hasattr(args, "output")
        assert hasattr(args, "all_files")
        assert hasattr(args, "force")
        assert hasattr(args, "config")
        assert args.all_files is False
        assert args.force is False

    def test_render_flags_present(self):
        """render parser exposes same four flags."""
        args = cli._build_parser().parse_args(["render", "pkg"])
        assert hasattr(args, "output")
        assert hasattr(args, "all_files")
        assert hasattr(args, "force")
        assert hasattr(args, "config")

    def test_profile_all_files_flag_parses(self):
        """--all-files is actionable on profile."""
        args = cli._build_parser().parse_args(["profile", "dataset.toml", "--all-files"])
        assert args.all_files is True
        assert args.dataset == "dataset.toml"

    def test_render_all_files_flag_parses(self):
        """--all-files is actionable on render."""
        args = cli._build_parser().parse_args(["render", "dataset.toml", "--all-files"])
        assert args.all_files is True

    def test_help_lists_all_flags_profile(self, capsys):
        """profile --help lists all four flags and TOML contract."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["profile", "--help"])
        out = capsys.readouterr().out
        assert "--output" in out
        assert "--all-files" in out
        assert "--force" in out
        assert "--config" in out
        assert "[[file]]" in out

    def test_help_lists_all_flags_render(self, capsys):
        """render --help lists all four flags."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["render", "--help"])
        out = capsys.readouterr().out
        assert "--output" in out
        assert "--all-files" in out
        assert "--force" in out
        assert "--config" in out
        assert "[[file]]" in out

    def test_profile_batch_dispatch(self, tmp_path, restore_tool_config):
        """sofer profile dataset.toml --all-files dispatches batch and writes profiles."""
        (tmp_path / "cache").mkdir()
        (tmp_path / "cache" / "a.csv").write_text("col;val\n1;2\n", encoding="utf-8")
        toml = tmp_path / "dataset.toml"
        toml.write_text(
            '[dataset]\nname = "test"\nrepo_id = "u/test"\n\n'
            '[[file]]\nlocal = "cache/a.csv"\nremote = "a.csv"\n',
            encoding="utf-8",
        )
        rc = cli._cmd_profile(cli._build_parser().parse_args(["profile", str(toml), "--all-files"]))
        assert rc == 0
        assert (tmp_path / "cache" / "profiles" / "a.metadata.yaml").is_file()

    def test_render_batch_dispatch(self, tmp_path, restore_tool_config):
        """sofer render dataset.toml --all-files dispatches batch."""
        import sofer.config as cfg

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        (tmp_path / "cache" / "a.csv").write_text("col;val\n1;2\n", encoding="utf-8")
        toml = tmp_path / "dataset.toml"
        toml.write_text(
            '[dataset]\nname = "test"\nrepo_id = "u/test"\n\n'
            '[[file]]\nlocal = "cache/a.csv"\nremote = "a.csv"\n',
            encoding="utf-8",
        )
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        ds_cfg = DatasetConfig.from_toml(toml)
        generate_all_profiles(ds_cfg)
        rc = cli._cmd_render(cli._build_parser().parse_args(["render", str(toml), "--all-files"]))
        assert rc == 0
        assert (tmp_path / "cache" / "renders" / "a.README.md").is_file()

    def test_toml_without_files_nonzero(self, tmp_path, capsys):
        """TOML without [[file]] + --all-files exits non-zero mentioning [[file]]."""
        toml = tmp_path / "dataset.toml"
        toml.write_text('[dataset]\nname = "x"\nrepo_id = "u/x"\n', encoding="utf-8")
        rc = cli._cmd_profile(
            Namespace(dataset=str(toml), output=None, all_files=True, force=False, config=str(toml))
        )
        assert rc == 1
        assert "[[file]]" in capsys.readouterr().err
        rc2 = cli._cmd_render(
            Namespace(package=str(toml), output=None, all_files=True, force=False, config=str(toml))
        )
        assert rc2 == 1

    def test_profile_and_render_appear_in_help(self, capsys):
        """sofer --help lists both profile and render subcommands."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["--help"])
        out = capsys.readouterr().out
        assert "profile" in out
        assert "render" in out

    def test_config_flag_overrides_positional(self, tmp_path, restore_tool_config):
        """--config overrides positional TOML path for batch."""
        (tmp_path / "cache").mkdir()
        (tmp_path / "cache" / "a.csv").write_text("col;val\n1;2\n", encoding="utf-8")
        toml_a = tmp_path / "a.toml"
        toml_a.write_text(
            '[dataset]\nname = "test"\nrepo_id = "u/test"\n\n'
            '[[file]]\nlocal = "cache/a.csv"\nremote = "a.csv"\n',
            encoding="utf-8",
        )
        toml_b = tmp_path / "b.toml"
        toml_b.write_text('[dataset]\nname = "x"\nrepo_id = "u/x"\n', encoding="utf-8")
        # positional is b.toml (no files) but --config points to a.toml -> should succeed
        args = cli._build_parser().parse_args(
            ["profile", str(toml_b), "--all-files", "--config", str(toml_a)]
        )
        rc = cli._cmd_profile(args)
        assert rc == 0

    def test_profile_help_describes_metadata(self, capsys):
        """profile help mentions metadata.yaml and use --force hint."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["profile", "--help"])
        out = capsys.readouterr().out
        assert "metadata.yaml" in out
        assert "use --force to overwrite" in out

    def test_render_help_describes_readme(self, capsys):
        """render help mentions README.md and use --force hint."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["render", "--help"])
        out = capsys.readouterr().out
        assert "README.md" in out
        assert "use --force to overwrite" in out


# ── mcp registration — CLI help (CLI-R09) ─────────────────────────────────


class TestMcpCliHelp:
    """sofer mcp add/remove help per CLI-R09."""

    def test_sofer_help_has_mcp(self, capsys):
        """sofer --help lists mcp subcommand."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["--help"])
        out = capsys.readouterr().out
        assert "mcp" in out

    def test_mcp_help_has_add_remove(self, capsys):
        """sofer mcp --help lists add and remove."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["mcp", "--help"])
        out = capsys.readouterr().out
        assert "add" in out
        assert "remove" in out

    def test_mcp_add_help_flags(self, capsys):
        """sofer mcp add --help lists --agent, --scope, --cwd, --dry-run."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["mcp", "add", "--help"])
        out = capsys.readouterr().out
        assert "--agent" in out
        assert "--scope" in out
        assert "--cwd" in out
        assert "--dry-run" in out

    def test_mcp_remove_help_flags(self, capsys):
        """sofer mcp remove --help lists --agent, --scope, --dry-run."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["mcp", "remove", "--help"])
        out = capsys.readouterr().out
        assert "--agent" in out
        assert "--scope" in out
        assert "--dry-run" in out

    def test_mcp_add_no_cwd_on_remove(self, capsys):
        """sofer mcp remove --help must NOT list --cwd (only add)."""
        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["mcp", "remove", "--help"])
        out = capsys.readouterr().out
        assert "--cwd" not in out
