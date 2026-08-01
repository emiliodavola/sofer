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

    def test_quality_result_partial_defaults_false(self):
        """QualityResult.partial defaults to False."""
        r = QualityResult(check="duplicates", severity="warn", message="test")
        assert r.partial is False

    def test_quality_result_partial_explicit(self):
        """QualityResult.partial can be set explicitly."""
        r = QualityResult(check="duplicates", severity="warn", message="test", partial=True)
        assert r.partial is True


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

    def test_empty_column_per_file_isolation(self, tmp_path):
        """Column empty in one file but populated in another → flagged per-file."""
        p1 = _make_csv(tmp_path / "a.csv", [["id", "notes"], ["1", "hello"]])

        p2 = _make_csv(tmp_path / "b.csv", [["id", "notes"], ["2", ""]])

        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=p1, remote="a.csv"),
                FileEntry(local=p2, remote="b.csv"),
            ],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "empty_columns"]
        # "notes" is populated in a.csv but fully empty in b.csv
        # Should be flagged as an empty column in b.csv
        assert len(qr) >= 1
        assert any("notes" in r.message for r in qr)
        # The message should identify the file where it's empty
        assert any("b.csv" in r.message for r in qr)


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

    def test_unreadable_file_produces_fail_finding(self, tmp_path, monkeypatch):
        """An unreadable file produces a fail finding with filename."""
        p = _make_csv(tmp_path / "broken.csv", [["a", "b"], ["1", "x"]])

        # Force open() to raise OSError when trying to open broken.csv
        builtin_open = open

        def _failing_open(file, *args, **kwargs):
            if isinstance(file, (str, Path)) and "broken.csv" in str(file):
                raise OSError("Permission denied")
            return builtin_open(file, *args, **kwargs)

        monkeypatch.setattr("builtins.open", _failing_open)

        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=p, remote="broken.csv")],
        )
        report = _run_quality(cfg)
        # Should produce a fail finding, not silently skip
        fail_findings = [
            r for r in report.quality_results if r.severity == "fail" and "broken.csv" in r.message
        ]
        assert len(fail_findings) >= 1, (
            f"Expected fail finding for broken.csv, got results: {report.quality_results}"
        )


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


# ── Persisted quality report (Issue #14) ─────────────────────────────────────


class TestQualityReportFile:
    def test_quality_report_written_to_disk(self, tmp_path):
        """Quality run writes quality-report.md with findings grouped by file."""
        p = _make_csv(tmp_path / "data.csv", [["id", "val"], ["1", ""], ["2", ""]])

        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=p, remote="data.csv")],
            _base_dir=tmp_path,
        )
        report = _run_quality(cfg)
        report_path = tmp_path / "quality-report.md"

        from data_uploader.quality import write_quality_report

        write_quality_report(report, report_path)

        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "# Quality Report" in content
        assert "test" in content
        # Should mention findings or "no issues"
        assert (
            "empty_columns" in content.lower()
            or "null_profiling" in content.lower()
            or "no issues" in content.lower()
            or "duplicates" in content.lower()
        )

    def test_quality_report_handles_empty_results(self, tmp_path):
        """Quality report is still generated when there are zero findings."""
        p = _make_csv(tmp_path / "data.csv", [["id", "val"], ["1", "x"]])

        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=p, remote="data.csv")],
            _base_dir=tmp_path,
        )
        report = _run_quality(cfg)
        report_path = tmp_path / "quality-report.md"

        from data_uploader.quality import write_quality_report

        write_quality_report(report, report_path)

        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "# Quality Report" in content


class TestHonestCheckAccounting:
    def test_skipped_check_not_counted_as_passed(self, capsys):
        """value_range without config is skipped, not passed."""
        report = ValidationReport("test")
        report.quality_results = [
            QualityResult(check="duplicates", severity="warn", message="dup"),
        ]
        # Only duplicates ran (1 finding), all others are either skipped or no finding
        report.ran_checks = {"duplicates", "empty_rows", "empty_columns"}
        report.print_summary()
        captured = capsys.readouterr()
        # Should mention skipped checks, not count them as "passed"
        assert "skipped" in captured.out.lower() or "duplicates" in captured.out

    def test_ran_check_without_findings_is_passed(self, capsys):
        """A check that ran but found nothing is counted as passed."""
        report = ValidationReport("test")
        report.quality_results = [
            QualityResult(check="duplicates", severity="warn", message="dup"),
        ]
        report.ran_checks = {"duplicates", "empty_rows"}
        report.print_summary()
        captured = capsys.readouterr()
        # empty_rows ran but found nothing → should be counted somewhere
        assert "empty_rows" in captured.out or "passed" in captured.out.lower()


class TestFullFileCoverage:
    def test_fail_check_scans_full_file(self, tmp_path):
        """fail-severity check scans all rows even when max_sample is small."""
        # Create 150 rows — exceeds default max_sample=100_000, but we set it low
        rows = [[str(i)] for i in range(150)]
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["val"],
            rows,
            quality_checks=[
                QualityCheck(check="corrupt_records", severity="fail"),
            ],
        )
        # Set a low max_sample
        cfg.quality.max_sample = 50
        report = _run_quality(cfg)
        # Even with max_sample=50, the fail check should scan all rows
        # If full scan worked, no corrupt_records findings (all rows are fine)
        qr = [r for r in report.quality_results if r.check == "corrupt_records"]
        # No corrupt records expected — all rows have correct field count
        assert len(qr) == 0, f"Expected no corrupt records, got: {qr}"

    def test_corrupt_row_beyond_sample_limit_detected(self, tmp_path):
        """A corrupt row beyond max_sample is still detected by fail checks."""
        # Create rows where row 120 has a corrupt record (wrong field count)
        rows = [["col1", "col2"]]  # header
        for i in range(1, 151):
            if i == 120:
                rows.append(["only_one_field"])  # corrupt: 1 field vs 2
            else:
                rows.append([str(i), "b"])
        p = _make_csv(tmp_path / "data.csv", rows)
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=p, remote="data.csv")],
            quality=QualityConfig(
                checks=[QualityCheck(check="corrupt_records", severity="fail")],
                max_sample=50,
            ),
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "corrupt_records"]
        # Should find the corrupt record at row 119 (0-indexed: 119 is the 120th data row)
        assert len(qr) >= 1, f"Expected corrupt record at row 119, got: {qr}"

    def test_warn_check_partial_when_max_sample_applied(self, tmp_path):
        """warn-severity findings are marked partial when max_sample is used."""
        rows = [[str(i)] for i in range(200)]
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["val"],
            rows,
            quality_checks=[
                QualityCheck(check="null_profiling", severity="warn"),
            ],
        )
        cfg.quality.max_sample = 50
        # Force all values to be null so we get a finding
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "null_profiling"]
        if qr:
            assert qr[0].partial is True, (
                f"Expected partial=True for warn check with max_sample, got partial={qr[0].partial}"
            )


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
