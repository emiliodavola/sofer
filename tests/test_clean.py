"""Tests for sofer._clean — allowlist and orphan pruning (PUB-11 / PRP-09).

Covers ``allowed_output_remotes`` recognising single-underscore
``DATA_GOT_ALL`` sheets and ``prune_orphans`` deleting stale orphans
while retaining compliance / keep_csv files, plus idempotency and
``clean_build`` / ``clean_cache`` anchoring.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from sofer._clean import allowed_output_remotes, clean_build, clean_cache, prune_orphans
from sofer.model import DatasetConfig, FileEntry


def _cfg(tmp_path: Path, files: list[FileEntry], **kw: Any) -> DatasetConfig:
    """Build a minimal DatasetConfig rooted at tmp_path."""
    return DatasetConfig(
        name="test",
        repo_id="user/test",
        files=files,
        _base_dir=tmp_path,
        **kw,
    )


def _make_xlsx(path: Path, sheets: dict[str, list[list[object]]]) -> None:
    """Create an XLSX at *path* with *sheets* mapping sheet->rows (header first)."""
    import openpyxl

    wb = openpyxl.Workbook()
    first = True
    for name, rows in sheets.items():
        if first:
            ws = wb.active
            assert ws is not None
            ws.title = name
            first = False
        else:
            ws = wb.create_sheet(title=name)
        for row in rows:
            ws.append(row)
    wb.save(path)


class TestAllowedOutputRemotes:
    """allowed_output_remotes: single-underscore sheets are recognised as owned."""

    def test_single_underscore_data_got_all_sheets_in_allowlist(self, tmp_path: Path) -> None:
        """DATA_GOT_ALL.xlsx → data_got_all_aristas/nodos are allowed, not orphans."""
        xlsx = tmp_path / "DATA_GOT_ALL.xlsx"
        _make_xlsx(
            xlsx,
            {
                "aristas": [["id", "src"], [1, "a"]],
                "nodos": [["id", "label"], [1, "n"]],
            },
        )
        cfg = _cfg(tmp_path, [FileEntry(local=xlsx, remote="DATA_GOT_ALL.xlsx")])
        out = tmp_path / "build"
        # Simulate prepare output: single-underscore normalized layout
        out.mkdir()
        pq.write_table(pa.table({"id": [1]}), out / "data_got_all_aristas.parquet")
        pq.write_table(pa.table({"id": [1]}), out / "data_got_all_nodos.parquet")

        allowed = allowed_output_remotes(cfg, keep_csv=False, output_dir=out)
        assert "data_got_all_aristas.parquet" in allowed
        assert "data_got_all_nodos.parquet" in allowed

    def test_compliance_files_in_allowlist(self, tmp_path: Path) -> None:
        """README.md, LICENSE, codebook.md are always allowed."""
        csv = tmp_path / "a.csv"
        csv.write_text("x\n1\n", encoding="utf-8")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="a.csv")])
        out = tmp_path / "build"
        out.mkdir()
        allowed = allowed_output_remotes(cfg, keep_csv=False, output_dir=out)
        assert "readme.md" in allowed
        assert "license" in allowed
        assert "codebook.md" in allowed

    def test_keep_csv_adds_csv_remote(self, tmp_path: Path) -> None:
        """With keep_csv=True the original CSV remote is allowed."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"
        out.mkdir()
        pq.write_table(pa.table({"a": [1]}), out / "data.parquet")
        allowed_no = allowed_output_remotes(cfg, keep_csv=False, output_dir=out)
        allowed_yes = allowed_output_remotes(cfg, keep_csv=True, output_dir=out)
        assert "data.csv" not in allowed_no
        assert "data.csv" in allowed_yes
        assert "data.parquet" in allowed_yes


class TestPruneOrphans:
    """prune_orphans: deletes stale, retains compliance / keep_csv / single-_, idempotent."""

    def test_deletes_stale_file(self, tmp_path: Path) -> None:
        """A stale .parquet not in allowlist is removed."""
        csv = tmp_path / "keep.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="keep.csv")])
        out = tmp_path / "build"
        out.mkdir()
        # Owned file
        pq.write_table(pa.table({"x": [1]}), out / "keep.parquet")
        # Orphan
        pq.write_table(pa.table({"y": [1]}), out / "stale.parquet")
        allowed = allowed_output_remotes(cfg, keep_csv=False, output_dir=out)
        removed = prune_orphans(out, allowed)
        assert (out / "stale.parquet").exists() is False
        assert (out / "keep.parquet").exists() is True
        assert len(removed) == 1

    def test_retains_compliance_and_codebooks(self, tmp_path: Path) -> None:
        """README, LICENSE, codebook.md, codebooks/** survive pruning."""
        csv = tmp_path / "a.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="a.csv")])
        out = tmp_path / "build"
        out.mkdir()
        pq.write_table(pa.table({"x": [1]}), out / "a.parquet")
        (out / "README.md").write_text("# card", encoding="utf-8")
        (out / "LICENSE").write_text("MIT", encoding="utf-8")
        (out / "codebook.md").write_text("# index", encoding="utf-8")
        codebooks_dir = out / "codebooks"
        codebooks_dir.mkdir()
        (codebooks_dir / "a.md").write_text("# cb", encoding="utf-8")
        allowed = allowed_output_remotes(cfg, keep_csv=False, output_dir=out)
        removed = prune_orphans(out, allowed)
        assert (out / "README.md").exists()
        assert (out / "LICENSE").exists()
        assert (out / "codebook.md").exists()
        assert (out / "codebooks" / "a.md").exists()
        assert removed == []

    def test_retains_keep_csv_original(self, tmp_path: Path) -> None:
        """With keep_csv=True the CSV original (data/foo.csv) is not an orphan."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data/foo.csv")])
        out = tmp_path / "build"
        out.mkdir(parents=True)
        (out / "data").mkdir(parents=True, exist_ok=True)
        # Ensure built layout: data/foo.parquet vs data/foo.csv
        # Use expanded layout: remote data/foo.csv -> data/foo.parquet normalized
        if (out / "foo.parquet").exists():
            (out / "foo.parquet").unlink()
        pq.write_table(pa.table({"a": [1]}), out / "data" / "foo.parquet")
        (out / "data" / "foo.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        allowed = allowed_output_remotes(cfg, keep_csv=True, output_dir=out)
        removed = prune_orphans(out, allowed)
        assert (out / "data" / "foo.csv").exists()
        assert removed == []

    def test_single_underscore_orphan_pruning(self, tmp_path: Path) -> None:
        """An orphan data_got_all_* file is removed; owned sheets are kept."""
        xlsx = tmp_path / "DATA_GOT_ALL.xlsx"
        _make_xlsx(xlsx, {"aristas": [["id"], [1]]})
        _cfg(tmp_path, [FileEntry(local=xlsx, remote="DATA_GOT_ALL.xlsx")])
        out = tmp_path / "build"
        out.mkdir()
        pq.write_table(pa.table({"id": [1]}), out / "data_got_all_aristas.parquet")
        pq.write_table(pa.table({"id": [1]}), out / "data_got_all_nodos.parquet")
        # Reproduce stale TOML entry case: old remote removed
        cfg2 = _cfg(tmp_path, [FileEntry(local=tmp_path / "keep.csv", remote="keep.csv")])
        (tmp_path / "keep.csv").write_text("x\n1\n", encoding="utf-8")
        out2 = tmp_path / "build2"
        out2.mkdir()
        pq.write_table(pa.table({"x": [1]}), out2 / "keep.parquet")
        pq.write_table(pa.table({"y": [1]}), out2 / "old.parquet")
        allowed2 = allowed_output_remotes(cfg2, keep_csv=False, output_dir=out2)
        removed2 = prune_orphans(out2, allowed2)
        assert (out2 / "old.parquet").exists() is False
        assert (out2 / "keep.parquet").exists() is True
        assert len(removed2) == 1

    def test_idempotent_second_run(self, tmp_path: Path) -> None:
        """A second prune with same allowlist deletes nothing (idempotent)."""
        csv = tmp_path / "a.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="a.csv")])
        out = tmp_path / "build"
        out.mkdir()
        pq.write_table(pa.table({"x": [1]}), out / "a.parquet")
        (out / "stale.parquet").write_text("x", encoding="utf-8")
        allowed = allowed_output_remotes(cfg, keep_csv=False, output_dir=out)
        first = prune_orphans(out, allowed)
        assert len(first) == 1
        second = prune_orphans(out, allowed)
        assert second == []

    def test_logs_absolute_paths(self, tmp_path: Path, capsys) -> None:
        """Pruned files are logged with absolute paths."""
        csv = tmp_path / "a.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="a.csv")])
        out = tmp_path / "build"
        out.mkdir()
        pq.write_table(pa.table({"x": [1]}), out / "a.parquet")
        pq.write_table(pa.table({"y": [1]}), out / "stale.parquet")
        allowed = allowed_output_remotes(cfg, keep_csv=False, output_dir=out)
        prune_orphans(out, allowed)
        captured = capsys.readouterr().out
        assert str((out / "stale.parquet").resolve()) in captured


class TestCleanHelpers:
    """clean_build / clean_cache: existence check + anchored deletion."""

    def test_clean_build_removes_resolved_dir(self, tmp_path: Path) -> None:
        """clean_build deletes the resolved build directory."""
        csv = tmp_path / "a.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="a.csv")], build_dir="build")
        out = tmp_path / "build"
        out.mkdir()
        (out / "file.txt").write_text("x", encoding="utf-8")
        clean_build(cfg, None)
        assert not out.exists()

    def test_clean_build_respects_output_override(self, tmp_path: Path) -> None:
        """--output override is honoured; default build stays."""
        csv = tmp_path / "a.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="a.csv")], build_dir="build")
        default_out = tmp_path / "build"
        default_out.mkdir()
        (default_out / "keep.txt").write_text("x", encoding="utf-8")
        override_out = tmp_path / "staging"
        override_out.mkdir()
        (override_out / "file.txt").write_text("x", encoding="utf-8")
        clean_build(cfg, "./staging")
        assert not override_out.exists()
        assert default_out.exists()

    def test_clean_cache_anchored_to_base_dir(self, tmp_path: Path) -> None:
        """clean_cache deletes cache/ anchored to base_dir, not cwd."""
        cache = tmp_path / "cache"
        cache.mkdir()
        (cache / "file.txt").write_text("x", encoding="utf-8")
        clean_cache(tmp_path)
        assert not cache.exists()

    def test_clean_cache_noop_when_missing(self, tmp_path: Path) -> None:
        """Missing cache/ is a no-op (no exception)."""
        clean_cache(tmp_path)  # should not raise
        assert not (tmp_path / "cache").exists()

    def test_clean_build_noop_when_missing(self, tmp_path: Path) -> None:
        """Missing build is a no-op."""
        csv = tmp_path / "a.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="a.csv")])
        clean_build(cfg, None)  # should not raise
