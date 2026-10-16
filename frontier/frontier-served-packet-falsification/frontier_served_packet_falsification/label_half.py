"""LABEL half: apply the frozen counter-label support rubric to the served packet.

The frozen rubric modules are vendored byte-identically from
lab/frontier/frontier-counter-label-integrity.  This module adapts the entry
point so the SERVED packet (38839347028) can be scored without the old
registration gate: the rubric/lexicons/anchors/normalization are the frozen
bytes; only the input registration differs (the frozen RULES.json inputs list
names the 38799024807 packet, not the served one).  Anchors, verdict threshold
(1.0), scored statuses, defect classes and precedence are unchanged.

No new threshold is introduced.  The verdict classes and the absolute
per-label bar come verbatim from the frozen verdict_rule block.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from .vendored.frontier_counter_label_integrity.extract import (
    counter_rows,
    load_bundle,
    sha256_file,
)
from .vendored.frontier_counter_label_integrity.injection import run_non_vacuity
from .vendored.frontier_counter_label_integrity.report import (
    _class_breakdown,
    _criterion_breakdown,
    _population_summary,
    _signal_breakdown,
)
from .vendored.frontier_counter_label_integrity.rubric import (
    ALL_VARIANTS,
    VARIANT_PRIMARY,
    make_context,
    score_row,
)
from .vendored.frontier_counter_label_integrity.rules import load_rules

# qid -> frozen anchor profile key.  The served packet uses the same three
# question profiles frozen in RULES_LABEL.json's question_anchors block.
QID_TO_PROFILE = {
    "de-kapitalverletzung": "de-kapitalverletzung",
    "fr-bail-entretien": "fr-bail-entretien",
    "it-responsabilita-medica": "it-responsabilita-medica",
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def score_served_bundle(
    rules,
    bundle_path: str,
    qid: str,
    *,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    """Score one served-packet bundle under the frozen rubric (all variants).

    Unlike the accepted team's score_bundle, this does NOT require the path to
    be a frozen input of RULES.json (the served packet is a later rebuild).
    The frozen rubric, lexicons, anchors and verdict threshold are applied
    unchanged; the input identity is pinned by INPUT_LIST.json sha256 instead.
    """
    digest = sha256_file(bundle_path)
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError(
            f"input sha256 drift for {bundle_path}: expected {expected_sha256}, observed {digest}"
        )

    profile_key = QID_TO_PROFILE.get(qid)
    if profile_key is None or profile_key not in rules.anchors:
        raise ValueError(f"no frozen anchor profile for qid {qid!r}")

    bundle = load_bundle(bundle_path)
    scored_statuses = list(rules.rubric["scored_statuses"])
    reported_statuses = list(rules.rubric["reported_separately_never_scored"])
    scored_rows, reported_rows = counter_rows(bundle, scored_statuses, reported_statuses)

    by_variant: dict[str, list[dict[str, Any]]] = {}
    for variant in ALL_VARIANTS:
        ctx = make_context(rules, profile_key, variant)
        by_variant[variant] = [score_row(r, ctx) for r in scored_rows]

    primary = by_variant[VARIANT_PRIMARY]
    n_supported = sum(1 for r in primary if r["supported"])
    return {
        "qid": qid,
        "bundle_path": bundle_path,
        "sha256": digest,
        "sha256_matches_expected": (
            digest == expected_sha256 if expected_sha256 is not None else None
        ),
        "anchor_profile": profile_key,
        "n_decisions": len(bundle.get("decisions") or []),
        "n_scored": len(primary),
        "n_supported": n_supported,
        "support_rate": (n_supported / len(primary)) if primary else None,
        "n_reported_only": len(reported_rows),
        "reported_only_rows": [
            {
                "decision_id": r["decision_id"],
                "rank": r["rank"],
                "language": r["language"],
                "counter_status": r["counter_status"],
                "counter_evidence": r["counter_evidence"],
                "counter_uncertainty": r["counter_uncertainty"],
            }
            for r in reported_rows
        ],
        "defect_classes": _class_breakdown(primary),
        "defect_signals": _signal_breakdown(primary),
        "criterion_failures": _criterion_breakdown(primary),
        "rows": primary,
        "rows_by_variant": by_variant,
        "query": bundle.get("query"),
    }


def _population_summary_served(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    """Overall summary across the three served bundles (single population)."""
    rows: list[dict[str, Any]] = []
    for b in sorted(bundles, key=lambda x: x["qid"]):
        for r in b["rows"]:
            rows.append({**r, "bundle": b["qid"]})
    rows.sort(key=lambda r: (str(r["bundle"]), int(r["rank"] or 10**9), str(r["decision_id"])))
    n = len(rows)
    supported = [r for r in rows if r["supported"]]
    unsupported = [r for r in rows if not r["supported"]]
    rate = (len(supported) / n) if n else None

    # counter_evidence_verified distribution
    verified = {"present_true": 0, "present_false": 0, "absent": 0}
    for r in rows:
        v = r.get("counter_evidence_verified")
        present = r.get("counter_evidence_verified_field_present")
        if v is True:
            verified["present_true"] += 1
        elif v is False:
            verified["present_false"] += 1
        else:
            verified["absent"] += 1
        _ = present

    # Empty-evidence at max uncertainty: the charter's named 16
    empty_max = [
        {
            "bundle": r["bundle"],
            "decision_id": r["decision_id"],
            "counter_status": r["counter_status"],
            "counter_uncertainty": r["counter_uncertainty"],
            "counter_evidence": r.get("cited_evidence"),
            "primary_defect_class": r["primary_defect_class"],
            "reason_code": r["reason_code"],
            "supported": r["supported"],
        }
        for r in rows
        if r.get("cited_evidence_empty")
        and float(r.get("counter_uncertainty") or 0) >= 0.95
    ]
    empty_max.sort(key=lambda x: (str(x["bundle"]), str(x["decision_id"])))

    return {
        "n_bundles": len(bundles),
        "n_scored": n,
        "n_supported": len(supported),
        "n_unsupported": len(unsupported),
        "support_rate": rate,
        "supported_row_ids": sorted(str(r["decision_id"]) for r in supported),
        "unsupported_row_ids": sorted(str(r["decision_id"]) for r in unsupported),
        "defect_classes": _class_breakdown(rows),
        "defect_signals": _signal_breakdown(rows),
        "criterion_failures": _criterion_breakdown(rows),
        "counter_evidence_verified_distribution": verified,
        "n_empty_evidence_at_uncertainty_ge_0_95": len(empty_max),
        "empty_evidence_at_uncertainty_ge_0_95_rows": empty_max,
        "language_distribution": {
            lang: sum(1 for r in rows if r["language"] == lang)
            for lang in sorted({r["language"] for r in rows})
        },
        "rows": [
            {
                "bundle": r["bundle"],
                "decision_id": r["decision_id"],
                "counter_status": r["counter_status"],
                "rank": r["rank"],
                "language": r["language"],
                "counter_reason": r.get("counter_reason"),
                "counter_confidence": r.get("counter_confidence"),
                "counter_uncertainty": r.get("counter_uncertainty"),
                "cited_evidence": r.get("cited_evidence"),
                "primary_defect_class": r["primary_defect_class"],
                "reason_code": r["reason_code"],
                "defect_signals": r["defect_signals"],
                "precedence_step_fired": r["precedence_step_fired"],
                "criterion_marks": {k: v["pass"] for k, v in r["criterion_marks"].items()},
                "supported": r["supported"],
            }
            for r in rows
        ],
    }


def run_label_half(
    rules_path: str,
    packet_dir: str,
    bundle_sha256: dict[str, str],
    *,
    expected_rules_sha256: str,
) -> dict[str, Any]:
    """Score all three served bundles under the frozen rubric and produce the
    half-verdict under the frozen verdict_rule."""
    rules = load_rules(rules_path)
    if rules.sha256 != expected_rules_sha256:
        raise ValueError(
            f"rules sha256 mismatch: expected {expected_rules_sha256}, observed {rules.sha256}"
        )

    bundles: list[dict[str, Any]] = []
    for qid, sha in sorted(bundle_sha256.items()):
        path = os.path.join(packet_dir, "questions", f"{qid}.bundle.json")
        bundles.append(
            score_served_bundle(rules, path, qid, expected_sha256=sha)
        )

    non_vacuity = run_non_vacuity(rules)
    overall = _population_summary_served(bundles)

    # Frozen verdict_rule: LABEL_SOUND iff support_rate == 1.0 on the
    # deciding population; ANY unsupported label makes it LABEL_UNSOUND.
    # There is no separate primary/secondary here: the served packet IS the
    # deciding population (three bundles, 65 issued labels).
    n = overall["n_scored"]
    if not non_vacuity["passed"]:
        verdict = "INSUFFICIENT_POPULATION"
        gaps = ["non-vacuity did not pass"]
    elif n == 0:
        verdict = "INSUFFICIENT_POPULATION"
        gaps = ["no scored rows"]
    elif overall["n_supported"] == n:
        verdict = "LABEL_SOUND"
        gaps = []
    else:
        verdict = "LABEL_UNSOUND"
        gaps = []

    # Sensitivity variants over the same served population
    variants: dict[str, Any] = {}
    for variant in ALL_VARIANTS:
        rows_v: list[dict[str, Any]] = []
        for b in sorted(bundles, key=lambda x: x["qid"]):
            for r in b["rows_by_variant"][variant]:
                rows_v.append({**r, "bundle": b["qid"]})
        rows_v.sort(key=lambda r: (str(r["bundle"]), int(r["rank"] or 10**9), str(r["decision_id"])))
        sup_v = [r for r in rows_v if r["supported"]]
        variants[variant] = {
            "n_scored": len(rows_v),
            "n_supported": len(sup_v),
            "support_rate": (len(sup_v) / len(rows_v)) if rows_v else None,
            "defect_classes": _class_breakdown(rows_v),
            "row_class_map": {str(r["decision_id"]): r["primary_defect_class"] for r in rows_v},
        }

    # Non-vacuity on the population (acceptance test 6): can any real row
    # reach SUPPORTED?  If zero do, the report must say so with evidence.
    n_real_supported = overall["n_supported"]
    population_nonvacuity = {
        "n_real_rows_scored_supported": n_real_supported,
        "at_least_one_real_row_supported": n_real_supported > 0,
        "statement": (
            f"{n_real_supported} of {n} real served-packet rows score SUPPORTED under the frozen rubric."
            if n_real_supported > 0
            else (
                f"ZERO of {n} real served-packet rows can reach SUPPORTED under the frozen rubric. "
                "This is an acceptable and expected outcome of the harness, not a harness failure; "
                "it is never presented as SUPPORTED."
            )
        ),
        "harness_non_vacuity_injection_passed": non_vacuity["passed"],
    }

    return {
        "schema": "frontier-served-packet-falsification/label-half/1",
        "rules_sha256": rules.sha256,
        "rules_byte_identity_ok": rules.sha256 == expected_rules_sha256,
        "population_definition": (
            "Every row of the served gate packet 38839347028 whose counter_status is in "
            "the frozen scored_statuses set {candidate-limiting, candidate-contrary, "
            "contrary_or_exception, limiting}."
        ),
        "n_scored": n,
        "n_supported": overall["n_supported"],
        "support_rate": overall["support_rate"],
        "verdict": verdict,
        "verdict_classes_available": list(rules.verdict_rule["verdict_classes"]),
        "threshold_support_rate_sound": rules.verdict_rule["threshold_support_rate_sound"],
        "threshold_support_rate_unsound_below": rules.verdict_rule["threshold_support_rate_unsound_below"],
        "aggregation": rules.verdict_rule["aggregation"],
        "gaps": gaps,
        "non_vacuity": non_vacuity,
        "population_nonvacuity": population_nonvacuity,
        "overall": overall,
        "bundles": [
            {
                "qid": b["qid"],
                "sha256": b["sha256"],
                "sha256_matches_expected": b["sha256_matches_expected"],
                "n_decisions": b["n_decisions"],
                "n_scored": b["n_scored"],
                "n_supported": b["n_supported"],
                "support_rate": b["support_rate"],
                "n_reported_only": b["n_reported_only"],
                "reported_only_rows": b["reported_only_rows"],
                "defect_classes": b["defect_classes"],
                "anchor_profile": b["anchor_profile"],
                "query": b["query"],
                "rows": [
                    {
                        "decision_id": r["decision_id"],
                        "counter_status": r["counter_status"],
                        "rank": r["rank"],
                        "language": r["language"],
                        "counter_reason": r.get("counter_reason"),
                        "counter_uncertainty": r.get("counter_uncertainty"),
                        "counter_evidence_verified": r.get("counter_evidence_verified"),
                        "cited_evidence": r.get("cited_evidence"),
                        "primary_defect_class": r["primary_defect_class"],
                        "reason_code": r["reason_code"],
                        "criterion_marks": {k: v["pass"] for k, v in r["criterion_marks"].items()},
                        "supported": r["supported"],
                    }
                    for r in b["rows"]
                ],
            }
            for b in sorted(bundles, key=lambda x: x["qid"])
        ],
        "sensitivity_variants": variants,
    }
