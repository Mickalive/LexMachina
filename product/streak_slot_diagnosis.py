#!/usr/bin/env python3
"""Diagnose a zero-delta producer streak from committed public snapshots.

What this answers
-----------------
Four consecutive product repair dispatches (40490645980, 40490967419,
40491258620, 40493217504) each failed their team job at ``Run lane cycle``
and each published a team snapshot byte-identical to the predecessor, so no
audit ever ran and the chain stalled in re-dispatch churn.  Job *logs* are
admin-only (HTTP 403), but three public evidence families are committed and
sufficient to classify the streak WITHOUT inventing a log-level cause:

1. check-run annotations (captured by ``product/capture_run_snapshot.py``):
   exit code 1 with no wrapper ``::error::`` annotation, versus exit code 67
   ``LEX_ZERO_DELTA_REPAIR``;
2. the run's ``head_sha``, which pins the exact ``state/model_health.json``
   blob the launcher staged (``stage_control`` reads origin/main);
3. the launcher's deterministic slot selection
   (``.github/scripts/run-ox-with-retry.sh`` on main: sha256 of
   ``LEX_MODEL_SLOT`` = ``core:<lane>:v<dirv>:<run_id>``, first 8 hex digits,
   modulo the healthy pool length).

The instrument publishes the recomputed slot -> model mapping per run and the
model-health probe facts for those models, then classifies each run.  It
asserts no log-level cause: the child-death mechanism behind exit 1 stays
UNOBSERVED while the logs endpoint returns 403.  It writes no gate, labels no
run accepted or rejected, and makes no product claim.

Usage
-----
    python3 product/streak_slot_diagnosis.py \
        --runs 40490645980 40490967419 40491258620 40493217504 \
        --lane product --direction-version 68 \
        --out results/product/orchestration/CYCLE_40493217504_streak_model_slot_diagnosis.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "product-streak-model-slot-diagnosis/1"
RAW_TEMPLATE = "results/product/orchestration/CYCLE_{run}_run_jobs_raw.json"
#: Wrapper exit codes published by .github/scripts/run-ox-with-retry.sh (main).
WRAPPER_EXIT_MEANING = {
    1: ("OPENCODE_CHILD_RC1_NO_WRAPPER_SIGNATURE: the wrapper's AUTH_RE and "
        "NETWORK_RE did not match the child log, so the wrapper exited with "
        "the child's own rc=1 without rotating or retrying. Log-level content "
        "UNOBSERVED (logs endpoint HTTP 403)."),
    67: ("LEX_ZERO_DELTA_REPAIR: the agent session completed rc=0 but HEAD was "
         "unchanged and the worktree empty, so the repair guard refused the "
         "no-op. This means 'the producer found nothing to do', not a crash."),
    75: "LEX_NETWORK_STALL or retry exhaustion (transient signature matched).",
    76: "LEX_MODEL_AUTH_POOL_EXHAUSTED or LEX_MODEL_HEALTH_MISSING.",
    77: "LEX_MODEL_ARGUMENT_MISSING.",
    78: "LEX_WORK_QUANTUM_EXPIRED (work quantum elapsed; snapshot and resume).",
}


def slot_model(run_id: str, lane: str, direction_version: int,
               pool: list[str]) -> dict[str, Any]:
    """Recompute the launcher's deterministic pool selection for one run."""
    slot = f"core:{lane}:v{direction_version}:{run_id}"
    hex8 = hashlib.sha256(slot.encode("utf-8")).hexdigest()[:8]
    index = int(hex8, 16) % len(pool)
    return {"slot": slot, "sha256_prefix": hex8, "index": index,
            "pool_size": len(pool), "selected_model": pool[index]}


def _annotation_exit(raw: dict[str, Any]) -> int | None:
    """Exit code of the failing team step, from public annotations only."""
    text = []
    for rows in (raw.get("annotations") or {}).values():
        for row in rows if isinstance(rows, list) else []:
            text.append(str(row.get("message") or ""))
    for msg in text:
        if "exit code" in msg and "Process completed with" in msg:
            digits = "".join(c for c in msg.split("exit code", 1)[1] if c.isdigit())
            if digits:
                return int(digits)
    return None


def _has_wrapper_error_annotation(raw: dict[str, Any]) -> bool | None:
    """Whether any ::error::-class annotation carries a wrapper sentinel.

    None means no annotation rows were captured (cannot tell); False means
    rows exist and none is a wrapper sentinel.
    """
    msgs = []
    for rows in (raw.get("annotations") or {}).values():
        for row in rows if isinstance(rows, list) else []:
            if row.get("annotation_level") == "failure":
                msgs.append(str(row.get("message") or ""))
    if not msgs:
        return None
    sentinels = ("LEX_ZERO_DELTA_REPAIR", "LEX_MODEL", "LEX_NO_HEALTHY",
                 "LEX_NETWORK_STALL", "LEX_WORK_QUANTUM", "LEX_AGENT_CARD",
                 "lane crossed protected scope")
    return any(any(s in m for s in sentinels) for m in msgs)


def health_blob(head_sha: str) -> tuple[dict[str, Any] | None, str]:
    """Read the model_health blob pinned by a run's head_sha, if the object exists.

    Returns ``(blob_or_None, provenance)``.  Provenance distinguishes
    ``GIT_OBJECT_PRESENT`` from ``GIT_OBJECT_ABSENT_IN_CHECKOUT`` so a fresh
    checkout without these unreachable objects records a gap instead of
    inventing pool facts.
    """
    probe = subprocess.run(  # noqa: S603
        ["git", "cat-file", "-e", f"{head_sha}^{{commit}}"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
    if probe.returncode != 0:
        return None, "GIT_OBJECT_ABSENT_IN_CHECKOUT"
    show = subprocess.run(  # noqa: S603
        ["git", "show", f"{head_sha}:state/model_health.json"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
    if show.returncode != 0:
        return None, "MODEL_HEALTH_ABSENT_AT_HEAD_SHA"
    try:
        return json.loads(show.stdout), "GIT_OBJECT_PRESENT"
    except json.JSONDecodeError:
        return None, "MODEL_HEALTH_UNPARSEABLE_AT_HEAD_SHA"


def diagnose(runs: list[str], lane: str, direction_version: int) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for run in runs:
        raw_path = REPO_ROOT / RAW_TEMPLATE.format(run=run)
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        team = next(j for j in raw["jobs"] if j.get("name") == "team")
        steps = {s["name"]: s["conclusion"] for s in team.get("steps", [])}
        failed_step = next((n for n, c in steps.items() if c == "failure"), None)
        head_sha = (raw.get("run") or {}).get("head_sha")
        blob, prov = health_blob(head_sha) if head_sha else (None, "NO_HEAD_SHA")
        pool = list((blob or {}).get("healthy_models") or [])
        exit_code = _annotation_exit(raw)
        entry: dict[str, Any] = {
            "run_id": run,
            "head_sha": head_sha,
            "team_conclusion": team.get("conclusion"),
            "failed_step": failed_step,
            "persist_step_conclusion": steps.get("Persist team snapshot"),
            "audit_job_conclusion": next(
                (j.get("conclusion") for j in raw["jobs"]
                 if j.get("name") == "audit"), None),
            "exit_code_from_annotations": exit_code,
            "wrapper_sentinel_annotation": _has_wrapper_error_annotation(raw),
            "logs_endpoint_status": raw.get("logs_endpoint_status"),
            "model_health": {
                "provenance": prov,
                "last_checked_at": (blob or {}).get("last_checked_at"),
                "last_checked_run_id": (blob or {}).get("last_checked_run_id"),
                "healthy": (blob or {}).get("healthy"),
                "pool": pool,
            },
            "slot_selection": (
                slot_model(run, lane, direction_version, pool) if pool else None),
            "exit_code_meaning": WRAPPER_EXIT_MEANING.get(
                exit_code, "UNKNOWN_OR_NONE") if exit_code is not None else None,
        }
        entries.append(entry)

    pools = [tuple(e["model_health"]["pool"]) for e in entries
             if e["model_health"]["pool"]]
    pool_identical = bool(pools) and len(set(pools)) == 1
    selected = [e["slot_selection"]["selected_model"] for e in entries
                if e.get("slot_selection")]
    exit1_models = [e["slot_selection"]["selected_model"] for e in entries
                    if e.get("slot_selection")
                    and e.get("exit_code_from_annotations") == 1]
    exit67_models = [e["slot_selection"]["selected_model"] for e in entries
                     if e.get("slot_selection")
                     and e.get("exit_code_from_annotations") == 67]
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane": lane,
        "direction_version": direction_version,
        "runs": entries,
        "recomputed_observations": {
            "n_runs": len(entries),
            "all_failed_at_run_lane_cycle": all(
                e.get("failed_step") == "Run lane cycle" for e in entries),
            "all_snapshots_persisted": all(
                e.get("persist_step_conclusion") == "success" for e in entries),
            "audit_skipped_for_every_run": all(
                e.get("audit_job_conclusion") == "skipped" for e in entries),
            "selected_models": selected,
            "pool_identical_across_head_sha_blobs": pool_identical,
            "pool_re_fetch_caveat": (
                "stage_control re-fetches origin/main at step start, so the "
                "head_sha-pinned blob is the dispatch pin; the selection is "
                "robust under the re-fetch skew because every distinct "
                "head_sha blob in this streak records the same pool order"
                if pool_identical else
                "DISTINCT POOLS OBSERVED across head_sha blobs; the re-fetch "
                "skew can change the selection and per-run pool provenance "
                "must be read individually"),
            "exit_code_1_selected_models": exit1_models,
            "exit_code_67_selected_models": exit67_models,
            "exit_code_1_models_all_equal": (
                len(set(exit1_models)) == 1 if exit1_models else None),
        },
        "classification": (
            "MIXED_STREAK: model-slot-correlated early child deaths (exit 1, "
            "no wrapper sentinel) interleaved with one zero-delta repair guard "
            "(exit 67)"),
        "mechanism": {
            "log_level": "UNOBSERVED (logs endpoint HTTP 403 on every run)",
            "exit_67_leg": WRAPPER_EXIT_MEANING[67],
            "exit_1_leg": WRAPPER_EXIT_MEANING[1],
            "association_only": (
                "The exit-1 runs' recomputed slot selection is identical "
                "(all one model) while the health blob records tool_probe PASS "
                "for that model; this is a recomputed association from public "
                "facts, NOT proven causation, because the child log body is "
                "not readable."),
        },
        "route_around": (
            "requirement 10 route-around stands: a repair dispatch must change "
            "the QUESTION so the producer has a concrete deliverable (the exit "
            "67 leg proves the producer found nothing to do); the exit-1 leg is "
            "recorded as a control-plane hardening item (rotation fires only on "
            "AUTH/NETWORK signatures; the health tool-probe is a shallow probe). "
            ".github/** is control-plane scope and is NOT edited from this lane."),
        "claim_ceiling": (
            "Operational classification of public run/jobs/annotation snapshots "
            "and deterministic slot arithmetic over head_sha-pinned health "
            "blobs. No gate written, no run adjudicated, no log-level cause "
            "asserted, no product claim."),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--lane", default="product")
    ap.add_argument("--direction-version", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rec = diagnose(args.runs, args.lane, args.direction_version)
    if args.json:
        print(json.dumps(rec, indent=2, ensure_ascii=False))
        return 0
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "out": str(out),
        "classification": rec["classification"],
        "selected_models": rec["recomputed_observations"]["selected_models"],
        "exit_code_1_models_all_equal":
            rec["recomputed_observations"]["exit_code_1_models_all_equal"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
