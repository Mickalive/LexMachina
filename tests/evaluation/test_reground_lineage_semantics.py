"""Contract pins for the lineage-stable regrounding experiment (run 38996043415).

The experiment answers the single successor question cycle 38993062549 left
open: can the frozen geometry gate's regression semantics be re-grounded on a
lineage-stable property, or must it be re-scoped to served_lineage only? These
tests pin the candidate predicates, the R1-R5 discriminating requirements, the
non-vacuity battery and the recorded verdict, so a later cycle cannot silently
soften the accepted outcome or re-derive a frozen bar.

Three layers:
  1. pure predicate tests on synthetic masks (no mount, no network) -- the
     semantics themselves are pinned independent of any real data;
  2. frozen-rubric integration tests -- S2's direction parsing and coverage
     are read from the accepted RULES_GEOMETRY, never assumed;
  3. recorded-run assertions -- the claim-bearing findings are asserted from
     the immutable record, matching the convention of the accepted sweep tests.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation import reground_lineage_semantics as rls
from evaluation.frozen_bars import geometry_gate

REPO = Path(__file__).resolve().parent.parent.parent
FREEZE = (REPO / "results" / "evaluation" / "reground_semantics"
          / "FROZEN_HYPOTHESIS_38996043415.json")
RECORD = (REPO / "results" / "evaluation" / "reground_semantics"
          / "38996043415.json")
MOUNT = Path("/tmp/lex_accepted/product")

requires_record = pytest.mark.skipif(
    not RECORD.exists(), reason=f"record of run 38996043415 absent: {RECORD}")
requires_mount = pytest.mark.skipif(
    not MOUNT.is_dir(), reason="accepted product mount absent")


# ---------------------------------------------------------- the freeze ----
def test_freeze_exists_and_pins_the_question():
    assert FREEZE.exists(), "the hypothesis must be frozen before execution"
    f = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert f["frozen_before_execution"] is True
    assert "lineage-stable" in f["question"].lower()
    assert "re-scoped to served_lineage only" in f["question"]


def test_freeze_pins_no_new_threshold_and_claim_ceiling():
    f = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert "Does NOT re-measure either Frontier candidate" in f["claim_ceiling"]
    assert "does NOT touch, relax or re-derive either frozen bar" in f["claim_ceiling"]
    assert f["candidate_semantics"]["S1_clean_prefix_cell_regression"]["threshold_invented"] is False
    assert f["candidate_semantics"]["S2_monotone_degradation_endpoint"]["threshold_invented"] is False


def test_freeze_discloses_prior_observation_order():
    """The freeze must disclose what was already known, per the no-laundering rule."""
    f = json.loads(FREEZE.read_text(encoding="utf-8"))
    d = f["honest_disclosure_of_observation_order"]
    assert d["what_was_already_known_before_this_freeze"], "must disclose prior knowledge"
    assert d["what_was_NOT_observed_before_this_freeze"], "must disclose the open parts"


# ------------------------------------------- 1. pure predicate semantics --
def _mk_masks(patterns: dict) -> dict:
    """patterns: {packet_id: {qid: {criterion: bool}}} -- fill all criteria."""
    out = {}
    for pid, qs in patterns.items():
        out[pid] = {}
        for q, cells in qs.items():
            out[pid][q] = {c: bool(cells.get(c, False))
                           for c in geometry_gate.CRITERIA_ORDER}
    return out


def _mk_values(patterns: dict) -> dict:
    out = {}
    for pid, qs in patterns.items():
        out[pid] = {}
        for q, cells in qs.items():
            out[pid][q] = {c: cells.get(c) for c in geometry_gate.CRITERIA_ORDER}
    return out


def test_s1_fires_on_clean_prefix_pass_to_fail_transition():
    """P then F -> fires on the second packet. The core S1 predicate."""
    masks = _mk_masks({
        "a": {"q": {"PROJ_RANK": True}},
        "b": {"q": {"PROJ_RANK": False}},
    })
    values = _mk_values({"a": {"q": {"PROJ_RANK": 0.5}}, "b": {"q": {"PROJ_RANK": 0.1}}})
    rls.score_lineage.direction_map = {}
    res = rls.score_lineage(masks, values, ["a", "b"], qids=("q",))
    assert res["S1_clean_prefix"]["fired_keys"] == [("b", "q", "PROJ_RANK")]


def test_s1_never_fires_on_the_first_packet():
    """Empty prefix: the first packet can never be a clean-prefix regression."""
    masks = _mk_masks({"a": {"q": {"PROJ_RANK": False}}})
    values = _mk_values({"a": {"q": {"PROJ_RANK": 0.1}}})
    rls.score_lineage.direction_map = {}
    res = rls.score_lineage(masks, values, ["a"], qids=("q",))
    assert res["S1_clean_prefix"]["fired_keys"] == []


def test_s1_never_fires_on_a_born_failing_cell():
    """F then F: no pass->fail transition exists, so S1 is silent by design."""
    masks = _mk_masks({
        "a": {"q": {"PROJ_RANK": False}},
        "b": {"q": {"PROJ_RANK": False}},
    })
    values = _mk_values({"a": {"q": {"PROJ_RANK": 0.1}}, "b": {"q": {"PROJ_RANK": 0.05}}})
    rls.score_lineage.direction_map = {}
    res = rls.score_lineage(masks, values, ["a", "b"], qids=("q",))
    assert res["S1_clean_prefix"]["fired_keys"] == []


def test_s1_clean_prefix_does_not_fire_after_an_intervening_failure():
    """P, F, F: the third packet's prefix contains a failure, so no fire.

    This is the frozen clean-prefix rule: only the FIRST departure from a
    clean history is a regression; continued failing is not re-flagged.
    """
    masks = _mk_masks({
        "a": {"q": {"PROJ_RANK": True}},
        "b": {"q": {"PROJ_RANK": False}},
        "c": {"q": {"PROJ_RANK": False}},
    })
    values = _mk_values({
        "a": {"q": {"PROJ_RANK": 0.5}}, "b": {"q": {"PROJ_RANK": 0.2}},
        "c": {"q": {"PROJ_RANK": 0.1}}})
    rls.score_lineage.direction_map = {}
    res = rls.score_lineage(masks, values, ["a", "b", "c"], qids=("q",))
    assert res["S1_clean_prefix"]["fired_keys"] == [("b", "q", "PROJ_RANK")]


def test_s1_immediate_prior_control_diverges_on_oscillation():
    """P, F, P, F: full-prefix S1 stays silent at the fourth packet (the
    prefix contains an earlier failure) while the immediate-prior control
    fires (the third packet passed). This is the ONLY divergence mode and
    pins that the two predicates are genuinely different."""
    masks = _mk_masks({
        "a": {"q": {"PROJ_RANK": True}},
        "b": {"q": {"PROJ_RANK": False}},
        "c": {"q": {"PROJ_RANK": True}},
        "d": {"q": {"PROJ_RANK": False}},
    })
    values = _mk_values({
        "a": {"q": {"PROJ_RANK": 0.5}}, "b": {"q": {"PROJ_RANK": 0.2}},
        "c": {"q": {"PROJ_RANK": 0.5}}, "d": {"q": {"PROJ_RANK": 0.1}}})
    rls.score_lineage.direction_map = {}
    res = rls.score_lineage(masks, values, ["a", "b", "c", "d"], qids=("q",))
    assert ("d", "q", "PROJ_RANK") not in res["S1_clean_prefix"]["fired_keys"]
    assert ("d", "q", "PROJ_RANK") in res["S1_immediate_prior_CONTROL"]["fired_keys"]
    assert res["S1_immediate_prior_CONTROL"]["differs_from_S1"] is True


def test_s2_fires_on_monotone_degradation_crossing_a_down_bar():
    """Values fall strictly and the endpoint fails a >= bar: fires, subclass
    crossing_regression because the first packet passed."""
    masks = _mk_masks({
        "a": {"q": {"PROJ_RANK": True}},
        "b": {"q": {"PROJ_RANK": False}},
    })
    values = _mk_values({"a": {"q": {"PROJ_RANK": 0.4}}, "b": {"q": {"PROJ_RANK": 0.1}}})
    rls.score_lineage.direction_map = {"PROJ_RANK": "down_degrading"}
    res = rls.score_lineage(masks, values, ["a", "b"], qids=("q",))
    fired = res["S2_monotone"]["fired"]
    assert len(fired) == 1
    assert fired[0]["subclass"] == "crossing_regression"


def test_s2_fires_on_monotone_worsening_of_a_never_passing_cell():
    """F, F with strictly falling values: fires, subclass
    worsening_while_always_failing (a trend warning, not a transition)."""
    masks = _mk_masks({
        "a": {"q": {"PROJ_SPEARMAN": False}},
        "b": {"q": {"PROJ_SPEARMAN": False}},
    })
    values = _mk_values({"a": {"q": {"PROJ_SPEARMAN": -0.02}},
                         "b": {"q": {"PROJ_SPEARMAN": -0.09}}})
    rls.score_lineage.direction_map = {"PROJ_SPEARMAN": "down_degrading"}
    res = rls.score_lineage(masks, values, ["a", "b"], qids=("q",))
    fired = res["S2_monotone"]["fired"]
    assert len(fired) == 1
    assert fired[0]["subclass"] == "worsening_while_always_failing"


def test_s2_does_not_fire_when_the_endpoint_still_passes():
    """Strictly degrading but the endpoint crosses no bar: no fire (frozen
    rule: monotone approach without crossing is a warning, not a regression)."""
    masks = _mk_masks({
        "a": {"q": {"PROJ_RANK": True}},
        "b": {"q": {"PROJ_RANK": True}},
    })
    values = _mk_values({"a": {"q": {"PROJ_RANK": 0.5}}, "b": {"q": {"PROJ_RANK": 0.35}}})
    rls.score_lineage.direction_map = {"PROJ_RANK": "down_degrading"}
    res = rls.score_lineage(masks, values, ["a", "b"], qids=("q",))
    assert res["S2_monotone"]["fired_keys"] == []


def test_s2_does_not_fire_on_non_monotone_movement():
    """Down then up (or up then down) is not monotone: no fire."""
    masks = _mk_masks({
        "a": {"q": {"STRUCTURE_LARGEST": False}},
        "b": {"q": {"STRUCTURE_LARGEST": False}},
        "c": {"q": {"STRUCTURE_LARGEST": False}},
    })
    values = _mk_values({
        "a": {"q": {"STRUCTURE_LARGEST": 0.7}}, "b": {"q": {"STRUCTURE_LARGEST": 0.5}},
        "c": {"q": {"STRUCTURE_LARGEST": 0.8}}})
    rls.score_lineage.direction_map = {"STRUCTURE_LARGEST": "up_degrading"}
    res = rls.score_lineage(masks, values, ["a", "b", "c"], qids=("q",))
    assert res["S2_monotone"]["fired_keys"] == []


def test_s2_needs_at_least_two_observations():
    """A single observation has no sequence; S2 is silent on the first packet."""
    masks = _mk_masks({"a": {"q": {"PROJ_RANK": False}}})
    values = _mk_values({"a": {"q": {"PROJ_RANK": 0.1}}})
    rls.score_lineage.direction_map = {"PROJ_RANK": "down_degrading"}
    res = rls.score_lineage(masks, values, ["a"], qids=("q",))
    assert res["S2_monotone"]["fired_keys"] == []


def test_s2_up_and_down_directions_are_both_honoured():
    """STRUCTURE_LARGEST (<= bar, up-degrading) and PROJ_RANK (>= bar,
    down-degrading) both fire in their degrading directions."""
    masks = _mk_masks({
        "a": {"q": {"STRUCTURE_LARGEST": True, "PROJ_RANK": True}},
        "b": {"q": {"STRUCTURE_LARGEST": False, "PROJ_RANK": False}},
    })
    values = _mk_values({
        "a": {"q": {"STRUCTURE_LARGEST": 0.5, "PROJ_RANK": 0.4}},
        "b": {"q": {"STRUCTURE_LARGEST": 0.8, "PROJ_RANK": 0.1}}})
    rls.score_lineage.direction_map = {"STRUCTURE_LARGEST": "up_degrading",
                                       "PROJ_RANK": "down_degrading"}
    res = rls.score_lineage(masks, values, ["a", "b"], qids=("q",))
    assert set(res["S2_monotone"]["fired_keys"]) == {
        ("b", "q", "STRUCTURE_LARGEST"), ("b", "q", "PROJ_RANK")}


# ------------------------------------- 2. frozen-rubric integration ------
def test_rules_rehash_to_the_accepted_sha256():
    ident = rls.verify_rules_identity()
    assert ident["RULES_LABEL.json"]["matches"] is True
    assert ident["RULES_GEOMETRY.json"]["matches"] is True
    assert ident["all_match"] is True


def test_s2_direction_parsing_reads_the_frozen_bar_strings():
    """Direction comes from the frozen bar text, never a re-derived constant."""
    rules = geometry_gate.load_frozen_geometry_rules()
    assert rls.parse_bar_direction(rules, "PROJ_RANK")["direction"] == "down_degrading"
    assert rls.parse_bar_direction(rules, "STRUCTURE_LARGEST")["direction"] == "up_degrading"
    assert rls.parse_bar_direction(rules, "STRUCTURE_SEP")["direction"] == "up_degrading"
    assert rls.parse_bar_direction(rules, "LABEL_JACCARD")["direction"] == "up_degrading"


def test_s2_excludes_dynamic_and_compound_bars_by_design():
    rules = geometry_gate.load_frozen_geometry_rules()
    cov = rls.s2_applicable_criteria(rules)
    assert set(cov["applicable"]) == set(rls.S2_STATIC_BAR_CRITERIA)
    assert set(cov["excluded"]) == set(rls.S2_EXCLUDED_BY_DESIGN)
    # the frozen hypothesis and the module agree on the exclusion set
    f = json.loads(FREEZE.read_text(encoding="utf-8"))
    frozen_excl = set(f["candidate_semantics"]["S2_monotone_degradation_endpoint"]["excluded_by_design"])
    assert set(cov["excluded"]) == frozen_excl


def test_s2_coverage_is_seven_static_bar_criteria():
    """Pin the count so a silent expansion of S2's scope is a visible red."""
    rules = geometry_gate.load_frozen_geometry_rules()
    cov = rls.s2_applicable_criteria(rules)
    assert len(cov["applicable"]) == 7
    assert len(cov["excluded"]) == 4


def test_r5_static_scan_finds_no_threshold_writing_in_the_module():
    """An implementation bug that invents a bar voids the run (ENVIRONMENT)."""
    r5 = rls.r5_no_new_threshold(REPO / "evaluation" / "reground_lineage_semantics.py")
    assert r5["holds"] is True
    assert r5["n_offending_lines"] == 0


def test_module_does_not_import_product_code():
    src = (REPO / "evaluation" / "reground_lineage_semantics.py").read_text(encoding="utf-8")
    assert "from product" not in src
    assert "import product" not in src


def test_module_reuses_accepted_entry_points():
    """REUSE-FIRST: the accepted engine and the accepted sweep helpers."""
    src = (REPO / "evaluation" / "reground_lineage_semantics.py").read_text(encoding="utf-8")
    assert "geometry_gate.score_packet" in src or "criterion_mask" in src
    assert "packet_lineage_sweep" in src
    assert "_hostile_geometry" in src


def test_old_anchor_contrast_reproduces_F5_structure():
    """The contrast semantics has an anchor parameter and must be able to
    produce multiple verdict sets; this pins the STRUCTURE, not the outcome."""
    per_counts = {
        "a": {"q1": 6, "q2": 5, "q3": 5},
        "b": {"q1": 6, "q2": 4, "q3": 5},
        "c": {"q1": 6, "q2": 5, "q3": 4},
    }
    # monkeypatch QIDS for the unit test by relying on the module's QIDS
    original = rls.QIDS
    try:
        rls.QIDS = ("q1", "q2", "q3")
        res = rls.old_anchor_contrast(per_counts, ["a", "b", "c"])
        assert res["n_distinct_verdict_sets"] >= 2
        assert res["verdict_set_is_anchor_determined"] is True
        # no anchor marks itself
        assert all(not v["includes_itself"] for v in res["anchors"].values())
    finally:
        rls.QIDS = original


# ------------------------------------------ 3. recorded-run assertions ----
@requires_record
def test_record_verdict_is_regroundable():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    assert rec["verdict"] == "REGROUNDABLE"
    assert rec["exit_code"] == 0


@requires_record
def test_record_R1_order_grounding_holds():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    assert rec["R1_order_grounding"]["holds"] is True
    assert rec["R1_order_grounding"]["orders_identical"] is True


@requires_record
def test_record_R2_old_F5_reproduced_and_new_semantics_anchor_free():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    r2 = rec["R2_anchor_freedom"]
    assert r2["old_semantics_F5_reproduced"] is True
    assert r2["old_n_distinct_verdict_sets"] >= 2
    assert r2["S1_n_verdict_sets"] == 1
    assert r2["S2_n_verdict_sets"] == 1


@requires_record
def test_record_R2_discloses_whole_prefix_control_coincidence():
    """The whole-prefix vs immediate-prior control coincided on this
    population; the freeze's disclosure rule requires it be recorded, not
    hidden. This test pins the disclosure so it cannot be silently dropped."""
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    r2 = rec["R2_anchor_freedom"]
    assert "disclosure" in r2
    assert "coincide" in r2["disclosure"] or "limitation" in r2["disclosure"]
    # and the empirical coincidence itself is recorded either way
    assert isinstance(r2["whole_prefix_reference_load_bearing"], bool)


@requires_record
def test_record_R3_detected_both_accepted_F3_degradations():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    r3 = rec["R3_real_degradation_detection"]
    assert r3["holds"] is True
    assert all(r3["found"].values())


@requires_record
def test_record_R4_hostile_extension_fires_new_cells():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    r4 = rec["R4_non_vacuity_hostile"]
    assert r4["holds"] is True
    assert r4["new_cells"], "the hostile control must fire at least one new cell"


@requires_record
def test_record_battery_all_hold():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    b = rec["non_vacuity_battery"]
    assert b["all_hold"] is True
    for k in ("N1_at_least_one_real_fire", "N2_not_indiscriminate",
              "N3_hostile_detects_new", "N4_old_F5_reproduced",
              "N5_rules_identity"):
        assert b[k]["holds"] is True, k


@requires_record
def test_record_R5_holds():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    assert rec["R5_no_new_threshold"]["holds"] is True


@requires_record
def test_record_S1_fired_exactly_the_two_accepted_F3_cells():
    """S1's real fired set is exactly the two pass->fail transitions the
    accepted F3 analysis identified: (served, de, PROJ_RANK) and
    (middle, fr, STRUCTURE_LARGEST). No more, no less."""
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    fired = {tuple(e) for e in rec["real_population_scoring"]["S1_clean_prefix"]["fired_keys"]}
    assert fired == {
        ("38839347028", "de-kapitalverletzung", "PROJ_RANK"),
        ("38812599575", "fr-bail-entretien", "STRUCTURE_LARGEST"),
    }


@requires_record
def test_record_S2_subclass_split_is_recorded():
    """The crossing-vs-always-failing split is a disclosure, not a predicate;
    it must be present so a consumer can read the difference."""
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    split = rec["real_population_scoring"]["S2_monotone"]["subclass_split"]
    assert "crossing_regression" in split
    assert "worsening_while_always_failing" in split
    # the two F3 degradations appear as crossings
    crossings = {tuple(e) for e in split["crossing_regression"]}
    assert ("38839347028", "de-kapitalverletzung", "PROJ_RANK") in crossings
    assert ("38812599575", "fr-bail-entretien", "STRUCTURE_LARGEST") in crossings


@requires_record
def test_record_claim_ceiling_stays_narrow():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    cc = rec["claim_ceiling"]
    assert "not the CANDIDATE" in cc
    assert "Does NOT re-measure either Frontier candidate" in cc
    assert "says nothing about jurist usefulness" in cc


@requires_record
@requires_mount
def test_record_population_matches_the_accepted_mount():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    assert rec["population"]["in_scope_packet_ids"] == [
        "38799024807", "38812599575", "38839347028"]
    assert rec["population"]["n_in_scope"] == 3
