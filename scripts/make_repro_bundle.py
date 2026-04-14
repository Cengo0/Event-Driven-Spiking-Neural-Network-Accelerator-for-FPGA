#!/usr/bin/env python3
"""Create a reproducibility bundle (G14) with artifact copies + manifest + hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


@dataclass
class CopiedArtifact:
    src: str
    dst: str
    sha256: str
    size_bytes: int


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(cmd: List[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=str(cwd), text=True).strip()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build reproducibility bundle for paper artifacts")
    p.add_argument("--repo-root", default=".", help="Repo root path")
    p.add_argument("--bundle-dir", default="", help="Output bundle directory (default: outputs/repro_bundle_<ts>)")
    p.add_argument("--artifact", action="append", default=[], help="Artifact path to include (repeatable)")
    p.add_argument("--commands-file", default="", help="Optional file containing canonical run commands")
    p.add_argument("--tar", action="store_true", help="Also create .tar.gz archive")
    return p.parse_args()


def default_artifacts(repo_root: Path) -> List[Path]:
    candidates = [
        repo_root / "outputs" / "snn_integrated_v2.bit",
        repo_root / "outputs" / "snn_integrated_v2.hwh",
        repo_root / "outputs" / "snn_integrated_v2_timing.rpt",
        repo_root / "outputs" / "snn_integrated_v2_utilization.rpt",
        repo_root / "outputs" / "snn_integrated_v2_power.rpt",
        repo_root / "outputs" / "integrated_power_final.rpt",
        repo_root / "ACCEPTANCE_CRITERIA.md",
        repo_root / "README.md",
        repo_root / "docs" / "developer_guide.md",
        repo_root / "scripts" / "compute_energy_metrics.py",
        repo_root / "tests" / "fpga_10class_inference.py",
        repo_root / "tests" / "fpga_stdp_parity.py",
    ]
    return [p for p in candidates if p.exists()]


def copy_artifact(src: Path, repo_root: Path, dst_root: Path) -> CopiedArtifact:
    try:
        rel = src.resolve().relative_to(repo_root.resolve())
        dst = dst_root / "artifacts" / rel
    except ValueError:
        dst = dst_root / "artifacts" / src.name

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

    return CopiedArtifact(
        src=str(src),
        dst=str(dst),
        sha256=sha256_file(dst),
        size_bytes=dst.stat().st_size,
    )


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if args.bundle_dir:
        bundle_dir = Path(args.bundle_dir).resolve()
    else:
        bundle_dir = (repo_root / "outputs" / f"repro_bundle_{timestamp}").resolve()

    bundle_dir.mkdir(parents=True, exist_ok=True)

    selected: List[Path] = []
    if args.artifact:
        for a in args.artifact:
            p = Path(a)
            if not p.is_absolute():
                p = (repo_root / p)
            if p.exists():
                selected.append(p.resolve())
            else:
                print(f"[WARN] missing artifact skipped: {p}")
    else:
        selected = default_artifacts(repo_root)

    copied: List[CopiedArtifact] = []
    for src in selected:
        copied.append(copy_artifact(src, repo_root, bundle_dir))

    git_head = git(["git", "rev-parse", "HEAD"], repo_root)
    git_branch = git(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    git_status = git(["git", "status", "--short"], repo_root)

    if args.commands_file:
        cmd_src = Path(args.commands_file)
        if not cmd_src.is_absolute():
            cmd_src = repo_root / cmd_src
        if cmd_src.exists():
            cmd_dst = bundle_dir / "commands.sh"
            shutil.copy2(cmd_src, cmd_dst)
        else:
            print(f"[WARN] commands file not found: {cmd_src}")
    else:
        (bundle_dir / "commands.sh").write_text(
            """#!/usr/bin/env bash
set -euo pipefail

# Canonical inference (PL clock explicit)
sudo python3 /home/xilinx/snn/tests/fpga_10class_inference.py \\
  --data /home/xilinx/snn \\
  --n 10000 \\
  --packet-id-width 13 \\
  --assert-hls-reset \\
  --strict-identical \\
  --pl-clock-hz 80000000 \\
  --output /home/xilinx/snn/mnist_10class_results_pl_80m.json

# Canonical STDP parity
source /etc/profile.d/xrt_setup.sh 2>/dev/null || true
sudo -E PYTHONPATH=/home/xilinx/snn/software/python:$PYTHONPATH \\
/usr/local/share/pynq-venv/bin/python3 /home/xilinx/snn/tests/fpga_stdp_parity.py \\
  --data /home/xilinx/snn \\
  --n-steps 100 \\
  --checkpoint-every 0 \\
  --run-chunk-steps 1 \\
  --runtime-profile balanced \\
  --packet-id-width 13 \\
  --assert-hls-reset \\
  --strict \\
  --no-cma-spike-buffer \\
  --post-flush-runs 4 \\
  --sw-post-source synthetic \\
  --check-hls-version
""",
            encoding="utf-8",
        )

    manifest: Dict[str, object] = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "git": {
            "branch": git_branch,
            "commit": git_head,
            "dirty": bool(git_status.strip()),
            "status_short": git_status.splitlines(),
        },
        "artifacts": [a.__dict__ for a in copied],
    }

    manifest_path = bundle_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Bundle dir: {bundle_dir}")
    print(f"Manifest:   {manifest_path}")
    print(f"Artifacts:  {len(copied)} files")

    if args.tar:
        tar_path = bundle_dir.with_suffix(".tar.gz")
        with tarfile.open(tar_path, "w:gz") as tf:
            tf.add(bundle_dir, arcname=bundle_dir.name)
        print(f"Archive:    {tar_path}")


if __name__ == "__main__":
    main()
