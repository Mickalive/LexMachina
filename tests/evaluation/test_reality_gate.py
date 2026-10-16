#!/usr/bin/env python3
"""Frozen tests for the evaluation-lane reality benchmark (direction v49).

These tests pin the benchmark itself: they fail if the frozen spec is
tampered with (digest pin) and they prove every gate CAN fail — a gate that
cannot fail is not a benchmark.  Pure standard library + pytest.
"""
import json

import pytest

from evaluation.reality_gate import frozen, gates

SPEC = frozen.load_frozen()
QUESTIONS = frozen.question_by_slug(SPEC)

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
