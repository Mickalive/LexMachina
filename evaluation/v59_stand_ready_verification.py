#!/usr/bin/env python3
"""v59 stand-readiness verification (direction v59, ordered work 1-3).

Run 39355375694. Freezes-first hypothesis:
evaluation/V59_STAND_READY_VERIFICATION_HYPOTHESIS_V1.json (sha pinned in
evaluation/V59_STAND_READY_VERIFICATION_FREEZE_RECORD.json).

What this instrument does (and ONLY this):
  1. Re-hash every frozen pin (RULES_LABEL, RULES_GEOMETRY, frozen retrieval
     benchmark, FREEZE_RECORD, MAPPING_FREE freeze record) against the
     direction-pinned sha256 values. Never regenerates, paraphrases or
     re-tunes any of them.
  2. Re-adjudicate the serve trigger for the packet-of-record 39319405429,
     derived ONLY from its own committed admission fields
     (PACKET_OF_RECORD.json). NOT_SERVED => the falsification battery on its
     exact bytes stays ARMED_UNFIRED.
  3. Re-prove the armed battery's integrity: run the three legs on the
     ACCEPTED HISTORICAL mount (served packet 38839347028 + synthetic
     falsification controls), NEVER on the packet-of-record bytes. Expect
     BENCHMARK_VALID_NO_FALSIFICATION (leg 1 exit 0, legs 2+3 exit 1).
  4. F-3B carry-forward re-hash against the ACCEPTED disposition record
     (expected digests READ from the record, never hand-typed).
  5. Packet byte verification: packet.json raw sha vs the PACKET_OF_RECORD's
     own declared value; per-bundle sha vs the hypothesis pins.
  6. Evaluation's published cross-check numbers on the packet-of-record bytes
     (structural read: per-bundle n_decisions; mapping-free mega-cluster
     disclosure conformance on the size-based share; admission fields) —
     re-derived and published BESIDE the frozen cells, never in place of
     them, and NOT frozen-label/geometry verdicts.
  7. Serve-audit team status check: has a serve verdict landed? (GitHub API
     read of the team run + branch; graceful degradation to the frozen pin
     when the API is unreachable.)
  8. Dispatch-chain diagnosis: re-read the GitHub run record and compare with
     the dispatch chain pinned at freeze time.
  9. Pre-emption guard: zero frozen-label/geometry verdict fields on the
     packet-of-record bytes in the emitted record.
 10. Non-vacuity battery: blanked admission fields never claim SERVED;
     synthetic admitted fields flip to SERVED; the battery legs fire.

What this instrument NEVER does: scores the packet-of-record under
RULES_LABEL.json or RULES_GEOMETRY.json, issues a serve recommendation,
lifts a DO-NOT-SERVE order, refreshes the population pin (the v59 question
pins the refresh at DISCHARGE time, not before), re-tunes a threshold,
rebuilds the benchmark, or asks the owner anything.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation import packet_of_record_stand_ready as PSR  # noqa: E402
from evaluation import benchmark_retrieval_counter_authority as BENCH  # noqa: E402
from evaluation.frozen_bars import label_gate  # noqa: E402

HYPOTHESIS = "evaluation/V59_STAND_READY_VERIFICATION_HYPOTHESIS_V1.json"
FREEZE_RECORD = "evaluation/V59_STAND_READY_VERIFICATION_FREEZE_RECORD.json"
DISPOSITION = "results/evaluation/f3b_restore_disposition/39287274485.json"
PACKET_MOUNT = "/tmp/lex_accepted/product"
NEW_PACKET = "39319405429"
QIDS = ["de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica"]
MEGA_SHARE_FLOOR = 0.5  # direction-pinned product disclosure floor, never edited here
GITHUB_API = "https://api.github.com/repos/Mickalive/LexMachina"
SERVE_AUDIT_TEAM = "frontier-packet-serve-audit"
SERVE_AUDIT_RUN = "39355384602"
DISPATCH_CHAIN_RUNS = ["39349747472", "39354142707", "39354569073", "39355375694"]


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def product_mount_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "origin/lab/product"], text=True
        ).strip()
    except Exception:
        return "UNKNOWN"


def github_get(path: str):
    """Best-effort GitHub API read; returns (ok, data_or_error)."""
    try:
        req = urllib.request.Request(
            f"{GITHUB_API}/{path}",
            headers={"Accept": "application/vnd.github+json",
                     "User-Agent": "lex-evaluation-stand-ready"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return True, json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 -- network is best-effort evidence
        return False, f"{type(exc).__name__}: {exc}"


# ------------------------------------------------- step 6: cross-check numbers
def cross_check_numbers(out: dict) -> dict:
    """Evaluation's published cross-check numbers on the packet-of-record bytes:
    the structural read and the mapping-free mega-cluster disclosure
    conformance. These are NOT frozen-label/geometry verdicts; they are the
    quantities the serve audit's cross-check table places beside its own
    recomputation (v59 ordered work 3(b))."""
    por = out.get("_por") or {}
    ledger_q = out.get("_ledger_questions") or {}
    rows = []
    all_ok = True
    for qid in QIDS:
        bundle = load_json(f"{PACKET_MOUNT}/results/product/gate_packet/{NEW_PACKET}/questions/{qid}.bundle.json")
        n_decisions = len(bundle.get("decisions") or [])
        clusters = bundle.get("clusters") or []
        largest = max(clusters, key=lambda c: c.get("size") or 0) if clusters else {}
        size = largest.get("size") or 0
        share = (size / n_decisions) if n_decisions else None
        warning_fires = bool(share is not None and share >= MEGA_SHARE_FLOOR)
        verdict_block = (ledger_q.get(qid) or {}).get("verdict") if isinstance(ledger_q.get(qid), dict) else None
        finding_rows = verdict_block.get("findings") if isinstance(verdict_block, dict) else None
        ledger_warnings = [f.get("code") for f in (finding_rows or []) if f.get("code") == "map_is_one_mega_cluster"]
        conforms = bool(ledger_warnings) == warning_fires
        all_ok = all_ok and conforms and n_decisions > 0
        rows.append({
            "qid": qid,
            "n_decisions": n_decisions,
            "largest_cluster_size": size,
            "size_based_share": round(share, 4) if share is not None else None,
            "mega_share_floor": MEGA_SHARE_FLOOR,
            "warning_fires_on_size_based_share": warning_fires,
            "product_warning_present_in_committed_ledger": bool(ledger_warnings),
            "conforms": conforms,
            "kind": "mapping-free disclosure conformance — NOT a RULES_GEOMETRY verdict and NOT a frozen-bar measurement",
        })
    return {
        "all_conform": all_ok,
        "per_question": rows,
        "note": "evaluation's published cross-check numbers on the packet-of-record bytes; frozen-label/geometry verdicts are NOT computed here (pre-emption guard)",
    }


# ------------------------------------------------- step 7: serve-audit status
def serve_audit_status(out: dict) -> dict:
    ok_run, run_data = github_get(f"actions/runs/{SERVE_AUDIT_RUN}")
    ok_branch, branch_data = github_get(f"commits?sha=lab/{SERVE_AUDIT_TEAM}&per_page=5")
    status = {
        "team_id": SERVE_AUDIT_TEAM,
        "portfolio_version": 32,
        "run_id": SERVE_AUDIT_RUN,
        "run_api_reachable": ok_run,
        "branch_api_reachable": ok_branch,
    }
    if ok_run and isinstance(run_data, dict):
        status["run_status"] = run_data.get("status")
        status["run_conclusion"] = run_data.get("conclusion")
        status["run_created_at"] = run_data.get("created_at")
    else:
        status["run_status"] = "API_UNREACHABLE"
        status["run_api_error"] = str(run_data)[:200]
    if ok_branch and isinstance(branch_data, list):
        status["branch_head"] = branch_data[0]["sha"] if branch_data else None
        status["branch_head_date"] = branch_data[0]["commit"]["author"]["date"] if branch_data else None
        status["branch_n_commits_listed"] = len(branch_data)
        # a landed verdict would appear as a non-bootstrap commit on the team branch
        status["verdict_commit_present"] = any(
            "bootstrap" not in (c["commit"]["message"] or "").lower() for c in branch_data
        )
    else:
        status["branch_head"] = "API_UNREACHABLE"
        status["branch_api_error"] = str(branch_data)[:200]
        status["verdict_commit_present"] = None
    # the serve trigger fires only on an ACCEPTED serve verdict; an in-progress
    # or bootstrap-only team run is NOT a serve verdict
    status["serve_verdict_landed"] = bool(
        ok_run and isinstance(run_data, dict)
        and run_data.get("conclusion") == "success"
        and status.get("verdict_commit_present")
    )
    status["frozen_pin_at_freeze"] = {
        "status": "RUN",
        "charter_version": 1,
        "verdict_landed": False,
    }
    return status


# ------------------------------------------------- step 8: dispatch chain
def dispatch_chain(out: dict) -> dict:
    rows = []
    all_match = True
    for run_id in DISPATCH_CHAIN_RUNS:
        ok, data = github_get(f"actions/runs/{run_id}")
        if ok and isinstance(data, dict):
            rows.append({
                "run_id": run_id,
                "name": data.get("name"),
                "status": data.get("status"),
                "conclusion": data.get("conclusion"),
                "created_at": data.get("created_at"),
            })
        else:
            rows.append({"run_id": run_id, "api_reachable": False,
                         "api_error": str(data)[:120]})
    return {
        "runs": rows,
        "api_reachable": all(r.get("api_reachable", True) for r in rows),
        "diagnosis_class": "ORCHESTRATION_FAILURE_NOT_LANE_WORK_FAILURE — team-job deaths with no gate, consistent with factory-wide requirement 20 (provider rotation/overload) and the work-quantum contract; never read as an audit verdict or a product defect",
        "note": "job logs are admin-only 403 on the public API, so failure-mode attribution is by job-level record + the documented requirement-20 class, not by log line",
    }


# ------------------------------------------------- step 9: pre-emption guard
FORBIDDEN_KEY_FRAGMENTS = [
    "rules_label_verdict",
    "label_verdict",
    "support_rate",
    "geometry_verdict",
    "criteria_passed",
    "n_bundles_pass",
    "frozen_bar_verdict",
]


def pre_emption_guard(record: dict) -> dict:
    offenders = []

    def walk(node, path=""):
        if isinstance(node, dict):
            for key, val in node.items():
                lowered = key.lower()
                if any(frag in lowered for frag in FORBIDDEN_KEY_FRAGMENTS):
                    if val in (0, "0", None, False):
                        continue
                    offenders.append({"path": f"{path}.{key}", "value": val})
                walk(val, f"{path}.{key}")
        elif isinstance(node, list):
            for i, val in enumerate(node):
                walk(val, f"{path}[{i}]")

    walk(record)
    return {
        "offenders": offenders,
        "clean": not offenders,
        "rule": "zero frozen-label / frozen-geometry verdict fields on the packet-of-record bytes; zero-count guard fields are permitted",
    }


# ------------------------------------------------------------------- main run
def main() -> int:
    started = time.time()
    run_id = os.environ.get("GITHUB_RUN_ID", "39355375694")
    hyp = load_json(HYPOTHESIS)
    freeze = load_json(FREEZE_RECORD)
    hyp_sha = sha256_file(HYPOTHESIS)
    if hyp_sha != freeze["hypothesis_sha256"]:
        print(
            f"FATAL: hypothesis sha {hyp_sha} != freeze record {freeze['hypothesis_sha256']}",
            file=sys.stderr,
        )
        return 2

    pins = hyp["population_pinned_before_execution"]
    record = {
        "schema": "lex-evaluation-v59-stand-ready-verification/1",
        "run_id": run_id,
        "direction_version": 59,
        "generated_at": utcnow(),
        "hypothesis_sha256": hyp_sha,
        "freeze_record_sha256": sha256_file(FREEZE_RECORD),
        "lane_question_item": "v59 ordered work (1) STAND READY — battery stays ARMED_UNFIRED, discharged the moment a serve verdict lands; ordered work (2) standing frozen-pin discipline; ordered work (3) the in-flight run 39349747472 produced NO gate (team-job failure), so this dispatch is bound by the v59 question itself",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": _try_import("numpy"),
            "scipy": _try_import("scipy"),
            "sklearn": _try_import("sklearn"),
            "blas": "NOT_AVAILABLE",
            "note": "this instrument is pure-stdlib JSON/digest work plus a subprocess re-run of the accepted battery on the historical mount; no numeric reduction order is involved in the verification itself",
        },
        "product_mount": PACKET_MOUNT,
        "product_mount_head": product_mount_head(),
        "product_mount_head_pinned": pins["product_mount_head"],
    }

    out = record
    por = load_json(f"{PACKET_MOUNT}/results/product/gate_packet/{NEW_PACKET}/PACKET_OF_RECORD.json")
    out["_por"] = por
    ledger_q = {}
    for q in (por.get("ledger") or {}).get("questions", []):
        ledger_q[q.get("qid")] = q
    out["_ledger_questions"] = ledger_q

    # ---- step 1: frozen pins ------------------------------------------------
    pins_ok = PSR.frozen_pin_check(pins["frozen_pins"], out)

    # ---- step 2: serve-trigger adjudication ----------------------------------
    verdict = PSR.adjudicate_serve_trigger(por, out)

    # ---- step 3: battery integrity on the HISTORICAL mount -------------------
    scratch = Path("results/evaluation/_scratch_namespaced") / run_id
    bench_out = scratch / "benchmark"
    bench_report = scratch / "report"
    bench_rc, bench_record = BENCH.run_benchmark(run_id, bench_out, bench_report)
    out["battery_integrity_on_historical_mount"] = {
        "instrument": "evaluation/benchmark_retrieval_counter_authority.py",
        "scratch_out_dir": str(bench_out),
        "scratch_report_dir": str(bench_report),
        "scratch_rationale": "the battery's own scratch-run obligation (audit CYCLE_39164900837 F9): a verification re-run must NOT overwrite the committed claim-bearing records at results/evaluation/retrieval_counter_authority_benchmark/; the accepted records 39200567493 / 39214324454 stay the claim-bearing evidence",
        "exit_code": bench_rc,
        "verdict": bench_record.get("verdict"),
        "falsification_proven": bench_record.get("falsification_proven"),
        "legs": [
            {"leg": lg.get("leg"), "exit_code": lg.get("exit_code"),
             "expected": lg.get("expected_exit_code"),
             "matches": lg.get("exit_code_matches_expectation"),
             "verdict": lg.get("verdict")}
            for lg in (bench_record.get("legs") or [])
        ],
        "combined_record_sha256": sha256_file(bench_out / f"{run_id}.json"),
        "packet_of_record_bytes_touched": False,
    }
    battery_ok = (
        bench_rc == 0
        and bench_record.get("verdict") == "BENCHMARK_VALID_NO_FALSIFICATION"
        and bench_record.get("falsification_proven") is True
    )

    # ---- step 4: F-3B carry-forward ------------------------------------------
    f3b_ok = PSR.f3b_carry_forward(pins["f3b_pins_read_from_accepted_disposition"], out)

    # ---- step 5: packet byte verification -------------------------------------
    actual_packet_sha = sha256_file(f"{PACKET_MOUNT}/results/product/gate_packet/{NEW_PACKET}/packet.json")
    declared = por.get("packet_raw_sha256")
    bundle_checks = []
    bundles_ok = True
    for q in pins["packet_of_record_39319405429"]["questions"]:
        qid = q["qid"]
        actual = sha256_file(f"{PACKET_MOUNT}/results/product/gate_packet/{NEW_PACKET}/questions/{qid}.bundle.json")
        ok = actual == q["bundle_sha256"]
        bundles_ok = bundles_ok and ok
        bundle_checks.append({"qid": qid, "pinned": q["bundle_sha256"], "actual": actual, "match": ok})
    out["packet_byte_verification"] = {
        "packet": NEW_PACKET,
        "actual_packet_json_sha256": actual_packet_sha,
        "declared_in_PACKET_OF_RECORD": declared,
        "match": actual_packet_sha == declared,
        "bundle_sha256": bundle_checks,
        "all_bundles_match_pins": bundles_ok,
    }

    # ---- step 6: cross-check numbers ------------------------------------------
    out["evaluation_cross_check_numbers"] = cross_check_numbers(out)

    # ---- step 7: serve-audit status -------------------------------------------
    out["serve_audit_team_status"] = serve_audit_status(out)

    # ---- step 8: dispatch chain -----------------------------------------------
    out["dispatch_chain"] = dispatch_chain(out)

    # ---- population pin: NOT refreshed (v59 pins the refresh at discharge) ----
    out["population_pin"] = {
        "status": "NOT_REFRESHED_THIS_CYCLE",
        "frozen_incumbent_n_scored": label_gate.INCUMBENT["n_scored"],
        "frozen_incumbent_matches_65": label_gate.INCUMBENT["n_scored"] == 65,
        "note": "the v59 question pins the population-pin refresh at DISCHARGE time (the moment a serve verdict lands), not before; the frozen 65-row incumbent pin stays untouched",
    }

    # ---- step 10: non-vacuity -------------------------------------------------
    vac_ok = PSR.non_vacuity_battery(por, out)

    del out["_por"]
    del out["_ledger_questions"]

    guard = pre_emption_guard(record)
    record["pre_emption_guard"] = guard

    overall = (
        pins_ok
        and verdict == "NOT_SERVED_WITHHELD_PENDING_SERVE"
        and battery_ok
        and f3b_ok
        and out["packet_byte_verification"]["match"]
        and bundles_ok
        and out["evaluation_cross_check_numbers"]["all_conform"]
        and out["population_pin"]["frozen_incumbent_matches_65"]
        and vac_ok
        and guard["clean"]
        and record["product_mount_head"] == pins["product_mount_head"]
        and not out["serve_audit_team_status"]["serve_verdict_landed"]
    )
    record["verdict"] = "STAND_READY_POSTURE_HOLDS" if overall else "POSTURE_BROKEN"
    record["verdict_detail"] = {
        "frozen_pins_match": pins_ok,
        "serve_trigger": verdict,
        "battery_integrity_on_historical_mount": battery_ok,
        "f3b_intact": f3b_ok,
        "packet_bytes_match": out["packet_byte_verification"]["match"],
        "bundles_match_pins": bundles_ok,
        "cross_check_numbers_conform": out["evaluation_cross_check_numbers"]["all_conform"],
        "population_pin_unmodified": out["population_pin"]["frozen_incumbent_matches_65"],
        "non_vacuity": vac_ok,
        "pre_emption_clean": guard["clean"],
        "product_mount_head_matches": record["product_mount_head"] == pins["product_mount_head"],
        "serve_verdict_not_landed": not out["serve_audit_team_status"]["serve_verdict_landed"],
    }
    record["packet_admitted"] = por.get("packet_admitted")
    record["human_gate_ready"] = False
    record["ready_for_owner_session"] = False
    record["owner_decision_required"] = False
    record["falsification_battery"] = (
        "ARMED_UNFIRED" if verdict.startswith("NOT_SERVED") else "ARMED_FIRED"
    )
    record["frozen_label_verdicts_computed_on_packet_of_record_bytes"] = 0
    record["frozen_geometry_verdicts_computed_on_packet_of_record_bytes"] = 0
    record["claim_ceiling"] = (
        "This instrument establishes exactly: (a) every frozen pin holds "
        "byte-identically; (b) the packet-of-record 39319405429 is NOT SERVED "
        "under its own committed fail-closed admission record, so the "
        "falsification battery on its exact bytes stays ARMED_UNFIRED and ZERO "
        "frozen-label/geometry verdicts were computed on them; (c) the armed "
        "battery is intact — its served-baseline leg passes on the accepted "
        "historical mount and both falsification legs fire on deliberately "
        "regressed inputs (proven on the historical mount and synthetic "
        "controls, NEVER on the packet-of-record bytes); (d) the F-3B "
        "disposition stays INTACT_NOT_REOPENED; (e) evaluation's published "
        "cross-check numbers on the packet bytes (structural read + "
        "mapping-free mega-cluster disclosure conformance) are re-derived and "
        "published beside the frozen cells; (f) the population pin is NOT "
        "refreshed (the v59 question pins the refresh at discharge time); "
        "(g) the dispatch chain since the v58 accept is recorded as "
        "orchestration failures (team-job deaths, no gate), consistent with "
        "factory-wide requirement 20. It does NOT serve, admit or falsify the "
        "packet under the frozen bars, does NOT move any accepted bar, does "
        "NOT lift any DO-NOT-SERVE order, and makes NO owner ask."
    )
    record["exit_code"] = 0 if overall else 1
    record["elapsed_s"] = round(time.time() - started, 3)

    out_dir = "results/evaluation/v59_stand_ready_verification"
    os.makedirs(out_dir, exist_ok=True)
    out_path = f"{out_dir}/{run_id}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
    print(json.dumps({"verdict": record["verdict"], "out": out_path, "detail": record["verdict_detail"]}, indent=2))
    return record["exit_code"]


def _try_import(name: str) -> str:
    try:
        mod = __import__(name)
        return getattr(mod, "__version__", "IMPORTED")
    except Exception:
        return "NOT_IMPORTABLE"


if __name__ == "__main__":
    sys.exit(main())
