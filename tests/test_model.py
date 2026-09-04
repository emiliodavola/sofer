"""Tests for sofer.model — TOML loading, config representation, validation."""

from pathlib import Path

import sofer.config as config
from sofer.model import DatasetConfig, FileEntry, InferenceStatus

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

    def test_build_dir_defaults_to_build(self, tmp_path):
        """A TOML without ``[dataset] build_dir`` defaults to ``"build"``."""
        p = tmp_path / "minimal.toml"
        p.write_text(SAMPLE_TOML_MINIMAL)
        cfg = DatasetConfig.from_toml(p)
        assert cfg.build_dir == "build"

    def test_build_dir_custom_from_toml(self, tmp_path):
        """``[dataset] build_dir`` is parsed into ``DatasetConfig.build_dir``."""
        p = tmp_path / "custom.toml"
        p.write_text(
            '[dataset]\nname = "custom"\nrepo_id = "user/custom"\n'
            'build_dir = "staging"\n\n'
            '[[file]]\nlocal = "data.csv"\nremote = "data.csv"\n'
        )
        cfg = DatasetConfig.from_toml(p)
        assert cfg.build_dir == "staging"

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


# ── TC-05: from_toml discovery_root bound ────────────────────────────────────


class TestFromTomlDiscoveryRoot:
    """DatasetConfig.from_toml honors the optional discovery_root bound."""

    MINIMAL_TOML = '[dataset]\nname = "x"\nrepo_id = "u/x"\n'

    def test_discovery_root_applies_at_or_below(self, restore_tool_config, pytree):
        """Values from a pyproject at/below discovery_root apply; above-root
        overrides do not (TC-05 scenario 2)."""
        pytree("[tool.sofer]\nschema_sample_size = 999\n", at="outer")
        discovery_root = pytree(None, at="outer/proj")
        inner = pytree("[tool.sofer]\nschema_sample_size = 250\n", at="outer/proj/data")
        toml_path = inner / "dataset.toml"
        toml_path.write_text(self.MINIMAL_TOML, encoding="utf-8")

        cfg = DatasetConfig.from_toml(toml_path, discovery_root=discovery_root)
        assert cfg.name == "x"
        assert config.SCHEMA_SAMPLE_SIZE == 250

    def test_discovery_root_blocks_above_root_override(self, restore_tool_config, pytree):
        """Without a pyproject at/below discovery_root, an above-root
        override must NOT apply — built-in defaults do."""
        pytree("[tool.sofer]\nschema_sample_size = 999\n", at="outer")
        discovery_root = pytree(None, at="outer/proj")
        toml_path = discovery_root / "dataset.toml"
        toml_path.write_text(self.MINIMAL_TOML, encoding="utf-8")

        cfg = DatasetConfig.from_toml(toml_path, discovery_root=discovery_root)
        assert cfg.name == "x"
        assert config.SCHEMA_SAMPLE_SIZE == config._DEFAULTS["schema_sample_size"]

    def test_omitted_discovery_root_stays_unbounded(self, restore_tool_config, pytree):
        """CLI compatibility: without a bound the walk-up applies above-root
        pyproject overrides (TC-05 scenario 1)."""
        pytree("[tool.sofer]\nschema_sample_size = 250\n", at="outer")
        data_dir = pytree(None, at="outer/proj/data")
        toml_path = data_dir / "dataset.toml"
        toml_path.write_text(self.MINIMAL_TOML, encoding="utf-8")

        cfg = DatasetConfig.from_toml(toml_path)
        assert cfg.name == "x"
        assert config.SCHEMA_SAMPLE_SIZE == 250


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

    # ── RC-R16 case-fold collisions (S1-S4) ─────────────────────────────

    def test_case_collision_error_present(self, tmp_path):
        """Case-differing .csv remotes produce a collision error in validate()."""
        (tmp_path / "a.csv").touch()
        (tmp_path / "b.csv").touch()
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[
                FileEntry(local=tmp_path / "a.csv", remote="Data/Prov/Train.CSV"),
                FileEntry(local=tmp_path / "b.csv", remote="data/prov/train.csv"),
            ],
            _base_dir=tmp_path,
        )
        errors = cfg.validate()
        assert any("Case-fold collision" in e for e in errors)

    def test_case_collision_error_names_both_remotes(self, tmp_path):
        """The collision error names both colliding remotes (S1)."""
        (tmp_path / "a.csv").touch()
        (tmp_path / "b.csv").touch()
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[
                FileEntry(local=tmp_path / "a.csv", remote="Data/a.csv"),
                FileEntry(local=tmp_path / "b.csv", remote="data/a.csv"),
            ],
            _base_dir=tmp_path,
        )
        errors = cfg.validate()
        collision = next(e for e in errors if "Case-fold collision" in e)
        assert "Data/a.csv" in collision
        assert "data/a.csv" in collision

    def test_exact_duplicate_no_collision_error(self, tmp_path):
        """Verbatim-identical remotes do not raise an RC-R16 error (S2)."""
        (tmp_path / "a.csv").touch()
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[
                FileEntry(local=tmp_path / "a.csv", remote="data/train.csv"),
                FileEntry(local=tmp_path / "a.csv", remote="data/train.csv"),
            ],
            _base_dir=tmp_path,
        )
        errors = cfg.validate()
        assert not any("Case-fold collision" in e for e in errors)

    def test_unicode_casefold_distinct_no_error(self, tmp_path):
        """straße vs strasse stay distinct under lower() — no error (S3)."""
        (tmp_path / "a.csv").touch()
        (tmp_path / "b.csv").touch()
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[
                FileEntry(local=tmp_path / "a.csv", remote="straße.csv"),
                FileEntry(local=tmp_path / "b.csv", remote="strasse.csv"),
            ],
            _base_dir=tmp_path,
        )
        errors = cfg.validate()
        assert not any("Case-fold collision" in e for e in errors)

    def test_include_in_schema_false_pair_collides(self, tmp_path):
        """include_in_schema=false .csv pair still collides (D2 overrides S4)."""
        (tmp_path / "a.csv").touch()
        (tmp_path / "b.csv").touch()
        cfg = DatasetConfig(
            name="test",
            repo_id="user/test",
            files=[
                FileEntry(local=tmp_path / "a.csv", remote="Data/a.csv", include_in_schema=False),
                FileEntry(local=tmp_path / "b.csv", remote="data/a.csv", include_in_schema=False),
            ],
            _base_dir=tmp_path,
        )
        errors = cfg.validate()
        assert any("Case-fold collision" in e for e in errors)


# ═══════════════════════════════════════════════════════════════════════════════
#  FileEntry.include_in_schema — schema opt-out feature
# ═══════════════════════════════════════════════════════════════════════════════


class TestFileEntryIncludeInSchema:
    """FileEntry.include_in_schema default, TOML parse, and from_toml behaviour."""

    def test_default_value_is_true(self):
        """include_in_schema should default to True when not specified."""
        entry = FileEntry(local=Path("data.csv"), remote="data.csv")
        assert entry.include_in_schema is True

    def test_explicit_false_in_dataclass(self):
        """include_in_schema=False should be supported at construction."""
        entry = FileEntry(local=Path("labels.csv"), remote="labels.csv", include_in_schema=False)
        assert entry.include_in_schema is False

    def test_explicit_true_in_dataclass(self):
        """include_in_schema=True should be supported at construction."""
        entry = FileEntry(local=Path("data.csv"), remote="data.csv", include_in_schema=True)
        assert entry.include_in_schema is True

    def test_toml_field_absent_defaults_true(self, tmp_path):
        """When include_in_schema is absent from TOML, default to True."""
        toml = (
            SAMPLE_TOML_MINIMAL
            + """
[[file]]
local = "labels.csv"
remote = "labels.csv"
"""
        )
        p = tmp_path / "t.toml"
        p.write_text(toml)
        (tmp_path / "data.csv").touch()
        (tmp_path / "labels.csv").touch()
        cfg = DatasetConfig.from_toml(p)
        # First file has no include_in_schema → True
        assert cfg.files[0].include_in_schema is True
        # Second file also defaults True
        assert cfg.files[1].include_in_schema is True

    def test_toml_explicit_false(self, tmp_path):
        """include_in_schema = false in TOML should parse as False."""
        toml = (
            SAMPLE_TOML_MINIMAL
            + """
[[file]]
local = "labels.csv"
remote = "labels.csv"
include_in_schema = false
"""
        )
        p = tmp_path / "t.toml"
        p.write_text(toml)
        (tmp_path / "data.csv").touch()
        (tmp_path / "labels.csv").touch()
        cfg = DatasetConfig.from_toml(p)
        # First file defaults True
        assert cfg.files[0].include_in_schema is True
        # Second file explicitly False
        assert cfg.files[1].include_in_schema is False

    def test_toml_explicit_true(self, tmp_path):
        """include_in_schema = true in TOML should parse as True."""
        toml = (
            SAMPLE_TOML_MINIMAL
            + """
[[file]]
local = "labels.csv"
remote = "labels.csv"
include_in_schema = true
"""
        )
        p = tmp_path / "t.toml"
        p.write_text(toml)
        (tmp_path / "data.csv").touch()
        (tmp_path / "labels.csv").touch()
        cfg = DatasetConfig.from_toml(p)
        assert cfg.files[1].include_in_schema is True


# ═══════════════════════════════════════════════════════════════════════════════
#  InferenceStatus — metadata-core status vocabulary (MTA-04)
# ═══════════════════════════════════════════════════════════════════════════════


class TestInferenceStatus:
    """InferenceStatus must be a frozen 3-value vocabulary."""

    def test_exactly_three_values(self):
        """The vocabulary is exactly confirmed, inferred, unknown."""
        values = {member.value for member in InferenceStatus}
        assert values == {"confirmed", "inferred", "unknown"}

    def test_members_are_string_comparable(self):
        """Members behave as strings, enabling plain serialization."""
        assert InferenceStatus.CONFIRMED == "confirmed"
        assert InferenceStatus.INFERRED == "inferred"
        assert InferenceStatus.UNKNOWN == "unknown"

    def test_member_names_match_values(self):
        """Each member name maps to its lowercase value."""
        assert {m.name for m in InferenceStatus} == {
            "CONFIRMED",
            "INFERRED",
            "UNKNOWN",
        }
