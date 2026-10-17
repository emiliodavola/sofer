"""Tests for sofer.checks — data integrity verification."""

import csv
from pathlib import Path

from sofer import config
from sofer.checks import DatasetValidator, meta_placeholder_warnings
from sofer.model import ColumnCheck, DatasetConfig, FileEntry


def _make_csv(path: Path, rows: list[list[str]], delimiter: str = ";") -> Path:
    """Write a small CSV for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerows(rows)
    return path


# ── File existence ────────────────────────────────────────────────────────────


def test_all_files_exist(tmp_path):
    """When all declared files exist, there should be zero errors."""
    (tmp_path / "data.csv").touch()
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / "data.csv", remote="data.csv")],
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert report.passed
    assert len(report.errors) == 0


def test_missing_file_reported(tmp_path):
    """A missing file should produce exactly one error."""
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / "ghost.csv", remote="ghost.csv")],
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert not report.passed
    assert any("ghost.csv" in e for e in report.errors)


def test_missing_directory_reported(tmp_path):
    """A missing recursive directory should produce an error."""
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / "labels", remote="labels/", recursive=True)],
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert not report.passed
    assert any("labels" in e for e in report.errors)


# ── Minimum file count ────────────────────────────────────────────────────────


def test_below_min_files(tmp_path):
    """Declaring fewer files than min_files should fail."""
    (tmp_path / "a.csv").touch()
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / "a.csv", remote="a.csv")],
        min_files=5,
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert not report.passed
    assert any("5" in e for e in report.errors)


def test_at_min_files(tmp_path):
    """Exactly min_files entries should pass."""
    for i in range(3):
        (tmp_path / f"{i}.csv").touch()
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / f"{i}.csv", remote=f"{i}.csv") for i in range(3)],
        min_files=3,
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert report.passed


# ── Total size ────────────────────────────────────────────────────────────────


def test_below_min_size_warns(tmp_path):
    """Below the size threshold should produce a warning (not an error)."""
    (tmp_path / "small.csv").write_text("a,b,c\n1,2,3\n")
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / "small.csv", remote="small.csv")],
        min_total_size_mb=1000.0,  # unreachable
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert report.passed  # warning, not error
    assert len(report.warnings) >= 1
    assert any("size" in w.lower() for w in report.warnings)


def test_size_threshold_zero_bypasses_check(tmp_path):
    """When min_total_size_mb is 0, the size check is skipped."""
    (tmp_path / "tiny.csv").write_text("a\n1\n")
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / "tiny.csv", remote="tiny.csv")],
        min_total_size_mb=0.0,
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert report.passed
    # no warning about size
    assert not any("size" in w.lower() for w in report.warnings)


# ── CSV column checks ─────────────────────────────────────────────────────────


def test_csv_columns_pass(tmp_path):
    """When expected columns are present, the check passes."""
    csv_path = _make_csv(
        tmp_path / "data.csv",
        [
            ["id", "name", "value"],
            ["1", "foo", "10"],
        ],
    )
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=csv_path, remote="data.csv")],
        column_checks=[ColumnCheck(filename="data.csv", expected=["id", "value"])],
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert report.passed


def test_csv_columns_missing(tmp_path):
    """A missing column should fail."""
    csv_path = _make_csv(
        tmp_path / "data.csv",
        [
            ["id", "name"],
            ["1", "foo"],
        ],
    )
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=csv_path, remote="data.csv")],
        column_checks=[ColumnCheck(filename="data.csv", expected=["id", "MISSING_COL"])],
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert not report.passed
    assert any("MISSING_COL" in e for e in report.errors)


def test_csv_columns_case_insensitive(tmp_path):
    """Column name matching should be case-insensitive."""
    csv_path = _make_csv(
        tmp_path / "d.csv",
        [
            ["ID", "NAME"],
            ["1", "foo"],
        ],
    )
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=csv_path, remote="d.csv")],
        column_checks=[ColumnCheck(filename="d.csv", expected=["id", "name"])],
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert report.passed


def test_csv_columns_file_not_matched(tmp_path):
    """When the expected file isn't among entries, it should warn, not crash."""
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        files=[FileEntry(local=tmp_path / "exists.csv", remote="exists.csv")],
        column_checks=[ColumnCheck(filename="unknown.csv", expected=["x"])],
    )
    (tmp_path / "exists.csv").touch()
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    assert report.passed  # warning only
    assert any("unknown.csv" in w for w in report.warnings)


# ── Mixed / combined ──────────────────────────────────────────────────────────


def test_multiple_errors_collected(tmp_path):
    """All errors should be collected, not just the first one."""
    cfg = DatasetConfig(
        name="test",
        repo_id="user/repo",
        # two files, both missing
        files=[
            FileEntry(local=tmp_path / "a.csv", remote="a.csv"),
            FileEntry(local=tmp_path / "b.csv", remote="b.csv"),
        ],
        min_files=5,
    )
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    # errors: 2 missing files + 1 min_files
    assert len(report.errors) == 3


def test_empty_dataset(tmp_path):
    """A config with zero file entries and default checks should warn."""
    cfg = DatasetConfig(name="test", repo_id="user/repo", files=[])
    validator = DatasetValidator(cfg)
    report = validator.run_all()
    # min_files = 1 > 0 → error
    assert not report.passed


class TestMetaPlaceholderGate:
    """#288: a [meta] placeholder reaches the agent instead of travelling silently.

    `sofer init` writes an all-placeholder [meta] block, and before this gate the
    values travelled through validate, prepare, codebook_all, profile_all and
    render_all with every envelope reporting ok: true.
    """

    @staticmethod
    def _cfg(**meta: object) -> DatasetConfig:
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=Path("a.csv"), remote="a.parquet")],
        )
        for key, value in meta.items():
            setattr(cfg, key, value)
        return cfg

    def test_the_real_init_template_trips_every_guard(self) -> None:
        """The template is the whole reason the gate exists."""
        from sofer.cli import _INIT_TEMPLATE

        rendered = _INIT_TEMPLATE.format(name="test", user="someone")
        assert "TODO: short description" in rendered
        assert "TODO: MIT / restricted" in rendered
        assert "TODO: organisation name" in rendered
        assert "TODO: tag1" in rendered

    def test_each_placeholder_field_warns(self) -> None:
        cfg = self._cfg(
            description="TODO: short description",
            license="TODO: MIT / restricted / …",
            source="TODO: organisation name",
            tags=["TODO: tag1", "TODO: tag2"],
        )
        warnings = meta_placeholder_warnings(cfg)
        assert len(warnings) == 4
        assert "[meta] description" in warnings[0]
        assert "[meta] license" in warnings[1]
        assert "[meta] source" in warnings[2]
        assert "[meta] tags" in warnings[3]

    def test_an_empty_value_warns_for_the_three_scalars(self) -> None:
        """An empty `tags` list is not a placeholder: there is no value to replace."""
        warnings = meta_placeholder_warnings(self._cfg())
        assert len(warnings) == 3
        assert "(empty)" in warnings[0]

    def test_real_values_do_not_warn(self) -> None:
        cfg = self._cfg(
            description="Household census, 2025 wave.",
            license="MIT",
            source="National Statistics Office",
            tags=["census", "households"],
        )
        assert meta_placeholder_warnings(cfg) == []

    def test_an_example_prefixed_source_is_flagged(self) -> None:
        """`example` is one of the issue's prefixes, so this is intended.

        It is also the gate's false-positive risk: an organisation genuinely
        named "Example ..." is flagged. That is preferred over letting the
        template's own `TODO:`-style stand-ins through, and the ambiguity is
        recorded in the change's design doc rather than hidden.
        """
        cfg = self._cfg(description="Real.", license="MIT", source="Example Organisation")
        warnings = meta_placeholder_warnings(cfg)
        assert len(warnings) == 1
        assert "[meta] source" in warnings[0]

    def test_the_match_is_case_insensitive(self) -> None:
        cfg = self._cfg(description="todo: fix", source="EXAMPLE Org", license="Your_License")
        assert len(meta_placeholder_warnings(cfg)) == 3

    def test_a_real_value_merely_containing_a_prefix_is_fine(self) -> None:
        """Only a PREFIX marks a placeholder, so prose is not a false positive."""
        cfg = self._cfg(
            description="An example-driven survey of 1,200 households.",
            license="MIT",
            source="National Statistics Office",
            tags=["example-driven-study"],
        )
        warnings = meta_placeholder_warnings(cfg)
        assert [w for w in warnings if "[meta] description" in w] == []
        assert [w for w in warnings if "[meta] source" in w] == []
        assert len(warnings) == 1  # only the tag prefix still matches
        assert "[meta] tags" in warnings[0]

    def test_prefixes_are_config_owned(self, monkeypatch) -> None:
        """A [tool.sofer] value, never a literal in the call path (rule 1)."""
        monkeypatch.setattr(config, "META_PLACEHOLDER_PREFIXES", ["DRAFT"])
        cfg = self._cfg(description="DRAFT text", license="TODO: x", source="Real Org")
        warnings = meta_placeholder_warnings(cfg)
        assert len(warnings) == 1
        assert "[meta] description" in warnings[0]

    def test_the_warning_reaches_the_report_and_keeps_passed_true(self, tmp_path) -> None:
        """D3: a warning, never a failure — the exit code is untouched.

        The declared file exists, so the only thing in play is the [meta] warning:
        a missing file would fail the report for an unrelated reason and the
        assertion would prove nothing.
        """
        (tmp_path / "a.csv").write_text("a;b\n1;2\n", encoding="utf-8")
        cfg = DatasetConfig(
            name="test",
            repo_id="u/test",
            files=[FileEntry(local=Path("a.csv"), remote="a.parquet")],
            description="TODO: x",
        )
        cfg._base_dir = tmp_path
        report = DatasetValidator(cfg).run_all()
        assert any("[meta]" in w for w in report.warnings)
        assert report.errors == []
        assert report.passed is True

    def test_the_warning_is_visible_in_the_printed_summary(self, capsys) -> None:
        cfg = self._cfg(description="TODO: x")
        report = DatasetValidator(cfg).run_all()
        report.print_summary()
        assert "[meta] description" in capsys.readouterr().out
