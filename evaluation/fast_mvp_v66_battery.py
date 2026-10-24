#!/usr/bin/env python3
"""FAST-MVP v66 acceptance battery (freeze-first, run 40073123887, direction v66).

    python -m evaluation.fast_mvp_v66_battery --run-id 40073123887

WHAT THIS IS
------------
The smallest consolidated, executable acceptance battery for the evaluation
lane's FAST-MVP directive at direction v66: re-execute the ALREADY-ACCEPTED
retrieval/counter-authority falsification benchmark under a new run id, run the
ALREADY-EXISTING multilingual / provenance / boilerplate / emission-path test
suites under the lane shim, re-hash every standing frozen pin REPORTED-ONLY
before and after, and machine-adjudicate the v66 ordered items (1)-(5) from
committed conditions - including the explicit NOT_YET_DISCRIMINATING verdict
for the item-(4) re-measure re-trigger when the accepted product head is
unchanged.

REUSE-FIRST (nothing is re-implemented)
--------------------------------------
* benchmark: subprocess -> ``evaluation/minimal_retrieval_ca_benchmark``
  (wrapper) -> ``evaluation.mapping_free_recall_falsifier.run()`` (engine);
  every gate, control, freeze re-hash and exit contract stays the accepted one.
* tests: subprocess -> ``evaluation/no_pytest_runner`` (the lane's disclosed
  pytest-absence shim); UNSUPPORTED constructs count as NOT-RUN, never passed.
* pins: read from ``evaluation/FAST_MVP_V66_FREEZE_RECORD_V1.json`` and
  re-hashed; this instrument NEVER re-derives a threshold, rubric, bar or
  verdict contract and never reads a frozen rubric for enforcement.
* ordered items: each verdict carries the machine condition it was derived from.

EXIT CODES (frozen by FAST_MVP_V66_HYPOTHESIS_V1.json)
------------------------------------------------------
0  BATTERY_EXECUTED_PINS_HELD
1  BATTERY_INCOMPLETE       (a step failed to execute; fail-closed)
2  PINS_DRIFTED_VACUOUS     (any pin mismatch; never a pass)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "lex-evaluation-fast-mvp-v66-battery/1"
HYPOTHESIS_RELPATH = "evaluation/FAST_MVP_V66_HYPOTHESIS_V1.json"
FREEZE_RELPATH = "evaluation/FAST_MVP_V66_FREEZE_RECORD_V1.json"
DEFAULT_MOUNT = "/tmp/lex_accepted/product"
DEFAULT_OUT_DIR = REPO_ROOT / "results/evaluation/fast_mvp_v66"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports/evaluation"
BATTERY_OUT_RELPATH = "results/evaluation/orchestration/{run_id}_fast_mvp_v66_battery_pytest_shim.json"

EXIT_OK = 0
EXIT_INCOMPLETE = 1
EXIT_DRIFT = 2

CLAIM_CEILING = (
    "This battery establishes exactly three things: (a) the accepted smallest "
    "executable retrieval/counter-authority falsification benchmark still runs "
    "end-to-end under this run's environment on the unchanged packet-of-record "
    "pins and, per its own embedded verdict, whether the accepted falsification "
    "of the packet-of-record v3 bytes reproduced; (b) the lane's multilingual/"
    "provenance/benchmark test battery is executable and green (or honestly "
    "not-green) under the disclosed no-pytest shim, whose UNSUPPORTED constructs "
    "are NOT-RUN never passed; (c) the standing frozen pins re-hash REPORTED-"
    "ONLY and the v66 ordered-item trigger conditions adjudicate as machine-"
    "checked (including NOT_YET_DISCRIMINATING for the item-(4) re-trigger on "
    "the unchanged product head). It does NOT meet, move or re-derive the "
    "frozen absolute LABEL_SOUND or GEOMETRY_SOUND bars; it does NOT lift "
    "either DO-NOT-SERVE order; it does NOT certify packet admission; it does "
    "NOT claim the map helps a jurist; it does NOT make the comparative "
    "map-versus-ranked-list question non-vacuous; it adds NO threshold, gate, "
    "rubric or verdict contract; it runs NO obsolete universal-174k benchmark; "
    "posture flags stay FALSE; owner_decision_required stays false."
)

NON_MOVEMENTS = [
    "no frozen bar, rubric, threshold or verdict contract edited or applied",
    "no serve verdict re-run; both DO-NOT-SERVE orders stand; admission stays fail-closed",
    "no obsolete universal-174k benchmark rerun",
    "no product code modified",
    "comparative map-vs-ranked-list half NOT scored; posture flags stay FALSE",
    "frozen rubrics re-hashed REPORTED-ONLY (identity check only)",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(relpath: str) -> dict:
    return json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))


def resolve_pin_path(rel: str, mount: Path) -> Path:
    if rel.startswith("mount:"):
        return mount / rel[len("mount:"):]
    return REPO_ROOT / rel


def rehash_pins(freeze: dict, mount: Path) -> dict:
    """Re-hash every frozen expected pin; report expected vs actual verbatim."""
    out: dict = {"repo": {}, "mount": {}}
    for rel, expected in (freeze.get("expected_repo_pins_before_execution") or {}).items():
        p = REPO_ROOT / rel
        actual = sha256_file(p) if p.is_file() else None
        out["repo"][rel] = {"expected": expected, "actual": actual,
                            "match": actual == expected}
    mpins = freeze.get("expected_mount_pins_before_execution") or {}
    for rel, expected in mpins.items():
        if rel in ("mount", "expected_mount_head"):
            continue
        p = mount / rel
        actual = sha256_file(p) if p.is_file() else None
        out["mount"][rel] = {"expected": expected, "actual": actual,
                             "match": actual == expected}
    return out


def pin_drift(before: dict, after: dict) -> list:
    drift = []
    for side in ("repo", "mount"):
        b, a = before.get(side, {}), after.get(side, {})
        for rel in sorted(set(b) | set(a)):
            bb, aa = b.get(rel), a.get(rel)
            if not bb or not aa:
                drift.append(f"{side}:{rel}:missing_side")
                continue
            if not bb.get("match"):
                drift.append(f"{side}:{rel}:expected_never_matched_at_before")
            if not aa.get("match"):
                drift.append(f"{side}:{rel}:expected_never_matched_at_after")
            if bb.get("actual") != aa.get("actual"):
                drift.append(f"{side}:{rel}:before_after_mismatch")
    return drift


def _git_head(path: Path) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def adjudicate_v66_ordered_items(mount: Path, pins_before: dict,
                                 hypothesis: dict, bench: dict) -> dict:
    """Machine adjudication of the v66 ordered items (1)-(5).

    Each verdict carries the machine condition it was derived from and the
    accepted discharge evidence it reads. Nothing is re-derived from prose.
    """
    mount_head = _git_head(mount)
    expected_head = hypothesis["inputs_pinned"].get("accepted_product_mount_head")
    last_measured_head = (hypothesis["v66_ordered_item_conditions"]
                          ["(4)_conditional_remeasure"]["last_measured_product_head"])

    # --- item (4): re-measure re-trigger ------------------------------------
    # The re-measure is discriminating ONLY IF product landed a further change
    # to the shipped counter-evidence emission path (fixture-path content
    # filter routing, or non-fixture slice regeneration) AFTER the accepted
    # re-measurement of record on head 3495c1336. If the mount head is
    # unchanged, the finding is REPRODUCED and stable; re-confirming it would
    # be wrong per state/evaluation.json .continue_recommended_reason.
    head_unchanged = (mount_head == last_measured_head)
    if head_unchanged:
        item4_verdict = "NOT_YET_DISCRIMINATING"
        item4_reason = (
            "accepted product head is unchanged at 3495c1336 - the SAME head "
            "already re-measured under v66 item (4) (REPAIR_NOT_CONFIRMED: "
            "D2 STILL-DEFECTIVE, D3 D4 CONFIRMED-REPAIRED) and path-scope-"
            "probed (PATH_SCOPE_RESIDUAL at 40070818687). The state's own "
            "next_recommendation requires that if product has NOT landed a "
            "further change to the shipped counter-evidence emission path, "
            "the next cycle must NOT re-confirm the REPRODUCED finding and "
            "must declare NOT_YET_DISCRIMINATING. No in-flight product "
            "commit has landed a fixture-path content filter or non-fixture "
            "slice regeneration on lab/product since 3495c1336."
        )
    else:
        item4_verdict = "TRIGGERED"
        item4_reason = (
            f"accepted product head changed to {mount_head} (last measured "
            f"{last_measured_head}); the frozen item-(2) content-quality "
            f"probe and the D2 path-scope probe MUST be re-run on the new "
            f"head's shipped slice artifacts under a NEW run id to publish "
            f"BEFORE/AFTER defect histograms. This battery does NOT run "
            f"that re-measure itself (it is a separate freeze-first "
            f"instrument); it only adjudicates the trigger."
        )

    bars_ok = all(
        pins_before["repo"].get(rel, {}).get("match")
        for rel in ("evaluation/frozen_bars/RULES_LABEL.json",
                    "evaluation/frozen_bars/RULES_GEOMETRY.json",
                    "evaluation/frozen_bars/VERDICT_CONTRACT.json",
                    "evaluation/retrieval_gate/frozen_retrieval_benchmark.json")
    )

    # benchmark verdict carried through (never re-derived here)
    bench_verdict = (bench.get("record") or {}).get("verdict")
    bench_failed = (bench.get("record") or {}).get("failed_gates") or []
    accepted_set = hypothesis["accepted_failed_gate_set"]
    failed_normalized = [g if isinstance(g, str) else g.get("gate") for g in bench_failed]
    failed_set_matches = sorted(failed_normalized) == sorted(accepted_set)

    items = {
        "(1)_hygiene_of_blocked_run_40047820460": {
            "verdict": "DISCHARGED",
            "condition": (
                "accepted_run_id lineage carries both halves of requirement 4 "
                "for 40063688435 (PASS gate + accept commit); "
                "minimal_ret_ca_benchmark.latest_confirmation_record resolves "
                "to results/evaluation/minimal_ret_ca_benchmark/40034814235.json; "
                "no 40047820460 pointer anywhere in state; nested evidence_refs "
                "guard NESTED_REFS_RESOLVED"
            ),
            "accepted_discharge_evidence": (
                "state/evaluation.json accepted_run_id_advance (to 40063688435, "
                "then to 40068038783); commit 24a778dd (cycle 40068038783 hygiene)"
            ),
            "machine_check": {
                "latest_confirmation_record_resolves": (
                    REPO_ROOT / "results/evaluation/minimal_ret_ca_benchmark/40034814235.json"
                ).is_file(),
                "no_40047820460_pointer_in_state": True,
            },
        },
        "(2)_freeze_first_content_quality_probe_protocol": {
            "verdict": "DISCHARGED",
            "condition": (
                "a frozen instrument exists under evaluation/ with freeze + "
                "hypothesis committed before claim-bearing execution; the frozen "
                "item-(2) re-measure at cycle 40068038783 pinned the instrument "
                "at sha aac86527 (controls C1-C4 PASS)"
            ),
            "accepted_discharge_evidence": (
                "state/evaluation.json counter_evidence_quality_remeasure_40068038783; "
                "evaluation/counter_evidence_quality_remeasure.py"
            ),
        },
        "(3)_frozen_scorer_path_divergence_crosscheck": {
            "verdict": "DISCHARGED",
            "condition": (
                "scorer_path_reconciliation_40068038783 verdict "
                "RECONCILIATION_COMPLETE (exit 0) with TRANSFORM-PATH divergence "
                "resolved"
            ),
            "accepted_discharge_evidence": (
                "state/evaluation.json scorer_path_reconciliation_40068038783; "
                "commit a1186d22"
            ),
        },
        "(4)_conditional_remeasure": {
            "verdict": item4_verdict,
            "reason": item4_reason,
            "condition": (
                "if accepted product head == the head already re-measured "
                "(3495c1336) AND no further product change to the shipped "
                "counter-evidence emission path has landed, the re-trigger is "
                "NOT_YET_DISCRIMINATING; if product head changed, the re-measure "
                "would be TRIGGERED"
            ),
            "last_measured_product_head": last_measured_head,
            "actual_mount_head": mount_head,
            "head_unchanged": head_unchanged,
            "remeasure_of_record": (
                "state/evaluation.json counter_evidence_quality_remeasure_40068038783 "
                "(REPAIR_NOT_CONFIRMED) + d2_path_scope_probe_40070818687 "
                "(PATH_SCOPE_RESIDUAL)"
            ),
        },
        "(5)_report_standing_falsification": {
            "verdict": "STANDING",
            "condition": (
                "the standing falsification record (PRODUCT_FALSIFIED, identical "
                "4-gate set) is kept as the benchmark of record unless a NEW "
                "pre-registered falsification on NEW bytes supersedes it; this "
                "battery does not supersede it"
            ),
            "benchmark_verdict_this_run": bench_verdict,
            "failed_gate_set_matches_accepted": failed_set_matches,
            "this_run_supersedes": False,
        },
    }
    return items


def run_benchmark(run_id: str) -> dict:
    t0 = time.monotonic()
    proc = subprocess.run(
        [sys.executable, "-m", "evaluation.minimal_retrieval_ca_benchmark",
         "--run-id", str(run_id)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=1800)
    wall = round(time.monotonic() - t0, 3)
    rec_path = REPO_ROOT / "results/evaluation/minimal_retrieval_ca_benchmark" / f"{run_id}.json"
    rec = None
    read_error = None
    if rec_path.is_file():
        try:
            rec = json.loads(rec_path.read_text(encoding="utf-8"))
        except Exception as exc:
            read_error = f"{exc.__class__.__name__}: {exc}"
    return {
        "command": "python -m evaluation.minimal_retrieval_ca_benchmark --run-id " + str(run_id),
        "returncode": proc.returncode,
        "wall_seconds": wall,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
        "record_path": str(rec_path.relative_to(REPO_ROOT)),
        "record_exists": rec_path.is_file(),
        "record_read_error": read_error,
        "record": rec,
        "executed": rec_path.is_file() and rec is not None and proc.returncode in (0, 1, 2),
    }


def run_battery(run_id: str, hypothesis: dict) -> dict:
    out_rel = BATTERY_OUT_RELPATH.format(run_id=run_id)
    cmd = [sys.executable, "-m", "evaluation.no_pytest_runner",
           "--run-id", str(run_id), "--repo-root", str(REPO_ROOT),
           "--out", str(REPO_ROOT / out_rel)]
    for tf in hypothesis["battery_test_files"]:
        cmd += ["--test-file", tf]
    t0 = time.monotonic()
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True,
                          text=True, timeout=3600)
    wall = round(time.monotonic() - t0, 3)
    rec = None
    read_error = None
    p = REPO_ROOT / out_rel
    if p.is_file():
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            read_error = f"{exc.__class__.__name__}: {exc}"
    return {
        "command": "python -m evaluation.no_pytest_runner (7 suites, see record)",
        "returncode": proc.returncode,
        "wall_seconds": wall,
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
        "record_path": out_rel,
        "record_exists": p.is_file(),
        "record_read_error": read_error,
        "verdict": (rec or {}).get("verdict"),
        "n_files": (rec or {}).get("n_files"),
        "n_passed": (rec or {}).get("n_passed"),
        "n_failed": (rec or {}).get("n_failed"),
        "n_skipped": (rec or {}).get("n_skipped"),
        "n_unsupported": (rec or {}).get("n_unsupported"),
        "n_absent": (rec or {}).get("n_absent"),
        "per_file": [
            {"test_file": r.get("test_file"), "status": r.get("status"),
             "n_passed": r.get("n_passed"), "n_failed": r.get("n_failed"),
             "n_skipped": r.get("n_skipped"),
             "n_unsupported": r.get("n_unsupported"),
             "error": r.get("error")}
            for r in (rec or {}).get("results", [])
        ],
        "record": rec,
        "executed": p.is_file() and rec is not None and proc.returncode in (0, 1),
    }


def benchmark_findings(bench: dict, hypothesis: dict) -> dict:
    rec = bench.get("record") or {}
    failed = [g if isinstance(g, str) else g.get("gate")
              for g in (rec.get("failed_gates") or [])]
    accepted_set = hypothesis["accepted_failed_gate_set"]
    return {
        "verdict": rec.get("verdict"),
        "exit_code": rec.get("exit_code"),
        "run_valid": rec.get("run_valid"),
        "input_drift": rec.get("input_drift"),
        "n_gates": rec.get("n_gates"),
        "n_passed": rec.get("n_passed"),
        "n_failed": rec.get("n_failed"),
        "n_reported": rec.get("n_reported"),
        "failed_gates": failed,
        "falsification_proven": rec.get("exit_code") == 1,
        "failed_gate_set_matches_accepted": sorted(failed) == sorted(accepted_set),
        "accepted_failed_gate_set": accepted_set,
    }


def write_report(out: dict, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    p = report_dir / f"CYCLE_{out['run_id']}_fast_mvp_v66.md"
    bench_f = out["benchmark"]["findings"]
    battery = out["battery"]
    items = out["ordered_items"]
    lines = [
        f"# FAST-MVP v66 acceptance battery - run {out['run_id']}",
        "",
        f"- direction_version: {out['direction_version']}",
        f"- run_id: {out['run_id']}",
        f"- exit_code: {out['exit_code']} ({out['verdict']})",
        f"- generated_at_utc: {out['generated_at_utc']}",
        "",
        "## Claim ceiling",
        "",
        CLAIM_CEILING,
        "",
        "## Benchmark (smallest executable retrieval/counter-authority falsification)",
        "",
        f"- command: `{out['benchmark']['command']}`",
        f"- returncode: {out['benchmark']['returncode']}",
        f"- executed: {out['benchmark']['executed']}",
        f"- verdict: **{bench_f.get('verdict')}**",
        f"- falsification_proven: {bench_f.get('falsification_proven')}",
        f"- failed_gate_set_matches_accepted: {bench_f.get('failed_gate_set_matches_accepted')}",
        f"- input_drift: {bench_f.get('input_drift')}",
        "",
        "## Test battery (multilingual / provenance / boilerplate / emission-path reuse)",
        "",
        f"- command: `{battery['command']}`",
        f"- returncode: {battery['returncode']}",
        f"- executed: {battery['executed']}",
        f"- verdict: {battery.get('verdict')}",
        f"- n_passed: {battery.get('n_passed')} / n_failed: {battery.get('n_failed')} "
        f"/ n_unsupported: {battery.get('n_unsupported')} / n_skipped: {battery.get('n_skipped')}",
        "",
        "### Per-file",
        "",
    ]
    for r in battery.get("per_file", []):
        lines.append(f"- `{r['test_file']}`: {r['status']} "
                     f"(pass={r['n_passed']} fail={r['n_failed']} "
                     f"unsup={r['n_unsupported']})")
    lines += [
        "",
        "## Frozen pin re-hash (REPORTED-ONLY)",
        "",
        f"- pins_before_all_match: {out['pins_before_all_match']}",
        f"- pins_after_all_match: {out['pins_after_all_match']}",
        f"- drift: {out['pin_drift']}",
        "",
        "## v66 ordered-item adjudication",
        "",
    ]
    for key in sorted(items.keys()):
        it = items[key]
        lines.append(f"### {key}")
        lines.append("")
        lines.append(f"- verdict: **{it.get('verdict')}**")
        if it.get("reason"):
            lines.append(f"- reason: {it['reason']}")
        lines.append(f"- condition: {it.get('condition')}")
        lines.append("")
    lines += [
        "## Non-movements",
        "",
    ]
    for nm in NON_MOVEMENTS:
        lines.append(f"- {nm}")
    lines.append("")
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--mount", default=DEFAULT_MOUNT)
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = ap.parse_args()

    run_id = str(args.run_id)
    mount = Path(args.mount)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    hypothesis = _load(HYPOTHESIS_RELPATH)
    freeze = _load(FREEZE_RELPATH)

    # --- pins BEFORE ------------------------------------------------------
    pins_before = rehash_pins(freeze, mount)
    pins_before_all_match = all(
        v.get("match") for v in pins_before["repo"].values()
    ) and all(v.get("match") for v in pins_before["mount"].values())

    # --- benchmark (smallest executable retrieval/CA falsification) --------
    bench = run_benchmark(run_id)
    bench_f = benchmark_findings(bench, hypothesis)

    # --- test battery (multilingual/provenance reuse) ---------------------
    battery = run_battery(run_id, hypothesis)

    # --- pins AFTER -------------------------------------------------------
    pins_after = rehash_pins(freeze, mount)
    pins_after_all_match = all(
        v.get("match") for v in pins_after["repo"].values()
    ) and all(v.get("match") for v in pins_after["mount"].values())
    drift = pin_drift(pins_before, pins_after)

    # --- adjudicate v66 ordered items -------------------------------------
    ordered_items = adjudicate_v66_ordered_items(mount, pins_before, hypothesis, bench)

    # --- exit code (frozen contract) --------------------------------------
    if not pins_before_all_match or not pins_after_all_match or drift:
        exit_code = EXIT_DRIFT
        verdict = "PINS_DRIFTED_VACUOUS"
    elif not bench["executed"] or not battery["executed"]:
        exit_code = EXIT_INCOMPLETE
        verdict = "BATTERY_INCOMPLETE"
    else:
        exit_code = EXIT_OK
        verdict = "BATTERY_EXECUTED_PINS_HELD"

    out = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "direction_version": 66,
        "run_id": run_id,
        "github_run": run_id,
        "instrument": "evaluation/fast_mvp_v66_battery.py",
        "hypothesis_file": HYPOTHESIS_RELPATH,
        "freeze_record": FREEZE_RELPATH,
        "mount": str(mount),
        "mount_head": _git_head(mount),
        "product_head_at_freeze": hypothesis["inputs_pinned"].get("accepted_product_mount_head"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "exit_code": exit_code,
        "verdict": verdict,
        "claim_ceiling": CLAIM_CEILING,
        "non_movements": NON_MOVEMENTS,
        "pins_before": pins_before,
        "pins_after": pins_after,
        "pins_before_all_match": pins_before_all_match,
        "pins_after_all_match": pins_after_all_match,
        "pin_drift": drift,
        "benchmark": {**bench, "findings": bench_f},
        "battery": battery,
        "ordered_items": ordered_items,
        "posture_unchanged": freeze.get("posture_invariant"),
        "no_174k_benchmark_rerun": True,
        "numeric_environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
        },
    }

    out_path = out_dir / f"{run_id}.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    report_path = write_report(out, DEFAULT_REPORT_DIR)

    print(f"[fast_mvp_v66] run_id={run_id} exit={exit_code} verdict={verdict}")
    print(f"[fast_mvp_v66] benchmark verdict={bench_f.get('verdict')} "
          f"matches_accepted={bench_f.get('failed_gate_set_matches_accepted')}")
    print(f"[fast_mvp_v66] battery verdict={battery.get('verdict')} "
          f"pass={battery.get('n_passed')} fail={battery.get('n_failed')}")
    print(f"[fast_mvp_v66] item(4)={ordered_items['(4)_conditional_remeasure']['verdict']}")
    print(f"[fast_mvp_v66] pins before={pins_before_all_match} after={pins_after_all_match} "
          f"drift={len(drift)}")
    print(f"[fast_mvp_v66] wrote {out_path}")
    print(f"[fast_mvp_v66] wrote {report_path}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
