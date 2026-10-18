"""The accepted Evaluation handoff: under-covered query concepts are DISCLOSED.

Provenance of the requirement (accepted evidence, not this cycle's invention)
---------------------------------------------------------------------------
Core Evaluation's question-native coverage finding, accepted on lab/evaluation
via commit ``09cd5c7d`` (run 39117425713; originating cycle 39113690481, verdict
``QUESTION_NATIVE_PRODUCT_DEFECT_ESTABLISHED``), established that the served
packet's own admission machinery *measured*
``query_concepts_under_covered = ["kapitalverletzung", "uberwachungspflicht"]``
on ``de-kapitalverletzung`` (0 rows in 214) and still shipped
``admissible=true, warning_count=0, blocking_count=0``.  Run 39120832665
(``DISCLOSURE_DEFECT_TRANSFERRED``, accepted at 904aff83) proved the same defect
transfers unchanged to the rebuilt packet ``rebuilt-39027045675``.

The handoff, verbatim from ``reports/evaluation/CYCLE_39113690481.md`` on
``lab/evaluation`` (committed tree of that branch):

    admission::selfcheck_disagreement - a bundle is admitted with zero warnings
    while the packet's own concept self-check reports core concepts with zero
    rows.  Emit an admission finding (at minimum severity: warning) whenever
    query_concepts_under_covered is non-empty.  That is a disclosure change in
    product/query/gate_admissibility.py, not a retrieval change, and it does not
    touch any frozen bar or threshold.

Evaluation's frozen disclosure predicate (``evaluation/question_native_transfer.py``,
``DISCLOSURE_MARKERS``) reads a finding **code** containing one of
``concept`` / ``under_covered`` / ``undercovered`` / ``query_concept``
(case-insensitive).  The marker tuple is replicated here as a literal so this
lane does not import Core Evaluation's package; its provenance is this docstring,
not a runtime dependency.

Evaluation's caveat, carried verbatim wherever the defect is reported (direction
v57 ordered work (1)): a German compound noun may simply not be the doctrine's
own vocabulary - decisions may write *Verletzung der Kapitalverwaltung* rather
than *Kapitalverletzung*.  So this is a retrieval signal that the product itself
already computes, not proof that the authorities are absent.  The auditable claim
is the disagreement between the bundle's content and the packet's own admission
record.

Everything here runs offline against committed artifacts; no network, no model.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product"))
sys.path.insert(0, str(ROOT))

from product.query import gate_admissibility as ga  # noqa: E402
from product.query.bundle import build_bundle  # noqa: E402

#: Verbatim copy of the frozen marker tuple of
#: evaluation/question_native_transfer.py (run 39120832665).  Pinned here as a
#: literal, never imported, never re-derived.
FROZEN_DISCLOSURE_MARKERS = ("concept", "under_covered", "undercovered", "query_concept")

DE_QUESTION = ("Aktive Fürsorgepflicht des Arbeitgebers bei einer Kapitalverletzung: "
               "wie weit geht der aktive Eingriff, und welche Entscheidungen begrenzen ihn "
               "gegenüber einer blossen Überwachungspflicht?")

FURSORGE_ROWS = [
    ("Fürsorgepflicht des Arbeitgebers im Bereich der Gesundheit des Arbeitnehmers. "
     "Der Arbeitgeber muss alle zumutbaren Vorkehren treffen."),
    ("Weiter zur Fürsorgepflicht des Arbeitgebers: Verletzung der Pflicht, wenn der "
     "Stand der Technik eingehalten werden muss."),
    ("Fürsorgepflicht des Arbeitgebers auch im Konkurs; Schadenersatz bei Verletzung."),
]


def _decision(idx: int, regeste: str) -> dict:
    return {
        "decision_id": f"d{idx:03d}",
        "rank": idx,
        "court": "bger",
        "language": "de",
        "citation": f"CITE-{idx}",
        "canonical_url": f"https://mcp.opencaselaw.ch/decisions/d{idx:03d}",
        "source_url": f"https://mcp.opencaselaw.ch/decisions/d{idx:03d}",
        "score": 1.0 / idx,
        "cluster_id": 0,
        "x": 0.1 * idx,
        "y": 0.2 * idx,
        "is_outlier": False,
        "counter_status": "none",
        "provenance": {},
        "snippet": regeste[:400],
        "regeste": regeste,
        "full_text": "",
        "title": f"Entscheid {idx}",
    }


def _bundle_with_cited_answer() -> dict:
    """The post-handoff shape: cited, ready answer; concepts still under-covered.

    This is exactly the shape the accepted defect was measured on - an answer
    grounded in the concepts the corpus *does* cover, with two core concepts of
    the question carrying zero rows.
    """
    decisions = [_decision(i + 1, text) for i, text in enumerate(FURSORGE_ROWS)]
    answer = {
        "prose": "Die Fürsorgepflicht des Arbeitgebers ist in der Rechtsprechung "
                 "klar umrissen [d001]. Für die übrigen Konzepte der Frage "
                 "liegen keine Entscheidungen vor.",
        "statements": [],
        "cited_decision_ids": ["d001"],
        "method": "generative_audit_llm_v2",
        "model": "m",
        "status": "ready",
    }
    return build_bundle(
        query=DE_QUESTION, query_variants=[], answer=answer, decisions=decisions,
        clusters=[{"cluster_id": 0, "label": "test",
                   "member_ids": [d["decision_id"] for d in decisions]}],
        relations=[], provenance={},
    )


def _verdict(bundle: dict) -> dict:
    return ga.verify_bundle(bundle, question={"qid": "de-kapitalverletzung", "language": "de"},
                            min_decisions=1)


# --------------------------------------------------------------------------- #
# the handoff, executed
# --------------------------------------------------------------------------- #
def test_under_covered_concepts_fire_a_warning_even_on_an_admissible_answer():
    """The accepted defect shape, repaired: measured gap -> disclosing finding.

    Before the handoff this bundle admitted with ``warning_count=0`` while
    ``measured.query_concepts_under_covered`` named core concepts with zero
    rows.  The admission record must now agree with its own measurement.
    """
    verdict = _verdict(_bundle_with_cited_answer())
    assert verdict["admissible"], [f["code"] for f in verdict["findings"]
                                   if f["severity"] == "blocking"]
    assert verdict["measured"]["query_concepts_under_covered"], \
        "precondition: this fixture must reproduce the measured gap"
    codes = [f["code"] for f in verdict["findings"]]
    assert "query_concepts_under_covered" in codes
    finding = next(f for f in verdict["findings"] if f["code"] == "query_concepts_under_covered")
    assert finding["severity"] == "warning"
    detail = finding["detail"]
    for term in verdict["measured"]["query_concepts_under_covered"]:
        assert term in detail, f"the finding detail must name the under-covered term {term!r}"
    # Evaluation's caveat travels with the disclosure, not only with the report.
    assert "not proof that the authorities are absent" in detail
    assert finding["query_concepts_under_covered"] == \
        verdict["measured"]["query_concepts_under_covered"]


def test_finding_code_carries_a_frozen_disclosure_marker():
    """evaluation/question_native_transfer.py reads a MARKER in the code.

    The frozen predicate counts a finding as disclosing iff its code contains
    one of the frozen markers.  A code like ``selfcheck_disagreement`` would be
    invisible to that instrument even though a human could read the detail, so
    the marker is part of the contract, not a style choice.
    """
    verdict = _verdict(_bundle_with_cited_answer())
    codes = [str(f["code"]).lower() for f in verdict["findings"]]
    disclosing = [c for c in codes if any(m in c for m in FROZEN_DISCLOSURE_MARKERS)]
    assert disclosing, "no finding code carries a frozen disclosure marker"
    assert any(m in "query_concepts_under_covered" for m in FROZEN_DISCLOSURE_MARKERS)


def test_the_warning_never_changes_admissibility():
    """Handoff: 'a disclosure change, not a retrieval change' - warning only."""
    bundle = _bundle_with_cited_answer()
    verdict = _verdict(bundle)
    blocking_codes = {f["code"] for f in verdict["findings"] if f["severity"] == "blocking"}
    assert "query_concepts_under_covered" not in blocking_codes
    assert verdict["admissible"] is True
    assert verdict["warning_count"] == sum(1 for f in verdict["findings"]
                                           if f["severity"] == "warning")


def test_no_finding_when_every_concept_is_covered():
    """The finding must not fire on a healthy bundle - it is a disclosure."""
    question = "Fürsorgepflicht des Arbeitgebers"
    decisions = [_decision(i + 1, "Fürsorgepflicht des Arbeitgebers, Verletzung der Pflicht.")
                 for i in range(3)]
    answer = {"prose": "Antwort mit Beleg [d001].", "statements": [],
              "cited_decision_ids": ["d001"], "method": "generative_audit_llm_v2",
              "model": "m", "status": "ready"}
    bundle = build_bundle(
        query=question, query_variants=[], answer=answer, decisions=decisions,
        clusters=[{"cluster_id": 0, "label": "test",
                   "member_ids": [d["decision_id"] for d in decisions]}],
        relations=[], provenance={},
    )
    verdict = _verdict(bundle)
    assert verdict["measured"]["query_concepts_under_covered"] in (None, []), \
        "precondition: every concept of this question is covered"
    assert "query_concepts_under_covered" not in {f["code"] for f in verdict["findings"]}


def test_fires_also_while_the_bundle_is_blocked_for_an_unrelated_reason():
    """The disclosure is independent of the answer path (it is measured for
    every verdict); an uncited answer must not silence it."""
    bundle = _bundle_with_cited_answer()
    bundle["answer"]["cited_decision_ids"] = []
    bundle["answer"]["status"] = "ready"
    verdict = _verdict(bundle)
    assert not verdict["admissible"]
    codes = {f["code"] for f in verdict["findings"]}
    assert "answer_cites_nothing" in codes
    assert "query_concepts_under_covered" in codes
