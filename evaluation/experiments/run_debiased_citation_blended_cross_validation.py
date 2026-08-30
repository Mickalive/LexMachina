#!/usr/bin/env python3
"""
Evaluation Lane — Cross-validate debiased_citation_blended on Canonical Frozen Harness v3

BOUNDED QUESTION: Does the debiased_citation_blended representation from fractal-map
lane (cycles 12-14, validated with 14-benchmark suite, recommended for PRODUCTIZE)
pass the canonical frozen adversarial harness v3 benchmarks?

This is an independent cross-lane adversarial check:
- Cycle 14 validated on 1000 decisions with 14 benchmarks (different methodology)
- Frozen harness v3 evaluates on 1000/1200 decisions with canonical adversarial gates
  (LangDom, Jurist Pref, Jurivoc NMI, scale stability, fractal quality)

If debiased_citation_blended generalizes to the canonical benchmarks, the PRODUCTIZE
recommendation is strengthened. If not, the recommendation is falsified.

FROZEN SETUP:
- Harness: v3 (seed=42, config_hash=4323f833fa72366a)
- Corpus: 1000 decisions (fractal-map baseline, perfect subset of 1200-slice)
- Representation: debiased_citation_blended (768-dim, from fractal-map lane)
- Metadata: 1200-slice metadata filtered to 1000 fractal-map decisions

HYPOTHESIS: debiased_citation_blended will pass both adversarial gates on canonical
benchmarks, confirming the fractal-map lane's PRODUCTIZE recommendation.

BASELINE: cycle 14 report (LangDom=0.6406, citation_heritage_AUC=0.9102)

SUCCESS RULE (frozen before inspection):
- debiased_citation_blended PASSES both adversarial gates (LangDom < 0.85, JP > 0.5)
- Results consistent with cycle 14 within 0.05 tolerance
"""

import json
import sys
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter, defaultdict
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# PATHS
# ============================================================
REPO_ROOT = Path("/home/runner/work/LexMachina/LexMachina")
ACCEPTED_ROOT = Path("/tmp/lex_accepted")

# fractal-map lane accepted evidence
FM_BASELINE_META = ACCEPTED_ROOT / "fractal-map/results/fractal_map/baseline/metadata.json"
FM_DEBIASED_EMB = ACCEPTED_ROOT / "fractal-map/results/legal_distance/embeddings/debiased_citation_blended.npy"

# frozen harness v3 1200-slice metadata (has branch field)
FH_METADATA = ACCEPTED_ROOT / "legal-distance/legal_distance/results/v5/center_projected_full/metadata.json"

# Output
OUTPUT_DIR = REPO_ROOT / "evaluation/results/debiased_citation_blended_cross_validation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Frozen harness parameters
FROZEN_SEED = 42
FROZEN_CONFIG_HASH = "4323f833fa72366a"

ADVERSARIAL_THRESHOLDS = {
    "language_dominance": 0.85,
    "jurist_pairwise": 0.5,
    "langdom_target": 0.6,
    "jurist_pref_target": 0.7,
}

# Chamber-to-branch mapping (canonical, from frozen harness v3)
CHAMBER_TO_BRANCH = {
    "I. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "II. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "III. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "IV. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "I. Zivilrechtliche Abteilung": "zivilrecht",
    "II. Zivilrechtliche Abteilung": "zivilrecht",
    "I. Strafrechtliche Abteilung": "strafrecht",
    "II. Strafrechtliche Abteilung": "strafrecht",
    "II. sozialrechtliche Abteilung": "sozialversicherungsrecht",
    "IIe Cour de droit social": "sozialversicherungsrecht",
    "Ire Cour de droit public": "oeffentliches_recht",
    "IIe Cour de droit public": "oeffentliches_recht",
    "Ire Cour de droit civil": "zivilrecht",
    "IIe Cour de droit civil": "zivilrecht",
    "Ire Cour de droit pénal": "strafrecht",
    "IIe Cour de droit pénal": "strafrecht",
}


def assign_branch(chamber: str) -> str:
    if chamber in CHAMBER_TO_BRANCH:
        return CHAMBER_TO_BRANCH[chamber]
    chamber_lower = chamber.lower()
    if "öffentlich" in chamber_lower or "public" in chamber_lower:
        return "oeffentliches_recht"
    if "zivil" in chamber_lower or "civil" in chamber_lower:
        return "zivilrecht"
    if "straf" in chamber_lower or "pénal" in chamber_lower or "penal" in chamber_lower:
        return "strafrecht"
    if "sozial" in chamber_lower or "social" in chamber_lower:
        return "sozialversicherungsrecht"
    return "unknown"


# ============================================================
# DATA LOADING
# ============================================================
def load_data():
    """Load all data with proper alignment."""
    # Load fractal-map baseline metadata
    with open(FM_BASELINE_META) as f:
        fm_meta = json.load(f)
    fm_ids = set(m["decision_id"] for m in fm_meta)
    logger.info(f"Fractal-map baseline: {len(fm_meta)} decisions")

    # Load frozen harness 1200-slice metadata (has branch field)
    with open(FH_METADATA) as f:
        fh_meta_all = json.load(f)
    logger.info(f"Frozen harness 1200-slice: {len(fh_meta_all)} decisions")

    # Build lookup from decision_id to frozen harness metadata
    fh_lookup = {m["decision_id"]: m for m in fh_meta_all}

    # Load debiased_citation_blended embeddings
    embeddings = np.load(FM_DEBIASED_EMB)
    logger.info(f"Debiased citation blended shape: {embeddings.shape}")

    # Align: for each fractal-map decision, get the frozen harness metadata (with branch)
    aligned_meta = []
    aligned_indices = []
    for i, fm_m in enumerate(fm_meta):
        did = fm_m["decision_id"]
        if did in fh_lookup:
            fh_m = fh_lookup[did]
            aligned_meta.append({
                "decision_id": did,
                "language": fh_m.get("language", fm_m.get("language", "unknown")),
                "legal_area": fh_m.get("legal_area", fm_m.get("legal_area", "unknown")),
                "branch": fh_m.get("branch", assign_branch(fh_m.get("chamber", ""))),
                "chamber": fh_m.get("chamber", fm_m.get("chamber", "unknown")),
                "year": fh_m.get("year", fm_m.get("year", "unknown")),
            })
            aligned_indices.append(i)

    aligned_embeddings = embeddings[aligned_indices]
    logger.info(f"Aligned: {len(aligned_meta)} decisions, embeddings shape: {aligned_embeddings.shape}")

    # Verify branch coverage
    branches = [m["branch"] for m in aligned_meta]
    branch_counts = Counter(branches)
    logger.info(f"Branch distribution: {dict(branch_counts)}")

    languages = [m["language"] for m in aligned_meta]
    lang_counts = Counter(languages)
    logger.info(f"Language distribution: {dict(lang_counts)}")

    return aligned_embeddings, aligned_meta


# ============================================================
# ADVERSARIAL BENCHMARKS (canonical frozen harness v3)
# ============================================================
def adversarial_language_dominance(embeddings, metadata, k=20):
    from sklearn.neighbors import NearestNeighbors
    n = len(embeddings)
    k_actual = min(k + 1, n)
    nn_model = NearestNeighbors(n_neighbors=k_actual, metric='cosine')
    nn_model.fit(embeddings)
    _, indices = nn_model.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    dominance_rates = []
    for i, m in enumerate(metadata):
        lang = m.get('language', 'unknown')
        neighbor_langs = [metadata[n].get('language', 'unknown') for n in neighbors[i]]
        same_lang = sum(1 for l in neighbor_langs if l == lang)
        dominance_rates.append(same_lang / k)
    mean_dominance = float(np.mean(dominance_rates))
    return {
        'mean_language_dominance': mean_dominance,
        'std_language_dominance': float(np.std(dominance_rates)),
        'k': k,
        'threshold': 0.85,
        'status': 'PASS' if mean_dominance < 0.85 else 'FAIL',
    }


def simulate_pairwise_preference(embeddings, branches, languages, k=10):
    from sklearn.neighbors import NearestNeighbors
    n = len(branches)
    k_actual = min(k + 1, n)
    nn_model = NearestNeighbors(n_neighbors=k_actual, metric='cosine')
    nn_model.fit(embeddings)
    _, indices = nn_model.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    legal_relevant_count = 0
    language_artifact_count = 0
    both_count = 0
    neither_count = 0
    for i in range(n):
        branch_i = branches[i]
        lang_i = languages[i]
        neighbor_branches = branches[neighbors[i]]
        neighbor_langs = languages[neighbors[i]]
        has_legal_relevant = False
        has_language_artifact = False
        for nb, nl in zip(neighbor_branches, neighbor_langs):
            if nb == branch_i and nl != lang_i:
                has_legal_relevant = True
            if nb != branch_i and nl == lang_i:
                has_language_artifact = True
        if has_legal_relevant and has_language_artifact:
            both_count += 1
        elif has_legal_relevant:
            legal_relevant_count += 1
        elif has_language_artifact:
            language_artifact_count += 1
        else:
            neither_count += 1
    jurist_correct = legal_relevant_count + both_count
    legal_neighbor_rate = jurist_correct / n
    return {
        "status": "PASS" if legal_neighbor_rate > 0.5 else "FAIL",
        "total_decisions": n,
        "legal_relevant_only": legal_relevant_count,
        "language_artifact_only": language_artifact_count,
        "both_available": both_count,
        "neither_available": neither_count,
        "jurist_would_succeed_rate": round(legal_neighbor_rate, 4),
        "jurist_forced_wrong_rate": round(language_artifact_count / n, 4),
    }


def compute_jurivoc_alignment(embeddings, metadata):
    from sklearn.cluster import KMeans
    from sklearn.metrics import normalized_mutual_info_score
    branches = [m.get('branch', 'unknown') for m in metadata]
    legal_areas = [m.get('legal_area', 'unknown') for m in metadata]
    legal_areas = [la if la and la != 'null' else 'unknown' for la in legal_areas]
    kmeans_l0 = KMeans(n_clusters=4, random_state=FROZEN_SEED, n_init=10)
    labels_l0 = kmeans_l0.fit_predict(embeddings)
    nmi_l0 = normalized_mutual_info_score(branches, labels_l0)
    kmeans_l1 = KMeans(n_clusters=16, random_state=FROZEN_SEED, n_init=10)
    labels_l1 = kmeans_l1.fit_predict(embeddings)
    nmi_l1 = normalized_mutual_info_score(legal_areas, labels_l1)
    return {
        "level_0_nmi": float(nmi_l0),
        "level_1_nmi": float(nmi_l1),
        "status": "PASS" if nmi_l0 > 0.3 and nmi_l1 > 0.2 else "FAIL",
    }


def compute_scale_stability(embeddings):
    from sklearn.neighbors import NearestNeighbors
    n = embeddings.shape[0]
    np.random.seed(FROZEN_SEED)
    indices = np.arange(n)
    np.random.shuffle(indices)
    split_idx = int(0.8 * n)
    train_idx = indices[:split_idx]
    test_idx = indices[split_idx:]
    nn_full = NearestNeighbors(n_neighbors=min(11, n), metric='cosine')
    nn_full.fit(embeddings)
    _, full_neighbors = nn_full.kneighbors(embeddings)
    full_neighbors = full_neighbors[:, 1:]
    train_embeddings = embeddings[train_idx]
    train_to_full = {i: idx for i, idx in enumerate(train_idx)}
    nn_sub = NearestNeighbors(n_neighbors=min(11, len(train_embeddings)), metric='cosine')
    nn_sub.fit(train_embeddings)
    _, sub_neighbors = nn_sub.kneighbors(embeddings[test_idx])
    sub_neighbors = sub_neighbors[:, 1:]
    sub_neighbors_full = np.array([[train_to_full.get(n, n) for n in row] for row in sub_neighbors])
    overlaps = []
    for i, test_i in enumerate(test_idx):
        full_set = set(full_neighbors[test_i])
        sub_set = set(sub_neighbors_full[i])
        overlap = len(full_set & sub_set) / len(full_set) if full_set else 0
        overlaps.append(overlap)
    mean_overlap = float(np.mean(overlaps))
    return {
        "mean_neighbor_overlap": mean_overlap,
        "status": "PASS" if mean_overlap > 0.5 else "FAIL",
    }


def compute_fractal_quality(embeddings, metadata):
    """Compute fractal quality using Leiden clustering at multiple resolutions."""
    from sklearn.metrics import normalized_mutual_info_score
    try:
        import leidenalg
        import igraph as ig
        HAS_LEIDEN = True
    except ImportError:
        HAS_LEIDEN = False

    if not HAS_LEIDEN:
        # Fallback: use agglomerative clustering
        from sklearn.cluster import AgglomerativeClustering
        branches = [m.get('branch', 'unknown') for m in metadata]

        results = {}
        for n_clusters in [4, 8, 16]:
            clustering = AgglomerativeClustering(n_clusters=n_clusters)
            labels = clustering.fit_predict(embeddings)
            nmi = normalized_mutual_info_score(branches, labels)
            # Purity
            unique_clusters = set(labels)
            total_correct = 0
            total_count = 0
            for cid in unique_clusters:
                mask = labels == cid
                cluster_branches = [branches[j] for j in range(len(branches)) if mask[j]]
                if not cluster_branches:
                    continue
                majority = Counter(cluster_branches).most_common(1)[0][0]
                correct = sum(1 for b in cluster_branches if b == majority)
                total_correct += correct
                total_count += len(cluster_branches)
            purity = total_correct / total_count if total_count > 0 else 0
            results[n_clusters] = {"nmi": nmi, "purity": purity, "n_clusters": n_clusters}

        # Improvement rate: does fine clustering improve over coarse?
        coarse_purity = results.get(4, {}).get("purity", 0)
        fine_purity = results.get(16, {}).get("purity", 0)
        improvement_rate = (fine_purity - coarse_purity) / coarse_purity if coarse_purity > 0 else 0

        return {
            "method": "agglomerative_fallback",
            "results": results,
            "coarse_purity": coarse_purity,
            "fine_purity": fine_purity,
            "improvement_rate": improvement_rate,
            "status": "PASS" if improvement_rate > 0 else "FAIL",
        }

    # Leiden clustering
    from scipy.spatial.distance import cosine as cosine_dist
    from scipy.sparse import csr_matrix

    n = embeddings.shape[0]
    # Build kNN graph
    from sklearn.neighbors import NearestNeighbors
    k = min(30, n - 1)
    nn = NearestNeighbors(n_neighbors=k + 1, metric='cosine')
    nn.fit(embeddings)
    distances, indices = nn.kneighbors(embeddings)

    # Build sparse graph
    rows, cols, vals = [], [], []
    for i in range(n):
        for j_idx in range(1, k + 1):  # skip self
            j = indices[i, j_idx]
            rows.append(i)
            cols.append(j)
            vals.append(1.0 - distances[i, j_idx])  # convert cosine distance to similarity
    graph = csr_matrix((vals, (rows, cols)), shape=(n, n))
    graph = (graph + graph.T) / 2  # symmetrize

    ig_graph = ig.Graph.Weighted_Adjacency(graph, mode="undirected")

    branches = [m.get('branch', 'unknown') for m in metadata]

    resolutions = [0.5, 1.0, 3.0]
    results = {}
    for res in resolutions:
        partition = leidenalg.find_partition(
            ig_graph, leidenalg.RBConfigurationVertexPartition,
            resolution_parameter=res, random_state=FROZEN_SEED
        )
        labels = np.array(partition.membership)
        nmi = normalized_mutual_info_score(branches, labels)
        # Purity
        unique_clusters = set(labels)
        total_correct = 0
        total_count = 0
        for cid in unique_clusters:
            mask = labels == cid
            cluster_branches = [branches[j] for j in range(len(branches)) if mask[j]]
            if not cluster_branches:
                continue
            majority = Counter(cluster_branches).most_common(1)[0][0]
            correct = sum(1 for b in cluster_branches if b == majority)
            total_correct += correct
            total_count += len(cluster_branches)
        purity = total_correct / total_count if total_count > 0 else 0
        results[res] = {
            "nmi": nmi, "purity": purity,
            "n_clusters": len(unique_clusters)
        }

    coarse_purity = results.get(0.5, {}).get("purity", 0)
    fine_purity = results.get(3.0, {}).get("purity", 0)
    improvement_rate = (fine_purity - coarse_purity) / coarse_purity if coarse_purity > 0 else 0

    return {
        "method": "leiden",
        "results": results,
        "coarse_purity": coarse_purity,
        "fine_purity": fine_purity,
        "improvement_rate": improvement_rate,
        "status": "PASS" if improvement_rate > 0 else "FAIL",
    }


# ============================================================
# MAIN
# ============================================================
def main():
    run_id = f"debiased_cb_crossval_{int(time.time())}"
    logger.info(f"Starting cross-validation: {run_id}")
    start_time = time.time()

    # Load data
    embeddings, metadata = load_data()
    branches = np.array([m["branch"] for m in metadata])
    languages = np.array([m["language"] for m in metadata])

    # Run adversarial benchmarks
    logger.info("\n--- Adversarial Language Dominance ---")
    lang_dom = adversarial_language_dominance(embeddings, metadata, k=20)
    logger.info(f"  LangDom: {lang_dom['mean_language_dominance']:.4f} ({lang_dom['status']})")

    logger.info("\n--- Jurist Pairwise Preference ---")
    jurist_pref = simulate_pairwise_preference(embeddings, branches, languages, k=10)
    logger.info(f"  Jurist: {jurist_pref['jurist_would_succeed_rate']:.4f} ({jurist_pref['status']})")

    both_pass = lang_dom['status'] == 'PASS' and jurist_pref['status'] == 'PASS'
    logger.info(f"  Both gates: {'PASS' if both_pass else 'FAIL'}")

    # Run additional benchmarks
    logger.info("\n--- Jurivoc Alignment ---")
    jurivoc = compute_jurivoc_alignment(embeddings, metadata)
    logger.info(f"  L0 NMI: {jurivoc['level_0_nmi']:.4f}, L1 NMI: {jurivoc['level_1_nmi']:.4f} ({jurivoc['status']})")

    logger.info("\n--- Scale Stability ---")
    scale = compute_scale_stability(embeddings)
    logger.info(f"  Mean overlap: {scale['mean_neighbor_overlap']:.4f} ({scale['status']})")

    logger.info("\n--- Fractal Quality ---")
    fractal = compute_fractal_quality(embeddings, metadata)
    logger.info(f"  Coarse purity: {fractal['coarse_purity']:.4f}")
    logger.info(f"  Fine purity: {fractal['fine_purity']:.4f}")
    logger.info(f"  Improvement rate: {fractal['improvement_rate']:.4f} ({fractal['status']})")

    # Cross-language retrieval
    logger.info("\n--- Cross-Language Retrieval ---")
    from sklearn.neighbors import NearestNeighbors
    k_cross = min(10, len(embeddings) - 1)
    nn_model = NearestNeighbors(n_neighbors=k_cross + 1, metric='cosine')
    nn_model.fit(embeddings)
    _, indices = nn_model.kneighbors(embeddings)
    cross_lang_hits = 0
    total_queries = 0
    for i in range(len(metadata)):
        lang_i = languages[i]
        branch_i = branches[i]
        # Find decisions in same branch but different language
        same_branch_diff_lang = [
            j for j in range(len(metadata))
            if j != i and branches[j] == branch_i and languages[j] != lang_i
        ]
        if not same_branch_diff_lang:
            continue
        total_queries += 1
        neighbor_set = set(indices[i, 1:])
        if any(j in neighbor_set for j in same_branch_diff_lang):
            cross_lang_hits += 1
    cross_lang_recall = cross_lang_hits / total_queries if total_queries > 0 else 0
    logger.info(f"  Cross-lang recall@{k_cross}: {cross_lang_recall:.4f} (threshold: 0.2)")

    # Compile results
    duration = time.time() - start_time
    results = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "representation": "debiased_citation_blended",
        "source_lane": "fractal-map",
        "source_run": "cycle_14_productize_recommendation",
        "evaluation_framework": "frozen_harness_v3",
        "frozen_harness": {
            "seed": FROZEN_SEED,
            "config_hash": FROZEN_CONFIG_HASH,
        },
        "corpus": f"{len(metadata)} decisions (fractal-map baseline, subset of 1200-slice)",
        "embedding_dimension": int(embeddings.shape[1]),
        "results": {
            "adversarial": {
                "language_dominance": lang_dom,
                "jurist_pairwise_preference": jurist_pref,
                "both_pass": both_pass,
                "language_dominance_score": lang_dom['mean_language_dominance'],
                "jurist_preference_rate": jurist_pref['jurist_would_succeed_rate'],
            },
            "jurivoc": jurivoc,
            "scale_stability": scale,
            "fractal_quality": fractal,
            "cross_lang_recall": {
                "recall_at_k": cross_lang_recall,
                "k": k_cross,
                "total_queries": total_queries,
                "status": "PASS" if cross_lang_recall >= 0.2 else "FAIL",
            },
        },
        "verdict": "PASS" if both_pass else "FAIL",
        "duration_seconds": round(duration, 2),
    }

    # Save results
    output_path = OUTPUT_DIR / f"{run_id}_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\nResults saved to {output_path}")

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("CROSS-VALIDATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Representation: debiased_citation_blended (768-dim)")
    logger.info(f"Source: fractal-map lane cycle 14 PRODUCTIZE recommendation")
    logger.info(f"Evaluation: canonical frozen harness v3 benchmarks")
    logger.info(f"")
    logger.info(f"ADVERSARIAL GATES:")
    logger.info(f"  Language Dominance: {lang_dom['mean_language_dominance']:.4f} < 0.85? {'PASS' if lang_dom['status'] == 'PASS' else 'FAIL'}")
    logger.info(f"  Jurist Preference:  {jurist_pref['jurist_would_succeed_rate']:.4f} > 0.50? {'PASS' if jurist_pref['status'] == 'PASS' else 'FAIL'}")
    logger.info(f"  Both Gates: {'PASS' if both_pass else 'FAIL'}")
    logger.info(f"")
    logger.info(f"ADDITIONAL BENCHMARKS:")
    logger.info(f"  Jurivoc L0 NMI: {jurivoc['level_0_nmi']:.4f} (> 0.3? {'PASS' if jurivoc['level_0_nmi'] > 0.3 else 'FAIL'})")
    logger.info(f"  Scale Stability: {scale['mean_neighbor_overlap']:.4f} (> 0.5? {'PASS' if scale['status'] == 'PASS' else 'FAIL'})")
    logger.info(f"  Fractal Improvement: {fractal['improvement_rate']:.4f} (> 0? {'PASS' if fractal['status'] == 'PASS' else 'FAIL'})")
    logger.info(f"  Cross-lang Recall: {cross_lang_recall:.4f} (> 0.2? {'PASS' if cross_lang_recall >= 0.2 else 'FAIL'})")
    logger.info(f"")
    logger.info(f"VERDICT: {results['verdict']}")
    logger.info(f"Duration: {duration:.1f}s")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    results = main()
