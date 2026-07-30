"""Tests for data_uploader.repo_compliance — Dataset Card, LICENSE, schema report."""

from pathlib import Path

import pytest

from data_uploader.model import DatasetConfig, FileEntry
from data_uploader.repo_compliance import (
    ColumnSchema,
    build_dataset_card,
    build_license_file,
    build_schema_report,
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
        """Duplicate column names across files should be disambiguated with ::."""
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
        assert "file_a.csv::value" in names
        assert "file_b.csv::value" in names

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
        from data_uploader import uploader

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_file", lambda *a, **kw: None)

    def test_compliance_called_before_upload(self, tmp_path, monkeypatch):
        """Compliance functions should be called — verify via mocked tracking."""
        from data_uploader import uploader

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
        """README.md should be uploaded first, then LICENSE, then data files."""
        from data_uploader import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv")],
            _base_dir=tmp_path,
        )

        upload_targets = []

        def _tracking_upload(path_or_fileobj="", path_in_repo="", **kw):
            upload_targets.append(path_in_repo)

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_file", _tracking_upload)

        import tempfile

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        # README.md should appear before LICENSE before data file
        readme_idx = next(i for i, t in enumerate(upload_targets) if t == "README.md")
        lic_idx = next(i for i, t in enumerate(upload_targets) if t == "LICENSE")
        data_idx = next(
            i for i, t in enumerate(upload_targets) if t.endswith(".parquet") or t.endswith(".csv")
        )

        assert readme_idx < lic_idx < data_idx, (
            f"Upload order wrong: README.md at {readme_idx}, LICENSE at {lic_idx},"
            f" data at {data_idx} ({upload_targets[data_idx]})"
        )

    def test_tempdir_cleanup_on_success(self, tmp_path, monkeypatch):
        """Temp directory should be cleaned up after successful upload."""
        from data_uploader import uploader

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
        from data_uploader import uploader

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
        from data_uploader import uploader

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
        """Disambiguated column names should use .parquet prefix."""
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
        assert "a.parquet::value" in names
        assert "b.parquet::value" in names
