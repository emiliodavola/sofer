"""Fail-closed preflight checks for cutting a sofer release tag.

Releases are tag-driven: pushing an annotated ``vX.Y.Z`` tag runs
``.github/workflows/release.yml``, which refuses to publish unless the
``CITATION.cff`` at that commit declares the tagged version. That gate covers
the version, but the release procedure also depends on facts no workflow can
enforce: that the tagged commit is on ``main``, and that the tag does not
already exist.

This script encodes those procedural checks, read-only:

* ``--version`` is a bare ``MAJOR.MINOR.PATCH`` (no leading ``v``);
* ``--sha`` is a full 40-character commit OID that exists in this clone;
* that commit is reachable from ``<remote>/main`` (ancestry, not equality);
* ``CITATION.cff`` **at that commit** declares the requested version with a
  valid ISO ``date-released`` — checked by running the same
  ``update_citation.py --check`` gate the release workflow runs, against the
  blob read via ``git show``, so the worktree and index are never touched;
* the tag ``vX.Y.Z`` exists neither locally nor on the remote.

When every check passes it prints the two commands to run. When any check
fails it explains why, prints no command, and exits 1. Creating and pushing the
tag stays a deliberately human action; this script never mutates anything.

The script is stdlib-only and shells out to ``git``, so it runs with no
``uv sync``. Run ``git fetch`` first when ``<remote>/main`` may be stale: a
stale ref can only produce a false refusal, never a false pass.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_VERSION_RE = re.compile(r"^(?P<version>\d+\.\d+\.\d+)$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_CITATION_SCRIPT = Path(__file__).resolve().with_name("update_citation.py")


def _run(command: list[str], cwd: Path, *, check: bool = False) -> subprocess.CompletedProcess[str]:
    """Run a command and capture its text output.

    Args:
        command: The full argv, executable included.
        cwd:     Directory to run in.
        check:   When True, raise on a non-zero exit (`CalledProcessError`).

    Returns:
        The completed process, with ``stdout`` and ``stderr`` as text.
    """
    return subprocess.run(
        command,
        cwd=str(cwd),
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run ``git`` with ``args`` in ``cwd``, without raising.

    Args:
        args: Arguments after the ``git`` executable.
        cwd:  Repository directory.

    Returns:
        The completed process. Callers inspect ``returncode`` themselves.
    """
    return _run(["git", *args], cwd)


def validate_version(version: str) -> str | None:
    """Return an error message when ``version`` is not a bare release version.

    Args:
        version: The candidate version, e.g. ``"0.7.0"``.

    Returns:
        ``None`` when the value is ``MAJOR.MINOR.PATCH``; otherwise the message
        describing the expected shape.
    """
    if _VERSION_RE.fullmatch(version):
        return None
    return (
        f"--version {version!r} must be MAJOR.MINOR.PATCH without a leading 'v' "
        "(the tag adds the 'v'), e.g. 0.7.0"
    )


def validate_sha(sha: str) -> str | None:
    """Return an error message when ``sha`` is not a full lower-case commit OID.

    Args:
        sha: The candidate commit OID.

    Returns:
        ``None`` when the value is exactly 40 lower-case hex characters;
        otherwise the message describing the expected shape.
    """
    if _SHA_RE.fullmatch(sha):
        return None
    return f"--sha {sha!r} must be a full 40-character commit OID, not a branch, tag or short SHA"


def check_commit_exists(sha: str, cwd: Path) -> str | None:
    """Verify the commit object exists in this clone.

    Args:
        sha: The full commit OID.
        cwd: Repository directory.

    Returns:
        ``None`` when the object exists; otherwise the error message.
    """
    result = _git(["cat-file", "-e", f"{sha}^{{commit}}"], cwd)
    if result.returncode == 0:
        return None
    return f"commit {sha} is not present in this clone; fetch it first (git fetch)"


def check_ancestor(sha: str, remote: str, cwd: Path) -> str | None:
    """Verify ``sha`` is reachable from ``<remote>/main``.

    Args:
        sha:    The full commit OID.
        remote: Remote name, e.g. ``"origin"``.
        cwd:    Repository directory.

    Returns:
        ``None`` when the commit is an ancestor of ``<remote>/main``; otherwise
        the error message naming the missing ref or the failed ancestry.
    """
    main_ref = f"{remote}/main"
    if _git(["rev-parse", "--verify", "--quiet", f"{main_ref}^{{commit}}"], cwd).returncode != 0:
        return f"remote ref {main_ref} does not exist locally; run: git fetch {remote}"
    result = _git(["merge-base", "--is-ancestor", sha, main_ref], cwd)
    if result.returncode == 0:
        return None
    if result.returncode == 1:
        return f"commit {sha} is not reachable from {main_ref}; a release must tag a main commit"
    return (
        f"git merge-base failed while checking ancestry against {main_ref}: {result.stderr.strip()}"
    )


def check_citation(sha: str, version: str, cwd: Path) -> str | None:
    """Verify ``CITATION.cff`` at ``sha`` through the release workflow's gate.

    The blob is read with ``git show`` so the worktree and index are never
    touched, written to a temporary file outside the repository, and checked by
    the same ``update_citation.py --check`` that ``release.yml`` runs.

    Args:
        sha:     The full commit OID.
        version: The expected release version.
        cwd:     Repository directory.

    Returns:
        ``None`` when the CFF at that commit declares ``version``; otherwise the
        error message, including the checker's own output.
    """
    result = _git(["show", f"{sha}:CITATION.cff"], cwd)
    if result.returncode != 0:
        return f"cannot read CITATION.cff at {sha}: {result.stderr.strip()}"
    with tempfile.TemporaryDirectory(prefix="sofer-preflight-") as tmp:
        cff_path = Path(tmp) / "CITATION.cff"
        try:
            cff_path.write_text(result.stdout, encoding="utf-8")
        except OSError as exc:
            return f"cannot stage CITATION.cff for checking: {exc}"
        checked = _run(
            [
                sys.executable,
                str(_CITATION_SCRIPT),
                "--check",
                "--version",
                version,
                "--cff-path",
                str(cff_path),
            ],
            cwd,
        )
    if checked.returncode == 0:
        return None
    detail = (checked.stderr or checked.stdout).strip()
    return f"CITATION.cff at {sha} does not declare version {version}: {detail}"


def check_tag_absent(tag: str, remote: str, cwd: Path) -> str | None:
    """Verify the tag exists neither locally nor on the remote.

    Args:
        tag:    The tag name, e.g. ``"v0.7.0"``.
        remote: Remote name, e.g. ``"origin"``.
        cwd:    Repository directory.

    Returns:
        ``None`` when the tag is absent everywhere; otherwise the error message.
        A remote query that fails is treated as a refusal, never as absence.
    """
    if _git(["rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"], cwd).returncode == 0:
        return f"tag {tag} already exists locally; a release tag is never moved or reused"
    result = _git(["ls-remote", "--tags", remote, f"refs/tags/{tag}"], cwd)
    if result.returncode != 0:
        return (
            f"cannot query tags on {remote} (refusing rather than assuming the tag is free): "
            f"{result.stderr.strip()}"
        )
    if result.stdout.strip():
        return f"tag {tag} already exists on {remote}; a release tag is never moved or reused"
    return None


def run_checks(version: str, sha: str, remote: str, cwd: Path) -> list[str]:
    """Run every preflight check and collect the failures.

    Args:
        version: The expected release version.
        sha:     The full commit OID that would be tagged.
        remote:  Remote name.
        cwd:     Repository directory.

    Returns:
        The failure messages, in check order. Empty means every check passed.
    """
    errors: list[str] = []
    version_error = validate_version(version)
    sha_error = validate_sha(sha)
    if version_error:
        errors.append(version_error)
    if sha_error:
        errors.append(sha_error)
    if errors:
        return errors

    for error in (
        check_commit_exists(sha, cwd),
        check_ancestor(sha, remote, cwd),
        check_citation(sha, version, cwd),
        check_tag_absent(f"v{version}", remote, cwd),
    ):
        if error:
            errors.append(error)
    return errors


def main(argv: list[str] | None = None) -> int:
    """Run the CLI: verify the release preconditions or refuse.

    Orchestration flow:
    1. Parse ``--version``, ``--sha`` and ``--remote`` (default ``origin``).
    2. Validate the version and SHA shapes; report every failure at once.
    3. Run the repository checks: the commit exists, is reachable from
       ``<remote>/main``, its ``CITATION.cff`` passes the release gate, and the
       tag is absent locally and remotely.
    4. On success, print the two commands that would create and push the tag.
       On any failure, print every reason to stderr, print no command, exit 1.

    Args:
        argv: CLI arguments; defaults to ``sys.argv[1:]`` when None.

    Returns:
        Exit code: 0 when every check passes; 1 when anything is refused.
    """
    parser = argparse.ArgumentParser(
        prog="release_preflight",
        description=(
            "Verify the preconditions for tagging a sofer release: the commit is on "
            "main, CITATION.cff at that commit declares the version, and the tag is "
            "free. Read-only; it never creates or pushes a tag."
        ),
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Release version without the leading 'v', e.g. 0.7.0.",
    )
    parser.add_argument(
        "--sha",
        required=True,
        help="Full 40-character commit OID that would be tagged (the merged main commit).",
    )
    parser.add_argument(
        "--remote",
        default="origin",
        help="Remote name whose <remote>/main must contain the commit (default: origin).",
    )
    args = parser.parse_args(argv)

    cwd = Path.cwd()
    errors = run_checks(args.version, args.sha, args.remote, cwd)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        print("FAIL: release preflight refused; no tag command printed.", file=sys.stderr)
        return 1

    tag = f"v{args.version}"
    print(
        f"preflight OK: {tag} at {args.sha} "
        f"(reachable from {args.remote}/main, CITATION.cff declares it, tag free)"
    )
    print("")
    print("Run these, in this order, only with explicit release authorization:")
    print("")
    print(f'git tag -a "{tag}" "{args.sha}" -m "sofer {tag}"')
    print(f'git push --no-follow-tags {args.remote} "refs/tags/{tag}:refs/tags/{tag}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
