#!/usr/bin/env python3
"""
Run citation heritage benchmark on 19k dense embeddings (years 2000-2002).
Tests whether dense semantic embeddings recover citation heritage (doctrinal proximity).
"""

import json
import numpy as np
import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
from sklearn.metrics import roc_auc_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_CHECKPOINTS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
FULL_METADATA_PATH = Path("/tmp/lex_accepted/legal-distance/evaluation/data/174k/metadata_174k.json")
CITATION_PAIRS_PATH = Path("/tmp/lex_accepted/legal-distance/evaluation/results/174k_citation_heritage/citation_pairs_174k.json")
OUTPUT_DIR = Path("/tmp/lex_accepted/legal-distance/evaluation/results/174k/dense_19k_formal_suite/citation_heritage")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ACCEPTED years (3 years: 2000-2002)
TARGET_YEARS = list(range(2000, 2003))

def load_full_metadata() -> List[Dict]:
    """Load full 174k metadata (canonical order)."""
    logger.info("Loading full 174k metadata...")
    with open(FULL_METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Full metadata: {len(metadata)} decisions")
    return metadata

def load_citation_pairs() -> Dict:
    """Load citation heritage pairs."""
    logger.info("Loading citation pairs...")
    with open(CITATION_PAIRS_PATH) as f:
        pairs = json.load(f)
    logger.info(f"Positive pairs: {len(pairs['positive_pairs'])}, Negative pairs: {len(pairs['negative_pairs'])}")
    return pairs

def load_dense_embeddings_subset(full_metadata: List[Dict], years: List[int]) -> Tuple[np.ndarray, List[Dict]]:
    """Load dense embeddings for specified years and assemble in full metadata order."""
    logger.info(f"Loading dense embeddings for years {years[0]}-{years[-1]}...")
    
    # Build decision_id -> index mapping for full metadata
    full_id_to_idx = {m['decision_id']: i for i, m in enumerate(full_metadata)}
    
    # Collect all decision_ids for the target years
    target_ids = set()
    year_meta = {}
    year_emb = {}
    
    for year in years:
        meta_path = DENSE_CHECKPOINTS_DIR / f"metadata_{year}.json"
        emb_path = DENSE_CHECKPOINTS_DIR / f"embeddings_{year}.npy"
        
        if not meta_path.exists() or not emb_path.exists():
            logger.warning(f"Checkpoint missing for {year}")
            continue
            
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
    
    logger.info(f"Subset metadata count (in full metadata order): {len(subset_metadata)}")
    
    # Build a lookup: decision_id -> (year, local_index)
    id_to_year_local = {}
    for year in years:
        if year not in year_meta:
            continue
        meta = year_meta[year]
        for local_idx, m in enumerate(meta):
            id_to_year_local[m['decision_id']] = (year, local_idx)
    
    # Assemble embeddings
    dim = year_emb[years[0]].shape[1]
    embeddings_subset = np.zeros((len(subset_metadata), dim), dtype=np.float32)
    
    missing = 0
    for i, m in enumerate(subset_metadata):
        did = m['decision_id']
        if did in id_to_year_local:
            year, local_idx = id_to_year_local[did]
            embeddings_subset[i] = year_emb[year][local_idx]
        else:
            missing += 1
            logger.warning(f"Decision {did} not found in year embeddings")
    
    if missing > 0:
        logger.warning(f"Missing embeddings for {missing} decisions")
    
    logger.info(f"Assembled embeddings shape: {embeddings_subset.shape}")
    return embeddings_subset, subset_metadata

def language_center_projection(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    """Project each embedding to remove the component toward its language center."""
    languages = sorted(set(m.get('language', 'unknown') for m in metadata))
    
    # Compute language centers
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
            logger.info(f"  {lang}: {np.sum(mask)} decisions, center norm={np.linalg.norm(centers[lang]):.4f}")
    
    # For each embedding, subtract its language center
    debiased = np.copy(embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    # L2 normalize
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    debiased = debiased / norms
    
    logger.info(f"Center projected shape: {debiased.shape}")
    logger.info(f"Norm stats: min={np.linalg.norm(debiased, axis=1).min():.6f}, max={np.linalg.norm(debiased, axis=1).max():.6f}, mean={np.linalg.norm(debiased, axis=1).mean():.6f}")
    
    return debiased

def apply_frozen_pca(embeddings: np.ndarray, n_components: int = 64, random_state: int = 42) -> Tuple[np.ndarray, PCA]:
    """Apply PCA fitted on the given embeddings (frozen for this dataset)."""
    logger.info(f"Fitting PCA: {embeddings.shape[1]} -> {n_components} dimensions...")
    pca = PCA(n_components=n_components, random_state=random_state)
    reduced = pca.fit_transform(embeddings)
    reduced = normalize(reduced, norm='l2', axis=1)
    
    explained_var = pca.explained_variance_ratio_.sum()
    logger.info(f"Explained variance ratio (top {n_components}): {explained_var:.4f}")
    
    return reduced, pca

def build_embedding_lookup(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, np.ndarray]:
    """Build decision_id -> embedding lookup for fast retrieval."""
    lookup = {}
    for i, m in enumerate(metadata):
        lookup[m['decision_id']] = embeddings[i]
    return lookup

def run_citation_heritage_benchmark(
    name: str,
    embeddings: np.ndarray,
    metadata: List[Dict],
    citation_pairs: Dict,
    min_shared_citations: int = 2,
    max_pairs: int = 500,
    random_seed: int = 42
) -> Dict[str, Any]:
    """Run citation graph neighborhood benchmark on embeddings."""
    logger.info(f"\n=== Running Citation Heritage Benchmark: {name} ===")
    start_time = time.time()
    
    # Build embedding lookup
    emb_lookup = build_embedding_lookup(embeddings, metadata)
    logger.info(f"Embedding lookup size: {len(emb_lookup)}")
    
    # Filter citation pairs to only those where both decisions have embeddings
    positive_pairs = []
    for d1, d2 in citation_pairs['positive_pairs']:
        if d1 in emb_lookup and d2 in emb_lookup:
            positive_pairs.append((d1, d2))
    
    negative_pairs = []
    for d1, d2 in citation_pairs['negative_pairs']:
        if d1 in emb_lookup and d2 in emb_lookup:
            negative_pairs.append((d1, d2))
    
    logger.info(f"Positive pairs with embeddings: {len(positive_pairs)}")
    logger.info(f"Negative pairs with embeddings: {len(negative_pairs)}")
    
    if len(positive_pairs) < 10:
        return {
            "status": "ERROR",
            "error": f"Insufficient positive pairs with embeddings: {len(positive_pairs)}",
            "name": name
        }
    
    # Limit pairs
    import random
    random.seed(random_seed)
    if len(positive_pairs) > max_pairs:
        random.shuffle(positive_pairs)
        positive_pairs = positive_pairs[:max_pairs]
    if len(negative_pairs) > max_pairs:
        random.shuffle(negative_pairs)
        negative_pairs = negative_pairs[:max_pairs]
    
    # Compute similarities
    positive_scores = []
    negative_scores = []
    
    for d1, d2 in positive_pairs:
        sim = cosine_similarity(emb_lookup[d1], emb_lookup[d2])
        positive_scores.append(sim)
    
    for d1, d2 in negative_pairs:
        sim = cosine_similarity(emb_lookup[d1], emb_lookup[d2])
        negative_scores.append(sim)
    
    # Compute metrics
    metrics = {}
    if positive_scores and negative_scores:
        y_true = [1] * len(positive_scores) + [0] * len(negative_scores)
        y_scores = positive_scores + negative_scores
        metrics["auc_roc"] = float(roc_auc_score(y_true, y_scores))
        metrics["positive_mean_sim"] = float(np.mean(positive_scores))
        metrics["negative_mean_sim"] = float(np.mean(negative_scores))
        metrics["mean_similarity_gap"] = float(np.mean(positive_scores) - np.mean(negative_scores))
    else:
        metrics["auc_roc"] = 0.5
    
    metrics["num_positive_pairs"] = len(positive_pairs)
    metrics["num_negative_pairs"] = len(negative_pairs)
    metrics["num_embedded_decisions"] = len(emb_lookup)
    
    # Pass if AUC > 0.7
    auc = metrics.get("auc_roc", 0.5)
    status = "PASSED" if auc > 0.7 else "FAILED"
    
    duration = time.time() - start_time
    
    result = {
        "name": name,
        "status": status,
        "metrics": metrics,
        "duration_seconds": duration,
        "details": {
            "positive_pairs_sample": positive_pairs[:10],
            "negative_pairs_sample": negative_pairs[:10],
        },
        "baseline_comparison": {
            "auc_roc_random": 0.5,
            "note": "Random embeddings: AUC = 0.5. TF-IDF citation-based: AUC ~0.71-0.74 (PASS). TF-IDF text-based: AUC ~0.50-0.63 (FAIL)."
        }
    }
    
    logger.info(f"  AUC-ROC: {metrics['auc_roc']:.4f} ({status})")
    logger.info(f"  Positive mean sim: {metrics['positive_mean_sim']:.4f}")
    logger.info(f"  Negative mean sim: {metrics['negative_mean_sim']:.4f}")
    logger.info(f"  Similarity gap: {metrics['mean_similarity_gap']:.4f}")
    logger.info(f"  Positive pairs: {metrics['num_positive_pairs']}, Negative pairs: {metrics['num_negative_pairs']}")
    
    return result

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

def main():
    logger.info("=" * 70)
    logger.info("CITATION HERITAGE BENCHMARK ON DENSE EMBEDDINGS (19-YEAR: 2000-2002)")
    logger.info("=" * 70)
    
    # Load data
    full_metadata = load_full_metadata()
    citation_pairs = load_citation_pairs()
    
    # Load and assemble dense embeddings for target years
    embeddings_768, subset_metadata = load_dense_embeddings_subset(full_metadata, TARGET_YEARS)
    
    # Filter citation pairs to target years
    target_ids = set(m['decision_id'] for m in subset_metadata)
    filtered_positive = [(d1, d2) for d1, d2 in citation_pairs['positive_pairs'] if d1 in target_ids and d2 in target_ids]
    filtered_negative = [(d1, d2) for d1, d2 in citation_pairs['negative_pairs'] if d1 in target_ids and d2 in target_ids]
    logger.info(f"Filtered positive pairs (both in target years): {len(filtered_positive)}")
    logger.info(f"Filtered negative pairs (both in target years): {len(filtered_negative)}")
    
    filtered_pairs = {
        'positive_pairs': filtered_positive,
        'negative_pairs': filtered_negative
    }
    
    results = {}
    
    # 1. Raw 768-dim
    logger.info("\n" + "=" * 70)
    logger.info("Evaluating RAW 768-dim embeddings")
    logger.info("=" * 70)
    results['raw_768dim'] = run_citation_heritage_benchmark(
        "multilingual_e5_768dim_19k",
        embeddings_768,
        subset_metadata,
        filtered_pairs
    )
    
    # 2. Center projected 768-dim
    logger.info("\n" + "=" * 70)
    logger.info("Applying center projection...")
    logger.info("=" * 70)
    embeddings_cp_768 = language_center_projection(embeddings_768, subset_metadata)
    results['center_projected_768dim'] = run_citation_heritage_benchmark(
        "center_projected_768dim_19k",
        embeddings_cp_768,
        subset_metadata,
        filtered_pairs
    )
    
    # 3. Center projected 64-dim
    logger.info("\n" + "=" * 70)
    logger.info("Applying PCA to 64 dimensions...")
    logger.info("=" * 70)
    embeddings_cp_64, pca_64 = apply_frozen_pca(embeddings_cp_768, n_components=64, random_state=42)
    results['center_projected_64dim'] = run_citation_heritage_benchmark(
        "center_projected_64dim_19k",
        embeddings_cp_64,
        subset_metadata,
        filtered_pairs
    )
    
    # 4. Center projected 128-dim
    logger.info("\n" + "=" * 70)
    logger.info("Applying PCA to 128 dimensions...")
    logger.info("=" * 70)
    embeddings_cp_128, pca_128 = apply_frozen_pca(embeddings_cp_768, n_components=128, random_state=42)
    results['center_projected_128dim'] = run_citation_heritage_benchmark(
        "center_projected_128dim_19k",
        embeddings_cp_128,
        subset_metadata,
        filtered_pairs
    )
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("CITATION HERITAGE BENCHMARK SUMMARY (19k dense)")
    logger.info("=" * 70)
    
    for name, result in results.items():
        if result.get('status') != 'ERROR':
            metrics = result.get('metrics', {})
            auc = metrics.get('auc_roc', 0.5)
            status = result.get('status', 'UNKNOWN')
            logger.info(f"{name}: AUC={auc:.4f} ({status})")
        else:
            logger.info(f"{name}: ERROR - {result.get('error')}")
    
    # Save results
    from datetime import datetime
    output_file = OUTPUT_DIR / f"citation_heritage_19k_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\nResults saved to: {output_file}")
    
    # Also save latest
    latest_file = OUTPUT_DIR / "citation_heritage_19k_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Latest results saved to: {latest_file}")
    
    return results

if __name__ == "__main__":
    main()