#!/usr/bin/env python3
"""Tests for evaluation/shipped_bundle_exposure_benchmark.py.

Deliberately runnable WITHOUT the accepted product mount: the falsifier and
non-vacuity logic is exercised on synthetic bundles so the suite stays green in
the CI image and in a bare checkout.  The mount-dependent population is only
used by the two explicitly skipif-guarded tests at the bottom, and their
mount dependence is DISCLOSED rather than hidden.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation.shipped_bundle_exposure_benchmark import (  # noqa: E402
    ADVERSARIAL_EMITTED,
    ABSTAINED,
    CITED,
    FALSIFIERS,
    FROZEN_PINS,
    PACKET_JSON_SHA256,
    check_frozen_pins,
    f1_unclustered_point_mass,
    f2_cluster_panel_coverage,
    f3_cluster_size_member_len_divergence,
    f4_language_unassigned,
    f5_emitted_label_placement,
    f6_issued_population_reconciliation,
    measure,
    non_vacuity,
    _hostile_uncluster,
    _hostile_cover,
    _hostile_size,
    _hostile_language,
    _hostile_emit,
)

MOUNT = Path("/tmp/lex_accepted/product")
SHIPPED = MOUNT / "results/product/gate_packet/rebuilt-39027045675/questions"


def _approx(a: float, b: float, tol: float = 1e-9) -> bool:
    """Plain-arithmetic stand-in for pytest.approx.

    evaluation/no_pytest_runner.py supports only: plain test functions,
    pytest.mark.skipif, pytest.raises and module-level `from evaluation import`.
    `pytest.approx` is NOT supported and raises AttributeError under the shim,
    so it is deliberately not used anywhere in this file.
    """
    return abs(float(a) - float(b)) <= tol


def _bundle(n=6, n_clusters=2):
    """A synthetic shipped-shaped bundle.  Cluster 0 is declared; cluster 1 is
    declared but one point is left unclustered so F1/F2/F3 have something to see."""
    decisions = []
    for i in range(n):
        clustered = i < n - 2
        decisions.append({
            "decision_id": f"dec_{i}",
            "language": "de" if i % 2 == 0 else "fr",
            "cluster_id": 0 if clustered else -1,
            "unclustered": not clustered,
            "is_outlier": clustered,
            "counter_status": "none",
            "counter_anchor_label": None,
            "decision_date": "2020-01-01",
        })
    decisions[0]["counter_status"] = "candidate-contrary"
    decisions[0]["counter_anchor_label"] = "contrary"
    decisions[1]["counter_status"] = ABSTAINED
    decisions[1]["counter_anchor_label"] = "ABSTAIN"
    decisions[2]["counter_status"] = CITED
    clusters = [
        {"cluster_id": 0, "label": "l0", "size": 3,
         "member_ids": ["dec_0", "dec_1", "dec_2"]},
        {"cluster_id": 1, "label": "l1", "size": 2, "member_ids": []},
    ]
    return {"bundle_version": "1.0", "query": "q", "decisions": decisions,
            "clusters": clusters, "answer": {"cited_decision_ids": ["dec_0"]},
            "relations": [], "provenance": {"mode": "live"}}


# ------------------------------------------------------------------ F1
def test_f1_counts_unclustered_points():
    r = f1_unclustered_point_mass(_bundle())
    assert r["n_decisions"] == 6
    assert r["declared_cluster_ids"] == [0, 1]
    assert r["n_fired"] == 2
    assert _approx(r["share"], 2 / 6)
    assert r["by_reason"]["unclustered_flag"] == 2


def test_f1_is_zero_on_a_fully_clustered_bundle():
    b = _bundle()
    for d in b["decisions"]:
        d["unclustered"] = False
        d["cluster_id"] = 0
    r = f1_unclustered_point_mass(b)
    assert r["n_fired"] == 0


def test_f1_hostile_control_moves_the_count():
    b = _bundle()
    assert (f1_unclustered_point_mass(_hostile_uncluster(b))["n_fired"]
            == f1_unclustered_point_mass(b)["n_fired"] - 1)


# ------------------------------------------------------------------ F2
def test_f2_reports_both_differences_and_is_not_identity():
    r = f2_cluster_panel_coverage(_bundle())
    assert r["n_in_both"] == 3
    assert r["n_only_in_decision_list"] == 3          # dec_3..dec_5
    assert r["n_only_in_cluster_member_ids"] == 0
    assert r["set_relations_equal"] is False


def test_f2_fires_on_an_injected_member_id():
    r = f2_cluster_panel_coverage(_hostile_cover(_bundle()))
    assert r["n_only_in_cluster_member_ids"] == 1
    assert r["set_relations_equal"] is False
    assert "__injected_not_a_decision__" in r["examples_only_in_cluster_member_ids"]


def test_f2_is_equal_when_the_panel_covers_everything():
    b = _bundle()
    b["clusters"][0]["member_ids"] = [d["decision_id"] for d in b["decisions"]]
    b["clusters"][1]["member_ids"] = []
    b["clusters"][0]["size"] = 6
    b["clusters"][1]["size"] = 0
    r = f2_cluster_panel_coverage(b)
    assert r["set_relations_equal"] is True
    assert r["fired"] is False


# ------------------------------------------------------------------ F3
def test_f3_counts_size_member_divergence():
    r = f3_cluster_size_member_len_divergence(_bundle())
    # cluster 0: size 3 == len 3 (ok); cluster 1: size 2 vs len 0 (diverges)
    assert r["n_clusters_divergent"] == 1
    assert r["n_rows_omitted_from_panel"] == 2
    assert r["fired"] is True


def test_f3_is_explicitly_not_a_re_raise_of_the_closed_item():
    r = f3_cluster_size_member_len_divergence(_bundle())
    assert r["status"] == "NOT_A_RE_RAISE_OF_THE_ACCEPTED_CLOSED_ITEM"
    assert "CLOSED" in r["cross_reference"]


def test_f3_hostile_control_moves_the_count():
    b = _bundle()
    before = f3_cluster_size_member_len_divergence(b)
    after = f3_cluster_size_member_len_divergence(_hostile_size(b))
    assert (after["n_clusters_divergent"], after["n_rows_omitted_from_panel"]) != (
        before["n_clusters_divergent"], before["n_rows_omitted_from_panel"])


# ------------------------------------------------------------------ F4
def test_f4_counts_unassigned_language_and_the_overlap_with_f1():
    b = _bundle()
    for d in b["decisions"]:
        d["language"] = None
    r = f4_language_unassigned(b)
    assert r["n_fired"] == 6
    assert _approx(r["share"], 1.0)
    assert r["n_missing_that_are_also_F1_unclustered"] == 2


def test_f4_language_histogram_counts_only_assigned():
    r = f4_language_unassigned(_bundle())
    assert r["language_histogram"] == {"de": 3, "fr": 3}
    assert r["n_fired"] == 0


def test_f4_hostile_control_moves_the_count():
    b = _bundle()
    assert f4_language_unassigned(_hostile_language(b))["n_fired"] == \
        f4_language_unassigned(b)["n_fired"] + 1


# ------------------------------------------------------------------ F5
def test_f5_reports_emitted_placement_and_vocabularies():
    r = f5_emitted_label_placement(_bundle())
    assert r["n_emitted_adversarial"] == 1
    assert r["n_abstained"] == 1
    assert r["n_cited_with_counter_evidence"] == 1
    assert r["n_no_counter_evidence"] == 3
    assert r["n_emitted_in_declared_clusters"] == 1
    assert r["n_emitted_unclustered"] == 0
    assert r["emitted_cluster_ids"] == [0]
    assert r["fired"] is False


def test_f5_fires_when_every_emitted_row_is_concealed():
    r = f5_emitted_label_placement(_hostile_emit(_bundle()))
    assert r["n_emitted_adversarial"] == 1
    assert r["n_emitted_in_declared_clusters"] == 0
    assert r["fired"] is True


def test_f5_vocabulary_constants_are_the_shipped_ones():
    assert ADVERSARIAL_EMITTED == ("candidate-contrary", "candidate-limiting")
    assert ABSTAINED == "abstained_unevidenced"
    assert CITED == "cited"


# ------------------------------------------------------------------ F6
def test_f6_set_relation_equals_anchored_on_a_well_formed_bundle():
    r = f6_issued_population_reconciliation(_bundle(), None)
    assert r["set_relations"]["emitted_equals_anchored"] is True
    assert r["shipped_counts"]["n_rows_carrying_counter_anchor_label"] == 1
    assert r["fired"] is False


def test_f6_reports_candidate_denominators_without_claiming_65():
    r = f6_issued_population_reconciliation(_bundle(), None)
    pops = r["candidate_denominator_populations"]
    assert pops["emitted_plus_abstained"] == 2
    assert pops["emitted_plus_abstained_plus_cited"] == 3
    assert pops["all_decisions"] == 6
    assert "discover_population" in r["population_predicate_pinned_to"]


# ------------------------------------------------------------------ battery
def test_non_vacuity_battery_holds_on_a_synthetic_bundle():
    nv = non_vacuity(_bundle())
    assert nv["n_controls"] == 5
    assert nv["all_hold"] is True
    assert all(c["moved"] for c in nv["controls"])
    assert nv["n_not_applicable_zero_population"] == 0


def test_r2_control_moves_in_the_reveal_direction_when_conceal_is_saturated():
    """The r1 defect, regression-guarded.

    r1 shipped a CONCEAL-only F5 control. On a bundle whose emitted rows are
    ALREADY unclustered and unflagged, concealing further cannot move the
    quantity, so r1 failed closed with ENVIRONMENT_OR_VACUOUS. r2 adds the
    REVEAL mutation so the battery is proven live in that situation too.
    """
    b = _bundle()
    # saturate: every emitted row already unclustered and not an outlier
    for d in b["decisions"]:
        if d.get("counter_status") in ADVERSARIAL_EMITTED:
            d["cluster_id"] = -1
            d["unclustered"] = True
            d["is_outlier"] = False
    saturated = f5_emitted_label_placement(b)
    assert saturated["n_emitted_in_declared_clusters"] == 0
    assert saturated["n_emitted_flagged_outlier"] == 0

    nv = non_vacuity(b)
    f5 = next(c for c in nv["controls"] if c["control"] == "F5")
    assert f5["status"] == "MOVED"
    assert f5["moved"] is True
    assert f5["moved_by"] == "_hostile_reveal"
    assert nv["all_hold"] is True


def test_r2_declares_an_empty_population_not_applicable_and_never_a_pass():
    """A bundle that emitted zero adversarial rows cannot prove F5 live."""
    b = _bundle()
    for d in b["decisions"]:
        if d.get("counter_status") in ADVERSARIAL_EMITTED:
            d["counter_status"] = "none"
            d["counter_anchor_label"] = None
    nv = non_vacuity(b)
    f5 = next(c for c in nv["controls"] if c["control"] == "F5")
    assert f5["status"] == "NOT_APPLICABLE_ZERO_POPULATION"
    assert f5["moved"] is None
    assert "NOT a pass" in f5["reading"]
    assert nv["n_not_applicable_zero_population"] == 1
    # a NOT_APPLICABLE control must not be silently counted as holding
    assert nv["all_hold"] is True  # the other four still moved
    assert nv["not_applicable_is_not_a_pass"] is True


def test_r2_still_fails_closed_when_no_direction_moves():
    """If both mutations fail to move, the battery must report VACUOUS."""
    import evaluation.shipped_bundle_exposure_benchmark as mod
    saved = mod.HOSTILE_CONTROLS
    # replace F5's mutations with two that provably change nothing
    mod.HOSTILE_CONTROLS = tuple(
        (tag, name, fn, (lambda b: b, lambda b: b))
        if tag == "F5" else (tag, name, fn, muts)
        for tag, name, fn, muts in saved)
    try:
        b = _bundle()
        nv = non_vacuity(b)
        f5 = next(c for c in nv["controls"] if c["control"] == "F5")
        assert f5["status"] == "VACUOUS"
        assert f5["moved"] is False
        assert nv["all_hold"] is False
    finally:
        mod.HOSTILE_CONTROLS = saved


def test_measure_covers_every_declared_falsifier():
    m = measure(_bundle(), None)
    for fn in FALSIFIERS:
        assert fn.__name__ in m
    assert "f6_issued_population_reconciliation" in m


def test_no_new_threshold_constants_exist_in_the_module():
    """Guard against a later cycle quietly introducing a bar."""
    src = (_REPO_ROOT / "evaluation/shipped_bundle_exposure_benchmark.py").read_text()
    for banned in ("THRESHOLD", "MIN_RECALL", "PASS_BAR", ">= 0.9", "0.5 threshold"):
        assert banned not in src, f"new-threshold token {banned!r} introduced"


# ------------------------------------------------------------------ frozen pins
def test_frozen_pins_rehash_to_the_direction_pins():
    r = check_frozen_pins(_REPO_ROOT)
    assert r["all_match"] is True, r
    for pin in r["pins"]:
        assert pin["observed_sha256"] == FROZEN_PINS[pin["path"]]


def test_packet_pin_matches_factory_direction():
    assert PACKET_JSON_SHA256 == (
        "2942c3c2d729f0055d1b288db3666df1f780d6c1b4ce1f660480ad8bfacf8170")


# ------------------------------------------------- mount-dependent (skipif-guarded)
# DISCLOSURE: these two need the accepted product mount at /tmp/lex_accepted/product.
# They are SKIPIF-guarded, not silently green, and the snapshot-audit record for
# this run discloses that the lane pytest scope is RED-with-2-known-mount-dependent
# failures on other files (see state/evaluation.json audit_fixes_applied_39076123103.R2).
mount_missing = not (SHIPPED / "de-kapitalverletzung.bundle.json").exists()
skip_no_mount = pytest.mark.skipif(
    mount_missing, reason="accepted product mount absent in this image")


@skip_no_mount
def test_shipped_bundles_are_all_measurable():
    paths = sorted(SHIPPED.glob("*.bundle.json"))
    assert len(paths) == 3
    for p in paths:
        b = json.loads(p.read_text())
        m = measure(b, None)
        assert m["f1_unclustered_point_mass"]["n_decisions"] == len(b["decisions"])
        assert m["f5_emitted_label_placement"]["n_no_counter_evidence"] >= 0


@skip_no_mount
def test_shipped_packet_json_matches_the_pin():
    import hashlib
    pj = MOUNT / "results/product/gate_packet/rebuilt-39027045675/packet.json"
    assert hashlib.sha256(pj.read_bytes()).hexdigest() == PACKET_JSON_SHA256