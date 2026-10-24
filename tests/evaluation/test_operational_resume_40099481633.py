"""Round-1 repair invariants for rejected evaluation cycle 40099481633.

Audit ``results/audit/evaluation/CYCLE_40099481633_GATE.json`` (gate REVISE)
required four fixes; this file pins each one as an executable invariant so the
same zero-delta defect cannot silently return:

F1  the run-40099481633 diagnosis set exists, references the run, and records
    the delta-guard bypass (inherited head 0b4963a0 adopted with a clean
    worktree) plus the current v67 work posture;
F2  the comparison contract was frozen BEFORE the re-execution, the inherited
    item-(1) deliverable is byte-stable (sha256 f5fade6d...), the frozen
    instrument is byte-identical (aac86527...), the 19-item reproduction
    verdict is REPRODUCES with 0 mismatches, and the canonical state advanced
    its run identity with disclosure while keeping accepted_run_id;
F3  the previously stale identity pin is repaired WITHOUT deleting history and
    a fresh real-pytest (9.1.1) living-suite record exists at the repaired head;
F4  nothing frozen moved: rubric/threshold/verdict-contract digests, the
    accepted baseline 40062917685 bytes, the fail-closed posture flags, both
    DO-NOT-SERVE orders and the no-product-code/no-174k scope all hold.

NON-WEAKENING CONTRACT: this file adds no threshold, metric or success rule; it
asserts only previously frozen digests, the audit's own required-fixes list and
the lane's standing fail-closed posture.  It scores no frozen bar, re-runs no
serve verdict and makes no product or legal-usefulness claim.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

RUN = "40099481633"
REPAIR_RUN = "40101127061"
DELIV = "40089391202"

STATE = json.loads((_REPO_ROOT / "state/evaluation.json").read_text(encoding="utf-8"))


def _load(rel: str) -> dict:
    return json.loads((_REPO_ROOT / rel).read_text(encoding="utf-8"))


def _sha256(rel: str) -> str:
    return hashlib.sha256((_REPO_ROOT / rel).read_bytes()).hexdigest()


# ====================================================================== F1
def test_f1_rest_jobs_snapshot_references_the_rejected_run():
    snap = _load(f"results/evaluation/orchestration/{RUN}_rest_jobs.json")
    assert snap["schema"] == "lex-evaluation-orchestration-rest-snapshot/1"
    assert str(snap["run"]["id"]) == RUN
    assert snap["run"]["conclusion"] == "success"
    jobs = {j["name"]: j["conclusion"] for j in snap["jobs"]}
    assert jobs == {"team": "success", "audit": "success",
                    "integrate": "success", "resilience": "success"}
    assert snap["fetched_by_run"] == REPAIR_RUN


def test_f1_diagnosis_records_delta_guard_bypass_and_zero_delta():
    d = _load(f"results/evaluation/orchestration/{RUN}_failure_chain_diagnosis.json")
    assert d["run_id"] == RUN and d["diagnosing_run"] == REPAIR_RUN
    z = d["zero_durable_delta_diagnosis"]
    assert z["verdict"] == "ZERO_DURABLE_DELTA_UNDER_SUCCESS"
    assert "0b4963a0" in z["explanation"] and "f2734734" in z["explanation"]
    assert "run-ox-with-retry.sh" in z["explanation"]  # mechanism cited, not edited
    assert z["artifacts_referencing_run_before_repair"] == 0
    assert z["state_before_this_repair"]["github_run"] == "40096174340"
    # current v67 work posture recorded in the same artifact
    p = d["v67_work_posture_this_run"]
    assert "DISCHARGED-AND-INHERITED" in p["item_1_d2_letterhead_pattern_profile"]
    assert "NOT_YET_DISCRIMINATING" in p["item_2_conditional_remeasure"]
    assert "offline_slice.py:79" in p["item_2_conditional_remeasure"]
    assert "pipeline.py:1339" in p["item_2_conditional_remeasure"]
    assert "not re-run" in p["item_3_standing_falsification_record"]
    post = d["posture_unchanged"]
    assert post["both_do_not_serve_orders_stand"] is True
    assert post["no_frozen_bar_rubric_threshold_verdict_contract_edit"] is True
    assert post["no_obsolete_universal_174k_benchmark_rerun"] is True
    assert post["no_product_code_modified"] is True


# ====================================================================== F2
def test_f2_freeze_committed_before_reexecution_and_pins_inventory():
    frz = _load(f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json")
    hyp = _load(f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json")
    assert frz["run_id"] == RUN and frz["repair_run_id"] == REPAIR_RUN
    assert frz["repair_round"] == 1
    assert frz["n_fields"] == 19
    assert frz["hypothesis_sha256"] == _sha256(
        f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json")
    assert frz["hypothesis_record"] == (
        f"evaluation/OPERATIONAL_RESUME_{RUN}_HYPOTHESIS_V1.json")
    assert hyp["decision_rule_frozen_before_execution"]["REPRODUCES"]
    # freeze-first ordering proven at commit level: the freeze commit precedes
    # the commit that added the re-execution artifact
    import subprocess
    freeze_commit = subprocess.run(
        ["git", "log", "--format=%H", "--diff-filter=A", "--",
         f"evaluation/OPERATIONAL_RESUME_{RUN}_FREEZE_V1.json"],
        cwd=_REPO_ROOT, capture_output=True, text=True, timeout=30
    ).stdout.split()[0]
    reexec_commits = subprocess.run(
        ["git", "log", "--format=%H", "--diff-filter=A", "--",
         f"results/evaluation/d2_letterhead_pattern_profile/{RUN}.json"],
        cwd=_REPO_ROOT, capture_output=True, text=True, timeout=30
    ).stdout.split()
    assert reexec_commits, "re-execution artifact not committed"
    order = subprocess.run(
        ["git", "rev-list", "--reverse", f"{freeze_commit}~1..HEAD"],
        cwd=_REPO_ROOT, capture_output=True, text=True, timeout=30
    ).stdout.split()
    assert order.index(freeze_commit) < order.index(reexec_commits[0]), (
        "freeze record must be an ancestor order-before the re-execution")


def test_f2_deliverable_untouched_instrument_byte_identical():
    assert _sha256(
        f"results/evaluation/d2_letterhead_pattern_profile/{DELIV}.json"
    ) == "f5fade6d11ebf14e3004d5beebf2f959444720fc3152e4e5b0b479a644d3cab7"
    assert _sha256(
        "evaluation/counter_evidence_quality_benchmark.py"
    ) == "aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d"
    repro = _load(
        f"results/evaluation/d2_letterhead_pattern_profile/"
        f"{RUN}_reproduction_check_vs_{DELIV}.json")
    assert repro["run_id"] == RUN
    assert repro["repair_run_id"] == REPAIR_RUN  # execution provenance disclosed
    assert repro["verdict"] == "REPRODUCES"
    assert repro["n_discrimination_fields_compared"] == 19
    assert repro["n_mismatches"] == 0
    assert repro["controls_all_pass"] is True
    assert repro["file_byte_identity_claimed"] is False  # requirement 30
    assert repro["deliverable_untouched"] is True
    reexec = _load(f"results/evaluation/d2_letterhead_pattern_profile/{RUN}.json")
    assert reexec["run_id"] == RUN
    assert reexec["controls_all_pass"] is True
    assert reexec["n_bundles"] == 93


def test_f2_state_advanced_with_disclosure_and_accepted_run_kept():
    st = STATE
    assert str(st["github_run"]) == REPAIR_RUN, (
        "github_run must name the repair run that made the claim")
    adv = st["github_run_advance"]
    assert adv["from"] == "40096174340" and adv["to"] == REPAIR_RUN
    assert adv["repair_of_run"] == RUN and adv["repair_round"] == 1
    assert st["accepted_run_id"] == "40084716045"  # kept until both-halves promo
    blk = st.get(f"repair_round1_{RUN}") or {}
    assert blk.get("required_fixes") == ["F1", "F2", "F3", "F4"]
    assert blk.get("repaired_by_run") == REPAIR_RUN
    assert blk["fixes_discharged"]["F2"]["reproduction_verdict"] == "REPRODUCES"
    assert blk["fixes_discharged"]["F2"]["freeze_first"] is True
    assert blk["fixes_discharged"]["F2"]["waiver"] is None
    assert blk["fixes_discharged"]["F1"]["verdict"] == "DISCHARGED"
    assert blk["fixes_discharged"]["F3"]["verdict"] == "DISCHARGED"
    assert blk["fixes_discharged"]["F4"]["verdict"].startswith("DISCHARGED")
    # required-fixes text preserved verbatim from the audit gate of record
    assert any(s.startswith("F1 durable delta") for s in
               blk["required_fixes_verbatim"])
    assert any("zero-delta round-1 repair is invalid" in s for s in
               blk["required_fixes_verbatim"])


# ====================================================================== F3
def test_f3_stale_identity_pin_repaired_without_deleting_history():
    src = (_REPO_ROOT / "tests/evaluation/test_operational_resume_40094203248.py"
           ).read_text(encoding="utf-8")
    # the stale literal pin is gone ...
    assert 'assert STATE["github_run"] == "40094203248"' not in src
    assert 'assert STATE["operational_resume_of"] == "40089391202"' not in src
    # ... history is NOT deleted: the historical run ids stay asserted
    assert '"40094203248" in history_ids' in src
    assert '"40089391202" in history_ids' in src
    # the identity chain in state contains every lineage run id
    ids = {str(h.get("run_id")) for h in STATE.get("run_identity_history", [])}
    for run in ("40089391202", "40094203248", "40096174340", RUN, REPAIR_RUN):
        assert run in ids, run
    # the repaired test file itself still passes the posture pins
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session", "owner_decision_required"):
        assert STATE[flag] is False, flag


def test_f3_fresh_real_pytest_living_suite_record_at_repaired_head():
    rec = _load(f"results/evaluation/orchestration/{REPAIR_RUN}_pytest_shim.json")
    assert rec["pytest_version"] == "9.1.1"
    assert rec["failed"] == 0 and rec["skipped"] >= 0
    assert rec["passed"] >= 34
    assert rec["run_id"] == REPAIR_RUN
    assert rec["repairs_run_id"] == RUN
    assert (_REPO_ROOT / rec["junit_xml"]).exists()
    inv = _load(
        f"results/evaluation/orchestration/{REPAIR_RUN}_pytest_repair_invariants.json")
    assert inv["pytest_version"] == "9.1.1" and inv["failed"] == 0
    ml = _load(
        f"results/evaluation/orchestration/{REPAIR_RUN}_multiling_prov_pytest.json")
    assert ml["pytest_version"] == "9.1.1" and ml["failed"] == 0


# ====================================================================== F4
def test_f4_no_frozen_contract_edit_baseline_unmoved():
    assert _sha256("evaluation/frozen_bars/RULES_LABEL.json") == (
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608")
    assert _sha256("evaluation/frozen_bars/RULES_GEOMETRY.json") == (
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633")
    assert _sha256("evaluation/frozen_bars/VERDICT_CONTRACT.json") == (
        "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c")
    assert _sha256(
        "results/evaluation/counter_evidence_quality_benchmark/40062917685.json"
    ) == "948a8929817f265236c87bbc1b3a17559fa7db2bd03ee4ccddc36332977ac717"


def test_f4_posture_fail_closed_and_orders_stand():
    for flag in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                 "ready_for_owner_session", "owner_decision_required"):
        assert STATE[flag] is False, flag
    blk = STATE[f"repair_round1_{RUN}"]["fixes_discharged"]["F4"]
    assert blk["both_do_not_serve_orders_stand"] is True
    assert blk["no_obsolete_universal_174k_benchmark_rerun"] is True
    assert blk["no_product_code_modified"] is True
    assert blk["baseline_unmoved"] is True
    # ceiling: this repair claims no product/serve/usefulness outcome
    ceil = STATE[f"repair_round1_{RUN}"]["claim_ceiling"]
    assert "no frozen bar" in ceil and "Both DO-NOT-SERVE orders stand" in ceil


def test_v67_item2_still_not_yet_discriminating_reverified():
    blk = STATE[f"repair_round1_{RUN}"]
    assert blk["v67_item_2_status"]["status"] == "NOT_YET_DISCRIMINATING"
    assert blk["v67_item_2_status"]["product_head"].startswith("e2270c37")
    assert STATE["next_recommendation"].startswith("NOT_YET_DISCRIMINATING")
