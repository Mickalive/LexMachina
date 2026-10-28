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

When no public run/jobs snapshot was captured for the resumed run (for example
an operational resume dispatched straight from a failed run whose logs are not
reachable from the producer environment), omit ``--raw``: the instrument then
records ``RAW_SNAPSHOT_UNAVAILABLE`` / ``mechanism_unobserved`` instead of
inventing a cause, while still proving the durable-delta fact from git refs.
``--predecessor-ref`` (default ``origin/lab/product``) compares the snapshot
against the accepted head the failed run was dispatched from, which is the
right delta baseline for a resume run: comparing against the previous *team*
ref would count the accepted audit commit as if the failed run had produced it.

Refs must already be available locally for the default offline contract: the
instrument never fetches unless the caller explicitly passes
``--ensure-accepted-ref``.  That opt-in exists because the core-lane workflow's
repair path fetches only the team/audit refs (``core-lane.yml`` "Validate lane
and initialize accepted base") and the accepted-peer mount deliberately skips
the lane's own ``lab/<lane>`` branch, so every repair-round diagnosis recorded
``ACCEPTED_REF_ABSENT`` even when ``lab/product`` exists on the remote —
measured on the 40692326715 diagnosis against real remote head ``7be4480e``.
The fetch, when requested, is read-only into the remote-tracking ref
(``git fetch origin lab/product:refs/remotes/origin/lab/product``); it never
touches a local branch and its outcome (ok / failed / skipped) is recorded in
the artifact instead of being assumed.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product import audit_step_diagnosis as asd  # noqa: E402
from product import query_env  # noqa: E402
from product import resume_chain_diagnosis as rcd  # noqa: E402

SCHEMA = "product-resume-snapshot-diagnosis/1"
ACCEPTED_REF = "origin/lab/product"


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT),
                          capture_output=True, text=True)


def ensure_accepted_ref() -> dict[str, Any]:
    """Read-only fetch of the accepted-head remote-tracking ref, if asked for.

    Repair-round checkouts do not contain ``origin/lab/product`` (the workflow
    fetches only the team/audit refs and the peer mount skips the lane's own
    branch), which made every resume diagnosis report ``ACCEPTED_REF_ABSENT``
    even when the ref exists on the remote.  This helper records, never
    assumes: the returned dict always states whether a fetch was attempted and
    what it observed, and a failed fetch leaves the later classification at
    ``ACCEPTED_REF_ABSENT`` rather than guessing a head.
    """
    before = _rev(ACCEPTED_REF)
    if before is not None:
        return {"attempted": False, "reason": "ref_already_present",
                "accepted_head": before}
    remote = _git("fetch", "origin",
                  f"lab/product:refs/remotes/{ACCEPTED_REF}")
    after = _rev(ACCEPTED_REF)
    return {
        "attempted": True,
        "ok": after is not None,
        "method": "git-fetch-remote-tracking-only",
        "fetch_returncode": remote.returncode,
        "fetch_stderr_tail": (remote.stderr or "").strip().splitlines()[-2:],
        "accepted_head": after,
    }


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


def _accepted_head_relation(
    delta: dict[str, Any],
    fetch_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """State whether the snapshot is literally the accepted product head.

    Verified on run 40423595480: after cycle 40284658455 was accepted, the
    scheduler kept dispatching operational resumes whose team ref was the
    accepted head itself (``7be4480e``).  The always-run persist step then
    republished that unchanged tree, so the run had no producer delta it could
    ever add and the next resume could only repeat the no-op.  Recording that
    relation lets the next cycle choose a fresh question/delta instead of
    re-dispatching the identical resume (the rc-67 zero-delta failure class).
    """
    accepted_head = _rev(ACCEPTED_REF)
    snapshot_head = delta.get("snapshot_head")
    if accepted_head is None:
        out = {
            "accepted_ref": ACCEPTED_REF,
            "accepted_head": None,
            "snapshot_head": snapshot_head,
            "classification": "ACCEPTED_REF_ABSENT",
            "is_accepted_head": None,
        }
    elif snapshot_head is None:
        out = {
            "accepted_ref": ACCEPTED_REF,
            "accepted_head": accepted_head,
            "snapshot_head": None,
            "classification": "SNAPSHOT_REF_ABSENT",
            "is_accepted_head": None,
        }
    elif snapshot_head == accepted_head:
        out = {
            "accepted_ref": ACCEPTED_REF,
            "accepted_head": accepted_head,
            "snapshot_head": snapshot_head,
            "classification": "SNAPSHOT_IS_ACCEPTED_HEAD",
            "is_accepted_head": True,
        }
    else:
        out = {
            "accepted_ref": ACCEPTED_REF,
            "accepted_head": accepted_head,
            "snapshot_head": snapshot_head,
            "classification": "SNAPSHOT_NOT_ACCEPTED_HEAD",
            "is_accepted_head": False,
        }
    if fetch_record is not None:
        out["accepted_ref_fetch"] = fetch_record
    if out["classification"] == "SNAPSHOT_IS_ACCEPTED_HEAD":
        out["resume_action"] = (
            "NO_PRODUCER_DELTA_POSSIBLE: the snapshot already IS the accepted "
            "product head. Do not re-run the identical operational resume; "
            "choose a fresh executable question/delta for the lane."
        )
    elif out["classification"] == "SNAPSHOT_NOT_ACCEPTED_HEAD":
        out["resume_action"] = (
            "The snapshot diverges from the accepted head; verify the durable "
            "delta, finish the lane deliverable and make it audit-ready."
        )
    else:
        out["resume_action"] = (
            "The relation to the accepted head could not be proven from "
            "available refs; record REF_ABSENT rather than guessing."
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


CYCLE_TEST_RE = re.compile(r"product/tests/test_cycle_[A-Za-z0-9_]+\.py")


def _fresh_runner_probe() -> dict[str, Any]:
    """Probe the query runtime with ``-S`` to reproduce a fresh runner.

    The core-lane team job installs nothing, so a fresh runner has neither
    numpy nor scikit-learn.  ``python -S`` skips the user site where the
    bootstrap installs them, which makes that validation gap reproducible
    without touching the current environment.
    """
    code = (
        "import json,sys;"
        "sys.path.insert(0, '.');"
        "from product import query_env;"
        "print(json.dumps(query_env.probe()))"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-S", "-c", code], cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=60, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        return {"ok": None, "error": f"{type(exc).__name__}: {exc}"}
    probe: dict[str, Any] = {}
    if proc.stdout.strip():
        try:
            probe = json.loads(proc.stdout)
        except json.JSONDecodeError:
            probe = {}
    return {
        "ok": probe.get("ok"),
        "missing": probe.get("missing"),
        "exit_code": proc.returncode,
        "stderr_tail": (proc.stderr or "").strip().splitlines()[-3:],
        "meaning": (
            "python -S skips the user site used by bootstrap_query_env.sh; "
            "missing modules here are the fresh-runner validation gap, not a "
            "product defect"
        ),
    }


def _validation_findings(run_id: str, predecessor_run_id: str) -> dict[str, Any]:
    """Reproduce the validation gaps that can stop a snapshot before its gate.

    This is deliberately narrow and offline.  It does not infer a provider
    mechanism; it records three checkable things a resume must repair:

    * a ``product/tests/test_cycle_*.py`` path the snapshot's own report claims
      but the snapshot did not commit;
    * an audit-readiness dossier produced with its mandatory re-runs skipped;
    * the pinned query runtime's presence on the machine that consumes the
      snapshot (the core-lane team job installs nothing, so a fresh runner
      fails with ModuleNotFoundError before any product claim can be tested).
    """
    candidates = [
        REPO_ROOT / "reports" / "product" / f"CYCLE_{run_id}.md",
        REPO_ROOT / "reports" / "product" / f"CYCLE_{predecessor_run_id}.md",
    ]
    claimed_tests: list[dict[str, Any]] = []
    seen: set[str] = set()
    for report in candidates:
        if not report.is_file():
            continue
        for rel in sorted(set(CYCLE_TEST_RE.findall(
                report.read_text(encoding="utf-8", errors="replace")))):
            if rel in seen:
                continue
            seen.add(rel)
            claimed_tests.append({
                "path": rel,
                "claimed_by_report": _repo_relative(report),
                "present": (REPO_ROOT / rel).is_file(),
            })

    dossiers = [
        REPO_ROOT / "results" / "product" / "audit_readiness"
        / f"CYCLE_{rid}_audit_readiness.json"
        for rid in (run_id, predecessor_run_id) if rid
    ]
    dossier_summary = []
    for dossier in dossiers:
        if not dossier.is_file():
            continue
        try:
            data = json.loads(dossier.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        dossier_summary.append({
            "path": _repo_relative(dossier),
            "overall_status": data.get("overall_status"),
            "skipped_checks": data.get("skipped_checks") or [],
            "failed_checks": data.get("failed_checks") or [],
        })

    fresh = _fresh_runner_probe()

    historical = sorted(
        _repo_relative(path)
        for path in (REPO_ROOT / "results" / "product" / "reality_check").glob(
            "*missing-deps*.json")
    )
    probe = query_env.probe()
    return {
        "claimed_cycle_tests": claimed_tests,
        "missing_claimed_cycle_tests": [
            row["path"] for row in claimed_tests if not row["present"]
        ],
        "audit_readiness_dossiers": dossier_summary,
        "dossiers_with_skipped_mandatory_reruns": [
            row["path"] for row in dossier_summary if row["skipped_checks"]
        ],
        "runtime_preflight": {
            "ok": probe["ok"],
            "missing": probe["missing"],
            "installed": probe["installed"],
            "pinned": probe["pinned"],
            "remedy": probe["remedy"],
            "workflow_gap": probe["workflow_gap"],
            "fresh_runner_no_site_probe": fresh,
        },
        "historical_missing_dependency_artifacts": historical[:5],
        "meaning": (
            "These are reproducible validation gaps, not a provider/auth "
            "mechanism and not a product verdict. Missing deps and a missing "
            "claimed test make a green snapshot fail its own self-check on a "
            "fresh runner; they are repaired by the resuming cycle, never by "
            "weakening a frozen bar."
        ),
    }


def _orchestration_without_raw(raw_path: Path | None) -> dict[str, Any]:
    """Honest placeholder when no public run/jobs snapshot was captured.

    The missing artefact is recorded as such.  A git-ref delta and the absence
    of an audit half still prove a great deal, but they cannot name a provider,
    auth or quantum mechanism, so none is invented.
    """
    return {
        "schema": asd.SCHEMA,
        "classification": "RAW_SNAPSHOT_UNAVAILABLE",
        "mechanism_unobserved": True,
        "raw_snapshot": _repo_relative(raw_path) if raw_path else None,
        "meaning": (
            "No committed run/jobs snapshot exists for this failed run in the "
            "producer checkout (job logs require admin rights). The durable "
            "delta and the absent audit half are still proven from git refs; "
            "the provider/auth/timeout mechanism is NOT claimed."
        ),
    }


def run(
    run_id: str,
    predecessor_run_id: str = "",
    raw_path: Path | None = None,
    *,
    predecessor_ref: str | None = None,
    ensure_accepted: bool = False,
) -> dict[str, Any]:
    fetch_record: dict[str, Any] | None = None
    if ensure_accepted:
        # Must happen before any _rev(ACCEPTED_REF) read so a repair-round
        # checkout can resolve the accepted head it was never fetch-granted.
        fetch_record = ensure_accepted_ref()
    orchestration = (
        asd.classify(json.loads(Path(raw_path).read_text(encoding="utf-8")))
        if raw_path is not None
        else _orchestration_without_raw(None)
    )
    if predecessor_ref:
        delta = _delta(f"origin/cycle/core/product/{run_id}/team", predecessor_ref)
    elif predecessor_run_id:
        delta = _delta(
            f"origin/cycle/core/product/{run_id}/team",
            f"origin/cycle/core/product/{predecessor_run_id}/team",
        )
    else:
        delta = _delta(f"origin/cycle/core/product/{run_id}/team", ACCEPTED_REF)
    accept = _accept_commit(run_id)
    audit = _audit_half(run_id)
    accepted = bool(accept.get("accept_commit")) and bool(
        audit.get("gate_verdict") == "PASS"
        and audit.get("safe_to_integrate") is True
    )
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": run_id,
        "predecessor_run_id": predecessor_run_id,
        "raw_snapshot": _repo_relative(Path(raw_path)) if raw_path else None,
        "orchestration": orchestration,
        "durable_delta": delta,
        "accepted_head_relation": _accepted_head_relation(delta, fetch_record),
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
        "validation_findings": _validation_findings(run_id, predecessor_run_id),
        "claim_ceiling": (
            "This artifact classifies an orchestration outcome and a git-ref "
            "delta. It writes no gate, labels no run accepted or rejected, "
            "asserts no cause the committed run/jobs snapshot cannot show, and "
            "makes no product, legal or serve claim."
        ),
    }
    if raw_path is None:
        # Only the raw-free mode needs to name the delta baseline; preserving
        # the historical raw-mode record byte shape keeps accepted cycle tests
        # reproducible.
        record["predecessor_ref"] = predecessor_ref or ACCEPTED_REF
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--predecessor-run-id", default="",
                    help="previous cycle's team ref (optional when --predecessor-ref is given)")
    ap.add_argument("--predecessor-ref", default="",
                    help="explicit git ref for the durable-delta baseline (default origin/lab/product)")
    ap.add_argument("--raw", default=None,
                    help="committed run/jobs snapshot for --run-id; omit when unavailable")
    ap.add_argument("--ensure-accepted-ref", action="store_true",
                    help="read-only fetch origin/lab/product into the remote-tracking "
                         "ref when absent (repair-round checkouts lack it); the "
                         "attempt and outcome are recorded in the artifact")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if not args.predecessor_run_id and not args.predecessor_ref:
        args.predecessor_ref = ACCEPTED_REF
    rec = run(
        args.run_id,
        args.predecessor_run_id,
        Path(args.raw) if args.raw else None,
        predecessor_ref=args.predecessor_ref or None,
        ensure_accepted=args.ensure_accepted_ref,
    )
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
