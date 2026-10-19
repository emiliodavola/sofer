"""Package artifact manifest (PRP-11/PUB-12, GitHub #122).

The package boundary is explicit: every artifact of the selected build
profile is classified as **publishable** (parquet incl. multi-sheet
expansion, csv when keep_csv, README.md, LICENSE, codebook.md,
codebooks/**) or **intermediate** (profiles, renders, per-sheet
intermediates, schema/card inputs). ``prepare`` writes the manifest into
the output directory, and every later phase that adds package artifacts
refreshes it through :func:`write_manifest`, so the durable document on
disk is always the one a recount would produce (issue #349); publish
dry-run and confirm consume the SAME manifest so their decisions never
diverge.

Status vocabulary is the single source of truth for the "no false warning"
fix: an optional artifact absent is ``optional`` (never a missing-artifact
warning); a required artifact absent is ``missing`` and blocks publication.

Two independent axes, and they answer different questions. ``classification``
says whether an artifact belongs to the delivery at all; ``status`` says whether
it is present and whether its absence blocks. Before #346 only ``status``
existed, so a present-but-local-only layer (``profile``/``render``) was
indistinguishable from a deliverable one in the JSON, and every reader had to
know from memory which ``artifact_type`` values are never uploaded. The manifest
declared 135 artifacts on a corpus whose delivery was 133.
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


class ArtifactClass(str, Enum):
    """Delivery class of one package artifact (PUB-12, GitHub #346).

    ``classification`` answers *does this belong to the delivery*; ``status``
    answers *is it here, and does its absence block*. They are independent: an
    intermediate layer that is present is ``staged`` and still never uploaded.
    """

    PUBLISHABLE = "publishable"  # part of the delivery set
    INTERMEDIATE = "intermediate"  # local-only layer, regenerable, never uploaded


@dataclass(frozen=True)
class ManifestEntry:
    """One classified artifact: source config, type, relative path, status, class."""

    source: str
    artifact_type: str
    path: str
    status: ArtifactStatus
    classification: ArtifactClass = ArtifactClass.PUBLISHABLE

    def to_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "artifact_type": self.artifact_type,
            "path": self.path,
            "status": self.status.value,
            "classification": self.classification.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ManifestEntry:
        """Read one entry, defaulting ``classification`` for pre-#346 manifests."""
        return cls(
            source=str(data["source"]),
            artifact_type=str(data["artifact_type"]),
            path=str(data["path"]),
            status=ArtifactStatus(str(data["status"])),
            classification=ArtifactClass(
                str(data.get("classification", ArtifactClass.PUBLISHABLE.value))
            ),
        )

    @property
    def is_directory(self) -> bool:
        """Whether this entry denotes a tree rather than one file.

        A recursive remote is recorded as ONE directory entry (path with a
        trailing slash, the same marker the ``codebooks/``/``profiles/``
        placeholders use) because its files are enumerated at copy time, not by
        the manifest. Reading such an entry as a single delivered file would
        overstate the upload — and a tree that stages zero files would count as
        one (#346).
        """
        return self.path.endswith("/")


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

    def publishable(self) -> list[ManifestEntry]:
        """Entries that belong to the delivery set (``publishable``).

        This is the set the upload is measured against: the copy path stages
        exactly these plus nothing, so a reader counting them is counting what
        arrives (#346).
        """
        return [e for e in self.entries if e.classification is ArtifactClass.PUBLISHABLE]

    def intermediate(self) -> list[ManifestEntry]:
        """Local-only layers (``intermediate``): present or not, never uploaded."""
        return [e for e in self.entries if e.classification is ArtifactClass.INTERMEDIATE]

    def delivered(self) -> list[ManifestEntry]:
        """Publishable **file** entries that are present: what the upload stages.

        Derived, never a third classification: ``publishable`` answers *does this
        belong to the delivery*, ``status`` answers *is it here*, and this is the
        conjunction restricted to file entries. For them it equals the files
        ``_copy_package`` stages for the same tree, so counting it is counting what
        arrives (#346). An absent optional artifact — ``codebook.md`` before an
        ``--all-files`` prepare, a codebook page no flow promised — is publishable
        in principle and still not delivered, which is why ``publishable()`` alone
        must not be read as the delivery set.

        Directory entries (:attr:`ManifestEntry.is_directory`) are excluded: a
        recursive remote is a tree whose files the copy path enumerates, so it is
        never one delivered file, and a tree that stages nothing (an empty
        directory) contributes nothing here.
        """
        return [
            e
            for e in self.entries
            if e.classification is ArtifactClass.PUBLISHABLE
            and e.status is ArtifactStatus.STAGED
            and not e.is_directory
        ]

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
    present. Profiles and renders are always ``intermediate`` and never
    publishable: they are probed where the pipeline actually writes them (the
    artifact cache, ``<root>/<output_dir>/<dir>``) and under the dataset root for
    an explicit location, so the entry reports the tree instead of a path nobody
    writes to (#346).

    Args:
        cfg: Dataset configuration (source identity for the manifest).
        output_dir: The prepared package directory (mirror layout root).
        keep_csv: Whether original CSVs upload alongside Parquet.
        codebooks_required: Whether the surrounding flow promised per-file
            codebooks, which makes an absent ``codebooks/`` block instead of warn.

    Returns:
        A :class:`PackageManifest` with one entry per artifact, each carrying an
        explicit :class:`ArtifactClass`.
    """
    from ._mirror import expanded_planned_remotes

    source = str(_real_config_path(cfg))
    entries: list[ManifestEntry] = []

    def _add(
        artifact_type: str,
        path: str,
        status: ArtifactStatus,
        classification: ArtifactClass = ArtifactClass.PUBLISHABLE,
    ) -> None:
        entries.append(ManifestEntry(source, artifact_type, path, status, classification))

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
        # A recursive remote is a TREE, not a file: its files are enumerated at
        # copy time, so the recorded path keeps the directory marker (#346) and
        # never counts as one delivered file.
        recorded = f"{remote.rstrip('/')}/" if is_recursive else remote
        _add(
            artifact_type,
            recorded,
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

    # Intermediate layers (never publishable, PUB-12/#346). profile_all and
    # render_all write them under the artifact cache, and an explicit run may
    # place them under the dataset root, so both locations are probed: reporting
    # a layer at a root nobody writes to is what made every entry read
    # ``optional`` while the layers were sitting in ``cache/``.
    base = cfg._base_dir if cfg._base_dir else Path.cwd()
    for dir_name, artifact_type in (
        (config.PROFILE_DIR, "profile"),
        (config.RENDER_DIR, "render"),
    ):
        layer_dir = next(
            (
                candidate
                for candidate in (base / config.OUTPUT_DIR / dir_name, base / dir_name)
                if candidate.is_dir()
            ),
            None,
        )
        if layer_dir is None:
            _add(
                artifact_type,
                f"{dir_name}/",
                ArtifactStatus.OPTIONAL,
                ArtifactClass.INTERMEDIATE,
            )
            continue
        for layer_path in sorted(layer_dir.rglob("*")):
            if not layer_path.is_file():
                continue
            try:
                rel_path = layer_path.relative_to(base).as_posix()
            except ValueError:  # layer dir outside base (absolute output_dir)
                rel_path = layer_path.as_posix()
            _add(
                artifact_type,
                rel_path,
                ArtifactStatus.STAGED,
                ArtifactClass.INTERMEDIATE,
            )

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


def write_manifest(
    cfg: DatasetConfig,
    output_dir: Path,
    *,
    keep_csv: bool = False,
    codebooks_required: bool = False,
    only_if_present: bool = False,
) -> Path | None:
    """Write (or refresh) the durable ``manifest.json`` in *output_dir*.

    The single writer of the package's durable record (PRP-11, issue #349):
    ``prepare`` creates it, and every later phase that adds package artifacts
    calls this again, so the file on disk is never a stale prepare-time snapshot
    while the delivery has moved on.

    A phase that wrote outside a package directory asks with
    ``only_if_present=True``: it then gets ``None`` back instead of inventing a
    package record for a tree ``prepare`` never prepared.

    Args:
        cfg: Dataset configuration (source identity for the manifest).
        output_dir: The package directory the manifest describes.
        keep_csv: Whether original CSVs belong to the delivery (PUB-07).
        codebooks_required: Whether the surrounding flow promised per-file
            codebooks, which makes an absent ``codebooks/`` block instead of warn.
        only_if_present: Refresh only when a manifest already exists here.

    Returns:
        The path written, or ``None`` when *only_if_present* held and there was
        nothing to refresh.
    """
    path = output_dir / MANIFEST_NAME
    if only_if_present and not path.is_file():
        return None
    path.write_bytes(
        build_package_manifest(
            cfg,
            output_dir,
            keep_csv=keep_csv,
            codebooks_required=codebooks_required,
        ).json_bytes()
    )
    return path


def _package_output_dir(cfg: DatasetConfig) -> Path:
    """The resolved package directory for *cfg* (``[dataset] build_dir``)."""
    from .prepare import resolve_output_dir

    return resolve_output_dir(cfg, None)


def refresh_manifest(
    cfg: DatasetConfig,
    written_to: Path | None = None,
    *,
    keep_csv: bool = False,
    codebooks_required: bool = False,
) -> Path | None:
    """Refresh the durable manifest of the package a phase just wrote into.

    Every phase that adds package artifacts calls this at the end of its run
    (issue #349), so the file on disk is never a prepare-time snapshot while the
    delivery has moved on. Nothing is created: a manifest is refreshed only where
    one already exists, so a phase can never invent a package record for a tree
    ``prepare`` never prepared.

    Args:
        cfg: Dataset configuration (source identity for the manifest).
        written_to: The resolved directory the phase wrote into. ``None`` means it
            wrote to the shared artifact cache, which owns no manifest: the
            refresh then targets the resolved package directory, because that is
            the record whose entries (``cache/<layer>/...``) the write changes.
        keep_csv: Whether original CSVs belong to the delivery (PUB-07).
        codebooks_required: Whether the surrounding flow promised per-file
            codebooks, which makes an absent ``codebooks/`` block instead of warn.

    Returns:
        The path rewritten, or ``None`` when no manifest owns that directory.
    """
    target = written_to if written_to is not None else _package_output_dir(cfg)
    return write_manifest(
        cfg,
        target,
        keep_csv=keep_csv,
        codebooks_required=codebooks_required,
        only_if_present=True,
    )
