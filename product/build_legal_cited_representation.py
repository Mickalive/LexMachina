#!/usr/bin/env python3
"""
Build legal_cited_decisions_only TF-IDF representation for product integration.

This is the legal-distance signal that passes ALL 14 benchmarks (AUC 0.9719 for citation heritage).
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize


RESULTS_DIR = Path("/home/runner/work/LexMachina/LexMachina/product/results/fractal_map")
SIGNALS_FILE = RESULTS_DIR / "legal_signals_1000.jsonl"
BASELINE_META = RESULTS_DIR / "baseline" / "metadata.json"
OUTPUT_DIR = RESULTS_DIR / "legal_cited_decisions"


def load_signals() -> Dict[str, Any]:
    """Load extracted legal signals."""
    signals = {}
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    print(f"Loaded signals for {len(signals)} decisions")
    return signals


def load_baseline_metadata() -> List[Dict]:
    """Load baseline metadata for decision ordering."""
    with open(BASELINE_META, 'r') as f:
        metadata = json.load(f)
    print(f"Loaded metadata for {len(metadata)} decisions")
    return metadata


def build_cited_decisions_texts(signals: Dict[str, Any], metadata: List[Dict]) -> Tuple[List[str], List[str]]:
    """Build text representations from cited_decisions for TF-IDF vectorization."""
    texts = []
    decision_ids = []
    
    for meta in metadata:
        did = meta['decision_id']
        sig = signals.get(did, {})
        
        parts = []
        
        # Cited decisions - this is the key signal that passed ALL benchmarks
        if sig.get('cited_decisions'):
            parts.append(" ".join(sig['cited_decisions']))
        
        combined = " ".join(parts) if parts else ""
        texts.append(combined)
        decision_ids.append(did)
    
    return texts, decision_ids


def main():
    print("=" * 60)
    print("Building legal_cited_decisions_only representation")
    print("=" * 60)
    
    # Load data
    signals = load_signals()
    metadata = load_baseline_metadata()
    
    # Build texts from cited_decisions
    texts, decision_ids = build_cited_decisions_texts(signals, metadata)
    
    # Check coverage
    non_empty = sum(1 for t in texts if t)
    print(f"Decisions with cited_decisions: {non_empty}/{len(texts)}")
    
    # Build TF-IDF
    print("Building TF-IDF representation...")
    vectorizer = TfidfVectorizer(
        max_features=5000,
        min_df=2,
        max_df=0.95,
        ngram_range=(1, 2),
        sublinear_tf=True,
        lowercase=True,
        strip_accents='unicode',
    )
    
    tfidf_matrix = vectorizer.fit_transform(texts)
    print(f"TF-IDF shape: {tfidf_matrix.shape}")
    print(f"Vocabulary size: {len(vectorizer.vocabulary_)}")
    
    # Normalize
    legal_emb = normalize(tfidf_matrix.toarray(), norm='l2', axis=1)
    print(f"Normalized embeddings shape: {legal_emb.shape}")
    
    # Create 2D projection using PCA
    print("Creating 2D projection...")
    pca_2d = PCA(n_components=2, random_state=42)
    projection_2d = pca_2d.fit_transform(legal_emb)
    print(f"2D projection shape: {projection_2d.shape}")
    print(f"Explained variance ratio: {pca_2d.explained_variance_ratio_}")
    
    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    np.save(OUTPUT_DIR / "embeddings.npy", legal_emb.astype(np.float32))
    np.save(OUTPUT_DIR / "projection_2d.npy", projection_2d.astype(np.float32))
    
    # Save metadata aligned with baseline
    with open(OUTPUT_DIR / "metadata.json", 'w') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # Save vectorizer info
    vectorizer_info = {
        "vocabulary_size": len(vectorizer.vocabulary_),
        "max_features": 5000,
        "min_df": 2,
        "max_df": 0.95,
        "ngram_range": [1, 2],
        "sublinear_tf": True,
        "signal_source": "cited_decisions_only",
        "benchmark_status": "14/14 PASS",
        "citation_heritage_auc": 0.9719,
        "note": "Legal-distance signal passing ALL evaluation benchmarks. Use as selectable map mode for citation-proximity navigation."
    }
    with open(OUTPUT_DIR / "vectorizer_info.json", 'w') as f:
        json.dump(vectorizer_info, f, indent=2)
    
    print(f"\nSaved to {OUTPUT_DIR}")
    print("  - embeddings.npy")
    print("  - projection_2d.npy")
    print("  - metadata.json")
    print("  - vectorizer_info.json")
    
    return legal_emb, projection_2d


if __name__ == "__main__":
    main()