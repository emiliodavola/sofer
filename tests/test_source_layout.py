"""Issue #397 — a source outside the config directory is a layout error.

A declared source that lives inside the containment root but outside the
config directory cannot be named by the batch artifact layout. The three
documentation generators used to let ``Path.relative_to`` raise a bare
``ValueError``, which the adapters reported as "Collision in … outputs" for a
config holding a single source. These tests pin the honest diagnosis and the
control that still works.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sofer._layout import SourceLayoutError, rel_stem
from sofer.codebook import generate_all_result as codebook_all
from sofer.model import DatasetConfig, FileEntry
from sofer.profile import generate_all_profiles_result as profile_all
from sofer.render import generate_all_renders as render_all


def _sibling_cfg(root, *, local: str = "../shared/input.csv") -> DatasetConfig:
    """Build a config anchored at ``root/config`` whose source may live outside it."""
    (root / "shared").mkdir(parents=True, exist_ok=True)
    (root / "shared" / "input.csv").write_text("a;b\n1;2\n", encoding="utf-8")
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "raw").mkdir(exist_ok=True)
    (root / "config" / "raw" / "input.csv").write_text("a;b\n1;2\n", encoding="utf-8")
    return DatasetConfig(
        name="sibling",
        repo_id="user/sibling",
        files=[FileEntry(local=Path(local), remote="input.csv")],
        _base_dir=root / "config",
    )


class TestRelStem:
    def test_cache_relative(self, tmp_path) -> None:
        """A source under ``cache/`` keeps its cache-relative stem."""
        cache = tmp_path / "cache"
        cache.mkdir()
        source = cache / "data.csv"
        source.write_text("a\n1\n", encoding="utf-8")

        assert rel_stem(source, base_dir=tmp_path, data_dir=cache) == source.relative_to(cache)

    def test_config_relative(self, tmp_path) -> None:
        """A source under the config directory is named relative to it."""
        source = tmp_path / "raw" / "data.csv"
        source.parent.mkdir()
        source.write_text("a\n1\n", encoding="utf-8")

        assert rel_stem(source, base_dir=tmp_path, data_dir=tmp_path / "cache") == (
            source.relative_to(tmp_path)
        )

    def test_outside_both_raises(self, tmp_path) -> None:
        """A source in neither directory raises the typed layout error."""
        source = tmp_path / "shared" / "data.csv"
        source.parent.mkdir()
        source.write_text("a\n1\n", encoding="utf-8")

        with pytest.raises(SourceLayoutError) as exc_info:
            rel_stem(source, base_dir=tmp_path / "config", data_dir=tmp_path / "config" / "cache")

        assert isinstance(exc_info.value, ValueError)
        assert exc_info.value.source == source
        assert exc_info.value.base_dir == tmp_path / "config"


class TestGeneratorsRejectSiblingSource:
    """Every batch generator names the layout problem instead of a collision."""

    @pytest.mark.parametrize(
        "generate",
        [profile_all, codebook_all, render_all],
        ids=["profile", "codebook", "render"],
    )
    def test_sibling_source_is_a_layout_error(self, tmp_path, generate) -> None:
        cfg = _sibling_cfg(tmp_path)
        source = (tmp_path / "config" / ".." / "shared" / "input.csv").resolve()

        with pytest.raises(SourceLayoutError) as exc_info:
            generate(cfg, output_dir=tmp_path / "build")

        message = str(exc_info.value)
        assert "Source layout not supported" in message
        assert str(source) in message
        assert str((tmp_path / "config").resolve()) in message
        assert "collision" not in message.lower()

    @pytest.mark.parametrize(
        "generate",
        [profile_all, codebook_all, render_all],
        ids=["profile", "codebook", "render"],
    )
    def test_source_under_the_config_dir_still_works(self, tmp_path, generate) -> None:
        cfg = _sibling_cfg(tmp_path, local="raw/input.csv")

        # render needs a profile first; the point here is that the stem resolves.
        if generate is render_all:
            profile_all(cfg, output_dir=tmp_path / "build")
        generated = generate(cfg, output_dir=tmp_path / "build")

        if generate is profile_all:
            assert len(generated.files) == 1
        else:
            assert generated
