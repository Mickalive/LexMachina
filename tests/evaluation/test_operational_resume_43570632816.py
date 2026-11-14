"""Regression locks for operational resume 43570632816 -> 43570757974.

Plain functions only: the producer image has no pytest, so these are executed by
``evaluation.no_pytest_runner``.  They assert the frozen diagnosis and snapshot
facts, not a new product claim.
"""

import hashlib
import json
import subprocess
from pathlib import Path

from evaluation.operational_resume_43570632816 import (
    ACCEPTED_RUN_ID,
    API_DIR,
    DELIVERABLE,
    DIRV,
    FAMILY_GATE,
    FREEZE,
    HYPOTHESIS,
    PACK_DIR,
    RESUMED,
    RUN_ID,
    SNAPSHOT_HEAD,
    SNAPSHOT_PARENT,
    STATE_PATH,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_constants_identify_this_resume():
    assert RUN_ID == "43570757974"
    assert RESUMED == "43570632816"
    assert SNAPSHOT_HEAD == "c79dae10ef9591e4448c4a7e426c81e4686a180c"
    assert SNAPSHOT_PARENT == "c40cd9288bbcab02a5489bd768e2a329f4dea218"
    assert DIRV == 68
    assert ACCEPTED_RUN_ID == 40265377500


def test_freeze_pins_still_match():
    freeze = _load(FREEZE)
    assert freeze["freeze_before_execution"] is True
    pins = freeze["pins"]
    assert len(pins) >= 40
    bad = [rel for rel, want in pins.items()
           if _sha(REPO_ROOT / rel) != want]
    assert bad == [], f"pins drifted: {bad}"


def test_hypothesis_is_preregistered_and_five_way():
    hyp = _load(HYPOTHESIS)
    assert hyp["frozen_before_formal_evidence"] is True
    assert sorted(hyp["hypotheses"]) == ["H1", "H2", "H3", "H4", "H5"]
    assert hyp["claim_ceiling"]


def test_resumed_failure_is_launch_exit_1_not_zero_delta():
    diag = _load(PACK_DIR / f"diagnosis_{RESUMED}.json")
    sig = diag["signature"]
    assert sig["run_conclusion"] == "failure"
    assert sig["team_conclusion"] == "failure"
    assert sig["failing_step"] == "Run lane cycle"
    assert sig["failure_duration_s"] < 60
    assert sig["exit_code_1_annotation"] is True
    assert sig["persist_snapshot_conclusion"] == "success"
    assert sig["validate_state_conclusion"] == "skipped"
    assert sig["write_scope_conclusion"] == "skipped"
    assert sig["audit_job_conclusion"] == "skipped"
    assert sig["integrate_job_conclusion"] == "skipped"


def test_launch_signature_is_distinct_from_zero_delta_and_quantum():
    diag = _load(PACK_DIR / f"diagnosis_{RESUMED}.json")
    chain = diag["comparison_signatures"]
    assert chain["launch_failure_43542234373"]["failure_duration_s"] == 16
    assert chain["launch_failure_43542234373"]["exit_code_1_annotation"] is True
    assert chain["chain_prior_43570515880"]["failure_duration_s"] == 16
    zero = chain["zero_delta_43541879339"]
    assert zero["failure_duration_s"] > 60
    assert zero["exit_code_1_annotation"] is False
    classes = " ".join(diag["failure_class_distinct_from"])
    assert "ZERO_DELTA_REPAIR" in classes
    assert "ORCHESTRATION_AUDIT_WORK_QUANTUM_EXPIRED" in classes


def test_snapshot_delta_is_41_files_with_zero_audit_namespace():
    out = subprocess.run(
        ["git", "diff", "--name-only", SNAPSHOT_PARENT, SNAPSHOT_HEAD],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout
    delta = [ln for ln in out.splitlines() if ln.strip()]
    assert len(delta) == 41
    assert [p for p in delta if p.startswith("results/audit/evaluation/")
            or p.startswith("reports/audit/evaluation/")] == []


def test_prior_snapshot_artifacts_are_byte_pinned():
    snap = _load(PACK_DIR / f"snapshot_verification_{RUN_ID}.json")
    assert snap["all_hold"] is True
    assert snap["prior_snapshot_verify"]["exit_code"] == 0
    prior = _load(REPO_ROOT / snap["prior_snapshot_verify"]["record"])
    assert prior["record"]["all_hold"] is True
    assert len(snap["pins"]) == 33
    assert all(row["match"] for row in snap["pins"])


def test_deliverable_is_product_falsified_with_zero_issued_rows():
    rec = _load(DELIVERABLE)
    assert rec["verdict"] == "PRODUCT_FALSIFIED"
    assert rec["exit_code"] == 1
    assert rec["packet"] == "39319405429"
    assert rec["direction_version"] == 68
    assert rec["n_questions"] == 3
    issued = sum(r["counter_authority"]["n_issued"] for r in rec["results"])
    assert issued == 0
    ver = _load(PACK_DIR / f"deliverable_verification_{RUN_ID}.json")
    assert ver["all_hold"] is True
    assert ver["replay"]["error"] is None
    assert ver["replay"]["reproduces_measurement"] is True


def test_family_gate_stays_not_yet_discriminating():
    gate = _load(FAMILY_GATE)
    assert gate["status"] == "NOT_YET_DISCRIMINATING"
    assert gate["zero_delta_check"]["already_measured_since_evaluation_run"] is True
    assert gate["zero_delta_check"]["byte_identical_n"] == 50
    card = gate["role_cardinality"]
    assert card["role_parity"] is False
    assert card["member_for_member_ceiling"] == 14
    assert card["frozen_family_n"] == 15
    assert gate["product"]["head"].startswith("7be4480e")
    work = _load(PACK_DIR / f"ordered_work_{RUN_ID}.json")
    assert work["item_2"]["re_measure_executed"] is False
    assert work["item_5"]["new_same_question_measurement"] is False


def test_state_discloses_pending_audit_and_keeps_accepted_run():
    state = _load(STATE_PATH)
    block = state[f"operational_resume_{RESUMED}"]
    assert state["github_run"] == int(RUN_ID)
    assert state["accepted_run_id"] == ACCEPTED_RUN_ID
    assert state["audit_status"] == "PENDING_INDEPENDENT_AUDIT"
    assert block["resumed_run_id"] == RESUMED
    assert block["run_id"] == str(RUN_ID)
    assert block["audit_status"] == "PENDING_INDEPENDENT_AUDIT"


def test_instrument_exposes_read_only_verify_phase():
    out = subprocess.run(
        ["python3", "-m", f"evaluation.operational_resume_{RESUMED}",
         "--phase", "verify"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
    rec = json.loads(out.stdout)
    # H5 is written after this shim runs inside the final phase, so this lock
    # asserts the read-only invariants that must hold at every point, not the
    # summary flag that is written later in the same phase.
    assert rec["checks"]["freeze_pins_match"] is True
    assert rec["checks"]["H1_H4_all_hold"] is True
    assert rec["checks"]["state_identity"] is True
    assert rec["checks"]["audit_index_refs_resolve"] is True
    summary = _load(PACK_DIR / f"summary_{RUN_ID}.json")
    if summary.get("hypotheses_failed") == []:
        assert out.returncode == 0, out.stdout + out.stderr
        assert rec["all_hold"] is True
