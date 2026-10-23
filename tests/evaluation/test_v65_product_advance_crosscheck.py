"""Tests for the v65 product-advance currency cross-check of run 40012474431.

This test module is the committed re-derivation shim for
``evaluation/v65_product_advance_crosscheck.py`` (instrument of record for the
operational-resume work executed under the rc-67 diagnosis of runs 40006151200
/ 40011795717).  It does NOT re-execute the falsification benchmark or the
planner; it re-derives, from the committed artifacts, every claim the cycle's
verdict rests on, with an independent code path (no import of the instrument
under test for the quantity arithmetic).

SCOPE / NON-WEAKENING CONTRACT
--------------------------------
* No frozen rule, rubric, bar, threshold or success rule is re-derived, edited
  or re-scored here — the hypothesis and frozen rules are only RE-HASHED.
* No falsification is re-executed by these tests; the committed falsification
  record's outcomes are asserted unchanged (set equality against the accepted
  failed-gate set of run 39986080045).
* Mount-dependent byte recomputation skips with an explicit reason when the
  ephemeral product mount ``/tmp/lex_accepted/product`` is absent (never a
  silent pass); the mount-free tests still pin every committed claim.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
RUN_ID = "40012474431"
OUT_DIR = REPO / "results/evaluation/v65_product_advance_crosscheck"
RUN_JSON = OUT_DIR / f"{RUN_ID}.json"
FALSIFICATION_JSON = OUT_DIR / f"falsification/{RUN_ID}.json"
MULTILINGUAL_JSON = OUT_DIR / f"{RUN_ID}_multilingual_provenance_reuse.json"
HYPOTHESIS_JSON = REPO / "evaluation/V65_PRODUCT_ADVANCE_CROSSCHECK_HYPOTHESIS_V1.json"
FREEZE_JSON = REPO / "evaluation/V65_PRODUCT_ADVANCE_CROSSCHECK_FREEZE_RECORD_V1.json"
INSTRUMENT = REPO / "evaluation/v65_product_advance_crosscheck.py"
MOUNT = Path("/tmp/lex_accepted/product")

ACCEPTED_FAILED_GATES = {
    "mf::concept_coverage::39319405429::de-kapitalverletzung",
    "mf::counter_authority_surface::39319405429::de-kapitalverletzung",
    "mf::counter_authority_surface::39319405429::fr-bail-entretien",
    "mf::counter_authority_surface::39319405429::it-responsabilita-medica",
}

EXPECTED = {
    "rules_label": "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608",
    "rules_geometry": "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633",
    "packet_json": "32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70",
    "planner": "9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9",
    "mount_head": "f9618377f67d8a79205fab86646d724f9739a339",
    "hypothesis": "9382a0a9a666a2e883a5c9590efd8c3759707c223f228cd4d9447889dc97b9f6",
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture(scope="module")
def record() -> dict:
    assert RUN_JSON.exists(), f"missing committed record {RUN_JSON}"
    return json.loads(RUN_JSON.read_text())


# ---------------------------------------------------------------------------
# 1. Verdict contract of the committed record
# ---------------------------------------------------------------------------

def test_record_identity_and_schema(record):
    assert record["run_id"] == RUN_ID
    assert record["direction_version"] == 65
    assert record["schema"].startswith("lex-evaluation-v65-product-advance-crosscheck")


def test_verdict_contract_exit0_means_pass_no_falsification(record):
    """exit 0 ⇔ PASS_NO_FALSIFICATION ⇔ 0 applied-tolerance divergences and a
    reproduced falsification verdict."""
    assert record["verdict"] == "PASS_NO_FALSIFICATION"
    assert record["exit_code"] == 0
    cc = record["currency_crosscheck"]
    assert cc["headline"] == "ALL_CONFIRMED"
    assert cc["n_divergent"] == 0
    assert cc["n_not_found"] == 0
    assert cc["n_quantities"] == 57
    assert cc["n_confirmed"] + cc["n_divergent"] + cc["n_not_found"] == cc["n_quantities"]
    fr = record["falsification_rerun"]
    assert fr["executed"] is True
    assert fr["verdict"] == "PRODUCT_FALSIFIED"


def test_coverage_v2_refreeze_not_executed(record):
    cv2 = record["coverage_v2_refreeze"]
    assert cv2["executed"] is False
    assert "NOT resumed" in cv2["reason"]


def test_claim_ceiling_is_currency_only(record):
    ceiling = record["claim_ceiling"]
    assert "scores no frozen bar" in ceiling
    assert record["posture_unchanged"]["human_gate_ready"] is False
    assert record["posture_unchanged"]["machine_gate_ready"] is False
    assert record["posture_unchanged"]["packet_admitted"] is False


# ---------------------------------------------------------------------------
# 2. Dual float convention (frozen exception D-A of run 39986080045)
# ---------------------------------------------------------------------------

def test_dual_float_convention_both_verdicts_published(record):
    fd = record["currency_crosscheck"]["float_comparison_disclosure"]
    assert fd["frozen_literal_tolerance"] == 1e-6
    assert fd["applied_tolerance"] == 5e-4
    assert fd["frozen_rule_edited"] is False
    assert fd["both_verdicts_published_per_float_quantity"] is True
    assert fd["n_float_quantities"] == len(fd["float_quantities"]) == 13
    # strict headline admits the 3-decimal publication-precision divergences;
    # applied headline is the one the verdict is based on.
    assert fd["headline_frozen_literal_1e_6"] == "DIVERGENCE_PRESENT"
    assert fd["counts_frozen_literal_1e_6"] == {
        "n_confirmed": 54, "n_divergent": 2, "n_not_found": 0}
    assert fd["headline_applied_precision_matched"] == "ALL_CONFIRMED"
    assert fd["counts_applied_precision_matched"] == {
        "n_confirmed": 57, "n_divergent": 0, "n_not_found": 0}


def test_strict_divergences_are_exactly_the_two_known_rounded_floats(record):
    fd = record["currency_crosscheck"]["float_comparison_disclosure"]
    strict_div = [q for q in fd["float_quantities"]
                  if q.get("strict_verdict_1e_6") == "DIVERGENT"]
    assert len(strict_div) == 2
    ids = {q["id"] for q in strict_div}
    assert ids == {
        "reliability_40000001926_ready_rate",
        "reliability_40000001926_prose_citation_validity",
    }
    for q in strict_div:
        # both are the frozen 3-decimal publication-precision artefacts
        assert q["applied_verdict_precision_matched"] == "CONFIRMED"
        assert 1e-6 < q["abs_delta"] <= 5e-4


# ---------------------------------------------------------------------------
# 3. Frozen exception class: correction_landed (kind=correction_landed)
# ---------------------------------------------------------------------------

def test_correction_landed_row_confirmed_corrected_with_both_arms(record):
    rows = {r["id"]: r for r in record["currency_crosscheck"]["rows"]}
    row = rows["span_selection_39986094168_report_arm_label_correction_landed"]
    assert row["verdict"] == "CONFIRMED_CORRECTED"
    found = row["found"]
    assert found["guarded_n_emitted"] == 1
    assert found["guarded_yield"] == 0.05
    assert found["unguarded_n_emitted"] == 6
    assert found["unguarded_yield"] == 0.3
    assert found["report_labels_6_as_candidate"] is True
    assert found["correction_phrase_present"] is True
    assert record["currency_crosscheck"]["n_corrected_disclosed"] == 1


# ---------------------------------------------------------------------------
# 4. Falsification re-run reproduces the accepted failed-gate set exactly
# ---------------------------------------------------------------------------

def test_falsification_identical_to_accepted_failed_gates(record):
    fr = record["falsification_rerun"]
    assert fr["exit_code"] == 1
    assert fr["verdict"] == "PRODUCT_FALSIFIED"
    assert set(fr["failed_gates"]) == ACCEPTED_FAILED_GATES
    assert fr["failed_gates_equals_accepted"] is True
    assert fr["input_drift"] == []
    assert fr["n_questions_measured"] == 3
    # frozen pins of the benchmark inputs (packet bytes unchanged on the mount)
    assert record["pins_before"]["mount:results/product/gate_packet/39319405429/packet.json"] == \
        EXPECTED["packet_json"]
    assert record["pins_after"]["mount:results/product/gate_packet/39319405429/packet.json"] == \
        EXPECTED["packet_json"]


def test_falsification_artifacts_exist_and_agree(record):
    assert FALSIFICATION_JSON.exists()
    committed = json.loads(FALSIFICATION_JSON.read_text())
    fr = record["falsification_rerun"]
    assert committed["verdict"] == fr["verdict"]
    committed_gates = {g["gate"] if isinstance(g, dict) else g
                       for g in committed["failed_gates"]}
    assert committed_gates == ACCEPTED_FAILED_GATES


# ---------------------------------------------------------------------------
# 5. Planner pin, degradation pin, requirement-4 lineage, controls
# ---------------------------------------------------------------------------

def test_planner_pin_confirmed_with_pipeline_drift_disclosed(record):
    pp = record["planner_and_degradation_pin"]
    assert pp["overall"] == "CONFIRMED"
    assert pp["product_pins_drift_disclosed"] is True
    diverged = {c["relpath"]: (c["expected"], c["found"])
                for c in pp["findings"]["frozen_product_pins_rehash"]["diverged_pins"]}
    # exactly one disclosed product-advance drift (pipeline.py), never silent
    assert set(diverged) == {"product/query/pipeline.py"}
    expected, found = diverged["product/query/pipeline.py"]
    assert expected.startswith("e105bfed")
    assert found.startswith("265b82ac")
    assert expected != found


def test_requirement_4_lineage_all_accepted(record):
    lin = record["requirement_4_lineage"]
    assert lin["all_accepted"] is True
    assert lin["40000001926"]["requirement_4_both_halves"] is True
    assert lin["40005362253"]["requirement_4_both_halves"] is True


def test_controls_all_passed(record):
    c = record["controls"]
    assert c["C1_planted_currency_divergence_is_detected"]["passed"] is True
    assert c["C1_planted_currency_divergence_is_detected"]["detected_as_divergent"] is True
    assert c["C2_frozen_rules_rehash_holds"]["passed"] is True
    assert c["C3_packet_bytes_unchanged"]["passed"] is True
    assert record["control_failures"] == []


def test_resume_lineage_points_at_rc67_diagnosis(record):
    rl = record["resume_lineage"]
    assert rl["prior_resumed_run"] == "40006151200"
    assert rl["resumed_run"] == "40011795717"
    assert "rc 67" in rl["failure_class"]
    assert (REPO / rl["diagnosis_artifact"]).exists()


# ---------------------------------------------------------------------------
# 6. Freeze-first pin re-hash (hypothesis + frozen rules, repo-side)
# ---------------------------------------------------------------------------

def test_hypothesis_digest_matches_freeze_record_pin(record):
    assert _sha256_file(HYPOTHESIS_JSON) == EXPECTED["hypothesis"]
    freeze = json.loads(FREEZE_JSON.read_text())
    assert record["pins_before"][
        "repo:evaluation/V65_PRODUCT_ADVANCE_CROSSCHECK_HYPOTHESIS_V1.json"] == EXPECTED["hypothesis"]
    pin = freeze.get("hypothesis_sha256") or freeze.get("pins", {}).get("hypothesis")
    assert pin == EXPECTED["hypothesis"]


def test_frozen_rules_rehash_repo_side(record):
    assert _sha256_file(REPO / "evaluation/frozen_bars/RULES_LABEL.json") == EXPECTED["rules_label"]
    assert _sha256_file(REPO / "evaluation/frozen_bars/RULES_GEOMETRY.json") == EXPECTED["rules_geometry"]
    assert record["pins_before"]["repo:evaluation/frozen_bars/RULES_LABEL.json"] == EXPECTED["rules_label"]
    assert record["pins_before"]["repo:evaluation/frozen_bars/RULES_GEOMETRY.json"] == EXPECTED["rules_geometry"]


def test_pins_before_equal_pins_after(record):
    # no input mutated the pins between freeze and run
    assert record["pins_before"] == record["pins_after"]
    assert record["input_drift"] == []


def test_instrument_is_new_file_not_prior_pinned_instrument():
    """The prior accepted instrument must remain byte-identical (never edited)."""
    prior = REPO / "evaluation/v65_currency_crosscheck.py"
    assert prior.exists()
    # new instrument exists and is distinct
    assert INSTRUMENT.exists()
    assert _sha256_file(INSTRUMENT) != _sha256_file(prior)


# ---------------------------------------------------------------------------
# 7. Multilingual / provenance reuse wrapper (offline, no re-execution)
# ---------------------------------------------------------------------------

def test_multilingual_wrapper_pins_and_prior_equivalence(record):
    ml = json.loads(MULTILINGUAL_JSON.read_text())
    assert ml["run_id"] == RUN_ID
    assert ml["verdict_from_script"] == "PARTIAL_MISS"
    assert ml["all_row_ok"] is False
    assert ml["bundle_sha_match_all_three"] is True
    assert ml["language_robustness_holds_all_three"] is True
    assert ml["rows_equivalent_to_accepted_39986080045_record"] is True
    assert ml["packet_json_sha256"] == EXPECTED["packet_json"]
    assert ml["posture_unchanged"]["packet_admitted"] is False
    raw = OUT_DIR / "40012474431_multilingual_provenance_reuse_raw_script_output.json"
    assert raw.exists()
    raw_doc = json.loads(raw.read_text())
    assert raw_doc["summary"]["all_row_ok"] is False
    assert all(r["sha_matches_frozen"] for r in raw_doc["results"])
    assert all(r["language_ok"] for r in raw_doc["results"])
    assert all(not r["row_ok"] for r in raw_doc["results"])
    # pre-existing D-B schema property, never repaired by this lane
    assert ml["accepted_D_B_characterization_of_record"].startswith(
        "the PARTIAL_MISS is the pre-existing packet-schema property")


# ---------------------------------------------------------------------------
# 8. Mount-dependent byte recomputation (skipped without reason when absent)
# ---------------------------------------------------------------------------

pytestmark_mount = pytest.mark.skipif(
    not MOUNT.exists(),
    reason="ephemeral accepted product mount /tmp/lex_accepted/product is absent; "
           "mount-free tests above still pin every committed claim",
)


@pytestmark_mount
def test_mount_head_and_planner_digest(record):
    import subprocess
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=MOUNT,
        capture_output=True, text=True, check=True).stdout.strip()
    assert head == EXPECTED["mount_head"]
    assert record["product_mount_head"] == EXPECTED["mount_head"]
    assert _sha256_file(MOUNT / "product/query/adversarial_retrieval.py") == EXPECTED["planner"]


@pytestmark_mount
def test_rederive_ready_rate_from_40000001926_measurement():
    """Independent re-derivation of the headline reliability float from legs."""
    meas = json.loads(
        (MOUNT / "results/product/answer_reliability/40000001926_measurement.json").read_text())
    legs = meas["legs"]
    assert len(legs) == 7
    n_ready = sum(1 for leg in legs if leg["answer"]["ready"] is True)
    assert n_ready == 6  # business-judgment-rule leg is the degraded/aborted one
    rate = n_ready / len(legs)
    assert abs(rate - 0.8571428571428571) < 1e-12
    assert abs(meas["metrics"]["answer_ready_rate"] - rate) < 1e-12
    assert round(rate, 3) == 0.857
    # degradation is MARKER-VISIBLE on the newest measurement (6 MEASURED + 1 ABORT)
    statuses = [leg["degradation"]["adversarial_status"] for leg in legs]
    assert statuses.count("MEASURED") == 6
    assert statuses.count("DEGRADED_WRITER_ABORT") == 1
    assert all(leg["degradation"]["visible"] is True for leg in legs)


@pytestmark_mount
def test_rederive_span_selection_arms_from_artifact():
    art = json.loads(
        (MOUNT / "results/product/counter_span/CYCLE_39986094168_span_selection.json").read_text())
    arms = art["aggregate"]
    assert set(arms) == {"baseline", "candidate", "candidate_unguarded"}
    assert arms["candidate"]["n_emitted"] == 1
    assert arms["candidate_unguarded"]["n_emitted"] == 6
    assert arms["baseline"]["n_emitted"] == 0
    assert arms["candidate"]["n_scored"] == 20
    assert arms["candidate_unguarded"]["n_scored"] == 20


@pytestmark_mount
def test_report_labels_6_as_candidate_and_correction_phrase():
    report = (MOUNT / "reports/product/CYCLE_39986094168.md").read_text()
    assert "| candidate | 20 | **6** | 14 | **1.0** | **0.30** |" in report
    correction = (MOUNT / "reports/product/CYCLE_40005362253.md").read_text()
    assert "unguarded diagnostic" in correction
    assert "arm semantics disclosed" in correction
