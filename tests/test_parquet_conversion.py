"""Tests for CSV-to-Parquet conversion, keep-csv, pipeline integration, and model."""

import shutil
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from sofer import config
from sofer import publish as publish_mod
from sofer._converters import convert_file_to_parquet
from sofer.model import DatasetConfig, FileEntry
from sofer.prepare import prepare
from sofer.publish import publish


def _mock_hf_api(monkeypatch) -> None:
    """Stub every HF API method publish could reach (offline tests)."""
    monkeypatch.setattr(publish_mod._api, "create_repo", lambda *a, **kw: None)
    monkeypatch.setattr(publish_mod._api, "list_repo_files", lambda *a, **kw: [])
    monkeypatch.setattr(publish_mod._api, "upload_folder", lambda *a, **kw: None)


def _fixed_staging(tmp_path: Path, monkeypatch) -> Path:
    """Point tempfile.mkdtemp at tmp_path/_staging and keep it (no rmtree)."""
    td = tmp_path / "_staging"
    td.mkdir()
    monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))
    monkeypatch.setattr(shutil, "rmtree", lambda p, **kw: None)
    return td


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


# --- Byte-identity + declared-dialect coverage (PC-U01 / PC-U06, E1-E5) ---


def _declared_cfg(tmp_path: Path, meta_lines: str):
    """Write a dataset TOML declaring *meta_lines* and load it via from_toml."""
    toml = tmp_path / "dataset.toml"
    toml.write_text(
        "[dataset]\n"
        'name = "t"\n'
        'repo_id = "user/t"\n'
        "[[file]]\n"
        'local = "data.csv"\n'
        'remote = "data.csv"\n'
        "[meta]\n"
        f"{meta_lines}"
    )
    return DatasetConfig.from_toml(toml)


def _plain_cfg(tmp_path: Path, files) -> DatasetConfig:
    """Minimal programmatic config anchored at *tmp_path* (no [meta] keys)."""
    return DatasetConfig(name="t", repo_id="user/t", files=files, _base_dir=tmp_path)


class TestUndeclaredDialectByteIdentical:
    """No declared dialect => byte-identical to the pre-change output (E5)."""

    def test_undeclared_dialect_matches_prechange_bytes(self, tmp_path):
        """The undeclared path adds no read_options, so bytes are unchanged.

        The reference is recreated at test time from the pre-change read shape
        (sniff + ``pyarrow.csv.read_csv`` with no ``read_options``, through the
        same writer), so a permitted pyarrow upgrade moves both sides together
        and cannot break the assertion for the wrong reason.
        """
        import pyarrow.csv as pc

        from sofer._converters import _sniff_csv_delimiter, _write_parquet_table

        csv = tmp_path / "data.csv"
        csv.write_text("col_a;col_b\n1;alpha\n2;beta\n", encoding="utf-8-sig")
        cfg = _plain_cfg(tmp_path, [])
        result = convert_file_to_parquet(csv, tmp_path / "staging", cfg)

        delimiter = _sniff_csv_delimiter(csv, config.CSV_ENCODING)
        reference_table = pc.read_csv(csv, parse_options=pc.ParseOptions(delimiter=delimiter))
        reference = _write_parquet_table(reference_table, tmp_path / "reference", csv.stem)

        assert result["data"].read_bytes() == reference.read_bytes()


class TestDeclaredDialectWins:
    """Declared dialect wins end-to-end; single home is exercised (E1, E2)."""

    def test_declared_delimiter_outside_sniff_set_uncollapsed(self, tmp_path):
        """Mis-split catcher (E1): a declared ``|`` keeps the true column count."""
        (tmp_path / "data.csv").write_text("col1|col2|col3\nval1|val2|val3\n", encoding="utf-8-sig")
        cfg = _declared_cfg(tmp_path, 'csv_delimiter = "|"\n')
        assert "csv_delimiter" in cfg.declared_meta_keys
        out = tmp_path / "build"
        rc = prepare(cfg, out)
        assert rc == 0
        table = pq.read_table(out / "data.parquet")
        assert table.num_columns == 3
        assert table.column_names == ["col1", "col2", "col3"]

    def test_declared_semicolon_wins_over_comma_sniff(self, tmp_path):
        """Declared ``;`` on a ``;`` file converts through the declared seam."""
        (tmp_path / "data.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _declared_cfg(tmp_path, 'csv_delimiter = ";"\n')
        staging = tmp_path / "staging"
        result = convert_file_to_parquet(tmp_path / "data.csv", staging, cfg)
        assert result
        assert pq.read_table(result["data"]).column_names == ["a", "b"]

    def test_undeclared_dialect_prepare_delegated_to_single_home(self, tmp_path, monkeypatch):
        """PC-U06 single home: prepare() routes CSV conversion through _converters."""
        from sofer import _converters
        from sofer.prepare import prepare

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _plain_cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        seen: list[tuple[object, ...]] = []
        original = _converters.convert_file_to_parquet

        def _spy(local, staging_dir, cfg_arg=None):
            seen.append((local, cfg_arg))
            return original(local, staging_dir, cfg_arg)

        monkeypatch.setattr(_converters, "convert_file_to_parquet", _spy)
        rc = prepare(cfg, tmp_path / "build")
        assert rc == 0
        assert seen, "prepare() did not route through _converters"
        assert seen[0][1] is cfg


class TestDeclaredEncodingHonoured:
    """Declared encoding actually governs the read (E4)."""

    def test_declared_encoding_decodes_and_does_not_stage_csv(self, tmp_path):
        """A cp1252 file decodes correctly and the original CSV is not staged."""
        (tmp_path / "data.csv").write_bytes("name\nJos\u00e9\n".encode("cp1252"))
        cfg = _declared_cfg(tmp_path, 'csv_encoding = "cp1252"\n')
        out = tmp_path / "build"
        rc = prepare(cfg, out)
        assert rc == 0
        table = pq.read_table(out / "data.parquet")
        assert table.column("name").to_pylist() == ["Jos\u00e9"]
        assert not (out / "data.csv").exists()

    def test_undeclared_encoding_still_falls_back_to_tool_wide(self, tmp_path):
        """An undeclared encoding keeps the tool-wide read (no read_options)."""
        (tmp_path / "data.csv").write_bytes("name\nJos\u00e9\n".encode("cp1252"))
        cfg = _plain_cfg(tmp_path, [])
        staging = tmp_path / "staging"
        result = convert_file_to_parquet(tmp_path / "data.csv", staging, cfg)
        assert result == {}


class TestDeclaredDisagreementWarning:
    """D2: warn naming both values, keep the declared one, never fail (E3)."""

    def test_declared_delimiter_disagreement_warns_and_keeps_declared(self, tmp_path, capsys):
        """A declared ``;`` on a ``,`` file warns with both values, non-blocking."""
        (tmp_path / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8-sig")
        cfg = _declared_cfg(tmp_path, 'csv_delimiter = ";"\n')
        staging = tmp_path / "staging"
        result = convert_file_to_parquet(tmp_path / "data.csv", staging, cfg)
        out = capsys.readouterr().out
        assert result, "declared dialect must still convert (non-blocking)"
        assert ";" in out and "," in out
        assert "declared" in out.lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  Conversion pipeline — upload() integration tests (mocked HF calls)
# ═══════════════════════════════════════════════════════════════════════════════


class TestConversionPipeline:
    """Conversion loop in the prepare/publish flow — CSVs are converted,
    upload_as_csv and .parquet entries are staged as-is."""

    def test_csv_converted_when_not_upload_as_csv(self, tmp_path, monkeypatch):
        """upload_as_csv=False (default): CSV should be converted to Parquet."""
        csv = tmp_path / "data.csv"
        csv.write_text("x\n1\n2\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv")],
            _base_dir=tmp_path,
        )

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        publish(cfg, target="hf")

        # Verify that data.parquet was staged (not data.csv)
        staging_root = td / "repo"
        assert (staging_root / "data.parquet").is_file()
        assert not (staging_root / "data.csv").exists()

    def test_csv_not_converted_when_upload_as_csv(self, tmp_path, monkeypatch):
        """upload_as_csv=True should skip conversion, upload original CSV."""
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

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        publish(cfg, target="hf")

        # No .parquet should be created for this entry
        staging_root = td / "repo"
        assert (staging_root / "raw.csv").is_file()
        assert not (staging_root / "raw.parquet").exists()

    def test_parquet_passthrough_skips_conversion(self, tmp_path, monkeypatch):
        """Existing .parquet files should be passed through without conversion."""
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

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        publish(cfg, target="hf")

        # The original parquet file should still exist and be staged
        assert parquet_path.exists()
        assert (td / "repo" / "existing.parquet").is_file()

    def test_non_csv_file_passthrough(self, tmp_path, monkeypatch):
        """Non-CSV, non-Parquet files should pass through without conversion."""
        json_path = tmp_path / "meta.json"
        json_path.write_text('{"key": "value"}', encoding="utf-8")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=json_path, remote="meta.json")],
            _base_dir=tmp_path,
        )

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        publish(cfg, target="hf")

        assert json_path.exists()
        assert (td / "repo" / "meta.json").is_file()


class TestKeepCsv:
    """keep_csv flag behaviour — publish both Parquet and CSV, or just Parquet."""

    def test_keep_csv_false_uploads_only_parquet(self, tmp_path, monkeypatch):
        """Without keep_csv, only the Parquet file should be staged."""
        csv = tmp_path / "data.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv")],
            _base_dir=tmp_path,
        )

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        publish(cfg, target="hf")

        # Should have data.parquet (NOT data.csv) in staging
        staging_root = td / "repo"
        assert (staging_root / "data.parquet").is_file()
        assert not (staging_root / "data.csv").exists()

    def test_keep_csv_true_uploads_both(self, tmp_path, monkeypatch):
        """With keep_csv=True, both Parquet and original CSV should be staged."""
        csv = tmp_path / "data.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv")],
            _base_dir=tmp_path,
        )

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        publish(cfg, target="hf", keep_csv=True)

        staging_root = td / "repo"
        assert (staging_root / "data.parquet").is_file()
        assert (staging_root / "data.csv").is_file()


class TestUploadFileSelection:
    """Upload path and remote path are correct for converted files."""

    def test_converted_file_uses_staging_path(self, tmp_path, monkeypatch):
        """Converted Parquet should be staged in staging_root with correct remote path."""
        csv = tmp_path / "data.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv")],
            _base_dir=tmp_path,
        )

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        publish(cfg, target="hf")

        # Parquet should be in staging_root under repo/
        staging_root = td / "repo"
        parquet_files = list(staging_root.rglob("*.parquet"))
        assert len(parquet_files) > 0
        assert str(td) in str(parquet_files[0])

    def test_converted_file_parquet_remote(self, tmp_path, monkeypatch):
        """Staged file should have .parquet extension at correct relative path."""
        csv = tmp_path / "data.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")

        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[FileEntry(local=csv, remote="data.csv")],
            _base_dir=tmp_path,
        )

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        publish(cfg, target="hf")

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
        from sofer._converters import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == ";"

    def test_comma_delimiter(self, tmp_path):
        """Comma-heavy first line should pick comma."""
        csv = tmp_path / "data.csv"
        csv.write_text("a,b,c,d\n1,2,3,4", encoding="utf-8-sig")
        from sofer._converters import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == ","

    def test_tab_delimiter(self, tmp_path):
        """Tab-separated first line should pick tab."""
        csv = tmp_path / "data.tsv"
        csv.write_text("a\tb\tc\n1\t2\t3", encoding="utf-8-sig")
        from sofer._converters import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == "\t"

    def test_quoted_commas_not_counted(self, tmp_path):
        """Commas inside double-quoted fields should not sway the count."""
        csv = tmp_path / "data.csv"
        csv.write_text('id;"name, with comma";age\n1;Alice;30', encoding="utf-8-sig")
        from sofer._converters import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == ";"

    def test_quoted_semicolons_not_counted(self, tmp_path):
        """Semicolons inside double-quoted fields should not sway the count."""
        csv = tmp_path / "data.csv"
        csv.write_text('id,name,"desc; with semicolons"\n1,Alice,ok', encoding="utf-8-sig")
        from sofer._converters import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == ","

    def test_fallback_on_unreadable(self, tmp_path):
        """Unreadable file should fall back to semicolon default."""
        csv = tmp_path / "ghost.csv"
        # File does not exist
        from sofer._converters import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == ";"

    def test_edge_case_all_quoted(self, tmp_path):
        """When every field is quoted, delimiter between quotes should still count."""
        csv = tmp_path / "data.csv"
        csv.write_text('"a";"b";"c"\n1;2;3', encoding="utf-8-sig")
        from sofer._converters import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == ";"

    def test_edge_case_empty_file(self, tmp_path):
        """An empty file should fall back to semicolon."""
        csv = tmp_path / "empty.csv"
        csv.write_text("", encoding="utf-8-sig")
        from sofer._converters import _sniff_csv_delimiter

        assert _sniff_csv_delimiter(csv) == ";"


# ═══════════════════════════════════════════════════════════════════════════════
#  Upload integration — delimiter plumbing
# ═══════════════════════════════════════════════════════════════════════════════


class TestDelimiterPlumbing:
    """cfg.csv_delimiter is passed through to the conversion via prepare()."""

    def test_custom_delimiter_used_via_upload(self, tmp_path, monkeypatch):
        """A declared ``|`` survives the publish seam with its true columns.

        The declared-TOML seam is required because ``declared_meta_keys`` — the
        presence signal PC-U01 keys on — is populated only by
        ``DatasetConfig.from_toml``. Asserting the column count, not the mere
        presence of ``data.parquet``, is what makes a mis-split fail: a
        one-column Parquet satisfies an existence-only check (issue #205 F1).
        """
        (tmp_path / "data.csv").write_text("col1|col2\nval1|val2", encoding="utf-8-sig")
        cfg = _declared_cfg(tmp_path, 'csv_delimiter = "|"\n')

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        publish(cfg, target="hf")

        staging_root = td / "repo"
        parquet_path = staging_root / "data.parquet"
        assert parquet_path.is_file()
        table = pq.read_table(parquet_path)
        assert table.num_columns == 2
        assert table.column_names == ["col1", "col2"]
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
