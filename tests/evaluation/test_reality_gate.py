#!/usr/bin/env python3
"""Frozen tests for the evaluation-lane reality benchmark (direction v49).

These tests pin the benchmark itself: they fail if the frozen spec is
tampered with (digest pin) and they prove every gate CAN fail — a gate that
cannot fail is not a benchmark.  Pure standard library + pytest.
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from evaluation.reality_gate import frozen, gate_contract, gates, run_benchmark

SPEC = frozen.load_frozen()
QUESTIONS = frozen.question_by_slug(SPEC)
REPO = Path(__file__).resolve().parents[2]

# --------------------------------------------------------------------------- #
# freeze discipline
# --------------------------------------------------------------------------- #


def test_frozen_spec_digest_pin():
    import hashlib
    raw = frozen._PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == frozen.FROZEN_SHA256


def test_frozen_question_set_exact():
    assert [q["slug"] for q in SPEC["questions"]] == [
        "rent-default",
        "corporate-criminal-liability",
        "business-judgment-rule",
        "petty-theft-dismissal",
    ]
    assert SPEC["direction_version"] == 49
    assert SPEC["latency_budget_seconds"] == 300.0


def test_frozen_controlling_authorities_pinned():
    """The controlling authorities the observed reality-check failures turned on."""
    ccl = QUESTIONS["corporate-criminal-liability"]
    assert set(ccl["required_citation_ids"]) == {"bge_BGE_142_IV_333", "bger_6B_124_2016"}
    bjr = QUESTIONS["business-judgment-rule"]
    assert set(bjr["required_citation_ids"]) == {
        "bger_4A_219_2015", "bger_4A_259_2016", "bger_4A_626_2013",
        "bger_4A_603_2014", "bger_4A_62_2024",
    }
    petty = QUESTIONS["petty-theft-dismissal"]
    assert set(petty["required_citation_ids"]) == {"bger_4A_228_2015", "bger_4A_177_2017"}
    assert set(petty["required_retrieval_ids"]) == {"bger_4A_228_2015", "bger_4A_177_2017"}


def test_frozen_phrases_match_their_normalized_form():
    """The frozen phrase lists survive the normalization unchanged (apostrophe variants)."""
    for q in SPEC["questions"]:
        for gate in q["truth_gates"]:
            phrases = gate.get("contains_any") or gate.get("absent_any") or []
            for phrase in phrases:
                norm = gates.normalize_text(phrase)
                if "’" not in phrase and "'" not in phrase:
                    assert norm == phrase.casefold(), (phrase, norm)


# --------------------------------------------------------------------------- #
# truth gates: every gate can fail
# --------------------------------------------------------------------------- #

POSITIVE_PROSE = {
    "rent-default": (
        "Le bailleur peut résilier le bail d'habitation pour retard de loyer: "
        "préavis de 30 jours, prise d'effet à la fin d'un mois. "
        "L'abus de droit et l'exigence de bonne foi limitent cette prérogative."
    ),
    "corporate-criminal-liability": (
        "L'art. 102 CP connaît deux régimes: la responsabilité subsidiaire de "
        "l'entreprise (al. 1) et la responsabilité primaire (al. 2)."
    ),
    "business-judgment-rule": (
        "Le juge suisse exige une information suffisante du conseil "
        "d'administration, l'absence de conflit d'intérêt et fait preuve de "
        "retenue: il s'abstient de revoir le fond (abstention/deference)."
    ),
    "petty-theft-dismissal": (
        "Un vol de faible valeur (bagatell, geringfugig) commis par un employé "
        "peut justifier un licenciement immédiat selon l'art. 337 CO."
    ),
}


@pytest.mark.parametrize("slug", list(POSITIVE_PROSE))
def test_truth_gates_pass_on_positive_prose(slug):
    outcomes = gates.evaluate_truth_gates(QUESTIONS[slug], POSITIVE_PROSE[slug])
    assert outcomes, slug
    assert all(o["passed"] for o in outcomes), (slug, outcomes)


@pytest.mark.parametrize("slug", list(POSITIVE_PROSE))
def test_truth_gates_fail_when_each_required_branch_is_removed(slug):
    base = POSITIVE_PROSE[slug]
    for gate in QUESTIONS[slug]["truth_gates"]:
        if gate["kind"] == "phrase_absent":
            continue
        # remove the branch: drop the sentence containing the first phrase
        phrase = gate["contains_any"][0]
        norm = gates.normalize_text(base)
        assert phrase in norm
        sentences = norm.split(". ")
        mutated = ". ".join(s for s in sentences if phrase not in s)
        if mutated == norm:
            mutated = norm.replace(phrase, phrase[0] + "X" + phrase[2:])
        outcomes = gates.evaluate_truth_gates(QUESTIONS[slug], mutated)
        by_id = {o["gate"]: o for o in outcomes}
        assert by_id[f"truth::{gate['id']}"]["passed"] is False, (slug, gate["id"])


def test_art102_reversal_gate_fails_on_reversed_classification():
    q = QUESTIONS["corporate-criminal-liability"]
    reversed_prose = (
        "L'art. 102 CP ne cree pas une responsabilite primaire pour l'entreprise."
    )
    outcomes = gates.evaluate_truth_gates(q, reversed_prose)
    by_id = {o["gate"]: o for o in outcomes}
    # the phrase-presence gates still fire on the (negated) phrase — this is
    # exactly why the frozen benchmark carries a dedicated phrase_absent gate:
    # phrase presence alone cannot detect a reversed classification.
    assert by_id["truth::art102_primary"]["passed"] is True
    assert by_id["truth::art102_no_reversal"]["passed"] is False


# --------------------------------------------------------------------------- #
# language gate
# --------------------------------------------------------------------------- #


def test_language_gate_rejects_wrong_language_answer():
    q = QUESTIONS["rent-default"]
    en = ("The landlord may terminate the residential lease for rent default. "
          "The notice period is thirty days and ends at the end of the month. "
          "Good faith limits the termination.")
    outcome = gates.evaluate_language_gate(q, en, SPEC)
    assert outcome["passed"] is False
    assert "wrong-language" in outcome["detail"]


def test_language_gate_accepts_question_language_and_german_fallback():
    q = QUESTIONS["rent-default"]
    fr = POSITIVE_PROSE["rent-default"]
    de = ("Der Vermieter kann den Mietvertrag wegen Mietrückständen kündigen: "
          "Frist von 30 Jahren, Ende eines Monats, Rechtsmissbrauch schränkt ein.")
    assert gates.evaluate_language_gate(q, fr, SPEC)["passed"] is True
    assert gates.evaluate_language_gate(q, de, SPEC)["passed"] is True


# --------------------------------------------------------------------------- #
# corruption gate
# --------------------------------------------------------------------------- #


def test_corruption_gate_flags_repetition_loop():
    prose = ("Le juge s'abstient de revoir la décision. " * 40)
    outcome = gates.evaluate_corruption_gate(prose)
    assert outcome["passed"] is False
    assert any("repeated sentence" in r for r in outcome["measured"]["corruption_reasons"])


def test_corruption_gate_flags_mojibake():
    outcome = gates.evaluate_corruption_gate("Le juge � s'abstient de revoir la d�cision.")
    assert outcome["passed"] is False
    assert any("U+FFFD" in r for r in outcome["measured"]["corruption_reasons"])


def test_corruption_gate_accepts_clean_prose():
    outcome = gates.evaluate_corruption_gate(POSITIVE_PROSE["business-judgment-rule"])
    assert outcome["passed"] is True
    assert outcome["measured"]["corruption_reasons"] == []


# --------------------------------------------------------------------------- #
# latency gate
# --------------------------------------------------------------------------- #


def test_latency_gate_boundary():
    assert gates.evaluate_latency(299.9, 300.0)["passed"] is True
    assert gates.evaluate_latency(300.0, 300.0)["passed"] is False
    assert gates.evaluate_latency(861.409, 300.0)["passed"] is False


def test_latency_gate_not_measurable_without_timing():
    outcome = gates.evaluate_latency(None, 300.0)
    assert outcome["passed"] is None
    assert "not_measurable" in outcome["detail"]


# --------------------------------------------------------------------------- #
# recall gates
# --------------------------------------------------------------------------- #


def test_recall_gate_citation_hits_and_misses():
    q = QUESTIONS["business-judgment-rule"]
    hit = gates.evaluate_required_hits(q["required_citation_ids"],
                                      {"bger_4A_626_2013"}, "citation", True)
    assert hit["passed"] is True
    miss = gates.evaluate_required_hits(q["required_citation_ids"],
                                       {"some_other_id"}, "citation", True)
    assert miss["passed"] is False
    assert "bger_4A_219_2015" in miss["measured"]["missing"]


def test_recall_gate_retrieval_requires_artifact_id_list():
    q = QUESTIONS["petty-theft-dismissal"]
    ok = gates.evaluate_required_hits(q["required_retrieval_ids"],
                                      {"bger_4A_228_2015", "x"}, "retrieval", True)
    assert ok["passed"] is True
    nm = gates.evaluate_required_hits(q["required_retrieval_ids"], set(),
                                      "retrieval", False)
    assert nm["passed"] is None  # slim artifact: honestly not measurable


# --------------------------------------------------------------------------- #
# structural gates (single bundle)
# --------------------------------------------------------------------------- #


def _bundle(decisions, cited):
    return {
        "answer": {"status": "ready", "cited_decision_ids": cited, "prose": "x" * 200},
        "decisions": decisions,
        "provenance": {"phase": "complete", "latency_seconds_total": 10.0},
    }


def _decision(i, **kw):
    d = {"decision_id": f"d{i}", "canonical_url": f"https://mcp.opencaselaw.ch/entscheid/d{i}",
         "language": "fr", "cluster_id": 0, "x": 0.1, "y": 0.2, "is_outlier": False}
    d.update(kw)
    return d


def test_structural_bundle_clean_passes():
    checks = gates.bundle_structural(_bundle([_decision(1), _decision(2)], ["d1"]))
    assert all(checks[k] for k in ("bundle_nonempty", "duplicate_free",
                                   "source_urls_valid", "answer_citations_constrained",
                                   "counter_classifications_supported"))


def test_structural_bundle_duplicates_fail():
    checks = gates.bundle_structural(_bundle([_decision(1), _decision(1)], []))
    assert checks["duplicate_free"] is False


def test_structural_bad_source_url_fails():
    checks = gates.bundle_structural(
        _bundle([_decision(1, canonical_url="https://example.com/d1")], []))
    assert checks["source_urls_valid"] is False
    assert checks["bad_source_ids"] == ["d1"]


def test_structural_invented_citation_fails():
    checks = gates.bundle_structural(_bundle([_decision(1)], ["invented"]))
    assert checks["answer_citations_constrained"] is False


def test_structural_counter_without_evidence_fails():
    checks = gates.bundle_structural(
        _bundle([_decision(1, counter_status="contrary_or_exception")], []))
    assert checks["counter_classifications_supported"] is False


# --------------------------------------------------------------------------- #
# multilingual robustness
# --------------------------------------------------------------------------- #


def test_multilingual_coverage_per_bundle():
    bundle = {
        "query": "Wann endet ein Mietvertrag?",
        "decisions": [
            _decision(1, language="de"), _decision(2, language="de"),
            _decision(3, language="fr"), _decision(4, language="it"),
        ],
    }
    out = gates.evaluate_multilingual_coverage([dict(bundle, _label="de-tenancy")])
    assert out[0]["passed"] is True


def test_multilingual_coverage_rejects_single_language_bundle():
    bundle = {
        "query": "Wann endet ein Mietvertrag?",
        "decisions": [_decision(1, language="de"), _decision(2, language="de")],
    }
    out = gates.evaluate_multilingual_coverage([dict(bundle, _label="de-tenancy")])
    assert out[0]["passed"] is False


# --------------------------------------------------------------------------- #
# frozen spec loads through the public loader (used by the runner)
# --------------------------------------------------------------------------- #


def test_loader_round_trip():
    spec = frozen.load_frozen()
    assert spec["schema"] == "lex-frozen-reality-benchmark/1"
    assert len(spec["questions"]) == 4


# ---------------------------------------------------------------------------
# audit repair R1: recall-gate semantics are ">=1 of the frozen set", per gate
# ---------------------------------------------------------------------------


def test_recall_gate_semantics_is_exactly_at_least_one_of_frozen_set():
    """A partial-set pass still PASSES and names the missing authorities; the
    frozen wording is '>=1 of frozen authority set' (restated, not re-frozen)."""
    bjr = QUESTIONS["business-judgment-rule"]
    required = bjr["required_citation_ids"]
    assert len(required) == 5
    one_hit = gates.evaluate_required_hits(required, {required[0]}, "citation", True)
    assert one_hit["passed"] is True
    assert one_hit["detail"] == ""
    assert set(one_hit["measured"]["missing"]) == set(required) - {required[0]}
    zero = gates.evaluate_required_hits(required, set(), "citation", True)
    assert zero["passed"] is False
    empty_set = gates.evaluate_required_hits(set(), {"x"}, "citation", True)
    assert empty_set["passed"] is True
    assert empty_set["detail"] == ""  # informational note lives in measured.note


# ---------------------------------------------------------------------------
# audit repair R4: passing gates never carry failure-flavoured detail
# ---------------------------------------------------------------------------


def test_all_passing_gates_carry_blank_detail():
    clean_report = {
        "answer_status": "ready", "answer_method": "generative_audit_llm_v2",
        "answer_prose": "x" * 200, "cited_decision_ids": ["d1"],
        "provider_error": None, "adversarial_method": "independent_llm_adversarial_v2",
        "adversarial_error": None,
    }
    for outcome in gates.evaluate_structural_from_report(clean_report):
        assert outcome["passed"] is True
        assert outcome["detail"] == "", outcome
    clean_bundle = _bundle([_decision(1), _decision(2)], ["d1"])
    for outcome in gates.evaluate_structural_from_bundle(clean_bundle):
        if outcome["passed"] is True:
            assert outcome["detail"] == "", outcome
    empty_required = gates.evaluate_required_hits([], {"d1"}, "citation", True)
    assert empty_required["passed"] is True and empty_required["detail"] == ""


# ---------------------------------------------------------------------------
# audit repair R5: negative tests for the eight slim-report structural gates
# ---------------------------------------------------------------------------

_CLEAN_REPORT = {
    "answer_status": "ready", "answer_method": "generative_audit_llm_v2",
    "answer_prose": "x" * 200, "cited_decision_ids": ["d1"],
    "provider_error": None, "adversarial_method": "independent_llm_adversarial_v2",
    "adversarial_error": None,
}

_STRUCTURAL_MUTATIONS = [
    ({"validation_errors": ["schema mismatch"]}, "structural::bundle_validation_clean"),
    ({"answer_status": "partial"}, "structural::answer_ready"),
    ({"answer_method": "rule_based"}, "structural::answer_method"),
    ({"answer_prose": "trop court"}, "structural::prose_min_length"),
    ({"cited_decision_ids": []}, "structural::citations_nonempty"),
    ({"provider_error": "timeout"}, "structural::provider_clean"),
    ({"adversarial_method": "none"}, "structural::adversarial_method"),
    ({"adversarial_error": "llm unavailable"}, "structural::adversarial_clean"),
]


@pytest.mark.parametrize("mutation,gate", _STRUCTURAL_MUTATIONS)
def test_each_slim_structural_gate_can_fail(mutation, gate):
    mutated = {**_CLEAN_REPORT, **mutation}
    outcomes = {o["gate"]: o for o in gates.evaluate_structural_from_report(mutated)}
    assert outcomes[gate]["passed"] is False, gate
    assert outcomes[gate]["detail"] != "", gate
    # the other seven gates still pass (mutation is isolated)
    for name, outcome in outcomes.items():
        if name != gate:
            assert outcome["passed"] is True, (gate, name)


def test_slim_structural_gates_all_pass_on_clean_report():
    outcomes = gates.evaluate_structural_from_report(_CLEAN_REPORT)
    assert len(outcomes) == 8
    assert all(o["passed"] for o in outcomes)


# ---------------------------------------------------------------------------
# audit repair R2: coverage honesty for excluded/unmatched artifacts
# ---------------------------------------------------------------------------


def test_excluded_kinds_carry_explicit_not_measurable_with_reasons():
    from evaluation.reality_gate import run_benchmark
    arts = [
        {"artifact": "x/fatal.json", "kind": "fatal_stub",
         "data": {"slug": "rent-default", "leg_passed": False, "fatal_error": "boom"}},
        {"artifact": "x/rollup.json", "kind": "summary_rollup",
         "data": {"all_legs_passed": True}},
        {"artifact": "x/other.json", "kind": "unmatched_kind", "data": {"foo": 1}},
    ]
    rep = run_benchmark.evaluate_artifacts(arts, SPEC)
    for rec in rep["artifacts"]:
        assert rec["evaluation_scope"] == "none", rec
        assert rec["gates"] == []
        assert rec["artifact_passed"] is None
        assert rec["not_measurable_gates"], rec
        assert rec["not_measurable_reasons"], rec
        assert set(rec["not_measurable_gates"]) == set(rec["not_measurable_reasons"])
    fatal = next(r for r in rep["artifacts"] if r["artifact"] == "x/fatal.json")
    # slug known -> concrete frozen truth gates enumerated, with reasons
    assert "truth::art257d2_30day_notice" in fatal["not_measurable_gates"]
    assert "truth::art257d2_end_of_month" in fatal["not_measurable_gates"]
    rollup = next(r for r in rep["artifacts"] if r["artifact"] == "x/rollup.json")
    # no slug -> whole truth family under one placeholder
    assert "truth::*" in rollup["not_measurable_gates"]


def test_unmatched_bundle_gets_question_independent_checks():
    from evaluation.reality_gate import run_benchmark
    bundle = {
        "query": "a question that matches no frozen leg",
        "decisions": [_decision(1), _decision(2)],
        "answer": {"prose": "x" * 200, "cited_decision_ids": ["d1"],
                   "status": "ready", "method": "generative_audit_llm_v2"},
        "provenance": {"latency_seconds_total": 10.0},
    }
    rep = run_benchmark.evaluate_artifacts(
        [{"artifact": "x/b.json", "kind": "full_bundle", "data": bundle}], SPEC)
    rec = rep["artifacts"][0]
    assert rec["evaluation_scope"] == "question_independent_only"
    names = [g["gate"] for g in rec["gates"]]
    for g in ("structural::bundle_nonempty", "structural::duplicate_free",
              "structural::source_urls_valid", "structural::answer_citations_constrained",
              "structural::counter_classifications_supported",
              "corruption::clean", "latency::under_budget"):
        assert g in names, g
    # question-dependent gates explicitly not measurable, with reasons
    for g in ("truth::*", "language::dominant_in_accepted",
              "recall::citation_controlling_authority",
              "recall::retrieval_controlling_authority",
              "structural::geometry_preserved", "structural::progressive_phases"):
        assert g in rec["not_measurable_gates"], g
        assert rec["not_measurable_reasons"][g]
    assert rec["artifact_passed"] is True
    # multilingual coverage still runs over the unmatched bundle
    assert len(rep["multilingual_checks"]) == 1


def test_unmatched_bundle_counter_gate_falsifies():
    """A recorded bundle with evidence-free counter rows FAILS the
    question-independent structural gate — negative evidence must be visible."""
    from evaluation.reality_gate import run_benchmark
    bundle = {
        "query": "another unknown question",
        "decisions": [_decision(1, counter_status="contrary_or_exception")],
        "answer": {"prose": "x" * 200, "cited_decision_ids": ["d1"]},
    }
    rep = run_benchmark.evaluate_artifacts(
        [{"artifact": "x/b.json", "kind": "full_bundle", "data": bundle}], SPEC)
    rec = rep["artifacts"][0]
    assert rec["evaluation_scope"] == "question_independent_only"
    assert rec["failed_gates"] == ["structural::counter_classifications_supported"]
    assert rec["artifact_passed"] is False
    assert rep["overall_pass"] is False


# ---------------------------------------------------------------------------
# audit repair R6a: empty/absent evidence input is an environment error,
# never a plausible-looking FAIL verdict record
# ---------------------------------------------------------------------------


def test_absent_evidence_dir_exits_2_without_record(tmp_path, capsys):
    from evaluation.reality_gate import run_benchmark
    out = tmp_path / "out.json"
    rc = run_benchmark.main(["--evidence-dir", str(tmp_path / "absent"),
                             "--out", str(out)])
    assert rc == 2
    assert not out.exists()
    err = capsys.readouterr().err
    assert "does not exist" in err


def test_empty_evidence_dir_exits_2_without_record(tmp_path, capsys):
    from evaluation.reality_gate import run_benchmark
    out = tmp_path / "out.json"
    rc = run_benchmark.main(["--evidence-dir", str(tmp_path), "--out", str(out)])
    assert rc == 2
    assert not out.exists()
    err = capsys.readouterr().err
    assert "no readable artifacts" in err


# ---------------------------------------------------------------------------
# cycle 38934722443: the minimal durable-workflow roll-up shape (legs array,
# no all_legs_passed) must classify as a roll-up, not as an unrecognized blob
# ---------------------------------------------------------------------------


def test_minimal_rollup_shape_classifies_as_summary_rollup():
    from evaluation.reality_gate import run_benchmark
    minimal = {
        "durable_run_required": "product-reality-check.yml",
        "generated_at": "2026-10-16T16:10:06Z",
        "legs": [{"slug": "business-judgment-rule", "passed": True,
                  "report": "results/product/reality_check/bjr_live_x.json"}],
        "local_evidence_only": True,
        "mode": "live",
    }
    assert run_benchmark._classify(minimal) == "summary_rollup"
    rep = run_benchmark.evaluate_artifacts(
        [{"artifact": "x/summary_live.json", "kind": "summary_rollup",
          "data": minimal}], SPEC)
    rec = rep["artifacts"][0]
    assert rec["evaluation_scope"] == "none"
    assert rec["producer_legs"] == [
        {"slug": "business-judgment-rule", "passed": True,
         "report": "results/product/reality_check/bjr_live_x.json"}]
    # a slim leg report still wins its own classification (slug present)
    assert run_benchmark._classify(
        {**minimal, "slug": "x", "leg_passed": True,
         "answer_prose": "prose"}) == "slim_report"
    # an old-style run summary keeps classifying too
    assert run_benchmark._classify({"all_legs_passed": True, "legs": []}) == "summary_rollup"


# ---------------------------------------------------------------------------
# cycle 38934722443: pins the CURRENT accepted product packet's verdicts.
# Skipped cleanly when the accepted-product mount is absent (plain CI).
# ---------------------------------------------------------------------------

_MOUNT = "/tmp/lex_accepted/product/results/product/reality_check"

_CURRENT_PACKET_LEG_PINS = {
    # fresh live legs of product cycle V49_TARGETED_REALITY_REPAIR_4OF4_LIVE
    "rent-default_live_20261016T154849Z.json": (
        True, []),
    "corporate-criminal-liability_live_20261016T160526Z.json": (
        True, []),
    "petty-theft-dismissal_live_20261016T160318Z.json": (
        True, []),  # partial recall pass: cites bger_4A_177_2017, misses 4A_228_2015
    # FALSIFYING: the fresh BJR leg cites none of the five frozen direct-TF
    # BJR authorities (bger_4A_219_2015/259_2016/626_2013/603_2014/62_2024);
    # the producer's own structural+truth gates pass it.
    "business-judgment-rule_live_20261016T161006Z.json": (
        False, ["recall::citation_controlling_authority"]),
    # PRESERVED pre-fix negative: answer ignored direct TF petty-theft
    # authority (bger_4A_177/228) — the failure the product repaired.
    "petty-theft-dismissal_live_20261016T155135Z.json": (
        False, ["recall::citation_controlling_authority"]),
}

_CURRENT_PACKET_EXCLUDED_PINS = {
    "rent-default_fixture_20261016T154703Z.json": "fatal_stub",
    "rent-default_fixture_20261016T154708Z.json": "fatal_stub",
    "business-judgment-rule_fixture_20261016T154708Z.json": "fatal_stub",
    "corporate-criminal-liability_fixture_20261016T154708Z.json": "fatal_stub",
    "petty-theft-dismissal_fixture_20261016T154708Z.json": "fatal_stub",
    "summary_fixture_20261016T154708Z.json": "summary_rollup",
    "summary_live_20261016T154849Z.json": "summary_rollup",
    "summary_live_20261016T155135Z.json": "summary_rollup",
    "summary_live_20261016T160318Z.json": "summary_rollup",
    "summary_live_20261016T160526Z.json": "summary_rollup",
    "summary_live_20261016T161006Z.json": "summary_rollup",
}


@pytest.mark.skipif(not Path(_MOUNT).is_dir(),
                    reason="accepted-product mount not present")
def test_current_accepted_packet_leg_verdicts_pinned():
    """Re-execute the frozen benchmark over the refreshed accepted mount and
    pin each current-packet leg's verdict.  The frozen spec is NOT modified by
    this test; it only records what the frozen gates decide on this packet."""
    import hashlib
    from evaluation.reality_gate import run_benchmark
    raw = frozen._PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == frozen.FROZEN_SHA256

    artifacts = run_benchmark._load_artifacts(Path(_MOUNT), [])
    rep = run_benchmark.evaluate_artifacts(artifacts, SPEC)
    by_name = {a["artifact"].rsplit("/", 1)[-1]: a for a in rep["artifacts"]}

    for name, (expected_pass, expected_failed) in _CURRENT_PACKET_LEG_PINS.items():
        assert name in by_name, name
        rec = by_name[name]
        assert rec["kind"] == "slim_report", (name, rec["kind"])
        assert rec["artifact_passed"] is expected_pass, (
            name, rec["failed_gates"])
        assert rec["failed_gates"] == expected_failed, (
            name, rec["failed_gates"])
        if expected_pass:
            # every passing leg still names its partial recall misses, if any
            for gate in rec["gates"]:
                if gate["gate"] == "recall::citation_controlling_authority":
                    assert gate["passed"] is True
                    assert gate["detail"] == ""
        else:
            recall = next(g for g in rec["gates"]
                          if g["gate"] == "recall::citation_controlling_authority")
            assert recall["measured"]["hits"] == [], name
            assert recall["measured"]["missing"], name

    for name, expected_kind in _CURRENT_PACKET_EXCLUDED_PINS.items():
        assert name in by_name, name
        assert by_name[name]["kind"] == expected_kind, (
            name, by_name[name]["kind"])
        assert by_name[name]["evaluation_scope"] == "none"

    # the recorded history carries falsifying failures (preserved negatives:
    # latency >=300s runs, end-of-month misses, unsupported counter rows),
    # so the whole-mount verdict stays FAIL — honest, not a product pass.
    assert rep["overall_pass"] is False
    # the fresh BJR leg's missing list is exactly the five frozen authorities
    bjr = by_name["business-judgment-rule_live_20261016T161006Z.json"]
    recall = next(g for g in bjr["gates"]
                  if g["gate"] == "recall::citation_controlling_authority")
    assert set(recall["measured"]["missing"]) == set(
        QUESTIONS["business-judgment-rule"]["required_citation_ids"])
    # the repaired petty-theft leg cites the authority the pre-fix leg missed
    petty = by_name["petty-theft-dismissal_live_20261016T160318Z.json"]
    petty_recall = next(g for g in petty["gates"]
                        if g["gate"] == "recall::citation_controlling_authority")
    assert petty_recall["measured"]["hits"] == ["bger_4A_177_2017"]
    assert petty_recall["measured"]["missing"] == ["bger_4A_228_2015"]


# --------------------------------------------------------------------------- #
# gate-contract digest coverage (cycle 38945976309)
#
# frozen_benchmark.json pins the questions, phrases, authority sets, the answer
# language set and the 300 s budget.  These gate values were NOT in it: they were
# literals in gates.py, so a silent edit changed what the frozen benchmark
# accepted without tripping FROZEN_SHA256.  GATE_CONTRACT.json gives them their
# own digest.
# --------------------------------------------------------------------------- #


def test_gate_contract_digest_pin():
    raw = gate_contract._PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == gate_contract.GATE_CONTRACT_SHA256


def test_gate_contract_values_equal_the_literals_they_replaced():
    """No threshold moved; this is added coverage, not a relaxation."""
    c = gate_contract.load_contract()
    assert c["answer"]["expected_answer_method"] == "generative_audit_llm_v2"
    assert c["answer"]["expected_adversarial_method"] == "independent_llm_adversarial_v2"
    assert c["answer"]["min_prose_chars"] == 120
    assert c["source"] == {"required_scheme": "https",
                           "allowed_host": "mcp.opencaselaw.ch"}
    assert c["corruption"] == {"repetition_ngram": 8, "repetition_min_words": 60,
                               "repetition_max_share": 0.35,
                               "repeated_sentence_min_chars": 20,
                               "repeated_sentence_min_sentences": 5,
                               "repeated_sentence_min_repeats": 4,
                               "control_char_min_chars": 200,
                               "control_char_max_ratio": 0.01}
    assert c["multilingual"]["swiss_languages"] == ["fr", "de", "it"]
    assert c["multilingual"]["min_swiss_languages"] == 2
    assert c["recall"]["min_hits_of_frozen_set"] == 1


def test_gates_read_their_thresholds_from_the_contract_not_from_literals():
    assert gates.MIN_RECALL_HITS == 1

    def report(n_chars: int) -> dict:
        return {"answer_status": "ready",
                "answer_method": gate_contract.load_contract()["answer"]["expected_answer_method"],
                "answer_prose": "x" * n_chars, "cited_decision_ids": ["d1"],
                "provider_error": None,
                "adversarial_method": gate_contract.load_contract()["answer"]["expected_adversarial_method"],
                "adversarial_error": None}

    # prose_min_length still separates at exactly the contract's 120 chars
    short = gates.evaluate_structural_from_report(report(119))
    long = gates.evaluate_structural_from_report(report(120))
    assert short[3]["gate"] == long[3]["gate"] == "structural::prose_min_length"
    assert short[3]["passed"] is False and long[3]["passed"] is True

    # the allowed source host still comes from the contract
    from urllib.parse import urlparse
    host = gate_contract.load_contract()["source"]["allowed_host"]
    assert urlparse(f"https://{host}/entscheid/x").hostname == host


def test_gate_contract_tamper_is_refused(tmp_path, monkeypatch):
    contract = gate_contract.load_contract()
    contract["answer"]["min_prose_chars"] = 12          # the weakening edit
    tmp = tmp_path / "GATE_CONTRACT.json"
    tmp.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    monkeypatch.setattr(gate_contract, "_PATH", tmp)
    monkeypatch.setattr(gate_contract, "_CACHED", None)
    with pytest.raises(gate_contract.GateContractError) as excinfo:
        gate_contract.load_contract()
    assert "digest mismatch" in str(excinfo.value)


# --------------------------------------------------------------------------- #
# execution-record integrity (cycle 38945976309)
#
# The retrieval gate recomputes its stored verdict byte-identically; this lane
# had no equivalent, so a hand-edited record passed every test.  These tests
# close that hole and prove each tamper class is detected.
# --------------------------------------------------------------------------- #


RECORDS_DIR = REPO / "results" / "evaluation" / "reality_benchmark"
COMMITTED_RECORDS = sorted(RECORDS_DIR.glob("*.json"))


def test_execution_records_exist():
    assert COMMITTED_RECORDS, "no committed reality-benchmark execution record"


@pytest.mark.parametrize("path", COMMITTED_RECORDS, ids=lambda p: p.name)
def test_committed_execution_record_is_internally_consistent(path):
    problems = run_benchmark.check_record_integrity(run_benchmark.load_record(path), SPEC)
    assert problems == [], problems


def _tampered_record() -> dict:
    return copy.deepcopy(run_benchmark.load_record(RECORDS_DIR / "38934722443.json"))


def _flip_first_failure(record: dict, gate_name: str) -> bool:
    for entry in record["artifacts"]:
        for g in entry.get("gates") or []:
            if g["gate"] == gate_name and g["passed"] is False:
                g["passed"] = True
                g["detail"] = ""
                entry["failed_gates"] = [x for x in entry["failed_gates"]
                                         if x != gate_name]
                entry["artifact_passed"] = not entry["failed_gates"]
                return True
    return False


def test_record_tamper_flipping_a_latency_failure_to_a_pass_is_detected():
    rec = _tampered_record()
    assert _flip_first_failure(rec, "latency::under_budget") is True
    problems = run_benchmark.check_record_integrity(rec, SPEC)
    assert problems, "a flipped latency verdict must be detected"
    assert any("its own measurements say" in p and "latency::under_budget" in p
               for p in problems), problems


def test_record_tamper_flipping_an_authority_recall_failure_is_detected():
    rec = _tampered_record()
    assert _flip_first_failure(rec, "recall::citation_controlling_authority") is True
    problems = run_benchmark.check_record_integrity(rec, SPEC)
    assert any("hit(s) of" in p for p in problems), problems


def test_record_tamper_flipping_a_truth_failure_is_detected():
    rec = _tampered_record()
    assert _flip_first_failure(rec, "truth::art257d2_end_of_month") is True
    problems = run_benchmark.check_record_integrity(rec, SPEC)
    assert any("matched phrase" in p for p in problems), problems


@pytest.mark.parametrize("label,mutate", [
    ("dropped_artifact", lambda r: r["artifacts"].pop()),
    ("inflated_n_evaluated", lambda r: r.__setitem__("n_evaluated", 99)),
    ("foreign_frozen_digest", lambda r: r.__setitem__("frozen_sha256", "0" * 64)),
    ("overall_pass_flipped", lambda r: r.__setitem__("overall_pass", True)),
    ("excluded_artifact_gains_a_verdict",
     lambda r: r["artifacts"][0].__setitem__("evaluation_scope", "full_match")),
])
def test_record_tamper_classes_are_detected(label, mutate):
    rec = _tampered_record()
    mutate(rec)
    assert run_benchmark.check_record_integrity(rec, SPEC), label


def test_record_tamper_blanking_a_failure_detail_is_detected():
    rec = _tampered_record()
    n = 0
    for entry in rec["artifacts"]:
        for g in entry.get("gates") or []:
            if g["passed"] is False:
                g["detail"] = ""
                n += 1
    assert n > 0, "fixture record carries no failing gate to tamper with"
    assert run_benchmark.check_record_integrity(rec, SPEC)


def test_record_integrity_check_declares_what_it_cannot_check():
    """Claim ceiling: gates without a measured payload stay on trust."""
    coverage = run_benchmark.gate_arithmetic_coverage()
    assert any("recall" in c for c in coverage)
    assert any("latency" in c for c in coverage)
    assert not any("counter_classifications" in c for c in coverage), (
        "structural bundle gates carry no measured payload and are NOT re-derived "
        "from the record; keep them out of the coverage claim")


def test_check_record_integrity_declares_its_own_untamperable_classes():
    """Self-audit: the check must name what it cannot catch.

    Three tamper classes were found by adversarial probing of this cycle's own
    check. If the list ever shrinks without a test failing, a reader would
    believe the check is stronger than it is.
    """
    gaps = run_benchmark.check_record_integrity_known_gaps()
    assert len(gaps) == 3, gaps
    assert "deleting_an_artifact_and_renumbering_every_count" in gaps
    assert "flipping_a_structural_gate_failure_to_a_pass" in gaps
    assert "rewriting_a_gate_measured_payload_to_match_a_flipped_verdict" in gaps
    # and each really is undetectable, so the list is not self-flattering
    spec = frozen.load_frozen()
    rec = copy.deepcopy(run_benchmark.load_record(RECORDS_DIR / "38934722443.json"))
    for entry in rec["artifacts"]:
        for g in entry.get("gates") or []:
            if g["gate"].startswith("structural::") and g["passed"] is False:
                g["passed"], g["detail"] = True, ""
                entry["failed_gates"] = [x for x in entry["failed_gates"]
                                         if not x.startswith("structural::")]
                entry["artifact_passed"] = not entry["failed_gates"]
                break
    assert run_benchmark.check_record_integrity(rec, spec) == []


def test_bundle_validation_clean_is_re_derived_from_its_measurements():
    """The one structural gate that does carry a payload is now covered.

    Synthesised, because no committed record contains a bundle_validation_clean
    failure — it passes everywhere on the accepted packet, so a test that waited
    for one would silently never run.
    """
    contract = "structural::bundle_validation_clean"
    assert any(contract in c for c in run_benchmark.gate_arithmetic_coverage())
    spec = frozen.load_frozen()
    rec = copy.deepcopy(run_benchmark.load_record(RECORDS_DIR / "38934722443.json"))
    entry = next(e for e in rec["artifacts"] if e.get("gates"))
    for g in entry["gates"]:
        if g["gate"] == contract:
            assert g["passed"] is True
            g["measured"] = {"validation_errors": ["answer cites unknown id dX"]}
            break
    else:
        pytest.fail(f"{contract} not present in the fixture record")
    problems = run_benchmark.check_record_integrity(rec, spec)
    assert any(contract in p for p in problems), problems
    assert any("bundle validation errors" in p for p in problems), problems
