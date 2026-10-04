#!/usr/bin/env python3
"""
Evaluate citation heritage at 24-year scale (2000-2023, ~158k decisions).
Extends the 22-year (144k) evaluation using existing year checkpoints.
"""

import json
import numpy as np
from pathlib import Path
from sklearn.metrics import roc_auc_score
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/checkpoints")
CITATION_PAIRS_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/results/174k_citation_heritage/citation_pairs_174k.json")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/citation_heritage_eval")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_year_checkpoints():
    """Load and concatenate all year checkpoints (2000-2023)."""
    all_embeddings = []
    all_metadata = []
    year_indices = {}
    current_idx = 0
    
    for year in range(2000, 2024):
        emb_path = CHECKPOINT_DIR / f"embeddings_{year}.npy"
        meta_path = CHECKPOINT_DIR / f"metadata_{year}.json"
        
        if emb_path.exists() and meta_path.exists():
            embeddings = np.load(emb_path)
            with open(meta_path) as f:
                metadata = json.load(f)
            
            all_embeddings.append(embeddings)
            all_metadata.extend(metadata)
            year_indices[str(year)] = (current_idx, current_idx + len(embeddings))
            current_idx += len(embeddings)
            logger.info(f"Loaded {year}: {embeddings.shape}")
        else:
            logger.warning(f"Missing checkpoint for {year}")
    
    all_embeddings = np.vstack(all_embeddings)
    logger.info(f"Concatenated embeddings: {all_embeddings.shape}")
    logger.info(f"Total metadata entries: {len(all_metadata)}")
    
    return all_embeddings, all_metadata, year_indices


def compute_center_projected(embeddings, metadata):
    """Subtract language centers and L2 normalize."""
    languages = sorted(set(m.get('language', 'unknown') for m in metadata))
    logger.info(f"Languages: {languages}")
    
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
            logger.info(f"  {lang}: {np.sum(mask)} decisions, center norm={np.linalg.norm(centers[lang]):.4f}")
    
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
    
    return debiased, centers


def compute_pca_projections(debiased, n_components_list=[64, 128]):
    """Compute PCA projections of center-projected embeddings."""
    results = {}
    for n_comp in n_components_list:
        logger.info(f"Computing PCA {n_comp}...")
        pca = PCA(n_components=n_comp, random_state=42)
        projected = pca.fit_transform(debiased)
        projected = normalize(projected, norm='l2', axis=1)
        results[n_comp] = {
            'embeddings': projected.astype(np.float32),
            'explained_variance_ratio': pca.explained_variance_ratio_.sum()
        }
        logger.info(f"  Explained variance ratio ({n_comp} components): {pca.explained_variance_ratio_.sum():.4f}")
    return results


def build_decision_index(metadata):
    """Build decision_id -> index mapping."""
    return {m['decision_id']: i for i, m in enumerate(metadata)}


def evaluate_citation_heritage(embeddings_dict, decision_index, citation_pairs, name):
    """Evaluate AUC-ROC on citation heritage pairs."""
    pos_pairs = citation_pairs['positive_pairs']
    neg_pairs = citation_pairs['negative_pairs']
    
    # Filter pairs where both decisions exist in embeddings
    valid_pos = []
    valid_neg = []
    
    for a, b in pos_pairs:
        if a in decision_index and b in decision_index:
            valid_pos.append((decision_index[a], decision_index[b]))
    
    for a, b in neg_pairs:
        if a in decision_index and b in decision_index:
            valid_neg.append((decision_index[a], decision_index[b]))
    
    logger.info(f"{name}: {len(valid_pos)}/{len(pos_pairs)} positive pairs, {len(valid_neg)}/{len(neg_pairs)} negative pairs valid")
    
    if len(valid_pos) < 10 or len(valid_neg) < 10:
        logger.warning(f"{name}: Insufficient pairs for evaluation")
        return None
    
    # Compute similarities
    pos_sims = []
    for i, j in valid_pos:
        sim = np.dot(embeddings_dict[i], embeddings_dict[j])
        pos_sims.append(sim)
    
    neg_sims = []
    for i, j in valid_neg:
        sim = np.dot(embeddings_dict[i], embeddings_dict[j])
        neg_sims.append(sim)
    
    pos_sims = np.array(pos_sims)
    neg_sims = np.array(neg_sims)
    
    # AUC-ROC
    y_true = np.concatenate([np.ones(len(pos_sims)), np.zeros(len(neg_sims))])
    y_scores = np.concatenate([pos_sims, neg_sims])
    auc = roc_auc_score(y_true, y_scores)
    
    pos_mean = pos_sims.mean()
    neg_mean = neg_sims.mean()
    sim_gap = pos_mean - neg_mean
    
    logger.info(f"{name}: AUC={auc:.4f}, pos_mean={pos_mean:.4f}, neg_mean={neg_mean:.4f}, gap={sim_gap:.4f}")
    
    return {
        'name': name,
        'status': 'PASSED' if auc > 0.75 else 'FAILED',
        'metrics': {
            'auc_roc': float(auc),
            'positive_mean_sim': float(pos_mean),
            'negative_mean_sim': float(neg_mean),
            'mean_similarity_gap': float(sim_gap),
            'num_positive_pairs': len(valid_pos),
            'num_negative_pairs': len(valid_neg),
            'num_embedded_decisions': len(embeddings_dict)
        }
    }


def main():
    logger.info("=" * 70)
    logger.info("24-YEAR CITATION HERITAGE EVALUATION (2000-2023)")
    logger.info("=" * 70)
    
    # Load citation pairs
    with open(CITATION_PAIRS_PATH) as f:
        citation_pairs = json.load(f)
    logger.info(f"Loaded {len(citation_pairs['positive_pairs'])} positive, {len(citation_pairs['negative_pairs'])} negative pairs")
    
    # Load and concatenate year checkpoints
    embeddings_768, metadata, year_indices = load_year_checkpoints()
    
    # Build decision index
    decision_index = build_decision_index(metadata)
    logger.info(f"Built decision index with {len(decision_index)} entries")
    
    # Compute center_projected
    logger.info("Computing center_projected...")
    center_projected_768, centers = compute_center_projected(embeddings_768, metadata)
    
    # Compute PCA projections
    logger.info("Computing PCA projections...")
    pca_results = compute_pca_projections(center_projected_768, [64, 128])
    center_projected_64 = pca_results[64]['embeddings']
    center_projected_128 = pca_results[128]['embeddings']
    
    # Evaluate all variants
    results = {}
    
    variants = {
        'raw_768dim': embeddings_768,
        'center_projected_768dim': center_projected_768,
        'center_projected_64dim': center_projected_64,
        'center_projected_128dim': center_projected_128,
    }
    
    for name, emb in variants.items():
        result = evaluate_citation_heritage(emb, decision_index, citation_pairs, name)
        if result:
            results[name] = result
    
    # Save results
    output_path = OUTPUT_DIR / "citation_heritage_24year_latest.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved results to {output_path}")
    
    # Also save with timestamp
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    timestamped_path = OUTPUT_DIR / f"citation_heritage_24year_{timestamp}.json"
    with open(timestamped_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved timestamped results to {timestamped_path}")
    
    # Print summary
    logger.info("=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    for name, result in results.items():
        m = result['metrics']
        logger.info(f"{name}: AUC={m['auc_roc']:.4f}, gap={m['mean_similarity_gap']:.4f}, pos_pairs={m['num_positive_pairs']}, status={result['status']}")
    
    return results


if __name__ == "__main__":
    main()