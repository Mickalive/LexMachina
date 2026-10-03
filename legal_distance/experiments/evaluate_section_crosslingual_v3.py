#!/usr/bin/env python3
"""
Section-specific cross-lingual evaluation (sachverhalt/erwaegungen/dispositiv) 
at available corpus density (1000-decision sample with section extractions).
"""

import json
import numpy as np
import logging
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter

from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina')

from run_174k_formal_suite import (
    run_cross_language_benchmarks,
    prepare_metadata,
    assign_branch,
    GLOBAL_SEED,
    K_NEIGHBORS_CROSS_LANG_FROZEN,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

SIGNALS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/legal_signals_1000_v3.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/174k_dense_embeddings/section_crosslingual_eval")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
BATCH_SIZE = 32

SECTIONS = {
    'sachverhalt': 'sachverhalt_text',
    'erwaegungen': 'erwaegungen_text',
    'dispositiv': 'dispositiv_text',
}


def load_signals():
    """Load legal signals with section extractions."""
    signals = []
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            signals.append(json.loads(line))
    logger.info(f"Loaded {len(signals)} decisions with section extractions")
    return signals


def load_full_metadata(signal_ids: List[str]) -> Dict[str, Dict]:
    """Load full metadata for signal decision IDs."""
    id_to_meta = {}
    with open('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.jsonl', 'r') as f:
        for line in f:
            m = json.loads(line)
            if m['decision_id'] in signal_ids:
                id_to_meta[m['decision_id']] = m
    logger.info(f"Loaded full metadata for {len(id_to_meta)}/{len(signal_ids)} signal decisions")
    return id_to_meta


def compute_embeddings(texts: List[str], model: SentenceTransformer) -> np.ndarray:
    """Compute embeddings for texts."""
    logger.info(f"  Computing embeddings for {len(texts)} texts...")
    start = time.time()
    embeddings = model.encode(texts, batch_size=BATCH_SIZE, show_progress_bar=True, convert_to_numpy=True)
    elapsed = time.time() - start
    logger.info(f"  Computed {embeddings.shape} in {elapsed:.1f}s ({len(texts)/elapsed:.1f} texts/s)")
    return embeddings


def language_center_projection(embeddings: np.ndarray, languages: List[str]) -> np.ndarray:
    """Project embeddings to remove language centers."""
    unique_langs = sorted(set(languages))
    centers = {}
    for lang in unique_langs:
        mask = np.array([l == lang for l in languages])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
    
    debiased = np.copy(embeddings)
    for i, lang in enumerate(languages):
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    # L2 normalize
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    debiased = debiased / norms
    
    return debiased


def evaluate_section(section_name: str, embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run cross-language benchmarks on section embeddings."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating section: {section_name} ({embeddings.shape[0]} decisions)")
    logger.info(f"{'='*60}")
    
    # Run cross-language benchmarks (uses exact k-NN on valid subset)
    results = run_cross_language_benchmarks(embeddings, metadata)
    
    return results


def main():
    logger.info("=" * 70)
    logger.info("SECTION-SPECIFIC CROSS-LINGUAL EVALUATION (v3: +dispositiv)")
    logger.info("=" * 70)
    
    # Load signals
    signals = load_signals()
    signal_ids = [s['decision_id'] for s in signals]
    
    # Load full metadata for branch/language info
    full_metadata = load_full_metadata(signal_ids)
    
    # Load model
    logger.info(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    logger.info("Model loaded")
    
    all_results = {}
    
    for section_name, section_key in SECTIONS.items():
        logger.info(f"\n{'='*70}")
        logger.info(f"PROCESSING SECTION: {section_name}")
        logger.info(f"{'='*70}")
        
        # Filter to decisions with this section AND full metadata
        filtered_signals = []
        texts = []
        languages = []
        for s in signals:
            text = s.get(section_key, '').strip()
            if text and s['decision_id'] in full_metadata:
                filtered_signals.append(s)
                texts.append(text)
                languages.append(s.get('language', 'de'))
        
        if len(filtered_signals) < 50:
            logger.warning(f"  Too few decisions ({len(filtered_signals)}), skipping")
            continue
        
        # Prepare metadata for evaluation using full metadata (has branch)
        metadata = []
        for s in filtered_signals:
            fm = full_metadata[s['decision_id']]
            metadata.append({
                'decision_id': s['decision_id'],
                'language': fm.get('language', s.get('language', 'de')),
                'branch': fm.get('branch', 'unknown'),
                'chamber': fm.get('chamber', ''),
                'legal_area': fm.get('legal_area', ''),
                'year': fm.get('year', 2024),
            })
        
        # Filter to only decisions with known branch for evaluation
        valid_metadata = [m for m in metadata if m['branch'] != 'unknown']
        valid_indices = [i for i, m in enumerate(metadata) if m['branch'] != 'unknown']
        valid_texts = [texts[i] for i in valid_indices]
        valid_languages = [languages[i] for i in valid_indices]
        
        logger.info(f"  Decisions with section: {len(filtered_signals)}")
        logger.info(f"  Decisions with known branch: {len(valid_metadata)}")
        
        if len(valid_metadata) < 50:
            logger.warning(f"  Too few decisions with known branch ({len(valid_metadata)}), skipping")
            continue
        
        # Compute embeddings
        embeddings = compute_embeddings(valid_texts, model)
        
        # Apply language center projection
        logger.info("  Applying language center projection...")
        embeddings_cp = language_center_projection(embeddings, valid_languages)
        
        # Apply PCA to 64 dim
        logger.info("  Applying PCA to 64 dimensions...")
        pca = PCA(n_components=64, random_state=GLOBAL_SEED)
        embeddings_64 = pca.fit_transform(embeddings_cp)
        embeddings_64 = normalize(embeddings_64, norm='l2', axis=1)
        logger.info(f"  Explained variance: {pca.explained_variance_ratio_.sum():.4f}")
        
        # Evaluate raw embeddings
        logger.info(f"\n  Evaluating raw 768-dim embeddings...")
        result_raw = evaluate_section(f"{section_name}_raw_768", embeddings, valid_metadata)
        
        # Evaluate center-projected 768-dim
        logger.info(f"\n  Evaluating center-projected 768-dim embeddings...")
        result_cp768 = evaluate_section(f"{section_name}_cp_768", embeddings_cp, valid_metadata)
        
        # Evaluate center-projected 64-dim
        logger.info(f"\n  Evaluating center-projected 64-dim embeddings...")
        result_cp64 = evaluate_section(f"{section_name}_cp_64", embeddings_64, valid_metadata)
        
        all_results[section_name] = {
            'raw_768': result_raw,
            'center_projected_768': result_cp768,
            'center_projected_64': result_cp64,
            'n_decisions': len(valid_metadata),
            'coverage': len(valid_metadata) / len(signals),
        }
        
        # Print summary
        logger.info(f"\n  SUMMARY for {section_name}:")
        for name, result in [('raw_768', result_raw), ('cp_768', result_cp768), ('cp_64', result_cp64)]:
            cl = result.get('cross_language', {})
            if cl:
                clnq = cl.get('cross_language_neighbor_quality', {})
                zsc = cl.get('zero_shot_cross_language_transfer', {})
                lsrq = cl.get('language_specific_representation_quality', {})
                logger.info(f"    {name}:")
                logger.info(f"      cross_lang_same_branch: {clnq.get('cross_lang_same_branch_mean', 'N/A'):.4f}")
                logger.info(f"      same_lang_same_branch: {clnq.get('same_lang_same_branch_mean', 'N/A'):.4f}")
                logger.info(f"      invariance_gap: {clnq.get('invariance_gap', 'N/A'):.4f}")
                logger.info(f"      zero_shot_mean_nmi: {zsc.get('zero_shot_mean_nmi', 'N/A'):.4f}")
                logger.info(f"      lang_specific_mean_nmi: {lsrq.get('mean_nmi', 'N/A'):.4f}")
    
    # Save results
    from datetime import datetime
    output_file = OUTPUT_DIR / f"section_crosslingual_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    latest_file = OUTPUT_DIR / "section_crosslingual_eval_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info(f"Latest: {latest_file}")
    
    # Final summary
    logger.info("\n" + "=" * 70)
    logger.info("FINAL SUMMARY - SECTION-SPECIFIC CROSS-LINGUAL EVALUATION (v3)")
    logger.info("=" * 70)
    
    for section_name, results in all_results.items():
        logger.info(f"\n{section_name} (n={results['n_decisions']}, coverage={results['coverage']:.1%}):")
        for variant, result in [('raw_768', results['raw_768']), ('cp_768', results['center_projected_768']), ('cp_64', results['center_projected_64'])]:
            cl = result.get('cross_language', {})
            if cl:
                clnq = cl.get('cross_language_neighbor_quality', {})
                zsc = cl.get('zero_shot_cross_language_transfer', {})
                lsrq = cl.get('language_specific_representation_quality', {})
                logger.info(f"  {variant}:")
                logger.info(f"    cross_lang_same_branch: {clnq.get('cross_lang_same_branch_mean', 'N/A'):.4f}")
                logger.info(f"    invariance_gap: {clnq.get('invariance_gap', 'N/A'):.4f}")
                logger.info(f"    zero_shot_nmi: {zsc.get('zero_shot_mean_nmi', 'N/A'):.4f}")
                logger.info(f"    lang_specific_nmi: {lsrq.get('mean_nmi', 'N/A'):.4f}")
    
    return all_results


if __name__ == "__main__":
    main()