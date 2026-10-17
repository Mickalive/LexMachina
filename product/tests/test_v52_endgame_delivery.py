"""v52 endgame delivery regression guards (P1 adoption / P2 rebuild / P3 handoff).

Why this module exists
----------------------
Factory direction v52 product lane P1-P3 added three product-owned code paths in
cycle 39027045675 (``product/query/counter_anchor.py``, ``product/rebuild_packet.py``,
and the adoption of the accepted ``frontier-counter-anchor-classifier``) plus the
rebuilt packet directory ``results/product/gate_packet/rebuilt-39027045675/``.
Unlike the sibling geometry adoption (``test_qmap_geometry_variant.py``) these
new paths shipped with **no regression test**, so nothing pinned:

  * the adoption seam reproducing the accepted incumbent numbers (65 scored /
    5 emitted / 60 abstained, yield 0.0769) and keeping abstained rows visible;
  * the vendored classifier's committed bytes against its own PROVENANCE hashes
    (tamper detection, parity with the geometry variant's provenance test);
  * pre-serving obligation (a): the SHIPPED bundle is ``post_rerank_product_bundle``
    and its frozen 11-criteria counts are published beside the pre-rerank
    reference with the per-criterion delta (never a promise of equality);
  * pre-serving obligation (b): the V2 axis label is ``retrieval relevance score``
    and the stale word ``rerank score`` is gone from axis metadata;
  * the size-based mega-cluster disclosure (``len(idx)/n``, bar unchanged at 0.5)
    and the source packet's fired warning at share 0.7696;
  * the P3 handoff ``content_sha256`` values reproducing via the product's own
    ``replay_bundle.content_sha256`` and the raw ``packet.json`` bytes;
  * zero forbidden constructions (the classifier's claim ceiling) in any
    committed rebuilt-packet artifact.

These are contract/shape assertions only.  They never re-measure a frozen bar,
never re-tune a rubric and never assert legal usefulness.  Every number asserted
below is recomputed from the committed artifacts by this module, not read back
from a report.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.query import counter_anchor as ca  # noqa: E402
from product.replay_bundle import content_sha256  # noqa: E402

REBUILT = ROOT / "results" / "product" / "gate_packet" / "rebuilt-39027045675"
SOURCE = ROOT / "results" / "product" / "gate_packet" / "38839347028"
QIDS = ("fr-bail-entretien", "de-kapitalverletzung", "it-responsabilita-medica")

pytestmark = pytest.mark.skipif(
    not (REBUILT / "handoff.json").is_file(),
    reason="rebuilt packet rebuilt-39027045675 not present",
)


def _handoff() -> dict:
    return json.loads((REBUILT / "handoff.json").read_text(encoding="utf-8"))


def _bundle(qid: str, *, source: bool = False) -> dict:
    root = SOURCE if source else REBUILT
    return json.loads((root / "questions" / f"{qid}.bundle.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# P1 - counter-anchor adoption seam
# --------------------------------------------------------------------------

def test_frozen_label_rubric_refuses_a_tampered_copy(tmp_path):
    """A re-frozen rubric invalidates the run: the seam must raise, never re-score."""
    raw = (ROOT / "product" / "frozen" / "RULES_LABEL.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ca.FROZEN_LABEL_RULES_SHA256
    tampered = tmp_path / "RULES_LABEL.json"
    tampered.write_bytes(raw + b"\n")
    with pytest.raises(ValueError):
        ca.load_frozen_rules(path=tampered)


def test_adoption_record_names_the_accepted_audit_and_never_re_assigns_polarity():
    rec = ca.adoption_record()
    assert rec["decision"] == "ADOPT"
    assert rec["mode"] == "abstain-and-disclose"
    assert rec["audit_gate"] == "PASS" and rec["safe_to_integrate"] is True
    assert rec["accept_commit"].startswith("d236f599")
    assert rec["frozen_label_rules_sha256"].startswith("4457e971")
    assert rec["default_mode"] == ca.MODE_ANCHOR
    # the claim ceiling binds every product artifact
    assert "never asserts that any specific decision IS" in rec["claim_ceiling"]


def test_forbidden_construction_detector_has_a_positive_and_negative_control():
    assert ca.find_forbidden_constructions("the map shows three colour-coded clusters") == []
    assert ca.FORBIDDEN_CONSTRUCTION_PATTERNS  # non-empty battery
    for sentence in (
        "Decision bge_110_II_391 is contrary authority",
        "we classify bger_4A_1_2020 as limiting",
        "the court asserts that bge_1 is supporting",
    ):
        assert ca.find_forbidden_constructions(sentence), sentence


def test_adoption_seam_reproduces_the_accepted_incumbent_numbers():
    """65 scored / 5 emitted / 60 abstained, yield 0.0769 - recomputed here.

    This is the exact incumbent population published by the accepted
    falsification and by the v52 P1 record; reproducing it from the committed
    source packet proves the seam, not a report, carries the numbers.
    """
    total_scored = total_emitted = total_abstained = 0
    for qid in QIDS:
        out = ca.apply_anchor_labels(_bundle(qid, source=True), qid=qid)
        prov = out["provenance"]["counter_anchor"]
        assert prov["applied"] is True
        assert prov["mode"] == "abstain-and-disclose"
        assert prov["frozen_rules_sha256"] == ca.FROZEN_LABEL_RULES_SHA256
        assert prov["n_scored"] == prov["n_emitted"] + prov["n_abstained"]
        # every emitted label is supported by construction; yield is emitted share
        assert prov["support_rate_among_emitted"] == (1.0 if prov["n_emitted"] else 0.0)
        assert prov["yield"] == pytest.approx(prov["n_emitted"] / prov["n_scored"])
        total_scored += prov["n_scored"]
        total_emitted += prov["n_emitted"]
        total_abstained += prov["n_abstained"]

    assert (total_scored, total_emitted, total_abstained) == (65, 5, 60)
    assert total_emitted / total_scored == pytest.approx(0.076923, abs=1e-6)


def test_abstained_rows_stay_visible_and_are_marked_not_dropped():
    out = ca.apply_anchor_labels(_bundle("it-responsabilita-medica", source=True),
                                 qid="it-responsabilita-medica")
    n_before = len(_bundle("it-responsabilita-medica", source=True)["decisions"])
    assert len(out["decisions"]) == n_before, "the seam must never drop a row"
    abstained = [d for d in out["decisions"]
                 if d.get("counter_status") == ca.ABSTAINED_STATUS]
    assert abstained, "the it bundle has abstained counter rows"
    for d in abstained:
        assert d["counter_anchor_label"] == "ABSTAIN"
        assert d.get("counter_reason_code")
        assert 0.0 <= float(d.get("counter_uncertainty", -1)) <= 1.0
    # an abstained row is still a row on the map: geometry is untouched
    assert all("x" in d and "y" in d and "cluster_id" in d for d in abstained)


def test_summary_publishes_support_abstention_and_yield_side_by_side():
    out = ca.apply_anchor_labels(_bundle("de-kapitalverletzung", source=True),
                                 qid="de-kapitalverletzung")
    s = ca.counter_anchor_summary(out)
    assert set(s) >= {"n_scored", "n_emitted", "n_abstained",
                      "support_rate_among_emitted", "yield"}
    assert s["n_scored"] == s["n_emitted"] + s["n_abstained"]
    assert s["n_abstained"] > 0  # abstain-and-disclose is not a silent emit-all


def test_resolve_anchor_profile_prefers_the_bundle_qid_and_falls_back_by_query():
    rules, _ = ca.load_frozen_rules()
    assert ca.resolve_anchor_profile(rules, qid="fr-bail-entretien") is not None
    # a query in an anchor's language resolves to some frozen profile
    prof = ca.resolve_anchor_profile(rules, query="Kündigung Mietvertrag Mietrecht",
                                     language="de")
    assert prof is not None
    # an unrelated query is refused rather than assigned an invented profile
    assert ca.resolve_anchor_profile(rules, query="quantum chromodynamics",
                                     language="de") is None


def test_vendored_classifier_matches_its_recorded_provenance_hashes():
    """Tamper detection parity with the vendored geometry variant."""
    root = ROOT / "product" / "vendored" / "frontier_counter_anchor_classifier"
    meta = json.loads((root / "PROVENANCE.json").read_text(encoding="utf-8"))
    assert meta["promoted_variant"] == "Outcome A (abstain-and-disclose)"
    assert meta["accept_commit"].startswith("d236f599")
    assert meta["frozen_label_rules_sha256"].startswith("4457e971")
    assert meta["vendored_files"]
    for rel, rec in meta["vendored_files"].items():
        digest = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        assert digest == rec["sha256"], f"vendored {rel} drifted from provenance"
        assert rec["matches_accepted_source"] is True


# --------------------------------------------------------------------------
# P2 - rebuilt packet obligations
# --------------------------------------------------------------------------

def test_shipped_bundle_is_post_rerank_and_records_the_one_shot_transform():
    """Pre-serving obligation (a): the scored bundle is literally post rerank."""
    for b in _handoff()["bundles"]:
        rr = b["rerank_product_bundle"]
        assert rr["applied"] is True
        assert rr["function"] == "product.query.relevance.rerank_product_bundle"
        assert rr["call_count"] == 1 and rr["runs_once"] is True
        assert rr["non_idempotent"] is True, (
            "rerank reads the adapter score as input; the shipped bytes are one-shot")
        assert rr["same_row_set"] is True
        assert rr["retrieval_score_raw_present"] is True


def test_obligation_a_publishes_post_rerank_counts_beside_the_measured_reference():
    """Comparison, not equality: both states and the per-criterion delta ship."""
    by_qid = {b["qid"]: b["geometry_scoring"] for b in _handoff()["bundles"]}
    assert set(by_qid) == set(QIDS)
    for qid in QIDS:
        gs = by_qid[qid]
        assert gs["bundle_state"] == "post_rerank_product_bundle"
        assert gs["frozen_rules_sha256"] == (
            "a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633")
        assert gs["n_criteria"] == 11
        assert gs["measured_pass_count"] in (7, 8)
        ref = gs["pre_rerank_reference"]
        assert ref["n_pass"] == gs["measured_pass_count"], (
            "the pre-rerank reference must reproduce the measured 7/8/7 state")
        comp = gs["comparison"]
        assert comp["absolute_bar"] == "11 of 11 criteria on every bundle"
        assert comp["absolute_bar_met_post_rerank"] is False, (
            "the geometry absolute bar is unmet under the measured states")
        assert isinstance(comp["criterion_flips"], dict)
    # the accepted measured counts are 7/7/8 and the post-rerank FR bundle drops
    assert by_qid["fr-bail-entretien"]["measured_pass_count"] == 8
    assert by_qid["fr-bail-entretien"]["n_pass"] < 8
    assert "COHERENCE_QUERY_LANG" in by_qid["fr-bail-entretien"]["comparison"]["criterion_flips"]


def test_obligation_b_axis_is_relabelled_and_the_stale_word_is_gone():
    """The V2 x axis is 'retrieval relevance score'; never 'rerank score'."""
    for b in _handoff()["bundles"]:
        assert b["axis_x_label"] == "retrieval relevance score"
    for name in ("handoff.json", "disclosures.json", "packet.json"):
        text = (REBUILT / name).read_text(encoding="utf-8")
        assert "rerank score" not in text, (
            f"{name} still carries the stale axis word 'rerank score'")


def test_mega_cluster_disclosure_is_size_based_with_the_threshold_unchanged():
    for b in _handoff()["bundles"]:
        m = b["mega_cluster_disclosure"]
        assert m["bar"] == 0.5 and m["threshold_edited"] is False
        assert "size" in m["definition"] and "len(idx)" in m["definition"]
        assert m["size_based_not_member_ids"] is True
        # the source packet's French bundle is the recorded fired example
        if b["qid"] == "fr-bail-entretien":
            src = m["source_packet"]
            assert src["fired"] is True
            assert src["largest_cluster_share"] == pytest.approx(0.7696, abs=1e-4)
            assert src["largest_cluster_share"] >= 0.5
            # the divergence that the size-based fix addresses: the member_ids
            # share is far below the bar while the size share is far above it
            assert src["largest_cluster_member_ids_share"] == pytest.approx(0.2304, abs=1e-4)
            assert src["largest_cluster_member_ids_share"] < 0.5
            assert m["fired_on_any_check"] is True


def test_no_committed_rebuilt_artifact_asserts_a_forbidden_construction():
    for name in ("handoff.json", "disclosures.json", "packet.json"):
        text = (REBUILT / name).read_text(encoding="utf-8")
        assert ca.find_forbidden_constructions(text) == [], name
    for qid in QIDS:
        q = (REBUILT / "questions" / f"{qid}.question.json").read_text(encoding="utf-8")
        assert ca.find_forbidden_constructions(q) == [], qid


# --------------------------------------------------------------------------
# P3 - handoff integrity + admission
# --------------------------------------------------------------------------

def test_handoff_content_sha256_reproduces_via_the_product_own_hasher():
    h = _handoff()
    for b in h["bundles"]:
        recomputed = content_sha256(json.loads(Path(b["bundle_path"]).read_text(
            encoding="utf-8")))
        assert recomputed == b["content_sha256"], f"{b['qid']} content hash drifted"


def test_handoff_packet_content_sha256_matches_the_raw_packet_bytes():
    h = _handoff()
    raw = (REBUILT / "packet.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == h["packet_content_sha256"]
    assert h["packet_path"].endswith("rebuilt-39027045675/packet.json")


def test_handoff_does_not_self_certify_and_admission_denies():
    from product.query import packet_admission as pa

    h = _handoff()
    assert h["self_certification"] is False
    assert h["human_gate_ready"] is False
    adm = pa.assess()
    assert adm["packet_admitted"] is False
    assert adm["ready_for_owner_session_allowed"] is False


def test_reproducibility_scope_disclosure_is_present_and_consistent():
    """The committed-bytes identity is stable; a from-source rebuild is not
    byte-identical across numeric environments. That boundary is disclosed so a
    recomputation diff is never misread as data tampering (the environment-scoped
    reproducibility class recorded for frontier-served-packet-falsification).
    """
    scope_path = ROOT / "results" / "product" / "gate_packet" / (
        "REBUILT_39027045675_REPRODUCIBILITY_SCOPE.json")
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    assert scope["schema"] == "product-rebuilt-packet-reproducibility-scope/1"
    assert scope["scope_finding"]
    assert scope["artifact_of_record"]
    by_qid = scope["per_bundle"]
    assert set(by_qid) == set(QIDS)
    for qid in QIDS:
        cell = by_qid[qid]
        # the committed bytes always re-hash to the published identity
        assert cell["committed_bytes_reproduce"] is True
        assert cell["committed_content_sha256"] == (
            {b["qid"]: b["content_sha256"] for b in _handoff()["bundles"]}[qid])
        assert cell["n_rows"] > 0
        assert cell["cluster_id_drift_rows"] <= cell["n_rows"]
