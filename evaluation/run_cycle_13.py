#!/usr/bin/env python3
"""
Evaluation Cycle 13: Debiasing Parameter Sensitivity

Hypothesis: The debiased_citation_blended representation from cycle 12 achieved
BOTH success criteria (language_dominance=0.630 < 0.85, citation_heritage_AUC=0.910 > 0.65).
This cycle tests sensitivity to the two key hyperparameters:
  - n_pca_components: number of top PCA components removed for language debiasing
  - alpha: blending weight between debiased baseline and citation graph embeddings

Frozen before observation:
- Corpus: 1000 BGer decisions (2020-2024) from fractal-map baseline
- Baseline embeddings: 768-dim (accepted from fractal-map lane)
- Citation graph: from canonical corpus

Grid:
  n_pca_components: [1, 2, 3, 5]
  alpha: [0.3, 0.5, 0.7]
  = 12 combinations + cycle 12's (n=2, alpha=0.5) as anchor

Success rule: identify parameter region where BOTH criteria hold
  (language_dominance < 0.85 AND citation_heritage_AUC > 0.65)
  without dimensional collapse (mean_similarity < 0.99)

Product decision: Map the Pareto frontier over branch_knn_accuracy vs
citation_heritage_AUC vs language_dominance to recommend a product default.
"""

import json
import time
import sys
import os
import logging
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Any, Optional, Set

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA, TruncatedSVD
from math import erf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Paths ───────────────────────────────────────────────────────────────────
ACCEPTED = Path("/tmp/lex_accepted")
BASELINE_META = ACCEPTED / "fractal-map/results/fractal_map/baseline/metadata.json"
BASELINE_EMB = ACCEPTED / "fractal-map/results/fractal_map/baseline/embeddings.npy"
CORPUS_FILE = ACCEPTED / "corpus/corpus/normalization/canonical/bger_2000plus_slice_1000.jsonl"
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results")
REPORT_DIR = Path("/home/runner/work/LexMachina/LexMachina/reports/evaluation")

# ─── Chamber-to-Branch mapping ──────────────────────────────────────────────
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


def load_corpus_citations() -> Dict[str, List[str]]:
    citations = {}
    with open(CORPUS_FILE) as f:
        for line in f:
            d = json.loads(line)
            did = d["decision_id"]
            cited = d.get("cited_decisions", [])
            if cited:
                citations[did] = cited
    logger.info(f"Loaded {len(citations)} decisions with citations")
    total_edges = sum(len(v) for v in citations.values())
    logger.info(f"Total citation edges: {total_edges}")
    return citations


def build_shared_citation_pairs(
    citations: Dict[str, List[str]],
    min_shared: int = 1,
    max_pairs: int = 5000,
) -> List[Tuple[str, str, int]]:
    reverse = defaultdict(set)
    for did, cited_list in citations.items():
        for c in cited_list:
            reverse[c].add(did)

    pair_shared = Counter()
    for citation, deciders in reverse.items():
        dec_list = list(deciders)
        for i in range(len(dec_list)):
            for j in range(i + 1, len(dec_list)):
                pair = tuple(sorted([dec_list[i], dec_list[j]]))
                pair_shared[pair] += 1

    pairs = [(a, b, n) for (a, b), n in pair_shared.items() if n >= min_shared]
    pairs.sort(key=lambda x: -x[2])
    pairs = pairs[:max_pairs]
    logger.info(f"Citation pairs with >= {min_shared} shared: {len(pairs)}")
    return pairs


def load_representations():
    with open(BASELINE_META) as f:
        metadata = json.load(f)
    baseline = np.load(BASELINE_EMB)
    logger.info(f"Loaded {len(metadata)} decisions, baseline shape: {baseline.shape}")
    return metadata, baseline


def prepare_valid_data(metadata, embeddings):
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
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return emb / norms


def compute_similarity(emb_norm):
    sim = emb_norm @ emb_norm.T
    np.fill_diagonal(sim, -1)
    return sim


# ═══════════════════════════════════════════════════════════════════════════════
# Representation creation with parameterized debiasing
# ═══════════════════════════════════════════════════════════════════════════════

def create_debiased_citation_blended(
    baseline_768: np.ndarray,
    metadata: List[Dict],
    citations: Dict[str, List[str]],
    n_pca_components: int = 2,
    alpha: float = 0.5,
    dims: int = 64,
) -> Tuple[np.ndarray, Dict]:
    """Create debiased citation blended with parameterized debiasing."""
    import networkx as nx
    from scipy.sparse import lil_matrix

    start = time.time()

    # Step 1: PCA debiasing on 768-dim baseline
    pca_debias = PCA(n_components=n_pca_components, random_state=42)
    pca_debias.fit(baseline_768)
    variance_removed = float(np.sum(pca_debias.explained_variance_ratio_))

    projected = pca_debias.transform(baseline_768)
    debiased_projected = projected.copy()
    debiased_projected[:, :n_pca_components] = 0
    debiased_768 = pca_debias.inverse_transform(debiased_projected)

    # Rescale to preserve original norm
    orig_norms = np.linalg.norm(baseline_768, axis=1, keepdims=True)
    debiased_norms = np.linalg.norm(debiased_768, axis=1, keepdims=True)
    debiased_norms[debiased_norms == 0] = 1
    debiased_768 = debiased_768 * (orig_norms / debiased_norms)

    # Step 2: PCA project debiased 768-dim to 64-dim
    pca_64 = PCA(n_components=dims, random_state=42)
    debiased_64 = pca_64.fit_transform(debiased_768)
    explained_64 = float(np.sum(pca_64.explained_variance_ratio_))

    # Step 3: Build citation graph from debiased baseline
    id_to_idx = {m.get("decision_id", ""): i for i, m in enumerate(metadata)}

    G = nx.DiGraph()
    for source_id, targets in citations.items():
        for target in targets:
            G.add_edge(source_id, target)

    baseline_nodes = set(id_to_idx.keys())
    graph_nodes = set(G.nodes())
    common_nodes = baseline_nodes & graph_nodes

    G_undirected = G.to_undirected()
    walk_length = 20
    num_walks = 5

    walks = []
    nodes = list(G_undirected.nodes())
    for _ in range(num_walks):
        np.random.shuffle(nodes)
        for node in nodes:
            walk = [node]
            for _ in range(walk_length - 1):
                current = walk[-1]
                neighbors = list(G_undirected.neighbors(current))
                if not neighbors:
                    break
                next_node = np.random.choice(neighbors)
                walk.append(next_node)
            walks.append(walk)

    vocab = {n: i for i, n in enumerate(nodes)}
    cooccur = lil_matrix((len(nodes), len(nodes)))

    for walk in walks:
        for i, node in enumerate(walk):
            for j in range(max(0, i - 5), min(len(walk), i + 6)):
                if i != j:
                    cooccur[vocab[node], vocab[walk[j]]] += 1

    cooccur = cooccur.tocsr()

    svd = TruncatedSVD(n_components=dims, random_state=42)
    node_embeddings = svd.fit_transform(cooccur)

    norms = np.linalg.norm(node_embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    node_embeddings = node_embeddings / norms

    # Step 4: Blend
    graph_embeddings = np.zeros((len(metadata), dims))
    in_graph_mask = np.zeros(len(metadata), dtype=bool)

    for node in common_nodes:
        idx = id_to_idx[node]
        node_idx = vocab[node]
        graph_embeddings[idx] = node_embeddings[node_idx]
        in_graph_mask[idx] = True

    debiased_citation_blended = np.copy(debiased_64)
    for i in range(len(metadata)):
        if in_graph_mask[i]:
            debiased_citation_blended[i] = alpha * debiased_64[i] + (1 - alpha) * graph_embeddings[i]

    duration = time.time() - start

    info = {
        "n_pca_components": n_pca_components,
        "alpha": alpha,
        "variance_removed_by_debiasing": round(variance_removed, 4),
        "pca_64_explained_variance": round(explained_64, 4),
        "in_graph_decisions": int(np.sum(in_graph_mask)),
        "total_decisions": len(metadata),
        "creation_duration": round(duration, 2),
    }

    return debiased_citation_blended, info


# ═══════════════════════════════════════════════════════════════════════════════
# Benchmarks (lightweight versions for grid search)
# ═══════════════════════════════════════════════════════════════════════════════

def run_citation_heritage_fast(
    sim_matrix: np.ndarray,
    metadata: List[Dict],
    valid_indices: List[int],
    citation_pairs: List[Tuple[str, str, int]],
) -> Dict[str, Any]:
    """Fast citation-heritage benchmark (core metrics only)."""
    start = time.time()
    n = sim_matrix.shape[0]

    id_to_local = {}
    for local_idx, global_idx in enumerate(valid_indices):
        did = metadata[global_idx]["decision_id"]
        id_to_local[did] = local_idx

    valid_pairs = []
    for d1, d2, shared_count in citation_pairs:
        if d1 in id_to_local and d2 in id_to_local:
            valid_pairs.append((id_to_local[d1], id_to_local[d2], shared_count))

    if len(valid_pairs) < 10:
        return {"status": "INSUFFICIENT_DATA", "num_valid_pairs": len(valid_pairs)}

    positive_set = set(tuple(sorted([a, b])) for a, b, _ in valid_pairs)

    positive_pairs = [(a, b) for a, b, _ in valid_pairs]
    negative_pairs = []
    rng = np.random.RandomState(42)
    while len(negative_pairs) < len(positive_pairs) * 2:
        i, j = rng.randint(0, n, size=2)
        if i != j:
            pair = tuple(sorted([i, j]))
            if pair not in positive_set:
                negative_pairs.append(pair)

    positive_scores = [float(sim_matrix[a, b]) for a, b in positive_pairs]
    negative_scores = [float(sim_matrix[a, b]) for a, b in negative_pairs]

    y_true = [1] * len(positive_scores) + [0] * len(negative_scores)
    y_scores = positive_scores + negative_scores
    auc_roc = float(roc_auc_score(y_true, y_scores))

    pos_mean = float(np.mean(positive_scores))
    neg_mean = float(np.mean(negative_scores))
    gap = pos_mean - neg_mean

    # NN citation rate
    nn_has_citation = 0
    for i in range(n):
        nn_idx = np.argmax(sim_matrix[i])
        pair = tuple(sorted([i, nn_idx]))
        if pair in positive_set:
            nn_has_citation += 1
    nn_citation_rate = nn_has_citation / n

    # Subgroup analysis
    subgroup_results = {}
    for threshold in [1, 3, 5]:
        subgroup = [(a, b, s) for a, b, s in valid_pairs if s >= threshold]
        if subgroup:
            sub_scores = [float(sim_matrix[a, b]) for a, b, _ in subgroup]
            subgroup_results[f"shared>={threshold}"] = {
                "count": len(subgroup),
                "mean_similarity": round(float(np.mean(sub_scores)), 4),
            }

    return {
        "status": "PASSED",
        "falsified": auc_roc < 0.5,
        "num_positive_pairs": len(positive_pairs),
        "num_negative_pairs": len(negative_pairs),
        "auc_roc": round(auc_roc, 4),
        "positive_mean_similarity": round(pos_mean, 4),
        "negative_mean_similarity": round(neg_mean, 4),
        "similarity_gap": round(gap, 4),
        "nn_citation_rate": round(nn_citation_rate, 4),
        "subgroup_analysis": subgroup_results,
        "duration": time.time() - start,
    }


def run_adversarial_fast(
    sim_matrix: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
) -> Dict[str, Any]:
    """Fast adversarial benchmark (core metrics only)."""
    start = time.time()
    n = len(branches)
    k = 10

    lang_dominance = []
    for i in range(n):
        top_k_idx = np.argsort(sim_matrix[i])[-k:]
        neighbor_langs = languages[top_k_idx]
        same_lang_frac = np.mean(neighbor_langs == languages[i])
        lang_dominance.append(same_lang_frac)

    branch_coherence = []
    for i in range(n):
        top_k_idx = np.argsort(sim_matrix[i])[-k:]
        neighbor_branches = branches[top_k_idx]
        same_branch_frac = np.mean(neighbor_branches == branches[i])
        branch_coherence.append(same_branch_frac)

    # Dead zones: cross-branch pairs with sim > 0.95
    dead_zones_count = 0
    for i in range(n):
        top_20_idx = np.argsort(sim_matrix[i])[-20:]
        for j in top_20_idx:
            if i != j and branches[i] != branches[j] and sim_matrix[i, j] > 0.95:
                dead_zones_count += 1

    lang_dom_mean = float(np.mean(lang_dominance))
    branch_coh_mean = float(np.mean(branch_coherence))

    falsified = False
    falsification_reasons = []
    if lang_dom_mean > 0.9:
        falsified = True
        falsification_reasons.append(f"Language dominance {lang_dom_mean:.3f} > 0.9")
    if branch_coh_mean < 0.3:
        falsified = True
        falsification_reasons.append(f"Branch coherence {branch_coh_mean:.3f} < 0.3")
    if dead_zones_count > 5:
        falsified = True
        falsification_reasons.append(f"{dead_zones_count} pairs with sim>0.95 across branches")

    return {
        "status": "FALSIFIED" if falsified else "PASSED",
        "falsified": falsified,
        "falsification_reasons": falsification_reasons,
        "language_dominance_mean": round(lang_dom_mean, 4),
        "branch_coherence_mean": round(branch_coh_mean, 4),
        "dead_zones_gt095": dead_zones_count,
        "duration": time.time() - start,
    }


def run_branch_knn_fast(sim_matrix: np.ndarray, branches: np.ndarray) -> Dict[str, Any]:
    """Fast branch k-NN classification."""
    n = len(branches)
    k_values = [1, 3, 5, 10]
    results = {}
    for k in k_values:
        correct = 0
        for i in range(n):
            top_k_idx = np.argsort(sim_matrix[i])[-k:]
            neighbor_labels = branches[top_k_idx]
            majority = Counter(neighbor_labels).most_common(1)[0][0]
            if majority == branches[i]:
                correct += 1
        results[f"knn_accuracy@{k}"] = round(correct / n, 4) if n > 0 else 0
    n_labels = len(set(branches))
    results["random_baseline"] = round(1.0 / n_labels, 4) if n_labels > 0 else 0
    return results


def check_for_collapse_fast(sim_matrix: np.ndarray) -> Dict[str, Any]:
    """Fast collapse check."""
    n = sim_matrix.shape[0]
    mask = np.triu(np.ones((n, n), dtype=bool), k=1)
    upper_tri = sim_matrix[mask]

    mean_sim = float(np.mean(upper_tri))
    std_sim = float(np.std(upper_tri))
    near_identical = int(np.sum(upper_tri > 0.99))
    total_pairs = int(len(upper_tri))

    collapsed = mean_sim > 0.99 or std_sim < 0.01

    return {
        "mean_similarity": round(mean_sim, 4),
        "std_similarity": round(std_sim, 4),
        "near_identical_pairs_gt099": near_identical,
        "total_pairs": total_pairs,
        "fraction_near_identical": round(near_identical / total_pairs, 4) if total_pairs > 0 else 0,
        "collapsed": collapsed,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Main: Grid search over debiasing parameters
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    run_id = f"eval_cycle_13_{int(time.time())}"
    logger.info(f"Starting evaluation cycle 13: {run_id}")

    # Load data
    citations = load_corpus_citations()
    citation_pairs = build_shared_citation_pairs(citations, min_shared=1)
    metadata, baseline_768 = load_representations()

    # Parameter grid
    n_components_list = [1, 2, 3, 5]
    alpha_list = [0.3, 0.5, 0.7]

    logger.info(f"Parameter grid: n_components={n_components_list}, alpha={alpha_list}")
    logger.info(f"Total combinations: {len(n_components_list) * len(alpha_list)}")

    results = {
        "run_id": run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cycle": 13,
        "hypothesis": (
            "The debiased_citation_blended representation from cycle 12 achieved "
            "BOTH success criteria. This cycle tests sensitivity to n_pca_components "
            "(1, 2, 3, 5) and alpha (0.3, 0.5, 0.7) to map the Pareto frontier "
            "and identify robust parameter regions."
        ),
        "frozen_sample": "1000 BGer decisions (2020-2024) from fractal-map baseline",
        "frozen_metrics": [
            "citation_heritage_auc_roc",
            "language_dominance_mean",
            "branch_coherence_mean",
            "branch_knn_accuracy@5",
            "dead_zones_gt095",
            "collapse_mean_similarity",
        ],
        "success_rule": (
            "language_dominance < 0.85 AND citation_heritage_AUC > 0.65; "
            "no dimensional collapse (mean_similarity < 0.99)"
        ),
        "parameter_grid": {
            "n_pca_components": n_components_list,
            "alpha": alpha_list,
        },
        "grid_results": {},
        "pareto_frontier": [],
        "anchor_comparison": {},
    }

    # Also test the anchor: n=2, alpha=0.5 (cycle 12's exact setting)
    anchor_key = "n2_a0.5"

    for n_comp in n_components_list:
        for alpha in alpha_list:
            key = f"n{n_comp}_a{alpha}"
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing: n_pca_components={n_comp}, alpha={alpha}")
            logger.info(f"{'='*60}")

            # Create representation
            emb, creation_info = create_debiased_citation_blended(
                baseline_768, metadata, citations,
                n_pca_components=n_comp, alpha=alpha, dims=64,
            )

            # Prepare valid data
            emb_valid, branches, languages, chambers, legal_areas, valid_idx = \
                prepare_valid_data(metadata, emb)

            emb_norm = normalize_embeddings(emb_valid)
            sim_matrix = compute_similarity(emb_norm)

            # Run benchmarks
            citation = run_citation_heritage_fast(sim_matrix, metadata, valid_idx, citation_pairs)
            adversarial = run_adversarial_fast(sim_matrix, branches, languages)
            branch_knn = run_branch_knn_fast(sim_matrix, branches)
            collapse = check_for_collapse_fast(sim_matrix)

            # Success criteria
            auc = citation.get("auc_roc", 0)
            lang_dom = adversarial.get("language_dominance_mean", 1.0)
            collapsed = collapse.get("collapsed", True)
            branch_acc = branch_knn.get("knn_accuracy@5", 0)

            both_criteria = (lang_dom < 0.85) and (auc > 0.65) and (not collapsed)

            grid_entry = {
                "n_pca_components": n_comp,
                "alpha": alpha,
                "creation_info": creation_info,
                "citation_heritage_auc": auc,
                "language_dominance": lang_dom,
                "branch_coherence": adversarial.get("branch_coherence_mean", 0),
                "dead_zones_gt095": adversarial.get("dead_zones_gt095", 0),
                "branch_knn_accuracy@5": branch_acc,
                "collapse_mean_similarity": collapse.get("mean_similarity", 0),
                "collapse_std_similarity": collapse.get("std_similarity", 0),
                "collapsed": collapsed,
                "both_criteria_met": both_criteria,
                "citation_heritage": citation,
                "adversarial": adversarial,
                "branch_knn": branch_knn,
                "collapse_check": collapse,
            }

            results["grid_results"][key] = grid_entry

            status = "BOTH_MET" if both_criteria else "FAILED"
            logger.info(f"  AUC={auc:.4f}, lang_dom={lang_dom:.4f}, "
                       f"branch_knn={branch_acc:.4f}, collapsed={collapsed} "
                       f"=> {status}")

            # Track Pareto frontier
            results["pareto_frontier"].append({
                "n_pca_components": n_comp,
                "alpha": alpha,
                "citation_heritage_auc": auc,
                "language_dominance": lang_dom,
                "branch_knn_accuracy@5": branch_acc,
                "both_criteria_met": both_criteria,
                "collapsed": collapsed,
            })

    # ─── Pareto frontier analysis ────────────────────────────────────────────
    logger.info(f"\n{'='*60}")
    logger.info("PARETO FRONTIER ANALYSIS")
    logger.info(f"{'='*60}")

    # Find best by citation heritage AUC among those meeting both criteria
    candidates = [p for p in results["pareto_frontier"] if p["both_criteria_met"]]
    if candidates:
        best_auc = max(candidates, key=lambda x: x["citation_heritage_auc"])
        best_branch = max(candidates, key=lambda x: x["branch_knn_accuracy@5"])
        lowest_lang_dom = min(candidates, key=lambda x: x["language_dominance"])

        results["best_by_auc"] = best_auc
        results["best_by_branch_knn"] = best_branch
        results["lowest_language_dominance"] = lowest_lang_dom

        logger.info(f"  Best by AUC: n={best_auc['n_pca_components']}, "
                   f"alpha={best_auc['alpha']}, AUC={best_auc['citation_heritage_auc']:.4f}")
        logger.info(f"  Best by branch k-NN: n={best_branch['n_pca_components']}, "
                   f"alpha={best_branch['alpha']}, kNN={best_branch['branch_knn_accuracy@5']:.4f}")
        logger.info(f"  Lowest lang dom: n={lowest_lang_dom['n_pca_components']}, "
                   f"alpha={lowest_lang_dom['alpha']}, dom={lowest_lang_dom['language_dominance']:.4f}")
    else:
        results["best_by_auc"] = None
        results["best_by_branch_knn"] = None
        results["lowest_language_dominance"] = None
        logger.info("  No candidates meet both criteria!")

    # Compare to anchor (cycle 12's n=2, alpha=0.5)
    anchor = results["grid_results"].get(anchor_key)
    if anchor:
        results["anchor_comparison"] = {
            "n_pca_components": 2,
            "alpha": 0.5,
            "citation_heritage_auc": anchor["citation_heritage_auc"],
            "language_dominance": anchor["language_dominance"],
            "branch_knn_accuracy@5": anchor["branch_knn_accuracy@5"],
            "both_criteria_met": anchor["both_criteria_met"],
        }

    # Sensitivity summary
    logger.info(f"\n{'='*60}")
    logger.info("SENSITIVITY SUMMARY")
    logger.info(f"{'='*60}")

    # By n_components (averaged over alpha)
    for n_comp in n_components_list:
        entries = [results["grid_results"][f"n{n_comp}_a{a}"] for a in alpha_list]
        avg_auc = np.mean([e["citation_heritage_auc"] for e in entries])
        avg_dom = np.mean([e["language_dominance"] for e in entries])
        avg_knn = np.mean([e["branch_knn_accuracy@5"] for e in entries])
        n_pass = sum(1 for e in entries if e["both_criteria_met"])
        logger.info(f"  n_components={n_comp}: avg_AUC={avg_auc:.4f}, "
                   f"avg_dom={avg_dom:.4f}, avg_kNN={avg_knn:.4f}, "
                   f"pass={n_pass}/{len(alpha_list)}")

    # By alpha (averaged over n_components)
    for alpha in alpha_list:
        entries = [results["grid_results"][f"n{n}_a{alpha}"] for n in n_components_list]
        avg_auc = np.mean([e["citation_heritage_auc"] for e in entries])
        avg_dom = np.mean([e["language_dominance"] for e in entries])
        avg_knn = np.mean([e["branch_knn_accuracy@5"] for e in entries])
        n_pass = sum(1 for e in entries if e["both_criteria_met"])
        logger.info(f"  alpha={alpha}: avg_AUC={avg_auc:.4f}, "
                   f"avg_dom={avg_dom:.4f}, avg_kNN={avg_knn:.4f}, "
                   f"pass={n_pass}/{len(n_components_list)}")

    # Key findings
    findings = []
    n_pass_total = sum(1 for p in results["pareto_frontier"] if p["both_criteria_met"])
    findings.append(
        f"Grid search: {n_pass_total}/{len(n_components_list)*len(alpha_list)} "
        f"parameter combinations meet BOTH success criteria"
    )

    if results["best_by_auc"]:
        b = results["best_by_auc"]
        findings.append(
            f"Best by citation heritage AUC: n_pca={b['n_pca_components']}, "
            f"alpha={b['alpha']}, AUC={b['citation_heritage_auc']:.4f}"
        )

    if results["best_by_branch_knn"]:
        b = results["best_by_branch_knn"]
        findings.append(
            f"Best by branch k-NN: n_pca={b['n_pca_components']}, "
            f"alpha={b['alpha']}, kNN={b['branch_knn_accuracy@5']:.4f}"
        )

    # Check if anchor (n=2, a=0.5) is still best
    if anchor and results["best_by_auc"]:
        if (anchor["citation_heritage_auc"] == results["best_by_auc"]["citation_heritage_auc"]
                and anchor["language_dominance"] == results["best_by_auc"]["language_dominance"]):
            findings.append(
                "Anchor (n=2, alpha=0.5) remains optimal — no parameter improvement found"
            )
        else:
            findings.append(
                "Anchor (n=2, alpha=0.5) is NOT optimal — better parameters exist"
            )

    # Collapse analysis
    n_collapsed = sum(1 for p in results["pareto_frontier"] if p["collapsed"])
    findings.append(f"Collapse: {n_collapsed}/{len(results['pareto_frontier'])} combinations collapsed")

    # Sensitivity to n_components
    auc_range_by_n = {}
    for n_comp in n_components_list:
        aucs = [results["grid_results"][f"n{n_comp}_a{a}"]["citation_heritage_auc"] for a in alpha_list]
        auc_range_by_n[n_comp] = max(aucs) - min(aucs)
    max_range_n = max(auc_range_by_n.values())
    findings.append(
        f"Sensitivity to n_components: max AUC range across alpha = {max_range_n:.4f}"
    )

    results["key_findings"] = findings

    for f in findings:
        logger.info(f"  FINDING: {f}")

    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_path = OUTPUT_DIR / "cycle_13_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Results saved to {results_path}")

    return results


if __name__ == "__main__":
    results = main()
    print("\n=== CYCLE 13 COMPLETE ===")
    print(f"Run ID: {results['run_id']}")
    n_pass = sum(1 for p in results["pareto_frontier"] if p["both_criteria_met"])
    print(f"Parameter combinations meeting both criteria: {n_pass}/12")
    if results.get("best_by_auc"):
        b = results["best_by_auc"]
        print(f"Best by AUC: n_pca={b['n_pca_components']}, alpha={b['alpha']}, AUC={b['citation_heritage_auc']:.4f}")
