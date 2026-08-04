"""Tests for sofer.scanner — discover, merge, copy, write, and integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sofer import config
from sofer.model import DatasetConfig
from sofer.scanner import (
    check_flatten_collisions,
    copy_files,
    discover_files,
    flatten_first_level,
    merge_entries,
    write_toml,
)


# ------------------------------------------------------------------
# TestConfigConstants
# ------------------------------------------------------------------


class TestConfigConstants:
    """Unit tests for tool-wide config constants used by the scan pipeline."""

    def test_codebooks_dir_constant_exists(self) -> None:
        """CODEBOOKS_DIR is a str constant exposed by the config module."""
        assert hasattr(config, "CODEBOOKS_DIR")
        assert isinstance(config.CODEBOOKS_DIR, str)
        assert config.CODEBOOKS_DIR == "codebooks"


# ------------------------------------------------------------------
# TestFlattenFirstLevel
# ------------------------------------------------------------------


class TestFlattenFirstLevel:
    """Unit tests for :func:`flatten_first_level` — first-segment stripping."""

    def test_root_file_unchanged(self) -> None:
        """A file at the config root (no directory component) keeps its name."""
        result = flatten_first_level(Path("a.csv"))
        assert result == Path("a.csv")

    def test_single_dir_strips_first_segment(self) -> None:
        """A file one level deep gets its first segment removed."""
        result = flatten_first_level(Path("raw/a.csv"))
        assert result == Path("a.csv")

    def test_nested_strips_only_first_segment(self) -> None:
        """Deeper subdirectories beyond the first segment are preserved."""
        result = flatten_first_level(Path("raw/Labels/a.csv"))
        assert result == Path("Labels/a.csv")

    def test_root_file_without_extension(self) -> None:
        """Flatten works on files without extensions too."""
        result = flatten_first_level(Path("README"))
        assert result == Path("README")


# ------------------------------------------------------------------
# TestCheckFlattenCollisions
# ------------------------------------------------------------------


class TestCheckFlattenCollisions:
    """Unit tests for :func:`check_flatten_collisions`."""

    def test_collision_raises_naming_sources(self) -> None:
        """Two files from different source dirs colliding on the same dest raise ValueError."""
        discovered = [Path("raw/a.csv"), Path("processed/a.csv")]
        with pytest.raises(ValueError, match="Collision in data/"):
            check_flatten_collisions(discovered, Path("."))

    def test_collision_error_names_both_sources(self) -> None:
        """The error message names all colliding source paths."""
        discovered = [Path("raw/a.csv"), Path("processed/a.csv")]
        try:
            check_flatten_collisions(discovered, Path("."))
        except ValueError as exc:
            msg = str(exc)
            assert "raw/a.csv" in msg
            assert "processed/a.csv" in msg

    def test_collision_with_more_than_two_sources(self) -> None:
        """Three or more sources colliding on the same destination all appear in the error."""
        discovered = [
            Path("A/data.csv"),
            Path("B/data.csv"),
            Path("C/data.csv"),
        ]
        try:
            check_flatten_collisions(discovered, Path("."))
        except ValueError as exc:
            msg = str(exc)
            assert "A/data.csv" in msg
            assert "B/data.csv" in msg
            assert "C/data.csv" in msg

    def test_no_collision_single_source(self) -> None:
        """No error when all files come from the same first-level dir."""
        discovered = [Path("raw/a.csv"), Path("raw/b.csv")]
        # Should not raise.
        check_flatten_collisions(discovered, Path("."))

    def test_no_collision_different_flattened_names(self) -> None:
        """No error when files flatten to different names."""
        discovered = [Path("raw/a.csv"), Path("processed/b.csv")]
        # Should not raise.
        check_flatten_collisions(discovered, Path("."))

    def test_no_collision_nested_different_dirs(self) -> None:
        """No error when nested paths flatten to distinct destinations."""
        discovered = [
            Path("raw/Labels/a.csv"),
            Path("raw/Config/b.csv"),
        ]
        # Should not raise — different flattened names.
        check_flatten_collisions(discovered, Path("."))


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _touch(path: Path, content: str = "x") -> Path:
    """Create *path* and its parents, write *content*, return the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _make_tree(tmp_path: Path, entries: list[str]) -> None:
    """Populate *tmp_path* with empty files matching *entries*.

    Each entry is a relative path like ``"data/a.csv"`` or ``".venv/junk.py"``.
    """
    for p in entries:
        _touch(tmp_path / p)


# ------------------------------------------------------------------
# TestDiscoverFiles
# ------------------------------------------------------------------


class TestDiscoverFiles:
    """Unit tests for :func:`discover_files`."""

    def test_filter_by_extension(self, tmp_path: Path) -> None:
        """Only files with supported suffixes are returned."""
        _make_tree(tmp_path, ["a.csv", "b.tsv", "c.parquet", "d.xlsx", "e.jsonl", "f.txt", "g.py"])
        result = discover_files(tmp_path)
        names = {p.name for p in result}
        assert names == {"a.csv", "b.tsv", "c.parquet", "d.xlsx", "e.jsonl"}

    def test_excluded_dirs_are_skipped(self, tmp_path: Path) -> None:
        """Files inside EXCLUSIONS directories are ignored."""
        _make_tree(
            tmp_path,
            ["a.csv", ".git/hidden.csv", "__pycache__/cached.csv", ".venv/lib/foo.csv"],
        )
        result = discover_files(tmp_path)
        names = {p.name for p in result}
        assert names == {"a.csv"}

    def test_ext_override(self, tmp_path: Path) -> None:
        """--ext restricts discovery to the requested suffixes only."""
        _make_tree(tmp_path, ["a.csv", "b.tsv", "c.parquet"])
        result = discover_files(tmp_path, extensions=[".csv"])
        names = {p.name for p in result}
        assert names == {"a.csv"}

    def test_ext_without_dot(self, tmp_path: Path) -> None:
        """--ext csv (without dot prefix) is normalised internally."""
        _make_tree(tmp_path, ["a.csv", "b.tsv"])
        result = discover_files(tmp_path, extensions=["csv"])
        names = {p.name for p in result}
        assert names == {"a.csv"}

    def test_empty_results(self, tmp_path: Path) -> None:
        """An empty list is returned when no supported files exist."""
        _make_tree(tmp_path, ["f.txt", "notes.md"])
        result = discover_files(tmp_path)
        assert result == []

    def test_results_are_sorted(self, tmp_path: Path) -> None:
        """Returned paths are sorted for deterministic output."""
        _make_tree(tmp_path, ["z.csv", "a.csv", "m.csv"])
        result = discover_files(tmp_path)
        names = [p.name for p in result]
        assert names == ["a.csv", "m.csv", "z.csv"]

    def test_nested_subdirectories(self, tmp_path: Path) -> None:
        """Files in nested subdirectories (not excluded) are discovered."""
        _make_tree(tmp_path, ["sub1/a.csv", "sub1/sub2/b.csv"])
        result = discover_files(tmp_path)
        assert len(result) == 2

    def test_excluded_by_name_only(self, tmp_path: Path) -> None:
        """Only directories named exactly in EXCLUSIONS are pruned, not
        similarly-named files."""
        _make_tree(tmp_path, ["build.csv", "build/nested.csv"])
        result = discover_files(tmp_path)
        names = {p.name for p in result}
        # build.csv is a file, so kept; build/nested.csv is in excluded dir, so skipped
        assert names == {"build.csv"}


# ------------------------------------------------------------------
# TestMergeEntries
# ------------------------------------------------------------------


class TestMergeEntries:
    """Unit tests for :func:`merge_entries`."""

    def _raw_toml(self, **overrides: Any) -> dict[str, Any]:
        """Return a minimal raw TOML dict."""
        data: dict[str, Any] = {
            "dataset": {"name": "test", "repo_id": "u/r"},
            "meta": {"description": "desc"},
            "file": [],
        }
        data.update(overrides)
        return data

    def test_new_entries_are_appended(self, tmp_path: Path) -> None:
        """Discovered files with no prior registration get new [[file]] entries."""
        _touch(tmp_path / "a.csv")
        _touch(tmp_path / "b.csv")
        discovered = sorted([tmp_path / "a.csv", tmp_path / "b.csv"])

        raw = self._raw_toml()
        merge_entries(discovered, raw, tmp_path, tmp_path / "data")

        files = raw["file"]
        assert len(files) == 2
        assert files[0]["local"] == "data/a.csv"
        assert files[0]["remote"] == "a.csv"
        assert files[1]["local"] == "data/b.csv"
        assert files[1]["remote"] == "b.csv"

    def test_dedup_by_resolved_path(self, tmp_path: Path) -> None:
        """A discovered file whose dest already has a registered entry is skipped."""
        _touch(tmp_path / "a.csv")
        # Pre-populate data/ so FileEntry resolves to the same absolute path.
        (tmp_path / "data").mkdir()
        _touch(tmp_path / "data" / "a.csv")

        raw = self._raw_toml(file=[{"local": "data/a.csv", "remote": "a.csv"}])
        discovered = [tmp_path / "a.csv"]

        merge_entries(discovered, raw, tmp_path, tmp_path / "data")
        assert len(raw["file"]) == 1  # no duplicate added

    def test_section_preservation(self, tmp_path: Path) -> None:
        """Non-[[file]] sections ([dataset], [meta], [[check]], [[quality])
        are left untouched."""
        raw: dict[str, Any] = {
            "dataset": {"name": "test", "repo_id": "u/r"},
            "meta": {"source": "some-org"},
            "file": [],
            "check": [{"min_files": 3}],
            "quality": [{"check": "duplicates"}],
        }
        _touch(tmp_path / "a.csv")
        merge_entries([tmp_path / "a.csv"], raw, tmp_path, tmp_path / "data")

        assert raw["dataset"]["name"] == "test"
        assert raw["meta"]["source"] == "some-org"
        assert raw["check"] == [{"min_files": 3}]
        assert raw["quality"] == [{"check": "duplicates"}]

    def test_idempotency(self, tmp_path: Path) -> None:
        """Running merge_entries twice with the same discovered files
        produces identical file lists."""
        _touch(tmp_path / "a.csv")
        discovered = [tmp_path / "a.csv"]

        raw = self._raw_toml()
        merge_entries(discovered, raw, tmp_path, tmp_path / "data")
        len_after_first = len(raw["file"])

        merge_entries(discovered, raw, tmp_path, tmp_path / "data")
        assert len(raw["file"]) == len_after_first

    def test_remote_uses_posix_separators(self, tmp_path: Path) -> None:
        """Remote paths use forward slashes (PurePosixPath) after flattening."""
        _touch(tmp_path / "sub" / "nested" / "a.csv")
        discovered = [tmp_path / "sub" / "nested" / "a.csv"]

        raw = self._raw_toml()
        merge_entries(discovered, raw, tmp_path, tmp_path / "data")
        assert raw["file"][0]["remote"] == "nested/a.csv"

    def test_preserves_existing_unrelated_entries(self, tmp_path: Path) -> None:
        """Pre-existing [[file]] entries for unrelated files are kept."""
        raw = self._raw_toml(
            file=[
                {"local": "data/readme.md", "remote": "README.md", "recursive": False},
            ]
        )
        _touch(tmp_path / "a.csv")
        merge_entries([tmp_path / "a.csv"], raw, tmp_path, tmp_path / "data")

        # Existing entry + 1 new
        assert len(raw["file"]) == 2
        assert raw["file"][0]["local"] == "data/readme.md"

    def test_merge_flattened_local_and_remote(self, tmp_path: Path) -> None:
        """local and remote paths use the flattened first-segment shape (SCN-02)."""
        _touch(tmp_path / "raw" / "DPTO.csv")
        _touch(tmp_path / "raw" / "Labels" / "etiquetas_a.csv")
        discovered = sorted([tmp_path / "raw" / "DPTO.csv", tmp_path / "raw" / "Labels" / "etiquetas_a.csv"])

        raw = self._raw_toml()
        merge_entries(discovered, raw, tmp_path, tmp_path / "data")

        assert raw["file"][0]["local"] == "data/DPTO.csv"
        assert raw["file"][0]["remote"] == "DPTO.csv"
        assert raw["file"][1]["local"] == "data/Labels/etiquetas_a.csv"
        assert raw["file"][1]["remote"] == "Labels/etiquetas_a.csv"

    def test_root_level_file_keeps_name(self, tmp_path: Path) -> None:
        """A root-level file (no directory) keeps its name in local and remote (SCN-02)."""
        _touch(tmp_path / "x.csv")
        discovered = [tmp_path / "x.csv"]

        raw = self._raw_toml()
        merge_entries(discovered, raw, tmp_path, tmp_path / "data")

        assert raw["file"][0]["local"] == "data/x.csv"
        assert raw["file"][0]["remote"] == "x.csv"


# ------------------------------------------------------------------
# TestCopyFiles
# ------------------------------------------------------------------


class TestCopyFiles:
    """Unit tests for :func:`copy_files`."""

    def test_creates_subdirs_lazily(self, tmp_path: Path) -> None:
        """Parent directories in data/ are created on demand after flattening."""
        _touch(tmp_path / "sub" / "nested" / "a.csv")
        discovered = [tmp_path / "sub" / "nested" / "a.csv"]
        data_dir = tmp_path / "data"

        copy_files(discovered, tmp_path, data_dir)
        dest = data_dir / "nested" / "a.csv"
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == "x"

    def test_dry_run_no_copy(self, tmp_path: Path) -> None:
        """dry_run=True reports without writing files."""
        _touch(tmp_path / "a.csv")
        data_dir = tmp_path / "data"

        copied = copy_files([tmp_path / "a.csv"], tmp_path, data_dir, dry_run=True)
        assert len(copied) == 1
        assert not (data_dir / "a.csv").exists()

    def test_file_exists_error_without_force(self, tmp_path: Path) -> None:
        """FileExistsError is raised when dest exists and force=False."""
        _touch(tmp_path / "a.csv")
        data_dir = tmp_path / "data"
        _touch(data_dir / "a.csv")

        with pytest.raises(FileExistsError, match="--force"):
            copy_files([tmp_path / "a.csv"], tmp_path, data_dir)

    def test_force_overwrites(self, tmp_path: Path) -> None:
        """force=True overwrites existing dest without error."""
        _touch(tmp_path / "a.csv", content="original")
        data_dir = tmp_path / "data"
        _touch(data_dir / "a.csv", content="old-dest")

        copy_files([tmp_path / "a.csv"], tmp_path, data_dir, force=True)
        assert (data_dir / "a.csv").read_text(encoding="utf-8") == "original"

    def test_source_untouched_after_copy(self, tmp_path: Path) -> None:
        """The original source file is not modified."""
        _touch(tmp_path / "a.csv", content="keep-me")
        data_dir = tmp_path / "data"

        copy_files([tmp_path / "a.csv"], tmp_path, data_dir)
        assert (tmp_path / "a.csv").read_text(encoding="utf-8") == "keep-me"


# ------------------------------------------------------------------
# TestWriteToml
# ------------------------------------------------------------------


class TestWriteToml:
    """Unit tests for :func:`write_toml`."""

    def test_writes_valid_toml(self, tmp_path: Path) -> None:
        """The written file is parseable by tomllib/tomli."""
        try:
            import tomli as _tomli
        except ImportError:
            import tomllib as _tomli

        config = tmp_path / "out.toml"
        raw = {
            "dataset": {"name": "x", "repo_id": "u/r"},
            "meta": {},
            "file": [{"local": "data/a.csv", "remote": "a.csv"}],
        }
        write_toml(raw, config)
        parsed = _tomli.loads(config.read_text(encoding="utf-8"))
        assert parsed["dataset"]["name"] == "x"
        assert parsed["file"][0]["remote"] == "a.csv"

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        """write_toml replaces the file content."""
        config = tmp_path / "out.toml"
        config.write_text("old", encoding="utf-8")
        write_toml({"dataset": {"name": "new", "repo_id": "u/r"}}, config)
        assert "new" in config.read_text(encoding="utf-8")


# ------------------------------------------------------------------
# TestIntegration
# ------------------------------------------------------------------


class TestIntegration:
    """End-to-end tests through the full scan pipeline."""

    def test_full_pipeline(self, tmp_path: Path, monkeypatch) -> None:
        """Full scan produces valid TOML that passes DatasetConfig.validate()."""
        from sofer.cli import _cmd_scan

        # Build a realistic tree.
        _touch(tmp_path / "a.csv")
        _touch(tmp_path / "b.parquet")
        _touch(tmp_path / "notes.txt")  # unsupported — ignored
        _touch(tmp_path / ".git" / "hidden.csv")  # excluded dir

        # Minimal TOML fixture.
        config = tmp_path / "dataset.toml"
        init_content = (
            '[dataset]\nname = "test"\nrepo_id = "u/t"\n\n[meta]\ndescription = "scan test"\n'
        )
        config.write_text(init_content, encoding="utf-8")

        monkeypatch.chdir(tmp_path)

        # Simulate CLI args — scan dataset.toml (the default).
        from argparse import Namespace

        args = Namespace(config=str(config), dry_run=False, force=True, ext=None)
        rc = _cmd_scan(args)
        assert rc == 0

        # Parse the resulting TOML.
        cfg = DatasetConfig.from_toml(config)
        assert len(cfg.files) == 2

        # Validate — all files should exist under data/ now.
        errors = cfg.validate()
        assert errors == [], f"Validation errors: {errors}"

    def test_dry_run_no_disk_changes(self, tmp_path: Path, monkeypatch) -> None:
        """dry_run reports but modifies neither TOML nor data/."""
        from sofer.cli import _cmd_scan

        _touch(tmp_path / "a.csv")
        config = tmp_path / "dataset.toml"
        config.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        original_toml = config.read_text(encoding="utf-8")

        monkeypatch.chdir(tmp_path)

        from argparse import Namespace

        args = Namespace(config=str(config), dry_run=True, force=False, ext=None)
        rc = _cmd_scan(args)
        assert rc == 0

        # TOML unchanged.
        assert config.read_text(encoding="utf-8") == original_toml
        # data/ never created.
        assert not (tmp_path / "data").exists()

    def test_idempotent_scan(self, tmp_path: Path, monkeypatch) -> None:
        """Running scan twice with same files produces identical TOML [[file]] count."""
        from sofer.cli import _cmd_scan

        _touch(tmp_path / "a.csv")
        config = tmp_path / "dataset.toml"
        config.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        from argparse import Namespace

        # First scan.
        args = Namespace(config=str(config), dry_run=False, force=True, ext=None)
        rc = _cmd_scan(args)
        assert rc == 0

        first_cfg = DatasetConfig.from_toml(config)
        first_count = len(first_cfg.files)

        # Second scan — idempotent (use --force since data/ files already exist).
        args2 = Namespace(config=str(config), dry_run=False, force=True, ext=None)
        rc2 = _cmd_scan(args2)
        assert rc2 == 0

        second_cfg = DatasetConfig.from_toml(config)
        assert len(second_cfg.files) == first_count

    def test_missing_config_returns_error(self, tmp_path: Path, monkeypatch) -> None:
        """Calling scan with a nonexistent config returns exit code 1."""
        from sofer.cli import _cmd_scan

        monkeypatch.chdir(tmp_path)
        from argparse import Namespace

        args = Namespace(config="nonexistent.toml", dry_run=False, force=False, ext=None)
        rc = _cmd_scan(args)
        assert rc == 1

    def test_no_supported_files_returns_ok(self, tmp_path: Path, monkeypatch) -> None:
        """Scan on a directory with only unsupported files returns exit code 0."""
        from sofer.cli import _cmd_scan

        (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
        (tmp_path / "readme.md").write_text("# doc", encoding="utf-8")
        config = tmp_path / "dataset.toml"
        config.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        from argparse import Namespace

        args = Namespace(config=str(config), dry_run=False, force=False, ext=None)
        rc = _cmd_scan(args)
        assert rc == 0

    def test_malformed_toml_returns_error(self, tmp_path: Path, monkeypatch) -> None:
        """Scan with a syntactically invalid TOML returns exit code 1."""
        from sofer.cli import _cmd_scan

        config = tmp_path / "dataset.toml"
        config.write_text("this is not valid [[[[ toml", encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        from argparse import Namespace

        args = Namespace(config=str(config), dry_run=False, force=False, ext=None)
        rc = _cmd_scan(args)
        assert rc == 1

    def test_confirmation_yes_proceeds(self, tmp_path: Path, monkeypatch) -> None:
        """Prompting 'y' proceeds with copy."""
        from sofer.cli import _cmd_scan

        _touch(tmp_path / "a.csv")
        config = tmp_path / "dataset.toml"
        config.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        monkeypatch.setattr("builtins.input", lambda _prompt="": "y")
        from argparse import Namespace

        args = Namespace(config=str(config), dry_run=False, force=False, ext=None)
        rc = _cmd_scan(args)
        assert rc == 0
        assert (tmp_path / "data" / "a.csv").exists()

    def test_confirmation_no_aborts(self, tmp_path: Path, monkeypatch) -> None:
        """Prompting 'n' aborts without copying."""
        from sofer.cli import _cmd_scan

        _touch(tmp_path / "a.csv")
        config = tmp_path / "dataset.toml"
        config.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        monkeypatch.setattr("builtins.input", lambda _prompt="": "n")
        from argparse import Namespace

        args = Namespace(config=str(config), dry_run=False, force=False, ext=None)
        rc = _cmd_scan(args)
        assert rc == 0
        assert not (tmp_path / "data").exists()
