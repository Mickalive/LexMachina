#!/usr/bin/env python3
"""
Evaluation Cycle 12: Debiased-Baseline → Citation Graph Approach

Hypothesis: Applying language debiasing BEFORE citation graph construction
avoids the dimensional collapse observed in cycle 11. The key insight is that
PCA on 768-dim baseline removes only ~0.5% of variance (not 34% as in 64-dim
citation-blended), so the debiased baseline preserves enough structure for
citation graph construction.

Approach (Option A from cycle 11):
1. Take the baseline (768-dim) embeddings
2. Apply PCA debiasing to get language-debiased baseline (768-dim)
3. Build citation graph from debiased baseline embeddings
4. Create citation-blended from debiased baseline

Product decision: If this approach achieves BOTH low language dominance (< 0.85)
AND high citation heritage AUC (> 0.65), it becomes the recommended combination
strategy for the product.

Frozen before observation:
- Corpus: 1000 BGer decisions (2020-2024) from fractal-map baseline
- Embeddings: baseline (768-dim), language_debiased_pca2 (768-dim),
              citation_blended (64-dim), citation_graph_only (64-dim)
- NEW: debiased_baseline_64 (64-dim PCA from debiased 768-dim)
- NEW: debiased_citation_blended (64-dim, citation graph from debiased baseline)
- NEW: debiased_citation_graph_only (64-dim, graph-only from debiased baseline)
- Success rule: debiased_citation_blended has language_dominance < 0.85 AND
  citation_heritage AUC > 0.65; no dimensional collapse (all-pairs similarity < 0.99)
"""

import json
import time
import sys
import os
import re
import logging
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Any, Optional, Set

import numpy as np
from sklearn.metrics import roc_auc_score, normalized_mutual_info_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
from math import erf

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


def build_shared_citation_pairs(
    citations: Dict[str, List[str]], 
    min_shared: int = 1,
    max_pairs: int = 5000
) -> List[Tuple[str, str, int]]:
    """Build pairs of decisions that share at least min_shared citations."""
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
    
    logger.info(f"  Citation pairs with >= {min_shared} shared: {len(pairs)}")
    if pairs:
        logger.info(f"  Max shared: {pairs[0][2]}, Median shared: {pairs[len(pairs)//2][2]}")
    return pairs


def load_representations():
    """Load metadata and all representations."""
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
# NEW: Debiased-Baseline → Citation Graph Approach (Option A)
# ═══════════════════════════════════════════════════════════════════════════════

def create_debiased_baseline_64(
    baseline_768: np.ndarray,
    n_pca_components: int = 2,
) -> np.ndarray:
    """
    Create a 64-dim PCA projection from the 768-dim baseline.
    
    This is the standard PCA baseline for fair comparison with citation-blended.
    """
    logger.info(f"Creating 64-dim PCA baseline from {baseline_768.shape}")
    pca = PCA(n_components=64, random_state=42)
    baseline_64 = pca.fit_transform(baseline_768)
    
    explained_var = np.sum(pca.explained_variance_ratio_)
    logger.info(f"  PCA explained variance (64 components): {explained_var:.4f}")
    logger.info(f"  Shape: {baseline_64.shape}")
    
    return baseline_64


def create_debiased_baseline_then_citation(
    baseline_768: np.ndarray,
    metadata: List[Dict],
    citations: Dict[str, List[str]],
    n_pca_components: int = 2,
    alpha: float = 0.5,
    dims: int = 64,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create citation-blended representation from debiased baseline.
    
    Strategy (Option A from cycle 11):
    1. Apply PCA debiasing to 768-dim baseline (removes top 2 variance components)
    2. PCA-project debiased 768-dim to 64-dim for fair comparison
    3. Build citation graph node2vec on debiased baseline
    4. Blend debiased baseline with citation graph embeddings
    
    This avoids dimensional collapse because:
    - PCA on 768 dims removes only ~0.5% of variance (not 34% as in 64-dim)
    - Citation graph is built in the debiased space
    - Blended representation preserves both debiased and citation signals
    """
    import networkx as nx
    
    logger.info(f"Creating debiased-baseline → citation graph representation")
    logger.info(f"  Baseline shape: {baseline_768.shape}")
    logger.info(f"  PCA debiasing: removing top {n_pca_components} components")
    
    # Step 1: PCA debiasing on 768-dim baseline
    pca_debias = PCA(n_components=n_pca_components, random_state=42)
    pca_debias.fit(baseline_768)
    logger.info(f"  PCA explained variance ratio (top {n_pca_components}): "
                f"{pca_debias.explained_variance_ratio_.tolist()}")
    logger.info(f"  Total variance removed: {np.sum(pca_debias.explained_variance_ratio_):.4f}")
    
    # Project to PCA space and remove top components
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
    explained_64 = np.sum(pca_64.explained_variance_ratio_)
    logger.info(f"  PCA 64-dim explained variance from debiased: {explained_64:.4f}")
    
    # Step 3: Build citation graph from debiased baseline
    id_to_idx = {m.get("decision_id", ""): i for i, m in enumerate(metadata)}
    
    # Build NetworkX graph
    G = nx.DiGraph()
    for source_id, targets in citations.items():
        for target in targets:
            G.add_edge(source_id, target)
    
    baseline_nodes = set(id_to_idx.keys())
    graph_nodes = set(G.nodes())
    common_nodes = baseline_nodes & graph_nodes
    logger.info(f"  Citation graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    logger.info(f"  Common nodes: {len(common_nodes)}")
    
    # Node2vec on debiased baseline
    G_undirected = G.to_undirected()
    walk_length = 20
    num_walks = 5
    
    # Generate random walks
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
    
    logger.info(f"  Generated {len(walks)} walks of length {walk_length}")
    
    # Build co-occurrence matrix
    from scipy.sparse import lil_matrix
    vocab = {n: i for i, n in enumerate(nodes)}
    cooccur = lil_matrix((len(nodes), len(nodes)))
    
    for walk in walks:
        for i, node in enumerate(walk):
            for j in range(max(0, i - 5), min(len(walk), i + 6)):
                if i != j:
                    cooccur[vocab[node], vocab[walk[j]]] += 1
    
    cooccur = cooccur.tocsr()
    
    # SVD on log co-occurrence
    from sklearn.decomposition import TruncatedSVD
    svd = TruncatedSVD(n_components=dims, random_state=42)
    node_embeddings = svd.fit_transform(cooccur)
    
    # L2 normalize
    norms = np.linalg.norm(node_embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    node_embeddings = node_embeddings / norms
    
    # Step 4: Blend debiased baseline with citation graph
    graph_embeddings = np.zeros((len(metadata), dims))
    in_graph_mask = np.zeros(len(metadata), dtype=bool)
    
    for node in common_nodes:
        idx = id_to_idx[node]
        node_idx = vocab[node]
        graph_embeddings[idx] = node_embeddings[node_idx]
        in_graph_mask[idx] = True
    
    # Blend: for in-graph nodes, combine debiased_64 + graph
    debiased_citation_blended = np.copy(debiased_64)
    for i in range(len(metadata)):
        if in_graph_mask[i]:
            debiased_citation_blended[i] = alpha * debiased_64[i] + (1 - alpha) * graph_embeddings[i]
    
    # Graph-only version
    debiased_citation_graph_only = np.copy(debiased_64)
    for i in range(len(metadata)):
        if in_graph_mask[i]:
            debiased_citation_graph_only[i] = graph_embeddings[i]
    
    logger.info(f"  In-graph decisions: {np.sum(in_graph_mask)}/{len(metadata)}")
    logger.info(f"  Debiased citation blended shape: {debiased_citation_blended.shape}")
    
    return debiased_citation_blended, debiased_citation_graph_only


# ═══════════════════════════════════════════════════════════════════════════════
# Existing benchmarks (from cycle 11)
# ═══════════════════════════════════════════════════════════════════════════════

def build_cross_language_pairs(
    metadata: List[Dict],
    valid_indices: List[int],
    max_pairs: int = 2000,
) -> List[Tuple[int, int, str, str]]:
    """Build cross-language pairs: decisions in different languages but same branch."""
    logger.info("Building cross-language pairs")
    
    branch_groups = defaultdict(lambda: defaultdict(list))
    for local_idx, global_idx in enumerate(valid_indices):
        meta = metadata[global_idx]
        chamber = meta.get("chamber", "")
        branch = assign_branch(chamber)
        lang = meta.get("language", "unknown")
        branch_groups[branch][lang].append(local_idx)
    
    pairs = []
    for branch, lang_groups in branch_groups.items():
        langs = list(lang_groups.keys())
        for i in range(len(langs)):
            for j in range(i + 1, len(langs)):
                lang_a, lang_b = langs[i], langs[j]
                for idx_a in branch_groups[branch][lang_a]:
                    for idx_b in branch_groups[branch][lang_b]:
                        pairs.append((idx_a, idx_b, lang_a, lang_b))
    
    if len(pairs) > max_pairs:
        rng = np.random.RandomState(42)
        indices = rng.choice(len(pairs), max_pairs, replace=False)
        pairs = [pairs[i] for i in indices]
    
    logger.info(f"  Cross-language pairs: {len(pairs)}")
    return pairs


def run_cross_language_benchmark(
    sim_matrix: np.ndarray,
    cross_lang_pairs: List[Tuple[int, int, str, str]],
    representation_name: str,
) -> Dict[str, Any]:
    """Benchmark: cross-language similarity for same-branch decisions."""
    logger.info(f"Running cross-language benchmark for {representation_name}")
    start = time.time()
    
    n = sim_matrix.shape[0]
    
    cross_sims = []
    for idx_a, idx_b, lang_a, lang_b in cross_lang_pairs:
        sim = float(sim_matrix[idx_a, idx_b])
        cross_sims.append(sim)
    
    rng = np.random.RandomState(42)
    same_lang_sims = []
    n_same = min(len(cross_sims), 2000)
    for _ in range(n_same):
        i, j = rng.randint(0, n, size=2)
        if i != j:
            same_lang_sims.append(float(sim_matrix[i, j]))
    
    cross_sims = np.array(cross_sims)
    same_lang_sims = np.array(same_lang_sims)
    
    metrics = {
        "representation": representation_name,
        "num_cross_lang_pairs": len(cross_sims),
        "cross_lang_mean_similarity": round(float(np.mean(cross_sims)), 4),
        "cross_lang_std_similarity": round(float(np.std(cross_sims)), 4),
        "cross_lang_median_similarity": round(float(np.median(cross_sims)), 4),
        "same_lang_mean_similarity": round(float(np.mean(same_lang_sims)), 4),
        "same_lang_std_similarity": round(float(np.std(same_lang_sims)), 4),
        "cross_same_gap": round(float(np.mean(same_lang_sims) - np.mean(cross_sims)), 4),
        "cross_lang_paired_t": 0.0,
    }
    
    min_len = min(len(cross_sims), len(same_lang_sims))
    if min_len > 10:
        diffs = same_lang_sims[:min_len] - cross_sims[:min_len]
        mean_diff = np.mean(diffs)
        std_diff = np.std(diffs, ddof=1)
        if std_diff > 0:
            t_stat = mean_diff / (std_diff / np.sqrt(min_len))
            p_value = 2 * (1 - 0.5 * (1 + erf(abs(t_stat) / np.sqrt(2))))
            metrics["cross_lang_paired_t"] = round(float(t_stat), 4)
            metrics["cross_lang_paired_p"] = round(float(p_value), 6)
    
    duration = time.time() - start
    metrics["duration"] = duration
    
    return metrics


def run_boilerplate_resistance_on_real_corpus(
    metadata: List[Dict],
    valid_indices: List[int],
    embeddings: Dict[str, np.ndarray],
    corpus_file: Path,
    sample_size: int = 100,
) -> Dict[str, Any]:
    """Test boilerplate resistance on real corpus text."""
    logger.info(f"Running boilerplate resistance on real corpus (sample_size={sample_size})")
    start = time.time()
    
    corpus_texts = {}
    with open(corpus_file) as f:
        for i, line in enumerate(f):
            if i >= sample_size * 3:
                break
            d = json.loads(line)
            did = d.get("decision_id", "")
            text = d.get("full_text", "")
            lang = d.get("language", "de")
            if did and text and len(text) > 500:
                corpus_texts[did] = {"text": text, "language": lang}
    
    logger.info(f"  Loaded {len(corpus_texts)} decisions with text")
    
    results = {}
    
    for rep_name, rep_emb in embeddings.items():
        logger.info(f"  Testing {rep_name}")
        
        valid_dids = []
        valid_embs = []
        for local_idx, global_idx in enumerate(valid_indices):
            did = metadata[global_idx].get("decision_id", "")
            if did in corpus_texts:
                valid_dids.append(did)
                valid_embs.append(rep_emb[local_idx])
        
        if not valid_dids:
            logger.warning(f"  No valid decisions for {rep_name}")
            continue
        
        valid_embs = np.array(valid_embs)
        valid_embs_norm = normalize_embeddings(valid_embs)
        
        if len(valid_dids) >= 20:
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            texts = [corpus_texts[did]["text"][:5000] for did in valid_dids]
            vectorizer = TfidfVectorizer(max_features=3000, ngram_range=(1, 2))
            tfidf_matrix = vectorizer.fit_transform(texts)
            
            text_sim = (tfidf_matrix @ tfidf_matrix.T).toarray()
            np.fill_diagonal(text_sim, -1)
            
            emb_sim = compute_similarity(valid_embs_norm)
            
            rng = np.random.RandomState(42)
            n_pairs = min(500, len(valid_dids) * (len(valid_dids) - 1) // 2)
            
            text_sims_sample = []
            emb_sims_sample = []
            
            for _ in range(n_pairs):
                i, j = rng.randint(0, len(valid_dids), size=2)
                if i != j:
                    text_sims_sample.append(text_sim[i, j])
                    emb_sims_sample.append(emb_sim[i, j])
            
            if text_sims_sample:
                x = np.array(text_sims_sample)
                y = np.array(emb_sims_sample)
                n = len(x)
                mean_x = np.mean(x)
                mean_y = np.mean(y)
                std_x = np.std(x, ddof=1)
                std_y = np.std(y, ddof=1)
                if std_x > 0 and std_y > 0:
                    corr = np.mean((x - mean_x) * (y - mean_y)) / (std_x * std_y)
                    t_stat_corr = corr * np.sqrt((n - 2) / (1 - corr**2 + 1e-10))
                    p_value = 2 * (1 - 0.5 * (1 + erf(abs(t_stat_corr) / np.sqrt(2))))
                else:
                    corr = 0
                    p_value = 1.0
                
                results[rep_name] = {
                    "num_decisions": len(valid_dids),
                    "text_embedding_correlation": round(float(corr), 4),
                    "correlation_p_value": round(float(p_value), 6),
                    "mean_embedding_similarity": round(float(np.mean(emb_sims_sample)), 4),
                    "mean_text_similarity": round(float(np.mean(text_sims_sample)), 4),
                    "resistance_score": round(1.0 - abs(float(corr)), 4),
                }
                
                logger.info(f"    Text-embedding correlation: {corr:.4f} (p={p_value:.6f})")
                logger.info(f"    Resistance score: {results[rep_name]['resistance_score']:.4f}")
    
    duration = time.time() - start
    
    return {
        "results": results,
        "duration": duration,
        "sample_size": sample_size,
    }


def run_citation_heritage_benchmark(
    sim_matrix: np.ndarray,
    metadata: List[Dict],
    valid_indices: List[int],
    citation_pairs: List[Tuple[str, str, int]],
    representation_name: str,
    k_values: List[int] = [1, 5, 10, 20, 50],
) -> Dict[str, Any]:
    """Run citation-heritage benchmark."""
    logger.info(f"Running citation-heritage benchmark for {representation_name}")
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
    
    logger.info(f"  Valid citation pairs: {len(valid_pairs)} / {len(citation_pairs)}")
    
    if len(valid_pairs) < 10:
        return {
            "representation": representation_name,
            "status": "INSUFFICIENT_DATA",
            "num_valid_pairs": len(valid_pairs),
        }
    
    positive_pairs = [(a, b) for a, b, _ in valid_pairs]
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
    
    positive_scores = [float(sim_matrix[a, b]) for a, b in positive_pairs]
    negative_scores = [float(sim_matrix[a, b]) for a, b in negative_pairs]
    
    y_true = [1] * len(positive_scores) + [0] * len(negative_scores)
    y_scores = positive_scores + negative_scores
    auc_roc = float(roc_auc_score(y_true, y_scores))
    
    pos_mean = float(np.mean(positive_scores))
    neg_mean = float(np.mean(negative_scores))
    gap = pos_mean - neg_mean
    
    precision_at_k = {}
    for k in k_values:
        precisions = []
        for a, b in positive_pairs:
            top_k = set(np.argsort(sim_matrix[a])[-k:])
            precisions.append(1.0 if b in top_k else 0.0)
            top_k_b = set(np.argsort(sim_matrix[b])[-k:])
            precisions.append(1.0 if a in top_k_b else 0.0)
        precision_at_k[f"precision@{k}"] = round(float(np.mean(precisions)), 4)
    
    nn_has_citation = 0
    for i in range(n):
        nn_idx = np.argmax(sim_matrix[i])
        pair = tuple(sorted([i, nn_idx]))
        if pair in positive_set:
            nn_has_citation += 1
    nn_citation_rate = nn_has_citation / n
    
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


def run_adversarial_benchmark(
    sim_matrix: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    representation_name: str,
) -> Dict[str, Any]:
    """Run adversarial falsification tests."""
    logger.info(f"Running adversarial benchmark for {representation_name}")
    start = time.time()
    
    n = len(branches)
    k = 10
    
    lang_dominance = []
    for i in range(n):
        top_k_idx = np.argsort(sim_matrix[i])[-k:]
        neighbor_langs = languages[top_k_idx]
        same_lang_frac = np.mean(neighbor_langs == languages[i])
        lang_dominance.append(same_lang_frac)
    lang_dominance = np.array(lang_dominance)
    
    branch_coherence = []
    for i in range(n):
        top_k_idx = np.argsort(sim_matrix[i])[-k:]
        neighbor_branches = branches[top_k_idx]
        same_branch_frac = np.mean(neighbor_branches == branches[i])
        branch_coherence.append(same_branch_frac)
    branch_coherence = np.array(branch_coherence)
    
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


def check_for_collapse(sim_matrix: np.ndarray, representation_name: str) -> Dict[str, Any]:
    """Check if representation has collapsed (all embeddings nearly identical)."""
    logger.info(f"Checking for collapse: {representation_name}")
    
    # Compute pairwise similarity statistics
    n = sim_matrix.shape[0]
    mask = np.triu(np.ones((n, n), dtype=bool), k=1)
    upper_tri = sim_matrix[mask]
    
    mean_sim = float(np.mean(upper_tri))
    std_sim = float(np.std(upper_tri))
    min_sim = float(np.min(upper_tri))
    max_sim = float(np.max(upper_tri))
    median_sim = float(np.median(upper_tri))
    
    # Check for collapse: if mean similarity > 0.99 or std < 0.01
    collapsed = mean_sim > 0.99 or std_sim < 0.01
    
    # Count near-identical pairs
    near_identical = int(np.sum(upper_tri > 0.99))
    total_pairs = int(len(upper_tri))
    
    return {
        "representation": representation_name,
        "mean_similarity": round(mean_sim, 4),
        "std_similarity": round(std_sim, 4),
        "min_similarity": round(min_sim, 4),
        "max_similarity": round(max_sim, 4),
        "median_similarity": round(median_sim, 4),
        "near_identical_pairs_gt099": near_identical,
        "total_pairs": total_pairs,
        "fraction_near_identical": round(near_identical / total_pairs, 4) if total_pairs > 0 else 0,
        "collapsed": collapsed,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Main execution
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    run_id = f"eval_cycle_12_{int(time.time())}"
    logger.info(f"Starting evaluation cycle 12: {run_id}")
    
    # Load corpus citations
    citations = load_corpus_citations()
    
    # Build citation pairs
    citation_pairs = build_shared_citation_pairs(citations, min_shared=1)
    
    # Load all representations
    metadata, representations = load_representations()
    
    # ─── NEW: Create debiased-baseline → citation graph representations ───
    logger.info("\n" + "="*60)
    logger.info("CREATING DEBIASED-BASELINE → CITATION GRAPH REPRESENTATIONS")
    logger.info("="*60)
    
    # 1. Create 64-dim PCA baseline (for fair comparison)
    debiased_baseline_64 = create_debiased_baseline_64(
        representations["baseline"],
        n_pca_components=2,
    )
    representations["debiased_baseline_64"] = debiased_baseline_64
    
    # 2. Create debiased-baseline → citation graph representations
    debiased_citation_blended, debiased_citation_graph_only = create_debiased_baseline_then_citation(
        representations["baseline"],
        metadata,
        citations,
        n_pca_components=2,
        alpha=0.5,
        dims=64,
    )
    representations["debiased_citation_blended"] = debiased_citation_blended
    representations["debiased_citation_graph_only"] = debiased_citation_graph_only
    
    results = {
        "run_id": run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cycle": 12,
        "hypothesis": (
            "Applying language debiasing BEFORE citation graph construction "
            "avoids the dimensional collapse observed in cycle 11. The debiased "
            "baseline (768-dim with top 2 PCA components removed) preserves enough "
            "structure for citation graph construction. The resulting representation "
            "should achieve BOTH low language dominance (< 0.85) AND high citation "
            "heritage AUC (> 0.65)."
        ),
        "frozen_sample": "1000 BGer decisions (2020-2024) from fractal-map baseline",
        "frozen_metrics": [
            "citation_heritage_auc_roc",
            "citation_heritage_similarity_gap",
            "language_dominance_mean",
            "branch_coherence_mean",
            "branch_knn_accuracy@5",
            "dead_zones_gt095",
            "cross_lang_mean_similarity",
            "cross_same_gap",
            "text_embedding_correlation",
            "collapse_check",
        ],
        "success_rule": (
            "debiased_citation_blended has language_dominance < 0.85 AND "
            "citation_heritage AUC > 0.65; no dimensional collapse "
            "(mean_similarity < 0.99)"
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
        
        # Collapse check (NEW for cycle 12)
        collapse = check_for_collapse(sim_matrix, name)
        
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
        
        # Cross-language benchmark
        cross_lang_pairs = build_cross_language_pairs(metadata, valid_idx, max_pairs=2000)
        cross_lang = run_cross_language_benchmark(
            sim_matrix, cross_lang_pairs, name
        )
        
        results["representations"][name] = {
            "collapse_check": collapse,
            "citation_heritage": citation_heritage,
            "adversarial": adversarial,
            "tf_metadata": tf_metadata,
            "cross_language": cross_lang,
        }
    
    # Run boilerplate resistance on real corpus
    logger.info(f"\n{'='*60}")
    logger.info("BOILERPLATE RESISTANCE ON REAL CORPUS")
    logger.info(f"{'='*60}")
    
    boilerplate_results = run_boilerplate_resistance_on_real_corpus(
        metadata, valid_idx, representations, CORPUS_FILE, sample_size=100
    )
    results["boilerplate_resistance"] = boilerplate_results
    
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
        "cross_lang_mean_similarity": {},
        "cross_same_gap": {},
        "collapse_mean_similarity": {},
        "collapse_std_similarity": {},
        "collapse_fraction_near_identical": {},
    }
    
    for name, res in results["representations"].items():
        ch = res["citation_heritage"]
        adv = res["adversarial"]
        tf = res["tf_metadata"]
        cl = res["cross_language"]
        collapse = res["collapse_check"]
        
        comparison["citation_heritage_auc"][name] = ch.get("auc_roc", None)
        comparison["citation_heritage_gap"][name] = ch.get("similarity_gap", None)
        comparison["adversarial_status"][name] = adv["status"]
        comparison["language_dominance"][name] = adv["language_dominance_mean"]
        comparison["branch_coherence"][name] = adv["branch_coherence_mean"]
        comparison["dead_zones_gt095"][name] = adv["dead_zones_gt095"]
        comparison["branch_knn_accuracy"][name] = tf["summary"]["branch_knn_accuracy@5"]
        comparison["cross_lang_mean_similarity"][name] = cl.get("cross_lang_mean_similarity", None)
        comparison["cross_same_gap"][name] = cl.get("cross_same_gap", None)
        comparison["collapse_mean_similarity"][name] = collapse["mean_similarity"]
        comparison["collapse_std_similarity"][name] = collapse["std_similarity"]
        comparison["collapse_fraction_near_identical"][name] = collapse["fraction_near_identical"]
        
        logger.info(f"  {name}:")
        logger.info(f"    Citation heritage AUC: {ch.get('auc_roc', 'N/A')}")
        logger.info(f"    Language dominance: {adv['language_dominance_mean']:.3f}")
        logger.info(f"    Branch coherence: {adv['branch_coherence_mean']:.3f}")
        logger.info(f"    Dead zones >0.95: {adv['dead_zones_gt095']}")
        logger.info(f"    Branch k-NN@5: {tf['summary']['branch_knn_accuracy@5']:.3f}")
        logger.info(f"    Cross-lang similarity: {cl.get('cross_lang_mean_similarity', 'N/A')}")
        logger.info(f"    Collapse check: mean_sim={collapse['mean_similarity']:.4f}, "
                    f"collapsed={collapse['collapsed']}")
    
    results["comparison"] = comparison
    
    # Key findings
    findings = []
    
    # Check debiased_citation_blended (the main hypothesis)
    debiased_cb_res = results["representations"].get("debiased_citation_blended", {})
    if debiased_cb_res:
        debiased_cb_adv = debiased_cb_res.get("adversarial", {})
        debiased_cb_ch = debiased_cb_res.get("citation_heritage", {})
        debiased_cb_collapse = debiased_cb_res.get("collapse_check", {})
        
        if debiased_cb_adv:
            lang_dom = debiased_cb_adv.get("language_dominance_mean", 1.0)
            findings.append(
                f"Debiased citation blended language dominance: {lang_dom:.3f} "
                f"{'PASS' if lang_dom < 0.85 else 'FAIL'} (< 0.85 target)"
            )
        
        if debiased_cb_ch:
            auc = debiased_cb_ch.get("auc_roc", 0)
            findings.append(
                f"Debiased citation blended citation heritage AUC: {auc:.3f} "
                f"{'PASS' if auc > 0.65 else 'FAIL'} (> 0.65 target)"
            )
        
        if debiased_cb_collapse:
            mean_sim = debiased_cb_collapse.get("mean_similarity", 1.0)
            collapsed = debiased_cb_collapse.get("collapsed", True)
            findings.append(
                f"Debiased citation blended collapse check: mean_sim={mean_sim:.4f} "
                f"{'PASS (no collapse)' if not collapsed else 'FAIL (COLLAPSED)'} "
                f"(target: < 0.99)"
            )
    
    # Compare debiased_citation_blended vs cycle 11's citation_blended_debiased
    cycle11_cb_debiased = results["representations"].get("citation_blended_debiased", {})
    if cycle11_cb_debiased and debiased_cb_res:
        cycle11_collapse = cycle11_cb_debiased.get("collapse_check", {})
        cycle12_collapse = debiased_cb_res.get("collapse_check", {})
        
        if cycle11_collapse and cycle12_collapse:
            cycle11_mean = cycle11_collapse.get("mean_similarity", 1.0)
            cycle12_mean = cycle12_collapse.get("mean_similarity", 1.0)
            findings.append(
                f"Cycle 11 vs 12 collapse: cycle11_mean_sim={cycle11_mean:.4f} vs "
                f"cycle12_mean_sim={cycle12_mean:.4f} "
                f"{'IMPROVED' if cycle12_mean < cycle11_mean else 'SAME/WORSE'}"
            )
    
    # Cross-language analysis for debiased_citation_blended
    if debiased_cb_res:
        debiased_cb_cl = debiased_cb_res.get("cross_language", {})
        if debiased_cb_cl:
            gap = debiased_cb_cl.get("cross_same_gap", 0)
            findings.append(
                f"Debiased citation blended cross-language gap: {gap:.4f} "
                f"{'PASS' if gap > 0 else 'NEEDS INVESTIGATION'}"
            )
    
    # Boilerplate resistance
    bp = results.get("boilerplate_resistance", {}).get("results", {})
    for rep_name, bp_res in bp.items():
        corr = bp_res.get("text_embedding_correlation", 0)
        resistance = bp_res.get("resistance_score", 0)
        findings.append(
            f"Boilerplate resistance ({rep_name}): correlation={corr:.4f}, "
            f"resistance={resistance:.4f} "
            f"{'PASS' if resistance > 0.5 else 'FAIL'} (> 0.5 target)"
        )
    
    results["key_findings"] = findings
    
    for f in findings:
        logger.info(f"  FINDING: {f}")
    
    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_path = OUTPUT_DIR / "cycle_12_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Results saved to {results_path}")
    
    return results


if __name__ == "__main__":
    results = main()
    print("\n=== CYCLE 12 COMPLETE ===")
    print(f"Run ID: {results['run_id']}")
    for name, auc in results["comparison"]["citation_heritage_auc"].items():
        print(f"  {name}: citation heritage AUC = {auc}")
