"""
Upload engine.

Delegates the actual upload to ``huggingface-cli``, which provides
progress bars, resume support for large files, and recursive upload.
This module stays thin — all validation happens in :mod:`checks`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .model import DatasetConfig


def _ensure_repo(cfg: DatasetConfig) -> None:
    """Create the HF repository if it doesn't exist.

    Errors are silently ignored when the repo already exists.
    """
    cmd = [
        "huggingface-cli",
        "repo",
        "create",
        cfg.repo_id,
        "--type",
        cfg.repo_type,
        "--private" if cfg.private else "--public",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if "already exists" in result.stderr.lower():
            print(f"  i  Repository already exists: {cfg.repo_id}")
        else:
            print(f"  ⚠  {result.stderr.strip()}")


def upload(cfg: DatasetConfig) -> int:
    """Upload all files declared in *cfg* to Hugging Face Hub.

    Returns:
        Exit code (0 = success, 1 = one or more uploads failed).
    """
    print(f"\n{'=' * 60}")
    print(f"  Dataset:   {cfg.name}")
    print(f"  Target:    {cfg.repo_id}")
    print(f"  Type:      {cfg.repo_type}")
    print(f"  Private:   {cfg.private}")
    print(f"  File entries: {len(cfg.files)}")
    print(f"{'=' * 60}\n")

    _ensure_repo(cfg)

    ok = 0
    fail = 0

    base = cfg._base_dir if cfg._base_dir else Path.cwd()
    for entry in cfg.files:
        local = entry.resolve(base)
        remote = entry.remote
        label = local.name if not entry.recursive else f"{local.name}/"

        if not local.exists():
            print(f"  ✗  NOT FOUND: {local}")
            fail += 1
            continue

        cmd = [
            "huggingface-cli",
            "upload",
            cfg.repo_id,
            str(local.absolute()),
            remote,
            "--repo-type",
            cfg.repo_type,
        ]
        if entry.recursive:
            cmd.append("--recursive")

        print(f"  ↑  {label}  →  {remote}")
        with subprocess.Popen(cmd, stdout=sys.stdout, stderr=subprocess.PIPE, text=True) as proc:
            stderr = proc.stderr.read() if proc.stderr else ""
            proc.wait()
            if proc.returncode == 0:
                print(f"  ✓  {label}")
                ok += 1
            else:
                print(f"  ✗  {stderr.strip()}")
                fail += 1

    print(f"\n{'=' * 60}")
    print(f"  Result: {ok} uploaded, {fail} failed")
    print(f"{'=' * 60}\n")
    return 0 if fail == 0 else 1
