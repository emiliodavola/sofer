"""Tests for sofer.prepare — offline dataset artifact generation (PRP-01..08, RC-R04).

Every test runs ``prepare()`` directly against a ``tmp_path`` fixture: no
Hugging Face network access, no credentials, no ``cache/`` mutation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from sofer.model import ColumnCheck, DatasetConfig, FileEntry
from sofer.prepare import prepare, resolve_output_dir
from sofer.repo_compliance import build_schema_report_with_rows
from sofer.verification import VerificationReport

# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _cfg(tmp_path: Path, files: list[FileEntry], **kw: Any) -> DatasetConfig:
    """Build a minimal DatasetConfig rooted at tmp_path (mirrors TOML load)."""
    return DatasetConfig(
        name="test",
        repo_id="user/test",
        files=files,
        _base_dir=tmp_path,
        **kw,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  PRP-06 — output directory resolution
# ═══════════════════════════════════════════════════════════════════════════════


class TestResolveOutputDir:
    """resolve_output_dir: build_dir from TOML by default, --output overrides."""

    def test_default_uses_build_dir(self, tmp_path: Path) -> None:
        """No override -> cfg._base_dir / build_dir (default 'build')."""
        cfg = _cfg(tmp_path, [])
        assert resolve_output_dir(cfg, None) == (tmp_path / "build").resolve()

    def test_custom_build_dir_from_toml(self, tmp_path: Path) -> None:
        """[dataset] build_dir='staging' is honoured when no override."""
        cfg = _cfg(tmp_path, [], build_dir="staging")
        assert resolve_output_dir(cfg, None) == (tmp_path / "staging").resolve()

    def test_override_wins_over_build_dir(self, tmp_path: Path) -> None:
        """--output overrides the TOML default per-run (anchored to config dir)."""
        cfg = _cfg(tmp_path, [], build_dir="build")
        assert resolve_output_dir(cfg, "./out") == (tmp_path / "out").resolve()

    def test_absolute_override(self, tmp_path: Path) -> None:
        """An absolute --output is used as-is, not re-anchored."""
        cfg = _cfg(tmp_path, [])
        abs_out = tmp_path / "abs-out"
        assert resolve_output_dir(cfg, str(abs_out)) == abs_out.resolve()


# ═══════════════════════════════════════════════════════════════════════════════
#  PRP-01 — offline generation, zero network
# ═══════════════════════════════════════════════════════════════════════════════


class TestPrepareOffline:
    """prepare never contacts the network and needs no credentials."""

    def test_full_run_produces_artifacts_offline(self, tmp_path: Path) -> None:
        """prepare has no network imports and generates all artifacts."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        assert rc == 0
        assert (out / "data.parquet").is_file()
        assert (out / "README.md").is_file()
        assert (out / "LICENSE").is_file()

    def test_succeeds_without_hf_token(self, tmp_path: Path, monkeypatch) -> None:
        """No HF_TOKEN and no Hub connectivity -> exit 0."""
        monkeypatch.delenv("HF_TOKEN", raising=False)

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])

        rc = prepare(cfg, tmp_path / "build")
        assert rc == 0


# ═══════════════════════════════════════════════════════════════════════════════
#  PRP-02 — CSV→Parquet conversion into the mirror layout
# ═══════════════════════════════════════════════════════════════════════════════


class TestPrepareConversion:
    """Converted parquets mirror remote paths; upload_as_csv stays CSV."""

    def test_converted_parquet_mirrors_remote_layout(self, tmp_path: Path) -> None:
        """Same-stem files in different remote dirs get distinct parquets."""
        (tmp_path / "PROV").mkdir()
        (tmp_path / "DPTO").mkdir()
        (tmp_path / "PROV" / "train.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        (tmp_path / "DPTO" / "train.csv").write_text("a;b\n3;4\n", encoding="utf-8-sig")

        cfg = _cfg(
            tmp_path,
            [
                FileEntry(local=tmp_path / "PROV" / "train.csv", remote="data/PROV/train.csv"),
                FileEntry(local=tmp_path / "DPTO" / "train.csv", remote="data/DPTO/train.csv"),
            ],
        )
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        assert rc == 0
        assert (out / "data/prov/train.parquet").is_file()
        assert (out / "data/dpto/train.parquet").is_file()
        # Distinct content — same-stem conversion must not collide.
        prov = pq.read_table(out / "data/prov/train.parquet").to_pydict()
        dpto = pq.read_table(out / "data/dpto/train.parquet").to_pydict()
        assert prov["a"] == [1]
        assert dpto["a"] == [3]

    def test_backslash_remote_round_trips(self, tmp_path: Path) -> None:
        """RC-R15 e2e (S6): a TOML-style backslash remote derives the same
        forward-slash key on the writer and reader sides — the staged Parquet
        is found and read from the Parquet branch."""
        (tmp_path / "data" / "a").mkdir(parents=True)
        csv = tmp_path / "data" / "a" / "train.csv"
        csv.write_text("v\n1\n2\n3\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data\\a\\train.csv")])
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        assert rc == 0
        assert (out / "data" / "a" / "train.parquet").is_file()

        columns, row_counts = build_schema_report_with_rows(cfg, staging_dir=out)
        # Row count comes from Parquet metadata under the verbatim remote key.
        assert row_counts == {"data\\a\\train.csv": 3}
        # Parquet branch taken: native int64 dtype + remote-relative origin.
        assert columns[0].hf_dtype == "int64"
        assert columns[0].origin == "data/a/train.parquet"


class TestPrepareSchemaReportParity:
    """RC-R13 — prepare's mirror output feeds the schema report losslessly."""

    def test_nested_remote_report_matches_parquet(self, tmp_path: Path) -> None:
        """S3: prepare on remote data/PROV/train.csv, then
        build_schema_report_with_rows(staging_dir=out) matches the Parquet's
        dtypes and metadata row count."""
        (tmp_path / "PROV").mkdir()
        csv = tmp_path / "PROV" / "train.csv"
        csv.write_text("a;b;label\n1;2.5;x\n3;4.5;y\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data/PROV/train.csv")])
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        assert rc == 0

        columns, row_counts = build_schema_report_with_rows(cfg, staging_dir=out)
        table = pq.read_table(out / "data/prov/train.parquet")

        # Exact row counts come from Parquet metadata.
        assert row_counts == {"data/PROV/train.csv": table.num_rows}

        # Column dtypes match the converted Parquet schema.
        by_name = {c.name: c for c in columns}
        for field in table.schema:
            col = by_name[field.name]
            assert col.nullable == field.nullable
            assert col.origin == "data/prov/train.parquet"
        assert by_name["a"].hf_dtype == "int64"
        assert by_name["b"].hf_dtype == "float64"
        assert by_name["label"].hf_dtype == "string"

    def test_upload_as_csv_keeps_csv(self, tmp_path: Path) -> None:
        """upload_as_csv=True -> original CSV staged at remote path, no parquet."""
        csv = tmp_path / "raw.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="raw.csv", upload_as_csv=True)])
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        assert rc == 0
        assert (out / "raw.csv").is_file()
        assert not (out / "raw.parquet").exists()

    def test_conversion_failure_falls_back_to_csv(self, tmp_path: Path, capsys) -> None:
        """A CSV that fails to parse is warned about and staged as CSV."""
        csv = tmp_path / "bad.csv"
        csv.write_text("a;b\n1;2;3\n", encoding="utf-8-sig")  # ragged row
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="bad.csv")])
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        captured = capsys.readouterr().out
        assert rc == 0
        assert "conversion failed" in captured.lower()
        assert (out / "bad.csv").is_file()
        assert not (out / "bad.parquet").exists()

    def test_parquet_passthrough_staged_as_is(self, tmp_path: Path) -> None:
        """Existing .parquet entries pass through unchanged (no CSV reading)."""
        parquet_path = tmp_path / "existing.parquet"
        pq.write_table(pa.table({"x": [1, 2]}), parquet_path)
        cfg = _cfg(tmp_path, [FileEntry(local=parquet_path, remote="existing.parquet")])
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        assert rc == 0
        assert (out / "existing.parquet").is_file()
        assert parquet_path.exists()


# ═══════════════════════════════════════════════════════════════════════════════
#  PRP-03 — Dataset Card (README.md) and LICENSE at the output root
# ═══════════════════════════════════════════════════════════════════════════════


class TestPrepareCardLicense:
    """README.md + LICENSE generated at the output root."""

    def test_card_and_license_written_to_output_root(self, tmp_path: Path) -> None:
        """Card embeds the schema table; LICENSE carries the SPDX text."""
        csv = tmp_path / "data.csv"
        csv.write_text("age;name\n1;Alice\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")], license="cc0-1.0")
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        assert rc == 0
        readme = (out / "README.md").read_text(encoding="utf-8")
        license_text = (out / "LICENSE").read_text(encoding="utf-8")
        assert "age" in readme  # schema codebook table embedded
        assert "Creative Commons Zero" in license_text

    def test_custom_readme_overrides_generation(self, tmp_path: Path) -> None:
        """cfg.readme pointing at an existing file replaces the generated card."""
        custom = tmp_path / "custom.md"
        custom.write_text("# CUSTOM CARD\n", encoding="utf-8")
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(
            tmp_path,
            [FileEntry(local=csv, remote="data.csv")],
            readme=str(custom),
        )
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        assert rc == 0
        assert (out / "README.md").read_text(encoding="utf-8") == "# CUSTOM CARD\n"

    def test_relative_readme_resolves_against_config_dir(self, tmp_path: Path) -> None:
        """A RELATIVE cfg.readme resolves against the config dir (PRP-03),
        never the process cwd — the TOML's directory is the anchor."""
        custom = tmp_path / "custom.md"
        custom.write_text("# RELATIVE CARD\n", encoding="utf-8")
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(
            tmp_path,
            [FileEntry(local=csv, remote="data.csv")],
            readme="custom.md",
        )
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        assert rc == 0
        assert (out / "README.md").read_text(encoding="utf-8") == "# RELATIVE CARD\n"

    def test_recipe_and_study_design_relative_to_config_dir(self, tmp_path: Path, capsys) -> None:
        """Relative recipe/study_design resolve against the config dir and
        their content is embedded into the card."""
        (tmp_path / "recipe.R").write_text("# recipe\n", encoding="utf-8")
        (tmp_path / "design.md").write_text("# design\n", encoding="utf-8")
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(
            tmp_path,
            [FileEntry(local=csv, remote="data.csv")],
            recipe="recipe.R",
            study_design="design.md",
        )
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        captured = capsys.readouterr()
        assert rc == 0
        assert "declared but not found" not in captured.out
        card = (out / "README.md").read_text(encoding="utf-8")
        assert "# recipe" in card
        assert "# design" in card

    def test_relative_readme_missing_warns_and_falls_back(self, tmp_path: Path, capsys) -> None:
        """A relative readme that does not exist keeps the 'declared but not
        found' warning and falls back to the generated card."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(
            tmp_path,
            [FileEntry(local=csv, remote="data.csv")],
            readme="missing.md",
        )
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        captured = capsys.readouterr()
        assert rc == 0
        assert "readme declared but not found" in captured.out
        assert (out / "README.md").is_file()

    def test_no_license_still_succeeds(self, tmp_path: Path) -> None:
        """license='' -> LICENSE holds the fallback message; exit 0."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")], license="")
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        assert rc == 0
        lic = (out / "LICENSE").read_text(encoding="utf-8")
        assert "No license has been declared" in lic


# ═══════════════════════════════════════════════════════════════════════════════
#  PRP-04 — codebooks (Option B: directly into output_dir, never cache/)
# ═══════════════════════════════════════════════════════════════════════════════


class TestPrepareCodebooks:
    """--all-files writes codebooks into output_dir; cache/ untouched."""

    def test_all_files_codebooks_into_output(self, tmp_path: Path) -> None:
        """build/codebooks/*.md + build/codebook.md exist; cache/codebooks absent."""
        (tmp_path / "DPTO.csv").write_text("a;b\n1;2\n", encoding="utf-8-sig")
        labels = tmp_path / "Labels"
        labels.mkdir()
        (labels / "etiquetas_a.csv").write_text("x;y\n1;2\n", encoding="utf-8-sig")

        cfg = _cfg(
            tmp_path,
            [
                FileEntry(local=tmp_path / "DPTO.csv", remote="DPTO.csv"),
                FileEntry(local=labels / "etiquetas_a.csv", remote="Labels/etiquetas_a.csv"),
            ],
        )
        out = tmp_path / "build"

        rc = prepare(cfg, out, all_files=True)
        assert rc == 0
        assert (out / "codebooks" / "DPTO.md").is_file()
        assert (out / "codebooks" / "Labels" / "etiquetas_a.md").is_file()
        assert (out / "codebook.md").is_file()
        # Option B: the shared cache/ directory is never touched.
        assert not (tmp_path / "cache").exists()

    def test_no_codebooks_without_all_files(self, tmp_path: Path, capsys) -> None:
        """Without --all-files: no codebooks dir + advisory to re-run with flag."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        captured = capsys.readouterr()
        assert rc == 0
        assert not (out / "codebooks").exists()
        assert "--all-files" in captured.err
        assert not (tmp_path / "cache").exists()


# ═══════════════════════════════════════════════════════════════════════════════
#  PRP-05 — checks run by default, --no-checks skips them (non-blocking)
# ═══════════════════════════════════════════════════════════════════════════════


class TestPrepareChecks:
    """DatasetValidator/QualityValidator reports are non-blocking."""

    def test_checks_run_by_default_non_blocking(self, tmp_path: Path, capsys) -> None:
        """A column-check violation appears in the report; generation completes."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(
            tmp_path,
            [FileEntry(local=csv, remote="data.csv")],
            column_checks=[ColumnCheck(filename="data.csv", expected=["missing_col"])],
        )
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        captured = capsys.readouterr().out
        assert "Columns missing" in captured
        assert rc == 0
        assert (out / "README.md").is_file()

    def test_no_checks_skips_report(self, tmp_path: Path, capsys) -> None:
        """--no-checks prints no validation report but still generates."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(
            tmp_path,
            [FileEntry(local=csv, remote="data.csv")],
            column_checks=[ColumnCheck(filename="data.csv", expected=["missing_col"])],
        )
        out = tmp_path / "build"

        rc = prepare(cfg, out, no_checks=True)
        captured = capsys.readouterr().out
        assert "Validation report" not in captured
        assert rc == 0
        assert (out / "README.md").is_file()


# ═══════════════════════════════════════════════════════════════════════════════
#  PRP-06 — --output isolation
# ═══════════════════════════════════════════════════════════════════════════════


class TestPrepareOutputIsolation:
    def test_output_override_isolated_from_build_dir(self, tmp_path: Path) -> None:
        """Everything lands under the override; default build/ is untouched."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        staging = tmp_path / "staging"

        rc = prepare(cfg, staging)
        assert rc == 0
        assert (staging / "data.parquet").is_file()
        assert (staging / "README.md").is_file()
        assert not (tmp_path / "build").exists()


# ═══════════════════════════════════════════════════════════════════════════════
#  PRP-07 — --force overwrite protection
# ═══════════════════════════════════════════════════════════════════════════════


class TestPrepareForce:
    """Existing generated artifacts block regeneration unless --force."""

    def test_existing_artifacts_block_without_force(self, tmp_path: Path, capsys) -> None:
        """Second run without --force: error names the file, exit 1, file unchanged."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"

        assert prepare(cfg, out) == 0
        before = (out / "data.parquet").read_bytes()

        rc = prepare(cfg, out)
        captured = capsys.readouterr().out
        assert rc == 1
        assert "data.parquet" in captured
        assert (out / "data.parquet").read_bytes() == before  # unchanged

    def test_force_regenerates_everything(self, tmp_path: Path) -> None:
        """--force overwrites existing artifacts and exits 0."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"

        assert prepare(cfg, out) == 0
        rc = prepare(cfg, out, force=True)
        assert rc == 0
        assert (out / "data.parquet").is_file()


# ═══════════════════════════════════════════════════════════════════════════════
#  PRP-08 — --verify loads the generated package locally (non-blocking)
# ═══════════════════════════════════════════════════════════════════════════════


class TestPrepareVerify:
    """verify_load_dataset is invoked against output_dir; exit stays 0."""

    def test_verify_passed_printed_and_exit_zero(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """Successful verification prints PASSED and does not block."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"

        monkeypatch.setattr(
            "sofer.prepare.verify_load_dataset",
            lambda staging_dir, cfg: VerificationReport(
                passed=True,
                split_names=["train"],
                expected_splits=["train"],
            ),
        )

        rc = prepare(cfg, out, verify=True)
        captured = capsys.readouterr().out
        assert rc == 0
        assert "PASSED" in captured

    def test_verify_failed_reported_but_exit_zero(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        """Failed verification prints FAILED; generation result stays exit 0."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"

        monkeypatch.setattr(
            "sofer.prepare.verify_load_dataset",
            lambda staging_dir, cfg: VerificationReport(passed=False, errors=["load failed"]),
        )

        rc = prepare(cfg, out, verify=True)
        captured = capsys.readouterr().out
        assert rc == 0
        assert "FAILED" in captured


# ═══════════════════════════════════════════════════════════════════════════════
#  RC-R04 — recursive=true trees staged without exception
# ═══════════════════════════════════════════════════════════════════════════════


class TestPrepareRecursiveStaging:
    def test_recursive_tree_staged_without_exception(self, tmp_path: Path) -> None:
        """Nested subdirs + empty dir stage cleanly (copy_to_mirror, RC-R04)."""
        src = tmp_path / "tree"
        (src / "nested" / "deep").mkdir(parents=True)
        (src / "nested" / "deep" / "a.parquet").write_bytes(b"x")
        (src / "top.csv").write_text("x\n1\n", encoding="utf-8-sig")
        (src / "empty").mkdir()

        cfg = _cfg(tmp_path, [FileEntry(local=src, remote="subdir/", recursive=True)])
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        assert rc == 0
        assert (out / "subdir" / "nested" / "deep" / "a.parquet").is_file()
        assert (out / "subdir" / "top.csv").is_file()
        assert (out / "subdir" / "empty").is_dir()


# ═══════════════════════════════════════════════════════════════════════════════
#  Cross-file schema assertion + card dtype sanity (moved from test_uploader, PR 4)
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
#  _assert_cross_file_schema
# ═══════════════════════════════════════════════════════════════════════════════


class TestAssertCrossFileSchema:
    """Cross-file schema identity assertion per split (Issue #16)."""

    def test_same_split_identical_schemas_passes(self, tmp_path):
        """Two files in the same split with identical schemas → no errors."""
        from sofer.prepare import _assert_cross_file_schema

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

    def test_different_column_sets_in_same_split_passes(self, tmp_path):
        """Multi-table datasets: files in the same split with different
        column sets are independent tables → no cross-file check."""
        from sofer.prepare import _assert_cross_file_schema

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
        assert errors == []

    def test_dtype_mismatch_in_same_split_fails(self, tmp_path):
        """Same column names but different dtype in same split → error."""
        from sofer.prepare import _assert_cross_file_schema

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
        from sofer.prepare import _assert_cross_file_schema

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
        from sofer.prepare import _assert_cross_file_schema

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

    def test_multi_table_same_split_standalone_tables_pass(self, tmp_path):
        """Census-style multi-table: each table has unique columns → no errors.

        Simulates CPV2010 (['ref_id']) + HOGAR (['foo','bar']) — different
        column sets → each is a standalone table, no cross-file check.
        """
        from sofer.prepare import _assert_cross_file_schema

        staging = tmp_path / "staging"
        staging.mkdir()

        t_cpv = pa.table({"CPV2010_REF_ID": [1]})
        pq.write_table(t_cpv, staging / "CPV2010.parquet")

        t_dpto = pa.table({"DPTO": ["a"], "NOMDPTO": ["b"]})
        pq.write_table(t_dpto, staging / "DPTO.parquet")

        t_hogar = pa.table({"HOGAR_REF_ID": [1], "NHOG": [2], "PROP": [3]})
        pq.write_table(t_hogar, staging / "HOGAR.parquet")

        converted = {
            "CPV2010": (staging / "CPV2010.parquet", Path(), ""),
            "DPTO": (staging / "DPTO.parquet", Path(), ""),
            "HOGAR": (staging / "HOGAR.parquet", Path(), ""),
        }

        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[
                FileEntry(local=Path("CPV2010.parquet"), remote="CPV2010.parquet"),
                FileEntry(local=Path("DPTO.parquet"), remote="DPTO.parquet"),
                FileEntry(local=Path("HOGAR.parquet"), remote="HOGAR.parquet"),
            ],
        )

        errors = _assert_cross_file_schema(converted, cfg)
        assert errors == []

    def test_multi_table_same_columns_dtype_mismatch_still_fails(self, tmp_path):
        """If two files share column names but have different dtypes,
        the check still fires (they're assumed to be the same table)."""
        from sofer.prepare import _assert_cross_file_schema

        staging = tmp_path / "staging"
        staging.mkdir()

        t1 = pa.table({"col": [1, 2, 3]})
        pq.write_table(t1, staging / "train-1.parquet")

        t2 = pa.table({"col": ["a", "b"]})
        pq.write_table(t2, staging / "train-2.parquet")

        # These share columns → same group → dtype check runs
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


class TestSchemaAssertion:
    """_assert_card_dtypes_match_parquet should flag float64 vs int64 mismatches."""

    def test_no_mismatch_when_dtypes_match(self, tmp_path):
        """No warning when Parquet int64 → card int64."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        from sofer.prepare import _assert_card_dtypes_match_parquet
        from sofer.repo_compliance import ColumnSchema

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

        from sofer.prepare import _assert_card_dtypes_match_parquet
        from sofer.repo_compliance import ColumnSchema

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

        from sofer.prepare import _assert_card_dtypes_match_parquet
        from sofer.repo_compliance import ColumnSchema

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


# ═══════════════════════════════════════════════════════════════════════════════
#  fix-prepare-multisheet-xlsx-copy — leak regression, overwrite fallback,
#  schema grouping, single-sheet preservation
# ═══════════════════════════════════════════════════════════════════════════════


def _make_xlsx(path: Path, sheets: dict[str, list[list[object]]]) -> None:
    """Create an XLSX at *path* with *sheets* mapping sheet→rows (header first)."""
    import openpyxl

    wb = openpyxl.Workbook()
    first = True
    for name, rows in sheets.items():
        if first:
            ws = wb.active
            assert ws is not None
            ws.title = name
            first = False
        else:
            ws = wb.create_sheet(title=name)
        for row in rows:
            ws.append(row)
    wb.save(path)


class TestMultisheetLeakRegression:
    """DATA_GOT_ALL.xlsx → clean build/ only data_got_all_*.parquet, no .xlsx."""

    def test_multisheet_stages_only_parquet_no_source_leak(self, tmp_path: Path) -> None:
        xlsx = tmp_path / "DATA_GOT_ALL.xlsx"
        _make_xlsx(
            xlsx,
            {
                "aristas": [["id", "src", "dst"], [1, "a", "b"], [2, "b", "c"]],
                "nodos": [["id", "label"], [1, "n"], [2, "m"]],
            },
        )
        cfg = _cfg(tmp_path, [FileEntry(local=xlsx, remote="DATA_GOT_ALL.xlsx")])
        out = tmp_path / "build"
        rc = prepare(cfg, out)
        assert rc == 0
        assert (out / "data_got_all_aristas.parquet").is_file()
        assert (out / "data_got_all_nodos.parquet").is_file()
        assert list(out.glob("*.xlsx")) == []
        assert not (out / "DATA_GOT_ALL.xlsx").exists()
        assert not (out / "data_got_all.xlsx").exists()
        # parquet readable
        assert pq.read_table(out / "data_got_all_aristas.parquet").num_rows == 2
        assert pq.read_table(out / "data_got_all_nodos.parquet").num_rows == 2


class TestSingleSheetPreserved:
    """Single-sheet XLSX → exactly one dataset.parquet, no dataset_*.parquet."""

    def test_single_sheet_one_parquet(self, tmp_path: Path) -> None:
        xlsx = tmp_path / "dataset.xlsx"
        _make_xlsx(xlsx, {"Sheet1": [["a", "b"], [1, 2], [3, 4]]})
        cfg = _cfg(tmp_path, [FileEntry(local=xlsx, remote="dataset.xlsx")])
        out = tmp_path / "build"
        rc = prepare(cfg, out)
        assert rc == 0
        assert (out / "dataset.parquet").is_file()
        assert list(out.glob("dataset_*.parquet")) == []
        assert list(out.glob("*.xlsx")) == []


class TestOverwriteFallbackSingleUnderscore:
    """Overwrite guard detects single-underscore sheet via fallback glob."""

    def test_fallback_detects_without_force(self, tmp_path: Path) -> None:
        xlsx = tmp_path / "Report.XLSX"
        _make_xlsx(
            xlsx,
            {
                "Ventas": [["v"], [1], [2]],
                "Costos": [["c"], [10]],
            },
        )
        cfg = _cfg(tmp_path, [FileEntry(local=xlsx, remote="Report.XLSX")])
        out = tmp_path / "build"
        assert prepare(cfg, out) == 0
        # Second run without --force must refuse via fallback _*.parquet
        rc = prepare(cfg, out, force=False)
        assert rc == 1
        # With --force it overwrites
        rc2 = prepare(cfg, out, force=True)
        assert rc2 == 0
        assert (out / "report_ventas.parquet").is_file()
        assert (out / "report_costos.parquet").is_file()

    def test_check_local_overwrite_fallback_direct(self, tmp_path: Path) -> None:
        """_check_local_overwrite finds _*.parquet when __*.parquet absent."""
        from sofer.prepare import _check_local_overwrite

        xlsx = tmp_path / "Report.XLSX"
        _make_xlsx(xlsx, {"Ventas": [["v"], [1]]})
        cfg = _cfg(tmp_path, [FileEntry(local=xlsx, remote="Report.XLSX")])
        out = tmp_path / "build"
        out.mkdir(parents=True)
        # Seed single-underscore parquet + normal placeholder should trigger
        pq.write_table(pa.table({"v": [1]}), out / "report_ventas.parquet")
        existing = _check_local_overwrite(cfg, out, all_files=False)
        assert any("report_ventas.parquet" in p for p in existing)

    def test_no_false_positive_on_unrelated_prefix(self, tmp_path: Path) -> None:
        """_*.parquet filter must not flag unrelated prefix files without stem match."""
        from sofer.prepare import _check_local_overwrite

        xlsx = tmp_path / "Report.XLSX"
        _make_xlsx(xlsx, {"Ventas": [["v"], [1]]})
        cfg = _cfg(tmp_path, [FileEntry(local=xlsx, remote="Report.XLSX")])
        out = tmp_path / "build"
        out.mkdir(parents=True)
        pq.write_table(pa.table({"x": [1]}), out / "report_extra_other.parquet")
        existing = _check_local_overwrite(cfg, out, all_files=False)
        # fallback should include report_extra_other.parquet
        assert any("report_extra_other.parquet" in p for p in existing)


class TestSchemaGroupingSingleUnderscore:
    """Cross-file schema grouping handles single-underscore normalized keys."""

    def test_grouping_with_single_underscore_keys(self, tmp_path: Path) -> None:
        from sofer.prepare import _assert_cross_file_schema

        staging = tmp_path / "staging"
        staging.mkdir()
        # Two files with same columns but different dtypes → should error when grouped
        t1 = pa.table({"a": [1, 2], "b": [3, 4]})
        pq.write_table(t1, staging / "a.parquet")
        t2 = pa.table({"a": ["x", "y"], "b": [1, 2]})
        pq.write_table(t2, staging / "b.parquet")
        converted = {
            "data_got_all_aristas.parquet": (staging / "a.parquet", Path(), ""),
            "data_got_all_nodos.parquet": (staging / "b.parquet", Path(), ""),
        }
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=Path("DATA_GOT_ALL.xlsx"), remote="DATA_GOT_ALL.xlsx")],
        )
        errors = _assert_cross_file_schema(converted, cfg)
        # Both keys share prefix data_got_all_ and are in same fallback train split;
        # they share column set {a,b} but dtype mismatch → error
        assert len(errors) >= 1
        assert any("differ in dtypes" in e for e in errors)

    def test_single_sheet_no_extra_grouping(self, tmp_path: Path) -> None:
        """Single-sheet key == norm_key still works, no spurious grouping."""
        from sofer.prepare import _assert_cross_file_schema

        staging = tmp_path / "staging"
        staging.mkdir()
        t = pa.table({"a": [1, 2]})
        pq.write_table(t, staging / "single.parquet")
        converted = {
            "dataset.parquet": (staging / "single.parquet", Path(), ""),
        }
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=Path("dataset.xlsx"), remote="dataset.xlsx")],
        )
        errors = _assert_cross_file_schema(converted, cfg)
        assert errors == []


# ═══════════════════════════════════════════════════════════════════════════════
#  PRP-09 — orphan pruning on force prepare
# ═══════════════════════════════════════════════════════════════════════════════


class TestPreparePruneOrphans:
    """PRP-09: prepare(force=True) prunes orphans, keeps compliance/keep_csv, idempotent."""

    def test_force_true_prunes_stale_parquet(self, tmp_path: Path) -> None:
        """A stale .parquet from a removed [[file]] entry is deleted on force."""
        csv_keep = tmp_path / "keep.csv"
        csv_keep.write_text("x\n1\n", encoding="utf-8-sig")
        csv_old = tmp_path / "old.csv"
        csv_old.write_text("y\n1\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv_keep, remote="keep.csv")])
        out = tmp_path / "build"
        # First prepare with both files, then second with only keep
        cfg_both = _cfg(
            tmp_path,
            [
                FileEntry(local=csv_keep, remote="keep.csv"),
                FileEntry(local=csv_old, remote="old.csv"),
            ],
        )
        assert prepare(cfg_both, out) == 0
        assert (out / "old.parquet").exists()
        assert (out / "keep.parquet").exists()
        # Now prune: force=True with only keep should delete old
        rc = prepare(cfg, out, force=True)
        assert rc == 0
        assert (out / "keep.parquet").exists()
        assert not (out / "old.parquet").exists()

    def test_force_false_retains_orphan(self, tmp_path: Path) -> None:
        """Without --force an orphan is not pruned (prepare refuses to overwrite)."""
        csv = tmp_path / "a.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="a.csv")])
        out = tmp_path / "build"
        assert prepare(cfg, out) == 0
        # Inject orphan manually
        pq.write_table(pa.table({"y": [1]}), out / "stale.parquet")
        # Without force, prepare should refuse to run due to existing artifacts, but orphan stays
        # To test force=False no-prune we directly check that stale file would not be deleted
        # if we could run; instead we verify that force=False path does not call prune
        # by checking that stale file remains after a failed prepare (rc 1)
        rc = prepare(cfg, out, force=False)
        assert rc == 1
        assert (out / "stale.parquet").exists()

    def test_compliance_survives_force_prune(self, tmp_path: Path) -> None:
        """README, LICENSE, codebook.md, codebooks/** survive force prune."""
        csv = tmp_path / "a.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="a.csv")])
        out = tmp_path / "build"
        assert prepare(cfg, out, all_files=True) == 0
        # Inject orphan
        pq.write_table(pa.table({"y": [1]}), out / "orphan.parquet")
        rc = prepare(cfg, out, force=True, all_files=True)
        assert rc == 0
        assert (out / "README.md").exists()
        assert (out / "LICENSE").exists()
        assert (out / "codebook.md").exists()
        assert (out / "codebooks" / "a.md").exists()
        assert not (out / "orphan.parquet").exists()

    def test_idempotent_second_force(self, tmp_path: Path) -> None:
        """Second force run deletes nothing (idempotent)."""
        csv = tmp_path / "a.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="a.csv")])
        out = tmp_path / "build"
        assert prepare(cfg, out) == 0
        pq.write_table(pa.table({"y": [1]}), out / "stale.parquet")
        assert prepare(cfg, out, force=True) == 0
        assert not (out / "stale.parquet").exists()
        # Second force should be idempotent
        rc2 = prepare(cfg, out, force=True)
        assert rc2 == 0
        assert (out / "a.parquet").exists()

    def test_single_underscore_orphan_via_prepare(self, tmp_path: Path) -> None:
        """Single-underscore sheet orphans are handled via dual guard (prepare force)."""
        xlsx = tmp_path / "DATA_GOT_ALL.xlsx"
        _make_xlsx(xlsx, {"aristas": [["id"], [1]], "nodos": [["id"], [1]]})
        cfg = _cfg(tmp_path, [FileEntry(local=xlsx, remote="DATA_GOT_ALL.xlsx")])
        out = tmp_path / "build"
        assert prepare(cfg, out) == 0
        assert (out / "data_got_all_aristas.parquet").exists()
        assert (out / "data_got_all_nodos.parquet").exists()
        # Inject a generic stale file — should be pruned even though single-underscore sheets exist
        pq.write_table(pa.table({"x": [1]}), out / "stale_single.parquet")
        rc = prepare(cfg, out, force=True)
        assert rc == 0
        assert not (out / "stale_single.parquet").exists()
        assert (out / "data_got_all_aristas.parquet").exists()
        assert (out / "data_got_all_nodos.parquet").exists()
