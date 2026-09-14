"""Tests for sofer.cli — argument parsing and command dispatch.

The upload and validate commands depend on Hugging Face credentials and real
filesystem state, so they are integration-level.  Here we test everything
that can be verified without network calls or real data, including
user-visible output through an executable CLI subprocess (PB-02) via the
shared ``conftest.run_cli`` helper (PB-09).
"""

import csv
import io
import sys
from argparse import Namespace

import pytest as _pytest
from conftest import run_cli

from sofer import cli, config, mcp_registration

# ── Argument parsing ──────────────────────────────────────────────────────────


class TestParser:
    def test_init_command(self):
        """`sofer init my-dataset --user alice` should parse to the init command."""
        args = cli._build_parser().parse_args(["init", "my-dataset", "--user", "alice"])
        assert args.command == "init"
        assert args.name == "my-dataset"
        assert callable(args.func)

    def test_init_requires_user(self, capsys):
        """`sofer init my-dataset` without --user exits 2 naming --user (CLI-R07)."""
        import pytest

        with pytest.raises(SystemExit) as excinfo:
            cli._build_parser().parse_args(["init", "my-dataset"])
        assert excinfo.value.code == 2
        assert "--user" in capsys.readouterr().err

    def test_init_user_flag(self):
        """`sofer init my-dataset --user alice` should parse user."""
        args = cli._build_parser().parse_args(["init", "my-dataset", "--user", "alice"])
        assert args.name == "my-dataset"
        assert args.user == "alice"

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
        """`sofer init <name> --user alice` should write a .toml file."""
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_init(Namespace(name="my-dataset", user="alice"))
        assert rc == 0
        assert (tmp_path / "my-dataset.toml").exists()

    def test_init_refuses_overwrite(self, tmp_path, monkeypatch):
        """`sofer init <name>` on an existing file should fail."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "existing.toml").write_text("hello", encoding="utf-8")
        rc = cli._cmd_init(Namespace(name="existing", user="alice"))
        assert rc == 1  # refuses to overwrite

    def test_init_content_is_valid_toml(self, tmp_path, monkeypatch):
        """The generated template should parse as valid TOML."""
        try:
            import tomli as _tomli
        except ImportError:
            import tomllib as _tomli

        monkeypatch.chdir(tmp_path)
        cli._cmd_init(Namespace(name="test-ds", user="alice"))
        content = (tmp_path / "test-ds.toml").read_text(encoding="utf-8")
        parsed = _tomli.loads(content)
        assert parsed["dataset"]["name"] == "test-ds"
        assert parsed["dataset"]["repo_id"] == "alice/test-ds"

    def test_init_content_has_placeholders(self, tmp_path, monkeypatch):
        """The template should contain TODO markers to guide the user."""
        monkeypatch.chdir(tmp_path)
        cli._cmd_init(Namespace(name="ds", user="alice"))
        content = (tmp_path / "ds.toml").read_text(encoding="utf-8")
        assert "TODO" in content

    def test_init_template_windows_safe_placeholder(self, tmp_path, monkeypatch):
        """The template [[file]] local MUST be Windows-safe raw/example.csv (INIT-01, CLI-R07)."""
        import ntpath

        try:
            import tomli as _tomli
        except ImportError:
            import tomllib as _tomli

        monkeypatch.chdir(tmp_path)
        cli._cmd_init(Namespace(name="ds-win", user="alice"))
        content = (tmp_path / "ds-win.toml").read_text(encoding="utf-8")
        parsed = _tomli.loads(content)
        locals_list = [e.get("local", "") for e in parsed.get("file", [])]
        assert "raw/example.csv" in locals_list
        for local in locals_list:
            assert ":" not in local, f"colon in local {local!r}"
            drive, _tail = ntpath.splitdrive(local)
            assert drive == "", f"ntpath drive not empty for {local!r}"
        assert "TODO: raw/file.csv" not in content
        assert "TODO: raw/directory/" not in content

    def test_init_template_has_build_dir(self, tmp_path, monkeypatch):
        """The template declares ``[dataset] build_dir = "build"`` so the
        default prepare/publish output directory is explicit."""
        try:
            import tomli as _tomli
        except ImportError:
            import tomllib as _tomli

        monkeypatch.chdir(tmp_path)
        cli._cmd_init(Namespace(name="build-ds", user="alice"))
        content = (tmp_path / "build-ds.toml").read_text(encoding="utf-8")
        parsed = _tomli.loads(content)
        assert parsed["dataset"]["build_dir"] == "build"

    def test_init_user_sets_repo_id(self, tmp_path, monkeypatch):
        """`sofer init myds --user alice` creates repo_id alice/myds."""
        try:
            import tomli as _tomli
        except ImportError:
            import tomllib as _tomli

        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_init(Namespace(name="myds", user="alice"))
        assert rc == 0
        content = (tmp_path / "myds.toml").read_text(encoding="utf-8")
        parsed = _tomli.loads(content)
        assert parsed["dataset"]["repo_id"] == "alice/myds"

    def test_init_missing_user_rejected_handler(self, tmp_path, monkeypatch, capsys):
        """A direct _cmd_init call without user exits 1, no TOML written (defense-in-depth)."""
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_init(Namespace(name="myds2"))
        assert rc == 1
        assert not (tmp_path / "myds2.toml").exists()
        assert not (tmp_path / "raw").exists()
        err = capsys.readouterr().err
        assert "user must be non-empty" in err

    def test_init_missing_user_rejected_subprocess(self, tmp_path):
        """`sofer init myds` without --user exits 2 naming --user (CLI-R07), no TOML."""
        result = run_cli(["init", "myds2"], cwd=tmp_path)
        assert result.returncode == 2
        assert "--user" in result.stderr
        assert not (tmp_path / "myds2.toml").exists()
        assert not (tmp_path / "raw").exists()


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
        cli._cmd_init(Namespace(name="ds", user="alice"))
        content = (tmp_path / "ds.toml").read_text(encoding="utf-8")
        assert "sofer upload" not in content
        assert "sofer prepare" in content
        assert "sofer publish" in content

    def test_init_prints_prepare_publish(self, tmp_path, monkeypatch, capsys):
        """_cmd_init success prints prepare + publish hints, never upload."""
        monkeypatch.chdir(tmp_path)
        cli._cmd_init(Namespace(name="ds", user="alice"))
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

    def test_invalid_csv_delimiter_type_validate_returns_1(self, tmp_path, capsys):
        """A dataset TOML with [meta] csv_delimiter = 5 fails validation with a
        stable diagnostic and rc 1 (TC-13, #118)."""
        toml_path = tmp_path / "invalid.toml"
        toml_path.write_text(
            '[dataset]\nname = "x"\nrepo_id = "user/x"\n\n'
            '[[file]]\nlocal = "missing.csv"\nremote = "missing.csv"\n\n'
            "[meta]\ncsv_delimiter = 5\n",
            encoding="utf-8",
        )
        rc = cli._cmd_validate(Namespace(config=str(toml_path)))
        assert rc == 1
        assert "csv_delimiter" in capsys.readouterr().out

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

        rc = cli._cmd_codebook(
            Namespace(all_files=True, config=str(toml_path), csv=None, max_sample=None)
        )
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
            Namespace(all_files=True, config=str(toml_path), csv=None, output=None, max_sample=None)
        )
        assert rc == 0
        # CLI parity with MCP sofer_codebook_all: codebooks land in the package
        # build_dir (where publish collects them), never the shared cache/.
        root = tmp_path / "build" / "codebook.md"
        assert root.exists()
        assert not (tmp_path / "cache" / "codebook.md").exists()
        assert not (tmp_path / "codebook.md").exists()

    def test_all_files_output_override_writes_to_output_dir(self, tmp_path, monkeypatch):
        """`codebook --all-files --output out` honours the override, writing
        under out/ instead of the default build_dir."""
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
            Namespace(
                all_files=True, config=str(toml_path), csv=None, output="out", max_sample=None
            )
        )
        assert rc == 0
        assert (tmp_path / "out" / "codebook.md").exists()
        assert (tmp_path / "out" / "codebooks" / "data" / "f.md").exists()
        assert not (tmp_path / "build" / "codebook.md").exists()


# ── raw-folder organization: init + --move-existing (CLI-R07 / CLI-R08) ────────


class TestInitRawFolder:
    """CLI-R07: init creates raw/ and --move-existing depth-1 SUPPORTED_FORMATS."""

    def test_init_creates_raw_dir(self, tmp_path, monkeypatch):
        """sofer init creates raw/ and TOML contains raw/ guidance (SCN-07 template)."""
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_init(
            Namespace(name="my-ds", user="alice", move_existing=False, dry_run=False, force=False)
        )
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
        rc = cli._cmd_init(
            Namespace(name="my-ds", user="alice", move_existing=False, dry_run=False, force=False)
        )
        assert rc == 0
        rc2 = cli._cmd_init(
            Namespace(name="other", user="alice", move_existing=False, dry_run=False, force=False)
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
        rc = cli._cmd_init(
            Namespace(name="my-ds", user="alice", move_existing=True, dry_run=False, force=True)
        )
        assert rc == 0
        assert (tmp_path / "raw" / "a.csv").exists()
        assert not (tmp_path / "a.csv").exists()
        assert (tmp_path / "subdir" / "b.csv").exists()
        assert (tmp_path / "notes.txt").exists()
        assert (tmp_path / "cache" / "c.csv").exists()

    def test_move_existing_skips_symlink(self, tmp_path, tmp_path_factory, monkeypatch):
        """A symlinked CSV at the dataset root is never moved into raw/
        (SCN-01 exfiltration guard, CF-3)."""
        import pytest

        monkeypatch.chdir(tmp_path)
        outside = tmp_path_factory.mktemp("outside")
        secret = outside / "secret.csv"
        secret.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        link = tmp_path / "leak.csv"
        try:
            link.symlink_to(secret)
        except OSError:
            pytest.skip("symlink creation unavailable on this host")
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")

        rc = cli._cmd_init(
            Namespace(name="my-ds", user="alice", move_existing=True, dry_run=False, force=True)
        )
        assert rc == 0
        assert (tmp_path / "raw" / "a.csv").exists()
        assert not (tmp_path / "raw" / "leak.csv").exists(), "symlink must not be moved"
        assert link.exists(), "the link itself must remain in place"

    def test_move_existing_collision_guard(self, tmp_path, monkeypatch, capsys):
        """Collision with existing raw/ content fails naming both sources."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "raw").mkdir()
        (tmp_path / "raw" / "a.csv").write_text("existing\n", encoding="utf-8")
        (tmp_path / "a.csv").write_text("loose\n", encoding="utf-8")
        rc = cli._cmd_init(
            Namespace(name="my-ds", user="alice", move_existing=True, dry_run=False, force=True)
        )
        assert rc == 1
        err = capsys.readouterr().err.lower()
        assert "collision" in err
        assert "a.csv" in err
        # no move happened
        assert (tmp_path / "a.csv").exists()
        assert (tmp_path / "raw" / "a.csv").exists()

    def test_move_existing_dry_run_no_mutation(self, tmp_path, monkeypatch, capsys):
        """--dry-run previews moves, writes NO TOML, no raw/ when absent, no moves."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        (tmp_path / "b.xlsx").write_text("x", encoding="utf-8")
        rc = cli._cmd_init(
            Namespace(name="my-ds", user="alice", move_existing=True, dry_run=True, force=False)
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "dry run" in out.lower()
        assert "a.csv" in out
        assert "Would create my-ds.toml" in out
        assert not (tmp_path / "my-ds.toml").exists()
        # raw/ not created when absent under dry-run
        assert not (tmp_path / "raw").exists()
        assert (tmp_path / "a.csv").exists()
        assert (tmp_path / "b.xlsx").exists()

    def test_init_plain_dry_run_no_mutation(self, tmp_path, monkeypatch, capsys):
        """`init --dry-run` (no --move-existing) previews, writes no TOML/raw/ (CLI-R07)."""
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_init(
            Namespace(name="my-ds", user="alice", move_existing=False, dry_run=True, force=False)
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "DRY RUN" in out
        assert "Would create my-ds.toml" in out
        assert "Would scaffold raw" in out
        assert not (tmp_path / "my-ds.toml").exists()
        assert not (tmp_path / "raw").exists()

    def test_move_existing_non_interactive_guard(self, tmp_path, monkeypatch, capsys):
        """not isatty without --force skips move, creates raw/, hints --force."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        rc = cli._cmd_init(
            Namespace(name="my-ds", user="alice", move_existing=True, dry_run=False, force=False)
        )
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
        rc = cli._cmd_init(
            Namespace(name="my-ds", user="alice", move_existing=True, dry_run=False, force=False)
        )
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
        rc = cli._cmd_init(
            Namespace(name="my-ds", user="alice", move_existing=True, dry_run=False, force=False)
        )
        assert rc == 0
        assert (tmp_path / "raw" / "a.csv").exists()
        assert not (tmp_path / "a.csv").exists()

    def test_template_mentions_raw_no_stale_path(self, tmp_path, monkeypatch):
        """Generated TOML mentions raw/ guidance and no stale path/to hint."""
        monkeypatch.chdir(tmp_path)
        cli._cmd_init(
            Namespace(name="my-ds", user="alice", move_existing=False, dry_run=False, force=False)
        )
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


class TestScanTruthfulReport:
    """SCN-08: ``Registered N`` is only printed AFTER copy + TOML write succeed."""

    def test_write_toml_failure_does_not_report_registered(self, tmp_path, monkeypatch, capsys):
        """A TOML write failure exits 1 and never prints a ``Registered``
        success line — the cache copy happened but registration did not."""
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        def _boom(_raw_toml, _config_path):
            raise OSError("disk full")

        monkeypatch.setattr(cli, "write_toml", _boom)
        rc = cli._cmd_scan(Namespace(config=str(cfg), dry_run=False, force=True, ext=None))
        assert rc == 1
        captured = capsys.readouterr()
        assert "Registered" not in captured.out
        assert "Failed to write TOML" in captured.err

    def test_success_reports_registered_after_write(self, tmp_path, monkeypatch, capsys):
        """A successful scan prints the registration line after the copy and
        TOML write complete."""
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_scan(Namespace(config=str(cfg), dry_run=False, force=True, ext=None))
        assert rc == 0
        out = capsys.readouterr().out
        assert "Registered 1 new [[file]] entry(s)." in out


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

    def test_mcp_add_help_env_forwarding(self, capsys):
        """sofer mcp add --help documents env forwarding and the opencode warning."""
        import re

        import pytest

        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["mcp", "add", "--help"])
        out = capsys.readouterr().out
        # argparse reflows the description at the terminal width; normalize
        # whitespace so the pinned substrings survive the wrap. The pinned
        # help sentence renders "(names only, values never written)", so the
        # stable substring is the prefix ending at "(names only".
        flat = re.sub(r"\s+", " ", out)
        assert "codex and gemini receive env forwarding (names only" in flat
        assert "opencode entries carry no environment" in flat


# ── subprocess boundary: user-visible output via executable CLI (PB-02) ───────


class TestSubprocessBoundary:
    """CLI output through a real ``python -m sofer.cli`` subprocess (PB-02).

    Uses the shared ``conftest.run_cli`` helper (PB-09) — subprocess spawning
    is never re-implemented here — so help text, console encoding, and
    dispatch behavior are observed through the same boundary real users hit,
    not through in-process parser calls.
    """

    #: Every subcommand the CLI exposes (the ``--help`` roster, PB-02).
    SUBCOMMANDS = (
        "init",
        "scan",
        "validate",
        "prepare",
        "publish",
        "codebook",
        "profile",
        "render",
        "mcp",
    )

    def test_help_exits_zero_and_lists_every_subcommand(self, tmp_path) -> None:
        """``python -m sofer.cli --help`` exits 0 and lists all subcommands."""
        result = run_cli(["--help"], cwd=tmp_path)
        assert result.returncode == 0
        for command in self.SUBCOMMANDS:
            assert command in result.stdout, f"{command!r} missing from --help"

    @_pytest.mark.parametrize(
        "argv",
        [
            ["--help"],
            *([command, "--help"] for command in SUBCOMMANDS),
            ["mcp", "add", "--help"],
            ["mcp", "remove", "--help"],
        ],
    )
    def test_help_strict_cp1252(self, argv: list[str], tmp_path) -> None:
        """Every help screen under cp1252 exits 0 with no UnicodeEncodeError.

        ``PYTHONIOENCODING=cp1252`` forces the child to encode its stdout as
        cp1252; ``run_cli`` decodes it with ``errors="strict"``, so any byte
        the child could not encode (a non-cp1252 glyph would crash the child
        with ``UnicodeEncodeError`` and a non-zero exit) fails loudly here.
        Re-encoding the decoded text pins the "no non-cp1252 glyphs" contract
        explicitly.

        The parametrization covers every invocation PB-02 names — ``--help``
        alone, ``<cmd> --help`` for all nine top-level subcommands, and the two
        nested ``mcp`` help screens — because the single ``--help`` case that
        this test used to run renders no subparser ``description=`` and
        therefore passed while ``prepare --help`` / ``scan --help`` crashed
        (#161). Assertions stay ASCII-substring shaped: the boundary never
        pins how the CLI keeps its text encodable.
        """
        result = run_cli(
            argv,
            cwd=tmp_path,
            env={"PYTHONIOENCODING": "cp1252"},
            encoding="cp1252",
        )
        assert result.returncode == 0, result.stderr
        assert "UnicodeEncodeError" not in result.stderr
        # Every glyph must be representable in cp1252 — a glyph outside the
        # codec (e.g. an em dash or arrow) raises UnicodeEncodeError here.
        result.stdout.encode("cp1252")

    def test_runtime_output_strict_cp1252(self, tmp_path) -> None:
        """A cp1252 runtime console path keeps its result (CLI-R11, PB-02).

        ``validate`` against a TOML carrying configuration errors prints the
        ``\u2717`` marker before the ASCII ``Configuration errors`` text. On a
        cp1252 stream that marker used to raise ``UnicodeEncodeError`` and abort
        ``validate`` with a traceback instead of the report.

        ``rc == 1`` is deliberately *not* the discriminator: a traceback also
        exits 1. The stable ASCII substring is.
        """
        toml_path = tmp_path / "dataset.toml"
        toml_path.write_text(
            '[dataset]\nname = "test-ds"\nrepo_id = "YOUR_USER/test-ds"\n\n'
            '[[file]]\nlocal = "missing.csv"\nremote = "missing.csv"\n',
            encoding="utf-8",
        )
        result = run_cli(
            ["validate", str(toml_path)],
            cwd=tmp_path,
            env={"PYTHONIOENCODING": "cp1252"},
            encoding="cp1252",
        )
        assert result.returncode == 1
        assert "Configuration errors" in result.stdout
        assert "UnicodeEncodeError" not in result.stderr
        result.stdout.encode("cp1252")

    def test_scan_dry_run_strict_cp1252(self, tmp_path) -> None:
        """A cp1252 ``scan --dry-run`` copy preview keeps rc 0 (CLI-R11).

        The dry-run copy preview prints a ``U+2192`` arrow per would-be copy;
        on a cp1252 stream that write used to abort the command with a
        traceback. ``rc == 0`` is the discriminator: the ASCII ``DRY RUN`` line
        is printed *before* the arrow, so the substring alone would already
        pass today.
        """
        (tmp_path / "raw").mkdir()
        (tmp_path / "raw" / "a.csv").write_text("a;b\n1;2\n", encoding="utf-8")
        toml_path = tmp_path / "dataset.toml"
        toml_path.write_text(
            '[dataset]\nname = "test-ds"\nrepo_id = "user/test-ds"\n',
            encoding="utf-8",
        )
        result = run_cli(
            ["scan", "dataset.toml", "--dry-run"],
            cwd=tmp_path,
            env={"PYTHONIOENCODING": "cp1252"},
            encoding="cp1252",
        )
        assert result.returncode == 0, result.stderr
        assert "DRY RUN" in result.stdout
        assert "UnicodeEncodeError" not in result.stderr
        result.stdout.encode("cp1252")

    def test_interpolated_stdout_value_strict_cp1252(self, tmp_path) -> None:
        """ASCII literal + unencodable interpolated TOML value, on stdout.

        ``scan --dry-run`` previews the MOVE phase with the ASCII literal
        ``DRY RUN`` / ``-> raw/`` followed by the declared local path. When
        that path's name carries ``U+2192``, only the *interpolated* value
        falls outside cp1252 — the surrounding literal is pure ASCII and the
        arrow is the ASCII ``->``, not the authored ``U+2192`` glyph. On the
        pre-fix tree the strict cp1252 stdout raised ``UnicodeEncodeError``
        inside that f-string write and aborted with ``rc 1``; the guard must
        degrade the value and keep the documented result instead.

        ``rc == 0`` is the discriminator (the pre-fix traceback exits 1): the
        ``DRY RUN`` header is printed *before* the offending write, so the
        substring alone would pass pre-fix. No glyph and no substitution
        rendering is asserted — the spec leaves ``?`` vs an escape open
        (CLI-R11 scenario 2, stdout clause).
        """
        (tmp_path / "data\u2192.csv").write_text("col_a;col_b\n1;2\n", encoding="utf-8")
        toml_path = tmp_path / "dataset.toml"
        toml_path.write_text(
            '[dataset]\nname = "test-ds"\nrepo_id = "user/test-ds"\n\n'
            '[[file]]\nlocal = "data\u2192.csv"\nremote = "data.csv"\n',
            encoding="utf-8",
        )
        result = run_cli(
            ["scan", "dataset.toml", "--dry-run"],
            cwd=tmp_path,
            env={"PYTHONIOENCODING": "cp1252"},
            encoding="cp1252",
        )
        assert result.returncode == 0, result.stderr
        assert "DRY RUN" in result.stdout
        assert "raw/" in result.stdout
        assert "UnicodeEncodeError" not in result.stderr
        result.stdout.encode("cp1252")

    def test_interpolated_unencodable_value_strict_cp1252(self, tmp_path) -> None:
        """An ASCII literal with an unencodable interpolated value survives.

        ``scan <path>`` with a nonexistent path whose name carries ``U+2192``
        prints the ASCII literal ``Config file not found`` with the resolved
        path interpolated. The traceback this used to raise *also* echoes the
        ASCII literal, so only ``UnicodeEncodeError not in stderr``
        discriminates (CLI-R11).
        """
        missing = tmp_path / "missing\u2192dataset.toml"
        result = run_cli(
            ["scan", str(missing)],
            cwd=tmp_path,
            env={"PYTHONIOENCODING": "cp1252"},
            encoding="cp1252",
        )
        assert result.returncode == 1
        assert "Config file not found" in result.stderr
        assert "UnicodeEncodeError" not in result.stderr
        result.stderr.encode("cp1252")

    def test_codebook_warning_strict_cp1252(self, tmp_path) -> None:
        """A cp1252 console warning carrying a glyph degrades, not aborts.

        ``codebook --all-files`` warns on stderr about a registered entry whose
        format it cannot analyse; the ``\u26a0`` marker used to raise
        ``UnicodeEncodeError`` and abort the run (rc 1). ``rc == 0`` is the
        discriminator here (CLI-R11).
        """
        (tmp_path / "data.csv").write_text("a;b\n1;2\n", encoding="utf-8")
        (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
        toml_path = tmp_path / "dataset.toml"
        toml_path.write_text(
            '[dataset]\nname = "test-ds"\nrepo_id = "user/test-ds"\n\n'
            '[[file]]\nlocal = "data.csv"\nremote = "data.csv"\n\n'
            '[[file]]\nlocal = "notes.txt"\nremote = "notes.txt"\n',
            encoding="utf-8",
        )
        result = run_cli(
            ["codebook", "--all-files", "--config", "dataset.toml"],
            cwd=tmp_path,
            env={"PYTHONIOENCODING": "cp1252"},
            encoding="cp1252",
        )
        assert result.returncode == 0, result.stderr
        assert "Unsupported format" in result.stderr
        assert "UnicodeEncodeError" not in result.stderr
        result.stderr.encode("cp1252")

    def test_unknown_command_exits_2(self, tmp_path) -> None:
        """``python -m sofer.cli <unknown-command>`` exits 2 via argparse."""
        result = run_cli(["definitely-not-a-command"], cwd=tmp_path)
        assert result.returncode == 2
        assert "invalid choice" in result.stderr

    def test_init_prints_absolute_config_path(self, tmp_path) -> None:
        """Success prints the canonical absolute config_path (CLI-R07)."""
        result = run_cli(["init", "myds", "--user", "alice"], cwd=tmp_path)
        assert result.returncode == 0
        assert str(tmp_path.resolve() / "myds.toml") in result.stdout
        assert (tmp_path / "myds.toml").exists()

    def test_init_dry_run_no_mutation(self, tmp_path) -> None:
        """`init --dry-run` exits 0, previews, and writes nothing (CLI-R07).

        Parity with MCP ``sofer_init(dry_run=True)`` (no-mutation in both
        branches): the plain init branch must not write the TOML nor create
        raw/ under ``--dry-run``.
        """
        result = run_cli(["init", "myds", "--user", "alice", "--dry-run"], cwd=tmp_path)
        assert result.returncode == 0
        assert "DRY RUN" in result.stdout
        assert "Would create myds.toml" in result.stdout
        assert "Would scaffold raw" in result.stdout
        assert not (tmp_path / "myds.toml").exists()
        assert not (tmp_path / "raw").exists()

    def test_init_placeholder_user_rejected(self, tmp_path) -> None:
        """`--user YOUR_USER` exits 1 naming the placeholder, no file written."""
        result = run_cli(["init", "myds", "--user", "YOUR_USER"], cwd=tmp_path)
        assert result.returncode == 1
        assert "placeholder" in result.stderr
        assert not (tmp_path / "myds.toml").exists()
        assert not (tmp_path / "raw").exists()

    def test_init_unsafe_name_rejected(self, tmp_path) -> None:
        """Unsafe name `a/../b` exits 1 naming the component, no file written."""
        result = run_cli(["init", "a/../b", "--user", "alice"], cwd=tmp_path)
        assert result.returncode == 1
        assert "a/../b" in result.stderr
        assert not (tmp_path / "b.toml").exists()
        assert not (tmp_path / "raw").exists()

    def test_init_windows_invalid_name_rejected(self, tmp_path) -> None:
        """Windows-invalid char name `a*b` exits 1 pre-write, no TOML/raw."""
        result = run_cli(["init", "a*b", "--user", "alice"], cwd=tmp_path)
        assert result.returncode == 1
        assert "Windows-invalid" in result.stderr
        assert not (tmp_path / "a*b.toml").exists()
        assert not (tmp_path / "raw").exists()

    def test_init_reserved_device_name_rejected(self, tmp_path) -> None:
        """Reserved device name `CON` exits 1 pre-write — no TOML, no raw/
        (no partial state; on Windows CON.toml would be unmaterializable)."""
        result = run_cli(["init", "CON", "--user", "alice"], cwd=tmp_path)
        assert result.returncode == 1
        assert "reserved" in result.stderr.lower()
        assert not (tmp_path / "CON.toml").exists()
        assert not (tmp_path / "raw").exists()

    def test_codebook_relative_output_anchors_to_input_parent(self, tmp_path) -> None:
        """A relative single-file ``-o`` anchors to the INPUT's parent, not cwd.

        MSP-R10 parity with the MCP side (D9): the codebook must land next to
        the analysed file. The input lives in ``data/`` while the subprocess
        cwd is the parent, so an un-anchored output would land at
        ``<cwd>/out.md`` — this pins the anchored ``<data>/out.md`` instead.
        """
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "sample.csv").write_text("col;val\n1;2\n", encoding="utf-8")
        result = run_cli(["codebook", "data/sample.csv", "-o", "out.md"], cwd=tmp_path)
        assert result.returncode == 0, result.stderr
        assert (tmp_path / "data" / "out.md").is_file(), "output must land next to the input"
        assert not (tmp_path / "out.md").exists(), "output must not land in cwd"

    def test_profile_relative_output_anchors_to_input_parent(self, tmp_path) -> None:
        """A relative single-file profile ``--output`` anchors to the INPUT's
        parent (metadata.yaml lands in ``data/out/``, never ``<cwd>/out/``)."""
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "sample.csv").write_text("col;val\n1;2\n", encoding="utf-8")
        result = run_cli(["profile", "data/sample.csv", "--output", "out"], cwd=tmp_path)
        assert result.returncode == 0, result.stderr
        assert (tmp_path / "data" / "out" / "metadata.yaml").is_file(), (
            "output must land next to the input"
        )
        assert not (tmp_path / "out" / "metadata.yaml").exists(), "output must not land in cwd"

    def test_render_relative_output_anchors_to_input_parent(self, tmp_path) -> None:
        """A relative single-file render ``--output`` anchors to the package's
        parent (README.md lands in ``data/out/``, never ``<cwd>/out/``)."""
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "sample.csv").write_text("col;val\n1;2\n", encoding="utf-8")
        profiled = run_cli(["profile", "data/sample.csv"], cwd=tmp_path)
        assert profiled.returncode == 0, profiled.stderr
        assert (tmp_path / "data" / "metadata.yaml").is_file()
        result = run_cli(["render", "data/metadata.yaml", "--output", "out"], cwd=tmp_path)
        assert result.returncode == 0, result.stderr
        assert (tmp_path / "data" / "out" / "README.md").is_file(), (
            "output must land next to the package"
        )
        assert not (tmp_path / "out" / "README.md").exists(), "output must not land in cwd"

    def test_prepare_reads_relative_readme_from_toml_dir(self, tmp_path) -> None:
        """CLI prepare resolves a relative [meta] readme against the TOML's
        directory (PRP-03), never the process cwd.

        The TOML lives in ``proj/`` while the subprocess cwd is the parent —
        an un-anchored read would miss ``proj/custom.md`` and fall back to the
        generated card.
        """
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "custom.md").write_text("# PROJ CARD\n", encoding="utf-8")
        (proj / "data.csv").write_text("col_a;col_b\n1;2\n3;4\n", encoding="utf-8-sig")
        (proj / "dataset.toml").write_text(
            "[dataset]\n"
            'name = "test-ds"\n'
            'repo_id = "user/test-ds"\n'
            "\n"
            "[meta]\n"
            "confidential = false\n"
            'readme = "custom.md"\n'
            "\n"
            "[[file]]\n"
            'local = "data.csv"\n'
            'remote = "data.csv"\n',
            encoding="utf-8",
        )
        result = run_cli(["prepare", "proj/dataset.toml"], cwd=tmp_path)
        assert result.returncode == 0, result.stderr
        assert (proj / "build" / "README.md").read_text(encoding="utf-8") == "# PROJ CARD\n"


class TestConsoleEncodingGuard:
    """``cli._configure_console_streams`` pinned directly (CLI-R11).

    The three tests exercise the helper's three outcome shapes — the in-place
    reconfigure, the non-text-stream skip, and the refuses-to-reconfigure skip
    — so every line and branch arm of the helper has a deterministic carrier
    independent of how pytest's own capture object behaves (AGENTS.md rule 14
    forbids ``# pragma: no cover``).
    """

    def test_console_streams_reconfigured_in_place(self, monkeypatch) -> None:
        """A real text stream gets ``errors="replace"``, in place (CLI-R11).

        Asserting both ``stream.errors`` and the substitution bytes proves the
        guard *substitutes* an unencodable character instead of raising (the
        stream stays ASCII-encoded, so writing ``U+2192`` can only land as the
        replacement byte).
        """
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding="ascii", errors="strict")
        monkeypatch.setattr(sys, "stdout", stream)
        monkeypatch.setattr(sys, "stderr", stream)
        # The guard's policy is owned by config.py, never a [tool.sofer] key.
        assert config.CONSOLE_ERRORS == "replace"

        cli._configure_console_streams()

        assert stream.errors == "replace"
        assert sys.stdout is stream
        assert sys.stderr is stream
        stream.write("\u2192")
        stream.flush()
        assert buffer.getvalue() == b"?"

    def test_console_guard_skips_stream_without_reconfigure(self, monkeypatch) -> None:
        """An ``io.StringIO`` capture object is left untouched (CLI-R11).

        ``io.StringIO`` is exactly the object
        :func:`sofer.mcp_server._capture_output` installs; the guard must
        neither raise nor replace it, keeping MSP-R01 stdout framing intact.
        """
        out = io.StringIO()
        err = io.StringIO()
        monkeypatch.setattr(sys, "stdout", out)
        monkeypatch.setattr(sys, "stderr", err)

        cli._configure_console_streams()

        assert sys.stdout is out
        assert sys.stderr is err
        assert out.getvalue() == ""
        assert err.getvalue() == ""

    def test_console_guard_survives_unreconfigurable_text_wrapper(self, monkeypatch) -> None:
        """A closed ``TextIOWrapper`` is skipped, never raised on (CLI-R11).

        A closed buffer still passes the ``isinstance`` gate and makes
        ``reconfigure`` raise ``ValueError``; the guard must swallow it and
        leave the stream object in place rather than become a new
        first-statement crash source for ``main()``.
        """
        stream = io.TextIOWrapper(io.BytesIO(), encoding="ascii")
        stream.close()
        monkeypatch.setattr(sys, "stdout", stream)
        monkeypatch.setattr(sys, "stderr", stream)

        cli._configure_console_streams()

        assert sys.stdout is stream
        assert sys.stderr is stream


def test_codebook_all_files_max_sample_parity(tmp_path):
    """#155: CLI codebook --all-files forwards --max-sample (CLI/MCP parity)."""
    (tmp_path / "data.csv").write_text("col_a;col_b\n1;x\n2;y\n3;z\n", encoding="utf-8-sig")
    (tmp_path / "dataset.toml").write_text(
        "[dataset]\nname='ds'\nrepo_id='u/ds'\n\n[[file]]\nlocal='data.csv'\nremote='data.csv'\n",
        encoding="utf-8",
    )
    result = run_cli(
        ["codebook", "--all-files", "--config", "dataset.toml", "--max-sample", "1"],
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    cb = tmp_path / "build" / "codebooks" / "data.md"
    assert "Analysed rows:** 1 (sample)" in cb.read_text(encoding="utf-8")


# ── kept __main__ guard executed in-process (COV-06, Resolution A) ────────────


def test_cli_main_guard_executed_via_runpy(monkeypatch) -> None:
    """The kept ``if __name__ == "__main__": main()`` guard executes in-process
    via ``runpy.run_module(..., run_name="__main__")`` under the coverage tracer
    (COV-06 scenario d). The body runs ``main()`` through the guard with argv at
    a harmless subcommand (``--help``), which exits 0 after printing usage — the
    guard lines count as covered, mandatory for the cli.py 100.00 row (Resolution
    A: zero ``src/sofer/`` edits; the guard is covered, never removed).
    """
    import runpy

    import pytest

    monkeypatch.setattr(sys, "argv", ["sofer", "--help"])
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("sofer.cli", run_name="__main__")
    assert excinfo.value.code == 0


# ── Unit B: drive cli.py to 100.00% line coverage (COV-06) ────────────────────


class TestNoChecksPath:
    def test_prepare_no_checks_runs_happy_path(self, tmp_path) -> None:
        """--no-checks short-circuits the validators (cli.py:83) and the
        ``_cmd_prepare`` happy tail (output resolve + real run_prepare)."""
        (tmp_path / "data.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        toml = tmp_path / "dataset.toml"
        toml.write_text(
            '[dataset]\nname = "test"\nrepo_id = "u/test"\nbuild_dir = "build"\n\n'
            '[[file]]\nlocal = "data.csv"\nremote = "data.csv"\n',
            encoding="utf-8",
        )
        rc = cli._cmd_prepare(
            Namespace(
                config=str(toml),
                output=None,
                all_files=False,
                no_checks=True,
                force=False,
                verify=False,
            )
        )
        assert rc == 0
        assert (tmp_path / "build" / "data.parquet").is_file()
        assert (tmp_path / "build" / "README.md").is_file()


class TestCodebookAllFilesErrors:
    def test_all_files_valueerror_returns_1(self, tmp_path, monkeypatch, capsys) -> None:
        """generate_all_codebooks raising ValueError surfaces on stderr with rc 1."""
        (tmp_path / "data.csv").write_text("col\n1\n", encoding="utf-8")
        toml = tmp_path / "dataset.toml"
        toml.write_text(
            '[dataset]\nname = "test"\nrepo_id = "alice/test"\n\n'
            '[[file]]\nlocal = "data.csv"\nremote = "data.csv"\n',
            encoding="utf-8",
        )

        def _boom(*_a, **_k):
            raise ValueError("boom: no codebook")

        monkeypatch.setattr(cli, "generate_all_codebooks", _boom)
        rc = cli._cmd_codebook(
            Namespace(all_files=True, config=str(toml), csv=None, output=None, max_sample=None)
        )
        assert rc == 1
        assert "boom: no codebook" in capsys.readouterr().err

    def test_codebook_requires_file_or_all_files(self, capsys) -> None:
        """No FILE positional and no --all-files exits 1 with the guidance."""
        rc = cli._cmd_codebook(
            Namespace(
                all_files=False,
                config="ignored.toml",
                csv=None,
                output=None,
                max_sample=None,
            )
        )
        assert rc == 1
        assert "Must specify a FILE" in capsys.readouterr().err

    def test_codebook_relative_output_anchors_to_input_parent(self, tmp_path) -> None:
        """A relative single-file -o anchors to the INPUT's parent, not cwd
        (MSP-R10; the subprocess twin lives in TestSubprocessBoundary)."""
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "sample.csv").write_text("col;val\n1;2\n", encoding="utf-8")
        rc = cli._cmd_codebook(
            Namespace(
                all_files=False,
                csv=str(tmp_path / "data" / "sample.csv"),
                output="out.md",
                config="d.toml",
                max_sample=None,
            )
        )
        assert rc == 0
        assert (tmp_path / "data" / "out.md").is_file()
        assert not (tmp_path / "out.md").exists()


class TestProfileRenderFlagCoverage:
    @staticmethod
    def _batch_toml(tmp_path) -> str:
        (tmp_path / "cache").mkdir(exist_ok=True)
        (tmp_path / "cache" / "a.csv").write_text("col;val\n1;2\n", encoding="utf-8")
        toml = tmp_path / "custom.toml"
        toml.write_text(
            '[dataset]\nname = "test"\nrepo_id = "u/test"\n\n'
            '[[file]]\nlocal = "cache/a.csv"\nremote = "a.csv"\n',
            encoding="utf-8",
        )
        return str(toml)

    @_pytest.mark.parametrize(
        "config_arg,dataset_arg,chdir",
        [
            ("CUSTOM", None, False),
            ("DEFAULT", "CUSTOM", False),
            ("DEFAULT", None, True),
        ],
    )
    def test_profile_all_files_toml_selection_variants(
        self, tmp_path, monkeypatch, restore_tool_config, config_arg, dataset_arg, chdir
    ) -> None:
        """All three effective-TOML selection branches of ``_cmd_profile``."""
        import sofer.config as cfg_mod

        custom = self._batch_toml(tmp_path)
        if chdir:
            monkeypatch.chdir(tmp_path)
            (tmp_path / "dataset.toml").write_text(
                '[dataset]\nname = "test"\nrepo_id = "u/test"\n\n'
                '[[file]]\nlocal = "cache/a.csv"\nremote = "a.csv"\n',
                encoding="utf-8",
            )
        cfg_mod.reload(tmp_path)
        config_val = custom if config_arg == "CUSTOM" else cfg_mod.DEFAULT_CONFIG_NAME
        dataset_val = custom if dataset_arg == "CUSTOM" else None
        rc = cli._cmd_profile(
            Namespace(
                dataset=dataset_val,
                output=None,
                all_files=True,
                force=False,
                config=config_val,
            )
        )
        assert rc == 0
        assert (tmp_path / "cache" / "profiles" / "a.metadata.yaml").is_file()

    def test_profile_all_files_no_file_entries_returns_1(
        self, tmp_path, capsys, monkeypatch
    ) -> None:
        """Defensive branch: an empty-but-valid config prints the [[file]]
        guidance and exits 1. DatasetConfig.validate() itself rejects empty
        files, so the CLI's own defense-in-depth check is exercised with the
        validator seam returning [] (simulating that degenerate valid state)."""
        toml = tmp_path / "empty.toml"
        toml.write_text('[dataset]\nname = "x"\nrepo_id = "u/x"\n', encoding="utf-8")
        monkeypatch.setattr(cli.DatasetConfig, "validate", lambda self: [])
        rc = cli._cmd_profile(
            Namespace(dataset=None, output=None, all_files=True, force=False, config=str(toml))
        )
        assert rc == 1
        assert "No [[file]] entries found" in capsys.readouterr().err

    def test_profile_all_files_generator_valueerror_returns_1(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        """A batch profile ValueError (e.g. output collision) surfaces on stderr
        with rc 1 via the _gen_all guard."""
        import sofer.profile as profile_mod

        custom = self._batch_toml(tmp_path)

        def _boom(*_a, **_k):
            raise ValueError("collision detected")

        monkeypatch.setattr(profile_mod, "generate_all_profiles", _boom)
        rc = cli._cmd_profile(
            Namespace(dataset=None, output=None, all_files=True, force=False, config=custom)
        )
        assert rc == 1
        assert "collision detected" in capsys.readouterr().err

    def test_profile_all_files_unreadable_toml_returns_1(self, tmp_path, capsys) -> None:
        """A non-existent --config path surfaces from_toml failure with rc 1."""
        rc = cli._cmd_profile(
            Namespace(dataset=None, output=None, all_files=True, force=False, config="nope.toml")
        )
        assert rc == 1
        assert "Failed to read TOML" in capsys.readouterr().err

    def test_profile_requires_dataset_or_all_files(self, capsys) -> None:
        """Single-file profile without a dataset positional exits 1."""
        rc = cli._cmd_profile(
            Namespace(dataset=None, output=None, all_files=False, force=False, config="d.toml")
        )
        assert rc == 1
        assert "Must specify a dataset file" in capsys.readouterr().err

    def test_profile_relative_output_anchors_to_dataset_parent(self, tmp_path) -> None:
        """A relative single-file profile --output anchors next to the dataset."""
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "sample.csv").write_text("col;val\n1;2\n", encoding="utf-8")
        rc = cli._cmd_profile(
            Namespace(
                dataset=str(tmp_path / "data" / "sample.csv"),
                output="out",
                all_files=False,
                force=False,
                config="d.toml",
            )
        )
        assert rc == 0
        assert (tmp_path / "data" / "out" / "metadata.yaml").is_file()
        assert not (tmp_path / "out" / "metadata.yaml").exists()

    @_pytest.mark.parametrize("variant", ["config", "package", "defaults"])
    def test_render_all_files_selection_and_error_variants(
        self, tmp_path, monkeypatch, restore_tool_config, variant
    ) -> None:
        """Render --all-files effective-TOML selection mirrors the profile set:
        explicit --config, package positional, and the all-default fallback."""
        import sofer.config as cfg_mod
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        custom = self._batch_toml(tmp_path)
        generate_all_profiles(DatasetConfig.from_toml(custom))
        cfg_mod.reload(tmp_path)
        if variant == "config":
            rc = cli._cmd_render(
                Namespace(
                    package=None,
                    output=None,
                    all_files=True,
                    force=False,
                    config=custom,
                )
            )
        elif variant == "package":
            monkeypatch.chdir(tmp_path)
            rc = cli._cmd_render(
                Namespace(
                    package=custom,
                    output=None,
                    all_files=True,
                    force=False,
                    config=cfg_mod.DEFAULT_CONFIG_NAME,
                )
            )
        else:
            monkeypatch.chdir(tmp_path)
            (tmp_path / "dataset.toml").write_text(
                '[dataset]\nname = "test"\nrepo_id = "u/test"\n\n'
                '[[file]]\nlocal = "cache/a.csv"\nremote = "a.csv"\n',
                encoding="utf-8",
            )
            rc = cli._cmd_render(
                Namespace(
                    package=None,
                    output=None,
                    all_files=True,
                    force=False,
                    config=cfg_mod.DEFAULT_CONFIG_NAME,
                )
            )
        assert rc == 0
        assert (tmp_path / "cache" / "renders" / "a.README.md").is_file()

    def test_render_no_entries_returns_1(self, tmp_path, capsys, monkeypatch) -> None:
        """Defensive branch: an empty-but-valid config prints the [[file]]
        guidance and exits 1 (validator seam simulates the degenerate state)."""
        toml = tmp_path / "empty.toml"
        toml.write_text('[dataset]\nname = "x"\nrepo_id = "u/x"\n', encoding="utf-8")
        monkeypatch.setattr(cli.DatasetConfig, "validate", lambda self: [])
        rc = cli._cmd_render(
            Namespace(package=None, output=None, all_files=True, force=False, config=str(toml))
        )
        assert rc == 1
        assert "No [[file]] entries found" in capsys.readouterr().err

    def test_render_all_files_generator_valueerror_returns_1(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        """A batch render ValueError (e.g. output collision) surfaces on stderr
        with rc 1 via the _gen_all_renders guard."""
        import sofer.render as render_mod

        custom = self._batch_toml(tmp_path)

        def _boom(*_a, **_k):
            raise ValueError("render collision detected")

        monkeypatch.setattr(render_mod, "generate_all_renders", _boom)
        rc = cli._cmd_render(
            Namespace(package=None, output=None, all_files=True, force=False, config=custom)
        )
        assert rc == 1
        assert "render collision detected" in capsys.readouterr().err

    def test_render_unreadable_toml_returns_1(self, tmp_path, capsys) -> None:
        """Render --all-files with a missing config path exits 1."""
        rc = cli._cmd_render(
            Namespace(package=None, output=None, all_files=True, force=False, config="nope.toml")
        )
        assert rc == 1
        assert "Failed to read TOML" in capsys.readouterr().err

    def test_render_requires_package_and_reports_toml_errors(self, tmp_path, capsys) -> None:
        """Single-file render without a package exits 1; render errors surface rc 1."""
        rc = cli._cmd_render(
            Namespace(package=None, output=None, all_files=False, force=False, config="d.toml")
        )
        assert rc == 1
        assert "Must specify a package path" in capsys.readouterr().err
        (tmp_path / "pkg").mkdir()
        rc2 = cli._cmd_render(
            Namespace(
                package=str(tmp_path / "pkg"),
                output=None,
                all_files=False,
                force=False,
                config="d.toml",
            )
        )
        assert rc2 == 1

    def test_render_relative_output_and_existing_readme_hint(self, tmp_path) -> None:
        """Relative single-file render --output anchors next to the package and
        an existing destination without --force raises the overwrite hint."""
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "sample.csv").write_text("col;val\n1;2\n", encoding="utf-8")
        from sofer.profile import profile as run_profile

        assert run_profile(tmp_path / "data" / "sample.csv") == 0
        rc = cli._cmd_render(
            Namespace(
                package=str(tmp_path / "data" / "metadata.yaml"),
                output="out",
                all_files=False,
                force=False,
                config="d.toml",
            )
        )
        assert rc == 0
        assert (tmp_path / "data" / "out" / "README.md").is_file()
        rc2 = cli._cmd_render(
            Namespace(
                package=str(tmp_path / "data" / "metadata.yaml"),
                output="out",
                all_files=False,
                force=False,
                config="d.toml",
            )
        )
        assert rc2 == 1


class TestScanPromptGate:
    def test_scan_phase1_prompt_preview_and_yes(self, tmp_path, monkeypatch, capsys) -> None:
        """Phase-1 prompt previews the move target; answering y proceeds."""
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("builtins.input", lambda _p="": "y")
        rc = cli._cmd_scan(Namespace(config=str(cfg), dry_run=False, force=False, ext=None))
        assert rc == 0
        out = capsys.readouterr().out
        assert "The following files will be moved to raw/:" in out
        assert (tmp_path / "raw" / "a.csv").exists()
        assert (tmp_path / "cache" / "a.csv").exists()

    def test_scan_phase1_eof_aborts_atomically(self, tmp_path, monkeypatch, capsys) -> None:
        """Phase-1 gate EOFError aborts before any move (TOML untouched)."""
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        original = cfg.read_text(encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        def _eof(_p=""):
            raise EOFError

        monkeypatch.setattr("builtins.input", _eof)
        rc = cli._cmd_scan(Namespace(config=str(cfg), dry_run=False, force=False, ext=None))
        assert rc == 0
        out = capsys.readouterr().out
        assert "OK  Aborted." in out
        assert (tmp_path / "a.csv").exists()  # never moved
        assert not (tmp_path / "raw" / "a.csv").exists()
        assert cfg.read_text(encoding="utf-8") == original

    def test_scan_phase2_eof_aborts_atomically(self, tmp_path, monkeypatch, capsys) -> None:
        """Phase-2 gate EOFError aborts atomically: TOML untouched, no cache copy."""
        (tmp_path / "raw").mkdir()
        (tmp_path / "raw" / "a.csv").write_text("x\n1\n", encoding="utf-8")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        original = cfg.read_text(encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        def _eof(_p=""):
            raise EOFError

        monkeypatch.setattr("builtins.input", _eof)
        rc = cli._cmd_scan(Namespace(config=str(cfg), dry_run=False, force=False, ext=None))
        assert rc == 0
        out = capsys.readouterr().out
        assert "OK  Aborted." in out
        assert cfg.read_text(encoding="utf-8") == original
        assert not (tmp_path / "cache").exists()


class TestScanCliFailurePaths:
    def test_scan_move_failure_returns_1(self, tmp_path, monkeypatch, capsys) -> None:
        """move_to_raw raising surfaces on stderr with rc 1 (no TOML write)."""
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        def _boom(*_a, **_k):
            raise OSError("permission denied")

        monkeypatch.setattr(cli, "move_to_raw", _boom)
        rc = cli._cmd_scan(Namespace(config=str(cfg), dry_run=False, force=True, ext=None))
        assert rc == 1
        assert "Failed to move to raw/" in capsys.readouterr().err

    def test_scan_flatten_collision_aborts_before_copy(self, tmp_path, monkeypatch, capsys) -> None:
        """A flatten collision in Phase 2 aborts before any copy (TOML untouched)."""
        (tmp_path / "raw").mkdir()
        (tmp_path / "raw" / "a.csv").write_text("1\n", encoding="utf-8")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        original = cfg.read_text(encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        def _raise(*_a, **_k):
            raise ValueError("Collision in cache/: two files flatten to a.csv")

        monkeypatch.setattr(cli, "check_flatten_collisions", _raise)
        rc = cli._cmd_scan(Namespace(config=str(cfg), dry_run=False, force=True, ext=None))
        assert rc == 1
        assert "Collision in cache/" in capsys.readouterr().err
        assert cfg.read_text(encoding="utf-8") == original
        assert not (tmp_path / "cache").exists()

    def test_scan_copy_collision_returns_1(self, tmp_path, monkeypatch, capsys) -> None:
        """A differing pre-existing cache/ dest (without --force) exits 1."""
        (tmp_path / "raw").mkdir()
        (tmp_path / "raw" / "a.csv").write_text("src\n", encoding="utf-8")
        (tmp_path / "cache").mkdir()
        (tmp_path / "cache" / "a.csv").write_text("different-dest\n", encoding="utf-8")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("builtins.input", lambda _p="": "y")
        rc = cli._cmd_scan(Namespace(config=str(cfg), dry_run=False, force=False, ext=None))
        assert rc == 1
        assert "already exists and differs" in capsys.readouterr().err


class TestScanDryRun:
    def test_scan_dry_run_idempotent_cache(self, tmp_path, monkeypatch, capsys) -> None:
        """dry-run with an already-identical cache/ dest reports 'Nothing to copy'."""
        (tmp_path / "raw").mkdir()
        (tmp_path / "cache").mkdir()
        (tmp_path / "raw" / "a.csv").write_text("same\n", encoding="utf-8")
        (tmp_path / "cache" / "a.csv").write_text("same\n", encoding="utf-8")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_scan(Namespace(config=str(cfg), dry_run=True, force=False, ext=None))
        assert rc == 0
        out = capsys.readouterr().out
        assert "DRY RUN  Nothing to copy" in out
        assert "all files already present" in out

    def test_scan_dry_run_all_registered(self, tmp_path, monkeypatch, capsys) -> None:
        """dry-run with every discovered file already registered reports idempotent."""
        (tmp_path / "raw").mkdir()
        (tmp_path / "raw" / "a.csv").write_text("same\n", encoding="utf-8")
        (tmp_path / "cache").mkdir()
        (tmp_path / "cache" / "a.csv").write_text("same\n", encoding="utf-8")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text(
            '[dataset]\nname = "test"\nrepo_id = "u/t"\n\n'
            '[[file]]\nlocal = "cache/a.csv"\nremote = "a.csv"\n',
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_scan(Namespace(config=str(cfg), dry_run=True, force=False, ext=None))
        assert rc == 0
        out = capsys.readouterr().out
        assert "DRY RUN  All discovered files already registered (idempotent)." in out


class TestMcpAddCliCoverage:
    def test_mcp_add_defaults_to_cwd(self, tmp_path, monkeypatch) -> None:
        """No --cwd resolves the entry cwd from Path.cwd() (cli.py:652)."""
        import json as _json
        from pathlib import Path as _Path

        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(_Path, "home", lambda: home)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        rc = cli._cmd_mcp_add(Namespace(agent="opencode", scope="project", cwd=None, dry_run=False))
        assert rc == 0
        path = tmp_path / "opencode.json"
        assert path.exists()
        data = _json.loads(path.read_text(encoding="utf-8"))
        assert data["mcp"]["sofer"]["cwd"] == str(tmp_path.resolve())

    def test_mcp_add_native_delegation_skips_file_edit(self, tmp_path, monkeypatch, capsys) -> None:
        """probe True + delegate True prints the delegated line and writes none."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: True)
        monkeypatch.setattr(mcp_registration, "delegate_add", lambda *a, **kw: True)
        rc = cli._cmd_mcp_add(
            Namespace(agent="codex", scope="project", cwd=str(tmp_path), dry_run=False)
        )
        assert rc == 0
        assert "codex delegated via native mcp add" in capsys.readouterr().out
        assert not (tmp_path / ".codex" / "config.toml").exists()

    def test_mcp_add_native_failure_falls_back(self, tmp_path, monkeypatch, capsys) -> None:
        """probe True but delegate raising falls back to the file-edit path."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: True)

        def _raise(*_a, **_k):
            raise RuntimeError("native boom")

        monkeypatch.setattr(mcp_registration, "delegate_add", _raise)
        rc = cli._cmd_mcp_add(
            Namespace(agent="codex", scope="project", cwd=str(tmp_path), dry_run=False)
        )
        assert rc == 0
        err = capsys.readouterr().err
        assert "native delegation failed, falling back to file edit" in err
        assert (tmp_path / ".codex" / "config.toml").exists()

    @_pytest.mark.parametrize("with_cwd", [True, False])
    def test_mcp_add_project_scope_path_anchoring(self, tmp_path, monkeypatch, with_cwd) -> None:
        """Both project-scope resolve_config_path branches anchor correctly."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        cwd = str(tmp_path) if with_cwd else None
        rc = cli._cmd_mcp_add(Namespace(agent="opencode", scope="project", cwd=cwd, dry_run=False))
        assert rc == 0
        assert (tmp_path / "opencode.json").exists()

    def test_mcp_add_user_scope_anchors_under_home(self, tmp_path, monkeypatch) -> None:
        """User scope resolves the config under the patched home (else branch)."""
        from pathlib import Path as _Path

        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(_Path, "home", lambda: home)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        rc = cli._cmd_mcp_add(Namespace(agent="gemini", scope="user", cwd=None, dry_run=False))
        assert rc == 0
        assert (home / ".config" / "gemini" / "settings.json").exists()


class TestMcpAddCliFailure:
    def test_mcp_add_backup_failure_returns_1(self, tmp_path, monkeypatch, capsys) -> None:
        """backup failure surfaces on stderr with overall rc 1."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()

        def _boom(_path):
            raise OSError("backup exploded")

        monkeypatch.setattr(mcp_registration, "backup", _boom)
        rc = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc == 1
        assert "backup failed" in capsys.readouterr().err

    def test_mcp_add_write_failure_returns_1(self, tmp_path, monkeypatch, capsys) -> None:
        """atomic_write failure surfaces on stderr with overall rc 1."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        monkeypatch.setattr(mcp_registration, "validate_cwd", lambda *a, **kw: True)
        proj = tmp_path / "proj"
        proj.mkdir()

        def _boom(*_a, **_k):
            raise OSError("write exploded")

        monkeypatch.setattr(mcp_registration, "atomic_write", _boom)
        rc = cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=False)
        )
        assert rc == 1
        assert "write failed" in capsys.readouterr().err


class TestMcpRemoveCliCoverage:
    def test_mcp_remove_native_success_and_fallback(self, tmp_path, monkeypatch, capsys) -> None:
        """native remove success skips file edit; a later failure falls back."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: True)

        calls: dict[str, int] = {"n": 0}

        def _delegate(*_a, **_k):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("native remove boom")
            return calls["n"] == 1  # first succeeds

        monkeypatch.setattr(mcp_registration, "delegate_remove", _delegate)
        rc = cli._cmd_mcp_remove(Namespace(agent="codex", scope="project", dry_run=False))
        assert rc == 0
        out = capsys.readouterr().out
        assert "codex delegated remove via native mcp remove" in out
        rc2 = cli._cmd_mcp_remove(Namespace(agent="codex", scope="project", dry_run=False))
        assert rc2 == 0
        err = capsys.readouterr().err
        assert "native remove failed, falling back to file edit" in err

    def test_mcp_remove_idempotent_absent(self, tmp_path, monkeypatch, capsys) -> None:
        """remove_entry returning (doc, False) prints the idempotent line."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        rc = cli._cmd_mcp_remove(Namespace(agent="gemini", scope="project", dry_run=False))
        assert rc == 0
        assert "already absent (idempotent)" in capsys.readouterr().out

    def test_mcp_remove_dry_run_no_mutation(self, tmp_path, monkeypatch) -> None:
        """dry-run remove previews without mutating the config file."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        cli._cmd_mcp_add(
            Namespace(agent="opencode", scope="project", cwd=str(tmp_path), dry_run=False)
        )
        path = tmp_path / "opencode.json"
        before = path.read_bytes()
        rc = cli._cmd_mcp_remove(Namespace(agent="opencode", scope="project", dry_run=True))
        assert rc == 0
        assert path.read_bytes() == before


class TestMcpRemoveCliFailure:
    @_pytest.mark.parametrize("which", ["unreadable", "backup", "write"])
    def test_mcp_remove_error_paths_return_1(self, tmp_path, monkeypatch, capsys, which) -> None:
        """Unreadable config, backup failure, and write failure each exit 1."""
        proj = tmp_path / "proj"
        proj.mkdir()
        monkeypatch.chdir(proj)
        monkeypatch.setattr(mcp_registration, "probe_native", lambda *a, **kw: False)
        cli._cmd_mcp_add(Namespace(agent="opencode", scope="project", cwd=str(proj), dry_run=False))
        path = proj / "opencode.json"
        if which == "unreadable":
            path.write_text("{ not json", encoding="utf-8")
            expected = "config unreadable"
        elif which == "backup":
            monkeypatch.setattr(
                mcp_registration,
                "backup",
                lambda *a, **kw: (_ for _ in ()).throw(OSError("boom")),
            )
            expected = "backup failed"
        else:
            monkeypatch.setattr(
                mcp_registration,
                "atomic_write",
                lambda *a, **kw: (_ for _ in ()).throw(OSError("boom")),
            )
            expected = "write failed"
        rc = cli._cmd_mcp_remove(Namespace(agent="opencode", scope="project", dry_run=False))
        assert rc == 1
        err = capsys.readouterr().err
        assert expected in err


class TestInitMoveExistingCoverage:
    def test_move_existing_no_candidates_dry_run(self, tmp_path, monkeypatch, capsys) -> None:
        """No supported files + --move-existing --dry-run prints the no-move line
        and skips the collision check entirely (branch 957->965)."""
        (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_init(
            Namespace(name="ds", user="alice", move_existing=True, dry_run=True, force=False)
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "DRY RUN  No supported files to move." in out
        assert "Would create ds.toml" in out
        assert not (tmp_path / "ds.toml").exists()
        assert not (tmp_path / "raw").exists()

    def test_move_existing_prompt_eof_aborts_but_creates_toml(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        """TTY + EOFError at the move prompt aborts the move but still writes the
        TOML and scaffolds raw/ (exit 0)."""
        (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        def _eof(_p=""):
            raise EOFError

        monkeypatch.setattr("builtins.input", _eof)
        rc = cli._cmd_init(
            Namespace(name="ds", user="alice", move_existing=True, dry_run=False, force=False)
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "OK  Aborted move." in out
        assert (tmp_path / "ds.toml").exists()
        assert (tmp_path / "raw").is_dir()
        assert (tmp_path / "a.csv").exists()  # never moved
        assert not (tmp_path / "raw" / "a.csv").exists()
