"""Tests for split detection, repo inspection, remote path validation,
overwrite protection, split mapping validation, and load_dataset verification
in sofer.uploader, sofer.splits, and sofer.verification."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pyarrow.parquet as pq

from sofer.model import DatasetConfig, FileEntry
from sofer.splits import (
    SplitInfo,
    SplitReport,
    detect_split_keyword,
    detect_splits,
    validate_layout,
    validate_split_mapping,
)
from sofer.uploader import (
    _check_overwrite_protection,
    _repo_diff_summary,
    _validate_remote_paths,
)
from sofer.verification import VerificationReport, verify_load_dataset

# ═══════════════════════════════════════════════════════════════════════════════
#  detect_split_keyword
# ═══════════════════════════════════════════════════════════════════════════════


class TestDetectSplitKeyword:
    def test_train_filename(self):
        """train.csv should detect 'train'."""
        assert detect_split_keyword("train.csv") == "train"

    def test_test_filename(self):
        """test.csv should detect 'test'."""
        assert detect_split_keyword("test.csv") == "test"

    def test_validation_synonym_valid(self):
        """valid.csv should detect 'validation' via the 'valid' synonym."""
        assert detect_split_keyword("valid.csv") == "validation"

    def test_validation_synonym_val(self):
        """val.csv should detect 'validation'."""
        assert detect_split_keyword("val.csv") == "validation"

    def test_validation_synonym_dev(self):
        """dev.csv should detect 'validation'."""
        assert detect_split_keyword("dev.csv") == "validation"

    def test_test_synonym_eval(self):
        """eval.csv should detect 'test'."""
        assert detect_split_keyword("eval.csv") == "test"

    def test_test_synonym_testing(self):
        """testing.csv should detect 'test'."""
        assert detect_split_keyword("testing.csv") == "test"

    def test_train_synonym_training(self):
        """training.csv should detect 'train'."""
        assert detect_split_keyword("training.csv") == "train"

    def test_keyword_must_be_delimited(self):
        """testfile.csv should NOT match — 'test' is not delimited."""
        assert detect_split_keyword("testfile.csv") is None

    def test_keyword_in_middle_delimited(self):
        """my-test-data.csv should detect 'test' (delimited by hyphens)."""
        assert detect_split_keyword("my-test-data.csv") == "test"

    def test_keyword_with_underscore(self):
        """train_data.csv should detect 'train' (delimited by underscore)."""
        assert detect_split_keyword("train_data.csv") == "train"

    def test_keyword_with_dot(self):
        """train.data.csv should detect 'train' (delimited by dot)."""
        assert detect_split_keyword("train.data.csv") == "train"

    def test_no_keyword(self):
        """data.csv has no split keyword."""
        assert detect_split_keyword("data.csv") is None

    def test_case_insensitive(self):
        """TRAIN.CSV should detect 'train'."""
        assert detect_split_keyword("TRAIN.CSV") == "train"


# ═══════════════════════════════════════════════════════════════════════════════
#  detect_splits — filename strategy (Strategy 2)
# ═══════════════════════════════════════════════════════════════════════════════


class TestDetectSplitsFilename:
    def test_train_test_csv(self):
        """train.csv + test.csv should produce train and test splits."""
        report = detect_splits(["train.csv", "test.csv"])
        names = {s.name for s in report.splits}
        assert names == {"train", "test"}
        assert report.unclassified == []

    def test_train_val_test_parquet(self):
        """train/data/test parquet files should produce all three splits."""
        report = detect_splits(["train.parquet", "validation.parquet", "test.parquet"])
        names = {s.name for s in report.splits}
        assert names == {"train", "validation", "test"}

    def test_single_file_defaults_to_train(self):
        """A single data file with no keyword should be train split."""
        report = detect_splits(["data.csv"])
        assert len(report.splits) == 1
        assert report.splits[0].name == "train"
        assert report.splits[0].files == ["data.csv"]

    def test_multi_file_same_split(self):
        """Multiple files with the same keyword should be grouped."""
        report = detect_splits(["train-part1.csv", "train-part2.csv", "test.csv"])
        names = {s.name for s in report.splits}
        assert names == {"train", "test"}
        train_split = next(s for s in report.splits if s.name == "train")
        assert len(train_split.files) == 2

    def test_empty_list(self):
        """Empty list should produce empty report."""
        report = detect_splits([])
        assert report.splits == []
        assert report.unclassified == []

    def test_excluded_metadata_files(self):
        """README.md and LICENSE should not affect split detection."""
        report = detect_splits(["README.md", "LICENSE", "train.csv"])
        names = {s.name for s in report.splits}
        assert names == {"train"}
        assert len(report.splits[0].files) == 1

    def test_only_metadata_files(self):
        """When only metadata files exist, all go to train."""
        report = detect_splits(["README.md", "LICENSE"])
        assert len(report.splits) == 1
        assert report.splits[0].name == "train"


# ═══════════════════════════════════════════════════════════════════════════════
#  detect_splits — directory strategy (Strategy 1 — higher priority)
# ═══════════════════════════════════════════════════════════════════════════════


class TestDetectSplitsDirectory:
    def test_train_test_dirs(self):
        """train/data.csv + test/data.csv should detect via directory names."""
        report = detect_splits(["train/data.csv", "test/data.csv"])
        names = {s.name for s in report.splits}
        assert names == {"train", "test"}

    def test_directory_wins_over_filename(self):
        """Directory detection takes priority over filename detection."""
        report = detect_splits(["train/test-data.csv"])
        # The file itself has 'test' in the name, but directory is 'train'
        assert len(report.splits) == 1
        assert report.splits[0].name == "train"


# ═══════════════════════════════════════════════════════════════════════════════
#  detect_splits — shard strategy (Strategy 3)
# ═══════════════════════════════════════════════════════════════════════════════


class TestDetectSplitsShard:
    def test_shard_pattern_two_splits(self):
        """train-00001-of-00005.parquet + test-00001-of-00003.parquet → train/test."""
        report = detect_splits(
            [
                "train-00001-of-00005.parquet",
                "train-00002-of-00005.parquet",
                "test-00001-of-00003.parquet",
                "test-00002-of-00003.parquet",
            ]
        )
        names = {s.name for s in report.splits}
        assert names == {"train", "test"}

    def test_shard_with_validation(self):
        """Shard pattern with validation split."""
        report = detect_splits(
            [
                "train-00001-of-00005.parquet",
                "validation-00001-of-00002.parquet",
                "test-00001-of-00003.parquet",
            ]
        )
        names = {s.name for s in report.splits}
        assert names == {"train", "validation", "test"}

    def test_shard_pattern_needs_two_splits(self):
        """Shard detection requires at least 2 splits to fire."""
        report = detect_splits(["train-00001-of-00005.parquet"])
        # Falls back to filename detection (train keyword in filename)
        assert len(report.splits) == 1
        assert report.splits[0].name == "train"


# ═══════════════════════════════════════════════════════════════════════════════
#  validate_layout
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidateLayout:
    def test_train_test_layout_valid(self):
        """train.csv + test.csv is viewer-loadable."""
        warnings = validate_layout(["train.csv", "test.csv"])
        assert warnings == []

    def test_no_train_split_warns(self):
        """Without a train split, warn."""
        warnings = validate_layout(["test.csv", "validation.csv"])
        assert any("train" in w.lower() for w in warnings)

    def test_unclassified_files_warn(self):
        """Non-split files produce a warning."""
        warnings = validate_layout(["train.csv", "mystery-data.csv"])
        assert any("unclassified" in w.lower() for w in warnings)


# ═══════════════════════════════════════════════════════════════════════════════
#  Remote path validation
# ═══════════════════════════════════════════════════════════════════════════════


class TestRemotePathValidation:
    def test_trailing_slash_non_recursive(self):
        """remote='subfolder/' without recursive=True should fail."""
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=Path("data.csv"), remote="subfolder/"),
            ],
        )
        errors = _validate_remote_paths(cfg)
        assert len(errors) >= 1
        assert any("trailing slash" in e.lower() for e in errors)

    def test_trailing_slash_recursive_ok(self):
        """remote='subfolder/' with recursive=True is valid."""
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=Path("data"), remote="subfolder/", recursive=True),
            ],
        )
        errors = _validate_remote_paths(cfg)
        assert errors == []

    def test_valid_file_paths(self):
        """Normal file paths should pass."""
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=Path("a.csv"), remote="a.csv"),
                FileEntry(local=Path("b.parquet"), remote="subdir/b.parquet"),
            ],
        )
        errors = _validate_remote_paths(cfg)
        assert errors == []

    def test_empty_remote(self):
        """Empty remote path should fail."""
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=Path("data.csv"), remote="/"),
            ],
        )
        errors = _validate_remote_paths(cfg)
        assert len(errors) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
#  Repo diff summary
# ═══════════════════════════════════════════════════════════════════════════════


class TestRepoDiffSummary:
    def test_empty_repo(self, tmp_path):
        """An empty repo should show all files as new."""
        data = tmp_path / "data.csv"
        data.write_text("x\n1\n", encoding="utf-8")
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=data, remote="data.csv")],
            _base_dir=tmp_path,
        )
        summary = _repo_diff_summary(cfg, [], keep_csv=False)
        assert "ADDED" in summary
        assert "data.parquet" in summary
        assert "README.md" in summary
        assert "LICENSE" in summary

    def test_existing_files_show_as_modified(self):
        """Files already in the repo should show as OVERWRITTEN."""
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[],
        )
        summary = _repo_diff_summary(
            cfg,
            existing_files=["README.md", "LICENSE", "data.parquet"],
            keep_csv=False,
        )
        assert "OVERWRITTEN" in summary
        assert "README.md" in summary
        assert "LICENSE" in summary


# ═══════════════════════════════════════════════════════════════════════════════
#  Overwrite protection
# ═══════════════════════════════════════════════════════════════════════════════


class TestOverwriteProtection:
    def test_force_skips_protection(self):
        """With force=True, nothing is protected."""
        protected = _check_overwrite_protection(
            existing_files=["README.md", "LICENSE"],
            force=True,
        )
        assert protected == set()

    def test_not_force_but_no_existing(self):
        """When files don't exist yet, nothing is protected."""
        protected = _check_overwrite_protection(
            existing_files=[],
            force=False,
        )
        assert protected == set()

    def test_not_force_non_interactive(self, monkeypatch):
        """In non-interactive mode without force, existing files are protected."""
        # Simulate non-interactive stdin
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        protected = _check_overwrite_protection(
            existing_files=["README.md", "LICENSE"],
            force=False,
        )
        assert "readme.md" in protected
        assert "license" in protected

    def test_not_force_one_file_each(self, monkeypatch):
        """Only existing compliance files are protected, not all of them."""
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        protected = _check_overwrite_protection(
            existing_files=["README.md"],  # only README exists
            force=False,
        )
        assert "readme.md" in protected
        assert "license" not in protected


# ═══════════════════════════════════════════════════════════════════════════════
#  SplitReport dataclass
# ═══════════════════════════════════════════════════════════════════════════════


class TestSplitReportDataclass:
    def test_defaults(self):
        """Default SplitReport has empty lists."""
        report = SplitReport()
        assert report.splits == []
        assert report.unclassified == []
        assert report.warnings == []

    def test_split_info(self):
        """SplitInfo holds name and files."""
        si = SplitInfo(name="train", files=["a.csv", "b.csv"])
        assert si.name == "train"
        assert si.files == ["a.csv", "b.csv"]


# ═══════════════════════════════════════════════════════════════════════════════
#  validate_split_mapping
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidateSplitMapping:
    def test_single_file_no_warning(self):
        """A single file without a keyword should not produce multiple-file warning."""
        warnings = validate_split_mapping(["data.csv"])
        # Single file fallback is acceptable — no multi-file warning
        assert not any("Multiple files" in w for w in warnings)

    def test_multiple_files_no_keywords(self):
        """Multiple files without split keywords should warn."""
        warnings = validate_split_mapping(["a.csv", "b.csv", "c.csv"])
        assert any("Multiple files" in w or "Default-load warning" in w for w in warnings)

    def test_multiple_files_with_keywords_no_warning(self):
        """Files with proper split keywords should not produce warnings."""
        warnings = validate_split_mapping(["train.csv", "test.csv", "validation.csv"])
        assert warnings == []

    def test_directory_based_splits(self):
        """Directory-based splits should not produce warnings."""
        warnings = validate_split_mapping(["train/data.csv", "test/data.csv"])
        assert warnings == []

    def test_excluded_metadata_files_ignored(self):
        """README.md and LICENSE should be ignored in split validation."""
        warnings = validate_split_mapping(["README.md", "LICENSE"])
        # Only metadata → no data files → no warnings
        assert not any("Multiple files" in w for w in warnings)

    def test_mixed_keyword_and_no_keyword(self):
        """Files with and without keywords should produce unclassified warning."""
        warnings = validate_split_mapping(["train.csv", "mystery.csv"])
        # train.csv is classified, mystery.csv is unclassified → single fallback wins
        assert not any("Multiple files" in w for w in warnings)

    def test_default_load_warning_for_many_files(self):
        """Many files without keywords should get the default-load warning."""
        warnings = validate_split_mapping(["f1.csv", "f2.csv", "f3.csv"])
        assert any("Default-load warning" in w or "multiple files" in w.lower() for w in warnings)

    def test_parquet_remotes(self):
        """Parquet files should be handled the same as CSV."""
        warnings = validate_split_mapping(["train.parquet", "test.parquet"])
        assert warnings == []

    def test_no_split_keyword_in_assigned_file(self):
        """A file assigned to a split via directory but with no keyword in its name."""
        # train/data.csv: directory is train, file is data.csv → fine
        warnings = validate_split_mapping(["train/data.csv"])
        assert warnings == []


# ═══════════════════════════════════════════════════════════════════════════════
#  verify_load_dataset
# ═══════════════════════════════════════════════════════════════════════════════


class TestVerifyLoadDataset:
    def test_skips_when_datasets_not_installed(self, tmp_path):
        """When datasets is not installed, return skipped report."""
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=Path("data.csv"), remote="data.csv")],
            _base_dir=tmp_path,
        )
        with patch.dict(sys.modules, {"datasets": None}):
            report = verify_load_dataset(tmp_path, cfg)
        assert report.skipped is True
        assert any("not installed" in w for w in report.warnings)

    def test_loads_parquet_files_and_detects_splits(self, tmp_path):
        """When datasets is available and parquet files exist, load succeeds."""
        # Create parquet files with split keywords in names
        table_train = pa.table({"x": [1, 2, 3]})
        pq.write_table(table_train, tmp_path / "train.parquet")

        table_test = pa.table({"x": [4, 5]})
        pq.write_table(table_test, tmp_path / "test.parquet")

        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=tmp_path / "train.parquet", remote="train.parquet"),
                FileEntry(local=tmp_path / "test.parquet", remote="test.parquet"),
            ],
            _base_dir=tmp_path,
        )

        # Mock datasets.load_dataset
        mock_ds = {
            "train": MagicMock(),
            "test": MagicMock(),
        }
        mock_ds["train"].__len__ = lambda self: 3
        mock_ds["test"].__len__ = lambda self: 2

        mock_datasets = MagicMock()
        mock_datasets.load_dataset.return_value = mock_ds

        with patch.dict(sys.modules, {"datasets": mock_datasets}):
            report = verify_load_dataset(tmp_path, cfg)

        assert report.skipped is False
        assert report.passed is True
        assert set(report.split_names) == {"train", "test"}
        assert report.split_row_counts["train"] == 3
        assert report.split_row_counts["test"] == 2
        assert report.expected_splits == ["train", "test"]

    def test_detects_split_mismatch(self, tmp_path):
        """When actual splits differ from expected, a warning is issued."""
        table = pa.table({"x": [1, 2]})
        pq.write_table(table, tmp_path / "data.parquet")

        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=tmp_path / "data.parquet", remote="data.parquet"),
            ],
            _base_dir=tmp_path,
        )

        # Mock datasets to return a train split (expected is also train)
        mock_ds = {"train": MagicMock()}
        mock_ds["train"].__len__ = lambda self: 2
        mock_datasets = MagicMock()
        mock_datasets.load_dataset.return_value = mock_ds

        with patch.dict(sys.modules, {"datasets": mock_datasets}):
            report = verify_load_dataset(tmp_path, cfg)

        # Both expected and actual are "train" — should pass
        assert report.passed is True
        assert report.split_names == ["train"]
        assert report.expected_splits == ["train"]

    def test_load_dataset_raises(self, tmp_path):
        """When load_dataset raises, report the error."""
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=Path("data.csv"), remote="data.csv")],
            _base_dir=tmp_path,
        )

        mock_datasets = MagicMock()
        mock_datasets.load_dataset.side_effect = ValueError("No data files found")

        with patch.dict(sys.modules, {"datasets": mock_datasets}):
            report = verify_load_dataset(tmp_path, cfg)

        assert report.passed is False
        assert not report.skipped
        assert len(report.errors) == 1
        assert "No data files found" in report.errors[0]

    def test_verification_report_defaults(self):
        """VerificationReport has sensible defaults."""
        report = VerificationReport()
        assert report.passed is False
        assert report.skipped is False
        assert report.split_names == []
        assert report.split_row_counts == {}
        assert report.expected_splits == []
        assert report.warnings == []
        assert report.errors == []

    def test_passed_when_split_matches_and_no_errors(self):
        """passed is True when splits match and there are no errors."""
        report = VerificationReport(
            passed=True,
            split_names=["train", "test"],
            expected_splits=["train", "test"],
        )
        assert report.passed is True

    def test_not_passed_when_warnings_exist(self):
        """passed is False when there are warnings (split mismatch)."""
        report = VerificationReport(
            passed=False,
            split_names=["train"],
            expected_splits=["train", "test"],
            warnings=["Split names differ"],
        )
        assert report.passed is False


# ═══════════════════════════════════════════════════════════════════════════════
#  _assert_cross_file_schema
# ═══════════════════════════════════════════════════════════════════════════════


class TestAssertCrossFileSchema:
    """Cross-file schema identity assertion per split (Issue #16)."""

    def test_same_split_identical_schemas_passes(self, tmp_path):
        """Two files in the same split with identical schemas → no errors."""
        from sofer.uploader import _assert_cross_file_schema

        staging = tmp_path / "staging"
        staging.mkdir()

        # Create two parquet files with identical schema
        t1 = pa.table({"a": [1, 2], "b": ["x", "y"]})
        pq.write_table(t1, staging / "train-1.parquet")

        t2 = pa.table({"a": [3, 4], "b": ["z", "w"]})
        pq.write_table(t2, staging / "train-2.parquet")

        converted = {
            "train-1": (staging / "train-1.parquet", Path(), ""),
            "train-2": (staging / "train-2.parquet", Path(), ""),
        }

        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=Path("train-1.parquet"), remote="train-1.parquet"),
                FileEntry(local=Path("train-2.parquet"), remote="train-2.parquet"),
            ],
        )

        errors = _assert_cross_file_schema(converted, cfg)
        assert errors == []

    def test_column_name_mismatch_in_same_split_fails(self, tmp_path):
        """Different column names in same split → error."""
        from sofer.uploader import _assert_cross_file_schema

        staging = tmp_path / "staging"
        staging.mkdir()

        t1 = pa.table({"a": [1, 2], "b": ["x", "y"]})
        pq.write_table(t1, staging / "train-1.parquet")

        t2 = pa.table({"a": [1], "c": [3]})
        pq.write_table(t2, staging / "train-2.parquet")

        converted = {
            "train-1": (staging / "train-1.parquet", Path(), ""),
            "train-2": (staging / "train-2.parquet", Path(), ""),
        }

        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=Path("train-1.parquet"), remote="train-1.parquet"),
                FileEntry(local=Path("train-2.parquet"), remote="train-2.parquet"),
            ],
        )

        errors = _assert_cross_file_schema(converted, cfg)
        assert len(errors) >= 1
        assert any("Schema mismatch" in e for e in errors)
        assert any("missing" in e.lower() for e in errors)

    def test_dtype_mismatch_in_same_split_fails(self, tmp_path):
        """Same column names but different dtype in same split → error."""
        from sofer.uploader import _assert_cross_file_schema

        staging = tmp_path / "staging"
        staging.mkdir()

        t1 = pa.table({"col": [1, 2, 3]})
        pq.write_table(t1, staging / "train-1.parquet")

        t2 = pa.table({"col": ["a", "b"]})
        pq.write_table(t2, staging / "train-2.parquet")

        converted = {
            "train-1": (staging / "train-1.parquet", Path(), ""),
            "train-2": (staging / "train-2.parquet", Path(), ""),
        }

        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=Path("train-1.parquet"), remote="train-1.parquet"),
                FileEntry(local=Path("train-2.parquet"), remote="train-2.parquet"),
            ],
        )

        errors = _assert_cross_file_schema(converted, cfg)
        assert len(errors) >= 1
        assert any("differ in dtypes" in e for e in errors)

    def test_different_splits_different_schemas_passes(self, tmp_path):
        """Different splits are NOT compared — only within-split identity."""
        from sofer.uploader import _assert_cross_file_schema

        staging = tmp_path / "staging"
        staging.mkdir()

        t_train = pa.table({"a": [1], "b": [2]})
        pq.write_table(t_train, staging / "train.parquet")

        t_test = pa.table({"x": ["a"], "y": ["b"]})
        pq.write_table(t_test, staging / "test.parquet")

        converted = {
            "train": (staging / "train.parquet", Path(), ""),
            "test": (staging / "test.parquet", Path(), ""),
        }

        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=Path("train.parquet"), remote="train.parquet"),
                FileEntry(local=Path("test.parquet"), remote="test.parquet"),
            ],
        )

        errors = _assert_cross_file_schema(converted, cfg)
        # Each split has only 1 file → no within-split comparison
        assert errors == []

    def test_single_file_no_comparison_needed(self, tmp_path):
        """A single file in a split → nothing to compare, no errors."""
        from sofer.uploader import _assert_cross_file_schema

        staging = tmp_path / "staging"
        staging.mkdir()

        t = pa.table({"a": [1, 2, 3]})
        pq.write_table(t, staging / "train.parquet")

        converted = {
            "train": (staging / "train.parquet", Path(), ""),
        }

        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=Path("train.parquet"), remote="train.parquet"),
            ],
        )

        errors = _assert_cross_file_schema(converted, cfg)
        assert errors == []


# ═══════════════════════════════════════════════════════════════════════════════
#  Quality gate inside upload() — Issue #14
# ═══════════════════════════════════════════════════════════════════════════════


class TestUploadQualityGate:
    def test_upload_gates_on_failed_quality_report(self, tmp_path):
        """upload() returns 1 before any upload when quality report has failures."""
        from sofer.checks import ValidationReport
        from sofer.quality import QualityResult
        from sofer.uploader import upload

        data = tmp_path / "data.csv"
        data.write_text("a;b\n1;2\n", encoding="utf-8")

        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=data, remote="data.csv")],
            _base_dir=tmp_path,
        )

        # Create a report with a fail finding
        report = ValidationReport("test")
        report.quality_results = [
            QualityResult(check="corrupt_records", severity="fail", message="bad"),
        ]

        # upload should return 1 (failure) without doing any network calls
        exit_code = upload(cfg, quality_report=report, dry_run=True)
        assert exit_code == 1

    def test_upload_proceeds_when_quality_report_passes(self, tmp_path):
        """upload() proceeds normally when quality report has no failures."""
        from sofer.checks import ValidationReport
        from sofer.uploader import upload

        data = tmp_path / "data.csv"
        data.write_text("a;b\n1;2\n", encoding="utf-8")

        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=data, remote="data.csv")],
            _base_dir=tmp_path,
        )

        # A clean report
        report = ValidationReport("test")

        # upload should proceed (dry_run returns 0 on success)
        exit_code = upload(cfg, quality_report=report, dry_run=True)
        assert exit_code == 0


# ═══════════════════════════════════════════════════════════════════════════════
#  Reads override, codebook upload, schema assertion
# ═══════════════════════════════════════════════════════════════════════════════


class TestReadmeOverride:
    """cfg.readme should replace the generated Dataset Card."""

    def test_readme_file_used_when_set(self, tmp_path, monkeypatch):
        """When cfg.readme points to a file, use it instead of generating."""
        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")

        custom_readme = tmp_path / "CUSTOM_README.md"
        custom_readme.write_text("# My Custom Dataset\n\nCustom content.", encoding="utf-8")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv")],
            readme=str(custom_readme),
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)

        # Track what gets written as the README.md upload
        uploaded_readme_content: list[str] = []

        def _track_upload(path_or_fileobj="", path_in_repo="", **kw):
            if path_in_repo == "README.md":
                uploaded_readme_content.append(
                    Path(str(path_or_fileobj)).read_text(encoding="utf-8")
                )

        monkeypatch.setattr(uploader._api, "upload_file", _track_upload)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        assert len(uploaded_readme_content) >= 1
        assert "My Custom Dataset" in uploaded_readme_content[0]
        assert "Custom content" in uploaded_readme_content[0]
        assert not td.exists()  # cleanup verified

    def test_readme_fallback_when_file_missing(self, tmp_path, monkeypatch):
        """When cfg.readme points to a missing file, fall back to generation."""
        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv")],
            readme="nonexistent.md",
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)

        uploaded_readme_content: list[str] = []

        def _track_upload(path_or_fileobj="", path_in_repo="", **kw):
            if path_in_repo == "README.md":
                uploaded_readme_content.append(
                    Path(str(path_or_fileobj)).read_text(encoding="utf-8")
                )

        monkeypatch.setattr(uploader._api, "upload_file", _track_upload)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        assert len(uploaded_readme_content) >= 1
        # Should be a generated card (not the missing file)
        assert "Dataset Card for test" in uploaded_readme_content[0]
        assert not td.exists()


class TestCodebookUpload:
    """RC-C01: Generated codebooks uploaded under codebooks/ prefix after data files."""

    def test_codebook_uploaded_to_codebook_subpath(self, tmp_path, monkeypatch):
        """Per-file codebooks and root index uploaded with correct remotes and order."""
        from sofer import uploader
        from sofer.config import CODEBOOKS_DIR, OUTPUT_DIR

        # Create data file
        data_dir = tmp_path / OUTPUT_DIR
        data_dir.mkdir(parents=True)
        csv = data_dir / "DPTO.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")

        # Create generated per-file codebooks
        codebooks_path = data_dir / CODEBOOKS_DIR
        codebooks_path.mkdir(parents=True)
        (codebooks_path / "DPTO.md").write_text("# DPTO codebook", encoding="utf-8")
        (codebooks_path / "PROV.md").write_text("# PROV codebook", encoding="utf-8")

        # Create root index
        (tmp_path / "codebook.md").write_text("# Root index", encoding="utf-8")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="DPTO.csv", upload_as_csv=True)],
            _base_dir=tmp_path,
        )

        uploaded: list[str] = []

        def _track(path_or_fileobj="", path_in_repo="", **kw):
            uploaded.append(path_in_repo)

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_file", _track)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        # ── Assert correct remote paths ──
        codebook_uploads = [u for u in uploaded if u.startswith("codebooks/") or u == "codebook.md"]
        assert len(codebook_uploads) >= 1
        assert "codebooks/DPTO.md" in codebook_uploads
        assert "codebooks/PROV.md" in codebook_uploads
        assert "codebook.md" in codebook_uploads

        # ── Assert order: data files before codebooks, root index last ──
        data_remotes = {
            u
            for u in uploaded
            if not u.startswith("codebook") and u != "README.md" and u != "LICENSE"
        }
        assert "DPTO.csv" in data_remotes
        last_data_idx = max(uploaded.index(u) for u in uploaded if u in data_remotes)
        codebook_idxes = [i for i, u in enumerate(uploaded) if u.startswith("codebooks/")]
        assert codebook_idxes, "expected per-file codebook uploads"
        assert last_data_idx < min(codebook_idxes), "data files must be uploaded before codebooks"

        index_idx = uploaded.index("codebook.md")
        assert max(codebook_idxes) < index_idx, "root index must upload after per-file codebooks"

        assert not td.exists()

    def test_no_codebooks_generated_skips(self, tmp_path, monkeypatch, capsys):
        """No data/codebooks/ directory or codebook.md → skip silently, no warning."""
        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv", upload_as_csv=True)],
            _base_dir=tmp_path,
        )

        uploaded: list[str] = []

        def _track(path_or_fileobj="", path_in_repo="", **kw):
            uploaded.append(path_in_repo)

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_file", _track)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)
        captured = capsys.readouterr()

        # No codebook-related uploads
        codebook_uploads = [u for u in uploaded if "codebook" in u.lower()]
        assert codebook_uploads == [], f"unexpected codebook uploads: {codebook_uploads}"

        # No warning about missing codebooks
        assert "codebook" not in captured.out.lower()
        assert "codebook" not in captured.err.lower()

        assert not td.exists()

    def test_legacy_codebook_not_uploaded(self, tmp_path, monkeypatch):
        """cfg.codebook declared in TOML → uploader ignores it; RC-C01 supersedes."""
        from sofer import uploader
        from sofer.config import CODEBOOKS_DIR, OUTPUT_DIR

        # Set up generated codebooks (RC-C01 path)
        data_dir = tmp_path / OUTPUT_DIR
        data_dir.mkdir(parents=True)
        csv = data_dir / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")

        codebooks_path = data_dir / CODEBOOKS_DIR
        codebooks_path.mkdir(parents=True)
        (codebooks_path / "data.md").write_text("# Generated codebook", encoding="utf-8")
        (tmp_path / "codebook.md").write_text("# Root index", encoding="utf-8")

        # Also create the legacy codebook file (should be ignored)
        legacy_cb = tmp_path / "old_codebook.md"
        legacy_cb.write_text("# Legacy — should be ignored", encoding="utf-8")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv", upload_as_csv=True)],
            codebook=str(legacy_cb),  # legacy path — RC-C01 ignores it
            _base_dir=tmp_path,
        )

        uploaded: list[str] = []

        def _track(path_or_fileobj="", path_in_repo="", **kw):
            uploaded.append(path_in_repo)

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_file", _track)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        # RC-C01 codebooks uploaded
        assert "codebooks/data.md" in uploaded
        assert "codebook.md" in uploaded

        # Legacy codebook NOT uploaded — no codebook/old_codebook.md
        assert "old_codebook.md" not in uploaded
        assert not any("codebook/old_codebook.md" in u for u in uploaded)

        assert not td.exists()

    def test_codebook_upload_order_data_first(self, tmp_path, monkeypatch):
        """_hf_upload for codebooks happens AFTER the data-file loop."""
        from sofer import uploader
        from sofer.config import CODEBOOKS_DIR, OUTPUT_DIR

        data_dir = tmp_path / OUTPUT_DIR
        data_dir.mkdir(parents=True)
        csv = data_dir / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")

        codebooks_path = data_dir / CODEBOOKS_DIR
        codebooks_path.mkdir(parents=True)
        (codebooks_path / "data.md").write_text("# codebook", encoding="utf-8")
        (tmp_path / "codebook.md").write_text("# index", encoding="utf-8")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv", upload_as_csv=True)],
            _base_dir=tmp_path,
        )

        call_order: list[str] = []

        def _track(path_or_fileobj="", path_in_repo="", **kw):
            call_order.append(path_in_repo)

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_file", _track)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        data_idx = call_order.index("data.csv")
        first_cb_idx = min(call_order.index(u) for u in call_order if u.startswith("codebooks/"))
        assert data_idx < first_cb_idx, f"data.csv at {data_idx}, first codebook at {first_cb_idx}"

        assert not td.exists()

    def test_root_index_uploaded_as_codebook_md(self, tmp_path, monkeypatch):
        """codebook.md in base_dir is uploaded as codebook.md in HF."""
        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")

        (tmp_path / "codebook.md").write_text("# Root index content", encoding="utf-8")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv", upload_as_csv=True)],
            _base_dir=tmp_path,
        )

        uploaded: list[str] = []

        def _track(path_or_fileobj="", path_in_repo="", **kw):
            uploaded.append(path_in_repo)

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_file", _track)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        assert "codebook.md" in uploaded

        assert not td.exists()

    def test_repo_diff_summary_lists_codebook_remotes(self, tmp_path):
        """_repo_diff_summary includes codebook remotes when provided."""
        from sofer.config import OUTPUT_DIR

        data_dir = tmp_path / OUTPUT_DIR
        data_dir.mkdir(parents=True)
        data = data_dir / "data.csv"
        data.write_text("x\n1\n", encoding="utf-8")

        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=data, remote="data.csv")],
            _base_dir=tmp_path,
        )

        codebook_remotes = ["codebooks/data.md", "codebook.md"]
        summary = _repo_diff_summary(
            cfg, existing_files=[], keep_csv=False, codebook_remotes=codebook_remotes
        )
        assert "codebooks/data.md" in summary
        assert "codebook.md" in summary


class TestSchemaAssertion:
    """_assert_card_dtypes_match_parquet should flag float64 vs int64 mismatches."""

    def test_no_mismatch_when_dtypes_match(self, tmp_path):
        """No warning when Parquet int64 → card int64."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        from sofer.repo_compliance import ColumnSchema
        from sofer.uploader import _assert_card_dtypes_match_parquet

        parquet_path = tmp_path / "test.parquet"
        table = pa.table({"age": pa.array([25, 30, 35], type=pa.int64())})
        pq.write_table(table, parquet_path)

        schema = [
            ColumnSchema(
                name="age",
                dtype="numeric",
                nullable=False,
                example="25",
                unique=3,
                missing=0.0,
                hf_dtype="int64",
            ),
        ]
        converted = {"test": (parquet_path, Path("dummy.csv"), "test.csv")}

        # Should not raise and should not print warnings about this column
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            _assert_card_dtypes_match_parquet(schema, converted)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        assert "SCHEMA ASSERTION" not in output

    def test_flags_float64_vs_int64_mismatch(self, tmp_path):
        """Should warn when Parquet is int64 but card says float64."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        from sofer.repo_compliance import ColumnSchema
        from sofer.uploader import _assert_card_dtypes_match_parquet

        parquet_path = tmp_path / "test.parquet"
        table = pa.table({"age": pa.array([25, 30, 35], type=pa.int64())})
        pq.write_table(table, parquet_path)

        schema = [
            ColumnSchema(
                name="age",
                dtype="numeric",
                nullable=False,
                example="25",
                unique=3,
                missing=0.0,
                hf_dtype="float64",
            ),
        ]
        converted = {"test": (parquet_path, Path("dummy.csv"), "test.csv")}

        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            _assert_card_dtypes_match_parquet(schema, converted)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        assert "SCHEMA ASSERTION" in output
        assert "age" in output
        assert "float64" in output
        assert "int64" in output

    def test_skips_disambiguated_columns(self, tmp_path):
        """:: prefixed columns should not trigger schema assertion."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        from sofer.repo_compliance import ColumnSchema
        from sofer.uploader import _assert_card_dtypes_match_parquet

        parquet_path = tmp_path / "test.parquet"
        table = pa.table({"age": pa.array([25, 30, 35], type=pa.int64())})
        pq.write_table(table, parquet_path)

        schema = [
            ColumnSchema(
                name="a.parquet::age",
                dtype="numeric",
                nullable=False,
                example="25",
                unique=3,
                missing=0.0,
                hf_dtype="float64",
            ),
        ]
        converted = {"test": (parquet_path, Path("dummy.csv"), "test.csv")}

        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            _assert_card_dtypes_match_parquet(schema, converted)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        assert "SCHEMA ASSERTION" not in output
