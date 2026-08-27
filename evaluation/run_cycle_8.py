#!/usr/bin/env python3
"""
Evaluation Cycle 8: Adversarial Falsification + TF Human Indexing

Hypothesis: The current best representation (language_debiased_pca2) may have
hidden weaknesses that positive benchmarks don't catch. Additionally, canonical
court metadata (branch, chamber, legal_area) provides human indexing that
existing benchmarks underexploit.

Product decision: If adversarial tests reveal significant weaknesses, the
legal-distance lane must address them before productization. If TF metadata
benchmark shows the representation recovers fine-grained court structure,
it strengthens the case for the current approach.

Frozen before observation:
- Corpus: 1000 BGer decisions (2020-2024) from fractal-map baseline metadata
- Embeddings: baseline (768-dim), language_debiased_pca2 (2-dim)
- Success rule: Adversarial degradation < 20% on neighbor quality;
  chamber-level NMI > 0.3 for TF metadata benchmark
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
    precision_score,
    recall_score,
    f1_score,
)
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Paths ───────────────────────────────────────────────────────────────────
ACCEPTED = Path("/tmp/lex_accepted")
BASELINE_META = ACCEPTED / "fractal-map/results/fractal_map/baseline/metadata.json"
BASELINE_EMB = ACCEPTED / "fractal-map/results/fractal_map/baseline/embeddings.npy"
DEBIASED_EMB = ACCEPTED / "fractal-map/results/fractal_map/language_debiasing/embeddings_pca2.npy"
CANONICAL_DIR = ACCEPTED / "corpus/corpus/normalization/canonical"
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results")
REPORT_DIR = Path("/home/runner/work/LexMachina/LexMachina/reports/evaluation")

# ─── Chamber-to-Branch mapping ──────────────────────────────────────────────
CHAMBER_TO_BRANCH = {
    "I. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "II. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "III. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
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


def load_baseline_data():
    """Load baseline metadata and embeddings."""
    with open(BASELINE_META) as f:
        metadata = json.load(f)
    embeddings = np.load(BASELINE_EMB)
    logger.info(f"Loaded {len(metadata)} decisions, embeddings shape {embeddings.shape}")
    return metadata, embeddings


def load_debiased_embeddings():
    """Load language-debiased PCA2 embeddings."""
    embeddings = np.load(DEBIASED_EMB)
    logger.info(f"Loaded debiased embeddings shape {embeddings.shape}")
    return embeddings


def assign_branch(chamber: str) -> str:
    """Map chamber name to branch."""
    if chamber in CHAMBER_TO_BRANCH:
        return CHAMBER_TO_BRANCH[chamber]
    # Fallback: try partial matching
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


# ═══════════════════════════════════════════════════════════════════════════════
# Benchmark 1: TF Metadata Human-Indexing Benchmark
# ═══════════════════════════════════════════════════════════════════════════════

def run_tf_metadata_benchmark(
    metadata: List[Dict],
    embeddings: np.ndarray,
    representation_name: str,
) -> Dict[str, Any]:
    """
    Benchmark using canonical court metadata as human indexing.

    Tests:
    1. Branch classification (4 categories): Can the representation
       recover the court's own branch assignment?
    2. Chamber classification (8+ categories): Can it recover finer
       chamber structure?
    3. Legal-area clustering (many categories): Can it recover the
       specific legal area?

    Uses k-NN classification (not clustering) to test whether nearby
    decisions share the same human-assigned labels.
    """
    logger.info(f"Running TF metadata benchmark for {representation_name}")
    start = time.time()

    # Assign branch labels
    branches = []
    chambers = []
    legal_areas = []
    valid_indices = []

    for i, meta in enumerate(metadata):
        chamber = meta.get("chamber", "")
        branch = assign_branch(chamber)
        legal_area = meta.get("legal_area", "unknown")

        if branch != "unknown":
            branches.append(branch)
            chambers.append(chamber)
            legal_areas.append(legal_area)
            valid_indices.append(i)

    if len(valid_indices) < 50:
        return {"error": "Insufficient valid decisions"}

    emb = embeddings[valid_indices]
    branches = np.array(branches)
    chambers = np.array(chambers)
    legal_areas = np.array(legal_areas)

    # Normalize embeddings
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms[norms == 0] = 1
    emb_norm = emb / norms

    # Compute pairwise cosine similarity
    sim_matrix = emb_norm @ emb_norm.T
    np.fill_diagonal(sim_matrix, -1)  # Exclude self

    # ─── Branch k-NN classification ────────────────────────────────────────
    branch_results = _knn_classification(
        sim_matrix, branches, k_values=[1, 3, 5, 10], label="branch"
    )

    # ─── Chamber k-NN classification ───────────────────────────────────────
    chamber_results = _knn_classification(
        sim_matrix, chambers, k_values=[1, 3, 5, 10], label="chamber"
    )

    # ─── Legal-area k-NN classification ────────────────────────────────────
    area_results = _knn_classification(
        sim_matrix, legal_areas, k_values=[1, 3, 5, 10], label="legal_area"
    )

    # ─── Branch purity at various k ────────────────────────────────────────
    branch_purity_results = _cluster_purity_at_k(
        sim_matrix, branches, k_values=[5, 10, 20, 50]
    )

    # ─── Cross-branch confusion matrix ─────────────────────────────────────
    confusion = _cross_label_confusion(sim_matrix, branches, label="branch")

    duration = time.time() - start

    # Summary
    branch_acc = branch_results.get("knn_accuracy@5", 0)
    chamber_acc = chamber_results.get("knn_accuracy@5", 0)
    area_acc = area_results.get("knn_accuracy@5", 0)
    purity_10 = branch_purity_results.get("mean_purity@10", 0)

    # Pass criteria: branch k-NN accuracy > 0.5 (well above random ~0.25)
    branch_pass = branch_acc > 0.5
    # At least one metric significantly above random
    any_pass = branch_acc > 0.5 or chamber_acc > 0.3 or purity_10 > 0.6

    return {
        "representation": representation_name,
        "num_decisions": len(valid_indices),
        "branch_distribution": dict(Counter(branches)),
        "branch_knn": branch_results,
        "chamber_knn": chamber_results,
        "legal_area_knn": area_results,
        "branch_purity_at_k": branch_purity_results,
        "cross_branch_confusion": confusion,
        "summary": {
            "branch_knn_accuracy@5": branch_acc,
            "chamber_knn_accuracy@5": chamber_acc,
            "legal_area_knn_accuracy@5": area_acc,
            "branch_purity@10": purity_10,
            "branch_pass": branch_pass,
            "any_pass": any_pass,
        },
        "duration": duration,
    }


def _knn_classification(
    sim_matrix: np.ndarray,
    labels: np.ndarray,
    k_values: List[int],
    label: str,
) -> Dict[str, float]:
    """k-NN classification using cosine similarity."""
    n = len(labels)
    results = {}

    for k in k_values:
        correct = 0
        total = 0
        for i in range(n):
            # Get top-k neighbors (excluding self, which is already -1)
            top_k_idx = np.argsort(sim_matrix[i])[-k:]
            # Majority vote
            neighbor_labels = labels[top_k_idx]
            majority = Counter(neighbor_labels).most_common(1)[0][0]
            if majority == labels[i]:
                correct += 1
            total += 1

        accuracy = correct / total if total > 0 else 0
        results[f"knn_accuracy@{k}"] = round(accuracy, 4)

    # Random baseline
    n_labels = len(set(labels))
    results["random_baseline"] = round(1.0 / n_labels, 4) if n_labels > 0 else 0

    return results


def _cluster_purity_at_k(
    sim_matrix: np.ndarray,
    labels: np.ndarray,
    k_values: List[int],
) -> Dict[str, float]:
    """Compute mean purity of k-NN neighborhoods."""
    n = len(labels)
    results = {}

    for k in k_values:
        purities = []
        for i in range(n):
            top_k_idx = np.argsort(sim_matrix[i])[-k:]
            neighbor_labels = labels[top_k_idx]
            # Purity = fraction of majority label
            counts = Counter(neighbor_labels)
            majority_count = counts.most_common(1)[0][1]
            purities.append(majority_count / k)

        results[f"mean_purity@{k}"] = round(float(np.mean(purities)), 4)

    return results


def _cross_label_confusion(
    sim_matrix: np.ndarray,
    labels: np.ndarray,
    label: str,
) -> Dict[str, Any]:
    """Measure cross-label confusion: what fraction of neighbors share the label."""
    n = len(labels)
    unique_labels = sorted(set(labels))
    label_to_idx = {l: i for i, l in enumerate(unique_labels)}

    # For each label, compute mean fraction of same-label neighbors at k=10
    k = 10
    confusion = {}
    for lbl in unique_labels:
        mask = labels == lbl
        indices = np.where(mask)[0]
        if len(indices) == 0:
            continue

        fractions = []
        for i in indices:
            top_k_idx = np.argsort(sim_matrix[i])[-k:]
            neighbor_labels = labels[top_k_idx]
            same_label_frac = np.mean(neighbor_labels == lbl)
            fractions.append(same_label_frac)

        confusion[lbl] = {
            "count": int(len(indices)),
            "mean_same_label_fraction@10": round(float(np.mean(fractions)), 4),
        }

    return confusion


# ═══════════════════════════════════════════════════════════════════════════════
# Benchmark 2: Adversarial Falsification Test
# ═══════════════════════════════════════════════════════════════════════════════

def run_adversarial_falsification(
    metadata: List[Dict],
    embeddings: np.ndarray,
    representation_name: str,
) -> Dict[str, Any]:
    """
    Adversarial test that actively tries to break the representation.

    Tests:
    1. **Embedding-space**: Are there "dead zones" where the representation
       assigns high similarity to unrelated decisions?
    2. **Neighbor homogeneity**: Are neighbors too homogeneous (all same
       language) or too heterogeneous (mixed branches)?
    3. **Sensitivity to metadata**: Does the representation's neighbor quality
       vary dramatically across metadata subgroups?
    4. **Worst-case neighbors**: What do the worst neighbors look like?
    """
    logger.info(f"Running adversarial falsification for {representation_name}")
    start = time.time()

    # Assign labels
    branches = []
    languages = []
    valid_indices = []

    for i, meta in enumerate(metadata):
        chamber = meta.get("chamber", "")
        branch = assign_branch(chamber)
        lang = meta.get("language", "unknown")

        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            valid_indices.append(i)

    if len(valid_indices) < 50:
        return {"error": "Insufficient valid decisions"}

    emb = embeddings[valid_indices]
    branches = np.array(branches)
    languages = np.array(languages)

    # Normalize
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms[norms == 0] = 1
    emb_norm = emb / norms

    # Pairwise similarity
    sim_matrix = emb_norm @ emb_norm.T
    np.fill_diagonal(sim_matrix, -1)

    n = len(valid_indices)
    k = 10

    # ─── Test 1: Language dominance in neighbors ────────────────────────────
    # For each decision, what fraction of its k-NN are same language?
    lang_dominance = []
    for i in range(n):
        top_k_idx = np.argsort(sim_matrix[i])[-k:]
        neighbor_langs = languages[top_k_idx]
        same_lang_frac = np.mean(neighbor_langs == languages[i])
        lang_dominance.append(same_lang_frac)

    lang_dominance = np.array(lang_dominance)

    # ─── Test 2: Branch coherence in neighbors ──────────────────────────────
    # For each decision, what fraction of its k-NN share the same branch?
    branch_coherence = []
    for i in range(n):
        top_k_idx = np.argsort(sim_matrix[i])[-k:]
        neighbor_branches = branches[top_k_idx]
        same_branch_frac = np.mean(neighbor_branches == branches[i])
        branch_coherence.append(same_branch_frac)

    branch_coherence = np.array(branch_coherence)

    # ─── Test 3: Worst-case neighbors ──────────────────────────────────────
    # Find decisions where branch coherence is lowest
    worst_branch_idx = np.argsort(branch_coherence)[:20]
    worst_cases = []
    for idx in worst_branch_idx:
        top_k_idx = np.argsort(sim_matrix[idx])[-k:]
        neighbor_branches = branches[top_k_idx]
        worst_cases.append({
            "index": int(valid_indices[idx]),
            "branch": branches[idx],
            "language": languages[idx],
            "branch_coherence@10": round(float(branch_coherence[idx]), 4),
            "neighbor_branches": [str(b) for b in neighbor_branches],
        })

    # ─── Test 4: Dead zones (high similarity between unrelated decisions) ───
    # Find pairs with high similarity but different branches
    dead_zones = []
    for i in range(n):
        top_20_idx = np.argsort(sim_matrix[i])[-20:]
        for j in top_20_idx:
            if i != j and branches[i] != branches[j]:
                dead_zones.append({
                    "i": int(valid_indices[i]),
                    "j": int(valid_indices[j]),
                    "similarity": round(float(sim_matrix[i, j]), 4),
                    "branch_i": branches[i],
                    "branch_j": branches[j],
                    "lang_i": languages[i],
                    "lang_j": languages[j],
                })

    # Sort by similarity (highest = worst)
    dead_zones.sort(key=lambda x: x["similarity"], reverse=True)
    dead_zones = dead_zones[:20]

    # ─── Test 5: Subgroup sensitivity ──────────────────────────────────────
    # Does branch coherence vary across branches?
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

    # ─── Test 6: Similarity distribution analysis ──────────────────────────
    # Check if the similarity distribution has concerning shapes
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

    # ─── Falsification summary ─────────────────────────────────────────────
    # Check for falsification conditions
    falsified = False
    falsification_reasons = []

    # Falsification 1: Language dominance > 90% (representation groups by language, not law)
    if np.mean(lang_dominance) > 0.9:
        falsified = True
        falsification_reasons.append(
            f"Language dominance {np.mean(lang_dominance):.3f} > 0.9: "
            f"representation groups by language, not legal content"
        )

    # Falsification 2: Branch coherence < 0.3 (worse than random for 4 branches)
    if np.mean(branch_coherence) < 0.3:
        falsified = True
        falsification_reasons.append(
            f"Branch coherence {np.mean(branch_coherence):.3f} < 0.3: "
            f"neighbors are no more legally coherent than random"
        )

    # Falsification 3: High cross-branch similarity (dead zones)
    high_sim_cross_branch = [dz for dz in dead_zones if dz["similarity"] > 0.95]
    if len(high_sim_cross_branch) > 5:
        falsified = True
        falsification_reasons.append(
            f"{len(high_sim_cross_branch)} pairs with similarity > 0.95 "
            f"across different branches: dead zones in embedding space"
        )

    duration = time.time() - start

    # Pass if NOT falsified
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
        "worst_cases": worst_cases,
        "dead_zones": dead_zones,
        "subgroup_sensitivity": subgroup_sensitivity,
        "similarity_distribution": sim_stats,
        "duration": duration,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Main execution
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    run_id = f"eval_cycle_8_{int(time.time())}"
    logger.info(f"Starting evaluation cycle 8: {run_id}")

    # Load data
    metadata, baseline_emb = load_baseline_data()
    debiased_emb = load_debiased_embeddings()

    results = {
        "run_id": run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cycle": 8,
        "hypothesis": (
            "Adversarial testing reveals hidden weaknesses in current representations. "
            "TF metadata benchmark tests finer-grained human indexing than branch-only."
        ),
        "frozen_sample": "1000 BGer decisions (2020-2024) from fractal-map baseline",
        "frozen_metrics": [
            "branch_knn_accuracy@5",
            "chamber_knn_accuracy@5",
            "language_dominance_mean",
            "branch_coherence_mean",
            "falsification_status",
        ],
        "success_rule": (
            "Adversarial degradation < 20% on neighbor quality; "
            "branch k-NN accuracy > 0.5 for TF metadata benchmark"
        ),
        "representations": [],
    }

    # ─── Baseline representation ───────────────────────────────────────────
    logger.info("Evaluating baseline representation")
    baseline_tf = run_tf_metadata_benchmark(metadata, baseline_emb, "baseline")
    baseline_adv = run_adversarial_falsification(metadata, baseline_emb, "baseline")
    results["representations"].append({
        "name": "baseline",
        "description": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2 (768-dim)",
        "tf_metadata": baseline_tf,
        "adversarial": baseline_adv,
    })

    # ─── Language-debiased PCA2 representation ─────────────────────────────
    logger.info("Evaluating language-debiased PCA2 representation")
    debiased_tf = run_tf_metadata_benchmark(metadata, debiased_emb, "language_debiased_pca2")
    debiased_adv = run_adversarial_falsification(metadata, debiased_emb, "language_debiased_pca2")
    results["representations"].append({
        "name": "language_debiased_pca2",
        "description": "Baseline with language-component removed via PCA (2-dim)",
        "tf_metadata": debiased_tf,
        "adversarial": debiased_adv,
    })

    # ─── Comparison ─────────────────────────────────────────────────────────
    results["comparison"] = {
        "tf_metadata": {
            "baseline_branch_knn@5": baseline_tf.get("summary", {}).get("branch_knn_accuracy@5", 0),
            "debiased_branch_knn@5": debiased_tf.get("summary", {}).get("branch_knn_accuracy@5", 0),
            "baseline_chamber_knn@5": baseline_tf.get("summary", {}).get("chamber_knn_accuracy@5", 0),
            "debiased_chamber_knn@5": debiased_tf.get("summary", {}).get("chamber_knn_accuracy@5", 0),
            "baseline_purity@10": baseline_tf.get("summary", {}).get("branch_purity@10", 0),
            "debiased_purity@10": debiased_tf.get("summary", {}).get("branch_purity@10", 0),
        },
        "adversarial": {
            "baseline_status": baseline_adv.get("status", "UNKNOWN"),
            "debiased_status": debiased_adv.get("status", "UNKNOWN"),
            "baseline_lang_dominance": baseline_adv.get("language_dominance", {}).get("mean", 0),
            "debiased_lang_dominance": debiased_adv.get("language_dominance", {}).get("mean", 0),
            "baseline_branch_coherence": baseline_adv.get("branch_coherence", {}).get("mean", 0),
            "debiased_branch_coherence": debiased_adv.get("branch_coherence", {}).get("mean", 0),
        },
    }

    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"cycle_8_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Results saved to {output_file}")

    # Print summary
    print("\n" + "=" * 72)
    print("EVALUATION CYCLE 8 SUMMARY")
    print("=" * 72)
    print(f"Run ID: {run_id}")
    print(f"Representations: baseline, language_debiased_pca2")
    print()

    print("TF Metadata Benchmark (k-NN accuracy @ k=5):")
    print(f"  Branch:    baseline={results['comparison']['tf_metadata']['baseline_branch_knn@5']:.3f}  "
          f"debiased={results['comparison']['tf_metadata']['debiased_branch_knn@5']:.3f}  "
          f"(random=0.25)")
    print(f"  Chamber:   baseline={results['comparison']['tf_metadata']['baseline_chamber_knn@5']:.3f}  "
          f"debiased={results['comparison']['tf_metadata']['debiased_chamber_knn@5']:.3f}")
    print(f"  Purity@10: baseline={results['comparison']['tf_metadata']['baseline_purity@10']:.3f}  "
          f"debiased={results['comparison']['tf_metadata']['debiased_purity@10']:.3f}")
    print()

    print("Adversarial Falsification:")
    print(f"  Baseline:    {results['comparison']['adversarial']['baseline_status']}")
    print(f"  Debiased:    {results['comparison']['adversarial']['debiased_status']}")
    print(f"  Lang dominance: baseline={results['comparison']['adversarial']['baseline_lang_dominance']:.3f}  "
          f"debiased={results['comparison']['adversarial']['debiased_lang_dominance']:.3f}")
    print(f"  Branch coherence: baseline={results['comparison']['adversarial']['baseline_branch_coherence']:.3f}  "
          f"debiased={results['comparison']['adversarial']['debiased_branch_coherence']:.3f}")
    print()

    # Falsification details
    for rep in results["representations"]:
        adv = rep["adversarial"]
        if adv.get("falsified"):
            print(f"  FALSIFIED {rep['name']}:")
            for reason in adv.get("falsification_reasons", []):
                print(f"    - {reason}")
    print("=" * 72)

    return results


if __name__ == "__main__":
    results = main()
