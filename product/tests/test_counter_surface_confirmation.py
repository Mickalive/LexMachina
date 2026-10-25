"""Direction v68 — stage 2 of the counter-evidence seam (the surface→gate bridge).

Why this module exists
----------------------
The claim ceiling of the accepted product chain ends with:

    *"the comparative map-versus-ranked-list question stays VACUOUS until
    evidenced sound counter rows exist"*

and the shipped path produced almost none.  Measured on the flagship offline
family before this stage (``results/product/counter_content_family/`` and the
stage-1 provenance of the 2026-10-25 bundles): stage 1 saw **n_candidates=1**
per 100-row bundle and **n_selected=0** on every profile-bearing bundle, while
the accepted pool counter-surface scan (``counter_surface/2``) already held
**10..26 verbatim evidence sentences per bundle** that the frozen
confirm-or-abstain gate had never been shown — by its own contract it writes no
scored field.

``apply_surface_span_confirmation`` is that missing hand-off.  These tests pin
the contract that makes it safe to ship:

1. it writes a scored counter field ONLY on a frozen-gate confirmation of a
   byte-exact verbatim span that also passes the frozen D1-D4 content
   predicates;
2. an abstention is PUBLISHED, never converted into a label;
3. ``cited`` rows are excluded (``NON_COUNTER_STATUSES``: citing a case is the
   opposite of countering it) and the exclusion is reported, not silent;
4. rows stage 1 already owns are never re-processed, and stage 1's own
   provenance block is byte-identical with stage 2 on and off;
5. geometry, ranks, clusters and relations are never touched;
6. the population partition balances (no silent narrowing);
7. the kill-switch is inert-and-honest, and the stage is deterministic and
   idempotent;
8. the pipeline orders it AFTER the pool scan that produces its input.

No frozen gate, rubric, threshold or bar is imported, edited or re-tuned here.
"""
from __future__ import annotations

import copy
import json
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.query import counter_evidence_span as ces  # noqa: E402
from product.query.counter_anchor import SCORED_STATUSES  # noqa: E402
from product.query.counter_status import counter_authority_count  # noqa: E402

SLUG = "rent-default"
BUNDLE = ROOT / "results" / "product" / "offline_slice" / "20261025T045400Z" / \
    "rent-default.bundle.json"


def _enrich(surface_span_env: str | None) -> dict:
    from product.query.pipeline import enrich_query_bundle, run_query_initial
    from product.reality_check import LEGS

    import os

    real_connect = socket.socket.connect

    def _no_network(*_a, **_k):
        raise AssertionError("offline test attempted network access")

    socket.socket.connect = _no_network
    try:
        if surface_span_env is None:
            os.environ.pop(ces.SURFACE_SPAN_ENV, None)
        else:
            os.environ[ces.SURFACE_SPAN_ENV] = surface_span_env
        initial = run_query_initial(LEGS[SLUG], top_n=100, retrieval_mode="fixture")
        return enrich_query_bundle(
            initial, retrieval_mode="fixture", fixture_generation=True)
    finally:
        socket.socket.connect = real_connect
        os.environ.pop(ces.SURFACE_SPAN_ENV, None)


@pytest.fixture(scope="module")
def bundles():
    """The same fixture enrich, stage 2 off and stage 2 on."""
    return {"off": _enrich("off"), "on": _enrich(None)}


@pytest.fixture()
def base(bundles):
    """A bundle produced WITHOUT stage 2, for direct stage-2 unit calls."""
    return copy.deepcopy(bundles["off"])


def _prov(bundle: dict) -> dict:
    return (bundle.get("provenance") or {}).get("counter_evidence_span_surface") or {}


# ---------------------------------------------------------------------------
# 1. it only confirms, and only with verbatim + content-clean evidence
# ---------------------------------------------------------------------------

def test_stage2_confirms_rows_that_stage1_never_reached(bundles):
    on = bundles["on"]
    p1 = (on["provenance"] or {}).get("counter_evidence_span") or {}
    p2 = _prov(on)
    assert p2["applied"] is True
    assert p2["proposal_channel"] == "counter_surface_signal"
    # the shipped slice previously confirmed ZERO rows through stage 1 alone
    assert p1.get("n_selected", 0) == 0, "stage-1 baseline moved; re-measure"
    assert p2["n_selected"] >= 1, "the bridge did not produce any evidenced row"
    assert set(p2["selected_ids"]) <= set(p2["candidate_ids"])
    # the product-visible counter-authority count moved with it
    assert counter_authority_count(on["decisions"]) > counter_authority_count(
        bundles["off"]["decisions"])


def test_every_confirmed_quote_is_byte_exact_and_content_clean(bundles):
    by_id = {d["decision_id"]: d for d in bundles["on"]["decisions"]}
    p2 = _prov(bundles["on"])
    assert p2["selected_ids"]
    for did in p2["selected_ids"]:
        row = by_id[did]
        rec = row["counter_evidence_span"]
        assert rec["stage"] == 2
        assert rec["proposal_channel"] == "counter_surface_signal"
        assert rec["verified"] is True and rec["selected"] is True
        assert row["counter_evidence_verified"] is True
        assert row["counter_status"] in SCORED_STATUSES
        quote = row["counter_evidence"]
        field = rec["field"]
        assert quote
        assert str(row.get(field) or "")[rec["start"]:rec["end"]] == quote
        assert ces.frozen_content_defects(quote, row) == [], (
            did, ces.frozen_content_defects(quote, row))
        # the content filter provenance is published alongside
    assert p2["content_filter"]["predicate_source_sha256"] == (
        ces.FROZEN_PREDICATE_SOURCE_SHA256)


def test_abstained_rows_are_published_and_never_labelled(bundles):
    on = bundles["on"]
    by_id = {d["decision_id"]: d for d in on["decisions"]}
    p2 = _prov(on)
    assert p2["n_abstained"] == len(p2["abstained"])
    assert p2["n_abstained"] >= 1, "the slice must exercise the abstention leg"
    for entry in p2["abstained"]:
        row = by_id[entry["decision_id"]]
        assert entry["reason_code"], entry
        # stage 2 writes a record ONLY on confirmation
        assert not (row.get("counter_evidence_span") or {}).get("stage") == 2, (
            entry["decision_id"])
        assert row.get("counter_evidence_verified") is not True, (
            entry["decision_id"], "abstention left a verified flag")
        assert row.get("counter_status") not in SCORED_STATUSES, (
            entry["decision_id"], "abstention wrote a scored status")
        assert entry["counter_status_unchanged"] == row.get("counter_status")
    # three numbers published together, support rate NOT pre-declared
    assert p2["n_candidates"] == p2["n_selected"] + p2["n_abstained"]
    assert "support_rate" not in json.dumps(
        {k: v for k, v in p2.items() if k != "claim_ceiling"})


# ---------------------------------------------------------------------------
# 2. population accounting — no silent narrowing
# ---------------------------------------------------------------------------

def test_population_partition_balances(bundles):
    p2 = _prov(bundles["on"])
    assert p2["n_candidates"] + p2["n_excluded_cited"] + p2["n_owned_by_stage_1"] == (
        p2["n_surface_signals"])
    assert p2["population_partition"]


def test_cited_surface_rows_are_excluded_and_reported(bundles):
    on = bundles["on"]
    p2 = _prov(on)
    by_id = {d["decision_id"]: d for d in on["decisions"]}
    for did in p2["excluded_cited_ids"]:
        assert by_id[did]["counter_status"] == "cited", did
        assert did not in p2["candidate_ids"]
    assert "opposite of countering" in p2["excluded_cited_reason"]


def test_stage1_owned_rows_are_never_reprocessed(bundles):
    on = bundles["on"]
    p1 = (on["provenance"] or {}).get("counter_evidence_span") or {}
    p2 = _prov(on)
    stage1_ids = set(p1.get("selected_ids") or []) | set(p1.get("abstained_ids") or [])
    overlap = stage1_ids & set(p2["candidate_ids"])
    assert not overlap, f"stage 2 re-processed stage-1 rows: {sorted(overlap)}"


def test_stage1_provenance_block_is_byte_identical_with_stage2_on_and_off(bundles):
    p1_off = (bundles["off"]["provenance"] or {}).get("counter_evidence_span")
    p1_on = (bundles["on"]["provenance"] or {}).get("counter_evidence_span")
    assert p1_off == p1_on


# ---------------------------------------------------------------------------
# 3. geometry / stage-independence / kill switch
# ---------------------------------------------------------------------------

def test_stage2_never_touches_geometry_ranks_clusters_or_relations(base):
    before_geo = {
        d["decision_id"]: (d["x"], d["y"], d["cluster_id"], d["rank"],
                           d.get("is_outlier"))
        for d in base["decisions"]
    }
    before_rel = json.dumps(base.get("relations"), sort_keys=True)
    before_clusters = json.dumps(base.get("clusters"), sort_keys=True)
    out = ces.apply_surface_span_confirmation(base)
    after_geo = {
        d["decision_id"]: (d["x"], d["y"], d["cluster_id"], d["rank"],
                           d.get("is_outlier"))
        for d in out["decisions"]
    }
    assert after_geo == before_geo
    assert json.dumps(out.get("relations"), sort_keys=True) == before_rel
    assert json.dumps(out.get("clusters"), sort_keys=True) == before_clusters
    assert len(out["decisions"]) == len(base["decisions"])


def test_manual_stage2_reproduces_the_pipeline_result(bundles, base):
    """Determinism: the pipeline's stage-2 output is a pure function of its input."""
    manual = ces.apply_surface_span_confirmation(base)
    piped = bundles["on"]
    for did in _prov(manual)["selected_ids"]:
        a = next(d for d in manual["decisions"] if d["decision_id"] == did)
        b = next(d for d in piped["decisions"] if d["decision_id"] == did)
        assert a["counter_status"] == b["counter_status"]
        assert a["counter_evidence"] == b["counter_evidence"]
        assert a["counter_evidence_verified"] == b["counter_evidence_verified"]


def test_stage2_is_idempotent(base):
    once = ces.apply_surface_span_confirmation(base)
    twice = ces.apply_surface_span_confirmation(once)
    assert _prov(once)["selected_ids"] == _prov(twice)["selected_ids"]
    assert _prov(once)["n_candidates"] == _prov(twice)["n_candidates"]
    assert _prov(once)["n_abstained"] == _prov(twice)["n_abstained"]
    scored = lambda b: {  # noqa: E731
        d["decision_id"]: (d.get("counter_status"), d.get("counter_evidence"),
                           d.get("counter_evidence_verified"))
        for d in b["decisions"]
    }
    assert scored(once) == scored(twice)


def test_kill_switch_is_inert_and_says_so(base):
    out = ces.apply_surface_span_confirmation(base, env={ces.SURFACE_SPAN_ENV: "off"})
    p = _prov(out)
    assert p["applied"] is False
    assert p["reason"] == f"{ces.SURFACE_SPAN_ENV}=off"
    assert p["enabled"] is False
    scored = lambda b: {  # noqa: E731
        d["decision_id"]: (d.get("counter_status"), d.get("counter_evidence_verified"))
        for d in b["decisions"]
    }
    assert scored(out) == scored(base)


def test_no_frozen_anchor_profile_reports_and_writes_nothing():
    """petty-theft resolves to no profile: the stage must refuse, not guess."""
    from product.reality_check import LEGS
    from product.query.pipeline import enrich_query_bundle, run_query_initial
    import os

    real_connect = socket.socket.connect

    def _no_network(*_a, **_k):
        raise AssertionError("offline test attempted network access")

    socket.socket.connect = _no_network
    try:
        os.environ.pop(ces.SURFACE_SPAN_ENV, None)
        initial = run_query_initial(LEGS["petty-theft-dismissal"], top_n=100,
                                    retrieval_mode="fixture")
        out = enrich_query_bundle(initial, retrieval_mode="fixture",
                                  fixture_generation=True)
    finally:
        socket.socket.connect = real_connect
    p = _prov(out)
    if p.get("reason") == "no_frozen_anchor_profile_for_query":
        assert p["applied"] is False
        assert p["n_selected"] == 0
        for d in out["decisions"]:
            assert not (d.get("counter_evidence_span") or {}).get("stage") == 2
    else:
        # a profile resolved for this query: then it must have applied cleanly
        assert p["applied"] is True


# ---------------------------------------------------------------------------
# 4. pipeline ordering
# ---------------------------------------------------------------------------

def test_pipeline_runs_stage2_after_the_pool_counter_surface_scan():
    src = (ROOT / "product" / "query" / "pipeline.py").read_text(encoding="utf-8")
    scan_at = src.index("audited = apply_counter_surface(")
    stage2_at = src.index("audited = apply_surface_span_confirmation(")
    assert scan_at < stage2_at, (
        "stage 2 must run after the pool scan that produces its input")
    # and after the stage-1 span pass it must not interfere with
    span1_at = src.index("audited = apply_verified_span_selection(")
    assert span1_at < scan_at


# ---------------------------------------------------------------------------
# 5. the shipped bundle on disk carries the same contract
# ---------------------------------------------------------------------------

def test_shipped_offline_bundle_carries_the_bridge_and_content_histogram_zero():
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    p1 = (bundle.get("provenance") or {}).get("counter_evidence_span") or {}
    p2 = _prov(bundle)
    assert p1.get("applied") is True, "stage-1 routing leg must still be applied"
    assert p2.get("applied") is True
    assert p2["n_selected"] >= 1
    by_id = {d["decision_id"]: d for d in bundle["decisions"]}
    for did in p2["selected_ids"]:
        row = by_id[did]
        assert row["counter_evidence_verified"] is True
        assert ces.frozen_content_defects(row.get("counter_evidence") or "", row) == []
    # the D2/D3/D4 defect histogram stays zero over the whole shipped bundle
    hist: dict[str, int] = {}
    for d in bundle["decisions"]:
        if d.get("counter_evidence_verified") is True:
            for defect in ces.frozen_content_defects(
                    d.get("counter_evidence") or "", d):
                hist[defect] = hist.get(defect, 0) + 1
    assert hist == {}, hist
