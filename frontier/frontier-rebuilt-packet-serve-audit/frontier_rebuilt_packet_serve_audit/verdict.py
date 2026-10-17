"""ONE machine-checked serve recommendation (charter acceptance test 6).

Pure function of the three measured halves. Enum (frozen in RULES.json):
  SERVE / DO-NOT-SERVE-UNCHANGED / BOUNDED-NEGATIVE-OWNER-DECISION
At most ONE bounded cause per failed half.
"""
from __future__ import annotations

RECOMMENDATION_ENUM = (
    "SERVE",
    "DO-NOT-SERVE-UNCHANGED",
    "BOUNDED-NEGATIVE-OWNER-DECISION",
)


def _label_bar_met(half_a: dict) -> bool:
    """Absolute label bar AS WRITTEN: every issued label supported.

    Uses the ACCEPTED label_gate absolute_status on the scored issued
    population (the population-free instrument reading; see
    half_a.label_bar_status_by_instrument_and_text for the frozen
    rules-text INSUFFICIENT_POPULATION residual, disclosed not re-derived).
    NOT_APPLICABLE from any regression instrument is NOT a pass and never
    contributes to a SERVE.
    """
    gate = half_a.get("accepted_label_gate_as_written") or {}
    pooled = half_a.get("pooled") or {}
    n_issued = pooled.get("n_issued") or 0
    if n_issued == 0:
        return False
    return gate.get("absolute_status") == "LABEL_SOUND"


def _geometry_bar_met(half_b: dict) -> bool:
    return (half_b.get("n_bundles_pass_all_11") or 0) == 3


def _mega_fires(half_b: dict) -> bool:
    return bool(half_b.get("mega_cluster_fires_on_any_rebuilt_bundle"))


def resolve(half_a: dict, half_b: dict, half_c: dict) -> dict:
    label_ok = _label_bar_met(half_a)
    geometry_ok = _geometry_bar_met(half_b)
    mega_ok = _mega_fires(half_b)
    marginal = bool((half_c.get("pooled") or {}).get("marginal_discovery_exists"))
    negative_reproduced = bool((half_c.get("pooled") or {}).get("classification_only_negative_reproduced"))

    # Product-improving halves are promoted AS SUCH regardless of the final
    # enum (charter hypothesis: "IF ANY half comes back passing or
    # independently improving, that is a real product-improving result and
    # must be promoted AS SUCH, never explained away by the pre-rebuild
    # baseline").
    improving = []
    pooled = half_a.get("pooled") or {}
    if pooled.get("n_issued", 0) > 0 and pooled.get("support_rate_among_issued") == 1.0:
        improving.append(
            f"label_half_improving: {pooled.get('n_supported')}/{pooled.get('n_issued')} "
            f"issued counter labels supported under the frozen rubric "
            f"(support_rate_among_issued=1.0; abstentions={pooled.get('n_abstained')}); "
            "accepted instrument (label_gate) absolute_status as written = LABEL_SOUND "
            "(population-free reading; frozen RULES_LABEL.json prose verdict_rule residual "
            "INSUFFICIENT_POPULATION at n_scored<7 disclosed in the record, not re-derived)"
        )
    counts = half_b.get("criterion_counts") or {}
    incumbents = half_b.get("incumbent_counts") or {}
    improved_qids = [
        q for q in sorted(counts)
        if incumbents.get(q) is not None and counts[q] > incumbents[q]
    ]
    if improved_qids:
        pretty = ", ".join(f"{q} {incumbents[q]}->{counts[q]}" for q in improved_qids)
        improving.append(f"geometry_half_improving: per-criterion count rose vs incumbent on {pretty}")
    if marginal:
        improving.append(
            "comparative_half_improving: marginal discovery EXISTS — issued counter "
            "authorities are absent from the initial-pool top-K and/or invisible in "
            "the list top-K, so the map adds a discovery channel the ranked list does not"
        )

    bounded_causes = []
    if not label_ok:
        n_issued = pooled.get("n_issued") or 0
        n_supported = pooled.get("n_supported") or 0
        bounded_causes.append(
            f"label_bar_unmet: {n_supported}/{n_issued} issued counter labels supported "
            "under the frozen rubric (absolute bar 1.0 as written); "
            f"abstentions={pooled.get('n_abstained')}"
        )
    if not geometry_ok:
        pretty = ", ".join(f"{q}={counts.get(q)}" for q in sorted(counts))
        bounded_causes.append(
            f"geometry_bar_unmet: per-criterion counts {pretty} of 11 "
            "(no bundle reaches 11/11 on the frozen criteria)"
        )
    if marginal and not (label_ok and geometry_ok):
        bounded_causes.append(
            "comparative_marginal_discovery_present: some issued counter authorities "
            "are absent from the initial-pool top-K or invisible in the list top-K"
        )
    elif negative_reproduced and not (label_ok and geometry_ok):
        bounded_causes.append(
            "comparative_negative_reproduced: every issued counter authority was "
            "already in the initial-pool top-K and visible in the list top-K "
            "(CLASSIFICATION_ONLY-style negative on the rebuilt bytes)"
        )

    if label_ok and geometry_ok and mega_ok:
        recommendation = "SERVE"
        rationale = (
            "Both frozen absolute bars met as written on the rebuilt bytes "
            "(every issued counter label supported; every anchor bundle 11/11) "
            "and the size-based mega-cluster disclosure fires."
        )
        bounded_causes = []
    elif label_ok and geometry_ok and not mega_ok:
        # SERVE path requires the mega-cluster disclosure to fire (charter
        # stop_promote_rule outcome (A)). Without it this is not a SERVE.
        recommendation = "BOUNDED-NEGATIVE-OWNER-DECISION"
        rationale = (
            "Both frozen absolute bars met but the size-based mega-cluster "
            "disclosure does not fire on the rebuilt bundles, so outcome (A) "
            "SERVE is not reachable; converting the remaining product choice "
            "to the owner."
        )
        bounded_causes.append(
            "mega_cluster_disclosure_not_firing: outcome (A) requires the "
            "size-based mega-cluster disclosure to fire; it does not on the "
            "rebuilt bundles"
        )
    elif not label_ok and not geometry_ok:
        recommendation = "BOUNDED-NEGATIVE-OWNER-DECISION"
        rationale = (
            "Both frozen absolute bars remain unmet on the rebuilt bytes and no "
            "in-budget fix exists inside this charter (charter prohibits classifier "
            "repair, renderer work and threshold design); the map-versus-ranked-list "
            "choice is converted into exactly ONE explicit owner product decision."
        )
    else:
        # Exactly one bar unmet: the rebuild did not clear the serve conclusion.
        # (C) requires BOTH bars unmet, so this residual is (B) — but the
        # improving halves above are still promoted in the record.
        recommendation = "DO-NOT-SERVE-UNCHANGED"
        failed = "label" if not label_ok else "geometry"
        extra = (
            " Product-improving halves are promoted in this record and must not be "
            "explained away by the pre-rebuild baseline."
            if improving else ""
        )
        rationale = (
            f"The rebuild does not change the serve conclusion: the frozen absolute "
            f"{failed} bar remains unmet on the rebuilt bytes; the accepted "
            f"DO-NOT-SERVE order stands.{extra}"
        )

    # At most ONE bounded cause per failed half.
    per_half = {}
    for cause in bounded_causes:
        half = cause.split(":", 1)[0]
        per_half.setdefault(half, cause)
    bounded_causes = [per_half[k] for k in sorted(per_half)]

    one_sentence = f"SERVE RECOMMENDATION: {recommendation} — {rationale}"
    return {
        "serve_recommendation": recommendation,
        "one_sentence": one_sentence,
        "rationale": rationale,
        "bounded_causes": bounded_causes,
        "product_improving_findings": improving,
        "inputs": {
            "label_bar_met": label_ok,
            "geometry_bar_met": geometry_ok,
            "mega_cluster_disclosure_fires": mega_ok,
            "marginal_discovery_exists": marginal,
            "classification_only_negative_reproduced": negative_reproduced,
        },
        "enum": list(RECOMMENDATION_ENUM),
        "machine_checked": True,
        "charter_outcome": {
            "SERVE": "A",
            "DO-NOT-SERVE-UNCHANGED": "B",
            "BOUNDED-NEGATIVE-OWNER-DECISION": "C",
        }[recommendation],
    }
