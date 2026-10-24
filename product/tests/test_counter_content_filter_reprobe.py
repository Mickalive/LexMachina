"""Direction v66 P0: counter-evidence content-quality repair (D2/D3/D4).

Frozen acceptance contract for this cycle (factory-wide requirement 37):
  * the 14 known defective rows are filtered or downgraded (defect histogram
    -> 0 on the re-probe),
  * NO substantive span the frozen gate previously confirmed is falsely
    rejected (regression count on the confirmed set == 0),
  * the guarded-arm yield on packet-of-record v3 does not decrease.

Plus the ordered item-(2) frozen-scorer path diagnosis and the guard rails
that keep the filter a narrowing-only, model-free instrument.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from product.query.counter_evidence_span import (
    LANGUAGE_MARKER_SETS,
    MIN_MARKER_HITS,
    SPAN_CONTENT_FILTER_ENV,
    content_defects_for_row,
    detect_language_marker_mismatch,
    downgrade_content_defects,
    passes_content_filter,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REPROBE = (
    REPO_ROOT / "results" / "product" / "counter_span"
    / "CYCLE_40057956963_content_filter_reprobe.json"
)
DIAGNOSIS = (
    REPO_ROOT / "results" / "product" / "counter_span"
    / "CYCLE_40057956963_frozen_scorer_path_diagnosis.json"
)
ACCEPTED_H2 = (
    REPO_ROOT / "results" / "product" / "counter_span"
    / "accepted_h2_probe_40044626742.json"
)
FLAGSHIP_LETTERHEAD = (
    REPO_ROOT / "results" / "product" / "offline_slice"
    / "20261023T224250Z" / "rent-default.bundle.json"
)
FLAGSHIP_MARKUP = (
    REPO_ROOT / "results" / "product" / "server_slice"
    / "20261023T224255Z" / "served.bundle.json"
)


@pytest.fixture(scope="module")
def report() -> dict:
    from product.measure_counter_content_filter import run

    return run()


@pytest.fixture(scope="module")
def diagnosis() -> dict:
    from product.diagnose_frozen_scorer_path import run as diag_run

    return diag_run()


def _row(path: Path, decision_id: str) -> dict:
    blob = json.loads(path.read_text(encoding="utf-8"))
    for d in blob.get("decisions") or []:
        if str(d.get("decision_id")) == decision_id:
            return d
    raise AssertionError(f"{decision_id} not in {path}")


# --------------------------------------------------------------------------
# Success rule 1 - defect histogram -> 0 on the re-probe
# --------------------------------------------------------------------------
def test_before_histogram_reproduces_the_accepted_h2_probe(report: dict) -> None:
    a = report["part_a_flagship_reprobe"]
    assert a["reproduces_accepted_h2_before_histogram"] is True
    assert a["before"]["defect_histogram"] == {
        "D2_letterhead_zone": 10,
        "D3_markup_residue": 4,
        "D4_language_marker_mismatch": 4,
    }
    assert a["before"]["n_rows"] == 14
    assert a["before"]["n_distinct_decisions"] == 2
    assert a["before_product_filter"]["n_disagreements"] == 0
    assert a["n_bundles_missing"] == 0
    assert a["n_bundles_sha_drift"] == 0


def test_after_histogram_is_zero_and_all_14_rows_are_handled(report: dict) -> None:
    a = report["part_a_flagship_reprobe"]
    assert a["after"]["defect_histogram_over_surviving_verified_rows"] == {}
    assert a["after"]["n_filtered_or_downgraded"] == 14
    assert a["after"]["n_downgraded_by_seam"] == 14
    assert a["success_rule_14_defective_rows_handled"] is True


# --------------------------------------------------------------------------
# Success rules 2 and 3 - no false rejection, yield never decreases
# --------------------------------------------------------------------------
def test_regression_count_on_confirmed_set_is_zero(report: dict) -> None:
    b = report["part_b_packet_v3_yield_and_regression"]
    assert b["regression_count_on_confirmed_set"] == 0
    assert b["regressions"] == []


def test_guarded_and_unguarded_yield_do_not_decrease(report: dict) -> None:
    b = report["part_b_packet_v3_yield_and_regression"]
    agg = b["aggregate"]
    baseline = b["accepted_span_baseline"]
    assert agg["guarded_filter_on"]["yield"] >= baseline["guarded_yield"]
    assert agg["unguarded_filter_on"]["yield"] >= baseline["unguarded_yield"]
    # Filter on/off must be identical on this population: the filter rejected
    # nothing the frozen gate had confirmed, which is the non-regression claim.
    assert agg["guarded_filter_on"]["n_emitted"] == agg["guarded_filter_off"]["n_emitted"]
    assert agg["unguarded_filter_on"]["n_emitted"] == agg["unguarded_filter_off"]["n_emitted"]
    assert agg["guarded_filter_on"]["support_rate_among_issued"] == 1.0
    assert agg["unguarded_filter_on"]["support_rate_among_issued"] == 1.0


def test_all_success_rules_are_met(report: dict) -> None:
    sr = report["success_rule"]
    assert sr["all_rules_met"] is True, sr
    assert all(v is True for v in sr.values())


def test_committed_reprobe_artifact_matches_a_fresh_run() -> None:
    assert REPROBE.exists(), "committed P0 reprobe artifact missing"
    committed = json.loads(REPROBE.read_text(encoding="utf-8"))
    from product.measure_counter_content_filter import run

    fresh = run()
    assert committed["success_rule"] == fresh["success_rule"]
    assert (
        committed["part_a_flagship_reprobe"]["after"]
        == fresh["part_a_flagship_reprobe"]["after"]
    )
    assert (
        committed["part_a_flagship_reprobe"]["before"]["defect_histogram"]
        == fresh["part_a_flagship_reprobe"]["before"]["defect_histogram"]
    )
    assert (
        committed["part_b_packet_v3_yield_and_regression"]["aggregate"]
        == fresh["part_b_packet_v3_yield_and_regression"]["aggregate"]
    )


# --------------------------------------------------------------------------
# The filter itself: deterministic, model-free, narrow-only
# --------------------------------------------------------------------------
def test_letterhead_row_is_rejected_as_d2() -> None:
    row = _row(FLAGSHIP_LETTERHEAD, "gr_gerichte_ERZ 2010 25")
    assert row.get("counter_evidence_verified") is True
    ok, reason = passes_content_filter(
        str(row.get("counter_evidence") or ""), row, start=0, field="full_text"
    )
    assert ok is False
    assert reason == "d2_letterhead_zone"
    assert "d2_letterhead_zone" in content_defects_for_row(row)


def test_markup_and_language_rows_are_rejected_as_d3_d4() -> None:
    row = _row(FLAGSHIP_MARKUP, "bge_BGE_121_III_260")
    assert row.get("counter_evidence_verified") is True
    codes = content_defects_for_row(row)
    assert "d3_markup_residue" in codes
    assert "d4_language_marker_mismatch" in codes
    ok, reason = passes_content_filter(
        str(row.get("counter_evidence") or ""), row, start=0, field="full_text"
    )
    assert ok is False
    assert reason in ("d3_markup_residue", "d4_language_marker_mismatch")


def test_unlabelled_language_is_never_a_mismatch() -> None:
    # A filter may narrow spans; it may never invent a language the row did
    # not declare.  UNLABELLED rows carrying German function words must pass.
    german = "Der Vermieter kann das Mietverhältnis kündigen und wird nicht " \
             "davon absehen, denn die Parteien sind nicht einverstanden."
    for lang in ("UNLABELLED", "", None, "de"):
        assert detect_language_marker_mismatch(german, lang) is False
    # ...while a declared-Italian row carrying that German text IS a mismatch.
    assert detect_language_marker_mismatch(german, "it") is True


def test_filter_constants_are_byte_identical_to_the_accepted_h2_definitions() -> None:
    art = json.loads(ACCEPTED_H2.read_text(encoding="utf-8"))
    defs = art["shipped_slice_counter_evidence_probe"]["definitions"]
    assert LANGUAGE_MARKER_SETS == defs["LANGUAGE_MARKER_SETS"]
    assert MIN_MARKER_HITS == defs["MIN_MARKER_HITS"]


def test_downgrade_only_narrows_and_leaves_geometry_and_status_counts_alone() -> None:
    blob = json.loads(FLAGSHIP_LETTERHEAD.read_text(encoding="utf-8"))
    before_geo = {
        (d["decision_id"], d.get("x"), d.get("y"), d.get("cluster_id"))
        for d in blob["decisions"]
    }
    before_hist = {
        d["decision_id"]: d.get("counter_status") for d in blob["decisions"]
    }
    out = downgrade_content_defects(copy.deepcopy(blob))
    after_geo = {
        (d["decision_id"], d.get("x"), d.get("y"), d.get("cluster_id"))
        for d in out["decisions"]
    }
    assert after_geo == before_geo

    target = _row_from(out, "gr_gerichte_ERZ 2010 25")
    assert target["counter_evidence_verified"] is False
    assert target["counter_status"] == "abstained_unevidenced"
    # Append-only: the original quote is never deleted.
    assert target["counter_evidence"]
    assert target["counter_evidence_downgraded"] == "d2_letterhead_zone"

    prov = out["provenance"]["counter_evidence_content_filter"]
    assert prov["model_free"] is True
    assert prov["touches_frozen_gate"] is False
    assert prov["n_downgraded"] >= 1

    # The one counter authority stays a counter authority (abstained rows are
    # counter statuses), so offline-slice headline counts do not move.
    from product.query.counter_status import counter_authority_count

    assert counter_authority_count(out["decisions"]) == counter_authority_count(
        blob["decisions"]
    )
    assert before_hist  # sanity: the fixture really carries counter statuses


def _row_from(blob: dict, decision_id: str) -> dict:
    for d in blob.get("decisions") or []:
        if str(d.get("decision_id")) == decision_id:
            return d
    raise AssertionError(decision_id)


def test_pipeline_wires_the_downgrade_pass() -> None:
    src = (REPO_ROOT / "product" / "query" / "pipeline.py").read_text(encoding="utf-8")
    assert "downgrade_content_defects(audited)" in src


def test_content_filter_env_knob_is_wired_and_defaults_on() -> None:
    from product.query.counter_evidence_span import _content_filter_enabled

    assert _content_filter_enabled({}) is True
    assert _content_filter_enabled({SPAN_CONTENT_FILTER_ENV: "off"}) is False
    assert _content_filter_enabled({SPAN_CONTENT_FILTER_ENV: "on"}) is True


# --------------------------------------------------------------------------
# Ordered item (2) - frozen-scorer path visibility
# --------------------------------------------------------------------------
def test_diagnosis_names_the_code_path_and_declares_a_product_contract_gap(
    diagnosis: dict,
) -> None:
    assert diagnosis["verdict"] == "PRODUCT_CONTRACT_GAP"
    assert diagnosis["scorer_defect"] is False
    assert diagnosis["answer"].startswith("IT SCORES ONLY THE PRE-SEAM PROPOSALS")
    assert diagnosis["frozen_rules_reported_only"]["rehash_matches"] is True

    lines = diagnosis["frozen_scorer_reference"]["line_anchors"]
    assert lines["label_gate.py"]["counter_rows_call"] > 0
    assert lines["extract.py"]["population_read"] > 0
    assert lines["extract.py"]["scored_membership_test"] > 0

    path = diagnosis["code_path_difference"]
    assert len(path) >= 6
    assert any(e["family"] == "frozen_scorer" for e in path)
    assert any(e["family"] == "product_span_seam" for e in path)
    assert any(e["family"] == "gap" for e in path)
    assert diagnosis["remediation_not_taken_here"]


def test_both_measurement_families_are_published_side_by_side(diagnosis: dict) -> None:
    a = diagnosis["measurement_A_frozen_scorer_family"]
    assert a["n_issued"] == 0
    assert a["n_emitted"] == 0
    assert "NOT the product harness" in a["quote_ceiling"]
    b = diagnosis["measurement_B_product_span_harness_family"]
    assert b["guarded_filter_on"]["n_emitted"] == 1
    assert b["unguarded_filter_on"]["n_emitted"] == 6
    assert "never interchangeable" in diagnosis["side_by_side"]
    # The packet really carries no span-seam provenance.
    for bundle in a["packet"]["bundles"].values():
        assert bundle["provenance_has_counter_evidence_span"] is False
        assert bundle["n_rows_in_frozen_scored_statuses"] == 0


def test_committed_diagnosis_artifact_matches_a_fresh_run(diagnosis: dict) -> None:
    assert DIAGNOSIS.exists(), "committed diagnosis artifact missing"
    committed = json.loads(DIAGNOSIS.read_text(encoding="utf-8"))
    assert committed["verdict"] == diagnosis["verdict"]
    assert committed["code_path_difference"] == diagnosis["code_path_difference"]
    assert (
        committed["measurement_A_frozen_scorer_family"]["n_issued"]
        == diagnosis["measurement_A_frozen_scorer_family"]["n_issued"]
    )


# --------------------------------------------------------------------------
# Frozen inputs are re-hashed, never re-derived
# --------------------------------------------------------------------------
def test_frozen_rules_label_is_rehashed_not_rederived() -> None:
    import hashlib

    path = REPO_ROOT / "product" / "frozen" / "RULES_LABEL.json"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
