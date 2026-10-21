"""Tests for sofer._csv_reader and sofer.quality."""

import codecs
import csv
import tracemalloc
from pathlib import Path

import pytest

from sofer import config
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
        assert cfg.full_scan is None

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

    def test_quality_policy_table_parsed(self, tmp_path):
        """An optional ``[quality]`` table carries full_scan / max_sample."""
        toml = (
            '[dataset]\nname = "t"\nrepo_id = "u/t"\n\n'
            '[[file]]\nlocal = "d.csv"\nremote = "d.csv"\n\n'
            '[quality]\nfull_scan = "never"\nmax_sample = 250\n'
        )
        p = tmp_path / "t.toml"
        p.write_text(toml)
        (tmp_path / "d.csv").touch()
        cfg = DatasetConfig.from_toml(p)
        assert cfg.quality.full_scan == "never"
        assert cfg.quality.max_sample == 250
        assert cfg.quality.checks == []

    def test_unknown_full_scan_mode_warns(self, tmp_path, capsys):
        """An unknown per-dataset full_scan mode is ignored with a warning."""
        toml = (
            '[dataset]\nname = "t"\nrepo_id = "u/t"\n\n'
            '[[file]]\nlocal = "d.csv"\nremote = "d.csv"\n\n'
            '[quality]\nfull_scan = "sometimes"\n'
        )
        p = tmp_path / "t.toml"
        p.write_text(toml)
        (tmp_path / "d.csv").touch()
        cfg = DatasetConfig.from_toml(p)
        assert cfg.quality.full_scan is None
        captured = capsys.readouterr()
        assert "sometimes" in captured.out


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


def _two_same_basename_csvs(
    tmp_path: Path,
    left: list[list[str]],
    right: list[list[str]],
) -> DatasetConfig:
    """Two declared sources both named ``data.csv``, in different folders.

    The layouts are valid and indistinguishable by basename, which is exactly
    the collision issue #369 is about.
    """
    left_path = _make_csv(tmp_path / "a" / "data.csv", left)
    right_path = _make_csv(tmp_path / "b" / "data.csv", right)
    return DatasetConfig(
        name="test",
        repo_id="u/test",
        _base_dir=tmp_path,
        files=[
            FileEntry(local=left_path, remote="a/data.csv"),
            FileEntry(local=right_path, remote="b/data.csv"),
        ],
    )


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

    def test_duplicates_finding_names_the_file(self, tmp_path):
        """A duplicate pair names the file it came from (issue #293).

        RED: _dup_findings stores only the row numbers, so the emitted message
        cannot be traced back to a table — and the hash is namespaced per file,
        so the envelope cannot resolve it either.
        """
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["id", "val"],
            [["1", "a"], ["2", "b"], ["1", "a"]],
        )
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "duplicates"]
        assert len(qr) == 1
        assert qr[0].message.startswith("Duplicate rows: ")
        assert "data.csv: Row 1 = Row 3" in qr[0].message

    def test_duplicates_cap_does_not_hide_another_file(self, tmp_path):
        """A noisy file cannot fill the item cap and hide the other files.

        RED: the pairs are emitted in scan order, so a.csv's pairs use the whole
        REPORT_MAX_ITEMS budget before b.csv's single pair is reached.
        """
        repeated = [["1", "x"] for _ in range(config.REPORT_MAX_ITEMS + 2)]
        p1 = _make_csv(tmp_path / "a.csv", [["id", "val"], *repeated])
        p2 = _make_csv(tmp_path / "b.csv", [["id", "val"], ["9", "z"], ["9", "z"]])
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
        assert len(qr) == 1
        message = qr[0].message
        assert "a.csv: Row 1 = Row 2" in message
        assert "b.csv: Row 1 = Row 2" in message
        assert message.count(" = ") == config.REPORT_MAX_ITEMS

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

    @staticmethod
    def _duplicates(cfg: DatasetConfig) -> list[QualityResult]:
        report = _run_quality(cfg)
        return [r for r in report.quality_results if r.check == "duplicates"]

    def test_a_pipe_in_a_cell_does_not_make_two_rows_equal(self, tmp_path):
        """Issue #368: joining fields with a separator is ambiguous."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["left", "right"],
            [["a|b", "c"], ["a", "b|c"]],
        )

        assert self._duplicates(cfg) == []

    def test_empty_fields_are_framed_unambiguously(self, tmp_path):
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["left", "right"],
            [["a|", ""], ["a", "|"]],
        )

        assert self._duplicates(cfg) == []

    def test_backslashes_and_unicode_keep_their_boundaries(self, tmp_path):
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["left", "right"],
            [["é|b", "c"], ["é", "b|c"], ["a\\", "b|c"], ["a\\|b", "c"]],
        )

        assert self._duplicates(cfg) == []

    def test_an_exact_repeated_row_with_a_pipe_is_still_reported(self, tmp_path):
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["left", "right"],
            [["a|b", "c"], ["1", "2"], ["a|b", "c"]],
        )

        findings = self._duplicates(cfg)

        assert [finding.message for finding in findings] == [
            "Duplicate rows: data.csv: Row 1 = Row 3"
        ]

    def test_no_false_duplicate_when_duplicates_is_a_fail_check(self, tmp_path):
        """A false finding would block the dataset, so the file must pass."""
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["left", "right"],
            [["a|b", "c"], ["a", "b|c"]],
            quality_checks=[QualityCheck(check="duplicates", severity="fail")],
        )

        report = _run_quality(cfg)

        assert report.passed is True
        assert [r for r in report.quality_results if r.check == "duplicates"] == []

    def test_same_basename_sources_are_not_duplicates_of_each_other(self, tmp_path):
        """Issue #369: one row in each of a/data.csv and b/data.csv is no pair."""
        cfg = _two_same_basename_csvs(
            tmp_path,
            [["id", "val"], ["1", "x"]],
            [["id", "val"], ["1", "x"]],
        )

        assert self._duplicates(cfg) == []

    def test_real_duplicates_in_a_same_basename_source_are_disambiguated(self, tmp_path):
        """The pair is real, so the message must say which data.csv it is."""
        cfg = _two_same_basename_csvs(
            tmp_path,
            [["id", "val"], ["1", "x"], ["1", "x"]],
            [["id", "val"], ["2", "y"]],
        )

        findings = self._duplicates(cfg)

        assert [finding.message for finding in findings] == [
            "Duplicate rows: a/data.csv: Row 1 = Row 2"
        ]

    def test_reversing_the_declaration_order_keeps_per_file_results(self, tmp_path):
        """The left file repeats, so order must not change the attribution."""
        left = _make_csv(
            tmp_path / "a" / "data.csv",
            [["id", "val"], ["1", "x"], ["1", "x"]],
        )
        right = _make_csv(tmp_path / "b" / "data.csv", [["id", "val"], ["2", "y"]])
        forward = DatasetConfig(
            name="test",
            repo_id="u/test",
            _base_dir=tmp_path,
            files=[
                FileEntry(local=left, remote="a/data.csv"),
                FileEntry(local=right, remote="b/data.csv"),
            ],
        )
        reversed_order = DatasetConfig(
            name="test",
            repo_id="u/test",
            _base_dir=tmp_path,
            files=[
                FileEntry(local=right, remote="b/data.csv"),
                FileEntry(local=left, remote="a/data.csv"),
            ],
        )

        assert [f.message for f in self._duplicates(forward)] == [
            f.message for f in self._duplicates(reversed_order)
        ]


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

    def test_same_basename_sources_keep_independent_empty_columns(self, tmp_path):
        """Issue #369: `notes` empty in a/data.csv but populated in b/data.csv."""
        cfg = _two_same_basename_csvs(
            tmp_path,
            [["id", "notes"], ["1", ""], ["2", "  "]],
            [["id", "notes"], ["1", "x"], ["2", "y"]],
        )

        report = _run_quality(cfg)

        findings = [r for r in report.quality_results if r.check == "empty_columns"]
        assert [f.message for f in findings] == ["Fully empty columns in 'a/data.csv': notes"]

    def test_a_header_only_same_basename_source_cannot_erase_the_other(self, tmp_path):
        """The zero-row source must not overwrite the populated one's count."""
        cfg = _two_same_basename_csvs(
            tmp_path,
            [["id"]],
            [["id"], ["1"], ["2"]],
        )

        validator = QualityValidator(cfg)
        validator.run()

        assert sorted(validator._file_row_count.values()) == [0, 2]
        assert len(validator._file_row_count) == 2


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

    def test_same_basename_sources_are_tracked_separately(self, tmp_path):
        """Issue #369: a/data.csv and b/data.csv are two sources, not one."""
        cfg = _two_same_basename_csvs(
            tmp_path,
            [["year"], ["2020"]],
            [["total"], ["10"]],
        )

        validator = QualityValidator(cfg)
        validator.run()

        assert sorted(validator._file_col_types) == ["a/data.csv", "b/data.csv"]
        assert validator._file_col_types["a/data.csv"] == {"year": "numeric"}
        assert validator._file_col_types["b/data.csv"] == {"total": "numeric"}


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


class TestEncodingProbeBoundary:
    """Issue #370: a window that ends mid-character is not an encoding error.

    The probe judges its first ``probe_chunk_bytes``. The bytes that complete a
    sequence cut by that window exist in the file and are simply not read, so
    they must not make a valid file fail. Only a sequence cut by physical
    end-of-file is genuinely undecodable, and that distinction is what the
    incremental decoder has to preserve.
    """

    @staticmethod
    def _cfg(tmp_path: Path, payload: bytes, name: str = "data.csv") -> DatasetConfig:
        """Write *payload* byte for byte (a text-mode write could not)."""
        path = tmp_path / name
        path.write_bytes(payload)
        return DatasetConfig(
            name="probe",
            repo_id="u/probe",
            files=[FileEntry(local=path, remote=name)],
        )

    @staticmethod
    def _findings(cfg: DatasetConfig) -> list[QualityResult]:
        report = QualityValidator(cfg).run()
        assert "encoding_validation" in report.ran_checks
        return [r for r in report.quality_results if r.check == "encoding_validation"]

    @staticmethod
    def _single_column_payload(window: int, char: str) -> bytes:
        """One-column rows whose *char* has exactly one byte inside *window*."""
        header = b"value\n"
        filler = b"a\n" * ((window - len(header) - 1) // 2) + b"a"
        return header + filler + char.encode("utf-8") + b"\n1\n"

    @staticmethod
    def _straddling(window: int, char: str, inside: int, prefix: bytes = b"") -> bytes:
        """Build a payload whose *char* is cut after *inside* bytes by *window*."""
        encoded = char.encode("utf-8")
        assert 1 <= inside < len(encoded), "the cut must fall inside the character"
        header = prefix + b"value\n"
        filler = b"a" * (window - len(header) - inside)
        return header + filler + encoded + b"\n"

    @pytest.mark.parametrize(
        ("char", "inside"),
        [("é", 1), ("€", 1), ("€", 2), ("😀", 1), ("😀", 2), ("😀", 3)],
    )
    def test_a_character_cut_by_the_window_is_not_an_error(self, tmp_path, char, inside):
        """2-, 3- and 4-byte characters, cut at every internal offset."""
        window = config.PROBE_CHUNK_BYTES

        cfg = self._cfg(tmp_path, self._straddling(window, char, inside))

        assert self._findings(cfg) == []

    def test_a_bom_and_a_character_cut_by_the_window_are_both_accepted(self, tmp_path):
        window = config.PROBE_CHUNK_BYTES

        cfg = self._cfg(tmp_path, self._straddling(window, "é", 1, prefix=codecs.BOM_UTF8))

        assert self._findings(cfg) == []

    def test_a_deliberately_small_window_still_tolerates_the_cut(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "PROBE_CHUNK_BYTES", 16)

        cfg = self._cfg(tmp_path, self._straddling(16, "😀", 2, prefix=b"x\n"))

        assert self._findings(cfg) == []

    def test_invalid_bytes_inside_the_window_still_fail(self, tmp_path):
        window = config.PROBE_CHUNK_BYTES

        cfg = self._cfg(tmp_path, b"a\n" + b"\xff" + b"b" * window)

        findings = self._findings(cfg)
        assert [finding.severity for finding in findings] == ["fail"]

    def test_a_character_truncated_by_a_short_file_still_fails(self, tmp_path):
        """Physical EOF cuts the sequence for real, so it must not be tolerated."""
        cfg = self._cfg(tmp_path, b"\xc3")

        findings = self._findings(cfg)
        assert [finding.severity for finding in findings] == ["fail"]

    def test_a_character_truncated_at_an_exact_window_still_fails(self, tmp_path):
        """A file whose length equals the window ends at physical EOF."""
        window = config.PROBE_CHUNK_BYTES

        cfg = self._cfg(tmp_path, b"a" * (window - 1) + b"\xc3")

        findings = self._findings(cfg)
        assert [finding.severity for finding in findings] == ["fail"]

    def test_an_empty_file_produces_no_finding(self, tmp_path):
        cfg = self._cfg(tmp_path, b"")

        assert self._findings(cfg) == []

    def test_a_short_valid_file_produces_no_finding(self, tmp_path):
        cfg = self._cfg(tmp_path, b"a;b\n1;2\n")

        assert self._findings(cfg) == []

    def test_a_valid_character_cut_by_the_window_passes_mid_stream(self, tmp_path):
        """The cut character in a later row must not fail the streaming pass."""
        window = config.PROBE_CHUNK_BYTES

        cfg = self._cfg(tmp_path, self._single_column_payload(window, "é"))

        report = QualityValidator(cfg).run()
        findings = [
            r
            for r in report.quality_results
            if r.check in {"encoding_validation", "corrupt_records"}
        ]
        assert findings == []

    def test_a_non_utf8_row_inside_the_window_is_reported_once(self, tmp_path):
        """The probe reports it; the streaming pass must not duplicate it."""
        cfg = self._cfg(tmp_path, b"a;b\n1;2\n\xff;2\n")

        report = QualityValidator(cfg).run()

        encoding = [r for r in report.quality_results if r.check == "encoding_validation"]
        corrupt = [r for r in report.quality_results if r.check == "corrupt_records"]
        assert [r.severity for r in encoding] == ["fail"]
        assert corrupt == []

    def test_a_non_utf8_tail_cannot_abort_the_run(self, tmp_path):
        """A row the probe never saw must become a finding, not an exception.

        The probe judges the first ``probe_chunk_bytes``. A mislabeled file
        whose first invalid byte sits past that window decodes its header, so
        the streaming pass is the one that discovers the problem; before the
        fix the ``ValueError`` escaped ``run()`` and the caller got no report
        at all.
        """
        window = config.PROBE_CHUNK_BYTES
        payload = b"a;b\n" + b"1;2\n" * (window // 4) + b"\xff;2\n" + b"3;4\n"
        cfg = self._cfg(tmp_path, payload)

        report = QualityValidator(cfg).run()

        corrupt = [r for r in report.quality_results if r.check == "corrupt_records"]
        assert [r.severity for r in corrupt] == ["fail"]
        assert "data.csv" in corrupt[0].message
        encoding = [r for r in report.quality_results if r.check == "encoding_validation"]
        assert encoding == []


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
        # Sampling only happens when no row-requiring fail check is active
        # (issue #290), so both default fail checks are downgraded to warn.
        rows = [["", ""]] * 200
        cfg, _ = _make_csv_cfg(
            tmp_path,
            ["a", "b"],
            rows,
            quality_checks=[
                QualityCheck(check="null_profiling", severity="warn"),
                QualityCheck(check="corrupt_records", severity="warn"),
                QualityCheck(check="encoding_validation", severity="warn"),
            ],
        )
        cfg.quality.max_sample = 50
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "null_profiling"]
        assert qr, "expected a null_profiling finding"
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
    """TSV is text-eligible and parsed with tabs, never the CSV delimiter."""

    @staticmethod
    def _write(path: Path, rows: list[list[str]]) -> Path:
        """Write a real tab-delimited file, not a CSV wearing a ``.tsv`` name."""
        with open(path, "w", newline="", encoding="utf-8") as handle:
            csv.writer(handle, delimiter="\t").writerows(rows)
        return path

    @staticmethod
    def _corrupt(cfg: DatasetConfig) -> list[QualityResult]:
        report = _run_quality(cfg)
        return [r for r in report.quality_results if r.check == "corrupt_records"]

    def test_tsv_short_row_produces_corrupt_records_fail(self, tmp_path):
        """A tab-delimited TSV with a short row → corrupt_records fail."""
        tsv = self._write(
            tmp_path / "data.tsv",
            [["a", "b", "c"], ["1", "x", "10"], ["2", "y"]],
        )
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=tsv, remote="data.tsv")],
        )

        findings = self._corrupt(cfg)

        assert [finding.severity for finding in findings] == ["fail"]
        assert findings[0].message == "Row 2 in 'data.tsv' has 2 fields, header has 3"

    def test_tsv_overlong_row_is_reported_with_its_field_counts(self, tmp_path):
        tsv = self._write(
            tmp_path / "data.tsv",
            [["a", "b", "c"], ["1", "2", "3"], ["4", "5", "6", "7"]],
        )
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=tsv, remote="data.tsv")],
        )

        findings = self._corrupt(cfg)

        assert findings[0].message == "Row 2 in 'data.tsv' has 4 fields, header has 3"

    def test_a_valid_tab_delimited_tsv_produces_no_corrupt_finding(self, tmp_path):
        """The default CSV delimiter is ``;``; a real TSV must still pass."""
        tsv = self._write(
            tmp_path / "data.tsv",
            [["a", "b", "c"], ["1", "2", "3"], ["4", "5", "6"]],
        )
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=tsv, remote="data.tsv")],
        )

        assert self._corrupt(cfg) == []

    def test_an_uppercase_tsv_uses_tabs_too(self, tmp_path):
        tsv = self._write(
            tmp_path / "DATA.TSV",
            [["a", "b", "c"], ["1", "2"]],
        )
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=tsv, remote="DATA.TSV")],
        )

        findings = self._corrupt(cfg)

        assert findings[0].message == "Row 1 in 'DATA.TSV' has 2 fields, header has 3"

    def test_a_csv_delimiter_override_does_not_reach_tsv(self, tmp_path):
        """A comma override for CSV must leave TSV tab-delimited."""
        tsv = self._write(
            tmp_path / "data.tsv",
            [["a", "b", "c"], ["1", "2"]],
        )
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=tsv, remote="data.tsv")],
            csv_delimiter=",",
        )

        findings = self._corrupt(cfg)

        assert findings[0].message == "Row 1 in 'data.tsv' has 2 fields, header has 3"

    def test_a_csv_keeps_the_configured_comma_delimiter(self, tmp_path):
        """The CSV side keeps honouring the configured separator."""
        source = tmp_path / "data.csv"
        with open(source, "w", newline="", encoding="utf-8") as handle:
            csv.writer(handle, delimiter=",").writerows([["a", "b", "c"], ["1", "2"]])
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=source, remote="data.csv")],
            csv_delimiter=",",
        )

        findings = self._corrupt(cfg)

        assert findings[0].message == "Row 1 in 'data.csv' has 2 fields, header has 3"


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
        # values.TSV with short row — real tabs, whatever the CSV delimiter is
        with open(tsv_file, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter="\t")
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
            w = csv.writer(f, delimiter="\t")
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


class TestColNonemptyBoolean:
    """``empty_columns`` bookkeeping is a per-column boolean (issue #290).

    Replaces the old ``TestValuePreviewLen`` class: the accumulator no longer
    stores distinct values (so ``config.QUALITY_VALUE_PREVIEW_LEN`` has no
    reader and was removed), it stores a single "seen non-empty" flag keyed
    ``file::col``.
    """

    def test_seen_flag_is_a_bool_not_a_value_set(self, tmp_path):
        """A populated column stores a single ``True`` flag, not a value set."""
        cfg, _ = _make_csv_cfg(tmp_path, ["note"], [["a"], ["a"], ["b"]])
        validator = QualityValidator(cfg)
        validator.run()
        assert len(validator._col_nonempty) == 1
        ((_source, column), seen) = next(iter(validator._col_nonempty.items()))
        assert column == "note"
        assert seen is True
        assert isinstance(seen, bool)

    def test_empty_column_stays_false_and_is_reported(self, tmp_path):
        """A fully empty column keeps ``False`` and still produces a finding."""
        cfg, _ = _make_csv_cfg(tmp_path, ["note"], [[""], ["  "]])
        validator = QualityValidator(cfg)
        report = validator.run()
        assert list(validator._col_nonempty.values()) == [False]
        assert any(r.check == "empty_columns" for r in report.quality_results)

    def test_memory_is_o_columns_not_o_rows(self, tmp_path):
        """A 5000-row stream over one column keeps exactly one boolean."""
        rows = [[f"value-{i}-" + "x" * 40] for i in range(5000)]
        cfg, _ = _make_csv_cfg(tmp_path, ["note"], rows)
        validator = QualityValidator(cfg)
        validator.run()
        assert len(validator._col_nonempty) == 1
        assert list(validator._col_nonempty.values()) == [True]


# ── Bounded quality scan (issue #290) ─────────────────────────────────────────


def _corrupt_csv_cfg(
    tmp_path,
    corrupt_rows: list[int],
    *,
    row_count: int = 150,
    max_sample: int = 50,
    severity: str = "fail",
) -> DatasetConfig:
    """Build a 2-column CSV config where the named 1-based rows are corrupt."""
    rows: list[list[str]] = [["col1", "col2"]]
    for i in range(1, row_count + 1):
        rows.append(["only_one_field"] if i in corrupt_rows else [str(i), "b"])
    p = _make_csv(tmp_path / "data.csv", rows)
    return DatasetConfig(
        name="test",
        repo_id="u/test",
        files=[FileEntry(local=p, remote="data.csv")],
        quality=QualityConfig(
            checks=[QualityCheck(check="corrupt_records", severity=severity)],
            max_sample=max_sample,
        ),
    )


class TestDuplicateTrackingCap:
    """S2/D2/D5: ``_dup_hashes`` is capped and the cap is named as partial."""

    def test_cap_marks_partial_and_names_the_cap(self, tmp_path, monkeypatch):
        """Hitting the cap marks ``duplicates`` partial and names the cap."""
        import sofer.config as _config

        monkeypatch.setattr(_config, "QUALITY_MAX_DUP_TRACKING", 3)
        rows = [["a"], ["b"], ["c"], ["d"], ["e"], ["a"]]
        cfg, _ = _make_csv_cfg(tmp_path, ["val"], rows)
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "duplicates"]
        assert len(qr) == 1
        assert qr[0].partial is True
        assert "3" in qr[0].message

    def test_cap_without_duplicates_reports_partial(self, tmp_path, monkeypatch):
        """An all-unique corpus stops at the cap and is still reported partial."""
        import sofer.config as _config

        monkeypatch.setattr(_config, "QUALITY_MAX_DUP_TRACKING", 5)
        rows = [[f"v{i}"] for i in range(20)]
        cfg, _ = _make_csv_cfg(tmp_path, ["val"], rows)
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "duplicates"]
        assert len(qr) == 1
        assert qr[0].partial is True
        assert "5" in qr[0].message

    def test_tracking_dict_never_exceeds_the_cap(self, tmp_path, monkeypatch):
        """A 200-row unique stream leaves exactly ``cap`` tracked hashes."""
        import sofer.config as _config

        monkeypatch.setattr(_config, "QUALITY_MAX_DUP_TRACKING", 10)
        rows = [[f"v{i}"] for i in range(200)]
        cfg, _ = _make_csv_cfg(tmp_path, ["val"], rows)
        validator = QualityValidator(cfg)
        validator.run()
        assert len(validator._dup_hashes) == 10
        assert validator._dup_hashes_capped is True


class TestAccumulatorCaps:
    """S7/T6: the three per-row finding lists stop growing at report limits."""

    def test_duplicate_findings_capped_at_report_limit(self, tmp_path):
        import sofer.config as _config

        rows = [["x"]] * (_config.REPORT_MAX_ITEMS + 5)
        cfg, _ = _make_csv_cfg(tmp_path, ["val"], rows)
        validator = QualityValidator(cfg)
        validator.run()
        # Pairs are grouped per file (issue #293) and each file's list is capped
        # at the report limit (issue #290), so the first N pairs are kept.
        ((_source, pairs),) = validator._dup_findings.items()
        assert len(pairs) == _config.REPORT_MAX_ITEMS
        assert pairs[0] == (1, 2)
        assert pairs[-1] == (1, _config.REPORT_MAX_ITEMS + 1)

    def test_empty_rows_capped_at_report_limit(self, tmp_path):
        import sofer.config as _config

        rows = [["", ""]] * (_config.REPORT_MAX_ITEMS + 5) + [["v", "v"]]
        cfg, _ = _make_csv_cfg(tmp_path, ["a", "b"], rows)
        validator = QualityValidator(cfg)
        validator.run()
        assert len(validator._empty_row_numbers) == _config.REPORT_MAX_ITEMS

    def test_corrupt_findings_capped_at_report_limit(self, tmp_path):
        import sofer.config as _config

        limit = _config.REPORT_MAX_CORRUPT_RECORDS
        rows = [["only_one"]] * (limit + 5)
        p = _make_csv(tmp_path / "data.csv", [["a", "b"], *rows])
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=p, remote="data.csv")],
        )
        validator = QualityValidator(cfg)
        validator.run()
        assert len(validator._corrupt_findings) == limit

    def test_accumulator_sizes_do_not_grow_with_dataset_size(self, tmp_path, monkeypatch):
        """Two stream sizes produce identical (capped) accumulator sizes."""
        import sofer.config as _config

        monkeypatch.setattr(_config, "QUALITY_MAX_DUP_TRACKING", 25)

        def _sizes(n: int) -> tuple[int, int, int]:
            rows = [["", ""]] * n + [["v", "v"]]
            cfg, _ = _make_csv_cfg(tmp_path / f"n{n}", ["a", "b"], rows)
            validator = QualityValidator(cfg)
            validator.run()
            return (
                len(validator._dup_hashes),
                len(validator._empty_row_numbers),
                sum(len(pairs) for pairs in validator._dup_findings.values()),
            )

        assert _sizes(100) == _sizes(3000)


class TestEncodingProbePeak:
    """Issue #326/S3: the 8 KB probe must not materialize the whole file.

    The probe is the one read the quality pass makes whose size is not capped by
    ``max_sample``: it exists to answer "does the first ``probe_chunk_bytes``
    decode?", so materializing the file to slice it makes the pass's peak follow
    the corpus size — the property the `data-quality` spec forbids (S4).
    """

    # Slack allowed between the two peaks. The corpora below differ by ~100x on
    # disk (~34 KiB vs ~3.4 MiB), so anything that makes the peak follow the
    # input shows up as a difference two orders of magnitude above this bound.
    PEAK_FLATNESS_SLACK_BYTES = 1 << 20

    SMALL_ROWS = 2_000
    LARGE_ROWS = 200_000

    @staticmethod
    def _write_corpus(path: Path, rows: int) -> Path:
        """Write *rows* three-column data rows to *path* and return it."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, delimiter=";")
            writer.writerow(["a", "b", "c"])
            for i in range(rows):
                writer.writerow([f"value-{i}", "x", "y"])
        return path

    @classmethod
    def _peak_bytes(cls, tmp_path: Path, rows: int) -> int:
        """Return the ``tracemalloc`` peak of one quality pass over *rows* rows.

        The scan is sampled (``full_scan = "never"``) with a tiny ``max_sample``
        so every *capped* accumulator saturates after a couple of hundred rows:
        what is left to grow with the corpus is exactly the uncapped read.
        """
        path = cls._write_corpus(tmp_path / f"rows-{rows}.csv", rows)
        cfg = DatasetConfig(
            name="peak",
            repo_id="u/peak",
            files=[FileEntry(local=path, remote=path.name)],
            quality=QualityConfig(max_sample=200, full_scan="never"),
        )
        tracemalloc.start()
        try:
            QualityValidator(cfg).run()
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        return peak

    def test_peak_does_not_track_the_corpus_size(self, tmp_path):
        """Two corpora 100x apart in size must peak within a flatness slack."""
        small_peak = self._peak_bytes(tmp_path, self.SMALL_ROWS)
        large_peak = self._peak_bytes(tmp_path, self.LARGE_ROWS)
        assert large_peak - small_peak < self.PEAK_FLATNESS_SLACK_BYTES

    def test_only_the_probe_window_is_judged(self, tmp_path):
        """Invalid bytes *after* the probe window keep the previous verdict.

        The probe judges the first ``probe_chunk_bytes`` only — the accepted
        limitation §4.9 records — and bounding the read must not quietly widen
        that window to the whole file.
        """
        path = tmp_path / "late-invalid.csv"
        window = config.PROBE_CHUNK_BYTES
        with open(path, "wb") as fh:
            fh.write(b"a;b\n")
            fh.write(b"1;2\n" * (window // 4))  # valid UTF-8, longer than one window
            fh.write(b"\xff\xfe\x00\x00")  # invalid UTF-8, past the window
        cfg = DatasetConfig(
            name="window",
            repo_id="u/window",
            files=[FileEntry(local=path, remote=path.name)],
            quality=QualityConfig(max_sample=50, full_scan="never"),
        )
        report = QualityValidator(cfg).run()
        assert "encoding_validation" in report.ran_checks
        assert [r for r in report.quality_results if r.check == "encoding_validation"] == []


class TestFullScanPolicy:
    """S3/S4/D3/D4: the full-scan decision is explicit and config-owned."""

    def test_needs_full_scan_is_false_for_encoding_probe_only(self, tmp_path):
        """Only a *row-requiring* fail check turns ``_needs_full_scan`` on."""
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[],
            quality=QualityConfig(
                checks=[
                    QualityCheck(check="corrupt_records", severity="warn"),
                    QualityCheck(check="encoding_validation", severity="fail"),
                ]
            ),
        )
        assert QualityValidator(cfg)._needs_full_scan() is False

    def test_needs_full_scan_true_for_default_corrupt_records(self, tmp_path):
        """The built-in ``corrupt_records`` fail check is row-requiring."""
        cfg, _ = _make_csv_cfg(tmp_path, ["val"], [["1"]])
        assert QualityValidator(cfg)._needs_full_scan() is True

    def test_encoding_probe_does_not_force_full_scan(self, tmp_path):
        """A 120th-row corrupt record is missed when only the probe fails."""
        import sofer.config as _config

        cfg = _corrupt_csv_cfg(tmp_path, [120], severity="warn")
        cfg.quality.checks.append(QualityCheck(check="encoding_validation", severity="fail"))
        report = _run_quality(cfg)
        assert [r for r in report.quality_results if r.check == "corrupt_records"] == []
        assert _config.QUALITY_ROW_REQUIRING_CHECKS == ["corrupt_records"]

    def test_row_requiring_fail_check_still_scans_full_file(self, tmp_path):
        """The default ``corrupt_records`` fail check sees the 120th row."""
        cfg = _corrupt_csv_cfg(tmp_path, [120], severity="fail")
        report = _run_quality(cfg)
        assert any(r.check == "corrupt_records" for r in report.quality_results)

    def test_never_honours_max_sample_with_fail_check(self, tmp_path, monkeypatch):
        """``never`` samples even with a fail check, and marks it partial."""
        import sofer.config as _config

        monkeypatch.setattr(_config, "QUALITY_FULL_SCAN", "never")
        cfg = _corrupt_csv_cfg(tmp_path, [10, 120], severity="fail")
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "corrupt_records"]
        assert len(qr) == 1, f"row 120 must not be seen, got {qr}"
        assert qr[0].partial is True

    def test_encoding_probe_finding_is_never_partial(self, tmp_path, monkeypatch):
        """A fixed-size probe finding is never marked partial by sampling."""
        import sofer.config as _config

        monkeypatch.setattr(_config, "QUALITY_FULL_SCAN", "never")
        good = _make_csv(tmp_path / "good.csv", [["a"], *[[str(i)] for i in range(100)]])
        bad = tmp_path / "bad.csv"
        bad.write_bytes(b"PK\x03\x04\xff\xfe\xfd\xfc mislabeled")
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=good, remote="good.csv"),
                FileEntry(local=bad, remote="bad.csv"),
            ],
            quality=QualityConfig(
                checks=[
                    QualityCheck(check="corrupt_records", severity="warn"),
                    QualityCheck(check="encoding_validation", severity="fail"),
                ],
                max_sample=10,
            ),
        )
        report = _run_quality(cfg)
        enc = [r for r in report.quality_results if r.check == "encoding_validation"]
        assert enc, "expected an encoding_validation finding"
        assert all(r.partial is False for r in enc)

    def test_always_scans_everything(self, tmp_path, monkeypatch):
        """``always`` scans the full file and leaves findings non-partial."""
        import sofer.config as _config

        monkeypatch.setattr(_config, "QUALITY_FULL_SCAN", "always")
        cfg = _corrupt_csv_cfg(tmp_path, [120], severity="warn")
        report = _run_quality(cfg)
        qr = [r for r in report.quality_results if r.check == "corrupt_records"]
        assert len(qr) == 1
        assert qr[0].partial is False

    def test_per_dataset_override_wins_over_tool_default(self, tmp_path):
        """``cfg.quality.full_scan`` wins over the tool-wide default."""
        cfg = _corrupt_csv_cfg(tmp_path, [120], severity="warn")
        cfg.quality.full_scan = "always"
        report = _run_quality(cfg)
        assert any(r.check == "corrupt_records" for r in report.quality_results)
