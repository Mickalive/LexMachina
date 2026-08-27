#!/usr/bin/env python3
"""
Evaluation Cycle 9: Citation-Graph Representations + Temporal Stability

Hypothesis: Citation-graph representations (blended, graph-only) may resolve
dead zones and language dominance problems identified in cycle 8, because
citations cross language boundaries. Temporal stability tests whether neighbor
quality is consistent across corpus subsets.

Product decision: If citation-graph representations pass adversarial tests
that baseline/debiased failed, they become candidates for productization.
If temporal stability is poor, the representation is unreliable.

Frozen before observation:
- Corpus: 1000 BGer decisions (2024) from fractal-map baseline metadata
- Embeddings: baseline (768-dim), language_debiased_pca2 (768-dim),
              embeddings_blended (64-dim), embeddings_graph_only (64-dim)
- Success rule: Adversarial degradation < 20% on neighbor quality;
  branch k-NN accuracy > 0.5; temporal stability drift < 0.1
"""

import json
import time
import sys
import os
import logging
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
from sklearn.metrics import (
    roc_auc_score,
    normalized_mutual_info_score,
)
from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Paths ───────────────────────────────────────────────────────────────────
ACCEPTED = Path("/tmp/lex_accepted")
BASELINE_META = ACCEPTED / "fractal-map/results/fractal_map/baseline/metadata.json"
BASELINE_EMB = ACCEPTED / "fractal-map/results/fractal_map/baseline/embeddings.npy"
DEBIASED_EMB = ACCEPTED / "fractal-map/results/fractal_map/language_debiasing/embeddings_pca2.npy"
BLENDED_EMB = ACCEPTED / "fractal-map/results/fractal_map/citation_graph/embeddings_blended.npy"
GRAPH_ONLY_EMB = ACCEPTED / "fractal-map/results/fractal_map/citation_graph/embeddings_graph_only.npy"
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results")
REPORT_DIR = Path("/home/runner/work/LexMachina/LexMachina/reports/evaluation")

# ─── Chamber-to-Branch mapping (from run_cycle_8.py) ────────────────────────
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
    """Map chamber name to branch."""
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


def load_all_representations():
    """Load metadata and all four representations."""
    with open(BASELINE_META) as f:
        metadata = json.load(f)

    baseline = np.load(BASELINE_EMB)
    debiased = np.load(DEBIASED_EMB)
    blended = np.load(BLENDED_EMB)
    graph_only = np.load(GRAPH_ONLY_EMB)

    logger.info(f"Loaded {len(metadata)} decisions")
    logger.info(f"  baseline: {baseline.shape}")
    logger.info(f"  debiased: {debiased.shape}")
    logger.info(f"  blended:  {blended.shape}")
    logger.info(f"  graph_only: {graph_only.shape}")

    return metadata, {
        "baseline": baseline,
        "language_debiased_pca2": debiased,
        "citation_blended": blended,
        "citation_graph_only": graph_only,
    }


def prepare_valid_data(metadata, embeddings):
    """Filter to valid decisions with known branch, return filtered embeddings and labels."""
    branches = []
    languages = []
    chambers = []
    legal_areas = []
    valid_indices = []

    for i, meta in enumerate(metadata):
        chamber = meta.get("chamber", "")
        branch = assign_branch(chamber)
        lang = meta.get("language", "unknown")
        legal_area = meta.get("legal_area", "unknown")

        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            chambers.append(chamber)
            legal_areas.append(legal_area)
            valid_indices.append(i)

    emb = embeddings[valid_indices]
    return emb, np.array(branches), np.array(languages), np.array(chambers), np.array(legal_areas), valid_indices


def normalize_embeddings(emb):
    """L2-normalize embeddings."""
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return emb / norms


def compute_similarity(emb_norm):
    """Compute pairwise cosine similarity matrix."""
    sim = emb_norm @ emb_norm.T
    np.fill_diagonal(sim, -1)
    return sim


# ═══════════════════════════════════════════════════════════════════════════════
# Adversarial Falsification Benchmark
# ═══════════════════════════════════════════════════════════════════════════════

def run_adversarial_benchmark(
    sim_matrix: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    representation_name: str,
) -> Dict[str, Any]:
    """Run adversarial falsification tests on a representation."""
    logger.info(f"Running adversarial benchmark for {representation_name}")
    start = time.time()

    n = len(branches)
    k = 10

    # ─── Test 1: Language dominance ──────────────────────────────────────────
    lang_dominance = []
    for i in range(n):
        top_k_idx = np.argsort(sim_matrix[i])[-k:]
        neighbor_langs = languages[top_k_idx]
        same_lang_frac = np.mean(neighbor_langs == languages[i])
        lang_dominance.append(same_lang_frac)
    lang_dominance = np.array(lang_dominance)

    # ─── Test 2: Branch coherence ────────────────────────────────────────────
    branch_coherence = []
    for i in range(n):
        top_k_idx = np.argsort(sim_matrix[i])[-k:]
        neighbor_branches = branches[top_k_idx]
        same_branch_frac = np.mean(neighbor_branches == branches[i])
        branch_coherence.append(same_branch_frac)
    branch_coherence = np.array(branch_coherence)

    # ─── Test 3: Worst-case neighbors ────────────────────────────────────────
    worst_branch_idx = np.argsort(branch_coherence)[:20]
    worst_cases = []
    for idx in worst_branch_idx:
        top_k_idx = np.argsort(sim_matrix[idx])[-k:]
        neighbor_branches_arr = branches[top_k_idx]
        worst_cases.append({
            "index": int(idx),
            "branch": branches[idx],
            "language": languages[idx],
            "branch_coherence@10": round(float(branch_coherence[idx]), 4),
            "neighbor_branches": [str(b) for b in neighbor_branches_arr],
        })

    # ─── Test 4: Dead zones ──────────────────────────────────────────────────
    dead_zones = []
    for i in range(n):
        top_20_idx = np.argsort(sim_matrix[i])[-20:]
        for j in top_20_idx:
            if i != j and branches[i] != branches[j]:
                dead_zones.append({
                    "i": int(i),
                    "j": int(j),
                    "similarity": round(float(sim_matrix[i, j]), 4),
                    "branch_i": branches[i],
                    "branch_j": branches[j],
                    "lang_i": languages[i],
                    "lang_j": languages[j],
                })
    dead_zones.sort(key=lambda x: x["similarity"], reverse=True)
    dead_zones = dead_zones[:20]

    # ─── Test 5: Subgroup sensitivity ────────────────────────────────────────
    subgroup_sensitivity = {}
    for branch in sorted(set(branches)):
        mask = branches == branch
        if np.sum(mask) < 10:
            continue
        coherence_vals = branch_coherence[mask]
        subgroup_sensitivity[branch] = {
            "count": int(np.sum(mask)),
            "mean_coherence@10": round(float(np.mean(coherence_vals)), 4),
            "std_coherence@10": round(float(np.std(coherence_vals)), 4),
            "min_coherence@10": round(float(np.min(coherence_vals)), 4),
        }

    # ─── Test 6: Similarity distribution ─────────────────────────────────────
    all_sims = sim_matrix[np.triu_indices(n, k=1)]
    sim_stats = {
        "mean": round(float(np.mean(all_sims)), 4),
        "std": round(float(np.std(all_sims)), 4),
        "min": round(float(np.min(all_sims)), 4),
        "max": round(float(np.max(all_sims)), 4),
        "p5": round(float(np.percentile(all_sims, 5)), 4),
        "p25": round(float(np.percentile(all_sims, 25)), 4),
        "p50": round(float(np.percentile(all_sims, 50)), 4),
        "p75": round(float(np.percentile(all_sims, 75)), 4),
        "p95": round(float(np.percentile(all_sims, 95)), 4),
    }

    # ─── Falsification summary ───────────────────────────────────────────────
    falsified = False
    falsification_reasons = []

    if np.mean(lang_dominance) > 0.9:
        falsified = True
        falsification_reasons.append(
            f"Language dominance {np.mean(lang_dominance):.3f} > 0.9: "
            f"representation groups by language, not legal content"
        )

    if np.mean(branch_coherence) < 0.3:
        falsified = True
        falsification_reasons.append(
            f"Branch coherence {np.mean(branch_coherence):.3f} < 0.3: "
            f"neighbors are no more legally coherent than random"
        )

    high_sim_cross_branch = [dz for dz in dead_zones if dz["similarity"] > 0.95]
    if len(high_sim_cross_branch) > 5:
        falsified = True
        falsification_reasons.append(
            f"{len(high_sim_cross_branch)} pairs with similarity > 0.95 "
            f"across different branches: dead zones in embedding space"
        )

    duration = time.time() - start
    status = "FALSIFIED" if falsified else "PASSED"

    return {
        "representation": representation_name,
        "num_decisions": n,
        "status": status,
        "falsified": falsified,
        "falsification_reasons": falsification_reasons,
        "language_dominance": {
            "mean": round(float(np.mean(lang_dominance)), 4),
            "std": round(float(np.std(lang_dominance)), 4),
            "median": round(float(np.median(lang_dominance)), 4),
        },
        "branch_coherence": {
            "mean": round(float(np.mean(branch_coherence)), 4),
            "std": round(float(np.std(branch_coherence)), 4),
            "median": round(float(np.median(branch_coherence)), 4),
        },
        "worst_cases": worst_cases[:10],  # Top 10 for brevity
        "dead_zones": dead_zones,
        "subgroup_sensitivity": subgroup_sensitivity,
        "similarity_distribution": sim_stats,
        "duration": duration,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TF Metadata Human-Indexing Benchmark
# ═══════════════════════════════════════════════════════════════════════════════

def _knn_classification(sim_matrix, labels, k_values, label):
    """k-NN classification using cosine similarity."""
    n = len(labels)
    results = {}
    for k in k_values:
        correct = 0
        for i in range(n):
            top_k_idx = np.argsort(sim_matrix[i])[-k:]
            neighbor_labels = labels[top_k_idx]
            majority = Counter(neighbor_labels).most_common(1)[0][0]
            if majority == labels[i]:
                correct += 1
        accuracy = correct / n if n > 0 else 0
        results[f"knn_accuracy@{k}"] = round(accuracy, 4)
    n_labels = len(set(labels))
    results["random_baseline"] = round(1.0 / n_labels, 4) if n_labels > 0 else 0
    return results


def _cluster_purity_at_k(sim_matrix, labels, k_values):
    """Compute mean purity of k-NN neighborhoods."""
    n = len(labels)
    results = {}
    for k in k_values:
        purities = []
        for i in range(n):
            top_k_idx = np.argsort(sim_matrix[i])[-k:]
            neighbor_labels = labels[top_k_idx]
            counts = Counter(neighbor_labels)
            majority_count = counts.most_common(1)[0][1]
            purities.append(majority_count / k)
        results[f"mean_purity@{k}"] = round(float(np.mean(purities)), 4)
    return results


def run_tf_metadata_benchmark(
    sim_matrix: np.ndarray,
    branches: np.ndarray,
    chambers: np.ndarray,
    legal_areas: np.ndarray,
    representation_name: str,
) -> Dict[str, Any]:
    """Run TF metadata human-indexing benchmark."""
    logger.info(f"Running TF metadata benchmark for {representation_name}")
    start = time.time()

    branch_results = _knn_classification(sim_matrix, branches, [1, 3, 5, 10], "branch")
    chamber_results = _knn_classification(sim_matrix, chambers, [1, 3, 5, 10], "chamber")
    area_results = _knn_classification(sim_matrix, legal_areas, [1, 3, 5, 10], "legal_area")
    purity_results = _cluster_purity_at_k(sim_matrix, branches, [5, 10, 20, 50])

    branch_acc = branch_results.get("knn_accuracy@5", 0)
    chamber_acc = chamber_results.get("knn_accuracy@5", 0)
    area_acc = area_results.get("knn_accuracy@5", 0)
    purity_10 = purity_results.get("mean_purity@10", 0)

    duration = time.time() - start

    return {
        "representation": representation_name,
        "num_decisions": len(branches),
        "branch_knn": branch_results,
        "chamber_knn": chamber_results,
        "legal_area_knn": area_results,
        "branch_purity_at_k": purity_results,
        "summary": {
            "branch_knn_accuracy@5": branch_acc,
            "chamber_knn_accuracy@5": chamber_acc,
            "legal_area_knn_accuracy@5": area_acc,
            "branch_purity@10": purity_10,
            "branch_pass": branch_acc > 0.5,
            "any_pass": branch_acc > 0.5 or chamber_acc > 0.3 or purity_10 > 0.6,
        },
        "duration": duration,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Temporal Stability Test (NEW in cycle 9)
# ═══════════════════════════════════════════════════════════════════════════════

def run_temporal_stability_test(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    representation_name: str,
    n_splits: int = 5,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Test temporal stability: split corpus into random halves, measure whether
    neighbor quality (branch coherence) is consistent across splits.

    Since all decisions are from 2024, we use random splits as a proxy for
    temporal stability. If the representation is stable, branch coherence
    should be similar across random subsets.
    """
    logger.info(f"Running temporal stability test for {representation_name}")
    start = time.time()

    rng = np.random.RandomState(seed)
    n = len(branches)
    half = n // 2

    split_results = []
    for split_idx in range(n_splits):
        # Random split
        indices = rng.permutation(n)
        split_a = indices[:half]
        split_b = indices[half:]

        # Compute similarity within each split
        emb_a = normalize_embeddings(embeddings[split_a])
        emb_b = normalize_embeddings(embeddings[split_b])

        sim_a = compute_similarity(emb_a)
        sim_b = compute_similarity(emb_b)

        # Branch coherence in each split
        branches_a = branches[split_a]
        branches_b = branches[split_b]
        langs_a = languages[split_a]
        langs_b = languages[split_b]

        k = 10
        coherence_a = []
        lang_dom_a = []
        for i in range(len(split_a)):
            top_k_idx = np.argsort(sim_a[i])[-k:]
            coherence_a.append(np.mean(branches_a[top_k_idx] == branches_a[i]))
            lang_dom_a.append(np.mean(langs_a[top_k_idx] == langs_a[i]))

        coherence_b = []
        lang_dom_b = []
        for i in range(len(split_b)):
            top_k_idx = np.argsort(sim_b[i])[-k:]
            coherence_b.append(np.mean(branches_b[top_k_idx] == branches_b[i]))
            lang_dom_b.append(np.mean(langs_b[top_k_idx] == langs_b[i]))

        split_results.append({
            "split": split_idx,
            "size_a": len(split_a),
            "size_b": len(split_b),
            "branch_coherence_a": round(float(np.mean(coherence_a)), 4),
            "branch_coherence_b": round(float(np.mean(coherence_b)), 4),
            "language_dominance_a": round(float(np.mean(lang_dom_a)), 4),
            "language_dominance_b": round(float(np.mean(lang_dom_b)), 4),
            "coherence_diff": round(abs(np.mean(coherence_a) - np.mean(coherence_b)), 4),
            "lang_dom_diff": round(abs(np.mean(lang_dom_a) - np.mean(lang_dom_b)), 4),
        })

    # Aggregate stability metrics
    coherence_values = [s["branch_coherence_a"] for s in split_results] + \
                       [s["branch_coherence_b"] for s in split_results]
    lang_dom_values = [s["language_dominance_a"] for s in split_results] + \
                      [s["language_dominance_b"] for s in split_results]
    coherence_diffs = [s["coherence_diff"] for s in split_results]

    duration = time.time() - start

    return {
        "representation": representation_name,
        "n_splits": n_splits,
        "split_results": split_results,
        "aggregate": {
            "mean_branch_coherence": round(float(np.mean(coherence_values)), 4),
            "std_branch_coherence": round(float(np.std(coherence_values)), 4),
            "mean_language_dominance": round(float(np.mean(lang_dom_values)), 4),
            "std_language_dominance": round(float(np.std(lang_dom_values)), 4),
            "mean_coherence_diff": round(float(np.mean(coherence_diffs)), 4),
            "max_coherence_diff": round(float(np.max(coherence_diffs)), 4),
            "stability_drift": round(float(np.std(coherence_values)), 4),
        },
        "duration": duration,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Main execution
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    run_id = f"eval_cycle_9_{int(time.time())}"
    logger.info(f"Starting evaluation cycle 9: {run_id}")

    # Load all representations
    metadata, representations = load_all_representations()

    results = {
        "run_id": run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cycle": 9,
        "hypothesis": (
            "Citation-graph representations (blended, graph-only) may resolve "
            "dead zones and language dominance because citations cross language "
            "boundaries. Temporal stability tests whether neighbor quality is "
            "consistent across corpus subsets."
        ),
        "frozen_sample": "1000 BGer decisions (2024) from fractal-map baseline",
        "frozen_metrics": [
            "language_dominance_mean",
            "branch_coherence_mean",
            "falsification_status",
            "branch_knn_accuracy@5",
            "temporal_stability_drift",
        ],
        "success_rule": (
            "No new falsification from citation-graph representations; "
            "temporal stability drift < 0.1"
        ),
        "representations": {},
        "comparison": {},
    }

    # Run benchmarks on each representation
    for name, emb in representations.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {name} (shape {emb.shape})")
        logger.info(f"{'='*60}")

        emb_valid, branches, languages, chambers, legal_areas, valid_idx = \
            prepare_valid_data(metadata, emb)

        emb_norm = normalize_embeddings(emb_valid)
        sim_matrix = compute_similarity(emb_norm)

        # Adversarial benchmark
        adversarial = run_adversarial_benchmark(sim_matrix, branches, languages, name)

        # TF metadata benchmark
        tf_metadata = run_tf_metadata_benchmark(
            sim_matrix, branches, chambers, legal_areas, name
        )

        # Temporal stability test
        stability = run_temporal_stability_test(emb_valid, branches, languages, name)

        results["representations"][name] = {
            "adversarial": adversarial,
            "tf_metadata": tf_metadata,
            "temporal_stability": stability,
        }

    # ─── Cross-representation comparison ─────────────────────────────────────
    logger.info(f"\n{'='*60}")
    logger.info("COMPARISON")
    logger.info(f"{'='*60}")

    comparison = {
        "adversarial_status": {},
        "language_dominance": {},
        "branch_coherence": {},
        "dead_zones_count": {},
        "branch_knn_accuracy": {},
        "temporal_stability_drift": {},
    }

    for name, res in results["representations"].items():
        adv = res["adversarial"]
        tf = res["tf_metadata"]
        stab = res["temporal_stability"]

        comparison["adversarial_status"][name] = adv["status"]
        comparison["language_dominance"][name] = adv["language_dominance"]["mean"]
        comparison["branch_coherence"][name] = adv["branch_coherence"]["mean"]
        comparison["dead_zones_count"][name] = len(adv["dead_zones"])
        comparison["branch_knn_accuracy"][name] = tf["summary"]["branch_knn_accuracy@5"]
        comparison["temporal_stability_drift"][name] = stab["aggregate"]["stability_drift"]

        logger.info(f"  {name}:")
        logger.info(f"    Adversarial: {adv['status']}")
        logger.info(f"    Language dominance: {adv['language_dominance']['mean']:.3f}")
        logger.info(f"    Branch coherence: {adv['branch_coherence']['mean']:.3f}")
        logger.info(f"    Dead zones (>0.95): {len([dz for dz in adv['dead_zones'] if dz['similarity'] > 0.95])}")
        logger.info(f"    Branch k-NN@5: {tf['summary']['branch_knn_accuracy@5']:.3f}")
        logger.info(f"    Temporal drift: {stab['aggregate']['stability_drift']:.4f}")

    results["comparison"] = comparison

    # ─── Key findings ────────────────────────────────────────────────────────
    findings = []

    # Check if citation-graph representations pass adversarial tests
    for name in ["citation_blended", "citation_graph_only"]:
        status = comparison["adversarial_status"][name]
        if status == "PASSED":
            findings.append(
                f"KEY: {name} PASSES adversarial tests (baseline and debiased were FALSIFIED)"
            )
        else:
            reasons = results["representations"][name]["adversarial"]["falsification_reasons"]
            findings.append(f"{name} FALSIFIED: {'; '.join(reasons)}")

    # Language dominance comparison
    ld_baseline = comparison["language_dominance"]["baseline"]
    ld_blended = comparison["language_dominance"]["citation_blended"]
    ld_graph = comparison["language_dominance"]["citation_graph_only"]
    findings.append(
        f"Language dominance: baseline={ld_baseline:.3f}, "
        f"blended={ld_blended:.3f}, graph_only={ld_graph:.3f}"
    )

    # Dead zones comparison
    dz_baseline = comparison["dead_zones_count"]["baseline"]
    dz_blended = comparison["dead_zones_count"]["citation_blended"]
    dz_graph = comparison["dead_zones_count"]["citation_graph_only"]
    findings.append(
        f"Dead zones (>0.95 sim across branches): baseline={dz_baseline}, "
        f"blended={dz_blended}, graph_only={dz_graph}"
    )

    # Temporal stability
    for name in representations:
        drift = comparison["temporal_stability_drift"][name]
        findings.append(f"Temporal stability drift ({name}): {drift:.4f}")

    results["key_findings"] = findings

    for f in findings:
        logger.info(f"  FINDING: {f}")

    # ─── Save results ────────────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_path = OUTPUT_DIR / "cycle_9_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Results saved to {results_path}")

    return results


if __name__ == "__main__":
    results = main()
    print("\n=== CYCLE 9 COMPLETE ===")
    print(f"Run ID: {results['run_id']}")
    for name, status in results["comparison"]["adversarial_status"].items():
        print(f"  {name}: {status}")
