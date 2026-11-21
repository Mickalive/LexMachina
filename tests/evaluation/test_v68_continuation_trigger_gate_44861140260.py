"""Freeze-integrity and result-guard tests for the v68 continuation trigger
gate (run 44861140260).

The gate is an OPERATIONAL instrument: it publishes byte-identity and
set-relation facts only, so these tests pin the freeze-first ordering, the
frozen input digests, the trigger definitions, an INDEPENDENT recomputation of
trigger A, the verdict/exit-code contract and the fail-closed posture flags.
They never assert a product-quality number, because the gate measures none.

They use only plain asserts and pytest.mark.skipif so the lane's
evaluation/no_pytest_runner shim can execute them when pytest is absent.

SHIM ASSERTION REPAIR (run 44864973813, disclosed not silent): on its first
no-pytest execution in run 44861140260, test_exit_code_contract_is_frozen_and_outcome_free
asserted the literal substring "NOT a job failure", which does not occur in the
frozen hypothesis exit_code_contract["0"] (sha 85c7201d...). The frozen artifact
is CORRECT and is NOT edited: its text is "...never in the exit code, so no
workflow can read a fired trigger as a job failure". This test-only assertion was
re-pointed at that real frozen wording so it checks the same invariant without
touching any frozen input, bar or verdict. The original test bytes are preserved
byte-for-byte under
results/evaluation/operational_resume_44864973813/pre_repair/.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
MOUNT = Path("/tmp/lex_accepted/product")
RUN = "44861140260"
HYPO = REPO_ROOT / f"evaluation/V68_CONTINUATION_TRIGGER_GATE_{RUN}_HYPOTHESIS_V1.json"
FREEZE = REPO_ROOT / f"evaluation/V68_CONTINUATION_TRIGGER_GATE_{RUN}_FREEZE_V1.json"
GATE_RESULT = REPO_ROOT / f"results/evaluation/v68_continuation_trigger_gate/{RUN}.json"
CA_HYPO = REPO_ROOT / f"evaluation/POST_REPAIR_FAMILY_CA_FALSIFIER_{RUN}_HYPOTHESIS_V1.json"
BASELINE_HEAD = "5fb312e4a71c99dce0ed6fbd2d3fce9a88ad6e68"
CURRENT_HEAD = "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83"

MOUNT_REQUIRED = pytest.mark.skipif(not MOUNT.is_dir(),
                                    reason="accepted product mount absent")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha256(commit: str, path: str) -> str | None:
    p = subprocess.run(["git", "cat-file", "blob", f"{commit}:{path}"],
                       cwd=str(REPO_ROOT), capture_output=True, timeout=120)
    if p.returncode != 0:
        return None
    return hashlib.sha256(p.stdout).hexdigest()


def _git_paths(commit: str, prefix: str) -> list[str]:
    p = subprocess.run(["git", "ls-tree", "-r", "--name-only", commit, "--",
                        prefix], cwd=str(REPO_ROOT), capture_output=True,
                       text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    return [ln for ln in p.stdout.splitlines() if ln]


# --------------------------------------------------------------- freeze ----
def test_freeze_first_hypothesis_and_freeze_are_consistent():
    hyp, freeze = _load(HYPO), _load(FREEZE)
    assert _sha(HYPO) == freeze["hypothesis_sha256_at_freeze"]
    assert hyp["run_id"] == RUN
    assert freeze["run_id"] == RUN
    assert hyp["direction_version"] == freeze["direction_version"] == 68
    # the gate's trigger B pins the claim-bearing hypothesis of the SAME cycle;
    # that cross-pin must still hold so the two instruments cannot diverge
    assert _sha(CA_HYPO) == \
        hyp["triggers_FROZEN"]["trigger_B_full_family_regenerated"][
            "ca_hypothesis_sha256_at_freeze"]


def test_frozen_input_pins_match_live_bytes():
    hyp = _load(HYPO)
    for rel, expected in hyp["frozen_inputs_REPORTED_ONLY"].items():
        path = (MOUNT / rel[6:]) if rel.startswith("mount:") else (REPO_ROOT / rel)
        assert path.is_file(), rel
        assert _sha(path) == expected, rel


def test_exit_code_contract_is_frozen_and_outcome_free():
    hyp = _load(HYPO)
    assert set(hyp["exit_code_contract"]) == {"0", "2"}
    # a trigger status must never be carried by the exit code. The frozen text
    # (sha 85c7201d...) says "never in the exit code, so no workflow can read a
    # fired trigger as a job failure"; assert that real invariant, not a phrase
    # the frozen artifact never contained (authoring defect repaired 44864973813).
    contract0 = hyp["exit_code_contract"]["0"]
    assert "never in the exit code" in contract0
    assert "no workflow can read a fired trigger as a job failure" in contract0
    for key in ("claim_ceiling", "next_step_map_FROZEN", "triggers_FROZEN"):
        assert key in hyp
    assert set(hyp["next_step_map_FROZEN"]) == {
        "TRIGGER_A_FIRED_RETRIEVAL_CODE_CHANGED",
        "TRIGGER_B_FIRED_FAMILY_REGENERATED",
        "TRIGGERS_A_AND_B_FIRED",
        "NO_TRIGGER_FIRED_NOT_DISCRIMINATING"}


def test_no_frozen_bar_rubric_or_verdict_contract_edited():
    assert _sha(REPO_ROOT / "evaluation/frozen_bars/RULES_LABEL.json") == \
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
    assert _sha(REPO_ROOT / "evaluation/frozen_bars/RULES_GEOMETRY.json") == \
        "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"
    assert _sha(REPO_ROOT / "evaluation/frozen_bars/VERDICT_CONTRACT.json") == \
        "b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c"


# ------------------------------------------------------------ trigger A ----
def test_trigger_a_independently_recomputed_product_query_is_byte_identical():
    """Recompute trigger A from git instead of trusting the published record."""
    hyp = _load(HYPO)
    spec = hyp["triggers_FROZEN"]["trigger_A_retrieval_reranking_code_changed"]
    assert spec["baseline_head"] == BASELINE_HEAD
    assert spec["expected_current_head"] == CURRENT_HEAD

    base = _git_paths(BASELINE_HEAD, "product/query/")
    cur = _git_paths(CURRENT_HEAD, "product/query/")
    assert len(base) == len(cur) == 35
    assert set(base) == set(cur)
    changed = [p for p in base
               if _git_blob_sha256(BASELINE_HEAD, p) != _git_blob_sha256(CURRENT_HEAD, p)]
    assert changed == [], changed


@MOUNT_REQUIRED
def test_trigger_a_record_agrees_with_independent_recomputation():
    rec = _load(GATE_RESULT)
    a = rec["trigger_A"]
    assert a["fired"] is False
    assert a["baseline_head"] == BASELINE_HEAD
    assert a["current_head"] == CURRENT_HEAD
    rel = a["set_relations_REQUIREMENT_16"]
    assert rel["added_n"] == rel["removed_n"] == rel["modified_n"] == 0
    assert rel["identical_n"] == rel["baseline_n"] == rel["current_n"] == 35
    assert a["mount_matches_current_head"] == {"holds": True, "mismatches": [],
                                              "n_files_checked": 35}


# ------------------------------------------------------------ trigger B ----
@MOUNT_REQUIRED
def test_trigger_b_reuses_accepted_precondition_gate_and_stays_14_of_15():
    from evaluation import post_repair_family_ca_falsifier as PRF
    hyp, rec = _load(HYPO), _load(GATE_RESULT)
    b = rec["trigger_B"]
    assert b["ca_hypothesis_pin_ok"] is True
    assert b["ca_hypothesis_sha256_actual"] == \
        b["ca_hypothesis_sha256_at_freeze"] == _sha(CA_HYPO)

    # the gate must be a thin wrapper, not a second implementation
    gate = PRF.precondition_gate(_load(CA_HYPO), MOUNT)
    assert b["member_for_member_matching"] == \
        gate["set_relations_REQUIREMENT_16"]["member_for_member_matching"]
    assert b["fired"] == gate["H2_precondition_full_family_regenerated"] is False
    assert b["leg_landed"] == gate["H1_precondition_leg_landed"] is True
    assert b["member_for_member_matching"]["matched_members"] == 14
    assert b["member_for_member_matching"]["of"] == 15


# --------------------------------------------------------------- result ----
def test_result_record_reports_no_trigger_and_exit_zero():
    rec = _load(GATE_RESULT)
    assert rec["verdict"] == "NO_TRIGGER_FIRED_NOT_DISCRIMINATING"
    assert rec["exit_code"] == 0
    assert rec["trigger_A"]["fired"] is False
    assert rec["trigger_B"]["fired"] is False
    assert rec["hypothesis"]["sha256"] == _sha(HYPO)
    assert rec["freeze_record"]["sha256"] == _sha(FREEZE)
    assert rec["vacuous_reasons"] == []
    assert rec["frozen_inputs"]["all_match"] is True


def test_result_ordered_work_status_matches_direction_v68():
    rec = _load(GATE_RESULT)
    st = rec["ordered_work_status"]
    assert st["item_1_correction_of_record"].startswith("DISCHARGED")
    assert st["item_2_conditional_remeasure"].startswith("NOT_YET_DISCRIMINATING")
    assert st["item_2_leg_half"] == "LANDED"
    assert "UNCHANGED" in st["item_3_standing_falsification_record"]
    assert "no" in st["item_5_no_re_derivation"]
    assert rec["trigger_B"]["item_2_full_protocol_status"].startswith(
        "NOT_YET_DISCRIMINATING")


def test_claim_ceiling_and_posture_stay_fail_closed():
    rec = _load(GATE_RESULT)
    for flag in ("packet_admitted", "machine_gate_ready", "human_gate_ready",
                 "ready_for_owner_session", "owner_decision_required"):
        assert rec[flag] is False, flag
    assert rec["network_calls"] == 0
    assert rec["no_174k_benchmark_rerun"] is True
    assert "NO_TRIGGER_FIRED verdict is NOT a pass" in rec["claim_ceiling"]


def test_report_writes_a_new_record_and_never_a_bar():
    rec = _load(GATE_RESULT)
    assert rec["schema"] == "lex-evaluation-v68-continuation-trigger-gate/1"
    assert rec["lane"] == "evaluation"
    assert rec["run_id"] == RUN
    # the gate publishes no verdict vocabulary of its own
    assert "verdict_vocabulary" not in rec
    assert "defect_histogram" not in rec
    assert "falsification_proven" not in rec
