#!/usr/bin/env python3
"""
Build legal-signal TF-IDF embeddings for 174k corpus:
1. cited_decisions_tfidf - TF-IDF on cited decisions (strong doctrinal signal)
2. outcome_tfidf - TF-IDF on outcome/disposition (strong outcome signal)
3. regeste_tfidf - TF-IDF on case summary/headnote (strong legal signal)
4. full_text_tfidf_light - TF-IDF on truncated full_text

Creates hybrids:
- cited_decisions_tfidf_outcome_hybrid_0.5 (BEST PRODUCTION)
- cited_decisions_tfidf_outcome_hybrid_0.7 (BEST FRACTAL)
- regeste_full_text_hybrid_0.5
- regeste_full_text_hybrid_0.7
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
import logging
from datetime import datetime, timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD, PCA
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

METADATA_PATH = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k/metadata_174k_full.json")
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDING_DIM = 128

# Cited decisions params
CITED_MAX_FEATURES = 5000
CITED_MIN_DF = 2
CITED_MAX_DF = 0.95
CITED_NGRAM_RANGE = (1, 2)

# Outcome params
OUTCOME_MAX_FEATURES = 3000
OUTCOME_MIN_DF = 2
OUTCOME_MAX_DF = 0.95
OUTCOME_NGRAM_RANGE = (1, 2)

# Regeste params
REGESTE_MAX_FEATURES = 10000
REGESTE_MIN_DF = 2
REGESTE_MAX_DF = 0.95
REGESTE_NGRAM_RANGE = (1, 2)

# Full text params (lighter for speed)
FULL_TEXT_MAX_FEATURES = 3000
FULL_TEXT_MIN_DF = 5
FULL_TEXT_MAX_DF = 0.9
FULL_TEXT_NGRAM_RANGE = (1, 1)  # unigrams only for speed


def load_metadata():
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    return metadata


def load_corpus_decisions(metadata):
    decision_ids = set(m['decision_id'] for m in metadata)
    decisions = {}
    
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


def create_hybrid(emb_a, emb_b, alpha):
    """Create hybrid: alpha * emb_a + (1-alpha) * emb_b"""
    target_dim = min(emb_a.shape[1], emb_b.shape[1])
    
    if emb_a.shape[1] != target_dim:
        pca_a = PCA(n_components=target_dim, random_state=42)
        emb_a = pca_a.fit_transform(emb_a)
    if emb_b.shape[1] != target_dim:
        pca_b = PCA(n_components=target_dim, random_state=42)
        emb_b = pca_b.fit_transform(emb_b)
    
    norms_a = np.linalg.norm(emb_a, axis=1, keepdims=True)
    norms_a[norms_a == 0] = 1
    emb_a_norm = emb_a / norms_a
    
    norms_b = np.linalg.norm(emb_b, axis=1, keepdims=True)
    norms_b[norms_b == 0] = 1
    emb_b_norm = emb_b / norms_b
    
    hybrid = alpha * emb_a_norm + (1 - alpha) * emb_b_norm
    norms = np.linalg.norm(hybrid, axis=1, keepdims=True)
    norms[norms == 0] = 1
    hybrid = hybrid / norms
    
    return hybrid


def save_embeddings(embeddings, name):
    path = OUTPUT_DIR / f"{name}.npy"
    np.save(path, embeddings.astype(np.float32))
    logger.info(f"Saved {name} to {path}")
    return path


def main():
    logger.info("=== Building 174k Legal TF-IDF Embeddings ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    metadata = load_metadata()
    decisions = load_corpus_decisions(metadata)
    
    logger.info("\nExtracting cited_decisions text...")
    cited_texts = []
    for m in metadata:
        did = m['decision_id']
        if did in decisions:
            cited = decisions[did].get('cited_decisions', [])
            if cited:
                cited_texts.append(" ".join(cited))
            else:
                cited_texts.append("")
        else:
            cited_texts.append("")
    non_empty_cited = sum(1 for t in cited_texts if t.strip())
    logger.info(f"  Non-empty cited_decisions: {non_empty_cited}/{len(cited_texts)}")
    
    logger.info("\nExtracting outcome text...")
    outcome_texts = []
    for m in metadata:
        did = m['decision_id']
        if did in decisions:
            outcome = decisions[did].get('outcome', '')
            if outcome and outcome != 'null':
                outcome_texts.append(str(outcome))
            else:
                outcome_texts.append("")
        else:
            outcome_texts.append("")
    non_empty_outcome = sum(1 for t in outcome_texts if t.strip())
    logger.info(f"  Non-empty outcome: {non_empty_outcome}/{len(outcome_texts)}")
    
    logger.info("\nExtracting regeste text...")
    regeste_texts = extract_field_text(decisions, metadata, 'regeste')
    non_empty_regeste = sum(1 for t in regeste_texts if t.strip() and t != 'None')
    logger.info(f"  Non-empty regeste: {non_empty_regeste}/{len(regeste_texts)}")
    
    logger.info("\nExtracting full_text (truncated for speed)...")
    full_texts = extract_field_text(decisions, metadata, 'full_text')
    full_texts_truncated = [t[:5000] for t in full_texts]
    non_empty_full = sum(1 for t in full_texts_truncated if t.strip() and t != 'None')
    logger.info(f"  Non-empty full_text (truncated): {non_empty_full}/{len(full_texts_truncated)}")
    
    logger.info("\n--- Computing TF-IDF Embeddings ---")
    cited_emb = compute_tfidf(cited_texts, "cited_decisions_tfidf",
                               CITED_MAX_FEATURES, CITED_MIN_DF, CITED_MAX_DF, CITED_NGRAM_RANGE)
    outcome_emb = compute_tfidf(outcome_texts, "outcome_tfidf",
                                 OUTCOME_MAX_FEATURES, OUTCOME_MIN_DF, OUTCOME_MAX_DF, OUTCOME_NGRAM_RANGE)
    regeste_emb = compute_tfidf(regeste_texts, "regeste_tfidf",
                                 REGESTE_MAX_FEATURES, REGESTE_MIN_DF, REGESTE_MAX_DF, REGESTE_NGRAM_RANGE)
    full_text_emb = compute_tfidf(full_texts_truncated, "full_text_tfidf_light",
                                   FULL_TEXT_MAX_FEATURES, FULL_TEXT_MIN_DF, FULL_TEXT_MAX_DF, FULL_TEXT_NGRAM_RANGE)
    
    logger.info("\n--- Computing Hybrid Embeddings ---")
    hybrid_05 = create_hybrid(cited_emb, outcome_emb, 0.5)
    hybrid_07 = create_hybrid(cited_emb, outcome_emb, 0.7)
    regeste_full_05 = create_hybrid(regeste_emb, full_text_emb, 0.5)
    regeste_full_07 = create_hybrid(regeste_emb, full_text_emb, 0.7)
    
    logger.info(f"  cited_outcome_hybrid_0.5: {hybrid_05.shape}")
    logger.info(f"  cited_outcome_hybrid_0.7: {hybrid_07.shape}")
    logger.info(f"  regeste_full_hybrid_0.5: {regeste_full_05.shape}")
    logger.info(f"  regeste_full_hybrid_0.7: {regeste_full_07.shape}")
    
    save_embeddings(cited_emb, "cited_decisions_tfidf")
    save_embeddings(outcome_emb, "outcome_tfidf")
    save_embeddings(regeste_emb, "regeste_tfidf")
    save_embeddings(full_text_emb, "full_text_tfidf_light")
    save_embeddings(hybrid_05, "cited_decisions_tfidf_outcome_hybrid_0.5")
    save_embeddings(hybrid_07, "cited_decisions_tfidf_outcome_hybrid_0.7")
    save_embeddings(regeste_full_05, "regeste_full_text_hybrid_0.5")
    save_embeddings(regeste_full_07, "regeste_full_text_hybrid_0.7")
    
    metadata_ref = {
        "run_id": f"legal_tfidf_embeddings_174k_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 25,
        "n_decisions": len(metadata),
        "embedding_dim": EMBEDDING_DIM,
        "embeddings": {
            "cited_decisions_tfidf": "cited_decisions_tfidf.npy",
            "outcome_tfidf": "outcome_tfidf.npy",
            "regeste_tfidf": "regeste_tfidf.npy",
            "full_text_tfidf_light": "full_text_tfidf_light.npy",
            "cited_decisions_tfidf_outcome_hybrid_0.5": "cited_decisions_tfidf_outcome_hybrid_0.5.npy",
            "cited_decisions_tfidf_outcome_hybrid_0.7": "cited_decisions_tfidf_outcome_hybrid_0.7.npy",
            "regeste_full_text_hybrid_0.5": "regeste_full_text_hybrid_0.5.npy",
            "regeste_full_text_hybrid_0.7": "regeste_full_text_hybrid_0.7.npy",
        },
        "tfidf_params": {
            "cited_decisions": {"max_features": CITED_MAX_FEATURES, "ngram_range": CITED_NGRAM_RANGE, "min_df": CITED_MIN_DF, "max_df": CITED_MAX_DF},
            "outcome": {"max_features": OUTCOME_MAX_FEATURES, "ngram_range": OUTCOME_NGRAM_RANGE, "min_df": OUTCOME_MIN_DF, "max_df": OUTCOME_MAX_DF},
            "regeste": {"max_features": REGESTE_MAX_FEATURES, "ngram_range": REGESTE_NGRAM_RANGE, "min_df": REGESTE_MIN_DF, "max_df": REGESTE_MAX_DF},
            "full_text_light": {"max_features": FULL_TEXT_MAX_FEATURES, "ngram_range": FULL_TEXT_NGRAM_RANGE, "min_df": FULL_TEXT_MIN_DF, "max_df": FULL_TEXT_MAX_DF},
        },
        "field_coverage": {
            "cited_decisions": non_empty_cited / len(cited_texts),
            "outcome": non_empty_outcome / len(outcome_texts),
            "regeste": non_empty_regeste / len(regeste_texts),
            "full_text": non_empty_full / len(full_texts_truncated),
        },
        "corpus_note": "175,440 decisions from bger_*.jsonl files. Legal signals: cited_decisions, outcome, regeste (case summary). Full-text truncated to 5k chars for speed.",
    }
    
    with open(OUTPUT_DIR / "embeddings_metadata.json", 'w') as f:
        json.dump(metadata_ref, f, indent=2)
    
    logger.info("\n=== 174k Legal TF-IDF embeddings complete ===")


if __name__ == "__main__":
    main()