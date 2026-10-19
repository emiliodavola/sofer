"""Regression tests for the tree-derived codebook promise (#354, PUB-12).

The root ``codebook.md`` index is the durable record of the promise: the
canonical chain writes it but creates ``codebooks/`` only when it writes a page,
so index-present/page-absent is exactly "promised and empty". These tests pin the
three facts ``tests/test_manifest.py`` cannot: the real write path produces that
state, no caller-supplied flag survives, and an older ``optional`` record is not
mistaken for path divergence.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from sofer.manifest import (
    ArtifactStatus,
    PackageManifest,
    build_package_manifest,
    refresh_manifest,
    write_manifest,
)
from sofer.model import DatasetConfig, FileEntry
from sofer.prepare import prepare
from sofer.publish import _delivery_divergence, publish


def _cfg(root: Path) -> DatasetConfig:
    """Build a one-file dataset rooted at *root*."""
    csv = root / "data.csv"
    csv.write_text("a;b\n1;2\n", encoding="utf-8-sig")
    return DatasetConfig(
        name="test",
        repo_id="user/test",
        files=[FileEntry(local=csv, remote="data.csv")],
        _base_dir=root,
    )


def test_prepare_all_files_records_the_real_promised_absence(tmp_path: Path) -> None:
    """``prepare --all-files`` writes the index without pages: record it missing.

    An unreadable source is the cheapest way to reach the real writer state
    ``codebook.md`` present + zero pages. The durable record must carry that
    absence, which the old caller-supplied flag never reached.
    """
    cfg = _cfg(tmp_path)
    (tmp_path / "data.csv").write_bytes(b"\xff\xfe\x00bad bytes")
    out = tmp_path / "build"

    assert prepare(cfg, out, all_files=True) == 0
    assert (out / "codebook.md").is_file()
    pages = sorted((out / "codebooks").rglob("*.md")) if (out / "codebooks").is_dir() else []
    assert pages == []

    durable = PackageManifest.from_dir(out)
    assert durable is not None
    assert [(e.path, e.status) for e in durable.of_type("codebook_page")] == [
        ("codebooks/", ArtifactStatus.MISSING)
    ]
    assert "codebooks/" in [e.path for e in durable.required_missing()]


def test_no_caller_supplied_codebooks_flag_remains() -> None:
    """S4: one home, the tree. The dead keyword is gone from every signature."""
    for fn in (
        build_package_manifest,
        write_manifest,
        refresh_manifest,
        publish,
        _delivery_divergence,
    ):
        assert "codebooks_required" not in inspect.signature(fn).parameters


def test_a_pre_change_optional_record_is_not_a_path_divergence(tmp_path: Path) -> None:
    """D6: a stale record blocks through required-missing, not path churn.

    A record written before this change says ``optional``. A ``missing`` entry is
    never part of the promised set, so the recount agrees with the record and the
    divergence guard stays empty; the block the human sees names the artifact and
    the recovery.
    """
    cfg = _cfg(tmp_path)
    out = tmp_path / "build"
    assert prepare(cfg, out) == 0
    (out / "codebook.md").write_text("# index\n", encoding="utf-8")
    write_manifest(cfg, out)

    record_path = out / "manifest.json"
    doc = json.loads(record_path.read_text(encoding="utf-8"))
    for entry in doc["artifacts"]:
        if entry["artifact_type"] == "codebook_page":
            entry["status"] = "optional"
    record_path.write_text(json.dumps(doc, sort_keys=True, indent=2), encoding="utf-8")

    old_record = PackageManifest.from_dir(out)
    assert old_record is not None
    assert [(e.path, e.status) for e in old_record.of_type("codebook_page")] == [
        ("codebooks/", ArtifactStatus.OPTIONAL)
    ]
    assert _delivery_divergence(cfg, out, old_record) == ([], [])
    assert build_package_manifest(cfg, out).required_missing()
