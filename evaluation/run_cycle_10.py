#!/usr/bin/env python3
"""
Evaluation Cycle 10: Citation-Heritage Benchmark + Benchmark Sensitivity Validation

Hypothesis: A citation-heritage benchmark built from the real corpus citation graph
(2105 edges, 1628 cited nodes) will discriminate between representations based on
their ability to place citation-linked decisions close together. Additionally,
a deliberately degraded representation should fail all benchmarks (sanity check).

Product decision: If the citation-heritage benchmark passes on at least one
representation and correctly degrades on the random baseline, it becomes a
reliable benchmark for the legal-distance lane.

Frozen before observation:
- Corpus: 1000 BGer decisions from fractal-map baseline metadata
- Embeddings: baseline (768-dim), language_debiased_pca2 (768-dim),
              embeddings_blended (64-dim), embeddings_graph_only (64-dim)
- Citation graph: from corpus canonical data (bger_2000plus_slice_1000.jsonl)
- Success rule: Citation-heritage AUC > 0.6 on at least one representation;
  random-degraded AUC < 0.55; dead zone count discriminating.
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
from sklearn.metrics import roc_auc_score, normalized_mutual_info_score
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


def load_corpus_citations() -> Dict[str, List[str]]:
    """Load citation graph from canonical corpus."""
    logger.info(f"Loading corpus citations from {CORPUS_FILE}")
    citations = {}
    with open(CORPUS_FILE) as f:
        for line in f:
            d = json.loads(line)
            did = d["decision_id"]
            cited = d.get("cited_decisions", [])
            if cited:
                citations[did] = cited
    logger.info(f"  Loaded {len(citations)} decisions with citations")
    total_edges = sum(len(v) for v in citations.values())
    logger.info(f"  Total citation edges: {total_edges}")
    return citations


def build_citation_graph(citations: Dict[str, List[str]]) -> Tuple[Set[str], Set[Tuple[str, str]]]:
    """Build citation graph: (cited_nodes, edges)."""
    cited_nodes = set()
    edges = set()
    for src, targets in citations.items():
        for tgt in targets:
            cited_nodes.add(tgt)
            edges.add((src, tgt))
    return cited_nodes, edges


def build_shared_citation_pairs(
    citations: Dict[str, List[str]], 
    min_shared: int = 1,
    max_pairs: int = 5000
) -> List[Tuple[str, str, int]]:
    """Build pairs of decisions that share at least min_shared citations."""
    # Build reverse index: citation -> decisions that cite it
    reverse = defaultdict(set)
    for did, cited_list in citations.items():
        for c in cited_list:
            reverse[c].add(did)
    
    # Count shared citations between pairs
    pair_shared = Counter()
    for citation, deciders in reverse.items():
        dec_list = list(deciders)
        for i in range(len(dec_list)):
            for j in range(i + 1, len(dec_list)):
                pair = tuple(sorted([dec_list[i], dec_list[j]]))
                pair_shared[pair] += 1
    
    # Filter by min_shared and limit
    pairs = [(a, b, n) for (a, b), n in pair_shared.items() if n >= min_shared]
    pairs.sort(key=lambda x: -x[2])  # Most shared first
    pairs = pairs[:max_pairs]
    
    logger.info(f"  Citation pairs with >= {min_shared} shared: {len(pairs)}")
    if pairs:
        logger.info(f"  Max shared: {pairs[0][2]}, Median shared: {pairs[len(pairs)//2][2]}")
    return pairs


def load_representations():
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
    """Filter to valid decisions with known branch."""
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
# Citation-Heritage Benchmark (NEW in cycle 10)
# ═══════════════════════════════════════════════════════════════════════════════

def run_citation_heritage_benchmark(
    sim_matrix: np.ndarray,
    metadata: List[Dict],
    valid_indices: List[int],
    citation_pairs: List[Tuple[str, str, int]],
    representation_name: str,
    k_values: List[int] = [1, 5, 10, 20, 50],
) -> Dict[str, Any]:
    """
    Benchmark: decisions that share citations should be closer than random pairs.
    
    Uses the real citation graph from the corpus as weak supervision.
    """
    logger.info(f"Running citation-heritage benchmark for {representation_name}")
    start = time.time()
    
    n = sim_matrix.shape[0]
    
    # Build ID -> local index mapping
    id_to_local = {}
    for local_idx, global_idx in enumerate(valid_indices):
        did = metadata[global_idx]["decision_id"]
        id_to_local[did] = local_idx
    
    # Filter citation pairs to those where both decisions are in our valid set
    valid_pairs = []
    for d1, d2, shared_count in citation_pairs:
        if d1 in id_to_local and d2 in id_to_local:
            valid_pairs.append((id_to_local[d1], id_to_local[d2], shared_count))
    
    logger.info(f"  Valid citation pairs: {len(valid_pairs)} / {len(citation_pairs)}")
    
    if len(valid_pairs) < 10:
        return {
            "representation": representation_name,
            "status": "INSUFFICIENT_DATA",
            "num_valid_pairs": len(valid_pairs),
        }
    
    # Build positive pairs (cite each other)
    positive_pairs = [(a, b) for a, b, _ in valid_pairs]
    
    # Build negative pairs: random pairs that do NOT share citations
    positive_set = set(tuple(sorted([a, b])) for a, b, _ in valid_pairs)
    negative_pairs = []
    rng = np.random.RandomState(42)
    attempts = 0
    while len(negative_pairs) < len(positive_pairs) * 2 and attempts < len(positive_pairs) * 10:
        i, j = rng.randint(0, n, size=2)
        if i != j:
            pair = tuple(sorted([i, j]))
            if pair not in positive_set:
                negative_pairs.append(pair)
        attempts += 1
    
    logger.info(f"  Positive pairs: {len(positive_pairs)}, Negative pairs: {len(negative_pairs)}")
    
    # Compute similarity scores
    positive_scores = [float(sim_matrix[a, b]) for a, b in positive_pairs]
    negative_scores = [float(sim_matrix[a, b]) for a, b in negative_pairs]
    
    # AUC-ROC
    y_true = [1] * len(positive_scores) + [0] * len(negative_scores)
    y_scores = positive_scores + negative_scores
    auc_roc = float(roc_auc_score(y_true, y_scores))
    
    # Mean similarity gap
    pos_mean = float(np.mean(positive_scores))
    neg_mean = float(np.mean(negative_scores))
    gap = pos_mean - neg_mean
    
    # Precision@k: for each positive pair, are they neighbors?
    precision_at_k = {}
    for k in k_values:
        precisions = []
        for a, b in positive_pairs:
            # How many of a's top-k neighbors include b?
            top_k = set(np.argsort(sim_matrix[a])[-k:])
            precisions.append(1.0 if b in top_k else 0.0)
            top_k_b = set(np.argsort(sim_matrix[b])[-k:])
            precisions.append(1.0 if a in top_k_b else 0.0)
        precision_at_k[f"precision@{k}"] = round(float(np.mean(precisions)), 4)
    
    # Neighbor quality: for each decision, check if its nearest neighbor shares citations
    nn_has_citation = 0
    for i in range(n):
        nn_idx = np.argmax(sim_matrix[i])
        pair = tuple(sorted([i, nn_idx]))
        if pair in positive_set:
            nn_has_citation += 1
    nn_citation_rate = nn_has_citation / n
    
    # Subgroup analysis by shared citation count
    subgroup_results = {}
    for threshold in [1, 2, 3, 5]:
        subgroup = [(a, b, s) for a, b, s in valid_pairs if s >= threshold]
        if subgroup:
            sub_scores = [float(sim_matrix[a, b]) for a, b, _ in subgroup]
            subgroup_results[f"shared>={threshold}"] = {
                "count": len(subgroup),
                "mean_similarity": round(float(np.mean(sub_scores)), 4),
                "std_similarity": round(float(np.std(sub_scores)), 4),
            }
    
    # Falsification checks
    falsified = False
    falsification_reasons = []
    
    if auc_roc < 0.5:
        falsified = True
        falsification_reasons.append(f"AUC-ROC {auc_roc:.3f} < 0.5: citation pairs less similar than random")
    
    if gap < 0:
        falsified = True
        falsification_reasons.append(f"Negative similarity gap {gap:.4f}: citation pairs less similar than random")
    
    duration = time.time() - start
    status = "FALSIFIED" if falsified else "PASSED"
    
    return {
        "representation": representation_name,
        "status": status,
        "falsified": falsified,
        "falsification_reasons": falsification_reasons,
        "num_positive_pairs": len(positive_pairs),
        "num_negative_pairs": len(negative_pairs),
        "auc_roc": round(auc_roc, 4),
        "positive_mean_similarity": round(pos_mean, 4),
        "negative_mean_similarity": round(neg_mean, 4),
        "similarity_gap": round(gap, 4),
        "precision_at_k": precision_at_k,
        "nn_citation_rate": round(nn_citation_rate, 4),
        "subgroup_analysis": subgroup_results,
        "duration": duration,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Adversarial Falsification (from cycle 8/9)
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
    
    # Language dominance
    lang_dominance = []
    for i in range(n):
        top_k_idx = np.argsort(sim_matrix[i])[-k:]
        neighbor_langs = languages[top_k_idx]
        same_lang_frac = np.mean(neighbor_langs == languages[i])
        lang_dominance.append(same_lang_frac)
    lang_dominance = np.array(lang_dominance)
    
    # Branch coherence
    branch_coherence = []
    for i in range(n):
        top_k_idx = np.argsort(sim_matrix[i])[-k:]
        neighbor_branches = branches[top_k_idx]
        same_branch_frac = np.mean(neighbor_branches == branches[i])
        branch_coherence.append(same_branch_frac)
    branch_coherence = np.array(branch_coherence)
    
    # Dead zones
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
    
    # Falsification
    falsified = False
    falsification_reasons = []
    
    if np.mean(lang_dominance) > 0.9:
        falsified = True
        falsification_reasons.append(
            f"Language dominance {np.mean(lang_dominance):.3f} > 0.9"
        )
    
    if np.mean(branch_coherence) < 0.3:
        falsified = True
        falsification_reasons.append(
            f"Branch coherence {np.mean(branch_coherence):.3f} < 0.3"
        )
    
    high_sim_cross = [dz for dz in dead_zones if dz["similarity"] > 0.95]
    if len(high_sim_cross) > 5:
        falsified = True
        falsification_reasons.append(
            f"{len(high_sim_cross)} pairs with sim>0.95 across branches"
        )
    
    duration = time.time() - start
    status = "FALSIFIED" if falsified else "PASSED"
    
    return {
        "representation": representation_name,
        "status": status,
        "falsified": falsified,
        "falsification_reasons": falsification_reasons,
        "language_dominance_mean": round(float(np.mean(lang_dominance)), 4),
        "branch_coherence_mean": round(float(np.mean(branch_coherence)), 4),
        "dead_zones_gt095": len(high_sim_cross),
        "dead_zones_total": len(dead_zones),
        "duration": duration,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TF Metadata Human-Indexing Benchmark (from cycle 8/9)
# ═══════════════════════════════════════════════════════════════════════════════

def _knn_classification(sim_matrix, labels, k_values):
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
    
    branch_results = _knn_classification(sim_matrix, branches, [1, 3, 5, 10])
    chamber_results = _knn_classification(sim_matrix, chambers, [1, 3, 5, 10])
    area_results = _knn_classification(sim_matrix, legal_areas, [1, 3, 5, 10])
    
    duration = time.time() - start
    
    return {
        "representation": representation_name,
        "num_decisions": len(branches),
        "branch_knn": branch_results,
        "chamber_knn": chamber_results,
        "legal_area_knn": area_results,
        "summary": {
            "branch_knn_accuracy@5": branch_results.get("knn_accuracy@5", 0),
            "chamber_knn_accuracy@5": chamber_results.get("knn_accuracy@5", 0),
            "legal_area_knn_accuracy@5": area_results.get("knn_accuracy@5", 0),
        },
        "duration": duration,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Deliberately Degraded Representation (Sanity Check)
# ═══════════════════════════════════════════════════════════════════════════════

def create_degraded_representation(embeddings: np.ndarray, seed: int = 42) -> np.ndarray:
    """
    Create a deliberately degraded representation by shuffling rows.
    This matches decision i to a random decision j's embedding, completely
    destroying the embedding structure while preserving the distribution.
    
    Note: dimension permutation (previous approach) is ineffective for cosine
    similarity in high dimensions because it preserves the dot product distribution.
    Row shuffling destroys all meaningful pairwise relationships.
    """
    rng = np.random.RandomState(seed)
    n = embeddings.shape[0]
    perm = rng.permutation(n)
    degraded = embeddings[perm]
    return degraded


# ═══════════════════════════════════════════════════════════════════════════════
# Main execution
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    run_id = f"eval_cycle_10_{int(time.time())}"
    logger.info(f"Starting evaluation cycle 10: {run_id}")
    
    # Load corpus citations
    citations = load_corpus_citations()
    cited_nodes, edges = build_citation_graph(citations)
    logger.info(f"Citation graph: {len(cited_nodes)} cited nodes, {len(edges)} edges")
    
    # Build citation pairs
    citation_pairs = build_shared_citation_pairs(citations, min_shared=1)
    
    # Load all representations
    metadata, representations = load_representations()
    
    # Create degraded representation from baseline
    baseline_emb = representations["baseline"]
    degraded_emb = create_degraded_representation(baseline_emb)
    representations["random_degraded"] = degraded_emb
    
    results = {
        "run_id": run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cycle": 10,
        "hypothesis": (
            "Citation-heritage benchmark built from real corpus citation graph "
            "discriminates between representations. Deliberately degraded representation "
            "should fail all benchmarks."
        ),
        "frozen_sample": "1000 BGer decisions (2020-2024) from fractal-map baseline",
        "frozen_metrics": [
            "citation_heritage_auc_roc",
            "citation_heritage_similarity_gap",
            "language_dominance_mean",
            "branch_coherence_mean",
            "branch_knn_accuracy@5",
            "dead_zones_gt095",
        ],
        "success_rule": (
            "Citation-heritage AUC > 0.6 on at least one representation; "
            "random-degraded AUC < 0.55; dead zone count discriminating"
        ),
        "citation_graph_stats": {
            "decisions_with_citations": len(citations),
            "cited_nodes": len(cited_nodes),
            "edges": len(edges),
            "citation_pairs_at_least_1": len(citation_pairs),
        },
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
        
        # Citation-heritage benchmark
        citation_heritage = run_citation_heritage_benchmark(
            sim_matrix, metadata, valid_idx, citation_pairs, name
        )
        
        # Adversarial benchmark
        adversarial = run_adversarial_benchmark(sim_matrix, branches, languages, name)
        
        # TF metadata benchmark
        tf_metadata = run_tf_metadata_benchmark(
            sim_matrix, branches, chambers, legal_areas, name
        )
        
        results["representations"][name] = {
            "citation_heritage": citation_heritage,
            "adversarial": adversarial,
            "tf_metadata": tf_metadata,
        }
    
    # Cross-representation comparison
    logger.info(f"\n{'='*60}")
    logger.info("COMPARISON")
    logger.info(f"{'='*60}")
    
    comparison = {
        "citation_heritage_auc": {},
        "citation_heritage_gap": {},
        "adversarial_status": {},
        "language_dominance": {},
        "branch_coherence": {},
        "dead_zones_gt095": {},
        "branch_knn_accuracy": {},
    }
    
    for name, res in results["representations"].items():
        ch = res["citation_heritage"]
        adv = res["adversarial"]
        tf = res["tf_metadata"]
        
        comparison["citation_heritage_auc"][name] = ch.get("auc_roc", None)
        comparison["citation_heritage_gap"][name] = ch.get("similarity_gap", None)
        comparison["adversarial_status"][name] = adv["status"]
        comparison["language_dominance"][name] = adv["language_dominance_mean"]
        comparison["branch_coherence"][name] = adv["branch_coherence_mean"]
        comparison["dead_zones_gt095"][name] = adv["dead_zones_gt095"]
        comparison["branch_knn_accuracy"][name] = tf["summary"]["branch_knn_accuracy@5"]
        
        logger.info(f"  {name}:")
        logger.info(f"    Citation heritage AUC: {ch.get('auc_roc', 'N/A')}")
        logger.info(f"    Similarity gap: {ch.get('similarity_gap', 'N/A')}")
        logger.info(f"    Adversarial: {adv['status']}")
        logger.info(f"    Language dominance: {adv['language_dominance_mean']:.3f}")
        logger.info(f"    Branch coherence: {adv['branch_coherence_mean']:.3f}")
        logger.info(f"    Dead zones >0.95: {adv['dead_zones_gt095']}")
        logger.info(f"    Branch k-NN@5: {tf['summary']['branch_knn_accuracy@5']:.3f}")
    
    results["comparison"] = comparison
    
    # Key findings
    findings = []
    
    # Sanity check: degraded representation should fail
    degraded_auc = comparison["citation_heritage_auc"].get("random_degraded")
    if degraded_auc is not None and degraded_auc < 0.55:
        findings.append(
            f"SANITY CHECK PASSED: Random-degraded AUC {degraded_auc:.3f} < 0.55"
        )
    elif degraded_auc is not None:
        findings.append(
            f"SANITY CHECK CONCERN: Random-degraded AUC {degraded_auc:.3f} >= 0.55"
        )
    
    # Citation heritage discrimination
    for name in ["baseline", "language_debiased_pca2", "citation_blended", "citation_graph_only"]:
        auc = comparison["citation_heritage_auc"].get(name)
        if auc is not None:
            findings.append(f"Citation heritage AUC ({name}): {auc:.3f}")
    
    # Best representation
    valid_aucs = {k: v for k, v in comparison["citation_heritage_auc"].items() 
                  if v is not None and k != "random_degraded"}
    if valid_aucs:
        best = max(valid_aucs, key=valid_aucs.get)
        findings.append(f"BEST citation heritage: {best} (AUC={valid_aucs[best]:.3f})")
    
    # Dead zone discrimination
    findings.append(
        f"Dead zones: baseline={comparison['dead_zones_gt095']['baseline']}, "
        f"debiased={comparison['dead_zones_gt095']['language_debiased_pca2']}, "
        f"blended={comparison['dead_zones_gt095']['citation_blended']}, "
        f"graph_only={comparison['dead_zones_gt095']['citation_graph_only']}, "
        f"degraded={comparison['dead_zones_gt095']['random_degraded']}"
    )
    
    # Language dominance
    findings.append(
        f"Language dominance: baseline={comparison['language_dominance']['baseline']:.3f}, "
        f"degraded={comparison['language_dominance']['random_degraded']:.3f}"
    )
    
    results["key_findings"] = findings
    
    for f in findings:
        logger.info(f"  FINDING: {f}")
    
    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_path = OUTPUT_DIR / "cycle_10_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Results saved to {results_path}")
    
    return results


if __name__ == "__main__":
    results = main()
    print("\n=== CYCLE 10 COMPLETE ===")
    print(f"Run ID: {results['run_id']}")
    for name, auc in results["comparison"]["citation_heritage_auc"].items():
        print(f"  {name}: citation heritage AUC = {auc}")
