"""Tests for ``scripts/release_preflight.py`` — the fail-closed release preflight.

Every test drives the script as a subprocess against a throwaway repository with
a bare ``origin``. The contract under test is the process boundary: the exit
code, the printed tag commands, and the refusal reasons — not an internal
function signature.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO_ROOT / "scripts" / "release_preflight.py"

_CFF_TEMPLATE = """cff-version: 1.2.0
message: "If you use sofer, please cite it as below."
title: sofer
version: {version}
date-released: 2026-10-21
authors:
  - family-names: Tester
    given-names: Test
"""


class _ReleaseRepo:
    """A throwaway repository whose ``origin`` is a bare repository."""

    def __init__(self, path: Path, config: Path, sha: str) -> None:
        self.path = path
        self.config = config
        self.sha = sha

    def env(self) -> dict[str, str]:
        """Return a git environment isolated from the host configuration."""
        env = dict(os.environ)
        env.update(
            {
                "GIT_CONFIG_GLOBAL": str(self.config),
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_AUTHOR_NAME": "Preflight Tester",
                "GIT_AUTHOR_EMAIL": "preflight@example.com",
                "GIT_COMMITTER_NAME": "Preflight Tester",
                "GIT_COMMITTER_EMAIL": "preflight@example.com",
            }
        )
        return env

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run git in the repository."""
        return subprocess.run(
            ["git", *args],
            cwd=self.path,
            check=check,
            capture_output=True,
            text=True,
            env=self.env(),
        )

    def commit_file(self, name: str, content: str, message: str) -> str:
        """Write a file, commit it, and return the commit OID."""
        (self.path / name).write_text(content, encoding="utf-8")
        self.git("add", name)
        self.git("commit", "-m", message)
        return self.git("rev-parse", "HEAD").stdout.strip()

    def preflight(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run the preflight script inside the repository."""
        return subprocess.run(
            [sys.executable, str(_SCRIPT), *args],
            cwd=self.path,
            capture_output=True,
            text=True,
            env=self.env(),
        )


@pytest.fixture()
def repo(tmp_path: Path) -> _ReleaseRepo:
    """Build a repository with one main commit carrying ``CITATION.cff`` 0.7.0."""
    config = tmp_path / "gitconfig"
    config.write_text("[init]\n\tdefaultBranch = main\n", encoding="utf-8")
    base_env = dict(os.environ)
    base_env.update(
        {
            "GIT_CONFIG_GLOBAL": str(config),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Preflight Tester",
            "GIT_AUTHOR_EMAIL": "preflight@example.com",
            "GIT_COMMITTER_NAME": "Preflight Tester",
            "GIT_COMMITTER_EMAIL": "preflight@example.com",
        }
    )

    def run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=base_env
        )

    remote = tmp_path / "remote.git"
    run(tmp_path, "init", "--bare", "--initial-branch=main", str(remote))

    path = tmp_path / "repo"
    path.mkdir()
    run(path, "init", "--initial-branch=main")
    (path / "CITATION.cff").write_text(_CFF_TEMPLATE.format(version="0.7.0"), encoding="utf-8")
    run(path, "add", "CITATION.cff")
    run(path, "commit", "-m", "init")
    sha = run(path, "rev-parse", "HEAD").stdout.strip()
    run(path, "remote", "add", "origin", str(remote))
    run(path, "push", "-u", "origin", "main")
    run(path, "fetch", "origin")
    return _ReleaseRepo(path, config, sha)


def test_preflight_passes_and_prints_the_two_commands(repo: _ReleaseRepo) -> None:
    """The happy path exits 0 and prints exactly the tag and push commands."""
    result = repo.preflight("--version", "0.7.0", "--sha", repo.sha)

    assert result.returncode == 0, result.stderr
    assert "preflight OK: v0.7.0" in result.stdout
    assert f'git tag -a "v0.7.0" "{repo.sha}" -m "sofer v0.7.0"' in result.stdout
    assert 'git push --no-follow-tags origin "refs/tags/v0.7.0:refs/tags/v0.7.0"' in result.stdout
    assert result.stderr == ""


def test_preflight_creates_no_tag(repo: _ReleaseRepo) -> None:
    """The preflight is read-only: it must not create the tag it describes."""
    result = repo.preflight("--version", "0.7.0", "--sha", repo.sha)

    assert result.returncode == 0, result.stderr
    tags = repo.git("tag", "--list").stdout.strip()
    assert tags == "", f"the preflight must not create tags, found: {tags!r}"


def test_preflight_rejects_a_version_with_a_leading_v(repo: _ReleaseRepo) -> None:
    """A `v`-prefixed version is refused, because the tag adds the `v`."""
    result = repo.preflight("--version", "v0.7.0", "--sha", repo.sha)

    assert result.returncode == 1
    assert "leading 'v'" in result.stderr
    assert "git tag -a" not in result.stdout


def test_preflight_rejects_a_branch_name_instead_of_a_full_oid(repo: _ReleaseRepo) -> None:
    """A branch name or short SHA is refused: a release tags an exact commit."""
    result = repo.preflight("--version", "0.7.0", "--sha", "main")

    assert result.returncode == 1
    assert "40-character commit OID" in result.stderr
    assert "git tag -a" not in result.stdout


def test_preflight_rejects_a_commit_absent_from_the_clone(repo: _ReleaseRepo) -> None:
    """A commit this clone does not have is refused, not guessed."""
    result = repo.preflight("--version", "0.7.0", "--sha", "0" * 40)

    assert result.returncode == 1
    assert "not present in this clone" in result.stderr
    assert "git tag -a" not in result.stdout


def test_preflight_rejects_a_commit_outside_main(repo: _ReleaseRepo) -> None:
    """A commit that is not reachable from origin/main is refused."""
    repo.git("switch", "-c", "side")
    side_sha = repo.commit_file("side.txt", "not merged\n", "side work")
    repo.git("switch", "main")

    result = repo.preflight("--version", "0.7.0", "--sha", side_sha)

    assert result.returncode == 1
    assert "not reachable from origin/main" in result.stderr
    assert "git tag -a" not in result.stdout


def test_preflight_rejects_a_citation_version_mismatch(repo: _ReleaseRepo) -> None:
    """CITATION.cff at the tagged commit must declare the requested version."""
    result = repo.preflight("--version", "0.8.0", "--sha", repo.sha)

    assert result.returncode == 1
    assert "does not declare version 0.8.0" in result.stderr
    assert "git tag -a" not in result.stdout


def test_preflight_rejects_an_existing_local_tag(repo: _ReleaseRepo) -> None:
    """A local tag means the version was already cut and is never reused."""
    repo.git("tag", "-a", "v0.7.0", "-m", "already released")

    result = repo.preflight("--version", "0.7.0", "--sha", repo.sha)

    assert result.returncode == 1
    assert "already exists locally" in result.stderr
    assert "git tag -a" not in result.stdout


def test_preflight_rejects_an_existing_remote_tag(repo: _ReleaseRepo) -> None:
    """A tag on the remote blocks the release even when the local tag is gone."""
    repo.git("tag", "-a", "v0.7.0", "-m", "already released")
    repo.git("push", "origin", "refs/tags/v0.7.0")
    repo.git("tag", "-d", "v0.7.0")

    result = repo.preflight("--version", "0.7.0", "--sha", repo.sha)

    assert result.returncode == 1
    assert "already exists on origin" in result.stderr
    assert "git tag -a" not in result.stdout


def test_preflight_fails_closed_when_the_remote_cannot_be_queried(
    repo: _ReleaseRepo, tmp_path: Path
) -> None:
    """An unreachable remote is a refusal, never an assumption that the tag is free."""
    repo.git("remote", "set-url", "origin", str(tmp_path / "missing.git"))

    result = repo.preflight("--version", "0.7.0", "--sha", repo.sha)

    assert result.returncode == 1
    assert "cannot query tags on origin" in result.stderr
    assert "git tag -a" not in result.stdout
