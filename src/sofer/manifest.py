"""Package artifact manifest (PRP-11/PUB-12, GitHub #122).

The package boundary is explicit: every artifact of the selected build
profile is classified as **publishable** (parquet incl. multi-sheet
expansion, csv when keep_csv, README.md, LICENSE, codebook.md,
codebooks/**) or **intermediate** (profiles, renders, per-sheet
intermediates, schema/card inputs). ``prepare`` writes the manifest into
the output directory; publish dry-run and confirm consume the SAME manifest
so their decisions never diverge.

Status vocabulary is the single source of truth for the "no false warning"
fix: an optional artifact absent is ``optional`` (never a missing-artifact
warning); a required artifact absent is ``missing`` and blocks publication.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from . import config

if TYPE_CHECKING:
    from .model import DatasetConfig

MANIFEST_NAME = "manifest.json"

# Root files always written by prepare (PRP-03): README card, LICENSE, and
# the standalone codebook.md when generated.
_ROOT_PUBLISHABLE: tuple[tuple[str, str, bool], ...] = (
    ("README.md", "card", True),
    ("LICENSE", "license", True),
    ("codebook.md", "codebook", False),
)


class ArtifactStatus(str, Enum):
    """Machine-readable status of one package artifact (PUB-12)."""

    STAGED = "staged"  # present in the output dir
    EXPECTED = "expected"  # promised by the profile, not yet verified
    OPTIONAL = "optional"  # optional and absent -- never a missing warning
    MISSING = "missing"  # required and absent -- blocks publication


@dataclass(frozen=True)
class ManifestEntry:
    """One classified artifact: source config, type, relative path, status."""

    source: str
    artifact_type: str
    path: str
    status: ArtifactStatus

    def to_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "artifact_type": self.artifact_type,
            "path": self.path,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ManifestEntry:
        return cls(
            source=str(data["source"]),
            artifact_type=str(data["artifact_type"]),
            path=str(data["path"]),
            status=ArtifactStatus(str(data["status"])),
        )


@dataclass(frozen=True)
class PackageManifest:
    """The package manifest: source config path plus classified entries."""

    source: str
    entries: tuple[ManifestEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "artifacts": [e.to_dict() for e in self.entries],
        }

    def json_bytes(self) -> bytes:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2).encode(config.OUTPUT_ENCODING)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PackageManifest:
        return cls(
            source=str(data["source"]),
            entries=tuple(ManifestEntry.from_dict(e) for e in data["artifacts"]),
        )

    @classmethod
    def from_json(cls, payload: bytes) -> PackageManifest:
        return cls.from_dict(json.loads(payload.decode(config.OUTPUT_ENCODING)))

    @classmethod
    def from_dir(cls, output_dir: Path) -> PackageManifest | None:
        """Read ``manifest.json`` from *output_dir*, or ``None`` when absent."""
        path = output_dir / MANIFEST_NAME
        if not path.is_file():
            return None
        return cls.from_json(path.read_bytes())

    def required_missing(self) -> list[ManifestEntry]:
        return [e for e in self.entries if e.status is ArtifactStatus.MISSING]

    def of_type(self, artifact_type: str) -> list[ManifestEntry]:
        return [e for e in self.entries if e.artifact_type == artifact_type]


def _real_config_path(cfg: DatasetConfig) -> Path:
    """The config's real path (custom-named TOMLs), matching publish staleness.

    ``Path()`` is the hand-built-config sentinel (issue #116); explicit
    compare before falling back to the default config name.
    """
    base = cfg._base_dir if cfg._base_dir else Path.cwd()
    if cfg._config_path != Path():
        return cfg._config_path
    return base / config.DEFAULT_CONFIG_NAME


def build_package_manifest(
    cfg: DatasetConfig,
    output_dir: Path,
    *,
    keep_csv: bool = False,
    codebooks_required: bool = False,
) -> PackageManifest:
    """Classify every artifact of the selected build profile under *output_dir*.

    Publishable set = ground-truth expanded remotes (PUB-10, multi-sheet
    ``stem__sheet.parquet`` included) + root files + per-file codebooks when
    present. Profiles and renders live under the dataset root and are always
    intermediate (staged when present, optional when the directory does not
    exist).

    Args:
        cfg: Dataset configuration (source identity for the manifest).
        output_dir: The prepared package directory (mirror layout root).
        keep_csv: Whether original CSVs upload alongside Parquet.

    Returns:
        A :class:`PackageManifest` with one entry per classified artifact.
    """
    from ._mirror import expanded_planned_remotes

    source = str(_real_config_path(cfg))
    entries: list[ManifestEntry] = []

    def _add(artifact_type: str, path: str, status: ArtifactStatus) -> None:
        entries.append(ManifestEntry(source, artifact_type, path, status))

    # Root publishable files
    for name, artifact_type, required in _ROOT_PUBLISHABLE:
        path = output_dir / name
        status = (
            ArtifactStatus.STAGED
            if path.is_file()
            else (ArtifactStatus.MISSING if required else ArtifactStatus.OPTIONAL)
        )
        _add(artifact_type, name, status)

    # Data remotes (ground truth expansion, PUB-10). Recursive entries are
    # directories: present when the directory tree exists in the output dir,
    # never a per-file MISSING (their files are enumerated at copy time).
    recursive_remotes = {
        entry.remote.rstrip("/\\").lower() for entry in cfg.files if entry.recursive
    }
    for remote in expanded_planned_remotes(cfg, keep_csv, output_dir):
        rel = PurePosixPath(remote)
        lower = remote.lower()
        is_recursive = remote.rstrip("/\\").lower() in recursive_remotes
        if is_recursive:
            present = (output_dir / rel).is_dir()
        else:
            present = (output_dir / rel).is_file()
        if lower.endswith(".parquet"):
            artifact_type = "parquet"
        elif lower.endswith(".csv"):
            artifact_type = "csv"
        else:
            artifact_type = "data"
        _add(
            artifact_type,
            remote,
            ArtifactStatus.STAGED if present else ArtifactStatus.MISSING,
        )

    # Per-file codebooks (RC-C01): uploaded when present; optional when absent.
    # When the surrounding flow promised them (codebooks_required, e.g. the MCP
    # canonical chain after codebook_all), their absence is MISSING and blocks.
    codebooks_dir = output_dir / config.CODEBOOKS_DIR
    if codebooks_dir.is_dir():
        for cb_path in sorted(codebooks_dir.rglob("*.md")):
            _add(
                "codebook_page",
                cb_path.relative_to(output_dir).as_posix(),
                ArtifactStatus.STAGED,
            )
    elif codebooks_required:
        _add(
            "codebook_page",
            f"{config.CODEBOOKS_DIR}/",
            ArtifactStatus.MISSING,
        )
    else:
        _add(
            "codebook_page",
            f"{config.CODEBOOKS_DIR}/",
            ArtifactStatus.OPTIONAL,
        )

    # Intermediate layers under the dataset root (never publishable)
    base = cfg._base_dir if cfg._base_dir else Path.cwd()
    for dir_name, artifact_type in (
        (config.PROFILE_DIR, "profile"),
        (config.RENDER_DIR, "render"),
    ):
        layer_dir = base / dir_name
        if layer_dir.is_dir():
            for layer_path in sorted(layer_dir.rglob("*")):
                if layer_path.is_file():
                    _add(
                        artifact_type,
                        layer_path.relative_to(base).as_posix(),
                        ArtifactStatus.STAGED,
                    )
        else:
            _add(artifact_type, f"{dir_name}/", ArtifactStatus.OPTIONAL)

    # Deterministic ordering: publishable set first (root, data), then
    # codebooks, then optional/intermediate layers -- stable JSON output.
    order = {
        "card": 0,
        "license": 1,
        "codebook": 2,
        "parquet": 3,
        "csv": 4,
        "data": 5,
        "codebook_page": 6,
        "profile": 7,
        "render": 8,
    }
    entries.sort(key=lambda e: (order.get(e.artifact_type, 9), e.path))
    return PackageManifest(source, tuple(entries))
