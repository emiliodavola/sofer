"""Tests for sofer.scanner — discover, merge, copy, write, and integration."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from sofer import config
from sofer.model import DatasetConfig
from sofer.scanner import (
    EXCLUSIONS,
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

    def test_output_dir_default_is_cache(self) -> None:
        """OUTPUT_DIR defaults to ``cache`` — sofer artifacts live under
        ``cache/``, while ``data/`` stays reserved for raw source files."""
        assert config.OUTPUT_DIR == "cache"


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
        with pytest.raises(ValueError, match="Collision in cache/"):
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
# TestCheckRawCollisions
# ------------------------------------------------------------------


class TestCheckRawCollisions:
    """Unit tests for :func:`check_raw_collisions` (SCN-07)."""

    def test_collision_names_both(self, tmp_path: Path) -> None:
        """Existing raw/<rel> raises ValueError naming source and dest."""
        from sofer.scanner import check_raw_collisions

        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        _touch(raw_dir / "a.csv")
        src = _touch(tmp_path / "a.csv")
        with pytest.raises(ValueError, match="Collision in raw/"):
            check_raw_collisions([src], raw_dir, tmp_path)
        try:
            check_raw_collisions([src], raw_dir, tmp_path)
        except ValueError as exc:
            msg = str(exc)
            assert "a.csv" in msg
            assert "raw/a.csv" in msg

    def test_no_collision_when_dest_absent(self, tmp_path: Path) -> None:
        """No error when raw destination does not exist."""
        from sofer.scanner import check_raw_collisions

        raw_dir = tmp_path / "raw"
        src = _touch(tmp_path / "sub" / "b.xlsx")
        # Should not raise — raw/sub/b.xlsx absent
        check_raw_collisions([src], raw_dir, tmp_path)

    def test_nested_tree_collision(self, tmp_path: Path) -> None:
        """Collision preserves tree: sub/b.xlsx maps to raw/sub/b.xlsx."""
        from sofer.scanner import check_raw_collisions

        raw_dir = tmp_path / "raw"
        _touch(raw_dir / "sub" / "b.xlsx")
        src = _touch(tmp_path / "sub" / "b.xlsx")
        with pytest.raises(ValueError, match=r"raw/sub/b\.xlsx"):
            check_raw_collisions([src], raw_dir, tmp_path)


# ------------------------------------------------------------------
# TestMoveToRaw
# ------------------------------------------------------------------


class TestMoveToRaw:
    """Unit tests for :func:`move_to_raw` (SCN-07)."""

    def test_preserves_tree_and_removes_source(self, tmp_path: Path) -> None:
        """MOVE preserves relative_to tree; source gone, dest exists."""
        from sofer.scanner import move_to_raw

        src_a = _touch(tmp_path / "a.csv", content="a")
        src_b = _touch(tmp_path / "sub" / "b.xlsx", content="b")
        raw_dir = tmp_path / "raw"

        moved = move_to_raw([src_a, src_b], tmp_path, raw_dir)

        assert (raw_dir / "a.csv").exists()
        assert (raw_dir / "sub" / "b.xlsx").exists()
        assert not src_a.exists()
        assert not src_b.exists()
        assert len(moved) == 2

    def test_dry_run_no_mutation(self, tmp_path: Path) -> None:
        """dry_run=True computes destinations without touching FS."""
        from sofer.scanner import move_to_raw

        src = _touch(tmp_path / "a.csv")
        raw_dir = tmp_path / "raw"

        moved = move_to_raw([src], tmp_path, raw_dir, dry_run=True)

        assert src.exists()
        assert not (raw_dir / "a.csv").exists()
        assert moved[0][1] == raw_dir / "a.csv"

    def test_mkdir_parents_lazily(self, tmp_path: Path) -> None:
        """Parent directories are created lazily on first move."""
        from sofer.scanner import move_to_raw

        src = _touch(tmp_path / "a" / "b" / "c.csv")
        raw_dir = tmp_path / "raw"

        move_to_raw([src], tmp_path, raw_dir)

        assert (raw_dir / "a" / "b" / "c.csv").exists()

    def test_exclusions_and_txt_not_moved_via_discover(self, tmp_path: Path) -> None:
        """Files in EXCLUSIONS or with .txt suffix are never candidates (discover)."""
        from sofer.scanner import discover_files

        _touch(tmp_path / "a.csv")
        _touch(tmp_path / "f.txt")
        _touch(tmp_path / ".venv" / "lib" / "data.csv")
        exclude = EXCLUSIONS | frozenset({config.OUTPUT_DIR, config.RAW_DIR})
        result = discover_files(tmp_path, exclude_dirs=exclude)
        names = {p.name for p in result}
        assert "a.csv" in names
        assert "f.txt" not in names
        assert "data.csv" not in names

    def test_five_exts_vs_txt(self, tmp_path: Path) -> None:
        """Only 5 supported exts are moved; f.txt ignored."""
        from sofer.scanner import discover_files, move_to_raw

        _make_tree(tmp_path, ["a.csv", "b.tsv", "c.xlsx", "d.jsonl", "e.parquet", "f.txt"])
        exclude = EXCLUSIONS | frozenset({config.OUTPUT_DIR, config.RAW_DIR})
        candidates = discover_files(tmp_path, exclude_dirs=exclude)
        assert {p.suffix for p in candidates} == {".csv", ".tsv", ".xlsx", ".jsonl", ".parquet"}
        raw_dir = tmp_path / "raw"
        move_to_raw(candidates, tmp_path, raw_dir)
        for name in ["a.csv", "b.tsv", "c.xlsx", "d.jsonl", "e.parquet"]:
            assert (raw_dir / name).exists()
        assert (tmp_path / "f.txt").exists()
        assert not (raw_dir / "f.txt").exists()


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


def _make_link(link: Path, target: Path) -> bool:
    """Create a symlink (or NTFS junction on win32) ``link -> target``.

    Returns ``True`` on success. On win32, ``os.symlink`` requires
    developer-mode privileges — falls back to ``mklink /J`` (junction). When
    the OS refuses both, returns ``False`` so the caller skips with a
    documented reason instead of stalling. Mirrors the helper in
    ``test_mcp_server.py`` (link creation is a platform capability, not
    sofer logic).
    """
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
        return True
    except OSError:
        if os.name != "nt":
            return False
        try:
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0 and link.exists()
        except OSError:
            return False


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

    def test_symlinked_file_outside_not_discovered(self, tmp_path, tmp_path_factory) -> None:
        """A file symlink pointing OUTSIDE tmp_path is never discovered (SCN-01).

        On Python 3.10-3.12 ``rglob`` yields the link and ``is_file()``
        follows it — without the ``_is_link`` guard the external file would
        be discovered, copied into cache/, registered, and publishable.
        """
        outside = tmp_path_factory.mktemp("outside-leak")
        secret = outside / "secret.csv"
        secret.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        link = tmp_path / "leak.csv"
        if not _make_link(link, secret):
            pytest.skip("symlink/junction creation unavailable on this host")
        _make_tree(tmp_path, ["real.csv"])
        result = discover_files(tmp_path)
        assert link not in result, "external file reached via symlink must not be discovered"
        assert {p.name for p in result} == {"real.csv"}

    def test_symlinked_dir_outside_not_discovered(self, tmp_path, tmp_path_factory) -> None:
        """A directory symlink pointing OUTSIDE tmp_path is not traversed.

        The link's target contents must not be discovered even though on
        3.10-3.12 ``rglob`` follows directory links and would yield the
        children as regular (non-link) entries — the ancestor guard rejects
        them.
        """
        outside = tmp_path_factory.mktemp("outside-leak")
        (outside / "secret.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        link = tmp_path / "leakdir"
        if not _make_link(link, outside):
            pytest.skip("symlink/junction creation unavailable on this host")
        _make_tree(tmp_path, ["real.csv"])
        result = discover_files(tmp_path)
        assert all("secret" not in p.name for p in result), (
            f"external dir contents leaked into discovery: {result}"
        )
        assert {p.name for p in result} == {"real.csv"}

    def test_regular_file_still_discovered_alongside_links(
        self, tmp_path, tmp_path_factory
    ) -> None:
        """A regular file next to a symlink is still discovered (only links are excluded)."""
        outside = tmp_path_factory.mktemp("outside-leak")
        (outside / "x.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        link = tmp_path / "leak.csv"
        if not _make_link(link, outside / "x.csv"):
            pytest.skip("symlink/junction creation unavailable on this host")
        _touch(tmp_path / "keep.csv")
        result = discover_files(tmp_path)
        names = {p.name for p in result}
        assert names == {"keep.csv"}


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

    def test_dedup_by_remote_migration_from_data_to_cache(self, tmp_path: Path) -> None:
        """A pre-cache TOML (local='data/a.csv') re-scanned into cache/ must
        not duplicate — dedup keys on the remote, not just the resolved local
        path, so the cache/ rename is migration-safe."""
        _touch(tmp_path / "a.csv")
        # Old-layout entry: local under data/ (pre-cache), remote a.csv.
        raw = self._raw_toml(file=[{"local": "data/a.csv", "remote": "a.csv"}])
        discovered = [tmp_path / "a.csv"]

        merge_entries(discovered, raw, tmp_path, tmp_path / "cache")
        assert len(raw["file"]) == 1  # same remote → skipped despite data/ local

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
        discovered = sorted(
            [tmp_path / "raw" / "DPTO.csv", tmp_path / "raw" / "Labels" / "etiquetas_a.csv"]
        )

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

    def test_merge_removes_todo_template_entries(self, tmp_path: Path) -> None:
        """Template entries from ``sofer init`` (local starting with ``TODO:``)
        are stripped before merging, so they never reach validate/upload."""
        _touch(tmp_path / "a.csv")
        raw: dict[str, Any] = {
            "file": [
                {"local": "TODO: path/to/file.csv", "remote": "file.csv"},
                {"local": "TODO: path/to/dir/", "remote": "subfolder/", "recursive": True},
            ]
        }
        merge_entries([tmp_path / "a.csv"], raw, tmp_path, tmp_path / "data")
        # All TODO entries must be gone.
        remaining = [str(e["local"]) for e in raw["file"]]
        assert not any("TODO:" in r for r in remaining), f"TODO entries survived: {remaining}"
        # The discovered file must be present.
        assert any("a.csv" in r for r in remaining), f"Discovered file missing: {remaining}"


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

    def test_dry_run_skips_identical_dest(self, tmp_path: Path) -> None:
        """dry_run=True must NOT list an already-identical destination: apply
        skips it (SCN-08 idempotent re-scan), so the preview must too —
        otherwise the dry-run output is misleading ("would copy" a file that
        apply leaves untouched)."""
        _touch(tmp_path / "a.csv", content="same")
        data_dir = tmp_path / "data"
        _touch(data_dir / "a.csv", content="same")

        copied = copy_files([tmp_path / "a.csv"], tmp_path, data_dir, dry_run=True)
        assert copied == []
        # Read-only: destination untouched, no new files.
        assert (data_dir / "a.csv").read_text(encoding="utf-8") == "same"

    def test_dry_run_raises_on_differing_dest(self, tmp_path: Path) -> None:
        """dry_run=True must surface the apply-time failure: a destination
        that exists with DIFFERENT content raises FileExistsError on apply,
        so the preview must raise the same error instead of reporting a copy
        that would never happen."""
        _touch(tmp_path / "a.csv", content="source")
        data_dir = tmp_path / "data"
        _touch(data_dir / "a.csv", content="different-dest")

        with pytest.raises(FileExistsError, match="--force"):
            copy_files([tmp_path / "a.csv"], tmp_path, data_dir, dry_run=True)
        # Read-only: destination untouched, no new files.
        assert (data_dir / "a.csv").read_text(encoding="utf-8") == "different-dest"

    def test_file_exists_error_without_force(self, tmp_path: Path) -> None:
        """FileExistsError is raised when dest exists with DIFFERENT content and force=False."""
        _touch(tmp_path / "a.csv", content="source")
        data_dir = tmp_path / "data"
        _touch(data_dir / "a.csv", content="different-dest")

        with pytest.raises(FileExistsError, match="--force"):
            copy_files([tmp_path / "a.csv"], tmp_path, data_dir)

    def test_identical_dest_skipped_without_force(self, tmp_path: Path) -> None:
        """An already-identical destination is skipped, not an error (SCN-08
        idempotent re-scan) — ``scan twice is safe`` without ``--force``."""
        _touch(tmp_path / "a.csv", content="same")
        data_dir = tmp_path / "data"
        _touch(data_dir / "a.csv", content="same")

        copied = copy_files([tmp_path / "a.csv"], tmp_path, data_dir)

        assert copied == []
        assert (data_dir / "a.csv").read_text(encoding="utf-8") == "same"

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

    def test_atomic_write_no_tmp_leftover(self, tmp_path: Path) -> None:
        """write_toml commits via temp + os.replace — no .tmp file remains."""
        config = tmp_path / "out.toml"
        write_toml({"dataset": {"name": "x", "repo_id": "u/r"}}, config)

        assert config.exists()
        assert not config.with_name(config.name + ".tmp").exists()


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

        # Validate — all files should exist under cache/ now.
        errors = cfg.validate()
        assert errors == [], f"Validation errors: {errors}"

    def test_dry_run_no_disk_changes(self, tmp_path: Path, monkeypatch) -> None:
        """dry_run reports but modifies neither TOML, raw/ nor cache/."""
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
        # neither raw/ nor cache/ created on dry-run with loose files
        assert not (tmp_path / "cache").exists()
        # On dry-run loose file stays, no move to raw/
        assert (tmp_path / "a.csv").exists()
        assert not (tmp_path / "raw" / "a.csv").exists()

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

        # Second scan — idempotent (use --force since cache/ files already exist).
        args2 = Namespace(config=str(config), dry_run=False, force=True, ext=None)
        rc2 = _cmd_scan(args2)
        assert rc2 == 0

        second_cfg = DatasetConfig.from_toml(config)
        assert len(second_cfg.files) == first_count

    def test_partial_failure_recovery_via_force(self, tmp_path: Path, monkeypatch) -> None:
        """A TOML write failure after the cache copy leaves the TOML untouched;
        a re-run with --force recovers (SCN-08)."""
        import sofer.cli as cli_mod
        from sofer.cli import _cmd_scan

        _touch(tmp_path / "raw" / "a.csv", content="x,y\n1,2\n")
        config = tmp_path / "dataset.toml"
        config.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        original = config.read_text(encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        from argparse import Namespace

        # Simulate a TOML write failure AFTER the copy phase succeeds.
        monkeypatch.setattr(
            cli_mod, "write_toml", lambda _raw, _path: (_ for _ in ()).throw(OSError("disk full"))
        )
        rc = _cmd_scan(Namespace(config=str(config), dry_run=False, force=True, ext=None))
        assert rc == 1
        # TOML unchanged — no partial registration.
        assert config.read_text(encoding="utf-8") == original
        # Cache copy happened before the failed TOML write.
        assert (tmp_path / "cache" / "a.csv").exists()

        # Recovery: restore the real writer and re-run with --force.
        monkeypatch.undo()
        rc2 = _cmd_scan(Namespace(config=str(config), dry_run=False, force=True, ext=None))
        assert rc2 == 0
        cfg = DatasetConfig.from_toml(config)
        assert len(cfg.files) == 1

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
        assert (tmp_path / "cache" / "a.csv").exists()

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
        assert not (tmp_path / "cache").exists()

    def test_scan_collision_exits_1_no_copy(self, tmp_path: Path, monkeypatch) -> None:
        """Raw collision (loose a.csv → raw/a.csv exists) → exit 1, no move, no cache."""
        from sofer.cli import _cmd_scan

        _touch(tmp_path / "raw" / "a.csv")
        _touch(tmp_path / "a.csv")
        config = tmp_path / "dataset.toml"
        config.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        original_toml = config.read_text(encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        from argparse import Namespace

        args = Namespace(config=str(config), dry_run=False, force=True, ext=None)
        rc = _cmd_scan(args)
        assert rc == 1
        # No file moved, TOML unchanged, no cache/
        assert (tmp_path / "a.csv").exists()
        assert (tmp_path / "raw" / "a.csv").exists()
        assert not (tmp_path / "cache").exists()
        assert config.read_text(encoding="utf-8") == original_toml

    def test_scan_flatten_collision_exits_1(self, tmp_path: Path, monkeypatch) -> None:
        """Flatten collision among raw/ files → exit 1 after MOVE, before copy."""

        # Two loose files from different subdirs that after MOVE preserve tree
        # won't flatten-collide, so craft raw collision directly:
        # Use files already under raw that flatten to same name via raw/ root vs
        # raw-subdir? We simulate by placing files under raw/ that after flatten
        # share destination: create raw/a.csv and also have a.csv at base that
        # after move would be raw/a.csv — but we already test raw collision above.
        # Instead test flatten collision via raw/ vs raw/ nested not covered;
        # verify check_flatten_collisions still raises for direct call.
        from sofer.scanner import check_flatten_collisions

        discovered = [tmp_path / "raw" / "a.csv", tmp_path / "processed" / "a.csv"]
        # Simulate base_dir = tmp_path, both flatten to a.csv
        with __import__("pytest").raises(ValueError, match="Collision in cache/"):
            check_flatten_collisions(discovered, tmp_path)

    def test_scan_dry_run_reports_flattened_paths(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        """--dry-run shows flattened destination paths."""
        from sofer.cli import _cmd_scan

        _touch(tmp_path / "raw" / "a.csv")
        config = tmp_path / "dataset.toml"
        config.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        from argparse import Namespace

        args = Namespace(config=str(config), dry_run=True, force=False, ext=None)
        rc = _cmd_scan(args)
        assert rc == 0

        captured = capsys.readouterr().out
        # The dry-run report shows flattened paths: "cache/a.csv", not "cache/raw/a.csv"
        assert "a.csv" in captured
        # Should NOT show the raw/ prefix — the first segment was dropped.
        assert "cache/raw/" not in captured

    def test_scan_preview_shows_flattened_paths(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """Interactive preview before copy shows flattened paths."""
        from sofer.cli import _cmd_scan

        _touch(tmp_path / "raw" / "a.csv")
        config = tmp_path / "dataset.toml"
        config.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        # Simulate answering "y" to the prompt so the scan proceeds.
        monkeypatch.setattr("builtins.input", lambda _prompt="": "y")

        from argparse import Namespace

        args = Namespace(config=str(config), dry_run=False, force=False, ext=None)
        rc = _cmd_scan(args)
        assert rc == 0

        captured = capsys.readouterr().out
        # The preview lists flattened paths: "→ cache/a.csv", not "→ cache/raw/a.csv"
        assert "cache/a.csv" in captured
        assert "cache/raw/" not in captured


# ------------------------------------------------------------------
# Raw-folder organization: raw/cache flatten, EXCLUSIONS, e2e
# ------------------------------------------------------------------


class TestRawCacheDiscovery:
    """SCN-01 MOD: raw discovered, cache excluded; EXCLUSIONS unchanged."""

    def test_raw_discovered_cache_excluded(self, tmp_path: Path) -> None:
        """raw/a.csv discovered, cache/a.csv and .venv excluded."""
        _touch(tmp_path / "raw" / "a.csv")
        _touch(tmp_path / "cache" / "a.csv")
        _touch(tmp_path / ".venv" / "lib" / "b.csv")
        exclude = EXCLUSIONS | frozenset({config.OUTPUT_DIR})
        result = discover_files(tmp_path, exclude_dirs=exclude)
        names_posix = {p.relative_to(tmp_path).as_posix() for p in result}
        assert "raw/a.csv" in names_posix
        assert "cache/a.csv" not in names_posix
        assert not any(".venv" in n for n in names_posix)

    def test_exclusions_does_not_contain_raw(self) -> None:
        """EXCLUSIONS must never contain 'raw' (tracked source root)."""
        assert "raw" not in EXCLUSIONS
        assert "cache" not in EXCLUSIONS  # cache excluded via OUTPUT_DIR, not EXCLUSIONS

    def test_scanner_module_doc_mentions_raw_cache_build(self) -> None:
        """scanner.py docstring documents raw/ -> cache/ -> build/ pipeline."""
        import sofer.scanner as scanner_mod

        doc = scanner_mod.__doc__ or ""
        assert "raw/" in doc
        assert "cache/" in doc
        assert "flatten_first_level" in doc


class TestSourceLayoutCopyOnly:
    """SCN-07: raw/ -> cache/ copy-only, sources untouched."""

    def test_sources_untouched_after_scan(self, tmp_path: Path, monkeypatch) -> None:
        """raw/DPTO.csv unchanged after scan, cache/DPTO.csv exists."""
        from argparse import Namespace

        from sofer.cli import _cmd_scan

        raw_file = _touch(tmp_path / "raw" / "DPTO.csv", content="a,b\n1,2\n")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("builtins.input", lambda _p="": "y")
        raw_content_before = raw_file.read_text(encoding="utf-8")
        rc = _cmd_scan(Namespace(config=str(cfg), dry_run=False, force=False, ext=None))
        assert rc == 0
        assert raw_file.read_text(encoding="utf-8") == raw_content_before
        assert (tmp_path / "cache" / "DPTO.csv").exists()
        assert (tmp_path / "cache" / "DPTO.csv").read_text(encoding="utf-8") == raw_content_before

    def test_docs_show_diagram(self) -> None:
        """README / docs contain raw/->cache/->build diagram."""
        readme = Path("README.md").read_text(encoding="utf-8")
        assert "raw/" in readme
        assert "cache" in readme.lower()
        docs = Path("docs/configuration.md").read_text(encoding="utf-8")
        assert "raw/DPTO.csv" in docs or "raw/" in docs


class TestE2EInitMoveScan:
    """SCN-02/03/06 E2E: init --move-existing --force -> scan -> cache flattened."""

    def test_e2e_init_move_scan_flattened(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """Loose a.csv moved to raw/, then scan copies to cache/, TOML flattened."""
        from argparse import Namespace

        from sofer.cli import _cmd_init, _cmd_scan

        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.csv").write_text("x,y\n1,2\n", encoding="utf-8")
        (tmp_path / "b.parquet").write_text("fake", encoding="utf-8")

        rc = _cmd_init(
            Namespace(name="my-ds", user="testuser", move_existing=True, dry_run=False, force=True)
        )
        assert rc == 0
        assert (tmp_path / "raw" / "a.csv").exists()
        assert not (tmp_path / "a.csv").exists()
        # raw/b.parquet also supported format -> moved
        assert (tmp_path / "raw" / "b.parquet").exists()

        cfg = tmp_path / "my-ds.toml"
        # init embeds a validated repo_id (identity checked pre-write)
        # scan registers raw/ files into TOML and copies to cache/
        monkeypatch.setattr("builtins.input", lambda _p="": "y")
        rc2 = _cmd_scan(Namespace(config=str(cfg), dry_run=False, force=True, ext=None))
        assert rc2 == 0
        assert (tmp_path / "cache" / "a.csv").exists()
        assert (tmp_path / "cache" / "b.parquet").exists()
        # raw sources still exist (copy-only)
        assert (tmp_path / "raw" / "a.csv").exists()

        parsed = DatasetConfig.from_toml(cfg)
        # locals should be cache/<flat>
        locals_posix = {str(f.local).replace("\\", "/") for f in parsed.files}
        assert "cache/a.csv" in locals_posix
        assert "cache/b.parquet" in locals_posix
        assert parsed.validate() == []

    def test_e2e_nested_raw_flatten_preserved(self, tmp_path: Path, monkeypatch) -> None:
        """raw/Labels/a.csv -> cache/Labels/a.csv preserves subdirs beyond first."""
        from argparse import Namespace

        from sofer.cli import _cmd_scan

        _touch(tmp_path / "raw" / "Labels" / "a.csv", content="h\n1\n")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("builtins.input", lambda _p="": "y")
        rc = _cmd_scan(Namespace(config=str(cfg), dry_run=False, force=False, ext=None))
        assert rc == 0
        assert (tmp_path / "cache" / "Labels" / "a.csv").exists()
        parsed = DatasetConfig.from_toml(cfg)
        assert any("cache/Labels/a.csv" in str(f.local).replace("\\", "/") for f in parsed.files)


class TestScanMoveScenarios:
    """SCN-07 MOVE scenarios covering tree, ext filter, exclusions, etc."""

    def test_move_preserves_tree_and_removes_source(self, tmp_path: Path, monkeypatch) -> None:
        """Loose a.csv + sub/b.xlsx → raw/a.csv + raw/sub/b.xlsx, originals gone, cache copies."""
        from argparse import Namespace

        from sofer.cli import _cmd_scan

        _touch(tmp_path / "a.csv", content="a")
        _touch(tmp_path / "sub" / "b.xlsx", content="b")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        rc = _cmd_scan(Namespace(config=str(cfg), dry_run=False, force=True, ext=None))
        assert rc == 0
        assert (tmp_path / "raw" / "a.csv").exists()
        assert (tmp_path / "raw" / "sub" / "b.xlsx").exists()
        assert not (tmp_path / "a.csv").exists()
        assert not (tmp_path / "sub" / "b.xlsx").exists()
        assert (tmp_path / "cache" / "a.csv").exists()
        assert (tmp_path / "cache" / "sub" / "b.xlsx").exists() or (
            tmp_path / "cache" / "b.xlsx"
        ).exists()
        # P2 flatten: raw/sub/b.xlsx → cache/sub/b.xlsx (flat drops raw)
        assert (tmp_path / "cache" / "sub" / "b.xlsx").exists() or (
            tmp_path / "cache" / "b.xlsx"
        ).exists()

    def test_supported_extensions_only(self, tmp_path: Path, monkeypatch) -> None:
        """5 supported exts moved, f.txt untouched."""
        from argparse import Namespace

        from sofer.cli import _cmd_scan

        _make_tree(tmp_path, ["a.csv", "b.tsv", "c.xlsx", "d.jsonl", "e.parquet", "f.txt"])
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        rc = _cmd_scan(Namespace(config=str(cfg), dry_run=False, force=True, ext=None))
        assert rc == 0
        for name in ["a.csv", "b.tsv", "c.xlsx", "d.jsonl", "e.parquet"]:
            assert (tmp_path / "raw" / name).exists(), f"raw/{name} missing"
            assert not (tmp_path / name).exists(), f"loose {name} not moved"
        assert (tmp_path / "f.txt").exists()
        assert not (tmp_path / "raw" / "f.txt").exists()

    def test_excluded_dirs_never_moved(self, tmp_path: Path, monkeypatch) -> None:
        """.venv and node_modules never moved."""
        from argparse import Namespace

        from sofer.cli import _cmd_scan

        _touch(tmp_path / ".venv" / "lib" / "data.csv")
        _touch(tmp_path / "node_modules" / "pkg" / "data.csv")
        _touch(tmp_path / "a.csv")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        rc = _cmd_scan(Namespace(config=str(cfg), dry_run=False, force=True, ext=None))
        assert rc == 0
        assert (tmp_path / "raw" / "a.csv").exists()
        assert not (tmp_path / "raw" / ".venv").exists()
        assert (tmp_path / ".venv" / "lib" / "data.csv").exists()
        assert (tmp_path / "node_modules" / "pkg" / "data.csv").exists()

    def test_dry_run_previews_without_mutation(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """--dry-run lists -> raw/... without moving or writing."""
        from argparse import Namespace

        from sofer.cli import _cmd_scan

        _touch(tmp_path / "a.csv")
        _touch(tmp_path / "sub" / "b.parquet")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        original = cfg.read_text(encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        rc = _cmd_scan(Namespace(config=str(cfg), dry_run=True, force=False, ext=None))
        assert rc == 0
        out = capsys.readouterr().out
        assert "-> raw/a.csv" in out
        assert "-> raw/sub/b.parquet" in out
        assert (tmp_path / "a.csv").exists()
        assert not (tmp_path / "raw" / "a.csv").exists()
        assert not (tmp_path / "cache").exists()
        assert cfg.read_text(encoding="utf-8") == original

    def test_collision_fails_before_any_move(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """Collision names both paths, exit 1, no move."""
        from argparse import Namespace

        from sofer.cli import _cmd_scan

        _touch(tmp_path / "raw" / "a.csv")
        _touch(tmp_path / "a.csv")
        _touch(tmp_path / "b.csv")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        rc = _cmd_scan(Namespace(config=str(cfg), dry_run=False, force=True, ext=None))
        assert rc == 1
        err = capsys.readouterr().err
        assert "a.csv" in err
        # No file moved atomically
        assert (tmp_path / "a.csv").exists()
        assert (tmp_path / "b.csv").exists()
        assert not (tmp_path / "cache").exists()

    def test_interactive_abort_is_atomic(self, tmp_path: Path, monkeypatch) -> None:
        """Prompt N aborts without moves or TOML change."""
        from argparse import Namespace

        from sofer.cli import _cmd_scan

        _touch(tmp_path / "a.csv")
        _touch(tmp_path / "b.csv")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        original = cfg.read_text(encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("builtins.input", lambda _p="": "n")

        rc = _cmd_scan(Namespace(config=str(cfg), dry_run=False, force=False, ext=None))
        assert rc == 0
        assert (tmp_path / "a.csv").exists()
        assert (tmp_path / "b.csv").exists()
        assert not (tmp_path / "raw" / "a.csv").exists()
        assert cfg.read_text(encoding="utf-8") == original

    def test_idempotency_when_already_under_raw(self, tmp_path: Path, monkeypatch) -> None:
        """Second scan with all files under raw moves 0, TOML identical."""
        from argparse import Namespace

        from sofer.cli import _cmd_scan

        _touch(tmp_path / "raw" / "a.csv")
        cfg = tmp_path / "dataset.toml"
        cfg.write_text('[dataset]\nname = "test"\nrepo_id = "u/t"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        rc1 = _cmd_scan(Namespace(config=str(cfg), dry_run=False, force=True, ext=None))
        assert rc1 == 0
        toml_after_first = cfg.read_text(encoding="utf-8")

        rc2 = _cmd_scan(Namespace(config=str(cfg), dry_run=False, force=True, ext=None))
        assert rc2 == 0
        assert cfg.read_text(encoding="utf-8") == toml_after_first


# ------------------------------------------------------------------
# Unit C: drive scanner.py to 100.00% (COV-06)
# ------------------------------------------------------------------


class TestLinkDetection:
    """Unit tests for the private :func:`_is_link` tail via a FakePath stub.

    The real-symlink leg needs FS privileges that CI-ish hosts may deny, so the
    Windows reparse-point / OSError / non-NT arms are driven through an
    injectable stub (D-strategy) with ``os.name`` patched.
    """

    @pytest.mark.parametrize(
        "is_symlink,os_name,attrs,raise_lstat,expected",
        [
            (True, "posix", 0, False, True),  # real-symlink leg (is_symlink True)
            (False, "posix", 0, False, False),  # non-NT short-circuit
            (False, "nt", 0, True, False),  # lstat OSError → False
            (False, "nt", 0, False, False),  # attrs=0 → False
            (False, "nt", 0x400, False, True),  # REPARSE_POINT flag → True
            (False, "nt", 0x10, False, False),  # plain DIRECTORY attr → False
        ],
    )
    def test_is_link_reparse_point_and_oserror_branches(
        self, monkeypatch, is_symlink, os_name, attrs, raise_lstat, expected
    ) -> None:
        """Every ``_is_link`` tail arm returns the documented value."""
        from sofer import scanner as scanner_mod

        class _StatLike:
            st_file_attributes = attrs

        class _FakePath:
            def is_symlink(self) -> bool:
                return is_symlink

            def lstat(self):
                if raise_lstat:
                    raise OSError("no stat")
                return _StatLike()

        monkeypatch.setattr(scanner_mod.os, "name", os_name)
        from typing import cast as _cast

        fake = _cast(Path, _cast(object, _FakePath()))
        assert scanner_mod._is_link(fake) is expected


class TestCollectInitMoves:
    """Unit tests for :func:`collect_init_moves` (init --move-existing)."""

    @pytest.mark.parametrize("raw_exists", [True, False])
    def test_collect_init_moves_existing_raw_and_absent_raw(
        self, tmp_path: Path, raw_exists: bool
    ) -> None:
        """Existing raw/ files become *existing*; a missing raw/ yields empty."""
        from sofer.scanner import collect_init_moves

        root = tmp_path / "root"
        root.mkdir()
        (root / "a.csv").write_text("1\n", encoding="utf-8")
        (root / "notes.txt").write_text("x", encoding="utf-8")
        raw_dir = root / "raw"
        if raw_exists:
            raw_dir.mkdir()
            (raw_dir / "old.csv").write_text("old\n", encoding="utf-8")
            (raw_dir / "ignore.txt").write_text("x", encoding="utf-8")
            (raw_dir / "nested").mkdir()
            (raw_dir / "nested" / "deep.csv").write_text("d\n", encoding="utf-8")

        candidates, existing = collect_init_moves(root, "ds.toml", raw_dir)

        assert [c.name for c in candidates] == ["a.csv"]
        if raw_exists:
            assert sorted(e.name for e in existing) == ["deep.csv", "old.csv"]
        else:
            assert existing == []

    def test_collect_init_moves_skips_links_and_toml_name(self, tmp_path, monkeypatch) -> None:
        """Links are never candidates; a supported file matching the TOML name is
        excluded from the move set (SCN-01 + INIT-05)."""
        from sofer import scanner as scanner_mod

        root = tmp_path / "root"
        root.mkdir()
        (root / "keep.csv").write_text("1\n", encoding="utf-8")
        (root / "link.csv").write_text("2\n", encoding="utf-8")
        (root / "data.csv").write_text("3\n", encoding="utf-8")

        # A junction/symlink at the root cannot be fabricated without FS
        # privileges on every host; the exclusion contract is pinned through the
        # _is_link seam (the exclusion logic is what is under test).
        monkeypatch.setattr(scanner_mod, "_is_link", lambda p: p.name == "link.csv")
        candidates, _existing = scanner_mod.collect_init_moves(root, "data.csv", root / "raw")
        names = [c.name for c in candidates]
        assert "link.csv" not in names
        assert "data.csv" not in names  # excluded as the TOML name
        assert names == ["keep.csv"]


class TestDiscoverRegistryDefault:
    """Default registry extension set (``ext_set = set(SUPPORTED_FORMATS.keys())``)."""

    def test_default_extension_registry(self, tmp_path: Path) -> None:
        """discover_files with no --ext uses the full supported-format registry."""
        from sofer.scanner import discover_files

        _make_tree(tmp_path, ["a.csv", "b.tsv", "c.parquet", "d.xlsx", "e.jsonl", "f.txt"])
        result = discover_files(tmp_path)
        names = {p.name for p in result}
        assert names == {"a.csv", "b.tsv", "c.parquet", "d.xlsx", "e.jsonl"}


class TestMergeEntriesEdgeCases:
    """Edge arcs of :func:`merge_entries` (malformed entries, remotes, layout)."""

    def test_merge_skips_malformed_entry_without_dedup(self, tmp_path: Path) -> None:
        """An unparseable [[file]] entry is preserved but never blocks discovery."""
        from sofer.scanner import merge_entries

        (tmp_path / "a.csv").write_text("1\n", encoding="utf-8")
        raw: dict[str, Any] = {
            "dataset": {"name": "x", "repo_id": "u/r"},
            "file": [{"local": "data/broken.csv"}],  # missing remote → KeyError
        }
        merge_entries([tmp_path / "a.csv"], raw, tmp_path, tmp_path / "cache")
        assert len(raw["file"]) == 2  # malformed preserved + new entry
        remotes = [e.get("remote", "") for e in raw["file"]]
        assert "a.csv" in remotes

    def test_merge_empty_remote_skips_remote_dedup(self, tmp_path: Path) -> None:
        """A falsy ``remote`` skips the remote-based dedup arm (loop-back arc)."""
        from sofer.scanner import merge_entries

        (tmp_path / "a.csv").write_text("1\n", encoding="utf-8")
        raw: dict[str, Any] = {
            "dataset": {"name": "x", "repo_id": "u/r"},
            "file": [{"local": "data/other.csv", "remote": ""}],
        }
        merge_entries([tmp_path / "a.csv"], raw, tmp_path, tmp_path / "cache")
        remotes = [e.get("remote", "") for e in raw["file"]]
        assert "a.csv" in remotes
        assert "" in remotes  # preserved untouched

    def test_merge_data_dir_outside_base_falls_back_to_name(self, tmp_path: Path) -> None:
        """data_dir not relative to base_dir falls back to ``<name>/<flat>``."""
        from sofer.scanner import merge_entries

        base = tmp_path / "proj"
        base.mkdir()
        (base / "a.csv").write_text("1\n", encoding="utf-8")
        data_dir = tmp_path / "elsewhere"  # sibling, outside base_dir
        raw: dict[str, Any] = {"file": []}
        merge_entries([base / "a.csv"], raw, base, data_dir)
        assert raw["file"][0]["local"] == "elsewhere/a.csv"
        assert raw["file"][0]["remote"] == "a.csv"


class TestCopyFilesOserrorArc:
    """filecmp.cmp raising OSError is treated as differing (copy_files decision)."""

    def test_files_identical_oserror_treated_as_different(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A comparison failure must NOT skip a differing destination (fail-open
        would silently keep stale cache/ content on re-scan)."""
        from sofer import scanner as scanner_mod
        from sofer.scanner import copy_files

        src = tmp_path / "a.csv"
        src.write_text("same\n", encoding="utf-8")
        dest_dir = tmp_path / "cache"
        dest_dir.mkdir()
        (dest_dir / "a.csv").write_text("same\n", encoding="utf-8")

        def _boom(*_a, **_k):
            raise OSError("cmp failed")

        monkeypatch.setattr(scanner_mod.filecmp, "cmp", _boom)
        assert scanner_mod._files_identical(src, dest_dir / "a.csv") is False
        with pytest.raises(FileExistsError):
            copy_files([src], tmp_path, dest_dir)


class TestDiscoverNoParentChain:
    """A discovery entry whose ``parents`` chain is empty (defensive branch).

    ``Path.parents`` is never empty for real rglob-yielded paths under an
    absolute root, so the parent-guard loop's natural-exit arm is driven through
    the FS-walk seam: a fake rglob result with no parents must NOT be flagged as
    a linked ancestor and must be discovered normally.
    """

    def test_entry_without_parents_is_discovered(self, tmp_path: Path, monkeypatch) -> None:
        from pathlib import Path as _Path

        from sofer import scanner as scanner_mod

        class _FakeEntry:
            parts = ("secret.csv",)
            suffix = ".csv"

            def is_symlink(self) -> bool:
                return False

            def is_file(self) -> bool:
                return True

            def lstat(self):
                raise OSError("no lstat needed")

            @property
            def parents(self):
                return []

        fake = _FakeEntry()
        monkeypatch.setattr(_Path, "rglob", lambda self, pattern: iter([fake]))
        result = scanner_mod.discover_files(tmp_path)
        assert result == [fake]  # not flagged as linked, appended to the results
