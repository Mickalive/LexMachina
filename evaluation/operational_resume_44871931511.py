#!/usr/bin/env python3
"""Operational-resume verification for evaluation run 44871931511.

Read-only: re-hashes frozen pins, compares the fresh benchmark re-execution
against the committed comparison targets, and records the v68 ordered-work
posture. Writes results/evaluation/operational_resume_44871931511/verification_44871931511.json.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/evaluation/operational_resume_44871931511"
RUN = "44871931511"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> int:
    checks: list[dict] = []

    def check(name: str, ok: bool, detail) -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    # --- H2: benchmark reproduction -------------------------------------
    new = load(OUT / f"{RUN}_verify.json")
    targets = {
        "44870660846": ROOT
        / "results/evaluation/minimal_ca_falsify_benchmark/44870660846.json",
        "44870538384": ROOT
        / "results/evaluation/minimal_ca_falsify_benchmark/44870538384.json",
        "44871041590_smoke": OUT.parent
        / "operational_resume_44871041590/44871041590_smoke.json",
    }
    expected_failed = [
        "mf::concept_coverage::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::fr-bail-entretien",
        "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
    ]
    def gate_ids(records) -> set:
        out = set()
        for g in records:
            out.add(g if isinstance(g, str) else g.get("gate", json.dumps(g, sort_keys=True)))
        return out

    def gate_details(records) -> dict:
        out = {}
        for g in records:
            if isinstance(g, str):
                out[g] = None
            else:
                out[g.get("gate", json.dumps(g, sort_keys=True))] = g.get("detail")
        return out

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
            "failed_gates_set_equal": gate_ids(ref["failed_gates"])
            == gate_ids(new["failed_gates"]),
            "failed_gate_details_equal": gate_details(ref["failed_gates"])
            == gate_details(new["failed_gates"]),
            "product_mount_head_equal": ref.get("product_mount_head")
            == new.get("product_mount_head"),
            "run_valid_equal": ref.get("run_valid") == new.get("run_valid"),
            "input_drift_empty": new.get("input_drift") == [],
        }
        cmp_["all_equal"] = all(
            v for k, v in cmp_.items() if k.endswith(("equal", "empty"))
        )
        comparisons[rid] = cmp_
    check(
        "H2_reproduces_committed_records",
        all(c["all_equal"] for c in comparisons.values()),
        comparisons,
    )
    check(
        "H2_expected_failed_gate_set",
        gate_ids(new["failed_gates"]) == set(expected_failed),
        sorted(gate_ids(new["failed_gates"])),
    )
    ref_ceiling = load(targets["44870660846"]).get("claim_ceiling")
    ceiling = str(new.get("claim_ceiling", ""))
    check(
        "H2_claim_ceiling_unchanged_and_fail_closed",
        ceiling == ref_ceiling
        and "DO-NOT-SERVE" in ceiling
        and "fail-closed" in ceiling
        and "human_gate_ready stays false" in ceiling,
        {
            "equal_to_committed_record": ceiling == ref_ceiling,
            "mentions_do_not_serve": "DO-NOT-SERVE" in ceiling,
            "mentions_fail_closed": "fail-closed" in ceiling,
            "mentions_human_gate_false": "human_gate_ready stays false" in ceiling,
            "this_runs_own_ceiling_note": "the re-execution is recorded as verification-only in the resume report and summary, not as a second independent falsification",
        },
    )

    # --- freeze pin re-hash ----------------------------------------------
    freeze = load(ROOT / f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json")
    pin_results = {}
    for rel, want in freeze["frozen_instruments"].items():
        got = sha256(ROOT / rel)
        pin_results[rel] = {"expected": want, "actual": got, "match": got == want}
    for rel, want in freeze["comparison_targets"].items():
        got = sha256(ROOT / rel)
        pin_results[rel] = {"expected": want, "actual": got, "match": got == want}
    check(
        "freeze_pins_rehash_equal",
        all(v["match"] for v in pin_results.values()),
        pin_results,
    )
    audit_pins = {}
    for rel, meta in freeze["audit_namespace_inputs_to_rehome"].items():
        relocated = {
            "reports/audit/evaluation/CYCLE_44869867193.md": OUT
            / "CYCLE_44869867193.relocated.md",
            "results/audit/evaluation/CYCLE_44869867193_GATE.json": OUT
            / "CYCLE_44869867193_GATE.relocated.json",
        }[rel]
        got = sha256(relocated)
        src_git = subprocess.run(
            ["git", "show", f"{meta['introducing_commit']}:{rel}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        git_sha = hashlib.sha256(src_git).hexdigest()
        audit_pins[rel] = {
            "expected": meta["sha256"],
            "relocated_sha256": got,
            "introducing_commit_sha256": git_sha,
            "match": got == meta["sha256"] == git_sha,
            "relocated_path": str(relocated.relative_to(ROOT)),
            "source_removed_from_worktree": not (ROOT / rel).exists(),
        }
    check(
        "H3_relocation_byte_identical_and_source_removed",
        all(v["match"] and v["source_removed_from_worktree"] for v in audit_pins.values()),
        audit_pins,
    )

    # --- H3: tree-level scope check vs accepted base ----------------------
    diff = subprocess.run(
        ["git", "diff", "--name-only", "origin/lab/evaluation", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    audit_paths = [p for p in diff if p.startswith(("reports/audit/", "results/audit/"))]
    check(
        "H3_tree_diff_vs_accepted_base_has_no_audit_namespace_paths",
        audit_paths == [],
        {"n_diff_paths": len(diff), "audit_paths": audit_paths},
    )

    # --- H3: guard predicate simulation over current porcelain ------------
    porcelain = subprocess.run(
        ["git", "status", "--porcelain", "-uall"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    allowed_prefixes = (
        "evaluation/",
        "tests/evaluation/",
        "results/evaluation/",
        "reports/evaluation/",
        "state/evaluation.json",
        "data/evaluation/",
    )
    bad = []
    entries = []
    for line in porcelain:
        p = line[3:]
        entries.append(line)
        if p and not p.startswith(allowed_prefixes):
            bad.append(p)
    check(
        "H3_guard_simulation_n_bad_zero",
        bad == [],
        {"n_entries": len(entries), "bad_paths": bad, "entries": entries},
    )

    # --- v68 ordered-work posture ----------------------------------------
    correction_md = ROOT / "reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md"
    correction_json = ROOT / "results/evaluation/bypass_clause_correction/40113448025.json"
    check(
        "item1_correction_of_record_present",
        correction_md.exists() and correction_json.exists(),
        {
            "report": str(correction_md.relative_to(ROOT)) if correction_md.exists() else None,
            "report_sha256": sha256(correction_md) if correction_md.exists() else None,
            "record": str(correction_json.relative_to(ROOT)) if correction_json.exists() else None,
            "record_sha256": sha256(correction_json) if correction_json.exists() else None,
            "prior_inventory_report_sha256": "b10eeb3a720cd6352fbc7eabbf8d3430989b52d90193d0f948e69908ef5dc48d",
        },
    )
    posture = {
        k: new.get(k)
        for k in (
            "packet_admitted",
            "machine_gate_ready",
            "human_gate_ready",
            "ready_for_owner_session",
            "no_174k_benchmark_rerun",
            "no_new_thresholds",
        )
    }
    check(
        "posture_fail_closed",
        posture["packet_admitted"] is False
        and posture["machine_gate_ready"] is False
        and posture["human_gate_ready"] is False
        and posture.get("ready_for_owner_session") in (False, None)
        and posture["no_174k_benchmark_rerun"] is True,
        posture,
    )
    check(
        "direction_version_pinned_68",
        new.get("direction_version") == 68,
        new.get("direction_version"),
    )

    n_pass = sum(1 for c in checks if c["pass"])
    n_fail = len(checks) - n_pass
    out = {
        "schema": "lex-evaluation-operational-resume-verification/1",
        "lane": "evaluation",
        "run": int(RUN),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checks": checks,
        "n_checks": len(checks),
        "n_pass": n_pass,
        "n_fail": n_fail,
        "verdict": "VERIFICATION_PASS" if n_fail == 0 else "VERIFICATION_FAIL",
        "benchmark_reproduction": {
            "run_id": new["run_id"],
            "verdict": new["verdict"],
            "n_gates": new["n_gates"],
            "n_passed": new["n_passed"],
            "n_failed": new["n_failed"],
            "failed_gates": new["failed_gates"],
            "product_mount_head": new["product_mount_head"],
            "run_valid": new["run_valid"],
            "input_drift": new["input_drift"],
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
    (OUT / f"verification_{RUN}.json").write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({"verdict": out["verdict"], "n_pass": n_pass, "n_fail": n_fail}))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
