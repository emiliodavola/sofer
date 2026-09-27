"""Packaging and release-readiness tests (PKG-01..PKG-05, CLI-R05, CLI-R06).

These tests verify the distribution contract end-to-end: the runtime version
resolver never returns an empty or non-PEP-440 value, no static version literal
exists anywhere (PKG-01), ``uv build`` produces a complete wheel (PKG-02,
PKG-03), the installed console script runs standalone (PKG-03, CLI-R05), and both
READMEs document the git-tag install paths (PKG-05).

Build and install steps shell out to ``uv``. The first ``uv build`` run is NOT
network-free: build isolation fetches the build backends (hatch-vcs) from the
index, and uv caches them afterwards. The installed-CLI test installs the wheel
with ``--no-deps`` and reuses the project venv's site-packages through a
``.pth`` indirection, so no dependency resolution is involved for the runtime
check itself.
"""

from __future__ import annotations

import importlib
import os
import re
import subprocess
import sys
import sysconfig
import zipfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Simplified PEP 440 regex (spec appendix): release segments, optional
# pre/post/dev segments, optional local label. Used to assert the resolved
# version is PEP 440-valid without hardcoding any specific version.
_PEP440_RE = re.compile(
    r"^"
    r"(?:0|[1-9]\d*)"
    r"(?:\.(?:0|[1-9]\d*))*"
    r"(?:[ab]|rc(?:0|[1-9]\d*))?"
    r"(?:\.post(?:0|[1-9]\d*))?"
    r"(?:\.dev(?:0|[1-9]\d*))?"
    r"(?:\+[a-z0-9]+(?:[-._][a-z0-9]+)*)?"
    r"$",
    re.IGNORECASE,
)


def _run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a subprocess, failing the test loudly on a non-zero exit."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, (
        f"command failed ({result.returncode}): {' '.join(cmd)}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result


# The fastmcp runtime cap is declared in `pyproject.toml` (the dependency, the
# `mcp` extra alias, and the dev group) and named by the packaging and mcp-server
# specs, `CONTRIBUTING.md`, and `.github/dependabot.yml`. This guard derives the
# cap from `pyproject.toml` so every prose home must agree with the shipped
# declaration and the retired `>=3.4,<4` cap cannot silently return (issue #257).
_FASTMCP_CAP_RE = re.compile(r"fastmcp(?P<cap>>=[0-9][0-9A-Za-z.\-]*,\s*<[0-9][0-9A-Za-z.\-]*)")


def test_fastmcp_cap_is_single_across_declaration_homes():
    """Issue #257: one fastmcp cap, and every declaring home names it."""
    pyproject = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    caps = set(_FASTMCP_CAP_RE.findall(pyproject))
    assert caps, "pyproject.toml declares no fastmcp requirement"
    assert len(caps) == 1, f"pyproject.toml must declare one fastmcp cap, got {sorted(caps)}"
    cap = caps.pop()
    upper = cap.rsplit(",", 1)[-1]  # e.g. "<5"

    prose_homes = (
        "openspec/specs/packaging/spec.md",
        "openspec/specs/mcp-server/spec.md",
    )
    for rel in prose_homes:
        text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        assert f"fastmcp{cap}" in text, (
            f"{rel} must name the declared fastmcp cap fastmcp{cap} (issue #257)"
        )
        other = set(_FASTMCP_CAP_RE.findall(text)) - {cap}
        assert not other, (
            f"{rel} names another fastmcp cap besides the declared {cap}: "
            f"{sorted(other)} (issue #257)"
        )

    stale = "fastmcp>=3.4,<4"
    for rel in (*prose_homes, "CONTRIBUTING.md", ".github/dependabot.yml"):
        text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        assert stale not in text, f"{rel} still names the retired fastmcp cap {stale} (issue #257)"
    for rel in ("CONTRIBUTING.md", ".github/dependabot.yml"):
        text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        assert f"`{upper}`" in text, (
            f"{rel} must name the declared fastmcp upper bound `{upper}` (issue #257)"
        )
        assert "`<4`" not in text, f"{rel} still calls the fastmcp cap `<4` (issue #257)"


# ── PKG-05 install documentation ────────────────────────────────────────────
# The documented install paths are git-tag installs because no PyPI project is
# published (AGENTS.md rule 12). The repository URL is derived from
# `[project.urls] Homepage`, so a repository move needs no test edit.
_README_TAG_PLACEHOLDER = "vX.Y.Z"

# A bare PyPI install: `pip install sofer` / `uv tool install sofer`. The
# lookaheads exclude the two legitimate git-tag forms — `sofer[...]` (the extra
# alias) and `sofer @ git+...` (the PEP 508 direct reference).
_RETIRED_INSTALL_RE = re.compile(r"(?:pip3?|uv\s+tool)\s+install\s+['\"]?sofer(?!\[)(?!\s*@)")


def _project_homepage() -> str:
    """Return the ``[project.urls] Homepage`` URL from ``pyproject.toml``."""
    parser = importlib.import_module("tomllib" if sys.version_info >= (3, 11) else "tomli")
    document = parser.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return document["project"]["urls"]["Homepage"]


def _documented_git_tag_commands() -> tuple[str, ...]:
    """Return the four install commands PKG-05 requires, derived from the homepage URL."""
    git_url = f"git+{_project_homepage().rstrip('/')}.git"
    tag = _README_TAG_PLACEHOLDER
    return (
        f'uv tool install "sofer @ {git_url}@{tag}" --force',
        f'pip install "sofer @ {git_url}@{tag}"',
        f'pip install "sofer[mcp] @ {git_url}@{tag}"',
        f'uvx --from {git_url}@{tag} --with "sofer[mcp]" sofer-mcp --help',
    )


def test_readme_documents_the_git_tag_install_paths():
    """PKG-05: both READMEs document the git-tag install commands, no bare PyPI path."""
    commands = _documented_git_tag_commands()
    for rel in ("README.md", "README_ES.md"):
        text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        for command in commands:
            assert command in text, f"{rel} must document `{command}` (PKG-05)"
        assert _RETIRED_INSTALL_RE.search(text) is None, (
            f"{rel} must not document a bare `pip install sofer` / "
            "`uv tool install sofer` — no PyPI project exists (PKG-05, issue #259)"
        )


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the distribution once per module with ``uv build``.

    The first run in a fresh cache needs network for build isolation
    (hatch-vcs / build backends); uv caches those dependencies afterwards.
    """
    dist_dir = tmp_path_factory.mktemp("dist")
    _run(["uv", "build", "--out-dir", str(dist_dir)], cwd=_REPO_ROOT)
    wheels = sorted(dist_dir.glob("sofer-*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, got {wheels}"
    return wheels[0]


class TestVersionResolver:
    """The runtime resolver returns a non-empty, PEP 440-valid version (PKG-04)."""

    def test_resolved_version_is_non_empty_and_pep440(self):
        from sofer._version import get_version

        version = get_version()
        assert version
        assert _PEP440_RE.match(version)

    def test_fallback_sentinel_when_metadata_unavailable(self, monkeypatch):
        """Without installed metadata the resolver returns its sentinel (PKG-01)."""
        import importlib.metadata

        import sofer._version as version_module

        def _raise(*args: object, **kwargs: object) -> str:
            raise importlib.metadata.PackageNotFoundError("sofer")

        monkeypatch.setattr(version_module.importlib.metadata, "version", _raise)
        version_module.get_version.cache_clear()
        try:
            version = version_module.get_version()
        finally:
            version_module.get_version.cache_clear()
        assert version == version_module._UNKNOWN_VERSION
        assert version
        assert _PEP440_RE.match(version)


class TestNoStaticVersionLiteral:
    """No static version literal exists in pyproject or package source (PKG-01, CLI-R06)."""

    def test_pyproject_declares_dynamic_version(self):
        text = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert 'dynamic = ["version"]' in text
        assert re.search(r"^version\s*=", text, re.MULTILINE) is None

    def test_no_version_constant_in_package_source(self):
        for path in sorted((_REPO_ROOT / "src").rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            assert re.search(r"^\s*__version__\s*=", text, re.MULTILINE) is None, path


class TestBuildSmoke:
    """The wheel is complete and exposes the console script (PKG-02, PKG-03)."""

    def test_wheel_contains_entry_point(self, built_wheel):
        with zipfile.ZipFile(built_wheel) as wheel:
            entry_points = next(
                name for name in wheel.namelist() if name.endswith("entry_points.txt")
            )
            assert "sofer = sofer.cli:main" in wheel.read(entry_points).decode("utf-8")

    def test_wheel_metadata_is_complete(self, built_wheel):
        with zipfile.ZipFile(built_wheel) as wheel:
            metadata = next(
                name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")
            )
            text = wheel.read(metadata).decode("utf-8")
        assert re.search(r"^Classifier:", text, re.MULTILINE)
        assert re.search(r"^Project-URL:", text, re.MULTILINE)


class TestInstalledCli:
    """The wheel's console script runs standalone without ``uv run`` (PKG-03, CLI-R05)."""

    def test_console_script_help_and_version(self, built_wheel, tmp_path):
        venv_dir = tmp_path / "venv"
        _run(["uv", "venv", str(venv_dir)])
        python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        _run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                "--no-deps",
                str(built_wheel),
            ]
        )

        # .pth indirection: expose the project venv's deps to the fresh venv.
        # (uv venv --system-site-packages would de-reference the interpreter
        # and expose empty site-packages, so sofer would crash on import.)
        purelib_out = _run(
            [str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"]
        ).stdout.strip()
        (Path(purelib_out) / "sofer_project_deps.pth").write_text(
            sysconfig.get_path("purelib") + "\n", encoding="utf-8"
        )

        console = venv_dir / ("Scripts/sofer.exe" if os.name == "nt" else "bin/sofer")
        _run([str(console), "--help"])
        version_out = _run([str(console), "--version"]).stdout.strip()
        assert version_out
        assert version_out.startswith("sofer v")
