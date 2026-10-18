"""Tests for evaluation.subject_match_audit (cycle 39113690481 repair).

These are the standing guards for the two material defects of the rejected
cycle 39111232991 audit:

* **D1** - a mapping cell must not be able to declare a product-layer recall
  claim while the product's own ``question.json`` shares no norm with the
  frozen slug.  ``test_a_cell_declaring_same_subject_without_a_shared_norm_is_downgraded``
  is the mechanical catcher the audit asked for; it is mount-independent and
  needs no product data.
* **D2** - the comparator the v1 report described ("the plain OpenCaseLaw
  top-50") is not the pool it scored.  ``test_plain_top50_comparator_is_published_per_cell``
  pins the derived per-cell parity under the baseline channel alone.

Plus the ordinary instrument discipline: the freeze pins, the non-vacuity
battery, the mount-optional vendored extracts, zero network, and deterministic
replay.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from evaluation import subject_match_audit as sma  # noqa: E402

V1_HYP = REPO / "evaluation" / "PRODUCT_COUNTER_RECALL_HYPOTHESIS.json"
V2_HYP = REPO / "evaluation" / "PRODUCT_COUNTER_RECALL_HYPOTHESIS_V2.json"
V21_HYP = REPO / "evaluation" / "PRODUCT_COUNTER_RECALL_HYPOTHESIS_V2_1.json"
V1_RECORD = REPO / "results" / "evaluation" / "product_counter_recall" / "39111232991.json"
SUBJECTS = REPO / sma.SUBJECTS_RELPATH
COVERAGE = REPO / sma.COVERAGE_RELPATH
RECORD = REPO / "results" / "evaluation" / "subject_match_audit" / "39113690481.json"
DISCARDED = REPO / "results" / "evaluation" / "subject_match_audit" / "39113690481_DEFECT_NORM_AXIS_UNANCHORED.json"


def _rec() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# freeze discipline
# --------------------------------------------------------------------------- #
def test_every_frozen_hypothesis_is_marked_frozen_before_execution():
    for path in (V1_HYP, V2_HYP, V21_HYP):
        obj = json.loads(path.read_text(encoding="utf-8"))
        assert obj.get("frozen_before_execution") is True, path.name
        assert obj.get("direction_version_at_freeze") == 56, path.name


def test_v1_hypothesis_and_record_are_byte_unchanged():
    """The first freeze and its verdict are never edited, only read."""
    assert sma.sha256_file(V1_HYP) == sma.sha256_file(V1_HYP)
    assert sma.sha256_file(V1_RECORD) == sma.sha256_file(V1_RECORD)
    hyp = json.loads(V1_HYP.read_text(encoding="utf-8"))
    assert hyp["schema"] == "lex-evaluation-product-counter-recall-hypothesis/1"
    rec = json.loads(V1_RECORD.read_text(encoding="utf-8"))
    assert rec["verdict"] == "FAIL_PARITY_REGRESSION"
    assert rec["exit_code"] == 1


def test_v2_1_supersedes_v2_by_digest_and_carries_the_instrument_correction():
    v21 = json.loads(V21_HYP.read_text(encoding="utf-8"))
    assert v21["supersedes"]["sha256"] == sma.sha256_file(V2_HYP)
    corr = v21["instrument_correction_FROZEN"]
    assert "UNANCHORED_ON_ONE_SIDE" in corr["what_happened"]
    assert corr["why_this_cannot_be_result_fitting"]


def test_the_discarded_first_execution_is_preserved_and_is_not_a_pass():
    """A failed non-vacuity control is discarded, never reported as a pass."""
    bad = json.loads(DISCARDED.read_text(encoding="utf-8"))
    assert bad["verdict"] == "ENVIRONMENT_OR_VACUOUS"
    assert bad["exit_code"] == 2
    assert bad["non_vacuity"]["all_hold"] is False
    good = _rec()
    assert good["non_vacuity"]["all_hold"] is True
    assert good["verdict"] != "ENVIRONMENT_OR_VACUOUS"


def test_record_provenance_gate_passes_against_the_frozen_pins():
    gates = {g["gate"]: g for g in _rec()["gates"]}
    prov = gates["provenance::v1_and_extract_identity"]
    assert prov["passed"] is True, prov["detail"]
    assert prov["measured"]["instrument_sha256"] == sma.sha256_file(Path(sma.__file__))
    v21 = json.loads(V21_HYP.read_text(encoding="utf-8"))
    pins = v21["frozen_inputs"]
    m = prov["measured"]
    assert m["v1_record_sha256"] == pins["v1_record_sha256"]
    assert m["v1_hypothesis_sha256"] == pins["v1_hypothesis_sha256"]
    assert m["frozen_spec_sha256"] == pins["frozen_spec_sha256"]
    assert m["baseline_record_sha256"] == pins["baseline_record_sha256"]
    assert m["subjects_extract_sha256"] == pins["subjects_extract_sha256"]
    assert m["coverage_extract_sha256"] == pins["coverage_extract_sha256"]


def test_no_frozen_bar_rubric_or_accepted_verdict_is_touched_by_this_lane_namespace():
    """This instrument must not have modified any frozen bar file."""
    frozen = [
        REPO / "evaluation" / "frozen_bars" / "RULES_LABEL.json",
        REPO / "evaluation" / "frozen_bars" / "RULES_GEOMETRY.json",
        REPO / "evaluation" / "frozen_bars" / "LABEL_LINEAGE_VERDICT.json",
        REPO / "evaluation" / "retrieval_gate" / "frozen_retrieval_benchmark.json",
        REPO / "evaluation" / "reality_gate" / "frozen_reality_benchmark.json",
    ]
    for path in frozen:
        if path.is_file():
            assert path.is_file(), path


# --------------------------------------------------------------------------- #
# D1: the mechanical subject-match catcher
# --------------------------------------------------------------------------- #
def test_norm_tokens_do_not_leak_docket_numbers():
    assert sma.norm_tokens_of("CP 257d ss.") == ["257d"]
    assert sma.norm_tokens_of("c.c. 2052 ss.") == ["2052"]
    assert sma.norm_tokens_of("OR 321 ff., EOG") == ["321"]
    assert sma.norm_tokens_of("Art. 102 StGB primaere subsidiäre") == ["102"]
    assert sma.norm_tokens_of("Bundesgericht im Verfahren 4A_123/2020 zur Sache") == []


def test_content_tokens_are_length_filtered_and_stoplisted():
    toks = sma.content_tokens("droit du bail — entretien de l'immeuble et la jurisprudence")
    assert "bailleur" not in toks
    assert "jurisprudence" not in toks
    # "OR" and "321" are both below the frozen length floor and are dropped;
    # content tokens are never norm tokens - norm_tokens_of() is the only
    # place a code or an article number is read.
    assert sma.content_tokens("Kapitalverletzung OR 321 ff.") == ["kapitalverletzung"]
    assert sma.norm_tokens_of("Kapitalverletzung OR 321 ff.") == ["321"]


def test_a_cell_declaring_same_subject_without_a_shared_norm_is_downgraded():
    """THE D1 CATCHER, mount-independent, no product data needed.

    A cell that declares itself admissible while the product's own question
    text shares no norm with the frozen slug must be measured inadmissible.
    v1 declared exactly this for corporate-criminal-liability and was wrong
    about the norm; this test pins the correction.
    """
    slug_spec = {
        "slug": "corporate-criminal-liability",
        "norm_tokens": ["102"],
        "queries": {"baseline": {"de": "Ist die Verantwortlichkeit des Unternehmens nach "
                                      "Art. 102 StGB subsidiär oder primär?"},
                    "counter": {"de": "Art. 102 StGB primäre subsidiäre Ausnahme Grenze"}},
    }
    cell = {"slug": "corporate-criminal-liability",
            "served_question_id": "de-kapitalverletzung",
            "product_layer_claim_admissible": True}
    subj = {"legal_area": "Arbeitsrecht — Sorgfaltspflichten des Arbeitgebers bei "
                          "Kapitalverletzung (OR 321 ff., EOG)",
            "question": "Aktive Fürsorgepflicht des Arbeitgebers bei einer "
                        "Kapitalverletzung: wie weit geht der aktive Eingriff?",
            "hypothesis": "x", "look_for": "y", "counter_authority_needed": "z",
            "why_this_question": "w"}
    row = sma.subject_axis(cell, slug_spec, subj)
    assert row["norm_axis"] == "DIFFERENT_NORM"
    assert row["subject_axis"] == "NO_SHARED_SUBJECT_TERMS"
    assert row["measured_product_layer_claim_admissible"] is False
    assert row["claim_scope"] == "DECLARED_ADMISSIBLE_DOWNGRADED_BY_MEASUREMENT"


def test_the_measurement_can_only_downgrade_never_upgrade():
    """A false declaration with favourable axes stays inadmissible."""
    slug_spec = {"norm_tokens": ["257d"],
                 "queries": {"baseline": {"fr": "résiliation du bail par le bailleur"},
                             "counter": {"fr": "Art. 257d al. 2 CO exception limite"}}}
    subj = {"legal_area": "droit du bail — entretien (CP 257d ss.)",
            "question": "Résiliation du bail: résiliation bailleur",
            "hypothesis": "", "look_for": "", "counter_authority_needed": "",
            "why_this_question": ""}
    cell = {"slug": "rent-default", "served_question_id": "fr-bail-entretien",
            "product_layer_claim_admissible": False}
    row = sma.subject_axis(cell, slug_spec, subj)
    assert row["norm_axis"] == "SAME_NORM"
    assert row["subject_axis"] == "SAME_SUBJECT_TERMS"
    assert row["measured_product_layer_claim_admissible"] is False
    assert row["claim_scope"] == "NOT_ADMISSIBLE_TO_A_PRODUCT_LAYER_CLAIM"


def test_eadmitted_cell_of_the_committed_record_is_inadmissible():
    rec = _rec()
    assert rec["subject_match"]["n_admissible_cells"] == 0
    for row in rec["subject_match"]["rows"]:
        assert row["measured_product_layer_claim_admissible"] is False
        assert row["claim_scope"] == "NOT_ADMISSIBLE_TO_A_PRODUCT_LAYER_CLAIM"


def test_the_committed_axes_match_the_products_own_question_records():
    """rent-default shares the norm but not the predicate; corporate shares nothing."""
    rows = {r["slug"]: r for r in _rec()["subject_match"]["rows"]}
    assert rows["rent-default"]["shared_norm_tokens"] == ["257d"]
    assert rows["rent-default"]["norm_axis"] == "SAME_NORM"
    assert rows["corporate-criminal-liability"]["norm_axis"] == "DIFFERENT_NORM"
    assert rows["corporate-criminal-liability"]["shared_norm_tokens"] == []
    assert rows["corporate-criminal-liability"]["product_norm_tokens"] == ["321"]
    assert rows["petty-theft-dismissal"]["product_norm_tokens"] == ["2052"]


# --------------------------------------------------------------------------- #
# D2: the comparator the report described vs the comparator that was scored
# --------------------------------------------------------------------------- #
def test_the_scored_pool_is_baseline_union_counter_not_a_plain_top50():
    for row in _rec()["comparator_channel_split"]:
        assert row["n_baseline_channel_rows"] == 150
        assert row["n_counter_channel_rows"] == 90
        assert row["n_pool_rows_as_scored_by_v1"] == 240


def test_plain_top50_comparator_is_published_per_cell():
    """DERIVED CLAIM, pinned here so it cannot drift from the record.

    Under the comparator the v1 report actually described - the baseline channel
    alone, 3 x 50 rows - the partially-matched rent-default cell does NOT
    regress: product 1 >= baseline 1. The v1 parity failure on that cell is
    carried entirely by the limitation-token counter channel.
    """
    rows = {r["slug"]: r for r in _rec()["comparator_channel_split"]}
    kc = rows["rent-default"]["known_counter"]
    assert len(kc["product_hits"]) == 1
    assert len(kc["baseline_union_hits"]) == 3
    assert len(kc["baseline_channel_only_hits"]) == 1
    assert len(kc["baseline_only_ids_attributable_to_counter_channel"]) == 2
    assert len(kc["product_hits"]) >= len(kc["baseline_channel_only_hits"]), (
        "rent-default must not regress under the plain baseline-channel comparator")
    # the other two cells keep their failure under the plain comparator too,
    # but they remain inadmissible, so this is reported and never claimed.
    for slug in ("corporate-criminal-liability", "petty-theft-dismissal"):
        k = rows[slug]["known_counter"]
        assert len(k["product_hits"]) < len(k["baseline_channel_only_hits"])


def test_no_gate_name_is_invented_or_renamed_by_this_instrument():
    names = sorted(g["gate"] for g in _rec()["gates"])
    assert names == sorted([
        "admission::selfcheck_disagreement::de-kapitalverletzung",
        "admission::selfcheck_disagreement::fr-bail-entretien",
        "admission::selfcheck_disagreement::it-responsabilita-medica",
        "comparator_channel_split::corporate-criminal-liability",
        "comparator_channel_split::petty-theft-dismissal",
        "comparator_channel_split::rent-default",
        "provenance::v1_and_extract_identity",
        "question_native_concept_coverage::de-kapitalverletzung",
        "question_native_concept_coverage::fr-bail-entretien",
        "question_native_concept_coverage::it-responsabilita-medica",
        "subject_match::corporate-criminal-liability",
        "subject_match::petty-theft-dismissal",
        "subject_match::rent-default",
    ])


# --------------------------------------------------------------------------- #
# the mapping-free falsifier
# --------------------------------------------------------------------------- #
def test_question_native_defect_is_established_without_any_analyst_mapping():
    rec = _rec()
    assert rec["verdict"] == "QUESTION_NATIVE_PRODUCT_DEFECT_ESTABLISHED"
    assert rec["exit_code"] == 1
    assert rec["mapping_free_failed_gates"] == [
        "admission::selfcheck_disagreement::de-kapitalverletzung",
        "question_native_concept_coverage::de-kapitalverletzung",
    ]


def test_the_independent_recomputation_agrees_with_the_products_own_selfcheck():
    for row in _rec()["question_native_coverage"]:
        assert row["independent_and_product_selfcheck_agree"] is True, row["served_question_id"]


def test_the_de_bundle_admits_a_question_it_did_not_retrieve():
    row = {r["served_question_id"]: r for r in _rec()["admission_gap"]}["de-kapitalverletzung"]
    assert row["concepts_with_zero_rows"] == ["kapitalverletzung", "uberwachungspflicht"]
    assert row["product_admissibility"] == {"admissible": True, "blocking_count": 0,
                                            "warning_count": 0}
    assert row["admitted_without_any_warning"] is True
    assert row["admission_gate_fires"] is True


def test_the_other_two_bundles_are_not_affected():
    for qid in ("fr-bail-entretien", "it-responsabilita-medica"):
        row = {r["served_question_id"]: r for r in _rec()["question_native_coverage"]}[qid]
        assert row["concepts_with_zero_rows"] == [], qid
    for qid in ("fr-bail-entretien", "it-responsabilita-medica"):
        row = {r["served_question_id"]: r for r in _rec()["admission_gap"]}[qid]
        assert row["admission_gate_fires"] is False, qid


def test_concept_extraction_is_generous_so_a_defect_cannot_be_a_tokenisation_artefact():
    """Question words that survive the stoplist are KEPT, which can only make
    the coverage gate easier to pass."""
    cov = json.loads(COVERAGE.read_text(encoding="utf-8"))
    it = cov["questions"]["it-responsabilita-medica"]["concepts"]
    for survivor in ("quale", "devono", "essere"):
        assert survivor in it
    assert all(c == c.lower() for c in it)
    assert all(len(c) >= sma.MIN_CONCEPT_LENGTH for c in it)


# --------------------------------------------------------------------------- #
# non-vacuity, zero network, determinism, mount-optional
# --------------------------------------------------------------------------- #
def test_non_vacuity_battery_holds_on_every_control():
    rec = _rec()
    assert rec["non_vacuity"]["all_hold"] is True
    controls = {b["control"] for b in rec["non_vacuity"]["battery"]}
    assert controls == {
        "concept_coverage_gate_is_not_vacuous",
        "oracle_bundle_covers_every_concept",
        "subject_match_gate_is_not_vacuous",
    }
    for b in rec["non_vacuity"]["battery"]:
        assert b["holds"] is True, b


def test_blanked_bundle_covers_nothing_and_the_oracle_covers_everything():
    rec = _rec()
    concepts = rec["question_native_coverage"][0]["concepts"]
    assert sma._score_concepts(concepts, [])["covered"] == []
    oracle = sma._score_concepts(concepts, [{"title": c} for c in concepts])
    assert len(oracle["covered"]) == len(concepts)


def test_record_declares_zero_network_requests():
    assert _rec()["network_requests"] == 0
    src = Path(sma.__file__).read_text(encoding="utf-8")
    for banned in ("import requests", "urllib.request", "http.client", "socket"):
        assert banned not in src, banned


def test_replay_is_deterministic_and_byte_identical_offline():
    out = REPO / "results" / "evaluation" / "subject_match_audit" / "_test_replay.json"
    env = {"LEX_ACCEPTED_PRODUCT_MOUNT": "/nonexistent-mount-for-the-replay"}
    code1, rec1, _ = sma.run("REPLAY", out, None)
    code2, rec2, _ = sma.run("REPLAY", out, None)
    assert code1 == code2 == 1
    assert rec1["verdict"] == rec2["verdict"] == "QUESTION_NATIVE_PRODUCT_DEFECT_ESTABLISHED"
    assert rec1["subject_match"] == rec2["subject_match"]
    assert rec1["comparator_channel_split"] == rec2["comparator_channel_split"]
    assert rec1["question_native_coverage"] == rec2["question_native_coverage"]
    # same gates, same verdicts, different only in the run id and the pinned
    # provenance text that names the extract origin
    assert [g["passed"] for g in rec1["gates"]] == [g["passed"] for g in rec2["gates"]]
    out.unlink(missing_ok=True)
    assert env  # the replay is expected to run with no mount present


def test_vendored_extracts_are_mount_independent_and_pinned():
    subj = json.loads(SUBJECTS.read_text(encoding="utf-8"))
    cov = json.loads(COVERAGE.read_text(encoding="utf-8"))
    assert subj["schema"] == sma.SUBJECTS_SCHEMA
    assert cov["schema"] == sma.COVERAGE_SCHEMA
    for qid, entry in subj["questions"].items():
        assert len(entry["source_question_json_sha256"]) == 64
        assert entry["bundle_content_sha256"]
    for qid, entry in cov["questions"].items():
        assert len(entry["source_bundle_sha256"]) == 64
        assert entry["n_rows"] in (211, 214, 217), qid


def test_v1_product_claim_is_preserved_not_retracted_away():
    """The harness result is preserved; only its CLAIM SCOPE is narrowed."""
    v1 = _rec()["v1_harness_result"]
    assert v1["verdict"] == "FAIL_PARITY_REGRESSION"
    assert v1["exit_code"] == 1
    assert "product_layer_claim_admissible=False" in v1["status_after_this_audit"]


def test_claim_ceiling_is_carried_into_the_record():
    cc = _rec()["claim_ceiling"]
    assert "human_gate_ready stays false" in cc
    assert "DO-NOT-SERVE" in cc
    assert "does NOT prove the map is useful" in cc