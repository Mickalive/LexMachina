"""Half (b): GEOMETRY, independently recomputed with the frozen 11 criteria.

Applies the ACCEPTED vendored geometry_gate to each SHIPPED post-rerank
rebuilt bundle and counts per-criterion passes against the 11 frozen
criteria; compares against the incumbent de 6 / fr 5 / it 5 (never asserts).
Re-measures the size-based mega-cluster disclosure independently.
"""
from __future__ import annotations

import json
from pathlib import Path

from .paths import QIDS, bootstrap_vendored_instruments

bootstrap_vendored_instruments()

from evaluation.frozen_bars import geometry_gate  # noqa: E402

MEGA_CLUSTER_BAR = 0.5
INCUMBENT_COUNTS = dict(geometry_gate.INCUMBENT_COUNTS)
CRITERIA_ORDER = list(geometry_gate.CRITERIA_ORDER)
RULES_GEOMETRY_PATH = Path(geometry_gate.__file__).resolve().parent / "RULES_GEOMETRY.json"


def size_based_mega_cluster(bundle: dict) -> dict:
    """Size-based (cluster['size'] / n_decisions) mega-cluster disclosure.

    Re-measured from the shipped bundle's own cluster 'size' fields — the
    same definition the rebuilt packet's disclosure wiring uses; NEVER the
    capped member_ids length.
    """
    decisions = bundle.get("decisions") or []
    n = len(decisions)
    clusters = bundle.get("clusters") or []
    sizes = [int(c.get("size") or 0) for c in clusters]
    largest = max(sizes) if sizes else 0
    share = (largest / n) if n else None
    member_ids_share = None
    if clusters:
        biggest = max(clusters, key=lambda c: int(c.get("size") or 0))
        member_ids_share = (len(biggest.get("member_ids") or []) / n) if n else None
    fired = bool(share is not None and share >= MEGA_CLUSTER_BAR)
    return {
        "definition": "largest_cluster_size / n_decisions (size-based, cluster['size'])",
        "bar": MEGA_CLUSTER_BAR,
        "n_decisions": n,
        "n_clusters": len(clusters),
        "largest_cluster_size": largest,
        "largest_cluster_share": share,
        "largest_cluster_member_ids_share": member_ids_share,
        "size_based_not_member_ids": True,
        "fired": fired,
        "threshold_edited": False,
    }


def measure(packet_questions: Path) -> dict:
    rules = geometry_gate.load_frozen_geometry_rules(str(RULES_GEOMETRY_PATH))
    bundles: dict[str, dict] = {}
    mega: dict[str, dict] = {}
    for qid in QIDS:
        path = packet_questions / f"{qid}.bundle.json"
        bundle = json.loads(path.read_text(encoding="utf-8"))
        bundles[qid] = bundle
        mega[qid] = size_based_mega_cluster(bundle)
    packet = geometry_gate.score_packet(bundles, rules)
    per_bundle: dict[str, dict] = {}
    for qid in QIDS:
        cell = packet["per_bundle"][qid]
        criteria = cell.get("criteria") or {}
        per_criterion = {}
        for name in CRITERIA_ORDER:
            c = criteria.get(name) or {}
            per_criterion[name] = {
                "pass": bool(c.get("pass")),
                "value": c.get("value"),
                "bar": c.get("bar"),
                "degenerate": c.get("degenerate"),
            }
        n_pass = cell["n_pass"]
        incumbent = INCUMBENT_COUNTS.get(qid)
        per_bundle[qid] = {
            "qid": qid,
            "bundle_state": "post_rerank_product_bundle",
            "n_criteria": cell.get("n_criteria", len(CRITERIA_ORDER)),
            "n_pass": n_pass,
            "overall_absolute": "GEOMETRY_SOUND" if n_pass == len(CRITERIA_ORDER) else "GEOMETRY_UNSOUND",
            "per_criterion": per_criterion,
            "incumbent_n_pass": incumbent,
            "delta_vs_incumbent": (n_pass - incumbent) if incumbent is not None else None,
            "regressed_vs_incumbent": bool(incumbent is not None and n_pass < incumbent),
            "mega_cluster_disclosure": mega[qid],
            "threshold_re_derived": False,
        }
    counts = {qid: per_bundle[qid]["n_pass"] for qid in QIDS}
    return {
        "half": "b_geometry",
        "rules_geometry_sha256": geometry_gate.EXPECTED_RULES_SHA256,
        "criteria_order": CRITERIA_ORDER,
        "per_bundle": per_bundle,
        "criterion_counts": counts,
        "incumbent_counts": INCUMBENT_COUNTS,
        "delta_vs_incumbent": {qid: per_bundle[qid]["delta_vs_incumbent"] for qid in QIDS},
        "n_bundles_pass_all_11": packet.get("n_bundles_pass_all_11"),
        "absolute_status": packet.get("absolute_status"),
        "absolute_enforced_as_build_blocker": packet.get("absolute_enforced_as_build_blocker", False),
        "regression": {
            "lineage": set(counts) == set(INCUMBENT_COUNTS),
            "incumbent_counts": INCUMBENT_COUNTS,
            "observed_counts": counts,
            "regressed_qids": [qid for qid in QIDS if per_bundle[qid]["regressed_vs_incumbent"]],
            "regression_verdict": packet.get("regression_verdict"),
            "gate_blocks_build": packet.get("gate_blocks_build", False),
            "not_applicable_is_not_a_pass": True,
        },
        "mega_cluster_disclosure_fires": {qid: mega[qid]["fired"] for qid in QIDS},
        "mega_cluster_fires_on_any_rebuilt_bundle": any(mega[qid]["fired"] for qid in QIDS),
        "threshold_re_derived": False,
    }
