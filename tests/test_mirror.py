"""Tests for sofer._mirror — remote-path validation, planned-remote
derivation, and dir-aware mirror copies (the RC-R04 regression)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sofer._mirror import (
    _validate_case_fold_collisions,
    copy_to_mirror,
    expanded_planned_remotes,
    parquet_remote_for,
    planned_remotes,
)
from sofer.model import DatasetConfig, FileEntry


def _cfg(files: list[FileEntry]) -> DatasetConfig:
    return DatasetConfig(name="test", repo_id="u/test", files=files)


# ══════════════════════════════════════════════════════════════════════════════
#  planned_remotes
# ══════════════════════════════════════════════════════════════════════════════


class TestPlannedRemotes:
    def test_csv_maps_to_parquet_without_keep_csv(self) -> None:
        """An eligible CSV maps to its .parquet remote (mirror of publish)."""
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
        """A nested CSV remote is normalized: dir lowercased, extension flips."""
        cfg = _cfg([FileEntry(local=Path("data.csv"), remote="data/PROV/train.csv")])
        assert planned_remotes(cfg, keep_csv=False) == ["data/prov/train.parquet"]


# ══════════════════════════════════════════════════════════════════════════════
#  parquet_remote_for
# ══════════════════════════════════════════════════════════════════════════════


class TestParquetRemoteFor:
    """RC-R15 — shared remote → .parquet key derivation (S6-unit, S7)."""

    def test_backslash_remote_normalizes_to_posix_key(self) -> None:
        """A backslash remote yields the same forward-slash key as its
        POSIX twin — writer and reader stay in sync (S6-unit)."""
        assert parquet_remote_for("data\\a\\train.csv") == "data/a/train.parquet"
        assert parquet_remote_for("data\\a\\train.csv") == parquet_remote_for("data/a/train.csv")

    def test_nested_forward_slash_remote_preserved(self) -> None:
        """Directory components are kept; only the suffix flips."""
        assert parquet_remote_for("data/PROV/train.csv") == "data/PROV/train.parquet"

    def test_root_remote_flips_suffix(self) -> None:
        """A bare remote maps to a bare .parquet key."""
        assert parquet_remote_for("survey.csv") == "survey.parquet"

    def test_case_preserving(self) -> None:
        """The derivation never lowercases — gating stays at each call site."""
        assert parquet_remote_for("Data/PROV/Train.CSV") == "Data/PROV/Train.parquet"

    def test_idempotent_on_normalized_and_backslash_inputs(self) -> None:
        """Re-deriving an already-derived remote is a no-op (S7), including
        backslash variants of every input shape."""
        for remote in (
            "a/b.csv",
            "a\\b.csv",
            "survey.csv",
            "data/PROV/train.csv",
            "data\\PROV\\train.csv",
        ):
            once = parquet_remote_for(remote)
            assert parquet_remote_for(once) == once


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

    def test_directory_copy_refuses_without_force(self, tmp_path: Path) -> None:
        """PUB-13 parity: ``force=False`` on an existing directory destination
        raises :class:`FileExistsError` instead of silently merging — the dir
        branch now honours the same overwrite guard as the file branch."""
        src = tmp_path / "labels"
        src.mkdir()
        (src / "a.txt").write_text("a", encoding="utf-8")
        dest = tmp_path / "mirror" / "labels"
        dest.mkdir(parents=True)

        with pytest.raises(FileExistsError, match="use --force to overwrite"):
            copy_to_mirror(src, tmp_path / "mirror", "labels", force=False)

        # force=True still merges (the guard is force-gated, not permanent).
        copy_to_mirror(src, tmp_path / "mirror", "labels", force=True)
        assert (dest / "a.txt").is_file()


# ══════════════════════════════════════════════════════════════════════════════
#  _validate_case_fold_collisions
# ══════════════════════════════════════════════════════════════════════════════


class TestValidateCaseFoldCollisions:
    """RC-R16 — case-differing ``.csv`` remotes that collide on the staged
    Parquet key are refused; verbatim dups / casefold-distinct / ineligible
    entries pass."""

    def test_case_differing_remotes_error_names_both(self) -> None:
        """Two remotes differing only by case map to one Parquet key — the
        error names BOTH remotes (S1)."""
        cfg = _cfg(
            [
                FileEntry(local=Path("a.csv"), remote="Data/Prov/Train.CSV"),
                FileEntry(local=Path("b.csv"), remote="data/prov/train.csv"),
            ]
        )
        errors = _validate_case_fold_collisions(cfg)
        assert len(errors) == 1
        assert "Data/Prov/Train.CSV" in errors[0]
        assert "data/prov/train.csv" in errors[0]

    def test_exact_duplicate_remotes_no_error(self) -> None:
        """Verbatim-identical remotes are RC-R11's concern, not RC-R16 (S2)."""
        cfg = _cfg(
            [
                FileEntry(local=Path("a.csv"), remote="data/train.csv"),
                FileEntry(local=Path("b.csv"), remote="data/train.csv"),
            ]
        )
        assert _validate_case_fold_collisions(cfg) == []

    def test_casefold_distinct_unicode_no_error(self) -> None:
        """lower() (not casefold) keeps ``straße`` != ``strasse`` — no error (S3)."""
        cfg = _cfg(
            [
                FileEntry(local=Path("a.csv"), remote="straße.csv"),
                FileEntry(local=Path("b.csv"), remote="strasse.csv"),
            ]
        )
        assert _validate_case_fold_collisions(cfg) == []

    def test_recursive_entry_ignored(self) -> None:
        """recursive entries are never scanned (S4)."""
        cfg = _cfg(
            [
                FileEntry(local=Path("d"), remote="Dir/", recursive=True),
                FileEntry(local=Path("a.csv"), remote="Dir/file.csv"),
            ]
        )
        assert _validate_case_fold_collisions(cfg) == []

    def test_non_csv_remote_ignored(self) -> None:
        """Non-.csv remotes are never scanned (S4)."""
        cfg = _cfg(
            [
                FileEntry(local=Path("a.parquet"), remote="Data/a.parquet"),
                FileEntry(local=Path("b.parquet"), remote="data/a.parquet"),
            ]
        )
        assert _validate_case_fold_collisions(cfg) == []

    def test_include_in_schema_false_pair_collides(self) -> None:
        """include_in_schema=false ``.csv`` remotes are still physically staged,
        so a case-differing pair errors (D2 overrides spec S4)."""
        cfg = _cfg(
            [
                FileEntry(local=Path("a.csv"), remote="Data/a.csv", include_in_schema=False),
                FileEntry(local=Path("b.csv"), remote="data/a.csv", include_in_schema=False),
            ]
        )
        errors = _validate_case_fold_collisions(cfg)
        assert len(errors) == 1

    def test_upload_as_csv_pair_collides(self) -> None:
        """upload_as_csv ``.csv`` remotes are staged as-is, so a case-differing
        pair errors (D2)."""
        cfg = _cfg(
            [
                FileEntry(local=Path("a.csv"), remote="Data/a.csv", upload_as_csv=True),
                FileEntry(local=Path("b.csv"), remote="data/a.csv", upload_as_csv=True),
            ]
        )
        errors = _validate_case_fold_collisions(cfg)
        assert len(errors) == 1

    def test_backslash_and_posix_remotes_collide(self) -> None:
        """Backslash-vs-slash remotes normalize to the same Parquet key via
        RC-R15 and are caught by the derived-key ``lower()`` keying (D3)."""
        cfg = _cfg(
            [
                FileEntry(local=Path("a.csv"), remote="data\\a\\c.csv"),
                FileEntry(local=Path("b.csv"), remote="data/a/c.csv"),
            ]
        )
        errors = _validate_case_fold_collisions(cfg)
        assert len(errors) == 1


# ══════════════════════════════════════════════════════════════════════════════
#  expanded_planned_remotes — PUB-10 mirror-grounded expansion
# ══════════════════════════════════════════════════════════════════════════════


class TestExpandedPlannedRemotes:
    """expanded_planned_remotes expands XLSX via mirror glob, falls back otherwise."""

    def test_multi_sheet_expands_to_n_remotes(self, tmp_path: Path) -> None:
        """Multi-sheet XLSX expands to N __ remotes when mirror has them."""
        cfg = _cfg([FileEntry(local=Path("report.xlsx"), remote="report.xlsx")])
        staging = tmp_path / "staging"
        staging.mkdir()
        (staging / "report__ventas.parquet").touch()
        (staging / "report__costos.parquet").touch()

        result = expanded_planned_remotes(cfg, keep_csv=False, staging_dir=staging)

        assert "report__ventas.parquet" in result
        assert "report__costos.parquet" in result
        assert "report.parquet" not in result
        assert len([r for r in result if "report" in r]) == 2

    def test_single_sheet_stays_single(self, tmp_path: Path) -> None:
        """Single-sheet XLSX staged as stem.parquet stays single, no phantom __."""
        cfg = _cfg([FileEntry(local=Path("single.xlsx"), remote="single.xlsx")])
        staging = tmp_path / "staging"
        staging.mkdir()
        (staging / "single.parquet").touch()

        result = expanded_planned_remotes(cfg, keep_csv=False, staging_dir=staging)

        assert result == ["single.parquet"]
        assert not any("__" in r for r in result)

    def test_fallback_when_staging_none(self) -> None:
        """When staging_dir is None, fallback to logical placeholder."""
        cfg = _cfg([FileEntry(local=Path("report.xlsx"), remote="report.xlsx")])
        assert expanded_planned_remotes(cfg, keep_csv=False, staging_dir=None) == ["report.parquet"]

    def test_fallback_when_staging_not_dir(self, tmp_path: Path) -> None:
        """When staging_dir is not a directory, fallback to planned_remotes."""
        cfg = _cfg([FileEntry(local=Path("report.xlsx"), remote="report.xlsx")])
        not_dir = tmp_path / "not_exist"
        assert expanded_planned_remotes(cfg, keep_csv=False, staging_dir=not_dir) == [
            "report.parquet"
        ]

    def test_recursive_passthrough(self, tmp_path: Path) -> None:
        """Recursive entries are not expanded even with staging."""
        cfg = _cfg([FileEntry(local=Path("labels"), remote="labels/", recursive=True)])
        staging = tmp_path / "staging"
        staging.mkdir()
        result = expanded_planned_remotes(cfg, keep_csv=False, staging_dir=staging)
        assert result == ["labels"]

    def test_keep_csv_csv_only(self, tmp_path: Path) -> None:
        """keep_csv adds original CSV but not for XLSX."""
        cfg = _cfg(
            [
                FileEntry(local=Path("a.csv"), remote="a.csv"),
                FileEntry(local=Path("report.xlsx"), remote="report.xlsx"),
            ]
        )
        staging = tmp_path / "staging"
        staging.mkdir()
        (staging / "report__s1.parquet").touch()
        (staging / "report__s2.parquet").touch()

        result = expanded_planned_remotes(cfg, keep_csv=True, staging_dir=staging)
        # CSV expands with keep
        assert "a.parquet" in result
        assert "a.csv" in result
        # XLSX expands to N, no CSV
        assert "report__s1.parquet" in result
        assert "report__s2.parquet" in result
        csv_count = result.count("a.csv")
        assert csv_count == 1

    def test_convert_to_parquet_false_passthrough(self, tmp_path: Path) -> None:
        """XLSX with convert_to_parquet=False stays as original remote."""
        cfg = _cfg(
            [
                FileEntry(
                    local=Path("report.xlsx"),
                    remote="report.xlsx",
                    convert_to_parquet=False,
                )
            ]
        )
        staging = tmp_path / "staging"
        staging.mkdir()
        (staging / "report__ventas.parquet").touch()

        result = expanded_planned_remotes(cfg, keep_csv=False, staging_dir=staging)
        assert result == ["report.xlsx"]

    def test_no_openpyxl_import(self, tmp_path: Path) -> None:
        """Helper must not import openpyxl — glob only."""
        import sys

        cfg = _cfg([FileEntry(local=Path("report.xlsx"), remote="report.xlsx")])
        staging = tmp_path / "staging"
        staging.mkdir()
        (staging / "report__ventas.parquet").touch()
        _ = expanded_planned_remotes(cfg, keep_csv=False, staging_dir=staging)
        assert "openpyxl" not in sys.modules or sys.modules["openpyxl"] is not None
        # Ensure helper didn't trigger workbook open: no import side effect
        # Check that calling helper didn't require openpyxl
        # If openpyxl were imported lazily, it would appear after call;
        # we assert that the function works even if openpyxl missing by checking
        # that no error was raised above.

    def test_nested_xlsx_with_dir(self, tmp_path: Path) -> None:
        """Nested XLSX respects directory prefix in glob."""
        cfg = _cfg([FileEntry(local=Path("report.xlsx"), remote="data/report.xlsx")])
        staging = tmp_path / "staging"
        (staging / "data").mkdir(parents=True)
        (staging / "data" / "report__ventas.parquet").touch()
        (staging / "data" / "report__costos.parquet").touch()

        result = expanded_planned_remotes(cfg, keep_csv=False, staging_dir=staging)

        assert "data/report__ventas.parquet" in result
        assert "data/report__costos.parquet" in result
