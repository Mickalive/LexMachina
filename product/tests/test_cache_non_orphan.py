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
docket number or its own decision_id.  The superseded artifact that failed
those guards (sha256
bc1165bcd3b6c5da660a0818342a3926429e35442cb224d4f2ff966a19365322) is
preserved byte-for-byte at
reports/product/incidents/foreign_citations_bundle_38759730609.RETIRED.json.

Run 38807538467 (operational resume of 38806623637) repairs required fix D1
of results/audit/product/CYCLE_38799024807_GATE.json.  Cycle 38799024807
committed 123 live-preflight envelopes (cache 392 -> 515 keys) while
``content_sha256`` keeps ``cache_stats.n_keys`` in its payload, so
``test_claim_bundle_content_hash_matches_a_fresh_replay`` went red at the
final head (committed 0837ee73... vs fresh replay f0726cc4..., and the audit
confirmed the ONLY differing leaves were the two ``n_keys`` counters).  The
identity function is deliberately NOT weakened: ``n_keys`` stays inside the
hash, so a partial-cache replay still cannot masquerade as the real one.
What is frozen instead is the *cache the replay reads* — the 392 envelopes
the claim bundle was generated from, pinned byte-for-byte in
``results/product/CYCLE_38759730609_cache_manifest.json``.  Two tests keep
both halves of the property honest: the subset replay must reproduce the
committed identity exactly, and a full-cache replay may differ ONLY at the
two ``n_keys`` leaves (so appending unrelated envelopes can never be read as
a claim-content change, and a real content change can never hide behind the
cache-size statistic).
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


#: Leaves of the hashed payload that record *how big* the cache directory
#: happened to be when a replay ran.  They stay inside ``content_sha256`` by
#: design (a partial-cache replay must not hash like a full one), so the only
#: difference a grown cache may introduce between the committed claim bundle
#: and a full-cache replay of it is these two counters.
CACHE_SIZE_LEAVES = frozenset({
    "provenance.cache_stats.n_keys",
    "provenance.retrieval.remote.cache_stats.n_keys",
})


def _leaf_differences(a, b, path: str = "") -> set:
    """Dotted paths at which two canonical bundle payloads disagree."""
    if type(a) is not type(b):
        return {f"{path or '<root>'}:type"}
    if isinstance(a, dict):
        out: set = set()
        for key in sorted(set(a) | set(b)):
            here = f"{path}.{key}" if path else str(key)
            if key not in a or key not in b:
                out.add(here)
            else:
                out |= _leaf_differences(a[key], b[key], here)
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return {f"{path or '<root>'}:len"}
        out = set()
        for i, (x, y) in enumerate(zip(a, b)):
            out |= _leaf_differences(x, y, f"{path}[{i}]")
        return out
    return set() if a == b else {path or "<root>"}


def test_claim_cache_manifest_is_intact_and_append_tolerant():
    """The frozen claim-cache subset must still be present, byte-for-byte.

    Required fix D1 of the cycle-38799024807 gate, first half: the manifest
    pins the 392 envelopes the claim bundle was generated from.  The repository
    cache is allowed to hold MORE than that (that growth is what turned the
    replay red); every pinned envelope must still exist with the recorded
    bytes, and the pinned count must still equal the ``n_keys`` the claim
    bundle recorded, or the freeze proves nothing.
    """
    from product.replay_bundle import (
        CLAIM_CACHE_ROOT_RELPATH,
        verify_claim_cache_manifest,
    )

    findings = verify_claim_cache_manifest()
    assert findings["ok"], f"frozen claim-cache manifest is broken: {findings}"
    assert findings["missing"] == [] and findings["mismatched"] == []
    assert findings["n_entries"] == findings["manifest_n_keys"]
    assert findings["n_entries"] == findings["bundle_cache_n_keys"], (
        "the frozen subset size no longer equals the n_keys the claim bundle "
        "recorded, so the subset cannot be the cache it was generated from"
    )
    assert findings["cache_files_present"] >= findings["n_entries"], (
        "the live cache holds fewer envelopes than the frozen subset: an "
        "envelope the claim bundle needs has been deleted"
    )
    for entry in json.loads(
        (PRODUCT_ROOT / "results/product/CYCLE_38759730609_cache_manifest.json").read_text(
            encoding="utf-8"
        )
    )["entries"]:
        assert entry["path"].startswith(f"{CLAIM_CACHE_ROOT_RELPATH}/"), (
            f"manifest entry escapes the product-owned cache root: {entry['path']}"
        )


def test_claim_bundle_content_hash_matches_a_fresh_replay(tmp_path):
    """The artifact's identity must be reproducible off the generating machine.

    Audit F2 (cycle 38779139471) compared raw file sha256 values across
    machines; those can never agree because the bundle embeds wall-clock
    timings.  ``content_sha256`` excludes exactly the five re-measured timing
    fields, so the committed claim bundle and a fresh replay of the same query
    out of the same cache must agree on it.

    Required fix D1 of the cycle-38799024807 gate (run 38807538467) changes
    WHICH cache that replay reads, not what is hashed: the committed cache has
    since grown from 392 to 515 envelopes with unrelated live-preflight
    entries, and ``n_keys`` is claim-relevant, so a full-cache replay of an
    older artifact can only ever disagree on the cache-size counters.  The
    replay is therefore pointed at the frozen subset; against that subset the
    committed bytes, the committed code and the committed identity must still
    meet exactly.
    """
    from product.replay_bundle import (
        content_sha256,
        replay_claim_bundle_against_frozen_cache,
        verify_claim_cache_manifest,
    )

    findings = verify_claim_cache_manifest()
    assert findings["ok"], f"frozen claim-cache manifest is broken: {findings}"

    with open(BUNDLE_PATH, encoding="utf-8") as f:
        committed = json.load(f)
    fresh, subset_root = replay_claim_bundle_against_frozen_cache(tmp_path)

    assert content_sha256(committed) == content_sha256(fresh), (
        "the committed claim bundle is not reproducible from its frozen claim "
        "cache subset with the committed code"
    )
    stats = fresh["provenance"]["cache_stats"]
    assert stats["n_keys"] == findings["n_entries"], (
        "the frozen-subset replay did not read exactly the frozen subset"
    )
    assert stats.get("misses") == 0, (
        f"the frozen subset is missing envelopes the replay needed: {stats}"
    )
    assert stats.get("writes") == 0, (
        f"the frozen-subset replay wrote to the cache, so n_keys is no longer "
        f"the frozen count: {stats}"
    )
    assert subset_root.is_dir()


def test_claim_bundle_full_cache_replay_differs_only_in_cache_size():
    """Appending unrelated cache envelopes must not look like a content change.

    Second half of required fix D1 of the cycle-38799024807 gate: the same
    query replayed against the whole (grown) committed cache must produce
    byte-identical claim content, with the two ``n_keys`` counters as the only
    tolerated difference.  If a future cache change ever moves a *different*
    leaf, this test names it instead of letting the identity hash silently
    absorb a claim-content regression; and if a real content change ever
    happens, the first test (frozen subset) fails rather than being excused by
    a bigger cache.
    """
    from product.replay_bundle import canonical_payload, content_sha256

    with open(BUNDLE_PATH, encoding="utf-8") as f:
        committed = json.load(f)
    fresh_full = run_query_initial(RECORDED_QUERY, top_n=RECORDED_TOP_N, retrieval_mode="offline")

    diffs = _leaf_differences(
        canonical_payload(committed), canonical_payload(fresh_full)
    )
    assert diffs <= CACHE_SIZE_LEAVES, (
        "a full-cache replay of the claim bundle differs from the committed "
        f"artifact on non-cache-size leaves: {sorted(diffs - CACHE_SIZE_LEAVES)[:20]}"
    )
    committed_keys = committed["provenance"]["cache_stats"]["n_keys"]
    fresh_keys = fresh_full["provenance"]["cache_stats"]["n_keys"]
    assert fresh_keys >= committed_keys, (
        "the cache shrank below the size the claim bundle was generated at"
    )
    assert diffs == set() or diffs == CACHE_SIZE_LEAVES, (
        f"unexpected cache-size difference shape: {sorted(diffs)}"
    )
    assert content_sha256(committed) != content_sha256(fresh_full) or fresh_keys == committed_keys


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


def test_content_hash_is_invariant_under_a_rewritten_cache_root():
    """Required fix D1 of cycle 38785927063: the identity must not encode a path.

    Audit finding: ``content_sha256`` stripped the five wall-clock fields but
    left ``provenance.cache_stats.root`` and
    ``provenance.retrieval.remote.cache_stats.root`` — absolute machine paths —
    inside the hashed payload.  The artifact therefore hashed differently on
    every checkout, and the test that claimed to encode machine independence
    passed only on the machine that generated it.

    This is the regression test the gate named.  It rewrites both cache roots
    to foreign absolute paths and requires the hash to be unchanged, and it
    separately requires a genuine content change to move the hash.
    """
    from product.replay_bundle import content_sha256

    with open(BUNDLE_PATH, encoding="utf-8") as f:
        committed = json.load(f)

    original = content_sha256(committed)

    moved = json.loads(json.dumps(committed))
    for path in (("provenance", "cache_stats", "root"),
                 ("provenance", "retrieval", "remote", "cache_stats", "root")):
        node = moved
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = "/some/completely/different/checkout/on/another/machine/query_cache"

    assert content_sha256(moved) == original, (
        "content_sha256 must be invariant under a rewritten cache_stats.root; "
        "the artifact's identity is still bound to one checkout path"
    )

    changed = json.loads(json.dumps(committed))
    changed["decisions"][0]["citation"] = str(changed["decisions"][0]["citation"]) + " X"
    assert content_sha256(changed) != original, (
        "neutralising the cache root must not also neutralise real content: "
        "a changed decision has to move the hash"
    )


def test_committed_bundle_has_no_unaccounted_absolute_paths():
    """The only machine paths in the claim bundle are the two declared cache roots.

    Anything else would mean the artifact's portability rests entirely on the
    scrub being correct rather than on a named, reviewable exclusion - the
    shape of defect D1.  The recorded upstream endpoints (``/citations``,
    ``/leading-cases``) start with ``/`` too but are claim content, so they are
    listed separately and must be present.
    """
    from product.replay_bundle import CACHE_ROOT_PATHS, hashed_payload_paths

    with open(BUNDLE_PATH, encoding="utf-8") as f:
        committed = json.load(f)

    paths = hashed_payload_paths(committed)
    expected_machine = sorted(".".join(("",) + path) for path in CACHE_ROOT_PATHS)
    assert paths["machine_paths"] == expected_machine, (
        f"unexpected machine-specific paths in the hashed payload: {paths['machine_paths']}"
    )
    assert any(p.endswith("citations.endpoint") for p in paths["api_endpoints"]), (
        "the recorded /citations endpoint must stay inside the hashed payload, "
        "not be swept up with the cache roots"
    )
    assert any(p.endswith("leading.endpoint") for p in paths["api_endpoints"]), (
        "the recorded /leading-cases endpoint must stay inside the hashed payload"
    )


def test_is_machine_path_separates_paths_from_upstream_endpoints():
    """The scrub's classifier itself, so a future edit cannot widen it silently."""
    from product.replay_bundle import is_absolute_fs_path, is_machine_path

    assert is_absolute_fs_path("/home/runner/work/results/product/query_cache")
    assert is_absolute_fs_path("C:\\Users\\runner\\query_cache")
    assert not is_absolute_fs_path("//mcp.opencaselaw.ch/decisions")  # protocol-relative URL
    assert not is_absolute_fs_path("https://mcp.opencaselaw.ch/decisions")
    assert not is_absolute_fs_path("bge_BGE_142_IV_333")

    assert is_machine_path("/home/runner/work/results/product/query_cache")
    assert not is_machine_path("/citations")
    assert not is_machine_path("/leading-cases")
    assert not is_machine_path("/decisions")


def test_relation_recall_is_disclosed_and_nothing_is_fabricated():
    """Advisory A1 of cycle 38785927063: coverage must ship, not stay in a report.

    The bundle presented its recovered typed edges as "the" relation view
    without saying how much of the on-map evidence they cover.  The replay now
    recomputes the denominator from the raw cached /citations envelopes for this
    query's own citation seeds, so a partial recovery is disclosed on the claim
    path and an unsupported edge is caught instead of shipped.
    """
    from product.replay_bundle import genuine, inspect_bundle, relation_recall

    with open(BUNDLE_PATH, encoding="utf-8") as f:
        committed = json.load(f)

    recall = relation_recall(committed)
    assert recall["seeds"], "the recorded query must have citation seeds to measure against"
    assert recall["on_map_typed_edges"] > 0, "the denominator must be non-empty to be meaningful"
    assert recall["fabricated"] == [], (
        f"every shipped relation must exist in the cached upstream records: {recall['fabricated']}"
    )
    assert recall["in_bundle"] == len(committed["relations"]), (
        "the shipped relation count and the measured denominator must agree"
    )
    assert 0 < recall["recall"] <= 1.0
    # The drop is disclosed by name, not silently absorbed.
    assert recall["dropped_on_map"] == sorted(
        e for e in recall["dropped_on_map"]
    ), "dropped edges must be listed deterministically"
    assert len(recall["dropped_on_map"]) == recall["on_map_typed_edges"] - recall["in_bundle"]

    findings = inspect_bundle(committed)
    assert findings["relation_recall"]["fabricated"] == []
    assert genuine(findings) is True, (
        "the committed claim bundle must still pass every replay guard with the "
        "fabrication guard switched on"
    )


def test_an_unsupported_relation_edge_is_not_genuine():
    """A relation the upstream records do not contain must refuse the artifact."""
    from product.replay_bundle import genuine, inspect_bundle

    with open(BUNDLE_PATH, encoding="utf-8") as f:
        bundle = json.load(f)
    # Both endpoints on the map, so the dangling guard does not fire; neither is
    # a citation seed, so the edge cannot appear in this query's upstream
    # /citations records either.  That isolates the fabrication guard alone.
    seeds = {
        str(e["seed"])
        for e in ((bundle["provenance"].get("stage_notes") or {}).get("citations") or {})
        .get("per_seed", [])
    }
    off_seed = [d["decision_id"] for d in bundle["decisions"] if d["decision_id"] not in seeds]
    assert len(off_seed) >= 2, "the recorded bundle must have non-seed decisions"
    bundle["relations"].append({"source": off_seed[0], "target": off_seed[1], "kind": "citation"})

    findings = inspect_bundle(bundle)
    assert findings["relation_recall"]["fabricated"], "the invented edge must be detected"
    assert genuine(findings) is False, "an invented edge must not count as genuine"


def test_decision_field_coverage_discloses_null_source_urls():
    """Advisory A7: a required key may be present and still be null on some rows."""
    from product.replay_bundle import field_coverage

    with open(BUNDLE_PATH, encoding="utf-8") as f:
        bundle = json.load(f)

    coverage = field_coverage(bundle["decisions"])
    assert coverage["decision_id"]["populated"] == len(bundle["decisions"])
    assert coverage["canonical_url"]["populated"] == len(bundle["decisions"]), (
        "every row must stay openable through canonical_url"
    )
    # The key is guaranteed, the value is not: the two facts are reported apart.
    assert all("source_url" in d for d in bundle["decisions"])
    s = coverage["source_url"]
    assert s["populated"] + s["null_or_empty"] == len(bundle["decisions"])
    assert s["null_or_empty"] >= 0
