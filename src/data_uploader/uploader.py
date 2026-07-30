"""
Upload engine.

Delegates the actual upload to ``huggingface-cli``, which provides
progress bars, resume support for large files, and recursive upload.
This module stays thin — all validation happens in :mod:`checks`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .model import DatasetConfig
from .repo_compliance import build_dataset_card, build_license_file, build_schema_report


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
            print(f"  \u26a0  {result.stderr.strip()}")


def _hf_upload(
    repo_id: str,
    local_path: str | Path,
    remote_path: str,
    repo_type: str,
) -> bool:
    """Upload a single file to a Hugging Face Hub repository.

    Returns:
        ``True`` on success, ``False`` on failure.
    """
    cmd = [
        "huggingface-cli",
        "upload",
        repo_id,
        str(local_path),
        remote_path,
        "--repo-type",
        repo_type,
    ]
    label = Path(local_path).name
    print(f"  \u2191  {label}  \u2192  {remote_path}")
    with subprocess.Popen(cmd, stdout=sys.stdout, stderr=subprocess.PIPE, text=True) as proc:
        stderr = proc.stderr.read() if proc.stderr else ""
        proc.wait()
        if proc.returncode == 0:
            print(f"  \u2713  {label}")
            return True
        print(f"  \u2717  {stderr.strip()}")
        return False


def upload(cfg: DatasetConfig) -> int:
    """Upload all files declared in *cfg* to Hugging Face Hub.

    Generates compliance artifacts (Dataset Card, LICENSE, schema report)
    before uploading any data files.

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

    # ── Staging (wraps compliance + upload for cleanup) ──────────────────
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # ── Compliance generation ────────────────────────────────────────
        print("  \U0001f4c4  Generating Dataset Card \u2026")
        schema = build_schema_report(
            cfg, csv_delimiter=cfg.csv_delimiter, csv_encoding=cfg.csv_encoding
        )

        recipe_content: str | None = None
        if cfg.recipe:
            recipe_path = Path(cfg.recipe)
            if recipe_path.exists():
                recipe_content = recipe_path.read_text(encoding="utf-8")

        card = build_dataset_card(cfg, schema, recipe_content=recipe_content)
        print("  \U0001f4c4  Generating LICENSE \u2026")
        license_text = build_license_file(cfg.license)

        (tmpdir / "README.md").write_text(card, encoding="utf-8")
        (tmpdir / "LICENSE").write_text(license_text, encoding="utf-8")

        # Upload compliance files first (order matters for HF recognition)
        _hf_upload(cfg.repo_id, tmpdir / "README.md", "README.md", cfg.repo_type)
        _hf_upload(cfg.repo_id, tmpdir / "LICENSE", "LICENSE", cfg.repo_type)

        # ── Upload data files ───────────────────────────────────────────
        ok = 0
        fail = 0

        base = cfg._base_dir if cfg._base_dir else Path.cwd()
        for entry in cfg.files:
            local = entry.resolve(base)
            remote = entry.remote
            label = local.name if not entry.recursive else f"{local.name}/"

            if not local.exists():
                print(f"  \u2717  NOT FOUND: {local}")
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

            print(f"  \u2191  {label}  \u2192  {remote}")
            with subprocess.Popen(
                cmd, stdout=sys.stdout, stderr=subprocess.PIPE, text=True
            ) as proc:
                stderr = proc.stderr.read() if proc.stderr else ""
                proc.wait()
                if proc.returncode == 0:
                    print(f"  \u2713  {label}")
                    ok += 1
                else:
                    print(f"  \u2717  {stderr.strip()}")
                    fail += 1

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"\n{'=' * 60}")
    print(f"  Result: {ok} uploaded, {fail} failed")
    print(f"{'=' * 60}\n")
    return 0 if fail == 0 else 1
