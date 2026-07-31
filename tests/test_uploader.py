"""Tests for split detection, repo inspection, remote path validation, and
overwrite protection in data_uploader.uploader and data_uploader.splits."""

from __future__ import annotations

from pathlib import Path

from data_uploader.model import DatasetConfig, FileEntry
from data_uploader.splits import (
    SplitInfo,
    SplitReport,
    detect_split_keyword,
    detect_splits,
    validate_layout,
)
from data_uploader.uploader import (
    _check_overwrite_protection,
    _repo_diff_summary,
    _validate_remote_paths,
)

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
