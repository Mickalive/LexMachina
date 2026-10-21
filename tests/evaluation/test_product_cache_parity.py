"""Tests for the product-cache retrieval/counter-authority parity falsifier.

Scope extension, disclosed: this file was added to the lane suite by run
39619144928 (same convention as the accepted scope extensions of runs
39111232991 and 39092033997).  Runnable by the stdlib shim
``evaluation/no_pytest_runner.py`` as well as pytest: plain zero-argument
``test_*`` functions, module-level imports and ``pytest.mark.skipif`` only.
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

RUN_ID = "39619144928"
RECORD = REPO_ROOT / "results" / "evaluation" / "product_cache_parity" / f"{RUN_ID}.json"


def _hypothesis() -> dict:
    return json.loads(pcp.HYPOTHESIS_PATH.read_text(encoding="utf-8"))


def _freeze() -> dict:
    return json.loads(pcp.FREEZE_RECORD_PATH.read_text(encoding="utf-8"))


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


# --------------------------------------------------------------------------- #
# the freeze itself
# --------------------------------------------------------------------------- #
def test_hypothesis_is_frozen_before_execution_with_an_honest_disclosure():
    hyp = _hypothesis()
    assert hyp["frozen_before_execution"] is True
    assert hyp["schema"] == "lex-evaluation-product-cache-parity-hypothesis/1"
    d = hyp["pre_freeze_reconnaissance_HONEST"]
    assert d["what_happened"] and d["what_was_seen"] and d["what_was_NOT_seen"]
    assert d["why_it_does_not_launder_the_result"]
    # the reconnaissance discloses envelope counts, never id hits
    assert "NO frozen authority id" in d["what_was_NOT_seen"]


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
    assert out["falsification_gates"] == \
        ["parity::same_query_counter_not_below_baseline::synth-question"]


def test_empty_frozen_id_set_is_not_measurable_never_a_pass():
    spec, baseline, envelopes, hyp = _synth(authority_ids=[], counter_ids=[])
    out = pcp.evaluate(hyp, spec, baseline, envelopes)
    names = {g["gate"]: g["passed"] for g in out["gates"]}
    assert names["product::authority_recall::synth-question"] is None
    assert names["product::counter_recall::synth-question"] is None
    assert names["parity::same_query_counter_not_below_baseline::synth-question"] is None
    assert out["verdict"] == "ENVIRONMENT_OR_VACUOUS"  # battery cannot prove C1
    assert out["exit_code"] == 2


def test_blank_pool_fails_parity_and_oracle_passes_it():
    spec, baseline, envelopes, hyp = _synth(counter_ids=["bge_BGE_100_II_1",
                                                         "bge_BGE_200_III_9"])
    base_text = spec["questions"][0]["queries"]["baseline"]["fr"]
    # blanked observed pool: the parity gate must falsify, and the battery's own
    # re-scored controls (C1 blanked / C2 oracle) must both hold
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
