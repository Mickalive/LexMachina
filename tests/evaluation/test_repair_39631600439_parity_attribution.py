"""Tests for the parity-attribution repair of rejected cycle 39628161040.

Repair round 1, run 39631600439.  The independent audit of cycle 39628161040
returned gate REVISE with four required fixes (F1 attribution/decomposition,
F2 frozen-rule contradiction, F3 test coverage, F4 disposition wording).  This
file guards the discharge of those four fixes and the house SUPERSEDED pattern
(the original wording is preserved verbatim, never deleted).

Standard-library only, plain zero-argument ``test_*`` functions: runnable
under pytest AND under the lane's no-pytest shim
(evaluation/no_pytest_runner.py).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

RUN_ID = "39631600439"
REPAIRED_CYCLE = "39628161040"
REPAIR_RECORD = (REPO / "results" / "evaluation" / "repair_39628161040" /
                 f"{RUN_ID}_parity_attribution_repair.json")
REPAIR_REPORT = (REPO / "reports" / "evaluation" /
                 f"PARITY_ATTRIBUTION_REPAIR_{RUN_ID}.md")
V2_RECORD = (REPO / "results" / "evaluation" / "product_cache_parity" /
             f"{RUN_ID}.json")
STATE = REPO / "state" / "evaluation.json"
OPRES_RECORD = (REPO / "results" / "evaluation" / "operational_resume" /
                f"{REPAIRED_CYCLE}.json")
V1_REPORT = (REPO / "reports" / "evaluation" /
             "PRODUCT_CACHE_PARITY_39619144928.md")

F4_CORRECTED = ("preserved in this branch snapshot with digests recorded in the "
                "lane machine record, removed at promotion by the integrate "
                "step's audit-directory checkout")
F4_SUPERSEDED = ("preserved in place as evidence of the scope failure; not "
                 "consumed as an audit verdict; deleted by no cycle")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _state() -> dict:
    return _load(STATE)


# --------------------------------------------------------------------------- #
# the repair record itself
# --------------------------------------------------------------------------- #
def test_repair_record_is_committed_and_complete():
    assert REPAIR_RECORD.is_file(), REPAIR_RECORD
    rec = _load(REPAIR_RECORD)
    assert rec["schema"] == "lex-evaluation-parity-attribution-repair/1"
    assert rec["run_id"] == RUN_ID
    assert rec["repaired_cycle"] == REPAIRED_CYCLE
    assert rec["all_required_fixes_complete"] is True
    assert rec["n_checks_passed"] == rec["n_checks"]
    assert set(rec["fixes"]) == {"F1", "F2", "F3", "F4"}
    for key in ("F1", "F2", "F3", "F4"):
        assert rec["fixes"][key]["complete"] is True
        assert rec["fixes"][key]["checks"]


def test_repair_record_carries_its_own_verdict():
    rec = _load(REPAIR_RECORD)
    assert rec["verdict"] == "REPAIR_FIXES_VERIFIED"
    assert rec["all_required_fixes_complete"] is True


def test_lane_suite_regression_is_recorded_without_claiming_green():
    rec = _load(REPAIR_RECORD)
    ls = rec["lane_suite_regression"]
    assert ls["present"] is True
    assert ls["is_audit_required_fix"] is False
    assert ls["n_new_failures"] == 0
    assert ls["verdict"] == "SHIM_NO_NEW_FAILURE"
    assert "NOT green" in ls["note"]
    # the shim comparison record itself
    cmp_rec = _load(REPO / "results" / "evaluation" / "orchestration" /
                    f"{RUN_ID}_shim_regression.json")
    assert cmp_rec["verdict"] == "SHIM_NO_NEW_FAILURE"
    assert cmp_rec["n_new_failures"] == 0
    assert cmp_rec["current_counts"]["n_failed"] > 0
    assert "NOT pytest" in cmp_rec["what_this_is_not"]


def test_repair_record_does_not_self_certify():
    rec = _load(REPAIR_RECORD)
    assert rec["pending_independent_audit"] is True
    assert rec["measurements_untouched"]["verdict_withdrawn"] is False
    assert rec["measurements_untouched"]["v1_artifacts_deleted"] is False
    assert rec["measurements_untouched"]["no_new_thresholds"] is True
    assert rec["measurements_untouched"]["no_174k_benchmark_rerun"] is True
    assert "independent audit of THIS cycle is still owed" in rec["claim_ceiling"]
    assert "authorises NO owner question" in rec["claim_ceiling"]


def test_repair_report_exists_and_names_every_fix():
    assert REPAIR_REPORT.is_file(), REPAIR_REPORT
    md = REPAIR_REPORT.read_text(encoding="utf-8")
    for key in ("F1", "F2", "F3", "F4"):
        assert f"## {key} —" in md
    assert "The FAIL verdict is **not** withdrawn" in md


# --------------------------------------------------------------------------- #
# F1: decomposition published, finding restated honestly
# --------------------------------------------------------------------------- #
def test_v2_record_publishes_the_decomposition():
    rec = _load(V2_RECORD)
    decomp = rec["gate_decomposition"]
    assert len(decomp) == 8
    for d in decomp:
        assert d["per_channel_language"]
        assert set(d["per_channel_language"]) == {
            "baseline/de", "baseline/fr", "baseline/it",
            "counter/de", "counter/fr", "counter/it"}
        for v in d["per_channel_language"].values():
            assert "n_hits" in v and "executed_by_product_cache" in v
        assert "executed_text_only_comparison" in d
        assert "comparator_only_attribution" in d


def test_v2_record_publishes_the_executed_text_only_comparison():
    rec = _load(V2_RECORD)
    same_text = [g for g in rec["gates"]
                 if g["role"] == "falsifier" and g["passed"] is not None]
    assert len(same_text) == 7
    for g in same_text:
        m = g["measured"]
        assert m["comparator_scope"] == "executed_text"
        assert len(m["product_hits"]) >= len(m["comparator_hits"])
    # the published per-cell executed-text comparison is the audited one,
    # in the audit's own (kind, slug) order
    order = [
        ("counter", "rent-default"),
        ("authority", "corporate-criminal-liability"),
        ("counter", "corporate-criminal-liability"),
        ("authority", "business-judgment-rule"),
        ("counter", "business-judgment-rule"),
        ("authority", "petty-theft-dismissal"),
        ("counter", "petty-theft-dismissal"),
    ]
    got = []
    for kind, slug in order:
        g = next(g for g in same_text
                 if g["gate"] == f"parity::same_query_{kind}_not_below_baseline::{slug}")
        got.append((len(g["measured"]["product_hits"]),
                    len(g["measured"]["comparator_hits"])))
    assert got == [(0, 0), (1, 0), (1, 1), (0, 0), (0, 0), (0, 0), (1, 0)]


def test_finding_is_restated_and_the_old_wording_is_kept_verbatim():
    md = V1_REPORT.read_text(encoding="utf-8")
    assert "Finding restatement (repair round 1, run 39631600439)" in md
    assert "not** a same-query" in md
    assert "18 comparator-only" in md
    # the superseded sentence is preserved verbatim (house SUPERSEDED pattern)
    state = _state()
    assert state["supersession"]["superseded_at_run"] == RUN_ID
    assert state["supersession"]["superseded_sentence_verbatim"] == (
        "the product's own cached retrieval responses to the frozen queries "
        "recall strictly fewer frozen ids than the plain OpenCaseLaw response "
        "to the identical query text: retrieval-first parity is falsified on "
        "the named cells")
    assert "QUERY-COVERAGE deficit, NOT a same-query retrieval-layer regression" \
        in state["supersession"]["corrected_sentence"]


def test_state_note_no_longer_claims_a_same_query_regression():
    note = _state()["product_cache_parity"]["note"]
    assert "Falsifies same-query retrieval parity" not in note
    assert "QUERY-COVERAGE deficit, NOT a same-query retrieval-layer regression" \
        in note
    assert "18 comparator-only ids come exclusively from texts the product " \
           "never executed" in note
    # the verdict itself is unchanged
    assert _state()["product_cache_parity"]["verdict"] == "FAIL_PRODUCT_CACHE_PARITY"
    assert _state()["product_cache_parity"]["exit_code"] == 1
    assert _state()["product_cache_parity"]["pending_independent_audit"] is True


# --------------------------------------------------------------------------- #
# F2: versioned hypothesis, no frozen rule weakened
# --------------------------------------------------------------------------- #
def test_v1_chain_is_byte_preserved_and_re_pinned():
    freeze = _load(REPO / "evaluation" / "PRODUCT_CACHE_PARITY_FREEZE_RECORD_V2.json")
    pres = freeze["superseded_spec_byte_preserved"]
    for rel, digest in (
            ("evaluation/PRODUCT_CACHE_PARITY_HYPOTHESIS_V1.json",
             pres["v1_hypothesis"]["sha256"]),
            ("evaluation/PRODUCT_CACHE_PARITY_FREEZE_RECORD_V1.json",
             pres["v1_freeze_record"]["sha256"])):
        path = REPO / rel
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    for rel, digest in pres["v1_records"].items():
        path = REPO / rel
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_v1_falsifiers_survive_one_to_one_in_the_v2_coverage_family():
    rec = _load(V2_RECORD)
    pres = rec["v1_preservation"]
    assert pres["all_preserved"] is True
    for rid in ("39628161040", "39619144928"):
        info = pres["records"][rid]
        assert info["all_preserved"] is True
        assert info["failed_sets_identical"] is True
        assert info["n_v1_failed"] == 7 and info["n_v2_failed"] == 7
        for m in info["gate_mapping"]:
            assert m["v2_gate"].startswith("coverage::union_frozen_texts_")
            assert m["passed_identical"] is True
            assert m["measured_differences"] == []
            assert m["quantities_compared"]


def test_the_verdict_is_not_downgraded():
    rec = _load(V2_RECORD)
    assert rec["verdict"] == "FAIL_PRODUCT_CACHE_PARITY"
    assert rec["exit_code"] == 1
    assert rec["coverage_verdict"] == "FAIL"
    assert rec["verdict_scope"] == "coverage"
    assert rec["same_text_parity_verdict"] == "PASS"
    assert len(rec["coverage_failed_gates"]) == 7
    assert rec["same_text_parity_failed_gates"] == []
    # the frozen success rule and claim ceiling are still published
    assert rec["success_rule"]
    assert "DO-NOT-SERVE" in rec["claim_ceiling"]


# --------------------------------------------------------------------------- #
# F3: the asymmetric synthetic case
# --------------------------------------------------------------------------- #
def test_asymmetric_case_is_exercised_by_the_lane_suite():
    from evaluation import product_cache_parity as pcp
    from evaluation.retrieval_gate import frozen as rg_frozen
    spec = {
        "id_match_rules": {"min_core_length": 6},
        "questions": [{
            "slug": "synth-asym",
            "queries": {
                "baseline": {"fr": "Alpha question text about leasing",
                             "de": "Alpha frage text ueber miete",
                             "it": "Alpha domanda testo su locazione"},
                "counter": {"fr": "Alpha exception limite reprise",
                            "de": "Alpha ausnahme grenze wiederaufnahme",
                            "it": "Alpha eccezione limite ripresa"},
            },
            "authority_ids": [],
            "known_counter_ids": [{"id": "bge_BGE_100_II_1"},
                                  {"id": "bge_BGE_200_III_9"}],
        }],
    }
    fr = "Alpha question text about leasing"
    de = "Alpha ausnahme grenze wiederaufnahme"

    def row(i):
        return {"decision_id": i, "canonical_decision_id": i,
                "citation_string_de": "BGE 100 II 1",
                "canonical_url": "https://www.opencaselaw.ch/x",
                "language": "de"}

    baseline = {
        "schema": "lex-retrieval-benchmark/1",
        "frozen_sha256": rg_frozen.FROZEN_SHA256,
        "queries": [
            {"slug": "synth-asym", "channel": "baseline", "language": "fr",
             "query": fr, "query_key": "k1", "rows": [row("bge_BGE_100_II_1")]},
            {"slug": "synth-asym", "channel": "counter", "language": "de",
             "query": de, "query_key": "k2", "rows": [row("bge_BGE_200_III_9")]},
        ],
    }
    envelopes = {rg_frozen.normalize_text(fr): [
        {"file": "syn/fr.json", "n_rows": 1, "rows": [row("bge_BGE_100_II_1")]}]}
    hyp = {"claim_ceiling": "synthetic",
           "metric_FROZEN": {"success_rule_FROZEN": "synthetic"}}
    out = pcp.evaluate(hyp, spec, baseline, envelopes)
    names = {g["gate"]: g for g in out["gates"]}
    same_text = names["parity::same_query_counter_not_below_baseline::synth-asym"]
    coverage = names["coverage::union_frozen_texts_counter_not_below_baseline::synth-asym"]
    # the never-executed text may not become a same-text falsification
    assert same_text["passed"] is True
    assert coverage["passed"] is False
    assert out["falsification_gates"] == [
        "coverage::union_frozen_texts_counter_not_below_baseline::synth-asym"]
    assert out["verdict_scope"] == "coverage"
    dec = [d for d in out["gate_decomposition"] if d["kind"] == "counter"][0]
    assert dec["comparator_only_ids"] == ["bge_BGE_200_III_9"]
    assert dec["comparator_only_ids_from_executed_texts"] == []


# --------------------------------------------------------------------------- #
# F4: disposition wording
# --------------------------------------------------------------------------- #
def test_disposition_wording_is_corrected_and_the_old_one_kept_verbatim():
    opres = _load(OPRES_RECORD)
    oos = (opres["snapshot_hygiene"] or {}).get("out_of_scope") or []
    assert oos
    for e in oos:
        assert F4_CORRECTED in e["disposition"]
        assert e["disposition_v1_verbatim"] == F4_SUPERSEDED
        assert e["disposition_amendment"]["amended_by_run"] == RUN_ID
    md = (REPO / "reports" / "evaluation" /
          f"OPERATIONAL_RESUME_{REPAIRED_CYCLE}.md").read_text(encoding="utf-8")
    assert F4_CORRECTED in md
    assert "preserved in place" not in md.split("Superseded wording")[0]
    state = _state()
    assert F4_CORRECTED in state["operational_resume"]["diagnosis"]


def test_state_flags_stay_fail_closed():
    state = _state()
    for key in ("human_gate_ready", "machine_gate_ready", "packet_admitted",
                "ready_for_owner_session", "owner_decision_required"):
        assert state[key] is False, key
    assert state["standing_orders_confirmed"]["do_not_serve_38839347028"] is True
    assert state["standing_orders_confirmed"][
        "do_not_serve_unchanged_rebuilt_39027045675"] is True
    assert state["accepted_run_id"] == "39581086634"
    assert state["evidence_tier"] == "EXPLORATORY"
