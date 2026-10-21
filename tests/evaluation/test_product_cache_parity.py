"""Tests for the product-cache retrieval/counter-authority parity falsifier.

Scope extension, disclosed: this file was added to the lane suite by run
39619144928 (same convention as the accepted scope extensions of runs
39111232991 and 39092033997).  Rewritten for the V2 two-family instrument by
repair round 1 of rejected cycle 39628161040 (run 39631600439).  Runnable by
the stdlib shim ``evaluation/no_pytest_runner.py`` as well as pytest: plain
zero-argument ``test_*`` functions, module-level imports and
``pytest.mark.skipif`` only.

The V1 chain (hypothesis, freeze record, measurement records) is never
modified: the V1 hypothesis/freeze record are byte-preserved and are pinned by
the V2 freeze record; the V1 measurement records are compared 1:1 against the
V2 coverage family so that the repair provably weakened nothing.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from evaluation import product_cache_parity as pcp  # noqa: E402
from evaluation.retrieval_gate import frozen as rg_frozen  # noqa: E402

RUN_ID = "39631600439"
RECORD = REPO_ROOT / "results" / "evaluation" / "product_cache_parity" / f"{RUN_ID}.json"
V1_RUN_ID = "39619144928"
V1_RECORD = REPO_ROOT / "results" / "evaluation" / "product_cache_parity" / f"{V1_RUN_ID}.json"
REJECTED_V1_RUN_ID = "39628161040"
REJECTED_V1_RECORD = (REPO_ROOT / "results" / "evaluation" / "product_cache_parity"
                      / f"{REJECTED_V1_RUN_ID}.json")


def _hypothesis() -> dict:
    return json.loads(pcp.HYPOTHESIS_PATH.read_text(encoding="utf-8"))


def _freeze() -> dict:
    return json.loads(pcp.FREEZE_RECORD_PATH.read_text(encoding="utf-8"))


def _hypothesis_v1() -> dict:
    return json.loads(pcp.HYPOTHESIS_V1_PATH.read_text(encoding="utf-8"))


def _freeze_v1() -> dict:
    return json.loads(pcp.FREEZE_RECORD_V1_PATH.read_text(encoding="utf-8"))


def _synth(question_slug: str = "synth-question",
           authority_ids=None, counter_ids=None) -> tuple[dict, dict, dict]:
    """Minimal spec / baseline / envelopes triple for pure-function tests."""
    spec = {
        "id_match_rules": {"min_core_length": 6},
        "questions": [{
            "slug": question_slug,
            "queries": {
                "baseline": {"fr": "Alpha question text about leasing",
                             "de": "Alpha frage text ueber miete",
                             "it": "Alpha domanda testo su locazione"},
                "counter": {"fr": "Alpha exception limite reprise",
                            "de": "Alpha ausnahme grenze wiederaufnahme",
                            "it": "Alpha eccezione limite ripresa"},
            },
            "authority_ids": list(authority_ids or []),
            "known_counter_ids": [{"id": i} for i in (counter_ids or [])],
        }],
    }
    base_text = spec["questions"][0]["queries"]["baseline"]["fr"]
    baseline_record = {
        "schema": "lex-retrieval-benchmark/1",
        "frozen_sha256": rg_frozen.FROZEN_SHA256,
        "queries": [{
            "slug": question_slug, "channel": "baseline", "language": "fr",
            "query": base_text, "query_key": "synth-baseline-fr",
            "rows": [{"decision_id": "bge_BGE_100_II_1",
                      "canonical_decision_id": "bge_BGE_100_II_1",
                      "citation_string_de": "BGE 100 II 1",
                      "canonical_url": "https://www.opencaselaw.ch/x",
                      "language": "de"},
                     {"decision_id": "bge_BGE_200_III_9",
                      "canonical_decision_id": "bge_BGE_200_III_9",
                      "citation_string_de": "BGE 200 III 9",
                      "canonical_url": "https://www.opencaselaw.ch/y",
                      "language": "de"}],
        }],
    }
    envelopes = {
        rg_frozen.normalize_text(base_text): [
            {"file": "syn/env1.json", "n_rows": 2,
             "rows": [dict(r) for r in baseline_record["queries"][0]["rows"]]}],
    }
    hypothesis = {
        "claim_ceiling": "synthetic ceiling for unit tests",
        "metric_FROZEN": {"success_rule_FROZEN": "synthetic rule"},
    }
    return spec, baseline_record, envelopes, hypothesis


def _synth_asymmetric():
    """The F3 case: the comparator pool contains a text the product never ran.

    The plain client answered ``baseline/fr`` AND ``counter/de``.  The product
    cache executed ``baseline/fr`` only.  The frozen counter id that only the
    never-executed ``counter/de`` text produced must be attributed to coverage,
    never converted into a same-text falsification.
    """
    spec, baseline, envelopes, hypothesis = _synth(
        counter_ids=["bge_BGE_100_II_1", "bge_BGE_200_III_9"])
    q = spec["questions"][0]
    fr_rows = [dict(r) for r in baseline["queries"][0]["rows"]]
    fr_hit = [r for r in fr_rows if r["decision_id"] == "bge_BGE_100_II_1"]
    de_only = [dict(r) for r in fr_rows if r["decision_id"] == "bge_BGE_200_III_9"]
    # the plain client's answer to the text the product never executed
    baseline["queries"][0]["rows"] = fr_hit
    baseline["queries"].append({
        "slug": "synth-question", "channel": "counter", "language": "de",
        "query": q["queries"]["counter"]["de"], "query_key": "synth-counter-de",
        "rows": de_only,
    })
    # the product pool: only the executed text, and only its own row
    envelopes = {
        rg_frozen.normalize_text(q["queries"]["baseline"]["fr"]): [
            {"file": "syn/env_fr.json", "n_rows": len(fr_hit),
             "rows": [dict(r) for r in fr_hit]}],
    }
    return spec, baseline, envelopes, hypothesis


# --------------------------------------------------------------------------- #
# the freeze itself
# --------------------------------------------------------------------------- #
def test_hypothesis_is_frozen_before_execution_with_an_honest_disclosure():
    hyp = _hypothesis()
    assert hyp["frozen_before_execution"] is True
    assert hyp["schema"] == "lex-evaluation-product-cache-parity-hypothesis/2"
    d = hyp["pre_freeze_disclosure_HONEST_V2"]
    assert d["what_happened"] and d["what_the_author_already_knows"]
    assert d["what_is_still_measured_fresh"] and d["why_this_does_not_launder_the_result"]
    # the disclosure states the already-known outcome; it never pretends to be
    # a pre-registered prediction
    assert "pre-registered prediction" in d["what_happened"]
    assert "pre_freeze_expectation_disclosed" in d
    # the disclosure names both gate families, so the attribution is disclosed
    assert "coverage" in d["pre_freeze_expectation_disclosed"]


def test_v1_hypothesis_and_freeze_record_are_byte_preserved():
    """The superseded V1 spec chain is preserved, not rewritten."""
    freeze = _freeze()
    pres = freeze["superseded_spec_byte_preserved"]
    assert pres["v1_hypothesis"]["path"].endswith("PRODUCT_CACHE_PARITY_HYPOTHESIS_V1.json")
    assert pres["v1_hypothesis"]["sha256"] == hashlib.sha256(
        pcp.HYPOTHESIS_V1_PATH.read_bytes()).hexdigest()
    assert pres["v1_freeze_record"]["sha256"] == hashlib.sha256(
        pcp.FREEZE_RECORD_V1_PATH.read_bytes()).hexdigest()
    # both V1 measurement records are re-pinned by digest
    for relpath, digest in pres["v1_records"].items():
        p = REPO_ROOT / relpath
        assert p.is_file()
        assert hashlib.sha256(p.read_bytes()).hexdigest() == digest
    # and the V1 hypothesis is still the V1 document
    v1 = _hypothesis_v1()
    assert v1["schema"] == "lex-evaluation-product-cache-parity-hypothesis/1"
    assert "pre_freeze_reconnaissance_HONEST" in v1
    assert _freeze_v1()["hypothesis"]["sha256"] == hashlib.sha256(
        pcp.HYPOTHESIS_V1_PATH.read_bytes()).hexdigest()


def test_freeze_record_pins_match_current_bytes():
    freeze = _freeze()
    assert freeze["hypothesis"]["sha256"] == hashlib.sha256(
        pcp.HYPOTHESIS_PATH.read_bytes()).hexdigest()
    spec_path = REPO_ROOT / "evaluation" / "retrieval_gate" / "frozen_retrieval_benchmark.json"
    assert freeze["frozen_inputs"]["frozen_spec"]["sha256"] == \
        hashlib.sha256(spec_path.read_bytes()).hexdigest() == rg_frozen.FROZEN_SHA256
    base_path = REPO_ROOT / pcp.BASELINE_RECORD_RELPATH
    assert freeze["frozen_inputs"]["baseline_record"]["sha256"] == \
        hashlib.sha256(base_path.read_bytes()).hexdigest()


def test_v2_freeze_record_declares_both_gated_families_and_keeps_the_failures():
    freeze = _freeze()
    reused = freeze["frozen_rules_reused_verbatim"]
    assert reused["zero_new_thresholds"] is True
    assert reused["frozen_id_sets_unchanged"] is True
    assert reused["matcher_unchanged"] is True
    # the gate count grows, the failing comparisons do not
    assert reused["gate_count_before"] == 7
    assert reused["gate_count_after"] == 14
    assert reused["failing_comparisons_before"] == 7
    assert reused["failing_comparisons_after_expected"] == 7
    hyp = _hypothesis()
    names = hyp["gate_names_FROZEN_V2"]
    assert any(n.startswith("parity::same_query_") for n in names)
    assert any(n.startswith("coverage::union_frozen_texts_") for n in names)


def test_identity_mapping_rule_consumes_no_analyst_mapping():
    hyp = _hypothesis()
    assert hyp["mapping_rule_IDENTITY_ONLY"]["analyst_mapping_consumed"] is False
    # the module never imports the retracted instrument's mapping machinery
    src = (REPO_ROOT / "evaluation" / "product_cache_parity.py").read_text(encoding="utf-8")
    assert "PRODUCT_COUNTER_RECALL_HYPOTHESIS" not in src
    assert "analyst_mapping" not in src


def test_success_rule_and_verdict_vocabulary_are_frozen():
    hyp = _hypothesis()
    statement = hyp["metric_FROZEN"]["success_rule_FROZEN"]
    assert "PASS_NO_PARITY_REGRESSION" in statement
    assert "FAIL_PRODUCT_CACHE_PARITY" in statement
    assert "NOT_MEASURED" in statement
    # the success rule must cover BOTH gated families
    assert "family" in statement
    vocab = hyp["verdict_vocabulary_FROZEN"]
    assert vocab["PASS_NO_PARITY_REGRESSION"] == 0
    assert vocab["FAIL_PRODUCT_CACHE_PARITY"] == 1
    assert vocab["NOT_MEASURED"] == 2
    assert vocab["ENVIRONMENT_OR_VACUOUS"] == 2


def test_claim_ceiling_keeps_the_standing_orders():
    hyp = _hypothesis()
    ceiling = hyp["claim_ceiling"]
    for needle in ("DO-NOT-SERVE", "REPORTED-ONLY", "human_gate_ready",
                   "does NOT re-issue the retracted 39111232991"):
        assert needle in ceiling


# --------------------------------------------------------------------------- #
# pure-function behaviour on synthetic inputs (scratch: never touches defaults)
# --------------------------------------------------------------------------- #
def test_identical_sides_pass_and_battery_holds():
    spec, baseline, envelopes, hyp = _synth(counter_ids=["bge_BGE_100_II_1",
                                                         "bge_BGE_200_III_9"])
    out = pcp.evaluate(hyp, spec, baseline, envelopes)
    assert out["verdict"] == "PASS_NO_PARITY_REGRESSION"
    assert out["exit_code"] == 0
    assert out["falsification_gates"] == []
    assert out["same_text_parity_verdict"] == "PASS"
    assert out["coverage_verdict"] == "PASS"
    assert out["verdict_scope"] == "none"
    assert out["non_vacuity"]["all_hold"] is True


def test_product_missing_one_comparator_hit_is_falsified():
    spec, baseline, envelopes, hyp = _synth(counter_ids=["bge_BGE_100_II_1",
                                                         "bge_BGE_200_III_9"])
    # product pool keeps only the first row -> 1 hit vs comparator 2
    envelopes[rg_frozen.normalize_text(
        spec["questions"][0]["queries"]["baseline"]["fr"])][0]["rows"] = \
        [dict(baseline["queries"][0]["rows"][0])]
    out = pcp.evaluate(hyp, spec, baseline, envelopes)
    assert out["verdict"] == "FAIL_PRODUCT_CACHE_PARITY"
    assert out["exit_code"] == 1
    # the executed text IS the only comparator text here, so BOTH families fail
    assert out["falsification_gates"] == [
        "parity::same_query_counter_not_below_baseline::synth-question",
        "coverage::union_frozen_texts_counter_not_below_baseline::synth-question",
    ]
    assert out["verdict_scope"] == "same_text_and_coverage"


def test_empty_frozen_id_set_is_not_measurable_never_a_pass():
    spec, baseline, envelopes, hyp = _synth(authority_ids=[], counter_ids=[])
    out = pcp.evaluate(hyp, spec, baseline, envelopes)
    names = {g["gate"]: g["passed"] for g in out["gates"]}
    assert names["product::authority_recall::synth-question"] is None
    assert names["product::counter_recall::synth-question"] is None
    assert names["parity::same_query_counter_not_below_baseline::synth-question"] is None
    assert names["coverage::union_frozen_texts_counter_not_below_baseline::synth-question"] is None
    assert out["verdict"] == "ENVIRONMENT_OR_VACUOUS"  # battery cannot prove C1
    assert out["exit_code"] == 2


def test_blank_pool_fails_parity_and_oracle_passes_it():
    spec, baseline, envelopes, hyp = _synth(counter_ids=["bge_BGE_100_II_1",
                                                         "bge_BGE_200_III_9"])
    base_text = spec["questions"][0]["queries"]["baseline"]["fr"]
    # blanked observed pool: the parity gate must falsify, and the battery's own
    # re-scored controls (C1 blanked / C2 oracle / C3 executed-text) must hold
    blanked = {rg_frozen.normalize_text(base_text): []}
    out_blank = pcp.evaluate(hyp, spec, baseline, blanked)
    assert out_blank["verdict"] == "FAIL_PRODUCT_CACHE_PARITY"
    assert out_blank["exit_code"] == 1
    assert out_blank["non_vacuity"]["all_hold"] is True
    # oracle: product pool IS the comparator rows
    oracle = {rg_frozen.normalize_text(base_text): [
        {"file": "syn/oracle.json", "n_rows": 2,
         "rows": [dict(r) for r in baseline["queries"][0]["rows"]]}]}
    out_oracle = pcp.evaluate(hyp, spec, baseline, oracle)
    assert out_oracle["verdict"] == "PASS_NO_PARITY_REGRESSION"
    assert out_oracle["non_vacuity"]["battery"][1]["holds"] is True
    assert out_oracle["non_vacuity"]["battery"][2]["holds"] is True


def test_non_executed_frozen_texts_are_reported_not_gated():
    spec, baseline, envelopes, hyp = _synth(counter_ids=["bge_BGE_100_II_1"])
    out = pcp.evaluate(hyp, spec, baseline, envelopes)
    cell = out["cells"][0]
    reach = cell["language_reach"]
    assert reach["baseline/fr"]["status"] == "EXECUTED"
    for key in ("baseline/de", "baseline/it", "counter/fr", "counter/de", "counter/it"):
        assert reach[key]["status"] == "NOT_EXECUTED"
    # no gate carries a language-coverage name
    assert not [g for g in out["gates"] if "language" in g["gate"] or "multilingual" in g["gate"]]


# --------------------------------------------------------------------------- #
# F3 (audit): a non-executed text's coverage may never become a same-text
# falsification
# --------------------------------------------------------------------------- #
def test_non_executed_text_coverage_cannot_become_a_same_text_falsification():
    spec, baseline, envelopes, hyp = _synth_asymmetric()
    out = pcp.evaluate(hyp, spec, baseline, envelopes)
    names = {g["gate"]: g for g in out["gates"]}
    same_text = names["parity::same_query_counter_not_below_baseline::synth-question"]
    coverage = names["coverage::union_frozen_texts_counter_not_below_baseline::synth-question"]
    # the executed text compares equal -> the same-text family PASSES
    assert same_text["passed"] is True
    assert same_text["measured"]["comparator_scope"] == "executed_text"
    # the union comparator reaches one id more -> the coverage family FAILS
    assert coverage["passed"] is False
    assert coverage["measured"]["comparator_scope"] == "union_all_frozen_texts"
    # the falsification is attributed to coverage only
    assert out["same_text_parity_verdict"] == "PASS"
    assert out["coverage_verdict"] == "FAIL"
    assert out["verdict_scope"] == "coverage"
    assert out["falsification_gates"] == [
        "coverage::union_frozen_texts_counter_not_below_baseline::synth-question"]
    # and the comparator-only id is attributed to the text the product never ran
    dec = [d for d in out["gate_decomposition"]
           if d["slug"] == "synth-question" and d["kind"] == "counter"][0]
    assert dec["comparator_only_ids"] == ["bge_BGE_200_III_9"]
    assert dec["comparator_only_ids_from_executed_texts"] == []
    assert dec["comparator_only_ids_from_non_executed_texts"] == ["bge_BGE_200_III_9"]
    assert dec["comparator_only_attribution"]["bge_BGE_200_III_9"] == ["counter/de"]
    # the same-text family is never charged with the never-executed text
    assert same_text["measured"]["comparator_texts"] == ["baseline/fr"]
    assert "counter/de" not in same_text["measured"]["comparator_texts"]


def test_asymmetric_case_does_not_report_a_language_named_gate():
    spec, baseline, envelopes, hyp = _synth_asymmetric()
    out = pcp.evaluate(hyp, spec, baseline, envelopes)
    assert not [g for g in out["gates"] if "de" in g["gate"].split("::")[-1]]


# --------------------------------------------------------------------------- #
# committed record conformance (claim-bearing run of this cycle)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not RECORD.is_file(),
                    reason=f"no committed record at {RECORD}")
def test_committed_record_conformance():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    assert rec["schema"] == pcp.SCHEMA
    assert rec["run_id"] == RUN_ID
    assert rec["hypothesis"]["sha256"] == hashlib.sha256(
        pcp.HYPOTHESIS_PATH.read_bytes()).hexdigest()
    assert rec["frozen_spec"]["sha256"] == rg_frozen.FROZEN_SHA256
    assert rec["network_requests"] == 0
    assert rec["no_174k_benchmark_rerun"] is True
    assert rec["no_new_thresholds"] is True
    assert rec["claim_ceiling"]
    assert rec["verdict"] in {"PASS_NO_PARITY_REGRESSION", "FAIL_PRODUCT_CACHE_PARITY",
                              "NOT_MEASURED", "ENVIRONMENT_OR_VACUOUS"}
    # fail-closed flags stay false on every verdict
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session", "owner_decision_required"):
        assert rec["standing_orders"][key] is False
    assert rec["rehash_after"]["all_pins_hold"] is True
    assert rec["non_vacuity"]["all_hold"] in (True, False)
    # both gated families are published with their own verdict
    assert rec["verdict_scope"] in {"same_text", "coverage", "same_text_and_coverage",
                                    "none"}
    assert rec["same_text_parity_verdict"] in {"PASS", "FAIL", "NOT_MEASURED"}
    assert rec["coverage_verdict"] in {"PASS", "FAIL", "NOT_MEASURED"}


@pytest.mark.skipif(not RECORD.is_file(),
                    reason=f"no committed record at {RECORD}")
def test_committed_record_reproduces_offline():
    """Re-evaluating the recorded inputs reproduces the recorded verdict."""
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    mount = pcp.resolve_product_mount(str(rec["product"]["mount"]))
    assert mount is not None
    cache_dir = mount / "results" / "product" / "query_cache"
    _, inv = pcp.cache_inventory(cache_dir)
    assert inv == rec["product"]["query_cache_inventory_sha256"]
    envelopes = pcp.scan_identity_envelopes(cache_dir)
    spec = rg_frozen.load_frozen()
    baseline = json.loads((REPO_ROOT / pcp.BASELINE_RECORD_RELPATH).read_text(encoding="utf-8"))
    out = pcp.evaluate(_hypothesis(), spec, baseline, envelopes)
    assert out["verdict"] == rec["verdict"]
    assert out["falsification_gates"] == rec["falsification_gates"]
    assert out["verdict_scope"] == rec["verdict_scope"]
    assert out["same_text_parity_verdict"] == rec["same_text_parity_verdict"]
    assert out["coverage_verdict"] == rec["coverage_verdict"]
    assert out["coverage_attribution_summary"] == rec["coverage_attribution_summary"]


# --------------------------------------------------------------------------- #
# nothing weakened: the V1 falsifiers survive 1:1 in the V2 coverage family
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not RECORD.is_file(),
                    reason=f"no committed record at {RECORD}")
def test_v1_falsifier_measurements_are_preserved_one_to_one():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    pres = rec["v1_preservation"]
    assert pres["all_preserved"] is True
    for rid in (REJECTED_V1_RUN_ID, V1_RUN_ID):
        info = pres["records"][rid]
        assert info["present"] is True
        assert info["all_preserved"] is True
        assert info["v1_falsifier_gate_count"] == 8
        for m in info["gate_mapping"]:
            assert m["v2_gate"].startswith("coverage::union_frozen_texts_")
            assert m["passed_identical"] is True
            assert m["measured_differences"] == []
            assert m["v1_comparator_hits"] == m["v2_comparator_hits"]
            assert m["v1_product_hits"] == m["v2_product_hits"]


@pytest.mark.skipif(not RECORD.is_file(),
                    reason=f"no committed record at {RECORD}")
def test_v1_failures_are_still_failures_in_v2():
    """The negative result of the rejected cycle is NOT downgraded."""
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    pres = rec["v1_preservation"]
    for rid in (REJECTED_V1_RUN_ID, V1_RUN_ID):
        info = pres["records"][rid]
        v1_failed = {n.replace("parity::same_query_", "coverage::union_frozen_texts_")
                     for n in info["v1_failed_falsifier_gates"]}
        v2_failed = set(info["v2_failed_coverage_gates"])
        assert v1_failed == v2_failed
        assert len(v2_failed) == 7
    # and the top-level verdict is still a failure driven by coverage
    assert rec["verdict"] == "FAIL_PRODUCT_CACHE_PARITY"
    assert rec["exit_code"] == 1
    assert rec["coverage_verdict"] == "FAIL"
    assert rec["verdict_scope"] == "coverage"


@pytest.mark.skipif(not RECORD.is_file(),
                    reason=f"no committed record at {RECORD}")
def test_comparator_only_ids_come_only_from_never_executed_texts():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    att = rec["coverage_attribution_summary"]
    assert att["n_comparator_only_ids"] == 18
    assert att["n_comparator_only_ids_from_non_executed_texts"] == 18
    assert att["n_comparator_only_ids_from_executed_texts"] == 0
    assert att["all_comparator_only_ids_come_from_non_executed_texts"] is True
    # the product executed one of the six frozen texts per question
    assert att["n_executed_texts_total"] == 4
    assert att["n_frozen_texts_total"] == 24
    # every gated cell is decomposed per (channel, language)
    for d in rec["gate_decomposition"]:
        assert d["per_channel_language"]
        assert all("n_hits" in v and "executed_by_product_cache" in v
                   for v in d["per_channel_language"].values())


@pytest.mark.skipif(not V1_RECORD.is_file(),
                    reason=f"no committed V1 record at {V1_RECORD}")
def test_v1_record_is_still_byte_preserved_and_conforms_to_v1_spec():
    rec = json.loads(V1_RECORD.read_text(encoding="utf-8"))
    assert rec["run_id"] == V1_RUN_ID
    assert rec["hypothesis"]["path"].endswith("PRODUCT_CACHE_PARITY_HYPOTHESIS_V1.json")
    assert rec["hypothesis"]["sha256"] == hashlib.sha256(
        pcp.HYPOTHESIS_V1_PATH.read_bytes()).hexdigest()
    assert rec["verdict"] == "FAIL_PRODUCT_CACHE_PARITY"
    assert rec["standing_orders"]["packet_admitted"] is False
    # V1 measured what it froze: the union comparator (240 rows per slug)
    for g in rec["gates"]:
        if g["role"] != "falsifier":
            continue
        m = g.get("measured") or {}
        assert "comparator_hits" in m or "n_comparator_hits" in m
        if "n_comparator_rows" in m:
            assert m["n_comparator_rows"] == 240
