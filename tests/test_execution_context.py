"""Unit matrix for the execution-context identity contract (INIT-05 / D5).

Covers :func:`validate_identity` (missing/blank, separators, drives, quotes,
control characters, whitespace, user regex, placeholder ban), the three
:func:`resolve_dataset_root` modes (no-bound CLI, strict-descendant
fail-closed, explicit-``cwd`` containment), and the
``DatasetIdentity``/``report_identity`` invariants (``config_path ==
dataset_root / name.toml``, absolute paths).
"""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from sofer.execution_context import (
    DatasetIdentity,
    IdentityResolutionError,
    report_identity,
    resolve_dataset_root,
    validate_identity,
)


class TestValidateIdentity:
    """validate_identity matrix per INIT-05 / D3."""

    def test_valid_pair_returns_no_errors(self):
        """A conforming (name, user) pair yields an empty error list."""
        assert validate_identity("test", "alice") == []

    def test_accepts_user_hyphen_and_underscore(self):
        """user regex accepts 'user-org' and 'user_org'."""
        assert validate_identity("test", "user-org") == []
        assert validate_identity("test", "user_org") == []

    @pytest.mark.parametrize("name", [None, "", "   "])
    def test_missing_or_blank_name_refused(self, name):
        """None/empty/whitespace-only name is refused, first error exact."""
        errors = validate_identity(name, "alice")
        assert errors
        assert errors[0] == "name must be non-empty"

    @pytest.mark.parametrize("user", [None, "", "   "])
    def test_missing_or_blank_user_refused(self, user):
        """None/empty/whitespace-only user is refused with a user error."""
        errors = validate_identity("test", user)
        assert any("user" in e for e in errors)

    @pytest.mark.parametrize("user", ["YOUR_USER", "Your_User", "your-username", "YOUR_ORG"])
    def test_placeholder_user_refused(self, user):
        """Any normalized _PLACEHOLDERS value is refused pre-write."""
        errors = validate_identity("test", user)
        assert any("placeholder" in e.lower() for e in errors)

    @pytest.mark.parametrize("name", ["a/b", "a\\b"])
    def test_separator_refused(self, name):
        """Both slash and backslash separators are refused."""
        errors = validate_identity(name, "alice")
        assert any("component" in e.lower() for e in errors)

    def test_drive_path_refused(self):
        """ntpath.splitdrive('C:/evil') -> ('C:', '/evil') on every OS."""
        errors = validate_identity("C:/evil", "alice")
        assert errors

    @pytest.mark.parametrize("name", [".", ".."])
    def test_exact_dot_components_refused(self, name):
        """Exact '.' and '..' are banned."""
        assert validate_identity(name, "alice")

    def test_nested_traversal_refused(self):
        """'a/../b' is refused (separator rule covers it)."""
        assert validate_identity("a/../b", "alice")

    @pytest.mark.parametrize("name", ['a"b', "a'b"])
    def test_quote_refused(self, name):
        """Both quote styles are refused."""
        assert validate_identity(name, "alice")

    @pytest.mark.parametrize("name", ["a\nb", "a\tb", "a\x00b", "a\x7fb"])
    def test_control_char_refused(self, name):
        """Newline, tab, NUL, and DEL are refused ([\x00-\x1f\x7f])."""
        assert validate_identity(name, "alice")

    @pytest.mark.parametrize("name", [" name", "name ", "\tname"])
    def test_leading_trailing_whitespace_refused(self, name):
        """Leading/trailing whitespace is refused."""
        assert validate_identity(name, "alice")

    @pytest.mark.parametrize("user", ["user.name", "user name"])
    def test_user_regex_rejects_non_conforming(self, user):
        """user not matching ^[\\w\\-]+$ is refused."""
        assert validate_identity("test", user)

    @pytest.mark.parametrize("user", ["alice\n", "alice\t", "alice\x00", "alice\x7f"])
    def test_user_control_char_refused(self, user):
        """Newline/tab/NUL/DEL users are refused.

        Python's ``$`` anchor matches before a trailing ``\n``, so the regex
        alone would let ``"alice\n"`` through; the ``\\Z`` anchor plus the
        explicit control-character check reject it (INIT-05 parity with the
        ``name`` component check).
        """
        errors = validate_identity("ds", user)
        assert any("control" in e.lower() or "match" in e.lower() for e in errors)

    def test_name_placeholder_not_banned(self):
        """The placeholder ban applies to user only — a placeholder-like
        name is still a valid single component."""
        assert validate_identity("YOUR_USER", "alice") == []

    @pytest.mark.parametrize("name", ["a*b", "a?b", "a<b", "a>b", "a|b", "a1:b"])
    def test_windows_invalid_chars_refused(self, name):
        """Windows-invalid filename characters (<>:|?*) are refused (INIT-05).

        These pass the single-component check (no separator/drive/quote) but
        cannot be materialized as ``<name>.toml`` on Windows. ``a:b`` /
        ``1:b`` are already caught by the drive check (ntpath.splitdrive
        treats any ``X:`` at index 1 as a drive), so the char-level ``:``
        check is pinned with a colon outside drive position (``a1:b``).
        """
        errors = validate_identity(name, "alice")
        assert any("Windows-invalid" in e for e in errors)

    @pytest.mark.parametrize(
        "name",
        [
            "CON",
            "con",
            "Prn",
            "AUX",
            "NUL",
            "COM1",
            "com9",
            "LPT1",
            "lpt9",
            "CON.txt",
            "con.toml",
        ],
    )
    def test_reserved_device_name_refused(self, name):
        """Windows reserved device names are refused pre-write (INIT-05).

        Dots are allowed in names, so the reserved check is stem-matched:
        ``CON`` and ``CON.txt`` are both rejected (``<name>.toml`` would be
        unmaterializable on Windows).
        """
        errors = validate_identity(name, "alice")
        assert any("reserved" in e.lower() for e in errors)

    def test_normal_names_still_accepted(self):
        """Names with dots/hyphens/underscores remain valid."""
        for name in ("my.ds", "my-dataset", "data_2024"):
            assert validate_identity(name, "alice") == []


class TestResolveDatasetRoot:
    """resolve_dataset_root three modes per D5."""

    def test_no_bound_returns_live_cwd(self, tmp_path):
        """Mode (a): CLI no-bound returns the resolved live cwd."""
        live = tmp_path / "cwd"
        live.mkdir()
        resolved = resolve_dataset_root(None, live_cwd=live)
        assert resolved == live.resolve()

    def test_no_bound_rejects_cwd(self, tmp_path):
        """Mode (a): cwd must be None without a server root."""
        with pytest.raises(IdentityResolutionError):
            resolve_dataset_root("child", live_cwd=tmp_path)

    def test_strict_descendant_inside_returns_live(self, tmp_path):
        """Mode (c): live cwd strictly inside root resolves to live."""
        child = tmp_path / "child"
        child.mkdir()
        resolved = resolve_dataset_root(None, live_cwd=child, server_root=tmp_path)
        assert resolved == child.resolve()

    def test_live_equal_root_fails_closed(self, tmp_path):
        """Mode (c): live cwd equal to root is refused (strict descendant)."""
        with pytest.raises(IdentityResolutionError, match="cwd"):
            resolve_dataset_root(None, live_cwd=tmp_path, server_root=tmp_path)

    def test_live_outside_root_fails_closed(self, tmp_path):
        """Mode (c): live cwd outside the root is refused."""
        outside = tmp_path.parent
        with pytest.raises(IdentityResolutionError, match="cwd"):
            resolve_dataset_root(None, live_cwd=outside, server_root=tmp_path)

    def test_error_message_names_cwd_with_guidance(self, tmp_path):
        """The fail-closed message names the required cwd argument with
        actionable guidance (pass cwd=\"<dataset dir>\")."""
        with pytest.raises(IdentityResolutionError, match='pass cwd="<dataset dir>"'):
            resolve_dataset_root(None, live_cwd=tmp_path, server_root=tmp_path)

    def test_explicit_cwd_relative_contained(self, tmp_path):
        """Mode (b): relative cwd absolutized against the root, contained."""
        child = tmp_path / "child"
        child.mkdir()
        resolved = resolve_dataset_root("child", live_cwd=tmp_path, server_root=tmp_path)
        assert resolved == child.resolve()

    def test_explicit_cwd_absolute_contained(self, tmp_path):
        """Mode (b): absolute cwd inside the root is accepted."""
        child = tmp_path / "child"
        child.mkdir()
        resolved = resolve_dataset_root(str(child), live_cwd=tmp_path, server_root=tmp_path)
        assert resolved == child.resolve()

    def test_explicit_cwd_expanduser_tilde(self, tmp_path, monkeypatch):
        """Mode (b): '~' is expanded before absolutizing against the root (D5:
        expanduser → absolutize → resolve → is_relative_to)."""
        child = tmp_path / "child"
        child.mkdir()
        monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows
        monkeypatch.setenv("HOME", str(tmp_path))  # POSIX
        resolved = resolve_dataset_root("~/child", live_cwd=tmp_path, server_root=tmp_path)
        assert resolved == child.resolve()

    def test_explicit_cwd_equal_root_accepted(self, tmp_path):
        """Mode (b): cwd equal to the root is contained (is_relative_to) —
        unlike mode (c), which requires a STRICT descendant."""
        resolved = resolve_dataset_root(str(tmp_path), live_cwd=tmp_path, server_root=tmp_path)
        assert resolved == tmp_path.resolve()

    def test_explicit_cwd_escape_rejected(self, tmp_path):
        """Mode (b): an absolute cwd escaping the root is refused."""
        evil = tmp_path.parent / "evil"
        with pytest.raises(IdentityResolutionError):
            resolve_dataset_root(str(evil), live_cwd=tmp_path, server_root=tmp_path)

    def test_explicit_cwd_traversal_rejected(self, tmp_path):
        """Mode (b): a '..' traversal resolving outside the root is refused."""
        with pytest.raises(IdentityResolutionError):
            resolve_dataset_root("child/../../evil", live_cwd=tmp_path, server_root=tmp_path)


class TestDatasetIdentity:
    """DatasetIdentity / report_identity invariants (D2, INIT-03)."""

    def test_config_path_derived_from_root_and_name(self, tmp_path):
        """config_path == dataset_root / f'{name}.toml' by construction."""
        identity = DatasetIdentity(name="my-ds", user="alice", dataset_root=tmp_path)
        assert identity.config_path == tmp_path / "my-ds.toml"

    def test_from_parts_resolves_root(self, tmp_path):
        """from_parts resolves dataset_root to an absolute path."""
        identity = DatasetIdentity.from_parts("my-ds", "alice", tmp_path)
        assert identity.dataset_root == tmp_path.resolve()
        assert identity.dataset_root.is_absolute()
        assert identity.config_path == tmp_path.resolve() / "my-ds.toml"

    def test_identity_is_frozen(self, tmp_path):
        """A frozen dataclass — fields cannot be reassigned."""
        identity = DatasetIdentity("my-ds", "alice", tmp_path)
        with pytest.raises(FrozenInstanceError):
            setattr(identity, "name", "other")

    def test_report_identity_absolute_strings(self, tmp_path):
        """report_identity returns absolute config_path/dataset_root strings."""
        identity = DatasetIdentity.from_parts("my-ds", "alice", tmp_path)
        reported = report_identity(identity)
        assert reported == {
            "config_path": str(identity.config_path),
            "dataset_root": str(identity.dataset_root),
        }
        assert Path(reported["config_path"]).is_absolute()
        assert Path(reported["dataset_root"]).is_absolute()
