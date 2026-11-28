"""Direction v68 P0 — rejection/incumbent leg on the stage-2 abstention path.

Stage 1 already downgrades a verified counter row whose evidence fails the
frozen D1-D4 content predicates.  Stage 2 (the pool-surface -> frozen gate
bridge) previously left every abstained row's ``counter_evidence_verified``
flag untouched, even when its incumbent was a letterhead/markup/language-
mismatch span.  A row reaches stage 2 with only a ``counter_surface_signal``
and no scored status or adversarial signal, so stage 1 never sees it; the
result was exactly the v68 residual: a verified row carrying defective
content after the gate abstained.

These tests pin the repair:

* D2, D3 and D4 incumbents on that stage-2-only population are downgraded
  to explicitly-unevidenced with a frozen content reason code;
* a content-sound incumbent is retained even when the frozen label gate
  abstains (support/label abstention is a different axis from content);
* a previously confirmed stage-2 row is re-checked on re-run;
* ``counter_status``, geometry, clusters and row count are never touched;
* the fixed-path committed bundle remains defect-free after a stage-2 replay.

No frozen gate, rubric, threshold or bar is edited or re-derived here.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.query import counter_evidence_span as ces  # noqa: E402

QID = "fr-bail-entretien"
QUERY = "Kündigung Mietvertrag art. 257d"
SHIPPED_BUNDLE = (
    ROOT / "results" / "product" / "offline_slice" / "20261025T204600Z"
    / "rent-default.bundle.json"
)

D2_HEADER = (
    "Kantonsgericht von Graubünden Dretgira chantunala dal Grischun "
    "Tribunale cantonale dei Grigioni"
)
D3_MARKUP = (
    "<mark>Selon la jurisprudence</mark>, l'art. 337 CO permet une "
    "résiliation immédiate pour de justes motifs."
)
D4_MISMATCH = (
    "Regeste Erwägung Kündigung Mietvertrag Bundesgericht Verfügung und "
    "weitere Ausführungen zum Vertragsrecht."
)
SOUND_FR = (
    "Le bailleur invoque le defaut d'entretien du bail et le locataire "
    "ne peut resilier le bail que si le defaut est grave selon art 257d CO "
    "dans la limite de la jurisprudence sur le bail."
)


def _surface_row(did: str, evidence: str, language: str, full_text: str) -> dict:
    """A stage-2-only row: no scored status, no span record, no adversarial signal."""
    return {
        "decision_id": did,
        "language": language,
        "full_text": full_text,
        "snippet": "",
        "regeste": "",
        "counter_status": "none",
        "counter_evidence": evidence,
        "counter_evidence_verified": True,
        "counter_surface_signal": {
            "heuristic_status": "candidate-limiting",
            "evidence": evidence,
        },
        "x": 0.1,
        "y": 0.2,
        "cluster_id": 3,
        "rank": 7,
    }


CASES = [
    ("D2_letterhead_zone", "d2_letterhead_zone", _surface_row(
        "S2_D2", D2_HEADER, "de", D2_HEADER + " Weitere Entscheidungsgründe folgen hier.")),
    ("D3_markup_residue", "d3_markup_residue", _surface_row(
        "S2_D3", D3_MARKUP, "fr", "x. " * 200 + D3_MARKUP + " Suite du texte.")),
    ("D4_language_marker_mismatch", "d4_language_marker_mismatch", _surface_row(
        "S2_D4", D4_MISMATCH, "it", "y. " * 200 + D4_MISMATCH + " Seguito.")),
]


def _run(row: dict) -> tuple[dict, dict]:
    bundle = {"query": QUERY, "decisions": [copy.deepcopy(row)]}
    out = ces.apply_surface_span_confirmation(bundle, qid=QID)
    return out, out["provenance"]["counter_evidence_span_surface"]


@pytest.mark.parametrize("defect,reason,row", CASES)
def test_stage2_abstention_downgrades_a_defective_verified_incumbent(
        defect, reason, row):
    assert ces.frozen_content_defects(row["counter_evidence"], row) == [defect]
    out, prov = _run(row)
    assert prov["applied"] is True
    after = out["decisions"][0]
    assert after["counter_evidence_verified"] is False
    assert after["counter_evidence_unevidenced"] is True
    assert after["counter_evidence_unevidenced_reason"] == reason
    # status, geometry and row count are untouched
    assert after["counter_status"] == row["counter_status"]
    assert (after["x"], after["y"], after["cluster_id"], after["rank"]) == (
        row["x"], row["y"], row["cluster_id"], row["rank"])
    assert len(out["decisions"]) == 1
    # per-row BEFORE/AFTER with both the content reason and the gate reason
    recs = [r for r in prov["downgrades"] if r["decision_id"] == row["decision_id"]]
    assert len(recs) == 1
    rec = recs[0]
    assert rec["leg"] == "stage2_abstention"
    assert rec["before"]["counter_evidence_verified"] is True
    assert rec["after"]["counter_evidence_verified"] is False
    assert rec["reason_code"] == reason
    assert rec["defects"] == [defect]
    assert rec["gate_reason_code"] in prov["abstention_reasons"]
    assert prov["n_downgraded"] == len(prov["downgrades"])
    entry = next(a for a in prov["abstained"]
                 if a["decision_id"] == row["decision_id"])
    assert entry["content_rejection"]["reason_code"] == reason


def test_content_sound_incumbent_is_retained_when_the_gate_abstains():
    row = _surface_row("S2_SOUND", SOUND_FR, "fr", "Pad. " * 100 + SOUND_FR + " Suite.")
    assert ces.frozen_content_defects(row["counter_evidence"], row) == []
    out, prov = _run(row)
    after = out["decisions"][0]
    assert after["counter_evidence_verified"] is True
    assert after.get("counter_evidence_unevidenced") is None
    assert prov["n_downgraded"] == 0
    assert prov["downgrades"] == []
    entry = next((a for a in prov["abstained"]
                  if a["decision_id"] == row["decision_id"]), None)
    if entry is not None:
        assert entry.get("content_sound_incumbent_retained") is True


def test_previously_confirmed_stage2_row_is_rechecked_and_downgraded():
    evidence = D2_HEADER
    row = _surface_row("S2_PRIOR", evidence, "de", evidence + " Weitere Gründe.")
    row["counter_status"] = "candidate-limiting"
    row["counter_evidence_span"] = {
        "stage": 2, "selected": True, "reason_code": "supported_verbatim_span",
    }
    out, prov = _run(row)
    assert prov["n_selected"] == 0
    assert prov["selected_ids"] == []
    assert prov["n_downgraded"] == 1
    assert prov["downgrades"][0]["leg"] == "stage2_prior_recheck"
    assert out["decisions"][0]["counter_evidence_verified"] is False


def test_stage2_rejection_is_idempotent():
    row = _surface_row("S2_D3", D3_MARKUP, "fr", "x. " * 200 + D3_MARKUP + " Suite.")
    once, p1 = _run(row)
    twice, p2 = _run(once["decisions"][0])
    assert p1["n_downgraded"] == 1
    assert p2["n_downgraded"] == 0, "a cleared flag must not be re-counted"
    assert once["decisions"][0]["counter_evidence_verified"] is False
    assert twice["decisions"][0]["counter_evidence_verified"] is False
    assert p1["selected_ids"] == p2["selected_ids"]
    assert p1["n_abstained"] == p2["n_abstained"]


def test_shipped_fixed_path_bundle_stays_defect_free_after_stage2_replay():
    doc = json.loads(SHIPPED_BUNDLE.read_text(encoding="utf-8"))
    out = ces.apply_surface_span_confirmation(doc, qid=QID)
    defective = [
        (d.get("decision_id"), ces.frozen_content_defects(
            str(d.get("counter_evidence") or ""), d))
        for d in out["decisions"]
        if d.get("counter_evidence_verified") is True
        and ces.frozen_content_defects(str(d.get("counter_evidence") or ""), d)
    ]
    assert defective == []
