"""Tests for sofer._mirror — remote-path validation, planned-remote
derivation, and dir-aware mirror copies (the RC-R04 regression)."""

from __future__ import annotations

from pathlib import Path

from sofer._mirror import copy_to_mirror, planned_remotes
from sofer.model import DatasetConfig, FileEntry


def _cfg(files: list[FileEntry]) -> DatasetConfig:
    return DatasetConfig(name="test", repo_id="u/test", files=files)


# ══════════════════════════════════════════════════════════════════════════════
#  planned_remotes
# ══════════════════════════════════════════════════════════════════════════════


class TestPlannedRemotes:
    def test_csv_maps_to_parquet_without_keep_csv(self) -> None:
        """An eligible CSV maps to its .parquet remote (mirror of uploader)."""
        cfg = _cfg([FileEntry(local=Path("a.csv"), remote="a.csv")])
        assert planned_remotes(cfg, keep_csv=False) == ["a.parquet"]

    def test_keep_csv_adds_original(self) -> None:
        """keep_csv=True adds the original CSV remote alongside the Parquet."""
        cfg = _cfg([FileEntry(local=Path("a.csv"), remote="a.csv")])
        assert planned_remotes(cfg, keep_csv=True) == ["a.parquet", "a.csv"]

    def test_upload_as_csv_keeps_csv(self) -> None:
        """upload_as_csv entries are never converted — CSV stays."""
        cfg = _cfg([FileEntry(local=Path("a.csv"), remote="a.csv", upload_as_csv=True)])
        assert planned_remotes(cfg, keep_csv=False) == ["a.csv"]
        assert planned_remotes(cfg, keep_csv=True) == ["a.csv"]

    def test_recursive_dir_strips_trailing_slash(self) -> None:
        """A recursive directory resolves to its path without the slash
        (copyable — unlike the ``*`` marker used in the diff summary)."""
        cfg = _cfg([FileEntry(local=Path("labels"), remote="subdir/", recursive=True)])
        assert planned_remotes(cfg, keep_csv=False) == ["subdir"]
        assert planned_remotes(cfg, keep_csv=True) == ["subdir"]

    def test_non_csv_file_passthrough(self) -> None:
        """Non-CSV files keep their remote path unchanged."""
        cfg = _cfg([FileEntry(local=Path("d.parquet"), remote="nested/d.parquet")])
        assert planned_remotes(cfg, keep_csv=False) == ["nested/d.parquet"]

    def test_mixed_entries_preserve_order(self) -> None:
        """Remotes follow cfg.files declaration order; keep_csv only affects
        converted CSV entries."""
        cfg = _cfg(
            [
                FileEntry(local=Path("a.csv"), remote="a.csv"),
                FileEntry(local=Path("labels"), remote="labels/", recursive=True),
                FileEntry(local=Path("b.parquet"), remote="b.parquet"),
            ]
        )
        assert planned_remotes(cfg, keep_csv=False) == ["a.parquet", "labels", "b.parquet"]
        assert planned_remotes(cfg, keep_csv=True) == [
            "a.parquet",
            "a.csv",
            "labels",
            "b.parquet",
        ]

    def test_nested_csv_remote_preserves_dir(self) -> None:
        """A nested CSV remote keeps its directory, only the extension flips."""
        cfg = _cfg([FileEntry(local=Path("data.csv"), remote="data/PROV/train.csv")])
        assert planned_remotes(cfg, keep_csv=False) == ["data/PROV/train.parquet"]


# ══════════════════════════════════════════════════════════════════════════════
#  copy_to_mirror
# ══════════════════════════════════════════════════════════════════════════════


class TestCopyToMirror:
    def test_plain_file_copy(self, tmp_path: Path) -> None:
        """A plain file is copied to dest_root/remote with identical content."""
        src = tmp_path / "a.csv"
        src.write_text("x;y\n1;2\n", encoding="utf-8")

        copy_to_mirror(src, tmp_path / "mirror", "a.csv")

        dest = tmp_path / "mirror" / "a.csv"
        assert dest.is_file()
        assert dest.read_text(encoding="utf-8") == "x;y\n1;2\n"

    def test_nested_file_dest_creates_parents(self, tmp_path: Path) -> None:
        """Parent directories of a nested remote are created on demand."""
        src = tmp_path / "a.csv"
        src.write_text("k\n1\n", encoding="utf-8")

        copy_to_mirror(src, tmp_path / "mirror", "sub/dir/a.csv")

        assert (tmp_path / "mirror" / "sub" / "dir" / "a.csv").is_file()

    def test_directory_copy_recursive_tree(self, tmp_path: Path) -> None:
        """RC-R04: a recursive=true entry stages its whole tree — never
        ``copy2`` on a directory (which raises PermissionError /
        IsADirectoryError)."""
        src = tmp_path / "labels"
        (src / "nested" / "deep").mkdir(parents=True)
        (src / "a.txt").write_text("a", encoding="utf-8")
        (src / "nested" / "b.txt").write_text("b", encoding="utf-8")
        (src / "nested" / "deep" / "c.txt").write_text("c", encoding="utf-8")
        (src / "empty").mkdir()  # empty subdir must be staged too

        copy_to_mirror(src, tmp_path / "mirror", "labels/")

        mirror = tmp_path / "mirror" / "labels"
        assert (mirror / "a.txt").is_file()
        assert (mirror / "nested" / "b.txt").is_file()
        assert (mirror / "nested" / "deep" / "c.txt").is_file()
        assert (mirror / "empty").is_dir()

    def test_directory_copy_merges_into_existing_dest(self, tmp_path: Path) -> None:
        """Copying into an existing destination merges (dirs_exist_ok=True)
        instead of raising FileExistsError."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "f.txt").write_text("x", encoding="utf-8")
        dest = tmp_path / "mirror" / "labels"
        dest.mkdir(parents=True)
        (dest / "existing.txt").write_text("keep", encoding="utf-8")

        copy_to_mirror(src, tmp_path / "mirror", "labels")

        assert (dest / "f.txt").is_file()
        assert (dest / "existing.txt").read_text(encoding="utf-8") == "keep"
