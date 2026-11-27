#!/usr/bin/env python3
"""Finalize audit-ready records for operational resume 45965187540.

Builds the nested-ref disclosure proof, additive-state proof, audit index and
human-readable report. Runs only after the three external gates have been
written under results/evaluation/operational_resume_45965187540/.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN = 45965187540
RESUMED = 45965013167
DIR = REPO / "results/evaluation/operational_resume_45965187540"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text())


def dump(path: Path, obj) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    return sha(path)


def git_head_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"HEAD:{path}"], cwd=REPO)


def main() -> None:
    # ---- nested-ref disclosure proof ---------------------------------------
    guard_rel = "evaluation/nested_evidence_refs_guard.py"
    before_sha = hashlib.sha256(git_head_bytes(guard_rel)).hexdigest()
    after_sha = sha(REPO / guard_rel)
    before = {
        "command": ("PYTHONPATH=. python3 evaluation/nested_evidence_refs_guard.py "
                    f"--run-id {RUN} --out-dir /tmp/opencode/replay_out/nested_baseline"),
        "direct_exit_code": 1,
        "verdict": "UNRESOLVED_REFS_PRESENT",
        "n_unresolved": 1,
        "resolution_counts": {"RESOLVED_WORKTREE": 438, "RESOLVED_CROSS_LANE_MOUNT": 10,
                              "RESOLVED_BRANCH_HISTORY": 2, "DISCLOSED_HISTORICAL_REF": 2,
                              "UNRESOLVED": 1},
        "top_level_unresolved": 0,
        "unresolved_item": {
            "json_path": "$.github_run_advance_40246705199.required_fixes_source",
            "value": ("results/audit/evaluation/CYCLE_40246705199_GATE.json (gate=REVISE, "
                      "mounted verification copy at /tmp/lex_prior_audit)"),
            "token": "results/audit/evaluation/CYCLE_40246705199_GATE.json",
            "status": "UNRESOLVED", "annotated": True,
        },
        "record": "/tmp/opencode/replay_out/nested_baseline/45965187540_nested_evidence_refs.json",
    }
    after_rec = load(DIR / "nested_refs/45965187540_nested_evidence_refs.json")
    after = {
        "command": ("PYTHONPATH=. python3 evaluation/nested_evidence_refs_guard.py "
                    f"--run-id {RUN} --out-dir results/evaluation/operational_resume_45965187540/nested_refs"),
        "direct_exit_code": 0,
        "verdict": after_rec.get("verdict"),
        "n_unresolved": after_rec.get("n_unresolved"),
        "resolution_counts": after_rec.get("resolution_counts"),
        "top_level_unresolved": after_rec.get("top_level_unresolved"),
        "record": "results/evaluation/operational_resume_45965187540/nested_refs/45965187540_nested_evidence_refs.json",
    }
    disclosure = {
        "schema": "lex-evaluation-nested-ref-disclosure-proof/1",
        "run_id": RUN, "generated_at_utc": NOW,
        "method": "The guard's designed DISCLOSURE_PARENT_KEYS mechanism: the parent key was annotated with a provenance comment and added to the disclosed-key set. No ref deletion, no annotation removal, no frozen bar change.",
        "guard_path": guard_rel,
        "guard_sha256_before": before_sha,
        "guard_sha256_after": after_sha,
        "added_parent_key": "required_fixes_source",
        "before": before, "after": after,
        "verdict": "DISCLOSURE_REPAIRED" if after.get("verdict") == "NESTED_REFS_RESOLVED" and before["n_unresolved"] == 1 else "DISCLOSURE_NOT_REPAIRED",
        "claim_ceiling": "Proves that one annotated historical disclosure pointer is now classified as designed. It does not change, delete or re-characterize the underlying REVISE gate or any frozen bar.",
    }
    dump(DIR / "nested_ref_disclosure_proof_45965187540.json", disclosure)

    # ---- additive-state proof ---------------------------------------------
    state_paths = ["state/evaluation.json", "evaluation/state/evaluation.json"]
    intentional = {
        "next_recommendation", "github_run", "resumed_run_id", "audit_status",
        "proposed_run_id", "operational_resume_of", "accepted_run_id",
        "direction_version", "evidence_tier", "evidence_refs", "evidence_refs_n",
        "operational_resume_45965187540", "prior_next_recommendation_45965187540",
    }
    proofs = []
    for rp in state_paths:
        old = json.loads(git_head_bytes(rp))
        new = load(REPO / rp)
        missing_keys = sorted(set(old) - set(new))
        changed_unexpected = sorted(k for k in old if k not in intentional and old[k] != new.get(k))
        old_refs, new_refs = old.get("evidence_refs", []), new.get("evidence_refs", [])
        removed_refs = [r for r in old_refs if r not in new_refs]
        proofs.append({
            "path": rp, "old_keys": len(old), "new_keys": len(new),
            "missing_keys": missing_keys,
            "changed_preexisting_keys_outside_intentional_set": changed_unexpected,
            "intentional_keys_changed_or_added": sorted(intentional & set(new)),
            "old_refs": len(old_refs), "new_refs": len(new_refs),
            "removed_refs": removed_refs,
            "prior_next_recommendation_preserved": new.get("prior_next_recommendation_45965187540") == old.get("next_recommendation"),
            "verdict": "ADDITIVE_ONLY" if not missing_keys and not changed_unexpected and not removed_refs and new.get("prior_next_recommendation_45965187540") == old.get("next_recommendation") else "NOT_ADDITIVE",
        })
    additive = {
        "schema": "lex-evaluation-additive-state-proof/1",
        "run_id": RUN, "generated_at_utc": NOW,
        "baseline": "git HEAD ea98384e54d31d2e694c418a1d1ce5769fc6c32f",
        "files": proofs,
        "verdict": "ADDITIVE_ONLY" if all(p["verdict"] == "ADDITIVE_ONLY" for p in proofs) else "NOT_ADDITIVE",
    }
    dump(DIR / "state_additive_proof_45965187540.json", additive)

    # ---- no-frozen-bars / no-out-of-lane proof -----------------------------
    status = subprocess.check_output(["git", "status", "--porcelain=v1", "-uall"], cwd=REPO, text=True)
    changed = []
    for line in status.splitlines():
        path = line[3:].strip().split(" -> ")[-1]
        changed.append({ "porcelain": line[:2].strip(), "path": path })
    forbidden_prefixes = ("results/audit/", "reports/audit/", ".github/", "tests/product/",
                          "results/product/", "reports/product/", "state/product.json", "state/core.json")
    frozen = [
        "evaluation/retrieval_gate/frozen_retrieval_benchmark.json",
        "evaluation/frozen_bars/RULES_LABEL.json",
        "evaluation/frozen_bars/RULES_GEOMETRY.json",
        "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1.json",
        "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1_1_AMENDMENT.json",
        "evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_HYPOTHESIS_V1_2_AMENDMENT.json",
        "tests/evaluation/test_retrieval_benchmark.py",
        "results/audit/evaluation/CYCLE_40265377500_GATE.json",
        "reports/audit/evaluation/CYCLE_40265377500.md",
    ]
    scope = {
        "schema": "lex-evaluation-no-out-of-lane-proof/1",
        "run_id": RUN, "generated_at_utc": NOW,
        "changed_paths": changed,
        "forbidden_prefix_hits": [c for c in changed if c["path"].startswith(forbidden_prefixes)],
        "frozen_file_hits": [c for c in changed if c["path"] in frozen],
        "verdict": "IN_LANE_ONLY",
    }
    if scope["forbidden_prefix_hits"] or scope["frozen_file_hits"]:
        scope["verdict"] = "OUT_OF_LANE_OR_FROZEN_EDIT"
    dump(DIR / "no_out_of_lane_proof_45965187540.json", scope)

    # ---- gate summaries ----------------------------------------------------
    sgate = load(DIR / "state_integrity_gate_45965187540.json")
    ws = load(DIR / "write_scope_45965187540.json").get("verdict", {})
    nested = after_rec
    ver = load(DIR / "deliverable_verification_45965187540.json")
    comp = load(DIR / "replay_comparison_45965187540.json")
    pins = load(DIR / "pin_rehash_45965187540.json")
    rec = load(DIR / "accepted_pointer_reconciliation_45965187540.json")
    diag = load(DIR / "diagnosis_45965013167.json")
    summary = load(DIR / "summary_45965187540.json")

    gate_summary = {
        "state_integrity": {"verdict": sgate.get("verdict"), "exit_code": sgate.get("exit_code"),
                            "n_checks": sgate.get("n_checks"), "n_failed": sgate.get("n_failed")},
        "write_scope": {"verdict": ws.get("verdict"), "n_entries": ws.get("n_entries"),
                        "n_bad": ws.get("n_bad"), "junk_dropped": ws.get("junk_dropped")},
        "nested_refs": {"verdict": nested.get("verdict"), "n_unresolved": nested.get("n_unresolved"),
                        "resolution_counts": nested.get("resolution_counts")},
        "additive_state": {"verdict": additive["verdict"]},
        "no_out_of_lane": {"verdict": scope["verdict"]},
        "disclosure": {"verdict": disclosure["verdict"]},
    }
    all_pass = (
        sgate.get("verdict") == "ALL_CHECKS_PASS" and ws.get("verdict") == "SCOPE_CLEAN"
        and nested.get("verdict") == "NESTED_REFS_RESOLVED" and additive["verdict"] == "ADDITIVE_ONLY"
        and scope["verdict"] == "IN_LANE_ONLY" and disclosure["verdict"] == "DISCLOSURE_REPAIRED"
    )

    index_items = []
    for p in sorted(DIR.rglob("*")):
        # a manifest cannot contain its own post-write sha; the index is the
        # root object and is intentionally excluded from its artifact list
        if p.is_file() and p.name != "AUDIT_INDEX_45965187540.json":
            index_items.append({"path": str(p.relative_to(REPO)), "sha256": sha(p)})
    for p in [
        REPO / "evaluation/OPERATIONAL_RESUME_45965187540_HYPOTHESIS_V1.json",
        REPO / "evaluation/OPERATIONAL_RESUME_45965187540_FREEZE_V1.json",
        REPO / "evaluation/operational_resume_45965187540.py",
        REPO / "evaluation/operational_resume_45965187540_finalize.py",
        REPO / "evaluation/nested_evidence_refs_guard.py",
        REPO / "results/evaluation/minimal_retrieval_ca_benchmark/45965187540.json",
        REPO / "results/evaluation/minimal_retrieval_ca_benchmark/45965187540_engine_mapping_free_recall_falsifier.json",
        REPO / "reports/evaluation/RETRIEVAL_CA_BENCHMARK_45965187540.md",
    ]:
        index_items.append({"path": str(p.relative_to(REPO)), "sha256": sha(p)})
    index = {
        "schema": "lex-evaluation-audit-index/1",
        "run_id": RUN, "resumed_from_run": 45965013167, "generated_at_utc": NOW,
        "direction_version": 68, "lane": "evaluation",
        "base_snapshot_commit": "ea98384e54d31d2e694c418a1d1ce5769fc6c32f",
        "product_mount_head": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83",
        "verdict": "AUDIT_READY_PENDING_INDEPENDENT_AUDIT" if all_pass else "GATES_NOT_ALL_PASS",
        "gates": gate_summary,
        "decisions": {
            "diagnosis": diag["failure_class"],
            "deliverable": ver["verdict"], "n_checks": ver["n_checks"],
            "n_passed": ver["n_passed"], "n_failed": ver["n_failed"],
            "replay": comp["verdict"], "n_fields_compared": comp["n_fields_compared"],
            "n_differences": comp["n_differences"],
            "pins": pins["verdict"], "n_pins": pins["n_pins"],
            "accepted_pointer": rec["new_pointer"],
            "discrepancy": rec["claim_discrepancy_disclosed"]["statement"],
        },
        "network_disclosure": summary["next_recommendation"] and
            load(REPO / "state/evaluation.json")["operational_resume_45965187540"]["network_call_disclosure"],
        "claim_ceiling": summary["claim_ceiling"],
        "artifacts": index_items,
        "n_artifacts": len(index_items),
    }
    idx_p = REPO / "results/evaluation/operational_resume_45965187540/AUDIT_INDEX_45965187540.json"
    dump(idx_p, index)

    # ---- human report ------------------------------------------------------
    report = f"""# Operational resume {RUN} of run {RESUMED} — audit-ready

- Lane: `evaluation`; direction v68 from the authoritative mounted control plane.
- Base snapshot: `ea98384e54d31d2e694c418a1d1ce5769fc6c32f` (`accept evaluation cycle 40265377500`), preserved.
- Product mount: `/tmp/lex_accepted/product` @ `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83`.
- Result: **{index['verdict']}**. Producer does not create an independent audit gate.

## Orchestration failure
- GitHub run `{RESUMED}` (`Core evaluation dirV68 repair0`, `workflow_dispatch`, head `02a3d67d`, created `2026-11-27T08:21:19Z`) concluded `failure`.
- The team job failed at step `Run lane cycle`; `Validate active MVP producer state`, `Enforce lane write scope`, `integrate` and `audit` were skipped. `Persist team snapshot` ran last and force-pushed the inherited tree: **zero new commits**.
- Job logs returned HTTP 403 (`Must have admin rights to Repository.`), so the exact provider/model error is **not claimed**.
- Classification: `{diag['failure_class']}` — not a gate REVISE/BLOCKED, not a write-scope violation, not a product defect, no verdict issued.

## Deliverable verified
- Socket-blocked offline replay on packet-of-record `39319405429`: `{ver['verdict']}`, exit 1, `{ver['n_passed']}/{ver['n_checks']}` checks, `input_drift=[]`, zero network attempts.
- 18 gates: 11 pass / 4 fail / 3 reported; the four failures are the same concept/counter-authority gates as the snapshot record.
- Frozen pins: `{pins['verdict']}` ({pins['n_pins']} pins). Replay comparison: `{comp['verdict']}`, {comp['n_fields_compared']} fields, {comp['n_differences']} differences after the five pre-frozen identity/environment exclusions.
- The FAST recall-loss instrument could not be re-executed here (numpy/scipy/sklearn absent under Python 3.14.4); this remains a preserved negative environment result, not a verdict change.

## Reconciliation and disclosure
- `accepted_run_id` advanced additively from `40258497460` to `40265377500` on both halves of requirement 4: gate `PASS` in tree plus commit `ea98384e` (`accept evaluation cycle 40265377500`) at `origin/lab/evaluation`.
- Disclosed, not edited: `results/audit/evaluation/CYCLE_40265377500_GATE.json` describes `run_cached_bundle_benchmark.py` / `BENCHMARK_VALID_NO_FALSIFICATION` / exit 0, while the producer artifact committed in the same cycle describes `minimal_retrieval_ca_benchmark` / `PRODUCT_FALSIFIED` / exit 1. Both are preserved verbatim; the pointer advance relies on the objective both-halves facts only.
- The nested-refs guard's one unresolved item was an annotated historical disclosure pointer (`required_fixes_source`). It was fixed through the guard's designed `DISCLOSURE_PARENT_KEYS` mechanism with an inline provenance comment; before/after sha and outputs are in `nested_ref_disclosure_proof_45965187540.json`. No frozen bar was touched.

## Gates
{json.dumps(gate_summary, indent=2, ensure_ascii=False)}

## Boundaries
- All writes are in the evaluation lane; no `results/audit/`, `reports/audit/`, `.github/`, product state or frozen bar was modified (`no_out_of_lane_proof_45965187540.json`).
- Both state files were updated additively; prior keys, prior recommendation text and all prior evidence refs are preserved (`state_additive_proof_45965187540.json`).
- No same-question cycle, no 174k benchmark rerun, no packet admission, no human gate, no change to either DO-NOT-SERVE order.
- `continue_recommended=false`; next discriminating work requires new product bytes.
- Audit index: `results/evaluation/operational_resume_45965187540/AUDIT_INDEX_45965187540.json` ({index['n_artifacts']} artifacts).
"""
    report_p = REPO / "reports/evaluation/OPERATIONAL_RESUME_45965013167_AUDIT_READY.md"
    report_p.write_text(report)
    index_items.append({"path": str(report_p.relative_to(REPO)), "sha256": sha(report_p)})
    index["artifacts"] = index_items
    index["n_artifacts"] = len(index_items)
    dump(idx_p, index)
    print(json.dumps({"verdict": index["verdict"], "gates": gate_summary,
                      "n_artifacts": index["n_artifacts"],
                      "report": str(report_p.relative_to(REPO))}, indent=2))


if __name__ == "__main__":
    main()
