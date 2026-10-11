"""
Query Bundle Adapter for frontier-query-map-ui

Adapts query_result_bundle (from product/query/pipeline.py) to the
visualization format expected by the WebGL/Canvas renderer.

This is the SEAM between the query pipeline and the visual map.
No dependency on global 174k alignment or global hierarchy.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

# Allow `python3 frontier/frontier-query-map-ui/src/<script>.py` and
# `import query_bundle_adapter` from the tests without an install step.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from product.query.bundle import validate_bundle, bundle_summary


# Color palette for clusters (matches existing LexMachina UI)
CLUSTER_COLORS = [
    '#7c8aff', '#ff6b6b', '#51cf66', '#ffd43b', '#cc5de8',
    '#20c997', '#ff922b', '#4dabf7', '#e599f7', '#69db7c',
    '#fcc419', '#ff8787', '#748ffc', '#63e6be', '#da77f2',
    '#a9e34b', '#ffa94d', '#74c0fc', '#b2f2bb', '#f783ac',
]

LANG_COLORS = {
    'de': '#4dabf7',
    'fr': '#ffd43b',
    'it': '#51cf66',
    'unknown': '#666',
}

COUNTER_STATUS_COLORS = {
    'cited': '#ffd43b',           # gold - cited in answer
    'candidate-limiting': '#c00',  # red - limiting authority
    'candidate-distinguishing': '#ff922b',  # orange - distinguishing
    'candidate-contrary': '#c00',  # red - contrary
    'candidate-exception': '#ff6b6b',  # light red - exception
    'none': '#7c8aff',             # default cluster color
    'supporting-candidate': '#7c8aff',  # default cluster color
    'context': '#7c8aff',          # default cluster color
}

COUNTER_STATUS_LABELS = {
    'cited': 'Cited in Answer',
    'candidate-limiting': 'Limiting Authority',
    'candidate-distinguishing': 'Distinguishing',
    'candidate-contrary': 'Contrary Authority',
    'candidate-exception': 'Exception',
    'none': 'Context',
    'supporting-candidate': 'Supporting',
    'context': 'Context',
}


def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    """Convert hex color to RGBA tuple (0-1 range)."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c * 2 for c in hex_color])
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b, alpha)


def adapt_bundle_to_visualization(bundle: dict) -> dict:
    """
    Convert a query_result_bundle to the visualization format.
    
    Input: query_result_bundle with decisions, clusters, relations, answer, provenance
    Output: visualization-ready data with positions, clusters, relations, metadata
    
    This is the CORE ADAPTER - no global 174k dependencies.
    """
    errors = validate_bundle(bundle)
    if errors:
        raise ValueError(f"Invalid bundle: {errors}")

    decisions = bundle["decisions"]
    clusters = bundle["clusters"]
    relations = bundle.get("relations", [])
    answer = bundle.get("answer", {})
    provenance = bundle.get("provenance", {})

    # Build cluster lookup
    cluster_by_id = {c["cluster_id"]: c for c in clusters}
    n_clusters = len(clusters)

    # Assign colors to clusters
    cluster_colors = {}
    cluster_labels = {}
    for i, c in enumerate(clusters):
        cid = c["cluster_id"]
        cluster_colors[cid] = CLUSTER_COLORS[i % len(CLUSTER_COLORS)]
        cluster_labels[cid] = c.get("label", f"Cluster {cid}")

    # Build adapted decisions with visualization fields
    adapted_decisions = []
    for d in decisions:
        cid = d.get("cluster_id", 0)
        counter_status = d.get("counter_status", "none")
        is_outlier = d.get("is_outlier", False)

        # Get counter status display info
        counter_color = COUNTER_STATUS_COLORS.get(counter_status, CLUSTER_COLORS[cid % len(CLUSTER_COLORS)])
        counter_label = COUNTER_STATUS_LABELS.get(counter_status, counter_status)

        adapted = {
            "decision_id": d["decision_id"],
            "x": d["x"],
            "y": d["y"],
            "cluster_id": cid,
            "cluster_label": cluster_labels.get(cid, f"Cluster {cid}"),
            "cluster_color": cluster_colors.get(cid, CLUSTER_COLORS[cid % len(CLUSTER_COLORS)]),
            "language": d.get("language", "unknown"),
            "lang_color": LANG_COLORS.get(d.get("language", "unknown"), LANG_COLORS["unknown"]),
            "rank": d.get("rank", 0),
            "score": d.get("score", 0.0),
            "snippet": d.get("snippet", ""),
            "counter_status": counter_status,
            "counter_label": counter_label,
            "counter_color": counter_color,
            "counter_evidence": d.get("counter_evidence", ""),
            "counter_markers": d.get("counter_markers", []),
            "is_outlier": is_outlier,
            "outlier_alpha": 0.55 if is_outlier else 0.9,
            "canonical_url": d.get("canonical_url", ""),
            "citation": d.get("citation", []),
            "court": d.get("court", ""),
            "decision_date": d.get("decision_date", ""),
            "docket_number": d.get("docket_number", ""),
            "provenance": d.get("provenance", ""),
            # Visual properties
            "radius": 7 if counter_status == "cited" else (5 if not is_outlier else 5),
            "stroke_width": 2.5 if counter_status in ("candidate-limiting", "candidate-contrary", "candidate-distinguishing", "candidate-exception") else (2 if counter_status == "cited" else 0),
            "stroke_color": counter_color if counter_status != "none" else "transparent",
            "stroke_dash": [2, 2] if is_outlier else [],
        }
        adapted_decisions.append(adapted)

    # Adapt clusters with visualization info
    adapted_clusters = []
    for c in clusters:
        cid = c["cluster_id"]
        member_ids = c.get("member_ids", [])
        outlier_count = sum(1 for d in decisions if d.get("cluster_id") == cid and d.get("is_outlier", False))
        counter_count = sum(1 for d in decisions if d.get("cluster_id") == cid and d.get("counter_status", "none") not in ("none", "cited", "supporting-candidate", "context"))
        cited_count = sum(1 for d in decisions if d.get("cluster_id") == cid and d.get("counter_status") == "cited")

        adapted_clusters.append({
            "cluster_id": cid,
            "label": cluster_labels.get(cid, f"Cluster {cid}"),
            "size": c.get("size", len(member_ids)),
            "color": cluster_colors.get(cid, CLUSTER_COLORS[cid % len(CLUSTER_COLORS)]),
            "member_ids": member_ids[:50],  # cap for UI
            "outlier_count": outlier_count,
            "counter_count": counter_count,
            "cited_count": cited_count,
            "centroid_x": sum(d["x"] for d in decisions if d.get("cluster_id") == cid) / max(1, sum(1 for d in decisions if d.get("cluster_id") == cid)),
            "centroid_y": sum(d["y"] for d in decisions if d.get("cluster_id") == cid) / max(1, sum(1 for d in decisions if d.get("cluster_id") == cid)),
        })

    # Adapt relations for on-demand edge rendering
    adapted_relations = []
    for r in relations:
        adapted_relations.append({
            "source": r["source"],
            "target": r["target"],
            "kind": r.get("kind", "shared_citation"),
            "shared": r.get("shared", [])[:5],
            "shared_count": len(r.get("shared", [])),
        })

    # Answer info for UI.  `cited_decision_ids` must stay a JSON-serialisable
    # list: this payload is written to disk and served over HTTP.
    answer_info = {
        "prose": answer.get("prose", ""),
        "statements": answer.get("statements", []),
        "cited_decision_ids": sorted(set(answer.get("cited_decision_ids", []))),
        "method": answer.get("method", ""),
    }

    # Provenance summary
    prov_summary = {
        "corpus": provenance.get("corpus", {}),
        "answer_method": provenance.get("answer_method", ""),
        "counter": provenance.get("counter", {}),
        "latency_seconds": provenance.get("latency_seconds", 0.0),
    }

    # Compute bounds for fit-to-data
    xs = [d["x"] for d in adapted_decisions]
    ys = [d["y"] for d in adapted_decisions]
    bounds = {
        "x_min": min(xs) if xs else -1,
        "x_max": max(xs) if xs else 1,
        "y_min": min(ys) if ys else -1,
        "y_max": max(ys) if ys else 1,
    }
    # Add padding
    x_pad = (bounds["x_max"] - bounds["x_min"]) * 0.1 or 0.2
    y_pad = (bounds["y_max"] - bounds["y_min"]) * 0.1 or 0.2
    bounds["x_min"] -= x_pad
    bounds["x_max"] += x_pad
    bounds["y_min"] -= y_pad
    bounds["y_max"] += y_pad

    return {
        "bundle_version": bundle.get("bundle_version", "1.0"),
        "query": bundle.get("query", ""),
        "query_variants": bundle.get("query_variants", []),
        "decisions": adapted_decisions,
        "clusters": adapted_clusters,
        "relations": adapted_relations,
        "answer": answer_info,
        "provenance": prov_summary,
        "bounds": bounds,
        "summary": bundle_summary(bundle),
        "n_decisions": len(adapted_decisions),
        "n_clusters": len(adapted_clusters),
        "n_relations": len(adapted_relations),
        "n_counter": sum(1 for d in adapted_decisions if d["counter_status"] not in ("none", "cited", "supporting-candidate", "context")),
        "n_cited": sum(1 for d in adapted_decisions if d["counter_status"] == "cited"),
        "n_outliers": sum(1 for d in adapted_decisions if d["is_outlier"]),
        "languages": list(set(d["language"] for d in adapted_decisions)),
    }


def load_bundle_from_file(path: str | Path) -> dict:
    """Load a query_result_bundle from a JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_visualization_data(data: dict, path: str | Path) -> None:
    """Save adapted visualization data to JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_fixture_bundle(query: str = "Kündigung Mietvertrag Mietrecht", top_n: int = 150) -> dict:
    """
    Create a test fixture bundle by running the product query pipeline over the
    vendored 100-decision OpenCaseLaw fixture (offline-capable).
    """
    from product_compat import run_query as compat_run_query
    bundle, _report = compat_run_query(query, top_n=top_n)
    return bundle


if __name__ == "__main__":
    # Quick test: run pipeline and adapt
    print("Creating test fixture bundle...")
    bundle = create_fixture_bundle()
    print(f"Bundle: {bundle_summary(bundle)}")
    
    print("\nAdapting to visualization format...")
    viz = adapt_bundle_to_visualization(bundle)
    print(f"Visualization: {viz['n_decisions']} decisions, {viz['n_clusters']} clusters, {viz['n_relations']} relations")
    print(f"Counter authorities: {viz['n_counter']}, Cited: {viz['n_cited']}, Outliers: {viz['n_outliers']}")
    print(f"Languages: {viz['languages']}")
    print(f"Bounds: {viz['bounds']}")
    
    # Save for UI testing
    out_path = Path(__file__).parent.parent / "fixtures" / "test_bundle_viz.json"
    save_visualization_data(viz, out_path)
    print(f"\nSaved visualization data to {out_path}")