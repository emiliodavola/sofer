"""The package's single atomic-replacement primitive (issues #365, #371).

Every writer in the package -- the surgical TOML editors, ``scanner.write_toml``
and MCP client-config registration -- reaches this module, so these cases pin
the staging policy itself: a call may change its destination and the temporary
file it created exclusively, never the predictable ``<destination>.tmp`` sibling
that may already belong to the user or to another writer.

The per-caller newline policies are pinned here too, because the primitive is
the only place that decides whether translation happens.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from sofer import _atomic


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


class TestAtomicWriteText:
    """``atomic_write_text`` changes the destination and its own temp file only."""

    def test_a_preexisting_regular_tmp_sibling_is_left_untouched(self, tmp_path: Path) -> None:
        destination = tmp_path / "dataset.toml"
        sibling = tmp_path / "dataset.toml.tmp"
        destination.write_text("original config", encoding="utf-8")
        sibling.write_text("pre-existing staging file", encoding="utf-8")

        _atomic.atomic_write_text(destination, "updated config")

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

        _atomic.atomic_write_text(destination, "updated config")

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

        monkeypatch.setattr(_atomic.os, "replace", _boom)
        with pytest.raises(OSError, match="disk full"):
            _atomic.atomic_write_text(destination, "updated config")

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

        monkeypatch.setattr(_atomic.os, "replace", _record)
        _atomic.atomic_write_text(destination, "one")
        _atomic.atomic_write_text(destination, "two")

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

        monkeypatch.setattr(_atomic.os, "chmod", _refuse)
        _atomic.atomic_write_text(destination, "new")

        assert destination.read_text(encoding="utf-8") == "new"

    def test_a_non_oserror_failure_leaves_no_staging_file(self, tmp_path: Path) -> None:
        """An encoding failure is not an OSError, and must not orphan a file."""
        destination = tmp_path / "dataset.toml"
        destination.write_text("old", encoding="utf-8")

        with pytest.raises(UnicodeEncodeError):
            _atomic.atomic_write_text(destination, "\ud800", encoding="utf-8")

        assert destination.read_text(encoding="utf-8") == "old"
        assert sorted(item.name for item in tmp_path.iterdir()) == ["dataset.toml"]

    def test_crlf_bytes_and_the_encoding_are_preserved(self, tmp_path: Path) -> None:
        destination = tmp_path / "dataset.toml"

        _atomic.atomic_write_text(destination, 'a = "1"\r\nb = "2"\r\n', encoding="utf-8")

        assert destination.read_bytes() == b'a = "1"\r\nb = "2"\r\n'

    def test_a_new_destination_is_created(self, tmp_path: Path) -> None:
        destination = tmp_path / "new.toml"

        _atomic.atomic_write_text(destination, 'a = "1"\n')

        assert destination.read_text(encoding="utf-8") == 'a = "1"\n'

    def test_the_default_policy_writes_the_bytes_it_was_given(self, tmp_path: Path) -> None:
        """``newline=""`` means no translation on any platform."""
        destination = tmp_path / "preserved.yaml"

        _atomic.atomic_write_text(destination, "a\nb\n")

        assert destination.read_bytes() == b"a\nb\n"

    def test_newline_none_keeps_the_platform_translation(self, tmp_path: Path) -> None:
        """Callers whose old writer translated newlines keep that behaviour."""
        destination = tmp_path / "platform.json"

        _atomic.atomic_write_text(destination, "a\nb\n", newline=None)

        assert destination.read_bytes() == f"a{os.linesep}b{os.linesep}".encode()

    @pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits")
    def test_a_new_destination_is_never_wider_than_0600(self, tmp_path: Path) -> None:
        destination = tmp_path / "new.toml"

        _atomic.atomic_write_text(destination, 'a = "1"\n')

        assert stat.S_IMODE(destination.stat().st_mode) == 0o600

    @pytest.mark.skipif(os.name != "posix", reason="POSIX NAME_MAX")
    def test_a_destination_near_the_name_limit_still_writes(self, tmp_path: Path) -> None:
        """The staging name must not grow with the destination's name."""
        destination = tmp_path / ("d" * 240 + ".toml")

        _atomic.atomic_write_text(destination, "new")

        assert destination.read_text(encoding="utf-8") == "new"

    @pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits")
    def test_the_destinations_permission_bits_are_preserved(self, tmp_path: Path) -> None:
        destination = tmp_path / "dataset.toml"
        destination.write_text("old", encoding="utf-8")
        destination.chmod(0o640)

        _atomic.atomic_write_text(destination, "new")

        assert stat.S_IMODE(destination.stat().st_mode) == 0o640

    def test_a_missing_directory_fails_without_creating_anything(self, tmp_path: Path) -> None:
        destination = tmp_path / "missing" / "dataset.toml"

        with pytest.raises(FileNotFoundError):
            _atomic.atomic_write_text(destination, "x")

        assert not destination.exists()
        assert list(tmp_path.iterdir()) == []


def _write_through_family(family: str, destination: Path) -> None:
    """Drive one of the three writer families through its public entry point."""
    if family == "surgical-edit":
        from sofer import meta_edit

        destination.write_text('[dataset]\nname = "x"\nrepo_id = "u/r"\n', encoding="utf-8")
        meta_edit.set_meta(destination, {"description": "Real"})
    elif family == "scanner":
        from sofer import scanner

        scanner.write_toml({"dataset": {"name": "x", "repo_id": "u/r"}}, destination)
    else:
        from sofer import mcp_registration

        doc = {"mcp": {"sofer": {"command": "sofer-mcp"}}}
        mcp_registration.atomic_write(destination, doc, "json")


@pytest.mark.parametrize("family", ["surgical-edit", "scanner", "registration"])
def test_each_writer_family_leaves_the_tmp_symlink_and_its_target_untouched(
    family: str, tmp_path: Path
) -> None:
    """Issue #371: no family may open the predictable ``<destination>.tmp`` path.

    The three writer families owned independent copies of the staging mechanics,
    so the guarantee is asserted at each public entry point, not only at the
    shared primitive they now use.
    """
    destination = tmp_path / "dataset.toml"
    unrelated = tmp_path / "unrelated.txt"
    link = tmp_path / "dataset.toml.tmp"
    unrelated.write_text("must not change", encoding="utf-8")
    if not _link_file(link, unrelated):
        pytest.skip("symlink creation unavailable on this host")

    _write_through_family(family, destination)

    assert unrelated.read_text(encoding="utf-8") == "must not change"
    assert link.is_symlink()
    assert not destination.is_symlink()
    assert destination.exists()
    assert [item.name for item in tmp_path.iterdir() if item.name.startswith(".sofer-")] == []
