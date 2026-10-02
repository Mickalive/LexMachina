#!/usr/bin/env python3
"""
Compute dense embeddings for remaining years (2022-2026) to complete 174k assembly.
Uses existing checkpoint directory with progress up to 2021.
"""
import json
import numpy as np
import pyarrow.parquet as pq
import pandas as pd
from pathlib import Path
from sentence_transformers import SentenceTransformer
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Configuration - use the working directory checkpoint path which has more progress
PARQUET_PATH = Path("/tmp/lex_accepted/corpus/corpus/acquisition/parquet/bger.parquet")
CHECKPOINT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/checkpoints")
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
BATCH_SIZE = 32
TARGET_YEARS = list(range(2022, 2027))  # 2022-2026 inclusive

PROGRESS_FILE = CHECKPOINT_DIR / "progress.json"

def load_progress():
    """Load progress from checkpoint."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"completed_years": [], "failed_years": []}

def save_progress(progress):
    """Save progress to checkpoint."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def get_year_data(year):
    """Extract texts and metadata for a specific year from parquet."""
    pf = pq.ParquetFile(PARQUET_PATH)
    year_texts = []
    year_metadata = []
    
    for rg_idx in range(pf.metadata.num_row_groups):
        table = pf.read_row_group(rg_idx)
        df = table.to_pandas()
        
        # Filter by year
        df['year'] = pd.to_datetime(df['decision_date'], errors='coerce').dt.year
        year_df = df[df['year'] == year]
        
        if len(year_df) == 0:
            continue
            
        # Extract texts and metadata
        for _, row in year_df.iterrows():
            full_text = row.get('full_text', '')
            if not full_text or pd.isna(full_text):
                full_text = ''
            
            # Use full_text for embedding
            year_texts.append(full_text)
            
            year_metadata.append({
                'decision_id': str(row.get('decision_id', '')),
                'language': str(row.get('language', 'de')),
                'branch': str(row.get('branch', '')) if pd.notna(row.get('branch')) else 'unknown',
                'chamber': str(row.get('chamber', '')) if pd.notna(row.get('chamber')) else 'unknown',
                'legal_area': str(row.get('legal_area', '')) if pd.notna(row.get('legal_area')) else 'unknown',
                'year': str(year)
            })
    
    return year_texts, year_metadata

def compute_embeddings(texts, model, batch_size=32):
    """Compute embeddings for a list of texts."""
    if not texts:
        return np.array([]).reshape(0, 768)
    
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=False
    )
    return embeddings.astype(np.float32)

def main():
    logger.info("=" * 70)
    logger.info("DENSE EMBEDDING COMPUTATION FOR REMAINING YEARS (2022-2026)")
    logger.info(f"Model: {MODEL_NAME}")
    logger.info(f"Target years: {TARGET_YEARS}")
    logger.info(f"Checkpoint dir: {CHECKPOINT_DIR}")
    logger.info("=" * 70)
    
    # Load progress
    progress = load_progress()
    completed_years = set(progress.get("completed_years", []))
    logger.info(f"Already completed: {sorted(completed_years)}")
    
    # Load model
    logger.info(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    logger.info("Model loaded")
    
    # Process each year
    for year in TARGET_YEARS:
        if str(year) in completed_years:
            logger.info(f"Year {year}: SKIPPED (already completed)")
            continue
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing year {year}...")
        logger.info(f"{'='*50}")
        
        start_time = time.time()
        
        try:
            # Get year data
            texts, metadata = get_year_data(year)
            logger.info(f"Year {year}: {len(texts)} decisions")
            
            if len(texts) == 0:
                logger.warning(f"Year {year}: No decisions found")
                progress["failed_years"].append(str(year))
                save_progress(progress)
                continue
            
            # Compute embeddings
            logger.info(f"Computing embeddings for {len(texts)} texts...")
            embeddings = compute_embeddings(texts, model, BATCH_SIZE)
            
            # Normalize embeddings
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1
            embeddings = embeddings / norms
            
            # Save checkpoint
            emb_path = CHECKPOINT_DIR / f"embeddings_{year}.npy"
            meta_path = CHECKPOINT_DIR / f"metadata_{year}.json"
            
            np.save(emb_path, embeddings)
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            elapsed = time.time() - start_time
            logger.info(f"Year {year} COMPLETED: {embeddings.shape[0]} embeddings, {embeddings.shape[1]} dims, {elapsed:.1f}s")
            logger.info(f"  Saved: {emb_path}")
            logger.info(f"  Saved: {meta_path}")
            
            # Update progress
            progress["completed_years"].append(str(year))
            save_progress(progress)
            
        except Exception as e:
            logger.error(f"Year {year} FAILED: {e}", exc_info=True)
            progress["failed_years"].append(str(year))
            save_progress(progress)
    
    # Final summary
    logger.info("\n" + "=" * 70)
    logger.info("COMPUTATION COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Completed years: {sorted(progress['completed_years'])}")
    logger.info(f"Failed years: {progress['failed_years']}")
    
    # Verify all checkpoints
    total_embeddings = 0
    for year in sorted(progress['completed_years']):
        emb_path = CHECKPOINT_DIR / f"embeddings_{year}.npy"
        if emb_path.exists():
            emb = np.load(emb_path, mmap_mode='r')
            total_embeddings += emb.shape[0]
            logger.info(f"  {year}: {emb.shape[0]} embeddings")
    
    logger.info(f"Total embeddings: {total_embeddings}")

if __name__ == "__main__":
    main()