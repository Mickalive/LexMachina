#!/usr/bin/env python3
"""
Flat-map baseline for fractal-map lane.
Computes document embeddings and creates a 2D UMAP projection as baseline.
"""
import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
import umap
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CORPUS_PATH = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical/bger_2000plus_slice_1000.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Use a multilingual model since corpus has DE, FR, IT
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

def load_corpus(limit=None):
    """Load decisions from JSONL corpus."""
    decisions = []
    with open(CORPUS_PATH, 'r') as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            decisions.append(json.loads(line))
    logger.info(f"Loaded {len(decisions)} decisions")
    return decisions

def prepare_texts(decisions):
    """Prepare text for embedding - use full_text for now."""
    texts = []
    metadata = []
    for d in decisions:
        # Use full_text as the primary content
        text = d.get('full_text', '')
        if not text:
            # Fallback to title + legal_area
            text = f"{d.get('title', '')} {d.get('legal_area', '')}"
        texts.append(text)
        metadata.append({
            'decision_id': d.get('decision_id'),
            'language': d.get('language'),
            'legal_area': d.get('legal_area'),
            'year': d.get('decision_date', '')[:4] if d.get('decision_date') else None,
            'court': d.get('court'),
            'chamber': d.get('chamber'),
        })
    return texts, metadata

def compute_embeddings(texts, model_name=MODEL_NAME, batch_size=32):
    """Compute embeddings using sentence transformer."""
    logger.info(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    logger.info(f"Computing embeddings for {len(texts)} texts...")
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=True, convert_to_numpy=True)
    logger.info(f"Embeddings shape: {embeddings.shape}")
    return embeddings

def compute_umap(embeddings, n_neighbors=15, min_dist=0.1, n_components=2, metric='cosine', random_state=42):
    """Compute UMAP projection."""
    logger.info(f"Computing UMAP with n_neighbors={n_neighbors}, min_dist={min_dist}, metric={metric}")
    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        n_components=n_components,
        metric=metric,
        random_state=random_state
    )
    projection = reducer.fit_transform(embeddings)
    logger.info(f"Projection shape: {projection.shape}")
    return projection, reducer

def save_results(embeddings, projection, metadata, reducer=None):
    """Save embeddings, projection, and metadata."""
    np.save(OUTPUT_DIR / "embeddings.npy", embeddings)
    np.save(OUTPUT_DIR / "projection_2d.npy", projection)
    with open(OUTPUT_DIR / "metadata.json", 'w') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # Save UMAP parameters for reproducibility
    umap_params = {
        'n_neighbors': 15,
        'min_dist': 0.1,
        'n_components': 2,
        'metric': 'cosine',
        'random_state': 42
    }
    with open(OUTPUT_DIR / "umap_params.json", 'w') as f:
        json.dump(umap_params, f, indent=2)
    
    logger.info(f"Saved results to {OUTPUT_DIR}")

def main():
    logger.info("Starting flat-map baseline computation")
    decisions = load_corpus()
    texts, metadata = prepare_texts(decisions)
    embeddings = compute_embeddings(texts)
    projection, reducer = compute_umap(embeddings)
    save_results(embeddings, projection, metadata, reducer)
    logger.info("Flat-map baseline complete")

if __name__ == "__main__":
    main()