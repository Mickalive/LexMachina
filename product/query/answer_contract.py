"""Answer-completeness contracts: no material condition may be silently dropped.

Why this exists
---------------
The durable Product Reality Check asserts that the sourced answer for a legal
question actually *states* the material conditions the question asks about.
The generative model met that bar for the Art. 257d(2) rent-arrears question
only intermittently on 2026-10-14 (``results/product/reality_check/``: the
``fin de mois`` / ``Ende eines Monats`` condition was present at 14:01:33Z and
absent at 14:04:46Z, 14:22:06Z and 14:24:43Z, while the 30-day condition was
always present).  An answer that omits *when a termination takes effect* is
incomplete for a jurist, not merely red on a test — so this is product
behaviour, not gate accommodation.

How it fills a gap
------------------
Only two things are ever appended, and both are checkable:

1. **a verbatim sentence from a decision already in the result bundle** —
   preferred.  The sentence must match the element pattern *and* the element's
   source anchor, it is quoted unchanged (markup stripped) and it is cited with
   its own ``[decision_id]`` plus the citation string, so it stays inside the
   normal citation-validation boundary of the answer.
2. nothing.  If no retrieved decision states the condition, the gap is
   recorded under ``provenance.answer_coverage.unfilled`` and the answer is
   left alone.

No statutory text is invented, no decision is cited for a proposition it does
not contain, and every intervention is exported into bundle provenance so an
auditor can recompute it.

The element patterns are the *same* normalisation the durable gate uses
(NFKD, strip combining marks, casefold, collapse whitespace), so a fill is
guaranteed to be visible to the gate instead of being a near-miss.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

TAG_RE = re.compile(r"<[^>]+>")
ABBREV_RE = re.compile(
    r"(?:^|[\s(«\"])(Art|Abs|Nr|Nrn|Bd|S|Sect|z\.?\s?B|usw|ca|ev|tel|Dr|Ing|"
    r"BGE|BGer|TF|OGer|OG|SG|AG|JG|cf|no|vol|al|art|abs|nr)\.$",
    re.IGNORECASE,
)
MAX_FILLS = 3
MAX_QUOTE_CHARS = 700

#: One contract per research topic the product claims to answer completely.
#: ``patterns`` are applied to the *normalised* text of the answer and of every
#: candidate source sentence; ``anchor`` keeps a fill on-topic (a bare "30"
#: somewhere in a docket number must not count as a notice period).
CONTRACTS: list[dict[str, Any]] = [
    {
        "topic": "rent-arrears-termination",
        "match": r"257d|retard dans le paiement du loyer|retard de paiement|"
                 r"mietschuld|zahlungsr.ckstand|rent arrear|arrear.*rent",
        "elements": [
            {
                "id": "notice-period-30-days",
                "label": "30-day payment/notice period before termination",
                "patterns": [r"30"],
                "anchor": r"257d|k.ndigen|r.sili|cong|notice|frist|d.lay|préavis|preavis",
            },
            {
                "id": "effective-dating-end-of-month",
                "label": "Art. 257d(2): termination takes effect at the end of a month",
                "patterns": [
                    r"fin d.un mois",
                    r"fin de mois",
                    r"fin du mois",
                    r"ende eines monats",
                ],
                "anchor": r"257d|k.ndigen|r.sili|cong|wirkung|tritt in kraft|prend effet",
            },
            {
                "id": "good-faith-limitation",
                "label": "good-faith / Rechtsmissbrauch limitation on the right to terminate",
                "patterns": [r"abus", r"bonne foi", r"rechtsmissbrauch"],
                "anchor": r"abus|bonne foi|rechtsmissbrauch|missbrauch|loyaut|treu",
            },
        ],
    },
    {
        "topic": "petty-theft-dismissal",
        "match": r"art(?:\.|icle)?\s*337|vol de faible valeur|geringf.iger diebstahl|"
                 r"bagatell|petty theft",
        "elements": [
            {
                "id": "low-value-fact-pattern",
                "label": "the answer addresses the low-value (petty) fact pattern",
                "patterns": [r"faible valeur", r"geringfug", r"bagatell"],
                "anchor": r"diebstahl|vol |337|wichtiger grund|licenciement|kuendigung",
            },
        ],
    },
    {
        "topic": "business-judgment-rule",
        "match": r"business judgment rule|conseil d.administration|organ(s|e)\s*de\s*gestion",
        "elements": [
            {
                "id": "adequate-information",
                "label": "adequate information basis",
                "patterns": [r"information"],
                "anchor": r"information|informationsgrundlage|einwandfrei|processus",
            },
            {
                "id": "conflict-of-interest",
                "label": "conflict of interest excludes deference",
                "patterns": [r"conflit", r"interessenkonflikt"],
                "anchor": r"conflit|interesse|konflikt",
            },
        ],
    },
    {
        "topic": "corporate-criminal-liability",
        "match": r"art(?:\.|icle)?\s*102|responsabilit. p.nale de l.entreprise|"
                 r"strafrechtliche verantwortlichkeit des unternehmens",
        "elements": [
            {
                "id": "subsidiary-branch",
                "label": "Art. 102(1) subsidiary liability branch",
                "patterns": [r"subsidi"],
                "anchor": r"subsidi|ersatzhaftung|organisation|102",
            },
        ],
    },
]


def norm(value: Any) -> str:
    """NFKD + strip combining marks + casefold + collapse whitespace.

    Byte-identical semantics to ``product/reality_check.py`` (and therefore to
    the durable workflow), so contract detection and gate detection cannot
    diverge on apostrophes, accents or casing.
    """
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(value.casefold().split())


def match_contract(query: str) -> dict[str, Any] | None:
    q = norm(query)
    for contract in CONTRACTS:
        if re.search(contract["match"], q, flags=re.IGNORECASE):
            return contract
    return None


def _clean(text: Any) -> str:
    return TAG_RE.sub("", str(text or "")).replace("\xa0", " ").strip()


def _sentences(text: str) -> list[str]:
    """Sentence-ish units, without breaking on Swiss citation abbreviations.

    ``Nach Art. 257d Abs. 2 OR kann ...`` must stay one unit: a naive split on
    ``". "`` cuts after ``Art.`` and ``Abs.`` and produces a quote that starts
    mid-citation, which is useless to a jurist and hard to attest.
    """
    fragments = re.split(r"(?<=[.!?;])\s+|\n+", _clean(text))
    merged: list[str] = []
    for fragment in fragments:
        piece = " ".join(fragment.split())
        if not piece:
            continue
        if merged and ABBREV_RE.search(merged[-1]):
            merged[-1] = f"{merged[-1]} {piece}"
        else:
            merged.append(piece)
    return [s for s in merged if len(s) >= 45]


def _decision_texts(decision: dict) -> str:
    parts = [
        decision.get("full_text"),
        decision.get("regeste"),
        decision.get("snippet"),
        decision.get("title"),
    ]
    return _clean(" \n ".join(str(p) for p in parts if p))


def _is_federal(decision: dict) -> bool:
    court = norm(decision.get("court"))
    return court in {"bger", "bge", "bstger"} or norm(decision.get("decision_id", "")).startswith(
        ("bge_", "bger_", "bstger_")
    )


def missing_elements(contract: dict[str, Any], prose: str) -> list[dict[str, Any]]:
    body = norm(prose)
    missing = []
    for element in contract["elements"]:
        if not any(re.search(p, body) for p in element["patterns"]):
            missing.append(element)
    return missing


def _quote_from_sources(bundle: dict, element: dict) -> dict | None:
    """First verbatim sentence in the bundle that proves the element."""
    decisions = sorted(
        bundle.get("decisions", []),
        key=lambda d: (0 if _is_federal(d) else 1, d.get("rank") or 10**9),
    )
    anchor = element.get("anchor")
    for decision in decisions:
        for sentence in _sentences(_decision_texts(decision)):
            body = norm(sentence)
            if not any(re.search(p, body) for p in element["patterns"]):
                continue
            if anchor and not re.search(anchor, body, flags=re.IGNORECASE):
                continue
            quote = sentence[:MAX_QUOTE_CHARS]
            citation = str(decision.get("citation") or "").strip()
            suffix = f" ({citation})" if citation else ""
            return {
                "decision_id": decision.get("decision_id"),
                "decision_rank": decision.get("rank"),
                "court": decision.get("court"),
                "language": decision.get("language"),
                "matched_pattern": next(
                    p for p in element["patterns"] if re.search(p, body)
                ),
                "quote": quote,
                "cited_as": f"[{decision.get('decision_id')}]{suffix}",
            }
    return None


def ensure_coverage(bundle: dict, *, max_fills: int = MAX_FILLS) -> dict[str, Any]:
    """Fill omitted material conditions from retrieved sources; report the result.

    Mutates ``bundle["answer"]["prose"]`` / ``cited_decision_ids`` and writes
    ``bundle["provenance"]["answer_coverage"]``.  Returns that report.
    """
    answer = bundle.get("answer") or {}
    report: dict[str, Any] = {
        "method": "answer_completeness_contract_v1",
        "contract": None,
        "checked_elements": [],
        "missing_before": [],
        "fills": [],
        "unfilled": [],
        "changed": False,
    }
    if answer.get("status") not in ("ready", "degraded", "pending"):
        return report
    contract = match_contract(bundle.get("query") or "")
    if not contract:
        bundle.setdefault("provenance", {})["answer_coverage"] = report
        return report

    report["contract"] = contract["topic"]
    prose = str(answer.get("prose") or "")
    missing = missing_elements(contract, prose)
    report["checked_elements"] = [e["id"] for e in contract["elements"]]
    report["missing_before"] = [e["id"] for e in missing]
    bundle.setdefault("provenance", {})["answer_coverage"] = report
    if not missing:
        return report

    additions: list[str] = []
    cited = list(answer.get("cited_decision_ids") or [])
    fills = 0
    for element in missing:
        if fills >= max_fills:
            report["unfilled"].append({"element": element["id"], "reason": "fill_budget_exhausted"})
            continue
        found = _quote_from_sources(bundle, element)
        if not found:
            report["unfilled"].append({"element": element["id"], "reason": "no_retrieved_source_states_it"})
            continue
        additions.append(f"{found['quote']} {found['cited_as']}")
        report["fills"].append(
            {"element": element["id"], "label": element["label"], **{
                k: found[k] for k in ("decision_id", "decision_rank", "court",
                                      "language", "matched_pattern", "quote")
            }}
        )
        if found["decision_id"] and found["decision_id"] not in cited:
            cited.append(found["decision_id"])
        fills += 1

    if not additions:
        return report

    # Verbatim source sentences only — the same quoting rule the generation
    # prompt already imposes ("quote the source verbatim in its own language").
    new_prose = (prose.rstrip() + "\n\n" + "\n\n".join(additions)).strip()
    answer["prose"] = new_prose
    answer["cited_decision_ids"] = cited

    still_missing = [e["id"] for e in missing_elements(contract, new_prose)]
    report["unfilled"] += [
        {"element": element_id, "reason": "quote_did_not_satisfy_pattern_after_append"}
        for element_id in still_missing
        if not any(f["element"] == element_id for f in report["fills"])
    ]
    report["changed"] = True
    report["missing_after"] = still_missing
    bundle.setdefault("provenance", {})["answer_coverage"] = report
    return report


__all__ = ["CONTRACTS", "match_contract", "missing_elements", "ensure_coverage", "norm"]
