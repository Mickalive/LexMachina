#!/usr/bin/env python3
"""
Cross-language transfer stability benchmarks for evaluation v2.
Tests zero-shot cross-language transfer, cross-language neighbor quality,
and language-specific representation degradation.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score
from sklearn.cluster import KMeans
from collections import defaultdict
import sys
sys.path.insert(0, '/home/runner/work/LexMachina/LexMachina/evaluation')
from data.real_corpus import load_real_corpus


def load_corpus_with_branch() -> Tuple[np.ndarray, List[Dict]]:
    """Load corpus with branch metadata using real_corpus loader."""
    decisions, rep_fn, corpus = load_real_corpus(max_decisions=1000)
    
    # Get TF-IDF representation
    embeddings = []
    metadata = []
    for did, d in decisions.items():
        vec = rep_fn(did)
        if vec is not None:
            embeddings.append(vec)
            metadata.append({
                'decision_id': did,
                'language': d.language,
                'branch': d.branch,
                'legal_area': d.legal_area,
                'chamber': d.chamber
            })
    
    embeddings = np.array(embeddings)
    return embeddings, metadata


def compute_representation(embeddings_subset: np.ndarray) -> np.ndarray:
    """Compute debiased_citation_blended representation."""
    n_samples = embeddings_subset.shape[0]
    n_components_64 = min(64, n_samples - 1, embeddings_subset.shape[1])
    
    pca_debias = PCA(n_components=1, random_state=42)
    debias_component = pca_debias.fit_transform(embeddings_subset)
    debiased = embeddings_subset - debias_component @ pca_debias.components_
    
    pca_64 = PCA(n_components=n_components_64, random_state=42)
    debiased_64 = pca_64.fit_transform(debiased)
    return normalize(debiased_64, norm='l2')


def split_by_language(embeddings: np.ndarray, metadata: List[Dict]) -> Dict[str, Tuple[np.ndarray, List[int]]]:
    """Split embeddings by language."""
    lang_indices = defaultdict(list)
    for i, m in enumerate(metadata):
        lang = m.get('language', 'unknown')
        lang_indices[lang].append(i)
    
    result = {}
    for lang, indices in lang_indices.items():
        if len(indices) > 10:  # Minimum size
            result[lang] = (embeddings[indices], indices)
    
    return result


def cross_language_neighbor_quality(embeddings: np.ndarray, metadata: List[Dict], 
                                     k: int = 10) -> Dict:
    """
    Test cross-language neighbor quality:
    For each decision, check if its k-NN include same-branch cross-language decisions.
    """
    # Group by branch and language
    branch_lang_groups = defaultdict(lambda: defaultdict(list))
    for i, m in enumerate(metadata):
        branch = m.get('branch', 'unknown')
        lang = m.get('language', 'unknown')
        branch_lang_groups[branch][lang].append(i)
    
    # Build NN graph on full embeddings
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]  # Exclude self
    
    # For each decision, measure cross-language same-branch neighbor fraction
    cross_lang_same_branch_rates = []
    same_lang_same_branch_rates = []
    cross_branch_rates = []
    
    for i, m in enumerate(metadata):
        branch = m.get('branch', 'unknown')
        lang = m.get('language', 'unknown')
        neighbor_indices = neighbors[i]
        
        neighbor_branches = [metadata[n].get('branch', 'unknown') for n in neighbor_indices]
        neighbor_langs = [metadata[n].get('language', 'unknown') for n in neighbor_indices]
        
        # Same branch, different language
        cross_lang_same_branch = sum(1 for b, l in zip(neighbor_branches, neighbor_langs) 
                                     if b == branch and l != lang)
        # Same branch, same language
        same_lang_same_branch = sum(1 for b, l in zip(neighbor_branches, neighbor_langs) 
                                    if b == branch and l == lang)
        # Different branch
        cross_branch = sum(1 for b in neighbor_branches if b != branch)
        
        cross_lang_same_branch_rates.append(cross_lang_same_branch / k)
        same_lang_same_branch_rates.append(same_lang_same_branch / k)
        cross_branch_rates.append(cross_branch / k)
    
    return {
        'cross_lang_same_branch_mean': float(np.mean(cross_lang_same_branch_rates)),
        'same_lang_same_branch_mean': float(np.mean(same_lang_same_branch_rates)),
        'cross_branch_mean': float(np.mean(cross_branch_rates)),
        'invariance_gap': float(np.mean(same_lang_same_branch_rates) - np.mean(cross_lang_same_branch_rates)),
        'separation': float(np.mean(cross_lang_same_branch_rates) - np.mean(cross_branch_rates)),
        'k': k
    }


def zero_shot_cross_language_transfer(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """
    Zero-shot cross-language transfer:
    Train PCA on one language, apply to another, measure quality degradation.
    """
    lang_splits = split_by_language(embeddings, metadata)
    
    # Need at least 2 languages with enough data
    langs = [l for l, (emb, _) in lang_splits.items() if len(emb) > 50]
    if len(langs) < 2:
        return {'status': 'INSUFFICIENT_LANGUAGES', 'langs': langs}
    
    results = {}
    
    for train_lang in langs:
        train_emb, train_indices = lang_splits[train_lang]
        n_train = len(train_emb)
        n_components_64 = min(64, n_train - 1, train_emb.shape[1])
        
        # Fit PCA on training language
        pca_debias = PCA(n_components=1, random_state=42)
        pca_debias.fit(train_emb)
        
        debias_train = pca_debias.transform(train_emb)
        debiased_train = train_emb - debias_train @ pca_debias.components_
        
        pca_64 = PCA(n_components=n_components_64, random_state=42)
        pca_64.fit(debiased_train)
        
        # Apply to all languages
        for test_lang in langs:
            test_emb, test_indices = lang_splits[test_lang]
            
            # Apply frozen pipeline
            debias_test = pca_debias.transform(test_emb)
            debiased_test = test_emb - debias_test @ pca_debias.components_
            test_64 = pca_64.transform(debiased_test)
            test_64 = normalize(test_64, norm='l2')
            
            # If same language, this is in-domain; if different, zero-shot
            is_zero_shot = (train_lang != test_lang)
            
            # Quality metric: cluster coherence on branch labels
            test_meta = [metadata[i] for i in test_indices]
            branches = [m.get('branch', 'unknown') for m in test_meta]
            unique_branches = list(set(branches))
            
            if len(unique_branches) > 1:
                n_clusters = min(len(unique_branches), 10)
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(test_64)
                
                branch_to_idx = {b: i for i, b in enumerate(unique_branches)}
                true_labels = np.array([branch_to_idx[b] for b in branches])
                
                nmi = normalized_mutual_info_score(true_labels, cluster_labels)
                ari = adjusted_rand_score(true_labels, cluster_labels)
            else:
                nmi = 0.0
                ari = 0.0
            
            key = f"{train_lang}->{test_lang}"
            results[key] = {
                'train_lang': train_lang,
                'test_lang': test_lang,
                'zero_shot': is_zero_shot,
                'nmi': float(nmi),
                'ari': float(ari),
                'test_size': len(test_emb)
            }
    
    # Summary
    zero_shot_nmis = [r['nmi'] for r in results.values() if r['zero_shot']]
    in_domain_nmis = [r['nmi'] for r in results.values() if not r['zero_shot']]
    
    return {
        'pairwise_results': results,
        'zero_shot_mean_nmi': float(np.mean(zero_shot_nmis)) if zero_shot_nmis else 0.0,
        'in_domain_mean_nmi': float(np.mean(in_domain_nmis)) if in_domain_nmis else 0.0,
        'transfer_gap': float(np.mean(in_domain_nmis) - np.mean(zero_shot_nmis)) if zero_shot_nmis and in_domain_nmis else 0.0,
        'status': 'PASS' if (zero_shot_nmis and np.mean(zero_shot_nmis) > 0.2) else 'FAIL'
    }


def language_specific_representation_quality(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """
    Measure representation quality separately per language.
    Computes branch NMI within each language.
    """
    lang_splits = split_by_language(embeddings, metadata)
    
    results = {}
    for lang, (emb, indices) in lang_splits.items():
        if len(emb) < 20:
            continue
            
        # Compute representation on this language only
        rep = compute_representation(emb)
        
        # Cluster and measure branch coherence
        meta = [metadata[i] for i in indices]
        branches = [m.get('branch', 'unknown') for m in meta]
        unique_branches = list(set(branches))
        
        if len(unique_branches) > 1:
            n_clusters = min(len(unique_branches) * 2, 15)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(rep)
            
            branch_to_idx = {b: i for i, b in enumerate(unique_branches)}
            true_labels = np.array([branch_to_idx[b] for b in branches])
            
            nmi = normalized_mutual_info_score(true_labels, cluster_labels)
            ari = adjusted_rand_score(true_labels, cluster_labels)
        else:
            nmi = 0.0
            ari = 0.0
        
        results[lang] = {
            'n_decisions': len(emb),
            'branch_nmi': float(nmi),
            'branch_ari': float(ari),
            'n_branches': len(unique_branches)
        }
    
    # Cross-language consistency: how much does NMI vary across languages?
    nmis = [r['branch_nmi'] for r in results.values()]
    
    return {
        'per_language': results,
        'mean_nmi': float(np.mean(nmis)) if nmis else 0.0,
        'std_nmi': float(np.std(nmis)) if nmis else 0.0,
        'min_nmi': float(np.min(nmis)) if nmis else 0.0,
        'max_nmi': float(np.max(nmis)) if nmis else 0.0,
        'status': 'PASS' if (nmis and np.mean(nmis) > 0.3 and np.std(nmis) < 0.2) else 'FAIL'
    }


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


def run_all_cross_language_benchmarks(embeddings: np.ndarray, metadata: List[Dict]) -> Dict:
    """Run all cross-language benchmarks."""
    results = {}
    
    print("Running cross-language neighbor quality...")
    results['cross_language_neighbor_quality'] = cross_language_neighbor_quality(embeddings, metadata)
    
    print("Running zero-shot cross-language transfer...")
    results['zero_shot_transfer'] = zero_shot_cross_language_transfer(embeddings, metadata)
    
    print("Running language-specific representation quality...")
    results['language_specific_quality'] = language_specific_representation_quality(embeddings, metadata)
    
    print("Running adversarial language dominance...")
    results['adversarial_language_dominance'] = adversarial_language_dominance(embeddings, metadata)
    
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
    parser.add_argument('--output', default='results/cross_language_benchmark_results.json')
    args = parser.parse_args()
    
    print("Loading corpus with branch metadata...")
    embeddings, metadata = load_corpus_with_branch()
    print(f"Loaded {len(embeddings)} decisions, {embeddings.shape[1]} dimensions")
    
    # Check branch distribution per language
    from collections import Counter
    lang_branch = Counter((m.get('language'), m.get('branch')) for m in metadata)
    print("Language-Branch distribution:")
    for (l,b),c in lang_branch.most_common():
        print(f"  {l}: {b} = {c}")
    
    # Compute representation
    print("Computing debiased_citation_blended representation...")
    representation = compute_representation(embeddings)
    print(f"Representation shape: {representation.shape}")
    
    print("\nRunning cross-language benchmarks...")
    results = run_all_cross_language_benchmarks(representation, metadata)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {output_path}")
    print(f"Summary: {results['summary']['passed']}/{results['summary']['total_benchmarks']} passed")
    for name, result in results.items():
        if name != 'summary':
            status = result.get('status', 'N/A')
            print(f"  {name}: {status}")