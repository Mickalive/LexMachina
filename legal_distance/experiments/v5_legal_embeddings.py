#!/usr/bin/env python3
"""
Legal Distance Lane v5 - Legal Embeddings Test for Multilingual Invariance

Tests multilingual legal embedding models:
1. ZurichNLP/swissbert (Swiss-specific multilingual)
2. intfloat/multilingual-e5-small (multilingual sentence embeddings)
3. xlm-roberta-base (multilingual RoBERTa)
4. sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (baseline from v4)

Evaluates on full corpus using fractal-map harness and cross-language benchmarks.
"""

import json
import numpy as np
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

import sys
sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation')

from hierarchical_leiden import (
    load_metadata_with_branch, load_representations, 
    load_corpus_decisions, leiden_clustering,
    compute_branch_purity,
)
from hierarchical_zoom_validation import hierarchical_leiden, compute_branch_purity_per_cluster

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

FULL_CORPUS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/legal_embeddings")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Legal embedding models to test
EMBEDDING_MODELS = {
    "swissbert": "ZurichNLP/swissbert",
    "multilingual_e5_small": "intfloat/multilingual-e5-small",
    "xlm_roberta_base": "xlm-roberta-base",
    "paraphrase_multilingual_minilm": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # v4 baseline
}

def load_full_corpus() -> List[Dict]:
    corpus = []
    with open(FULL_CORPUS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            corpus.append(json.loads(line))
    logger.info(f"Loaded {len(corpus)} decisions from full corpus")
    return corpus

def get_embeddings(model_name: str, model_id: str, corpus: List[Dict], text_field: str = 'full_text') -> np.ndarray:
    """Get embeddings from a transformer model."""
    logger.info(f"Loading model: {model_id}")
    
    if 'sentence-transformers' in model_id:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_id)
        texts = [d.get(text_field, '') for d in corpus]
        # Truncate long texts
        texts = [t[:8192] for t in texts]
        embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    else:
        from transformers import AutoTokenizer, AutoModel
        import torch
        
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModel.from_pretrained(model_id)
        model.eval()
        
        texts = [d.get(text_field, '') for d in corpus]
        embeddings_list = []
        
        with torch.no_grad():
            for i, text in enumerate(texts):
                if i % 100 == 0:
                    logger.info(f"  Embedding {i}/{len(texts)}...")
                # Truncate
                inputs = tokenizer(text[:512], return_tensors='pt', truncation=True, max_length=512, padding=True)
                outputs = model(**inputs)
                # Mean pooling
                last_hidden = outputs.last_hidden_state
                attention_mask = inputs['attention_mask']
                masked = last_hidden * attention_mask.unsqueeze(-1)
                summed = masked.sum(dim=1)
                counts = attention_mask.sum(dim=1, keepdim=True).clamp(min=1)
                pooled = summed / counts
                embeddings_list.append(pooled.squeeze().numpy())
        
        embeddings = np.array(embeddings_list)
    
    # Normalize
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms
    
    logger.info(f"  Embeddings shape: {embeddings.shape}")
    return embeddings

def evaluate_with_fractal_harness(
    embeddings: np.ndarray,
    metadata: List[Dict],
    config_name: str,
    coarse_res: float = 0.5,
    sub_res: float = 3.0
) -> Dict[str, Any]:
    logger.info(f"\n=== Evaluating {config_name} with Fractal-Map Harness ===")
    
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden(
        embeddings, metadata, coarse_res=coarse_res, sub_res=sub_res
    )
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    
    coarse_purities = compute_branch_purity_per_cluster(coarse_labels, metadata)
    coarse_overall = compute_branch_purity(coarse_labels, metadata)
    
    fine_purities = compute_branch_purity_per_cluster(hierarchical_labels, metadata)
    fine_overall = compute_branch_purity(hierarchical_labels, metadata)
    
    total_improvements = 0
    total_deteriorations = 0
    total_no_change = 0
    zoom_results = {}
    
    for coarse_id in sorted(coarse_to_fine.keys()):
        fine_ids = coarse_to_fine[coarse_id]
        if not fine_ids:
            continue
        
        coarse_pur = coarse_purities.get(coarse_id, 0)
        fine_purs = [fine_purities.get(fid, 0) for fid in fine_ids]
        fine_mean = np.mean(fine_purs) if fine_purs else 0
        improvement = fine_mean - coarse_pur
        
        improvements = sum(1 for fp in fine_purs if fp > coarse_pur + 0.01)
        deteriorations = sum(1 for fp in fine_purs if fp < coarse_pur - 0.01)
        no_change = len(fine_purs) - improvements - deteriorations
        
        total_improvements += improvements
        total_deteriorations += deteriorations
        total_no_change += no_change
        
        coarse_mask = coarse_labels == coarse_id
        coarse_branches = [metadata[i].get('branch') for i in np.where(coarse_mask)[0]]
        coarse_branches = [b for b in coarse_branches if b and b != 'null']
        coarse_dom = Counter(coarse_branches).most_common(1)[0][0] if coarse_branches else "unknown"
        
        zoom_results[int(coarse_id)] = {
            'coarse_size': int(np.sum(coarse_mask)),
            'coarse_purity': float(coarse_pur),
            'coarse_dominant_branch': coarse_dom,
            'n_fine_clusters': len(fine_ids),
            'fine_purity_mean': float(fine_mean),
            'fine_purity_values': [float(p) for p in fine_purs],
            'improvement': float(improvement),
            'improvement_pct': float(improvement / coarse_pur * 100) if coarse_pur > 0 else 0,
            'improvements': improvements,
            'deteriorations': deteriorations,
            'no_change': no_change,
        }
    
    overall_improvement = fine_overall - coarse_overall
    total_fine = total_improvements + total_deteriorations + total_no_change
    improvement_rate = total_improvements / total_fine if total_fine > 0 else 0
    
    from sklearn.metrics import normalized_mutual_info_score
    legal_areas = [metadata[i].get('legal_area', '') for i in range(len(metadata))]
    legal_areas = [la if la else 'unknown' for la in legal_areas]
    nmi = normalized_mutual_info_score(legal_areas, hierarchical_labels)
    
    flat_labels, _ = leiden_clustering(embeddings, resolution=sub_res)
    flat_purity = compute_branch_purity(flat_labels, metadata)
    
    logger.info(f"  Coarse clusters: {n_coarse}, Fine clusters: {n_fine}")
    logger.info(f"  Coarse purity: {coarse_overall:.4f}, Fine purity: {fine_overall:.4f}")
    logger.info(f"  Overall improvement: {overall_improvement:+.4f} ({overall_improvement/coarse_overall*100:+.1f}%)")
    logger.info(f"  Improvement rate: {improvement_rate:.1%} ({total_improvements}/{total_fine})")
    logger.info(f"  Legal area NMI: {nmi:.4f}")
    logger.info(f"  Flat Leiden (res={sub_res}) purity: {flat_purity:.4f}, Hierarchical advantage: {fine_overall - flat_purity:+.4f}")
    
    verdict = "PASS" if improvement_rate > 0.5 and overall_improvement > 0 else "PARTIAL" if improvement_rate > 0.3 else "FAIL"
    logger.info(f"  VERDICT: {verdict}")
    
    return {
        'config_name': config_name,
        'model_id': EMBEDDING_MODELS.get(config_name, 'unknown'),
        'n_coarse_clusters': n_coarse,
        'n_fine_clusters': n_fine,
        'coarse_purity': float(coarse_overall),
        'fine_purity': float(fine_overall),
        'overall_improvement': float(overall_improvement),
        'improvement_pct': float(overall_improvement / coarse_overall * 100) if coarse_overall > 0 else 0,
        'total_improvements': int(total_improvements),
        'total_deteriorations': int(total_deteriorations),
        'total_no_change': int(total_no_change),
        'improvement_rate': float(improvement_rate),
        'legal_area_nmi': float(nmi),
        'flat_purity': float(flat_purity),
        'hierarchical_advantage': float(fine_overall - flat_purity),
        'verdict': verdict,
        'embedding_shape': list(embeddings.shape),
        'zoom_results': zoom_results,
    }

def evaluate_cross_language(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Evaluate cross-language retrieval quality."""
    from sklearn.metrics.pairwise import cosine_similarity
    
    languages = [m.get('language', 'unknown') for m in metadata]
    branches = [m.get('branch', 'unknown') for m in metadata]
    
    # Compute similarity matrix
    sim = cosine_similarity(embeddings)
    
    # For each decision, find nearest neighbors and check cross-language same-branch retrieval
    cross_lang_same_branch = 0
    cross_lang_total = 0
    same_lang_same_branch = 0
    same_lang_total = 0
    
    for i in range(len(metadata)):
        lang_i = languages[i]
        branch_i = branches[i]
        if branch_i == 'unknown' or branch_i == 'null':
            continue
        
        # Get top-10 neighbors
        neighbors = np.argsort(sim[i])[::-1][1:11]  # Exclude self
        
        for j in neighbors:
            lang_j = languages[j]
            branch_j = branches[j]
            if branch_j == 'unknown' or branch_j == 'null':
                continue
            
            if lang_i != lang_j:
                cross_lang_total += 1
                if branch_i == branch_j:
                    cross_lang_same_branch += 1
            else:
                same_lang_total += 1
                if branch_i == branch_j:
                    same_lang_same_branch += 1
    
    cross_lang_rate = cross_lang_same_branch / cross_lang_total if cross_lang_total > 0 else 0
    same_lang_rate = same_lang_same_branch / same_lang_total if same_lang_total > 0 else 0
    invariance_gap = same_lang_rate - cross_lang_rate
    
    # Language dominance check (adversarial)
    # How much does language explain similarity vs legal content?
    lang_dominance = 0
    if cross_lang_total > 0 and same_lang_total > 0:
        # Compute average similarity for same-lang vs cross-lang pairs
        same_lang_sims = []
        cross_lang_sims = []
        for i in range(min(100, len(metadata))):  # Sample for efficiency
            for j in range(i+1, min(100, len(metadata))):
                if languages[i] == languages[j]:
                    same_lang_sims.append(sim[i, j])
                else:
                    cross_lang_sims.append(sim[i, j])
        
        if same_lang_sims and cross_lang_sims:
            lang_dominance = np.mean(same_lang_sims) / (np.mean(cross_lang_sims) + 1e-8)
    
    logger.info(f"  Cross-language same-branch rate: {cross_lang_rate:.4f}")
    logger.info(f"  Same-language same-branch rate: {same_lang_rate:.4f}")
    logger.info(f"  Invariance gap: {invariance_gap:.4f}")
    logger.info(f"  Language dominance ratio: {lang_dominance:.4f}")
    
    return {
        'cross_language_same_branch_rate': cross_lang_rate,
        'same_language_same_branch_rate': same_lang_rate,
        'invariance_gap': invariance_gap,
        'language_dominance_ratio': lang_dominance,
    }

def main():
    logger.info("=" * 70)
    logger.info("Legal Distance Lane v5 - Legal Embeddings Test")
    logger.info("=" * 70)
    
    # Load data
    logger.info("\n1. Loading full corpus...")
    corpus = load_full_corpus()
    
    logger.info("\n2. Loading metadata with branch...")
    _, metadata = load_metadata_with_branch()
    
    # Align corpus with metadata (by decision_id)
    corpus_by_id = {d['decision_id']: d for d in corpus}
    aligned_corpus = [corpus_by_id[m['decision_id']] for m in metadata if m['decision_id'] in corpus_by_id]
    logger.info(f"Aligned corpus: {len(aligned_corpus)} decisions")
    
    all_results = {}
    
    for model_key, model_id in EMBEDDING_MODELS.items():
        logger.info(f"\n{'='*70}")
        logger.info(f"TESTING MODEL: {model_key} ({model_id})")
        logger.info(f"{'='*70}")
        
        try:
            start = time.time()
            embeddings = get_embeddings(model_key, model_id, aligned_corpus, 'full_text')
            elapsed = time.time() - start
            logger.info(f"  Embedding time: {elapsed:.1f}s")
            
            # Fractal-map evaluation
            fractal_results = evaluate_with_fractal_harness(embeddings, metadata, model_key)
            
            # Cross-language evaluation
            cross_lang_results = evaluate_cross_language(embeddings, metadata)
            
            results = {
                'model_key': model_key,
                'model_id': model_id,
                'embedding_time_sec': elapsed,
                'fractal_map': fractal_results,
                'cross_language': cross_lang_results,
            }
            
            all_results[model_key] = results
            
            # Save intermediate
            with open(OUTPUT_DIR / f"embeddings_{model_key}_results.json", 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            # Save embeddings for later use
            np.save(OUTPUT_DIR / f"embeddings_{model_key}.npy", embeddings)
            
        except Exception as e:
            logger.error(f"  ERROR with {model_key}: {e}")
            all_results[model_key] = {'error': str(e)}
    
    # Save all results
    with open(OUTPUT_DIR / "legal_embeddings_all_results.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("LEGAL EMBEDDINGS SUMMARY")
    logger.info("=" * 80)
    logger.info(f"{'Model':<35} {'Coarse':>6} {'Fine':>6} {'Improv':>8} {'Rate':>7} {'NMI':>6} {'LangDom':>8} {'Verdict':>8}")
    logger.info("-" * 80)
    
    for model_key, res in all_results.items():
        if 'error' in res:
            logger.info(f"{model_key:<35} ERROR: {res['error']}")
            continue
        
        fm = res['fractal_map']
        cl = res['cross_language']
        
        coarse = fm.get('coarse_purity', 0)
        fine = fm.get('fine_purity', 0)
        improv = fm.get('overall_improvement', 0)
        rate = fm.get('improvement_rate', 0)
        nmi = fm.get('legal_area_nmi', 0)
        lang_dom = cl.get('language_dominance_ratio', 0)
        verdict = fm.get('verdict', 'N/A')
        
        logger.info(f"{model_key:<35} {coarse:.3f}  {fine:.3f}  {improv:+.3f}   {rate:.1%}  {nmi:.3f}  {lang_dom:.3f}  {verdict:>8}")
    
    logger.info("\n=== Legal Embeddings Test Complete ===")
    return all_results

if __name__ == "__main__":
    main()
