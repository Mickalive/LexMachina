#!/usr/bin/env python3
"""
Legal Distance Lane v6 - Adversarial Validation of Signal Ablation Hybrids

Factory Direction v6 requirement: Test signal ablation hybrids (legal_issues_outcomes, 
legal_area_tfidf, hybrid_erwaegungen_03) against the two critical adversarial gates:
1. adversarial_language_dominance < 0.85
2. jurist_pairwise_preference > 0.5

These hybrids showed promise in fractal-map harness (NMI, fine purity) but have NOT
been tested against the adversarial benchmarks that validate multilingual robustness
and jurist-useful neighbor structure.
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score
from sklearn.cluster import KMeans

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
SIGNAL_EMBEDDINGS_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/signal_ablation_embeddings")
CENTER_PROJECTED_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v5/center_projected_full")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results/v6/adversarial_signal_validation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Metadata loading
def load_evaluation_metadata() -> List[Dict]:
    """Load metadata from fractal-map baseline (1000 decisions)."""
    metadata_path = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json")
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
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
    
    for meta in metadata:
        chamber = meta.get("chamber", "")
        meta['branch'] = assign_branch(chamber)
        if 'language' not in meta:
            meta['language'] = meta.get('language', 'de')
    
    return metadata

def prepare_metadata(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
    """Extract branch, language, chamber from metadata."""
    branches = []
    languages = []
    chambers = []
    valid_indices = []
    
    for i, meta in enumerate(metadata):
        chamber = meta.get("chamber", "")
        branch = meta.get("branch", "unknown")
        lang = meta.get("language", "unknown")
        
        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            chambers.append(chamber)
            valid_indices.append(i)
    
    return np.array(branches), np.array(languages), np.array(chambers), valid_indices

# Adversarial benchmarks (copied from evaluation modules for reproducibility)

def adversarial_language_dominance(embeddings: np.ndarray, metadata: List[Dict], k: int = 20) -> Dict:
    """
    Adversarial test: measure language dominance in nearest neighbors.
    Language dominance = fraction of k-NN that share the same language.
    Should be LOW (not dominated by language).
    """
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
    """
    Simulate jurist pairwise preference study.
    
    A jurist is shown a decision and two neighbor candidates:
    - Candidate A: Same branch, different language (legally relevant)
    - Candidate B: Same language, different branch (language artifact)
    
    The jurist should prefer Candidate A. We measure how often
    the embedding space presents Candidate A vs B in top-k.
    """
    n = len(branches)
    
    # Build NN graph
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]  # Exclude self
    
    # For each decision, count same-branch-diff-lang vs same-lang-diff-branch in top-k
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
    
    # Simulated jurist preference: would choose legal-relevant if available
    # If both available, jurist picks legal-relevant (correct)
    # If only language artifact available, jurist is forced to pick it (wrong)
    jurist_correct = legal_relevant_count + both_count
    jurist_forced_wrong = language_artifact_count
    jurist_no_choice = neither_count
    
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

def run_adversarial_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run the two critical adversarial benchmarks."""
    # Prepare metadata
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    rep_valid = embeddings[valid_indices]
    meta_valid = [metadata[i] for i in valid_indices]
    
    # 1. Adversarial language dominance
    lang_dom = adversarial_language_dominance(rep_valid, meta_valid)
    
    # 2. Jurist pairwise preference
    jurist_pref = simulate_pairwise_preference(rep_valid, branches, languages)
    
    return {
        'adversarial_language_dominance': lang_dom,
        'jurist_pairwise_preference': jurist_pref,
        'both_pass': lang_dom.get('status') == 'PASS' and jurist_pref.get('status') == 'PASS',
        'language_dominance_score': lang_dom.get('mean_language_dominance', 1.0),
        'jurist_preference_rate': jurist_pref.get('jurist_would_succeed_rate', 0.0),
    }

def load_embeddings(embedding_dir: Path, names: List[str]) -> Dict[str, np.ndarray]:
    """Load specified embeddings from directory."""
    embeddings = {}
    for name in names:
        path = embedding_dir / f"{name}.npy"
        if path.exists():
            embeddings[name] = np.load(path)
            logger.info(f"Loaded {name}: {embeddings[name].shape}")
        else:
            logger.warning(f"Embedding not found: {path}")
    return embeddings

def main():
    logger.info("=" * 70)
    logger.info("Legal Distance v6 - Adversarial Validation of Signal Ablation Hybrids")
    logger.info("Testing against: language_dominance < 0.85, jurist_preference > 0.5")
    logger.info("=" * 70)
    
    # Load metadata
    logger.info("\n1. Loading evaluation metadata...")
    metadata = load_evaluation_metadata()
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    
    # Load center_projected baseline (reference)
    logger.info("\n2. Loading center_projected baseline...")
    cp_path = CENTER_PROJECTED_DIR / "embeddings_center_projected.npy"
    cp_metadata_path = CENTER_PROJECTED_DIR / "metadata.json"
    with open(cp_metadata_path) as f:
        cp_metadata = json.load(f)
    
    center_projected = np.load(cp_path)
    # Align to evaluation metadata (1000 decisions)
    cp_by_id = {m['decision_id']: i for i, m in enumerate(cp_metadata)}
    eval_ids = [m['decision_id'] for m in metadata]
    valid_ids = [did for did in eval_ids if did in cp_by_id]
    valid_cp_indices = [cp_by_id[did] for did in valid_ids]
    center_projected_aligned = center_projected[valid_cp_indices]
    metadata_aligned = [m for m in metadata if m['decision_id'] in cp_by_id]
    
    logger.info(f"Center projected aligned: {center_projected_aligned.shape}")
    logger.info(f"Metadata aligned: {len(metadata_aligned)} decisions")
    
    # Load signal ablation embeddings
    logger.info("\n3. Loading signal ablation embeddings...")
    
    # Key signal embeddings to test (from v4/v5 results)
    signal_names = [
        'signal_sachverhalt_tfidf',
        'signal_erwaegungen_tfidf',
        'signal_legal_area_tfidf',
        'signal_legal_issues_tfidf',
        'signal_outcome_tfidf',
        'signal_headings_tfidf',
        'signal_norm_embeddings',
        'signal_cited_decisions_tfidf',
        'signal_erwaegungen+citations',
        'signal_sachverhalt+erwaegungen',
        'signal_sachverhalt+norms',
        'signal_erwaegungen+norms',
        'signal_erwaegungen+doctrine',
        'signal_legal_issues_outcomes',
    ]
    
    hybrid_names = [
        'hybrid_erwaegungen_0.3',
        'hybrid_erwaegungen_0.5',
        'hybrid_erwaegungen_0.7',
        'hybrid_sachverhalt_0.3',
        'hybrid_sachverhalt_0.5',
        'hybrid_sachverhalt_0.7',
        'hybrid_norm_refs_0.3',
        'hybrid_norm_refs_0.5',
        'hybrid_norm_refs_0.7',
        'hybrid_legal_area_0.3',
        'hybrid_legal_area_0.5',
        'hybrid_legal_area_0.7',
        'hybrid_cited_decisions_0.3',
        'hybrid_cited_decisions_0.5',
        'hybrid_cited_decisions_0.7',
    ]
    
    signal_embeddings = load_embeddings(SIGNAL_EMBEDDINGS_DIR, signal_names)
    hybrid_embeddings = load_embeddings(SIGNAL_EMBEDDINGS_DIR, hybrid_names)
    
    # Also load baseline
    baseline_embeddings = load_embeddings(SIGNAL_EMBEDDINGS_DIR, ['baseline_center_projected'])
    
    all_embeddings = {}
    all_embeddings.update(signal_embeddings)
    all_embeddings.update(hybrid_embeddings)
    all_embeddings.update(baseline_embeddings)
    all_embeddings['center_projected_reference'] = center_projected_aligned
    
    logger.info(f"\nTotal embeddings loaded: {len(all_embeddings)}")
    
    # Run adversarial benchmarks on each
    logger.info("\n4. Running adversarial benchmarks...")
    all_results = {}
    
    for name, embeddings in all_embeddings.items():
        logger.info(f"\n--- Evaluating {name} ---")
        try:
            # Align embeddings to metadata
            if embeddings.shape[0] != len(metadata_aligned):
                # Try to align by truncating or warn
                if embeddings.shape[0] > len(metadata_aligned):
                    embeddings = embeddings[:len(metadata_aligned)]
                    logger.warning(f"  Truncated {name} from {embeddings.shape[0]} to {len(metadata_aligned)}")
                else:
                    logger.warning(f"  {name}: shape mismatch ({embeddings.shape[0]} vs {len(metadata_aligned)}), skipping")
                    continue
            
            results = run_adversarial_benchmarks(embeddings, metadata_aligned)
            results['embedding_shape'] = list(embeddings.shape)
            all_results[name] = results
            
            adv = results['adversarial_language_dominance']
            jp = results['jurist_pairwise_preference']
            logger.info(f"  Language Dominance: {adv['mean_language_dominance']:.4f} ({adv['status']})")
            logger.info(f"  Jurist Preference: {jp['jurist_would_succeed_rate']:.4f} ({jp['status']})")
            logger.info(f"  BOTH PASS: {results['both_pass']}")
            
        except Exception as e:
            logger.error(f"  ERROR evaluating {name}: {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {'error': str(e)}
    
    # Save results
    output_file = OUTPUT_DIR / "adversarial_signal_validation_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("ADVERSARIAL VALIDATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"{'Representation':<40} {'LangDom':>8} {'LD-Stat':>6} {'Jurist':>8} {'JP-Stat':>6} {'Both':>5}")
    logger.info("-" * 80)
    
    # Sort by both_pass, then jurist preference, then language dominance
    def sort_key(item):
        name, res = item
        if 'error' in res:
            return (0, 0, 1.0)
        both = res['both_pass']
        jurist = res['jurist_preference_rate']
        lang_dom = res['language_dominance_score']
        return (both, jurist, -lang_dom)
    
    sorted_results = sorted(all_results.items(), key=sort_key, reverse=True)
    
    for name, res in sorted_results:
        if 'error' in res:
            logger.info(f"{name:<40} {'ERROR':>8} {'N/A':>6} {'ERROR':>8} {'N/A':>6} {'N/A':>5}")
            continue
        
        ld = res['language_dominance_score']
        jp = res['jurist_preference_rate']
        ld_status = "✓" if res['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_status = "✓" if res['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if res['both_pass'] else "✗"
        
        logger.info(f"{name:<40} {ld:>8.4f} {ld_status:>6} {jp:>8.4f} {jp_status:>6} {both:>5}")
    
    # Find best representation
    valid_results = {k: v for k, v in all_results.items() if 'error' not in v}
    if valid_results:
        best = max(valid_results.items(), key=lambda x: (x[1]['both_pass'], 
                                                          x[1]['jurist_preference_rate'],
                                                          -x[1]['language_dominance_score']))
        logger.info(f"\n🏆 BEST REPRESENTATION: {best[0]}")
        logger.info(f"   Both adversarial pass: {best[1]['both_pass']}")
        logger.info(f"   Language dominance: {best[1]['language_dominance_score']:.4f}")
        logger.info(f"   Jurist preference: {best[1]['jurist_preference_rate']:.4f}")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 80)
    
    return all_results

if __name__ == "__main__":
    main()
