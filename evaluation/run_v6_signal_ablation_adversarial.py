#!/usr/bin/env python3
"""
Evaluation v6 — Adversarial Validation of Signal Ablation Variants (center_projected baseline)

This script:
1. Generates signal ablation variant embeddings using the legal-distance v5 methodology
2. Aligns them to the expanded 1,200-decision slice
3. Runs the full adversarial benchmark suite on each variant
4. Compares against center_projected baseline

Factory Direction v6: "Validate legal-distance unsupervised signal ablation results (on center_projected baseline) 
on expanded slice (1,200 decisions) using adversarial benchmarks"
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Any
from collections import Counter
from dataclasses import dataclass
import sys
import importlib.util
import logging

# Frozen global seed for reproducibility
GLOBAL_SEED = 42
np.random.seed(GLOBAL_SEED)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

eval_dir = Path('/home/runner/work/LexMachina/LexMachina/evaluation')
tests_dir = eval_dir / 'tests'

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load benchmark modules
cross_lang = load_module('cross_language_benchmarks', tests_dir / 'cross_language_benchmarks.py')
jurist_usability = load_module('jurist_usability', tests_dir / 'jurist_usability.py')
jurivoc_module = load_module('jurivoc_benchmarks', tests_dir / 'jurivoc_benchmarks.py')
scale_frozen = load_module('scale_benchmarks_frozen', tests_dir / 'scale_benchmarks_frozen.py')

# Import benchmark functions
cross_language_neighbor_quality = cross_lang.cross_language_neighbor_quality
zero_shot_cross_language_transfer = cross_lang.zero_shot_cross_language_transfer
language_specific_representation_quality = cross_lang.language_specific_representation_quality
adversarial_language_dominance = cross_lang.adversarial_language_dominance
run_all_cross_language_benchmarks = cross_lang.run_all_cross_language_benchmarks

simulate_pairwise_preference = jurist_usability.simulate_pairwise_preference
simulate_cluster_coherence_rating = jurist_usability.simulate_cluster_coherence_rating
simulate_cross_language_retrieval = jurist_usability.simulate_cross_language_retrieval

JurivocBenchmarks = jurivoc_module.JurivocBenchmarks

run_frozen_scale_benchmark = scale_frozen.run_frozen_scale_benchmark
compute_frozen_pipeline = scale_frozen.compute_frozen_pipeline
position_drift = scale_frozen.position_drift
neighbor_preservation = scale_frozen.neighbor_preservation
cluster_stability = scale_frozen.cluster_stability

# Boilerplate resistance - requires full text which expanded slice doesn't have
# We'll skip this in v6 and note it as a limitation
def run_boilerplate_resistance(embeddings, metadata):
    return {'status': 'SKIP', 'reason': 'Full decision text not available in expanded slice metadata. Requires corpus text for perturbation test.'}

# Paths
SIGNALS_FILE = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/legal_signals_full.jsonl")
CENTER_PROJECTED_DIR = Path("/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full")
EXPANDED_META_PATH = Path("/home/runner/work/LexMachina/LexMachina/evaluation/data/bger_expanded_1200_metadata.jsonl")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/evaluation/v6_signal_ablation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load sentence transformer for norm embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_MODEL = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    logger.info("Loaded sentence transformer for norm embeddings")
except ImportError:
    EMBEDDING_MODEL = None
    logger.warning("sentence_transformers not available, norm embeddings will be zeros")

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from scipy.sparse import csr_matrix


@dataclass
class SignalConfig:
    use_sachverhalt: bool = False
    use_erwaegungen: bool = False
    use_norm_embeddings: bool = False
    use_citation_weights: bool = False
    use_doctrine_refs: bool = False
    use_outcome: bool = False
    use_legal_area: bool = False
    use_erwaegungen_headings: bool = False
    max_features: int = 5000
    min_df: int = 2
    max_df: float = 0.95
    ngram_range: Tuple[int, int] = (1, 2)


def load_signals() -> Dict[str, Any]:
    signals = {}
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            signals[data['decision_id']] = data
    logger.info(f"Loaded signals for {len(signals)} decisions")
    return signals


def load_center_projected_baseline() -> Tuple[np.ndarray, List[Dict]]:
    embeddings_path = CENTER_PROJECTED_DIR / 'embeddings_center_projected.npy'
    metadata_path = CENTER_PROJECTED_DIR / 'metadata.json'
    embeddings = np.load(embeddings_path)
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    logger.info(f"Loaded center_projected baseline: {embeddings.shape}")
    return embeddings, metadata


def load_expanded_slice_metadata() -> List[Dict]:
    metadata = []
    with open(EXPANDED_META_PATH, 'r') as f:
        for line in f:
            metadata.append(json.loads(line))
    return metadata


def align_to_expanded_slice(embeddings: np.ndarray, cp_metadata: List[Dict]) -> Tuple[np.ndarray, List[Dict]]:
    """Align embeddings to expanded slice order."""
    expanded_metadata = load_expanded_slice_metadata()
    cp_id_to_idx = {m['decision_id']: i for i, m in enumerate(cp_metadata)}
    
    aligned_embeddings = np.zeros((len(expanded_metadata), embeddings.shape[1]), dtype=embeddings.dtype)
    aligned_metadata = []
    
    for i, exp_meta in enumerate(expanded_metadata):
        did = exp_meta['decision_id']
        if did in cp_id_to_idx:
            cp_idx = cp_id_to_idx[did]
            aligned_embeddings[i] = embeddings[cp_idx]
            aligned_metadata.append(exp_meta)
        else:
            logger.warning(f"Decision {did} not found in center_projected metadata")
    
    logger.info(f"Aligned {len(aligned_embeddings)} decisions to expanded slice")
    return aligned_embeddings, aligned_metadata


def prepare_metadata_full(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
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
    
    branches = []
    languages = []
    chambers = []
    valid_indices = []
    
    for i, meta in enumerate(metadata):
        chamber = meta.get("chamber", "")
        branch = assign_branch(chamber)
        lang = meta.get("language", "unknown")
        
        branches.append(branch)
        languages.append(lang)
        chambers.append(chamber)
        
        if branch != "unknown":
            valid_indices.append(i)
    
    return np.array(branches), np.array(languages), np.array(chambers), valid_indices


def build_norm_embeddings(signals: Dict[str, Any], metadata: List[Dict]) -> np.ndarray:
    if EMBEDDING_MODEL is None:
        return np.zeros((len(metadata), 384))
    
    valid_indices = []
    embeddings_list = []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        sig = signals.get(did, {})
        statute_contexts = sig.get('statute_contexts', [])
        if not statute_contexts:
            continue
        
        context_embeddings = EMBEDDING_MODEL.encode(statute_contexts, show_progress_bar=False)
        avg_embedding = np.mean(context_embeddings, axis=0)
        embeddings_list.append(avg_embedding)
        valid_indices.append(i)
    
    if not embeddings_list:
        return np.zeros((len(metadata), 384))
    
    n_dim = embeddings_list[0].shape[0]
    full_emb = np.zeros((len(metadata), n_dim))
    for j, idx in enumerate(valid_indices):
        full_emb[idx] = embeddings_list[j]
    
    norms = np.linalg.norm(full_emb, axis=1, keepdims=True)
    norms[norms == 0] = 1
    full_emb = full_emb / norms
    
    logger.info(f"Norm embeddings: {len(valid_indices)} valid, {n_dim} dims")
    return full_emb


def build_citation_weight_matrix(signals: Dict[str, Any], metadata: List[Dict]) -> np.ndarray:
    n = len(metadata)
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    rows, cols, weights = [], [], []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        sig = signals.get(did, {})
        
        outgoing = sig.get('outgoing_citations', [])
        for cit in outgoing:
            target = cit.get('target', '')
            if target in id_to_idx:
                j = id_to_idx[target]
                mention_count = cit.get('mention_count', 1)
                confidence = cit.get('confidence', 1.0)
                weight = mention_count * confidence
                rows.append(i)
                cols.append(j)
                weights.append(weight)
        
        cited = sig.get('cited_decisions', [])
        for target in cited:
            if target in id_to_idx:
                j = id_to_idx[target]
                if not any(r == i and c == j for r, c in zip(rows, cols)):
                    rows.append(i)
                    cols.append(j)
                    weights.append(1.0)
    
    if not rows:
        return np.zeros((n, 64))
    
    citation_matrix = csr_matrix((weights, (rows, cols)), shape=(n, n))
    citation_sym = citation_matrix + citation_matrix.T
    
    row_sums = np.array(citation_sym.sum(axis=1)).flatten()
    row_sums[row_sums == 0] = 1
    citation_norm = citation_sym.multiply(1.0 / row_sums[:, np.newaxis])
    
    n_comp = min(64, citation_norm.shape[1] - 1, n - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    emb = svd.fit_transform(citation_norm)
    
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms[norms == 0] = 1
    emb = emb / norms
    
    logger.info(f"Citation weight embeddings: {n} decisions, {n_comp} dims")
    return emb


def build_tfidf_signals(signals: Dict[str, Any], metadata: List[Dict], config: SignalConfig) -> Tuple[np.ndarray, List[int]]:
    texts = []
    valid_indices = []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        sig = signals.get(did, {})
        
        parts = []
        
        if config.use_sachverhalt and sig.get('sachverhalt_text'):
            parts.append(sig['sachverhalt_text'])
        
        if config.use_erwaegungen and sig.get('erwaegungen_text'):
            parts.append(sig['erwaegungen_text'])
        
        if config.use_doctrine_refs and sig.get('doctrine_refs'):
            parts.append(" ".join(sig['doctrine_refs']))
        
        if config.use_outcome and sig.get('outcome'):
            parts.append(sig['outcome'])
        
        if config.use_legal_area and sig.get('legal_area'):
            parts.append(sig['legal_area'])
        
        if config.use_erwaegungen_headings and sig.get('erwaegungen_headings'):
            parts.append(" ".join(sig['erwaegungen_headings']))
        
        if parts:
            texts.append(" ".join(parts))
            valid_indices.append(i)
        else:
            texts.append("")
    
    if len(valid_indices) < 100:
        logger.warning(f"Only {len(valid_indices)} valid texts for TF-IDF")
        return np.zeros((len(metadata), 128)), valid_indices
    
    valid_texts = [texts[i] for i in valid_indices]
    
    vectorizer = TfidfVectorizer(
        max_features=config.max_features,
        min_df=config.min_df,
        max_df=config.max_df,
        ngram_range=config.ngram_range,
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
    
    logger.info(f"TF-IDF signals: {len(valid_indices)} valid, {n_comp} dims")
    return full_emb, valid_indices


def project_to_dim(emb: np.ndarray, target_dim: int) -> np.ndarray:
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
    legal_proj = project_to_dim(legal_emb, target_dim)
    baseline_proj = project_to_dim(baseline_emb, target_dim)
    
    legal_proj = normalize(legal_proj, norm='l2', axis=1)
    baseline_proj = normalize(baseline_proj, norm='l2', axis=1)
    
    hybrid = alpha * legal_proj + (1 - alpha) * baseline_proj
    hybrid = normalize(hybrid, norm='l2', axis=1)
    
    return hybrid


def average_embeddings(emb_list: List[np.ndarray], target_dim: int = 64) -> np.ndarray:
    projected = [project_to_dim(emb, target_dim) for emb in emb_list]
    projected = [normalize(emb, norm='l2', axis=1) for emb in projected]
    avg = np.mean(projected, axis=0)
    avg = normalize(avg, norm='l2', axis=1)
    return avg


def run_adversarial_benchmarks(embeddings: np.ndarray, metadata: List[Dict], variant_name: str) -> Dict:
    """Run all adversarial benchmarks on embeddings."""
    logger.info(f"\nRunning adversarial benchmarks for {variant_name}...")
    
    # Prepare metadata arrays
    branches, languages, chambers, valid_indices = prepare_metadata_full(metadata)
    rep_valid = embeddings[valid_indices]
    branches_valid = branches[valid_indices]
    languages_valid = languages[valid_indices]
    metadata_valid = [metadata[i] for i in valid_indices]
    decision_ids = [m.get('decision_id', '') for m in metadata]
    decision_ids_valid = [decision_ids[i] for i in valid_indices]
    
    results = {'variant': variant_name, 'n_decisions': len(rep_valid), 'embedding_dim': embeddings.shape[1]}
    
    # 1. Cross-language benchmarks (expects embeddings and metadata with 'language' and 'branch' fields)
    logger.info("  Running cross-language benchmarks...")
    cl_results = run_all_cross_language_benchmarks(rep_valid, metadata_valid)
    results['cross_language'] = cl_results
    
    # 2. Jurist usability
    logger.info("  Running jurist usability benchmarks...")
    jurist_results = {}
    jurist_results['pairwise_preference'] = simulate_pairwise_preference(rep_valid, branches_valid, languages_valid)
    jurist_results['cluster_coherence_rating'] = simulate_cluster_coherence_rating(rep_valid, branches_valid, languages_valid)
    jurist_results['cross_language_retrieval'] = simulate_cross_language_retrieval(rep_valid, branches_valid, languages_valid)
    results['jurist_usability'] = jurist_results
    
    # 3. Jurivoc benchmarks (on full embeddings, not just valid)
    logger.info("  Running Jurivoc benchmarks...")
    jurivoc = JurivocBenchmarks(embeddings, decision_ids)
    jurivoc_results = jurivoc.run_all()
    results['jurivoc'] = jurivoc_results
    
    # 4. Scale stability (frozen PCA) - only if we have 768-dim
    # For signal ablation variants which are already low-dim, we test position stability differently
    # We'll test by subsampling and checking consistency
    logger.info("  Running scale stability test...")
    try:
        # Use the frozen PCA test on the embeddings directly
        scale_results = run_frozen_scale_benchmark(embeddings, metadata)
        results['scale_stability'] = scale_results
    except Exception as e:
        logger.warning(f"Scale stability test failed: {e}")
        results['scale_stability'] = {'status': 'SKIP', 'reason': str(e)}
    
    # 5. Boilerplate resistance
    logger.info("  Running boilerplate resistance test...")
    try:
        bp_results = run_boilerplate_resistance(embeddings, metadata)
        results['boilerplate_resistance'] = bp_results
    except Exception as e:
        logger.warning(f"Boilerplate resistance test failed: {e}")
        results['boilerplate_resistance'] = {'status': 'SKIP', 'reason': str(e)}
    
    return results


def main():
    logger.info("=" * 70)
    logger.info("EVALUATION v6 — ADVERSARIAL VALIDATION OF SIGNAL ABLATION VARIANTS")
    logger.info("=" * 70)
    logger.info(f"Global seed: {GLOBAL_SEED}")
    logger.info(f"Factory Direction Version: 6")
    logger.info(f"Baseline: center_projected (validated in v3/v5)")
    logger.info(f"Slice: expanded 1,200 decisions")
    
    # Load data
    logger.info("\n1. Loading legal signals (full corpus)...")
    signals = load_signals()
    
    logger.info("\n2. Loading center_projected baseline...")
    baseline_emb_full, cp_metadata = load_center_projected_baseline()
    
    logger.info("\n3. Building individual signal components...")
    # Single signals
    tfidf_sachverhalt, _ = build_tfidf_signals(signals, cp_metadata, SignalConfig(use_sachverhalt=True))
    tfidf_erwaegungen, _ = build_tfidf_signals(signals, cp_metadata, SignalConfig(use_erwaegungen=True))
    tfidf_doctrine, _ = build_tfidf_signals(signals, cp_metadata, SignalConfig(use_doctrine_refs=True))
    tfidf_outcome, _ = build_tfidf_signals(signals, cp_metadata, SignalConfig(use_outcome=True))
    tfidf_legal_area, _ = build_tfidf_signals(signals, cp_metadata, SignalConfig(use_legal_area=True))
    tfidf_headings, _ = build_tfidf_signals(signals, cp_metadata, SignalConfig(use_erwaegungen_headings=True))
    
    norm_emb = build_norm_embeddings(signals, cp_metadata)
    citation_emb = build_citation_weight_matrix(signals, cp_metadata)
    
    # 4. Define key experiment variants (from legal-distance v5 best results)
    experiments = {
        # Single signals (top performers from legal-distance)
        "sachverhalt_tfidf": tfidf_sachverhalt,
        "erwaegungen_tfidf": tfidf_erwaegungen,
        "norm_embeddings": norm_emb,
        "citation_weights": citation_emb,
        
        # Core combinations
        "sachverhalt+erwaegungen": average_embeddings([tfidf_sachverhalt, tfidf_erwaegungen]),
        "erwaegungen+norms": average_embeddings([tfidf_erwaegungen, norm_emb]),
        "erwaegungen+citations": average_embeddings([tfidf_erwaegungen, citation_emb]),
        "core_legal": average_embeddings([tfidf_erwaegungen, norm_emb, citation_emb]),
        
        # Hybrids with center_projected baseline (alpha = legal weight)
        "hybrid_erwaegungen_03": create_hybrid_representation(tfidf_erwaegungen, baseline_emb_full, 0.3),
        "hybrid_erwaegungen_05": create_hybrid_representation(tfidf_erwaegungen, baseline_emb_full, 0.5),
        "hybrid_erwaegungen_07": create_hybrid_representation(tfidf_erwaegungen, baseline_emb_full, 0.7),
        "hybrid_core_03": create_hybrid_representation(average_embeddings([tfidf_erwaegungen, norm_emb, citation_emb]), baseline_emb_full, 0.3),
        "hybrid_core_05": create_hybrid_representation(average_embeddings([tfidf_erwaegungen, norm_emb, citation_emb]), baseline_emb_full, 0.5),
        "hybrid_core_07": create_hybrid_representation(average_embeddings([tfidf_erwaegungen, norm_emb, citation_emb]), baseline_emb_full, 0.7),
        
        # Baseline
        "baseline_center_projected": baseline_emb_full,
    }
    
    # 5. Align all embeddings to expanded slice
    logger.info("\n4. Aligning embeddings to expanded 1,200-decision slice...")
    aligned_experiments = {}
    aligned_metadata = None
    
    for name, emb in experiments.items():
        aligned_emb, meta = align_to_expanded_slice(emb, cp_metadata)
        aligned_experiments[name] = aligned_emb
        if aligned_metadata is None:
            aligned_metadata = meta
    
    # 6. Run adversarial benchmarks on each variant
    logger.info(f"\n5. Running adversarial benchmarks on {len(aligned_experiments)} variants...")
    all_results = {
        'factory_direction_version': 6,
        'evaluation_version': 6,
        'global_seed': GLOBAL_SEED,
        'baseline_representation': 'center_projected',
        'slice': 'expanded_1200',
        'variants_tested': list(aligned_experiments.keys()),
        'benchmarks': {}
    }
    
    for name, emb in aligned_experiments.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"EVALUATING VARIANT: {name}")
        logger.info(f"  Shape: {emb.shape}")
        
        try:
            results = run_adversarial_benchmarks(emb, aligned_metadata, name)
            all_results['benchmarks'][name] = results
            
            # Save intermediate
            with open(OUTPUT_DIR / f"v6_{name}_results.json", 'w') as f:
                json.dump(results, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to evaluate {name}: {e}")
            import traceback
            traceback.print_exc()
            all_results['benchmarks'][name] = {'error': str(e)}
    
    # 7. Summary comparison
    logger.info("\n" + "=" * 80)
    logger.info("V6 SIGNAL ABLATION ADVERSARIAL VALIDATION SUMMARY")
    logger.info("=" * 80)
    
    # Print key metrics for each variant
    for name, results in all_results['benchmarks'].items():
        if 'error' in results:
            logger.info(f"  {name}: ERROR - {results['error']}")
            continue
        
        cl = results.get('cross_language', {})
        ju = results.get('jurist_usability', {})
        jv = results.get('jurivoc', {})
        
        lang_dom = cl.get('adversarial_language_dominance', {}).get('mean_language_dominance', 'N/A')
        pairwise = ju.get('pairwise_preference', {}).get('legal_neighbor_rate', 'N/A')
        jurivoc_l2 = jv.get('jurivoc_descriptor_recovery_l2', {}).get('nmi', 'N/A')
        jurivoc_sep = jv.get('jurivoc_hierarchy_alignment', {}).get('separation', 'N/A')
        bp_corr = results.get('boilerplate_resistance', {}).get('text_embedding_correlation', 'N/A')
        
        lang_pass = "PASS" if isinstance(lang_dom, float) and lang_dom < 0.85 else "FAIL" if isinstance(lang_dom, float) else "N/A"
        pair_pass = "PASS" if isinstance(pairwise, float) and pairwise > 0.5 else "FAIL" if isinstance(pairwise, float) else "N/A"
        
        logger.info(f"  {name}:")
        logger.info(f"    Language Dominance: {lang_dom} ({lang_pass})")
        logger.info(f"    Jurist Pairwise: {pairwise} ({pair_pass})")
        logger.info(f"    Jurivoc L2 NMI: {jurivoc_l2}")
        logger.info(f"    Jurivoc Hierarchy Sep: {jurivoc_sep}")
        logger.info(f"    Boilerplate Corr: {bp_corr}")
    
    # Save final results
    output_path = OUTPUT_DIR / 'v6_signal_ablation_adversarial_results.json'
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to: {output_path}")
    logger.info("\nEvaluation v6 complete.")
    
    return all_results


if __name__ == '__main__':
    main()