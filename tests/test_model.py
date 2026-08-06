"""Tests for sofer.model — TOML loading, config representation, validation."""

from pathlib import Path

from sofer.model import DatasetConfig, FileEntry

# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_TOML_FULL = """\
[dataset]
name = "my-dataset"
repo_id = "testuser/my-dataset"
private = true

[meta]
description = "Test dataset for unit tests"
license = "restricted"
confidential = true
source = "Some Organisation"
tags = ["tag1", "tag2"]
readme = "README.md"
codebook = "codebook.md"
study_design = "design.md"
recipe = "recipe.R"

[[file]]
local = "data.csv"
remote = "data.csv"

[[file]]
local = "labels/"
remote = "labels/"
recursive = true

[[check]]
min_files = 2
min_total_size_mb = 100.0

[[check]]
columns = "data.csv"
expected = ["id", "name", "value"]
"""


SAMPLE_TOML_MINIMAL = """\
[dataset]
name = "minimal"
repo_id = "user/minimal"

[[file]]
local = "data.csv"
remote = "data.csv"
"""


# ── Loading ───────────────────────────────────────────────────────────────────


class TestFromToml:
    def test_load_full_config(self, tmp_path):
        """A fully specified TOML should populate every field."""
        p = tmp_path / "full.toml"
        p.write_text(SAMPLE_TOML_FULL)
        cfg = DatasetConfig.from_toml(p)

        assert cfg.name == "my-dataset"
        assert cfg.repo_id == "testuser/my-dataset"
        assert cfg.private is True
        assert cfg.repo_type == "dataset"  # default

        assert cfg.description == "Test dataset for unit tests"
        assert cfg.license == "restricted"
        assert cfg.confidential is True
        assert cfg.source == "Some Organisation"
        assert cfg.tags == ["tag1", "tag2"]

        assert cfg.readme == "README.md"
        assert cfg.codebook == "codebook.md"
        assert cfg.study_design == "design.md"
        assert cfg.recipe == "recipe.R"

        assert len(cfg.files) == 2
        assert cfg.files[0].local == Path("data.csv")
        assert cfg.files[0].remote == "data.csv"
        assert cfg.files[0].recursive is False

        assert cfg.files[1].local == Path("labels/")
        assert cfg.files[1].remote == "labels/"
        assert cfg.files[1].recursive is True

        assert cfg.min_files == 2
        assert cfg.min_total_size_mb == 100.0
        assert len(cfg.column_checks) == 1
        assert cfg.column_checks[0].filename == "data.csv"
        assert cfg.column_checks[0].expected == ["id", "name", "value"]

    def test_load_minimal_config(self, tmp_path):
        """A minimal TOML should use sensible defaults."""
        p = tmp_path / "minimal.toml"
        p.write_text(SAMPLE_TOML_MINIMAL)
        cfg = DatasetConfig.from_toml(p)

        assert cfg.name == "minimal"
        assert cfg.repo_id == "user/minimal"
        assert cfg.private is True  # default
        assert cfg.min_files == 1  # default
        assert cfg.min_total_size_mb == 0.0  # default
        assert cfg.column_checks == []
        assert cfg.description == ""

    def test_file_entry_resolve_absolute(self):
        """An absolute local path should be returned as-is."""
        # Cross-platform absolute path: filesystem root + relative path
        # drive is '' on POSIX (→ /) and 'D:' on Windows (→ D:/)
        root = Path(Path.cwd().drive + "/")
        abs_path = root / "absolute" / "path" / "file.csv"
        entry = FileEntry(local=abs_path, remote="file.csv")
        resolved = entry.resolve(Path("."))
        assert resolved == abs_path

    def test_file_entry_resolve_relative(self, tmp_path):
        """A relative local path should be resolved against the base dir."""
        base = tmp_path / "configs"
        entry = FileEntry(local=Path("data.csv"), remote="data.csv")
        resolved = entry.resolve(base)
        assert resolved == (base / "data.csv").resolve()

    def test_repo_type_default(self, tmp_path):
        """repo_type defaults to 'dataset'."""
        p = tmp_path / "t.toml"
        p.write_text(SAMPLE_TOML_MINIMAL)
        cfg = DatasetConfig.from_toml(p)
        assert cfg.repo_type == "dataset"

    def test_repo_type_overridden(self, tmp_path):
        """repo_type can be overridden."""
        toml = SAMPLE_TOML_MINIMAL.replace("[dataset]", '[dataset]\nrepo_type = "model"')
        p = tmp_path / "t.toml"
        p.write_text(toml)
        cfg = DatasetConfig.from_toml(p)
        assert cfg.repo_type == "model"

    # ── New [meta] fields (hf-dataset-compliance) ──────────────────────

    def test_new_meta_defaults(self, tmp_path):
        """New [meta] fields should have sensible defaults when absent."""
        p = tmp_path / "t.toml"
        p.write_text(SAMPLE_TOML_MINIMAL)
        cfg = DatasetConfig.from_toml(p)

        assert cfg.language == []
        assert cfg.pretty_name == ""
        assert cfg.task_categories == []
        assert cfg.size_categories == ""
        assert cfg.citation == ""
        assert cfg.collection_method == ""
        assert cfg.csv_delimiter == ";"
        assert cfg.csv_encoding == "utf-8-sig"

    def test_new_meta_fields_read_from_toml(self, tmp_path):
        """All new [meta] fields should be read from TOML."""
        toml = (
            SAMPLE_TOML_MINIMAL
            + """
[meta]
language = ["es", "ay"]
pretty_name = "My Dataset"
task_categories = ["tabular-classification"]
size_categories = "1K<n<10K"
citation = "@article{...}"
collection_method = "Survey"
csv_delimiter = ","
csv_encoding = "latin-1"
"""
        )
        p = tmp_path / "t.toml"
        p.write_text(toml)
        cfg = DatasetConfig.from_toml(p)

        assert cfg.language == ["es", "ay"]
        assert cfg.pretty_name == "My Dataset"
        assert cfg.task_categories == ["tabular-classification"]
        assert cfg.size_categories == "1K<n<10K"
        assert cfg.citation == "@article{...}"
        assert cfg.collection_method == "Survey"
        assert cfg.csv_delimiter == ","
        assert cfg.csv_encoding == "latin-1"

    def test_new_meta_pretty_name_fallback(self, tmp_path):
        """pretty_name should default to cfg.name when not set."""
        p = tmp_path / "t.toml"
        p.write_text(SAMPLE_TOML_MINIMAL)
        cfg = DatasetConfig.from_toml(p)
        # When not set, pretty_name is empty; fallback to name happens in the card
        assert cfg.pretty_name == ""


# ── Validation ────────────────────────────────────────────────────────────────


class TestValidate:
    def test_valid_repo_id(self, tmp_path):
        """A valid 'user/repo' should pass."""
        p = tmp_path / "t.toml"
        p.write_text(SAMPLE_TOML_MINIMAL)
        cfg = DatasetConfig.from_toml(p)
        # make the file exist
        (tmp_path / "data.csv").touch()
        errors = cfg.validate()
        assert errors == []

    def test_invalid_repo_id_no_slash(self):
        """Missing slash in repo_id should produce an error."""
        cfg = DatasetConfig(name="test", repo_id="justtext")
        errors = cfg.validate()
        assert any("repo_id" in e for e in errors)

    def test_invalid_repo_id_trailing_slash(self):
        """Trailing slash should fail."""
        cfg = DatasetConfig(name="test", repo_id="user/")
        errors = cfg.validate()
        assert any("repo_id" in e for e in errors)

    def test_empty_files_list(self):
        """Zero file entries should fail."""
        cfg = DatasetConfig(name="test", repo_id="user/repo", files=[])
        errors = cfg.validate()
        assert any("No [[file]] entries" in e for e in errors)

    def test_missing_local_file(self, tmp_path):
        """A declared file that doesn't exist on disk should fail."""
        p = tmp_path / "t.toml"
        p.write_text(SAMPLE_TOML_MINIMAL)
        # data.csv does NOT exist in tmp_path
        cfg = DatasetConfig.from_toml(p)
        errors = cfg.validate()
        assert any("not found" in e.lower() for e in errors)

    # ── Placeholder rejection ───────────────────────────────────────────

    def test_rejects_your_user_placeholder(self):
        """repo_id with YOUR_USER placeholder should be rejected."""
        cfg = DatasetConfig(name="test", repo_id="YOUR_USER/dataset")
        errors = cfg.validate()
        assert any("placeholder" in e.lower() for e in errors)

    def test_rejects_your_org_placeholder(self):
        """repo_id with YOUR_ORG placeholder should be rejected."""
        cfg = DatasetConfig(name="test", repo_id="YOUR_ORG/dataset")
        errors = cfg.validate()
        assert any("placeholder" in e.lower() for e in errors)

    def test_rejects_your_username_placeholder_case_insensitive(self):
        """repo_id with 'your-username' (case-insensitive) should be rejected."""
        cfg = DatasetConfig(name="test", repo_id="your-username/dataset")
        errors = cfg.validate()
        assert any("placeholder" in e.lower() for e in errors)

    def test_rejects_your_organization_placeholder(self):
        """repo_id with YOUR_ORGANIZATION placeholder should be rejected."""
        cfg = DatasetConfig(name="test", repo_id="YOUR_ORGANIZATION/dataset")
        errors = cfg.validate()
        assert any("placeholder" in e.lower() for e in errors)

    def test_accepts_valid_user_repo(self):
        """Valid 'alice/my-dataset' should pass placeholder check."""
        cfg = DatasetConfig(name="test", repo_id="alice/my-dataset")
        errors = cfg.validate()
        assert not any("placeholder" in e.lower() for e in errors)

    def test_rejects_placeholder_in_multisegment(self):
        """repo_id with placeholder in multi-segment path should be rejected."""
        cfg = DatasetConfig(name="test", repo_id="your-username/sub/project")
        errors = cfg.validate()
        assert any("placeholder" in e.lower() for e in errors)

    def test_placeholder_error_message_names_placeholder(self, tmp_path):
        """Error message should name the specific placeholder found."""
        cfg = DatasetConfig(name="test", repo_id="YOUR_USER/dataset")
        (tmp_path / "data.csv").touch()
        errors = cfg.validate()
        assert any("YOUR_USER" in e for e in errors)

    def test_all_files_exist(self, tmp_path):
        """When all declared files exist, validation should pass."""
        p = tmp_path / "t.toml"
        p.write_text(SAMPLE_TOML_MINIMAL)
        (tmp_path / "data.csv").touch()
        cfg = DatasetConfig.from_toml(p)
        errors = cfg.validate()
        assert errors == []

    def test_missing_readme(self, tmp_path):
        """A declared readme that doesn't exist should warn."""
        toml = SAMPLE_TOML_MINIMAL + '\n[meta]\nreadme = "missing.md"\n'
        p = tmp_path / "t.toml"
        p.write_text(toml)
        (tmp_path / "data.csv").touch()
        cfg = DatasetConfig.from_toml(p)
        errors = cfg.validate()
        assert any("readme" in e for e in errors)

    def test_recursive_directory(self, tmp_path):
        """A recursive directory entry that exists should pass."""
        toml = SAMPLE_TOML_MINIMAL.replace(
            '[[file]]\nlocal = "data.csv"',
            '[[file]]\nlocal = "mydir"\nrecursive = true',
        )
        p = tmp_path / "t.toml"
        p.write_text(toml)
        (tmp_path / "mydir").mkdir()
        (tmp_path / "mydir" / "file.txt").touch()
        cfg = DatasetConfig.from_toml(p)
        errors = cfg.validate()
        assert errors == []
