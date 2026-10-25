"""Executable re-derivation of product cycle 40188639817's published claims.

This cycle is the OPERATIONAL RESUME of run 40182739499, whose team job
succeeded and whose audit job failed inside the "Independent audit" agent step
(no gate file, no audit ref).  The claims are kept in four separate groups:

1. **Orchestration diagnosis** - classified from a committed public run/jobs
   snapshot by ``product/audit_step_diagnosis.py``.  The team snapshot was
   persisted; the audit gate step was skipped; no mechanism is claimed because
   job logs were not downloadable.
2. **Ordered work (1) before/after** - the four decisions the accepted FAST-MVP
   falsifier measured as verified-but-defective are downgraded on the fixed
   path, with reason codes, and the sound row stays verified.
3. **Ordered work (2) completion** - the family histogram is still zero for
   D2/D3/D4, the accepted packet-of-record v3 bytes are unchanged, both v3
   arms reproduce the accepted measurement exactly, support-among-emitted /
   abstention count / yield are published together, and the guarded-arm yield
   does not decrease.
4. **Posture** - the accepted pointer is unchanged, every fail-closed flag
   stays false, and the vertical slice still passes over a real socket.

Nothing here writes a gate, scores a frozen bar, or labels any chain run as
accepted or rejected.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product import audit_step_diagnosis as asd              # noqa: E402
from product import content_family_probe as cfp            # noqa: E402
from product.query.counter_anchor import find_forbidden_constructions  # noqa: E402

RUN_ID = "40188639817"
RESUMED_RUN_ID = "40182739499"
DIRV = 68

ORCH = REPO_ROOT / "results" / "product" / "orchestration"
RAW = ORCH / f"CYCLE_{RUN_ID}_audit_step_raw.json"
DIAG = ORCH / f"CYCLE_{RUN_ID}_audit_step_diagnosis.json"
PROBE = (REPO_ROOT / "results" / "product" / "counter_content_family"
         / f"CYCLE_{RUN_ID}.json")
SMOKE = (REPO_ROOT / "results" / "product" / "progressive_smoke"
         / f"CYCLE_{RUN_ID}_progressive_smoke.json")
REPORT = REPO_ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md"
STATE = REPO_ROOT / "state" / "product.json"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# 1. Orchestration diagnosis
# ---------------------------------------------------------------------------

def test_audit_step_diagnosis_is_reproducible_from_the_raw_snapshot() -> None:
    raw = _load(RAW)
    art = _load(DIAG)
    assert str(raw["run"]["id"]) == RESUMED_RUN_ID
    assert raw["run"]["conclusion"] == "failure"
    fresh = asd.classify(raw)
    assert fresh["classification"] == art["classification"]
    # Amendment (operational resume 40193974025): the classifier gained
    # additive, separately-derived fields (persist-step conclusion, failed
    # team step, producer-validation/scope step conclusions).  Compare every
    # key the historical artifact published instead of forbidding additions.
    # This is not a weakening: an existing key that changes value still fails.
    for key, value in art["team"].items():
        assert fresh["team"][key] == value, key
    assert fresh["audit"] == art["audit"]
    assert fresh["integrate"] == art["integrate"]
    assert fresh["mechanism"]["status"] == "UNOBSERVED"


def test_the_team_snapshot_survived_and_no_audit_gate_was_written() -> None:
    art = _load(DIAG)
    assert art["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    )
    assert art["team"]["team_snapshot_persisted"] is True
    assert art["team"]["producer_state_validation_ran"] is True
    assert art["audit"]["failed_step"] == "Independent audit"
    assert art["audit"]["gate_step"] == "skipped"
    assert art["audit"]["gate_file_written"] is False
    assert art["integrate"]["conclusion"] == "skipped"
    assert art["adjudication"]["product_defect"] is False
    assert art["adjudication"]["requires_product_repair"] is False
    # Producer must never self-mint the independent gate.
    assert not (REPO_ROOT / "results" / "audit" / "product"
                / f"CYCLE_{RUN_ID}_GATE.json").exists()


# ---------------------------------------------------------------------------
# 2/3. Ordered work (1) and (2): published artifact reproduces
# ---------------------------------------------------------------------------

def test_content_family_artifact_reproduces_on_current_head() -> None:
    art = _load(PROBE)
    fresh = cfp.run(run_id=RUN_ID, direction_version=DIRV)
    assert art["run_id"] == RUN_ID
    for key in ("fixed_path_family", "historical_population", "all_committed",
                "confirmed_set", "before_after", "packet_v3_reemission",
                "ordered_work_2_success_rule",
                "ordered_work_2_full_success_rule", "false_reject_count"):
        assert fresh[key] == art[key], key
    t = art["fixed_path_family"]["totals"]
    assert t["n_bundles"] == 29
    assert t["n_verified_defective"] == 0
    assert t["defect_histogram"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }
    assert art["ordered_work_2_full_success_rule"]["met"] is True


def test_the_four_defective_rows_are_before_after_and_the_sound_row_survives() -> None:
    art = _load(PROBE)
    ba = art["before_after"]["per_row"]
    assert ba["all_four_present"] is True
    assert ba["all_four_before_verified"] is True
    assert ba["all_four_after_unevidenced"] is True
    assert ba["false_reject_count"] == 0
    assert ba["defect_free_downgrades"] == []
    coverage = {c["decision_id"]: c for c in ba["accepted_four_coverage"]}
    assert set(coverage) == {
        "gr_gerichte_ERZ 2010 25",
        "bge_BGE_110_II_391",
        "ge_gerichte_CAPH_107_2004",
        "bge_BGE_121_III_260",
    }
    for did, expected in {
        "gr_gerichte_ERZ 2010 25": ["D2_letterhead_zone"],
        "bge_BGE_110_II_391": ["D2_letterhead_zone"],
        "ge_gerichte_CAPH_107_2004": ["D3_markup_residue"],
        "bge_BGE_121_III_260": ["D3_markup_residue",
                                "D4_language_marker_mismatch"],
    }.items():
        row = coverage[did]
        assert row["observed_defects"] == expected, did
        assert row["before_verified"] is True, did
        assert row["after_verified"] is False, did
        assert row["after_reason_code"], did
    sound = ba["sound_row"]
    assert sound["decision_id"] == "bstger_SK.2023.49"
    assert sound["still_verified"] is True
    assert sound["defects"] == []
    # historical defects stay preserved beside the fixed path
    hist = art["before_after"]["per_class_histogram"]
    assert hist["historical_before_population"]["D2_letterhead_zone"] > 0
    assert hist["fixed_path_after_population"] == {
        "D1_empty_evidence": 0,
        "D2_letterhead_zone": 0,
        "D3_markup_residue": 0,
        "D4_language_marker_mismatch": 0,
    }


def test_packet_of_record_v3_arms_reproduce_and_bytes_do_not_move() -> None:
    art = _load(PROBE)["packet_v3_reemission"]
    assert art["available"] is True
    assert art["checks"] == {
        "packet_bytes_unchanged": True,
        "baseline_reproduced": True,
        "unguarded_reproduced": True,
        "guarded_reproduced": True,
        "guarded_yield_not_decreased": True,
        "guarded_emitted_content_clean": True,
        "guarded_emitted_verbatim": True,
    }
    # accepted artifact identity is pinned by hash, not re-written
    assert _sha256(REPO_ROOT / art["accepted_artifact"]) == (
        art["accepted_artifact_sha256"]
    )
    totals = art["totals"]
    assert totals["accepted_baseline"] == totals["current_baseline"]
    assert totals["accepted_unguarded"] == totals["current_unguarded"]
    assert totals["accepted_guarded"] == totals["current_guarded"]
    assert totals["current_guarded"]["n_scored"] == 20
    assert totals["current_guarded"]["n_emitted"] == 1
    assert totals["current_guarded"]["n_emitted_verified"] == 1
    assert totals["current_guarded"]["support_rate_among_emitted"] == 1.0
    assert totals["current_guarded"]["yield"] == 0.05
    assert totals["current_unguarded"]["n_emitted"] == 6
    assert totals["current_unguarded"]["n_emitted_verified"] == 6
    assert totals["current_unguarded"]["yield"] == 0.3
    # Yield did not decrease relative to the accepted guarded arm.
    assert totals["current_guarded"]["yield"] >= totals["accepted_guarded"]["yield"]
    for slug, b in art["bundles"].items():
        assert b["packet_bytes_unchanged"] is True, slug
        assert b["guarded_emitted_content_clean"] is True, slug
        assert b["guarded_emitted_verbatim"] is True, slug
        for defects in b["guarded_emitted_content_defects"].values():
            assert defects == [], (slug, defects)


def test_v68_rejection_leg_is_a_no_op_on_frozen_v3_bytes_and_that_is_disclosed() -> None:
    art = _load(PROBE)["packet_v3_reemission"]
    effect = art["v68_rejection_effect_on_v3"]
    assert effect["total_downgrades"] == 0
    assert "no verified defective incumbent" in effect["note"]
    # The one guarded emission is the accepted span seam's own clean row.
    fr = art["bundles"]["fr-bail-entretien"]
    assert fr["current_guarded"]["emitted_ids"] == ["bge_136 III 196"]
    assert fr["guarded_emitted_content_defects"] == {"bge_136 III 196": []}


# ---------------------------------------------------------------------------
# 4. Vertical slice and fail-closed posture
# ---------------------------------------------------------------------------

def test_progressive_smoke_still_passes_within_budget() -> None:
    art = _load(SMOKE)
    assert art["verdict"] == "PASS", art.get("failures")
    assert art["checks_passed"] == art["checks_total"]
    assert art["mode"].startswith("fixture")
    t = art["timings_s"]
    assert t["server_boot_s"] < 3.0, t
    assert t["start_s"] < 3.0, t


def test_state_stays_fail_closed_and_the_accepted_pointer_is_unchanged() -> None:
    st = _load(STATE)
    assert st["lane"] == "product"
    assert st["direction_version"] == DIRV
    assert st["cycle_status"] == "COMPLETE"
    assert st["continue_recommended"] is True
    assert st["human_gate_ready"] is False
    assert st["machine_gate_ready"] is False
    assert st["packet_admitted"] is False
    assert st["ready_for_owner_session"] is False
    assert st["accepted_run_id"] == "CYCLE_40159523259"
    cycle = st["cycle_40188639817"]
    assert cycle["resumed_run"] == RESUMED_RUN_ID
    assert cycle["orchestration_failure_of_record"]["classification"] == (
        "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE"
    )
    assert cycle["ordered_work_2_completion"]["full_success_rule_met"] is True
    assert cycle["accepted_this_cycle"] is False


def test_no_artifact_asserts_a_specific_decisions_counter_polarity() -> None:
    for path in (PROBE, DIAG, REPORT):
        text = path.read_text(encoding="utf-8")
        assert find_forbidden_constructions(text) == [], path
    report = REPORT.read_text(encoding="utf-8")
    assert RUN_ID in report
    assert "AUDIT_JOB_INDEPENDENT_AUDIT_STEP_FAILED_NO_GATE" in report
    assert "UNADJUDICATED" in report or "unadjudicated" in report
