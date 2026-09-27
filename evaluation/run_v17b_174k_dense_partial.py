#!/usr/bin/env python3
"""
Run v17b label normalization test on 16-year partial center_projected dense embeddings.
Tests whether normalized labels improve or match raw labels on hierarchy-family metrics.
"""

import json
import sys
import time
import numpy as np
import logging
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score

sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/evaluation')
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/evaluation/experiments')

from legal_area_normalize import normalize_legal_area

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
DENSE_CHECKPOINTS_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints")
FULL_METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/174k/metadata_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/v17b_174k_dense_partial")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMPLETED_YEARS = list(range(2000, 2016))  # 2000-2015 inclusive

# Fixed parameters (from protocol)
FROZEN_SEED = 42
HIERARCHY_SUBSAMPLE = 15000
K_VALUES = [5, 8, 10, 15, 20, 25, 30]
N_CLUSTERS_COHERENCE = 16

np.random.seed(FROZEN_SEED)

def load_dense_embeddings_subset(full_metadata: list, years: list):
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
        
        with open(meta_path) as f:
            meta = json.load(f)
        emb = np.load(emb_path)
        
        year_meta[year] = meta
        year_emb[year] = emb
        
        for m in meta:
            target_ids.add(m['decision_id'])
    
    logger.info(f"Total target decisions: {len(target_ids)}")
    
    # Filter full metadata to only target decisions, preserving order
    subset_metadata = []
    subset_indices = []
    
    for i, m in enumerate(full_metadata):
        if m['decision_id'] in target_ids:
            subset_metadata.append(m)
            subset_indices.append(i)
    
    logger.info(f"Subset metadata count: {len(subset_metadata)} (expected {len(target_ids)})")
    
    # Now assemble embeddings in the same order as subset_metadata
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
    
    logger.info(f"Assembled embeddings shape: {embeddings_subset.shape}")
    
    return embeddings_subset, subset_metadata


def center_project(embeddings: np.ndarray, metadata: list) -> np.ndarray:
    """Create center_projected embeddings by subtracting language centers."""
    languages = sorted(set(m.get('language', 'de') for m in metadata))
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language', 'de') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
    
    debiased = np.copy(embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language', 'de')
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return debiased / norms


def project_to_dim(emb: np.ndarray, target_dim: int) -> np.ndarray:
    n_samples, n_features = emb.shape
    if n_features <= target_dim:
        if n_features < target_dim:
            padding = np.zeros((n_samples, target_dim - n_features))
            return np.concatenate([emb, padding], axis=1)
        return emb
    if n_samples < target_dim + 1:
        return emb[:, :target_dim]
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import normalize
    pca = PCA(n_components=target_dim, random_state=FROZEN_SEED)
    projected = pca.fit_transform(emb)
    return normalize(projected, norm='l2', axis=1)


def load_metadata():
    with open(FULL_METADATA_PATH) as f:
        metadata = json.load(f)
    return metadata


def make_label_variants(metadata):
    """Create raw and normalized label arrays."""
    raw_labels = []
    for m in metadata:
        la = m.get('legal_area')
        raw_labels.append(la if la else 'NONE')
    raw_labels = np.array(raw_labels)
    
    norm_labels = np.array([normalize_legal_area(l) if l != 'NONE' else 'NONE' for l in raw_labels])
    n_norm = np.sum(raw_labels != norm_labels)
    return raw_labels, norm_labels, n_norm


def get_subsample_indices(metadata, labels, n=HIERARCHY_SUBSAMPLE):
    """Get stratified subsample indices by branch among decisions with known legal_area."""
    branches = np.array([m.get('branch', 'unknown') for m in metadata])
    valid_mask = (labels != 'NONE') & (branches != 'unknown')
    valid_indices = np.where(valid_mask)[0]
    
    if len(valid_indices) <= n:
        return valid_indices
    
    # Stratified by branch
    branch_labels = branches[valid_indices]
    unique_branches = np.unique(branch_labels)
    per_branch = n // len(unique_branches)
    subsample_indices = []
    
    for branch in unique_branches:
        branch_mask = branch_labels == branch
        branch_indices = valid_indices[branch_mask]
        if len(branch_indices) > per_branch:
            selected = np.random.choice(branch_indices, per_branch, replace=False)
        else:
            selected = branch_indices
        subsample_indices.extend(selected)
    
    return np.array(subsample_indices[:n])


def run_hierarchy_coherence(embeddings, labels, k_values=K_VALUES):
    """Run hierarchy coherence benchmark."""
    best_purity = 0
    best_nmi = 0
    best_k = None
    
    for k in k_values:
        if k >= len(embeddings):
            continue
        kmeans = KMeans(n_clusters=k, random_state=FROZEN_SEED, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)
        
        # Compute purity per cluster
        purities = []
        for c in range(k):
            mask = cluster_labels == c
            if np.sum(mask) == 0:
                continue
            cluster_labels_sub = labels[mask]
            unique, counts = np.unique(cluster_labels_sub, return_counts=True)
            purity = np.max(counts) / np.sum(counts)
            purities.append(purity)
        
        mean_purity = np.mean(purities) if purities else 0
        nmi = normalized_mutual_info_score(labels, cluster_labels)
        
        if mean_purity > best_purity:
            best_purity = mean_purity
            best_nmi = nmi
            best_k = k
    
    return {
        'best_purity': float(best_purity),
        'best_nmi': float(best_nmi),
        'best_k': int(best_k) if best_k else None,
        'k_values_tried': k_values
    }


def run_zoom_coherence(embeddings, labels):
    """Run zoom coherence benchmark (coarse vs fine clustering)."""
    # Coarse: 4 clusters (branch level)
    kmeans_coarse = KMeans(n_clusters=4, random_state=FROZEN_SEED, n_init=10)
    coarse_labels = kmeans_coarse.fit_predict(embeddings)
    
    coarse_purities = []
    for c in range(4):
        mask = coarse_labels == c
        if np.sum(mask) == 0:
            continue
        cluster_labels_sub = labels[mask]
        unique, counts = np.unique(cluster_labels_sub, return_counts=True)
        purity = np.max(counts) / np.sum(counts)
        coarse_purities.append(purity)
    coarse_purity = np.mean(coarse_purities) if coarse_purities else 0
    
    # Fine: 16 clusters
    kmeans_fine = KMeans(n_clusters=16, random_state=FROZEN_SEED, n_init=10)
    fine_labels = kmeans_fine.fit_predict(embeddings)
    
    fine_purities = []
    for c in range(16):
        mask = fine_labels == c
        if np.sum(mask) == 0:
            continue
        cluster_labels_sub = labels[mask]
        unique, counts = np.unique(cluster_labels_sub, return_counts=True)
        purity = np.max(counts) / np.sum(counts)
        fine_purities.append(purity)
    fine_purity = np.mean(fine_purities) if fine_purities else 0
    
    improvement_pct = ((fine_purity - coarse_purity) / coarse_purity * 100) if coarse_purity > 0 else 0
    
    return {
        'coarse_purity': float(coarse_purity),
        'fine_purity': float(fine_purity),
        'improvement_pct': float(improvement_pct)
    }


def run_legal_area_clustering(embeddings, labels):
    """Run legal area clustering benchmark."""
    unique_areas = np.unique(labels)
    n_areas = len(unique_areas)
    
    if n_areas < 2:
        return {'overall_purity': 0.0, 'nmi': 0.0, 'num_areas': n_areas}
    
    kmeans = KMeans(n_clusters=n_areas, random_state=FROZEN_SEED, n_init=10)
    cluster_labels = kmeans.fit_predict(embeddings)
    
    purities = []
    for c in range(n_areas):
        mask = cluster_labels == c
        if np.sum(mask) == 0:
            continue
        cluster_labels_sub = labels[mask]
        unique, counts = np.unique(cluster_labels_sub, return_counts=True)
        purity = np.max(counts) / np.sum(counts)
        purities.append(purity)
    
    overall_purity = np.mean(purities) if purities else 0
    nmi = normalized_mutual_info_score(labels, cluster_labels)
    
    return {
        'overall_purity': float(overall_purity),
        'nmi': float(nmi),
        'num_areas': int(n_areas)
    }


def run_all_hierarchy_benchmarks(embeddings, labels):
    """Run all three hierarchy-family benchmarks."""
    return {
        'hierarchy_coherence': run_hierarchy_coherence(embeddings, labels),
        'zoom_coherence': run_zoom_coherence(embeddings, labels),
        'legal_area_clustering': run_legal_area_clustering(embeddings, labels)
    }


def evaluate_representation(name: str, embeddings: np.ndarray, metadata: list, raw_labels: np.ndarray, norm_labels: np.ndarray, subsample_idx: np.ndarray):
    """Evaluate a single representation with raw and normalized labels."""
    logger.info(f"\nEvaluating {name}...")
    
    # Subsample embeddings
    emb_sub = embeddings[subsample_idx]
    raw_sub = raw_labels[subsample_idx]
    norm_sub = norm_labels[subsample_idx]
    
    # Run on raw labels
    raw_res = run_all_hierarchy_benchmarks(emb_sub, raw_sub)
    
    # Run on normalized labels
    norm_res = run_all_hierarchy_benchmarks(emb_sub, norm_sub)
    
    # Compute purity ratios
    def ratio(a, b):
        return round((a / b), 4) if b else None
    
    ratios = {
        "hierarchy_purity": ratio(norm_res['hierarchy_coherence']['best_purity'],
                                  raw_res['hierarchy_coherence']['best_purity']),
        "hierarchy_nmi": ratio(norm_res['hierarchy_coherence']['best_nmi'],
                               raw_res['hierarchy_coherence']['best_nmi']),
        "zoom_coarse": ratio(norm_res['zoom_coherence']['coarse_purity'],
                             raw_res['zoom_coherence']['coarse_purity']),
        "zoom_fine": ratio(norm_res['zoom_coherence']['fine_purity'],
                           raw_res['zoom_coherence']['fine_purity']),
        "legal_area_purity": ratio(norm_res['legal_area_clustering']['overall_purity'],
                                   raw_res['legal_area_clustering']['overall_purity']),
        "legal_area_nmi": ratio(norm_res['legal_area_clustering']['nmi'],
                                raw_res['legal_area_clustering']['nmi']),
    }
    
    result = {
        "raw": raw_res,
        "normalized": norm_res,
        "purity_ratios_norm_over_raw": ratios,
        "norm_num_areas": norm_res['legal_area_clustering']['num_areas'],
    }
    
    logger.info(f"  {name}: ratios {ratios}")
    
    return result


def main():
    logger.info("=" * 70)
    logger.info("v17b LABEL NORMALIZATION TEST ON 16-YEAR CENTER_PROJECTED PARTIAL (2000-2015)")
    logger.info("=" * 70)
    
    # Load full metadata
    full_metadata = load_metadata()
    logger.info(f"Full metadata: {len(full_metadata)} decisions")
    
    # Load and assemble raw dense embeddings for years 2000-2015
    embeddings_raw, subset_metadata = load_dense_embeddings_subset(full_metadata, COMPLETED_YEARS)
    
    # Create center_projected versions
    logger.info("Creating center_projected 768dim...")
    embeddings_cp_768 = center_project(embeddings_raw, subset_metadata)
    
    logger.info("Creating center_projected 64dim...")
    embeddings_cp_64 = project_to_dim(embeddings_cp_768, 64)
    
    logger.info("Creating center_projected 128dim...")
    embeddings_cp_128 = project_to_dim(embeddings_cp_768, 128)
    
    # Create label variants from subset metadata
    raw_labels, norm_labels, n_norm = make_label_variants(subset_metadata)
    logger.info(f"Labels normalized: {n_norm}/{len(subset_metadata)} ({100*n_norm/len(subset_metadata):.1f}%)")
    
    # Get subsample indices (same for all representations)
    subsample_idx = get_subsample_indices(subset_metadata, raw_labels)
    logger.info(f"Hierarchy subsample size: {len(subsample_idx)}")
    
    representations = {
        'center_projected_768dim_partial_2000_2015': embeddings_cp_768,
        'center_projected_64dim_partial_2000_2015': embeddings_cp_64,
        'center_projected_128dim_partial_2000_2015': embeddings_cp_128,
    }
    
    out = {
        "run_id": f"eval_v17b_174k_dense_partial_{int(time.time())}",
        "direction_version": 30,
        "seed": FROZEN_SEED,
        "subsample_size": len(subsample_idx),
        "n_labels_normalized": int(n_norm),
        "raw_unique_labels": len(np.unique(raw_labels[raw_labels != 'NONE'])),
        "normalized_unique_labels": len(np.unique(norm_labels[norm_labels != 'NONE'])),
        "per_representation": {},
    }
    
    for name, emb in representations.items():
        try:
            result = evaluate_representation(name, emb, subset_metadata, raw_labels, norm_labels, subsample_idx)
            out["per_representation"][name] = result
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            out["per_representation"][name] = {"error": str(e)}
    
    # Uniformity check
    worsened = {}
    for name, d in out["per_representation"].items():
        if "error" in d:
            continue
        for k, v in d["purity_ratios_norm_over_raw"].items():
            if v is not None and v < 0.9:
                worsened[f"{name}.{k}"] = v
    
    out["uniform_improvement_or_matching"] = (len(worsened) == 0)
    out["representations_worsened_by_gt10pct"] = worsened
    
    # Save results
    with open(OUTPUT_DIR / "v17b_174k_dense_partial_results.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    with open(OUTPUT_DIR / "v17b_174k_dense_partial_latest.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    
    logger.info("\n" + "=" * 70)
    logger.info(f"UNIFORM IMPROVEMENT: {out['uniform_improvement_or_matching']}")
    logger.info(f"REPRESENTATIONS WORSENED >10%: {worsened}")
    logger.info(f"Results saved to {OUTPUT_DIR}")
    logger.info("=" * 70)
    
    return out


if __name__ == "__main__":
    main()