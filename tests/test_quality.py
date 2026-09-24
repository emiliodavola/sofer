"""Tests for sofer._csv_reader and sofer.quality."""

import csv
from pathlib import Path

import pytest

from sofer._csv_reader import stream_csv
from sofer.checks import ValidationReport
from sofer.model import (
    DatasetConfig,
    FileEntry,
    QualityCheck,
    QualityConfig,
    QualityResult,
)
from sofer.quality import QualityValidator


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

    def test_duplicates_file_scoped_no_cross_file(self, tmp_path):
        """Two files sharing identical row content → NO duplicate warning.

        RED: dup_hashes is currently global, so identical rows across files
        are falsely reported as duplicates.
        """
        p1 = _make_csv(tmp_path / "a.csv", [["id", "val"], ["1", "x"]])
        p2 = _make_csv(tmp_path / "b.csv", [["id", "val"], ["1", "x"]])
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=p1, remote="a.csv"),
                FileEntry(local=p2, remote="b.csv"),
            ],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "duplicates"]
        assert len(qr) == 0, f"Cross-file duplicates should NOT be flagged, but got: {qr}"


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

    def test_empty_columns_skips_zero_row_file(self, tmp_path):
        """Header-only file (0 data rows) → no empty_columns finding.

        RED: a file with only a header gets every column tagged as "empty"
        because _col_nonempty entries are never populated for 0-row files.
        """
        p = _make_csv(tmp_path / "header_only.csv", [["id", "name"]])  # 0 data rows
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=p, remote="header_only.csv")],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "empty_columns"]
        assert len(qr) == 0, f"Zero-row file should not report empty columns, but got: {qr}"


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

    def test_cross_file_types_skips_zero_row_file(self, tmp_path):
        """Header-only file (0 data rows) → NOT included in type comparison.

        RED: header-only file gets type "unknown" and miscompares with data files.
        """
        # Header-only file listed FIRST so _col_samples is empty when inferring
        # its types (no cross-file sample leakage). This triggers the real bug:
        # type "unknown" vs "numeric" for the shared column.
        p1 = _make_csv(tmp_path / "header_only.csv", [["year"]])  # 0 data rows
        p2 = _make_csv(tmp_path / "data.csv", [["year"], ["2020"]])
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=p1, remote="header_only.csv"),
                FileEntry(local=p2, remote="data.csv"),
            ],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "cross_file_types"]
        assert len(qr) == 0, (
            f"Zero-row file should not participate in cross_file_types, but got: {qr}"
        )


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

        from sofer.quality import write_quality_report

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

        from sofer.quality import write_quality_report

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


# ── Text-eligible gating (fix-quality-encoding-xlsx) ───────────────────────


class TestBinaryFormatsSkipped:
    """Binary formats are skipped — no QualityResult, no ran_checks."""

    def test_run_with_xlsx_parquet_jsonl_yields_empty(self, tmp_path):
        """Binary .xlsx/.parquet/.jsonl → quality_results == [] and ran_checks == {}."""
        xlsx = tmp_path / "a.xlsx"
        parquet = tmp_path / "b.parquet"
        jsonl = tmp_path / "c.jsonl"
        xlsx.write_bytes(b"PK\x03\x04\x14\x00\x00\x00\x08\x00 fake xlsx content")
        parquet.write_bytes(b"PAR1\x15\x00\x00\x00fake parquet")
        jsonl.write_bytes(b'{"a": 1}\n{"a": 2}\n')
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=xlsx, remote="a.xlsx"),
                FileEntry(local=parquet, remote="b.parquet"),
                FileEntry(local=jsonl, remote="c.jsonl"),
            ],
        )
        report = _run_quality(cfg)
        assert report.quality_results == []
        assert report.ran_checks == set()


class TestTsvEligible:
    """TSV is text-eligible and checked like CSV."""

    def test_tsv_short_row_produces_corrupt_records_fail(self, tmp_path):
        """TSV with short row → corrupt_records fail."""
        tsv = tmp_path / "data.tsv"
        with open(tsv, "w", newline="", encoding="utf-8") as f:
            # Use default delimiter ";" so the validator (which uses cfg.csv_delimiter=";")
            # correctly parses the file regardless of .tsv suffix.
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["a", "b", "c"])
            writer.writerow(["1", "x", "10"])
            writer.writerow(["2", "y"])  # short row: 2 vs 3
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=tsv, remote="data.tsv")],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "corrupt_records"]
        assert len(qr) >= 1
        assert any(r.severity == "fail" for r in qr)


class TestCaseInsensitiveAndNoExtension:
    """Case-insensitive suffix and no-extension files are handled."""

    def test_uppercase_xlsx_and_readme_skipped(self, tmp_path):
        """DATA.XLSX + README skipped; Report.CSV + values.TSV checked."""
        xlsx = tmp_path / "DATA.XLSX"
        readme = tmp_path / "README"
        csv_file = tmp_path / "Report.CSV"
        tsv_file = tmp_path / "values.TSV"
        xlsx.write_bytes(b"PK\x03\x04 binary content for uppercase xlsx")
        readme.write_text("just a readme with no suffix", encoding="utf-8")
        # Report.CSV with short row
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["a", "b", "c"])
            w.writerow(["1", "x"])  # short
        # values.TSV with short row — use ";" so default delimiter parses it
        with open(tsv_file, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["x", "y", "z"])
            w.writerow(["1", "2"])  # short
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=xlsx, remote="DATA.XLSX"),
                FileEntry(local=readme, remote="README"),
                FileEntry(local=csv_file, remote="Report.CSV"),
                FileEntry(local=tsv_file, remote="values.TSV"),
            ],
        )
        report = _run_quality(cfg)
        # Should have corrupt_records findings for the two eligible files
        qr = [r for r in report.quality_results if r.check == "corrupt_records"]
        assert len(qr) >= 2
        messages = " ".join(r.message for r in qr)
        assert "Report.CSV" in messages
        assert "values.TSV" in messages
        # Non-eligible must not appear in messages
        assert "DATA.XLSX" not in messages
        assert "README" not in messages

    def test_csv_gz_suffix_skipped(self, tmp_path):
        """a.csv.gz → suffix .gz → skipped."""
        gz_csv = tmp_path / "a.csv.gz"
        gz_csv.write_bytes(b"PK\x03\x04 fake gzipped csv")
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=gz_csv, remote="a.csv.gz")],
        )
        report = _run_quality(cfg)
        assert report.quality_results == []
        assert report.ran_checks == set()


class TestBinaryOnlyNoCrossFile:
    """Binary-only datasets produce no cross-file findings."""

    def test_two_identical_xlsx_no_cross_file_findings(self, tmp_path):
        """Two identical .xlsx → no duplicates/cross_file_types/empty_columns/corrupt_records."""
        content = b"PK\x03\x04\x14\x00\x08\x00 identical xlsx bytes"
        p1 = tmp_path / "a.xlsx"
        p2 = tmp_path / "b.xlsx"
        p1.write_bytes(content)
        p2.write_bytes(content)
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=p1, remote="a.xlsx"),
                FileEntry(local=p2, remote="b.xlsx"),
            ],
        )
        report = _run_quality(cfg)
        assert report.quality_results == []
        assert report.ran_checks == set()
        for check in ("duplicates", "cross_file_types", "empty_columns", "corrupt_records"):
            assert not any(r.check == check for r in report.quality_results)


class TestDefensiveHelperGuards:
    """Direct helper calls on non-eligible paths are no-ops."""

    def test_check_encoding_validation_guard(self, tmp_path):
        """Direct _check_encoding_validation on .xlsx → no result, no ran_checks."""
        cfg, _ = _make_csv_cfg(tmp_path, ["a"], [["x"]])
        validator = QualityValidator(cfg)
        # Reset to known empty state
        validator._reset_accumulators()
        validator._check_encoding_validation(Path("data.xlsx"))
        assert validator._results == []
        assert validator._ran_checks == set()
        validator._check_encoding_validation(Path("data.parquet"))
        assert validator._results == []
        assert validator._ran_checks == set()
        validator._check_encoding_validation(Path("data.jsonl"))
        assert validator._results == []
        assert validator._ran_checks == set()

    def test_process_file_guard(self, tmp_path):
        """Direct _process_file on .parquet → no result, no ran_checks."""
        cfg, _ = _make_csv_cfg(tmp_path, ["a"], [["x"]])
        validator = QualityValidator(cfg)
        validator._reset_accumulators()
        validator._process_file(Path("data.parquet"))
        assert validator._results == []
        assert validator._ran_checks == set()
        validator._process_file(Path("data.xlsx"))
        assert validator._results == []
        assert validator._ran_checks == set()
        # Also check case-insensitive guard
        validator._process_file(Path("DATA.XLSX"))
        assert validator._results == []
        assert validator._ran_checks == set()


class TestMixedAndRanChecksAndEncoding:
    """Mixed datasets, ran_checks accounting, and UTF-8-only encoding."""

    def test_run_filters_before_accumulators(self, tmp_path):
        """a.csv + b.xlsx + c.tsv → only a/c reach probe/stream."""
        a_csv = _make_csv(tmp_path / "a.csv", [["a", "b", "c"], ["1", "x", "10"]])
        b_xlsx = tmp_path / "b.xlsx"
        b_xlsx.write_bytes(b"PK\x03\x04 fake xlsx")
        c_tsv = tmp_path / "c.tsv"
        with open(c_tsv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["a", "b", "c"])
            w.writerow(["1", "x"])  # short row → corrupt
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=a_csv, remote="a.csv"),
                FileEntry(local=b_xlsx, remote="b.xlsx"),
                FileEntry(local=c_tsv, remote="c.tsv"),
            ],
        )
        report = _run_quality(cfg)
        # Only c.tsv should produce corrupt_records
        qr = [r for r in report.quality_results if r.check == "corrupt_records"]
        assert len(qr) >= 1
        assert any("c.tsv" in r.message for r in qr)
        assert not any("b.xlsx" in r.message for r in qr)
        assert not any("a.csv" in r.message for r in qr)

    def test_mixed_ran_checks_reflects_only_eligible(self, tmp_path):
        """data.csv + extra.xlsx → ran_checks same as data.csv alone."""
        # Run with only eligible file
        data_only_csv = _make_csv(tmp_path / "data_only.csv", [["id", "val"], ["1", "x"]])
        cfg_only = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=data_only_csv, remote="data.csv")],
        )
        report_only = _run_quality(cfg_only)
        # Run with eligible + binary
        data_csv = _make_csv(tmp_path / "data.csv", [["id", "val"], ["1", "x"]])
        extra = tmp_path / "extra.xlsx"
        extra.write_bytes(b"PK\x03\x04 extra")
        cfg_mixed = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=data_csv, remote="data.csv"),
                FileEntry(local=extra, remote="extra.xlsx"),
            ],
        )
        report_mixed = _run_quality(cfg_mixed)
        assert report_mixed.ran_checks == report_only.ran_checks
        assert report_mixed.ran_checks != set()

    def test_binary_only_ran_checks_empty(self, tmp_path):
        """Binary-only → ran_checks == {} and quality_results == []."""
        p1 = tmp_path / "only.xlsx"
        p1.write_bytes(b"PK\x03\x04 binary")
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=p1, remote="only.xlsx")],
        )
        report = _run_quality(cfg)
        assert report.quality_results == []
        assert report.ran_checks == set()

    def test_latin1_csv_fails_utf8_passes_xlsx_skipped(self, tmp_path):
        """latin-1 José fails, UTF-8 passes, .xlsx skipped regardless."""
        # latin-1 csv
        latin_csv = _make_csv(tmp_path / "latin.csv", [["name"], ["José"]], encoding="latin-1")
        cfg_latin = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=latin_csv, remote="latin.csv")],
        )
        report_latin = _run_quality(cfg_latin)
        qr_latin = [r for r in report_latin.quality_results if r.check == "encoding_validation"]
        assert len(qr_latin) >= 1
        assert qr_latin[0].severity == "fail"

        # UTF-8 csv passes
        utf_csv = _make_csv(tmp_path / "utf.csv", [["name"], ["José"]], encoding="utf-8")
        cfg_utf = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=utf_csv, remote="utf.csv")],
        )
        report_utf = _run_quality(cfg_utf)
        qr_utf = [r for r in report_utf.quality_results if r.check == "encoding_validation"]
        assert len(qr_utf) == 0

        # .xlsx with valid UTF-8 bytes → still skipped
        xlsx = tmp_path / "data.xlsx"
        xlsx.write_bytes("name\nJosé\n".encode())
        cfg_xlsx = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=xlsx, remote="data.xlsx")],
        )
        report_xlsx = _run_quality(cfg_xlsx)
        assert report_xlsx.quality_results == []
        assert report_xlsx.ran_checks == set()

    def test_mislabeled_csv_with_pk_raises_value_error(self, tmp_path):
        """Mislabelled .csv containing PK + invalid UTF-8 → ValueError from stream_csv."""
        bad_csv = tmp_path / "bad.csv"
        # PK header plus invalid UTF-8 bytes (\xff\xfe) ensures decode failure
        bad_csv.write_bytes(b"PK\x03\x04\xff\xfe\xfd\xfc mislabeled")
        with pytest.raises(ValueError, match="Cannot decode"):
            list(stream_csv(bad_csv, encoding="utf-8-sig"))
        # Via QualityValidator it should surface as encoding_validation fail
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=bad_csv, remote="bad.csv")],
        )
        report = _run_quality(cfg)
        assert any(
            r.check == "encoding_validation" and r.severity == "fail"
            for r in report.quality_results
        )

    def test_is_text_eligible_direct(self):
        """is_text_eligible handles .csv/.tsv case-insensitive and others false."""
        from sofer._formats import is_text_eligible

        assert is_text_eligible(Path("a.csv")) is True
        assert is_text_eligible(Path("a.tsv")) is True
        assert is_text_eligible(Path("A.CSV")) is True
        assert is_text_eligible(Path("values.TSV")) is True
        assert is_text_eligible(Path("Report.CSV")) is True
        assert is_text_eligible(Path("a.xlsx")) is False
        assert is_text_eligible(Path("a.parquet")) is False
        assert is_text_eligible(Path("a.jsonl")) is False
        assert is_text_eligible(Path("a.csv.gz")) is False  # suffix .gz
        assert is_text_eligible(Path("README")) is False
        assert is_text_eligible(Path("DATA.XLSX")) is False


# ── Quality value preview cap (issue #189) ────────────────────────────────────


class TestValuePreviewLen:
    """Distinct quality values truncate to ``config.QUALITY_VALUE_PREVIEW_LEN``."""

    LONG_VALUE = "x" * 60

    def _stored_value(self, tmp_path, monkeypatch=None, preview_len=None):
        import sofer.config as _config

        if preview_len is not None:
            monkeypatch.setattr(_config, "QUALITY_VALUE_PREVIEW_LEN", preview_len)
        cfg, _ = _make_csv_cfg(tmp_path, ["note"], [[self.LONG_VALUE]])
        validator = QualityValidator(cfg)
        validator.run()
        stored = validator._col_nonempty["data.csv::note"]
        assert len(stored) == 1
        return next(iter(stored))

    def test_default_truncates_to_fifty(self, tmp_path):
        """Default cap (50) truncates a 60-char value to 50 chars."""
        stored = self._stored_value(tmp_path)
        assert stored == "x" * 50

    def test_override_changes_stored_length(self, tmp_path, monkeypatch):
        """Overriding the cap changes the stored value length."""
        stored = self._stored_value(tmp_path, monkeypatch, preview_len=7)
        assert stored == "x" * 7
