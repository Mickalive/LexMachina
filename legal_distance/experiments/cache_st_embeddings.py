#!/usr/bin/env python3
"""
Cache sentence transformer embeddings for the 1200-decision expanded corpus.

This ensures reproducibility across all experiments by computing embeddings once
and having all downstream scripts load from the same cached file.
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
EXPANDED_CORPUS_FILE = Path("/tmp/lex_accepted/evaluation/evaluation/data/bger_expanded_1200.jsonl")
EXPANDED_METADATA_FILE = Path("/tmp/lex_accepted/evaluation/evaluation/data/bger_expanded_1200_metadata.jsonl")
CACHE_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/cached_embeddings")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ST_EMBEDDINGS_FILE = CACHE_DIR / "st_embeddings_1200_paraphrase-multilingual-MiniLM-L12-v2_erwaegungen_2000.npy"
ST_EMBEDDINGS_META_FILE = CACHE_DIR / "st_embeddings_1200_metadata.json"

def load_expanded_corpus() -> Tuple[List[Dict], List[Dict]]:
    """Load the 1200-decision expanded corpus and metadata."""
    corpus = []
    with open(EXPANDED_CORPUS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            corpus.append(json.loads(line))
    
    metadata = []
    with open(EXPANDED_METADATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            metadata.append(json.loads(line))
    
    logger.info(f"Loaded expanded corpus: {len(corpus)} decisions, {len(metadata)} metadata entries")
    return corpus, metadata

def compute_sentence_transformer_embeddings(corpus: List[Dict]) -> np.ndarray:
    """Compute sentence transformer embeddings for the corpus."""
    from sentence_transformers import SentenceTransformer
    
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    
    # Use erwaegungen_text[:2000] as in both validation scripts
    texts = []
    for d in corpus:
        text = d.get('erwaegungen_text', '')[:2000]
        if not text:
            text = d.get('decision_id', '')
        texts.append(text)
    
    logger.info(f"Computing embeddings for {len(texts)} decisions...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    logger.info(f"Embeddings shape: {embeddings.shape}")
    return embeddings

def main():
    logger.info("=" * 70)
    logger.info("Caching Sentence Transformer Embeddings for 1200-Decision Corpus")
    logger.info("=" * 70)
    
    # Check if already cached
    if ST_EMBEDDINGS_FILE.exists() and ST_EMBEDDINGS_META_FILE.exists():
        logger.info(f"Cache already exists at {ST_EMBEDDINGS_FILE}")
        logger.info("Loading to verify...")
        embeddings = np.load(ST_EMBEDDINGS_FILE)
        with open(ST_EMBEDDINGS_META_FILE, 'r') as f:
            meta = json.load(f)
        logger.info(f"Cached embeddings shape: {embeddings.shape}")
        logger.info(f"Cached metadata count: {len(meta)}")
        logger.info(f"Model: {meta.get('model')}")
        logger.info(f"Text source: {meta.get('text_source')}")
        logger.info(f"Max length: {meta.get('max_length')}")
        return
    
    # Load corpus
    logger.info("\n1. Loading 1200-decision expanded corpus...")
    corpus, metadata = load_expanded_corpus()
    
    # Compute embeddings
    logger.info("\n2. Computing sentence transformer embeddings...")
    embeddings = compute_sentence_transformer_embeddings(corpus)
    
    # Save cache
    logger.info("\n3. Saving cached embeddings...")
    np.save(ST_EMBEDDINGS_FILE, embeddings)
    
    cache_meta = {
        'model': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
        'text_source': 'erwaegungen_text',
        'max_length': 2000,
        'n_decisions': len(corpus),
        'embedding_dim': int(embeddings.shape[1]),
        'corpus_file': str(EXPANDED_CORPUS_FILE),
        'metadata_file': str(EXPANDED_METADATA_FILE),
    }
    
    with open(ST_EMBEDDINGS_META_FILE, 'w') as f:
        json.dump(cache_meta, f, indent=2)
    
    logger.info(f"  Embeddings saved to: {ST_EMBEDDINGS_FILE}")
    logger.info(f"  Metadata saved to: {ST_EMBEDDINGS_META_FILE}")
    logger.info(f"  Shape: {embeddings.shape}")
    
    logger.info("\n=== Caching Complete ===")

if __name__ == "__main__":
    main()