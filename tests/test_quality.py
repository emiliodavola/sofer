"""Tests for data_uploader._csv_reader and data_uploader.quality."""

import csv
from pathlib import Path

import pytest

from data_uploader._csv_reader import stream_csv
from data_uploader.checks import ValidationReport
from data_uploader.model import (
    DatasetConfig,
    FileEntry,
    QualityCheck,
    QualityConfig,
    QualityResult,
)
from data_uploader.quality import QualityValidator


def _make_csv(
    path: Path,
    rows: list[list[str]],
    delimiter: str = ";",
    encoding: str = "utf-8",
) -> Path:
    """Write a small CSV for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding=encoding) as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerows(rows)
    return path


# ── Model dataclasses ──────────────────────────────────────────────────────────


class TestQualityModel:
    def test_quality_check_default_severity(self):
        """QualityCheck defaults severity to warn."""
        qc = QualityCheck(check="duplicates")
        assert qc.severity == "warn"

    def test_quality_config_empty_checks(self):
        """QualityConfig defaults to empty checks list."""
        cfg = QualityConfig()
        assert cfg.checks == []
        assert cfg.default_severity == "warn"
        assert cfg.max_sample == 100_000

    def test_quality_result_roundtrip(self):
        """QualityResult stores check, severity, message."""
        r = QualityResult(check="duplicates", severity="fail", message="Duplicates found")
        assert r.check == "duplicates"
        assert r.severity == "fail"
        assert r.message == "Duplicates found"


# ── [[quality]] TOML parsing ────────────────────────────────────────────────────


class TestQualityFromToml:
    def test_quality_section_absent(self, tmp_path):
        """No [[quality]] section → empty checks, no error."""
        toml = (
            '[dataset]\nname = "t"\nrepo_id = "u/t"\n\n'
            '[[file]]\nlocal = "d.csv"\nremote = "d.csv"\n'
        )
        p = tmp_path / "t.toml"
        p.write_text(toml)
        (tmp_path / "d.csv").touch()
        cfg = DatasetConfig.from_toml(p)
        assert cfg.quality.checks == []

    def test_quality_section_full(self, tmp_path):
        """[[quality]] entries produce matching QualityCheck objects."""
        toml = (
            '[dataset]\nname = "t"\nrepo_id = "u/t"\n\n'
            '[[file]]\nlocal = "d.csv"\nremote = "d.csv"\n\n'
            '[[quality]]\ncheck = "duplicates"\nseverity = "fail"\n\n'
            '[[quality]]\ncheck = "null_profiling"\n'
            'max_null_pct = 15.0\ncolumns = ["age", "income"]\n'
        )
        p = tmp_path / "t.toml"
        p.write_text(toml)
        (tmp_path / "d.csv").touch()
        cfg = DatasetConfig.from_toml(p)
        assert len(cfg.quality.checks) == 2
        assert cfg.quality.checks[0].check == "duplicates"
        assert cfg.quality.checks[0].severity == "fail"
        assert cfg.quality.checks[1].check == "null_profiling"
        assert cfg.quality.checks[1].max_null_pct == 15.0
        assert cfg.quality.checks[1].columns == ["age", "income"]

    def test_unknown_check_name_warns(self, tmp_path, capsys):
        """Unknown check name → warning printed, entry ignored."""
        toml = (
            '[dataset]\nname = "t"\nrepo_id = "u/t"\n\n'
            '[[file]]\nlocal = "d.csv"\nremote = "d.csv"\n\n'
            '[[quality]]\ncheck = "bogus_check"\n'
        )
        p = tmp_path / "t.toml"
        p.write_text(toml)
        (tmp_path / "d.csv").touch()
        cfg = DatasetConfig.from_toml(p)
        assert len(cfg.quality.checks) == 0
        captured = capsys.readouterr()
        assert "bogus_check" in captured.out or "bogus_check" in captured.err


# ── QualityValidator — all 9 P0 checks ──────────────────────────────────────────


def _make_csv_cfg(
    tmp_path,
    headers: list[str],
    rows: list[list[str]],
    filename: str = "data.csv",
    quality_checks: list | None = None,
    encoding: str = "utf-8",
) -> tuple[DatasetConfig, Path]:
    """Create a DatasetConfig with one CSV file and optional quality checks."""
    csv_path = _make_csv(tmp_path / filename, [headers, *rows], encoding=encoding)
    cfg = DatasetConfig(
        name="test",
        repo_id="u/test",
        files=[FileEntry(local=csv_path, remote=filename)],
        quality=QualityConfig(checks=quality_checks or []),
    )
    return cfg, csv_path


def _run_quality(cfg: DatasetConfig) -> ValidationReport:
    """Run QualityValidator and return the report."""
    v = QualityValidator(cfg)
    return v.run()


# ── 4.2 Duplicates ──────────────────────────────────────────────────────────────


class TestCheckDuplicates:
    def test_no_duplicates(self, tmp_path):
        """No duplicates → no warning."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["id", "val"],
            [["1", "a"], ["2", "b"], ["3", "c"]],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "duplicates"]
        assert len(qr) == 0

    def test_duplicates_detected(self, tmp_path):
        """Exact duplicate rows → warning with row numbers."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["id", "val"],
            [["1", "a"], ["2", "b"], ["1", "a"]],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "duplicates"]
        assert len(qr) >= 1
        assert any("duplicate" in r.message.lower() for r in qr)


# ── 4.3 Empty rows ──────────────────────────────────────────────────────────────


class TestCheckEmptyRows:
    def test_all_populated(self, tmp_path):
        """No empty rows → no warning."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["a", "b"],
            [["1", "x"], ["2", "y"]],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "empty_rows"]
        assert len(qr) == 0

    def test_empty_row_detected(self, tmp_path):
        """Row with all-empty fields → warning."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["a", "b"],
            [["1", "x"], ["", ""], ["3", "z"]],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "empty_rows"]
        assert len(qr) >= 1


# ── 4.4 Empty columns ────────────────────────────────────────────────────────────


class TestCheckEmptyColumns:
    def test_all_populated(self, tmp_path):
        """Every column has ≥ 1 non-empty value → no warning."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["a", "b"],
            [["1", "x"], ["2", "y"]],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "empty_columns"]
        assert len(qr) == 0

    def test_fully_empty_column(self, tmp_path):
        """Column with all-empty values → warning naming the column."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["id", "notes"],
            [["1", ""], ["2", ""], ["3", ""]],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "empty_columns"]
        assert len(qr) >= 1
        assert any("notes" in r.message for r in qr)


# ── 4.5 Null profiling ───────────────────────────────────────────────────────────


class TestCheckNullProfiling:
    def test_below_threshold(self, tmp_path):
        """Column with 10% missing → no warning (default threshold 50%)."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["a", "b"],
            [["1", "x"], ["2", ""], ["3", "z"], ["4", "w"], ["5", "v"]],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "null_profiling"]
        assert len(qr) == 0

    def test_above_threshold(self, tmp_path):
        """Column with 60% missing → warning."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["a", "b"],
            [["1", "x"], ["", ""], ["", ""], ["", ""], ["", ""]],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "null_profiling"]
        assert len(qr) >= 1


# ── 4.6 Format consistency ────────────────────────────────────────────────────────


class TestCheckFormatConsistency:
    def test_uniform_numeric(self, tmp_path):
        """All-numeric column → no warning."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["val"],
            [["100"], ["200"], ["300"]],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "format_consistency"]
        assert len(qr) == 0

    def test_mixed_types(self, tmp_path):
        """Column with both numeric and text → warning."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["val"],
            [["100"], ["200"], ["thirty"]],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "format_consistency"]
        assert len(qr) >= 1


# ── 4.7 Corrupt records ──────────────────────────────────────────────────────────


class TestCheckCorruptRecords:
    def test_uniform_lengths(self, tmp_path):
        """Every row has same field count as header → no error."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["a", "b", "c"],
            [["1", "x", "10"], ["2", "y", "20"]],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "corrupt_records"]
        assert len(qr) == 0

    def test_short_row_fails(self, tmp_path):
        """Row with fewer fields than header → fail-severity error."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["a", "b", "c"],
            [["1", "x", "10"], ["2", "y"]],  # row 2 missing field
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "corrupt_records"]
        assert len(qr) >= 1
        assert any(r.severity == "fail" for r in qr)


# ── 4.8 Value range ──────────────────────────────────────────────────────────────


class TestCheckValueRange:
    def test_values_in_range(self, tmp_path):
        """Values within configured range → no warning."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["age"],
            [["25"], ["30"], ["42"]],
            quality_checks=[
                QualityCheck(check="value_range", columns=["age"], min=0, max=120),
            ],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "value_range"]
        assert len(qr) == 0

    def test_out_of_range(self, tmp_path):
        """Value outside range → warning."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["age"],
            [["25"], ["200"], ["42"]],
            quality_checks=[
                QualityCheck(check="value_range", columns=["age"], min=0, max=120),
            ],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "value_range"]
        assert len(qr) >= 1

    def test_no_range_configured_skipped(self, tmp_path):
        """No min/max configured → check skipped entirely."""
        cfg, _ = _make_csv_cfg(tmp_path, ["age"], [["25"]])
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "value_range"]
        assert len(qr) == 0


# ── 4.9 Cross-file types ─────────────────────────────────────────────────────────


class TestCheckCrossFileTypes:
    def test_compatible_types(self, tmp_path):
        """Same column type across two files → no warning."""
        p1 = _make_csv(tmp_path / "a.csv", [["year", "val"], ["2020", "10"]])
        p2 = _make_csv(tmp_path / "b.csv", [["year", "val"], ["2021", "20"]])
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=p1, remote="a.csv"),
                FileEntry(local=p2, remote="b.csv"),
            ],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "cross_file_types"]
        assert len(qr) == 0

    def test_type_mismatch(self, tmp_path):
        """Same column, different types across files → warning."""
        p1 = _make_csv(tmp_path / "a.csv", [["year"], ["2020"]])
        p2 = _make_csv(tmp_path / "b.csv", [["year"], ["twenty twenty"]])
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=p1, remote="a.csv"),
                FileEntry(local=p2, remote="b.csv"),
            ],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "cross_file_types"]
        assert len(qr) >= 1
        assert any("year" in r.message for r in qr)


# ── 4.10 Encoding validation ─────────────────────────────────────────────────────


class TestCheckEncodingValidation:
    def test_valid_utf8(self, tmp_path):
        """Valid UTF-8 file → no error."""
        cfg, _ = _make_csv_cfg(tmp_path, ["a"], [["x"]], encoding="utf-8")
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "encoding_validation"]
        assert len(qr) == 0

    def test_fallback_latin1(self, tmp_path):
        """Latin-1 file → rejected by UTF-8 enforcement."""
        cfg, _ = _make_csv_cfg(tmp_path, ["a"], [["José"]], encoding="latin-1")
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "encoding_validation"]
        assert len(qr) >= 1
        assert qr[0].severity == "fail"


# ── print_summary quality section ───────────────────────────────────────────────


class TestPrintSummaryQuality:
    def test_quality_section_printed_when_results(self, capsys):
        """Quality results appear in a dedicated section."""
        report = ValidationReport("test")
        report.quality_results = [
            QualityResult(
                check="duplicates",
                severity="warn",
                message="Duplicate rows: Row 1 = Row 3",
            ),
            QualityResult(
                check="corrupt_records",
                severity="fail",
                message="Row 5 has 2 fields, header has 3",
            ),
        ]
        report.print_summary()
        captured = capsys.readouterr()
        assert "Quality checks" in captured.out
        assert "duplicates" in captured.out
        assert "corrupt_records" in captured.out

    def test_quality_section_omitted_when_empty(self, capsys):
        """No quality_results → no quality section."""
        report = ValidationReport("test")
        report.print_summary()
        captured = capsys.readouterr()
        assert "Quality checks" not in captured.out


# ── stream_csv ─────────────────────────────────────────────────────────────────


class TestStreamCsv:
    def test_normal_csv(self, tmp_path):
        """Normal CSV: first yield is header, then data rows."""
        csv_path = _make_csv(
            tmp_path / "data.csv",
            [["id", "name", "value"], ["1", "foo", "10"], ["2", "bar", "20"]],
        )
        results = list(stream_csv(csv_path))
        # First yield: header only
        header, row = results[0]
        assert row is None
        assert header == ["id", "name", "value"]
        # Data rows
        assert len(results) == 3  # header + 2 data
        assert results[1] == (["id", "name", "value"], ["1", "foo", "10"])
        assert results[2] == (["id", "name", "value"], ["2", "bar", "20"])

    def test_empty_file(self, tmp_path):
        """Empty file: yields header (empty list), row=None, then stops."""
        csv_path = _make_csv(tmp_path / "empty.csv", [])
        results = list(stream_csv(csv_path))
        assert len(results) == 1
        header, row = results[0]
        assert header == []
        assert row is None

    def test_header_only_file(self, tmp_path):
        """Header-only: yields header, row=None, then stops."""
        csv_path = _make_csv(
            tmp_path / "header_only.csv",
            [["a", "b", "c"]],
        )
        results = list(stream_csv(csv_path))
        assert len(results) == 1
        header, row = results[0]
        assert header == ["a", "b", "c"]
        assert row is None

    def test_sample_cap(self, tmp_path):
        """max_sample limits the number of data rows yielded."""
        rows = [["col"]] + [[str(i)] for i in range(200)]
        csv_path = _make_csv(tmp_path / "large.csv", rows)
        results = list(stream_csv(csv_path, max_sample=100))
        # header + 100 data rows = 101 yields
        assert len(results) == 101
        assert results[0][1] is None  # header
        assert results[-1][1] == ["99"]

    def test_encoding_fallback_latin1(self, tmp_path):
        """Latin-1 file → rejected by UTF-8 enforcement in stream_csv."""
        csv_path = _make_csv(
            tmp_path / "latin1.csv",
            [["name"], ["José"], ["François"]],
            encoding="latin-1",
        )
        with pytest.raises(ValueError, match="Cannot decode"):
            list(stream_csv(csv_path, encoding="utf-8-sig"))

    def test_encoding_fallback_utf8_direct(self, tmp_path):
        """Plain UTF-8 file decoded without fallback."""
        csv_path = _make_csv(
            tmp_path / "utf8.csv",
            [["a"], ["x"], ["y"]],
            encoding="utf-8",
        )
        results = list(stream_csv(csv_path, encoding="utf-8"))
        assert len(results) == 3

    def test_binary_file_is_rejected(self, tmp_path):
        """Binary file: UTF-8 enforcement rejects it."""
        csv_path = tmp_path / "binary.csv"
        csv_path.write_bytes(b"\xff\xfe\xfd\xfc\xfb\xfa\xfb\xfc\xff")
        with pytest.raises(ValueError, match="Cannot decode"):
            list(stream_csv(csv_path))
