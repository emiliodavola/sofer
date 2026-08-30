"""Tests for sofer.profile — the read-only profile orchestrator (WU5).

Covers Phase 5 (PRF-01..04): CSV/TSV → ``metadata.yaml`` beside the dataset
(PRF-02), email semantic type + status (PRF-02), possible-PII flag (PRF-02),
missing human-input fields reported and recorded (PRF-02), read-only source
guarantee (PRF-03), unsupported-format clean error (PRF-04), and the CLI wiring
(PRF-01 / CLI-R03).
"""

from __future__ import annotations

import csv
from argparse import Namespace

import pytest
import yaml

from sofer import cli
from sofer.profile import profile


def _write_csv(path, rows, delimiter=";"):
    """Write *rows* to *path* as a delimiter-separated file (utf-8)."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, delimiter=delimiter).writerows(rows)


def _write_email_csv(path):
    """A two-column CSV with an email column and a numeric column."""
    _write_csv(
        path,
        [
            ["user_email", "age"],
            ["alice@example.com", "30"],
            ["bob@example.com", "25"],
        ],
    )


class TestProfileWritesMetadataYaml:
    """profile() writes a ``metadata.yaml`` document (PRF-02)."""

    def test_csv_writes_metadata_yaml_next_to_dataset(self, tmp_path):
        csv_path = tmp_path / "contacts.csv"
        _write_email_csv(csv_path)

        rc = profile(csv_path)

        assert rc == 0
        meta_path = tmp_path / "metadata.yaml"
        assert meta_path.exists()
        data = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        assert "structure" in data
        assert data["file"]["format"] == "csv"

    def test_output_dir_override(self, tmp_path):
        csv_path = tmp_path / "contacts.csv"
        _write_email_csv(csv_path)
        out_dir = tmp_path / "out"

        rc = profile(csv_path, output_dir=out_dir)

        assert rc == 0
        assert (out_dir / "metadata.yaml").exists()
        # No metadata.yaml beside the dataset when --output is given.
        assert not (tmp_path / "metadata.yaml").exists()

    def test_tsv_writes_metadata_yaml(self, tmp_path):
        tsv_path = tmp_path / "contacts.tsv"
        _write_csv(
            tsv_path,
            [["user_email", "age"], ["alice@example.com", "30"]],
            delimiter="\t",
        )

        rc = profile(tsv_path)

        assert rc == 0
        data = yaml.safe_load((tmp_path / "metadata.yaml").read_text(encoding="utf-8"))
        assert data["file"]["format"] == "tsv"
        assert data["structure"]["schema"][0]["name"] == "user_email"


class TestProfileEmailDetection:
    """An email column is detected semantically and flagged as possible PII (PRF-02)."""

    def test_email_semantic_type_detected(self, tmp_path):
        csv_path = tmp_path / "contacts.csv"
        _write_email_csv(csv_path)

        profile(csv_path)
        col = yaml.safe_load((tmp_path / "metadata.yaml").read_text(encoding="utf-8"))["structure"][
            "schema"
        ][0]

        assert col["name"] == "user_email"
        assert col["semantic_type"]["type"] == "email"
        assert col["semantic_type"]["status"] == "confirmed"
        assert col["semantic_type"]["confidence"] == pytest.approx(0.98)
        assert col["semantic_type"]["basis"] == "email"

    def test_email_column_flagged_possible_pii(self, tmp_path):
        csv_path = tmp_path / "contacts.csv"
        _write_email_csv(csv_path)

        profile(csv_path)
        col = yaml.safe_load((tmp_path / "metadata.yaml").read_text(encoding="utf-8"))["structure"][
            "schema"
        ][0]

        assert col["pii"] == [
            {"label": "email", "confidence": pytest.approx(0.98), "note": "possible_pii"}
        ]

    def test_non_email_column_not_flagged(self, tmp_path):
        csv_path = tmp_path / "contacts.csv"
        _write_email_csv(csv_path)

        profile(csv_path)
        age_col = yaml.safe_load((tmp_path / "metadata.yaml").read_text(encoding="utf-8"))[
            "structure"
        ]["schema"][1]

        assert age_col["name"] == "age"
        assert age_col["semantic_type"]["status"] == "unknown"
        assert age_col["pii"] == []


class TestProfileMissingFields:
    """Human-input gaps are reported and recorded (PRF-02)."""

    def test_missing_fields_recorded_in_yaml(self, tmp_path):
        csv_path = tmp_path / "contacts.csv"
        _write_email_csv(csv_path)

        profile(csv_path)
        data = yaml.safe_load((tmp_path / "metadata.yaml").read_text(encoding="utf-8"))
        missing = data["documentation"]["missing_fields"]

        assert "description" in missing
        assert "license" in missing
        assert "source" in missing
        assert "user_email.description" in missing

    def test_missing_fields_printed(self, tmp_path, capsys):
        csv_path = tmp_path / "contacts.csv"
        _write_email_csv(csv_path)

        profile(csv_path)
        out = capsys.readouterr().out

        assert "description" in out
        assert "license" in out
        assert "source" in out


class TestProfileReadOnly:
    """profile() never modifies the source dataset (PRF-03)."""

    def test_source_bytes_unchanged(self, tmp_path):
        csv_path = tmp_path / "contacts.csv"
        _write_email_csv(csv_path)
        before = csv_path.read_bytes()

        profile(csv_path)

        assert csv_path.read_bytes() == before


class TestProfileUnsupportedFormat:
    """Unsupported formats fail cleanly with no metadata.yaml (PRF-04)."""

    def test_unsupported_format_returns_nonzero(self, tmp_path):
        bad_path = tmp_path / "data.xyz"
        bad_path.write_text("not a dataset", encoding="utf-8")

        rc = profile(bad_path)

        assert rc == 1
        assert not (tmp_path / "metadata.yaml").exists()

    def test_unsupported_format_prints_clean_error(self, tmp_path, capsys):
        bad_path = tmp_path / "data.xyz"
        bad_path.write_text("not a dataset", encoding="utf-8")

        profile(bad_path)
        err = capsys.readouterr().err

        assert "data.xyz" in err
        assert "Unsupported" in err


class TestProfileCli:
    """The ``profile`` subcommand and handler wire up correctly (PRF-01 / CLI-R03)."""

    def test_profile_subparser(self):
        args = cli._build_parser().parse_args(["profile", "data.csv"])
        assert args.command == "profile"
        assert args.dataset == "data.csv"
        assert args.output is None
        assert callable(args.func)

    def test_profile_subparser_with_output(self):
        args = cli._build_parser().parse_args(["profile", "data.csv", "--output", "out/"])
        assert args.dataset == "data.csv"
        assert args.output == "out/"

    def test_profile_appears_in_help(self, capsys):
        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["--help"])
        assert "profile" in capsys.readouterr().out

    def test_profile_help_accurate(self, capsys):
        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["profile", "--help"])
        out = capsys.readouterr().out
        assert "metadata.yaml" in out
        assert "--output" in out

    def test_cmd_profile_dispatches(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        _write_email_csv(csv_path)

        rc = cli._cmd_profile(Namespace(dataset=str(csv_path), output=None))

        assert rc == 0
        assert (tmp_path / "metadata.yaml").exists()


class TestProfileUniqueExcludesSentinels:
    """PRF-02 — the coarse schema's unique counts distinct non-missing values."""

    def test_unique_statistic_excludes_sentinels(self, tmp_path):
        """Sentinels ("", NA, NULL) must not count as distinct values."""
        csv_path = tmp_path / "vals.csv"
        _write_csv(csv_path, [["val"], ["A"], [""], ["NA"], ["B"], ["NULL"]])

        rc = profile(csv_path)

        assert rc == 0
        data = yaml.safe_load((tmp_path / "metadata.yaml").read_text(encoding="utf-8"))
        col = next(c for c in data["structure"]["schema"] if c["name"] == "val")
        assert col["unique"] == 2


# ---------------------------------------------------------------------------
#  PRF-05 / PRF-06 — batch + force guard (feat-profile-render-all-files)
# ---------------------------------------------------------------------------


def _write_dataset_toml(base: object, entries: list[str]):
    """Write a minimal dataset.toml under *base* with given [[file]] locals."""
    from pathlib import Path as _Path

    base_p = _Path(base)
    lines = [
        "[dataset]",
        'name = "test-ds"',
        'repo_id = "user/test-ds"',
        "",
    ]
    for local in entries:
        lines.extend(["[[file]]", f'local = "{local}"', f'remote = "{local}"', ""])
    toml_path = base_p / "dataset.toml"
    toml_path.write_text("\n".join(lines), encoding="utf-8")
    return toml_path


class TestProfileBatchPrf05:
    """PRF-05 batch profile via --all-files."""

    def test_batch_n_files(self, tmp_path, restore_tool_config):
        """Two files under cache/ -> two profiles under profiles/."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        for name in ("a.csv", "b.csv"):
            _write_csv(tmp_path / "cache" / name, [["col"], ["1"]])
        toml = _write_dataset_toml(tmp_path, ["cache/a.csv", "cache/b.csv"])
        dataset_cfg = DatasetConfig.from_toml(toml)

        results = generate_all_profiles(dataset_cfg)

        assert (tmp_path / "cache" / "profiles" / "a.metadata.yaml").is_file()
        assert (tmp_path / "cache" / "profiles" / "b.metadata.yaml").is_file()
        assert len(results) == 2

    def test_nested_labels_preserved(self, tmp_path, restore_tool_config):
        """cache/Labels/etiquetas_a.csv -> profiles/Labels/etiquetas_a.metadata.yaml."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg.reload(tmp_path)
        sub = tmp_path / "cache" / "Labels"
        sub.mkdir(parents=True)
        _write_csv(sub / "etiquetas_a.csv", [["col"], ["1"]])
        toml = _write_dataset_toml(tmp_path, ["cache/Labels/etiquetas_a.csv"])
        dataset_cfg = DatasetConfig.from_toml(toml)

        generate_all_profiles(dataset_cfg)

        assert (tmp_path / "cache" / "profiles" / "Labels" / "etiquetas_a.metadata.yaml").is_file()

    def test_collision_partial_write_then_value_error(self, tmp_path, restore_tool_config, capsys):
        """x.csv + x.parquet collide -> non-colliding written, colliding not, ValueError."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        _write_csv(tmp_path / "cache" / "a.csv", [["col"], ["1"]])
        _write_csv(tmp_path / "cache" / "x.csv", [["col"], ["1"]])
        # parquet with same stem x -> collision on x.metadata.yaml
        pq.write_table(pa.table({"col": ["1"]}), tmp_path / "cache" / "x.parquet")
        toml = _write_dataset_toml(tmp_path, ["cache/a.csv", "cache/x.csv", "cache/x.parquet"])
        dataset_cfg = DatasetConfig.from_toml(toml)

        with pytest.raises(ValueError, match="Collision"):
            generate_all_profiles(dataset_cfg)

        assert (tmp_path / "cache" / "profiles" / "a.metadata.yaml").is_file()
        assert not (tmp_path / "cache" / "profiles" / "x.metadata.yaml").is_file()
        err = capsys.readouterr().err
        assert "x.csv" in err and "x.parquet" in err

    def test_custom_output_absolute(self, tmp_path, restore_tool_config):
        """--output /tmp/out (absolute) writes under /tmp/out/profiles, cache untouched."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        _write_csv(tmp_path / "cache" / "a.csv", [["col"], ["1"]])
        toml = _write_dataset_toml(tmp_path, ["cache/a.csv"])
        dataset_cfg = DatasetConfig.from_toml(toml)

        out = tmp_path / "outAbs"
        results = generate_all_profiles(dataset_cfg, output_dir=out)

        assert (out / "profiles" / "a.metadata.yaml").is_file()
        assert str(out / "profiles" / "a.metadata.yaml") in results
        assert not (tmp_path / "cache" / "profiles").exists()

    def test_custom_output_relative(self, tmp_path, restore_tool_config, monkeypatch):
        """Relative --output anchors to cfg._base_dir (Option B), not CWD."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "cache").mkdir()
        _write_csv(proj / "cache" / "a.csv", [["col"], ["1"]])
        toml = _write_dataset_toml(proj, ["cache/a.csv"])
        dataset_cfg = DatasetConfig.from_toml(toml)

        cfg.reload(proj)
        # Change CWD elsewhere to prove anchoring is to base_dir, not CWD
        other = tmp_path / "other"
        other.mkdir()
        monkeypatch.chdir(other)

        generate_all_profiles(dataset_cfg, output_dir="rel/out")

        assert (proj / "rel" / "out" / "profiles" / "a.metadata.yaml").is_file()
        assert not (other / "rel" / "out" / "profiles" / "a.metadata.yaml").exists()
        assert not (proj / "cache" / "profiles").exists()

    def test_config_override_docs_profiles(self, tmp_path, restore_tool_config):
        """profile_dir=docs/profiles via pyproject -> outputs under docs/profiles/."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        (tmp_path / "pyproject.toml").write_text(
            '[tool.sofer]\nprofile_dir = "docs/profiles"\n', encoding="utf-8"
        )
        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        _write_csv(tmp_path / "cache" / "a.csv", [["col"], ["1"]])
        toml = _write_dataset_toml(tmp_path, ["cache/a.csv"])
        dataset_cfg = DatasetConfig.from_toml(toml)

        generate_all_profiles(dataset_cfg)

        assert (tmp_path / "cache" / "docs" / "profiles" / "a.metadata.yaml").is_file()

    def test_toml_without_files_fails_via_cli(self, tmp_path, restore_tool_config, capsys):
        """CLI --all-files with no [[file]] exits non-zero mentioning [[file]]."""
        toml = tmp_path / "dataset.toml"
        toml.write_text('[dataset]\nname = "x"\nrepo_id = "u/x"\n', encoding="utf-8")
        rc = cli._cmd_profile(
            Namespace(dataset=str(toml), output=None, all_files=True, force=False, config=str(toml))
        )
        assert rc == 1
        err = capsys.readouterr().err
        assert "[[file]]" in err

    def test_cache_untouched_when_output_given(self, tmp_path, restore_tool_config):
        """Batch with --output must never mutate cache/ (cache dir absent)."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        _write_csv(tmp_path / "cache" / "a.csv", [["col"], ["1"]])
        toml = _write_dataset_toml(tmp_path, ["cache/a.csv"])
        dataset_cfg = DatasetConfig.from_toml(toml)

        out = tmp_path / "build"
        generate_all_profiles(dataset_cfg, output_dir=out)

        assert (out / "profiles" / "a.metadata.yaml").is_file()
        assert not (tmp_path / "cache" / "profiles").exists()


class TestProfileForceGuardPrf06:
    """PRF-06 single-file force guard."""

    def test_guard_without_force_raises_and_unchanged(self, tmp_path):
        """Existing dest without --force raises FileExistsError with hint and file unchanged."""
        csv_path = tmp_path / "data.csv"
        _write_email_csv(csv_path)
        out = tmp_path / "out"
        out.mkdir()
        # first write
        rc = profile(csv_path, output_dir=out, force=False)
        assert rc == 0
        dest = out / "metadata.yaml"
        assert dest.is_file()
        dest.write_text("tampered", encoding="utf-8")
        # second write without force must raise and leave tampered content
        with pytest.raises(FileExistsError, match="use --force to overwrite"):
            profile(csv_path, output_dir=out, force=False)
        assert dest.read_text(encoding="utf-8") == "tampered"
        # hint must contain destination path
        try:
            profile(csv_path, output_dir=out, force=False)
        except FileExistsError as exc:
            assert str(dest) in str(exc)

    def test_overwrite_with_force(self, tmp_path):
        """With --force the existing file is overwritten and exit 0."""
        csv_path = tmp_path / "data.csv"
        _write_email_csv(csv_path)
        out = tmp_path / "out"
        out.mkdir()
        profile(csv_path, output_dir=out, force=False)
        dest = out / "metadata.yaml"
        dest.write_text("tampered", encoding="utf-8")
        rc = profile(csv_path, output_dir=out, force=True)
        assert rc == 0
        assert dest.read_text(encoding="utf-8") != "tampered"
        assert "structure" in dest.read_text(encoding="utf-8")

    def test_cli_guard_without_force_returns_1(self, tmp_path, capsys):
        """CLI profile without --force on existing dest returns 1 with hint."""
        csv_path = tmp_path / "data.csv"
        _write_email_csv(csv_path)
        out = tmp_path / "out"
        out.mkdir()
        rc1 = cli._cmd_profile(Namespace(dataset=str(csv_path), output=str(out), force=False))
        assert rc1 == 0
        rc2 = cli._cmd_profile(Namespace(dataset=str(csv_path), output=str(out), force=False))
        assert rc2 == 1
        assert "use --force to overwrite" in capsys.readouterr().err

    def test_cli_overwrite_with_force(self, tmp_path):
        """CLI profile --force overwrites and returns 0."""
        csv_path = tmp_path / "data.csv"
        _write_email_csv(csv_path)
        out = tmp_path / "out"
        out.mkdir()
        cli._cmd_profile(Namespace(dataset=str(csv_path), output=str(out), force=False))
        dest = out / "metadata.yaml"
        dest.write_text("tampered", encoding="utf-8")
        rc = cli._cmd_profile(Namespace(dataset=str(csv_path), output=str(out), force=True))
        assert rc == 0
        assert dest.read_text(encoding="utf-8") != "tampered"
