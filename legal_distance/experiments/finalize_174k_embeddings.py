#!/usr/bin/env python3
"""
Finalize 174k dense embeddings by concatenating existing checkpoints.
"""
import json
import numpy as np
from pathlib import Path
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/checkpoints")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings")
METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.jsonl")

def load_metadata_index():
    """Load metadata_174k.jsonl to get the canonical decision order and metadata."""
    metadata = []
    with open(METADATA_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                metadata.append(json.loads(line))
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    return metadata

def main():
    logger.info("=" * 70)
    logger.info("FINALIZING 174K DENSE EMBEDDINGS FROM CHECKPOINTS")
    logger.info("=" * 70)
    
    # Load metadata index (canonical order)
    metadata = load_metadata_index()
    
    # Load progress to get completed years
    progress_file = CHECKPOINT_DIR / "progress.json"
    with open(progress_file, 'r') as f:
        progress = json.load(f)
    completed_years = progress["completed_years"]
    logger.info(f"Completed years: {completed_years}")
    
    # Load all checkpoints in year order
    all_embeddings_list = []
    all_metadata_list = []
    year_indices = {}
    current_idx = 0
    
    for year in sorted(completed_years):
        emb_path = CHECKPOINT_DIR / f"embeddings_{year}.npy"
        meta_path = CHECKPOINT_DIR / f"metadata_{year}.json"
        
        if emb_path.exists() and meta_path.exists():
            embeddings = np.load(emb_path)
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            
            all_embeddings_list.append(embeddings)
            all_metadata_list.extend(meta)
            year_indices[year] = (current_idx, current_idx + len(embeddings))
            current_idx += len(embeddings)
            logger.info(f"  Loaded {year}: {embeddings.shape}")
        else:
            logger.warning(f"  Checkpoint missing for {year}")
    
    # Concatenate all embeddings
    logger.info("Concatenating all year embeddings...")
    all_embeddings = np.vstack(all_embeddings_list)
    logger.info(f"Full embeddings shape: {all_embeddings.shape}")
    
    # Verify order matches metadata
    assert len(all_metadata_list) == len(metadata), f"Metadata mismatch: {len(all_metadata_list)} vs {len(metadata)}"
    for i, (m1, m2) in enumerate(zip(all_metadata_list, metadata)):
        if m1['decision_id'] != m2['decision_id']:
            logger.error(f"Order mismatch at index {i}: {m1['decision_id']} vs {m2['decision_id']}")
            raise ValueError("Metadata order mismatch!")
    
    logger.info("Order verified against canonical metadata")
    
    # Save raw 768-dim embeddings
    raw_emb_path = OUTPUT_DIR / "embeddings_768.npy"
    np.save(raw_emb_path, all_embeddings.astype(np.float32))
    logger.info(f"Saved raw 768-dim embeddings to {raw_emb_path}")
    
    # Save metadata
    meta_path = OUTPUT_DIR / "metadata.json"
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved metadata to {meta_path}")
    
    # Create center_projected (subtract language centers)
    logger.info("Creating center_projected...")
    languages = sorted(set(m['language'] for m in metadata))
    logger.info(f"Languages: {languages}")
    
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = all_embeddings[mask].mean(axis=0)
            logger.info(f"  {lang}: {np.sum(mask)} decisions, center norm={np.linalg.norm(centers[lang]):.4f}")
    
    debiased = np.copy(all_embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in centers:
            debiased[i] = all_embeddings[i] - centers[lang]
    
    # L2 normalize
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    debiased = debiased / norms
    
    logger.info(f"Center projected shape: {debiased.shape}")
    logger.info(f"Norm stats: min={np.linalg.norm(debiased, axis=1).min():.6f}, max={np.linalg.norm(debiased, axis=1).max():.6f}, mean={np.linalg.norm(debiased, axis=1).mean():.6f}")
    
    # Save center_projected 768dim
    cp768_path = OUTPUT_DIR / "embeddings_center_projected.npy"
    np.save(cp768_path, debiased.astype(np.float32))
    logger.info(f"Saved center_projected 768dim to {cp768_path}")
    
    # Create 64-dim PCA version
    logger.info("Creating center_projected 64dim via PCA...")
    pca_64 = PCA(n_components=64, random_state=42)
    center_projected_64 = pca_64.fit_transform(debiased)
    center_projected_64 = normalize(center_projected_64, norm='l2', axis=1)
    cp64_path = OUTPUT_DIR / "embeddings_center_projected_64.npy"
    np.save(cp64_path, center_projected_64.astype(np.float32))
    logger.info(f"Saved center_projected_64 to {cp64_path}")
    logger.info(f"  Explained variance ratio (64 components): {pca_64.explained_variance_ratio_.sum():.4f}")
    
    # Create 128-dim version
    logger.info("Creating center_projected 128dim via PCA...")
    pca_128 = PCA(n_components=128, random_state=42)
    center_projected_128 = pca_128.fit_transform(debiased)
    center_projected_128 = normalize(center_projected_128, norm='l2', axis=1)
    cp128_path = OUTPUT_DIR / "embeddings_center_projected_128.npy"
    np.save(cp128_path, center_projected_128.astype(np.float32))
    logger.info(f"Saved center_projected_128 to {cp128_path}")
    logger.info(f"  Explained variance ratio (128 components): {pca_128.explained_variance_ratio_.sum():.4f}")
    
    # Save run metadata
    run_meta = {
        "run_id": f"dense_embeddings_174k_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 27,
        "model": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        "n_decisions": len(metadata),
        "embedding_dim": 768,
        "year_indices": year_indices,
        "languages": languages,
        "language_counts": {lang: sum(1 for m in metadata if m['language'] == lang) for lang in languages},
        "files": {
            "embeddings_768": "embeddings_768.npy",
            "embeddings_center_projected": "embeddings_center_projected.npy",
            "embeddings_center_projected_64": "embeddings_center_projected_64.npy",
            "embeddings_center_projected_128": "embeddings_center_projected_128.npy",
            "metadata": "metadata.json",
        },
        "corpus_note": "173,963 decisions from bger_*.jsonl files (2000-2024). Full-text used for embeddings.",
    }
    
    with open(OUTPUT_DIR / "run_metadata.json", 'w') as f:
        json.dump(run_meta, f, indent=2, ensure_ascii=False)
    
    logger.info("=" * 70)
    logger.info("174K DENSE EMBEDDING FINALIZATION COMPLETE")
    logger.info("=" * 70)
    
    return run_meta

if __name__ == "__main__":
    main()
