#!/usr/bin/env python3
"""
Compute UMAP 2D projections for 174k TF-IDF representations.
Uses the first 173,963 rows of embeddings (matching metadata_174k_eval.json which has 173,963 entries).
"""
import numpy as np
import json
from pathlib import Path
import logging
import umap

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

REP_DIRS = {
    "cited_decisions_tfidf_174k": "cited_decisions_tfidf.npy",
    "cited_outcome_hybrid_0.7_174k": "cited_decisions_tfidf_outcome_hybrid_0.7.npy",
}

EMBEDDING_DIR = Path("/home/runner/work/LexMachina/LexMachina/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings")
METADATA_EVAL_PATH = Path("/home/runner/work/LexMachina/LexMachina/product/results/fractal_map/hierarchical_map_174k/metadata_174k_eval.json")
TARGET_N = 173963  # Matches metadata_174k_eval.json (173,963 entries)

def compute_projection(rep_name, embedding_file):
    rep_dir = Path("/home/runner/work/LexMachina/LexMachina/product/results/fractal_map") / rep_name
    embedding_path = EMBEDDING_DIR / embedding_file
    
    logger.info(f"Loading embeddings for {rep_name} from {embedding_path}")
    embeddings = np.load(embedding_path)
    logger.info(f"  Full embeddings shape: {embeddings.shape}")
    
    # Verify TARGET_N against metadata
    with open(METADATA_EVAL_PATH) as f:
        metadata_eval = json.load(f)
    actual_n = len(metadata_eval)
    if actual_n != TARGET_N:
        raise ValueError(f"TARGET_N ({TARGET_N}) does not match metadata_174k_eval.json length ({actual_n})")
    logger.info(f"  Verified TARGET_N={TARGET_N} against metadata_174k_eval.json ({actual_n} entries)")
    
    # Slice to target_n (first 173,963 rows)
    if embeddings.shape[0] < TARGET_N:
        raise ValueError(f"Embeddings have only {embeddings.shape[0]} rows, need {TARGET_N}")
    embeddings = embeddings[:TARGET_N]
    logger.info(f"  Sliced embeddings shape: {embeddings.shape}")
    
    # Verify decision_ids alignment (first N decision_ids should match embedding rows)
    # This assumes the embedding file was generated in the same order as metadata_174k_eval.json
    eval_ids = [m['decision_id'] for m in metadata_eval]
    logger.info(f"  First 5 decision_ids from metadata: {eval_ids[:5]}")
    
    # Normalize
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms
    
    # Compute UMAP
    logger.info(f"  Computing UMAP projection for {TARGET_N} points...")
    reducer = umap.UMAP(n_components=2, n_neighbors=15, min_dist=0.1, metric='cosine', random_state=42)
    projection_2d = reducer.fit_transform(embeddings)
    
    # Save projection
    proj_path = rep_dir / "projection_2d.npy"
    np.save(proj_path, projection_2d.astype(np.float32))
    logger.info(f"  Saved projection to {proj_path} (shape: {projection_2d.shape})")
    
    # Save UMAP params
    umap_params = {
        "n_components": 2,
        "n_neighbors": 15,
        "min_dist": 0.1,
        "metric": "cosine",
        "random_state": 42,
    }
    with open(rep_dir / "umap_params.json", 'w') as f:
        json.dump(umap_params, f, indent=2)
    
    return projection_2d

def main():
    logger.info("=== Computing 174k UMAP Projections ===")
    
    for rep_name, embedding_file in REP_DIRS.items():
        try:
            compute_projection(rep_name, embedding_file)
        except Exception as e:
            logger.error(f"Failed to compute projection for {rep_name}: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info("=== Done ===")

if __name__ == "__main__":
    main()