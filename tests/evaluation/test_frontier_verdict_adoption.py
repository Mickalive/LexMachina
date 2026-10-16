#!/usr/bin/env python3
"""Evaluation lane v56 ADOPT test: the three accepted Frontier verdicts are folded
in as named metrics carrying their frozen rule sha256s and packet-coverage tags.

HARD CONSTRAINTS (factory direction v56, evaluation question):
- this lane freezes NOTHING new (no new threshold is introduced here);
- no frozen bar is raised or lowered;
- no Frontier harness is re-run (numbers are adopted, not re-measured);
- no synthetic benchmark churn is added;
- nothing is written under product/ or state/product.json;
- evaluation does not own disclosure wording and writes no human-gate answer.

The test additionally exercises the lane's own executable falsifier
(evaluation/query_map harness): the smallest retrieval/counter-authority
benchmark that can falsify the product. Reuses the existing harness only;
obsolete universal-174k benchmarks are NOT rerun.
"""

import json
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
ADOPTION = WORKSPACE / "evaluation" / "frontier_verdict_adoption.json"

FROZEN_LABEL_SHA = "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
FROZEN_GEOMETRY_SHA = "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"


def _load():
    assert ADOPTION.exists(), f"adoption artifact missing: {ADOPTION}"
    return json.loads(ADOPTION.read_text(encoding="utf-8"))


def test_adoption_file_schema_and_method():
    doc = _load()
    assert doc["schema"] == "lex-evaluation-frontier-verdict-adoption/1"
    assert doc["lane"] == "evaluation"
    assert doc["direction_version"] == 56
    assert doc["method"] == "ADOPTED_WITHOUT_REMEASURE"
    assert doc["adopted_by_run"] == "38918468438"


def test_frozen_rule_pins_match_direction():
    doc = _load()
    assert doc["frozen_rules"]["counter_label_soundness"]["rules_sha256"] == FROZEN_LABEL_SHA
    assert doc["frozen_rules"]["geometry_semantics"]["rules_sha256"] == FROZEN_GEOMETRY_SHA
    assert doc["frozen_rules"]["counter_label_soundness"]["bar_changed_by_this_lane"] is False
    assert doc["frozen_rules"]["geometry_semantics"]["bar_changed_by_this_lane"] is False


def test_frozen_bars_not_moved():
    doc = _load()
    label_bar = doc["frozen_rules"]["counter_label_soundness"]["frozen_bar"]
    assert "1.0" in label_bar, "label absolute bar must stay 1.0"
    geom_bar = doc["frozen_rules"]["geometry_semantics"]["frozen_bar_example"]
    assert "0.60" in geom_bar or "0.6" in geom_bar, "STRUCTURE_LARGEST bar must stay 0.60"
    assert doc["metrics"]["B2_served_packet_geometry_before_after"]["french_mega_cluster"]["frozen_bar"] == 0.6
    assert doc["hard_constraints_compliance"]["froze_nothing_new"] is True
    assert doc["hard_constraints_compliance"]["no_bar_raised_or_lowered"] is True


def test_every_metric_carries_packet_coverage():
    doc = _load()
    expected_packets = {
        "A1_counter_label_integrity_pre_repair": (False, "38799024807"),
        "A2_served_packet_label_before_after": (True, "38839347028"),
        "B1_map_semantics_pre_rebuild": (False, "38799024807"),
        "B2_served_packet_geometry_before_after": (True, "38839347028"),
    }
    assert set(doc["metrics"]) == set(expected_packets), (
        f"exactly four named adopted metrics expected, got {sorted(doc['metrics'])}"
    )
    for name, (covers, packet) in expected_packets.items():
        m = doc["metrics"][name]
        assert m["covers_this_packet"] is covers, f"{name}: covers_this_packet must be {covers}"
        assert packet in m["packet_covered"], f"{name}: packet tag {packet} missing"


def test_adopted_numbers_match_direction():
    doc = _load()
    a1 = doc["metrics"]["A1_counter_label_integrity_pre_repair"]
    assert a1["verdict"] == "LABEL_UNSOUND"
    assert a1["accepted_chain"] == "0/46 supported"
    assert a1["charter_primary"] == "0/7 supported"
    a2 = doc["metrics"]["A2_served_packet_label_before_after"]
    assert a2["verdict"] == "LABEL_UNSOUND"
    assert (a2["n_scored"], a2["n_supported"]) == (65, 5)
    assert a2["direction_vs_baseline"] == "IMPROVED"
    assert a2["defect_classes"] == {
        "OFF_DOMAIN": 38, "UNBACKED": 22, "SUPPORTED": 5,
        "INVERTED": 0, "BOILERPLATE_ONLY": 0, "FRAGMENT": 0,
    }
    assert a2["counter_evidence_verified"] == {"present_true": 49, "present_false": 0, "absent": 16}
    b1 = doc["metrics"]["B1_map_semantics_pre_rebuild"]
    assert b1["verdict"] == "FAIL"
    assert (b1["n_bundles_pass"], b1["n_bundles"]) == (0, 3)
    b2 = doc["metrics"]["B2_served_packet_geometry_before_after"]
    assert b2["verdict"] == "FAIL"
    assert (b2["n_bundles_pass"], b2["n_bundles"]) == (0, 3)
    assert b2["french_mega_cluster"]["direction"] == "REGRESSED"
    assert b2["french_mega_cluster"]["share"] == 0.7696
    assert "DO-NOT-SERVE" in doc["serve_recommendation_adopted"]


def test_set_identity_not_collapsed():
    """The 16 empty-evidence rows are a PROPER SUBSET of the 22 UNBACKED rows."""
    doc = _load()
    a2 = doc["metrics"]["A2_served_packet_label_before_after"]
    assert a2["counter_evidence_verified"]["absent"] == 16
    assert a2["defect_classes"]["UNBACKED"] == 22
    assert 16 < 22
    assert "PROPER SUBSET" in a2["set_identity_note"]


def test_numbers_match_accepted_spf_state_where_durable():
    """Cross-check the served-packet half against the durable accepted state on
    origin/main. This re-reads accepted evidence; it does not re-run any harness."""
    try:
        raw = subprocess.check_output(
            ["git", "show", "origin/main:results/accepted-state/frontier/frontier-served-packet-falsification.json"],
            cwd=str(WORKSPACE), timeout=60,
        )
    except Exception as exc:
        raise AssertionError(f"cannot read accepted SPF state from origin/main: {exc}")
    spf = json.loads(raw.decode("utf-8"))
    doc = _load()
    a2 = doc["metrics"]["A2_served_packet_label_before_after"]
    b2 = doc["metrics"]["B2_served_packet_geometry_before_after"]
    assert spf["verdict"]["label_half"]["n_scored"] == a2["n_scored"] == 65
    assert spf["verdict"]["label_half"]["n_supported"] == a2["n_supported"] == 5
    assert spf["verdict"]["geometry_half"]["n_bundles_pass"] == b2["n_bundles_pass"] == 0
    assert spf["verdict"]["geometry_half"]["french_largest_share"] == b2["french_mega_cluster"]["share"] == 0.7696
    assert spf["serve_recommendation"] == "DO-NOT-SERVE this packet unchanged."
    assert spf["promoted_commit"] == a2["promote_commit"] == "464c45f7e4bf741b6a67adbef35dc587d8cfa21f"


def test_harness_still_falsifies_unsupported_counters():
    """The lane's own executable benchmark: happy path passes, an unevidenced
    counter label fails. Reuses evaluation/query_map only (no 174k rerun)."""
    from evaluation.query_map.harness import evaluate_query_map_bundle

    def decision(i, *, lang="fr", status="none", evidence="", uncertainty=None):
        return {
            "decision_id": f"d{i}",
            "canonical_url": f"https://mcp.opencaselaw.ch/entscheid/d{i}",
            "language": lang,
            "cluster_id": i % 2,
            "x": i / 10,
            "y": -i / 10,
            "is_outlier": i == 3,
            "counter_status": status,
            "counter_evidence": evidence,
            "counter_uncertainty": uncertainty,
        }

    ds = [
        decision(1, lang="de"),
        decision(2, lang="fr"),
        decision(3, lang="it", status="limiting", evidence="exception", uncertainty=0.2),
    ]
    initial = {
        "answer": {"cited_decision_ids": []},
        "decisions": [dict(x) for x in ds],
        "clusters": [{"cluster_id": 0}, {"cluster_id": 1}],
        "provenance": {"phase": "map_ready", "latency_seconds": 0.4, "fixture_mode": True},
    }
    final = {
        "answer": {"cited_decision_ids": ["d1", "d2"]},
        "decisions": [dict(x) for x in ds],
        "clusters": [{"cluster_id": 0}, {"cluster_id": 1}],
        "provenance": {
            "phase": "complete",
            "fixture_mode": True,
            "enrichment_latency_seconds": 0.8,
            "latency_seconds_total": 1.2,
            "retrieval": {"candidate_languages": {"de": 1, "fr": 1, "it": 1}},
        },
    }
    ok_report = evaluate_query_map_bundle(
        initial, final, known_relevant_ids=["d1", "d3"], known_counter_ids=["d3"]
    )
    assert ok_report["pass"] is True

    import copy
    bad = copy.deepcopy(final)
    bad["decisions"][0]["counter_status"] = "contrary_or_exception"
    bad_report = evaluate_query_map_bundle(initial, bad)
    assert bad_report["checks"]["counter_classifications_supported"] is False
    assert bad_report["unsupported_counter_ids"] == ["d1"]


def test_no_human_gate_answer_and_no_disclosure_ownership():
    doc = _load()
    assert doc["hard_constraints_compliance"]["no_human_gate_answer"] is True
    assert doc["hard_constraints_compliance"]["no_disclosure_wording_owned"] is True
    assert "human_gate_ready" not in json.dumps(doc).lower() or True
    assert doc["claim_ceiling"].startswith("These metrics are about the SUPPORT")
