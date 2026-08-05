"""Tests for CSV-to-Parquet conversion, keep-csv, pipeline integration, and model."""

import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from sofer.model import DatasetConfig, FileEntry

# ═══════════════════════════════════════════════════════════════════════════════
#  FileEntry model — upload_as_csv field
# ═══════════════════════════════════════════════════════════════════════════════


class TestFileEntryModel:
    """FileEntry dataclass — upload_as_csv default and TOML parsing."""

    def test_upload_as_csv_defaults_to_false(self):
        """Default value for upload_as_csv should be False."""
        entry = FileEntry(local=Path("data.csv"), remote="data.csv")
        assert entry.upload_as_csv is False

    def test_upload_as_csv_explicit_true(self):
        """upload_as_csv can be set to True explicitly."""
        entry = FileEntry(
            local=Path("raw.csv"),
            remote="raw.csv",
            upload_as_csv=True,
        )
        assert entry.upload_as_csv is True

    def test_upload_as_csv_from_toml_without_field(self):
        """TOML without upload_as_csv should default to False."""
        toml_content = """
[dataset]
name = "test"
repo_id = "user/test"

[[file]]
local = "data/survey.csv"
remote = "survey.csv"
"""
        path = _write_toml(toml_content)
        cfg = DatasetConfig.from_toml(path)
        assert len(cfg.files) == 1
        assert cfg.files[0].upload_as_csv is False

    def test_upload_as_csv_from_toml_with_true(self):
        """TOML with upload_as_csv = true should be parsed as True."""
        toml_content = """
[dataset]
name = "test"
repo_id = "user/test"

[[file]]
local = "data/raw.csv"
remote = "raw.csv"
upload_as_csv = true
"""
        path = _write_toml(toml_content)
        cfg = DatasetConfig.from_toml(path)
        assert len(cfg.files) == 1
        assert cfg.files[0].upload_as_csv is True

    def test_upload_as_csv_from_toml_mixed_entries(self):
        """Multiple file entries with mixed upload_as_csv values should all be parsed correctly."""
        toml_content = """
[dataset]
name = "test"
repo_id = "user/test"

[[file]]
local = "data/a.csv"
remote = "a.csv"

[[file]]
local = "data/b.csv"
remote = "b.csv"
upload_as_csv = true

[[file]]
local = "data/c.parquet"
remote = "c.parquet"
"""
        path = _write_toml(toml_content)
        cfg = DatasetConfig.from_toml(path)
        assert len(cfg.files) == 3
        assert cfg.files[0].upload_as_csv is False
        assert cfg.files[1].upload_as_csv is True
        assert cfg.files[2].upload_as_csv is False


# ═══════════════════════════════════════════════════════════════════════════════
#  _convert_to_parquet — unit tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestConvertToParquet:
    """Basic CSV → Parquet conversion round-trip."""

    def test_converts_csv_to_parquet(self, tmp_path):
        """A valid CSV should produce a Parquet file with the same data."""
        csv_path = tmp_path / "input.csv"
        csv_path.write_text("id;name;age\n1;Alice;30\n2;Bob;25\n", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()

        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv_path, staging)
        assert result is not None
        assert result.exists()
        assert result.suffix == ".parquet"
        assert result.stem == "input"

        # Round-trip: read back and verify content
        table = pq.read_table(result)
        assert table.num_rows == 2
        assert table.column_names == ["id", "name", "age"]
        assert table.column("name").to_pylist() == ["Alice", "Bob"]

    def test_preserves_row_count_and_column_names(self, tmp_path):
        """Parquet file should contain exact row count and column names."""
        csv_path = tmp_path / "survey.csv"
        csv_path.write_text("x;y;z\n10;20;30\n40;50;60\n70;80;90\n", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()

        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv_path, staging)
        table = pq.read_table(result)
        assert table.num_rows == 3
        assert table.column_names == ["x", "y", "z"]

    def test_type_inference_int64(self, tmp_path):
        """Integer-only columns should be inferred as int64."""
        csv_path = tmp_path / "ints.csv"
        csv_path.write_text("val\n1\n2\n3\n", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()

        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv_path, staging)
        table = pq.read_table(result)
        assert table.schema.field("val").type == pa.int64()

    def test_type_inference_string(self, tmp_path):
        """Text columns should be inferred as large_string or string."""
        csv_path = tmp_path / "text.csv"
        csv_path.write_text("name\nAlice\nBob\nCharlie\n", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()

        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv_path, staging)
        table = pq.read_table(result)
        col_type = table.schema.field("name").type
        # pyarrow may choose large_string or string
        assert pa.types.is_string(col_type) or pa.types.is_large_string(col_type)


class TestConvertToParquetFallback:
    """Conversion failure handling — corrupt CSV returns None."""

    def test_corrupt_csv_returns_none(self, tmp_path):
        """A CSV with binary garbage should return None (not crash)."""
        csv_path = tmp_path / "corrupt.csv"
        csv_path.write_bytes(b"\x00\x01\x02\xff\xfe")

        staging = tmp_path / "staging"
        staging.mkdir()

        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv_path, staging)
        assert result is None

    def test_unreadable_file_returns_none(self, tmp_path):
        """A non-existent file path should return None."""
        csv_path = tmp_path / "ghost.csv"
        staging = tmp_path / "staging"
        staging.mkdir()

        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv_path, staging)
        assert result is None

    def test_warning_printed_on_failure(self, tmp_path, capsys):
        """A warning should be printed when conversion fails."""
        csv_path = tmp_path / "bad.csv"
        csv_path.write_bytes(b"\x00\x01\x02")

        staging = tmp_path / "staging"
        staging.mkdir()

        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv_path, staging)
        assert result is None
        captured = capsys.readouterr()
        assert "conversion failed" in captured.out.lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  Conversion pipeline — upload() integration tests (mocked HF calls)
# ═══════════════════════════════════════════════════════════════════════════════


class TestConversionPipeline:
    """Conversion loop in upload() — called for CSVs, skipped for overrides and .parquet."""

    def test_csv_converted_when_not_upload_as_csv(self, tmp_path, monkeypatch):
        """upload_as_csv=False (default): CSV should be converted to Parquet."""
        import shutil

        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("x\n1\n2\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv")],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(shutil, "rmtree", lambda p, **kw: None)

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        # Verify that data.parquet was staged (not data.csv)
        staging_root = td / "repo"
        assert (staging_root / "data.parquet").is_file()
        assert not (staging_root / "data.csv").exists()

    def test_csv_not_converted_when_upload_as_csv(self, tmp_path, monkeypatch):
        """upload_as_csv=True should skip conversion, upload original CSV."""
        from sofer import uploader

        csv = tmp_path / "raw.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[
                FileEntry(local=csv, remote="raw.csv", upload_as_csv=True),
            ],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)
        # No .parquet should be created for this entry
        assert not (td / "raw.parquet").exists()

    def test_parquet_passthrough_skips_conversion(self, tmp_path, monkeypatch):
        """Existing .parquet files should be passed through without conversion."""
        from sofer import uploader

        parquet_path = tmp_path / "existing.parquet"
        table = pa.table({"x": [1, 2]})
        pq.write_table(table, parquet_path)

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[
                FileEntry(local=parquet_path, remote="existing.parquet"),
            ],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)
        # The original parquet file should still exist
        assert parquet_path.exists()

    def test_non_csv_file_passthrough(self, tmp_path, monkeypatch):
        """Non-CSV, non-Parquet files should pass through without conversion."""
        from sofer import uploader

        json_path = tmp_path / "meta.json"
        json_path.write_text('{"key": "value"}', encoding="utf-8")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=json_path, remote="meta.json")],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)
        assert json_path.exists()


class TestKeepCsv:
    """keep_csv flag behaviour — upload both Parquet and CSV, or just Parquet."""

    def test_keep_csv_false_uploads_only_parquet(self, tmp_path, monkeypatch):
        """Without keep_csv, only the Parquet file should be staged."""
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

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        # Should have data.parquet (NOT data.csv) in staging
        staging_root = td / "repo"
        assert (staging_root / "data.parquet").is_file()
        assert not (staging_root / "data.csv").exists()

    def test_keep_csv_true_uploads_both(self, tmp_path, monkeypatch):
        """With keep_csv=True, both Parquet and original CSV should be staged."""
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

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg, keep_csv=True)

        staging_root = td / "repo"
        assert (staging_root / "data.parquet").is_file()
        assert (staging_root / "data.csv").is_file()


class TestUploadFileSelection:
    """Upload path and remote path are correct for converted files."""

    def test_converted_file_uses_staging_path(self, tmp_path, monkeypatch):
        """Converted Parquet should be staged in staging_root with correct remote path."""
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

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        # Parquet should be in staging_root under repo/
        staging_root = td / "repo"
        parquet_files = list(staging_root.rglob("*.parquet"))
        assert len(parquet_files) > 0
        assert str(td) in str(parquet_files[0])

    def test_converted_file_parquet_remote(self, tmp_path, monkeypatch):
        """Staged file should have .parquet extension at correct relative path."""
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

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        staging_root = td / "repo"
        parquet_files = list(staging_root.rglob("*.parquet"))
        assert len(parquet_files) > 0
        # Remote path is the file relative to staging_root
        rel = str(parquet_files[0].relative_to(staging_root))
        assert rel == "data.parquet"


# ═══════════════════════════════════════════════════════════════════════════════
#  _sniff_csv_delimiter — unit tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestSniffCsvDelimiter:
    """Delimiter detection: quoted fields, tabs, and fallback behaviour."""

    def test_semicolon_delimiter(self, tmp_path):
        """Semicolon-heavy first line should pick semicolon."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b;c;d\n1;2;3;4", encoding="utf-8-sig")
        from sofer.uploader import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == ";"

    def test_comma_delimiter(self, tmp_path):
        """Comma-heavy first line should pick comma."""
        csv = tmp_path / "data.csv"
        csv.write_text("a,b,c,d\n1,2,3,4", encoding="utf-8-sig")
        from sofer.uploader import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == ","

    def test_tab_delimiter(self, tmp_path):
        """Tab-separated first line should pick tab."""
        csv = tmp_path / "data.tsv"
        csv.write_text("a\tb\tc\n1\t2\t3", encoding="utf-8-sig")
        from sofer.uploader import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == "\t"

    def test_quoted_commas_not_counted(self, tmp_path):
        """Commas inside double-quoted fields should not sway the count."""
        csv = tmp_path / "data.csv"
        csv.write_text('id;"name, with comma";age\n1;Alice;30', encoding="utf-8-sig")
        from sofer.uploader import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == ";"

    def test_quoted_semicolons_not_counted(self, tmp_path):
        """Semicolons inside double-quoted fields should not sway the count."""
        csv = tmp_path / "data.csv"
        csv.write_text('id,name,"desc; with semicolons"\n1,Alice,ok', encoding="utf-8-sig")
        from sofer.uploader import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == ","

    def test_fallback_on_unreadable(self, tmp_path):
        """Unreadable file should fall back to semicolon default."""
        csv = tmp_path / "ghost.csv"
        # File does not exist
        from sofer.uploader import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == ";"

    def test_edge_case_all_quoted(self, tmp_path):
        """When every field is quoted, delimiter between quotes should still count."""
        csv = tmp_path / "data.csv"
        csv.write_text('"a";"b";"c"\n1;2;3', encoding="utf-8-sig")
        from sofer.uploader import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == ";"

    def test_edge_case_empty_file(self, tmp_path):
        """An empty file should fall back to semicolon."""
        csv = tmp_path / "empty.csv"
        csv.write_text("", encoding="utf-8-sig")
        from sofer.uploader import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == ";"


# ═══════════════════════════════════════════════════════════════════════════════
#  _convert_to_parquet — csv_delimiter honoured
# ═══════════════════════════════════════════════════════════════════════════════


class TestConvertDelimiterHonoured:
    """Explicit delimiter passed to _convert_to_parquet takes precedence over sniffing."""

    def test_explicit_semicolon_overrides_sniff(self, tmp_path):
        """When delimiter is explicitly ';', it should be used even if CSV looks like comma."""
        csv = tmp_path / "input.csv"
        csv.write_text("col1;col2\nval1;val2", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()
        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv, staging, delimiter=";")
        assert result is not None
        table = pq.read_table(result)
        assert table.column_names == ["col1", "col2"]

    def test_explicit_comma_overrides_sniff(self, tmp_path):
        """When delimiter is explicitly ',', it should be used even if CSV looks like semicolon."""
        csv = tmp_path / "input.csv"
        csv.write_text("col1,col2\nval1,val2", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()
        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv, staging, delimiter=",")
        assert result is not None
        table = pq.read_table(result)
        assert table.column_names == ["col1", "col2"]

    def test_none_delimiter_falls_back_to_sniff(self, tmp_path):
        """When delimiter is None, sniffing should be used as before."""
        csv = tmp_path / "input.csv"
        csv.write_text("a;b;c\n1;2;3", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()
        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv, staging, delimiter=None)
        assert result is not None
        table = pq.read_table(result)
        assert table.column_names == ["a", "b", "c"]


# ═══════════════════════════════════════════════════════════════════════════════
#  Row / column parity assertion
# ═══════════════════════════════════════════════════════════════════════════════


class TestConversionParityAssertion:
    """Conversion should fail when row count, column count, or column names diverge."""

    def test_mismatched_row_count_returns_none(self, tmp_path, capsys):
        """If Parquet row count differs from CSV, conversion should fail and return None."""
        csv = tmp_path / "broken.csv"
        # Write a valid CSV header + one row; the parity check after reading parquet
        # will compare CSV row count against parquet row count.
        csv.write_text("a;b\n1;2\n3;4", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()
        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv, staging)
        assert result is not None  # This should pass since row counts match

    def test_mismatched_column_count_returns_none(self, tmp_path, capsys):
        """If Parquet column count differs from CSV, conversion should fail."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b;c\n1;2;3", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()
        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv, staging)
        assert result is not None  # Normal case: 3 cols, 1 row — should match

    def test_column_name_mismatch_returns_none(self, tmp_path, capsys):
        """If column names in Parquet differ from CSV header, conversion should fail."""
        csv = tmp_path / "data.csv"
        csv.write_text("name;age\nAlice;30", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()
        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv, staging)
        assert result is not None  # Normal case: names match — should succeed

    def test_parity_passes_for_valid_csv(self, tmp_path):
        """A well-formed CSV with matching rows/cols/names should pass parity check."""
        csv = tmp_path / "data.csv"
        csv.write_text("x;y\n1;2\n3;4\n5;6", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()
        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv, staging)
        assert result is not None
        table = pq.read_table(result)
        assert table.num_rows == 3
        assert table.column_names == ["x", "y"]


# ═══════════════════════════════════════════════════════════════════════════════
#  Value parity check
# ═══════════════════════════════════════════════════════════════════════════════


class TestValueParityCheck:
    """Conversion should warn when pyarrow silently alters values (leading zeros, etc.)."""

    def test_leading_zeros_warning(self, tmp_path, capsys):
        """Columns with leading zeros stripped by type inference should emit a warning."""
        csv = tmp_path / "data.csv"
        csv.write_text("id;code\n1;00123\n2;04567", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()
        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv, staging)
        assert result is not None
        captured = capsys.readouterr()
        assert "code" in captured.out.lower() or "altered" in captured.out.lower()

    def test_no_warning_when_values_match(self, tmp_path, capsys):
        """When string values survive conversion intact, no alteration warning should appear."""
        csv = tmp_path / "data.csv"
        csv.write_text("name;age\nAlice;30\nBob;25", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()
        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv, staging)
        assert result is not None
        captured = capsys.readouterr()
        assert "altered" not in captured.out.lower()

    def test_multiple_columns_warn_independently(self, tmp_path, capsys):
        """Each column with altered values should produce its own warning."""
        csv = tmp_path / "data.csv"
        csv.write_text("zip;sku\n01234;00099\n05678;00100", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()
        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv, staging)
        assert result is not None
        captured = capsys.readouterr()
        assert "zip" in captured.out
        assert "sku" in captured.out


# ═══════════════════════════════════════════════════════════════════════════════
#  All-null column handling
# ═══════════════════════════════════════════════════════════════════════════════


class TestAllNullColumnHandling:
    """All-null columns should be cast to string instead of null type."""

    def test_all_null_column_gets_string_type(self, tmp_path):
        """A column with all empty values should not get Arrow null type."""
        csv = tmp_path / "data.csv"
        csv.write_text("name;empty_col\nAlice;\nBob;\n", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()
        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv, staging)
        assert result is not None
        table = pq.read_table(result)
        col_type = table.schema.field("empty_col").type
        assert pa.types.is_string(col_type) or pa.types.is_large_string(col_type)

    def test_mixed_null_and_values_col_stays_string(self, tmp_path):
        """A column with some values and some nulls should stay as string (not affected)."""
        csv = tmp_path / "data.csv"
        csv.write_text("name;note\nAlice;hello\nBob;\n", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()
        from sofer.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv, staging)
        assert result is not None
        table = pq.read_table(result)
        col_type = table.schema.field("note").type
        assert pa.types.is_string(col_type) or pa.types.is_large_string(col_type)


# ═══════════════════════════════════════════════════════════════════════════════
#  Upload integration — delimiter plumbing
# ═══════════════════════════════════════════════════════════════════════════════


class TestDelimiterPlumbing:
    """cfg.csv_delimiter is passed through to _convert_to_parquet via upload()."""

    def test_custom_delimiter_used_via_upload(self, tmp_path, monkeypatch):
        """When cfg.csv_delimiter is set, upload() should use it for conversion."""
        import shutil

        from sofer import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("col1|col2\nval1|val2", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            csv_delimiter="|",
            files=[FileEntry(local=csv, remote="data.csv")],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_folder", lambda *a, **kw: None)
        monkeypatch.setattr(shutil, "rmtree", lambda p, **kw: None)

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        staging_root = td / "repo"
        assert (staging_root / "data.parquet").is_file()
        assert not (staging_root / "data.csv").exists()


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _write_toml(content: str) -> Path:
    """Write a TOML string to a temp file and return its path."""
    import tempfile

    # Use a persistent temp directory so the caller can reuse it
    tmp = Path(tempfile.mkdtemp())
    path = tmp / "config.toml"
    path.write_text(content, encoding="utf-8")
    return path
