"""Determinism + non-vacuity protocols (frozen in RULES.json).

Determinism: >=3 identical offline runs must produce identical proposal and
label sets, or the bounded instability disclosure is published with the
differing rows named.

Non-vacuity: a seeded control that injects one eligible counter-evidence
sentence into one candidate text must flip at least one emission on its
bundle; a negative control (blanking topical vocabulary) must suppress it.
"""

from __future__ import annotations

import copy
import json
from typing import Any, Callable

from .classifier_bridge import SCORED_STATUSES, run_classifier_on_bundle
from .emission import promote_heuristic_proposals

#: One eligible counter-evidence sentence used by the seeded control.  It
#: carries a frozen counter-intent marker AND a topical term and is not
#: procedural boilerplate; it is injected into a candidate's full_text so the
#: topical/marker gate can fire on it.
SEED_SENTENCE_DE = (
    "Vorbehaltlich der ausdrücklichen Ausnahme, die das Bundesgericht in "
    "dieser Linie anerkennt, begrenzt die aktive Fürsorgepflicht des "
    "Arbeitgebers die reine Überwachungspflicht bei Kapitalverletzung."
)


def _label_signature(emission: dict[str, Any]) -> list[dict[str, Any]]:
    """Deterministic signature of proposal + label sets."""
    out = []
    for row in sorted(emission.get("abstained") or [], key=lambda r: r["decision_id"]):
        out.append({
            "decision_id": row["decision_id"],
            "kind": "abstain",
            "reason_code": row.get("reason_code"),
        })
    for did in sorted(emission.get("emitted_ids") or []):
        out.append({"decision_id": did, "kind": "emit"})
    return out


def run_determinism(
    bundle: dict,
    *,
    qid: str | None,
    n_runs: int = 3,
    classifier_root: str | None = None,
    rules_path: str | None = None,
) -> dict[str, Any]:
    """Run repair+classifier ``n_runs`` times; compare proposal/label sets."""
    signatures: list[list[dict[str, Any]]] = []
    emissions: list[dict[str, Any]] = []
    for _ in range(max(1, n_runs)):
        repaired = promote_heuristic_proposals(bundle, scored_statuses=SCORED_STATUSES)
        em = run_classifier_on_bundle(
            repaired, qid=qid,
            classifier_root=classifier_root, rules_path=rules_path,
        )
        signatures.append(_label_signature(em))
        emissions.append(em)
    first = signatures[0]
    all_identical = all(sig == first for sig in signatures[1:])
    differing: list[dict[str, Any]] = []
    if not all_identical:
        base_ids = {r["decision_id"]: r for r in first}
        for i, sig in enumerate(signatures[1:], start=2):
            cur_ids = {r["decision_id"]: r for r in sig}
            for did in sorted(set(base_ids) | set(cur_ids)):
                if base_ids.get(did) != cur_ids.get(did):
                    differing.append({
                        "run_index": i,
                        "decision_id": did,
                        "baseline": base_ids.get(did),
                        "variant": cur_ids.get(did),
                    })
    return {
        "n_runs": max(1, n_runs),
        "identical": all_identical,
        "signature": first,
        "differing_rows": differing,
        "emission_summary": {
            "n_scored": emissions[0]["n_scored"],
            "n_emitted": emissions[0]["n_emitted"],
            "n_abstained": emissions[0]["n_abstained"],
        },
        "disclosure": None if all_identical else (
            "BOUNDED_INSTABILITY: the repaired emission path was not byte-"
            "identical across identical offline runs; differing rows named above."
        ),
    }


def _seed_bundle(bundle: dict, *, target_decision_id: str | None = None) -> dict[str, Any]:
    """Inject the seed sentence into one candidate row's full_text."""
    out = copy.deepcopy(bundle)
    rows = out.get("decisions") or []
    target = None
    if target_decision_id:
        for d in rows:
            if str(d.get("decision_id")) == target_decision_id:
                target = d
                break
    if target is None:
        # Prefer a lazy/hydrated row that is not already adversarial-scored.
        for d in rows:
            if str(d.get("counter_status") or "") not in SCORED_STATUSES and (
                str(d.get("full_text_status") or "") in ("lazy", "fetched")
            ):
                target = d
                break
    if target is None and rows:
        target = rows[0]
    if target is None:
        raise ValueError("bundle has no decisions to seed")
    existing = str(target.get("full_text") or "")
    target["full_text"] = (existing + "\n\n" + SEED_SENTENCE_DE).strip()
    target["full_text_status"] = "fetched"
    # Ensure the row carries an adversarial signal slot the repair can read.
    if not target.get("adversarial_retrieval_signal"):
        target["adversarial_retrieval_signal"] = {
            "heuristic_status": None, "evidence": "", "markers": [],
        }
    prov = out.setdefault("provenance", {})
    prov["non_vacuity_seed"] = {
        "seeded_decision_id": str(target.get("decision_id") or ""),
        "seed_sentence": SEED_SENTENCE_DE,
    }
    return out


def _reclassify_seeded_row(bundle: dict, *, topic_terms: list[str]) -> dict[str, Any]:
    """Re-run the topical/marker gate on the seeded row and update its signal."""
    from .attribution import _scan_gate_pass  # local, deterministic

    prov = bundle.setdefault("provenance", {})
    adv = prov.setdefault("adversarial_retrieval", {})
    if topic_terms:
        adv["label_topic_terms"] = list(topic_terms)
    seed_meta = prov.get("non_vacuity_seed") or {}
    seeded_id = seed_meta.get("seeded_decision_id")
    out = copy.deepcopy(bundle)
    for d in out.get("decisions") or []:
        if str(d.get("decision_id")) != seeded_id:
            continue
        text = str(d.get("full_text") or "")
        intent = str(d.get("adversarial_intent") or "exception")
        would_pass, markers, sentence = _scan_gate_pass(text, intent, topic_terms)
        d["adversarial_retrieval_signal"] = {
            "heuristic_status": "candidate-limiting" if would_pass else None,
            "evidence": sentence if would_pass else "",
            "markers": markers,
        }
    return out


def _blank_topic_terms(bundle: dict) -> dict[str, Any]:
    """Negative control: blank the topical vocabulary for the classification."""
    out = copy.deepcopy(bundle)
    prov = out.setdefault("provenance", {})
    adv = prov.setdefault("adversarial_retrieval", {})
    adv["label_topic_terms"] = []
    return out


def run_non_vacuity(
    bundle: dict,
    *,
    qid: str | None,
    classifier_root: str | None = None,
    rules_path: str | None = None,
) -> dict[str, Any]:
    """Seeded control + negative control.  Both must pass for non-vacuity."""
    baseline = promote_heuristic_proposals(bundle, scored_statuses=SCORED_STATUSES)
    base_em = run_classifier_on_bundle(
        baseline, qid=qid, classifier_root=classifier_root, rules_path=rules_path,
    )

    topic_terms = [
        str(t).lower()
        for t in ((bundle.get("provenance") or {}).get("adversarial_retrieval") or {}).get(
            "label_topic_terms"
        ) or []
    ]

    # Seeded control
    seeded = _seed_bundle(bundle)
    seeded = _reclassify_seeded_row(seeded, topic_terms=topic_terms)
    seeded_repaired = promote_heuristic_proposals(seeded, scored_statuses=SCORED_STATUSES)
    seed_em = run_classifier_on_bundle(
        seeded_repaired, qid=qid, classifier_root=classifier_root, rules_path=rules_path,
    )
    seed_scored_delta = seed_em["n_scored"] - base_em["n_scored"]
    seed_emitted_delta = seed_em["n_emitted"] - base_em["n_emitted"]
    seeded_pass = (seed_scored_delta >= 1) or (seed_emitted_delta >= 1)

    # Negative control: blank topical vocabulary for the same seeded input.
    neg = _blank_topic_terms(seeded)
    neg = _reclassify_seeded_row(neg, topic_terms=[])
    neg_repaired = promote_heuristic_proposals(neg, scored_statuses=SCORED_STATUSES)
    neg_em = run_classifier_on_bundle(
        neg_repaired, qid=qid, classifier_root=classifier_root, rules_path=rules_path,
    )
    # The negative control must not reach the seeded-control's emission level.
    negative_pass = (
        neg_em["n_scored"] < seed_em["n_scored"]
        or neg_em["n_emitted"] < seed_em["n_emitted"]
    )

    return {
        "baseline": {
            "n_scored": base_em["n_scored"],
            "n_emitted": base_em["n_emitted"],
            "n_abstained": base_em["n_abstained"],
        },
        "seeded_control": {
            "seeded_decision_id": ((bundle.get("provenance") or {}).get("non_vacuity_seed") or {}).get("seeded_decision_id")
            or ((seeded.get("provenance") or {}).get("non_vacuity_seed") or {}).get("seeded_decision_id"),
            "n_scored": seed_em["n_scored"],
            "n_emitted": seed_em["n_emitted"],
            "n_abstained": seed_em["n_abstained"],
            "scored_delta": seed_scored_delta,
            "emitted_delta": seed_emitted_delta,
            "pass": seeded_pass,
        },
        "negative_control": {
            "blanked_topic_terms": True,
            "n_scored": neg_em["n_scored"],
            "n_emitted": neg_em["n_emitted"],
            "n_abstained": neg_em["n_abstained"],
            "pass": negative_pass,
        },
        "non_vacuity_pass": bool(seeded_pass and negative_pass),
    }


__all__ = [
    "SEED_SENTENCE_DE",
    "run_determinism",
    "run_non_vacuity",
]
