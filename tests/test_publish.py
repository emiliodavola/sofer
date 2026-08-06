"""Tests for sofer.publish — delivery of a prepared package (PUB-01..04, PUB-07).

Covers the delivery half of the prepare/publish split: the auto-prepare
signal (PUB-03), hf staging + single upload_folder call (PUB-01), the
quality gate, the local target's offline copy and in-place summary
(PUB-02), --dry-run which never prepares and never touches the network
(PUB-04), and --keep-csv (PUB-07).
"""

from __future__ import annotations

import os
import shutil as _shutil
import tempfile
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from sofer import publish as publish_mod
from sofer.model import DatasetConfig, FileEntry
from sofer.prepare import prepare
from sofer.publish import (
    _check_overwrite_protection,
    _needs_prepare,
    _repo_diff_summary,
    publish,
)

# Fixed timestamps (seconds since epoch) with wide gaps so mtime comparisons
# are immune to filesystem timestamp granularity.
_OLD = 1_600_000_000.0  # 2020-09-13
_MID = 1_700_000_000.0  # 2023-11-14
_NEW = 1_800_000_000.0  # 2027-01-15


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
    """Any HF API call raises — proves publish never touches the network."""
    raise AssertionError("network call attempted")


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
    monkeypatch.setattr(_shutil, "rmtree", lambda p, **kw: None)
    return td


# ═══════════════════════════════════════════════════════════════════════════════
#  PUB-03 — auto-prepare signal (_needs_prepare)
# ═══════════════════════════════════════════════════════════════════════════════


class TestNeedsPrepare:
    """_needs_prepare: missing parquet / newer TOML / newer source / up-to-date."""

    def test_missing_parquet_returns_true(self, tmp_path: Path) -> None:
        """No parquet files at all (missing or empty output dir) -> True."""
        out = tmp_path / "build"
        assert _needs_prepare(_cfg(tmp_path, []), out) is True
        out.mkdir()
        assert _needs_prepare(_cfg(tmp_path, []), out) is True

    def test_toml_newer_than_parquet_returns_true(self, tmp_path: Path) -> None:
        """dataset.toml modified after the newest parquet -> True."""
        out = tmp_path / "build"
        out.mkdir()
        pq.write_table(pa.table({"a": [1]}), out / "data.parquet")
        toml = tmp_path / "dataset.toml"
        toml.write_text("[dataset]", encoding="utf-8")
        os.utime(out / "data.parquet", (_MID, _MID))
        os.utime(toml, (_NEW, _NEW))

        assert _needs_prepare(_cfg(tmp_path, []), out) is True

    def test_source_newer_than_parquet_returns_true(self, tmp_path: Path) -> None:
        """A declared source CSV modified after the parquet -> True (TOML unchanged)."""
        out = tmp_path / "build"
        out.mkdir()
        pq.write_table(pa.table({"a": [1]}), out / "data.parquet")
        toml = tmp_path / "dataset.toml"
        toml.write_text("[dataset]", encoding="utf-8")
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        os.utime(out / "data.parquet", (_MID, _MID))
        os.utime(toml, (_OLD, _OLD))
        os.utime(csv, (_NEW, _NEW))

        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        assert _needs_prepare(cfg, out) is True

    def test_up_to_date_returns_false(self, tmp_path: Path) -> None:
        """Parquet newest of TOML and all sources -> False."""
        out = tmp_path / "build"
        out.mkdir()
        pq.write_table(pa.table({"a": [1]}), out / "data.parquet")
        toml = tmp_path / "dataset.toml"
        toml.write_text("[dataset]", encoding="utf-8")
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        os.utime(out / "data.parquet", (_NEW, _NEW))
        os.utime(toml, (_MID, _MID))
        os.utime(csv, (_OLD, _OLD))

        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        assert _needs_prepare(cfg, out) is False


# ═══════════════════════════════════════════════════════════════════════════════
#  PUB-02 — local target
# ═══════════════════════════════════════════════════════════════════════════════


class TestLocalTarget:
    """--target local writes a complete package, zero network."""

    def test_writes_package_offline(self, tmp_path: Path, monkeypatch) -> None:
        """--output receives the parquet tree, README.md and LICENSE offline."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"
        prepare(cfg, out)  # assemble the package first

        monkeypatch.setattr(publish_mod._api, "create_repo", _raise_network)
        monkeypatch.setattr(publish_mod._api, "list_repo_files", _raise_network)
        monkeypatch.setattr(publish_mod._api, "upload_folder", _raise_network)

        rc = publish(cfg, target="local", output_dir="./out")
        assert rc == 0
        assert (tmp_path / "out" / "data.parquet").is_file()
        assert (tmp_path / "out" / "README.md").is_file()
        assert (tmp_path / "out" / "LICENSE").is_file()

    def test_output_omitted_is_in_place_summary(self, tmp_path: Path, monkeypatch, capsys) -> None:
        """No --output -> package summary printed, nothing mutated."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"
        prepare(cfg, out)

        before = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())

        monkeypatch.setattr(publish_mod._api, "create_repo", _raise_network)
        rc = publish(cfg, target="local")
        captured = capsys.readouterr()

        after = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
        assert rc == 0
        assert after == before, "in-place summary must not mutate the package"
        assert "Local target" in captured.out


# ═══════════════════════════════════════════════════════════════════════════════
#  PUB-01 — quality gate blocks hf delivery
# ═══════════════════════════════════════════════════════════════════════════════


class TestQualityGate:
    """A failing quality report blocks hf delivery before any network call."""

    def test_failed_report_blocks_before_network(self, tmp_path: Path, monkeypatch) -> None:
        from sofer.checks import ValidationReport
        from sofer.quality import QualityResult

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])

        report = ValidationReport("test")
        report.quality_results = [
            QualityResult(check="corrupt_records", severity="fail", message="bad")
        ]

        monkeypatch.setattr(publish_mod._api, "create_repo", _raise_network)
        monkeypatch.setattr(publish_mod._api, "list_repo_files", _raise_network)
        monkeypatch.setattr(publish_mod._api, "upload_folder", _raise_network)

        rc = publish(cfg, target="hf", quality_report=report)
        assert rc == 1

    def test_clean_report_proceeds(self, tmp_path: Path, monkeypatch) -> None:
        """A clean report passes the gate; delivery completes (rc 0)."""
        from sofer.checks import ValidationReport

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])

        _mock_hf_api(monkeypatch)
        _fixed_staging(tmp_path, monkeypatch)

        rc = publish(cfg, target="hf", quality_report=ValidationReport("test"))
        assert rc == 0


# ═══════════════════════════════════════════════════════════════════════════════
#  PUB-05 — auto-generated files always overwrite (codebooks included)
# ═══════════════════════════════════════════════════════════════════════════════


class TestAutoGeneratedProtection:
    """_is_auto_generated: README/LICENSE/codebooks always overwrite (PUB-05)."""

    def test_compliance_names_are_auto_generated(self) -> None:
        from sofer.publish import _is_auto_generated

        assert _is_auto_generated("README.md") is True
        assert _is_auto_generated("LICENSE") is True
        assert _is_auto_generated("codebook.md") is True

    def test_codebook_paths_are_auto_generated(self) -> None:
        """Any codebooks/**/*.md remote is auto-generated (never protected)."""
        from sofer.publish import _is_auto_generated

        assert _is_auto_generated("codebooks/DPTO.md") is True
        assert _is_auto_generated("codebooks/Labels/etiquetas_a.md") is True

    def test_data_files_are_protected(self) -> None:
        from sofer.publish import _is_auto_generated

        assert _is_auto_generated("data.parquet") is False
        assert _is_auto_generated("data/PROV/train.parquet") is False
        assert _is_auto_generated("docs/README.md") is False  # not the root card

    def test_case_insensitive_match(self) -> None:
        from sofer.publish import _is_auto_generated

        assert _is_auto_generated("readme.md") is True
        assert _is_auto_generated("CodeBooks/DPTO.md") is True


# ═══════════════════════════════════════════════════════════════════════════════
#  PUB-04 — dry run
# ═══════════════════════════════════════════════════════════════════════════════


class TestDryRun:
    """--dry-run prints diff + split report; never prepares; no network."""

    def test_no_network_no_prepare_no_mutation(self, tmp_path: Path, monkeypatch, capsys) -> None:
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"

        monkeypatch.setattr(publish_mod._api, "create_repo", _raise_network)
        monkeypatch.setattr(publish_mod._api, "list_repo_files", _raise_network)
        monkeypatch.setattr(publish_mod._api, "upload_folder", _raise_network)

        rc = publish(cfg, dry_run=True)
        captured = capsys.readouterr()

        assert rc == 0
        assert not (out / "data.parquet").exists(), "dry-run must not run prepare"
        assert "Dry-run complete" in captured.out
        assert "ADDED" in captured.out  # diff summary from planned remotes


# ═══════════════════════════════════════════════════════════════════════════════
#  PUB-03 — auto-prepare triggers
# ═══════════════════════════════════════════════════════════════════════════════


class TestAutoPrepare:
    """publish runs prepare (force=True) when artifacts are stale or missing."""

    def _spy_prepare(self, monkeypatch) -> list[tuple[Any, ...]]:
        from sofer import publish as publish_mod

        calls: list[tuple[Any, ...]] = []
        orig = publish_mod.prepare

        def spy(cfg_: Any, out_: Any, **kw: Any) -> int:
            calls.append((cfg_, out_, kw))
            return orig(cfg_, out_, **kw)

        monkeypatch.setattr(publish_mod, "prepare", spy)
        return calls

    def test_missing_parquet_triggers_prepare(self, tmp_path: Path, monkeypatch) -> None:
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)
        calls = self._spy_prepare(monkeypatch)

        rc = publish(cfg, target="hf")
        assert rc == 0
        assert len(calls) == 1
        _cfg_arg, out_arg, kw = calls[0]
        assert out_arg == out.resolve()
        assert kw.get("force") is True
        assert (out / "data.parquet").is_file(), "prepare must have generated parquet"
        assert (td / "repo" / "data.parquet").is_file()

    def test_toml_newer_triggers_prepare(self, tmp_path: Path, monkeypatch) -> None:
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"
        prepare(cfg, out)

        toml = tmp_path / "dataset.toml"
        toml.write_text("[dataset]", encoding="utf-8")
        os.utime(out / "data.parquet", (_MID, _MID))
        os.utime(toml, (_NEW, _NEW))

        _mock_hf_api(monkeypatch)
        _fixed_staging(tmp_path, monkeypatch)
        calls = self._spy_prepare(monkeypatch)

        rc = publish(cfg, target="hf")
        assert rc == 0
        assert len(calls) == 1
        assert calls[0][1] == out.resolve()
        assert calls[0][2].get("force") is True

    def test_up_to_date_skips_prepare(self, tmp_path: Path, monkeypatch) -> None:
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"
        prepare(cfg, out)

        toml = tmp_path / "dataset.toml"
        toml.write_text("[dataset]", encoding="utf-8")
        os.utime(out / "data.parquet", (_NEW, _NEW))
        os.utime(toml, (_MID, _MID))
        os.utime(csv, (_OLD, _OLD))

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)
        calls = self._spy_prepare(monkeypatch)

        rc = publish(cfg, target="hf")
        assert rc == 0
        assert calls == [], "up-to-date package must skip prepare"
        assert (td / "repo" / "data.parquet").is_file(), "existing package delivered"


# ═══════════════════════════════════════════════════════════════════════════════
#  PUB-01 / PUB-07 — hf staging + single upload_folder call
# ═══════════════════════════════════════════════════════════════════════════════


class TestHfPublish:
    """hf target: single upload_folder call, staged mirror, split report."""

    def test_full_publish_upload_folder_called_once(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        from sofer import publish as publish_mod
        from sofer.checks import ValidationReport

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"

        monkeypatch.setattr(publish_mod._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(
            publish_mod._api,
            "list_repo_files",
            lambda *a, **kw: ["data.parquet", "README.md", "LICENSE"],
        )
        monkeypatch.setattr(publish_mod._api, "upload_folder", lambda *a, **kw: None)
        _fixed_staging(tmp_path, monkeypatch)

        calls: list[tuple[Any, ...]] = []
        orig = publish_mod._hf_upload_folder

        def track(*args: Any, **kwargs: Any) -> bool:
            calls.append(args)
            return orig(*args, **kwargs)

        monkeypatch.setattr(publish_mod, "_hf_upload_folder", track)

        report = ValidationReport("test")  # clean report — gate passes
        rc = publish(cfg, target="hf", quality_report=report)
        captured = capsys.readouterr()

        assert rc == 0
        assert len(calls) == 1, f"expected 1 upload_folder call, got {len(calls)}"
        staging_root = Path(calls[0][1])
        assert (staging_root / "data.parquet").is_file()
        assert (staging_root / "README.md").is_file()
        assert (staging_root / "LICENSE").is_file()
        assert (out / "data.parquet").is_file(), "auto-prepare must have run first"
        assert "Split detection" in captured.out  # post-upload split report
        assert "OVERWRITTEN" in captured.out  # diff against existing repo files

    def test_keep_csv_stages_csv_alongside_parquet(self, tmp_path: Path, monkeypatch) -> None:
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        rc = publish(cfg, target="hf", keep_csv=True)
        assert rc == 0
        staging_root = td / "repo"
        assert (staging_root / "data.parquet").is_file()
        assert (staging_root / "data.csv").is_file(), "--keep-csv must stage the CSV"
        assert (staging_root / "data.csv").read_text(encoding="utf-8-sig") == "a;b\n1;2\n"

    def test_upload_folder_failure_returns_1(self, tmp_path: Path, monkeypatch) -> None:
        from sofer import publish as publish_mod

        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"
        prepare(cfg, out)  # build first so auto-prepare stays quiet

        td = tmp_path / "_staging"
        td.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda: str(td))
        monkeypatch.setattr(publish_mod._api, "create_repo", lambda *a, **kw: None)
        monkeypatch.setattr(publish_mod._api, "list_repo_files", lambda *a, **kw: [])

        def _boom(*_a: Any, **_kw: Any) -> bool:
            raise RuntimeError("Simulated network failure")

        monkeypatch.setattr(publish_mod, "_hf_upload_folder", _boom)

        rc = publish(cfg, target="hf")
        assert rc == 1
        assert not td.exists(), "staging tmpdir should be cleaned up"

    def test_recursive_tree_staged_without_exception(self, tmp_path: Path, monkeypatch) -> None:
        assets = tmp_path / "assets"
        (assets / "nested").mkdir(parents=True)
        (assets / "a.txt").write_text("a", encoding="utf-8")
        (assets / "nested" / "b.txt").write_text("b", encoding="utf-8")
        empty = tmp_path / "empty"
        empty.mkdir()

        cfg = _cfg(
            tmp_path,
            [
                FileEntry(local=assets, remote="assets/", recursive=True),
                FileEntry(local=empty, remote="empty/", recursive=True),
            ],
        )
        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        rc = publish(cfg, target="hf")
        assert rc == 0
        staging_root = td / "repo"
        assert (staging_root / "assets" / "a.txt").is_file()
        assert (staging_root / "assets" / "nested" / "b.txt").is_file()
        assert (staging_root / "empty").is_dir()


# ═══════════════════════════════════════════════════════════════════════════════
#  Repo diff summary (moved from test_uploader, PR 4)
# ═══════════════════════════════════════════════════════════════════════════════


class TestRepoDiffSummary:
    """_repo_diff_summary: planned files shown as ADDED or OVERWRITTEN."""

    def test_empty_repo(self, tmp_path):
        """An empty repo should show all files as new."""
        data = tmp_path / "data.csv"
        data.write_text("x\n1\n", encoding="utf-8")
        cfg = _cfg(tmp_path, [FileEntry(local=data, remote="data.csv")])
        summary = _repo_diff_summary(cfg, [], keep_csv=False)
        assert "ADDED" in summary
        assert "data.parquet" in summary
        assert "README.md" in summary
        assert "LICENSE" in summary

    def test_existing_files_show_as_modified(self, tmp_path):
        """Files already in the repo should show as OVERWRITTEN."""
        cfg = _cfg(tmp_path, [])
        summary = _repo_diff_summary(
            cfg,
            existing_files=["README.md", "LICENSE", "data.parquet"],
            keep_csv=False,
        )
        assert "OVERWRITTEN" in summary
        assert "README.md" in summary
        assert "LICENSE" in summary

    def test_repo_diff_summary_lists_codebook_remotes(self, tmp_path):
        """_repo_diff_summary includes codebook remotes when provided (RC-C01)."""
        cfg = _cfg(tmp_path, [FileEntry(local=tmp_path / "data.csv", remote="data.csv")])
        codebook_remotes = ["codebooks/data.md", "codebook.md"]
        summary = _repo_diff_summary(
            cfg, existing_files=[], keep_csv=False, codebook_remotes=codebook_remotes
        )
        assert "codebooks/data.md" in summary
        assert "codebook.md" in summary


# ═══════════════════════════════════════════════════════════════════════════════
#  Overwrite protection (moved from test_uploader, PR 4)
# ═══════════════════════════════════════════════════════════════════════════════


class TestOverwriteProtection:
    """_check_overwrite_protection: README/LICENSE are auto-generated (PUB-05)."""

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


# ═══════════════════════════════════════════════════════════════════════════════
#  Batch staging (moved from test_uploader, PR 4) — PUB-01 staging contract
# ═══════════════════════════════════════════════════════════════════════════════


class TestBatchStaging:
    """hf staging: mirror layout, single upload_folder call, NOT FOUND skip."""

    def test_parquet_placed_in_remote_subdirs(self, tmp_path, monkeypatch):
        """Converted Parquet files are staged at their remote-relative path,
        not flat in the staging root."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data/PROV/data.csv")])

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        rc = publish(cfg, target="hf")
        assert rc == 0

        staging_root = Path(td) / "repo"
        expected = staging_root / "data" / "PROV" / "data.parquet"
        assert expected.is_file(), (
            f"Expected {expected}, found files: {list(staging_root.rglob('*'))}"
        )
        assert not (staging_root / "data.parquet").exists(), (
            "Parquet should NOT be flat in the staging root — it must mirror the remote path"
        )

    def test_codebooks_staged_in_staging(self, tmp_path, monkeypatch):
        """Codebooks from the prepared package + root index are staged."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"
        prepare(cfg, out, all_files=True)  # parquet + codebooks/data.md + codebook.md

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        rc = publish(cfg, target="hf")
        assert rc == 0

        staging_root = Path(td) / "repo"
        assert (staging_root / "codebooks" / "data.md").is_file()
        assert (staging_root / "codebook.md").is_file()

    def test_no_codebooks_means_nothing_codebook_staged(self, tmp_path, monkeypatch):
        """Negative path: when prepare ran without --all-files, publish stages
        no codebook files at all (no codebooks/ dir, no root index)."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"
        prepare(cfg, out)  # no --all-files → no codebooks generated

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        rc = publish(cfg, target="hf")
        assert rc == 0

        staging_root = Path(td) / "repo"
        assert not (staging_root / "codebooks").exists()
        assert not (staging_root / "codebook.md").exists()

    def test_upload_folder_called_once(self, tmp_path, monkeypatch):
        """_hf_upload_folder is called exactly once; _hf_upload is NOT."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        upload_folder_calls: list[tuple[Any, ...]] = []
        upload_file_calls: list[tuple[Any, ...]] = []
        orig_folder = publish_mod._hf_upload_folder
        orig_file = publish_mod._hf_upload

        def _track_folder(*args, **kwargs):
            upload_folder_calls.append(args)
            return orig_folder(*args, **kwargs)

        def _track_file(*args, **kwargs):
            upload_file_calls.append(args)
            return orig_file(*args, **kwargs)

        monkeypatch.setattr(publish_mod, "_hf_upload_folder", _track_folder)
        monkeypatch.setattr(publish_mod, "_hf_upload", _track_file)

        exit_code = publish(cfg, target="hf")
        assert exit_code == 0
        assert len(upload_folder_calls) == 1, (
            f"Expected 1 upload_folder call, got {len(upload_folder_calls)}"
        )
        staging_root = Path(td) / "repo"
        call_path = Path(upload_folder_calls[0][1]) if len(upload_folder_calls) > 0 else None
        assert call_path == staging_root, f"Called with {call_path}, expected {staging_root}"
        assert len(upload_file_calls) == 0, (
            f"_hf_upload was called {len(upload_file_calls)} times — should be 0"
        )

    def test_not_found_files_skipped_in_staging(self, tmp_path, monkeypatch):
        """Declared files missing on disk are reported, never staged."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        missing = tmp_path / "missing.csv"

        cfg = _cfg(
            tmp_path,
            [
                FileEntry(local=csv, remote="data.csv"),
                FileEntry(local=missing, remote="missing.csv"),
            ],
        )

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        rc = publish(cfg, target="hf")
        assert rc == 0

        staging_root = Path(td) / "repo"
        data_files = [
            str(f.relative_to(staging_root)) for f in staging_root.rglob("*") if f.is_file()
        ]
        assert any("data" in f for f in data_files), f"data file not staged: {data_files}"
        missing_files = [f for f in data_files if "missing" in f]
        assert missing_files == [], f"NOT FOUND file was staged: {missing_files}"

    def test_non_csv_files_copied_to_staging(self, tmp_path, monkeypatch):
        """Non-CSV files (e.g. .parquet) keep their remote path in staging."""
        parquet_file = tmp_path / "direct.parquet"
        pq.write_table(pa.table({"x": [1, 2, 3]}), parquet_file)

        cfg = _cfg(
            tmp_path,
            [FileEntry(local=parquet_file, remote="subdir/direct.parquet")],
        )

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        rc = publish(cfg, target="hf")
        assert rc == 0

        staging_root = Path(td) / "repo"
        expected = staging_root / "subdir" / "direct.parquet"
        assert expected.is_file(), f"Expected {expected}, found: {list(staging_root.rglob('*'))}"


# ═══════════════════════════════════════════════════════════════════════════════
#  README override end-to-end (moved from test_uploader, PR 4)
# ═══════════════════════════════════════════════════════════════════════════════


class TestReadmeOverride:
    """cfg.readme flows prepare → publish: the custom card is delivered."""

    def test_readme_file_used_when_set(self, tmp_path, monkeypatch):
        """Custom README content is generated by prepare and staged by publish."""
        custom_readme = tmp_path / "CUSTOM_README.md"
        custom_readme.write_text("# My Custom Dataset\n\nCustom content.", encoding="utf-8")

        csv = tmp_path / "data.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")
        cfg = _cfg(
            tmp_path,
            [FileEntry(local=csv, remote="data.csv")],
            readme=str(custom_readme),
        )
        out = tmp_path / "build"
        prepare(cfg, out)

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        rc = publish(cfg, target="hf")
        assert rc == 0

        staging_root = Path(td) / "repo"
        readme = staging_root / "README.md"
        assert readme.is_file(), "README.md missing from staging_root"
        content = readme.read_text(encoding="utf-8")
        assert "My Custom Dataset" in content
        assert "Custom content" in content

    def test_readme_fallback_when_file_missing(self, tmp_path, monkeypatch):
        """A missing cfg.readme falls back to the generated Dataset Card."""
        csv = tmp_path / "data.csv"
        csv.write_text("x\n1\n", encoding="utf-8-sig")
        cfg = _cfg(
            tmp_path,
            [FileEntry(local=csv, remote="data.csv")],
            readme="nonexistent.md",
        )
        out = tmp_path / "build"
        prepare(cfg, out)

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        rc = publish(cfg, target="hf")
        assert rc == 0

        staging_root = Path(td) / "repo"
        readme = staging_root / "README.md"
        assert readme.is_file(), "README.md missing from staging_root"
        assert "Dataset Card for test" in readme.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
#  Codebook upload (moved from test_uploader, PR 4) — RC-C01 / PUB-05
# ═══════════════════════════════════════════════════════════════════════════════


class TestCodebookUpload:
    """Codebooks from the prepared package are staged under codebooks/."""

    def test_codebook_uploaded_to_codebook_subpath(self, tmp_path, monkeypatch):
        """Per-file codebooks and root index staged with correct paths."""
        csv = tmp_path / "DPTO.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="DPTO.csv")])
        out = tmp_path / "build"
        prepare(cfg, out, all_files=True)  # generates codebooks/DPTO.md + codebook.md
        (out / "codebooks" / "PROV.md").write_text("# PROV codebook", encoding="utf-8")

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        rc = publish(cfg, target="hf")
        assert rc == 0

        staging_root = Path(td) / "repo"
        assert staging_root.is_dir()
        assert (staging_root / "codebooks" / "DPTO.md").is_file()
        assert (staging_root / "codebooks" / "PROV.md").is_file()
        assert (staging_root / "codebook.md").is_file()
        assert (staging_root / "DPTO.parquet").is_file(), "data file missing from staging"

    def test_legacy_codebook_not_uploaded(self, tmp_path, monkeypatch):
        """cfg.codebook declared in TOML is ignored; RC-C01 supersedes it."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        legacy_cb = tmp_path / "old_codebook.md"
        legacy_cb.write_text("# Legacy — should be ignored", encoding="utf-8")

        cfg = _cfg(
            tmp_path,
            [FileEntry(local=csv, remote="data.csv")],
            codebook=str(legacy_cb),  # legacy path — RC-C01 ignores it
        )
        out = tmp_path / "build"
        prepare(cfg, out, all_files=True)

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        rc = publish(cfg, target="hf")
        assert rc == 0

        staging_root = Path(td) / "repo"
        assert (staging_root / "codebooks" / "data.md").is_file()
        assert (staging_root / "codebook.md").is_file()
        assert not (staging_root / "old_codebook.md").exists()
        assert not (staging_root / "codebook" / "old_codebook.md").exists()

    def test_codebook_upload_order_data_first(self, tmp_path, monkeypatch):
        """Data and codebooks are staged together (single upload_folder call)."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"
        prepare(cfg, out, all_files=True)

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        rc = publish(cfg, target="hf")
        assert rc == 0

        staging_root = Path(td) / "repo"
        assert (staging_root / "data.parquet").is_file(), "Data file missing from staging"
        assert (staging_root / "codebooks" / "data.md").is_file(), "Codebook missing"
        assert (staging_root / "codebook.md").is_file(), "Root index missing"

    def test_root_index_uploaded_as_codebook_md(self, tmp_path, monkeypatch):
        """The prepared codebook.md is staged as codebook.md in the repo root."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
        cfg = _cfg(tmp_path, [FileEntry(local=csv, remote="data.csv")])
        out = tmp_path / "build"
        prepare(cfg, out, all_files=True)
        (out / "codebook.md").write_text("# Root index content", encoding="utf-8")

        _mock_hf_api(monkeypatch)
        td = _fixed_staging(tmp_path, monkeypatch)

        rc = publish(cfg, target="hf")
        assert rc == 0

        staging_root = Path(td) / "repo"
        root_idx = staging_root / "codebook.md"
        assert root_idx.is_file(), f"Missing: {root_idx}"
        assert root_idx.read_text(encoding="utf-8") == "# Root index content"
