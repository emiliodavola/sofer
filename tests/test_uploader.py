"""Tests for split detection, repo inspection, remote path validation,
overwrite protection, split mapping validation, and load_dataset verification
in sofer.uploader, sofer.splits, and sofer.verification."""

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
from sofer.uploader import (
    _check_overwrite_protection,
    _repo_diff_summary,
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
        """Auto-generated files bypass protection even in non-interactive mode."""
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        protected = _check_overwrite_protection(
            existing_files=["README.md", "LICENSE"],
            force=False,
        )
        assert "readme.md" not in protected
        assert "license" not in protected

    def test_not_force_one_file_each(self, monkeypatch):
        """README.md is auto-generated — never protected."""
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        protected = _check_overwrite_protection(
            existing_files=["README.md"],
            force=False,
        )
        assert "readme.md" not in protected
        assert "license" not in protected

    def test_readme_always_uploaded_even_when_in_repo(self, monkeypatch):
        """README.md in existing_files → never protected (auto-generated)."""
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        protected = _check_overwrite_protection(
            existing_files=["README.md"],
            force=False,
        )
        assert "readme.md" not in protected

    def test_license_always_uploaded_even_when_in_repo(self, monkeypatch):
        """LICENSE in existing_files → never protected (auto-generated)."""
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        protected = _check_overwrite_protection(
            existing_files=["LICENSE"],
            force=False,
        )
        assert "license" not in protected

    def test_codebook_missing_advisory(self, tmp_path, monkeypatch, capsys):
        """No cache/codebooks/ dir and no codebook.md → advisory printed to stderr."""
        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv", upload_as_csv=True)],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)
        captured = capsys.readouterr()

        assert "sofer codebook" in captured.err.lower(), (
            "Expected advisory on stderr, got: " + repr(captured.err)
        )


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
        import shutil as _shutil

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
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(_shutil, "rmtree", lambda p, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        # README.md should be staged in staging_root/repo/ with custom content
        staging_root = Path(td) / "repo"
        readme = staging_root / "README.md"
        assert readme.is_file(), "README.md missing from staging_root"
        content = readme.read_text(encoding="utf-8")
        assert "My Custom Dataset" in content
        assert "Custom content" in content

    def test_readme_fallback_when_file_missing(self, tmp_path, monkeypatch):
        """When cfg.readme points to a missing file, fall back to generation."""
        import shutil as _shutil

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
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(_shutil, "rmtree", lambda p, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        # README.md should be staged with generated card content
        staging_root = Path(td) / "repo"
        readme = staging_root / "README.md"
        assert readme.is_file(), "README.md missing from staging_root"
        content = readme.read_text(encoding="utf-8")
        assert "Dataset Card for test" in content


class TestCodebookUpload:
    """RC-C01: Generated codebooks uploaded under codebooks/ prefix after data files."""

    def test_codebook_uploaded_to_codebook_subpath(self, tmp_path, monkeypatch):
        """Per-file codebooks and root index staged with correct paths in staging_root."""
        import shutil as _shutil

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

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(_shutil, "rmtree", lambda p, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        staging_root = Path(td) / "repo"
        assert staging_root.is_dir()

        # Codebooks at codebooks/ relative to staging root
        cb_dpto = staging_root / "codebooks" / "DPTO.md"
        assert cb_dpto.is_file(), f"Missing: {cb_dpto}"
        assert cb_dpto.read_text(encoding="utf-8") == "# DPTO codebook"

        cb_prov = staging_root / "codebooks" / "PROV.md"
        assert cb_prov.is_file(), f"Missing: {cb_prov}"
        assert cb_prov.read_text(encoding="utf-8") == "# PROV codebook"

        # Root index at codebook.md
        root_idx = staging_root / "codebook.md"
        assert root_idx.is_file(), f"Missing: {root_idx}"
        assert root_idx.read_text(encoding="utf-8") == "# Root index"

        # Data file also staged
        assert (staging_root / "DPTO.csv").is_file(), "Data file missing from staging"

    def test_no_codebooks_generated_skips(self, tmp_path, monkeypatch, capsys):
        """No cache/codebooks/ directory or codebook.md → advisory on stderr, no codebook staged."""
        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv", upload_as_csv=True)],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)
        captured = capsys.readouterr()

        staging_root = Path(td) / "repo"

        # No codebook-related files staged
        codebook_files = [str(f.relative_to(staging_root)) for f in staging_root.rglob("codebook*")]
        assert codebook_files == [], f"unexpected codebook files staged: {codebook_files}"

        # Advisory printed to stderr (not stdout)
        assert "sofer codebook" in captured.err.lower()
        assert not Path(td).exists()

    def test_legacy_codebook_not_uploaded(self, tmp_path, monkeypatch):
        """cfg.codebook declared in TOML → staging ignores it; RC-C01 supersedes."""
        import shutil as _shutil

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

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(_shutil, "rmtree", lambda p, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        staging_root = Path(td) / "repo"

        # RC-C01 codebooks staged
        assert (staging_root / "codebooks" / "data.md").is_file()
        assert (staging_root / "codebook.md").is_file()

        # Legacy codebook NOT staged
        assert not (staging_root / "old_codebook.md").exists()
        assert not (staging_root / "codebook" / "old_codebook.md").exists()

    def test_codebook_upload_order_data_first(self, tmp_path, monkeypatch):
        """All files (data + codebooks) are staged together; upload_folder handles
        the batch. Order is irrelevant since it's a single call."""
        import shutil as _shutil

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

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(_shutil, "rmtree", lambda p, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        staging_root = Path(td) / "repo"

        # Both data and codebooks are staged together
        assert (staging_root / "data.csv").is_file(), "Data file missing from staging"
        assert (staging_root / "codebooks" / "data.md").is_file(), "Codebook missing from staging"
        assert (staging_root / "codebook.md").is_file(), "Root index missing from staging"

    def test_root_index_uploaded_as_codebook_md(self, tmp_path, monkeypatch):
        """codebook.md in base_dir is staged as codebook.md in staging root."""
        import shutil as _shutil

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

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(_shutil, "rmtree", lambda p, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        staging_root = Path(td) / "repo"
        root_idx = staging_root / "codebook.md"
        assert root_idx.is_file(), f"Missing: {root_idx}"
        assert root_idx.read_text(encoding="utf-8") == "# Root index content"

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




# ═══════════════════════════════════════════════════════════════════════════════
#  Batch Hugging Face Uploads — staging + upload_folder (Issue #38)
# ═══════════════════════════════════════════════════════════════════════════════


class TestBatchStaging:
    """Tests for batch HF uploads: staging mirror, codebook copy, single
    upload_folder call."""

    def test_parquet_placed_in_remote_subdirs(self, tmp_path, monkeypatch):
        """Converted Parquet files are placed in staging_root/<remote-path>/
        subdirectories, not flat in tmpdir. (Task 3.1)"""
        import shutil as _shutil

        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data/PROV/data.csv")],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(_shutil, "rmtree", lambda p, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        staging_root = Path(td) / "repo"
        assert staging_root.is_dir(), f"staging_root not created: {staging_root}"

        expected = staging_root / "data" / "PROV" / "data.parquet"
        assert expected.is_file(), (
            f"Expected {expected}, found files: {list(staging_root.rglob('*'))}"
        )

        flat = staging_root / "data.parquet"
        assert not flat.exists(), (
            "Parquet should NOT be flat in staging root — "
            "must be in subdirectories matching remote path"
        )

    def test_codebooks_staged_in_tmpdir(self, tmp_path, monkeypatch):
        """Generated codebooks and root index copied to staging_root with
        correct relative paths. (Task 3.2)"""
        import shutil as _shutil

        from sofer import uploader
        from sofer.config import CODEBOOKS_DIR, OUTPUT_DIR

        data_dir = tmp_path / OUTPUT_DIR
        data_dir.mkdir(parents=True)
        csv = data_dir / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")

        codebooks_path = data_dir / CODEBOOKS_DIR
        codebooks_path.mkdir(parents=True)
        (codebooks_path / "DPTO.md").write_text("# DPTO codebook", encoding="utf-8")
        (codebooks_path / "PROV.md").write_text("# PROV codebook", encoding="utf-8")
        (tmp_path / "codebook.md").write_text("# Root index", encoding="utf-8")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv", upload_as_csv=True)],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(_shutil, "rmtree", lambda p, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        staging_root = Path(td) / "repo"
        assert staging_root.is_dir()

        cb_dpto = staging_root / "codebooks" / "DPTO.md"
        assert cb_dpto.is_file(), f"Missing: {cb_dpto}"
        assert cb_dpto.read_text(encoding="utf-8") == "# DPTO codebook"

        cb_prov = staging_root / "codebooks" / "PROV.md"
        assert cb_prov.is_file(), f"Missing: {cb_prov}"
        assert cb_prov.read_text(encoding="utf-8") == "# PROV codebook"

        root_idx = staging_root / "codebook.md"
        assert root_idx.is_file(), f"Missing: {root_idx}"
        assert root_idx.read_text(encoding="utf-8") == "# Root index"

    def test_upload_folder_called_once(self, tmp_path, monkeypatch):
        """_hf_upload_folder is called exactly once; _hf_upload is NOT called
        for individual files. (Task 3.3)"""
        import shutil as _shutil

        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv")],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(_shutil, "rmtree", lambda p, **kw: None)

        upload_folder_calls: list[tuple] = []
        upload_file_calls: list[tuple] = []

        orig_upload_folder = uploader._hf_upload_folder
        orig_upload = uploader._hf_upload

        def _track_upload_folder(*args, **kwargs):
            upload_folder_calls.append(args)
            return orig_upload_folder(*args, **kwargs)

        def _track_upload(*args, **kwargs):
            upload_file_calls.append(args)
            return orig_upload(*args, **kwargs)

        monkeypatch.setattr(uploader, "_hf_upload_folder", _track_upload_folder)
        monkeypatch.setattr(uploader, "_hf_upload", _track_upload)

        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_file", lambda *a, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        exit_code = uploader.upload(cfg)

        assert (
            len(upload_folder_calls) == 1
        ), f"Expected 1 upload_folder call, got {len(upload_folder_calls)}"

        staging_root = Path(td) / "repo"
        assert staging_root.is_dir(), "staging_root not created"
        call_path = Path(upload_folder_calls[0][1]) if len(upload_folder_calls) > 0 else None
        assert call_path == staging_root, f"Called with {call_path}, expected {staging_root}"

        assert len(upload_file_calls) == 0, (
            f"_hf_upload was called {len(upload_file_calls)} times — "
            f"should be 0 after batch staging"
        )

        assert exit_code == 0

    def test_upload_folder_failure_sets_fail(self, tmp_path, monkeypatch):
        """When _hf_upload_folder raises, exit_code=1 and tmpdir is cleaned up.
        (Task 3.4)"""
        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv")],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)

        def _failing_upload_folder(*args, **kwargs):
            raise RuntimeError("Simulated network failure")

        monkeypatch.setattr(uploader, "_hf_upload_folder", _failing_upload_folder)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        exit_code = uploader.upload(cfg)

        assert exit_code == 1, f"Expected exit_code 1, got {exit_code}"
        assert not Path(td).exists(), f"tmpdir should be cleaned up, but {td} still exists"

    def test_not_found_files_skipped_in_staging(self, tmp_path, monkeypatch):
        """Files that don't exist on disk are skipped during staging, not
        uploaded. (Task 1.3)"""
        import shutil as _shutil

        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")

        missing = tmp_path / "missing.csv"

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[
                FileEntry(local=csv, remote="data.csv"),
                FileEntry(local=missing, remote="missing.csv"),
            ],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(_shutil, "rmtree", lambda p, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        staging_root = Path(td) / "repo"

        data_files = [
            str(f.relative_to(staging_root))
            for f in staging_root.rglob("*")
            if f.is_file()
        ]
        assert any("data" in f for f in data_files), f"data file not found in staging: {data_files}"

        missing_files = [f for f in data_files if "missing" in f]
        assert missing_files == [], f"NOT FOUND file was staged: {missing_files}"

    def test_non_csv_files_copied_to_staging(self, tmp_path, monkeypatch):
        """Non-CSV files (e.g., .parquet directly) are copied to staging_root
        preserving their remote path."""
        import shutil as _shutil

        import pyarrow as pa
        import pyarrow.parquet as pq

        from sofer import uploader

        parquet_file = tmp_path / "direct.parquet"
        table = pa.table({"x": [1, 2, 3]})
        pq.write_table(table, parquet_file)

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=parquet_file, remote="subdir/direct.parquet")],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(_shutil, "rmtree", lambda p, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        staging_root = Path(td) / "repo"

        expected = staging_root / "subdir" / "direct.parquet"
        assert expected.is_file(), (
            f"Expected {expected}, found: {list(staging_root.rglob('*'))}"
        )

    def test_keep_csv_stages_original_csv(self, tmp_path, monkeypatch):
        """When keep_csv=True, both the Parquet and the original CSV are staged
        in the correct remote paths."""
        import shutil as _shutil

        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv")],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(_shutil, "rmtree", lambda p, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg, keep_csv=True)

        staging_root = Path(td) / "repo"

        parquet_file = staging_root / "data.parquet"
        csv_file = staging_root / "data.csv"

        assert parquet_file.is_file(), f"Parquet missing: {parquet_file}"
        assert csv_file.is_file(), f"CSV missing (keep_csv=True): {csv_file}"

    def test_compliance_files_staged_in_staging_root(self, tmp_path, monkeypatch):
        """README.md and LICENSE are staged in staging_root (not flat in tmpdir)."""
        import shutil as _shutil

        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv", upload_as_csv=True)],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(_shutil, "rmtree", lambda p, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        staging_root = Path(td) / "repo"
        readme = staging_root / "README.md"
        license_file = staging_root / "LICENSE"

        assert readme.is_file(), "README.md missing from staging_root"
        assert license_file.is_file(), "LICENSE missing from staging_root"
        assert "Dataset Card for test" in readme.read_text(encoding="utf-8")
