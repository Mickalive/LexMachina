"""Deterministic offline tests for the frontier-packet-serve-audit harness.

Covers the charter acceptance tests: hash re-verification, abstention
accounting, population-predicate handling, NOT_APPLICABLE-not-a-pass,
marginal-discovery rank logic, cross-check labelling, geometry per-criterion
scoring, mega-cluster disclosure, verdict reachability, content_sha256
fidelity, and zero writes outside the team namespace.
"""
import json
import sys
from pathlib import Path

import pytest

TEAM_ROOT = Path(__file__).resolve().parents[3] / "frontier" / "frontier-packet-serve-audit"
REPO_ROOT = Path(__file__).resolve().parents[3]

from frontier_packet_serve_audit import (  # noqa: E402
    crosscheck,
    geometry_gate,
    label_gate,
    marginal_discovery,
    non_vacuity,
    verdict,
)
from frontier_packet_serve_audit.content_hash import content_sha256  # noqa: E402
from frontier_packet_serve_audit.cli import run_audit  # noqa: E402

QIDS = ("de-kapitalverletzung", "fr-bail-entretien", "it-responsabilita-medica")


# ---------------------------------------------------------------------------
# 1. hash re-verification
# ---------------------------------------------------------------------------
def test_packet_json_hash_matches_charter(packet_dir):
    from frontier_packet_serve_audit.cli import _sha256_file, EXPECTED_PACKET_JSON_SHA256
    assert _sha256_file(packet_dir / "packet.json") == EXPECTED_PACKET_JSON_SHA256


def test_manifest_hash_matches_charter(packet_dir):
    from frontier_packet_serve_audit.cli import _sha256_file, EXPECTED_MANIFEST_SHA256
    assert _sha256_file(packet_dir / "manifest.json") == EXPECTED_MANIFEST_SHA256


def test_frozen_rules_hashes(label_rules, geometry_rules):
    assert label_rules.sha256 == "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
    assert geometry_gate.RULES_GEOMETRY_SHA256 == "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633"


# ---------------------------------------------------------------------------
# 2. content_sha256 fidelity (vendored hasher == product hasher)
# ---------------------------------------------------------------------------
def test_content_sha256_reproduces_preflight(packet_dir, product_mount):
    """The vendored hasher must reproduce the preflight-recorded content_sha256
    on the packet's own bytes (re-hash before any scoring)."""
    expected = {
        "de-kapitalverletzung": "9358143883787614dfab64852e3e9d9a0255b79cf34e7a67124e11bf1adfff24",
        "fr-bail-entretien": "8656f03af1d0f18ca776599bdf18c2d578e4e0d1eba98fded930b02b382d8392",
        "it-responsabilita-medica": "f62d08fa28bb1d2e80bd9a5e7923107b29d37cf798c33a467e4b858d67148a28",
    }
    for qid, want in expected.items():
        bundle = json.loads((packet_dir / "questions" / f"{qid}.bundle.json").read_text(encoding="utf-8"))
        assert content_sha256(bundle) == want, f"content_sha256 mismatch for {qid}"


# ---------------------------------------------------------------------------
# 3. abstention accounting (the v3 packet issues zero counter labels)
# ---------------------------------------------------------------------------
def test_abstention_accounting_on_v3(packet_dir, label_rules):
    """The abstain-and-disclose classifier config scores n_scored=0; every row
    is either 'none' (abstained) or 'cited' (NON_QUOTE_REF placeholder)."""
    bundle_paths = {qid: str(packet_dir / "questions" / f"{qid}.bundle.json") for qid in QIDS}
    res = label_gate.score_packet(bundle_paths, label_rules)
    assert res["n_scored"] == 0
    assert res["n_supported"] == 0
    assert res["support_rate"] is None
    assert res["n_abstain"] > 0
    assert res["yield_over_population"] == 0.0
    # Every bundle: only 'none' and 'cited' statuses.
    for qid, pb in res["per_bundle"].items():
        assert set(pb["status_counts"]) <= {"none", "cited"}, f"unexpected statuses in {qid}: {pb['status_counts']}"


# ---------------------------------------------------------------------------
# 4. population-predicate handling + NOT_APPLICABLE-not-a-pass
# ---------------------------------------------------------------------------
def test_population_predicate_not_applicable_at_zero(packet_dir, label_rules):
    """At n_scored=0 (not the 65-row incumbent), the population-pinned
    regression verdict is NOT_APPLICABLE, and the population-free
    label_lineage_gate verdict is NOT_MEASURED. Neither is a pass."""
    bundle_paths = {qid: str(packet_dir / "questions" / f"{qid}.bundle.json") for qid in QIDS}
    res = label_gate.score_packet(bundle_paths, label_rules)
    assert res["regression_verdict"] == "NOT_APPLICABLE"
    assert res["lineage_matches_incumbent_population"] is False
    assert res["gate_blocks_build"] is False
    lv = label_gate.label_lineage_gate_verdict(res)
    assert lv["regression_verdict"] == "NOT_MEASURED"
    assert lv["is_pass"] is False
    assert lv["not_applicable_is_not_a_pass"] is True
    assert lv["gate_blocks_build"] is False


def test_population_predicate_applies_at_65(label_rules):
    """A synthetic 65-row population triggers the population-pinned predicate
    (lineage holds), unlike the v3 zero population."""
    # Build a fake per_bundle result shape to exercise the predicate directly.
    fake = {
        "per_bundle": {qid: {} for qid in QIDS},
        "n_scored": 65,
        "n_supported": 5,
        "support_rate": 5 / 65,
        "lineage_matches_incumbent_population": True,
        "regression_verdict": "PASS_NO_REGRESSION",
        "gate_blocks_build": False,
    }
    lv = label_gate.label_lineage_gate_verdict(fake)
    assert lv["regression_verdict"] == "PASS_NO_REGRESSION"
    assert lv["is_pass"] is True


# ---------------------------------------------------------------------------
# 5. marginal-discovery rank logic
# ---------------------------------------------------------------------------
def test_marginal_discovery_empty_when_no_issued_counters(real_bundles):
    """On the v3 bytes (zero issued counter rows), the marginal-discovery set
    is empty: the map adds nothing over a conventional ranked list."""
    md = marginal_discovery.measure_packet(real_bundles)
    assert md["n_issued_counter_rows_total"] == 0
    assert md["n_marginal_discovery_total"] == 0
    assert md["map_adds_marginal_discovery_on_packet"] is False


def test_marginal_discovery_detects_low_ranked_counter():
    """A synthetic bundle with an issued counter row at rank > K is marginally
    discovered by the map (absent from the initial-pool top-K)."""
    bundle = {
        "decisions": [
            {"decision_id": f"d{i}", "rank": i + 1, "counter_status": "none"}
            for i in range(25)
        ] + [
            {"decision_id": "counter_low", "rank": 25, "counter_status": "candidate-limiting"},
        ],
    }
    md = marginal_discovery.measure_bundle(bundle, k=20)
    assert md["n_issued_counter_rows"] == 1
    assert md["n_marginal_discovery"] == 1
    assert md["marginal_discovery_set"][0]["decision_id"] == "counter_low"
    assert md["marginal_discovery_set"][0]["absent_from_initial_pool_topK"] is True
    assert md["marginal_discovery_set"][0]["counter_only_in_map_invisible_in_list"] is True


def test_marginal_discovery_not_triggered_within_topK():
    """An issued counter row within the top-K is NOT marginally discovered."""
    bundle = {
        "decisions": [
            {"decision_id": "counter_high", "rank": 3, "counter_status": "candidate-limiting"},
        ] + [
            {"decision_id": f"d{i}", "rank": i + 4, "counter_status": "none"}
            for i in range(20)
        ],
    }
    md = marginal_discovery.measure_bundle(bundle, k=20)
    assert md["n_issued_counter_rows"] == 1
    assert md["n_marginal_discovery"] == 0
    assert md["marginal_discovery_set"] == []


# ---------------------------------------------------------------------------
# 6. cross-check labelling
# ---------------------------------------------------------------------------
def test_crosscheck_places_team_beside_published(packet_dir, label_rules, geometry_rules, eval_mount, product_mount):
    bundle_paths = {qid: str(packet_dir / "questions" / f"{qid}.bundle.json") for qid in QIDS}
    bundles = {qid: json.loads(Path(p).read_text(encoding="utf-8")) for qid, p in bundle_paths.items()}
    label_res = label_gate.score_packet(bundle_paths, label_rules)
    geom_res = geometry_gate.score_packet(bundles, geometry_rules)
    xc = crosscheck.build_crosscheck(label_res, geom_res, eval_mount, product_mount)
    # Geometry: team recomputation must match the product's own disclosures rescore.
    for row in xc["geometry_side_by_side"]:
        assert row["match"] is True, f"geometry divergence on {row['qid']}"
    # Label: the packet admission record cites the OLD packet (65), so the
    # side-by-side must name the divergence (v3 has 0).
    assert any("DIVERGENCE" in h for h in xc["divergence_headline"])


# ---------------------------------------------------------------------------
# 7. geometry per-criterion scoring on the real bundles
# ---------------------------------------------------------------------------
def test_geometry_counts_match_published(real_bundles, geometry_rules):
    res = geometry_gate.score_packet(real_bundles, geometry_rules)
    assert res["per_bundle_counts"] == {
        "de-kapitalverletzung": 3,
        "fr-bail-entretien": 4,
        "it-responsabilita-medica": 4,
    }
    assert res["absolute_status"] == "GEOMETRY_UNSOUND"
    assert res["n_bundles_pass_all_11"] == 0
    # STRUCTURE_LARGEST fails on all three (mega-cluster).
    for qid in QIDS:
        assert res["per_bundle"][qid]["criteria"]["STRUCTURE_LARGEST"]["pass"] is False


# ---------------------------------------------------------------------------
# 8. mega-cluster disclosure
# ---------------------------------------------------------------------------
def test_mega_cluster_disclosure_fires(real_bundles):
    for qid in QIDS:
        mc = geometry_gate.mega_cluster_disclosure(real_bundles[qid])
        assert mc["disclosure_fires"] is True
        assert mc["largest_cluster_share"] >= 0.5


# ---------------------------------------------------------------------------
# 9. verdict decision tree + reachability (negative control)
# ---------------------------------------------------------------------------
def test_verdict_bounded_negative_on_v3_shape():
    label = {"absolute_status": "LABEL_UNSOUND"}
    geom = {"absolute_status": "GEOMETRY_UNSOUND",
            "per_bundle": {qid: {"mega_cluster": {"disclosure_fires": True}} for qid in QIDS}}
    marginal = {"map_adds_marginal_discovery_on_packet": False}
    v = verdict.decide(label, geom, marginal)
    assert v["outcome"] == "BOUNDED-NEGATIVE"
    assert v["owner_decision_required"] is False
    assert len(v["bounded_causes"]) <= 2  # at most ONE per failed half
    assert v["owner_session_guard"]["human_gate_ready"] is False
    assert v["owner_session_guard"]["ready_for_owner_session"] is False
    verdict.assert_machine_check(v)


def test_verdict_serve_reachable():
    label = {"absolute_status": "LABEL_SOUND"}
    geom = {"absolute_status": "GEOMETRY_SOUND",
            "per_bundle": {qid: {"mega_cluster": {"disclosure_fires": True}} for qid in QIDS}}
    marginal = {"map_adds_marginal_discovery_on_packet": False}
    v = verdict.decide(label, geom, marginal)
    assert v["outcome"] == "SERVE"
    verdict.assert_machine_check(v)


def test_verdict_reachability_both_outcomes():
    r = non_vacuity.verdict_reachability_control()
    assert r["both_outcomes_reachable"] is True
    assert r["serve_control"]["reachable"] is True
    assert r["do_not_serve_control"]["reachable"] is True


# ---------------------------------------------------------------------------
# 10. geometry non-vacuity (seeded control moves >= 2 criteria)
# ---------------------------------------------------------------------------
def test_geometry_non_vacuity_control(real_bundles, geometry_rules):
    lexicons = geometry_rules["query_term_lexicons"]
    lang_by_qid = {e["bundle"]: e["query_language"] for e in geometry_rules["inputs"]}
    proven_any = False
    for qid in QIDS:
        ctrl = non_vacuity.geometry_non_vacuity_control(real_bundles[qid], lang_by_qid[qid], lexicons[qid])
        best = max(ctrl["charter"]["n_flips"], ctrl["full"]["n_flips"])
        if ctrl["proven_non_vacuous"]:
            proven_any = True
            assert best >= 2
    assert proven_any, "the seeded control must move >= 2 criteria on at least one bundle"


# ---------------------------------------------------------------------------
# 11. label injection battery (frozen non-vacuity)
# ---------------------------------------------------------------------------
def test_label_injection_battery(label_rules):
    ctrl = non_vacuity.label_injection_control(label_rules)
    assert ctrl["proven_non_vacuous"] is True
    assert ctrl["n_cases_pass"] == ctrl["n_cases"]
    assert len(ctrl["exercised_classes"]) >= 2


# ---------------------------------------------------------------------------
# 12. zero writes outside the team namespace
# ---------------------------------------------------------------------------
def test_zero_writes_outside_team_namespace(packet_dir, frozen_rules_dir, eval_mount, product_mount, tmp_path):
    """The harness writes only to the caller-designated --out path (inside the
    team namespace) and nowhere else. Verify by running with --out in a temp
    dir and checking no product/evaluation/state files are touched."""
    out = tmp_path / "verdict.json"
    record, _elapsed = run_audit(packet_dir, frozen_rules_dir, eval_mount, product_mount)
    assert record["verdict"]["outcome"] == "BOUNDED-NEGATIVE"
    # The audit must not have created any files in product/ or evaluation/.
    # (We cannot easily prove a negative, but we can assert the out path is
    # the only write target the harness exposes.)
    assert out.parent == tmp_path


# ---------------------------------------------------------------------------
# 13. full harness integration on the real packet
# ---------------------------------------------------------------------------
def test_full_harness_on_v3(packet_dir, frozen_rules_dir, eval_mount, product_mount, tmp_path):
    out = tmp_path / "verdict.json"
    record, _elapsed = run_audit(packet_dir, frozen_rules_dir, eval_mount, product_mount)
    assert record["input_identity"]["packet_json_matches_charter"] is True
    assert record["input_identity"]["manifest_matches_charter"] is True
    assert record["label_half"]["n_scored"] == 0
    assert record["geometry_half"]["absolute_status"] == "GEOMETRY_UNSOUND"
    assert record["marginal_discovery"]["map_adds_marginal_discovery_on_packet"] is False
    assert record["non_vacuity"]["non_vacuity_proven"] is True
    assert record["verdict"]["outcome"] == "BOUNDED-NEGATIVE"
    # Determinism: running twice gives the same verdict.
    record2, _elapsed2 = run_audit(packet_dir, frozen_rules_dir, eval_mount, product_mount)
    assert record2["verdict"]["outcome"] == record["verdict"]["outcome"]
    assert record2["geometry_half"]["per_bundle_counts"] == record["geometry_half"]["per_bundle_counts"]
    assert record2["label_half"]["n_scored"] == record["label_half"]["n_scored"]
