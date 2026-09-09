"""Unit tests for the package artifact manifest (PRP-11/PUB-12, #122).

Covers the manifest core: status vocabulary, exact publishable set for
single-sheet and multi-sheet sources, intermediate classification, and the
JSON contract written by prepare.
"""

from __future__ import annotations

import json
from pathlib import Path

from sofer.manifest import (
    MANIFEST_NAME,
    ArtifactStatus,
    PackageManifest,
    build_package_manifest,
)
from sofer.model import DatasetConfig

MINIMAL_TOML = """[dataset]
name = "x"
repo_id = "user/x"

[[file]]
local = "data.csv"
remote = "data.csv"
"""


def _dataset(tmp_path: Path) -> tuple[DatasetConfig, Path]:
    (tmp_path / "data.csv").write_text("a;b\n1;2\n3;4\n", encoding="utf-8")
    toml = tmp_path / "dataset.toml"
    toml.write_text(MINIMAL_TOML, encoding="utf-8")
    cfg = DatasetConfig.from_toml(toml)
    return cfg, tmp_path


def test_build_manifest_single_sheet_exact_set(tmp_path):
    cfg, root = _dataset(tmp_path)
    out = root / "build"
    out.mkdir()
    (out / "data.parquet").write_bytes(b"PAR1")
    (out / "README.md").write_text("# x\n", encoding="utf-8")
    (out / "LICENSE").write_text("MIT\n", encoding="utf-8")

    manifest = build_package_manifest(cfg, out)
    by_path = {e.path: e for e in manifest.entries}

    assert by_path["README.md"].artifact_type == "card"
    assert by_path["LICENSE"].artifact_type == "license"
    assert by_path["data.parquet"].artifact_type == "parquet"
    assert by_path["README.md"].status == ArtifactStatus.STAGED
    assert by_path["data.parquet"].status == ArtifactStatus.STAGED


def test_build_manifest_missing_required_data_is_missing(tmp_path):
    cfg, root = _dataset(tmp_path)
    out = root / "build"
    out.mkdir()
    # sin parquet: el remoto prometido existe como entrada pero no esta staged
    manifest = build_package_manifest(cfg, out)
    parquet = next(e for e in manifest.entries if e.artifact_type == "parquet")
    assert parquet.status == ArtifactStatus.MISSING, parquet


def test_build_manifest_optional_profile_intermediate(tmp_path):
    cfg, root = _dataset(tmp_path)
    out = root / "build"
    out.mkdir()
    profiles = root / "profiles"
    profiles.mkdir()
    (profiles / "metadata.yaml").write_text("x: 1\n", encoding="utf-8")

    manifest = build_package_manifest(cfg, out)
    prof = next(e for e in manifest.entries if e.artifact_type == "profile")
    assert prof.status == ArtifactStatus.STAGED
    # los renders ausentes son optional, nunca "missing" warn
    renders = [e for e in manifest.entries if e.artifact_type == "render"]
    assert renders and all(e.status == ArtifactStatus.OPTIONAL for e in renders)


def test_build_manifest_multi_sheet_expansion(tmp_path):
    cfg, root = _dataset(tmp_path)
    # xlsx multi-sheet: reescribir config con un .xlsx
    (root / "book.xlsx").touch()
    toml = root / "dataset.toml"
    toml.write_text(
        '[dataset]\nname = "x"\nrepo_id = "user/x"\n\n'
        '[[file]]\nlocal = "book.xlsx"\nremote = "book.xlsx"\n',
        encoding="utf-8",
    )
    cfg = DatasetConfig.from_toml(toml)
    out = root / "build"
    out.mkdir()
    # Real on-disk layout produced by prepare is single-underscore per
    # sheet (expanded_planned_remotes falls back to the stem_ glob; R2).
    (out / "book_Sheet1.parquet").write_bytes(b"P1")
    (out / "book_Sheet2.parquet").write_bytes(b"P2")

    manifest = build_package_manifest(cfg, out)
    parquets = sorted(e.path for e in manifest.entries if e.artifact_type == "parquet")
    assert parquets == ["book_Sheet1.parquet", "book_Sheet2.parquet"]


def test_prepare_writes_manifest_file(tmp_path):
    from sofer.prepare import prepare

    cfg, root = _dataset(tmp_path)
    out = root / "build"
    rc = prepare(cfg, out)
    assert rc == 0
    mf = out / MANIFEST_NAME
    assert mf.is_file(), "prepare must write manifest.json (PRP-11)"
    manifest = PackageManifest.from_json(mf.read_bytes())
    paths = {e.path for e in manifest.entries}
    assert "data.parquet" in paths
    assert "README.md" in paths and "LICENSE" in paths
    parquet = next(e for e in manifest.entries if e.artifact_type == "parquet")
    assert parquet.status == ArtifactStatus.STAGED


def test_manifest_json_roundtrip_stable(tmp_path):
    cfg, root = _dataset(tmp_path)
    out = root / "build"
    out.mkdir()
    (out / "data.parquet").write_bytes(b"PAR1")
    manifest = build_package_manifest(cfg, out)

    doc = json.loads(manifest.json_bytes())
    assert doc["source"] == str(cfg._config_path)
    assert doc["artifacts"]
    restored = PackageManifest.from_json(manifest.json_bytes())
    assert [e.path for e in restored.entries] == [e.path for e in manifest.entries]
    # stable roundtrip: bytes identicos
    assert PackageManifest.from_json(manifest.json_bytes()).json_bytes() == manifest.json_bytes()


def test_codebooks_required_when_flow_promises_them(tmp_path):
    cfg, root = _dataset(tmp_path)
    out = root / "build"
    out.mkdir()
    (out / "data.parquet").write_bytes(b"PAR1")

    optional = build_package_manifest(cfg, out)
    cb = next(e for e in optional.entries if e.artifact_type == "codebook_page")
    assert cb.status == ArtifactStatus.OPTIONAL

    promised = build_package_manifest(cfg, out, codebooks_required=True)
    cb2 = next(e for e in promised.entries if e.artifact_type == "codebook_page")
    assert cb2.status == ArtifactStatus.MISSING
    assert "codebooks/" in [e.path for e in promised.required_missing()]
