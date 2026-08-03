"""Tests for sofer.checks — data integrity verification."""

import csv
from pathlib import Path

from sofer.checks import DatasetValidator
from sofer.model import ColumnCheck, DatasetConfig, FileEntry


def _make_csv(path: Path, rows: list[list[str]], delimiter: str = ";") -> Path:
    """Write a small CSV for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerows(rows)
    return path


# ── File existence ────────────────────────────────────────────────────────────


def test_all_files_exist(tmp_path):
    """When all declared files exist, there should be zero errors."""
    (tmp_path / "data.csv").touch()
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / "data.csv", remote="data.csv")],
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert report.passed
    assert len(report.errors) == 0


def test_missing_file_reported(tmp_path):
    """A missing file should produce exactly one error."""
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / "ghost.csv", remote="ghost.csv")],
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert not report.passed
    assert any("ghost.csv" in e for e in report.errors)


def test_missing_directory_reported(tmp_path):
    """A missing recursive directory should produce an error."""
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / "labels", remote="labels/", recursive=True)],
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert not report.passed
    assert any("labels" in e for e in report.errors)


# ── Minimum file count ────────────────────────────────────────────────────────


def test_below_min_files(tmp_path):
    """Declaring fewer files than min_files should fail."""
    (tmp_path / "a.csv").touch()
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / "a.csv", remote="a.csv")],
        min_files=5,
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert not report.passed
    assert any("5" in e for e in report.errors)


def test_at_min_files(tmp_path):
    """Exactly min_files entries should pass."""
    for i in range(3):
        (tmp_path / f"{i}.csv").touch()
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / f"{i}.csv", remote=f"{i}.csv") for i in range(3)],
        min_files=3,
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert report.passed


# ── Total size ────────────────────────────────────────────────────────────────


def test_below_min_size_warns(tmp_path):
    """Below the size threshold should produce a warning (not an error)."""
    (tmp_path / "small.csv").write_text("a,b,c\n1,2,3\n")
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / "small.csv", remote="small.csv")],
        min_total_size_mb=1000.0,  # unreachable
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert report.passed  # warning, not error
    assert len(report.warnings) >= 1
    assert any("size" in w.lower() for w in report.warnings)


def test_size_threshold_zero_bypasses_check(tmp_path):
    """When min_total_size_mb is 0, the size check is skipped."""
    (tmp_path / "tiny.csv").write_text("a\n1\n")
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / "tiny.csv", remote="tiny.csv")],
        min_total_size_mb=0.0,
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert report.passed
    # no warning about size
    assert not any("size" in w.lower() for w in report.warnings)


# ── CSV column checks ─────────────────────────────────────────────────────────


def test_csv_columns_pass(tmp_path):
    """When expected columns are present, the check passes."""
    csv_path = _make_csv(
        tmp_path / "data.csv",
        [
            ["id", "name", "value"],
            ["1", "foo", "10"],
        ],
    )
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=csv_path, remote="data.csv")],
        column_checks=[ColumnCheck(filename="data.csv", expected=["id", "value"])],
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert report.passed


def test_csv_columns_missing(tmp_path):
    """A missing column should fail."""
    csv_path = _make_csv(
        tmp_path / "data.csv",
        [
            ["id", "name"],
            ["1", "foo"],
        ],
    )
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=csv_path, remote="data.csv")],
        column_checks=[ColumnCheck(filename="data.csv", expected=["id", "MISSING_COL"])],
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert not report.passed
    assert any("MISSING_COL" in e for e in report.errors)


def test_csv_columns_case_insensitive(tmp_path):
    """Column name matching should be case-insensitive."""
    csv_path = _make_csv(
        tmp_path / "d.csv",
        [
            ["ID", "NAME"],
            ["1", "foo"],
        ],
    )
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=csv_path, remote="d.csv")],
        column_checks=[ColumnCheck(filename="d.csv", expected=["id", "name"])],
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert report.passed


def test_csv_columns_file_not_matched(tmp_path):
    """When the expected file isn't among entries, it should warn, not crash."""
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / "exists.csv", remote="exists.csv")],
        column_checks=[ColumnCheck(filename="unknown.csv", expected=["x"])],
    )
    (tmp_path / "exists.csv").touch()
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert report.passed  # warning only
    assert any("unknown.csv" in w for w in report.warnings)


# ── Mixed / combined ──────────────────────────────────────────────────────────


def test_multiple_errors_collected(tmp_path):
    """All errors should be collected, not just the first one."""
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        # two files, both missing
        files=[
            FileEntry(local=tmp_path / "a.csv", remote="a.csv"),
            FileEntry(local=tmp_path / "b.csv", remote="b.csv"),
        ],
        min_files=5,
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    # errors: 2 missing files + 1 min_files
    assert len(report.errors) == 3


def test_empty_dataset(tmp_path):
    """A config with zero file entries and default checks should warn."""
    cfg = DatasetConfig(name="test", repo_id="user/repo", files=[])
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    # min_files = 1 > 0 → error
    assert not report.passed
