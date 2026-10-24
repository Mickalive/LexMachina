from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RULES_FILENAME = "RULES.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _git_commit_time_iso(repo_root: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo_root), "log", "-1", "--format=%cI"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode("utf-8").strip()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def freeze_rules(
    out_dir: Path,
    bundle_inputs: list[dict[str, Any]],
    definitions: dict[str, Any],
    algorithm: dict[str, Any],
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    repo_root = out_dir
    # walk up to find git repo root
    p = out_dir.resolve()
    for _ in range(10):
        if (p / ".git").exists():
            repo_root = p
            break
        if p.parent == p:
            break
        p = p.parent

    frozen_at_commit = _git_commit_time_iso(repo_root)
    frozen_at_wall = datetime.now(timezone.utc).isoformat()
    rules = {
        "rules_version": "frontier-counter-evidence-content-filter/v1",
        "frozen_at_commit_iso": frozen_at_commit,
        "frozen_at_wall_iso": frozen_at_wall,
        "freeze_order_proof": {
            "method": "git_log_-1_format_cI_at_repo_root",
            "repo_root": str(repo_root),
        },
        "bundle_inputs": bundle_inputs,
        "definitions": definitions,
        "algorithm": algorithm,
        "thresholds": thresholds,
    }
    rules_path = out_dir / RULES_FILENAME
    rules_bytes = json.dumps(rules, indent=2, sort_keys=False).encode("utf-8") + b"\n"
    rules_path.write_bytes(rules_bytes)
    rules_sha = hashlib.sha256(rules_bytes).hexdigest()
    rules["rules_sha256"] = rules_sha
    rules["rules_path"] = str(rules_path)
    # rewrite with sha
    rules_bytes2 = json.dumps(rules, indent=2, sort_keys=False).encode("utf-8") + b"\n"
    rules_path.write_bytes(rules_bytes2)
    return rules
