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
    ArtifactClass,
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


# ── #346: the delivery class is explicit, not inferred from artifact_type ────


def _prepared_tree(tmp_path: Path) -> tuple[DatasetConfig, Path, Path]:
    """A prepared package plus the local-only layers the pipeline writes.

    Returns ``(cfg, build_dir, root)`` with ``data.parquet``, the card, the
    license, one codebook page, and ``profile``/``render`` layers sitting where
    ``profile_all``/``render_all`` put them: under the artifact cache.
    """
    cfg, root = _dataset(tmp_path)
    out = root / "build"
    out.mkdir()
    (out / "data.parquet").write_bytes(b"PAR1")
    (out / "README.md").write_text("# x\n", encoding="utf-8")
    (out / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (out / "codebooks").mkdir()
    (out / "codebooks" / "data.md").write_text("# codebook\n", encoding="utf-8")
    profiles = root / "cache" / "profiles"
    profiles.mkdir(parents=True)
    (profiles / "data.metadata.yaml").write_text("x: 1\n", encoding="utf-8")
    renders = root / "cache" / "renders"
    renders.mkdir(parents=True)
    (renders / "data.README.md").write_text("# render\n", encoding="utf-8")
    return cfg, out, root


def test_every_entry_carries_an_explicit_classification(tmp_path: Path) -> None:
    """#346: no reader has to know which artifact types are never uploaded."""
    cfg, out, _root = _prepared_tree(tmp_path)

    manifest = build_package_manifest(cfg, out)

    assert all(isinstance(e.classification, ArtifactClass) for e in manifest.entries)
    assert {e.artifact_type for e in manifest.intermediate()} == {"profile", "render"}
    publishable_types = {e.artifact_type for e in manifest.publishable()}
    assert publishable_types == {"card", "license", "parquet", "codebook", "codebook_page"}
    # the absent optional codebook.md is publishable in principle, not delivered
    assert "codebook.md" in {e.path for e in manifest.publishable()}
    assert "codebook.md" not in {e.path for e in manifest.delivered()}


def test_delivered_set_is_the_staged_set(tmp_path: Path) -> None:
    """#346: what the manifest calls delivered is exactly what gets staged.

    This is the defect the issue reports, as one assertion: the manifest declared
    135 artifacts while `_copy_package` could stage 133. The two sets are now
    compared directly, on the same tree.
    """
    from sofer.publish import _copy_package

    cfg, out, root = _prepared_tree(tmp_path)
    manifest = build_package_manifest(cfg, out)
    dest = root / "staged"
    dest.mkdir()

    _copy_package(cfg, out, dest, keep_csv=False)

    staged = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())
    delivered = sorted(e.path for e in manifest.delivered())
    assert staged == delivered
    assert manifest.intermediate(), "the layers exist and are not part of the delivery"


def test_layer_probe_reads_the_artifact_cache(tmp_path: Path) -> None:
    """#346: the layers are reported where the pipeline writes them."""
    cfg, out, _root = _prepared_tree(tmp_path)

    manifest = build_package_manifest(cfg, out)

    profile = next(e for e in manifest.entries if e.artifact_type == "profile")
    assert profile.status == ArtifactStatus.STAGED
    assert profile.classification is ArtifactClass.INTERMEDIATE
    assert profile.path == "cache/profiles/data.metadata.yaml"


def test_layer_probe_still_reads_the_dataset_root(tmp_path: Path) -> None:
    """An explicitly located layer under the dataset root is still reported."""
    cfg, root = _dataset(tmp_path)
    out = root / "build"
    out.mkdir()
    (root / "renders").mkdir()
    (root / "renders" / "data.README.md").write_text("# r\n", encoding="utf-8")

    manifest = build_package_manifest(cfg, out)

    render = next(e for e in manifest.entries if e.artifact_type == "render")
    assert render.status == ArtifactStatus.STAGED
    assert render.path == "renders/data.README.md"


def test_manifest_without_classification_reads_as_publishable(tmp_path: Path) -> None:
    """A manifest written before the field existed still loads (#346 compat)."""
    legacy = {
        "source": "dataset.toml",
        "artifacts": [
            {
                "source": "dataset.toml",
                "artifact_type": "parquet",
                "path": "data.parquet",
                "status": "staged",
            }
        ],
    }

    manifest = PackageManifest.from_dict(legacy)

    assert manifest.entries[0].classification is ArtifactClass.PUBLISHABLE
    assert manifest.entries[0].to_dict()["classification"] == "publishable"
