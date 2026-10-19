"""Tests for the cached-OpenCaseLaw query-map bundle producer and its benchmark.

These are plain pytest-style functions with no fixtures, so the lane's
``evaluation/no_pytest_runner.py`` shim can execute them in the producer image
where pytest is ABSENT.  Anything the shim cannot express is reported
UNSUPPORTED and counted NOT-RUN, never as passed.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from evaluation.query_map.bundle_producer import (
    CANDIDATE_COUNTER_UNCERTAINTY, alnum_core, build_bundle, index_cache,
    match_frozen_id, normalise_text, read_cache, row_text,
)
from evaluation.query_map.harness import evaluate_query_map_bundle, geometry_signature
from evaluation.query_map import run_cached_bundle_benchmark as bench

REPO = Path(__file__).resolve().parent.parent.parent
SPEC = REPO / "evaluation/retrieval_gate/frozen_retrieval_benchmark.json"
CACHE = REPO / "results/evaluation/retrieval_benchmark/cache"

#: Frozen digests. These tests ASSERT the pins; they never rewrite them.
FROZEN_SPEC_SHA256 = bench.FROZEN_SPEC_SHA256


def _spec():
    return json.loads(SPEC.read_text(encoding="utf-8"))


def _index():
    return index_cache(read_cache(CACHE), _spec())


# ---------------------------------------------------------------- frozen pins
def test_frozen_spec_digest_is_the_pinned_one():
    assert hashlib.sha256(SPEC.read_bytes()).hexdigest() == FROZEN_SPEC_SHA256


def test_producer_module_introduces_no_threshold_constant():
    """Every constant in the producer is either a layout constant or the single
    declared fixture-grade uncertainty. No tunable gate threshold exists."""
    src = (REPO / "evaluation/query_map/bundle_producer.py").read_text(encoding="utf-8")
    for banned in ("MIN_RECALL", "RECALL_THRESHOLD", "SUPPORT_THRESHOLD",
                   "PASS_AT", "SCORE_CUTOFF", "MIN_SUPPORT"):
        assert banned not in src, banned


def test_uncertainty_constant_is_declared_and_not_calibrated():
    assert CANDIDATE_COUNTER_UNCERTAINTY == 0.5
    spec = _spec()
    assert "counter_uncertainty" not in json.dumps(spec), \
        "the frozen spec pins no counter_uncertainty; the constant is fixture-grade"


# ------------------------------------------------------- frozen id/lexical rules
def test_alnum_core_strips_leading_court_tokens():
    assert alnum_core("bger_4A_219_2015") == "4a2192015"
    assert alnum_core("BGE 142 IV 333") == "142iv333"
    assert alnum_core("bge_BGE_117_II_415") == "117ii415"


def test_match_frozen_id_is_auditable_and_respects_min_core_length():
    row = {"decision_id": "bger_4A_219_2015", "canonical_decision_id": "bger_4A_219_2015"}
    m = match_frozen_id(row, "bger_4A_219_2015", min_core_length=6)
    assert m and m["matched_core"] == "4a2192015" and m["row_decision_id"] == "bger_4A_219_2015"
    assert match_frozen_id(row, "x", min_core_length=6) is None


def test_normalisation_strips_marks_and_diacritics_per_frozen_marker_rule():
    # The frozen marker_rule specifies mark-stripping and NFKD/casefolding; it
    # does NOT collapse whitespace, so the assertion is whitespace-tolerant.
    assert " ".join(normalise_text("<mark>Art. 257d</mark> OR").split()) == "art. 257d or"
    assert "é" not in normalise_text("résiliation abusive")
    assert normalise_text("RÉSILIATION").startswith("resiliation")


def test_row_text_is_title_regeste_snippet():
    assert row_text({"title": None, "regeste": "Regeste", "snippet": "S"}) == "regeste s"


# ------------------------------------------------------------- cache indexing
def test_every_committed_envelope_maps_to_a_frozen_query():
    envelopes = read_cache(CACHE)
    idx = _index()
    assert len(envelopes) == 24
    assert len(idx) == 24, sorted(idx)
    expected = {(q["slug"], channel, lang)
                for q in _spec()["questions"]
                for channel in ("baseline", "counter")
                for lang in ("de", "fr", "it")}
    assert set(idx) == expected


def test_index_cache_ignores_an_unknown_query_rather_than_guessing():
    spec = _spec()
    bogus = {"url": "https://mcp.opencaselaw.ch/api/decisions?query=not+a+frozen+query",
             "body": "{}", "status": 200}
    assert index_cache([bogus], spec) == {}


# ------------------------------------------------------------- bundle building
def test_bundle_is_built_from_real_rows_and_passes_the_accepted_harness():
    b = build_bundle("rent-default", _index(), _spec())
    assert b["meta"]["n_decisions"] > 100, b["meta"]["n_decisions"]
    rep = evaluate_query_map_bundle(b["initial"], b["final"])
    assert rep["pass"], rep["checks"]
    assert rep["checks"]["source_urls_valid"] is True
    assert rep["checks"]["duplicate_free"] is True


def test_bundle_covers_all_three_query_languages():
    for slug in ("rent-default", "corporate-criminal-liability",
                 "business-judgment-rule", "petty-theft-dismissal"):
        b = build_bundle(slug, _index(), _spec())
        assert set(b["meta"]["languages"]) == {"de", "fr", "it"}, slug


def test_duplicate_suppression_is_recorded_not_silent():
    b = build_bundle("petty-theft-dismissal", _index(), _spec())
    dupes = b["initial"]["provenance"]["remote"]["duplicates_suppressed"]
    assert dupes, "the frozen duplicate rule must actually fire on real input"
    assert all("kept_from" in d and "suppressed_from" in d for d in dupes)
    ids = [d["decision_id"] for d in b["final"]["decisions"]]
    assert len(ids) == len(set(ids))


def test_geometry_is_identical_in_initial_and_final():
    b = build_bundle("business-judgment-rule", _index(), _spec())
    assert geometry_signature(b["initial"]) == geometry_signature(b["final"])


def test_progressive_phases_are_map_ready_then_complete():
    b = build_bundle("business-judgment-rule", _index(), _spec())
    assert b["initial"]["provenance"]["phase"] == "map_ready"
    assert b["final"]["provenance"]["phase"] == "complete"


def test_answer_carries_a_citation_set_and_no_fabricated_prose():
    b = build_bundle("business-judgment-rule", _index(), _spec())
    ans = b["final"]["answer"]
    assert ans["text"] is None and ans["generation"] == "none"
    assert ans["cited_decision_ids"]
    ids = {d["decision_id"] for d in b["final"]["decisions"]}
    assert set(ans["cited_decision_ids"]) <= ids


def test_counter_labels_carry_frozen_marker_evidence():
    b = build_bundle("rent-default", _index(), _spec())
    labels = [d for d in b["final"]["decisions"] if d["counter_status"] == "candidate-limiting"]
    assert labels, "the frozen marker rule must fire on at least one question"
    for d in labels:
        assert "frozen marker_rule match" in d["counter_evidence"]
        assert d["counter_uncertainty"] == CANDIDATE_COUNTER_UNCERTAINTY


def test_producer_is_deterministic_byte_for_byte():
    idx = _index()
    spec = _spec()
    a = build_bundle("petty-theft-dismissal", idx, spec)
    c = build_bundle("petty-theft-dismissal", idx, spec)
    assert hashlib.sha256(json.dumps(a, sort_keys=True).encode()).hexdigest() == \
           hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()


def test_provenance_never_claims_a_live_call():
    b = build_bundle("rent-default", _index(), _spec())
    prov = b["final"]["provenance"]
    assert prov["fixture_mode"] is True
    assert prov["remote"]["request_summary"]["network_calls"] == 0


# --------------------------------------------------- falsification legs fire
def test_blanking_counter_evidence_breaks_the_accepted_contract():
    b = build_bundle("rent-default", _index(), _spec())
    blanked = bench._blank_counter_evidence(b["final"])
    rep = evaluate_query_map_bundle(b["initial"], blanked)
    assert rep["checks"]["counter_classifications_supported"] is False


def test_breaking_one_source_url_breaks_the_accepted_contract():
    b = build_bundle("rent-default", _index(), _spec())
    broken = bench._break_one_source_url(b["final"])
    rep = evaluate_query_map_bundle(b["initial"], broken)
    assert rep["checks"]["source_urls_valid"] is False


def test_non_vacuity_scaffold_only_fires_when_no_label_was_emitted():
    b = build_bundle("corporate-criminal-liability", _index(), _spec())
    assert b["meta"]["n_counter_candidates"] == 0
    scaffolded, injected = bench._ensure_one_counter_label(b["final"])
    assert injected is True
    rep = evaluate_query_map_bundle(b["initial"], bench._blank_counter_evidence(scaffolded))
    assert rep["checks"]["counter_classifications_supported"] is False


def test_non_vacuity_scaffold_is_a_no_op_when_a_label_already_exists():
    b = build_bundle("rent-default", _index(), _spec())
    scaffolded, injected = bench._ensure_one_counter_label(b["final"])
    assert injected is False
    assert scaffolded == b["final"]


# -------------------------------------------------------- the negative result
def test_counter_authority_is_empty_for_two_of_four_frozen_questions():
    """ACCEPTED NEGATIVE RESULT. If this ever goes green the frozen inputs moved."""
    counts = {q["slug"]: build_bundle(q["slug"], _index(), _spec())["meta"]["n_counter_candidates"]
              for q in _spec()["questions"]}
    assert counts == {"rent-default": 16, "corporate-criminal-liability": 0,
                      "business-judgment-rule": 0, "petty-theft-dismissal": 4}, counts


def test_benchmark_refuses_a_drifted_frozen_spec():
    spec = SPEC.with_suffix(".drift.json")
    spec.write_text(_spec_text := SPEC.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    try:
        code, rec = bench.run_benchmark("DRIFT-TEST", Path("/tmp/opencode/drift"),
                                        Path("/tmp/opencode/drift"), spec, CACHE)
        assert code == 2 and rec["verdict"] == "ENVIRONMENT_OR_VACUOUS"
        assert "frozen spec digest drift" in rec["detail"]
    finally:
        spec.unlink()


def test_benchmark_writes_nothing_into_the_repo_on_a_scratch_run():
    import subprocess, sys
    before = sorted(p.name for p in (REPO / "results/evaluation/query_map_cached_bundle_benchmark").glob("*")) \
        if (REPO / "results/evaluation/query_map_cached_bundle_benchmark").exists() else []
    subprocess.run([sys.executable, "-m", "evaluation.query_map.run_cached_bundle_benchmark",
                    "--run-id", "SCRATCH-TEST", "--out-dir", "/tmp/opencode/scratch-test",
                    "--report-dir", "/tmp/opencode/scratch-test"],
                   cwd=str(REPO), capture_output=True, text=True, check=False)
    after = sorted(p.name for p in (REPO / "results/evaluation/query_map_cached_bundle_benchmark").glob("*")) \
        if (REPO / "results/evaluation/query_map_cached_bundle_benchmark").exists() else []
    assert before == after