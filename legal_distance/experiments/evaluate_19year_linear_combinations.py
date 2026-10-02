#!/usr/bin/env python3
"""
Evaluate linear combinations (linear_citation_concat, linear_hybrid05_concat) 
at 19-year scale (2000-2018, 122k decisions).
"""

import json
import numpy as np
from pathlib import Path
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
import logging
import sys
import time
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
CHECKPOINT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/checkpoints")
TFIDF_EMBEDDINGS_DIR = Path("/tmp/lex_accepted/evaluation/evaluation/results/174k/embeddings")
TFIDF_METADATA_PATH = Path("/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/linear_combinations_19year")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Evaluation imports
sys.path.insert(0, "/home/runner/work/LexMachina/LexMachina")
from legal_distance.experiments.evaluate_174k_dense_19year_center_projected import evaluate_embeddings as run_full_evaluation


def load_19year_checkpoints():
    """Load all 19-year (2000-2018) checkpoint embeddings and metadata."""
    logger.info("Loading 19-year checkpoint embeddings (2000-2018)...")
    
    all_embeddings = []
    all_metadata = []
    year_indices = {}
    current_idx = 0
    
    for year in range(2000, 2019):
        emb_path = CHECKPOINT_DIR / f"embeddings_{year}.npy"
        meta_path = CHECKPOINT_DIR / f"metadata_{year}.json"
        
        if emb_path.exists() and meta_path.exists():
            embeddings = np.load(emb_path)
            with open(meta_path, 'r') as f:
                metadata = json.load(f)
            
            all_embeddings.append(embeddings)
            all_metadata.extend(metadata)
            year_indices[str(year)] = (current_idx, current_idx + len(embeddings))
            current_idx += len(embeddings)
            logger.info(f"  Loaded {year}: {embeddings.shape}")
        else:
            logger.warning(f"  Missing checkpoint for {year}")
    
    all_embeddings = np.vstack(all_embeddings)
    logger.info(f"Total 19-year embeddings: {all_embeddings.shape}")
    logger.info(f"Total 19-year metadata: {len(all_metadata)}")
    
    return all_embeddings, all_metadata, year_indices


def compute_center_projected_64(embeddings, metadata):
    """Compute center_projected 64-dim from 768-dim embeddings."""
    logger.info("Computing center_projected (subtract language centers)...")
    
    languages = sorted(set(m.get('language', 'unknown') for m in metadata))
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
    
    logger.info(f"Center projected 768 shape: {debiased.shape}")
    
    # Create 64-dim PCA version
    logger.info("Creating center_projected 64dim via PCA...")
    pca_64 = PCA(n_components=64, random_state=42)
    center_projected_64 = pca_64.fit_transform(debiased)
    center_projected_64 = normalize(center_projected_64, norm='l2', axis=1)
    logger.info(f"  Explained variance ratio (64 components): {pca_64.explained_variance_ratio_.sum():.4f}")
    
    return center_projected_64, debiased


def load_tfidf_embeddings_and_metadata(embedding_name):
    """Load TF-IDF embeddings and metadata."""
    emb_path = TFIDF_EMBEDDINGS_DIR / f"{embedding_name}.npy"
    embeddings = np.load(emb_path)
    
    metadata = []
    with open(TFIDF_METADATA_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                metadata.append(json.loads(line))
    
    logger.info(f"Loaded TF-IDF {embedding_name}: {embeddings.shape}, metadata: {len(metadata)}")
    return embeddings, metadata


def match_19year_to_tfidf(year_metadata, tfidf_metadata, tfidf_embeddings):
    """Match 19-year decisions to TF-IDF embeddings by decision_id."""
    logger.info("Matching 19-year decisions to TF-IDF embeddings...")
    
    # Build TF-IDF decision_id -> index mapping
    tfidf_id_to_idx = {m['decision_id']: i for i, m in enumerate(tfidf_metadata)}
    
    # Find indices for 19-year decisions
    matched_indices = []
    matched_meta = []
    missing = 0
    
    for m in year_metadata:
        did = m['decision_id']
        if did in tfidf_id_to_idx:
            matched_indices.append(tfidf_id_to_idx[did])
            matched_meta.append(m)
        else:
            missing += 1
    
    logger.info(f"Matched: {len(matched_indices)}, Missing: {missing}")
    
    if matched_indices:
        matched_embeddings = tfidf_embeddings[matched_indices]
        return matched_embeddings, matched_meta
    return None, None


def evaluate_representation(name, embeddings, metadata, output_dir):
    """Run full evaluation on a representation."""
    logger.info(f"Running full evaluation for {name}...")
    start = time.time()
    
    results = run_full_evaluation(name, embeddings, metadata)
    results['duration_seconds'] = time.time() - start
    results['embedding_shape'] = list(embeddings.shape)
    
    # Save results
    output_path = output_dir / f"{name}_eval_latest.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved evaluation to {output_path}")
    
    return results


def main():
    logger.info("=" * 70)
    logger.info("19-YEAR LINEAR COMBINATIONS EVALUATION (2000-2018, 122k decisions)")
    logger.info("=" * 70)
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # 1. Load 19-year dense embeddings (768-dim from checkpoints)
    dense_19year, meta_19year, year_indices = load_19year_checkpoints()
    
    # 2. Compute center_projected_64
    center_projected_64, center_projected_768 = compute_center_projected_64(dense_19year, meta_19year)
    
    # 3. Load TF-IDF embeddings (cited_decisions_tfidf and hybrid_0.5)
    tfidf_cited, tfidf_meta = load_tfidf_embeddings_and_metadata("cited_decisions_tfidf")
    tfidf_hybrid_05, _ = load_tfidf_embeddings_and_metadata("cited_decisions_tfidf_outcome_hybrid_0.5")
    
    # 4. Match 19-year decisions to TF-IDF
    cited_19year, cited_meta = match_19year_to_tfidf(meta_19year, tfidf_meta, tfidf_cited)
    hybrid_19year, hybrid_meta = match_19year_to_tfidf(meta_19year, tfidf_meta, tfidf_hybrid_05)
    
    if cited_19year is None or hybrid_19year is None:
        logger.error("Failed to match 19-year decisions to TF-IDF embeddings")
        return
    
    logger.info(f"Matched cited_decisions_tfidf: {cited_19year.shape}")
    logger.info(f"Matched hybrid_0.5: {hybrid_19year.shape}")
    
    # 5. Create linear combinations
    # linear_citation_concat = center_projected_64 (64) + cited_decisions_tfidf (128) = 192
    linear_citation_concat = np.hstack([center_projected_64, cited_19year])
    logger.info(f"linear_citation_concat shape: {linear_citation_concat.shape}")
    
    # linear_hybrid05_concat = center_projected_64 (64) + cited_decisions_tfidf_outcome_hybrid_0.5 (128) = 192
    linear_hybrid05_concat = np.hstack([center_projected_64, hybrid_19year])
    logger.info(f"linear_hybrid05_concat shape: {linear_hybrid05_concat.shape}")
    
    # 6. Evaluate each representation
    results = {}
    
    # Evaluate center_projected_64 as baseline
    logger.info("\n" + "="*50)
    logger.info("Evaluating center_projected_64 (baseline)...")
    results['center_projected_64_19year'] = evaluate_representation(
        'center_projected_64_19year', center_projected_64, meta_19year, OUTPUT_DIR
    )
    
    # Evaluate cited_decisions_tfidf (TF-IDF baseline at 19-year)
    logger.info("\n" + "="*50)
    logger.info("Evaluating cited_decisions_tfidf (TF-IDF baseline)...")
    results['cited_decisions_tfidf_19year'] = evaluate_representation(
        'cited_decisions_tfidf_19year', cited_19year, cited_meta, OUTPUT_DIR
    )
    
    # Evaluate linear_citation_concat
    logger.info("\n" + "="*50)
    logger.info("Evaluating linear_citation_concat...")
    results['linear_citation_concat_19year'] = evaluate_representation(
        'linear_citation_concat_19year', linear_citation_concat, meta_19year, OUTPUT_DIR
    )
    
    # Evaluate linear_hybrid05_concat
    logger.info("\n" + "="*50)
    logger.info("Evaluating linear_hybrid05_concat...")
    results['linear_hybrid05_concat_19year'] = evaluate_representation(
        'linear_hybrid05_concat_19year', linear_hybrid05_concat, meta_19year, OUTPUT_DIR
    )
    
    # 7. Save combined results
    combined = {
        'run_id': f"linear_combinations_19year_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'direction_version': 29,
        'n_decisions': len(meta_19year),
        'year_range': '2000-2018',
        'representations': {
            'center_projected_64': {'dim': 64},
            'cited_decisions_tfidf': {'dim': 128},
            'linear_citation_concat': {'dim': 192, 'components': ['center_projected_64', 'cited_decisions_tfidf']},
            'linear_hybrid05_concat': {'dim': 192, 'components': ['center_projected_64', 'cited_decisions_tfidf_outcome_hybrid_0.5']},
        },
        'results': results,
        'year_indices': year_indices,
    }
    
    combined_path = OUTPUT_DIR / "linear_combinations_19year_eval_latest.json"
    with open(combined_path, 'w') as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    logger.info(f"\nSaved combined results to {combined_path}")
    
    # Print summary
    logger.info("\n" + "="*70)
    logger.info("SUMMARY: Adversarial Gates (LangDom < 0.85, JP > 0.5)")
    logger.info("="*70)
    for name, result in results.items():
        adv = result.get('adversarial', {})
        ld = adv.get('adversarial_language_dominance', {})
        jp = adv.get('jurist_pairwise_preference', {})
        ld_status = ld.get('status', 'N/A')
        jp_status = jp.get('status', 'N/A')
        ld_score = ld.get('mean_language_dominance', 'N/A')
        jp_score = jp.get('jurist_preference_rate', 'N/A')
        both = adv.get('both_pass', False)
        logger.info(f"  {name}:")
        logger.info(f"    LangDom: {ld_score:.4f} ({ld_status})")
        logger.info(f"    JuristPref: {jp_score:.4f} ({jp_status})")
        logger.info(f"    BOTH PASS: {both}")
    
    logger.info("=" * 70)
    logger.info("19-YEAR LINEAR COMBINATIONS EVALUATION COMPLETE")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()