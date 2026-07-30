"""Tests for data_uploader.cli — argument parsing and command dispatch.

The upload and validate commands depend on Hugging Face credentials and real
filesystem state, so they are integration-level.  Here we test everything
that can be verified without network calls or real data.
"""

import sys
from argparse import Namespace

from data_uploader import cli

# ── Argument parsing ──────────────────────────────────────────────────────────


class TestParser:
    def test_init_command(self):
        """`data-uploader init my-dataset` should parse to the init command."""
        args = cli._build_parser().parse_args(["init", "my-dataset"])
        assert args.command == "init"
        assert args.name == "my-dataset"
        assert callable(args.func)

    def test_validate_command(self):
        """`data-uploader validate path/to/file.toml` should parse correctly."""
        args = cli._build_parser().parse_args(["validate", "config.toml"])
        assert args.command == "validate"
        assert args.config == "config.toml"

    def test_upload_command(self):
        """`data-uploader upload config.toml` should parse correctly."""
        args = cli._build_parser().parse_args(["upload", "some.toml"])
        assert args.command == "upload"
        assert args.config == "some.toml"

    def test_codebook_command_no_output(self):
        """`data-uploader codebook data.csv` (stdout) should parse."""
        args = cli._build_parser().parse_args(["codebook", "data.csv"])
        assert args.command == "codebook"
        assert args.csv == "data.csv"
        assert args.output is None

    def test_codebook_command_with_output(self):
        """`data-uploader codebook data.csv -o out.md` should parse."""
        args = cli._build_parser().parse_args(["codebook", "data.csv", "-o", "out.md"])
        assert args.command == "codebook"
        assert args.csv == "data.csv"
        assert args.output == "out.md"

    def test_version(self):
        """`data-uploader --version` should print version and exit."""
        try:
            cli._build_parser().parse_args(["--version"])
        except SystemExit as e:
            assert e.code == 0


# ── init command ──────────────────────────────────────────────────────────────


class TestInitCommand:
    def test_init_creates_toml(self, tmp_path, monkeypatch):
        """`data-uploader init <name>` should write a .toml file."""
        monkeypatch.chdir(tmp_path)
        rc = cli._cmd_init(Namespace(name="my-dataset"))
        assert rc == 0
        assert (tmp_path / "my-dataset.toml").exists()

    def test_init_refuses_overwrite(self, tmp_path, monkeypatch):
        """`data-uploader init <name>` on an existing file should fail."""
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


# ─── Entry point smoke test ────────────────────────────────────────────────────


def test_main_help_prints(monkeypatch):
    """`data-uploader --help` should print usage and exit 0."""
    monkeypatch.setattr(sys, "argv", ["data-uploader", "--help"])
    try:
        cli.main()
    except SystemExit as e:
        assert e.code == 0
