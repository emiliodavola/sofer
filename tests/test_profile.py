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

    def test_deterministic_metadata_with_source_date_epoch(self, tmp_path, monkeypatch):
        """With SOURCE_DATE_EPOCH fixed, two identical runs produce byte-identical
        metadata.yaml (TC-13 determinism, #118)."""
        monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
        csv_path = tmp_path / "contacts.csv"
        _write_email_csv(csv_path)

        assert profile(csv_path) == 0
        first = (tmp_path / "metadata.yaml").read_bytes()
        (tmp_path / "metadata.yaml").unlink()
        assert profile(csv_path) == 0
        second = (tmp_path / "metadata.yaml").read_bytes()
        assert first == second

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

    base_p = _Path(str(base))
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
        """CLI profile --force overwrites."""
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


# ---------------------------------------------------------------------------
#  Multisheet 1:N (fix/multisheet-profile-render) — covers UNTESTED spec
# ---------------------------------------------------------------------------


def _make_xlsx(path, sheets: dict[str, list[list[object]]]):
    """Create an .xlsx at *path* with *sheets* mapping sheet_name -> rows (header first)."""
    import openpyxl

    wb = openpyxl.Workbook()
    first = True
    for name, rows in sheets.items():
        if first:
            ws = wb.active
            assert ws is not None
            ws.title = name
            first = False
            sheet_ws = ws
        else:
            sheet_ws = wb.create_sheet(title=name)
        for row in rows:
            sheet_ws.append(row)
    wb.save(path)


class TestProfileMultisheetPrf05:
    """PRF-05 multisheet 1:N — Sales/Inventory, sanitize, dedup, collision."""

    def test_multisheet_workbook_2_sheets_yields_2_profiles(self, tmp_path, restore_tool_config):
        """report.xlsx with Sales(id,amount) + Inventory(sku,qty) -> report__sales + __inventory."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir(parents=True)
        xlsx = tmp_path / "cache" / "report.xlsx"
        _make_xlsx(
            xlsx,
            {
                "Sales": [["id", "amount"], [1, 10], [2, 20]],
                "Inventory": [["sku", "qty"], ["A1", 5], ["B2", 7]],
            },
        )
        toml = _write_dataset_toml(tmp_path, ["cache/report.xlsx"])
        dataset_cfg = DatasetConfig.from_toml(toml)

        results = generate_all_profiles(dataset_cfg)

        sales_meta = tmp_path / "cache" / "profiles" / "report__sales.metadata.yaml"
        inv_meta = tmp_path / "cache" / "profiles" / "report__inventory.metadata.yaml"
        assert sales_meta.is_file(), results
        assert inv_meta.is_file()
        assert len(results) == 2
        sales_data = yaml.safe_load(sales_meta.read_text(encoding="utf-8"))
        inv_data = yaml.safe_load(inv_meta.read_text(encoding="utf-8"))
        sales_cols = [c["name"] for c in sales_data["structure"]["schema"]]
        inv_cols = [c["name"] for c in inv_data["structure"]["schema"]]
        assert sales_cols == ["id", "amount"]
        assert inv_cols == ["sku", "qty"]
        assert sales_data["file"]["rows"] == 2
        assert inv_data["file"]["rows"] == 2

    def test_multisheet_with_output_option_b_relative(
        self, tmp_path, restore_tool_config, monkeypatch
    ):
        """Multisheet relative --output anchored to base_dir (Option B)."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "cache").mkdir()
        xlsx = proj / "cache" / "report.xlsx"
        _make_xlsx(
            xlsx,
            {
                "Sales": [["id", "amount"], [1, 10]],
                "Inventory": [["sku", "qty"], ["A1", 5]],
            },
        )
        toml = _write_dataset_toml(proj, ["cache/report.xlsx"])
        dataset_cfg = DatasetConfig.from_toml(toml)
        cfg.reload(proj)
        other = tmp_path / "other"
        other.mkdir()
        monkeypatch.chdir(other)

        generate_all_profiles(dataset_cfg, output_dir="rel/out")

        assert (proj / "rel" / "out" / "profiles" / "report__sales.metadata.yaml").is_file()
        assert (proj / "rel" / "out" / "profiles" / "report__inventory.metadata.yaml").is_file()
        assert not (other / "rel").exists()

    def test_single_sheet_xlsx_stays_suffix_less(self, tmp_path, restore_tool_config):
        """Single-sheet .xlsx must emit profiles/<stem>.metadata.yaml (no __sheet), byte-stable."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        xlsx = tmp_path / "cache" / "single.xlsx"
        _make_xlsx(xlsx, {"Data": [["id", "val"], [1, "a"], [2, "b"]]})
        toml = _write_dataset_toml(tmp_path, ["cache/single.xlsx"])
        dataset_cfg = DatasetConfig.from_toml(toml)

        results = generate_all_profiles(dataset_cfg)

        expected = tmp_path / "cache" / "profiles" / "single.metadata.yaml"
        assert expected.is_file()
        assert len(results) == 1
        assert str(expected) in results
        # Ensure no __ sheet suffix was created
        assert not (tmp_path / "cache" / "profiles" / "single__data.metadata.yaml").exists()
        data = yaml.safe_load(expected.read_text(encoding="utf-8"))
        assert [c["name"] for c in data["structure"]["schema"]] == ["id", "val"]
        assert data["file"]["rows"] == 2

    def test_sanitize_sheet_name_applied(self, restore_tool_config):
        """sanitize DATA GOT Año->data_got_ano, empty->sheet."""
        from sofer._converters import sanitize_sheet_name

        assert sanitize_sheet_name("DATA GOT Año") == "data_got_ano"
        assert sanitize_sheet_name("Ventas 2024!") == "ventas_2024"
        assert sanitize_sheet_name("") == "sheet"
        assert sanitize_sheet_name("   ") == "sheet"
        assert sanitize_sheet_name("DATA GOT Año") == "data_got_ano"

    def test_dedup_via_seen(self, tmp_path, restore_tool_config):
        """Ventas variants -> ventas, ventas_2, ventas_3 via seen."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        xlsx = tmp_path / "cache" / "dedup.xlsx"
        # trailing spaces produce same sanitized 'ventas' -> dedup needed
        _make_xlsx(
            xlsx,
            {
                "Ventas": [["id"], [1]],
                "Ventas ": [["id"], [2]],
                "Ventas  ": [["id"], [3]],
            },
        )
        toml = _write_dataset_toml(tmp_path, ["cache/dedup.xlsx"])
        dataset_cfg = DatasetConfig.from_toml(toml)

        generate_all_profiles(dataset_cfg)

        assert (tmp_path / "cache" / "profiles" / "dedup__ventas.metadata.yaml").is_file()
        assert (tmp_path / "cache" / "profiles" / "dedup__ventas_2.metadata.yaml").is_file()
        assert (tmp_path / "cache" / "profiles" / "dedup__ventas_3.metadata.yaml").is_file()

    def test_sheet_aware_collision_normalized(self, tmp_path, restore_tool_config, capsys):
        """a__ventas.xlsx vs a_ventas.csv normalized collision."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        # a__ventas.xlsx single sheet 'Ventas' -> suffix-less profiles/a__ventas.metadata.yaml
        # normalized __+->_ -> a_ventas.metadata.yaml collides with a_ventas.csv
        xlsx = tmp_path / "cache" / "a__ventas.xlsx"
        _make_xlsx(xlsx, {"Ventas": [["id"], [1]]})
        _write_csv(tmp_path / "cache" / "a_ventas.csv", [["id"], ["9"]])
        _write_csv(tmp_path / "cache" / "ok.csv", [["col"], ["1"]])
        toml = _write_dataset_toml(
            tmp_path, ["cache/a__ventas.xlsx", "cache/a_ventas.csv", "cache/ok.csv"]
        )
        dataset_cfg = DatasetConfig.from_toml(toml)

        with pytest.raises(ValueError, match="Collision"):
            generate_all_profiles(dataset_cfg)

        # non-colliding ok.csv must be persisted
        assert (tmp_path / "cache" / "profiles" / "ok.metadata.yaml").is_file()
        # colliding outputs must NOT be written
        assert not (tmp_path / "cache" / "profiles" / "a_ventas.metadata.yaml").is_file()
        assert not (tmp_path / "cache" / "profiles" / "a__ventas.metadata.yaml").is_file()
        err = capsys.readouterr().err
        assert "a__ventas.xlsx" in err
        assert "a_ventas.csv" in err
        assert "::ventas" in err.lower()

    def test_profile_output_helper_purepath_suffixes(self, tmp_path):
        """_profile_output_for_rel suffixes handling."""
        from sofer.profile import _profile_output_for_rel

        out = _profile_output_for_rel(tmp_path / "profiles", tmp_path / "a.b", None)
        assert out.name == "a.metadata.yaml"
        out2 = _profile_output_for_rel(tmp_path / "profiles", tmp_path / "a.b", "ventas")
        assert out2.name == "a__ventas.metadata.yaml"

    def test_mcp_containment_profile_dir(self, tmp_path, restore_tool_config):
        """_validate_output_targets must flag escaping profile_dir (outside server root)."""
        from sofer.mcp_server import _validate_output_targets
        from sofer.model import DatasetConfig

        (tmp_path / "pyproject.toml").write_text(
            '[tool.sofer]\nprofile_dir = "../../evil"\n', encoding="utf-8"
        )
        import sofer.config as cfg

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir(exist_ok=True)
        _write_csv(tmp_path / "cache" / "a.csv", [["col"], ["1"]])
        toml = _write_dataset_toml(tmp_path, ["cache/a.csv"])
        dataset_cfg = DatasetConfig.from_toml(toml)

        errors = _validate_output_targets(dataset_cfg, root=tmp_path)
        assert any("profile_dir" in e and "outside the server root" in e for e in errors)

    def test_normalize_collision_key(self):
        """_normalize_profile_collision_key collapses __+ to _."""
        from pathlib import Path

        from sofer.profile import _normalize_profile_collision_key

        assert (
            _normalize_profile_collision_key(Path("a__ventas.metadata.yaml"))
            == "a_ventas.metadata.yaml"
        )
        assert (
            _normalize_profile_collision_key(Path("a___ventas.metadata.yaml"))
            == "a_ventas.metadata.yaml"
        )
        assert (
            _normalize_profile_collision_key(Path("a_ventas.metadata.yaml"))
            == "a_ventas.metadata.yaml"
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  Unit F: profile.py floor → ≥91 (COV-01)
# ═══════════════════════════════════════════════════════════════════════════════


def _make_xlsx_file(path, sheets: dict[str, list[list[object]]]) -> None:
    """Write an xlsx workbook with the named sheet → rows mapping."""
    import openpyxl

    wb = openpyxl.Workbook()
    first = wb.active
    if first is not None:
        wb.remove(first)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name)
        for row in rows:
            ws.append(row)
    wb.save(path)


class TestProfileMultisheetPrf05Next:
    def test_profile_output_for_rel_multisuffix(self, tmp_path) -> None:
        """A multi-suffix stem (.tar.csv → .tar.metadata.yaml) keeps the mid suffix."""
        from pathlib import Path as _Path

        from sofer.profile import _profile_output_for_rel

        out = _profile_output_for_rel(_Path("profiles"), _Path("data/a.tar.csv"), sheet=None)
        assert out.as_posix() == "profiles/data/a.tar.tar.metadata.yaml"

    def test_profile_output_for_rel_single_suffix(self, tmp_path) -> None:
        """A single-suffix stem replaces only the extension."""
        from pathlib import Path as _Path

        from sofer.profile import _profile_output_for_rel

        out = _profile_output_for_rel(_Path("profiles"), _Path("data/a.csv"), sheet=None)
        assert out.as_posix() == "profiles/data/a.metadata.yaml"

    def test_profile_output_for_sheet_suffix(self, tmp_path) -> None:
        """A sheet suffix appends after the base metadata name."""
        from pathlib import Path as _Path

        from sofer.profile import _profile_output_for_rel

        out = _profile_output_for_rel(_Path("profiles"), _Path("data/a.csv"), sheet="ventas")
        assert out.as_posix() == "profiles/data/a__ventas.metadata.yaml"


class TestProfileSingleFileEdges:
    def test_missing_dataset_file_returns_1(self, tmp_path, capsys) -> None:
        """profile() on a missing path prints a clean error and exits 1."""
        rc = profile(tmp_path / "nope.csv")
        assert rc == 1
        assert "Dataset not found" in capsys.readouterr().err

    def test_tsv_writes_metadata_with_tab_delimiter(self, tmp_path) -> None:
        """A TSV profile records the tab delimiter in metadata.yaml."""
        import yaml as _yaml

        tsv = tmp_path / "data.tsv"
        tsv.write_text("a\tb\n1\t2\n", encoding="utf-8")
        assert profile(tsv) == 0
        meta_path = tmp_path / "metadata.yaml"
        assert meta_path.is_file()
        payload = _yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        assert payload["file"]["delimiter"] == "\t"
        assert payload["file"]["format"] == "tsv"

    def test_profile_parquet_writes_metadata(self, tmp_path) -> None:
        """Parquet is profiled through the non-streamed _read_file branch."""
        import pyarrow as pa
        import pyarrow.parquet as pq
        import yaml as _yaml

        p = tmp_path / "data.parquet"
        pq.write_table(pa.table({"a": [1, 2], "b": ["x", "y"]}), p)
        rc = profile(p)
        assert rc == 0
        payload = _yaml.safe_load((tmp_path / "metadata.yaml").read_text(encoding="utf-8"))
        assert payload["file"]["format"] == "parquet"
        assert payload["file"]["rows"] == 2
        assert payload["file"]["delimiter"] == ""

    def test_profile_jsonl_writes_metadata(self, tmp_path) -> None:
        """JSON Lines is profiled through the non-streamed _read_file branch."""
        import json as _json

        import yaml as _yaml

        p = tmp_path / "data.jsonl"
        p.write_text(
            "\n".join(_json.dumps(r) for r in [{"a": 1}, {"a": 2}]) + "\n", encoding="utf-8"
        )
        rc = profile(p)
        assert rc == 0
        payload = _yaml.safe_load((tmp_path / "metadata.yaml").read_text(encoding="utf-8"))
        assert payload["file"]["format"] == "jsonl"
        assert payload["file"]["delimiter"] == ""

    def test_profile_ragged_longer_row_truncated(self, tmp_path) -> None:
        """A CSV row longer than the header is truncated by _stream_columns."""
        csv = tmp_path / "data.csv"
        csv.write_text("a;b\n1;2;3\n", encoding="utf-8")
        rc = profile(csv)
        assert rc == 0
        assert (tmp_path / "metadata.yaml").is_file()


class TestProfileBatchSkipPaths:
    def test_batch_skips_dir_missing_unsupported_and_empty(
        self, tmp_path, restore_tool_config, capsys
    ) -> None:
        """Batch skip paths: directory, missing file, unsupported format."""
        import sofer.config as cfg_mod
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg_mod.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        (tmp_path / "cache" / "ok.csv").write_text("a;b\n1;2\n", encoding="utf-8")
        (tmp_path / "cache" / "subdir").mkdir()
        (tmp_path / "cache" / "notes.txt").write_text("x", encoding="utf-8")
        toml = tmp_path / "dataset.toml"
        toml.write_text(
            '[dataset]\nname = "t"\nrepo_id = "u/t"\n\n'
            '[[file]]\nlocal = "cache/ok.csv"\nremote = "ok.csv"\n'
            '[[file]]\nlocal = "cache/subdir"\nremote = "subdir/"\nrecursive = true\n'
            '[[file]]\nlocal = "cache/missing.csv"\nremote = "missing.csv"\n'
            '[[file]]\nlocal = "cache/notes.txt"\nremote = "notes.txt"\n',
            encoding="utf-8",
        )
        results = generate_all_profiles(DatasetConfig.from_toml(str(toml)))
        err = capsys.readouterr().err
        assert "Skipping directory" in err
        assert "Skipping missing file" in err
        assert "Unsupported format, skipping" in err
        assert len(results) == 1
        assert results[0].replace("\\", "/").endswith("cache/profiles/ok.metadata.yaml")

    def test_batch_all_entries_skipped_returns_empty(self, tmp_path, restore_tool_config) -> None:
        """A config whose entries all fail collection returns [] (no profiles)."""
        import sofer.config as cfg_mod
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg_mod.reload(tmp_path)
        toml = tmp_path / "dataset.toml"
        toml.write_text(
            '[dataset]\nname = "t"\nrepo_id = "u/t"\n\n'
            '[[file]]\nlocal = "cache/nope.csv"\nremote = "nope.csv"\n',
            encoding="utf-8",
        )
        assert generate_all_profiles(DatasetConfig.from_toml(str(toml))) == []

    def test_batch_xlsx_read_error_skips(
        self, tmp_path, restore_tool_config, capsys, monkeypatch
    ) -> None:
        """An unreadable xlsx is skipped with a stderr note (expanded empty → [])."""
        import sofer.config as cfg_mod
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg_mod.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        (tmp_path / "cache" / "b.xlsx").write_bytes(b"not an xlsx")
        toml = tmp_path / "dataset.toml"
        toml.write_text(
            '[dataset]\nname = "t"\nrepo_id = "u/t"\n\n'
            '[[file]]\nlocal = "cache/b.xlsx"\nremote = "b.xlsx"\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "sofer.profile._read_xlsx_sheets",
            lambda _p: (_ for _ in ()).throw(ValueError("corrupt")),
        )
        results = generate_all_profiles(DatasetConfig.from_toml(str(toml)))
        assert "Error reading" in capsys.readouterr().err
        assert results == []

    def test_batch_profile_read_error_skips(
        self, tmp_path, restore_tool_config, capsys, monkeypatch
    ) -> None:
        """A per-file read failure is skipped with a stderr note."""
        import sofer.config as cfg_mod
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg_mod.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        (tmp_path / "cache" / "a.csv").write_text("a;b\n1;2\n", encoding="utf-8")
        (tmp_path / "cache" / "b.csv").write_text("a;b\n3;4\n", encoding="utf-8")
        toml = tmp_path / "dataset.toml"
        toml.write_text(
            '[dataset]\nname = "t"\nrepo_id = "u/t"\n\n'
            '[[file]]\nlocal = "cache/a.csv"\nremote = "a.csv"\n'
            '[[file]]\nlocal = "cache/b.csv"\nremote = "b.csv"\n',
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "sofer.profile._read_dataset_for_profile",
            lambda _p, _s: (_ for _ in ()).throw(ValueError("boom")),
        )
        results = generate_all_profiles(DatasetConfig.from_toml(str(toml)))
        assert "Error reading" in capsys.readouterr().err
        assert results == []


class TestProfileXlsxEdges:
    def test_xlsx_zero_sheets_writes_empty_metadata(
        self, tmp_path, restore_tool_config, capsys, monkeypatch
    ) -> None:
        """A workbook reported as sheet-less still emits the empty stub metadata."""
        import sofer.config as cfg_mod
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg_mod.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        _make_xlsx_file(tmp_path / "cache" / "z.xlsx", {"ventas": [["v"], [1]]})
        toml = tmp_path / "dataset.toml"
        toml.write_text(
            '[dataset]\nname = "t"\nrepo_id = "u/t"\n\n'
            '[[file]]\nlocal = "cache/z.xlsx"\nremote = "z.xlsx"\n',
            encoding="utf-8",
        )
        monkeypatch.setattr("sofer.profile._read_xlsx_sheets", lambda _p: {})
        results = generate_all_profiles(DatasetConfig.from_toml(str(toml)))
        assert results, "an empty stub metadata must be written"
        assert results[0].replace("\\", "/").endswith("cache/profiles/z.metadata.yaml")


class TestProfileBatchPrf05Next:
    def test_batch_reads_parquet_and_xlsx(self, tmp_path, restore_tool_config) -> None:
        """Batch profiler reads parquet through _read_dataset_for_profile."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        import sofer.config as cfg_mod
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg_mod.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        pq.write_table(pa.table({"a": [1, 2]}), tmp_path / "cache" / "p.parquet")
        _make_xlsx_file(tmp_path / "cache" / "x.xlsx", {"hoja": [["v"], [1]]})
        toml = tmp_path / "dataset.toml"
        toml.write_text(
            '[dataset]\nname = "t"\nrepo_id = "u/t"\n\n'
            '[[file]]\nlocal = "cache/p.parquet"\nremote = "p.parquet"\n'
            '[[file]]\nlocal = "cache/x.xlsx"\nremote = "x.xlsx"\n',
            encoding="utf-8",
        )
        results = generate_all_profiles(DatasetConfig.from_toml(str(toml)))
        assert len(results) == 2
        assert any(r.replace("\\", "/").endswith("cache/profiles/p.metadata.yaml") for r in results)
        assert any(r.replace("\\", "/").endswith("cache/profiles/x.metadata.yaml") for r in results)

    def test_collision_names_sources_outside_base(
        self, tmp_path, restore_tool_config, capsys
    ) -> None:
        """A collision with the write root OUTSIDE base falls back to absolute paths."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        import sofer.config as cfg_mod
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles

        cfg_mod.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        (tmp_path / "cache" / "x.csv").write_text("col\n1\n", encoding="utf-8")
        pq.write_table(pa.table({"col": [1]}), tmp_path / "cache" / "x.parquet")
        toml = tmp_path / "dataset.toml"
        toml.write_text(
            '[dataset]\nname = "t"\nrepo_id = "u/t"\n\n'
            '[[file]]\nlocal = "cache/x.csv"\nremote = "x.csv"\n'
            '[[file]]\nlocal = "cache/x.parquet"\nremote = "x.parquet"\n',
            encoding="utf-8",
        )
        outside = tmp_path.parent / f"outside-{tmp_path.name}"  # sibling, NOT under base
        with pytest.raises(ValueError, match="Collision"):
            generate_all_profiles(DatasetConfig.from_toml(str(toml)), output_dir=outside)
        err = capsys.readouterr().err
        assert "Collision:" in err
        assert "x.csv" in err and "x.parquet" in err
