"""Executable re-derivation of product cycle 40005362253's published claims.

Every number in reports/product/CYCLE_40005362253.md is re-derived here from
the committed artifacts, never copied from prose.  No network, no LLM, no
frozen bar scored.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PRODUCT_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.query import counter_precision as cp  # noqa: E402

RUN_ID = "40005362253"
CP_ART = REPO_ROOT / "results" / "product" / "counter_precision" / f"CYCLE_{RUN_ID}.json"
PROBE_ART = (REPO_ROOT / "results" / "product" / "counter_span"
             / f"CYCLE_{RUN_ID}_absent_id_span_probe.json")
DECLINE_ART = (REPO_ROOT / "results" / "product" / "frontier_verdicts"
               / f"DECLINE_frontier-counter-evidence-span-selection_{RUN_ID}.json")
SWEEP_ART = (REPO_ROOT / "results" / "product" / "regression"
             / f"CYCLE_{RUN_ID}_verification_sweep.json")
SPAN_ART = REPO_ROOT / "results" / "product" / "counter_span" / "CYCLE_39986094168_span_selection.json"
COV_ART = (REPO_ROOT / "results" / "product" / "counter_surface_known"
           / "CYCLE_39956256289.json")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_precision_adjudication_aggregate_re_derives() -> None:
    art = _load(CP_ART)
    pooled = art["aggregate"]["pooled_all_legs"]
    base, delta = pooled["baseline"], pooled["delta"]
    # the published headline numbers
    assert base["n_signals"] == 42
    assert base["n_evidenced_guarded"] == 6
    assert base["evidence_yield_guarded"] == round(6 / 42, 6)
    assert delta["n_signals"] == 28
    assert delta["n_evidenced_guarded"] == 2
    assert delta["evidence_yield_guarded"] == round(2 / 28, 6)
    # the arm rows in the artifact must actually sum to those counts
    pooled_rows = [r for leg in art["legs"] for r in leg["rows"]]
    assert sum(1 for r in pooled_rows if r["arm"] == "baseline") == 42
    assert sum(1 for r in pooled_rows if r["arm"] == "delta") == 28
    assert sum(1 for r in pooled_rows
               if r["arm"] == "delta" and r["guarded"]["evidenced"]) == 2
    # the verdict re-derives from the pre-registered rule, not from prose
    adj = art["aggregate"]["adjudication"]
    recomputed = cp._verdict(base, delta)
    assert adj["verdict"] == recomputed["verdict"] == cp.VERDICT_PROPORTIONAL
    assert adj["min_delta_rate_ratio"] == 0.5
    assert delta["evidence_yield_guarded"] >= 0.5 * base["evidence_yield_guarded"]
    # known reach matches the accepted coverage artifact
    cov = _load(COV_ART)
    assert art["aggregate"]["known_authority_reach"] == {"at_baseline_cap": 8,
                                                         "at_broad_cap": 11}
    assert cov["aggregate"]["by_cap"]["8"]["known_signalled_n"] == 8
    assert cov["aggregate"]["by_cap"]["24"]["known_signalled_n"] == 11
    # invariants
    assert art["invariants"]["network_calls_blocked"] is True
    assert art["invariants"]["budgets_unchanged"] is True
    # the profile coverage gap is disclosed, not hidden
    per_leg = art["profile_resolution_disclosure"]["per_leg"]
    assert per_leg["business-judgment-rule"] == "fr-bail-entretien"
    assert per_leg["petty-theft-dismissal"] is None
    assert per_leg["rent-default"] == "fr-bail-entretien"


def test_absent_id_probe_summary_re_derives() -> None:
    art = _load(PROBE_ART)
    assert art["summary"]["n_probed"] == 3
    assert art["summary"]["n_span_evidenced"] == 0
    assert art["summary"]["network_attempts"] == []
    by_id = {r["decision_id"]: r for r in art["summary"]["per_row"]}
    assert set(by_id) == {"gr_gerichte_PZ_2006_125", "zh_mietgericht_MB170006-L",
                          "ch_vb_JAAC_68.7__"}
    assert by_id["gr_gerichte_PZ_2006_125"]["reason_code"] == "pivot_absent"
    assert by_id["zh_mietgericht_MB170006-L"]["reason_code"] == "pivot_absent"
    assert by_id["ch_vb_JAAC_68.7__"]["reason_code"] == (
        "no_frozen_anchor_profile_for_query")
    # upstream diagnosis is cited
    assert "CYCLE_39986094168_absent_ids.json" in art["upstream_diagnosis"]


def test_frontier_decline_numbers_match_the_committed_span_measurement() -> None:
    decline = _load(DECLINE_ART)
    span = _load(SPAN_ART)
    assert decline["measured_state"]["accepted_run_id"] is None
    assert decline["measured_state"]["evidence_tier"] == "UNTESTED"
    assert decline["measured_state"]["deliverable_artifacts_beyond_control_plane_mirror"] == 0
    nums = decline["numbers_side_by_side"]["product_shipped_seam"]
    baseline = span["aggregate"]["baseline"]
    guarded = span["aggregate"]["candidate"]
    unguarded = span["aggregate"]["candidate_unguarded"]
    assert nums["baseline_n_emitted"] == baseline["n_emitted"] == 0
    assert nums["candidate_guarded_n_emitted"] == guarded["n_emitted"] == 1
    assert nums["candidate_unguarded_n_emitted"] == unguarded["n_emitted"] == 6
    assert nums["n_scored"] == guarded["n_scored"] == 20
    assert nums["candidate_guarded_yield"] == guarded["yield"] == 0.05
    assert nums["candidate_unguarded_yield"] == unguarded["yield"] == 0.3
    # the frontier side is honestly null, not a fabricated zero
    fc = decline["numbers_side_by_side"]["frontier_component"]
    assert all(fc[k] is None for k in
               ("n_emitted", "support_among_issued", "abstentions", "yield"))


def test_state_record_is_present_and_fail_closed() -> None:
    state = _load(REPO_ROOT / "state" / "product.json")
    assert state["current_run"] == RUN_ID
    assert state["accepted_run_id"] == "40000001926"
    assert state["direction_version"] == 65
    assert state["continue_recommended"] is True
    for flag in ("human_gate_ready", "machine_gate_ready",
                 "packet_admitted", "ready_for_owner_session"):
        assert state[flag] is False, flag
    rec = state[f"cycle_{RUN_ID}_direction_v65_ordered_work"]
    assert rec["run_id"] == int(RUN_ID)
    assert "DECLINE" in rec["ordered_item_1_frontier_consumption"]["decision"]
    assert rec["ordered_item_3_precision_adjudication"]["verdict"].startswith(
        "BROADER_BUDGET_ADDS_PROPORTIONAL_EVIDENCE")
    assert rec["ordered_item_4_absent_ids"]["result"].startswith("0/3")


def test_verification_sweep_artifact_matches_its_command() -> None:
    art = _load(SWEEP_ART)
    assert art["run_id"] == int(RUN_ID)
    assert art["result"]["passed"] == 135
    assert art["result"]["failed"] == 0
    assert art["vertical_slice_reverification"]["verdict"] == "PASS"
    assert art["vertical_slice_reverification"]["page_contract"] == "67 assertions"
    assert art["state_contract"]["exit"] == 0
    env = art["environment_disclosure"]
    assert env["numpy"] == "2.5.4" and env["pytest"] == "9.1.1"


def test_report_of_record_cites_only_artifacts_that_exist() -> None:
    report = (REPO_ROOT / "reports" / "product" / f"CYCLE_{RUN_ID}.md").read_text(
        encoding="utf-8")
    assert f"Cycle {RUN_ID}" in report
    for rel in (
        f"results/product/counter_precision/CYCLE_{RUN_ID}.json",
        f"results/product/counter_span/CYCLE_{RUN_ID}_absent_id_span_probe.json",
        f"results/product/frontier_verdicts/"
        f"DECLINE_frontier-counter-evidence-span-selection_{RUN_ID}.json",
        f"results/product/regression/CYCLE_{RUN_ID}_verification_sweep.json",
        "results/product/counter_surface_known/CYCLE_39956256289.json",
        "results/product/counter_span/CYCLE_39986094168_span_selection.json",
    ):
        assert rel in report, f"report must cite {rel}"
        assert (REPO_ROOT / rel).is_file(), f"cited artifact missing: {rel}"
