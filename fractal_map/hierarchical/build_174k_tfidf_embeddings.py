#!/usr/bin/env python3
"""
Build TF-IDF embeddings for 174k corpus using available fields:
1. regeste_tfidf - TF-IDF on case summary/headnote (strong legal signal)
2. regeste_full_text_hybrid_0.5 - 50/50 hybrid (using truncated full_text)
3. regeste_full_text_hybrid_0.7 - 70/30 regeste / 30 full_text

Uses compressed 5-level resolution ladder [0.25, 0.5, 1.0, 2.0, 3.0]
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
import logging
from datetime import datetime, timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k/metadata_174k_full.json")
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k/tfidf_embeddings")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDING_DIM = 128

# Regeste params (legal summary - strong signal, fast)
REGESTE_MAX_FEATURES = 10000
REGESTE_MIN_DF = 2
REGESTE_MAX_DF = 0.95
REGESTE_NGRAM_RANGE = (1, 2)

# Full text params (lighter for speed)
FULL_TEXT_MAX_FEATURES = 3000
FULL_TEXT_MIN_DF = 5
FULL_TEXT_MAX_DF = 0.9
FULL_TEXT_NGRAM_RANGE = (1, 1)  # unigrams only for speed

COMPRESSED_LADDER = [0.25, 0.5, 1.0, 2.0, 3.0]


def load_metadata():
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    return metadata


def load_corpus_decisions(metadata):
    decision_ids = set(m['decision_id'] for m in metadata)
    decisions = {}
    
    # Use bger_*.jsonl files (full corpus)
    for year_file in sorted(CORPUS_DIR.glob("bger_*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                if d['decision_id'] in decision_ids:
                    decisions[d['decision_id']] = d
    
    logger.info(f"Loaded {len(decisions)} decisions from corpus")
    return decisions


def extract_field_text(decisions, metadata, field_name):
    texts = []
    for m in metadata:
        did = m['decision_id']
        if did in decisions:
            d = decisions[did]
            val = d.get(field_name, '')
            if val is None:
                val = ''
            texts.append(str(val))
        else:
            texts.append('')
    return texts


def compute_tfidf(texts, name, max_features, min_df, max_df, ngram_range):
    logger.info(f"Computing TF-IDF for {name}...")
    
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=ngram_range,
        sublinear_tf=True,
        min_df=min_df,
        max_df=max_df,
        strip_accents='unicode'
    )
    
    tfidf_matrix = vectorizer.fit_transform(texts)
    logger.info(f"  TF-IDF matrix: {tfidf_matrix.shape}")
    
    n_comp = min(EMBEDDING_DIM, tfidf_matrix.shape[1] - 1, tfidf_matrix.shape[0] - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    reduced = svd.fit_transform(tfidf_matrix)
    
    reduced = normalize(reduced, norm='l2', axis=1)
    
    if reduced.shape[1] < EMBEDDING_DIM:
        padding = np.zeros((reduced.shape[0], EMBEDDING_DIM - reduced.shape[1]))
        reduced = np.hstack([reduced, padding])
    
    logger.info(f"  {name} embeddings: {reduced.shape}")
    return reduced


def save_embeddings(embeddings, name):
    path = OUTPUT_DIR / f"{name}.npy"
    np.save(path, embeddings.astype(np.float32))
    logger.info(f"Saved {name} to {path}")
    return path


def main():
    logger.info("=== Building 174k TF-IDF Embeddings (regeste + light full_text) ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    metadata = load_metadata()
    decisions = load_corpus_decisions(metadata)
    
    logger.info("\nExtracting regeste text...")
    regeste_texts = extract_field_text(decisions, metadata, 'regeste')
    non_empty_regeste = sum(1 for t in regeste_texts if t.strip() and t != 'None')
    logger.info(f"  Non-empty regeste: {non_empty_regeste}/{len(regeste_texts)}")
    
    logger.info("\nExtracting full_text (truncated for speed)...")
    full_texts = extract_field_text(decisions, metadata, 'full_text')
    # Truncate full_text to first 5000 chars for speed
    full_texts_truncated = [t[:5000] for t in full_texts]
    non_empty_full = sum(1 for t in full_texts_truncated if t.strip() and t != 'None')
    logger.info(f"  Non-empty full_text (truncated): {non_empty_full}/{len(full_texts_truncated)}")
    
    logger.info("\n--- Computing TF-IDF Embeddings ---")
    regeste_emb = compute_tfidf(regeste_texts, "regeste_tfidf", 
                                 REGESTE_MAX_FEATURES, REGESTE_MIN_DF, REGESTE_MAX_DF, REGESTE_NGRAM_RANGE)
    full_text_emb = compute_tfidf(full_texts_truncated, "full_text_tfidf_light",
                                   FULL_TEXT_MAX_FEATURES, FULL_TEXT_MIN_DF, FULL_TEXT_MAX_DF, FULL_TEXT_NGRAM_RANGE)
    
    logger.info("\n--- Computing Hybrid Embeddings ---")
    hybrid_05 = 0.5 * regeste_emb + 0.5 * full_text_emb
    hybrid_05 = normalize(hybrid_05, norm='l2', axis=1)
    
    hybrid_07 = 0.7 * regeste_emb + 0.3 * full_text_emb
    hybrid_07 = normalize(hybrid_07, norm='l2', axis=1)
    
    save_embeddings(regeste_emb, "regeste_tfidf")
    save_embeddings(full_text_emb, "full_text_tfidf_light")
    save_embeddings(hybrid_05, "regeste_full_text_hybrid_0.5")
    save_embeddings(hybrid_07, "regeste_full_text_hybrid_0.7")
    
    metadata_ref = {
        "run_id": f"tfidf_embeddings_174k_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 25,
        "n_decisions": len(metadata),
        "embedding_dim": EMBEDDING_DIM,
        "embeddings": {
            "regeste_tfidf": "regeste_tfidf.npy",
            "full_text_tfidf_light": "full_text_tfidf_light.npy",
            "regeste_full_text_hybrid_0.5": "regeste_full_text_hybrid_0.5.npy",
            "regeste_full_text_hybrid_0.7": "regeste_full_text_hybrid_0.7.npy",
        },
        "tfidf_params": {
            "regeste": {"max_features": REGESTE_MAX_FEATURES, "ngram_range": REGESTE_NGRAM_RANGE, "min_df": REGESTE_MIN_DF, "max_df": REGESTE_MAX_DF},
            "full_text_light": {"max_features": FULL_TEXT_MAX_FEATURES, "ngram_range": FULL_TEXT_NGRAM_RANGE, "min_df": FULL_TEXT_MIN_DF, "max_df": FULL_TEXT_MAX_DF},
        },
        "field_coverage": {
            "regeste": non_empty_regeste / len(regeste_texts),
            "full_text": non_empty_full / len(full_texts_truncated),
        },
        "corpus_note": "174,113 decisions from bger_*.jsonl files. Primary signal: regeste (case summary). Full-text truncated to 5k chars for speed.",
    }
    
    with open(OUTPUT_DIR / "embeddings_metadata.json", 'w') as f:
        json.dump(metadata_ref, f, indent=2)
    
    logger.info("\n=== 174k TF-IDF embeddings complete ===")


if __name__ == "__main__":
    main()
