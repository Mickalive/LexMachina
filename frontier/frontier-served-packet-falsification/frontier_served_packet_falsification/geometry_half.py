"""GEOMETRY half: apply the frozen map-semantics rule to the served packet.

The frozen metrics/textgeo modules are vendored byte-identically from
lab/frontier/frontier-map-semantics.  Frozen bars (PROJ_SPEARMAN >= 0.50,
PROJ_RANK >= 0.30, PROJ_KNN10 >= 0.40, STRUCTURE_LARGEST <= 0.60,
STRUCTURE_SEP < 0.90, COHERENCE_QUERY_LANG/TERM as frozen,
LABEL_CONTENT_FRACTION >= 0.80, LABEL_JACCARD <= 0.50 + distinct,
OUTLIER_VALIDITY, RELATIONS >= 10 & endpoints & kind) are applied unchanged.

The un-hydrated-row ablation is run side by side. Largest-cluster share is
reported from BOTH definitions: the cluster 'size' field and len(member_ids),
with the 50-cap truncation flagged.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from .vendored.frontier_map_semantics.metrics import ablate, tfidf_of, verdicts
from .vendored.frontier_map_semantics.textgeo import body

CRITERIA_ORDER = [
    "COHERENCE_QUERY_LANG",
    "COHERENCE_QUERY_TERM",
    "PROJ_RANK",
    "PROJ_SPEARMAN",
    "PROJ_KNN10",
    "STRUCTURE_LARGEST",
    "STRUCTURE_SEP",
    "LABEL_CONTENT_FRACTION",
    "LABEL_JACCARD",
    "OUTLIER_VALIDITY",
    "RELATIONS",
]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _largest_share_both_definitions(bundle: dict[str, Any]) -> dict[str, Any]:
    """Largest-cluster share from BOTH the cluster 'size' field and
    len(member_ids), side by side. The 50-cap truncation of member_ids is
    flagged explicitly because on the served French bundle the two are
    0.7696 and 0.2304 against the frozen MEGA/STRUCTURE bar of 0.60.
    """
    decisions = bundle.get("decisions") or []
    clusters = bundle.get("clusters") or []
    n = max(1, len(decisions))
    if not clusters:
        return {
            "largest_share_size_field": 0.0,
            "largest_share_member_ids": 0.0,
            "largest_size_field": 0,
            "largest_member_ids_len": 0,
            "member_ids_capped_at_50": False,
            "max_member_ids_len": 0,
        }
    by_size = max(clusters, key=lambda c: int(c.get("size") or 0))
    by_members = max(clusters, key=lambda c: len(c.get("member_ids") or []))
    size_share = int(by_size.get("size") or 0) / n
    member_share = len(by_members.get("member_ids") or []) / n
    max_members = max(len(c.get("member_ids") or []) for c in clusters)
    capped = max_members >= 50
    return {
        "largest_share_size_field": float(size_share),
        "largest_share_member_ids": float(member_share),
        "largest_size_field": int(by_size.get("size") or 0),
        "largest_member_ids_len": len(by_members.get("member_ids") or []),
        "largest_cluster_id_size_field": int(by_size.get("cluster_id") or -1),
        "largest_cluster_id_member_ids": int(by_members.get("cluster_id") or -1),
        "member_ids_capped_at_50": bool(capped),
        "max_member_ids_len": int(max_members),
        "n_decisions": len(decisions),
        "note": (
            "The cluster 'size' field is the full membership count. member_ids is truncated "
            "at 50 in the shipped bundle, so len(member_ids) undercounts the dominant "
            "cluster on any cluster larger than 50. Both are reported; the frozen "
            "STRUCTURE_LARGEST bar applies to the size-field definition (what the gate "
            "renders as the cluster's displayed size)."
        ),
    }


def _dominant_cluster_context(bundle: dict[str, Any], query_language: str) -> dict[str, Any]:
    """Read-only context for the dominant cluster: size, language mix, counter
    rows contained, cluster label. Emitted as CONTEXT only, never as a verdict.
    (Placement/visibility is NOT scored by this charter.)"""
    decisions = bundle.get("decisions") or []
    clusters = bundle.get("clusters") or []
    if not clusters:
        return {}
    dom = max(clusters, key=lambda c: int(c.get("size") or 0))
    dom_cid = int(dom.get("cluster_id") or -1)
    members = [d for d in decisions if int(d.get("cluster_id") or -1) == dom_cid]
    n_m = max(1, len(members))
    lang_counts: dict[str, int] = {}
    for d in members:
        lang = str(d.get("language") or "null")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    counter_statuses = ("candidate-limiting", "candidate-contrary", "contrary_or_exception", "limiting")
    n_counter = sum(1 for d in members if d.get("counter_status") in counter_statuses)
    return {
        "cluster_id": dom_cid,
        "size_field": int(dom.get("size") or 0),
        "member_ids_len": len(dom.get("member_ids") or []),
        "label": str(dom.get("label") or ""),
        "language_mix": dict(sorted(lang_counts.items())),
        "n_query_language": lang_counts.get(query_language, 0),
        "share_query_language": lang_counts.get(query_language, 0) / n_m,
        "n_counter_rows_contained": n_counter,
        "context_only_note": (
            "Read-only context. Placement, rank and findability are NOT scored by this charter."
        ),
    }


def run_geometry_half(
    rules_path: str,
    packet_dir: str,
    bundle_sha256: dict[str, str],
    *,
    expected_rules_sha256: str,
) -> dict[str, Any]:
    """Score all three served bundles under the frozen geometry rule."""
    with open(rules_path, "rb") as f:
        rules_raw = f.read()
    rules_sha = hashlib.sha256(rules_raw).hexdigest()
    if rules_sha != expected_rules_sha256:
        raise ValueError(
            f"geometry rules sha256 mismatch: expected {expected_rules_sha256}, observed {rules_sha}"
        )
    rules_geom = json.loads(rules_raw.decode("utf-8"))

    # Per-bundle frozen rule blocks: query_language + query_term_lexicon
    geom_inputs = {e["bundle"]: e for e in rules_geom.get("inputs", [])}

    bundle_reports: list[dict[str, Any]] = []
    for qid, expected_sha in sorted(bundle_sha256.items()):
        path = os.path.join(packet_dir, "questions", f"{qid}.bundle.json")
        digest = sha256_file(path)
        if digest != expected_sha:
            raise ValueError(
                f"input sha256 drift for {path}: expected {expected_sha}, observed {digest}"
            )
        with open(path, "rb") as f:
            bundle = json.loads(f.read().decode("utf-8"))

        entry = geom_inputs.get(qid) or {}
        qlang = entry.get("query_language") or (
            "de" if qid.startswith("de-") else "fr" if qid.startswith("fr-") else "it"
        )
        lex = entry.get("query_term_lexicon") or rules_geom.get("query_term_lexicons", {}).get(qid, [])
        rules_bundle = {"query_language": qlang, "query_term_lexicon": list(lex)}

        decisions = bundle.get("decisions") or []
        texts = [body(d)[:6000] for d in decisions]
        if not any(t.strip() for t in texts):
            texts = [str(d.get("decision_id") or i) for i, d in enumerate(decisions)]
        vec, X = tfidf_of(texts)
        qtext = str(bundle.get("query", ""))
        qvec = vec.transform([qtext])

        V, detail = verdicts(bundle, rules_bundle, X, qvec)
        side, g_all, g_hyd = ablate(bundle, rules_bundle, X=X, qvec=qvec)

        # Strip wall-clock timing fields so two runs are byte-identical.
        # Timing is not a claim-bearing number under this charter; the frozen
        # budget note applies to alternatives the charter does not score here.
        for key in ("recompute_all_time_s", "hydrated_time_s"):
            if key in side:
                side[key] = None
        sbs = side.get("side_by_side") or {}
        for panel_name in ("all_rows", "hydrated_only", "shipped_fields"):
            panel = sbs.get(panel_name)
            if isinstance(panel, dict) and "elapsed" in panel:
                panel["elapsed"] = None

        n_pass = sum(1 for c in CRITERIA_ORDER if V[c]["pass"])
        overall = "PASS" if n_pass == len(CRITERIA_ORDER) else "FAIL"

        both_defs = _largest_share_both_definitions(bundle)
        dom_ctx = _dominant_cluster_context(bundle, qlang)

        bundle_reports.append(
            {
                "qid": qid,
                "sha256": digest,
                "sha256_matches_expected": digest == expected_sha,
                "n_decisions": len(decisions),
                "n_clusters": len(bundle.get("clusters") or []),
                "n_relations": len(bundle.get("relations") or []),
                "query": bundle.get("query", ""),
                "query_language": qlang,
                "criteria": {c: V[c] for c in CRITERIA_ORDER},
                "n_pass": n_pass,
                "n_criteria": len(CRITERIA_ORDER),
                "overall": overall,
                "largest_share_both_definitions": both_defs,
                "dominant_cluster_context": dom_ctx,
                "ablation": side,
                "detail": detail,
            }
        )

    n_pass_bundles = sum(1 for b in bundle_reports if b["overall"] == "PASS")
    verdict = "PASS" if n_pass_bundles == 3 else "FAIL"

    return {
        "schema": "frontier-served-packet-falsification/geometry-half/1",
        "rules_sha256": rules_sha,
        "rules_byte_identity_ok": rules_sha == expected_rules_sha256,
        "criteria_order": CRITERIA_ORDER,
        "n_bundles": len(bundle_reports),
        "n_bundles_pass": n_pass_bundles,
        "verdict": verdict,
        "bundles": bundle_reports,
    }
