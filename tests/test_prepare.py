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


def _raise_network(*_args: Any, **_kwargs: Any) -> None:
    """Any HF API call raises — proves prepare never touches the network."""
    raise AssertionError("network call attempted")


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

    def test_full_run_produces_artifacts_offline(self, tmp_path: Path, monkeypatch) -> None:
        """Every HF API call raises; prepare still generates all artifacts."""
        from sofer import uploader

        monkeypatch.setattr(uploader._api, "create_repo", _raise_network)
        monkeypatch.setattr(uploader._api, "upload_folder", _raise_network)
        monkeypatch.setattr(uploader._api, "upload_file", _raise_network)

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
        assert (out / "data/PROV/train.parquet").is_file()
        assert (out / "data/DPTO/train.parquet").is_file()
        # Distinct content — same-stem conversion must not collide.
        prov = pq.read_table(out / "data/PROV/train.parquet").to_pydict()
        dpto = pq.read_table(out / "data/DPTO/train.parquet").to_pydict()
        assert prov["a"] == [1]
        assert dpto["a"] == [3]

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
        """Without --all-files: no codebooks dir + advisory to run codebook cmd."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"

        rc = prepare(cfg, out)
        captured = capsys.readouterr()
        assert rc == 0
        assert not (out / "codebooks").exists()
        assert "sofer codebook" in captured.err
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
