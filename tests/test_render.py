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
