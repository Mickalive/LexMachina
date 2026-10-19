"""Packet-of-record v3 regression guards (accepted-config disclosure layer).

Why this module exists
----------------------
Factory direction v58 product lane ordered work (2): assemble the next gate
packet -- the packet of record v3 -- on the promoted tip with every accepted fix
present in-tree, freeze the bytes, publish the packet's raw sha256 and run the
shipped ledger against the exact committed bytes.

``product/packet_of_record.py`` writes the disclosure layer over a LIVE packet's
committed bundles.  Nothing else pinned that the committed disclosure layer:

  * reproduces from the committed bundle bytes (the "published claim does not
    reproduce from the committed tree" defect class of factory requirement 29);
  * carries the relevance_ordered geometry re-score on the SHIPPED post-rerank
    bundles under the re-hashed frozen rule, with the accepted FAIL preserved
    beside it and no threshold edited;
  * publishes the size-based mega-cluster share (never member_ids-based) with the
    threshold unchanged;
  * publishes the abstain-and-disclose three numbers together;
  * carries the packet'status raw sha256 and handoff content hashes that re-hash;
  * stays fail-closed -- never owner-ready while the accepted frozen bars are
    unmet.

These are contract/shape assertions only.  They never re-measure a frozen bar,
never re-tune a rubric and never assert legal usefulness.  Every number asserted
here is recomputed from the committed artifacts by this module, not read back
from a report.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product import packet_of_record as por  # noqa: E402
from product.query import packet_admission  # noqa: E402

PACKET = ROOT / "results" / "product" / "gate_packet" / "39319405429"

pytestmark = pytest.mark.skipif(
    not (PACKET / "PACKET_OF_RECORD.json").is_file(),
    reason="packet of record 39319405429 not present",
)

REQUIRED_THREE = ("support_rate_among_emitted", "n_abstained", "yield")


def _record() -> dict:
    return json.loads((PACKET / "PACKET_OF_RECORD.json").read_text(encoding="utf-8"))


def _packet() -> dict:
    return json.loads((PACKET / "packet.json").read_text(encoding="utf-8"))


def _disclosures() -> dict:
    return json.loads((PACKET / "disclosures.json").read_text(encoding="utf-8"))


def _handoff() -> dict:
    return json.loads((PACKET / "handoff.json").read_text(encoding="utf-8"))


def _qids() -> list[str]:
    return [q["qid"] for q in _packet().get("questions") or []]


def _bundle(qid: str) -> dict:
    return json.loads(
        (PACKET / "questions" / f"{qid}.bundle.json").read_text(encoding="utf-8"))


def test_packet_of_record_is_live_and_fail_closed():
    packet = _packet()
    assert packet["mode"] == "live"
    record = _record()
    # The accepted frozen bars are unmet, so nothing may claim readiness.
    assert record["packet_admitted"] is False
    assert record["packet_admission_blocked"] is True
    assert record["ready_for_owner_session"] is False
    assert record["human_gate_ready"] is False
    assert record["machine_gate_ready"] is False
    assert (record.get("admission") or {}).get("packet_admitted") is False
    # fail-closed is a property of the accepted admission module, re-run here
    out: dict = {"mode": "live"}
    packet_admission.enforce(out)
    assert out["packet_admission_blocked"] is True


def test_packet_raw_sha256_reproduces_from_committed_bytes():
    raw = (PACKET / "packet.json").read_bytes()
    digests = {
        hashlib.sha256(raw).hexdigest(),
        _record()["packet_raw_sha256"],
        _handoff()["packet_raw_sha256"],
    }
    assert len(digests) == 1
    # the disclosures / handoff bytes the record names must also re-hash
    assert por._sha256_file(PACKET / "disclosures.json") == _record()["disclosures_sha256"]
    assert por._sha256_file(PACKET / "handoff.json") == _record()["handoff_sha256"]


def test_every_bundle_is_re_verifiable_by_the_shipped_ledger():
    record = _record()
    ledger = record["ledger"]
    assert set(ledger["admissible_questions"]) == set(_qids())
    assert ledger["blocked_questions"] == []
    assert record["packet_admission_blocked"] is True


def test_geometry_rescore_reproduces_and_preserves_the_accepted_fail():
    disc = _disclosures()
    for qid in _qids():
        recorded = disc["per_bundle"][qid]["geometry_rescore"]
        fresh = por.geometry_rescore(_bundle(qid), qid)
        assert json.dumps(recorded, sort_keys=True) == json.dumps(fresh, sort_keys=True)
        # accepted FAIL is reported side by side, verbatim
        assert recorded["accepted_fail_preserved"]["team_run_id"] == 38846038296
        assert recorded["accepted_fail_preserved"]["accept_commit"] == "15362f6"
        # frozen rule identity re-derived, never re-tuned
        assert recorded["frozen_rules_sha256"] == por.FROZEN_GEOMETRY_RULES_SHA256
        assert recorded["shipped"]["n_criteria"] == 11
        assert recorded["variant_rescore"]["geometry_variant"] == por.ADOPTABLE_VARIANT
        assert recorded["variant_rescore"]["axis_x_label"] == por.V2_AXIS_X_LABEL
        # the variant is never applied twice: when the packet ships it, the
        # re-score IS the shipped state and the basis says so
        if recorded["shipped"]["geometry_variant"] == por.ADOPTABLE_VARIANT:
            assert recorded["variant_rescore"]["basis"].startswith(
                "shipped_bundle_is_already_the_adopted_variant")
            assert recorded["variant_rescore"]["n_pass"] == recorded["shipped"]["n_pass"]


def test_shipped_packet_ships_the_adopted_geometry_variant():
    # The packet of record is assembled with the accepted variant enabled, so the
    # "shipped" state the re-score describes is the state the map actually ships.
    disc = _disclosures()
    for qid in _qids():
        shipped = disc["per_bundle"][qid]["geometry_rescore"]["shipped"]
        assert shipped["geometry_variant"] == por.ADOPTABLE_VARIANT
        assert (_bundle(qid).get("provenance") or {}).get("geometry_variant") == por.ADOPTABLE_VARIANT

def test_mega_cluster_disclosure_is_size_based_with_threshold_unchanged():
    disc = _disclosures()
    for qid in _qids():
        m = disc["per_bundle"][qid]["mega_cluster_disclosure"]
        assert "size" in m["definition"]
        assert m["bar"] == 0.5
        assert m["threshold_edited"] is False
        assert m["size_based_not_member_ids"] is True
        # the member_ids share is published beside the size-based share
        assert "largest_cluster_member_ids_share" in m["shipped_geometry"]


def test_mega_cluster_never_publishes_a_double_applied_phantom_variant_state():
    # apply_geometry_variant is not idempotent.  When the shipped bundle
    # already carries the adopted variant, the "variant" verdict must BE the
    # shipped verdict -- a re-application would publish a largest-cluster share
    # that exists nowhere in the packet (resume-run discovery on 39319405429).
    disc = _disclosures()
    for qid in _qids():
        m = disc["per_bundle"][qid]["mega_cluster_disclosure"]
        if (_bundle(qid).get("provenance") or {}).get("geometry_variant") == por.ADOPTABLE_VARIANT:
            assert m["variant_basis"].startswith("shipped_bundle_is_already_the_adopted_variant")
            assert m["variant_geometry"]["largest_cluster_share"] == \
                m["shipped_geometry"]["largest_cluster_share"]
            assert m["variant_geometry"]["fired"] == m["shipped_geometry"]["fired"]


def test_counter_anchor_three_numbers_published_together():
    disc = _disclosures()
    for qid in _qids():
        a = disc["per_bundle"][qid]["counter_anchor"]
        for key in REQUIRED_THREE:
            assert key in a, f"{qid} missing {key}"
        assert a["mode"] == "abstain-and-disclose"
        assert a["published_together"] == list(REQUIRED_THREE)
        fresh = por.counter_anchor_three_numbers(_bundle(qid))
        assert json.dumps(fresh, sort_keys=True) == json.dumps(a, sort_keys=True)


def test_handoff_content_sha256_reproduces_via_the_product_hasher():
    handoff = _handoff()
    for b in handoff["bundles"]:
        bundle = _bundle(b["qid"])
        assert por.content_sha256(bundle) == b["content_sha256"]
    assert handoff["human_gate_ready"] is False
    assert handoff["machine_gate_ready"] is False


def test_check_mode_reproduces_the_whole_disclosure_layer():
    result = por.check(PACKET)
    assert result["ok"] is True, result["mismatches"]


def test_assembler_refuses_a_fixture_packet_and_never_mutates_bundles(tmp_path: Path):
    # A fixture packet is rehearsal, not gate material: assemble must refuse it.
    fake = tmp_path / "fixture-packet"
    fake.mkdir()
    (fake / "manifest.json").write_text(json.dumps({"questions": []}), encoding="utf-8")
    (fake / "packet.json").write_text(json.dumps({"mode": "fixture", "questions": []}),
                                      encoding="utf-8")
    with pytest.raises(ValueError):
        por.assemble(fake, run_id="0", operator="test", tip="")

    # Re-running assemble must not change any bundle byte -- and must not
    # pollute the COMMITTED disclosure layer.  (Regression: an earlier version
    # of this test ran assemble over the real packet dir with tip="test", which
    # is exactly how the committed PACKET_OF_RECORD.json ended up carrying the
    # placeholder tip; the copy keeps the no-bundle-mutation assertion without
    # writing into the tracked tree.)
    copy = tmp_path / "packet-copy"
    shutil.copytree(PACKET, copy)
    qids = _qids()
    before = {q: hashlib.sha256((copy / "questions" / f"{q}.bundle.json").read_bytes()).hexdigest()
              for q in qids}
    record_before = (PACKET / "PACKET_OF_RECORD.json").read_bytes()
    por.assemble(copy, run_id="39319405429", operator="test-copy", tip="tip-under-test")
    after = {q: hashlib.sha256((copy / "questions" / f"{q}.bundle.json").read_bytes()).hexdigest()
             for q in qids}
    assert before == after
    copied_record = json.loads((copy / "PACKET_OF_RECORD.json").read_text(encoding="utf-8"))
    assert copied_record["tip_commit"] == "tip-under-test"
    assert (PACKET / "PACKET_OF_RECORD.json").read_bytes() == record_before


def test_committed_tip_commit_is_a_real_sha_not_a_placeholder():
    tip = _record()["tip_commit"]
    assert tip and tip != "test", "tip_commit must name the promoted tip, not a placeholder"
    assert len(tip) >= 7


def test_retrieval_provenance_never_conflates_cache_replay_with_network():
    # audit CYCLE_39310811831 R2: a warm-cache read-through replay narrated as
    # a live-network search.  The block must always equal the bundle's own
    # bytes, and a 0-network build must classify as replay, never live_network.
    disc = _disclosures()
    for qid in _qids():
        recorded = disc["per_bundle"][qid]["retrieval_provenance"]
        bundle = _bundle(qid)
        fresh = por.retrieval_provenance(bundle)
        assert json.dumps(recorded, sort_keys=True) == json.dumps(fresh, sort_keys=True)
        req = (bundle.get("provenance") or {}).get("request_summary") or {}
        assert recorded["network_calls"] == req.get("network_calls")
        assert recorded["cache_hits"] == req.get("cache_hits")
        if recorded["network_calls"] == 0 and (recorded["cache_hits"] or 0) > 0:
            assert recorded["classification"] == "cache_replayed_read_through"
        if (recorded["network_calls"] or 0) > 0:
            assert recorded["classification"] == "live_network"
        assert recorded["fixture_mode"] is False


def test_counter_status_rf1_split_published_and_cited_never_counts_as_counter():
    # audit CYCLE_39310811831 R3 (RF1 recurrence): cited rows labelled counter.
    disc = _disclosures()
    from product.query import counter_status
    for qid in _qids():
        recorded = disc["per_bundle"][qid]["counter_status_rf1"]
        bundle = _bundle(qid)
        rows = bundle.get("decisions") or []
        fresh = por.counter_status_rf1(bundle)
        assert json.dumps(recorded, sort_keys=True) == json.dumps(fresh, sort_keys=True)
        assert recorded["single_source_of_truth"] == "product/query/counter_status.py"
        assert recorded["n_counter_authorities"] == counter_status.counter_authority_count(rows)
        assert recorded["n_status_bearing"] == counter_status.counter_status_bearing_count(rows)
        # no cited decision id may ever appear among counter authorities
        cited_ids = {str(d.get("decision_id")) for d in rows
                     if str(d.get("counter_status") or "none") == "cited"}
        assert not (set(recorded["counter_authority_ids"]) & cited_ids)
        assert sum(recorded["histogram"].values()) == len(rows)
        # both counts always published together, never one alone
        assert "n_counter_authorities" in recorded and "n_status_bearing" in recorded


def test_evidence_hydration_counts_match_the_bundle_bytes():
    disc = _disclosures()
    for qid in _qids():
        recorded = disc["per_bundle"][qid]["evidence_hydration"]
        fresh = por.hydration_summary(_bundle(qid))
        assert json.dumps(recorded, sort_keys=True) == json.dumps(fresh, sort_keys=True)
        assert recorded["n_hydrated"] == recorded["n_hydrated_ids"] == len(
            recorded["hydrated_ids"])
        if recorded["requested"] is not None:
            assert recorded["n_hydrated"] <= recorded["requested"]
