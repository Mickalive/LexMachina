#!/usr/bin/env python3
"""
Legal Distance Lane v6 - Comprehensive Evaluation Against Refined Benchmark Suite

Tests ALL available representations against the 16-benchmark refined suite with
focus on the two critical adversarial gates:
1. adversarial_language_dominance < 0.85
2. jurist_pairwise_preference > 0.5

Representations tested:
- center_projected (baseline reference)
- Signal ablation variants (v4) on center_projected
- Scale test variants (v5) on center_projected
- Citation role hybrids (v6 rebuilt)
- Pre-trained legal embeddings (xlm-roberta-base, paraphrase-multilingual-minilm)
- multilingual-e5-small pre-trained (fine-tuning blocked by GPU)
"""

import json
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, Counter
import sys
import time
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score
from sklearn.cluster import KMeans

# Add paths for local modules
sys.path.insert(0, '/tmp/lex_accepted/fractal-map/fractal_map/hierarchical')
from hierarchical_leiden import hierarchical_leiden, compute_branch_purity

def compute_branch_purity_per_cluster(labels, metadata):
    """Compute branch purity per cluster."""
    from collections import Counter
    unique_labels = np.unique(labels[labels != -1])
    purities = {}
    
    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        
        if cluster_branches:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            purities[int(label)] = most_common / len(cluster_branches)
    
    return purities

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_RESULTS = Path("/home/runner/work/LexMachina/LexMachina/legal_distance/results")
OUTPUT_DIR = BASE_RESULTS / "v6_comprehensive_evaluation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# COPIED FUNCTIONS FROM EVALUATION MODULES (to avoid import issues)
# ============================================================

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

def load_evaluation_metadata() -> List[Dict]:
    """Load metadata from fractal-map baseline."""
    metadata_path = Path("/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json")
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
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
        branch = assign_branch(chamber)
        lang = meta.get("language", "unknown")
        
        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            chambers.append(chamber)
            valid_indices.append(i)
    
    return np.array(branches), np.array(languages), np.array(chambers), valid_indices

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

def simulate_cluster_coherence_rating(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    n_clusters: int = 16
) -> Dict:
    """
    Simulate jurist cluster coherence rating.
    
    A jurist is shown the top-5 decisions from each cluster and asked:
    "Do these decisions share a coherent legal theme?"
    
    We proxy this by measuring branch purity and Jurivoc alignment of clusters.
    """
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(embeddings)
    
    # Compute branch purity per cluster
    cluster_purities = []
    cluster_sizes = []
    cluster_branch_dist = {}
    
    for c in range(n_clusters):
        mask = cluster_labels == c
        if np.sum(mask) == 0:
            continue
        cluster_branches = branches[mask]
        majority = Counter(cluster_branches).most_common(1)[0][0]
        purity = np.mean(cluster_branches == majority)
        cluster_purities.append(purity)
        cluster_sizes.append(int(np.sum(mask)))
        cluster_branch_dist[c] = dict(Counter(cluster_branches))
    
    mean_purity = np.mean(cluster_purities)
    
    # NMI with branch labels
    nmi = normalized_mutual_info_score(branches, cluster_labels)
    
    # Language purity (should be high if language dominates)
    lang_purities = []
    for c in range(n_clusters):
        mask = cluster_labels == c
        if np.sum(mask) == 0:
            continue
        cluster_langs = languages[mask]
        majority = Counter(cluster_langs).most_common(1)[0][0]
        purity = np.mean(cluster_langs == majority)
        lang_purities.append(purity)
    
    mean_lang_purity = np.mean(lang_purities)
    
    return {
        "status": "PASS" if mean_purity > 0.7 else "FAIL",
        "n_clusters": n_clusters,
        "mean_branch_purity": round(float(mean_purity), 4),
        "branch_nmi": round(float(nmi), 4),
        "mean_language_purity": round(float(mean_lang_purity), 4),
        "cluster_purities": [round(p, 4) for p in cluster_purities],
        "cluster_sizes": cluster_sizes,
        "note": "Simulated jurist rates clusters by branch coherence. High branch purity = legally coherent clusters. High language purity = language-dominated clusters."
    }

def simulate_cross_language_retrieval(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    k: int = 10
) -> Dict:
    """
    Simulate jurist cross-language retrieval task.
    
    A jurist has a German decision and wants to find related French decisions.
    We measure the cross-language same-branch recall in top-k.
    """
    from collections import Counter
    
    # Group by branch and language
    branch_lang_groups = {}
    for i in range(len(branches)):
        key = (branches[i], languages[i])
        if key not in branch_lang_groups:
            branch_lang_groups[key] = []
        branch_lang_groups[key].append(i)
    
    # Build NN graph
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    # For each decision, measure cross-language same-branch recall
    cross_lang_recall_rates = []
    
    for i in range(len(branches)):
        branch = branches[i]
        lang = languages[i]
        
        # Find all same-branch different-language decisions (ground truth)
        cross_lang_gt = []
        for other_lang in ['de', 'fr', 'it']:
            if other_lang != lang:
                key = (branch, other_lang)
                if key in branch_lang_groups:
                    cross_lang_gt.extend(branch_lang_groups[key])
        
        if not cross_lang_gt:
            continue
        
        # Check how many appear in top-k
        neighbor_set = set(neighbors[i])
        found = sum(1 for gt in cross_lang_gt if gt in neighbor_set)
        recall = found / min(len(cross_lang_gt), k)
        cross_lang_recall_rates.append(recall)
    
    mean_recall = np.mean(cross_lang_recall_rates) if cross_lang_recall_rates else 0
    
    return {
        "status": "PASS" if mean_recall > 0.2 else "FAIL",
        "mean_cross_language_recall_at_k": round(float(mean_recall), 4),
        "k": k,
        "n_queries": len(cross_lang_recall_rates),
        "note": "Simulated jurist searches for cross-language legal equivalents. Recall > 0.2 means at least 1 in 5 cross-language legal equivalents appears in top-10."
    }

# ============================================================
# END OF COPIED FUNCTIONS
# ============================================================

def load_all_representations() -> Dict[str, np.ndarray]:
    """Load all available embedding representations."""
    representations = {}
    
    # 1. center_projected (baseline reference) - from v5/center_projected_full
    cp_path = BASE_RESULTS / "v5/center_projected_full/embeddings_center_projected.npy"
    if cp_path.exists():
        representations['center_projected'] = np.load(cp_path)
        logger.info(f"Loaded center_projected: {representations['center_projected'].shape}")
    
    # 2. Signal ablation embeddings (v4) - from v5/signal_ablation_embeddings
    signal_emb_dir = BASE_RESULTS / "v5/signal_ablation_embeddings"
    if signal_emb_dir.exists():
        for f in signal_emb_dir.glob("embeddings_*.npy"):
            name = f.stem.replace("embeddings_", "signal_")
            representations[name] = np.load(f)
            logger.info(f"Loaded {name}: {representations[name].shape}")
    
    # 3. Scale test embeddings - from v5/scale_test
    scale_emb_dir = BASE_RESULTS / "v5/scale_test"
    if scale_emb_dir.exists():
        for f in scale_emb_dir.glob("scale_*_embeddings.npy"):
            name = f.stem.replace("scale_", "scale_").replace("_embeddings", "")
            representations[name] = np.load(f)
            logger.info(f"Loaded {name}: {representations[name].shape}")
    
    # 4. Citation role embeddings (v6 rebuilt) - from v6/citation_roles_rebuilt
    cite_emb_dir = BASE_RESULTS / "v6/citation_roles_rebuilt"
    if cite_emb_dir.exists():
        for f in cite_emb_dir.glob("citation_role_*_rebuilt.npy"):
            name = f.stem.replace("citation_role_", "cite_").replace("_rebuilt", "")
            representations[name] = np.load(f)
            logger.info(f"Loaded {name}: {representations[name].shape}")
    
    # 5. Legal embeddings (v5) - from v5/legal_embeddings
    legal_emb_dir = BASE_RESULTS / "v5/legal_embeddings"
    if legal_emb_dir.exists():
        for f in legal_emb_dir.glob("embeddings_*.npy"):
            name = f.stem.replace("embeddings_", "legal_")
            representations[name] = np.load(f)
            logger.info(f"Loaded {name}: {representations[name].shape}")
    
    # 6. Finetune multilingual-e5 (v6) - from v6/finetune_multilingual_e5
    finetune_dir = BASE_RESULTS / "v6/finetune_multilingual_e5"
    if finetune_dir.exists():
        for f in finetune_dir.glob("embeddings_*.npy"):
            name = f.stem.replace("embeddings_", "ft_")
            representations[name] = np.load(f)
            logger.info(f"Loaded {name}: {representations[name].shape}")
    
    return representations

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

def run_fractal_quality_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Run fractal-map quality benchmarks (hierarchical Leiden, zoom coherence)."""
    # Align embeddings with metadata length
    n_metadata = len(metadata)
    if embeddings.shape[0] != n_metadata:
        # Truncate or pad embeddings to match metadata
        if embeddings.shape[0] > n_metadata:
            embeddings = embeddings[:n_metadata]
        else:
            # This shouldn't happen but handle gracefully
            logger.warning(f"Embeddings ({embeddings.shape[0]}) < metadata ({n_metadata}), skipping fractal benchmarks")
            return {
                'n_coarse': 0,
                'n_fine': 0,
                'coarse_purity': 0.0,
                'fine_purity': 0.0,
                'overall_improvement': 0.0,
                'improvement_rate': 0.0,
                'legal_area_nmi': 0.0,
                'flat_purity': 0.0,
                'hierarchical_advantage': 0.0,
                'cluster_coherence': {'status': 'SKIP', 'note': 'embedding/metadata length mismatch'},
                'cross_language_retrieval': {'status': 'SKIP', 'note': 'embedding/metadata length mismatch'},
            }
    
    # Run hierarchical Leiden
    result = hierarchical_leiden(
        embeddings, metadata, coarse_res=0.5, sub_res=3.0
    )
    hierarchical_labels, coarse_labels, cluster_info = result
    
    # Build coarse_to_fine mapping from cluster_info
    coarse_to_fine = defaultdict(list)
    for sub_id, info in cluster_info.items():
        if not info.get('too_small', False):
            coarse_id = info['coarse_id']
            coarse_to_fine[coarse_id].append(sub_id)
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    
    coarse_purities = compute_branch_purity_per_cluster(coarse_labels, metadata)
    coarse_overall = compute_branch_purity(coarse_labels, metadata)
    
    fine_purities = compute_branch_purity_per_cluster(hierarchical_labels, metadata)
    fine_overall = compute_branch_purity(hierarchical_labels, metadata)
    
    total_improvements = 0
    total_deteriorations = 0
    total_no_change = 0
    
    for coarse_id in sorted(coarse_to_fine.keys()):
        fine_ids = coarse_to_fine[coarse_id]
        if not fine_ids:
            continue
        coarse_pur = coarse_purities.get(coarse_id, 0)
        fine_purs = [fine_purities.get(fid, 0) for fid in fine_ids]
        improvements = sum(1 for fp in fine_purs if fp > coarse_pur + 0.01)
        deteriorations = sum(1 for fp in fine_purs if fp < coarse_pur - 0.01)
        no_change = len(fine_purs) - improvements - deteriorations
        total_improvements += improvements
        total_deteriorations += deteriorations
        total_no_change += no_change
    
    overall_improvement = fine_overall - coarse_overall
    total_fine = total_improvements + total_deteriorations + total_no_change
    improvement_rate = total_improvements / total_fine if total_fine > 0 else 0
    
    # Legal area NMI
    legal_areas = [metadata[i].get('legal_area', '') for i in range(len(metadata))]
    legal_areas = [la if la else 'unknown' for la in legal_areas]
    nmi = normalized_mutual_info_score(legal_areas, hierarchical_labels)
    
    # Flat Leiden comparison - use the same function but with different resolutions
    flat_result = hierarchical_leiden(embeddings, metadata, coarse_res=3.0, sub_res=0.5)
    flat_labels = flat_result[0]
    flat_purity = compute_branch_purity(flat_labels, metadata)
    hierarchical_advantage = fine_overall - flat_purity
    
    # Jurist cluster coherence
    branches_arr = np.array([m.get('branch', 'unknown') for m in metadata])
    languages_arr = np.array([m.get('language', 'unknown') for m in metadata])
    cluster_coherence = simulate_cluster_coherence_rating(embeddings, branches_arr, languages_arr, n_clusters=16)
    
    # Cross-language retrieval
    cross_lang = simulate_cross_language_retrieval(embeddings, branches_arr, languages_arr)
    
    return {
        'n_coarse': n_coarse,
        'n_fine': n_fine,
        'coarse_purity': float(coarse_overall),
        'fine_purity': float(fine_overall),
        'overall_improvement': float(overall_improvement),
        'improvement_rate': float(improvement_rate),
        'legal_area_nmi': float(nmi),
        'flat_purity': float(flat_purity),
        'hierarchical_advantage': float(hierarchical_advantage),
        'cluster_coherence': cluster_coherence,
        'cross_language_retrieval': cross_lang,
    }

def evaluate_representation(name: str, embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Any]:
    """Evaluate a single representation against all benchmarks."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating: {name}")
    logger.info(f"Shape: {embeddings.shape}")
    logger.info(f"{'='*60}")
    
    start_time = time.time()
    
    # Adversarial benchmarks
    logger.info("Running adversarial benchmarks...")
    adv_results = run_adversarial_benchmarks(embeddings, metadata)
    
    # Fractal quality benchmarks
    logger.info("Running fractal quality benchmarks...")
    fractal_results = run_fractal_quality_benchmarks(embeddings, metadata)
    
    duration = time.time() - start_time
    
    # Overall verdict
    both_pass = adv_results['both_pass']
    verdict = "PASS" if both_pass else "FAIL"
    
    return {
        'name': name,
        'embedding_shape': list(embeddings.shape),
        'duration_seconds': duration,
        'adversarial': adv_results,
        'fractal': fractal_results,
        'verdict': verdict,
        'both_adversarial_pass': both_pass,
    }

def main():
    logger.info("=" * 70)
    logger.info("Legal Distance Lane v6 - Comprehensive Evaluation")
    logger.info("Testing ALL representations against refined benchmark suite")
    logger.info("=" * 70)
    
    # Load metadata
    logger.info("\n1. Loading evaluation metadata...")
    metadata = load_evaluation_metadata()
    logger.info(f"Loaded metadata for {len(metadata)} decisions")
    
    # Load all representations
    logger.info("\n2. Loading all representations...")
    representations = load_all_representations()
    logger.info(f"Loaded {len(representations)} representations")
    
    # Evaluate each representation
    logger.info("\n3. Running evaluations...")
    all_results = {}
    
    for name, embeddings in representations.items():
        try:
            result = evaluate_representation(name, embeddings, metadata)
            all_results[name] = result
            
            # Log summary
            adv = result['adversarial']
            frac = result['fractal']
            logger.info(f"  {name}: verdict={result['verdict']}, "
                       f"lang_dom={adv['language_dominance_score']:.4f} "
                       f"({'PASS' if adv['adversarial_language_dominance']['status']=='PASS' else 'FAIL'}), "
                       f"jurist_pref={adv['jurist_preference_rate']:.4f} "
                       f"({'PASS' if adv['jurist_pairwise_preference']['status']=='PASS' else 'FAIL'}), "
                       f"improvement_rate={frac['improvement_rate']:.2%}, "
                       f"legal_area_nmi={frac['legal_area_nmi']:.4f}")
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            import traceback
            traceback.print_exc()
            all_results[name] = {
                'name': name,
                'error': str(e),
                'verdict': 'ERROR'
            }
    
    # Save all results
    output_file = OUTPUT_DIR / "comprehensive_evaluation_results.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Generate summary report
    logger.info("\n" + "=" * 80)
    logger.info("COMPREHENSIVE EVALUATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"{'Representation':<45} {'Verdict':<8} {'LangDom':>8} {'LangP':>5} {'Jurist':>8} {'JurP':>5} {'Both':>5} {'ImpRate':>8} {'NMI':>6} {'HAdv':>6}")
    logger.info("-" * 80)
    
    # Sort by adversarial pass, then jurist preference, then language dominance
    def sort_key(item):
        name, res = item
        if 'error' in res:
            return (0, 0, 1.0, 0.0)
        both = res['both_adversarial_pass']
        jurist = res['adversarial']['jurist_preference_rate']
        lang_dom = res['adversarial']['language_dominance_score']
        return (both, jurist, -lang_dom, res['fractal'].get('improvement_rate', 0))
    
    sorted_results = sorted(all_results.items(), key=sort_key, reverse=True)
    
    for name, res in sorted_results:
        if 'error' in res:
            logger.info(f"{name:<45} {'ERROR':<8} {'N/A':>8} {'N/A':>5} {'N/A':>8} {'N/A':>5} {'N/A':>5} {'N/A':>8} {'N/A':>6} {'N/A':>6}")
            continue
        
        adv = res['adversarial']
        frac = res['fractal']
        ld = adv['language_dominance_score']
        jp = adv['jurist_preference_rate']
        ld_pass = "✓" if adv['adversarial_language_dominance']['status'] == 'PASS' else "✗"
        jp_pass = "✓" if adv['jurist_pairwise_preference']['status'] == 'PASS' else "✗"
        both = "✓" if adv['both_pass'] else "✗"
        
        logger.info(f"{name:<45} {res['verdict']:<8} {ld:>8.4f} {ld_pass:>5} {jp:>8.4f} {jp_pass:>5} {both:>5} "
                   f"{frac.get('improvement_rate', 0):>7.1%} {frac.get('legal_area_nmi', 0):>6.4f} "
                   f"{frac.get('hierarchical_advantage', 0):>6.4f}")
    
    # Find best representation
    valid_results = {k: v for k, v in all_results.items() if 'error' not in v}
    if valid_results:
        best = max(valid_results.items(), key=lambda x: (x[1]['both_adversarial_pass'], 
                                                          x[1]['adversarial']['jurist_preference_rate'],
                                                          -x[1]['adversarial']['language_dominance_score']))
        logger.info(f"\n🏆 BEST REPRESENTATION: {best[0]}")
        logger.info(f"   Both adversarial pass: {best[1]['both_adversarial_pass']}")
        logger.info(f"   Language dominance: {best[1]['adversarial']['language_dominance_score']:.4f}")
        logger.info(f"   Jurist preference: {best[1]['adversarial']['jurist_preference_rate']:.4f}")
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 80)
    
    return all_results

if __name__ == "__main__":
    main()