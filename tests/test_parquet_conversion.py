"""Tests for CSV-to-Parquet conversion, keep-csv, pipeline integration, and model."""

import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from data_uploader.model import DatasetConfig, FileEntry

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

        from data_uploader.uploader import _convert_to_parquet

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

        from data_uploader.uploader import _convert_to_parquet

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

        from data_uploader.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv_path, staging)
        table = pq.read_table(result)
        assert table.schema.field("val").type == pa.int64()

    def test_type_inference_string(self, tmp_path):
        """Text columns should be inferred as large_string or string."""
        csv_path = tmp_path / "text.csv"
        csv_path.write_text("name\nAlice\nBob\nCharlie\n", encoding="utf-8-sig")

        staging = tmp_path / "staging"
        staging.mkdir()

        from data_uploader.uploader import _convert_to_parquet

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

        from data_uploader.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv_path, staging)
        assert result is None

    def test_unreadable_file_returns_none(self, tmp_path):
        """A non-existent file path should return None."""
        csv_path = tmp_path / "ghost.csv"
        staging = tmp_path / "staging"
        staging.mkdir()

        from data_uploader.uploader import _convert_to_parquet

        result = _convert_to_parquet(csv_path, staging)
        assert result is None

    def test_warning_printed_on_failure(self, tmp_path, capsys):
        """A warning should be printed when conversion fails."""
        csv_path = tmp_path / "bad.csv"
        csv_path.write_bytes(b"\x00\x01\x02")

        staging = tmp_path / "staging"
        staging.mkdir()

        from data_uploader.uploader import _convert_to_parquet

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
        """A CSV entry without upload_as_csv should be converted to Parquet."""
        from data_uploader import uploader

        csv = tmp_path / "data.csv"
        csv.write_text("x\n1\n2\n", encoding="utf-8-sig")

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

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        # Verify that data.parquet was uploaded (not data.csv)
        assert "data.parquet" in upload_targets
        assert "data.csv" not in upload_targets

    def test_csv_not_converted_when_upload_as_csv(self, tmp_path, monkeypatch):
        """upload_as_csv=True should skip conversion, upload original CSV."""
        from data_uploader import uploader

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
        monkeypatch.setattr(uploader._api, "upload_file", lambda *a, **kw: None)

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)
        # No .parquet should be created for this entry
        assert not (td / "raw.parquet").exists()

    def test_parquet_passthrough_skips_conversion(self, tmp_path, monkeypatch):
        """Existing .parquet files should be passed through without conversion."""
        from data_uploader import uploader

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
        monkeypatch.setattr(uploader._api, "upload_file", lambda *a, **kw: None)

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)
        # The original parquet file should still exist
        assert parquet_path.exists()

    def test_non_csv_file_passthrough(self, tmp_path, monkeypatch):
        """Non-CSV, non-Parquet files should pass through without conversion."""
        from data_uploader import uploader

        json_path = tmp_path / "meta.json"
        json_path.write_text('{"key": "value"}', encoding="utf-8")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=json_path, remote="meta.json")],
            _base_dir=tmp_path,
        )

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_file", lambda *a, **kw: None)

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)
        assert json_path.exists()


class TestKeepCsv:
    """keep_csv flag behaviour — upload both Parquet and CSV, or just Parquet."""

    def test_keep_csv_false_uploads_only_parquet(self, tmp_path, monkeypatch):
        """Without keep_csv, only the Parquet file should be uploaded."""
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

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        # Should have README, LICENSE, and data.parquet (NOT data.csv)
        assert "data.parquet" in upload_targets
        assert "data.csv" not in upload_targets

    def test_keep_csv_true_uploads_both(self, tmp_path, monkeypatch):
        """With keep_csv=True, both Parquet and original CSV should be uploaded."""
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

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        # Call with keep_csv=True
        uploader.upload(cfg, keep_csv=True)

        assert "data.parquet" in upload_targets
        assert "data.csv" in upload_targets


class TestUploadFileSelection:
    """Upload path and remote path are correct for converted files."""

    def test_converted_file_uses_staging_path(self, tmp_path, monkeypatch):
        """Upload should use staging_dir path for converted Parquet, not original CSV."""
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
            upload_targets.append((str(path_or_fileobj), path_in_repo))

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_file", _tracking_upload)

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        # Find data uploads (not README/LICENSE)
        data_uploads = [
            (local, remote) for local, remote in upload_targets if remote.endswith(".parquet")
        ]
        assert len(data_uploads) > 0
        # Local path should be inside staging dir
        local_path = data_uploads[0][0]
        assert str(td) in local_path or td.name in local_path

    def test_converted_file_parquet_remote(self, tmp_path, monkeypatch):
        """Remote path should have .parquet extension for converted files."""
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
            upload_targets.append((str(path_or_fileobj), path_in_repo))

        monkeypatch.setattr(uploader._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(uploader._api, "upload_file", _tracking_upload)

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))

        uploader.upload(cfg)

        # Find data uploads for parquet files
        data_uploads = [
            (local, remote) for local, remote in upload_targets if remote.endswith(".parquet")
        ]
        assert len(data_uploads) > 0
        remote_path = data_uploads[0][1]
        assert remote_path == "data.parquet"


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
