#!/usr/bin/env python3
"""
Run citation_heritage benchmark on 15-year dense embeddings (2000-2014, ~92k decisions).
Uses the frozen citation pairs from validate_citation_heritage_174k.py.
"""

import json
import numpy as np
import logging
import time
import sys
from pathlib import Path
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_CHECKPOINTS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
TFIDF_EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings")
FULL_METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
CITATION_PAIRS_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/citation_pairs_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/benchmark_15year")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPLETED_YEARS = list(range(2000, 2015))  # 2000-2014 inclusive (15 years)
FROZEN_SEED = 42
K_NEIGHBORS = 20

np.random.seed(FROZEN_SEED)

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

def assign_branch(chamber):
    if not chamber:
        return "unknown"
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

def load_citation_pairs():
    with open(CITATION_PAIRS_PATH) as f:
        data = json.load(f)
    positive_pairs = set(tuple(p) for p in data['positive_pairs'])
    negative_pairs = set(tuple(p) for p in data['negative_pairs'])
    logger.info(f"Loaded {len(positive_pairs)} positive pairs, {len(negative_pairs)} negative pairs")
    return positive_pairs, negative_pairs, data

def load_full_metadata():
    with open(FULL_METADATA_PATH) as f:
        metadata = json.load(f)
    did_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    return metadata, did_to_idx

def load_dense_embeddings_subset(full_metadata, years):
    """Load dense embeddings for specified years and assemble in full metadata order."""
    logger.info(f"Loading dense embeddings for years {years[0]}-{years[-1]}...")
    
    target_ids = set()
    year_meta = {}
    year_emb = {}
    
    for year in years:
        meta_path = DENSE_CHECKPOINTS_DIR / f"metadata_{year}.json"
        emb_path = DENSE_CHECKPOINTS_DIR / f"embeddings_{year}.npy"
        
        with open(meta_path) as f:
            meta = json.load(f)
        emb = np.load(emb_path)
        
        year_meta[year] = meta
        year_emb[year] = emb
        
        for m in meta:
            target_ids.add(m['decision_id'])
    
    logger.info(f"Total target decisions from checkpoints: {len(target_ids)}")
    
    # Filter full metadata to only target decisions, preserving order
    subset_metadata = []
    for m in full_metadata:
        if m['decision_id'] in target_ids:
            subset_metadata.append(m)
    
    logger.info(f"Subset metadata count (in full metadata order): {len(subset_metadata)} (expected {len(target_ids)})")
    
    # Build a lookup: decision_id -> (year, local_index)
    id_to_year_local = {}
    for year in years:
        meta = year_meta[year]
        for local_idx, m in enumerate(meta):
            id_to_year_local[m['decision_id']] = (year, local_idx)
    
    # Assemble embeddings
    dim = year_emb[years[0]].shape[1]
    embeddings_subset = np.zeros((len(subset_metadata), dim), dtype=np.float32)
    
    for i, m in enumerate(subset_metadata):
        year, local_idx = id_to_year_local[m['decision_id']]
        embeddings_subset[i] = year_emb[year][local_idx]
    
    logger.info(f"Assembled dense embeddings shape: {embeddings_subset.shape}")
    return embeddings_subset, subset_metadata

def apply_center_projection(embeddings, metadata):
    """Apply language center projection to embeddings."""
    languages = [m.get('language', 'de') for m in metadata]
    unique_langs = sorted(set(languages))
    centers = {}
    for lang in unique_langs:
        mask = np.array([l == lang for l in languages])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
    
    emb_cp = np.copy(embeddings)
    for i, lang in enumerate(languages):
        if lang in centers:
            emb_cp[i] = embeddings[i] - centers[lang]
    
    # L2 normalize
    norms = np.linalg.norm(emb_cp, axis=1, keepdims=True)
    norms[norms == 0] = 1
    emb_cp = emb_cp / norms
    return emb_cp

def apply_pca(embeddings, n_components):
    """Apply PCA to reduce dimensionality."""
    pca = PCA(n_components=n_components, random_state=FROZEN_SEED)
    emb_pca = pca.fit_transform(embeddings)
    emb_pca = normalize(emb_pca, norm='l2', axis=1)
    logger.info(f"PCA to {n_components} dim: explained variance = {pca.explained_variance_ratio_.sum():.4f}")
    return emb_pca

def load_citation_tfidf_for_subset(subset_metadata, full_metadata):
    """Load citation TF-IDF embeddings for the subset decisions."""
    logger.info("Loading citation TF-IDF embeddings for subset...")
    
    cited_tfidf_path = TFIDF_EMBEDDINGS_DIR / "cited_decisions_tfidf.npy"
    cited_tfidf = np.load(cited_tfidf_path, mmap_mode='r')
    logger.info(f"Full citation TF-IDF shape: {cited_tfidf.shape}")
    
    full_id_to_idx = {m['decision_id']: i for i, m in enumerate(full_metadata)}
    
    n_subset = len(subset_metadata)
    tfidf_dim = cited_tfidf.shape[1]
    subset_tfidf = np.zeros((n_subset, tfidf_dim), dtype=np.float32)
    
    for i, m in enumerate(subset_metadata):
        full_idx = full_id_to_idx[m['decision_id']]
        subset_tfidf[i] = cited_tfidf[full_idx]
    
    logger.info(f"Extracted subset citation TF-IDF shape: {subset_tfidf.shape}")
    return subset_tfidf

def load_outcome_hybrid_for_subset(subset_metadata, full_metadata, alpha=0.5):
    """Load cited_decisions_tfidf_outcome_hybrid embeddings for the subset decisions."""
    logger.info(f"Loading cited_decisions_tfidf_outcome_hybrid_{alpha} for subset...")
    
    hybrid_path = TFIDF_EMBEDDINGS_DIR / f"cited_decisions_tfidf_outcome_hybrid_{alpha}.npy"
    hybrid = np.load(hybrid_path, mmap_mode='r')
    logger.info(f"Full hybrid shape: {hybrid.shape}")
    
    full_id_to_idx = {m['decision_id']: i for i, m in enumerate(full_metadata)}
    
    n_subset = len(subset_metadata)
    hybrid_dim = hybrid.shape[1]
    subset_hybrid = np.zeros((n_subset, hybrid_dim), dtype=np.float32)
    
    for i, m in enumerate(subset_metadata):
        full_idx = full_id_to_idx[m['decision_id']]
        subset_hybrid[i] = hybrid[full_idx]
    
    logger.info(f"Extracted subset hybrid shape: {subset_hybrid.shape}")
    return subset_hybrid

def create_concat(dense_emb, citation_emb, name):
    """Concatenate dense and citation embeddings."""
    logger.info(f"Creating {name}: dense {dense_emb.shape} + citation {citation_emb.shape}")
    concat = np.hstack([dense_emb, citation_emb])
    logger.info(f"Concatenated shape: {concat.shape}")
    return concat

def run_citation_heritage_benchmark(embeddings, metadata, did_to_idx, positive_pairs, negative_pairs, name):
    """Run citation heritage benchmark using exact k-NN."""
    logger.info(f"  Building exact k-NN index for {name}...")
    nn = NearestNeighbors(n_neighbors=K_NEIGHBORS + 1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]  # Exclude self
    
    # Build neighbor sets for fast lookup
    neighbor_sets = [set(n) for n in neighbors]
    
    # Evaluate positive pairs
    pos_scores = []
    pos_found = 0
    for did1, did2 in positive_pairs:
        if did1 in did_to_idx and did2 in did_to_idx:
            idx1 = did_to_idx[did1]
            idx2 = did_to_idx[did2]
            found = idx2 in neighbor_sets[idx1]
            pos_scores.append(1.0 if found else 0.0)
            if found:
                pos_found += 1
    
    # Evaluate negative pairs
    neg_scores = []
    neg_found = 0
    for did1, did2 in negative_pairs:
        if did1 in did_to_idx and did2 in did_to_idx:
            idx1 = did_to_idx[did1]
            idx2 = did_to_idx[did2]
            found = idx2 in neighbor_sets[idx1]
            neg_scores.append(1.0 if found else 0.0)
            if found:
                neg_found += 1
    
    # Create labels and scores for AUC/AP
    y_true = [1] * len(pos_scores) + [0] * len(neg_scores)
    y_scores = pos_scores + neg_scores
    
    if len(set(y_true)) > 1:
        auc = roc_auc_score(y_true, y_scores)
        ap = average_precision_score(y_true, y_scores)
    else:
        auc = 0.5
        ap = 0.0
    
    pos_rate = pos_found / len(pos_scores) if pos_scores else 0
    neg_rate = neg_found / len(neg_scores) if neg_scores else 0
    
    return {
        'auc': float(auc),
        'average_precision': float(ap),
        'positive_recall_at_k': float(pos_rate),
        'negative_rate_at_k': float(neg_rate),
        'positive_pairs_evaluated': len(pos_scores),
        'negative_pairs_evaluated': len(neg_scores),
        'positive_found': pos_found,
        'negative_found': neg_found,
        'k': K_NEIGHBORS,
    }

def main():
    logger.info("=" * 70)
    logger.info("CITATION_HERITAGE BENCHMARK ON 15-YEAR DENSE EMBEDDINGS (2000-2014)")
    logger.info("=" * 70)
    
    # Load data
    positive_pairs, negative_pairs, pairs_data = load_citation_pairs()
    full_metadata, full_did_to_idx = load_full_metadata()
    
    # Load 15-year dense embeddings (768-dim)
    logger.info("\n=== Loading 15-year dense embeddings (768-dim) ===")
    dense_768, subset_metadata = load_dense_embeddings_subset(full_metadata, COMPLETED_YEARS)
    
    # Apply center projection
    logger.info("\n=== Applying language center projection ===")
    dense_cp_768 = apply_center_projection(dense_768, subset_metadata)
    
    # Create PCA versions
    logger.info("\n=== Creating PCA-reduced versions ===")
    dense_cp_128 = apply_pca(dense_cp_768, 128)
    dense_cp_64 = apply_pca(dense_cp_768, 64)
    
    # Load citation embeddings for subset
    logger.info("\n=== Loading citation embeddings for 15-year subset ===")
    citation_tfidf = load_citation_tfidf_for_subset(subset_metadata, full_metadata)
    hybrid_05 = load_outcome_hybrid_for_subset(subset_metadata, full_metadata, 0.5)
    
    # Create linear combinations
    logger.info("\n=== Creating linear combinations ===")
    linear_citation_concat = create_concat(dense_cp_64, citation_tfidf, "linear_citation_concat_15year")
    linear_hybrid05_concat = create_concat(dense_cp_64, hybrid_05, "linear_hybrid05_concat_15year")
    
    # Define all representations to evaluate
    representations = {
        'center_projected_768dim_15year': dense_cp_768,
        'center_projected_128dim_15year': dense_cp_128,
        'center_projected_64dim_15year': dense_cp_64,
        'linear_citation_concat_15year': linear_citation_concat,
        'linear_hybrid05_concat_15year': linear_hybrid05_concat,
        'cited_decisions_tfidf_15year': citation_tfidf,
        'cited_decisions_tfidf_outcome_hybrid_0.5_15year': hybrid_05,
    }
    
    # Build did_to_idx for subset
    subset_did_to_idx = {m['decision_id']: i for i, m in enumerate(subset_metadata)}
    
    # Run citation heritage on each
    all_results = {
        'run_id': f'citation_heritage_15year_{int(time.time())}',
        'direction_version': 29,
        'seed': FROZEN_SEED,
        'k_neighbors': K_NEIGHBORS,
        'years': COMPLETED_YEARS,
        'n_decisions': len(subset_metadata),
        'citation_pairs_info': {
            'positive_pairs_total': len(positive_pairs),
            'negative_pairs_total': len(negative_pairs),
            'coverage': pairs_data.get('coverage', {}),
        },
        'per_representation': {},
    }
    
    logger.info("\n=== Running citation heritage benchmark ===")
    for name, embeddings in representations.items():
        logger.info(f"\nEvaluating {name}...")
        try:
            result = run_citation_heritage_benchmark(embeddings, subset_metadata, subset_did_to_idx, positive_pairs, negative_pairs, name)
            all_results['per_representation'][name] = result
            
            logger.info(f"  {name}: AUC={result['auc']:.4f}, AP={result['average_precision']:.4f}, "
                       f"pos_recall@20={result['positive_recall_at_k']:.4f}, neg_rate={result['negative_rate_at_k']:.4f}")
            
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            all_results['per_representation'][name] = {'error': str(e)}
    
    # Save results
    output_file = OUTPUT_DIR / f"citation_heritage_15year_dense_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "citation_heritage_15year_dense_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("CITATION_HERITAGE 15-YEAR DENSE SUMMARY")
    logger.info("=" * 70)
    logger.info(f"{'Representation':<45} {'AUC':>6} {'AP':>6} {'Pos@20':>7} {'Neg@20':>7}")
    logger.info("-" * 70)
    
    for name, res in all_results['per_representation'].items():
        if 'error' in res:
            logger.info(f"{name:<45} {'ERROR':>6} {'ERROR':>6} {'ERROR':>7} {'ERROR':>7}")
        else:
            logger.info(f"{name:<45} {res['auc']:>6.4f} {res['average_precision']:>6.4f} "
                       f"{res['positive_recall_at_k']:>7.4f} {res['negative_rate_at_k']:>7.4f}")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 70)
    
    return all_results

if __name__ == "__main__":
    main()