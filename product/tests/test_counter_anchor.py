"""Tests for the accepted counter-anchor-classifier integration (v50 obligation 4).

The Frontier component ``frontier-counter-anchor-classifier`` (charter v1,
team run 38964146628, audit CYCLE_38964146628_GATE.json PASS, accept d236f599)
delivered a sentence-anchored counter-label decision function.  These tests
verify the product's abstain-and-disclose integration:

* the frozen rubric hash is verified on load (an edited rubric cannot silently
  change a verdict);
* the qid resolver matches the five frozen benchmark queries and returns
  ``None`` for unknown queries (fail closed);
* emitted labels keep their evidence-backed status;
* abstained rows are kept visible as ``abstained_unevidenced`` with a counted
  reason, never silently dropped;
* provenance records the emitted/abstained counts and the support rate.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "product") not in sys.path:
    sys.path.insert(0, str(ROOT / "product"))

from query.counter_anchor import (  # noqa: E402
    ABSTAINED_STATUS,
    FROZEN_RULES_SHA256,
    NO_ANCHOR_REASON,
    RULES_PATH,
    apply_counter_anchor_decisions,
    resolve_qid,
)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

def _rules() -> dict:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def _labeled_row(decision_id: str, status: str = "candidate-limiting",
                 evidence: str = "", **kw) -> dict:
    row = {
        "decision_id": decision_id,
        "counter_status": status,
        "counter_evidence": evidence,
        "language": "de",
        "title": "",
        "regeste": "",
        "rank": 10,
        "legal_area": "",
    }
    row.update(kw)
    return row


# --------------------------------------------------------------------------
# Frozen rubric integrity
# --------------------------------------------------------------------------

def test_frozen_rules_sha256_matches():
    """The vendored RULES_LABEL.json must be byte-identical to the frozen hash."""
    sha = hashlib.sha256(RULES_PATH.read_bytes()).hexdigest()
    assert sha == FROZEN_RULES_SHA256


def test_frozen_rules_hash_is_the_accepted_value():
    """The frozen hash is the one from the accepted audit (4457e971...)."""
    assert FROZEN_RULES_SHA256 == (
        "4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608"
    )


# --------------------------------------------------------------------------
# qid resolution
# --------------------------------------------------------------------------

@pytest.mark.parametrize("query,expected_qid", [
    ("Aktive Fürsorgepflicht des Arbeitgebers bei einer Kapitalverletzung",
     "de-kapitalverletzung"),
    ("Résiliation du bail pour défaut d'entretien du bailleur",
     "fr-bail-entretien"),
    ("Responsabilità del medico per errore terapeutico",
     "it-responsabilita-medica"),
    ("Kündigung Mietvertrag Mietrecht", "kuendigung-mietrecht"),
    ("Responsabilité pénale de l'entreprise selon l'art. 102 CP",
     "responsabilite-penale-entreprise-102cp"),
])
def test_resolve_qid_matches_frozen_queries(query, expected_qid):
    assert resolve_qid(query, _rules()) == expected_qid


def test_resolve_qid_returns_none_for_unknown_query():
    assert resolve_qid("completely unknown query about space law", _rules()) is None


def test_resolve_qid_returns_none_for_empty_query():
    assert resolve_qid("", _rules()) is None


# --------------------------------------------------------------------------
# apply_counter_anchor_decisions: pass-through
# --------------------------------------------------------------------------

def test_no_proposed_labels_is_pass_through():
    bundle = {"query": "test", "decisions": [
        {"decision_id": "a", "counter_status": "none"},
        {"decision_id": "b", "counter_status": "cited"},
    ]}
    out = apply_counter_anchor_decisions(bundle)
    prov = out["provenance"]["counter_anchor"]
    assert prov["n_proposed"] == 0
    assert prov["n_emitted"] == 0
    assert prov["n_abstained"] == 0
    assert prov["support_rate_emitted"] is None


def test_empty_decisions_is_pass_through():
    out = apply_counter_anchor_decisions({"query": "test", "decisions": []})
    assert out["provenance"]["counter_anchor"]["n_proposed"] == 0


# --------------------------------------------------------------------------
# apply_counter_anchor_decisions: fail-closed on unknown qid
# --------------------------------------------------------------------------

def test_unknown_qid_abstains_all_labels():
    """No authored anchor profile -> every proposed label is abstained."""
    bundle = {"query": "unknown query", "decisions": [
        _labeled_row("x1", evidence="some evidence"),
        _labeled_row("x2", status="candidate-contrary", evidence="other evidence"),
    ]}
    out = apply_counter_anchor_decisions(bundle)
    for d in out["decisions"]:
        assert d["counter_status"] == ABSTAINED_STATUS
        assert d["counter_reason_code"] == NO_ANCHOR_REASON
        assert d["counter_uncertainty"] == 1.0
        assert d["counter_evidence_verified"] is False
    prov = out["provenance"]["counter_anchor"]
    assert prov["n_proposed"] == 2
    assert prov["n_emitted"] == 0
    assert prov["n_abstained"] == 2
    assert prov["abstention_reasons"] == {NO_ANCHOR_REASON: 2}


def test_bjr_frozen_leg_fail_closes_no_anchor_profile():
    """Repair of audit R1 (cycle 39023182745).

    The live business-judgment-rule leg abstained ``bge_BGE_110_II_391`` with
    ``counter_status='abstained_unevidenced'``, and the cycle report/state
    wrongly attributed that to "its cited evidence failed the frozen rubric".
    The true cause is the fail-closed branch: the BJR question matches none of
    the five authored ``question_anchors``, so ``resolve_qid`` returns ``None``
    and the adapter records ``counter_reason_code='no_anchor_profile'`` without
    ever invoking ``decide_label``/the frozen rubric.  This test pins that
    distinction so the false causal claim cannot silently return.
    """
    from reality_check import LEGS  # noqa: E402  (frozen leg question strings)

    bjr_question = LEGS["business-judgment-rule"]
    assert resolve_qid(bjr_question, _rules()) is None, (
        "the BJR frozen-leg question must match no authored anchor profile"
    )
    bundle = {"query": bjr_question, "decisions": [
        _labeled_row("bge_BGE_110_II_391", evidence="cited evidence text"),
    ]}
    out = apply_counter_anchor_decisions(bundle)
    d = out["decisions"][0]
    assert d["counter_status"] == ABSTAINED_STATUS
    assert d["counter_reason_code"] == NO_ANCHOR_REASON, (
        "the abstention must be the fail-closed no_anchor_profile branch, "
        "not a frozen-rubric verdict"
    )
    assert d["counter_uncertainty"] == 1.0
    assert d["counter_evidence_verified"] is False
    prov = out["provenance"]["counter_anchor"]
    assert prov["qid"] is None
    assert prov["abstention_reasons"] == {NO_ANCHOR_REASON: 1}


# --------------------------------------------------------------------------
# apply_counter_anchor_decisions: emit and abstain on a known qid
# --------------------------------------------------------------------------

def test_known_qid_emits_and_abstains():
    """On a frozen query, supported rows are emitted and unsupported abstained."""
    # Use the real gate packet bundle for de-kapitalverletzung.
    bundle_path = (ROOT / "results" / "product" / "gate_packet" / "38839347028"
                   / "questions" / "de-kapitalverletzung.bundle.json")
    if not bundle_path.exists():
        pytest.skip("gate packet bundle not available")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    labeled = [d for d in bundle.get("decisions", [])
               if d.get("counter_status") not in (None, "", "none", "cited")]
    if not labeled:
        pytest.skip("no labeled rows in gate packet bundle")

    out = apply_counter_anchor_decisions(bundle)
    prov = out["provenance"]["counter_anchor"]
    assert prov["qid"] == "de-kapitalverletzung"
    assert prov["n_proposed"] == len(labeled)
    assert prov["n_emitted"] + prov["n_abstained"] == len(labeled)
    # Every emitted label is supported by construction.
    assert prov["support_rate_emitted"] == 1.0 or prov["n_emitted"] == 0
    # Abstained rows are kept visible with a counted reason.
    for d in out["decisions"]:
        if d.get("counter_status") == ABSTAINED_STATUS:
            assert d.get("counter_reason_code")
            assert d.get("counter_uncertainty") is not None
            assert d.get("counter_evidence_verified") is False


def test_emitted_row_keeps_label_and_marks_verified():
    """An emitted row keeps its proposed label and is marked verified."""
    bundle_path = (ROOT / "results" / "product" / "gate_packet" / "38839347028"
                   / "questions" / "de-kapitalverletzung.bundle.json")
    if not bundle_path.exists():
        pytest.skip("gate packet bundle not available")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    out = apply_counter_anchor_decisions(bundle)
    emitted = [d for d in out["decisions"]
               if d.get("counter_status") not in (None, "", "none", "cited", ABSTAINED_STATUS)]
    for d in emitted:
        assert d.get("counter_evidence_verified") is True
        assert d.get("counter_uncertainty") == 0.2
        assert d.get("counter_reason_code") == "supported"


# --------------------------------------------------------------------------
# Non-vacuity
# --------------------------------------------------------------------------

def test_nonvacuity_deliberately_mislabeled_row_is_abstained():
    """A row whose cited evidence is empty must be abstained (evidence_absent)."""
    bundle = {
        "query": "Kündigung Mietvertrag Mietrecht",
        "decisions": [_labeled_row("bad-row", evidence="")],
    }
    out = apply_counter_anchor_decisions(bundle)
    d = out["decisions"][0]
    assert d["counter_status"] == ABSTAINED_STATUS
    assert d["counter_reason_code"] == "evidence_absent"
    assert d["counter_uncertainty"] == 1.0


def test_nonvacuity_off_domain_row_is_abstained():
    """A row with evidence that has no domain anchor is abstained."""
    bundle = {
        "query": "Kündigung Mietvertrag Mietrecht",
        "decisions": [_labeled_row(
            "off-domain",
            evidence="The quick brown fox jumps over the lazy dog. "
                     "This sentence has no legal content whatsoever.",
        )],
    }
    out = apply_counter_anchor_decisions(bundle)
    d = out["decisions"][0]
    assert d["counter_status"] == ABSTAINED_STATUS
    assert d["counter_reason_code"] in {
        "no_intent_marker", "no_domain_anchor", "pivot_absent",
    }


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------

def test_provenance_records_frozen_hash_and_component():
    bundle = {"query": "test", "decisions": []}
    out = apply_counter_anchor_decisions(bundle)
    prov = out["provenance"]["counter_anchor"]
    assert prov["component"] == "frontier-counter-anchor-classifier/1"
    assert prov["frozen_rules_sha256"] == FROZEN_RULES_SHA256


def test_abstained_rows_are_never_dropped():
    """Abstained rows remain in the decisions list (counted, not dropped)."""
    bundle = {
        "query": "unknown query",
        "decisions": [
            _labeled_row("keep1", evidence=""),
            _labeled_row("keep2", evidence=""),
            {"decision_id": "keep3", "counter_status": "none"},
        ],
    }
    out = apply_counter_anchor_decisions(bundle)
    assert len(out["decisions"]) == 3
    ids = {d["decision_id"] for d in out["decisions"]}
    assert ids == {"keep1", "keep2", "keep3"}
