"""Runtime resolution of the sofer distribution version.

Single source for ``sofer --version`` and the version stamped into generated
documents (``generated.version``). The distribution version is derived from
the git release tag by hatch-vcs at build time; this module resolves it at
runtime. Never raises, never returns an empty string.

The fallback is intentionally NOT a reproduction of hatch-vcs. Actual
hatch-vcs shapes (verified on built wheels): off-tag ``NEXT.devN+g<sha>``
(v0.3.0 + 1 commit ships ``0.3.1.dev1+g<sha>``); zero-tag ``0.1.devN+g<sha>``
(a checkout with no reachable tags). A bare-tree run therefore does NOT
report what a build at that commit would ship — only installed metadata is
authoritative. The fallback is a marker, never compared against wheel output.
"""

from __future__ import annotations

import importlib.metadata
from functools import lru_cache

# Distribution name registered in pyproject.toml [project] — a name, not a version.
_DISTRIBUTION_NAME = "sofer"
# Marker for environments with no version signal (not installed). This is NOT
# the distribution version — it is an "unknown build" sentinel in the
# setuptools-scm convention; tests never compare against it (PKG-04).
_UNKNOWN_VERSION = "0.0.0.dev0"


@lru_cache(maxsize=1)
def get_version() -> str:
    """Return the sofer version: non-empty and PEP 440-valid, never raises.

    Resolution order:
      1. Installed distribution metadata (importlib.metadata) — the
         hatch-vcs-derived version stamped at build/install time. Covers
         released wheels (tag) and editable installs (dev version).
      2. ``_UNKNOWN_VERSION`` when the distribution is not installed (bare
         source tree or signal-less environment) — a deterministic marker,
         not a claim about what a build would ship.

    Returns:
        The resolved version string.
    """
    try:
        return importlib.metadata.version(_DISTRIBUTION_NAME)
    except importlib.metadata.PackageNotFoundError:
        return _UNKNOWN_VERSION
