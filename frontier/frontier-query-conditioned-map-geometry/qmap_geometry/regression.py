"""Regression suite: what a variant must NOT change.

Charter acceptance test (6).  A variant is a layout, not a new retrieval: the
rendered population, the identity of every decision, the cluster-count rule and
the size-versus-member_ids truncation contract are pinned to the shipped bundle.
"""
from __future__ import annotations

from typing import Any

from .hydration import hydration_mask

ACCEPTED_N_DECISIONS = {
    "de-kapitalverletzung": 214,
    "fr-bail-entretien": 217,
    "it-responsabilita-medica": 211,
}


def check_variant(
    shipped: dict,
    candidate: dict,
    qid: str,
    *,
    expected_n_clusters: int | None = 8,
) -> dict[str, Any]:
    s_dec = shipped.get("decisions") or []
    c_dec = candidate.get("decisions") or []
    s_ids = [d.get("decision_id") for d in s_dec]
    c_ids = [d.get("decision_id") for d in c_dec]
    checks: dict[str, bool] = {}

    checks["point_count_unchanged"] = len(s_dec) == len(c_dec)
    checks["per_bundle_decision_count_matches_accepted"] = (
        len(c_dec) == ACCEPTED_N_DECISIONS.get(qid, len(c_dec))
    )
    checks["decision_ids_same_order_no_drop_no_duplicate"] = s_ids == c_ids
    checks["decision_id_multiset_identical"] = sorted(map(str, s_ids)) == sorted(map(str, c_ids))
    checks["n_clusters_unchanged"] = (
        expected_n_clusters is None
        or len(candidate.get("clusters") or []) == expected_n_clusters
    )

    # size vs len(member_ids) truncation contract (qmap emits size=true,
    # member_ids capped at 50).
    trunc_ok = True
    member_prefix_ok = True
    membership_from_rows = {
        int(c["cluster_id"]): sum(1 for d in c_dec if int(d.get("cluster_id")) == int(c["cluster_id"]))
        for c in candidate.get("clusters") or []
    }
    for c in candidate.get("clusters") or []:
        cid = int(c["cluster_id"])
        size = int(c.get("size") or 0)
        members = c.get("member_ids") or []
        if size != membership_from_rows.get(cid, 0):
            trunc_ok = False
        if not (len(members) == min(50, size)):
            member_prefix_ok = False
        row_members = [d.get("decision_id") for d in c_dec if int(d.get("cluster_id")) == cid]
        if members != row_members[: len(members)]:
            member_prefix_ok = False
    checks["size_field_equals_true_membership"] = trunc_ok
    checks["member_ids_truncation_contract"] = member_prefix_ok

    # Unclustered shells: unique negative ids, never in a cluster record.
    mask = hydration_mask(s_dec)
    shell_ids = {s_ids[i] for i, s in enumerate(mask) if s}
    kept_ids = {s_ids[i] for i, s in enumerate(mask) if not s}
    c_shell_cids = [
        int(d.get("cluster_id")) for d in c_dec if d.get("decision_id") in shell_ids
    ]
    checks["shells_are_unclustered_negative_unique"] = (
        len(c_shell_cids) == len(shell_ids)
        and all(c < 0 for c in c_shell_cids)
        and len(set(c_shell_cids)) == len(c_shell_cids)
    )
    record_cids = {int(c["cluster_id"]) for c in candidate.get("clusters") or []}
    covered_by_records = {
        d.get("decision_id")
        for d in c_dec
        if int(d.get("cluster_id")) in record_cids
    }
    checks["cluster_records_never_cover_a_shell"] = not (covered_by_records & shell_ids)
    checks["cluster_record_ids_are_non_negative"] = all(c >= 0 for c in record_cids)
    checks["shell_cluster_ids_never_collide_with_a_record"] = not (
        {c for c in c_shell_cids} & record_cids
    )
    checks["every_non_shell_row_is_in_a_cluster"] = covered_by_records == kept_ids
    checks["no_cluster_record_without_members"] = all(
        membership_from_rows.get(int(c["cluster_id"]), 0) > 0
        for c in candidate.get("clusters") or []
    )

    # Fields a layout variant must not touch.
    def _pick(d: dict, keys: tuple[str, ...]) -> dict:
        return {k: d.get(k) for k in keys}

    passthrough = ("query", "answer", "provenance", "query_variants", "bundle_version")
    checks["bundle_header_fields_untouched"] = all(
        shipped.get(k) == candidate.get(k) for k in passthrough
    )
    row_fields = (
        "decision_id", "rank", "score", "language", "citation", "court",
        "decision_date", "full_text", "regeste", "snippet", "title",
        "detail_status", "counter_status", "counter_evidence",
    )
    checks["row_payloads_untouched"] = all(
        _pick(s, row_fields) == _pick(c, row_fields) for s, c in zip(s_dec, c_dec)
    )
    checks["relations_untouched"] = (shipped.get("relations") or []) == (
        candidate.get("relations") or []
    )

    # Outlier budget: qmap marks max(1, n//10) rows.
    n = len(c_dec)
    n_out = sum(1 for d in c_dec if d.get("is_outlier"))
    checks["outlier_budget_respected"] = n_out == (max(1, n // 10) if n >= 10 else 0)

    checks["every_row_has_coordinates"] = all(
        isinstance(d.get("x"), (int, float)) and isinstance(d.get("y"), (int, float))
        for d in c_dec
    )

    return {
        "qid": qid,
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(1 for v in checks.values() if not v),
        "passed": all(checks.values()),
        "n_decisions": n,
        "n_clusters": len(candidate.get("clusters") or []),
        "n_shells": len(shell_ids),
    }
