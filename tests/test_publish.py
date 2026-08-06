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
from sofer.publish import _needs_prepare, publish

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
