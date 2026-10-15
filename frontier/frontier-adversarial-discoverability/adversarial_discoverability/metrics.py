"""The seven frozen metric families (RULES.json ``metrics``).

Every metric returns a dict::

    {"name": ..., "applicability": "APPLICABLE"|"NOT_APPLICABLE",
     "value": <float|None>, "verdict": "PASS"|"FAIL"|"OBSERVED"|"NOT_APPLICABLE",
     "threshold": {...}, "why_not_applicable": <str|None>, ...detail...}

No metric reads the wall clock, the network, or any file.  Pure functions only.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from . import COUNTER_VALUES, PLACEHOLDER_EVIDENCE
from . import populations as pop

THRESHOLDS = {
    "MIN_COUNTER_YIELD": 0.02,
    "MIN_BEYOND_TOP20_SHARE": 0.30,
    "MIN_DISCOVERABLE_PLACEMENT_SHARE": 0.50,
    "MIN_VERIFIED_EVIDENCE_SHARE": 0.50,
    "MAX_PLACEHOLDER_EVIDENCE_SHARE": 0.50,
    "MIN_MINORITY_REACH_SHARE": 0.20,
}


def _na(name: str, why: str) -> Dict[str, Any]:
    return {
        "name": name,
        "applicability": "NOT_APPLICABLE",
        "value": None,
        "verdict": "NOT_APPLICABLE",
        "why_not_applicable": why,
    }


def _share(num: int, den: int) -> Optional[float]:
    if den <= 0:
        return None
    return round(num / den, 6)


def _pf(verdict: str, value: Optional[float], threshold: Dict[str, Any], **extra) -> Dict[str, Any]:
    out = {
        "name": None,
        "applicability": "APPLICABLE",
        "value": value,
        "verdict": verdict,
        "threshold": threshold,
    }
    out.update(extra)
    return out


# --------------------------------------------------------------------------
# (a) counter yield
# --------------------------------------------------------------------------

def metric_a_counter_yield(doc: Dict[str, Any], rows: Sequence[Dict[str, Any]],
                           n_bundle_total: Optional[int] = None) -> Dict[str, Any]:
    """``a_counter_yield(B) = |C_strict(B)| / |B_all(B)|`` — a share of the BUNDLE.

    ``n_bundle_total`` is ``|B_all|`` and is supplied by the harness because a
    slimmed reality-check leg exposes only its answer-cited rows while still
    reporting the true population size as ``decision_count``.  Scoring a leg
    against ``len(cited_decisions)`` would inflate its yield ~20x.
    """
    n_all = int(n_bundle_total) if n_bundle_total else len(rows)
    strict = pop.c_strict(rows)
    challenged = pop.c_challenged(rows)
    value = _share(len(strict), n_all)
    verdict = "PASS" if (value is not None and value >= THRESHOLDS["MIN_COUNTER_YIELD"]) else "FAIL"
    hist: Dict[str, int] = {}
    for d in rows:
        k = pop.counter_status(d)
        hist[k] = hist.get(k, 0) + 1
    out = _pf(
        verdict, value,
        {"rule": "PASS iff value >= MIN_COUNTER_YIELD", **THRESHOLDS},
        n_bundle_total=n_all,
        n_rows_exposed=len(rows),
        denominator_is_bundle_total=(n_all != len(rows)),
        n_counter_strict=len(strict),
        counter_strict_share=value,
        n_counter_challenged=len(challenged),
        counter_challenged_share=_share(len(challenged), n_all),
        counter_status_histogram=dict(sorted(hist.items())),
        counter_ids=[d.get("decision_id") for d in strict],
        challenged_ids=[d.get("decision_id") for d in challenged],
        counter_status_values=list(COUNTER_VALUES),
    )
    out["name"] = "a_counter_yield"
    return out


# --------------------------------------------------------------------------
# (b) marginal retrieval contribution
# --------------------------------------------------------------------------

def metric_b_marginal_retrieval(doc: Dict[str, Any], rows: Sequence[Dict[str, Any]],
                               shortlist: Optional[set] = None) -> Dict[str, Any]:
    name = "b_marginal_retrieval_contribution"
    if not pop.has_retrieval_provenance(doc):
        return _na(name, "artifact carries no initial-retrieval channel provenance "
                         "(reality-check leg reports slim the bundle); RULES.json "
                         "metrics.b_marginal_retrieval_contribution: NOT_APPLICABLE, "
                         "never PASS")

    strict = pop.c_strict(rows)
    initial = pop.initial_channel_set(doc)
    per_row_new: List[List[str]] = []
    hist: Dict[str, int] = {}
    new_channels: set = set()
    for d in strict:
        ch = pop.channels_of(d)
        for c in ch:
            hist[c] = hist.get(c, 0) + 1
        extra = sorted({c for c in ch if c not in initial})
        new_channels.update(extra)
        per_row_new.append(extra)

    b1 = sum(1 for extra in per_row_new if extra)
    all_ids = {str(d.get("decision_id")) for d in rows}
    b4 = sum(1 for d in strict if str(d.get("decision_id")) not in all_ids)

    b5 = b6 = None
    reach_detail: Dict[str, Any] = {}
    if shortlist is not None:
        counter_ids = {str(d.get("decision_id")) for d in strict}
        reached = len(counter_ids & set(shortlist))
        b5 = _share(reached, len(counter_ids)) if counter_ids else None
        b6 = _share(len(all_ids) - len(set(shortlist) & all_ids), len(all_ids))
        reach_detail = {
            "shortlist_size": len(shortlist),
            "bundle_size": len(all_ids),
            "counter_rows_reached": reached,
            "counter_rows": len(counter_ids),
            "shortlist_ids": sorted(str(x) for x in shortlist),
        }

    passed = (b1 >= 1) or (b4 >= 1)
    adv = (doc.get("provenance") or {}).get("generative_audit") or {}
    adv = adv.get("adversarial") if isinstance(adv, dict) else {}
    out = _pf(
        "PASS" if passed else "FAIL",
        b1,
        {"rule": "PASS iff b1_adversarial_channel_rows >= 1 OR b4_adversarial_only_ids >= 1"},
        b1_adversarial_channel_rows=b1,
        b1_rows=[d.get("decision_id") for d, extra in zip(strict, per_row_new) if extra],
        b1_per_row_new_channels={str(d.get("decision_id")): extra
                                 for d, extra in zip(strict, per_row_new) if extra},
        b2_new_channels=sorted(new_channels),
        b3_counter_channel_histogram=dict(sorted(hist.items())),
        b4_adversarial_only_ids=b4,
        b5_shortlist_reach_rate=b5,
        b6_pool_never_seen_rate=b6,
        initial_channel_set=sorted(initial),
        product_recorded=({
            "method": adv.get("method"),
            "bundle_decisions": adv.get("bundle_decisions"),
            "prompt_decisions": adv.get("prompt_decisions"),
            "prompt_strategy": adv.get("prompt_strategy"),
            "independence": adv.get("independence"),
        } if isinstance(adv, dict) else {}),
        context_only={
            "progressive": (doc.get("provenance") or {}).get("progressive"),
            "evidence_hydration": (doc.get("provenance") or {}).get("evidence_hydration"),
        },
        **reach_detail,
    )
    out["name"] = name
    return out


# --------------------------------------------------------------------------
# (c) rank placement
# --------------------------------------------------------------------------

def metric_c_rank_placement(doc: Dict[str, Any], rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    name = "c_rank_placement"
    strict = pop.c_strict(rows)
    pairs = pop.ranked_pairs(strict)
    ranks = sorted(r for _d, r in pairs)
    n = len(ranks)
    if n == 0:
        out = _pf("FAIL", 0.0,
                  {"rule": "PASS iff beyond_top20_share >= MIN_BEYOND_TOP20_SHARE", **THRESHOLDS},
                  counter_ranks=[], note="no counter rows; yield metric (a) governs")
        out["name"] = name
        return out
    beyond20 = sum(1 for r in ranks if r > 20)
    beyond10 = sum(1 for r in ranks if r > 10)
    value = _share(beyond20, n)
    median = ranks[n // 2] if n % 2 else (ranks[n // 2 - 1] + ranks[n // 2]) / 2.0
    out = _pf(
        "PASS" if (value is not None and value >= THRESHOLDS["MIN_BEYOND_TOP20_SHARE"]) else "FAIL",
        value,
        {"rule": "PASS iff beyond_top20_share >= MIN_BEYOND_TOP20_SHARE", **THRESHOLDS},
        n_counter=n,
        counter_ranks=ranks,
        counter_rank_by_id={str(d.get("decision_id")): r for d, r in pairs},
        min_rank=ranks[0],
        median_rank=median,
        max_rank=ranks[-1],
        top10_share=_share(sum(1 for r in ranks if r <= 10), n),
        top20_share=_share(sum(1 for r in ranks if r <= 20), n),
        beyond_top10_share=_share(beyond10, n),
        beyond_top20_share=value,
        bundle_rank_max=max((r for _d, r in pop.ranked_pairs(rows)), default=None),
    )
    out["name"] = name
    return out


# --------------------------------------------------------------------------
# (d) placement visibility
# --------------------------------------------------------------------------

def metric_d_placement(doc: Dict[str, Any], rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    name = "d_placement_visibility"
    strict = pop.c_strict(rows)
    if not strict:
        out = _pf("FAIL", 0.0,
                  {"rule": "PASS iff discoverable_placement_share >= MIN_DISCOVERABLE_PLACEMENT_SHARE",
                   **THRESHOLDS}, note="no counter rows")
        out["name"] = name
        return out
    if not any("cluster_id" in d or "is_outlier" in d for d in rows):
        return _na(name, "rows carry neither cluster_id nor is_outlier (reality-check leg "
                         "reports slim the bundle)")

    cc = pop.consensus_cluster(doc)
    n = len(strict)
    outliers = [d for d in strict if d.get("is_outlier") is True]
    distinct = [d for d in strict if d.get("cluster_id") != cc]
    discoverable = {str(d.get("decision_id")) for d in outliers} | {
        str(d.get("decision_id")) for d in distinct}
    value = _share(len(discoverable), n)
    hist: Dict[str, int] = {}
    for d in strict:
        k = str(d.get("cluster_id"))
        hist[k] = hist.get(k, 0) + 1
    out = _pf(
        "PASS" if (value is not None and value >= THRESHOLDS["MIN_DISCOVERABLE_PLACEMENT_SHARE"]) else "FAIL",
        value,
        {"rule": "PASS iff discoverable_placement_share >= MIN_DISCOVERABLE_PLACEMENT_SHARE",
         **THRESHOLDS},
        n_counter=n,
        consensus_cluster_id=cc,
        consensus_cluster_size=next((c.get("size") for c in (doc.get("clusters") or [])
                                     if c.get("cluster_id") == cc), None),
        is_outlier_share=_share(len(outliers), n),
        distinct_cluster_share=_share(len(distinct), n),
        discoverable_placement_share=value,
        counter_cluster_histogram=dict(sorted(hist.items())),
        counter_rows=[{
            "decision_id": d.get("decision_id"),
            "rank": d.get("rank"),
            "cluster_id": d.get("cluster_id"),
            "is_outlier": d.get("is_outlier"),
            "counter_status": pop.counter_status(d),
        } for d in strict],
    )
    out["name"] = name
    return out


# --------------------------------------------------------------------------
# (e) evidence quality
# --------------------------------------------------------------------------

def metric_e_evidence(doc: Dict[str, Any], rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    name = "e_evidence_quality"
    if not pop.rows_carry(doc, rows, ("counter_evidence", "counter_reason",
                                      "counter_evidence_verified")):
        return _na(name, "row schema exports no counter_evidence / counter_reason / "
                         "counter_evidence_verified at all (slimmed reality-check leg "
                         "report); scoring this as 0 would measure the reporting gap, "
                         "not the product's evidence quality")
    strict = pop.c_strict(rows)
    n = len(strict)
    if n == 0:
        out = _pf("FAIL", 0.0,
                  {"rule": "verified_with_reason_share >= MIN_VERIFIED_EVIDENCE_SHARE "
                           "and placeholder_evidence_share <= MAX_PLACEHOLDER_EVIDENCE_SHARE",
                   **THRESHOLDS}, note="no counter rows")
        out["name"] = name
        return out
    verified = [d for d in strict if pop.verified_flag(d)]
    with_reason = [d for d in strict if pop.substantive_reason(d)]
    both = [d for d in strict if pop.verified_flag(d) and pop.substantive_reason(d)]
    placeholders = [d for d in strict if pop.placeholder_evidence(d)]
    empty = [d for d in strict if not str(d.get("counter_evidence") or "").strip()]
    verified_share = _share(len(both), n)
    placeholder_share = _share(len(placeholders), n)
    ok = ((verified_share is not None and verified_share >= THRESHOLDS["MIN_VERIFIED_EVIDENCE_SHARE"])
          and (placeholder_share is not None and placeholder_share <= THRESHOLDS["MAX_PLACEHOLDER_EVIDENCE_SHARE"]))
    out = _pf(
        "PASS" if ok else "FAIL",
        verified_share,
        {"rule": "verified_with_reason_share >= MIN_VERIFIED_EVIDENCE_SHARE AND "
                 "placeholder_evidence_share <= MAX_PLACEHOLDER_EVIDENCE_SHARE",
         **THRESHOLDS},
        n_counter=n,
        n_verified_flag=len(verified),
        n_substantive_reason=len(with_reason),
        n_verified_with_reason=len(both),
        verified_with_reason_share=verified_share,
        n_placeholder_evidence=len(placeholders),
        placeholder_evidence_share=placeholder_share,
        n_empty_evidence=len(empty),
        placeholder_literal=PLACEHOLDER_EVIDENCE,
        counter_rows=[{
            "decision_id": d.get("decision_id"),
            "rank": d.get("rank"),
            "counter_status": pop.counter_status(d),
            "counter_evidence_verified": d.get("counter_evidence_verified"),
            "counter_reason": d.get("counter_reason"),
            "counter_uncertainty": d.get("counter_uncertainty"),
            "counter_confidence": d.get("counter_confidence"),
            "counter_evidence_preview": str(d.get("counter_evidence") or "")[:200],
            "evidence_class": ("placeholder" if pop.placeholder_evidence(d)
                               else ("empty" if not str(d.get("counter_evidence") or "").strip()
                                     else "substantive")),
        } for d in strict],
    )
    out["name"] = name
    return out


# --------------------------------------------------------------------------
# (f) answer linkage — OBSERVED only, never gated (RULES.json metrics.f)
# --------------------------------------------------------------------------

def metric_f_answer_linkage(doc: Dict[str, Any], rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    name = "f_answer_linkage"
    strict = pop.c_strict(rows)
    prose = pop.answer_prose(doc)
    cited = set(pop.answer_cited_ids(doc))
    per_row = []
    hits = 0
    for d in strict:
        did = str(d.get("decision_id"))
        in_prose = bool(did) and did in prose
        in_cited = did in cited
        hit = in_prose or in_cited
        hits += 1 if hit else 0
        per_row.append({"decision_id": did, "in_answer_prose": in_prose,
                        "in_answer_cited_decision_ids": in_cited})
    out = _pf(
        "OBSERVED",
        _share(hits, len(strict)) if strict else None,
        {"rule": "OBSERVED only; never enters a verdict (RULES.json metrics.f_answer_linkage)"},
        n_counter=len(strict),
        n_linked=hits,
        answer_mentions_counter_share=_share(hits, len(strict)) if strict else None,
        answer_prose_chars=len(prose),
        n_answer_cited_ids=len(cited),
        counter_rows=per_row,
    )
    out["name"] = name
    return out


# --------------------------------------------------------------------------
# (g) language / minority reach
# --------------------------------------------------------------------------

def metric_g_minority_reach(doc: Dict[str, Any], rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    name = "g_language_minority_reach"
    strict = pop.c_strict(rows)
    if not strict:
        out = _pf("FAIL", 0.0,
                  {"rule": "PASS iff minority_reach_share >= MIN_MINORITY_REACH_SHARE",
                   **THRESHOLDS}, note="no counter rows")
        out["name"] = name
        return out
    cc = pop.consensus_cluster(doc)
    cl = pop.modal_language(doc, cc)
    med = pop.median_year(doc)
    has_years = any(pop.year_of(d) is not None for d in rows)
    if cl is None and not has_years:
        return _na(name, "neither decision_date years nor a consensus-cluster modal language "
                         "are derivable from this artifact's rows (slimmed reality-check "
                         "leg report); scoring this as 0 would invent a minority-reach "
                         "finding")
    lang_rows, year_rows = [], []
    n = len(strict)
    for d in strict:
        lang = str(d.get("language") or "?").lower()
        y = pop.year_of(d)
        non_lang = (cl is not None and lang != cl)
        older = (med is not None and y is not None and y < med)
        lang_rows.append(non_lang)
        year_rows.append(older)
    reach = {i for i in range(n) if lang_rows[i] or year_rows[i]}
    value = _share(len(reach), n)
    out = _pf(
        "PASS" if (value is not None and value >= THRESHOLDS["MIN_MINORITY_REACH_SHARE"]) else "FAIL",
        value,
        {"rule": "PASS iff minority_reach_share >= MIN_MINORITY_REACH_SHARE", **THRESHOLDS},
        n_counter=n,
        consensus_cluster_id=cc,
        consensus_language=cl,
        bundle_median_year=med,
        non_consensus_language_share=_share(sum(lang_rows), n),
        older_than_median_share=_share(sum(year_rows), n),
        minority_reach_share=value,
        counter_rows=[{
            "decision_id": d.get("decision_id"),
            "language": d.get("language"),
            "decision_date": d.get("decision_date"),
            "year": pop.year_of(d),
            "non_consensus_language": lang_rows[i],
            "older_than_median": year_rows[i],
        } for i, d in enumerate(strict)],
    )
    out["name"] = name
    return out


ALL_METRICS = (metric_a_counter_yield, metric_b_marginal_retrieval,
               metric_c_rank_placement, metric_d_placement,
               metric_e_evidence, metric_f_answer_linkage,
               metric_g_minority_reach)


def all_metrics(doc: Dict[str, Any], rows: Sequence[Dict[str, Any]],
                shortlist: Optional[set] = None,
                n_bundle_total: Optional[int] = None) -> Dict[str, Any]:
    """Run the seven frozen metrics over one artifact.

    ``rows`` is the population the artifact actually exposes: ``decisions`` for
    a query_result_bundle, ``cited_decisions`` for a slimmed reality-check leg.
    ``n_bundle_total`` is ``|B_all|`` for metric (a)'s denominator.
    """
    out: Dict[str, Any] = {}
    for fn in ALL_METRICS:
        if fn is metric_b_marginal_retrieval:
            m = fn(doc, rows, shortlist)
        elif fn is metric_a_counter_yield:
            m = fn(doc, rows, n_bundle_total)
        else:
            m = fn(doc, rows)
        out[m["name"]] = m
    return out


def verdicts(metrics: Dict[str, Any]) -> Dict[str, str]:
    """RULES.json ``verdict_rule.per_input``, verbatim."""
    a = metrics["a_counter_yield"]["verdict"]
    c = metrics["c_rank_placement"]["verdict"]
    d = metrics["d_placement_visibility"]["verdict"]
    e = metrics["e_evidence_quality"]["verdict"]
    g = metrics["g_language_minority_reach"]["verdict"]
    b = metrics["b_marginal_retrieval_contribution"]["verdict"]

    discoverability = "PASS" if (a == c == d == "PASS") else "FAIL"
    parts_na = [k for k, v in (("a_counter_yield", a), ("c_rank_placement", c),
                               ("d_placement_visibility", d))
                if v == "NOT_APPLICABLE"]
    return {
        "retrieval_independence": b,
        "discoverability": discoverability,
        "discoverability_parts": {"a_counter_yield": a, "c_rank_placement": c,
                                  "d_placement_visibility": d},
        "discoverability_not_applicable_parts": parts_na,
        "discoverability_note": (
            "frozen rule evaluated verbatim: discoverability is PASS only if a, c and d "
            "all PASS. Parts that are NOT_APPLICABLE cannot PASS, so an artifact missing "
            "a part reports FAIL with the missing part listed." ) if parts_na else None,
        "evidence_quality": e,
        "minority_reach": g,
        "answer_linkage": "OBSERVED",
    }
