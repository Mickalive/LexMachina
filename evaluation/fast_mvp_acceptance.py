#!/usr/bin/env python3
"""FAST-MVP acceptance battery (freeze-first, run 39884405570, direction v63).

    python -m evaluation.fast_mvp_acceptance --run-id 39884405570

WHAT THIS IS
------------
The smallest consolidated, executable acceptance battery for the evaluation
lane's FAST-MVP directive: run the ALREADY-ACCEPTED retrieval/counter-authority
falsification benchmark under a new run id, run the ALREADY-EXISTING
multilingual / provenance / benchmark test suites under the lane shim, re-hash
every standing frozen pin before and after, and machine-adjudicate the v63
ordered items (1)-(5) from committed conditions.

REUSE-FIRST (nothing is re-implemented)
--------------------------------------
* benchmark: subprocess -> ``evaluation/minimal_retrieval_ca_benchmark``
  (wrapper) -> ``evaluation.mapping_free_recall_falsifier.run()`` (engine);
  every gate, control, freeze re-hash and exit contract stays the accepted one.
* tests: subprocess -> ``evaluation/no_pytest_runner`` (the lane's disclosed
  pytest-absence shim); UNSUPPORTED constructs count as NOT-RUN, never passed.
* pins: read from ``evaluation/FAST_MVP_ACCEPTANCE_FREEZE_RECORD_V1.json`` and
  re-hashed; this instrument NEVER re-derives a threshold, rubric, bar or
  verdict contract and never reads a frozen rubric for enforcement.
* ordered items: each verdict carries the machine condition it was derived from.

EXIT CODES (frozen by FAST_MVP_ACCEPTANCE_HYPOTHESIS_V1.json)
------------------------------------------------------------
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

SCHEMA = "lex-evaluation-fast-mvp-acceptance/1"
HYPOTHESIS_RELPATH = "evaluation/FAST_MVP_ACCEPTANCE_HYPOTHESIS_V1.json"
FREEZE_RELPATH = "evaluation/FAST_MVP_ACCEPTANCE_FREEZE_RECORD_V1.json"
DEFAULT_MOUNT = "/tmp/lex_accepted/product"
DEFAULT_OUT_DIR = REPO_ROOT / "results/evaluation/fast_mvp_acceptance"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports/evaluation"
BATTERY_OUT_RELPATH = "results/evaluation/orchestration/{run_id}_fast_mvp_battery_pytest_shim.json"

EXIT_OK = 0
EXIT_INCOMPLETE = 1
EXIT_DRIFT = 2

#: Text-taxonomy markers under which a serve recommendation counts as
#: DO-NOT-SERVE (operational trigger classification only; frozen in the
#: hypothesis's ordered_item_conditions - not a measurement threshold).
DO_NOT_SERVE_MARKERS = (
    "do-not-serve", "do_not_serve", "do not serve",
    "bounded-negative", "withheld_pending_serve", "built_not_served",
)

CLAIM_CEILING = (
    "This battery establishes exactly three things: (a) the accepted smallest "
    "executable retrieval/counter-authority falsification benchmark still runs "
    "end-to-end under this run's environment on the unchanged accepted pins and, "
    "per its own embedded verdict, whether the accepted falsification of the "
    "packet-of-record v3 bytes reproduced; (b) the lane's multilingual/"
    "provenance/benchmark test battery is executable and green (or honestly "
    "not-green) under the disclosed no-pytest shim, whose UNSUPPORTED constructs "
    "are NOT-RUN never passed; (c) the standing frozen pins and the ordered-item "
    "trigger conditions hold as machine-checked. It does NOT meet, move or "
    "re-derive the frozen absolute LABEL_SOUND or GEOMETRY_SOUND bars; it does "
    "NOT lift either DO-NOT-SERVE order; it does NOT certify packet admission; "
    "it does NOT claim the map helps a jurist; it does NOT make the comparative "
    "map-versus-ranked-list question non-vacuous; it adds NO threshold, gate, "
    "rubric or verdict contract; it runs NO obsolete universal-174k benchmark; "
    "human_gate_ready stays false."
)


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


def collect_serve_recommendations(mount: Path, repo: Path) -> list:
    """Walk committed verdict JSONs; collect every serve_recommendation string."""
    found = []
    dirs = [mount / "results/product/frontier_verdicts",
            repo / "evaluation/vendored_frontier_serve_audit"]
    for d in dirs:
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.json")):
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except Exception as exc:  # disclosed, never silently dropped
                found.append({"file": str(p.relative_to(repo)) if str(p).startswith(str(repo)) else str(p),
                              "error": f"unreadable:{exc.__class__.__name__}"})
                continue

            def walk(o, path=""):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if k == "serve_recommendation" and isinstance(v, str) and v.strip():
                            found.append({"file": p.name, "key": path + k, "value": v})
                        walk(v, path + k + ".")
                elif isinstance(o, list):
                    for x in o:
                        walk(x, path)
            walk(doc)
    return found


def classify_serve_recommendation(value: str) -> str:
    v = (value or "").lower()
    for marker in DO_NOT_SERVE_MARKERS:
        if marker in v:
            return "DO_NOT_SERVE"
    return "PERMITS_SERVE"


def adjudicate_ordered_items(mount: Path, pins_before: dict,
                             hypothesis: dict) -> dict:
    """Machine adjudication of the v63 ordered items; each verdict carries
    the condition it was derived from (never re-derived thresholds)."""
    planner_rel = "product/query/adversarial_retrieval.py"
    expected_planner = hypothesis["inputs_pinned"].get(
        "mount:/tmp/lex_accepted/product/product/query/adversarial_retrieval.py")
    actual_planner = sha256_file(mount / planner_rel) if (mount / planner_rel).is_file() else None
    mount_head = _git_head(mount)

    bars_ok = all(
        pins_before["repo"].get(rel, {}).get("match")
        for rel in ("evaluation/frozen_bars/RULES_LABEL.json",
                    "evaluation/frozen_bars/RULES_GEOMETRY.json",
                    "evaluation/frozen_bars/VERDICT_CONTRACT.json",
                    "evaluation/retrieval_gate/frozen_retrieval_benchmark.json")
    )

    recs = collect_serve_recommendations(mount, REPO_ROOT)
    classified = []
    for r in recs:
        c = dict(r)
        if "value" in r:
            c["classification"] = classify_serve_recommendation(r["value"])
        classified.append(c)
    permits = [c for c in classified if c.get("classification") == "PERMITS_SERVE"]

    items = {
        "(1)_remedy_a_re_freeze": {
            "verdict": "TRIGGERED" if actual_planner != expected_planner else "NOT_TRIGGERED",
            "condition": ("mount planner sha256 != the pin already re-frozen by accepted "
                          "run 39813664201 (SHIPPED_PLANNER_MATCHES_VERIFIED_REMEDY)"),
            "expected_planner_sha256": expected_planner,
            "actual_planner_sha256": actual_planner,
        },
        "(2)_cross_check_next_product_measurement": {
            "verdict": "TRIGGERED" if mount_head != hypothesis["inputs_pinned"]["accepted_product_mount_head"]
                       else "NOT_TRIGGERED",
            "condition": "mount HEAD != accepted product anchor fe219a19 (no newer accepted product cycle)",
            "expected_mount_head": hypothesis["inputs_pinned"]["accepted_product_mount_head"],
            "actual_mount_head": mount_head,
        },
        "(3)_frozen_bars_standing": {
            "verdict": "STANDING_OK" if bars_ok else "STANDING_VIOLATED",
            "condition": ("RULES_LABEL/RULES_GEOMETRY/VERDICT_CONTRACT/frozen retrieval benchmark "
                          "re-hash match (identity re-hash only, never re-derived)"),
            "all_match": bars_ok,
        },
        "(4)_p1_fr_counter_stage_divergence": {
            "verdict": "STANDING_OK",
            "condition": ("carry-forward reference to the accepted P1 FR divergence record in "
                          "state/evaluation.json; NOT re-derived, NOT re-measured by this run"),
        },
        "(5)_falsify_new_served_packet": {
            "verdict": "TRIGGERED" if permits else "NOT_TRIGGERED",
            "condition": ("any accepted serve_recommendation in mount frontier_verdicts or the "
                          "vendored serve verdict that does not carry a DO-NOT-SERVE marker "
                          "(markers frozen in the hypothesis: " + ", ".join(DO_NOT_SERVE_MARKERS) + ")"),
            "recommendations_found": classified,
            "permits_serve_count": len(permits),
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


def run_battery(run_id: str) -> dict:
    hypothesis = _load(HYPOTHESIS_RELPATH)
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
        # the wrapper record has no top-level falsification_proven field; the
        # wrapper's own CLI prints exit_code == 1 for it - same derivation here.
        "falsification_proven": rec.get("exit_code") == 1,
        "non_vacuity_all_hold": (rec.get("non_vacuity") or {}).get("all_hold"),
        "falsification_reproduced": rec.get("verdict") == "PRODUCT_FALSIFIED" and rec.get("exit_code") == 1,
        "failed_gate_set_matches_accepted": sorted(failed) == sorted(accepted_set),
        "product_mount_head": rec.get("product_mount_head"),
        "wrapper_direction_version_field": rec.get("direction_version"),
        "non_vacuity_battery": [
            {"control": c.get("control"), "holds": c.get("holds")}
            for c in (rec.get("non_vacuity") or {}).get("battery", [])
        ],
    }


def build_report(run_id: str, record: dict) -> str:
    b = record["benchmark"]
    bt = record["battery"]
    items = record["ordered_item_adjudication"]
    lat = record["latency_reported_only"]
    lines = [
        f"# FAST-MVP Acceptance Battery - run {run_id}",
        "",
        f"- Schema: `{SCHEMA}`",
        f"- Direction: v{record['direction_version']} (cycle field; wrapper instrument field "
        f"direction_version={b.get('wrapper_direction_version_field')} is the accepted wrapper's own frozen value)",
        f"- Battery verdict: **{record['verdict']}** (exit {record['exit_code']})",
        f"- Generated: {record['generated_at_utc']}",
        "",
        "## Benchmark step (accepted instrument, invoked unchanged)",
        "",
        f"- Verdict: **{b.get('verdict')}** (exit {b.get('exit_code')}), run_valid={b.get('run_valid')}, "
        f"input_drift={b.get('input_drift')}",
        f"- Gates: {b.get('n_passed')}/{b.get('n_gates')} passed, {b.get('n_failed')} failed, "
        f"{b.get('n_reported')} reported",
        f"- Failed gates: {b.get('failed_gates')}",
        f"- falsification_reproduced={b.get('falsification_reproduced')} | "
        f"failed_gate_set_matches_accepted={b.get('failed_gate_set_matches_accepted')} | "
        f"non_vacuity_all_hold={b.get('non_vacuity_all_hold')}",
        f"- Product mount head measured: {b.get('product_mount_head')}",
        "",
        "## Battery step (7 suites under the disclosed no-pytest shim)",
        "",
        f"- Verdict: **{bt.get('verdict')}** - passed={bt.get('n_passed')} failed={bt.get('n_failed')} "
        f"skipped={bt.get('n_skipped')} unsupported(NOT-RUN, never passed)={bt.get('n_unsupported')} "
        f"absent={bt.get('n_absent')} across {bt.get('n_files')} files",
        f"- Record: `{bt.get('record_path')}`",
        "- NOT pytest: a SHIM_PASS does not withdraw the standing disclosure that pytest is "
        "absent from the producer image.",
        "",
        "### Per-file",
        "",
    ]
    for r in bt.get("per_file", []):
        lines.append(f"- `{r.get('test_file')}`: status={r.get('status')} "
                     f"passed={r.get('n_passed')} failed={r.get('n_failed')} "
                     f"skipped={r.get('n_skipped')} unsupported={r.get('n_unsupported')}"
                     + (f" error={r.get('error')}" if r.get("error") else ""))
    lines += [
        "",
        "## Pin discipline (re-hashed before and after; identity only)",
        "",
        f"- Drift: {record['pin_drift'] if record['pin_drift'] else 'NONE (all pins identical before/after and matching expected)'}",
        "",
        "## Ordered-item adjudication (v63)",
        "",
    ]
    for key, it in items.items():
        lines.append(f"- **{key}**: {it['verdict']} - condition: {it['condition']}")
    lines += [
        "",
        "## Latency (REPORTED-ONLY, no threshold)",
        "",
        f"- benchmark: {lat.get('benchmark_seconds')}s | battery: {lat.get('battery_seconds')}s | "
        f"pin re-hash total: {lat.get('pin_hash_seconds')}s",
        "",
        "## Prior-session disclosure",
        "",
        "- " + record["prior_session_disclosure"],
        "",
        "## Claim ceiling",
        "",
        "- " + CLAIM_CEILING,
        "",
        "## Provenance",
        "",
        f"- Hypothesis: `{HYPOTHESIS_RELPATH}` sha256 {record['hypothesis_sha256']}",
        f"- Freeze record: `{FREEZE_RELPATH}` sha256 {record['freeze_sha256']}",
        f"- Machine record: `results/evaluation/fast_mvp_acceptance/{run_id}.json`",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-id", default=None,
                    help="default: $GITHUB_RUN_ID or 'local'")
    ap.add_argument("--product-mount", default=DEFAULT_MOUNT)
    ap.add_argument("--skip-execute", action="store_true",
                    help="assemble only: pins + adjudication, no benchmark/battery subprocess")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--report-dir", default=None)
    args = ap.parse_args(argv)
    import os
    run_id = args.run_id or os.environ.get("GITHUB_RUN_ID", "local")
    mount = Path(args.product_mount)
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUT_DIR
    report_dir = Path(args.report_dir) if args.report_dir else DEFAULT_REPORT_DIR

    hypothesis = _load(HYPOTHESIS_RELPATH)
    freeze = _load(FREEZE_RELPATH)
    hypothesis_sha = sha256_file(REPO_ROOT / HYPOTHESIS_RELPATH)
    freeze_sha = sha256_file(REPO_ROOT / FREEZE_RELPATH)

    # inputs_pinned in the hypothesis mixes mount: keys and one non-digest
    # head key; compare only the digest entries the freeze record also holds.
    hyp_digests = {k: v for k, v in (hypothesis.get("inputs_pinned") or {}).items()
                   if k.startswith("evaluation/")}
    consistency = {
        "hypothesis_sha_matches_freeze_record":
            hypothesis_sha == freeze.get("hypothesis_sha256_at_freeze"),
        "inputs_pinned_equal":
            hyp_digests == freeze.get("expected_repo_pins_before_execution"),
    }

    t = time.monotonic()
    pins_before = rehash_pins(freeze, mount)
    hash_before_s = round(time.monotonic() - t, 3)

    bench = {"executed": False, "skipped": True, "reason": "--skip-execute"}
    battery = {"executed": False, "skipped": True, "reason": "--skip-execute"}
    if not args.skip_execute:
        bench = run_benchmark(run_id)
        battery = run_battery(run_id)

    t = time.monotonic()
    pins_after = rehash_pins(freeze, mount)
    hash_after_s = round(time.monotonic() - t, 3)
    drift = pin_drift(pins_before, pins_after)

    findings = benchmark_findings(bench, hypothesis) if bench.get("record") else {
        "verdict": None, "falsification_reproduced": False,
        "failed_gate_set_matches_accepted": False,
        "non_vacuity_all_hold": None,
    }
    items = adjudicate_ordered_items(mount, pins_before, hypothesis)

    # ---- exit contract -----------------------------------------------------
    battery_ok = (battery.get("verdict") == "SHIM_PASS"
                  and not battery.get("n_failed") and not battery.get("n_absent"))
    consistency_ok = all(bool(v) for v in consistency.values())
    if not consistency_ok:
        drift = list(drift) + ["consistency:hypothesis_or_inputs_pinned_changed_after_freeze"]
    if drift:
        verdict, code = "PINS_DRIFTED_VACUOUS", EXIT_DRIFT
    elif args.skip_execute:
        verdict, code = "ASSEMBLE_ONLY_NOT_CLAIM_BEARING", EXIT_INCOMPLETE
    elif not (bench.get("executed") and battery.get("executed") and battery_ok):
        verdict, code = "BATTERY_INCOMPLETE", EXIT_INCOMPLETE
    else:
        verdict, code = "BATTERY_EXECUTED_PINS_HELD", EXIT_OK

    record = {
        "schema": SCHEMA,
        "lane": "evaluation",
        "run_id": str(run_id),
        "direction_version": 63,
        "entry_point": "python -m evaluation.fast_mvp_acceptance --run-id " + str(run_id),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": verdict,
        "exit_code": code,
        "product_mount": str(mount),
        "hypothesis_sha256": hypothesis_sha,
        "freeze_sha256": freeze_sha,
        "consistency": consistency,
        "pins_before": pins_before,
        "pins_after": pins_after,
        "pin_drift": drift,
        "benchmark": findings if bench.get("record") else {
            "executed": False, "stderr_tail": bench.get("stderr_tail"),
            "returncode": bench.get("returncode")},
        "benchmark_execution": {k: v for k, v in bench.items() if k != "record"},
        "battery": {k: v for k, v in battery.items() if k != "record"},
        "battery_executed": battery.get("executed"),
        "ordered_item_adjudication": items,
        "latency_reported_only": {
            "benchmark_seconds": bench.get("wall_seconds"),
            "battery_seconds": battery.get("wall_seconds"),
            "pin_hash_seconds": hash_before_s + hash_after_s,
            "note": "REPORTED-ONLY; no latency threshold exists or was added",
        },
        "frozen_rubrics_read_for_enforcement": False,
        "no_new_thresholds": True,
        "no_174k_benchmark_rerun": True,
        "prior_session_disclosure": (
            "A prior session of this same GitHub run executed the benchmark at "
            "2026-10-23T01:34:55Z under id local_eval_1792719295 (artifacts "
            "results/evaluation/minimal_retrieval_ca_benchmark/local_eval_1792719295*.json "
            "and reports/evaluation/RETRIEVAL_CA_BENCHMARK_local_eval_1792719295.md, "
            "uncommitted at freeze time); those bytes are preserved verbatim and are NOT "
            "this run's claim-bearing record - this record and "
            f"results/evaluation/minimal_retrieval_ca_benchmark/{run_id}.json are."
        ),
        "claim_ceiling": CLAIM_CEILING,
        "human_gate_ready": False,
        "machine_gate_ready": False,
        "ready_for_owner_session": False,
        "owner_decision_required": False,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}.json"
    out_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"FAST_MVP_ACCEPTANCE_{run_id}.md"
    report_path.write_text(build_report(run_id, record), encoding="utf-8")

    print(json.dumps({
        "verdict": verdict, "exit_code": code,
        "pin_drift": drift,
        "benchmark": {k: findings.get(k) for k in
                      ("verdict", "exit_code", "falsification_reproduced",
                       "failed_gate_set_matches_accepted", "non_vacuity_all_hold")},
        "battery": {k: battery.get(k) for k in
                    ("verdict", "n_passed", "n_failed", "n_unsupported", "n_absent")},
        "ordered_items": {k: v.get("verdict") for k, v in items.items()},
        "record": str(out_path.relative_to(REPO_ROOT)),
        "report": str(report_path.relative_to(REPO_ROOT)),
    }, indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
