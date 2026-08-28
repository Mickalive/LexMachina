#!/usr/bin/env python3
"""
Persist Signal Ablation Embeddings for Evaluation Adversarial Validation

Factory Direction v6 / Evaluation v3 requirement:
- Signal ablation embeddings must be persisted as .npy files
- So evaluation can run adversarial benchmarks (language dominance, jurist pairwise, etc.)

This script computes and saves embeddings for the top-performing signal ablation experiments
from v4 (center_projected baseline) and v5 (scale test) runs.
"""

import json
import numpy as np
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
FULL_CORPUS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/bger_full_corpus.jsonl")
CENTER_PROJECTED_PATH = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/signal_ablation_embeddings")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Signal extraction functions (reproduce from legal_signal_extraction.py)
def load_corpus() -> List[Dict]:
    corpus = []
    with open(FULL_CORPUS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            corpus.append(json.loads(line))
    logger.info(f"Loaded {len(corpus)} decisions from full corpus")
    return corpus

def extract_sachverhalt(text: str, language: str) -> str:
    """Extract Sachverhalt (facts) section."""
    if not text:
        return ""
    patterns = {
        'de': [r'Sachverhalt\s*:', r'Sachverhalt\s*\n'],
        'fr': [r'Faits\s*:', r'Faits\s*\n', r'En\s+fait\s*:'],
        'it': [r'Fatti\s*:', r'Fatti\s*\n', r'In\s+fatto\s*:'],
    }
    for pattern in patterns.get(language, patterns['de']):
        match = __import__('re').search(pattern, text, __import__('re').IGNORECASE)
        if match:
            start = match.end()
            end_patterns = [
                r'\n\s*(?:Erwägungen|Considérant|Considerando)\s*:',
                r'\n\s*(?:Dispositiv|Dispositif|Dispositivo)\s*:',
            ]
            end = len(text)
            for ep in end_patterns:
                m = __import__('re').search(ep, text[start:], __import__('re').IGNORECASE)
                if m:
                    end = min(end, start + m.start())
            return text[start:end].strip()
    return ""

def extract_erwaegungen(text: str, language: str) -> str:
    """Extract Erwägungen (reasoning) section."""
    if not text:
        return ""
    patterns = {
        'de': [r'Erwägungen\s*:', r'In\s+Erwägung\s*:'],
        'fr': [r'Considérant\s+en\s+droit\s*:', r'Considérant\s*:'],
        'it': [r'Considerando\s+in\s+diritto\s*:', r'Considerando\s*:'],
    }
    for pattern in patterns.get(language, patterns['de']):
        match = __import__('re').search(pattern, text, __import__('re').IGNORECASE)
        if match:
            start = match.end()
            end_patterns = [
                r'\n\s*(?:Dispositiv|Erkenntnis|Ausgang|Dispositif|Dispositivo)\s*:',
            ]
            end = len(text)
            for ep in end_patterns:
                m = __import__('re').search(ep, text[start:], __import__('re').IGNORECASE)
                if m:
                    end = min(end, start + m.start())
            return text[start:end].strip()
    return ""

def extract_headings(text: str, language: str) -> str:
    """Extract section headings."""
    if not text:
        return ""
    headings = __import__('re').findall(r'(?m)^\s*\d+(?:\.\d+)*\.\s+(.+)$', text)
    return " ".join(headings)

def extract_legal_area(text: str, language: str) -> str:
    """Extract legal area from metadata - not from text."""
    return ""  # This comes from metadata

def extract_norm_refs(text: str, language: str) -> str:
    """Extract statute/norm references."""
    if not text:
        return ""
    patterns = [
        r'\b(?:Art|Art\.)\s*\d+[a-z]?(?:\s+[A-Z][a-z]+)?(?:\s+[A-Z][a-z]+)?\b',
        r'\b(?:BGE|ATF)\s+\d+\s+[IVX]+\s+\d+\b',
        r'\b(?:ZGB|OR|StGB|StPO|ZPO|VG|BVG|BV|VwVG|VwGO|SG|SGB)\b',
    ]
    refs = []
    for pattern in patterns:
        refs.extend(__import__('re').findall(pattern, text, __import__('re').IGNORECASE))
    return " ".join(refs)

def extract_cited_decisions(text: str) -> str:
    """Extract cited decision references."""
    if not text:
        return ""
    patterns = [
        r'(?:BGE|ATF)\s+\d+\s+[IVX]+\s+\d+(?:\s+consid\.\s*\d+)?(?:\s+E\.\s*\d+)?',
    ]
    refs = []
    for pattern in patterns:
        refs.extend(__import__('re').findall(pattern, text, __import__('re').IGNORECASE))
    return " ".join(refs)

def extract_outcome(text: str, language: str) -> str:
    """Extract outcome/disposition."""
    if not text:
        return ""
    patterns = {
        'de': [r'Dispositiv\s*:', r'Erkenntnis\s*:'],
        'fr': [r'Dispositif\s*:'],
        'it': [r'Dispositivo\s*:'],
    }
    for pattern in patterns.get(language, patterns['de']):
        match = __import__('re').search(pattern, text, __import__('re').IGNORECASE)
        if match:
            return text[match.end():match.end()+500].strip()
    return ""

def extract_legal_issues(text: str, language: str) -> str:
    """Extract legal issues from headings and early reasoning."""
    if not text:
        return ""
    headings = extract_headings(text, language)
    erwaeg = extract_erwaegungen(text, language)
    return headings + " " + erwaeg[:1000]

def compute_tfidf_embeddings(texts: List[str], n_components: int = 128) -> np.ndarray:
    """Compute TF-IDF + SVD embeddings."""
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(texts)
    
    n_comp = min(n_components, tfidf_matrix.shape[1] - 1, tfidf_matrix.shape[0] - 1)
    if n_comp <= 0:
        n_comp = 1
    
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    embeddings = svd.fit_transform(tfidf_matrix)
    embeddings = normalize(embeddings, norm='l2')
    return embeddings

def compute_hybrid_embeddings(
    center_projected: np.ndarray,
    legal_embeddings: np.ndarray,
    alpha: float
) -> np.ndarray:
    """Compute hybrid: alpha * legal + (1-alpha) * center_projected"""
    # Ensure same dimensionality
    if center_projected.shape[1] != legal_embeddings.shape[1]:
        # Project legal to center_projected dim or vice versa
        from sklearn.decomposition import TruncatedSVD
        if legal_embeddings.shape[1] > center_projected.shape[1]:
            svd = TruncatedSVD(n_components=center_projected.shape[1], random_state=42)
            legal_embeddings = svd.fit_transform(legal_embeddings)
        else:
            svd = TruncatedSVD(n_components=legal_embeddings.shape[1], random_state=42)
            center_projected = svd.fit_transform(center_projected)
    
    hybrid = alpha * legal_embeddings + (1 - alpha) * center_projected
    hybrid = normalize(hybrid, norm='l2')
    return hybrid

def main():
    logger.info("=" * 70)
    logger.info("Persist Signal Ablation Embeddings for Evaluation")
    logger.info("=" * 70)
    
    # Load corpus
    logger.info("\n1. Loading corpus...")
    corpus = load_corpus()
    corpus_by_id = {d['decision_id']: d for d in corpus}
    
    # Load metadata for alignment
    sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
    from hierarchical_leiden import load_metadata_with_branch
    _, metadata = load_metadata_with_branch()
    
    # Align corpus with metadata
    aligned_corpus = [corpus_by_id[m['decision_id']] for m in metadata if m['decision_id'] in corpus_by_id]
    logger.info(f"Aligned corpus: {len(aligned_corpus)} decisions")
    
    # Load center_projected baseline
    logger.info("\n2. Loading center_projected baseline...")
    center_projected = np.load(CENTER_PROJECTED_PATH)
    # Align center_projected with metadata
    center_metadata_path = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")
    with open(center_metadata_path) as f:
        center_metadata = json.load(f)
    center_by_id = {m['decision_id']: i for i, m in enumerate(center_metadata)}
    center_projected_aligned = np.array([
        center_projected[center_by_id[m['decision_id']]] 
        for m in metadata if m['decision_id'] in center_by_id
    ])
    logger.info(f"Center projected aligned: {center_projected_aligned.shape}")
    
    # Extract signals for all decisions
    logger.info("\n3. Extracting legal signals...")
    signals = {}
    for d in aligned_corpus:
        did = d['decision_id']
        lang = d.get('language', 'de')
        full_text = d.get('full_text', '')
        
        signals[did] = {
            'sachverhalt': extract_sachverhalt(full_text, lang),
            'erwaegungen': extract_erwaegungen(full_text, lang),
            'headings': extract_headings(full_text, lang),
            'norm_refs': extract_norm_refs(full_text, lang),
            'cited_decisions': extract_cited_decisions(full_text),
            'outcome': extract_outcome(full_text, lang),
            'legal_issues': extract_legal_issues(full_text, lang),
            'legal_area': d.get('legal_area', ''),
        }
    
    # Prepare text arrays in metadata order
    metadata_ids = [m['decision_id'] for m in metadata if m['decision_id'] in signals]
    
    signal_texts = {
        'sachverhalt': [signals[did]['sachverhalt'] for did in metadata_ids],
        'erwaegungen': [signals[did]['erwaegungen'] for did in metadata_ids],
        'headings': [signals[did]['headings'] for did in metadata_ids],
        'norm_refs': [signals[did]['norm_refs'] for did in metadata_ids],
        'cited_decisions': [signals[did]['cited_decisions'] for did in metadata_ids],
        'outcome': [signals[did]['outcome'] for did in metadata_ids],
        'legal_issues': [signals[did]['legal_issues'] for did in metadata_ids],
        'legal_area': [signals[did]['legal_area'] for did in metadata_ids],
    }
    
    # Compute TF-IDF embeddings for each signal
    logger.info("\n4. Computing TF-IDF embeddings for each signal...")
    signal_embeddings = {}
    for name, texts in signal_texts.items():
        logger.info(f"  Computing {name}...")
        # Filter out empty texts
        non_empty = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
        if len(non_empty) < 2:
            logger.warning(f"  {name}: too few non-empty texts ({len(non_empty)}), skipping")
            signal_embeddings[name] = np.zeros((len(texts), 128))
            continue
        
        indices, non_empty_texts = zip(*non_empty)
        emb = compute_tfidf_embeddings(list(non_empty_texts), n_components=128)
        
        # Map back to full array
        full_emb = np.zeros((len(texts), 128))
        for idx, emb_idx in enumerate(indices):
            full_emb[emb_idx] = emb[idx]
        signal_embeddings[name] = full_emb
        logger.info(f"  {name}: {full_emb.shape}")
    
    # Save individual signal embeddings
    logger.info("\n5. Saving individual signal embeddings...")
    for name, emb in signal_embeddings.items():
        np.save(OUTPUT_DIR / f"signal_{name}.npy", emb)
        logger.info(f"  Saved signal_{name}.npy: {emb.shape}")
    
    # Compute and save key combinations from v4/v5 results
    logger.info("\n6. Computing and saving key combinations...")
    
    # Key combinations from v4 signal ablation results (top performers)
    combinations = {
        # Single signals
        'sachverhalt_tfidf': signal_embeddings['sachverhalt'],
        'erwaegungen_tfidf': signal_embeddings['erwaegungen'],
        'headings_tfidf': signal_embeddings['headings'],
        'norm_embeddings': signal_embeddings['norm_refs'],
        'cited_decisions_tfidf': signal_embeddings['cited_decisions'],
        'outcome_tfidf': signal_embeddings['outcome'],
        'legal_area_tfidf': signal_embeddings['legal_area'],
        'legal_issues_tfidf': signal_embeddings['legal_issues'],
        
        # Core combinations
        'erwaegungen+citations': None,  # Will compute
        'sachverhalt+erwaegungen': None,
        'sachverhalt+norms': None,
        'erwaegungen+norms': None,
        'erwaegungen+doctrine': None,  # erwaegungen + headings
        
        # Legal issues + outcomes (top NMI in scale test)
        'legal_issues_outcomes': None,
    }
    
    # Compute combinations
    combinations['erwaegungen+citations'] = normalize(
        signal_embeddings['erwaegungen'] + signal_embeddings['cited_decisions'], norm='l2'
    )
    combinations['sachverhalt+erwaegungen'] = normalize(
        signal_embeddings['sachverhalt'] + signal_embeddings['erwaegungen'], norm='l2'
    )
    combinations['sachverhalt+norms'] = normalize(
        signal_embeddings['sachverhalt'] + signal_embeddings['norm_refs'], norm='l2'
    )
    combinations['erwaegungen+norms'] = normalize(
        signal_embeddings['erwaegungen'] + signal_embeddings['norm_refs'], norm='l2'
    )
    combinations['erwaegungen+doctrine'] = normalize(
        signal_embeddings['erwaegungen'] + signal_embeddings['headings'], norm='l2'
    )
    combinations['legal_issues_outcomes'] = normalize(
        signal_embeddings['legal_issues'] + signal_embeddings['outcome'] + signal_embeddings['headings'], norm='l2'
    )
    
    for name, emb in combinations.items():
        np.save(OUTPUT_DIR / f"signal_{name}.npy", emb)
        logger.info(f"  Saved signal_{name}.npy: {emb.shape}")
    
    # Hybrids with center_projected (key alphas: 0.3, 0.5, 0.7)
    logger.info("\n7. Computing and saving hybrids with center_projected...")
    alphas = [0.3, 0.5, 0.7]
    key_signals = ['erwaegungen', 'sachverhalt', 'norm_refs', 'legal_area', 'cited_decisions']
    
    for signal_name in key_signals:
        legal_emb = signal_embeddings[signal_name]
        # Project legal to 768 dim to match center_projected using random projection
        from sklearn.random_projection import GaussianRandomProjection
        rp = GaussianRandomProjection(n_components=768, random_state=42)
        legal_emb_768 = rp.fit_transform(legal_emb)
        legal_emb_768 = normalize(legal_emb_768, norm='l2')
        
        for alpha in alphas:
            hybrid = alpha * legal_emb_768 + (1 - alpha) * center_projected_aligned
            hybrid = normalize(hybrid, norm='l2')
            np.save(OUTPUT_DIR / f"hybrid_{signal_name}_{alpha:.1f}.npy", hybrid)
            logger.info(f"  Saved hybrid_{signal_name}_{alpha:.1f}.npy: {hybrid.shape}")
    
    # Also save center_projected baseline for reference
    np.save(OUTPUT_DIR / "baseline_center_projected.npy", center_projected_aligned)
    logger.info(f"  Saved baseline_center_projected.npy: {center_projected_aligned.shape}")
    
    # Save metadata alignment
    with open(OUTPUT_DIR / "metadata_alignment.json", 'w') as f:
        json.dump({
            'n_decisions': len(metadata_ids),
            'decision_ids': metadata_ids,
            'corpus_source': 'bger_full_corpus.jsonl (1200 decisions, aligned to 1000 metadata)',
        }, f, indent=2)
    
    logger.info("\n" + "=" * 70)
    logger.info("SIGNAL ABLATION EMBEDDINGS PERSISTED")
    logger.info("=" * 70)
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Files created: {len(list(OUTPUT_DIR.glob('*.npy')))}")
    logger.info("\nEvaluation lane can now load these embeddings for adversarial validation.")
    
    return OUTPUT_DIR

if __name__ == "__main__":
    main()