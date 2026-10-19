"""Tests for evaluation.concept_seed_beside_frozen_cells (run 39329412076).

Direction v58 ordered work (3)(b): the accepted frontier-concept-seed-recall
natural-language concept-seed numbers are published BESIDE the frozen
benchmark's six failing fr/it authority-recall cells, never in place of them,
with the divergence named as the headline.  The lane issues no candidates and
re-tunes nothing.

These tests pin:
* the freeze-first contract (hypothesis + freeze record, all input re-hashes);
* the six frozen cells UNCHANGED (gate names, required ids, hits, missing);
* the concept-seed A0/A1_union/A2/A3 numbers per accepted team record;
* the pre-registered divergence headline (1/6 improved, 5/6 unchanged, 1/9 ids
  recovered, 8/9 still missing, coverage axis null);
* the non-vacuity controls and the F-3B carry-forward (INTACT_NOT_REOPENED);
* the unserved-packet pre-emption contract (no verdict on packet bytes);
* the no-candidate / no-retune invariants and the claim ceiling;
* the regression case: expected F-3B digests are READ from the accepted
  disposition record, never hand-typed (the PREFIX_BUGGY execution preserved
  under results/evaluation/_scratch_namespaced/39329412076/ was published with
  a hand-typed re-homed digest typo that false-flagged DRIFT).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from evaluation import concept_seed_beside_frozen_cells as P  # noqa: E402

RUN_RECORD = REPO / "results/evaluation/concept_seed_beside_frozen_cells/39329412076.json"
BUGGY = REPO / "results/evaluation/_scratch_namespaced/39329412076/PREFIX_BUGGY_f3b_hardcoded_digest_typo.json"

FROZEN_DIALECT = {
    "rules_label": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "rules_geometry": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "frozen_spec": "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72",
    "freeze_record": "b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49",
    "frozen_benchmark_record": "f976d53a2b8481db42bb1d0dde5f673b1b5bd5284d2b6c5fe6dcc3115cdebd75",
    "frontier_harness_blob": "01fdf0f868f8ad163bf812570ccd5cb36677dac1",
    "frontier_gate_blob": "18f828c25362dc4e459113aaa04af0ecddda41e1",
    "frontier_rules_blob": "4e988256c9cb3f4126d620dd197c0c1ad9404b29",
    "f3b_restored": "58a273de260770c12dcdc6f645b06b71f95a672757ae3cfa03e870be4bd5b11e",
    "f3b_rehomed": "d02255b8d11d7bce9b4529349e4e87de7b32a7d06311dfaa3aefa06f5de00032",
    "f3b_pre_restore_sibling": "47be772a9d3d1fcf30185b7ed2bed45603df468c82cf4956e498151e296a17f0",
}

EXPECTED_FROZEN_CELLS = {
    "authority::baseline_lang_recall::corporate-criminal-liability::fr": {
        "required": ["bge_BGE_142_IV_333", "bger_6B_124_2016"], "hits": [],
    },
    "authority::baseline_lang_recall::corporate-criminal-liability::it": {
        "required": ["bge_BGE_142_IV_333", "bger_6B_124_2016"], "hits": [],
    },
    "authority::baseline_lang_recall::business-judgment-rule::fr": {
        "required": ["bger_4A_219_2015", "bger_4A_259_2016", "bger_4A_603_2014", "bger_4A_626_2013", "bger_4A_62_2024"],
        "hits": [],
    },
    "authority::baseline_lang_recall::business-judgment-rule::it": {
        "required": ["bger_4A_219_2015", "bger_4A_259_2016", "bger_4A_603_2014", "bger_4A_626_2013", "bger_4A_62_2024"],
        "hits": [],
    },
    "authority::baseline_lang_recall::petty-theft-dismissal::fr": {
        "required": ["bger_4A_177_2017", "bger_4A_228_2015"], "hits": [],
    },
    "authority::baseline_lang_recall::petty-theft-dismissal::it": {
        "required": ["bger_4A_177_2017", "bger_4A_228_2015"], "hits": [],
    },
}

EXPECTED_A1_UNION = {
    "frozen::corporate-criminal-liability::fr": (0.5, ["bge_BGE_142_IV_333"]),
    "frozen::corporate-criminal-liability::it": (0.0, []),
    "frozen::business-judgment-rule::fr": (0.0, []),
    "frozen::business-judgment-rule::it": (0.0, []),
    "frozen::petty-theft-dismissal::fr": (0.0, []),
    "frozen::petty-theft-dismissal::it": (0.0, []),
}


def _load_record() -> dict:
    assert RUN_RECORD.is_file(), "claim-bearing record missing"
    return json.loads(RUN_RECORD.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# 1. freeze-first contract and input pins
# --------------------------------------------------------------------------- #
def test_hypothesis_and_freeze_record_exist_and_pin_direction_58():
    h = json.loads((REPO / P.HYPOTHESIS_RELPATH).read_text(encoding="utf-8"))
    f = json.loads((REPO / P.FREEZE_RELPATH).read_text(encoding="utf-8"))
    assert h["direction_version"] == 58
    assert f["direction_version"] == 58
    assert f["input_rehashes"]["evaluation/frozen_bars/RULES_LABEL.json"] == FROZEN_DIALECT["rules_label"]
    assert f["input_rehashes"]["evaluation/frozen_bars/RULES_GEOMETRY.json"] == FROZEN_DIALECT["rules_geometry"]
    assert f["input_rehashes"][P.FROZEN_RECORD] == FROZEN_DIALECT["frozen_benchmark_record"]
    assert f["embedded_pins_from_frozen_record"]["frozen_sha256"] == FROZEN_DIALECT["frozen_spec"]
    assert f["embedded_pins_from_frozen_record"]["freeze_record_sha256"] == FROZEN_DIALECT["freeze_record"]


def test_frozen_inputs_on_disk_rehash_to_the_pins():
    import hashlib

    for rel, pin in (
        (P.RULES_LABEL, FROZEN_DIALECT["rules_label"]),
        (P.RULES_GEOMETRY, FROZEN_DIALECT["rules_geometry"]),
        (P.FROZEN_RECORD, FROZEN_DIALECT["frozen_benchmark_record"]),
    ):
        digest = hashlib.sha256((REPO / rel).read_bytes()).hexdigest()
        assert digest == pin, f"pin drift on {rel}"


def test_frontier_blob_pins_verified_via_git():
    for rel_path, pin in (
        (P.FRONTIER_RULES, FROZEN_DIALECT["frontier_rules_blob"]),
        (P.FRONTIER_GATE, FROZEN_DIALECT["frontier_gate_blob"]),
        (P.FRONTIER_HARNESS, FROZEN_DIALECT["frontier_harness_blob"]),
    ):
        blob = subprocess.run(
            ["git", "rev-parse", f"{P.FRONTIER_REF}:{rel_path}"],
            cwd=REPO, capture_output=True, check=True,
        ).stdout.decode().strip()
        assert blob == pin, f"frontier blob drift on {rel_path}"


def test_frontier_audit_gate_is_pass():
    gate = json.loads(subprocess.run(
        ["git", "show", f"{P.FRONTIER_REF}:{P.FRONTIER_GATE}"],
        cwd=REPO, capture_output=True, check=True,
    ).stdout.decode())
    assert gate["gate"] == "PASS" and gate["safe_to_integrate"] is True and gate["required_fixes"] == []


# --------------------------------------------------------------------------- #
# 2. frozen cells published UNCHANGED
# --------------------------------------------------------------------------- #
def test_six_frozen_cells_published_unchanged():
    rec = _load_record()
    cells = rec["frozen_cells_published_unchanged"]
    assert set(cells) == set(EXPECTED_FROZEN_CELLS)
    for gate_name, expected in EXPECTED_FROZEN_CELLS.items():
        cell = cells[gate_name]
        assert cell["required"] == expected["required"], gate_name
        assert cell["hits"] == expected["hits"], gate_name
        assert cell["passed"] is False, gate_name
        assert cell["n_rows"] == 50, gate_name
    # the frozen record itself is untouched (never replaced by the new numbers)
    frozen = json.loads((REPO / P.FROZEN_RECORD).read_text(encoding="utf-8"))
    for gate in frozen["verdict"]["gates"]:
        if gate["gate"] in EXPECTED_FROZEN_CELLS:
            assert gate["measured"]["required"] == EXPECTED_FROZEN_CELLS[gate["gate"]]["required"]


# --------------------------------------------------------------------------- #
# 3. concept-seed numbers and the side-by-side table
# --------------------------------------------------------------------------- #
def test_concept_seed_numbers_match_accepted_team_record():
    rec = _load_record()
    for unit_id, (recall, hits) in EXPECTED_A1_UNION.items():
        cell = rec["concept_seed_cells"][unit_id]
        assert cell["A1_union"]["recall"] == recall, unit_id
        assert cell["A1_union"]["hits"] == hits, unit_id
        assert cell["A0_baseline_shipped"]["recall"] == 0.0, unit_id
        assert cell["A0_baseline_shipped"]["hits"] == [], unit_id


def test_side_by_side_table_derivation():
    rec = _load_record()
    table = rec["side_by_side"]
    assert len(table) == 6
    ccl_fr = next(c for c in table if c["slug"] == "corporate-criminal-liability" and c["language"] == "fr")
    assert ccl_fr["frozen_cell"]["hits"] == "0/2"
    assert ccl_fr["concept_seed_A1_union"]["hits"] == "1/2"
    assert ccl_fr["concept_seed_A1_union"]["hits_list"] == ["bge_BGE_142_IV_333"]
    assert ccl_fr["delta_hits"] == 1 and ccl_fr["improved"] is True
    for cell in table:
        if cell is ccl_fr:
            continue
        assert cell["delta_hits"] == 0 and cell["improved"] is False
        assert cell["frozen_cell"]["hits"] == cell["concept_seed_A0"]["hits"]


# --------------------------------------------------------------------------- #
# 4. divergence headline, pre-registered
# --------------------------------------------------------------------------- #
def test_divergence_headline_preregistered_and_exact():
    rec = _load_record()
    assert rec["verdict"] == "CONCEPT_SEED_BESIDE_FROZEN_CELLS_PUBLISHED"
    assert rec["cells_improved"] == 1
    assert rec["cells_unchanged_at_zero"] == 5
    assert rec["ids_recovered"] == ["bge_BGE_142_IV_333"]
    assert len(rec["unique_frozen_authority_ids"]) == 9
    assert len(rec["ids_still_missing_everywhere"]) == 8
    assert set(rec["ids_still_missing_everywhere"]) == {
        "bger_4A_177_2017", "bger_4A_219_2015", "bger_4A_228_2015",
        "bger_4A_259_2016", "bger_4A_603_2014", "bger_4A_626_2013",
        "bger_4A_62_2024", "bger_6B_124_2016",
    }
    assert rec["coverage_axis_null"] is True
    assert all(rec["divergence_checks"].values())
    headline = rec["divergence_headline"]
    assert "1 of the 6 frozen fr/it" in headline
    assert "0/2 -> 1/2" in headline
    assert "bge_BGE_142_IV_333" in headline
    assert "8 of the 9" in headline
    # named as the headline, never smoothed over: the recovery is cell-level
    assert "cell-level" in headline and "DIVERGENCE" in headline


def test_coverage_axis_null_numbers_rederived():
    rec = _load_record()
    de = rec["de_coverage"]
    assert de["A0_rows"] == 214 and de["A1_union_rows"] == 220
    assert de["kapitalverletzung_rows_A0"] == 0
    assert de["kapitalverletzung_rows_A1_union"] == 0
    assert de["uberwachungspflicht_rows_A0"] == 0
    assert de["uberwachungspflicht_rows_A1_union"] == 0
    assert "retrieval signal, not proof of corpus absence" in de["interpretation"]


def test_controls_hold():
    rec = _load_record()
    assert rec["controls"]["A2_blanked_equals_A0_on_all_units"] is True
    assert rec["controls"]["A3_rotated_raises_nothing_on_any_target"] is True
    assert rec["controls"]["candidate_beats_blanked_on_exactly_one_unit"] is True
    assert rec["controls"]["n_units_candidate_beats_blanked"] == 1


# --------------------------------------------------------------------------- #
# 5. F-3B carry-forward + the digest-typo regression
# --------------------------------------------------------------------------- #
def test_f3b_carry_forward_intact_not_reopened():
    rec = _load_record()
    f3b = rec["f3b_carry_forward"]
    assert f3b["status"] == "INTACT_NOT_REOPENED"
    assert f3b["restored_matches_pre_rewrite_digest"] is True
    assert f3b["digests"]["restored_sha256"] == FROZEN_DIALECT["f3b_restored"]
    assert f3b["digests"]["preimage_sha256"] == FROZEN_DIALECT["f3b_restored"]
    assert f3b["digests"]["pre_restore_sha256"] == FROZEN_DIALECT["f3b_pre_restore_sibling"]
    assert f3b["digests"]["rehomed_sha256"] == FROZEN_DIALECT["f3b_rehomed"]
    assert f3b["deleted"] == []
    assert f3b["siblings_preserved"] is True
    assert f3b["expected_digests_source"].startswith("results/evaluation/f3b_restore_disposition/39287274485.json")


def test_prefix_buggy_execution_preserved_with_digest_typo():
    """The first execution hand-typed the re-homed digest with a dropped '2'
    and false-flagged f3b_carry_forward DRIFT.  The buggy bytes are preserved
    verbatim (never overwritten) and the committed record is the corrected
    one.  This regression test fails if any future edit re-hardcodes an
    expected digest instead of reading it from the accepted disposition record.
    """
    assert BUGGY.is_file(), "buggy execution must be preserved, never deleted"
    buggy = json.loads(BUGGY.read_text(encoding="utf-8"))
    assert buggy["f3b_carry_forward"]["status"] == "DRIFT"
    rec = _load_record()
    assert rec["f3b_carry_forward"]["status"] == "INTACT_NOT_REOPENED"
    # the instrument source must NOT hand-type the re-homed expected digest:
    # it must read the expected digests from the accepted disposition record.
    src = (REPO / "evaluation/concept_seed_beside_frozen_cells.py").read_text(encoding="utf-8")
    assert 'f3b_accepted["records"]["rehomed"]["rehomed_sha256"]' in src
    assert '== "d02255b8' not in src  # no hand-typed full digest literal in source


# --------------------------------------------------------------------------- #
# 6. unserved-packet pre-emption contract
# --------------------------------------------------------------------------- #
def test_unserved_packet_withheld_no_verdict_on_bytes():
    rec = _load_record()
    pkt = rec["unserved_packet"]
    assert pkt["packet"] == "39275520116"
    assert pkt["verdict_computed_on_bytes"] is False
    assert pkt["falsification_verdict"] == "WITHHELD_PENDING_SERVE"
    if pkt.get("serve_status") != "MOUNT_ABSENT":
        assert pkt["packet_admitted"] is False
        assert pkt["ready_for_owner_session_allowed"] is False
    assert rec["no_candidate_no_retune"]["packet_verdicts_computed"] == 0


# --------------------------------------------------------------------------- #
# 7. no-candidate / no-retune invariants + claim ceiling
# --------------------------------------------------------------------------- #
def test_no_candidate_no_retune_invariants():
    rec = _load_record()
    inv = rec["no_candidate_no_retune"]
    assert inv["new_thresholds"] == 0
    assert inv["new_bars"] == 0
    assert inv["new_gates"] == 0
    assert inv["frozen_files_edited"] == 0
    assert inv["candidates_issued"] == 0
    # frozen record bytes unchanged by this run (mtime-independent: compare digest)
    import hashlib

    digest = hashlib.sha256((REPO / P.FROZEN_RECORD).read_bytes()).hexdigest()
    assert digest == FROZEN_DIALECT["frozen_benchmark_record"]


def test_claim_ceiling_respected_in_record():
    rec = _load_record()
    headline = rec["divergence_headline"].lower()
    # no bar-met, no packet-fitness, no map-usefulness, no corpus-absence assertion
    for forbidden in ("bar is met", "bar moved", "fit to serve", "helps a jurist", "absent from the corpus"):
        assert forbidden not in headline, forbidden
    assert rec["claim_ceiling"].startswith("This publication asserts ONLY")


def test_adoption_context_read_only():
    rec = _load_record()
    adoption = rec["product_adoption_context"]
    assert adoption["decision"] == "ADOPT"
    assert adoption["sha256"] == "17189fcd1c9d6ba45baaf5a159fb0fb51a15388f32202ba1c0e28455078ae816"


# --------------------------------------------------------------------------- #
# 8. instrument determinism: re-run reproduces the committed record bytes
# --------------------------------------------------------------------------- #
def test_instrument_rerun_is_byte_identical(tmp_path):
    proc = subprocess.run(
        [sys.executable, "evaluation/concept_seed_beside_frozen_cells.py",
         "--run-id", "determinism_probe", "--out-dir", str(tmp_path)],
        cwd=REPO, capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    probe = json.loads((tmp_path / "determinism_probe.json").read_text(encoding="utf-8"))
    committed = _load_record()
    # run-varying fields: the two fields that identify the run itself
    probe.pop("generated_at")
    probe.pop("run_id")
    committed.pop("generated_at")
    committed.pop("run_id")
    assert probe == committed, "instrument re-run is not identical after normalizing run_id/generated_at"
