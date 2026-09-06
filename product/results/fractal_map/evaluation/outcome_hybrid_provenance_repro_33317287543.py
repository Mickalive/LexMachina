#!/usr/bin/env python3
"""
Freeze-before-inspection provenance experiment for fractal-map run 33317287543.

Question:
  Can the accepted 1200-decision 2D outcome-hybrid embedding cache
  (/tmp/lex_accepted/legal-distance/legal_distance/results/v7/outcome_cited_hybrids/*.npy)
  reproduce the existing 1000-decision fractal-map cluster labels for the
  two BEST outcome-hybrid modes (cited_decisions_tfidf_outcome_hybrid_0.5/0.7)?

Why it matters (product capability):
  The fractal-map lane deliverable is BLOCKED on corpus lane for 192k scaling.
  The only actionable, un-blocked readiness path is a parameterized builder that
  can scale these BEST modes to full corpus. For such a builder to be trustworthy,
  its source embedding must reproduce (or be shown NOT to reproduce) the validated
  1000-decision map labels. This experiment freezes that question BEFORE inspecting
  the outcome, per evaluation doctrine.

Hypothesis (H0/aligned):  The 1200-decision cache, sliced to the first 1000 rows
  (assuming alignment with the 1000-decision fractal baseline metadata order),
  reproduces the stored map labels at resolution 1.0 for the outcome-hybrid-0.7 mode.

Metric / success rule:
  - Reproduce cluster labels via Leiden (k=15, seed=42) on the sliced embedding.
  - Compare against stored labels using cluster-matching purity:
        matched_purity = max over permutations... use Hungarian-like best-per-cluster
        measure: for each stored cluster, fraction of its members sharing the
        dominant reproduced label (mean over clusters).
  - Threshold: matched_purity >= 0.95 => REPRODUCIBLE; 0.7-0.95 => PARTIAL;
        < 0.7 => NOT-REPRODUCIBLE-from-cache.

Frozen BEFORE running: see above.
"""
import json
import numpy as np
from pathlib import Path
from collections import Counter

MODE = "cited_decisions_tfidf_outcome_hybrid_0.7"
CACHE_PATH = f"/tmp/lex_accepted/legal-distance/legal_distance/results/v7/outcome_cited_hybrids/{MODE}.npy"
LABELS_RES1_PATH = f"results/fractal_map/legal_distance_modes/{MODE}/labels_res_1.0.npy"
N_DECISIONS = 1000
K = 15
SEED = 42
MATCH_THRESHOLD = 0.95


def leiden_clustering(embeddings, resolution=1.0, k=K, seed=SEED):
    import igraph as ig
    import leidenalg
    from sklearn.neighbors import kneighbors_graph
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    k_actual = min(k, len(embeddings) - 1)
    graph = kneighbors_graph(normalized, n_neighbors=k_actual, metric='euclidean',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    sources, targets = graph.nonzero()
    weights = graph.data
    edges = list(zip(sources.tolist(), targets.tolist()))
    g = ig.Graph()
    g.add_vertices(graph.shape[0])
    g.add_edges(edges)
    g.es['weight'] = weights.tolist()
    partition = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        weights='weight', resolution_parameter=resolution, seed=seed)
    return np.array(partition.membership)


def cluster_matched_purity(stored, reproduced):
    """For each stored cluster, fraction of members sharing the dominant reproduced label."""
    stored_uniq = np.unique(stored)
    purities = []
    for c in stored_uniq:
        mask = stored == c
        if mask.sum() == 0:
            continue
        sub = reproduced[mask]
        dominant = Counter(sub.tolist()).most_common(1)[0][1]
        purities.append(dominant / len(sub))
    return float(np.mean(purities))


def main():
    cache = np.load(CACHE_PATH)
    stored = np.load(LABELS_RES1_PATH)
    result = {
        "run_id": "outcome_hybrid_provenance_33317287543",
        "github_run": "33317287543",
        "mode": MODE,
        "frozen_before_inspection": True,
        "hypothesis": "1200-decision cache sliced to 1000 rows reproduces stored res_1.0 labels",
        "success_rule": f"matched_purity >= {MATCH_THRESHOLD}",
        "cache_shape": list(cache.shape),
        "stored_shape": list(stored.shape),
    }
    if cache.shape[0] != N_DECISIONS and stored.shape[0] != N_DECISIONS:
        result["verdict"] = "INVALID"
        result["reason"] = "cache or stored labels are not 1000-decision"
        return result

    sliced = cache[:N_DECISIONS]
    reproduced = leiden_clustering(sliced, resolution=1.0)
    n_repro = len(set(reproduced.tolist()))
    n_stored = len(set(stored.tolist()))

    # Case A: sliced-first-1000
    purity_A = cluster_matched_purity(stored, reproduced)

    # Case B: use full 1200 (cluster purity on first 1000 entries only)
    if cache.shape[0] == 1200:
        reproduced_full = leiden_clustering(cache, resolution=1.0)
        purity_B = cluster_matched_purity(stored, reproduced_full[:1000])
    else:
        purity_B = None

    result["sliced_first1000"] = {
        "n_clusters_reproduced": n_repro,
        "n_clusters_stored": n_stored,
        "matched_purity": purity_A,
    }
    result["full1200_first1000"] = {
        "matched_purity": purity_B,
    }
    verdict = "REPRODUCIBLE" if (purity_A >= MATCH_THRESHOLD and purity_A is not None) else (
        "PARTIAL" if purity_A and purity_A >= 0.7 else "NOT-REPRODUCIBLE-from-cache")
    result["verdict"] = verdict
    return result


if __name__ == "__main__":
    out = main()
    print(json.dumps(out, indent=2))
