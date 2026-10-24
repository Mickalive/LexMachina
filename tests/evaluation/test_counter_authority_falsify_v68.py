#!/usr/bin/env python3
"""Pytest tests for the v68 counter-authority falsifier.
Reuses the ACCEPTED ``evaluation.counter_authority_surface_falsifier`` module
unchanged.  No new thresholds, gates, tokenisers, rubrics or stoplists.
No universal-174k benchmark rerun.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from evaluation import counter_authority_surface_falsifier as C  # noqa: E402
from evaluation import mapping_free_recall_falsifier as M  # noqa: E402

MOUNT = Path("/tmp/lex_accepted/product")
needs_mount = pytest.mark.skipif(not MOUNT.is_dir(), reason="no accepted product mount")

PACKET_OF_RECORD = "39319405429"
PACKET_JSON_SHA = "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70"
FROZEN_SPEC_SHA = "187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72"
RULES_LABEL_SHA = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
RULES_GEOMETRY_SHA = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"


# --------------------------------------------------------------------------- #
# 1. freeze-first artifacts
# --------------------------------------------------------------------------- #
def test_hypothesis_is_committed_and_pins_the_packet_of_record():
    h = json.loads((REPO / C.HYPOTHESIS_RELPATH).read_text(encoding="utf-8"))
    assert h["frozen_before_execution"] is True
    assert h["inputs_FROZEN"]["packet_of_record"]["id"] == PACKET_OF_RECORD
    assert h["inputs_FROZEN"]["packet_of_record"]["packet_json_sha256"] == PACKET_JSON_SHA
    # no new thresholds / no new gates
    assert h["no_new_thresholds"].startswith("Every numeric threshold")
    assert "introduces NO new threshold" in h["no_new_thresholds"]


def test_freeze_record_pins_v3_and_the_frozen_repo_inputs():
    f = json.loads((REPO / C.FREEZE_RELPATH).read_text(encoding="utf-8"))
    assert f["instrument_sha256"] == C._sha256_file(REPO / "evaluation" / "counter_authority_surface_falsifier.py")
    mount = f["frozen_mount_input_digests_before_execution"]
    assert mount["results/product/gate_packet/39319405429/packet.json"] == PACKET_JSON_SHA
    repo = f["frozen_repo_input_digests_before_execution"]
    assert repo["evaluation/frozen_bars/RULES_LABEL.json"] == RULES_LABEL_SHA
    assert repo["evaluation/frozen_bars/RULES_GEOMETRY.json"] == RULES_GEOMETRY_SHA
    # the instrument reuses the accepted measurement module, byte-pinned
    assert repo["evaluation/mapping_free_recall_falsifier.py"] == \
        C._sha256_file(REPO / "evaluation" / "mapping_free_recall_falsifier.py")


def test_frozen_bars_are_never_regenerated():
    # the frozen bars on disk still carry the accepted direction-v61 digests
    assert C._sha256_file(REPO / "evaluation" / "frozen_bars" / "RULES_LABEL.json") == RULES_LABEL_SHA
    assert C._sha256_file(REPO / "evaluation" / "frozen_bars" / "RULES_GEOMETRY.json") == RULES_GEOMETRY_SHA


def test_direction_version_is_derived_from_state_not_hardcoded():
    state = json.loads((REPO / "state" / "evaluation.json").read_text(encoding="utf-8"))
    assert C._current_direction_version() == int(state["direction_version"])


# --------------------------------------------------------------------------- #
# 2. reuse contract: the instrument re-uses the accepted measurement, adds no gate
# --------------------------------------------------------------------------- #
def test_instrument_delegates_to_the_accepted_measurement_module():
    assert C.M.measure is M.measure
    assert C.M.non_vacuity is M.non_vacuity
    assert C.M.verdict_of is M.verdict_of
    # exit-code contract is imported, so the two instruments cannot drift
    assert C.EXIT_PASS == M.EXIT_PASS
    assert C.EXIT_FALSIFIED == M.EXIT_FALSIFIED
    assert C.EXIT_VACUOUS == M.EXIT_VACUOUS
    src = (REPO / "evaluation" / "counter_authority_surface_falsifier.py").read_text(encoding="utf-8")
    # no re-derived gate vocabulary: the instrument never names a counter status
    assert "candidate-limiting" not in src
    assert "candidate-contrary" not in src


def test_claim_ceiling_denies_everything_the_direction_denies():
    c = C.CLAIM_CEILING
    for phrase in ("DO-NOT-SERVE", "REPORTED-ONLY", "human_gate_ready stays false",
                   "admission stays fail-closed", "frontier-counter-label-emission",
                   "universal-174k"):
        assert phrase in c


# --------------------------------------------------------------------------- #
# 3. mount-independent gate behaviour (reuses the accepted predicates)
# --------------------------------------------------------------------------- #
def test_counter_authority_surface_gate_detects_empty_and_populated():
    # empty surface: the product cannot surface contrary authority
    empty = M.counter_authority_surface({"decisions": [
        {"decision_id": "a_1", "counter_status": "none", "counter_evidence": ""}]},
        ["candidate-limiting", "candidate-contrary"])
    assert empty["n_issued"] == 0
    # populated surface with evidence: the gate can go green (non-vacuous)
    ok = M.counter_authority_surface({"decisions": [
        {"decision_id": "a_1", "counter_status": "candidate-limiting", "counter_evidence": "x"}]},
        ["candidate-limiting", "candidate-contrary"])
    assert ok["n_issued"] == 1 and ok["n_with_empty_evidence"] == 0
    # populated surface with empty evidence: still fails the gate
    bad = M.counter_authority_surface({"decisions": [
        {"decision_id": "a_1", "counter_status": "candidate-contrary", "counter_evidence": ""}]},
        ["candidate-limiting", "candidate-contrary"])
    assert bad["n_issued"] == 1 and bad["n_with_empty_evidence"] == 1


def test_non_vacuity_battery_is_reused_unchanged():
    def entry(qid: str, question: str, rows: list[dict]) -> dict:
        qrec = {"question": question}
        return {"qid": qid, "question_record": qrec,
                "coverage": M.concept_coverage(qrec, {"decisions": rows})}

    questions = [
        entry("q1", "Kapitalverletzung der Bank", [{"title": "etwas", "decision_id": "a_1"}]),
        entry("q2", "Responsabilita medica del medico",
              [{"title": "Responsabilita medica del medico", "decision_id": "b_1"}]),
    ]
    res = M.non_vacuity(questions, ["candidate-limiting"])
    assert res["all_hold"] is True
    assert {c["control"] for c in res["battery"]} >= {
        "A_blanked_pool_must_fail_concept_coverage",
        "A2_blanked_row_must_fail_source_validity",
        "C_oracle_pool_must_pass_concept_coverage",
        "B_admissibility_predicate_must_reject_a_subject_swapped_pair",
    }


def test_entry_point_exits_two_without_a_mount(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "resolve_mount", lambda explicit=None: None)
    code = C.main(["--run-id", "t", "--out", str(tmp_path / "r.json")])
    assert code == 2
    rec = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert rec["verdict"] == "NOT_MEASURED_VACUOUS"
    assert rec["exit_code"] == 2


# --------------------------------------------------------------------------- #
# 4. mount-dependent end-to-end: V3's exact bytes
# --------------------------------------------------------------------------- #
@needs_mount
def test_v3_measure_is_deterministic():
    a = M.measure(MOUNT, REPO, (PACKET_OF_RECORD,))
    b = M.measure(MOUNT, REPO, (PACKET_OF_RECORD,))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert len(a["questions"]) == 3
    assert a["spec_sha256"] == FROZEN_SPEC_SHA
    assert a["rules_label_sha256"] == RULES_LABEL_SHA


@needs_mount
def test_v3_end_to_end_falsifies_the_product(tmp_path):
    out = tmp_path / "v3.json"
    code, rec = C.run("t", out, None, REPO, (PACKET_OF_RECORD,))
    assert code == 1 and rec["verdict"] == "PRODUCT_FALSIFIED"
    assert rec["direction_version"] == int(
        (REPO / "state" / "evaluation.json").read_text(encoding="utf-8"))["direction_version"]
    assert rec["input_drift"] == [] and rec["input_drift_invalidates_run"] is False
    assert rec["non_vacuity"]["all_hold"] is True
    assert rec["n_gates"] == rec["n_passed"] + rec["n_failed"] + rec["n_reported"]
    # the packet of record's counter-authority surface is empty on every question
    failed = {g["gate"] for g in rec["failed_gates"]}
    assert "mf::counter_authority_surface::39319405429::de-kapitalverletzung" in failed
    assert "mf::counter_authority_surface::39319405429::fr-bail-entretien" in failed
    assert "mf::counter_authority_surface::39319405429::it-responsabilita-medica" in failed
    # the frozen slug->question admissibility predicate admits exactly one pair
    assert rec["admissibility"]["n_pairs_enumerated"] == 12
    assert rec["admissibility"]["n_pairs_admissible"] == 1
    # fail-closed flags
    assert rec["human_gate_ready"] is False and rec["packet_admitted"] is False
    assert rec["machine_gate_ready"] is False and rec["ready_for_owner_session"] is False
    assert rec["owner_decision_required"] is False


@needs_mount
def test_committed_v3_record_reproduces_from_the_committed_tree(tmp_path):
    # Ensure the v68 record exists and is committed
    committed = REPO / "results" / "evaluation" / "counter_authority_falsify_v68" / "68.json"
    if not committed.is_file():
        pytest.skip("v68 committed record not present yet")
    published = json.loads(committed.read_text(encoding="utf-8"))
    out = tmp_path / "replay.json"
    code, rec = C.run("t", out, None, REPO, (PACKET_OF_RECORD,))
    assert code == published["exit_code"]
    assert rec["verdict"] == published["verdict"]
    assert rec["n_gates"] == published["n_gates"]
    assert rec["n_failed"] == published["n_failed"]
    assert rec["failed_gates"] == published["failed_gates"]
    assert rec["admissibility"]["n_pairs_admissible"] == published["admissibility"]["n_pairs_admissible"]
    assert rec["input_drift"] == published["input_drift"]
