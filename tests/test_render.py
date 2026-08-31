"""Tests for sofer.render — README rendering from metadata.yaml (WU6).

Covers Phase 6 (RND-01..03, CLI-R03/R04): the file-vs-directory
disambiguation of the ``<package>`` argument (RND-01), the distinct rendering
of inference states — ``confirmed`` plain / ``email (inferred, 78%)`` /
``unknown`` (RND-03) — the round-half-to-even percentage rule, the
"unknown human fields render as ``unknown``" guarantee, and the ``render``
CLI wiring.
"""

from __future__ import annotations

from argparse import Namespace

import pytest

from sofer import cli
from sofer.metadata import (
    ColumnMetadata,
    DatasetMetadata,
    FileMetadata,
    Metadata,
    SemanticType,
    StructureMetadata,
    serialize,
)
from sofer.model import InferenceStatus
from sofer.pii import PiiDetection
from sofer.render import _percent, _render_semantic, render


def _metadata(*columns: ColumnMetadata, dataset: DatasetMetadata | None = None) -> Metadata:
    """Build a minimal Metadata document around the given schema columns."""
    return Metadata(
        dataset=dataset or DatasetMetadata(),
        file=FileMetadata(),
        structure=StructureMetadata(schema=list(columns)),
    )


def _write_metadata_yaml(tmp_path, meta: Metadata):
    """Serialize *meta* to ``metadata.yaml`` inside *tmp_path*."""
    path = tmp_path / "metadata.yaml"
    path.write_text(serialize(meta), encoding="utf-8")
    return path


def _email_semantic(status: InferenceStatus, confidence: float | None) -> SemanticType:
    """A ``user_email`` semantic result with the given status and confidence."""
    return SemanticType(type="email", status=status, confidence=confidence, basis="email")


class TestPercentRounding:
    """``_percent`` rounds confidence to a whole percentage (RND-03)."""

    def test_point_seventy_eight_is_78(self):
        assert _percent(0.78) == 78

    def test_rounds_nearest_not_truncated(self):
        # 0.789 * 100 = 78.9 → 79 (truncation would give 78).
        assert _percent(0.789) == 79

    def test_round_half_to_even_down(self):
        # 0.785 * 100 = 78.5 → 78 (round-half-to-even picks the even neighbour).
        assert _percent(0.785) == 78

    def test_round_half_to_even_up(self):
        # 0.795 * 100 = 79.5 → 80 (round-half-to-even, not round-half-up).
        assert _percent(0.795) == 80

    def test_whole_values(self):
        assert _percent(0.72) == 72
        assert _percent(0.9) == 90


class TestSemanticRendering:
    """Inference states render distinctly (RND-03)."""

    def test_confirmed_renders_plain(self):
        sem = _email_semantic(InferenceStatus.CONFIRMED, 0.98)
        assert _render_semantic(sem) == "email"

    def test_inferred_renders_with_confidence(self):
        sem = _email_semantic(InferenceStatus.INFERRED, 0.78)
        assert _render_semantic(sem) == "email (inferred, 78%)"

    def test_unknown_renders_unknown(self):
        assert _render_semantic(SemanticType()) == "unknown"

    def test_unknown_never_blank_or_fabricated(self):
        sem = SemanticType(type=None, status=InferenceStatus.UNKNOWN, confidence=None, basis=None)
        rendered = _render_semantic(sem)
        assert rendered == "unknown"
        assert rendered.strip() != ""
        assert "email" not in rendered  # never fabricate a type


class TestRenderResolvesPackagePath:
    """``render`` accepts a directory or a direct metadata.yaml path (RND-01)."""

    def test_directory_containing_metadata_yaml(self, tmp_path):
        _write_metadata_yaml(tmp_path, _metadata())
        assert render(tmp_path) == 0
        assert (tmp_path / "README.md").exists()

    def test_direct_metadata_yaml_path(self, tmp_path):
        meta_path = _write_metadata_yaml(tmp_path, _metadata())
        assert render(meta_path) == 0
        assert (tmp_path / "README.md").exists()

    def test_output_dir_override(self, tmp_path):
        _write_metadata_yaml(tmp_path, _metadata())
        out = tmp_path / "out"
        assert render(tmp_path, output_dir=out) == 0
        assert (out / "README.md").exists()
        # No README beside metadata.yaml when --output is given.
        assert not (tmp_path / "README.md").exists()

    def test_directory_without_metadata_yaml_returns_nonzero(self, tmp_path):
        assert render(tmp_path) == 1
        assert not (tmp_path / "README.md").exists()

    def test_nonexistent_path_returns_nonzero(self, tmp_path):
        assert render(tmp_path / "does-not-exist") == 1
        assert not (tmp_path / "README.md").exists()


class TestReadmeContent:
    """The rendered README reflects the metadata document (RND-02, RND-03)."""

    def test_confirmed_column_renders_plain(self, tmp_path):
        col = ColumnMetadata(
            name="user_email",
            storage_type="categorical/text",
            semantic_type=_email_semantic(InferenceStatus.CONFIRMED, 0.98),
        )
        _write_metadata_yaml(tmp_path, _metadata(col))
        render(tmp_path)
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "| user_email | categorical/text | email | — |" in text
        assert "inferred" not in text

    def test_inferred_column_renders_with_confidence(self, tmp_path):
        col = ColumnMetadata(
            name="user_email",
            storage_type="categorical/text",
            semantic_type=_email_semantic(InferenceStatus.INFERRED, 0.78),
        )
        _write_metadata_yaml(tmp_path, _metadata(col))
        render(tmp_path)
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "email (inferred, 78%)" in text

    def test_unknown_column_renders_unknown_not_blank(self, tmp_path):
        col = ColumnMetadata(name="age", storage_type="numeric")
        _write_metadata_yaml(tmp_path, _metadata(col))
        render(tmp_path)
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "| age | numeric | unknown | — |" in text

    def test_unknown_human_fields_render_unknown(self, tmp_path):
        _write_metadata_yaml(tmp_path, _metadata())
        render(tmp_path)
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "| License | unknown |" in text
        assert "| Source | unknown |" in text

    def test_readme_reflects_metadata(self, tmp_path):
        col = ColumnMetadata(
            name="user_email",
            storage_type="categorical/text",
            semantic_type=_email_semantic(InferenceStatus.INFERRED, 0.72),
            pii=[PiiDetection(label="email", confidence=0.72)],
        )
        meta = _metadata(
            col,
            dataset=DatasetMetadata(
                name="contacts",
                description="Customer list",
                license="MIT",
                source="Acme",
            ),
        )
        _write_metadata_yaml(tmp_path, meta)
        render(tmp_path)
        text = (tmp_path / "README.md").read_text(encoding="utf-8")
        assert "# contacts" in text
        assert "Customer list" in text
        assert "MIT" in text
        assert "Acme" in text
        assert "email (inferred, 72%)" in text
        assert "possible_pii" in text


class TestRenderCli:
    """The ``render`` subcommand and handler wire up correctly (CLI-R03/R04)."""

    def test_render_subparser(self):
        args = cli._build_parser().parse_args(["render", "./build/"])
        assert args.command == "render"
        assert args.package == "./build/"
        assert args.output is None
        assert callable(args.func)

    def test_render_subparser_with_output(self):
        args = cli._build_parser().parse_args(["render", "metadata.yaml", "--output", "out/"])
        assert args.package == "metadata.yaml"
        assert args.output == "out/"

    def test_render_appears_in_help(self, capsys):
        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["--help"])
        assert "render" in capsys.readouterr().out

    def test_render_help_accurate(self, capsys):
        with pytest.raises(SystemExit):
            cli._build_parser().parse_args(["render", "--help"])
        out = capsys.readouterr().out
        assert "README.md" in out
        assert "metadata.yaml" in out

    def test_cmd_render_dispatches(self, tmp_path):
        _write_metadata_yaml(tmp_path, _metadata())
        rc = cli._cmd_render(Namespace(package=str(tmp_path), output=None))
        assert rc == 0
        assert (tmp_path / "README.md").exists()


# ---------------------------------------------------------------------------
#  RND-04 / RND-05 — batch + force guard (feat-profile-render-all-files)
# ---------------------------------------------------------------------------


def _write_dataset_toml_render(base, entries: list[str]):
    """Write a minimal dataset.toml under *base*."""
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


def _write_csv_render(path, rows=None):
    """Write a simple CSV for profile generation."""
    import csv as _csv

    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = _csv.writer(fh, delimiter=";")
        w.writerows(rows or [["col"], ["1"]])


class TestRenderBatchRnd04:
    """RND-04 batch render via --all-files."""

    def test_batch_n_renders(self, tmp_path, restore_tool_config):
        """Two files each with metadata.yaml -> two READMEs under renders/."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles
        from sofer.render import generate_all_renders

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        for name in ("a.csv", "b.csv"):
            _write_csv_render(tmp_path / "cache" / name)
        toml = _write_dataset_toml_render(tmp_path, ["cache/a.csv", "cache/b.csv"])
        ds_cfg = DatasetConfig.from_toml(toml)
        generate_all_profiles(ds_cfg)
        results = generate_all_renders(ds_cfg)

        assert (tmp_path / "cache" / "renders" / "a.README.md").is_file()
        assert (tmp_path / "cache" / "renders" / "b.README.md").is_file()
        assert len(results) == 2

    def test_collision_detection(self, tmp_path, restore_tool_config, capsys):
        """x.csv + x.parquet collide -> non-colliding written, ValueError."""
        import pyarrow as pa
        import pyarrow.parquet as pq

        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles
        from sofer.render import generate_all_renders

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        _write_csv_render(tmp_path / "cache" / "a.csv")
        _write_csv_render(tmp_path / "cache" / "x.csv")
        pq.write_table(pa.table({"col": ["1"]}), tmp_path / "cache" / "x.parquet")
        toml = _write_dataset_toml_render(
            tmp_path, ["cache/a.csv", "cache/x.csv", "cache/x.parquet"]
        )
        ds_cfg = DatasetConfig.from_toml(toml)
        # profile will collide for x files; catch and ensure a's metadata exists
        try:
            generate_all_profiles(ds_cfg)
        except ValueError:
            pass
        assert (tmp_path / "cache" / "profiles" / "a.metadata.yaml").is_file()
        # ensure colliding metadata exists so render can detect collision (both point to same file)
        # create a dummy metadata for x so both entries have a file to render from
        profiles_dir = tmp_path / "cache" / "profiles"
        profiles_dir.mkdir(parents=True, exist_ok=True)
        dummy = profiles_dir / "x.metadata.yaml"
        if not dummy.is_file():
            dummy.write_text("file:\n  path: x\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Collision"):
            generate_all_renders(ds_cfg)
        assert (tmp_path / "cache" / "renders" / "a.README.md").is_file()
        assert not (tmp_path / "cache" / "renders" / "x.README.md").is_file()
        err = capsys.readouterr().err
        assert "x.csv" in err and "x.parquet" in err

    def test_custom_output_absolute(self, tmp_path, restore_tool_config):
        """--output absolute -> renders under /tmp/out/renders, cache untouched."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles
        from sofer.render import generate_all_renders

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        _write_csv_render(tmp_path / "cache" / "a.csv")
        toml = _write_dataset_toml_render(tmp_path, ["cache/a.csv"])
        ds_cfg = DatasetConfig.from_toml(toml)
        out = tmp_path / "outAbs"
        generate_all_profiles(ds_cfg, output_dir=out)
        results = generate_all_renders(ds_cfg, output_dir=out)

        assert (out / "renders" / "a.README.md").is_file()
        assert str(out / "renders" / "a.README.md") in results
        assert not (tmp_path / "cache" / "renders").exists()

    def test_custom_output_relative_anchored(self, tmp_path, restore_tool_config, monkeypatch):
        """Relative --output anchors to base_dir (Option B)."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles
        from sofer.render import generate_all_renders

        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "cache").mkdir()
        _write_csv_render(proj / "cache" / "a.csv")
        toml = _write_dataset_toml_render(proj, ["cache/a.csv"])
        ds_cfg = DatasetConfig.from_toml(toml)
        cfg.reload(proj)
        other = tmp_path / "other"
        other.mkdir()
        monkeypatch.chdir(other)
        out_rel = "rel/out"
        generate_all_profiles(ds_cfg, output_dir=out_rel)
        generate_all_renders(ds_cfg, output_dir=out_rel)

        assert (proj / "rel" / "out" / "renders" / "a.README.md").is_file()
        assert not (other / "rel" / "out" / "renders" / "a.README.md").exists()

    def test_config_override_docs_renders(self, tmp_path, restore_tool_config):
        """render_dir=docs/renders -> outputs under docs/renders/."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles
        from sofer.render import generate_all_renders

        (tmp_path / "pyproject.toml").write_text(
            '[tool.sofer]\nrender_dir = "docs/renders"\n', encoding="utf-8"
        )
        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        _write_csv_render(tmp_path / "cache" / "a.csv")
        toml = _write_dataset_toml_render(tmp_path, ["cache/a.csv"])
        ds_cfg = DatasetConfig.from_toml(toml)
        generate_all_profiles(ds_cfg)
        generate_all_renders(ds_cfg)

        assert (tmp_path / "cache" / "docs" / "renders" / "a.README.md").is_file()

    def test_toml_without_files_fails_via_cli(self, tmp_path, capsys):
        """CLI --all-files with no [[file]] exits non-zero."""
        toml = tmp_path / "dataset.toml"
        toml.write_text('[dataset]\nname = "x"\nrepo_id = "u/x"\n', encoding="utf-8")
        rc = cli._cmd_render(
            Namespace(package=str(toml), output=None, all_files=True, force=False, config=str(toml))
        )
        assert rc == 1
        assert "[[file]]" in capsys.readouterr().err

    def test_skip_missing_metadata(self, tmp_path, restore_tool_config, capsys):
        """Entries without metadata.yaml are skipped, others still render."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles
        from sofer.render import generate_all_renders

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        _write_csv_render(tmp_path / "cache" / "a.csv")
        _write_csv_render(tmp_path / "cache" / "b.csv")
        toml = _write_dataset_toml_render(tmp_path, ["cache/a.csv", "cache/b.csv"])
        ds_cfg = DatasetConfig.from_toml(toml)
        # only profile a, not b
        generate_all_profiles(ds_cfg)
        # delete b's metadata if it was created? Actually generate_all_profiles created both,
        # so remove one to simulate missing
        (tmp_path / "cache" / "profiles" / "b.metadata.yaml").unlink()
        results = generate_all_renders(ds_cfg)

        assert (tmp_path / "cache" / "renders" / "a.README.md").is_file()
        assert not (tmp_path / "cache" / "renders" / "b.README.md").is_file()
        assert len(results) == 1
        assert "missing metadata" in capsys.readouterr().err.lower()


class TestRenderForceGuardRnd05:
    """RND-05 single-file force guard."""

    def test_guard_without_force_raises(self, tmp_path):
        """Existing README without --force raises FileExistsError with hint."""
        _write_metadata_yaml(tmp_path, _metadata())
        assert render(tmp_path, force=False) == 0
        dest = tmp_path / "README.md"
        dest.write_text("tampered", encoding="utf-8")
        with pytest.raises(FileExistsError, match="use --force to overwrite"):
            render(tmp_path, force=False)
        assert dest.read_text(encoding="utf-8") == "tampered"

    def test_overwrite_with_force(self, tmp_path):
        """With --force the file is overwritten and exit 0."""
        _write_metadata_yaml(tmp_path, _metadata())
        render(tmp_path, force=False)
        dest = tmp_path / "README.md"
        dest.write_text("tampered", encoding="utf-8")
        assert render(tmp_path, force=True) == 0
        assert dest.read_text(encoding="utf-8") != "tampered"

    def test_cli_guard_without_force_returns_1(self, tmp_path, capsys):
        """CLI render without --force on existing dest returns 1."""
        _write_metadata_yaml(tmp_path, _metadata())
        rc1 = cli._cmd_render(Namespace(package=str(tmp_path), output=None, force=False))
        assert rc1 == 0
        rc2 = cli._cmd_render(Namespace(package=str(tmp_path), output=None, force=False))
        assert rc2 == 1
        assert "use --force to overwrite" in capsys.readouterr().err

    def test_cli_overwrite_with_force(self, tmp_path):
        """CLI render --force overwrites."""
        _write_metadata_yaml(tmp_path, _metadata())
        cli._cmd_render(Namespace(package=str(tmp_path), output=None, force=False))
        dest = tmp_path / "README.md"
        dest.write_text("tampered", encoding="utf-8")
        rc = cli._cmd_render(Namespace(package=str(tmp_path), output=None, force=True))
        assert rc == 0
        assert dest.read_text(encoding="utf-8") != "tampered"


# ---------------------------------------------------------------------------
#  Multisheet 1:N (fix/multisheet-profile-render) — RND-04 parity
# ---------------------------------------------------------------------------


def _make_xlsx_render(path, sheets: dict[str, list[list[object]]]):
    """Create an .xlsx at *path* with *sheets* mapping sheet_name -> rows."""
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


class TestRenderMultisheetRnd04:
    """RND-04 multisheet 1:N parity — 2 READMEs, sanitize, dedup."""

    def test_multisheet_workbook_2_sheets_yields_2_readmes(self, tmp_path, restore_tool_config):
        """report.xlsx Sales/Inventory -> 2 READMEs per-sheet."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles
        from sofer.render import generate_all_renders

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        xlsx = tmp_path / "cache" / "report.xlsx"
        _make_xlsx_render(
            xlsx,
            {
                "Sales": [["id", "amount"], [1, 10], [2, 20]],
                "Inventory": [["sku", "qty"], ["A1", 5]],
            },
        )
        toml = _write_dataset_toml_render(tmp_path, ["cache/report.xlsx"])
        ds_cfg = DatasetConfig.from_toml(toml)
        generate_all_profiles(ds_cfg)
        results = generate_all_renders(ds_cfg)

        sales_readme = tmp_path / "cache" / "renders" / "report__sales.README.md"
        inv_readme = tmp_path / "cache" / "renders" / "report__inventory.README.md"
        assert sales_readme.is_file(), results
        assert inv_readme.is_file()
        assert len(results) == 2
        sales_text = sales_readme.read_text(encoding="utf-8")
        inv_text = inv_readme.read_text(encoding="utf-8")
        assert "id" in sales_text and "amount" in sales_text
        assert "sku" in inv_text and "qty" in inv_text
        # each README renders only its sheet's schema
        assert "sku" not in sales_text
        assert "amount" not in inv_text

    def test_single_sheet_xlsx_stays_suffix_less(self, tmp_path, restore_tool_config):
        """Single-sheet xlsx stays renders/<stem>.README.md (no __sheet)."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles
        from sofer.render import generate_all_renders

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        xlsx = tmp_path / "cache" / "single.xlsx"
        _make_xlsx_render(xlsx, {"Data": [["id", "val"], [1, "a"]]})
        toml = _write_dataset_toml_render(tmp_path, ["cache/single.xlsx"])
        ds_cfg = DatasetConfig.from_toml(toml)
        generate_all_profiles(ds_cfg)
        results = generate_all_renders(ds_cfg)

        expected = tmp_path / "cache" / "renders" / "single.README.md"
        assert expected.is_file()
        assert len(results) == 1
        assert str(expected) in results
        assert not (tmp_path / "cache" / "renders" / "single__data.README.md").exists()

    def test_sanitize_sheet_name_parity(self, restore_tool_config):
        """sanitize_sheet_name parity with profile (DATA GOT Año->data_got_ano, ''->sheet)."""
        from sofer._converters import sanitize_sheet_name

        assert sanitize_sheet_name("DATA GOT Año") == "data_got_ano"
        assert sanitize_sheet_name("") == "sheet"
        assert sanitize_sheet_name("   ") == "sheet"
        # dedup parity checked via dedup test

    def test_dedup_preserved(self, tmp_path, restore_tool_config):
        """Ventas variants -> dedup __ventas, __ventas_2, __ventas_3."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles
        from sofer.render import generate_all_renders

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        xlsx = tmp_path / "cache" / "dedup.xlsx"
        _make_xlsx_render(
            xlsx,
            {
                "Ventas": [["id"], [1]],
                "Ventas ": [["id"], [2]],
                "Ventas  ": [["id"], [3]],
            },
        )
        toml = _write_dataset_toml_render(tmp_path, ["cache/dedup.xlsx"])
        ds_cfg = DatasetConfig.from_toml(toml)
        generate_all_profiles(ds_cfg)
        generate_all_renders(ds_cfg)

        assert (tmp_path / "cache" / "renders" / "dedup__ventas.README.md").is_file()
        assert (tmp_path / "cache" / "renders" / "dedup__ventas_2.README.md").is_file()
        assert (tmp_path / "cache" / "renders" / "dedup__ventas_3.README.md").is_file()

    def test_sheet_aware_collision_normalized(self, tmp_path, restore_tool_config, capsys):
        """a__ventas vs a_ventas normalized collision."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles
        from sofer.render import generate_all_renders

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir()
        xlsx = tmp_path / "cache" / "a__ventas.xlsx"
        _make_xlsx_render(xlsx, {"Ventas": [["id"], [1]]})
        _write_csv_render(tmp_path / "cache" / "a_ventas.csv", [["id"], ["9"]])
        _write_csv_render(tmp_path / "cache" / "ok.csv", [["col"], ["1"]])
        toml = _write_dataset_toml_render(
            tmp_path, ["cache/a__ventas.xlsx", "cache/a_ventas.csv", "cache/ok.csv"]
        )
        ds_cfg = DatasetConfig.from_toml(toml)
        # profile creates collision already (partial write)
        try:
            generate_all_profiles(ds_cfg)
        except ValueError:
            pass
        capsys.readouterr()
        assert (tmp_path / "cache" / "profiles" / "ok.metadata.yaml").is_file()

        with pytest.raises(ValueError, match="Collision"):
            generate_all_renders(ds_cfg)

        assert (tmp_path / "cache" / "renders" / "ok.README.md").is_file()
        assert not (tmp_path / "cache" / "renders" / "a_ventas.README.md").is_file()
        assert not (tmp_path / "cache" / "renders" / "a__ventas.README.md").is_file()
        err = capsys.readouterr().err
        assert "a__ventas.xlsx" in err
        assert "a_ventas.csv" in err
        assert "::ventas" in err.lower()

    def test_custom_output_relative_anchored_multisheet(
        self, tmp_path, restore_tool_config, monkeypatch
    ):
        """Relative --output anchored to base_dir (Option B)."""
        import sofer.config as cfg
        from sofer.model import DatasetConfig
        from sofer.profile import generate_all_profiles
        from sofer.render import generate_all_renders

        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "cache").mkdir()
        xlsx = proj / "cache" / "report.xlsx"
        _make_xlsx_render(
            xlsx,
            {
                "Sales": [["id", "amount"], [1, 10]],
                "Inventory": [["sku", "qty"], ["A1", 5]],
            },
        )
        toml = _write_dataset_toml_render(proj, ["cache/report.xlsx"])
        ds_cfg = DatasetConfig.from_toml(toml)
        cfg.reload(proj)
        other = tmp_path / "other"
        other.mkdir()
        monkeypatch.chdir(other)

        generate_all_profiles(ds_cfg, output_dir="rel/out")
        generate_all_renders(ds_cfg, output_dir="rel/out")

        assert (proj / "rel" / "out" / "renders" / "report__sales.README.md").is_file()
        assert (proj / "rel" / "out" / "renders" / "report__inventory.README.md").is_file()
        assert not (other / "rel").exists()

    def test_mcp_containment_render_dir(self, tmp_path, restore_tool_config):
        """_validate_output_targets must flag escaping render_dir."""
        from sofer.mcp_server import _validate_output_targets
        from sofer.model import DatasetConfig

        (tmp_path / "pyproject.toml").write_text(
            '[tool.sofer]\nrender_dir = "../../evil"\n', encoding="utf-8"
        )
        import sofer.config as cfg

        cfg.reload(tmp_path)
        (tmp_path / "cache").mkdir(exist_ok=True)
        _write_csv_render(tmp_path / "cache" / "a.csv")
        toml = _write_dataset_toml_render(tmp_path, ["cache/a.csv"])
        ds_cfg = DatasetConfig.from_toml(toml)

        errors = _validate_output_targets(ds_cfg, root=tmp_path)
        assert any("render_dir" in e and "outside the server root" in e for e in errors)

    def test_render_output_helper_suffixes(self, tmp_path):
        """_render_output_for_rel mirrors PurePath.suffixes handling."""
        from sofer.render import _render_output_for_rel

        out = _render_output_for_rel(tmp_path / "renders", tmp_path / "a.b", None)
        assert out.name == "a.README.md"
        out2 = _render_output_for_rel(tmp_path / "renders", tmp_path / "a.b", "ventas")
        assert out2.name == "a__ventas.README.md"

    def test_normalize_render_collision_key(self):
        """_normalize_render_collision_key collapses __+."""
        from pathlib import Path

        from sofer.render import _normalize_render_collision_key

        assert _normalize_render_collision_key(Path("a__ventas.README.md")) == "a_ventas.README.md"
