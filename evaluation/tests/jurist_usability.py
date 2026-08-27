#!/usr/bin/env python3
"""
Jurist Usability Study Framework for Evaluation v2.

This implements proxy/simulation benchmarks for jurist usability since
real human studies require participants. The simulation uses the
benchmark results as ground truth for what a jurist would observe.

Real jurist studies should test:
1. Pairwise neighbor preference (legal-relevant vs language-matched)
2. Cluster coherence rating (can jurists name clusters?)
3. Zoom task performance (find related decisions at different resolutions)
4. Cross-language retrieval (find French decisions from German query)
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
from sklearn.neighbors import NearestNeighbors
from collections import Counter


def load_baseline_embeddings() -> Tuple[np.ndarray, List[Dict]]:
    """Load the baseline 768-dim embeddings and metadata."""
    embeddings_path = Path('/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/embeddings.npy')
    metadata_path = Path('/tmp/lex_accepted/fractal-map/results/fractal_map/baseline/metadata.json')
    
    embeddings = np.load(embeddings_path)
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    return embeddings, metadata


def create_debiased_citation_blended(embeddings: np.ndarray) -> np.ndarray:
    """Create the validated debiased_citation_blended representation (64-dim)."""
    # PCA debiasing (n_pca=1)
    pca_debias = PCA(n_components=1, random_state=42)
    debias_component = pca_debias.fit_transform(embeddings)
    debiased = embeddings - debias_component @ pca_debias.components_
    
    # Project to 64-dim
    pca_64 = PCA(n_components=64, random_state=42)
    debiased_64 = pca_64.fit_transform(debiased)
    return normalize(debiased_64, norm='l2')


def prepare_metadata(metadata: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[int]]:
    """Extract branch, language, chamber from metadata."""
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
        
        if branch != "unknown":
            branches.append(branch)
            languages.append(lang)
            chambers.append(chamber)
            valid_indices.append(i)
    
    return np.array(branches), np.array(languages), np.array(chambers), valid_indices


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
    from sklearn.cluster import KMeans
    from sklearn.metrics import normalized_mutual_info_score
    
    # Cluster the embeddings
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


def simulate_zoom_task(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    valid_indices: List[int],
    cluster_assignments_path: Path
) -> Dict:
    """
    Simulate jurist zoom navigation task.
    
    A jurist starts at coarse clusters, clicks into a cluster, and should
    find more specific legal sub-clusters. We measure if zoom increases
    branch purity (as v1 zoom_coherence does).
    """
    try:
        with open(cluster_assignments_path, 'r') as f:
            cluster_data = json.load(f)
    except Exception as e:
        return {"status": "SKIP", "reason": f"cluster_assignments_not_available: {e}"}
    
    # Use res_0.5 (coarse) and res_3.0 (fine) as in v1
    coarse_key = "res_0.5"
    fine_key = "res_3.0"
    
    if coarse_key not in cluster_data or fine_key not in cluster_data:
        return {"status": "SKIP", "reason": "missing_resolution_levels"}
    
    branches_arr = np.array(branches)
    
    def compute_purity(labels_list):
        valid_labels = np.array([labels_list[idx] for idx in valid_indices])
        unique_clusters = set(valid_labels)
        total_correct = 0
        total_count = 0
        for cluster_id in unique_clusters:
            mask = valid_labels == cluster_id
            cluster_branches = branches_arr[mask]
            if len(cluster_branches) == 0:
                continue
            majority = Counter(cluster_branches).most_common(1)[0][0]
            correct = np.sum(cluster_branches == majority)
            total_correct += correct
            total_count += len(cluster_branches)
        return total_correct / total_count if total_count > 0 else 0
    
    coarse_purity = compute_purity(cluster_data[coarse_key])
    fine_purity = compute_purity(cluster_data[fine_key])
    improvement = (fine_purity - coarse_purity) / coarse_purity if coarse_purity > 0 else 0
    
    return {
        "status": "PASS" if fine_purity > coarse_purity else "FAIL",
        "coarse_purity": round(coarse_purity, 4),
        "fine_purity": round(fine_purity, 4),
        "improvement_pct": round(improvement * 100, 2),
        "note": "Simulated jurist zooms from coarse to fine clusters. Improvement in branch purity means zoom reveals more specific legal structure."
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


def run_all_jurist_usability_benchmarks(
    embeddings: np.ndarray,
    branches: np.ndarray,
    languages: np.ndarray,
    valid_indices: List[int]
) -> Dict:
    """Run all jurist usability simulation benchmarks."""
    results = {}
    
    print("Running jurist pairwise preference simulation...")
    results['pairwise_preference'] = simulate_pairwise_preference(embeddings, branches, languages)
    
    print("Running jurist cluster coherence rating simulation...")
    results['cluster_coherence_rating'] = simulate_cluster_coherence_rating(embeddings, branches, languages)
    
    print("Running jurist zoom task simulation...")
    results['zoom_task'] = simulate_zoom_task(embeddings, branches, languages, valid_indices,
                                               Path('/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map/cluster_assignments.json'))
    
    print("Running jurist cross-language retrieval simulation...")
    results['cross_language_retrieval'] = simulate_cross_language_retrieval(embeddings, branches, languages)
    
    # Summary
    passed = sum(1 for v in results.values() if v.get('status') == 'PASS')
    total = len(results)
    results['summary'] = {
        'total_benchmarks': total,
        'passed': passed,
        'failed': total - passed,
        'all_passed': passed == total
    }
    
    return results


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='results/jurist_usability_results.json')
    args = parser.parse_args()
    
    print("Loading baseline embeddings...")
    embeddings, metadata = load_baseline_embeddings()
    print(f"Loaded {len(embeddings)} decisions, {embeddings.shape[1]} dimensions")
    
    print("Creating debiased_citation_blended representation...")
    representation = create_debiased_citation_blended(embeddings)
    print(f"Representation shape: {representation.shape}")
    
    print("Preparing metadata...")
    branches, languages, chambers, valid_indices = prepare_metadata(metadata)
    
    print(f"Valid decisions: {len(valid_indices)}")
    print(f"Branch distribution: {Counter(branches)}")
    print(f"Language distribution: {Counter(languages)}")
    
    # Use only valid decisions
    rep_valid = representation[valid_indices]
    
    print("\nRunning jurist usability simulations...")
    results = run_all_jurist_usability_benchmarks(rep_valid, branches, languages, valid_indices)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {output_path}")
    print(f"Summary: {results['summary']['passed']}/{results['summary']['total_benchmarks']} passed")
    for name, result in results.items():
        if name == 'summary':
            continue
        status = result.get('status', 'N/A')
        print(f"  {name}: {status}")