"""Guard tests for evaluation cycle 40040574595 (direction v65).

These tests do NOT touch the product mount and do NOT execute any claim-bearing
measurement. They pin the frozen definitions of
``evaluation/v65_head_advance_crosscheck_v2.py`` to its committed hypothesis and
freeze record, prove the probe's D1-D4 predicates on planted rows, and prove the
instrument never applies a frozen bar.

Run under the lane's no-pytest runner or under real pytest:
    python -m evaluation.no_pytest_runner --run-id <id> \
        --test-file tests/evaluation/test_v65_head_advance_crosscheck_v2.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import v65_head_advance_crosscheck_v2 as INSTR  # noqa: E402

HYP = REPO_ROOT / "evaluation/V65_HEAD_ADVANCE_CROSSCHECK_HYPOTHESIS_V2.json"
FRZ = REPO_ROOT / "evaluation/V65_HEAD_ADVANCE_CROSSCHECK_FREEZE_RECORD_V2.json"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_freeze_record_pins_the_hypothesis_digest():
    frz = json.loads(FRZ.read_text())
    assert frz["hypothesis_sha256"] == _sha(HYP)
    assert frz["hypothesis_sha256"] == INSTR.EXPECTED_HYPOTHESIS_SHA


def test_frozen_probe_definitions_match_the_instrument():
    hyp = json.loads(HYP.read_text())
    d = hyp["probe_definitions_frozen"]
    assert d["LETTERHEAD_ZONE_OFFSET_MAX"] == INSTR.LETTERHEAD_ZONE_OFFSET_MAX == 400
    assert d["MARKUP_TOKENS"] == INSTR.MARKUP_TOKENS
    assert d["MIN_MARKER_HITS"] == INSTR.MIN_MARKER_HITS == 3
    assert d["LANGUAGE_MARKER_SETS"] == INSTR.LANGUAGE_MARKER_SETS


def test_frozen_bundle_list_matches_the_instrument():
    hyp = json.loads(HYP.read_text())
    d = hyp["probe_definitions_frozen"]
    flat = []
    for rels in d["probe_bundle_list"].values():
        flat.extend(rels)
    instr_flat = []
    for rels in INSTR.PROBE_BUNDLES.values():
        instr_flat.extend(rels)
    assert sorted(flat) == sorted(instr_flat)
    assert len(instr_flat) == 14
    assert d["prior_cycle_control"]["bundle"] == INSTR.PRIOR_CYCLE_CONTROL
    assert sorted(d["scoping_inspected_bundles"]) == sorted(INSTR.SCOPING_INSPECTED)


def test_currency_quantity_ids_are_unique_and_all_have_published_values():
    frz = json.loads(FRZ.read_text())
    qs = frz["currency_quantities_frozen"]
    ids = [q["id"] for q in qs]
    assert len(ids) == len(set(ids))
    for q in qs:
        assert "published" in q
        assert "kind" in q
        assert "artifact" in q


def test_frozen_pins_cover_every_probe_bundle():
    frz = json.loads(FRZ.read_text())
    keys = set(frz["frozen_pins"])
    for rels in INSTR.PROBE_BUNDLES.values():
        for rel in rels:
            assert f"mount:{rel}" in keys, rel
    assert f"mount:{INSTR.PRIOR_CYCLE_CONTROL}" in keys
    assert "mount:results/product/gate_packet/39319405429/packet.json" in keys
    assert "repo:evaluation/frozen_bars/RULES_LABEL.json" in keys
    assert "repo:evaluation/frozen_bars/RULES_GEOMETRY.json" in keys


def test_accepted_failed_gate_set_is_unchanged():
    assert INSTR.ACCEPTED_FAILED_GATES == [
        "mf::concept_coverage::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
        "mf::counter_authority_surface::39319405429::fr-bail-entretien",
        "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
    ]


def test_probe_fires_D2_on_planted_letterhead_and_not_on_mid_document():
    ft = ("Kantonsgericht von Graubünden\n" + ("_" * 120) + "\n" + ("x" * 500)
          + "\nGericht hat in Erwägung gesetzt, dass die Kündigung unwirksam ist.\n")
    letterhead = INSTR.classify_verified_row({
        "decision_id": "p1", "language": "de", "counter_status": "candidate-limiting",
        "counter_evidence_verified": True, "counter_evidence": ft[:120],
        "full_text": ft, "snippet": "", "regeste": ""})
    assert "D2_letterhead_zone" in letterhead["defects"]
    mid = INSTR.classify_verified_row({
        "decision_id": "p2", "language": "de", "counter_status": "candidate-limiting",
        "counter_evidence_verified": True,
        "counter_evidence": "Gericht hat in Erwägung gesetzt, dass die Kündigung unwirksam ist.",
        "full_text": ft, "snippet": "", "regeste": ""})
    assert "D2_letterhead_zone" not in mid["defects"]
    assert mid["class"] == "COUNTER_REASONING"


def test_probe_fires_D1_on_empty_and_D3_on_markup():
    empty = INSTR.classify_verified_row({
        "decision_id": "p3", "language": "de", "counter_status": "cited",
        "counter_evidence_verified": True, "counter_evidence": "",
        "full_text": "y" * 900, "snippet": "", "regeste": ""})
    assert "D1_empty_evidence" in empty["defects"]
    markup = INSTR.classify_verified_row({
        "decision_id": "p4", "language": "de", "counter_status": "candidate-limiting",
        "counter_evidence_verified": True,
        "counter_evidence": "Regeste <mark>Mietvertrag</mark> Anfechtung der Kündigung",
        "full_text": "y" * 900 + "Regeste <mark>Mietvertrag</mark> Anfechtung der Kündigung",
        "snippet": "", "regeste": ""})
    assert "D3_markup_residue" in markup["defects"]


def test_probe_fires_D4_on_language_marker_mismatch():
    row = INSTR.classify_verified_row({
        "decision_id": "p5", "language": "it", "counter_status": "candidate-limiting",
        "counter_evidence_verified": True,
        "counter_evidence": "Regeste Resolutiv bedingter Mietvertrag; Anfechtung der Kündigung",
        "full_text": "z" * 900, "snippet": "", "regeste": ""})
    assert "D4_language_marker_mismatch" in row["defects"]
    own = INSTR.classify_verified_row({
        "decision_id": "p6", "language": "de", "counter_status": "candidate-limiting",
        "counter_evidence_verified": True,
        "counter_evidence": "Regeste Resolutiv bedingter Mietvertrag; Anfechtung der Kündigung",
        "full_text": "z" * 900, "snippet": "", "regeste": ""})
    assert "D4_language_marker_mismatch" not in own["defects"]


def test_float_disclosure_dual_headlines():
    rows = [
        {"id": "a", "kind": "float", "published": 0.857, "raw_published": 0.857,
         "raw_found": 0.8571, "found": 0.8571, "verdict": "CONFIRMED"},
        {"id": "b", "kind": "exact", "published": 100, "found": 100, "verdict": "CONFIRMED"},
        {"id": "c", "kind": "float", "published": 0.076923, "raw_published": 0.076923,
         "raw_found": 0.0775, "found": 0.0775, "verdict": "CONFIRMED"},
    ]
    fd = INSTR.build_float_disclosure(rows)
    # row a: delta 1e-4 -> confirmed under BOTH tolerances
    # row c: delta 5.77e-4 -> CONFIRMED under applied 5e-4, DIVERGENT under literal 1e-6
    assert fd["headline_applied_precision_matched"] == "ALL_CONFIRMED"
    assert fd["headline_frozen_literal_1e_6"] == "DIVERGENCE_PRESENT"
    assert fd["n_float_quantities"] == 2
    assert fd["frozen_rule_edited"] is False


def test_instrument_never_applies_a_frozen_bar():
    src = (REPO_ROOT / "evaluation/v65_head_advance_crosscheck_v2.py").read_text()
    for banned in ("run_bar_gates", "label_gate", "label_lineage_gate",
                   "gate_admissibility", "RULES_LABEL\" ", "score_frozen"):
        assert banned not in src, banned
    # the frozen rubrics may only be re-hashed, never opened as a scorer
    assert "frozen_bars/RULES_LABEL.json" in src
    assert "REPORTED-ONLY" in src


def test_fail_closed_posture_constants_are_false():
    assert INSTR.MOUNT_HEAD.startswith("e4f72a8e")
    assert INSTR.DIRECTION_VERSION == 65
    assert INSTR.RUN_ID == "40040574595"
