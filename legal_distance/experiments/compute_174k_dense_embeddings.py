#!/usr/bin/env python3
"""
Year-split dense embedding computation for 174k corpus (bger decisions).

Computes 768-dim embeddings using paraphrase-multilingual-mpnet-base-v2
with year-split chunked processing and resumable checkpoints.
Then computes center_projected (768dim, 64dim, 128dim) by subtracting language centers.

Designed for CPU execution within 65-min job ceilings on free public runners.
"""

import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
import logging
import sys
import time
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Use the bger (unpublished decisions) corpus, not bge (published BGE volumes)
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
# Use the 174k metadata with bger_ decision IDs (173,963 entries)
METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
BATCH_SIZE = 128
EMBEDDING_DIM = 768

# Year files to process (2000 onward per product scope) - bger_ prefix for unpublished decisions
YEAR_FILES = sorted(CORPUS_DIR.glob("bger_20[0-9][0-9].jsonl"))
# Filter to only years >= 2000 (product scope)
YEAR_FILES = [f for f in YEAR_FILES if int(f.stem.split('_')[1]) >= 2000]

# Checkpoint files
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
PROGRESS_FILE = CHECKPOINT_DIR / "progress.json"
EMBEDDINGS_PATTERN = "embeddings_{year}.npy"
METADATA_PATTERN = "metadata_{year}.json"


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


def load_year_decisions(year_file, decision_ids_set):
    """Load decisions from a year file, filtering to only those in metadata."""
    decisions = []
    with open(year_file, 'r') as f:
        for line in f:
            d = json.loads(line)
            if d['decision_id'] in decision_ids_set:
                decisions.append(d)
    return decisions


def prepare_texts(decisions, metadata_order):
    """Prepare texts for embedding in the order of metadata."""
    decision_map = {d['decision_id']: d for d in decisions}
    texts = []
    meta_out = []
    for m in metadata_order:
        did = m['decision_id']
        if did in decision_map:
            d = decision_map[did]
            text = d.get('full_text', '')
            if not text:
                text = f"{d.get('title', '')} {d.get('legal_area', '')} {d.get('regeste', '')}"
            texts.append(text)
            meta_out.append(m)
        else:
            # This decision not in this year file
            texts.append("")
            meta_out.append(None)
    return texts, meta_out


def compute_year_embeddings(year, year_file, metadata, model, decision_ids_set):
    """Compute embeddings for a single year."""
    logger.info(f"Processing {year} from {year_file.name}...")
    
    # Load decisions for this year
    decisions = load_year_decisions(year_file, decision_ids_set)
    logger.info(f"  Loaded {len(decisions)} decisions from {year_file.name}")
    
    if not decisions:
        logger.info(f"  No matching decisions, skipping")
        return None, None
    
    # Prepare texts in metadata order
    texts, meta_out = prepare_texts(decisions, metadata)
    
    # Filter to only non-empty texts (decisions in this year)
    valid_indices = [i for i, t in enumerate(texts) if t.strip()]
    valid_texts = [texts[i] for i in valid_indices]
    valid_meta = [meta_out[i] for i in valid_indices]
    
    if not valid_texts:
        logger.info(f"  No valid texts, skipping")
        return None, None
    
    logger.info(f"  Computing embeddings for {len(valid_texts)} decisions...")
    start = time.time()
    embeddings = model.encode(valid_texts, batch_size=BATCH_SIZE, show_progress_bar=True, convert_to_numpy=True)
    elapsed = time.time() - start
    logger.info(f"  Computed {embeddings.shape} in {elapsed:.1f}s ({len(valid_texts)/elapsed:.1f} decisions/s)")
    
    return embeddings, valid_meta


def save_checkpoint(year, embeddings, metadata):
    """Save year embeddings and metadata as checkpoint."""
    np.save(CHECKPOINT_DIR / EMBEDDINGS_PATTERN.format(year=year), embeddings.astype(np.float32))
    with open(CHECKPOINT_DIR / METADATA_PATTERN.format(year=year), 'w') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    logger.info(f"  Saved checkpoint for {year}")


def load_checkpoint(year):
    """Load year embeddings and metadata from checkpoint."""
    emb_path = CHECKPOINT_DIR / EMBEDDINGS_PATTERN.format(year=year)
    meta_path = CHECKPOINT_DIR / METADATA_PATTERN.format(year=year)
    if emb_path.exists() and meta_path.exists():
        embeddings = np.load(emb_path)
        with open(meta_path, 'r') as f:
            metadata = json.load(f)
        logger.info(f"  Loaded checkpoint for {year}: {embeddings.shape}")
        return embeddings, metadata
    return None, None


def load_progress():
    """Load progress tracking."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"completed_years": [], "failed_years": []}


def save_progress(progress):
    """Save progress tracking."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def main():
    logger.info("=" * 70)
    logger.info("YEAR-SPLIT 174K DENSE EMBEDDING COMPUTATION (bger corpus)")
    logger.info("=" * 70)
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Model: {MODEL_NAME}")
    logger.info(f"Batch size: {BATCH_SIZE}")
    logger.info(f"Output dir: {OUTPUT_DIR}")
    
    # Load metadata index (canonical order)
    metadata = load_metadata_index()
    decision_ids_set = set(m['decision_id'] for m in metadata)
    logger.info(f"Total decisions in metadata: {len(metadata)}")
    
    # Load model
    logger.info(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    logger.info("Model loaded")
    
    # Load progress
    progress = load_progress()
    completed_years = set(progress["completed_years"])
    logger.info(f"Previously completed years: {sorted(completed_years)}")
    
    # Extract year from year files (bger_YYYY.jsonl format)
    year_files = []
    for yf in YEAR_FILES:
        year = yf.stem.split('_')[1]
        year_files.append((year, yf))
    
    # Process each year
    all_embeddings_list = []
    all_metadata_list = []
    year_indices = {}  # year -> (start_idx, end_idx) in final concatenated array
    
    current_idx = 0
    for year, year_file in year_files:
        if year in completed_years:
            # Load from checkpoint
            embeddings, meta = load_checkpoint(year)
            if embeddings is not None:
                all_embeddings_list.append(embeddings)
                all_metadata_list.extend(meta)
                year_indices[year] = (current_idx, current_idx + len(embeddings))
                current_idx += len(embeddings)
                logger.info(f"  Resumed {year}: {embeddings.shape}")
                continue
        
        # Compute embeddings for this year
        embeddings, meta = compute_year_embeddings(year, year_file, metadata, model, decision_ids_set)
        
        if embeddings is not None:
            # Save checkpoint
            save_checkpoint(year, embeddings, meta)
            
            # Accumulate
            all_embeddings_list.append(embeddings)
            all_metadata_list.extend(meta)
            year_indices[year] = (current_idx, current_idx + len(embeddings))
            current_idx += len(embeddings)
            
            # Update progress
            progress["completed_years"].append(year)
            save_progress(progress)
        else:
            progress["failed_years"].append(year)
            save_progress(progress)
    
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
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import normalize
    
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
        "model": MODEL_NAME,
        "n_decisions": len(metadata),
        "embedding_dim": EMBEDDING_DIM,
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
        "corpus_note": "174,113 decisions from bger_*.jsonl files (2000-2026). Full-text used for embeddings.",
    }
    
    with open(OUTPUT_DIR / "run_metadata.json", 'w') as f:
        json.dump(run_meta, f, indent=2, ensure_ascii=False)
    
    logger.info("=" * 70)
    logger.info("174K DENSE EMBEDDING COMPUTATION COMPLETE")
    logger.info("=" * 70)
    
    return run_meta


if __name__ == "__main__":
    main()