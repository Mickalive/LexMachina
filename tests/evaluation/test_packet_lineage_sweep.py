"""Contract pins for the packet-lineage gate-validity sweep (run 38993062549).

The sweep is the first executable test of whether the two accepted frozen-bar
gates are sound on the product's OWN bundle lineage, and the first thing anyone
has ever run them against a packet other than the one their incumbents came
from. That makes these tests the guard against the finding being quietly
softened: they pin the falsification, the battery, and the negative-control
structure, so a later cycle cannot turn an accepted negative result into a vague
disclaimer.

Every number asserted here is recomputed from the recorded artifact
results/evaluation/packet_lineage_sweep/38993062549.json, which is the record of
run 38993062549. No test re-runs the gate: the expensive, mount-dependent
execution is asserted from the record, and the cheap structural properties are
re-derived.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from evaluation import packet_lineage_sweep as pls
from evaluation.frozen_bars import geometry_gate

REPO = Path(__file__).resolve().parent.parent.parent
RECORD = REPO / "results" / "evaluation" / "packet_lineage_sweep" / "38993062549.json"
FROZEN = REPO / "results" / "evaluation" / "packet_lineage_sweep" / "FROZEN_HYPOTHESIS_38993062549.json"
MOUNT = Path("/tmp/lex_accepted/product")

requires_record = pytest.mark.skipif(
    not RECORD.exists(), reason=f"record of run 38993062549 absent: {RECORD}")
requires_mount = pytest.mark.skipif(
    not MOUNT.is_dir(), reason="accepted product mount absent")


# --------------------------------------------------------------- the rules --
def test_rules_rehash_to_the_accepted_sha256():
    """REUSE BY RE-HASH. The sweep refuses to score anything else."""
    ident = pls.verify_rules_identity()
    assert ident["RULES_LABEL.json"]["matches"] is True
    assert ident["RULES_GEOMETRY.json"]["matches"] is True
    assert ident["all_match"] is True


def test_sweep_does_not_import_product_code():
    """The bar is owned by Evaluation; scoring must not borrow Product's code."""
    src = (REPO / "evaluation" / "packet_lineage_sweep.py").read_text(encoding="utf-8")
    assert "from product" not in src
    assert "import product" not in src


def test_sweep_invokes_the_accepted_entry_point_only():
    """REUSE-FIRST: no parallel re-implementation of the frozen scoring."""
    src = (REPO / "evaluation" / "packet_lineage_sweep.py").read_text(encoding="utf-8")
    assert "evaluation.frozen_bars.run_bar_gates" in src
    assert "--adjudicate" in src
    # the only gate-side import is the accepted engine, for reading its mask
    assert "from evaluation.frozen_bars import geometry_gate" in src


# ------------------------------------------------------ the frozen contract --
@requires_record
def test_record_verdict_is_the_falsification():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    assert rec["verdict"] == "GATE_FALSIFIED_ON_ACCEPTED_LINEAGE"
    assert rec["exit_code"] == 1


@requires_record
def test_f1_fires_on_exactly_the_accepted_audited_packet():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    f1 = rec["F1_GATE_INVALID_ON_ACCEPTED_AUDITED_LINEAGE"]
    assert f1["holds"] is True
    assert f1["firing_packets"] == ["38812599575"]
    e = rec["per_packet"]["38812599575"]
    assert e["audit"]["gate"] == "PASS"
    assert e["audit"]["safe_to_integrate"] is True
    assert e["audit"]["n_required_fixes"] == 0
    assert e["audit"]["accepted"] is True
    assert e["gate"]["verdict"] == "FAIL_REGRESSION"
    assert e["gate"]["exit_code"] == 1
    assert e["f1_gate_invalid_on_accepted_audited_lineage"] is True


@requires_record
def test_f2_the_incumbent_is_not_a_floor():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    f2 = rec["F2_INCUMBENT_NOT_A_FLOOR"]
    assert f2["holds"] is True
    # strictly below the accepted incumbent on two different qids
    assert f2["min_counts_over_population"]["fr-bail-entretien"] == 4
    assert f2["min_counts_over_population"]["it-responsabilita-medica"] == 4
    assert f2["min_counts_over_population"]["de-kapitalverletzung"] == 6
    assert f2["incumbent_counts"] == geometry_gate.INCUMBENT_COUNTS


@requires_record
def test_f3_churn_moves_in_both_directions():
    """Net change hides opposing movements. A count threshold cannot localize."""
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    f3 = rec["F3_COUNT_MASK_CHURN"]
    assert f3["enforced"] is False  # descriptive only; enforcing churn would invent a bar
    assert f3["n_flipping_cells"] == 5
    assert f3["n_cells_total"] == 33
    assert f3["n_improved_in_time"] == 3
    assert f3["n_degraded_in_time"] == 2
    assert f3["net_change"] == 1
    assert f3["net_zero_churn_with_opposing_directions"] is True


@requires_record
def test_f3_flips_are_large_movements_not_measurement_noise():
    """The 'cancellation' reading must survive an honesty check.

    Every flipped criterion's |delta| is compared with its own frozen bar. A
    flip straddling the bar by ~0.01 would be jitter and the claim would have to
    weaken; these do not, so the cancellation claim stands on magnitude.
    """
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    mags = rec["F3_COUNT_MASK_CHURN"]["per_flip_magnitude"]
    assert len(mags) == 5
    assert rec["F3_COUNT_MASK_CHURN"]["magnitude_note"]
    for m in mags:
        assert isinstance(m["abs_delta_earliest_to_latest"], float), m
        # a knife-edge flip would sit within 0.05 of the bar on both sides
        assert m["abs_delta_earliest_to_latest"] > 0.05, m
    fr = [m for m in mags if m["criterion"] == "STRUCTURE_LARGEST"][0]
    # the French mega-cluster share degrades monotonically across all three builds
    vals = [fr["values_by_packet"][p] for p in sorted(fr["values_by_packet"])]
    assert vals == sorted(vals), vals
    assert fr["bar"] == 0.6
    assert vals[0] < fr["bar"] <= vals[1] <= vals[2]


@requires_record
def test_f5_the_verdict_is_anchor_determined():
    """The core falsification, quantified.

    Each in-scope packet is used in turn as the anchor and the FROZEN predicate
    is re-pointed at it. Three anchor choices produce three different verdicts
    for the same immutable population, so FAIL_REGRESSION encodes 'differs from
    the anchor build' rather than 'degraded relative to the accepted lineage'.
    """
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    f5 = rec["F5_ANCHOR_SENSITIVITY"]
    assert f5["enforced"] is False
    assert f5["verdict_set_is_anchor_determined"] is True
    assert f5["n_distinct_verdict_sets"] == 3
    anchors = f5["anchors"]
    assert set(anchors) == {"38799024807", "38812599575", "38839347028"}
    marked = {a: sorted(r["packet_id"] for r in v["marked_regressed"])
              for a, v in anchors.items()}
    # the accepted incumbent (the frozen anchor) marks BOTH earlier builds
    assert marked["38839347028"] == ["38799024807", "38812599575"]
    # anchoring on the earliest build inverts the verdict for the middle one
    assert marked["38799024807"] == ["38812599575"]
    assert marked["38812599575"] == ["38799024807"]
    # no anchor marks itself, so the comparison is internally coherent
    for a, v in anchors.items():
        assert v["includes_itself"] is False, a


@requires_record
def test_f4_rubric_declared_input_differs_from_the_measured_packet():
    """Set relation, computed as a difference -- never by matching cardinality."""
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    f4 = rec["F4_RUBRIC_INPUT_MISMATCH"]
    assert f4["verifiable"] is True
    assert f4["sets_equal"] is False
    # the discipline that matters: same cardinality, different sets
    assert f4["cardinality_matched_but_sets_differ"] is True
    assert len(f4["declared_not_measured"]) == 3
    assert len(f4["measured_not_declared"]) == 3
    assert set(f4["declared_not_measured"]).isdisjoint(f4["measured_not_declared"])
    # and the sets really do reconstruct both sides
    dec = set(f4["declared_input_sha256"].values())
    mea = set(f4["measured_input_sha256"].values())
    assert dec - set(f4["declared_not_measured"]) == mea - set(f4["measured_not_declared"])
    assert dec != mea


@requires_record
def test_population_records_out_of_scope_packets_with_a_reason():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    pop = rec["population"]
    assert pop["n_packet_dirs"] == 5
    assert pop["n_in_scope"] == 3
    assert pop["in_scope_packet_ids"] == ["38799024807", "38812599575", "38839347028"]
    dropped = {o["packet_id"] for o in pop["out_of_scope"]}
    assert dropped == {"38838116453", "offline_machinery_rehearsal"}
    for o in pop["out_of_scope"]:
        assert o["reason"], "an out-of-scope packet must carry a reason, never be dropped silently"


# ---------------------------------------------------------- non-vacuity ------
@requires_record
def test_non_vacuity_battery_is_complete_and_proven():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    b = rec["non_vacuity_battery"]
    assert b["all_hold"] is True
    assert b["N1_POSITIVE_must_fire"]["holds"] is True
    assert b["N1_POSITIVE_must_fire"]["firing_packets"] == ["38812599575"]
    assert b["N2_NEGATIVE_incumbent_must_not_fire"]["holds"] is True
    assert b["N2_NEGATIVE_incumbent_must_not_fire"]["gate_verdict"] == "PASS_NO_REGRESSION"
    assert b["N3_NEGATIVE_provenance_must_not_fire"]["holds"] is True
    assert b["N4_NEGATIVE_audit_gate_must_not_fire"]["holds"] is True


@requires_record
def test_negative_controls_actually_prove_something():
    """N3 must be a REAL regression, or its silence would be uninformative."""
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    syn = rec["non_vacuity_battery"]["N3_NEGATIVE_provenance_must_not_fire"]["synthetic"]
    assert syn["exit_code"] == 1
    assert syn["geometry_regression_verdict"] == "FAIL_REGRESSION"
    assert syn["is_fail_regression"] is True


@requires_record
def test_a_bare_regression_is_not_reported_as_gate_falsification():
    """38799024807 regresses and is NOT audited-accepted, so F1 must not fire."""
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    e = rec["per_packet"]["38799024807"]
    assert e["gate"]["verdict"] == "FAIL_REGRESSION"
    assert e["audit"]["accepted"] is False
    assert e["f1_gate_invalid_on_accepted_audited_lineage"] is False
    assert e["regression_without_accepted_audit"] is True


@requires_record
def test_incumbent_packet_itself_is_not_falsified():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    e = rec["per_packet"]["38839347028"]
    assert e["gate"]["verdict"] == "PASS_NO_REGRESSION"
    assert e["gate"]["exit_code"] == 0
    assert e["f1_gate_invalid_on_accepted_audited_lineage"] is False


# ---------------------------------------------------- structural self-checks --
@requires_record
def test_no_environment_failure_is_smuggled_into_a_verdict():
    """A missing gate verdict must never be read as 'no regression'."""
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    for pid, e in rec["per_packet"].items():
        assert e["gate"]["environment_failure"] is False, pid
        assert e["gate"]["exit_code"] in (0, 1), pid
        assert e["gate"]["verdict"] in ("PASS_NO_REGRESSION", "FAIL_REGRESSION"), pid


def test_environment_failure_suppresses_every_predicate(tmp_path):
    """If the gate returns no record, the sweep must return exit 2, not a verdict.

    Exercised against a mount that exists but holds no frozen-qid packet, which
    is the cheapest faithful route to the same guard the per-packet environment
    check enforces.
    """
    root = tmp_path / "results" / "product" / "gate_packet"
    (root / "empty").mkdir(parents=True)
    code, rec = pls.run("test-empty", mount=tmp_path)
    assert code == pls.EXIT_ENVIRONMENT
    assert rec["verdict"] == "ENVIRONMENT_OR_UNPROVEN"


def test_discover_packets_marks_in_scope_correctly(tmp_path):
    """Discovery must never classify a partial-qid packet as in scope."""
    root = tmp_path / "results" / "product" / "gate_packet"
    full = root / "full" / "questions"
    part = root / "partial" / "questions"
    full.mkdir(parents=True)
    part.mkdir(parents=True)
    for q in pls.QIDS:
        (full / f"{q}.bundle.json").write_text("{}", encoding="utf-8")
    for q in pls.QIDS[:2]:
        (part / f"{q}.bundle.json").write_text("{}", encoding="utf-8")
    d = pls.discover_packets(tmp_path)
    assert d["root_present"] is True
    by_id = {p["packet_id"]: p for p in d["packets"]}
    assert by_id["full"]["in_scope"] is True
    assert by_id["full"]["n_frozen_qids_present"] == 3
    assert by_id["partial"]["in_scope"] is False
    assert by_id["partial"]["n_frozen_qids_present"] == 2
    assert "it-responsabilita-medica" in by_id["partial"]["out_of_scope_reason"]


@requires_mount
def test_discover_packets_on_the_real_mount():
    d = pls.discover_packets(MOUNT)
    assert d["root_present"] is True
    inscope = {p["packet_id"] for p in d["packets"] if p["in_scope"]}
    assert {"38799024807", "38812599575", "38839347028"} <= inscope


@requires_record
def test_claim_ceiling_disclaims_what_the_sweep_does_not_do():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    cc = rec["claim_ceiling"].lower()
    for phrase in ("gate", "not the candidate", "nothing about jurist usefulness"):
        assert phrase in cc
    assert "absolute bars" in cc


# --------------------------------------------------- the freeze is honoured --
def test_frozen_hypothesis_exists_and_was_frozen_before_execution():
    assert FROZEN.exists(), "the claim-bearing hypothesis must be on disk, not in prose"
    f = json.loads(FROZEN.read_text(encoding="utf-8"))
    assert f["run_id"] == "38993062549"
    assert f["direction_version"] == 50
    for key in ("F1_GATE_INVALID_ON_ACCEPTED_AUDITED_LINEAGE",
                "F2_INCUMBENT_NOT_A_FLOOR",
                "F3_COUNT_MASK_CHURN",
                "F4_RUBRIC_INPUT_MISMATCH"):
        assert key in f["predicates"], key
    assert f["frozen_rubric_reuse_proof"]["RULES_LABEL.json"] == hashlib.sha256(
        (REPO / "evaluation" / "frozen_bars" / "RULES_LABEL.json").read_bytes()
    ).hexdigest()
    assert f["non_vacuity_requirement"]["N1_POSITIVE_must_fire"]


def test_frozen_hypothesis_discloses_the_pre_freeze_probe():
    """Honesty is part of the contract: the exploratory probe is not hidden."""
    f = json.loads(FROZEN.read_text(encoding="utf-8"))
    d = f["honest_disclosure_of_observation_order"]
    assert d["what_was_observed_before_this_freeze"]
    assert isinstance(d["what_was_NOT_observed_before_this_freeze"], list)
    assert len(d["what_was_NOT_observed_before_this_freeze"]) >= 4
    assert d["no_threshold_predicate_or_success_rule_in_this_file_was_changed_after_seeing_a_result"] is True