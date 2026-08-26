"""Packaging and release-readiness tests (PKG-01..PKG-05, CLI-R05, CLI-R06).

These tests verify the distribution contract end-to-end: the runtime version
resolver never returns an empty or non-PEP-440 value, no static version literal
exists anywhere (PKG-01), ``uv build`` produces a complete wheel (PKG-02,
PKG-03), and the installed console script runs standalone (PKG-03, CLI-R05).

Build and install steps shell out to ``uv``. The first ``uv build`` run is NOT
network-free: build isolation fetches the build backends (hatch-vcs) from the
index, and uv caches them afterwards. The installed-CLI test installs the wheel
with ``--no-deps`` and reuses the project venv's site-packages through a
``.pth`` indirection, so no dependency resolution is involved for the runtime
check itself.
"""

from __future__ import annotations

import os
import re
import subprocess
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
