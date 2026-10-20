"""Regression tests pinning the repair round 1 of rejected cycle 39338699604.

Independent audit CYCLE_39338699604 returned gate=REVISE with required_fixes
R1-R4. These tests pin that every fix is discharged and that the repaired
provenance fields are internally consistent, so the same defect class cannot
silently return.

R1  check-18 disclosure fully re-derived (newest_accept_commit, 34-gate list,
    superseded_snapshot_39338699604, truthful action_taken).
R2  previous_record digest provenance (canonical vs raw, rule documented).
R3  embedded timestamps no longer post-date their commits; originals preserved.
R4  lane-state accepted-run pointer advanced; prior promotion text preserved.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COVERAGE = ROOT / "results/evaluation/accepted_base_gate_coverage_39043684319.json"
HYP = ROOT / "evaluation/PACKET_OF_RECORD_STAND_READY_HYPOTHESIS_V1.json"
FREEZE = ROOT / "evaluation/PACKET_OF_RECORD_STAND_READY_FREEZE_RECORD.json"
RES = ROOT / "results/evaluation/packet_of_record_stand_ready/39338699604.json"
STATE = ROOT / "state/evaluation.json"

ACCEPTED_HEAD = "3506f0e4b095e14060bc7ed607ee302feb9f88a1"
NEWEST_SHA = "3506f0e4"
NEWEST_SUBJECT = "accept evaluation cycle 39334865522"
N_GATES = 34
GATE_39334865522 = "results/audit/evaluation/CYCLE_39334865522_GATE.json"
PRIOR_RAW_SHA = "9354331f2d7b913ca0a48cc933c285f818c00094f8c51a50825ec1a4eb5631be"
PRIOR_CANON_SHA = "4cb0ac187eb4f7985d8226d036e7128545c791d4a1d2181e25b3c13038b2c771"
BCE_TIME = "2026-10-19T23:16:14Z"   # commit time of bce774b7 (freeze commit)
C6B_TIME = "2026-10-19T23:31:36Z"   # commit time of c6b4d479 (result commit)
COMMIT_5A6 = "2026-10-19T23:39:02Z"  # commit time of 5a6aa4d9 (report/state closure)


def _load(p: Path) -> dict:
    assert p.exists(), f"missing {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


# ===================================================================== R1
def test_r1_newest_accept_commit_is_3506f0e4_not_d7b8301e():
    cov = _load(COVERAGE)
    na = cov["newest_accept_commit"]
    assert na["sha"] == NEWEST_SHA
    assert na["subject"] == NEWEST_SUBJECT
    # the stale value that the audit caught must be gone from the live field
    assert na["sha"] != "d7b8301e"


def test_r1_gate_list_is_34_and_includes_39334865522():
    cov = _load(COVERAGE)
    gates = cov["gates_present_on_accepted_branch"]
    assert len(gates) == N_GATES
    assert GATE_39334865522 in gates
    # the pre-repair 26-entry list must not silently reappear
    assert len(gates) != 26


def test_r1_gate_list_matches_git_at_accepted_head():
    cov = _load(COVERAGE)
    tree = _git("ls-tree", "-r", "--name-only", ACCEPTED_HEAD, "--",
                "results/audit/evaluation")
    derived = sorted(l for l in tree.splitlines() if "_GATE.json" in l)
    assert cov["gates_present_on_accepted_branch"] == derived


def test_r1_superseded_snapshot_39338699604_exists_and_preserves_prior_full_measurement():
    cov = _load(COVERAGE)
    snap = cov.get("superseded_snapshot_39338699604")
    assert snap is not None, "audit R1 required this block"
    # the prior full measurement: head d7b8301e, newest d7b8301e, 26 gates
    assert snap["accepted_branch_head"].startswith("d7b8301e")
    assert snap["newest_accept_commit"]["sha"] == "d7b8301e"
    assert len(snap["gates_present_on_accepted_branch"]) == 26
    assert snap["republished_by"] == "39200567493"
    assert snap["preserved_verbatim"] is True


def test_r1_partial_intermediate_state_also_preserved():
    cov = _load(COVERAGE)
    snap = cov.get("superseded_snapshot_39338699604_partial")
    assert snap is not None
    # the partial refresh had head 3506f0e4 but stale newest/gates
    assert snap["accepted_branch_head"] == ACCEPTED_HEAD
    assert snap["newest_accept_commit"]["sha"] == "d7b8301e"
    assert len(snap["gates_present_on_accepted_branch"]) == 26


def test_r1_action_taken_is_truthful_about_what_was_re_derived():
    cov = _load(COVERAGE)
    at = cov["action_taken"]
    # must claim a full re-derivation only because one happened, and name the superseded keys
    assert "superseded_snapshot_39338699604" in at
    assert "re-derived" in at.lower() or "re-derived" in at
    # the false prior claim of universal preservation under superseded keys is replaced
    assert "every prior measurement is preserved verbatim under its superseded_snapshot_* key" not in at


def test_r1_republished_by_is_current_run_not_stale_39200567493():
    cov = _load(COVERAGE)
    assert cov["republished_by"] == "39338699604"
    # the stale value lives only inside the superseded prior snapshot
    assert cov["superseded_snapshot_39338699604"]["republished_by"] == "39200567493"


def test_r1_head_and_ungated_still_consistent_with_check18():
    cov = _load(COVERAGE)
    assert cov["accepted_branch_head"] == ACCEPTED_HEAD
    assert cov["ungated_runs_above_the_newest_accept_commit"] == []
    assert cov["runs_above_newest_accept_commit"] == {}
    # check-18's own fields are unchanged in meaning
    assert cov["schema"] == "lex-evaluation-accepted-base-gate-coverage/1"
    assert cov["finding"]["what_is_NOT_claimed"]


# ===================================================================== R2
def test_r2_previous_record_sha256_renamed_to_canonical():
    cov = _load(COVERAGE)
    h0 = cov["history"][0]
    # the mislabeled field must be gone
    assert "previous_record_sha256" not in h0
    # both digests stored under unambiguous names
    assert h0["previous_record_canonical_sha256"] == PRIOR_CANON_SHA
    assert h0["previous_record_raw_sha256"] == PRIOR_RAW_SHA


def test_r2_canonicalization_rule_documented():
    cov = _load(COVERAGE)
    rule = cov["history"][0]["previous_record_canonicalization_rule"]
    assert "sort_keys" in rule
    assert "indent=2" in rule
    assert "ensure_ascii=False" in rule
    assert "NO trailing newline" in rule or "no trailing newline" in rule.lower()


def test_r2_raw_digest_reproduces_from_git_at_3506f0e4():
    raw = subprocess.check_output(
        ["git", "show", "3506f0e4:results/evaluation/accepted_base_gate_coverage_39043684319.json"],
        cwd=ROOT,
    )
    assert hashlib.sha256(raw).hexdigest() == PRIOR_RAW_SHA


def test_r2_canonical_digest_reproduces_from_git_at_3506f0e4():
    raw = subprocess.check_output(
        ["git", "show", "3506f0e4:results/evaluation/accepted_base_gate_coverage_39043684319.json"],
        cwd=ROOT,
    )
    prior = json.loads(raw)
    canon = hashlib.sha256(
        json.dumps(prior, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert canon == PRIOR_CANON_SHA


# ===================================================================== R3
def test_r3_hypothesis_frozen_at_no_longer_post_dates_its_commit():
    hyp = _load(HYP)
    # frozen_at must be <= commit time of bce774b7
    assert hyp["frozen_at"] <= BCE_TIME
    assert hyp["frozen_at"] == BCE_TIME


def test_r3_hypothesis_original_misstamped_value_preserved():
    hyp = _load(HYP)
    assert hyp["frozen_at_original_misstamped_39338699604"] == "2026-10-19T23:30:00Z"
    assert "frozen_at_clock_source" in hyp
    assert "COMMIT ORDER" in hyp["frozen_at_clock_source"] or "commit order" in hyp["frozen_at_clock_source"]


def test_r3_freeze_record_frozen_at_consistent_and_before_result():
    frz = _load(FREEZE)
    assert frz["frozen_at"] == BCE_TIME
    assert frz["frozen_at"] <= C6B_TIME
    assert frz["frozen_at_original_misstamped_39338699604"] == "2026-10-19T23:32:00Z"


def test_r3_freeze_record_re_pins_corrected_hypothesis_sha():
    frz = _load(FREEZE)
    actual = hashlib.sha256(HYP.read_bytes()).hexdigest()
    assert frz["hypothesis_sha256"] == actual
    # pre-repair digest preserved
    assert frz["hypothesis_sha256_repinned_by_repair"]["prior_hypothesis_sha256"] == (
        "a1fff3afa6e357f9592ce5bdfe07d72600b6eb210788bdb08d40acb6932a1957"
    )


def test_r3_result_record_pins_match_live_files():
    res = _load(RES)
    assert res["hypothesis_sha256"] == hashlib.sha256(HYP.read_bytes()).hexdigest()
    assert res["freeze_record_sha256"] == hashlib.sha256(FREEZE.read_bytes()).hexdigest()
    # pre-repair digests preserved
    assert res["hypothesis_sha256_pre_repair_39338699604"] == (
        "a1fff3afa6e357f9592ce5bdfe07d72600b6eb210788bdb08d40acb6932a1957"
    )
    assert res["freeze_record_sha256_pre_repair_39338699604"] == (
        "850b609366162c257ce2f971d79b46d70bc04d1819926d2e3159eab69cca2482"
    )


def test_r3_result_record_measurements_untouched():
    """The R3 repair must not have changed any claim-bearing measurement."""
    res = _load(RES)
    assert res["verdict"] == "PACKET_LANDED_NOT_SERVED_FALSIFICATION_ARMED"
    assert res["exit_code"] == 0
    assert res["packet_admitted"] is False
    assert res["human_gate_ready"] is False
    assert res["ready_for_owner_session"] is False
    assert res["owner_decision_required"] is False
    # generated_at still the original, 9s before its commit
    assert res["generated_at"] == "2026-10-19T23:31:27Z"


def test_r3_freeze_first_commit_order_untouched():
    """Freeze-first rests on commit order, which the repair must not touch."""
    # bce774b7 (freeze) must strictly precede c6b4d479 (result)
    t_freeze = _git("log", "-1", "--format=%cI", "bce774b7")
    t_result = _git("log", "-1", "--format=%cI", "c6b4d479")
    assert t_freeze < t_result
    # the freeze commit's subject still names the freeze-first hypothesis
    subj = _git("log", "-1", "--format=%s", "bce774b7")
    assert "freeze-first hypothesis" in subj


def test_r3_coverage_history_updated_at_no_longer_post_dates_commit():
    cov = _load(COVERAGE)
    h0 = cov["history"][0]
    assert h0["updated_by_run"] == "39338699604"
    assert h0["updated_at"] <= COMMIT_5A6
    assert h0["updated_at"] == COMMIT_5A6
    assert h0["updated_at_original_misstamped_39338699604"] == "2026-10-19T23:55:00Z"
    assert "commit time" in h0["updated_at_clock_source"]


def test_r3_repair_history_entry_present_and_appends():
    cov = _load(COVERAGE)
    assert len(cov["history"]) == 2
    h1 = cov["history"][1]
    assert h1.get("repair_round") == 1
    assert set(h1["repairs_discharged"]) == {"R1", "R2", "R3"}
    # the repair entry's own timestamp is wall-clock at/after the repair commit — allowed
    assert h1["updated_at"] >= COMMIT_5A6


# ===================================================================== R4
def test_r4_accepted_run_id_advanced_to_39334865522():
    st = _load(STATE)
    assert st["accepted_run_id"] == "39334865522"


def test_r4_github_run_is_current_producer_run():
    st = _load(STATE)
    assert st["github_run"] == "39338699604"


def test_r4_promotion_status_appended_not_deleted():
    st = _load(STATE)
    # prior text preserved verbatim
    prior = st["accepted_run_promotion_status_39322925971_verbatim"]
    assert "39329412076 is DELIVERED" in prior
    # appended acceptance recorded
    promo = st["accepted_run_promotion_status"]
    assert prior in promo  # verbatim prefix retained
    assert "3506f0e4" in promo
    assert "39334865522" in promo


def test_r4_current_run_stays_proposed_and_pending():
    st = _load(STATE)
    assert st["proposed_run_id"] == "39338699604"
    assert "PENDING_INDEPENDENT_AUDIT" in st["cycle_status"]
    assert st["continue_recommended"] is True
    # fail-closed flags unchanged
    assert st["summary"]["owner_decision_required"] is False
    assert "human_gate_ready" not in st or st.get("human_gate_ready") is None or st["human_gate_ready"] is False


def test_r4_durable_delta_pins_re_pinned_with_pre_repair_preserved():
    st = _load(STATE)
    dd = st["durable_delta_39338699604"]
    assert dd["hypothesis_sha256"] == hashlib.sha256(HYP.read_bytes()).hexdigest()
    assert dd["freeze_record_sha256"] == hashlib.sha256(FREEZE.read_bytes()).hexdigest()
    assert dd["run_record_sha256"] == hashlib.sha256(RES.read_bytes()).hexdigest()
    assert dd["hypothesis_sha256_pre_repair"] == (
        "a1fff3afa6e357f9592ce5bdfe07d72600b6eb210788bdb08d40acb6932a1957"
    )


# ================================================================== no weakening
def test_no_frozen_bar_or_do_not_serve_touched():
    st = _load(STATE)
    crit = json.dumps(st.get("critical_findings", {}))
    assert "DO-NOT-SERVE" in crit
    # both orders still stand
    assert "38839347028" in crit
    assert "rebuilt-39027045675" in crit
    # absolute bars still unmet / reported-only
    assert "LABEL_UNSOUND" in crit or "absolute_bars_unmet" in crit


def test_repair_block_records_all_four_fixes():
    st = _load(STATE)
    rep = st["repair_round_1_39338699604"]
    assert rep["required_fixes_discharged"] == ["R1", "R2", "R3", "R4"]
    assert "CYCLE_39338699604_GATE.json" in rep["audit_of_record"]
    assert rep["zero_weakening"]
