#!/usr/bin/env python3
"""
Regenerate missing label arrays at 173,963 for 174k TF-IDF representations.
Fixes:
- cited_decisions_tfidf_174k: labels_res_1.5.npy (was 1,000)
- cited_outcome_hybrid_0.7_174k: labels_res_0.75.npy and labels_res_1.5.npy (were 1,000)
"""
import numpy as np
import json
from pathlib import Path
import logging
import sys

# Import hierarchical Leiden from fractal-map
sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
from hierarchical_zoom_validation import leiden_clustering

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
PRODUCT_RESULTS = Path("/home/runner/work/LexMachina/LexMachina/product/results/fractal_map")
LEGAL_TFIDF_DIR = PRODUCT_RESULTS / "hierarchical_map_174k" / "legal_tfidf_embeddings"
ENRICHED_METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json")

REPRESENTATIONS = [
    {
        "name": "cited_decisions_tfidf_174k",
        "embedding_file": "cited_decisions_tfidf.npy",
        "missing_resolutions": [1.5],  # labels_res_1.5.npy is at 1,000
    },
    {
        "name": "cited_outcome_hybrid_0.7_174k",
        "embedding_file": "cited_decisions_tfidf_outcome_hybrid_0.7.npy",
        "missing_resolutions": [0.75, 1.5],  # labels_res_0.75.npy and labels_res_1.5.npy are at 1,000
    },
]

def load_metadata():
    with open(ENRICHED_METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded {len(metadata)} decisions with enriched metadata")
    return metadata

def load_and_prepare_embeddings(embedding_file, n_decisions):
    embedding_path = LEGAL_TFIDF_DIR / embedding_file
    logger.info(f"Loading embeddings from {embedding_path}")
    embeddings = np.load(embedding_path)
    logger.info(f"  Full embeddings shape: {embeddings.shape}")
    
    # Slice to n_decisions (173,963)
    embeddings = embeddings[:n_decisions]
    logger.info(f"  Sliced embeddings shape: {embeddings.shape}")
    
    # Normalize
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True).clip(min=1e-8)
    
    return embeddings

def main():
    logger.info("=== Regenerating Missing Label Arrays at 173,963 ===")
    
    metadata = load_metadata()
    n_decisions = len(metadata)
    
    for rep in REPRESENTATIONS:
        name = rep["name"]
        embedding_file = rep["embedding_file"]
        missing_resolutions = rep["missing_resolutions"]
        
        logger.info(f"\nProcessing {name}...")
        
        # Load embeddings
        embeddings = load_and_prepare_embeddings(embedding_file, n_decisions)
        
        # Output directory
        out_dir = PRODUCT_RESULTS / name
        
        # Regenerate missing resolutions
        for res in missing_resolutions:
            logger.info(f"  Running Leiden at resolution={res}...")
            flat_labels, _ = leiden_clustering(embeddings, resolution=res, k=15)
            
            # Verify shape
            if flat_labels.shape[0] != n_decisions:
                raise ValueError(f"Labels shape {flat_labels.shape} != {n_decisions}")
            
            # Save
            label_path = out_dir / f"labels_res_{res}.npy"
            np.save(label_path, flat_labels.astype(np.int32))
            logger.info(f"  Saved {label_path} (shape: {flat_labels.shape})")
            
            # Quick stats
            unique_labels = np.unique(flat_labels[flat_labels != -1])
            logger.info(f"    Clusters: {len(unique_labels)}, Noise: {np.sum(flat_labels == -1)}")
    
    logger.info("\n=== Done ===")

if __name__ == "__main__":
    main()