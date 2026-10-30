"""Relative artifact stems shared by the batch documentation generators.

``profile``, ``codebook`` and ``render`` each mirror declared sources into
``<write_root>/<artifact_dir>/<rel-stem>.*``. The stem is the source path
relative to ``cache/`` when the source lives there, otherwise relative to the
config directory (``cfg._base_dir``).

A source that exists inside the containment root but **outside** the config
directory cannot be expressed by that layout. Until issue #397 the three
generators asked ``Path.relative_to`` anyway; the resulting ``ValueError``
escaped to the adapters, which caught every ``ValueError`` as a collision and
reported "Collision in … outputs" for a config with a single source. This
module gives that condition its own type and an actionable message, so the
adapters can name the real problem without inventing a layout contract the
project has not agreed to (issue #397 leaves sibling-source support as a
separate decision).
"""

from __future__ import annotations

from pathlib import Path


class SourceLayoutError(ValueError):
    """A declared source lives under neither ``cache/`` nor the config directory.

    Subclasses :class:`ValueError` so the CLI handlers (which already turn a
    ``ValueError`` into ``Error: <message>`` plus exit 1) keep working without
    a special case, while the MCP adapters check this type first and report the
    real cause instead of the collision diagnosis.

    Attributes:
        source: The resolved source path that could not be named.
        base_dir: The config directory the artifact layout is anchored on.
    """

    def __init__(self, source: Path, base_dir: Path) -> None:
        self.source = source
        self.base_dir = base_dir
        super().__init__(
            f"Source layout not supported: {source} is outside the dataset "
            f"directory {base_dir}. Batch artifacts mirror each source "
            f"relative to that directory, so a source kept elsewhere (even "
            f"inside the server root) cannot be named. Move the file under "
            f"{base_dir} and update its [[file]] local entry."
        )


def rel_stem(local: Path, *, base_dir: Path, data_dir: Path) -> Path:
    """Return *local*'s artifact stem, relative to ``cache/`` or the config dir.

    Args:
        local: Resolved source path.
        base_dir: The config directory (``cfg._base_dir``).
        data_dir: The artifact cache directory (``base_dir / config.OUTPUT_DIR``).

    Returns:
        ``local`` relative to *data_dir* when it lives under the cache, else
        relative to *base_dir*.

    Raises:
        SourceLayoutError: When *local* is under neither directory, which the
            artifact layout cannot express.
    """
    if local.is_relative_to(data_dir):
        return local.relative_to(data_dir)
    if local.is_relative_to(base_dir):
        return local.relative_to(base_dir)
    raise SourceLayoutError(local, base_dir)
