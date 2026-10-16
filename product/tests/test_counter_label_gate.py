"""Adoption of the accepted counter-anchor classifier (factory direction v50).

The accepted Frontier component (team run 38964146628, outcome A) is adopted in
``abstain_and_disclose`` mode.  These tests pin the contract the adoption must
keep, on top of the component's own 22 acceptance tests:

* the frozen rubric is re-hashed before every use and a mismatch REFUSES;
* an abstained row stays visible, marked, and counted — never dropped;
* the emitted/abstained/yield numbers are published SIDE BY SIDE;
* no artifact this adapter writes may assert that a decision IS supporting,
  contrary or limiting (the accepted forbidden_construction_patterns);
* the adapter never computes a frozen-rubric support rate of its own;
* a bundle with no frozen anchor profile abstains rather than inventing anchors;
* the vendored component is byte-identical to the accepted mount.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from product.query import counter_label_gate as clg  # noqa: E402

ACCEPTED_MOUNT = Path("/tmp/lex_accepted/frontier/frontier-counter-anchor-classifier")
COMPONENT_ROOT = REPO_ROOT / "product" / "vendor" / "counter_anchor_classifier"
FORBIDDEN_PATTERNS = [
    r"\bdecision\s+[A-Za-z0-9_.\-]+\s+is\s+(supporting|contrary|limiting)\b",
    r"\bdecision\s+[A-Za-z0-9_.\-]+\s+is\s+not\s+(supporting|contrary|limiting)\b",
    r"\b[A-Za-z0-9_.\-]+\s+is\s+(a\s+)?(supporting|contrary|limiting)\s+(authority|decision|case)\b",
    r"\bwe\s+(classify|label|find)\s+[A-Za-z0-9_.\-]+\s+as\s+(supporting|contrary|limiting)\b",
    r"\basserts?\s+that\s+[A-Za-z0-9_.\-]+\s+is\s+(supporting|contrary|limiting)\b",
]


def _decision(did: str, status: str, evidence: str = "", *, language: str = "de",
              title: str = "", regeste: str = "", rank: int = 1, legal_area: str = "") -> dict:
    return {
        "decision_id": did, "counter_status": status, "counter_evidence": evidence,
        "language": language, "rank": rank, "title": title, "regeste": regeste,
        "legal_area": legal_area, "court": "BGer", "score": 1.0, "provenance": {},
        "snippet": "", "canonical_url": "", "citation": did,
        "x": 0.0, "y": 0.0, "cluster_id": 0, "is_outlier": False,
    }


def _bundle(decisions: list[dict], *, qid: str | None = "kuendigung-mietrecht",
            query: str = "Kündigung Mietvertrag Mietrecht") -> dict:
    return {
        "bundle_version": "1.0", "query": query, "query_variants": [],
        "qid": qid, "answer": {"prose": "", "cited_decision_ids": []},
        "decisions": decisions,
        "clusters": [{"cluster_id": 0, "label": "C0", "size": len(decisions)}],
        "relations": [], "provenance": {},
    }


# --------------------------------------------------------------------------- #
# 1. frozen rubric: re-hash or refuse
# --------------------------------------------------------------------------- #
def test_frozen_rules_file_rehashes_to_the_accepted_digest() -> None:
    payload = clg.rules_path().read_bytes()
    assert hashlib.sha256(payload).hexdigest() == clg.FROZEN_RULES_SHA256


def test_a_tampered_rules_file_is_refused_not_guessed(tmp_path, monkeypatch) -> None:
    tampered = tmp_path / "RULES_LABEL.json"
    payload = json.loads(clg.rules_path().read_text(encoding="utf-8"))
    payload["charter_version"] = 999
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(clg, "rules_path", lambda: tampered)
    with pytest.raises(RuntimeError, match="digest mismatch"):
        clg.load_frozen_rules()


# --------------------------------------------------------------------------- #
# 2. the abstain contract
# --------------------------------------------------------------------------- #
def test_empty_evidence_can_never_receive_a_confident_label() -> None:
    bundle = _bundle([
        _decision("a", "candidate-limiting", ""),
        _decision("b", "candidate-contrary", ""),
    ])
    out = clg.apply_counter_label_gate(bundle)
    for d in out["decisions"]:
        assert d["counter_status"] == clg.ABSTAINED_STATUS
        assert d["counter_label_anchor"]["reason_code"] == "evidence_absent"
        assert d["counter_uncertainty"] == 1.0
        assert d["counter_evidence_verified"] is False


def test_an_abstained_row_stays_visible_and_counted_never_dropped() -> None:
    bundle = _bundle([_decision("a", "candidate-limiting", "")])
    out = clg.apply_counter_label_gate(bundle)
    assert [d["decision_id"] for d in out["decisions"]] == ["a"]
    gate = out["provenance"]["counter_label_gate"]
    assert gate["n_proposed_labels"] == 1
    assert gate["n_abstained"] == 1
    assert gate["n_emitted"] == 0


def test_an_off_domain_row_abstains_and_keeps_its_own_cited_passage() -> None:
    # Arbeitsvertrag / KVG markers in a Mietrecht question: no PIVOT anchor of
    # the frozen profile appears anywhere in the row's own text.
    passage = ("Der Arbeitgeber haftet aus Arbeitsvertrag und KVG für die "
               "Kapitalverletzung des Arbeitnehmers.")
    bundle = _bundle([_decision("a", "candidate-limiting", passage)])
    out = clg.apply_counter_label_gate(bundle)
    d = out["decisions"][0]
    assert d["counter_status"] == clg.ABSTAINED_STATUS
    assert d["counter_label_anchor"]["reason_code"] in {"pivot_absent", "no_domain_anchor"}
    assert d["counter_evidence"] == passage  # jurist can still read the passage


def test_an_anchored_intent_passage_confirms_the_rows_own_label() -> None:
    # The cited passage carries a frozen counter-intent marker ("jedoch") AND
    # the question's own PIVOT/DOMAIN anchors (Kündigung / Mietvertrag), so
    # every frozen criterion (i)-(v) passes and the row's own label is emitted.
    passage = ("Der Vermieter kündigte den Mietvertrag, jedoch wurden die Mängel "
               "vom Mieter gerügt und die Räumung abgelehnt.")
    bundle = _bundle([_decision("a", "candidate-limiting", passage,
                                title="Kündigung Mietvertrag", regeste="Mietrecht 257d")])
    out = clg.apply_counter_label_gate(bundle)
    d = out["decisions"][0]
    assert d["counter_status"] == "candidate-limiting"  # the product's own label
    assert d["counter_label_anchor"]["reason_code"] == "supported"
    assert d["counter_label_anchor"]["abstained"] is False
    # The component's deterministic emitted uncertainty (EMITTED_UNCERTAINTY).
    assert d["counter_label_anchor"]["uncertainty"] == 0.2


def test_unlabelled_and_cited_rows_are_not_gated() -> None:
    bundle = _bundle([
        _decision("a", "none"),
        _decision("b", "cited", "cited in generated answer"),
        _decision("c", "unclassified"),
    ])
    out = clg.apply_counter_label_gate(bundle)
    assert [d["counter_status"] for d in out["decisions"]] == ["none", "cited", "unclassified"]
    assert out["provenance"]["counter_label_gate"]["n_proposed_labels"] == 0


def test_the_gate_is_deterministic() -> None:
    passage = ("Der Vermieter kündigte den Mietvertrag ohne Rüge der Mängel.")
    bundle = _bundle([_decision("a", "candidate-limiting", passage)])
    first = clg.apply_counter_label_gate(copy.deepcopy(bundle))
    second = clg.apply_counter_label_gate(copy.deepcopy(bundle))
    assert json.dumps(first, sort_keys=True, ensure_ascii=False) == \
        json.dumps(second, sort_keys=True, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# 3. no frozen profile: abstain, never invent anchors
# --------------------------------------------------------------------------- #
def test_a_bundle_without_a_frozen_profile_abstains_and_says_so() -> None:
    passage = ("Der Vermieter kündigte den Mietvertrag ohne Rüge der Mängel.")
    bundle = _bundle([_decision("a", "candidate-limiting", passage)],
                     qid=None, query="Eine völlig unbekannte Rechtsfrage 42")
    out = clg.apply_counter_label_gate(bundle)
    gate = out["provenance"]["counter_label_gate"]
    assert gate["anchor_profile"]["status"] == "absent"
    assert gate["anchor_profile"]["qid"] is None
    d = out["decisions"][0]
    assert d["counter_status"] == clg.ABSTAINED_STATUS
    assert d["counter_label_anchor"]["anchor_profile_status"] == "absent"


def test_the_frozen_profile_is_matched_by_exact_query_text_when_qid_is_absent() -> None:
    bundle = _bundle([_decision("a", "candidate-limiting", "")],
                     qid=None, query="Kündigung Mietvertrag Mietrecht")
    out = clg.apply_counter_label_gate(bundle)
    gate = out["provenance"]["counter_label_gate"]
    assert gate["anchor_profile"]["status"] == "frozen"
    assert gate["anchor_profile"]["qid"] == "kuendigung-mietrecht"


# --------------------------------------------------------------------------- #
# 4. publication ceilings
# --------------------------------------------------------------------------- #
def test_support_and_yield_are_published_side_by_side_and_support_is_not_recomputed() -> None:
    bundle = _bundle([
        _decision("a", "candidate-limiting", ""),
        _decision("b", "candidate-limiting", ""),
        _decision("c", "none"),
    ])
    gate = clg.apply_counter_label_gate(bundle)["provenance"]["counter_label_gate"]
    assert gate["side_by_side"] == {
        "n_proposed_labels": 2, "n_emitted": 0, "n_abstained": 2, "yield": 0.0,
    }
    assert gate["support_rate_computed_here"] is False
    assert gate["support_rate_among_emitted"] is None
    # The Frontier measurement is attached as ATTRIBUTED evidence about its own
    # population, never as a measurement of this bundle.
    ref = gate["frontier_measured_reference"]
    assert ref["team_run_id"] == "38964146628"
    assert "38839347028" in ref["scope"] or "38839347028" in ref["measured_packet"]


def test_no_written_artifact_matches_a_forbidden_construction_pattern() -> None:
    bundle = _bundle([
        _decision("a", "candidate-limiting", ""),
        _decision("b", "candidate-contrary",
                  "Die Kündigung des Mietvertrags wurde als missbräuchlich qualifiziert."),
    ])
    out = clg.apply_counter_label_gate(bundle)
    blob = json.dumps(out["provenance"]["counter_label_gate"], ensure_ascii=False)
    blob += json.dumps([d.get("counter_label_anchor") for d in out["decisions"]],
                       ensure_ascii=False)
    blob += clg.CLAIM_CEILING
    for pattern in FORBIDDEN_PATTERNS:
        assert re.search(pattern, blob, flags=re.IGNORECASE) is None, pattern


def test_disabled_gate_records_itself_and_changes_nothing() -> None:
    bundle = _bundle([_decision("a", "candidate-limiting", "")])
    out = clg.apply_counter_label_gate(bundle, enabled=False)
    assert out["decisions"][0]["counter_status"] == "candidate-limiting"
    assert out["provenance"]["counter_label_gate"]["enabled"] is False


# --------------------------------------------------------------------------- #
# 5. byte-identity with the accepted mount
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not ACCEPTED_MOUNT.is_dir(),
                    reason="accepted Frontier mount not present in this checkout")
def test_vendored_component_is_byte_identical_to_the_accepted_mount() -> None:
    src_root = ACCEPTED_MOUNT / "frontier" / "frontier-counter-anchor-classifier" \
        / "frontier_counter_anchor_classifier"
    for src in sorted(src_root.rglob("*.py")):
        rel = src.relative_to(src_root)
        dst = COMPONENT_ROOT / "frontier_counter_anchor_classifier" / rel
        assert dst.is_file(), f"missing vendored file {rel}"
        assert hashlib.sha256(dst.read_bytes()).hexdigest() == \
            hashlib.sha256(src.read_bytes()).hexdigest(), rel
    src_rules = ACCEPTED_MOUNT / "results" / "frontier" / \
        "frontier-counter-anchor-classifier" / "RULES_LABEL.json"
    assert hashlib.sha256((COMPONENT_ROOT / "RULES_LABEL.json").read_bytes()).hexdigest() == \
        hashlib.sha256(src_rules.read_bytes()).hexdigest()


def test_pipeline_enrich_applies_the_gate() -> None:
    """The adoption is wired into the shipped enrich path, not just available."""
    src = (REPO_ROOT / "product" / "query" / "pipeline.py").read_text(encoding="utf-8")
    assert "apply_counter_label_gate" in src
    gate_src = (REPO_ROOT / "product" / "query" / "counter_label_gate.py").read_text(encoding="utf-8")
    assert "abstain_and_disclose" in gate_src
