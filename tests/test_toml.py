"""Central TOML helpers: parser selection (issue #192) and the atomic writer.

Both parser arms are covered on any interpreter: the ``except`` branch is
reached by blocking stdlib ``tomllib`` in ``sys.modules`` and injecting a
fake ``tomli`` backport, so the coverage gate never depends on which Python
runs the suite.

The writer's staging policy is pinned here (issue #365): it may change the
destination and the temporary file it creates exclusively, never the
predictable ``<destination>.tmp`` sibling that may already belong to the user
or to another writer.
"""

from __future__ import annotations

import io
import os
import stat
import sys
import types
from pathlib import Path

import pytest

from sofer import _toml


def _link_file(link: Path, target: Path) -> bool:
    """Create *link* pointing at *target*; return ``False`` when unsupported.

    ``os.symlink`` requires Developer Mode or an elevated process on Windows,
    so the symlink cases skip there instead of failing the suite. The
    platform-independent staging assertions still cover the policy.
    """
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        return False
    return True


def test_load_parses_toml_with_stdlib_parser() -> None:
    data = _toml.load(io.BytesIO(b"[tool.sofer]\nfoo = 1\n"))
    assert data == {"tool": {"sofer": {"foo": 1}}}


def test_load_falls_back_to_tomli_backport(monkeypatch) -> None:
    fake = types.ModuleType("tomli")
    fake.load = lambda fp: {"backport": True}  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tomli", fake)
    # `None` makes `import tomllib` raise ImportError.
    monkeypatch.setitem(sys.modules, "tomllib", None)
    assert _toml.load(io.BytesIO(b"ignored")) == {"backport": True}


class TestAtomicWriteText:
    """``atomic_write_text`` changes the destination and its own temp file only."""

    def test_a_preexisting_regular_tmp_sibling_is_left_untouched(self, tmp_path: Path) -> None:
        destination = tmp_path / "dataset.toml"
        sibling = tmp_path / "dataset.toml.tmp"
        destination.write_text("original config", encoding="utf-8")
        sibling.write_text("pre-existing staging file", encoding="utf-8")

        _toml.atomic_write_text(destination, "updated config")

        assert sibling.read_text(encoding="utf-8") == "pre-existing staging file"
        assert destination.read_text(encoding="utf-8") == "updated config"
        assert not destination.is_symlink()

    def test_a_preexisting_tmp_symlink_and_its_target_are_untouched(self, tmp_path: Path) -> None:
        destination = tmp_path / "dataset.toml"
        unrelated = tmp_path / "unrelated.txt"
        link = tmp_path / "dataset.toml.tmp"
        destination.write_text("original config", encoding="utf-8")
        unrelated.write_text("must not change", encoding="utf-8")
        if not _link_file(link, unrelated):
            pytest.skip("symlink creation unavailable on this host")

        _toml.atomic_write_text(destination, "updated config")

        assert unrelated.read_text(encoding="utf-8") == "must not change"
        assert link.is_symlink()
        assert not destination.is_symlink()
        assert destination.read_text(encoding="utf-8") == "updated config"

    def test_a_failed_replace_preserves_the_destination_and_the_sibling(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        destination = tmp_path / "dataset.toml"
        sibling = tmp_path / "dataset.toml.tmp"
        destination.write_bytes(b"original config")
        sibling.write_bytes(b"pre-existing staging file")

        def _boom(*args: object, **kwargs: object) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(_toml.os, "replace", _boom)
        with pytest.raises(OSError, match="disk full"):
            _toml.atomic_write_text(destination, "updated config")

        assert destination.read_bytes() == b"original config"
        assert sibling.read_bytes() == b"pre-existing staging file"
        # Nothing else survives: the call removed the temporary file it created.
        assert sorted(item.name for item in tmp_path.iterdir()) == [
            "dataset.toml",
            "dataset.toml.tmp",
        ]

    def test_separate_invocations_use_distinct_staging_names(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        destination = tmp_path / "dataset.toml"
        destination.write_text("first", encoding="utf-8")
        staged: list[Path] = []
        real_replace = os.replace

        def _record(source: str | os.PathLike[str], target: str | os.PathLike[str]) -> None:
            staged.append(Path(source))
            real_replace(source, target)

        monkeypatch.setattr(_toml.os, "replace", _record)
        _toml.atomic_write_text(destination, "one")
        _toml.atomic_write_text(destination, "two")

        assert len(staged) == 2
        assert staged[0] != staged[1]
        assert all(path.name != "dataset.toml.tmp" for path in staged)
        # A staging file outside the destination's directory would make the
        # replacement cross-device (EXDEV) on a split mount.
        assert all(path.parent == destination.parent for path in staged)

    def test_a_refused_chmod_does_not_abort_the_write(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Some SMB/FUSE mounts refuse chmod; the write must still land."""
        destination = tmp_path / "dataset.toml"
        destination.write_text("old", encoding="utf-8")

        def _refuse(*args: object, **kwargs: object) -> None:
            raise PermissionError("operation not permitted")

        monkeypatch.setattr(_toml.os, "chmod", _refuse)
        _toml.atomic_write_text(destination, "new")

        assert destination.read_text(encoding="utf-8") == "new"

    def test_a_non_oserror_failure_leaves_no_staging_file(self, tmp_path: Path) -> None:
        """An encoding failure is not an OSError, and must not orphan a file."""
        destination = tmp_path / "dataset.toml"
        destination.write_text("old", encoding="utf-8")

        with pytest.raises(UnicodeEncodeError):
            _toml.atomic_write_text(destination, "\ud800", encoding="utf-8")

        assert destination.read_text(encoding="utf-8") == "old"
        assert sorted(item.name for item in tmp_path.iterdir()) == ["dataset.toml"]

    def test_crlf_bytes_and_the_encoding_are_preserved(self, tmp_path: Path) -> None:
        destination = tmp_path / "dataset.toml"

        _toml.atomic_write_text(destination, 'a = "1"\r\nb = "2"\r\n', encoding="utf-8")

        assert destination.read_bytes() == b'a = "1"\r\nb = "2"\r\n'

    def test_a_new_destination_is_created(self, tmp_path: Path) -> None:
        destination = tmp_path / "new.toml"

        _toml.atomic_write_text(destination, 'a = "1"\n')

        assert destination.read_text(encoding="utf-8") == 'a = "1"\n'

    @pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits")
    def test_a_new_destination_is_never_wider_than_0600(self, tmp_path: Path) -> None:
        destination = tmp_path / "new.toml"

        _toml.atomic_write_text(destination, 'a = "1"\n')

        assert stat.S_IMODE(destination.stat().st_mode) == 0o600

    @pytest.mark.skipif(os.name != "posix", reason="POSIX NAME_MAX")
    def test_a_destination_near_the_name_limit_still_writes(self, tmp_path: Path) -> None:
        """The staging name must not grow with the destination's name."""
        destination = tmp_path / ("d" * 240 + ".toml")

        _toml.atomic_write_text(destination, "new")

        assert destination.read_text(encoding="utf-8") == "new"

    @pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits")
    def test_the_destinations_permission_bits_are_preserved(self, tmp_path: Path) -> None:
        destination = tmp_path / "dataset.toml"
        destination.write_text("old", encoding="utf-8")
        destination.chmod(0o640)

        _toml.atomic_write_text(destination, "new")

        assert stat.S_IMODE(destination.stat().st_mode) == 0o640

    def test_a_missing_directory_fails_without_creating_anything(self, tmp_path: Path) -> None:
        destination = tmp_path / "missing" / "dataset.toml"

        with pytest.raises(FileNotFoundError):
            _toml.atomic_write_text(destination, "x")

        assert not destination.exists()
        assert list(tmp_path.iterdir()) == []
