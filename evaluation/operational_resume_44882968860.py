#!/usr/bin/env python3
"""Operational-resume verification for evaluation run 44882968860.

Read-only checks: re-hashes every freeze pin, compares the fresh benchmark
re-execution against committed records, verifies the persisted snapshot's shim
delta is byte-identical, confirms the v68 item-(1) correction is present,
confirms zero audit-namespace paths and a clean write-scope simulation, and
records the fail-closed posture. Writes
results/evaluation/operational_resume_44882968860/verification_44882968860.json.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/evaluation/operational_resume_44882968860"
RUN = "44882968860"
ACCEPTED_BASE = "ea98384e54d31d2e694c418a1d1ce5769fc6c32f"
SNAPSHOT = "519d6bc79b6097f06c724ae137a5be651d5ba2ef"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def gate_ids(records) -> set:
    return {g if isinstance(g, str) else g.get("gate", json.dumps(g, sort_keys=True)) for g in records}


def gate_details(records) -> dict:
    out = {}
    for g in records:
        if isinstance(g, str):
            out[g] = None
        else:
            out[g.get("gate", json.dumps(g, sort_keys=True))] = g.get("detail")
    return out


def main() -> int:
    checks: list[dict] = []

    def check(name: str, ok: bool, detail) -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    # --- H2: benchmark reproduction -------------------------------------
    new = load(OUT / f"{RUN}_verify.json")
    targets = {
        "44870660846": ROOT / "results/evaluation/minimal_ca_falsify_benchmark/44870660846.json",
        "44870538384": ROOT / "results/evaluation/minimal_ca_falsify_benchmark/44870538384.json",
    }
    expected_failed = [
        "mf::concept_coverage::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::fr-bail-entretien",
        "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
    ]
    comparisons = {}
    for rid, path in targets.items():
        ref = load(path)
        cmp_ = {
            "ref_record": str(path.relative_to(ROOT)),
            "ref_sha256": sha256(path),
            "verdict_equal": ref["verdict"] == new["verdict"],
            "n_gates_equal": ref["n_gates"] == new["n_gates"],
            "n_passed_equal": ref["n_passed"] == new["n_passed"],
            "n_failed_equal": ref["n_failed"] == new["n_failed"],
            "failed_gates_set_equal": gate_ids(ref["failed_gates"]) == gate_ids(new["failed_gates"]),
            "failed_gate_details_equal": gate_details(ref["failed_gates"]) == gate_details(new["failed_gates"]),
            "product_mount_head_equal": ref.get("product_mount_head") == new.get("product_mount_head"),
            "run_valid_equal": ref.get("run_valid") == new.get("run_valid"),
            "input_drift_empty": new.get("input_drift") == [],
            "direction_version_68": new.get("direction_version") == 68,
        }
        cmp_["all_equal"] = all(v for k, v in cmp_.items() if k.endswith(("equal", "empty", "68")))
        comparisons[rid] = cmp_
    check("H2_reproduces_committed_records", all(c["all_equal"] for c in comparisons.values()), comparisons)
    check("H2_expected_failed_gate_set", gate_ids(new["failed_gates"]) == set(expected_failed), sorted(gate_ids(new["failed_gates"])))

    ref_ceiling = load(targets["44870660846"]).get("claim_ceiling")
    ceiling = str(new.get("claim_ceiling", ""))
    check("H2_claim_ceiling_unchanged_and_fail_closed", ceiling == ref_ceiling, {
        "equal_to_committed_record": ceiling == ref_ceiling,
        "this_run_claim_ceiling_note": "verification re-execution of the frozen instrument on packet-of-record 39319405429; not a second independent falsification, not a re-score, not a serve verdict, no bar moved",
    })

    # --- freeze pin re-hash ----------------------------------------------
    freeze = load(ROOT / f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json")
    pin_results = {}
    for section in ("frozen_instruments", "comparison_targets", "item1_deliverable_pins", "test_file_pins"):
        for rel, want in freeze[section].items():
            got = sha256(ROOT / rel)
            pin_results[rel] = {"section": section, "expected": want, "actual": got, "match": got == want}
    for rel, want in freeze["snapshot_shim_pin"].items():
        if rel == "note" or not isinstance(want, str) or len(want) != 64:
            continue
        got = sha256(ROOT / rel)
        pin_results[rel] = {"section": "snapshot_shim_pin", "expected": want, "actual": got, "match": got == want}
    check("freeze_pins_rehash_equal", all(v["match"] for v in pin_results.values()), pin_results)

    # frozen rubrics pinned by reference (verify the vendored copies still hash equal)
    rubric_pins = {}
    for name, want in freeze["frozen_rules_reference"].items():
        if name.startswith("RULES_"):
            p = ROOT / "evaluation/frozen_bars" / name
            got = sha256(p) if p.exists() else None
            rubric_pins[name] = {"expected": want, "actual": got, "match": got == want}
    check("frozen_rubrics_by_reference_unchanged", all(v["match"] for v in rubric_pins.values()), rubric_pins)

    # --- H3: snapshot shim preserved byte-identical ----------------------
    shim_rel = "results/evaluation/orchestration/local_pytest_shim.json"
    git_bytes = subprocess.run(
        ["git", "show", f"{SNAPSHOT}:{shim_rel}"], cwd=ROOT, capture_output=True, check=True
    ).stdout
    git_sha = hashlib.sha256(git_bytes).hexdigest()
    work_sha = sha256(ROOT / shim_rel)
    check("H3_snapshot_shim_byte_identical", git_sha == work_sha == freeze["snapshot_shim_pin"][shim_rel], {
        "snapshot": SNAPSHOT, "git_blob_sha256": git_sha, "worktree_sha256": work_sha,
        "delta_vs_parent": "one M line only (local_pytest_shim.json)", "edited_by_resume": False,
    })

    # --- H3: item-(1) correction present ---------------------------------
    correction_md = ROOT / "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md"
    correction_json = ROOT / "results/evaluation/bypass_clause_correction/40113448025.json"
    check("H3_item1_correction_present", correction_md.exists() and correction_json.exists(), {
        "report": str(correction_md.relative_to(ROOT)), "report_sha256": sha256(correction_md),
        "record": str(correction_json.relative_to(ROOT)), "record_sha256": sha256(correction_json),
    })

    # --- H3: shim reproducibility ----------------------------------------
    shim = load(OUT / "no_pytest_44882968860.json")
    primary = [r for r in shim["results"] if r["test_file"] == "tests/evaluation/test_minimal_ca_falsify_benchmark.py"]
    disclosed = [r for r in shim["results"] if r["test_file"] == "tests/evaluation/test_retrieval_benchmark.py"]
    check("H3_no_pytest_shim_reproduces_SHIM_PASS_8_8",
          shim["verdict"] == "SHIM_PASS" and shim["n_passed"] == 8 and shim["n_failed"] == 0
          and len(primary) == 1 and primary[0]["status"] == "PASS" and primary[0]["n_passed"] == 8,
          {
              "verdict": shim["verdict"], "n_passed": shim["n_passed"], "n_failed": shim["n_failed"],
              "primary": primary[0]["status"] if primary else None,
              "multilingual_import_error_disclosed_not_counted": bool(disclosed) and disclosed[0]["status"] == "IMPORT_ERROR",
              "pytest_available": shim["pytest_available"],
          })

    # --- H3: tree-level scope check vs accepted base ----------------------
    diff = subprocess.run(
        ["git", "diff", "--name-only", ACCEPTED_BASE, "HEAD"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    audit_paths = [p for p in diff if p.startswith(("reports/audit/", "results/audit/"))]
    check("H3_tree_diff_vs_accepted_base_has_no_audit_namespace_paths", audit_paths == [],
          {"n_diff_paths": len(diff), "audit_paths": audit_paths})

    # --- H3: guard predicate simulation over current porcelain ------------
    porcelain = subprocess.run(
        ["git", "status", "--porcelain", "-uall"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    allowed_prefixes = ("evaluation/", "tests/evaluation/", "results/evaluation/", "reports/evaluation/", "state/evaluation.json", "data/evaluation/")
    bad = [line[3:] for line in porcelain if line[3:] and not line[3:].startswith(allowed_prefixes)]
    check("H3_guard_simulation_n_bad_zero", bad == [], {"n_entries": len(porcelain), "bad_paths": bad})

    # --- H1: audit ref absence -------------------------------------------
    audit_ref = subprocess.run(
        ["git", "rev-parse", "--verify", "origin/cycle/core/evaluation/44879155219/audit"],
        cwd=ROOT, capture_output=True, text=True,
    )
    gate_in_tree = (ROOT / "results/audit/evaluation/CYCLE_44879155219_GATE.json").exists()
    check("H1_no_audit_ref_no_gate_for_44879155219", audit_ref.returncode != 0 and not gate_in_tree, {
        "audit_ref_resolves": audit_ref.returncode == 0, "gate_file_in_tree": gate_in_tree,
        "failure_class": "AUDIT_AGENT_STEP_FAILURE_NO_GATE",
    })

    # --- posture ----------------------------------------------------------
    posture = {k: new.get(k) for k in ("packet_admitted", "machine_gate_ready", "human_gate_ready", "ready_for_owner_session", "no_174k_benchmark_rerun", "no_new_thresholds")}
    check("posture_fail_closed",
          posture["packet_admitted"] is False and posture["machine_gate_ready"] is False
          and posture["human_gate_ready"] is False and posture.get("ready_for_owner_session") in (False, None)
          and posture["no_174k_benchmark_rerun"] is True,
          posture)
    check("direction_version_pinned_68", new.get("direction_version") == 68, new.get("direction_version"))

    n_pass = sum(1 for c in checks if c["pass"])
    n_fail = len(checks) - n_pass
    out = {
        "schema": "lex-evaluation-operational-resume-verification/1",
        "lane": "evaluation", "run": int(RUN),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checks": checks, "n_checks": len(checks), "n_pass": n_pass, "n_fail": n_fail,
        "verdict": "VERIFICATION_PASS" if n_fail == 0 else "VERIFICATION_FAIL",
        "benchmark_reproduction": {
            "run_id": new["run_id"], "verdict": new["verdict"], "n_gates": new["n_gates"],
            "n_passed": new["n_passed"], "n_failed": new["n_failed"],
            "failed_gates": new["failed_gates"], "product_mount_head": new["product_mount_head"],
            "run_valid": new["run_valid"], "input_drift": new["input_drift"],
            "claim_ceiling": "verification re-execution of the frozen instrument on packet-of-record 39319405429; not a second independent falsification, not a re-score, not a serve verdict",
        },
        "ordered_work_status": {
            "1_correction_of_record": "PRESENT_AND_VERIFIED (not re-run, not changed)",
            "2_conditional_remeasure": "NOT_YET_DISCRIMINATING (no post-repair full flagship family landed by Core Product; no synthetic stand-in; standing falsification NOT re-run as a substitute)",
            "3_standing_falsification_record": "UNCHANGED - PRODUCT_FALSIFIED on packet-of-record 39319405429 remains the record of record",
            "4_non_blocking_required_fixes": "reported only where those counts are quoted",
            "5_no_rederivation": "honoured - this resume is operational verification, recorded as operational, not as new evidence",
        },
        "posture": posture,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"verification_{RUN}.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": out["verdict"], "n_pass": n_pass, "n_fail": n_fail}))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
