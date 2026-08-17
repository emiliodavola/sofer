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
