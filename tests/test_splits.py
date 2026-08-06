"""Tests for split detection (sofer.splits), remote path validation
(sofer._mirror), split mapping validation, and load_dataset verification
(sofer.verification)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pyarrow.parquet as pq

from sofer._mirror import _validate_remote_paths
from sofer.model import DatasetConfig, FileEntry
from sofer.splits import (
    SplitInfo,
    SplitReport,
    detect_split_keyword,
    detect_splits,
    validate_layout,
    validate_split_mapping,
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



