#!/usr/bin/env python3
"""Audit-ready diagnosis of an operational-resume snapshot.

An operational resume starts from a *persisted producer snapshot* after a
failed workflow.  Two independent questions must be answered before the
snapshot can be handed to an auditor:

1. **Why did the run stop before a gate?** - answered from the committed
   public run/jobs snapshot by :mod:`product.audit_step_diagnosis` (no token,
   no job logs, no invented mechanism).
2. **Does the persisted snapshot carry a durable delta at all?** - answered
   from git refs alone.  A snapshot equal to its predecessor's commit is
   ``ZERO_DURABLE_DELTA``: the workflow's ``if: always()`` persist step
   published the unchanged tree after the failed producer step, so the ref
   exists but proves no work.

The module also records, read-only, whether this run has either half of
factory-wide requirement 4 (an independent audit gate and an accept commit),
and whether the producer wrote anything into the auditor namespace.  It never
writes ``results/audit/**``, never mints a gate, and never labels a run
accepted or rejected.

Usage
-----
    python3 product/resume_snapshot_diagnosis.py \\
        --run-id 40193974025 --predecessor-run-id 40188639817 \\
        --raw results/product/orchestration/CYCLE_40193974025_team_step_raw.json \\
        --out results/product/orchestration/CYCLE_40193974025_resume_diagnosis.json

Refs must already be available locally (the workflow fetches ``main``,
``lab/<lane>`` and the team ref).  The instrument never fetches, so an
offline reproduction is honest about a missing ref instead of silently
reaching the network.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product import audit_step_diagnosis as asd  # noqa: E402
from product import resume_chain_diagnosis as rcd  # noqa: E402

SCHEMA = "product-resume-snapshot-diagnosis/1"
ACCEPTED_REF = "origin/lab/product"


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT),
                          capture_output=True, text=True)


def _rev(ref: str) -> str | None:
    p = _git("rev-parse", "--verify", "--quiet", ref)
    if p.returncode != 0:
        return None
    return p.stdout.strip() or None


def _delta(snapshot_ref: str, predecessor_ref: str) -> dict[str, Any]:
    head = _rev(snapshot_ref)
    pred = _rev(predecessor_ref)
    out: dict[str, Any] = {
        "snapshot_ref": snapshot_ref,
        "snapshot_head": head,
        "predecessor_ref": predecessor_ref,
        "predecessor_head": pred,
    }
    if head is None or pred is None:
        out["classification"] = "REF_ABSENT"
        out["meaning"] = (
            "at least one ref is not available in this checkout, so the delta "
            "cannot be proven locally; this is UNREPRODUCED, never ZERO_DELTA "
            "and never a durable delta"
        )
        return out
    if head == pred:
        out["classification"] = "ZERO_DURABLE_DELTA"
        out["changed_files"] = 0
        out["changed_paths_sample"] = []
        out["meaning"] = (
            "the team ref points at the predecessor's exact commit: the "
            "producer added and changed nothing, and the always-run persist "
            "step published that unchanged tree. This is an orchestration "
            "outcome, NOT a product defect and NOT a verdict; refs alone cannot "
            "distinguish rc-67 zero-delta from a producer death."
        )
        return out
    paths = _git("diff", "--name-only", pred, head).stdout.splitlines()
    out["classification"] = "COMMITTED_DELTA"
    out["changed_files"] = len(paths)
    out["changed_paths_sample"] = paths[:20]
    out["meaning"] = (
        "the team ref carries a committed delta over its predecessor; the "
        "snapshot can be resumed and audited on its own bytes"
    )
    return out


def _accept_commit(run_id: str) -> dict[str, Any]:
    if _rev(ACCEPTED_REF) is None:
        return {"accepted_ref_present": False, "accept_commit": None}
    log = _git("log", ACCEPTED_REF, "--format=%H%x09%s").stdout.splitlines()
    needle = f"accept product cycle {run_id}"
    for line in log:
        sha, _, subject = line.partition("\t")
        if subject.strip() == needle:
            return {"accepted_ref_present": True, "accept_commit": sha,
                    "accept_subject": subject.strip()}
    return {"accepted_ref_present": True, "accept_commit": None}


def _audit_half(run_id: str) -> dict[str, Any]:
    audit_ref = f"origin/cycle/core/product/{run_id}/audit"
    audit_head = _rev(audit_ref)
    gate_rel = f"results/audit/product/CYCLE_{run_id}_GATE.json"
    if audit_head is None:
        return {
            "audit_ref": audit_ref,
            "audit_ref_present": False,
            "gate_file_present": (REPO_ROOT / gate_rel).exists(),
            "gate_verdict": None,
        }
    raw = _git("show", f"{audit_ref}:{gate_rel}")
    gate = None
    if raw.returncode == 0:
        try:
            gate = json.loads(raw.stdout)
        except json.JSONDecodeError:
            gate = {"unparseable": True}
    return {
        "audit_ref": audit_ref,
        "audit_ref_present": True,
        "audit_head": audit_head,
        "gate_file_present": gate is not None,
        "gate_verdict": (gate or {}).get("gate"),
        "safe_to_integrate": (gate or {}).get("safe_to_integrate"),
        "required_fixes": (gate or {}).get("required_fixes"),
    }


def _audit_namespace() -> dict[str, Any]:
    try:
        inv = rcd.audit_namespace_inventory()
    except Exception as exc:  # noqa: BLE001 - recorded, never invented
        return {"error": f"{type(exc).__name__}: {exc}"}
    return {
        "accepted_ref_present": _rev(ACCEPTED_REF) is not None,
        "producer_minted_unadjudicated_chain": inv[
            "producer_minted_unadjudicated_chain"
        ],
        "producer_minted_accepted_baseline_count": len(
            inv["producer_minted_accepted_baseline"]
        ),
    }


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def run(run_id: str, predecessor_run_id: str, raw_path: Path) -> dict[str, Any]:
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    orchestration = asd.classify(raw)
    delta = _delta(
        f"origin/cycle/core/product/{run_id}/team",
        f"origin/cycle/core/product/{predecessor_run_id}/team",
    )
    accept = _accept_commit(run_id)
    audit = _audit_half(run_id)
    accepted = bool(accept.get("accept_commit")) and bool(
        audit.get("gate_verdict") == "PASS"
        and audit.get("safe_to_integrate") is True
    )
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": run_id,
        "predecessor_run_id": predecessor_run_id,
        "raw_snapshot": _repo_relative(Path(raw_path)),
        "orchestration": orchestration,
        "durable_delta": delta,
        "adjudication": {
            "audit": audit,
            "accept": accept,
            "accepted": accepted,
            "status": "ACCEPTED" if accepted else "UNADJUDICATED",
            "product_defect": False,
            "verdict_written": False,
            "why_not_accepted": (
                None if accepted else
                "requirement 4 needs BOTH an independent PASS gate on the "
                "audit ref AND an accept commit on lab/product; at least one "
                "half is absent for this run"
            ),
        },
        "audit_namespace": _audit_namespace(),
        "claim_ceiling": (
            "This artifact classifies an orchestration outcome and a git-ref "
            "delta. It writes no gate, labels no run accepted or rejected, "
            "asserts no cause the committed run/jobs snapshot cannot show, and "
            "makes no product, legal or serve claim."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--predecessor-run-id", required=True)
    ap.add_argument("--raw", required=True,
                    help="committed run/jobs snapshot for --run-id")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    rec = run(args.run_id, args.predecessor_run_id, Path(args.raw))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "out": str(out),
        "orchestration": rec["orchestration"]["classification"],
        "durable_delta": rec["durable_delta"]["classification"],
        "adjudication": rec["adjudication"]["status"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
