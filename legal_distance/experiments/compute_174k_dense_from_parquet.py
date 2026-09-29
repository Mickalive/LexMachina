#!/usr/bin/env python3
"""
Year-split dense embedding computation for 174k corpus from parquet data.

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
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
PARQUET_PATH = Path("/tmp/bger.parquet")
METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
BATCH_SIZE = 128
EMBEDDING_DIM = 768

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


def load_parquet_texts():
    """Load full_text from parquet, keyed by decision_id."""
    logger.info(f"Loading parquet from {PARQUET_PATH}...")
    df = pd.read_parquet(PARQUET_PATH)
    logger.info(f"Loaded {len(df)} rows from parquet")
    
    # Create decision_id -> full_text mapping
    text_map = {}
    for _, row in df.iterrows():
        did = row['decision_id']
        text = row['full_text']
        if pd.notna(text) and text.strip():
            text_map[did] = text
        else:
            # Fallback: use title + legal_area + regeste
            fallback = f"{row.get('title', '')} {row.get('legal_area', '')} {row.get('regeste', '')}"
            text_map[did] = fallback.strip()
    
    logger.info(f"Built text map for {len(text_map)} decisions")
    return text_map


def prepare_year_texts(year, metadata, text_map):
    """Prepare texts for a specific year in metadata order."""
    year_meta = [m for m in metadata if m.get('year') == year]
    logger.info(f"  Year {year}: {len(year_meta)} decisions in metadata")
    
    texts = []
    meta_out = []
    for m in year_meta:
        did = m['decision_id']
        if did in text_map:
            texts.append(text_map[did])
            meta_out.append(m)
        else:
            logger.warning(f"  Missing text for {did}")
            texts.append("")
            meta_out.append(None)
    
    # Filter to only non-empty texts
    valid_indices = [i for i, t in enumerate(texts) if t.strip()]
    valid_texts = [texts[i] for i in valid_indices]
    valid_meta = [meta_out[i] for i in valid_indices]
    
    logger.info(f"  Year {year}: {len(valid_texts)} valid texts")
    return valid_texts, valid_meta, year_meta


def save_checkpoint(year, embeddings, metadata):
    """Save year embeddings and metadata as checkpoint."""
    np.save(CHECKPOINT_DIR / EMBEDDINGS_PATTERN.format(year=year), embeddings.astype(np.float32))
    with open(CHECKPOINT_DIR / METADATA_PATTERN.format(year=year), 'w') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    logger.info(f"  Saved checkpoint for {year}: {embeddings.shape}")


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
    logger.info("YEAR-SPLIT 174K DENSE EMBEDDING COMPUTATION (from parquet)")
    logger.info("=" * 70)
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Model: {MODEL_NAME}")
    logger.info(f"Batch size: {BATCH_SIZE}")
    logger.info(f"Output dir: {OUTPUT_DIR}")

    # Load metadata index (canonical order)
    metadata = load_metadata_index()
    logger.info(f"Total decisions in metadata: {len(metadata)}")

    # Load parquet texts
    text_map = load_parquet_texts()

    # Load model
    logger.info(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    logger.info("Model loaded")

    # Load progress
    progress = load_progress()
    completed_years = set(progress["completed_years"])
    logger.info(f"Previously completed years: {sorted(completed_years)}")

    # Get years to process (from metadata)
    years_in_metadata = sorted(set(m.get('year') for m in metadata if m.get('year') is not None))
    logger.info(f"Years in metadata: {years_in_metadata}")

    # Process each year
    all_embeddings_list = []
    all_metadata_list = []
    year_indices = {}
    current_idx = 0

    for year in years_in_metadata:
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
        logger.info(f"Processing {year}...")
        valid_texts, valid_meta, year_meta = prepare_year_texts(year, metadata, text_map)

        if not valid_texts:
            logger.info(f"  No valid texts for {year}, skipping")
            progress["failed_years"].append(year)
            save_progress(progress)
            continue

        logger.info(f"  Computing embeddings for {len(valid_texts)} decisions...")
        start = time.time()
        embeddings = model.encode(valid_texts, batch_size=BATCH_SIZE, show_progress_bar=True, convert_to_numpy=True)
        elapsed = time.time() - start
        logger.info(f"  Computed {embeddings.shape} in {elapsed:.1f}s ({len(valid_texts)/elapsed:.1f} decisions/s)")

        # Save checkpoint
        save_checkpoint(year, embeddings, valid_meta)

        # Accumulate
        all_embeddings_list.append(embeddings)
        all_metadata_list.extend(valid_meta)
        year_indices[year] = (current_idx, current_idx + len(embeddings))
        current_idx += len(embeddings)

        # Update progress
        progress["completed_years"].append(year)
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
    languages = sorted(set(m.get('language', 'unknown') for m in metadata))
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
        "direction_version": 28,
        "model": MODEL_NAME,
        "n_decisions": len(metadata),
        "embedding_dim": EMBEDDING_DIM,
        "year_indices": year_indices,
        "languages": languages,
        "language_counts": {lang: sum(1 for m in metadata if m.get('language') == lang) for lang in languages},
        "files": {
            "embeddings_768": "embeddings_768.npy",
            "embeddings_center_projected": "embeddings_center_projected.npy",
            "embeddings_center_projected_64": "embeddings_center_projected_64.npy",
            "embeddings_center_projected_128": "embeddings_center_projected_128.npy",
            "metadata": "metadata.json",
        },
        "corpus_note": "173,963 decisions from parquet (2000-2026). Full-text used for embeddings.",
    }

    with open(OUTPUT_DIR / "run_metadata.json", 'w') as f:
        json.dump(run_meta, f, indent=2, ensure_ascii=False)

    logger.info("=" * 70)
    logger.info("174K DENSE EMBEDDING COMPUTATION COMPLETE")
    logger.info("=" * 70)

    return run_meta


if __name__ == "__main__":
    main()