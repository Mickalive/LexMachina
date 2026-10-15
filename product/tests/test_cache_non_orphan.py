"""Cycle-38759730609 required-fix tests: the 20 committed OpenCaseLaw cache
entries must be genuinely consumed by an offline replay, and the persisted
claim-path bundle must be that replay - not substitute content.

Required-fix provenance: results/audit/product/CYCLE_38759730609_GATE.json
(gate=REVISE) required a product test that *calls*
``run_query_initial(<recorded query>, top_n=120, retrieval_mode='offline')``
and asserts request_summary.network_calls == 0, cache_hits >= 8,
len(decisions) >= 100, per-decision decision_id/citation/canonical_url/x/y/
cluster_id, non-empty cluster labels and member_ids, and
validate_bundle(bundle) == [], while leaving the four frozen
product/reality_check.py leg replays unchanged.

Run 38766812030 (operational resume of 38763217418) additionally froze
guards for the defect it found on the claim path: the bundle previously
committed at results/product/CYCLE_38759730609_bundle.json contained 120
synthetic ``bge_BGE_test_*`` decisions labelled ``test decision group N``
instead of the offline replay. The synthetic bytes are preserved at
reports/product/incidents/synthetic_bundle_38759730609.RETIRED.json
(sha256 3f90bd560842c74d93f0dc3abde8b5e5acded2103eb31a541a819a132ba5a0d4).

Run 38779139471 (operational resume of 38776384327) freezes the citation
guards demanded by results/audit/product/CYCLE_38766812030_GATE.json
(gate=REVISE) required_fixes[0] ``must_add_guard``: no citation string may be
shared by two decisions, no citation-channel row may carry a citation seed's
own reference, and an unhydrated citation shell's citation must be its own
docket number or its own decision_id. The superseded artifact that failed
those guards (sha256
bc1165bcd3b6c5da660a0818342a3926429e35442cb224d4f2ff966a19365322) is
preserved byte-for-byte at
reports/product/incidents/foreign_citations_bundle_38759730609.RETIRED.json.
"""
from __future__ import annotations

import json
import math
import urllib.parse
from pathlib import Path

from product.query.bundle import validate_bundle
from product.query.pipeline import CITE_CHANNELS, _candidate_to_product, run_query_initial
from product.replay_bundle import citation_findings

PRODUCT_ROOT = Path(__file__).resolve().parents[2]
BUNDLE_PATH = PRODUCT_ROOT / "results/product/CYCLE_38759730609_bundle.json"
SUMMARY_PATH = PRODUCT_ROOT / "results/product/reality_check/summary_ci_38604340726.json"

RECORDED_QUERY = "Responsabilite penale de l'entreprise selon l'art. 102 CP"
RECORDED_TOP_N = 120

REQUIRED_NON_NULL = ("decision_id", "citation", "canonical_url", "x", "y", "cluster_id")
REQUIRED_KEYS = ("is_outlier", "source_url")
SOURCE_HOST_SUFFIX = "opencaselaw.ch"


def _assert_citations_are_own(bundle: dict) -> None:
    """required_fixes[0] guards: no foreign/duplicated citation ever ships.

    The three assertions are the gate's own ``must_add_guard`` plus the
    product's stronger shell-identity check; the helper
    ``product.replay_bundle.citation_findings`` implements them once and is
    also enforced by ``replay_bundle.py`` (exit 6).
    """
    decisions = bundle["decisions"]
    cited = [d for d in decisions if d.get("citation")]
    # Gate formula, verbatim: distinct citations == distinct citing decisions.
    assert len({d["citation"] for d in cited}) == len({d["decision_id"] for d in cited}), (
        "a citation string is shared by two decisions: "
        + str(citation_findings(bundle)["citation_duplicates"])
    )

    findings = citation_findings(bundle)
    assert findings["citation_channel_seed_refs"] == [], (
        "a citation-channel row carries a citation seed's own reference "
        f"(foreign attribution): {findings['citation_channel_seed_refs'][:5]}"
    )
    assert findings["pending_shell_identity"] == [], (
        "an unhydrated citation shell shows a citation that is neither its "
        f"docket number nor its decision_id: {findings['pending_shell_identity'][:5]}"
    )
    assert findings["citation_duplicates"] == {}, (
        f"duplicate citations across decisions: {findings['citation_duplicates']}"
    )
    has_cite_rows = any(
        set(d.get("channels") or ()) & CITE_CHANNELS for d in decisions
    )
    if has_cite_rows:
        assert findings["citation_seeds_checked"], (
            "citation-channel rows exist but provenance.stage_notes.citations."
            "per_seed recorded no seeds — the contamination guard would be blind"
        )


def _request_summary(bundle: dict) -> dict:
    prov = bundle["provenance"]
    remote = (prov.get("retrieval") or {}).get("remote") or {}
    return remote.get("request_summary") or prov.get("request_summary") or {}


def _assert_map_contract(bundle: dict, *, expect_offline_replay: bool) -> None:
    rs = _request_summary(bundle)
    if expect_offline_replay:
        assert rs.get("network_calls") == 0, f"Expected 0 network calls, got {rs.get('network_calls')}"
        assert rs.get("cache_hits", 0) >= 8, f"Expected >= 8 cache hits, got {rs.get('cache_hits')}"

    decisions = bundle["decisions"]
    assert len(decisions) >= 100, f"Expected >= 100 decisions, got {len(decisions)}"

    for i, d in enumerate(decisions):
        did = str(d.get("decision_id") or "")
        # The retired bundle's synthetic ids: bge_BGE_test_0000_2024.
        assert "test_" not in did.lower(), (
            f"Decision[{i}] carries synthetic id {did!r}; claim path must hold "
            "OpenCaseLaw-sourced decisions only"
        )
        for f in REQUIRED_NON_NULL:
            assert d.get(f) is not None and d.get(f) != "", (
                f"Decision[{i}] missing field '{f}'"
            )
        for f in REQUIRED_KEYS:
            assert f in d, f"Decision[{i}] missing key '{f}'"
        assert math.isfinite(d["x"]) and math.isfinite(d["y"]), (
            f"Decision[{i}] has non-finite x/y: {d['x']}, {d['y']}"
        )
        assert -1.0001 <= d["x"] <= 1.0001, f"Decision[{i}] x out of bounds: {d['x']}"
        assert -1.0001 <= d["y"] <= 1.0001, f"Decision[{i}] y out of bounds: {d['y']}"
        host = urllib.parse.urlparse(str(d["canonical_url"])).netloc
        assert host.endswith(SOURCE_HOST_SUFFIX), (
            f"Decision[{i}] canonical_url host {host!r} is not the OpenCaseLaw source"
        )

    decision_ids = {d["decision_id"] for d in decisions}
    clusters = bundle["clusters"]
    assert len(clusters) >= 2, f"Expected >= 2 clusters, got {len(clusters)}"
    for i, c in enumerate(clusters):
        label = str(c.get("label") or "")
        assert label, f"Cluster[{i}] missing label"
        assert "test decision group" not in label.lower(), (
            f"Cluster[{i}] carries a synthetic label: {label!r}"
        )
        members = c.get("member_ids") or []
        assert members, f"Cluster[{i}] missing member_ids"
        orphans = [m for m in members if m not in decision_ids]
        assert not orphans, f"Cluster[{i}] member ids not present in decisions: {orphans[:5]}"

    _assert_citations_are_own(bundle)

    errors = validate_bundle(bundle)
    assert errors == [], f"validate_bundle errors: {errors}"


def test_run_query_initial_offline_replay_contract():
    """required_fixes[3]: replay the recorded query from the committed cache."""
    bundle = run_query_initial(RECORDED_QUERY, top_n=RECORDED_TOP_N, retrieval_mode="offline")
    _assert_map_contract(bundle, expect_offline_replay=True)
    assert bundle["answer"]["status"] == "pending", (
        "map phase must stay zero-cost/zero-model (answer pending until enrich)"
    )


def test_persisted_claim_bundle_is_genuine_replay():
    """The artifact on the claim path must be the genuine offline replay.

    This is the regression guard for the defect found by run 38766812030:
    synthetic fixture decisions had been persisted under this exact path and
    described in the cycle report as a cache replay.
    """
    assert BUNDLE_PATH.is_file(), f"missing claim-path bundle {BUNDLE_PATH}"
    with open(BUNDLE_PATH, encoding="utf-8") as f:
        bundle = json.load(f)
    assert bundle.get("query") == RECORDED_QUERY, (
        f"claim-path bundle was built for a different query: {bundle.get('query')!r}"
    )
    _assert_map_contract(bundle, expect_offline_replay=True)


def test_cache_entries_unchanged_leg_replays():
    """The four frozen product/reality_check.py leg replays stay unchanged.

    This test ensures the cache non-orphan work does not regress the legacy
    legs that are part of the durable green run 38604340726.
    """
    with open(SUMMARY_PATH, encoding="utf-8") as f:
        summary = json.load(f)
    assert summary.get("all_legs_passed") is True, (
        "Durable green run legs must still be complete"
    )
    assert summary.get("legs_complete") is True, (
        "Leg replay completeness must still be true"
    )


def _shell_candidate(decision_id: str, *, direction_channel: str, citation: str,
                     docket: str | None, seed: str = "bger_6B_31_2019") -> dict:
    return {
        "decision_id": decision_id,
        "court": "Bundesgericht",
        "language": "de",
        "rank": 1,
        "score": 0.9,
        "score_kind": "citation_confidence",
        "provenance": f"ocl:{direction_channel} seed={seed}",
        "snippet": "",
        "canonical_url": f"https://mcp.opencaselaw.ch/decision/{decision_id}",
        "citation": citation,
        "docket_number": docket,
        "channels": [direction_channel],
        "detail_status": "pending",
        "record_kind": "citation_neighbour",
        "decision_date": "2025-11-03",
    }


def test_citation_shell_never_emits_the_seeds_reference():
    """required_fixes[0] root-cause unit test (foreign_citation_on_citation_channel_rows).

    For an *incoming* citation edge the adapter's ``target_ref`` is the CITED
    seed's reference (live payload shape: ``{source_decision_id: bger_7B_1163_2025,
    target_ref: '6B_31_2019', docket_number: '7B_1163/2025'}``), so the citing
    decision used to ship another decision's citation.  Product assembly must
    derive the row's own identity instead — docket number when the edge carries
    one, decision_id otherwise — while a non-shell search hit keeps the API's
    own citation untouched.
    """
    incoming = _shell_candidate(
        "bger_7B_1163_2025",
        direction_channel="citation.incoming",
        citation="6B_31_2019",          # the SEED's reference — the defect
        docket="7B 1163/2025",          # the citing decision's own docket
    )
    outgoing_no_docket = _shell_candidate(
        "bger_9C_55_2020",
        direction_channel="citation.outgoing",
        citation="9C_55_2020",
        docket=None,
    )
    search_hit = {
        "decision_id": "bge_BGE_142_IV_333",
        "court": "Bundesgericht",
        "language": "de",
        "rank": 2,
        "score": 0.8,
        "provenance": "ocl:search",
        "snippet": "regeste text",
        "canonical_url": "https://mcp.opencaselaw.ch/decision/bge_BGE_142_IV_333",
        "citation": "BGE 142 IV 333",   # the search hit's OWN citation
        "docket_number": "BGE 142 IV 333",
        "channels": ["search"],
        "detail_status": "search_hit",
        "record_kind": "search_hit",
    }
    out = _candidate_to_product({"query": "q", "candidates": [incoming, outgoing_no_docket, search_hit]})
    by_id = {d["decision_id"]: d for d in out["decisions"]}

    assert by_id["bger_7B_1163_2025"]["citation"] == "7B 1163/2025", (
        "an incoming citation shell must show its own docket, not the seed's target_ref"
    )
    assert by_id["bger_9C_55_2020"]["citation"] == "bger_9C_55_2020", (
        "without a docket the shell falls back to its own decision_id"
    )
    assert by_id["bge_BGE_142_IV_333"]["citation"] == "BGE 142 IV 333", (
        "non-citation-shell rows keep the API's own citation"
    )

    findings = citation_findings(out)
    assert findings["citation_duplicates"] == {}
    assert findings["citation_channel_seed_refs"] == []
    assert findings["pending_shell_identity"] == []


def test_claim_bundle_content_hash_matches_a_fresh_replay():
    """The artifact's identity must be reproducible off the generating machine.

    Audit F2 (cycle 38779139471) compared raw file sha256 values across
    machines; those can never agree because the bundle embeds wall-clock
    timings.  ``content_sha256`` excludes exactly the five re-measured timing
    fields, so the committed claim bundle and a fresh replay of the same query
    out of the same cache must agree on it.
    """
    from product.replay_bundle import content_sha256

    with open(BUNDLE_PATH, encoding="utf-8") as f:
        committed = json.load(f)
    fresh = run_query_initial(RECORDED_QUERY, top_n=RECORDED_TOP_N, retrieval_mode="offline")

    assert content_sha256(committed) == content_sha256(fresh), (
        "the committed claim bundle is not reproducible from the committed cache "
        "with the committed code"
    )


def test_replay_refuses_a_dangling_relation():
    """A relation naming a decision that is not on the map is unusable.

    ``replay_bundle.py`` exits 7 on it, in the same family as the exit-4/5/6
    guards: the claim path may not ship a relation the researcher cannot open.
    """
    from product.replay_bundle import genuine, inspect_bundle

    with open(BUNDLE_PATH, encoding="utf-8") as f:
        bundle = json.load(f)
    assert bundle["relations"], "the claim bundle is expected to carry typed relations"

    def on_map(b):
        return all(r["source"] in {d["decision_id"] for d in b["decisions"]}
                   and r["target"] in {d["decision_id"] for d in b["decisions"]}
                   for r in b["relations"])

    assert on_map(bundle), "shipped relations must reference mapped decisions"

    broken = json.loads(json.dumps(bundle))
    broken["relations"].append({
        "source": broken["decisions"][0]["decision_id"],
        "target": "bger_not_retrieved_0000",
        "kind": "citation",
    })
    findings = inspect_bundle(broken)
    assert findings["dangling_relations"], "the dangling relation must be detected"
    assert genuine(findings) is False, "a dangling relation must not count as genuine"


def test_replay_bundle_exits_7_on_a_dangling_relation(monkeypatch, tmp_path):
    """The CLI must refuse to write an artifact carrying an unopenable edge."""
    import product.replay_bundle as rb

    with open(BUNDLE_PATH, encoding="utf-8") as f:
        bundle = json.load(f)
    bundle["relations"].append({
        "source": bundle["decisions"][0]["decision_id"],
        "target": "bger_not_retrieved_0000",
        "kind": "citation",
    })
    monkeypatch.setattr(rb, "run_query_initial", lambda *a, **k: bundle)

    out = tmp_path / "must_not_exist.json"
    assert rb.main(["--query", RECORDED_QUERY, "--top-n", "120", "--out", str(out)]) == 7
    assert not out.exists(), "the replay must not write a bundle it just refused"
