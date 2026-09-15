"""
Data model for dataset publishing.

Reads a TOML configuration file and represents it as a typed `DatasetConfig`
dataclass. This module is purely about structure and validation of the
configuration itself — no Hugging Face logic here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from . import config
from ._mirror import _validate_case_fold_collisions

QUALITY_CHECK_NAMES: frozenset[str] = frozenset(
    {
        "duplicates",
        "empty_rows",
        "empty_columns",
        "null_profiling",
        "format_consistency",
        "corrupt_records",
        "value_range",
        "cross_file_types",
        "encoding_validation",
    }
)

_PLACEHOLDERS: frozenset[str] = frozenset(
    {"your_user", "your_org", "your_organization", "your_username", "your-username"}
)


def resolve_doc_path(value: str | None, base: Path) -> Path | None:
    """Resolve an optional documentation path against the config directory.

    ``[dataset] readme`` / ``study_design`` / ``recipe`` (and ``codebook``)
    are optional file paths read by :func:`sofer.prepare.prepare` and
    embedded into the published dataset card. They resolve against *base*
    (the TOML's directory, ``cfg._base_dir``) — never the process working
    directory — so a TOML declaring ``readme = "docs/readme.md"`` is read
    from next to the TOML regardless of where the CLI/MCP process runs.
    Absolute values are returned as-is.

    Args:
        value: The raw declared path, or ``None``/empty when not declared.
        base: Anchor directory for relative values (the config directory).

    Returns:
        The resolved path, or ``None`` when *value* is empty.
    """
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else base / path


class InferenceStatus(str, Enum):
    """Frozen vocabulary describing how a value was inferred.

    A semantic detector reports one of three states:

    - ``confirmed``: the confidence is at or above the confirm threshold.
    - ``inferred``: the confidence is below confirm but at or above the minimum.
    - ``unknown``: no detector produced a result (or confidence is too low).

    Lives in ``model.py`` alongside :data:`QUALITY_CHECK_NAMES` so that the
    semantic, metadata, and render modules can consume the same vocabulary
    without importing one another. Subclassing ``str`` keeps members directly
    serializable (e.g. into ``metadata.yaml``).
    """

    CONFIRMED = "confirmed"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


@dataclass
class FileEntry:
    """A single file or directory to be uploaded to a HF repo.

    Attributes:
        local:              Local filesystem path (absolute, or relative to the TOML file).
        remote:             Destination path inside the HF repository.
        recursive:          If True and local is a directory, upload it recursively.
        convert_to_parquet: When True (default), convertible files are staged as
            normalized Parquet.  When False, the original file is staged as-is.
        upload_as_csv:      Deprecated alias for ``convert_to_parquet`` — only
            honoured for ``.csv`` remotes.  Prefer ``convert_to_parquet``.
        include_in_schema:  Whether this file contributes to the schema report.
    """

    local: Path
    remote: str
    recursive: bool = False
    convert_to_parquet: bool = True
    upload_as_csv: bool = False
    include_in_schema: bool = True

    def __post_init__(self) -> None:
        """Honour deprecated ``upload_as_csv`` alias for direct construction.

        ``DatasetConfig.from_toml`` already implements precedence
        (explicit ``convert_to_parquet`` wins, csv-only deprecation warning).
        This hook keeps ad-hoc ``FileEntry(..., upload_as_csv=True)`` in tests
        and callers consistent without requiring TOML parsing.
        """
        if self.upload_as_csv and self.convert_to_parquet:
            if self.remote.lower().endswith(".csv"):
                # csv-only alias: upload_as_csv=True → convert_to_parquet=False
                # (no warning here — from_toml already warns for TOML path)
                object.__setattr__(self, "convert_to_parquet", False)
            else:
                # non-csv ignored — keep convert_to_parquet=True
                pass

    def resolve(self, base_dir: Path) -> Path:
        """Return the absolute local path.

        If ``self.local`` is already absolute, return it as-is.
        Otherwise, resolve it relative to ``base_dir`` (the TOML file's directory).
        """
        if self.local.is_absolute():
            return self.local
        return (base_dir / self.local).resolve()


@dataclass
class QualityCheck:
    """A single quality check configuration.

    Attributes:
        check:         Check name identifier (e.g. ``"duplicates"``).
        severity:      ``"warn"`` or ``"fail"``. Overrides default.
        columns:       Column subset this check applies to (``None`` = all).
        max_null_pct:  Threshold for ``null_profiling`` (0.0-100.0).
        min:           Minimum acceptable value for ``value_range``.
        max:           Maximum acceptable value for ``value_range``.
        min_unique:    Minimum distinct values for ``duplicates``.
        ignore_values: Values to treat as non-missing during type inference.
    """

    check: str
    severity: str = "warn"
    columns: list[str] | None = None
    max_null_pct: float | None = None
    min: float | None = None
    max: float | None = None
    min_unique: int | None = None
    ignore_values: list[str] | None = None


@dataclass
class QualityConfig:
    """Configuration for all quality checks on a dataset.

    Attributes:
        checks:           Per-check overrides (empty = use all built-in defaults).
        default_severity: Fallback severity when a check has no explicit severity.
        max_sample:       Max rows to read per file for checks that sample.
    """

    checks: list[QualityCheck] = field(default_factory=list)
    default_severity: str = "warn"
    max_sample: int = 100_000


@dataclass
class QualityResult:
    """A single quality check finding.

    Attributes:
        check:    Check name identifier (e.g. ``"duplicates"``).
        severity: ``"warn"`` or ``"fail"``.
        message:  Human-readable description of the finding.
        partial:  ``True`` when the finding is based on a sample (not the full file).
    """

    check: str
    severity: str
    message: str
    partial: bool = False


@dataclass
class ColumnCheck:
    """Describes an expected set of columns in a CSV file.

    Attributes:
        filename:  CSV file name (matched against ``FileEntry.remote``).
        expected:  List of column names that must be present.
    """

    filename: str
    expected: list[str]


@dataclass
class DatasetConfig:
    """Complete configuration for publishing one dataset to Hugging Face Hub.

    Loaded from a TOML file via :meth:`from_toml`.

    Attributes:
        name:              Short human-readable name.
        repo_id:           HF repository identifier (``user/repo``).
        repo_type:         ``"dataset"`` (default) or ``"model"``.
        private:           Whether the HF repo is private.
        skip_cross_file_schema:
                           When ``True``, skip schema consistency checks across
                           files that share the same column names.
        build_dir:         Default output directory for ``prepare`` /
                           ``publish`` artifacts, relative to the config
                           directory (default ``"build"``). ``--output``
                           overrides it per run without touching the TOML.

        description:       One-liner shown on the HF repo page.
        license:           SPDX identifier or ``"restricted"``.
        confidential:      Flag for sensitive / legally protected data.
        source:            Origin institution or organisation.
        tags:              List of tags for discoverability.

        language:          ISO 639-1/639-3 language code(s), e.g. ``["en"]``.
        pretty_name:       Human-readable display name for the dataset card.
        task_categories:   HF task category labels, e.g.
                           ``["tabular-classification"]``.
        size_categories:   Comma-separated size category string or single value
                           from the canonical HF enumeration (``"1K<n<10K"``, etc.).
        citation:          BibTeX or plain-text citation string.
        collection_method: How the data was collected (``"survey"``,
                           ``"admin"``, ``"sensor"``, etc.).

        csv_delimiter:     Delimiter character used in CSV files
                           (default ``";"``).
        csv_encoding:      File encoding for CSV files
                           (default ``"utf-8-sig"``).
        declared_meta_keys:
                           The ``[meta]`` keys the TOML actually declared.  This
                           is the presence signal used by ``_converters`` to tell
                           a dataset that declared ``csv_delimiter = ";"`` apart
                           from one that declared nothing, even though both read
                           back the value ``";"``.  Only :meth:`from_toml`
                           populates it; programmatic constructions keep the
                           empty default and therefore take the sniff fallback.

        annotations_creators:
                           Source of data annotations (``"found"``,
                           ``"crowdsourced"``, ``"expert-generated"``, etc.).
        language_creators:
                           Source of language content (same values as
                           *annotations_creators*).
        language_details:  Additional language metadata strings.
        multilinguality:   ``"monolingual"``, ``"multilingual"``,
                           ``"translation"``, or ``"other"``.
        task_ids:          HF task identifiers (e.g. ``["binary-classification"]``).

        paperswithcode_id: Papers With Code dataset identifier, if any.
        config_names:      List of configuration names for multi-config
                           datasets.

        license_name:      Custom license name when *license* is not an SPDX
                           identifier.
        license_link:      URL or relative path to the full license text.
        license_details:   Additional license notes or free-text terms.

        funded_by:         Organisation or grant that funded the dataset.
        shared_by:         Person or organisation that shared the dataset.
        paper_url:         URL to an associated academic paper.
        demo_url:          URL to an interactive demo or explorer.
        dataset_card_authors:
                           Author(s) of the HF dataset card (comma-separated
                           or free-text).

        files:             List of file entries to upload.
        readme, codebook, study_design, recipe:
                           Optional paths to data-sharing documentation files
                           that will be uploaded alongside the data.

        quality:           Quality check configuration (:class:`QualityConfig`).

        min_files:         Minimum number of file entries expected.
        min_total_size_mb: Minimum total data size in MB.
        column_checks:     List of :class:`ColumnCheck` entries.
    """

    # -- identity ----------------------------------------------------------
    name: str
    repo_id: str
    repo_type: str = "dataset"
    private: bool = True
    skip_cross_file_schema: bool = False
    build_dir: str = "build"

    # -- metadata ----------------------------------------------------------
    description: str = ""
    license: str = ""
    confidential: bool = False
    source: str = ""
    tags: list[str] = field(default_factory=list)

    # -- files -------------------------------------------------------------
    files: list[FileEntry] = field(default_factory=list)

    # -- data-sharing documentation (optional) -----------------------------
    readme: str | None = None
    codebook: str | None = None
    study_design: str | None = None
    recipe: str | None = None

    # -- quality checks ----------------------------------------------------
    quality: QualityConfig = field(default_factory=QualityConfig)

    # -- validation thresholds ---------------------------------------------
    min_files: int = 1
    min_total_size_mb: float = 0.0
    column_checks: list[ColumnCheck] = field(default_factory=list)

    # -- HF Dataset Card metadata (optional) -------------------------------
    language: list[str] = field(default_factory=list)
    pretty_name: str = ""
    task_categories: list[str] = field(default_factory=list)
    size_categories: str = ""
    citation: str = ""
    collection_method: str = ""
    csv_delimiter: str = ";"
    csv_encoding: str = "utf-8-sig"
    # Presence signal (issue #181 / PC-U01): the [meta] keys declared in the TOML.
    # Declaring `csv_delimiter = ";"` is then distinguishable from declaring
    # nothing while both keep the value ";".  Kept separate from the value so the
    # 244 existing `DatasetConfig(...)` sites and the six sibling readers stay
    # bit-identical (design D1).
    declared_meta_keys: frozenset[str] = field(default_factory=frozenset)
    annotations_creators: list[str] = field(default_factory=list)
    language_creators: list[str] = field(default_factory=list)
    language_details: list[str] = field(default_factory=list)
    multilinguality: str = ""
    task_ids: list[str] = field(default_factory=list)
    paperswithcode_id: str = ""
    config_names: list[str] = field(default_factory=list)
    license_name: str = ""
    license_link: str = ""
    license_details: str = ""
    funded_by: str = ""
    shared_by: str = ""
    paper_url: str = ""
    demo_url: str = ""
    dataset_card_authors: str = ""

    # -- internal ----------------------------------------------------------
    _base_dir: Path = Path()  # directory of the TOML file (set by from_toml)
    _config_path: Path = field(
        default=Path(), compare=False, repr=False
    )  # resolved TOML path (set by from_toml)

    # ------------------------------------------------------------------
    #  Factory / loading
    # ------------------------------------------------------------------

    @classmethod
    def from_toml(cls, path: str | Path, discovery_root: Path | None = None) -> DatasetConfig:
        """Parse a TOML file and return a :class:`DatasetConfig`.

        The TOML format is::

            [dataset]
            name = "my-dataset"
            repo_id = "user/my-dataset"
            repo_type = "dataset"
            private = true

            [meta]
            description = "..."
            license = "MIT"
            confidential = false
            source = "Some organisation"
            tags = ["tag1", "tag2"]
            readme = "README.md"

            [[file]]
            local = "data/some.csv"
            remote = "some.csv"

            [[file]]
            local = "data/dir"
            remote = "subdir/"
            recursive = true

            [[check]]
            min_files = 2
            min_total_size_mb = 50.0

            [[check]]
            columns = "some.csv"
            expected = ["col_a", "col_b"]

        Args:
            path: Path to the TOML configuration file.
            discovery_root: Optional upper bound for ``[tool.sofer]``
                discovery (TC-05): the walk-up never passes this directory,
                so overrides declared above it do not apply. ``None`` keeps
                the unbounded CLI behavior.

        Returns:
            A fully populated :class:`DatasetConfig` instance.
        """
        try:
            import tomli as _tomli
        except ImportError:  # Python ≥ 3.11
            import tomllib as _tomli

        path = Path(path)
        base_dir = path.parent

        # Phase-1 tool-config resolution: re-anchor [tool.sofer] discovery on
        # the dataset TOML's directory so every subsequent read of a module
        # constant (config.X) reflects the dataset-tree overrides for this
        # invocation (TC-04/TC-05). Harmless if called repeatedly — resolution
        # is a pure function of (anchor, filesystem). The optional
        # ``discovery_root`` bounds the walk-up (TC-05): discovery never
        # passes it, so overrides declared above the bound do not apply. The
        # ``stop_at`` keyword is only passed when a bound is given — the
        # unbounded CLI path keeps the exact ``reload(base_dir)`` call shape
        # (TC-04 spies on ``config.reload`` and accept no keywords).
        if discovery_root is not None:
            config.reload(base_dir, stop_at=discovery_root)
        else:
            config.reload(base_dir)

        with open(path, "rb") as fh:
            data = _tomli.load(fh)

        ds = data["dataset"]

        # -- files ---------------------------------------------------------
        files: list[FileEntry] = []
        for entry in data.get("file", []):
            remote_val: str = entry["remote"]
            upload_as_csv_val: bool = bool(entry.get("upload_as_csv", False))
            # Precedence: explicit convert_to_parquet wins; otherwise derive
            # from upload_as_csv for csv-only with deprecation warning.
            if "convert_to_parquet" in entry:
                convert_val: bool = bool(entry["convert_to_parquet"])
            elif upload_as_csv_val:
                if remote_val.lower().endswith(".csv"):
                    print(
                        "  [!] 'upload_as_csv' is deprecated — "
                        "use 'convert_to_parquet = false' instead."
                    )
                    convert_val = False
                else:
                    print(
                        f"  [!] 'upload_as_csv=true' ignored for non-csv remote '{remote_val}' — "
                        f"use 'convert_to_parquet = false' to keep the original."
                    )
                    convert_val = True
            else:
                convert_val = True
            files.append(
                FileEntry(
                    local=Path(entry["local"]),
                    remote=remote_val,
                    recursive=entry.get("recursive", False),
                    convert_to_parquet=convert_val,
                    upload_as_csv=upload_as_csv_val,
                    include_in_schema=entry.get("include_in_schema", True),
                )
            )

        # -- column checks -------------------------------------------------
        column_checks: list[ColumnCheck] = []
        for entry in data.get("check", []):
            if "columns" in entry:
                column_checks.append(
                    ColumnCheck(
                        filename=entry["columns"],
                        expected=entry.get("expected", []),
                    )
                )

        # -- quality checks ------------------------------------------------
        quality_checks: list[QualityCheck] = []
        valid_checks = set(QUALITY_CHECK_NAMES)
        for entry in data.get("quality", []):
            check_name = entry.get("check", "")
            if check_name not in valid_checks:
                print(f"  [!] Unknown quality check: '{check_name}' — ignoring.")
                continue
            quality_checks.append(
                QualityCheck(
                    check=check_name,
                    severity=entry.get("severity", "warn"),
                    columns=entry.get("columns"),
                    max_null_pct=entry.get("max_null_pct"),
                    min=entry.get("min"),
                    max=entry.get("max"),
                    min_unique=entry.get("min_unique"),
                    ignore_values=entry.get("ignore_values"),
                )
            )
        quality_config = QualityConfig(checks=quality_checks)

        # -- thresholds ----------------------------------------------------
        min_files = 1
        min_total_size_mb = 0.0
        for entry in data.get("check", []):
            if "min_files" in entry:
                min_files = entry["min_files"]
            if "min_total_size_mb" in entry:
                min_total_size_mb = entry["min_total_size_mb"]

        meta = data.get("meta", {})

        return cls(
            name=ds["name"],
            repo_id=ds["repo_id"],
            repo_type=ds.get("repo_type", "dataset"),
            private=ds.get("private", True),
            skip_cross_file_schema=ds.get("skip_cross_file_schema", False),
            build_dir=ds.get("build_dir", "build"),
            description=meta.get("description", ""),
            license=meta.get("license", ""),
            confidential=meta.get("confidential", False),
            source=meta.get("source", ""),
            tags=meta.get("tags", []),
            files=files,
            readme=meta.get("readme"),
            codebook=meta.get("codebook"),
            study_design=meta.get("study_design"),
            recipe=meta.get("recipe"),
            min_files=min_files,
            min_total_size_mb=min_total_size_mb,
            column_checks=column_checks,
            quality=quality_config,
            language=meta.get("language", []),
            pretty_name=meta.get("pretty_name", ""),
            task_categories=meta.get("task_categories", []),
            size_categories=meta.get("size_categories", ""),
            citation=meta.get("citation", ""),
            collection_method=meta.get("collection_method", ""),
            csv_delimiter=meta.get("csv_delimiter", ";"),
            csv_encoding=meta.get("csv_encoding", "utf-8-sig"),
            declared_meta_keys=frozenset(meta.keys()),
            annotations_creators=meta.get("annotations_creators", []),
            language_creators=meta.get("language_creators", []),
            language_details=meta.get("language_details", []),
            multilinguality=meta.get("multilinguality", ""),
            task_ids=meta.get("task_ids", []),
            paperswithcode_id=meta.get("paperswithcode_id", ""),
            config_names=meta.get("config_names", []),
            license_name=meta.get("license_name", ""),
            license_link=meta.get("license_link", ""),
            license_details=meta.get("license_details", ""),
            funded_by=meta.get("funded_by", ""),
            shared_by=meta.get("shared_by", ""),
            paper_url=meta.get("paper_url", ""),
            demo_url=meta.get("demo_url", ""),
            dataset_card_authors=meta.get("dataset_card_authors", ""),
            _base_dir=base_dir,
            _config_path=path.resolve(),
        )

    # ------------------------------------------------------------------
    #  Validation
    # ------------------------------------------------------------------

    def validate(self) -> list[str]:
        """Validate the configuration itself (before touching any files).

        Checks:
            - ``repo_id`` matches the ``user/repo`` format.
            - At least one file entry exists.
            - Every referenced local path exists on disk.
            - Optional documentation files exist if declared.

        Returns:
            A list of error messages (empty = valid).
        """
        errors: list[str] = []

        # TC-13: configuration type validation -- a malformed TOML value
        # (int delimiter, list encoding, str min_files, ...) must surface a
        # stable diagnostic here, before any reader or comparison executes
        # (GitHub #118). Runs first so invalid values never reach the
        # file/path resolution below as an arbitrary Python type.
        errors.extend(_validate_config_types(self))

        # placeholder detection
        repo_user = self.repo_id.split("/")[0] if "/" in self.repo_id else ""
        for placeholder in _PLACEHOLDERS:
            if repo_user.lower() == placeholder:
                errors.append(
                    f"repo_id contains placeholder '{repo_user}'. "
                    f"Replace it with your Hugging Face username."
                )
                break

        # repo_id format — `\Z` (not `$`) so a trailing newline is rejected,
        # matching the exact no-trailing-newline contract used for `user` in
        # validate_identity (INIT-05).
        if not re.match(r"^[\w\-]+/[\w\-]+\Z", self.repo_id):
            errors.append(f"Invalid repo_id: '{self.repo_id}'. Must be 'user/repo'.")

        # file entries
        if not self.files:
            errors.append("No [[file]] entries found in configuration.")

        base = self._base_dir if self._base_dir else Path.cwd()
        for f in self.files:
            resolved = f.resolve(base)
            if not resolved.exists():
                errors.append(f"Local path not found: {resolved}")

        # RC-R16: refuse case-fold collisions on staged-Parquet remotes before
        # any staging write.
        errors.extend(_validate_case_fold_collisions(self))

        # optional docs — resolved against the config's directory (PRP-03),
        # never the process cwd, so a relative declaration like
        # ``readme = "docs/readme.md"`` is found next to the TOML.
        for field_name, doc_path in (
            ("readme", self.readme),
            ("codebook", self.codebook),
            ("study_design", self.study_design),
            ("recipe", self.recipe),
        ):
            doc_resolved = resolve_doc_path(doc_path, base)
            if doc_resolved is not None and not doc_resolved.exists():
                errors.append(f"Declared {field_name} not found: {doc_resolved}")

        return errors


def _validate_config_types(cfg: DatasetConfig) -> list[str]:
    """Validate the *types* of configuration values, independent of files.

    TOML is untyped, so a dataset TOML may declare ``csv_delimiter = 5`` or
    ``min_files = "two"``; those values would otherwise reach comparisons and
    readers as arbitrary Python types (a list compared with ``== ","``, a str
    in ``len(files) < min_files``). Diagnostics are stable strings naming the
    offending key, the expected type, and the received value (TC-13, #118).

    Args:
        cfg: The parsed configuration to inspect.

    Returns:
        A list of stable error messages (empty = all types valid).
    """
    errors: list[str] = []

    def _add(key: str, expected: str, value: object) -> None:
        errors.append(f"{key} must be {expected}, got {type(value).__name__}: {value!r}")

    def _is_number(value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    # -- scalar meta fields ------------------------------------------------
    if not isinstance(cfg.csv_delimiter, str) or len(cfg.csv_delimiter) != 1:
        _add("csv_delimiter", "a single-character string", cfg.csv_delimiter)
    if not isinstance(cfg.csv_encoding, str) or not cfg.csv_encoding:
        _add("csv_encoding", "a non-empty string", cfg.csv_encoding)
    if not isinstance(cfg.repo_type, str) or not cfg.repo_type:
        _add("repo_type", "a non-empty string", cfg.repo_type)

    for field_name in ("confidential", "private", "skip_cross_file_schema"):
        value = getattr(cfg, field_name)
        if not isinstance(value, bool):
            _add(field_name, "a boolean", value)

    # -- thresholds --------------------------------------------------------
    if not isinstance(cfg.min_files, int) or isinstance(cfg.min_files, bool):
        _add("min_files", "a non-negative integer (bool is not an int here)", cfg.min_files)
    elif cfg.min_files < 0:
        _add("min_files", "a non-negative integer", cfg.min_files)

    if not _is_number(cfg.min_total_size_mb) or cfg.min_total_size_mb < 0:
        _add("min_total_size_mb", "a non-negative number", cfg.min_total_size_mb)

    # -- quality checks: numeric fields must be numbers when present -------
    for check in cfg.quality.checks:
        for field_name in ("max_null_pct", "min", "max", "min_unique"):
            value = getattr(check, field_name)
            if value is not None and not _is_number(value):
                _add(f"quality check '{check.check}' {field_name}", "a number", value)

    # -- column checks: expected must be a list of strings -----------------
    for col_check in cfg.column_checks:
        if not isinstance(col_check.expected, list) or not all(
            isinstance(item, str) for item in col_check.expected
        ):
            _add(
                f"column check '{col_check.filename}' expected",
                "a list of strings",
                col_check.expected,
            )

    return errors
