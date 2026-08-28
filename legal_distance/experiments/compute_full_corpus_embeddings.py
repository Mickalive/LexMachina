#!/usr/bin/env python3
"""
Compute 768-dim embeddings for full 1200-decision corpus and create center_projected.
Uses the same model as the fractal-map baseline: paraphrase-multilingual-mpnet-base-v2
"""

import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

FULL_CORPUS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

def load_full_corpus():
    corpus = []
    with open(FULL_CORPUS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            corpus.append(json.loads(line))
    logger.info(f"Loaded {len(corpus)} decisions from full corpus")
    return corpus

def prepare_texts(corpus):
    texts = []
    metadata = []
    for d in corpus:
        text = d.get('full_text', '')
        if not text:
            text = f"{d.get('title', '')} {d.get('legal_area', '')}"
        texts.append(text)
        metadata.append({
            'decision_id': d.get('decision_id'),
            'language': d.get('language'),
            'legal_area': d.get('legal_area'),
            'year': d.get('decision_date', '')[:4] if d.get('decision_date') else None,
            'court': d.get('court'),
            'chamber': d.get('chamber'),
            'branch': d.get('branch'),
        })
    return texts, metadata

def compute_embeddings(texts, model_name=MODEL_NAME, batch_size=32):
    logger.info(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    logger.info(f"Computing embeddings for {len(texts)} texts...")
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=True, convert_to_numpy=True)
    logger.info(f"Embeddings shape: {embeddings.shape}")
    return embeddings

def create_center_projected(embeddings: np.ndarray, metadata: list) -> np.ndarray:
    """Create center_projected by subtracting language centers."""
    languages = sorted(set(m['language'] for m in metadata))
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
    return debiased

def main():
    logger.info("=" * 70)
    logger.info("COMPUTE FULL CORPUS EMBEDDINGS AND CENTER_PROJECTED")
    logger.info("=" * 70)
    
    # Load corpus
    corpus = load_full_corpus()
    texts, metadata = prepare_texts(corpus)
    
    # Compute 768-dim embeddings
    embeddings = compute_embeddings(texts)
    
    # Save raw embeddings
    np.save(OUTPUT_DIR / "embeddings_768.npy", embeddings)
    with open(OUTPUT_DIR / "metadata.json", 'w') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved 768-dim embeddings to {OUTPUT_DIR / 'embeddings_768.npy'}")
    
    # Create center_projected
    center_projected = create_center_projected(embeddings, metadata)
    
    # Save center_projected
    np.save(OUTPUT_DIR / "embeddings_center_projected.npy", center_projected)
    logger.info(f"Saved center_projected to {OUTPUT_DIR / 'embeddings_center_projected.npy'}")
    
    # Also create 64-dim PCA version for hybrid compatibility
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import normalize
    
    pca_64 = PCA(n_components=64, random_state=42)
    center_projected_64 = pca_64.fit_transform(center_projected)
    center_projected_64 = normalize(center_projected_64, norm='l2', axis=1)
    np.save(OUTPUT_DIR / "embeddings_center_projected_64.npy", center_projected_64)
    logger.info(f"Saved center_projected_64 to {OUTPUT_DIR / 'embeddings_center_projected_64.npy'}")
    logger.info(f"  Explained variance ratio (64 components): {pca_64.explained_variance_ratio_.sum():.4f}")
    
    # Create 128-dim version
    pca_128 = PCA(n_components=128, random_state=42)
    center_projected_128 = pca_128.fit_transform(center_projected)
    center_projected_128 = normalize(center_projected_128, norm='l2', axis=1)
    np.save(OUTPUT_DIR / "embeddings_center_projected_128.npy", center_projected_128)
    logger.info(f"Saved center_projected_128 to {OUTPUT_DIR / 'embeddings_center_projected_128.npy'}")
    logger.info(f"  Explained variance ratio (128 components): {pca_128.explained_variance_ratio_.sum():.4f}")
    
    logger.info("=" * 70)
    logger.info("COMPLETE")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()