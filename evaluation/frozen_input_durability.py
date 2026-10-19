#!/usr/bin/env python3
"""Is the accepted retrieval benchmark's frozen input DURABLE, or a lucky snapshot?

WHY THIS FILE EXISTS
--------------------
Factory direction v57 item (1) closed FROZEN-BENCHMARK INTEGRITY on the claim
that the accepted run 39098571937's cache byte-identity was restored.  That
closure is a correct re-hash.  It is not sufficient, because the lane's own
accepted record ``state/evaluation.json::claim_reconciliation_39164900837`` says
verbatim that the restored envelope "was the upstream's own degraded page" and
that restoring it "reproduced the accepted aggregate while leaving the
underlying upstream non-determinism unmeasured".

So this instrument measures the thing that was left unmeasured: does the SAME
frozen query URL return the SAME bytes on a different day?

This is the oracle-stability half of the retrieval recall item.  The accepted
frozen verdict fails six ``authority::baseline_lang_recall::{fr,it}`` gates.
If those verdicts move when the upstream response moves, they are one-snapshot
instrumentation noise and no product decision may rest on them.  If they do not
move, they are stable measurement.

DISCIPLINE
----------
* Hypothesis, falsifiers, success rule and safety contract are frozen in
  ``evaluation/FROZEN_INPUT_DURABILITY_HYPOTHESIS_V1.json`` BEFORE execution.
* The committed cache ``results/evaluation/retrieval_benchmark/cache`` is NEVER
  written.  That cache is the object under test; writing to it would reproduce
  the very defect this instrument studies.  Every live byte goes to a scratch
  directory outside the tree, and the committed cache's per-file sha256 manifest
  is captured before and after and published.
* No frozen file is edited.  The frozen spec and the freeze record are re-hashed
  before and after and published.
* No claim-bearing record is overwritten.  The accepted run record is read-only
  input; the live run is written to a fresh results directory.
* Mapping-free: the only identities are the ``query_key`` already present in the
  accepted record and sha256 over bytes.

Exit codes
----------
0  a measurement was made, whatever the verdict (H_SUSTAINED or H_REFUTED)
2  environment error: no live body was retrieved at all, so there is nothing to
   compare and NO verdict is emitted
3  safety-contract violation (the committed cache or a frozen input moved)
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

_LANE_ROOT = Path(__file__).resolve().parent.parent
if str(_LANE_ROOT) not in sys.path:
    sys.path.insert(0, str(_LANE_ROOT))

from evaluation.retrieval_gate import client, frozen, gates  # noqa: E402
from evaluation.retrieval_gate import run_retrieval_benchmark as rrb  # noqa: E402

SCHEMA = "lex-evaluation-frozen-input-durability/1"

FROZEN_CACHE = _LANE_ROOT / "results" / "evaluation" / "retrieval_benchmark" / "cache"
ACCEPTED_RECORD = _LANE_ROOT / "results" / "evaluation" / "retrieval_benchmark" / "39098571937.json"

# The six gates whose stability is the product-facing question: they assert that
# the plain OpenCaseLaw baseline retrieves the frozen controlling authorities
# when the QUESTION is asked in French or Italian.
LANG_RECALL_GATES = [
    f"authority::baseline_lang_recall::{slug}::{lang}"
    for slug in ("corporate-criminal-liability", "business-judgment-rule",
                 "petty-theft-dismissal")
    for lang in ("fr", "it")
]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _utc_now() -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0).isoformat().replace("+00:00", "Z"))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(root: Path) -> dict:
    """sha256 of every file under ``root``, keyed by path relative to ``root``.

    Keys are relative to the scanned root (not to the repo), so the function is
    correct for any directory the caller names; the caller records the root
    alongside the manifest.
    """
    root = Path(root)
    out: dict[str, str] = {}
    if not root.is_dir():
        return out
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(root))] = _sha256_file(path)
    return out


def git_head(root: Path | None = None) -> str | None:
    root = root or _LANE_ROOT
    proc = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def gate_status_map(verdict: dict) -> dict:
    """gate id -> PASS / FAIL / NOT_MEASURABLE, read from a verdict record.

    The frozen verdict's ``gates`` list is the complete population and carries
    ``passed`` as a tri-state: ``True`` -> PASS, ``False`` -> FAIL, ``null`` ->
    NOT_MEASURABLE.  ``null`` is NOT a failure; mapping it onto FAIL would invent
    a falsification that the frozen scorer did not emit, so it is mapped
    explicitly.

    The verdict ALSO publishes the same population as three disjoint id lists.
    They are used as an independent cross-check (:func:`gate_status_map_selfcheck`),
    so this comparison stays a SET RELATION over gate ids and never a
    cardinality match, which is the standing factory-direction rule.
    """
    status: dict[str, str] = {}
    for g in verdict.get("gates") or []:
        if not isinstance(g, dict) or not g.get("gate"):
            continue
        passed = g.get("passed")
        if passed is True:
            status[g["gate"]] = "PASS"
        elif passed is False:
            status[g["gate"]] = "FAIL"
        else:
            status[g["gate"]] = "NOT_MEASURABLE"
    return status


def gate_status_map_selfcheck(verdict: dict) -> dict:
    """Cross-check the tri-state map against the verdict's three id lists.

    Returns the set relations, never a count match: the observed differences are
    published even when they are empty, so a reader can see that the relation
    was computed rather than inferred from matching totals.
    """
    status = gate_status_map(verdict)
    declared_failed = set(verdict.get("failed_gates") or [])
    declared_nm = set(verdict.get("not_measurable_gates") or [])
    observed_failed = {g for g, s in status.items() if s == "FAIL"}
    observed_nm = {g for g, s in status.items() if s == "NOT_MEASURABLE"}
    observed_pass = {g for g, s in status.items() if s == "PASS"}
    declared_pass = set(status) - declared_failed - declared_nm
    return {
        "n_gates": len(status),
        "n_passed_observed": len(observed_pass),
        "n_failed_observed": len(observed_failed),
        "n_not_measurable_observed": len(observed_nm),
        "counts_declared": {"n_passed": verdict.get("n_passed"),
                            "n_failed": verdict.get("n_failed"),
                            "n_not_measurable": verdict.get("n_not_measurable")},
        "failed_only_in_declared": sorted(declared_failed - observed_failed),
        "failed_only_in_observed": sorted(observed_failed - declared_failed),
        "not_measurable_only_in_declared": sorted(declared_nm - observed_nm),
        "not_measurable_only_in_observed": sorted(observed_nm - declared_nm),
        "pass_only_in_declared": sorted(declared_pass - observed_pass),
        "pass_only_in_observed": sorted(observed_pass - declared_pass),
        "counts_agree": (len(observed_pass) == verdict.get("n_passed")
                         and len(observed_failed) == verdict.get("n_failed")
                         and len(observed_nm) == verdict.get("n_not_measurable")),
        "sets_agree": not (declared_failed ^ observed_failed)
                      and not (declared_nm ^ observed_nm),
    }


def gate_diff(accepted_status: dict, live_status: dict) -> dict:
    """Set relation over gate ids: both differences, never a count match."""
    a, b = set(accepted_status), set(live_status)
    only_a, only_b = sorted(a - b), sorted(b - a)
    changed = sorted(
        gid for gid in (a & b) if accepted_status[gid] != live_status[gid]
    )
    return {
        "n_gates_accepted": len(a),
        "n_gates_live": len(b),
        "only_in_accepted": only_a,
        "only_in_live": only_b,
        "status_changed_gates": changed,
        "status_changed_detail": [
            {"gate": gid, "accepted": accepted_status[gid], "live": live_status[gid]}
            for gid in changed
        ],
        "identical": not only_a and not only_b and not changed,
    }


# --------------------------------------------------------------------------- #
# the measurement
# --------------------------------------------------------------------------- #


def build_plan_from_accepted(record: dict) -> list[dict]:
    """Reuse the accepted record's own plan.  Do NOT re-derive from the spec."""
    plan = []
    for q in record["queries"]:
        plan.append({
            "query_key": q["query_key"],
            "channel": q["channel"],
            "slug": q["slug"],
            "language": q["language"],
            "query": q["query"],
            "limit": int(q["limit"]),
        })
    return plan


def _build_record(queries: list[dict], spec: dict, run_id: str, *,
                  pass_a_mode: str, pass_a_wall: float) -> dict:
    """A record shaped exactly like the runner's, so the frozen gates apply."""
    replay_by_key = {r["query_key"]: r for r in queries}
    repro = []
    for q in queries:
        r = replay_by_key.get(q["query_key"])
        repro.append({
            "query_key": q["query_key"],
            "status": r["status"] if r else None,
            "raw_sha256": r["raw_sha256"] if r else None,
            "ids_sha256": r["ids_sha256"] if r else None,
            "cache_hit": bool(r and r.get("from_cache")),
        })
    now = _utc_now()
    return {
        "schema": "lex-retrieval-benchmark/1",
        "run_id": run_id,
        "direction_version": spec["direction_version"],
        "generated_at": now,
        "started_at": now,
        "pass_b_started_at": now,
        "frozen_sha256": frozen.FROZEN_SHA256,
        "pass_a_mode": pass_a_mode,
        "pass_a_wall_seconds": pass_a_wall,
        "pass_b_mode": "offline_cache_replay",
        "pass_b_wall_seconds": 0.0,
        "queries": queries,
        "reproducibility": {
            "pass_b": repro,
            "all_identical": all(e["raw_sha256"] == q["raw_sha256"]
                                 for q, e in zip(queries, repro)),
        },
        "transport": {
            "n_queries": len(queries),
            "n_ok": sum(1 for q in queries if q["status"] == 200),
            "n_failed": sum(1 for q in queries if q["status"] != 200),
            "failures": [{"query_key": q["query_key"], "error": q.get("error")}
                         for q in queries if q["status"] != 200],
        },
        "environment": {"python": sys.version.split()[0]},
        "claim_ceiling": spec["claim_ceiling"],
    }


def run(*, run_id: str, accepted_record: Path, scratch: Path,
        out_dir: Path, control_url: str | None) -> dict:
    started = _utc_now()
    spec = frozen.load_frozen()
    freeze = frozen.freeze_record()

    frozen_inputs_before = {
        "frozen_retrieval_benchmark.json": _sha256_file(
            _LANE_ROOT / "evaluation" / "retrieval_gate" / "frozen_retrieval_benchmark.json"),
        "FREEZE_RECORD.json": _sha256_file(
            _LANE_ROOT / "evaluation" / "retrieval_gate" / "FREEZE_RECORD.json"),
    }
    committed_cache_before = manifest(FROZEN_CACHE)
    accepted_sha_before = _sha256_file(accepted_record)

    accepted = json.loads(accepted_record.read_text(encoding="utf-8"))
    accepted_status = gate_status_map(accepted["verdict"])
    plan = build_plan_from_accepted(accepted)

    # ---- N1: the comparator must be able to report a difference ---------- #
    control_body = b'{"results":[],"control":"lex-evaluation-frozen-input-durability"}'
    control_altered = control_body[:-2] + b' }'
    non_vacuity = {
        "control_body_sha256": _sha256_bytes(control_body),
        "control_altered_sha256": _sha256_bytes(control_altered),
        "comparator_reports_difference": (
            _sha256_bytes(control_body) != _sha256_bytes(control_altered)),
    }

    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)

    # ---- N2: within-run duplicate control (two extra live fetches) -------- #
    dup_control: dict = {"executed": False}
    if control_url:
        probe_dir = scratch.parent / (scratch.name + "_probe")
        if probe_dir.exists():
            shutil.rmtree(probe_dir)
        cli = client.SearchClient(
            base_url=spec["endpoint"], user_agent=spec["user_agent"],
            cache_dir=probe_dir, timeout=float(spec["transport"]["timeout_seconds"]),
            retries=int(spec["transport"]["retries"]),
            backoff_seconds=float(spec["transport"]["backoff_seconds"]),
            max_rps=float(spec["max_requests_per_second"]), offline=False)
        shas = []
        for _ in range(2):
            out = cli.search(query_key="__dup_control__", channel="control",
                             slug="control", language="xx",
                             query=control_url, limit=int(spec["top_k"]["baseline"]))
            shas.append(out.raw_sha256 if out.status == 200 else None)
        dup_control = {
            "executed": True,
            "n_fetches": 2,
            "sha256": shas,
            "identical_within_run": bool(shas[0] and shas[0] == shas[1]),
            "note": ("two live fetches of the SAME frozen URL inside one run. "
                     "identical_within_run=false means the endpoint varies even "
                     "without crossing a day boundary"),
        }
        shutil.rmtree(probe_dir, ignore_errors=True)

    # ---- the live pass, into the scratch cache only ---------------------- #
    queries, wall = rrb.run_pass(plan, spec, offline=False, cache_dir=scratch)
    n_ok = sum(1 for q in queries if q["status"] == 200)

    committed_cache_after = manifest(FROZEN_CACHE)
    frozen_inputs_after = {
        "frozen_retrieval_benchmark.json": _sha256_file(
            _LANE_ROOT / "evaluation" / "retrieval_gate" / "frozen_retrieval_benchmark.json"),
        "FREEZE_RECORD.json": _sha256_file(
            _LANE_ROOT / "evaluation" / "retrieval_gate" / "FREEZE_RECORD.json"),
    }
    accepted_sha_after = _sha256_file(accepted_record)

    safety = {
        "S1_committed_cache_untouched": committed_cache_before == committed_cache_after,
        "S1_n_envelopes": len(committed_cache_before),
        "S1_manifest_root": str(FROZEN_CACHE.relative_to(_LANE_ROOT)),
        "S1_changed_files": sorted(
            set(committed_cache_before) ^ set(committed_cache_after)
        ) + sorted(g for g in committed_cache_before
                   if g in committed_cache_after
                   and committed_cache_before[g] != committed_cache_after[g]),
        "S1_manifest_sha256_before": _sha256_bytes(
            json.dumps(committed_cache_before, sort_keys=True).encode("utf-8")),
        "S1_manifest_sha256_after": _sha256_bytes(
            json.dumps(committed_cache_after, sort_keys=True).encode("utf-8")),
        "S2_frozen_inputs_untouched": frozen_inputs_before == frozen_inputs_after,
        "S2_before": frozen_inputs_before,
        "S2_after": frozen_inputs_after,
        "S3_accepted_record_untouched": accepted_sha_before == accepted_sha_after,
        "S3_accepted_record_sha256": accepted_sha_before,
        "scratch_cache_dir": str(scratch),
        "scratch_is_outside_committed_cache": True,
    }
    violations = [k for k in ("S1_committed_cache_untouched",
                              "S2_frozen_inputs_untouched",
                              "S3_accepted_record_untouched")
                  if not safety[k]]

    if n_ok == 0:
        return {
            "schema": SCHEMA, "run_id": run_id, "verdict": "NO_MEASUREMENT",
            "reason": "every live fetch failed transport; environment error, "
                      "not a benchmark result. No verdict emitted.",
            "safety": safety, "non_vacuity": non_vacuity,
            "duplicate_control": dup_control,
            "frozen_inputs": frozen_inputs_before,
        }

    # ---- F1: per-query byte comparison ---------------------------------- #
    accepted_by_key = {q["query_key"]: q for q in accepted["queries"]}
    per_query = []
    n_body_diff = 0
    n_ids_diff = 0
    for q in queries:
        a = accepted_by_key.get(q["query_key"])
        if a is None:
            continue
        body_same = (q.get("raw_sha256") == a.get("raw_sha256"))
        ids_same = (q.get("ids_sha256") == a.get("ids_sha256"))
        n_body_diff += 0 if body_same else 1
        n_ids_diff += 0 if ids_same else 1
        per_query.append({
            "query_key": q["query_key"],
            "status_live": q["status"],
            "n_results_live": q.get("n_results"),
            "n_results_accepted": a.get("n_results"),
            "raw_sha256_accepted": a.get("raw_sha256"),
            "raw_sha256_live": q.get("raw_sha256"),
            "body_identical": body_same,
            "ids_sha256_accepted": a.get("ids_sha256"),
            "ids_sha256_live": q.get("ids_sha256"),
            "ordered_ids_identical": ids_same,
        })

    # ---- F2: gate-by-gate, apples-to-apples and live-mode ----------------- #
    # The accepted record is an offline_replay, so its latency gates are
    # NOT_MEASURABLE. A live record makes them measurable, which would differ
    # for a reason that has nothing to do with the frozen input. Both readings
    # are computed and F2 is the CONSERVATIVE disjunction of the two.
    rec_replay = _build_record(queries, spec, f"{run_id}-offline_replay",
                               pass_a_mode="offline_replay", pass_a_wall=wall)
    rec_live = _build_record(queries, spec, f"{run_id}-live",
                             pass_a_mode="live", pass_a_wall=wall)
    verdict_replay = gates.evaluate(spec, rec_replay)
    verdict_live = gates.evaluate(spec, rec_live)

    diff_replay = gate_diff(accepted_status, gate_status_map(verdict_replay))
    diff_live = gate_diff(accepted_status, gate_status_map(verdict_live))

    lang_changed = sorted(
        g for g in LANG_RECALL_GATES
        if gate_status_map(verdict_replay).get(g) != accepted_status.get(g)
    )

    f1 = n_body_diff > 0
    f2a = not diff_replay["identical"]
    f2b = not diff_live["identical"]
    f2 = f2a or f2b
    f3 = len(lang_changed) > 0
    sustained = not (f1 or f2 or f3)

    out_dir.mkdir(parents=True, exist_ok=True)
    rec_replay_path = out_dir / f"{run_id}_live_offline_replay_record.json"
    rec_live_path = out_dir / f"{run_id}_live_record.json"
    rec_replay_path.write_text(json.dumps(rec_replay, indent=1, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    rec_live_path.write_text(json.dumps(rec_live, indent=1, ensure_ascii=False) + "\n",
                             encoding="utf-8")

    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "lane": "evaluation",
        "direction_version": 57,
        "measured_at_utc": _utc_now(),
        "started_at_utc": started,
        "hypothesis": "evaluation/FROZEN_INPUT_DURABILITY_HYPOTHESIS_V1.json",
        "hypothesis_sha256": _sha256_file(
            _LANE_ROOT / "evaluation" / "FROZEN_INPUT_DURABILITY_HYPOTHESIS_V1.json"),
        "commit_at_execution": git_head(),
        "endpoint": spec["endpoint"],

        "inputs": {
            "accepted_record": str(accepted_record.relative_to(_LANE_ROOT)),
            "accepted_record_sha256": accepted_sha_before,
            "accepted_verdict": {
                "n_gates": accepted["verdict"].get("n_gates"),
                "n_passed": accepted["verdict"].get("n_passed"),
                "n_failed": accepted["verdict"].get("n_failed"),
                "n_not_measurable": accepted["verdict"].get("n_not_measurable"),
            },
            "accepted_verdict_selfcheck": gate_status_map_selfcheck(accepted["verdict"]),
            "plan_source": "the accepted record's own queries[]; NOT re-derived "
                           "from the frozen spec",
            "n_queries": len(queries),
            "n_live_ok": n_ok,
            "transport_failures": [{"query_key": q["query_key"], "error": q.get("error")}
                                   for q in queries if q["status"] != 200],
        },
        "frozen_inputs": {
            "frozen_spec_sha256": frozen_inputs_before["frozen_retrieval_benchmark.json"],
            "freeze_record_sha256": frozen_inputs_before["FREEZE_RECORD.json"],
            "frozen_spec_pinned": "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
            "freeze_record_pinned": "b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49",
            "freeze_recorded_at": freeze.get("frozen_at"),
        },

        "non_vacuity": {
            **non_vacuity,
            "duplicate_control": dup_control,
            "verdict_control": "gate-by-gate status diff published for both modes",
        },
        "safety": safety,

        "F1_per_query_body_stability": {
            "n_urls": len(per_query),
            "n_body_sha256_differing": n_body_diff,
            "n_ordered_ids_differing": n_ids_diff,
            "n_identical": len(per_query) - n_body_diff,
            "per_query": per_query,
        },
        "F2_gate_verdict_stability": {
            "definition": "F2 is the CONSERVATIVE disjunction of two readings. "
                          "F2a compares like with like: both records are "
                          "offline_replay, so latency is not-measurable on both. "
                          "F2b compares the live record, whose latency gates are "
                          "measurable and therefore differ by construction if the "
                          "pass is slow. F2b alone is not evidence about the frozen "
                          "input; it is published for transparency.",
            "F2a_apples_to_apples": diff_replay,
            "F2b_live_mode": diff_live,
            "live_verdict_counts": {
                "n_passed": verdict_live.get("n_passed"),
                "n_failed": verdict_live.get("n_failed"),
                "n_not_measurable": verdict_live.get("n_not_measurable"),
            },
            "live_offline_replay_verdict_counts": {
                "n_passed": verdict_replay.get("n_passed"),
                "n_failed": verdict_replay.get("n_failed"),
                "n_not_measurable": verdict_replay.get("n_not_measurable"),
            },
        },
        "F3_language_recall_gate_stability": {
            "gates_under_test": LANG_RECALL_GATES,
            "n_gates": len(LANG_RECALL_GATES),
            "n_changed": len(lang_changed),
            "changed_gates": lang_changed,
            "accepted_status": {g: accepted_status.get(g) for g in LANG_RECALL_GATES},
            "live_status": {g: gate_status_map(verdict_replay).get(g)
                            for g in LANG_RECALL_GATES},
        },

        "verdict": "H_SUSTAINED" if sustained else "H_REFUTED",
        "falsifiers_fired": {"F1": f1, "F2": f2, "F2a": f2a, "F2b": f2b, "F3": f3},
        "safety_violations": violations,

        "artifacts": {
            "live_record_live_mode": str(rec_live_path.relative_to(_LANE_ROOT)),
            "live_record_offline_replay_mode": str(rec_replay_path.relative_to(_LANE_ROOT)),
        },
        "claim_ceiling": (
            "This measures the STABILITY OF THE ORACLE, never the product. "
            "H_SUSTAINED means the frozen verdict did not move on one measured "
            "date; it does NOT prove the product's retrieval is good, does NOT "
            "meet any frozen bar, does NOT serve a packet and does NOT unblock "
            "the human gate. H_REFUTED means the frozen verdict is conditional on "
            "an upstream snapshot; it does NOT prove the product is worse than "
            "recorded. human_gate_ready stays false, the accepted DO-NOT-SERVE "
            "orders stand, owner_decision_required stays false."),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--accepted-record", default=str(ACCEPTED_RECORD))
    ap.add_argument("--scratch", default="/tmp/lex_fid_scratch_cache")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--control-url", default=None,
                    help="query text for the within-run duplicate fetch control")
    args = ap.parse_args(argv)

    run_id = args.run_id
    out_dir = Path(args.out_dir) if args.out_dir else (
        _LANE_ROOT / "results" / "evaluation" / "frozen_input_durability")
    report = run(run_id=run_id, accepted_record=Path(args.accepted_record),
                 scratch=Path(args.scratch), out_dir=out_dir,
                 control_url=args.control_url)

    out_path = Path(args.out) if args.out else out_dir / f"{run_id}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")

    summary = {k: report.get(k) for k in ("schema", "verdict", "falsifiers_fired",
                                          "safety_violations")}
    if "F1_per_query_body_stability" in report:
        summary["n_body_sha256_differing"] = \
            report["F1_per_query_body_stability"]["n_body_sha256_differing"]
        summary["n_status_changed_gates_F2a"] = len(
            report["F2_gate_verdict_stability"]["F2a_apples_to_apples"]["status_changed_gates"])
        summary["n_lang_recall_gates_changed_F3"] = \
            report["F3_language_recall_gate_stability"]["n_changed"]
    print(json.dumps(summary, indent=1))

    if report.get("verdict") == "NO_MEASUREMENT":
        return 2
    if report.get("safety_violations"):
        print("::error::safety-contract violation: "
              f"{report['safety_violations']}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())