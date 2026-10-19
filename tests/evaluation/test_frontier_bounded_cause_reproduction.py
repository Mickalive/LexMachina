"""Frontier bounded-cause reproduction instrument: offline tests. NO NETWORK.

These tests never fetch anything and never execute the frozen claim cells against
the real pinned inputs (that is the single claim-bearing run's job). They attack
the instrument's digest convention, URL construction, envelope parsing and each
falsifier via synthetic fixtures, so an auditor can prove the falsifiers fire.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from evaluation import frontier_bounded_cause_reproduction as fbr

ROOT = Path(fbr._REPO_ROOT)
V1 = ROOT / "evaluation" / "FRONTIER_BOUNDED_CAUSE_REPRODUCTION_HYPOTHESIS_V1.json"
V11 = ROOT / "evaluation" / "FRONTIER_BOUNDED_CAUSE_REPRODUCTION_HYPOTHESIS_V1_1_AMENDMENT.json"


def _hyp() -> dict:
    return json.loads(V1.read_text(encoding="utf-8"))


# --------------------------------------------------------------------- #
# freeze contract
# --------------------------------------------------------------------- #


def test_hypothesis_and_amendment_exist_and_pin_the_same_run():
    hyp, amd = _hyp(), json.loads(V11.read_text(encoding="utf-8"))
    assert hyp["frozen_for_run"] == "39195084218"
    assert amd["amends"].endswith("V1.json")
    assert amd["amendment_of_run"] == hyp["frozen_for_run"]


def test_frozen_expectations_in_code_match_the_hypothesis_cells():
    hyp = _hyp()
    c1 = hyp["frozen_cells"]["C1_candidate_only_recovery"]
    assert fbr.EXPECTED_RECOVERED_DISTINCT == c1["expected_recovered_distinct"]
    assert fbr.EXPECTED_MISSING_DISTINCT_SIZE == c1["expected_missing_distinct_size"]
    c4 = hyp["frozen_cells"]["C4_latency_aggregates"]["rule"]
    assert str(fbr.EXPECTED_N_OVER_30) in c4
    assert "83.5047721599999" in c4
    assert "600.569" in c4 and "600.568" in c4
    c5 = hyp["frozen_cells"]["C5_mechanism_witness_count"]["rule"]
    assert "(12)" in c5
    assert fbr.TOTAL_CELLS == hyp["inputs"]["frontier_cache_manifest"]["n_envelopes_expected"]


def test_amendment_only_touches_c2_latency_and_keeps_exit_mapping():
    amd = json.loads(V11.read_text(encoding="utf-8"))
    assert set(amd["amended_cells"]) == {"C2_per_cell_record_vs_cache"}
    assert "per_search_calls" in amd["amended_cells"]["C2_per_cell_record_vs_cache"]["rule"]
    assert "byte-unchanged" in amd["unchanged"]


# --------------------------------------------------------------------- #
# digest + URL conventions on synthetic roots
# --------------------------------------------------------------------- #


def test_cache_manifest_digest_changes_when_one_envelope_byte_changes():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "aa").mkdir()
        body = {"url": "u", "status": 200, "latency_seconds": 1.0,
                "body": "{\"results\":[]}"}
        (root / "aa" / "x.json").write_text(json.dumps(body), encoding="utf-8")
        d1, rels = fbr.cache_manifest_digest(root)
        assert rels == ["aa/x.json"]
        body["status"] = 500
        (root / "aa" / "x.json").write_text(json.dumps(body), encoding="utf-8")
        d2, _ = fbr.cache_manifest_digest(root)
        assert d1 != d2


def test_url_for_joins_terms_with_plus_and_appends_frozen_suffix():
    url = fbr.url_for("a b c")
    assert url == ("https://mcp.opencaselaw.ch/api/decisions?query=a+b+c"
                   "&limit=50&offset=0&sort=relevance&fields=full&include_pinpoint=false")


def test_load_envelopes_parses_string_body_and_extracts_ids():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "bb").mkdir()
        env = {
            "url": fbr.url_for("q one"), "status": 200, "latency_seconds": 31.5,
            "body": json.dumps({"results": [
                {"canonical_decision_id": "bger_4A_219_2015"},
                {"canonical_decision_id": "bger_other"},
            ]}),
        }
        (root / "bb" / "y.json").write_text(json.dumps(env), encoding="utf-8")
        parsed = fbr.load_envelopes(root)
        assert list(parsed) == [fbr.url_for("q one")]
        rec = parsed[fbr.url_for("q one")]
        assert rec["n_rows"] == 2
        assert rec["id_set"] == {"bger_4A_219_2015", "bger_other"}
        assert rec["status"] == 200


# --------------------------------------------------------------------- #
# synthetic end-to-end fixture for the falsifiers
# --------------------------------------------------------------------- #


def _fixture(tmp_root: Path, a1_ids=None, a1_rows=None, a1_status=200,
             a1_latency=31.0, extra_envelope=False, envelope_status=None) -> dict:
    """Minimal harness/spec/durability/envelopes covering every cell family:
    one measurable leg cell, the CCL::fr named-response cell, the two named
    served-response cells (de-kapitalverletzung 0 rows, fr-bail-entretien 1 row).
    envelope_status decouples the cache envelope's status from the harness
    record's a1_status so a record-vs-cache mismatch can be injected.
    """
    a1_ids = a1_ids if a1_ids is not None else []
    a1_rows = a1_rows if a1_rows is not None else len(a1_ids)
    cache = tmp_root / "cache"
    (cache / "c1").mkdir(parents=True)

    def _env(name: str, query: str, rows_ids, status=200, latency=31.0):
        (cache / "c1" / f"{name}.json").write_text(json.dumps({
            "url": fbr.url_for(query), "status": status,
            "latency_seconds": latency,
            "body": json.dumps({"results": [
                {"canonical_decision_id": i} for i in rows_ids]}),
        }), encoding="utf-8")

    _env("a", "exp leg fr", a1_ids,
         status=(envelope_status if envelope_status is not None else a1_status),
         latency=a1_latency)
    _env("b", "exp served q", ["x"], latency=41.0)
    _env("c", "exp leg ccl fr", [], latency=30.8)
    _env("d", "exp served de", [], latency=21.0)
    if extra_envelope:
        _env("e", "unclaimed query", [], latency=1.0)

    harness = {
        "frozen_legs": {
            "business-judgment-rule": {
                "authority_ids": ["bger_A", "bger_B"],
                "per_language": {
                    "fr": {
                        "expansion_query": "exp leg fr",
                        "A0_baseline_shipped": {"hits": [], "n_rows": 50},
                        "A1_candidate_only": {
                            "n_rows": a1_rows,
                            "required": ["bger_A", "bger_B"],
                            "newly_found_ids": list(a1_ids),
                        },
                        "A1_union": {"n_rows": 50 + a1_rows},
                        "search": {"status": a1_status},
                    },
                },
            },
            "corporate-criminal-liability": {
                "authority_ids": ["bger_C"],
                "per_language": {
                    "fr": {
                        "expansion_query": "exp leg ccl fr",
                        "A0_baseline_shipped": {"hits": [], "n_rows": 50},
                        "A1_candidate_only": {
                            "n_rows": 0, "required": ["bger_C"],
                            "newly_found_ids": [],
                        },
                        "A1_union": {"n_rows": 50},
                        "search": {"status": 200},
                    },
                },
            },
        },
        "served_questions": {
            "fr-bail-entretien": {
                "expansion_query": "exp served q",
                "A0_baseline_shipped": {"n_rows": 217},
                "A1_candidate": {"n_rows": 1},
            },
            "de-kapitalverletzung": {
                "expansion_query": "exp served de",
                "A0_baseline_shipped": {"n_rows": 214},
                "A1_candidate": {"n_rows": 0},
            },
        },
        "latency_budget": {"per_search_calls": [
            {"query": "exp leg fr", "latency_seconds": round(a1_latency, 3),
             "status": a1_status},
            {"query": "exp served q", "latency_seconds": 41.0, "status": 200},
            {"query": "exp leg ccl fr", "latency_seconds": 30.8, "status": 200},
            {"query": "exp served de", "latency_seconds": 21.0, "status": 200},
        ]},
    }
    spec = {"questions": [
        {"slug": "business-judgment-rule", "authority_ids": ["bger_A", "bger_B"]},
        {"slug": "corporate-criminal-liability", "authority_ids": ["bger_C"]},
        {"slug": "rent-default", "authority_ids": []},
    ]}
    gates = {
        "authority::baseline_lang_recall::business-judgment-rule::fr": "FAIL",
        "authority::baseline_lang_recall::corporate-criminal-liability::fr": "FAIL",
    }
    durability = {"F3_language_recall_gate_stability": {
        "accepted_status": dict(gates), "live_status": dict(gates)}}
    envelopes = fbr.load_envelopes(cache)
    return fbr.run_comparisons(harness, spec, durability, envelopes)


def _claim_divergences(out: dict) -> list[str]:
    """Divergences in the cells a small synthetic fixture can satisfy.

    C4 (15-envelope aggregates), C5 (12-of-15 witness count) and the C1
    missing_distinct_size==9 denominator are calibrated to the real 15-cell
    population by the frozen hypothesis; a synthetic fixture cannot satisfy
    them and they are excluded HERE, never in the instrument.
    """
    return [d for d in out["divergences"]
            if not d.startswith("C4::")
            and not d.startswith("C5::")
            and not d.startswith("C1::missing_distinct_size")]


def test_clean_fixture_produces_zero_claim_cell_divergences():
    with tempfile.TemporaryDirectory() as td:
        out = _fixture(Path(td))
        assert _claim_divergences(out) == [], out["divergences"]
        assert out["C1_recovery"]["recovered_distinct"] == []
        assert out["bijection_ok"] is True


def test_falsifier_c1_fires_when_body_contains_a_missing_frozen_id():
    with tempfile.TemporaryDirectory() as td:
        out = _fixture(Path(td), a1_ids=["bger_A"])
        assert any(d.startswith("C1::recovered_distinct") for d in out["divergences"])
        assert out["C1_recovery"]["recovered_distinct"] == ["bger_A"]


def test_falsifier_c2_fires_on_status_mismatch():
    with tempfile.TemporaryDirectory() as td:
        out = _fixture(Path(td), a1_status=200, envelope_status=500)
        assert any(d.startswith("C2::business-judgment-rule::fr::")
                   for d in out["divergences"])


def test_falsifier_c2_fires_on_unclaimed_envelope():
    with tempfile.TemporaryDirectory() as td:
        out = _fixture(Path(td), extra_envelope=True)
        assert any("unclaimed_envelope" in d for d in out["divergences"])
        assert out["bijection_ok"] is False


def test_build_cells_reads_status_from_the_sibling_search_block():
    """Regression for run-1's extraction bug: status lives beside
    A1_candidate_only, not inside it."""
    harness = {"frozen_legs": {"leg-x": {"authority_ids": ["a"],
        "per_language": {"fr": {
            "expansion_query": "q", "A0_baseline_shipped": {"hits": [], "n_rows": 1},
            "A1_candidate_only": {"n_rows": 1, "required": ["a"]},
            "search": {"status": 200}}}}}, "served_questions": {}}
    cells = fbr.build_cells(harness)
    assert cells[0]["a1_status"] == 200


def test_c5_union_shrink_is_named_as_an_anomaly():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _fixture(root)
        cache = root / "cache"
        harness = {
            "frozen_legs": {"business-judgment-rule": {
                "authority_ids": ["bger_A"],
                "per_language": {"fr": {
                    "expansion_query": "exp leg fr",
                    "A0_baseline_shipped": {"hits": ["bger_A"], "n_rows": 50},
                    "A1_candidate_only": {"n_rows": 0, "required": ["bger_A"],
                                          "newly_found_ids": []},
                    "A1_union": {"n_rows": 45},
                    "search": {"status": 200}}}}},
            "served_questions": {},
            "latency_budget": {"per_search_calls": [
                {"query": "exp leg fr", "latency_seconds": 31.0, "status": 200}]},
        }
        spec = {"questions": [{"slug": "business-judgment-rule",
                               "authority_ids": ["bger_A"]}]}
        dur = {"F3_language_recall_gate_stability": {"accepted_status": {},
                                                     "live_status": {}}}
        out = fbr.run_comparisons(harness, spec, dur, fbr.load_envelopes(cache))
        assert any("union_shrink_anomaly" in d for d in out["divergences"])
        assert out["C5_witness_cells_added_semantics"] == 0
        assert out["C5_witness_cells"] == 1


def test_falsifier_c3_fires_when_named_row_count_changes():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _fixture(root)  # build the clean cache
        cache = root / "cache"
        env_path = cache / "c1" / "b.json"
        env = json.loads(env_path.read_text(encoding="utf-8"))
        env["body"] = json.dumps({"results": [{"canonical_decision_id": "x"},
                                              {"canonical_decision_id": "y"}]})
        env_path.write_text(json.dumps(env), encoding="utf-8")
        harness = {
            "frozen_legs": {
                "business-judgment-rule": {
                    "authority_ids": ["bger_A", "bger_B"],
                    "per_language": {"fr": {
                        "expansion_query": "exp leg fr",
                        "A0_baseline_shipped": {"hits": [], "n_rows": 50},
                        "A1_candidate_only": {"n_rows": 0,
                                              "required": ["bger_A", "bger_B"],
                                              "newly_found_ids": []},
                        "A1_union": {"n_rows": 50},
                        "search": {"status": 200},
                    }},
                }},
            "served_questions": {"fr-bail-entretien": {
                "expansion_query": "exp served q",
                "A0_baseline_shipped": {"n_rows": 217},
                "A1_candidate": {"n_rows": 1}}},
            "latency_budget": {"per_search_calls": [
                {"query": "exp leg fr", "latency_seconds": 31.0, "status": 200},
                {"query": "exp served q", "latency_seconds": 41.0, "status": 200}]},
        }
        spec = {"questions": [
            {"slug": "business-judgment-rule",
             "authority_ids": ["bger_A", "bger_B"]}]}
        dur = {"F3_language_recall_gate_stability": {"accepted_status": {},
                                                     "live_status": {}}}
        out = fbr.run_comparisons(harness, spec, dur, fbr.load_envelopes(cache))
        assert any(d.startswith("C3::fr-bail-entretien::") for d in out["divergences"])


def test_c4_divergence_names_sum_disagreement_with_published_values():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cache = root / "cache"
        (cache / "c1").mkdir(parents=True)
        (cache / "c1" / "a.json").write_text(json.dumps({
            "url": fbr.url_for("exp leg fr"), "status": 200,
            "latency_seconds": 31.0, "body": json.dumps({"results": []})}),
            encoding="utf-8")
        (cache / "c1" / "b.json").write_text(json.dumps({
            "url": fbr.url_for("exp served q"), "status": 200,
            "latency_seconds": 41.0, "body": json.dumps({"results": []})}),
            encoding="utf-8")
        harness = {
            "frozen_legs": {"business-judgment-rule": {
                "authority_ids": ["bger_A"],
                "per_language": {"fr": {
                    "expansion_query": "exp leg fr",
                    "A0_baseline_shipped": {"hits": ["bger_A"], "n_rows": 50},
                    "A1_candidate_only": {"n_rows": 0, "required": ["bger_A"],
                                          "newly_found_ids": []},
                    "A1_union": {"n_rows": 50},
                    "search": {"status": 200}}}}},
            "served_questions": {"q": {
                "expansion_query": "exp served q",
                "A0_baseline_shipped": {"n_rows": 10},
                "A1_candidate": {"n_rows": 10}}},
            "latency_budget": {"per_search_calls": [
                {"query": "exp leg fr", "latency_seconds": 31.0, "status": 200},
                {"query": "exp served q", "latency_seconds": 41.0, "status": 200}]},
        }
        spec = {"questions": [{"slug": "business-judgment-rule",
                               "authority_ids": ["bger_A"]}]}
        dur = {"F3_language_recall_gate_stability": {"accepted_status": {},
                                                     "live_status": {}}}
        out = fbr.run_comparisons(harness, spec, dur, fbr.load_envelopes(cache))
        # 31+41=72.0 matches neither 600.569 nor 600.568 -> both named
        assert any(d.startswith("C4::sum_round3") for d in out["divergences"])


# --------------------------------------------------------------------- #
# verify_inputs ENVIRONMENT path
# --------------------------------------------------------------------- #


def test_verify_inputs_flags_a_drifted_pin():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "pin.json"
        p.write_text("{}", encoding="utf-8")
        hyp = {"inputs": {"x": {"path": str(p), "sha256": "0" * 64}}}
        resolved, problems = fbr.verify_inputs(hyp)
        assert resolved == {}
        assert problems and "digest drift" in problems[0]


def test_verify_inputs_accepts_a_matching_pin_and_manifest():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        p = root / "pin.json"
        payload = '{"a": 1}'
        p.write_text(payload, encoding="utf-8")
        sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cache = root / "cache"
        (cache / "z").mkdir(parents=True)
        (cache / "z" / "e.json").write_text(json.dumps({
            "url": "u", "status": 200, "latency_seconds": 1.0,
            "body": "{\"results\":[]}"}), encoding="utf-8")
        manifest, _ = fbr.cache_manifest_digest(cache)
        hyp = {"inputs": {
            "x": {"path": str(p), "sha256": sha},
            "cache": {"root": str(cache), "manifest_sha256": manifest,
                      "n_envelopes_expected": 1}}}
        resolved, problems = fbr.verify_inputs(hyp)
        assert problems == []
        assert set(resolved) == {"x", "cache"}


# --------------------------------------------------------------------- #
# no-network guard
# --------------------------------------------------------------------- #


def test_instrument_module_has_no_network_imports():
    src = (ROOT / "evaluation" / "frontier_bounded_cause_reproduction.py").read_text("utf-8")
    for banned in ("import requests", "import urllib.request",
                   "import http.client", "import socket"):
        assert banned not in src
