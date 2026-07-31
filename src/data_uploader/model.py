"""
Data model for dataset publishing.

Reads a TOML configuration file and represents it as a typed `DatasetConfig`
dataclass. This module is purely about structure and validation of the
configuration itself — no Hugging Face logic here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileEntry:
    """A single file or directory to be uploaded to a HF repo.

    Attributes:
        local:     Local filesystem path (absolute, or relative to the TOML file).
        remote:    Destination path inside the HF repository.
        recursive: If True and local is a directory, upload it recursively.
    """

    local: Path
    remote: str
    recursive: bool = False
    upload_as_csv: bool = False

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

        description:       One-liner shown on the HF repo page.
        license:           SPDX identifier or ``"restricted"``.
        confidential:      Flag for sensitive / legally protected data.
        source:            Origin institution or organisation.
        tags:              List of tags for discoverability.

        files:             List of file entries to upload.
        readme, codebook, study_design, recipe:
                           Optional paths to data-sharing documentation files
                           that will be uploaded alongside the data.

        min_files:         Minimum number of file entries expected.
        min_total_size_mb: Minimum total data size in MB.
        column_checks:     List of :class:`ColumnCheck` entries.
    """

    # -- identity ----------------------------------------------------------
    name: str
    repo_id: str
    repo_type: str = "dataset"
    private: bool = True

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

    # ------------------------------------------------------------------
    #  Factory / loading
    # ------------------------------------------------------------------

    @classmethod
    def from_toml(cls, path: str | Path) -> DatasetConfig:
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

        Returns:
            A fully populated :class:`DatasetConfig` instance.
        """
        try:
            import tomli as _tomli
        except ImportError:  # Python ≥ 3.11
            import tomllib as _tomli

        path = Path(path)
        base_dir = path.parent

        with open(path, "rb") as fh:
            data = _tomli.load(fh)

        ds = data["dataset"]

        # -- files ---------------------------------------------------------
        files: list[FileEntry] = []
        for entry in data.get("file", []):
            files.append(
                FileEntry(
                    local=Path(entry["local"]),
                    remote=entry["remote"],
                    recursive=entry.get("recursive", False),
                    upload_as_csv=entry.get("upload_as_csv", False),
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
        valid_checks = {
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
        for entry in data.get("quality", []):
            check_name = entry.get("check", "")
            if check_name not in valid_checks:
                print(f"  ⚠  Unknown quality check: '{check_name}' — ignoring.")
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

        # repo_id format
        if not re.match(r"^[\w\-]+/[\w\-]+$", self.repo_id):
            errors.append(f"Invalid repo_id: '{self.repo_id}'. Must be 'user/repo'.")

        # file entries
        if not self.files:
            errors.append("No [[file]] entries found in configuration.")

        base = self._base_dir if self._base_dir else Path.cwd()
        for f in self.files:
            resolved = f.resolve(base)
            if not resolved.exists():
                errors.append(f"Local path not found: {resolved}")

        # optional docs
        for field_name, doc_path in (
            ("readme", self.readme),
            ("codebook", self.codebook),
            ("study_design", self.study_design),
            ("recipe", self.recipe),
        ):
            if doc_path and not Path(doc_path).exists():
                errors.append(f"Declared {field_name} not found: {doc_path}")

        return errors
