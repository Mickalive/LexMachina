#!/usr/bin/env python3
"""
Debug script for comprehensive_validation JP anomaly.
Compares the ST-based center_projected vs v5 baseline center_projected.
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter
from sklearn.decomposition import TruncatedSVD, PCA
from sklearn.preprocessing import normalize
from sklearn.neighbors import NearestNeighbors

# Add paths
import sys
sys.path.insert(0, '/tmp/lex_accepted/evaluation/evaluation/tests')
from jurist_usability import prepare_metadata, simulate_pairwise_preference

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
EXPANDED_CORPUS_FILE = Path("/tmp/lex_accepted/evaluation/evaluation/data/bger_expanded_1200.jsonl")
EXPANDED_METADATA_FILE = Path("/tmp/lex_accepted/evaluation/evaluation/data/bger_expanded_1200_metadata.jsonl")
CACHED_ST_EMBEDDINGS_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/cached_embeddings/st_embeddings_1200_paraphrase-multilingual-MiniLM-L12-v2_erwaegungen_2000.npy")
V5_CENTER_PROJECTED_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy")
V5_CENTER_PROJECTED_META_FILE = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full/metadata.json")

CHAMBER_TO_BRANCH = {
    "I. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "II. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "III. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "IV. Öffentlich-rechtliche Abteilung": "oeffentliches_recht",
    "I. Zivilrechtliche Abteilung": "zivilrecht",
    "II. Zivilrechtliche Abteilung": "zivilrecht",
    "I. Strafrechtliche Abteilung": "strafrecht",
    "II. Strafrechtliche Abteilung": "strafrecht",
    "II. sozialrechtliche Abteilung": "sozialversicherungsrecht",
    "IIe Cour de droit social": "sozialversicherungsrecht",
    "Ire Cour de droit public": "oeffentliches_recht",
    "IIe Cour de droit public": "oeffentliches_recht",
    "Ire Cour de droit civil": "zivilrecht",
    "IIe Cour de droit civil": "zivilrecht",
    "Ire Cour de droit pénal": "strafrecht",
    "IIe Cour de droit pénal": "strafrecht",
}

def assign_branch(chamber: str) -> str:
    if chamber in CHAMBER_TO_BRANCH:
        return CHAMBER_TO_BRANCH[chamber]
    chamber_lower = chamber.lower()
    if "öffentlich" in chamber_lower or "public" in chamber_lower:
        return "oeffentliches_recht"
    if "zivil" in chamber_lower or "civil" in chamber_lower:
        return "zivilrecht"
    if "straf" in chamber_lower or "pénal" in chamber_lower or "penal" in chamber_lower:
        return "strafrecht"
    if "sozial" in chamber_lower or "social" in chamber_lower:
        return "sozialversicherungsrecht"
    return "unknown"

def load_expanded_corpus() -> Tuple[List[Dict], List[Dict]]:
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

def load_cached_st_embeddings() -> np.ndarray:
    if not CACHED_ST_EMBEDDINGS_FILE.exists():
        raise FileNotFoundError(f"Cached embeddings not found at {CACHED_ST_EMBEDDINGS_FILE}")
    embeddings = np.load(CACHED_ST_EMBEDDINGS_FILE)
    logger.info(f"Loaded cached ST embeddings: {embeddings.shape}")
    return embeddings

def create_center_projected(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    languages = sorted(set(m['language'] for m in metadata))
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
    
    debiased = np.copy(embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    debiased = debiased / norms
    return debiased

def load_v5_center_projected() -> Tuple[np.ndarray, List[Dict]]:
    embeddings = np.load(V5_CENTER_PROJECTED_FILE)
    with open(V5_CENTER_PROJECTED_META_FILE, 'r') as f:
        metadata = json.load(f)
    
    # Add branch to metadata
    for m in metadata:
        chamber = m.get("chamber", "")
        m['branch'] = assign_branch(chamber)
    
    logger.info(f"Loaded v5 center_projected: {embeddings.shape}")
    return embeddings, metadata

def debug_jp_comparison(embeddings: np.ndarray, metadata: List[Dict], name: str, k: int = 10) -> Dict:
    """Debug jurist pairwise preference with detailed logging."""
    logger.info(f"\n{'='*60}")
    logger.info(f"DEBUG JP for: {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*60}")
    
    # Prepare metadata
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    meta_valid = [metadata[i] for i in valid_indices]
    emb_valid = embeddings[valid_indices]
    
    logger.info(f"Valid decisions: {len(valid_indices)} (out of {len(metadata)})")
    logger.info(f"Branch dist: {Counter(branches)}")
    logger.info(f"Language dist: {Counter(languages)}")
    
    # Run JP with debug
    n = len(branches)
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(emb_valid)
    _, indices = nn.kneighbors(emb_valid)
    neighbors = indices[:, 1:]
    
    legal_relevant_count = 0
    language_artifact_count = 0
    both_count = 0
    neither_count = 0
    
    # Track first 20 decisions for debugging
    debug_details = []
    
    for i in range(n):
        branch_i = branches[i]
        lang_i = languages[i]
        
        neighbor_branches = branches[neighbors[i]]
        neighbor_langs = languages[neighbors[i]]
        
        has_legal_relevant = False
        has_language_artifact = False
        
        # Debug: track neighbor details for first few
        if i < 20:
            neighbor_details = []
            for nb, nl in zip(neighbor_branches, neighbor_langs):
                neighbor_details.append(f"  ({nb}, {nl})")
                if nb == branch_i and nl != lang_i:
                    has_legal_relevant = True
                if nb != branch_i and nl == lang_i:
                    has_language_artifact = True
            debug_details.append({
                'decision_idx': i,
                'branch': branch_i,
                'lang': lang_i,
                'neighbors': neighbor_details[:5],  # top 5
                'has_legal_relevant': has_legal_relevant,
                'has_language_artifact': has_language_artifact,
            })
        else:
            for nb, nl in zip(neighbor_branches, neighbor_langs):
                if nb == branch_i and nl != lang_i:
                    has_legal_relevant = True
                if nb != branch_i and nl == lang_i:
                    has_language_artifact = True
        
        if has_legal_relevant and has_language_artifact:
            both_count += 1
        elif has_legal_relevant:
            legal_relevant_count += 1
        elif has_language_artifact:
            language_artifact_count += 1
        else:
            neither_count += 1
    
    jurist_correct = legal_relevant_count + both_count
    jurist_forced_wrong = language_artifact_count
    total = n
    legal_neighbor_rate = (legal_relevant_count + both_count) / total
    language_neighbor_rate = (language_artifact_count + both_count) / total
    
    logger.info(f"  legal_relevant_only: {legal_relevant_count}")
    logger.info(f"  language_artifact_only: {language_artifact_count}")
    logger.info(f"  both_available: {both_count}")
    logger.info(f"  neither_available: {neither_count}")
    logger.info(f"  legal_neighbor_rate: {legal_neighbor_rate:.4f}")
    logger.info(f"  language_neighbor_rate: {language_neighbor_rate:.4f}")
    logger.info(f"  jurist_would_succeed_rate: {jurist_correct/total:.4f}")
    logger.info(f"  jurist_forced_wrong_rate: {jurist_forced_wrong/total:.4f}")
    
    # Print debug details
    logger.info(f"\n  First 10 decisions neighbor details:")
    for d in debug_details[:10]:
        logger.info(f"    Decision {d['decision_idx']}: branch={d['branch']}, lang={d['lang']}")
        logger.info(f"      Neighbors: {', '.join(d['neighbors'])}")
        logger.info(f"      Legal relevant: {d['has_legal_relevant']}, Language artifact: {d['has_language_artifact']}")
    
    return {
        "status": "PASS" if legal_neighbor_rate > 0.5 else "FAIL",
        "total_decisions": total,
        "legal_relevant_only": legal_relevant_count,
        "language_artifact_only": language_artifact_count,
        "both_available": both_count,
        "neither_available": neither_count,
        "legal_neighbor_rate": round(legal_neighbor_rate, 4),
        "language_neighbor_rate": round(language_neighbor_rate, 4),
        "jurist_would_succeed_rate": round(jurist_correct / total, 4),
        "jurist_forced_wrong_rate": round(jurist_forced_wrong / total, 4),
    }

def main():
    logger.info("=" * 70)
    logger.info("DEBUG COMPREHENSIVE VALIDATION JP ANOMALY")
    logger.info("=" * 70)
    
    # 1. Load expanded corpus metadata
    logger.info("\n1. Loading expanded corpus metadata...")
    corpus, metadata = load_expanded_corpus()
    
    # 2. Load cached ST embeddings (384-dim)
    logger.info("\n2. Loading cached ST embeddings...")
    st_embeddings = load_cached_st_embeddings()
    
    # 3. Create ST-based center_projected
    logger.info("\n3. Creating ST-based center_projected...")
    st_center_projected = create_center_projected(st_embeddings, metadata)
    
    # 4. Load v5 baseline center_projected (768-dim)
    logger.info("\n4. Loading v5 baseline center_projected...")
    v5_center_projected, v5_metadata = load_v5_center_projected()
    
    # 5. Debug JP for both
    logger.info("\n" + "="*70)
    logger.info("COMPARING JURIST PREFERENCE")
    logger.info("="*70)
    
    # ST-based center_projected
    st_jp = debug_jp_comparison(st_center_projected, metadata, "ST-based center_projected (384-dim)")
    
    # v5 baseline center_projected (use its metadata)
    v5_jp = debug_jp_comparison(v5_center_projected, v5_metadata, "v5 baseline center_projected (768-dim)")
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)
    logger.info(f"ST-based center_projected JP: {st_jp['jurist_would_succeed_rate']:.4f} (legal_rel={st_jp['legal_relevant_only']}, lang_art={st_jp['language_artifact_only']}, both={st_jp['both_available']}, neither={st_jp['neither_available']})")
    logger.info(f"v5 baseline center_projected JP: {v5_jp['jurist_would_succeed_rate']:.4f} (legal_rel={v5_jp['legal_relevant_only']}, lang_art={v5_jp['language_artifact_only']}, both={v5_jp['both_available']}, neither={v5_jp['neither_available']})")
    
    # Also test adversarial language dominance
    logger.info("\n" + "="*70)
    logger.info("ADVERSARIAL LANGUAGE DOMINANCE")
    logger.info("="*70)
    
    def adv_lang_dom(embeddings, metadata, k=20):
        nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
        nn.fit(embeddings)
        _, indices = nn.kneighbors(embeddings)
        neighbors = indices[:, 1:]
        
        dominance_rates = []
        for i, m in enumerate(metadata):
            lang = m.get('language', 'unknown')
            neighbor_langs = [metadata[n].get('language', 'unknown') for n in neighbors[i]]
            same_lang = sum(1 for l in neighbor_langs if l == lang)
            dominance_rates.append(same_lang / k)
        return float(np.mean(dominance_rates))
    
    # For ST-based, use valid indices
    branches_st, languages_st, chambers_st, valid_indices_st = prepare_metadata(metadata)
    st_emb_valid = st_center_projected[valid_indices_st]
    st_meta_valid = [metadata[i] for i in valid_indices_st]
    st_lang_dom = adv_lang_dom(st_emb_valid, st_meta_valid)
    
    # For v5 baseline
    branches_v5, languages_v5, chambers_v5, valid_indices_v5 = prepare_metadata(v5_metadata)
    v5_emb_valid = v5_center_projected[valid_indices_v5]
    v5_meta_valid = [v5_metadata[i] for i in valid_indices_v5]
    v5_lang_dom = adv_lang_dom(v5_emb_valid, v5_meta_valid)
    
    logger.info(f"ST-based center_projected LangDom: {st_lang_dom:.4f}")
    logger.info(f"v5 baseline center_projected LangDom: {v5_lang_dom:.4f}")

if __name__ == "__main__":
    main()