#!/usr/bin/env python3
"""
Legal Distance Lane v6 - Comprehensive Validation on 1200-Decision Expanded Slice

Factory Direction v6 requirements addressed:
1. REPRODUCE center_projected representation on current codebase and validate on full v1+v2 benchmark suite
2. Re-run signal ablation (v4) and scale test (v5) USING center_projected as baseline
3. Validate cited_decisions_tfidf (new candidate passing BOTH adversarial gates) on full benchmark suite
4. Test cited_decisions_tfidf hybrids with center_projected

Key issue to resolve: center_projected jurist preference discrepancy
- 1000-decision baseline: JP=0.5275 (PASS)
- 1200-decision expanded: JP=0.4912 (FAIL) - metadata alignment issue
- Need to validate on the canonical 1200-decision expanded slice

This script uses the bger_expanded_1200.jsonl as the canonical corpus.
"""

import json
import numpy as np
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
from sklearn.decomposition import TruncatedSVD, PCA
from sklearn.preprocessing import normalize
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score
from sklearn.cluster import KMeans

# Add fractal-map hierarchical module
import sys
sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
from hierarchical_leiden import hierarchical_leiden, compute_branch_purity, leiden_clustering
from hierarchical_zoom_validation import hierarchical_leiden as hz_hierarchical_leiden, compute_branch_purity_per_cluster

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
EXPANDED_CORPUS_FILE = Path("/tmp/lex_accepted/evaluation/evaluation/data/bger_expanded_1200.jsonl")
EXPANDED_METADATA_FILE = Path("/tmp/lex_accepted/evaluation/evaluation/data/bger_expanded_1200_metadata.jsonl")
BASELINE_EMBEDDINGS_FILE = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/embeddings.npy")
BASELINE_METADATA_FILE = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json")
SIGNALS_FILE_V2 = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/legal_signals_1000_v2.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/comprehensive_validation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load multilingual sentence transformer
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_MODEL = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    logger.info("Loaded sentence transformer for embeddings")
except ImportError:
    EMBEDDING_MODEL = None
    logger.warning("sentence_transformers not available")

# Chamber to branch mapping
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
    """Load the 1200-decision expanded corpus and metadata."""
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


def load_signals_v2() -> Dict[str, Any]:
    """Load v2 legal signals (1000 decisions)."""
    signals = {}
    with open(SIGNALS_FILE_V2, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    logger.info(f"Loaded v2 signals for {len(signals)} decisions")
    return signals


def create_center_projected(embeddings: np.ndarray, metadata: List[Dict]) -> np.ndarray:
    """Create center_projected by subtracting language centers."""
    languages = sorted(set(m['language'] for m in metadata))
    
    # Compute language centers
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
    
    # For each embedding, subtract its language center
    debiased = np.copy(embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    # L2 normalize
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    debiased = debiased / norms
    
    return debiased


def compute_sentence_transformer_embeddings(corpus: List[Dict]) -> np.ndarray:
    """Compute sentence transformer embeddings for the corpus."""
    if EMBEDDING_MODEL is None:
        raise RuntimeError("sentence_transformers not available")
    
    # Combine title + erwaegungen_text for embedding
    texts = []
    for d in corpus:
        # Use the first part of erwaegungen_text as representative
        text = d.get('erwaegungen_text', '')[:2000]  # Limit length
        if not text:
            text = d.get('decision_id', '')
        texts.append(text)
    
    logger.info(f"Computing embeddings for {len(texts)} decisions...")
    embeddings = EMBEDDING_MODEL.encode(texts, show_progress_bar=True, batch_size=32)
    logger.info(f"Embeddings shape: {embeddings.shape}")
    return embeddings


def build_cited_decisions_tfidf(signals: Dict[str, Any], metadata: List[Dict], max_features: int = 5000) -> np.ndarray:
    """Build TF-IDF on cited decisions."""
    texts = []
    valid_indices = []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        sig = signals.get(did, {})
        
        cited = sig.get('cited_decisions', [])
        if cited:
            texts.append(" ".join(cited))
            valid_indices.append(i)
        else:
            texts.append("")
    
    if len(valid_indices) < 100:
        logger.warning(f"Only {len(valid_indices)} valid cited decisions for TF-IDF")
        return np.zeros((len(metadata), 128))
    
    valid_texts = [texts[i] for i in valid_indices]
    
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        min_df=2,
        max_df=0.95,
        ngram_range=(1, 2),
        sublinear_tf=True,
        lowercase=True,
        strip_accents='unicode',
    )
    
    tfidf_matrix = vectorizer.fit_transform(valid_texts)
    
    n_comp = min(128, tfidf_matrix.shape[1] - 1, len(valid_texts) - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    reduced = svd.fit_transform(tfidf_matrix)
    
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms
    
    full_emb = np.zeros((len(metadata), n_comp))
    for j, idx in enumerate(valid_indices):
        full_emb[idx] = reduced[j]
    
    logger.info(f"Cited decisions TF-IDF: {len(valid_indices)} valid, {n_comp} dims")
    return full_emb


def prepare_metadata(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
    """Extract branch, language, chamber from metadata."""
    branches = []
    languages = []
    chambers = []
    valid_indices = []
    
    for i, meta in enumerate(metadata):
        chamber = meta.get("chamber", "")
        branch = meta.get("branch") or assign_branch(chamber)
        lang = meta.get("language", "unknown")
        
        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            chambers.append(chamber)
            valid_indices.append(i)
    
    return np.array(branches), np.array(languages), np.array(chambers), valid_indices


def adversarial_language_dominance(embeddings: np.ndarray, metadata: List[Dict], k: int = 20) -> Dict:
    """Adversarial test: measure language dominance in nearest neighbors."""
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
    
    mean_dominance = np.mean(dominance_rates)
    
    return {
        'mean_language_dominance': float(mean_dominance),
        'std_language_dominance': float(np.std(dominance_rates)),
        'max_language_dominance': float(np.max(dominance_rates)),
        'k': k,
        'threshold': 0.85,
        'status': 'PASS' if mean_dominance < 0.85 else 'FAIL',
        'note': 'Lower is better - language should not dominate neighbors'
    }


def simulate_pairwise_preference(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    k: int = 10
) -> Dict:
    """Simulate jurist pairwise preference study."""
    n = len(branches)
    
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    legal_relevant_count = 0
    language_artifact_count = 0
    both_count = 0
    neither_count = 0
    
    for i in range(n):
        branch_i = branches[i]
        lang_i = languages[i]
        
        neighbor_branches = branches[neighbors[i]]
        neighbor_langs = languages[neighbors[i]]
        
        has_legal_relevant = False
        has_language_artifact = False
        
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
        "note": "Simulated jurist prefers legally-relevant neighbors. Rate > 0.5 means majority of decisions have at least one legally-relevant neighbor in top-k."
    }


def run_fractal_harness(
    embeddings: np.ndarray,
    metadata: List[Dict],
    config_name: str,
    coarse_res: float = 0.5,
    sub_res: float = 3.0
) -> Dict[str, Any]:
    """Run hierarchical Leiden + zoom coherence validation."""
    logger.info(f"  Running fractal-map harness for {config_name}...")
    
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hz_hierarchical_leiden(
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
    
    # Legal area NMI
    unique_labels = np.unique(hierarchical_labels[hierarchical_labels != -1])
    legal_areas = [metadata[i].get('legal_area', '') for i in range(len(metadata))]
    legal_areas = [la if la else 'unknown' for la in legal_areas]
    nmi = normalized_mutual_info_score(legal_areas, hierarchical_labels)
    
    # Flat Leiden comparison
    flat_labels, _ = leiden_clustering(embeddings, resolution=sub_res)
    flat_purity = compute_branch_purity(flat_labels, metadata)
    hierarchical_advantage = fine_overall - flat_purity
    
    logger.info(f"    Coarse: {n_coarse}, Fine: {n_fine}")
    logger.info(f"    Coarse purity: {coarse_overall:.4f}, Fine purity: {fine_overall:.4f}")
    logger.info(f"    Improvement: {overall_improvement:+.4f} ({improvement_rate:.1%})")
    logger.info(f"    Legal area NMI: {nmi:.4f}")
    logger.info(f"    Hierarchical advantage: {hierarchical_advantage:+.4f}")
    
    return {
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
        'hierarchical_advantage': float(hierarchical_advantage),
        'zoom_results': zoom_results,
    }


def project_to_dim(emb: np.ndarray, target_dim: int) -> np.ndarray:
    """Project embeddings to target dimension using SVD or padding."""
    n_samples, n_features = emb.shape
    
    if n_features <= target_dim:
        if n_features < target_dim:
            padding = np.zeros((n_samples, target_dim - n_features))
            return np.concatenate([emb, padding], axis=1)
        return emb
    
    if n_samples < target_dim + 1:
        return emb[:, :target_dim]
    
    svd = TruncatedSVD(n_components=target_dim, random_state=42)
    return svd.fit_transform(emb)


def create_hybrid_representation(
    legal_emb: np.ndarray,
    baseline_emb: np.ndarray,
    alpha: float = 0.5,
    target_dim: int = 64
) -> np.ndarray:
    """Create hybrid representation: alpha * legal + (1-alpha) * baseline."""
    legal_proj = project_to_dim(legal_emb, target_dim)
    baseline_proj = project_to_dim(baseline_emb, target_dim)
    
    legal_proj = normalize(legal_proj, norm='l2', axis=1)
    baseline_proj = normalize(baseline_proj, norm='l2', axis=1)
    
    hybrid = alpha * legal_proj + (1 - alpha) * baseline_proj
    hybrid = normalize(hybrid, norm='l2', axis=1)
    
    return hybrid


def evaluate_representation(
    name: str,
    embeddings: np.ndarray,
    metadata: List[Dict],
    branches: np.ndarray,
    languages: np.ndarray
) -> Dict[str, Any]:
    """Evaluate a single representation against adversarial + fractal benchmarks."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating: {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*60}")
    
    start_time = time.time()
    
    # 1. Adversarial benchmarks
    logger.info("  Running adversarial benchmarks...")
    lang_dom = adversarial_language_dominance(embeddings, metadata)
    jurist_pref = simulate_pairwise_preference(embeddings, branches, languages)
    
    both_pass = lang_dom.get('status') == 'PASS' and jurist_pref.get('status') == 'PASS'
    
    adv_results = {
        'adversarial_language_dominance': lang_dom,
        'jurist_pairwise_preference': jurist_pref,
        'both_pass': both_pass,
        'language_dominance_score': lang_dom.get('mean_language_dominance', 1.0),
        'jurist_preference_rate': jurist_pref.get('jurist_would_succeed_rate', 0.0),
    }
    
    # 2. Fractal quality benchmarks
    logger.info("  Running fractal-map harness...")
    fractal_results = run_fractal_harness(embeddings, metadata, name)
    
    duration = time.time() - start_time
    
    # Overall verdict
    verdict = "PASS" if both_pass else "FAIL"
    
    result = {
        'name': name,
        'embedding_shape': list(embeddings.shape),
        'duration_seconds': duration,
        'adversarial': adv_results,
        'fractal': fractal_results,
        'verdict': verdict,
        'both_adversarial_pass': both_pass,
    }
    
    # Log summary
    logger.info(f"  VERDICT: {verdict}")
    logger.info(f"  Language dominance: {adv_results['language_dominance_score']:.4f} ({lang_dom['status']})")
    logger.info(f"  Jurist preference: {adv_results['jurist_preference_rate']:.4f} ({jurist_pref['status']})")
    logger.info(f"  Improvement rate: {fractal_results['improvement_rate']:.2%}")
    logger.info(f"  Legal area NMI: {fractal_results['legal_area_nmi']:.4f}")
    logger.info(f"  Hierarchical advantage: {fractal_results['hierarchical_advantage']:.4f}")
    logger.info(f"  Coarse clusters: {fractal_results['n_coarse_clusters']}, Fine clusters: {fractal_results['n_fine_clusters']}")
    
    return result


def main():
    logger.info("=" * 70)
    logger.info("Legal Distance Lane v6 - Comprehensive Validation on 1200-Decision Slice")
    logger.info("=" * 70)
    
    # 1. Load data
    logger.info("\n1. Loading 1200-decision expanded corpus...")
    corpus, metadata = load_expanded_corpus()
    
    # Add branch to metadata if not present
    for m in metadata:
        if 'branch' not in m:
            m['branch'] = assign_branch(m.get('chamber', ''))
    
    logger.info(f"Languages: {Counter(m['language'] for m in metadata)}")
    logger.info(f"Branches: {Counter(m['branch'] for m in metadata)}")
    
    logger.info("\n2. Loading v2 legal signals...")
    signals = load_signals_v2()
    
    # 3. Compute sentence transformer embeddings for full 1200 decisions
    logger.info("\n3. Computing sentence transformer embeddings (768-dim)...")
    st_embeddings = compute_sentence_transformer_embeddings(corpus)
    
    # 4. Create center_projected representation
    logger.info("\n4. Creating center_projected representation...")
    center_projected = create_center_projected(st_embeddings, metadata)
    logger.info(f"  Center projected shape: {center_projected.shape}")
    
    # 5. Build cited_decisions_tfidf
    logger.info("\n5. Building cited_decisions_tfidf representation...")
    cited_decisions_tfidf = build_cited_decisions_tfidf(signals, metadata)
    logger.info(f"  Cited decisions TF-IDF shape: {cited_decisions_tfidf.shape}")
    
    # 6. Prepare metadata for adversarial benchmarks
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    meta_valid = [metadata[i] for i in valid_indices]
    logger.info(f"\nValid metadata for adversarial benchmarks: {len(valid_indices)} decisions")
    
    # 7. Define experiments
    experiments = [
        # Baseline references
        ("center_projected", center_projected, "REPRODUCED baseline: center_projected (language centers subtracted from 768-dim sentence transformer)"),
        ("cited_decisions_tfidf", cited_decisions_tfidf, "TF-IDF on cited decisions - NEW candidate passing both adversarial gates in v6 hybrids test"),
        
        # Hybrids: cited_decisions_tfidf + center_projected
        ("hybrid_cited_0.3", create_hybrid_representation(cited_decisions_tfidf, center_projected, 0.3), "Hybrid: 30% cited_decisions_tfidf + 70% center_projected"),
        ("hybrid_cited_0.5", create_hybrid_representation(cited_decisions_tfidf, center_projected, 0.5), "Hybrid: 50% cited_decisions_tfidf + 50% center_projected"),
        ("hybrid_cited_0.7", create_hybrid_representation(cited_decisions_tfidf, center_projected, 0.7), "Hybrid: 70% cited_decisions_tfidf + 30% center_projected"),
    ]
    
    # 8. Run evaluations
    logger.info(f"\n6. Running {len(experiments)} experiments against adversarial + fractal benchmarks...")
    all_results = {}
    
    for name, emb, desc in experiments:
        logger.info(f"\n{'='*60}")
        logger.info(f"EXPERIMENT: {name}")
        logger.info(f"  Description: {desc}")
        logger.info(f"  Embedding shape: {emb.shape}")
        
        # For adversarial benchmarks, use only valid indices
        emb_valid = emb[valid_indices]
        
        results = evaluate_representation(name, emb_valid, meta_valid, branches, languages)
        results['embedding_shape_full'] = list(emb.shape)
        all_results[name] = results
        
        # Save intermediate
        with open(OUTPUT_DIR / f"comprehensive_{name}_results.json", 'w') as f:
            json.dump(results, f, indent=2, default=str)
    
    # 9. Save all results
    with open(OUTPUT_DIR / "comprehensive_validation_all_results.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # 10. Summary comparison
    logger.info("\n" + "=" * 100)
    logger.info("V6 COMPREHENSIVE VALIDATION SUMMARY")
    logger.info("=" * 100)
    logger.info(f"{'Experiment':<30} {'Verdict':<8} {'LangDom':>8} {'Jurist':>8} {'Both':>5} {'ImpRate':>8} {'NMI':>6} {'HAdv':>6} {'C/F':>8}")
    logger.info("-" * 100)
    
    baseline_result = all_results.get("center_projected", {})
    baseline_fine = baseline_result.get('fractal', {}).get('fine_purity', 0)
    baseline_nmi = baseline_result.get('fractal', {}).get('legal_area_nmi', 0)
    baseline_coarse = baseline_result.get('fractal', {}).get('coarse_purity', 0)
    baseline_both = baseline_result.get('both_adversarial_pass', False)
    
    # Sort by both_adversarial_pass, then jurist preference, then -language dominance
    def sort_key(item):
        name, res = item
        both = res['both_adversarial_pass']
        jurist = res['adversarial']['jurist_preference_rate']
        lang_dom = res['adversarial']['language_dominance_score']
        return (both, jurist, -lang_dom)
    
    sorted_results = sorted(all_results.items(), key=sort_key, reverse=True)
    
    for name, res in sorted_results:
        adv = res['adversarial']
        frac = res['fractal']
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        both = "✓" if adv['both_pass'] else "✗"
        verdict = res['verdict']
        
        coarse = frac.get('coarse_purity', 0)
        fine = frac.get('fine_purity', 0)
        improv = frac.get('improvement_rate', 0)
        nmi = frac.get('legal_area_nmi', 0)
        hadv = frac.get('hierarchical_advantage', 0)
        n_coarse = frac.get('n_coarse_clusters', 0)
        n_fine = frac.get('n_fine_clusters', 0)
        
        logger.info(f"{name:<30} {verdict:<8} {ld:>8.4f} {jp:>8.4f} {both:>5} {improv:>7.1%} {nmi:>6.4f} {hadv:>6.4f} {n_coarse}/{n_fine:<4}")
    
    # 11. Key findings
    logger.info("\n" + "=" * 80)
    logger.info("KEY FINDINGS")
    logger.info("=" * 80)
    
    # Which pass both adversarial gates
    logger.info("\n✅ Representations passing BOTH adversarial gates:")
    for name, res in all_results.items():
        if res['both_adversarial_pass']:
            adv = res['adversarial']
            frac = res['fractal']
            hadv = frac.get('hierarchical_advantage', 0)
            n_coarse = frac.get('n_coarse_clusters', 0)
            n_fine = frac.get('n_fine_clusters', 0)
            logger.info(f"  {name}: lang_dom={adv['language_dominance_score']:.4f}, jurist={adv['jurist_preference_rate']:.4f}, "
                       f"hier_adv={hadv:.4f}, clusters={n_coarse}/{n_fine}")
    
    # Which pass adversarial but overcluster (hierarchical_advantage ≈ 0)
    logger.info("\n⚠️ Representations passing adversarial but OVERCLUSTERING (hierarchical_advantage ≈ 0):")
    for name, res in all_results.items():
        if res['both_adversarial_pass']:
            hadv = res['fractal'].get('hierarchical_advantage', 0)
            if hadv < 0.01:
                frac = res['fractal']
                logger.info(f"  {name}: hier_adv={hadv:.4f}, clusters={frac.get('n_coarse_clusters', 0)}/{frac.get('n_fine_clusters', 0)}")
    
    # Which fail adversarial
    logger.info("\n❌ Representations FAILING adversarial gates:")
    for name, res in all_results.items():
        if not res['both_adversarial_pass']:
            adv = res['adversarial']
            logger.info(f"  {name}: lang_dom={adv['language_dominance_score']:.4f} ({adv['adversarial_language_dominance']['status']}), "
                       f"jurist={adv['jurist_preference_rate']:.4f} ({adv['jurist_pairwise_preference']['status']})")
    
    # Compare with center_projected baseline
    logger.info("\n📊 Delta vs center_projected baseline:")
    for name, res in all_results.items():
        if name == "center_projected":
            continue
        adv = res['adversarial']
        frac = res['fractal']
        ld_delta = adv['language_dominance_score'] - baseline_result['adversarial']['language_dominance_score']
        jp_delta = adv['jurist_preference_rate'] - baseline_result['adversarial']['jurist_preference_rate']
        fine_delta = frac.get('fine_purity', 0) - baseline_fine
        nmi_delta = frac.get('legal_area_nmi', 0) - baseline_nmi
        coarse_delta = frac.get('coarse_purity', 0) - baseline_coarse
        hadv_delta = frac.get('hierarchical_advantage', 0) - baseline_result['fractal'].get('hierarchical_advantage', 0)
        
        both_pass = "✓" if adv['both_pass'] else "✗"
        logger.info(f"  {name}: both={both_pass}, Δlang={ld_delta:+.4f}, Δjurist={jp_delta:+.4f}, "
                   f"Δfine={fine_delta:+.4f}, ΔNMI={nmi_delta:+.4f}, Δcoarse={coarse_delta:+.4f}, ΔHadv={hadv_delta:+.4f}")
    
    # 12. Verdict for product decision
    logger.info("\n" + "=" * 80)
    logger.info("PRODUCT DECISION RECOMMENDATION")
    logger.info("=" * 80)
    
    center_cp = all_results.get("center_projected", {})
    cited_cp = all_results.get("cited_decisions_tfidf", {})
    
    if center_cp.get('both_adversarial_pass') and cited_cp.get('both_adversarial_pass'):
        logger.info("BOTH center_projected and cited_decisions_tfidf pass adversarial gates on 1200 decisions.")
        logger.info("→ cited_decisions_tfidf is a validated alternative with different tradeoffs.")
        logger.info("→ Test hybrids to find best of both worlds.")
    elif center_cp.get('both_adversarial_pass'):
        logger.info("ONLY center_projected passes both adversarial gates on 1200 decisions.")
        logger.info("→ center_projected remains the unique validated default.")
    elif cited_cp.get('both_adversarial_pass'):
        logger.info("ONLY cited_decisions_tfidf passes both adversarial gates on 1200 decisions.")
        logger.info("→ cited_decisions_tfidf should become the new default reference.")
    else:
        logger.info("NEITHER passes both adversarial gates on 1200 decisions.")
        logger.info("→ Need to investigate metadata alignment or representation quality.")
    
    logger.info("\n=== V6 Comprehensive Validation Complete ===")
    return all_results


if __name__ == "__main__":
    main()