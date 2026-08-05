"""Tests for sofer.repo_compliance — Dataset Card, LICENSE, schema report."""

from pathlib import Path

import pytest
import yaml

from sofer.model import DatasetConfig, FileEntry
from sofer.repo_compliance import (
    _SIZE_CATEGORIES,
    ColumnSchema,
    _csv_values_look_like_bool,
    _parquet_to_hf_dtype,
    _validate_size_category,
    build_dataset_card,
    build_license_file,
    build_schema_report,
    normalize_header,
)

# ── ColumnSchema ──────────────────────────────────────────────────────────────


class TestColumnSchema:
    """Dataclass structure and defaults."""

    def test_minimal_instantiation(self):
        """All fields should be required at construction."""
        cs = ColumnSchema(
            name="age",
            dtype="numeric",
            nullable=True,
            example="42",
            unique=10,
            missing=0.0,
        )
        assert cs.name == "age"
        assert cs.dtype == "numeric"
        assert cs.nullable is True
        assert cs.example == "42"
        assert cs.unique == 10
        assert cs.missing == 0.0

    def test_field_types(self):
        """Field types should match the dataclass definition."""
        cs = ColumnSchema(
            name="color",
            dtype="categorical/text",
            nullable=False,
            example="red",
            unique=3,
            missing=50.0,
        )
        assert isinstance(cs.name, str)
        assert isinstance(cs.dtype, str)
        assert isinstance(cs.nullable, bool)
        assert isinstance(cs.example, str)
        assert isinstance(cs.unique, int)
        assert isinstance(cs.missing, float)


# ── build_license_file ────────────────────────────────────────────────────────


class TestBuildLicenseFile:
    """License file generation — known SPDX, unknown, empty, restricted."""

    def test_known_spdx_cc0(self):
        """cc0-1.0 should contain its descriptive name."""
        result = build_license_file("cc0-1.0")
        assert "Creative Commons Zero v1.0 Universal" in result

    def test_known_spdx_mit(self):
        """mit should contain MIT License text."""
        result = build_license_file("mit")
        assert "MIT License" in result

    def test_known_spdx_apache(self):
        """apache-2.0 should contain Apache text."""
        result = build_license_file("apache-2.0")
        assert "Apache License, Version 2.0" in result

    def test_known_spdx_cc_by(self):
        """cc-by-4.0 should contain Attribution text."""
        result = build_license_file("cc-by-4.0")
        assert "Creative Commons Attribution 4.0" in result

    def test_known_spdx_cc_by_sa(self):
        """cc-by-sa-4.0 should contain ShareAlike text."""
        result = build_license_file("cc-by-sa-4.0")
        assert "Creative Commons Attribution-ShareAlike 4.0" in result

    def test_known_spdx_unlicense(self):
        """unlicense should contain public domain text."""
        result = build_license_file("unlicense")
        assert "free and unencumbered" in result

    def test_known_spdx_pddl(self):
        """pddl should contain PDDL text."""
        result = build_license_file("pddl")
        assert "Open Data Commons Public Domain Dedication and License" in result

    def test_unknown_spdx_returns_descriptive_fallback(self):
        """Non-SPDX string should produce a descriptive fallback."""
        result = build_license_file("made-up-1.0")
        assert "This dataset is shared under the following terms: made-up-1.0" in result
        assert "choosealicense.com" in result

    def test_empty_returns_generic_fallback(self):
        """Empty string should return the no-license-declared message."""
        result = build_license_file("")
        assert "No license has been declared" in result
        assert "choosealicense.com" in result

    def test_restricted_returns_generic_fallback(self):
        """ "restricted" should return the same generic fallback as empty."""
        result = build_license_file("restricted")
        assert "No license has been declared" in result
        assert "choosealicense.com" in result

    def test_case_insensitive_lookup(self):
        """SPDX lookup should be case-insensitive."""
        result = build_license_file("CC0-1.0")
        assert "Creative Commons Zero v1.0 Universal" in result


# ── build_schema_report ───────────────────────────────────────────────────────


class TestBuildSchemaReport:
    """CSV schema analysis — happy path, edge cases, error handling."""

    def test_single_csv_numeric_and_text(self, tmp_path):
        """A CSV with numeric and text columns should return correct types."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("id;name;age\n1;Alice;30\n2;Bob;25\n", encoding="utf-8-sig")
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv_path, remote="data.csv")],
            _base_dir=tmp_path,
        )
        schema = build_schema_report(cfg)
        assert len(schema) == 3

        by_name = {s.name: s for s in schema}
        assert by_name["id"].dtype == "numeric"
        assert by_name["name"].dtype == "categorical/text"
        assert by_name["age"].dtype == "numeric"

    def test_csv_with_missing_values(self, tmp_path):
        """Missing values should be reflected in nullable and missing%."""
        csv_path = tmp_path / "missing.csv"
        csv_path.write_text("val\n10\nNA\n\n30\nMISSING\n", encoding="utf-8-sig")
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv_path, remote="missing.csv")],
            _base_dir=tmp_path,
        )
        schema = build_schema_report(cfg)
        assert len(schema) == 1
        assert schema[0].nullable is True
        # 3 missing out of 5 data rows → 60.0%
        assert schema[0].missing == 60.0

    def test_no_csv_files(self, tmp_path):
        """A config with no CSV files should return an empty list."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[],
            _base_dir=tmp_path,
        )
        schema = build_schema_report(cfg)
        assert schema == []

    def test_column_name_collision_across_files(self, tmp_path):
        """Duplicate column names across files should skip the second occurrence."""
        a = tmp_path / "file_a.csv"
        a.write_text("value\n1\n2\n", encoding="utf-8-sig")
        b = tmp_path / "file_b.csv"
        b.write_text("value\n3\n4\n", encoding="utf-8-sig")
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[
                FileEntry(local=a, remote="file_a.csv"),
                FileEntry(local=b, remote="file_b.csv"),
            ],
            _base_dir=tmp_path,
        )
        schema = build_schema_report(cfg)
        names = [s.name for s in schema]
        # Only first occurrence kept; second duplicate skipped
        assert names == ["value"]

    def test_file_not_found_skipped_silently(self, tmp_path):
        """A missing CSV file should be skipped without raising."""
        existing = tmp_path / "exists.csv"
        existing.write_text("x\n1\n", encoding="utf-8-sig")
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[
                FileEntry(local=existing, remote="exists.csv"),
                FileEntry(local=tmp_path / "ghost.csv", remote="ghost.csv"),
            ],
            _base_dir=tmp_path,
        )
        schema = build_schema_report(cfg)
        # Only the existing file's column should appear
        assert len(schema) == 1

    def test_recursive_entries_skipped(self, tmp_path):
        """Recursive directory entries should not be analysed as CSVs."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("x\n1\n", encoding="utf-8-sig")
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[
                FileEntry(local=tmp_path / "subdir", remote="subdir/", recursive=True),
                FileEntry(local=csv_path, remote="data.csv"),
            ],
            _base_dir=tmp_path,
        )
        schema = build_schema_report(cfg)
        assert len(schema) == 1  # only the non-recursive file

    def test_non_csv_files_skipped(self, tmp_path):
        """Non-.csv files should be skipped."""
        txt_path = tmp_path / "notes.txt"
        txt_path.write_text("hello\n", encoding="utf-8")
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=txt_path, remote="notes.txt")],
            _base_dir=tmp_path,
        )
        schema = build_schema_report(cfg)
        assert schema == []


# ── build_dataset_card ────────────────────────────────────────────────────────


class TestBuildDatasetCard:
    """Dataset Card generation — frontmatter, body sections, edge cases."""

    def test_happy_path_full_meta(self):
        """Fully specified config should produce frontmatter + all sections."""
        cfg = DatasetConfig(
            name="my-dataset",
            repo_id="user/my-dataset",
            description="A test dataset",
            license="cc0-1.0",
            source="Org",
            language=["en"],
            pretty_name="My Dataset",
            task_categories=["tabular-classification"],
            size_categories="1K<n<10K",
            tags=["survey"],
        )
        schema = [
            ColumnSchema(
                name="age",
                dtype="numeric",
                nullable=False,
                example="30",
                unique=10,
                missing=0.0,
            ),
        ]
        result = build_dataset_card(cfg, schema)

        # YAML frontmatter
        assert result.startswith("---\n")
        assert "pretty_name: My Dataset" in result
        assert "language:" in result
        assert "license: cc0-1.0" in result
        assert "task_categories:" in result
        assert "size_categories:" in result

        # Body sections (official HF template format)
        assert "## Dataset Details" in result
        assert "### Dataset Description" in result
        assert "## Dataset Structure" in result
        assert "### Data Fields" in result
        assert "## License" in result
        assert "## Citation" in result

    def test_minimal_config_placeholders(self):
        """Minimal config should use [Not specified] placeholders."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[
                FileEntry(local=Path("data.csv"), remote="data.csv"),
            ],
        )
        result = build_dataset_card(cfg, schema=[])

        assert "pretty_name: test" in result
        assert "[Not specified]" in result
        assert "dataset_info" not in result  # empty schema → no features block

    def test_empty_schema_no_codebook_table(self):
        """Empty schema should not include a Data Fields section."""
        cfg = DatasetConfig(name="test", repo_id="user/test")
        result = build_dataset_card(cfg, schema=[])
        assert "### Data Fields" not in result

    def test_recipe_inlined(self):
        """Recipe content should appear in a fenced code block."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            recipe="recipe.R",
        )
        schema = []
        recipe = "library(tidyverse)\ndata <- read.csv('input.csv')"
        result = build_dataset_card(cfg, schema, recipe_content=recipe)

        assert "#### Processing Recipe" in result
        assert "```r" in result
        assert "library(tidyverse)" in result

    def test_recipe_missing_none(self):
        """None recipe_content with declared recipe should show 'not found'."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            recipe="missing.R",
        )
        result = build_dataset_card(cfg, schema=[], recipe_content=None)
        assert "Recipe file declared but not found" in result
        assert "missing.R" in result

    def test_no_recipe_not_mentioned(self):
        """Config without recipe should not produce a Processing Recipe section."""
        cfg = DatasetConfig(name="test", repo_id="user/test")
        result = build_dataset_card(cfg, schema=[])
        assert "#### Processing Recipe" not in result

    def test_no_files_tidy_desc(self):
        """Config with no files should say 'No data files declared.'"""
        cfg = DatasetConfig(name="test", repo_id="user/test", files=[])
        result = build_dataset_card(cfg, schema=[])
        assert "No data files declared" in result

    def test_citation_section(self):
        """Citation should appear in its section."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            citation="@article{key}",
        )
        result = build_dataset_card(cfg, schema=[])
        assert "@article{key}" in result


# ── TestUploadCompliance (mocked integration) ─────────────────────────────────


class TestUploadCompliance:
    """Upload orchestration — compliance call order, tempdir cleanup, error prop."""

    def _mock_hf_api(self, monkeypatch):
        """Mock huggingface_hub API calls used by uploader."""
        from sofer import uploader

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_file", lambda *a, **kw: None)

    def test_compliance_called_before_upload(self, tmp_path, monkeypatch):
        """Compliance functions should be called — verify via mocked tracking."""
        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv")],
            _base_dir=tmp_path,
        )

        self._mock_hf_api(monkeypatch)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        result = uploader.upload(cfg)
        assert result == 0
        # Tempdir was cleaned up (success path)
        assert not td.exists()

    def test_upload_order_readme_license_data(self, tmp_path, monkeypatch):
        """All files (README, LICENSE, data) are staged together in staging_root
        for batch upload."""
        import shutil

        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv")],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(shutil, "rmtree", lambda p, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        staging_root = td / "repo"
        assert (staging_root / "README.md").is_file(), "README.md missing"
        assert (staging_root / "LICENSE").is_file(), "LICENSE missing"

        # Data file (.parquet after conversion) is also staged
        parquet_files = list(staging_root.rglob("*.parquet"))
        assert len(parquet_files) >= 1, "No .parquet file found in staging"

    def test_tempdir_cleanup_on_success(self, tmp_path, monkeypatch):
        """Temp directory should be cleaned up after successful upload."""
        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv")],
            _base_dir=tmp_path,
        )

        self._mock_hf_api(monkeypatch)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)
        assert not td.exists()

    def test_tempdir_cleanup_on_exception(self, tmp_path, monkeypatch):
        """Temp directory should be cleaned up even when compliance raises."""
        from sofer import uploader

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[],
            _base_dir=tmp_path,
        )

        self._mock_hf_api(monkeypatch)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        # Make build_license_file raise (happens AFTER tempdir is created)
        def _raise_boom(_lic):
            raise RuntimeError("boom")

        monkeypatch.setattr(uploader, "build_license_file", _raise_boom)

        try:
            uploader.upload(cfg)
        except RuntimeError:
            pass

        assert not td.exists()

    def test_schema_exception_propagates(self, tmp_path, monkeypatch):
        """Exception from build_schema_report should propagate to caller."""
        from sofer import uploader

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[],
            _base_dir=tmp_path,
        )

        def failing_schema(*a, **kw):
            raise ValueError("bad csv")

        monkeypatch.setattr(uploader, "build_schema_report", failing_schema)
        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        with pytest.raises(ValueError, match="bad csv"):
            uploader.upload(cfg)

        assert not td.exists()


# ═══════════════════════════════════════════════════════════════════════════════
#  Parquet-aware schema report tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBuildSchemaReportParquet:
    """build_schema_report reading from Parquet — native types, nullable, column names."""

    def _write_parquet(self, tmp_path, name, data, schema=None):
        """Helper: write a small Parquet file and return its path."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        path = tmp_path / name
        if schema:
            table = pa.Table.from_pydict(data, schema=schema)
        else:
            table = pa.Table.from_pydict(data)
        pq.write_table(table, path)
        return path

    def test_parquet_happy_path(self, tmp_path):
        """Schema from Parquet should return correct column names and types."""
        _ = self._write_parquet(
            tmp_path,
            "survey.parquet",
            {"age": [25, 30, 35], "name": ["Alice", "Bob", "Charlie"]},
        )
        csv_path = tmp_path / "survey.csv"
        csv_path.write_text("age;name\n25;Alice\n30;Bob\n35;Charlie\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv_path, remote="survey.csv")],
            _base_dir=tmp_path,
        )

        schema = build_schema_report(cfg, staging_dir=tmp_path)
        by_name = {s.name: s for s in schema}

        assert "age" in by_name
        assert "name" in by_name
        assert by_name["age"].dtype == "numeric"
        assert by_name["name"].dtype == "categorical/text"

    def test_integer_column_type(self, tmp_path):
        """Parquet INT64 column should map to numeric dtype."""
        _ = self._write_parquet(
            tmp_path,
            "ints.parquet",
            {"val": [1, 2, 3]},
        )
        csv_path = tmp_path / "ints.csv"
        csv_path.write_text("val\n1\n2\n3\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv_path, remote="ints.csv")],
            _base_dir=tmp_path,
        )

        schema = build_schema_report(cfg, staging_dir=tmp_path)
        assert schema[0].dtype == "numeric"

    def test_float_column_type(self, tmp_path):
        """Parquet FLOAT/DOUBLE column should map to numeric dtype."""
        _ = self._write_parquet(
            tmp_path,
            "floats.parquet",
            {"val": [1.5, 2.5, 3.5]},
        )
        csv_path = tmp_path / "floats.csv"
        csv_path.write_text("val\n1.5\n2.5\n3.5\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv_path, remote="floats.csv")],
            _base_dir=tmp_path,
        )

        schema = build_schema_report(cfg, staging_dir=tmp_path)
        assert schema[0].dtype == "numeric"

    def test_boolean_column_type(self, tmp_path):
        """Parquet BOOLEAN column should map to categorical/text dtype."""
        _ = self._write_parquet(
            tmp_path,
            "bools.parquet",
            {"flag": [True, False, True]},
        )
        csv_path = tmp_path / "bools.csv"
        csv_path.write_text("flag\ntrue\nfalse\ntrue\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv_path, remote="bools.csv")],
            _base_dir=tmp_path,
        )

        schema = build_schema_report(cfg, staging_dir=tmp_path)
        assert schema[0].dtype == "categorical/text"

    def test_nullable_from_parquet_schema(self, tmp_path):
        """nullable should match Parquet schema's nullable attribute."""
        import pyarrow as pa

        schema = pa.schema([pa.field("val", pa.int64(), nullable=False)])
        _ = self._write_parquet(
            tmp_path,
            "nonnull.parquet",
            {"val": [1, 2, 3]},
            schema=schema,
        )
        csv_path = tmp_path / "nonnull.csv"
        csv_path.write_text("val\n1\n2\n3\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv_path, remote="nonnull.csv")],
            _base_dir=tmp_path,
        )

        result = build_schema_report(cfg, staging_dir=tmp_path)
        assert result[0].nullable is False


class TestBuildSchemaReportParquetFallback:
    """Fallback to CSV when Parquet not available or upload_as_csv=True."""

    def test_no_staging_dir_falls_back_to_csv(self, tmp_path):
        """build_schema_report without staging_dir should use CSV path."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("x\n1\n2\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv_path, remote="data.csv")],
            _base_dir=tmp_path,
        )

        # No staging_dir → CSV path
        schema = build_schema_report(cfg)
        assert len(schema) == 1
        assert schema[0].name == "x"
        # CSV infer_column_type should say "numeric"
        assert schema[0].dtype == "numeric"

    def test_staging_dir_missing_parquet_falls_back(self, tmp_path):
        """staging_dir provided but .parquet missing should fall back to CSV."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("x\n1\n2\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv_path, remote="data.csv")],
            _base_dir=tmp_path,
        )

        # staging_dir exists but no .parquet in it
        empty_staging = tmp_path / "empty"
        empty_staging.mkdir()
        schema = build_schema_report(cfg, staging_dir=empty_staging)
        assert len(schema) == 1
        assert schema[0].dtype == "numeric"

    def test_upload_as_csv_override(self, tmp_path):
        """upload_as_csv=True should skip Parquet reading, fall back to CSV."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        # Write both CSV and Parquet to staging
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("x\n1\n2\n", encoding="utf-8-sig")

        # Parquet in same dir would normally be used
        table = pa.table({"x": [10, 20]})
        pq.write_table(table, tmp_path / "data.parquet")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[
                FileEntry(local=csv_path, remote="data.csv", upload_as_csv=True),
            ],
            _base_dir=tmp_path,
        )

        # staging_dir provided, Parquet exists, but upload_as_csv=True
        schema = build_schema_report(cfg, staging_dir=tmp_path)
        assert len(schema) == 1
        # Should read CSV, so x values are 1, 2 (not 10, 20)
        assert schema[0].dtype == "numeric"


class TestBuildSchemaReportSampling:
    """Unique/missing/example computed from Parquet row-group sample."""

    def test_unique_and_missing_from_parquet(self, tmp_path):
        """Unique count and missing percentage should be computed from sample."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        csv_path = tmp_path / "data.csv"
        csv_path.write_text("val\n1\nNA\n3\n\n5\n", encoding="utf-8-sig")

        # Write matching Parquet
        table = pa.table({"val": [1, None, 3, None, 5]})
        pq.write_table(table, tmp_path / "data.parquet")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv_path, remote="data.csv")],
            _base_dir=tmp_path,
        )

        schema = build_schema_report(cfg, staging_dir=tmp_path)
        assert len(schema) == 1
        assert schema[0].unique <= 5
        # 2 out of 5 missing → 40.0%
        assert schema[0].missing == 40.0

    def test_example_from_first_non_null(self, tmp_path):
        """Example should be the first non-null value from the sample."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        csv_path = tmp_path / "data.csv"
        csv_path.write_text("val\n\n\nAlice\nBob\n", encoding="utf-8-sig")

        table = pa.table({"val": [None, None, "Alice", "Bob", None]})
        pq.write_table(table, tmp_path / "data.parquet")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv_path, remote="data.csv")],
            _base_dir=tmp_path,
        )

        schema = build_schema_report(cfg, staging_dir=tmp_path)
        assert schema[0].example == "Alice"


class TestBuildSchemaReportDisambiguationParquet:
    """Column name collision across Parquet files."""

    def test_disambiguation_uses_parquet_prefix(self, tmp_path):
        """Duplicate column names across Parquet files should skip second occurrence."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        # CSV files (original source)
        csv_a = tmp_path / "a.csv"
        csv_a.write_text("value\n1\n", encoding="utf-8-sig")
        csv_b = tmp_path / "b.csv"
        csv_b.write_text("value\n2\n", encoding="utf-8-sig")

        # Parquet files in staging
        table_a = pa.table({"value": [1]})
        pq.write_table(table_a, tmp_path / "a.parquet")
        table_b = pa.table({"value": [2]})
        pq.write_table(table_b, tmp_path / "b.parquet")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[
                FileEntry(local=csv_a, remote="a.csv"),
                FileEntry(local=csv_b, remote="b.csv"),
            ],
            _base_dir=tmp_path,
        )

        schema = build_schema_report(cfg, staging_dir=tmp_path)
        names = [s.name for s in schema]
        # Only first occurrence kept
        assert names == ["value"]


# ═══════════════════════════════════════════════════════════════════════════════
#  NEW tests — GitHub issue #10: Dataset Card YAML compliance
# ═══════════════════════════════════════════════════════════════════════════════


# ── Helper ────────────────────────────────────────────────────────────────────


def _parse_frontmatter(result: str) -> dict:
    """Parse YAML frontmatter from a Dataset Card string."""
    assert result.startswith("---\n"), "Card must start with YAML frontmatter"
    end = result.index("\n---\n", 4)
    yaml_str = result[4:end]
    return yaml.safe_load(yaml_str)


# ── 1. dataset_info.features shape (list, not dict) ───────────────────────────


class TestDatasetInfoFeatures:
    """dataset_info.features must be a list of {name, dtype} dicts, not a col→type dict."""

    def test_features_is_list_of_dicts(self):
        """features should be a list of {name, dtype} objects."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            description="A dataset.",
            license="mit",
        )
        schema = [
            ColumnSchema(
                name="age",
                dtype="numeric",
                nullable=False,
                example="30",
                unique=10,
                missing=0.0,
                hf_dtype="int64",
            ),
            ColumnSchema(
                name="city",
                dtype="categorical/text",
                nullable=True,
                example="NYC",
                unique=5,
                missing=2.0,
                hf_dtype="string",
            ),
        ]
        result = build_dataset_card(cfg, schema)
        fm = _parse_frontmatter(result)

        di = fm["dataset_info"]
        features = di["features"]
        assert isinstance(features, list), f"features should be a list, got {type(features)}"
        assert len(features) == 2
        assert features[0] == {"name": "age", "dtype": "int64"}
        assert features[1] == {"name": "city", "dtype": "string"}

    def test_features_fallback_when_no_hf_dtype(self):
        """When hf_dtype is None, fall back to _HF_FEATURE_MAP from internal dtype."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
        )
        schema = [
            ColumnSchema(
                name="score",
                dtype="numeric",
                nullable=False,
                example="85",
                unique=50,
                missing=0.0,
                hf_dtype=None,
            ),
        ]
        result = build_dataset_card(cfg, schema)
        fm = _parse_frontmatter(result)
        features = fm["dataset_info"]["features"]
        # Fallback: numeric → float64
        assert features[0] == {"name": "score", "dtype": "float64"}

    def test_dataset_info_has_config_name(self):
        """dataset_info should include config_name."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
        )
        schema = [
            ColumnSchema(
                name="x", dtype="numeric", nullable=False, example="1", unique=1, missing=0.0
            ),
        ]
        result = build_dataset_card(cfg, schema)
        fm = _parse_frontmatter(result)
        assert "config_name" in fm["dataset_info"]

    def test_dataset_info_has_splits_when_files_present(self):
        """dataset_info should include splits when files are declared."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            files=[FileEntry(local=Path("data.csv"), remote="data.csv")],
        )
        schema = [
            ColumnSchema(
                name="x", dtype="numeric", nullable=False, example="1", unique=10, missing=0.0
            ),
        ]
        result = build_dataset_card(cfg, schema)
        fm = _parse_frontmatter(result)
        di = fm["dataset_info"]
        assert "splits" in di
        assert len(di["splits"]) >= 1
        assert "name" in di["splits"][0]
        assert "num_examples" in di["splits"][0]


# ── 2. Dtype fidelity ────────────────────────────────────────────────────────


class TestDtypeFidelity:
    """Parquet-originated ColumnSchema must carry accurate HF dtypes."""

    def test_int64_from_parquet(self):
        """Parquet int64 → hf_dtype == 'int64'."""
        import pyarrow as pa

        assert _parquet_to_hf_dtype(pa.int64()) == "int64"

    def test_int32_from_parquet(self):
        """Parquet int32 → hf_dtype == 'int32'."""
        import pyarrow as pa

        assert _parquet_to_hf_dtype(pa.int32()) == "int32"

    def test_float32_from_parquet(self):
        """Parquet float32 → hf_dtype == 'float32'."""
        import pyarrow as pa

        assert _parquet_to_hf_dtype(pa.float32()) == "float32"

    def test_float64_from_parquet(self):
        """Parquet float64 → hf_dtype == 'float64'."""
        import pyarrow as pa

        assert _parquet_to_hf_dtype(pa.float64()) == "float64"

    def test_bool_from_parquet(self):
        """Parquet bool → hf_dtype == 'bool'."""
        import pyarrow as pa

        assert _parquet_to_hf_dtype(pa.bool_()) == "bool"

    def test_string_from_parquet(self):
        """Parquet string → hf_dtype == 'string'."""
        import pyarrow as pa

        assert _parquet_to_hf_dtype(pa.string()) == "string"

    def test_date32_from_parquet(self):
        """Parquet date32 → hf_dtype == 'date32'."""
        import pyarrow as pa

        assert _parquet_to_hf_dtype(pa.date32()) == "date32"

    def test_timestamp_from_parquet(self):
        """Parquet timestamp → hf_dtype == 'timestamp[s]'."""
        import pyarrow as pa

        assert _parquet_to_hf_dtype(pa.timestamp("s")) == "timestamp[s]"

    def test_null_returns_none(self):
        """Parquet null → None (omit from features)."""
        import pyarrow as pa

        assert _parquet_to_hf_dtype(pa.null()) is None

    def test_binary_falls_back_to_string(self):
        """Parquet binary → hf_dtype == 'string' (no native binary in HF)."""
        import pyarrow as pa

        assert _parquet_to_hf_dtype(pa.binary()) == "string"

    def test_parquet_schema_populates_hf_dtype(self, tmp_path):
        """build_schema_report from Parquet should populate hf_dtype on ColumnSchema."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        csv_path = tmp_path / "data.csv"
        csv_path.write_text("val\n1\n2\n3\n", encoding="utf-8-sig")

        # Parquet with specific types
        schema_pa = pa.schema(
            [
                ("id", pa.int32()),
                ("score", pa.float64()),
                ("flag", pa.bool_()),
                ("label", pa.string()),
            ]
        )
        table = pa.table(
            {
                "id": [1, 2, 3],
                "score": [1.0, 2.0, 3.0],
                "flag": [True, False, True],
                "label": ["a", "b", "c"],
            },
            schema=schema_pa,
        )
        pq.write_table(table, tmp_path / "data.parquet")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv_path, remote="data.csv")],
            _base_dir=tmp_path,
        )

        schema = build_schema_report(cfg, staging_dir=tmp_path)
        by_name = {s.name: s for s in schema}

        assert by_name["id"].hf_dtype == "int32"
        assert by_name["score"].hf_dtype == "float64"
        assert by_name["flag"].hf_dtype == "bool"
        assert by_name["label"].hf_dtype == "string"

    def test_csv_bool_detection(self):
        """_csv_values_look_like_bool should detect true/false values."""
        assert _csv_values_look_like_bool(["True", "False", "True"])
        assert _csv_values_look_like_bool(["0", "1", "1", "0"])
        assert _csv_values_look_like_bool(["yes", "no", "yes"])
        assert not _csv_values_look_like_bool(["hello", "world"])
        assert not _csv_values_look_like_bool(["1", "2", "3"])
        assert not _csv_values_look_like_bool([])


# ── 3. configs YAML ──────────────────────────────────────────────────────────


class TestConfigsYAML:
    """configs block must be emitted with config_name, data_files, default."""

    def test_configs_emitted_when_files_present(self):
        """configs should appear in frontmatter when files are declared."""
        cfg = DatasetConfig(
            name="my-ds",
            repo_id="user/my-ds",
            license="mit",
            files=[FileEntry(local=Path("data.csv"), remote="data/data.csv")],
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert "configs" in fm
        configs = fm["configs"]
        assert isinstance(configs, list)
        assert len(configs) == 1
        assert configs[0]["config_name"] == "my-ds"
        assert configs[0]["default"] is True
        assert "data_files" in configs[0]
        assert configs[0]["data_files"][0]["split"] == "train"

    def test_configs_uses_config_names_if_provided(self):
        """config_name should use cfg.config_names[0] when available."""
        cfg = DatasetConfig(
            name="my-ds",
            repo_id="user/my-ds",
            license="mit",
            config_names=["v1", "v2"],
            files=[FileEntry(local=Path("data.csv"), remote="data/data.csv")],
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert fm["configs"][0]["config_name"] == "v1"

    def test_no_configs_when_no_files(self):
        """configs should NOT appear when no files are declared."""
        cfg = DatasetConfig(name="test", repo_id="user/test", license="mit")
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert "configs" not in fm


# ── 4. size_categories validation ────────────────────────────────────────────


class TestSizeCategories:
    """size_categories must be validated and emitted as a YAML list."""

    def test_valid_category_passes(self):
        """Known size categories should be accepted."""
        for cat in _SIZE_CATEGORIES:
            assert _validate_size_category(cat) == cat

    def test_invalid_category_returns_none(self):
        """Unknown size category should return None."""
        assert _validate_size_category("invalid") is None
        assert _validate_size_category("") is None

    def test_size_categories_emitted_as_list(self):
        """size_categories should always be a YAML list, not a scalar string."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            size_categories="1K<n<10K",
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert "size_categories" in fm
        sc = fm["size_categories"]
        assert isinstance(sc, list), f"Expected list, got {type(sc)}: {sc}"
        assert sc == ["1K<n<10K"]

    def test_multiple_size_categories(self):
        """Comma-separated size_categories should all be emitted as a list."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            size_categories="1K<n<10K, n<1K",
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert fm["size_categories"] == ["1K<n<10K", "n<1K"]

    def test_invalid_size_category_filtered(self):
        """Invalid size categories should be silently filtered out."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            size_categories="1K<n<10K, bogus, 10K<n<100K",
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        # bogus should be filtered
        assert fm["size_categories"] == ["1K<n<10K", "10K<n<100K"]


# ── 5. license: other flow ───────────────────────────────────────────────────


class TestLicenseOther:
    """Non-SPDX licenses should emit license_name, license_link, license_details."""

    def test_other_license_emits_fields(self):
        """Unknown license → 'other' + optional fields."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="made-up-1.0",
            license_name="Made Up License",
            license_link="https://example.com/license",
            license_details="Custom terms apply.",
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)

        assert fm["license"] == "other"
        assert fm["license_name"] == "Made Up License"
        assert fm["license_link"] == "https://example.com/license"
        assert fm["license_details"] == "Custom terms apply."

    def test_other_license_defaults_license_link_to_license(self):
        """When license_link is empty, default to 'LICENSE'."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="made-up-1.0",
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)

        assert fm["license"] == "other"
        assert fm["license_link"] == "LICENSE"
        assert fm["license_details"] == "made-up-1.0"

    def test_known_spdx_not_other(self):
        """Known SPDX license should NOT use the 'other' flow."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            license_name="Should not appear",
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)

        assert fm["license"] == "mit"
        assert "license_name" not in fm

    def test_build_license_file_other(self):
        """build_license_file('other') should return a custom-terms template."""
        result = build_license_file("other")
        assert "custom terms" in result.lower()
        assert "LICENSE file" in result


# ── 6. Optional metadata keys ────────────────────────────────────────────────


class TestOptionalMetadata:
    """Optional HF Dataset Card metadata keys should appear when provided."""

    def test_annotations_creators(self):
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            annotations_creators=["expert-generated"],
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert fm["annotations_creators"] == ["expert-generated"]

    def test_language_creators(self):
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            language_creators=["found"],
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert fm["language_creators"] == ["found"]

    def test_language_details(self):
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            language_details=["en-US", "fr-FR"],
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert fm["language_details"] == ["en-US", "fr-FR"]

    def test_multilinguality(self):
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            multilinguality="monolingual",
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert fm["multilinguality"] == "monolingual"

    def test_task_ids(self):
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            task_ids=["text-classification"],
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert fm["task_ids"] == ["text-classification"]

    def test_paperswithcode_id(self):
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            paperswithcode_id="squad-1.1",
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert fm["paperswithcode_id"] == "squad-1.1"

    def test_config_names_multi_config(self):
        """config_names emitted in frontmatter only when >1 config."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            config_names=["v1", "v2", "v3"],
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert fm["config_names"] == ["v1", "v2", "v3"]

    def test_config_names_single_not_emitted(self):
        """Single config_name not emitted as config_names frontmatter key."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            config_names=["v1"],
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert "config_names" not in fm

    def test_metadata_not_emitted_when_empty(self):
        """Empty metadata fields should not appear in frontmatter."""
        cfg = DatasetConfig(name="test", repo_id="user/test", license="mit")
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert "annotations_creators" not in fm
        assert "language_creators" not in fm
        assert "language_details" not in fm
        assert "multilinguality" not in fm
        assert "task_ids" not in fm
        assert "paperswithcode_id" not in fm


# ── 7. Card body optional sections ───────────────────────────────────────────


class TestCardBodySections:
    """Optional card body sections: Funded by, Shared by, Paper, Demo, Authors."""

    def test_funded_by_in_card_body(self):
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            funded_by="National Science Foundation",
        )
        result = build_dataset_card(cfg, schema=[])
        assert "- **Funded by:** National Science Foundation" in result

    def test_shared_by_in_card_body(self):
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            shared_by="ACME Corporation",
        )
        result = build_dataset_card(cfg, schema=[])
        assert "- **Shared by:** ACME Corporation" in result

    def test_paper_section(self):
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            paper_url="https://arxiv.org/abs/1234.5678",
        )
        result = build_dataset_card(cfg, schema=[])
        assert "## Paper" in result
        assert "https://arxiv.org/abs/1234.5678" in result

    def test_demo_section(self):
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            demo_url="https://huggingface.co/spaces/user/demo",
        )
        result = build_dataset_card(cfg, schema=[])
        assert "## Demo" in result
        assert "https://huggingface.co/spaces/user/demo" in result

    def test_dataset_card_authors(self):
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            dataset_card_authors="Jane Doe; John Smith",
        )
        result = build_dataset_card(cfg, schema=[])
        assert "## Dataset Card Authors" in result
        assert "Jane Doe; John Smith" in result

    def test_optional_sections_not_emitted_when_empty(self):
        """Optional sections should not appear when fields are empty."""
        cfg = DatasetConfig(name="test", repo_id="user/test", license="mit")
        result = build_dataset_card(cfg, schema=[])
        assert "## Funded by" not in result
        assert "## Shared by" not in result
        assert "## Paper" not in result
        assert "## Demo" not in result
        assert "## Dataset Card Authors" not in result


# ── 8. Tags (modality + library) ─────────────────────────────────────────────


class TestTags:
    """Always emit 'datasets' library tag and a modality tag."""

    def test_datasets_tag_always_present(self):
        """datasets library tag must always be emitted."""
        cfg = DatasetConfig(name="test", repo_id="user/test", license="mit")
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert "datasets" in fm["tags"]

    def test_tabular_modality_tag_default(self):
        """tabular modality tag should be added by default."""
        cfg = DatasetConfig(name="test", repo_id="user/test", license="mit")
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert "tabular" in fm["tags"]

    def test_user_tags_preserved(self):
        """User-provided tags should be preserved alongside auto-tags."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            tags=["survey", "demographics"],
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert "survey" in fm["tags"]
        assert "demographics" in fm["tags"]
        assert "datasets" in fm["tags"]
        assert "tabular" in fm["tags"]

    def test_existing_modality_preserved(self):
        """When the user already provides a modality tag, don't add 'tabular'."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            tags=["text", "sentiment"],
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert "text" in fm["tags"]
        assert "datasets" in fm["tags"]
        # tabular should NOT be added since 'text' is already a modality
        assert "tabular" not in fm["tags"]


# ── 9. source_datasets ───────────────────────────────────────────────────────


class TestSourceDatasets:
    """source_datasets must be a dataset repo ID (with backward compat)."""

    def test_source_emitted_as_list(self):
        """source_datasets must always be a list."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            source="my-institution",
        )
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert "source_datasets" in fm
        assert isinstance(fm["source_datasets"], list)
        assert fm["source_datasets"] == ["my-institution"]

    def test_source_not_emitted_when_empty(self):
        """source_datasets should not appear when source is empty."""
        cfg = DatasetConfig(name="test", repo_id="user/test", license="mit")
        result = build_dataset_card(cfg, schema=[])
        fm = _parse_frontmatter(result)
        assert "source_datasets" not in fm


# ── 10. Full card YAML validity ──────────────────────────────────────────────


class TestFullCardYAMLValidity:
    """The entire Dataset Card YAML frontmatter must be valid YAML."""

    def test_full_frontmatter_parses_as_valid_yaml(self):
        """Multi-feature card frontmatter must be valid YAML."""
        cfg = DatasetConfig(
            name="census-2010",
            repo_id="org/census-2010",
            description="2010 census data.",
            license="cc0-1.0",
            source="wikipedia",
            language=["en"],
            pretty_name="Census 2010",
            task_categories=["tabular-classification"],
            size_categories="10K<n<100K",
            tags=["census"],
            annotations_creators=["expert-generated"],
            language_creators=["found"],
            language_details=["en-US"],
            multilinguality="monolingual",
            task_ids=["text-classification"],
            paperswithcode_id="census-2010",
            config_names=["default", "v2"],
            funded_by="NSF",
            shared_by="Census Bureau",
            paper_url="https://arxiv.org/abs/1234.5678",
            demo_url="https://huggingface.co/spaces/demo",
            dataset_card_authors="Jane Doe",
            collection_method="Survey",
            citation="@article{census2010}",
            files=[
                FileEntry(local=Path("data.csv"), remote="data/data.csv"),
                FileEntry(local=Path("extra.csv"), remote="data/extra.csv"),
            ],
        )
        schema = [
            ColumnSchema(
                name="age",
                dtype="numeric",
                nullable=False,
                example="30",
                unique=100,
                missing=0.0,
                hf_dtype="int64",
            ),
            ColumnSchema(
                name="city",
                dtype="categorical/text",
                nullable=True,
                example="NYC",
                unique=500,
                missing=2.5,
                hf_dtype="string",
            ),
            ColumnSchema(
                name="active",
                dtype="categorical/text",
                nullable=False,
                example="True",
                unique=2,
                missing=0.0,
                hf_dtype="bool",
            ),
        ]
        result = build_dataset_card(cfg, schema)

        # Must start with YAML frontmatter
        assert result.startswith("---\n")

        # Parse it
        fm = _parse_frontmatter(result)

        # Verify all key fields
        assert fm["pretty_name"] == "Census 2010"
        assert fm["license"] == "cc0-1.0"
        assert fm["task_categories"] == ["tabular-classification"]
        assert fm["size_categories"] == ["10K<n<100K"]
        assert fm["tags"] == ["census", "datasets", "tabular"]
        assert fm["source_datasets"] == ["wikipedia"]
        assert fm["language"] == ["en"]
        assert fm["annotations_creators"] == ["expert-generated"]
        assert fm["language_creators"] == ["found"]
        assert fm["language_details"] == ["en-US"]
        assert fm["multilinguality"] == "monolingual"
        assert fm["task_ids"] == ["text-classification"]
        assert fm["paperswithcode_id"] == "census-2010"
        assert fm["config_names"] == ["default", "v2"]

        # configs
        assert "configs" in fm
        assert fm["configs"][0]["config_name"] == "default"

        # dataset_info
        di = fm["dataset_info"]
        features = di["features"]
        assert len(features) == 3
        assert features[0] == {"name": "age", "dtype": "int64"}
        assert features[1] == {"name": "city", "dtype": "string"}
        assert features[2] == {"name": "active", "dtype": "bool"}
        assert "config_name" in di
        assert "splits" in di

        # Card body optional sections
        assert "## Dataset Card Authors" in result
        assert "## Paper" in result
        assert "## Demo" in result
        assert "Funded by:** NSF" in result
        assert "Shared by:** Census Bureau" in result

    def test_license_other_full_flow(self):
        """Complete 'other' license flow with all optional fields."""
        cfg = DatasetConfig(
            name="custom-ds",
            repo_id="org/custom-ds",
            description="Custom licensed dataset.",
            license="proprietary-v2",
            license_name="Proprietary License v2",
            license_link="https://example.com/license-v2",
            license_details="Contact legal@example.com for terms.",
            files=[FileEntry(local=Path("data.csv"), remote="data.csv")],
        )
        schema = [
            ColumnSchema(
                name="val",
                dtype="numeric",
                nullable=False,
                example="42",
                unique=10,
                missing=0.0,
                hf_dtype="int64",
            ),
        ]
        result = build_dataset_card(cfg, schema)
        fm = _parse_frontmatter(result)

        assert fm["license"] == "other"
        assert fm["license_name"] == "Proprietary License v2"
        assert fm["license_link"] == "https://example.com/license-v2"
        assert fm["license_details"] == "Contact legal@example.com for terms."

        # features still correct
        features = fm["dataset_info"]["features"]
        assert features[0] == {"name": "val", "dtype": "int64"}

        # Card body should display the original license string
        assert "proprietary-v2" in result


# ═══════════════════════════════════════════════════════════════════════════════
#  GitHub issue #13 — Schema Validation & Features Fidelity
# ═══════════════════════════════════════════════════════════════════════════════


class TestNormalizeHeader:
    """normalize_header strips whitespace and preserves case."""

    def test_strips_leading_trailing_whitespace(self):
        assert normalize_header("  col  ") == "col"

    def test_strips_tabs_and_newlines(self):
        assert normalize_header("\tname\r\n") == "name"

    def test_preserves_case(self):
        assert normalize_header("COLUMN_NAME") == "COLUMN_NAME"

    def test_leaves_clean_name_unchanged(self):
        assert normalize_header("age") == "age"

    def test_empty_string_returns_empty(self):
        assert normalize_header("   ") == ""


class TestNoColonPrefixedInCard:
    """:: prefixed pseudo-columns must not appear in dataset_info or Data Fields."""

    def test_colon_prefixed_filtered_from_features(self):
        """Schema entries with :: in name should be excluded from dataset_info.features."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
        )
        schema = [
            ColumnSchema(
                name="clean",
                dtype="numeric",
                nullable=False,
                example="1",
                unique=1,
                missing=0.0,
                hf_dtype="int64",
            ),
            ColumnSchema(
                name="a.parquet::value",
                dtype="numeric",
                nullable=False,
                example="2",
                unique=2,
                missing=0.0,
                hf_dtype="int64",
            ),
            ColumnSchema(
                name="file.csv::value",
                dtype="numeric",
                nullable=False,
                example="3",
                unique=3,
                missing=0.0,
                hf_dtype="int64",
            ),
        ]
        result = build_dataset_card(cfg, schema)
        fm = _parse_frontmatter(result)

        features = fm["dataset_info"]["features"]
        feature_names = [f["name"] for f in features]
        assert feature_names == ["clean"]
        assert "a.parquet::value" not in feature_names
        assert "file.csv::value" not in feature_names

    def test_colon_prefixed_filtered_from_data_fields_table(self):
        """:: prefixed columns should not appear in the Data Fields table."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
        )
        schema = [
            ColumnSchema(
                name="good",
                dtype="numeric",
                nullable=False,
                example="1",
                unique=1,
                missing=0.0,
                hf_dtype="int64",
            ),
            ColumnSchema(
                name="x::bad",
                dtype="numeric",
                nullable=True,
                example="2",
                unique=2,
                missing=5.0,
                hf_dtype="float64",
            ),
        ]
        result = build_dataset_card(cfg, schema)
        # The Data Fields table should only show 'good'
        assert "| `good` |" in result
        assert "| `x::bad` |" not in result


class TestSampleBasedFootnote:
    """Data Fields table must include a sample-based-stats footnote."""

    def test_footnote_present_when_schema_has_columns(self):
        """Footnote should appear after the Data Fields table."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
        )
        schema = [
            ColumnSchema(
                name="x", dtype="numeric", nullable=False, example="1", unique=10, missing=0.0
            ),
        ]
        result = build_dataset_card(cfg, schema)
        assert "Statistics (unique, missing%) based on a 10,000-row sample" in result

    def test_no_footnote_when_schema_empty(self):
        """When there is no schema, there is no Data Fields table → no footnote."""
        cfg = DatasetConfig(name="test", repo_id="user/test")
        result = build_dataset_card(cfg, schema=[])
        assert "Statistics (unique, missing%) based on a 10,000-row sample" not in result


class TestDataQualityNotes:
    """Empty columns and duplicate rows should be documented in the card."""

    def test_empty_columns_explicit(self):
        """Explicitly passed empty_columns should appear in a Data Quality section."""
        cfg = DatasetConfig(name="test", repo_id="user/test", license="mit")
        schema = [
            ColumnSchema(
                name="x", dtype="numeric", nullable=False, example="1", unique=10, missing=0.0
            ),
        ]
        result = build_dataset_card(cfg, schema, empty_columns=["dead_col"])
        assert "### Data Quality Notes" in result
        assert "`dead_col`" in result

    def test_empty_columns_auto_detected_from_schema(self):
        """Columns with missing==100% should be auto-detected."""
        cfg = DatasetConfig(name="test", repo_id="user/test", license="mit")
        schema = [
            ColumnSchema(
                name="full_col", dtype="numeric", nullable=True, example="1", unique=1, missing=0.0
            ),
            ColumnSchema(
                name="dead_col", dtype="unknown", nullable=True, example="", unique=0, missing=100.0
            ),
        ]
        result = build_dataset_card(cfg, schema)
        assert "### Data Quality Notes" in result
        assert "`dead_col`" in result

    def test_duplicate_rows_in_card(self):
        """Duplicate row counts should appear in the Data Quality section."""
        cfg = DatasetConfig(name="test", repo_id="user/test", license="mit")
        result = build_dataset_card(cfg, schema=[], duplicate_rows={"data.csv": 42})
        assert "### Data Quality Notes" in result
        assert "`data.csv`" in result
        assert "42" in result

    def test_no_section_when_nothing_to_report(self):
        """No Data Quality Notes section when no empty columns or duplicate rows."""
        cfg = DatasetConfig(name="test", repo_id="user/test", license="mit")
        schema = [
            ColumnSchema(
                name="x", dtype="numeric", nullable=False, example="1", unique=10, missing=0.0
            ),
        ]
        result = build_dataset_card(cfg, schema)
        assert "### Data Quality Notes" not in result

    def test_both_empty_and_dupes(self):
        """Both empty columns and duplicate rows can be shown together."""
        cfg = DatasetConfig(name="test", repo_id="user/test", license="mit")
        schema = [
            ColumnSchema(
                name="dead", dtype="unknown", nullable=True, example="", unique=0, missing=100.0
            ),
        ]
        result = build_dataset_card(
            cfg,
            schema,
            empty_columns=["extra_dead"],
            duplicate_rows={"f1.csv": 3, "f2.csv": 7},
        )
        assert "### Data Quality Notes" in result
        assert "`dead`" in result
        assert "`extra_dead`" in result
        assert "`f1.csv`" in result
        assert "3" in result
        assert "7" in result

    def test_colon_prefixed_not_duplicated_in_empty_columns(self):
        """:: prefixed columns should not be reported as empty even if at 100%."""
        cfg = DatasetConfig(name="test", repo_id="user/test", license="mit")
        schema = [
            ColumnSchema(
                name="x", dtype="numeric", nullable=False, example="1", unique=10, missing=0.0
            ),
            ColumnSchema(
                name="a.parquet::ghost",
                dtype="unknown",
                nullable=True,
                example="",
                unique=0,
                missing=100.0,
            ),
        ]
        result = build_dataset_card(cfg, schema)
        # "ghost" should NOT appear in empty columns because it's ::-prefixed
        # x is not empty, so no Data Quality section at all
        assert "### Data Quality Notes" not in result


# ── 10. Study design content in Dataset Card ──────────────────────────────────


class TestStudyDesign:
    """When ``cfg.study_design`` is set, its content should appear in the Dataset Card."""

    def test_study_design_in_cuartion_rationale(self):
        """study_design_content should replace '[More Information Needed]'."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
            study_design="design.md",
        )
        sd_content = "This dataset was collected via a stratified random sample."
        result = build_dataset_card(cfg, schema=[], study_design_content=sd_content)

        assert "### Curation Rationale" in result
        assert "stratified random sample" in result
        assert (
            "[More Information Needed]"
            not in result.split("### Curation Rationale")[1].split("###")[0]
        )

    def test_study_design_none_falls_back_to_placeholder(self):
        """When study_design_content is None, show '[More Information Needed]'."""
        cfg = DatasetConfig(name="test", repo_id="user/test", license="mit")
        result = build_dataset_card(cfg, schema=[])

        assert "### Curation Rationale" in result
        assert "[More Information Needed]" in result

    def test_study_design_content_is_stripped(self):
        """Trailing whitespace in study design content should be stripped."""
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            license="mit",
        )
        sd_content = "\n\n  Survey methodology details.  \n\n"
        result = build_dataset_card(cfg, schema=[], study_design_content=sd_content)

        # Content should appear without leading/trailing whitespace
        assert "Survey methodology details." in result
        # The stripped content should not cause multiple blank lines
        assert "\n\n\n" not in result
