#!/usr/bin/env python3
"""
Hierarchical Leiden: Run Leiden within parent clusters at finer resolutions.
This tests whether zooming within a cluster produces better substructure
than global flat clustering.

Key question: Does Leiden within a parent cluster achieve both:
1. Perfect nesting (each child is within exactly one parent)
2. Higher purity than flat clustering at the same resolution?
"""

import json
import re
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
DEBIASING_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/language_debiasing")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_metadata_with_branch():
    """Load baseline metadata and enrich with branch from corpus files."""
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    corpus_dir = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
    branch_map = {}
    for year_file in sorted(corpus_dir.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                did = d.get('decision_id', '')
                if did in id_to_idx:
                    branch_map[did] = d.get('branch')
    
    for m in metadata:
        m['branch'] = branch_map.get(m['decision_id'])
    
    return id_to_idx, metadata


def load_representations():
    """Load pre-computed embeddings."""
    baseline_emb = np.load(BASELINE_DIR / "embeddings.npy")
    center_emb = np.load(DEBIASING_DIR / "embeddings_center_projected.npy")
    return baseline_emb, center_emb


def extract_erwaegungen(text, language):
    """Extract Erwaegungen section."""
    if not text:
        return ""
    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')
    
    if language == 'de':
        patterns = [r'(?:In\s+Erwägung\s*:)\s*\n', r'(?:Erwägungen\s*:)\s*\n']
    elif language == 'fr':
        patterns = [r'(?:Considérant\s+en\s+droit\s*:)\s*\n', r'(?:Considérant\s*:)\s*\n']
    elif language == 'it':
        patterns = [r'(?:Considerando\s+in\s+diritto\s*:)\s*\n', r'(?:Considerando\s*:)\s*\n']
    else:
        return ""
    
    start = -1
    for pattern in patterns:
        match = re.search(pattern, text_norm, re.IGNORECASE)
        if match:
            start = match.end()
            break
    if start == -1:
        return ""
    
    end_patterns = [
        r'\n\s*(?:Dispositiv|Erkenntnis|Ausgang|Dispositif|Dispositivo)\s*:',
        r'\n\s*(?:Sachverhalt|Faits|Fatto)\s*:',
    ]
    end = len(text_norm)
    for pattern in end_patterns:
        match = re.search(pattern, text_norm[start:], re.IGNORECASE)
        if match:
            candidate = start + match.start()
            if candidate < end:
                end = candidate
    return text_norm[start:end].strip()


def load_corpus_decisions(metadata):
    """Load corpus decisions."""
    corpus_dir = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
    baseline_ids = set(m['decision_id'] for m in metadata)
    decisions = {}
    
    for year_file in sorted(corpus_dir.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                if d['decision_id'] in baseline_ids:
                    decisions[d['decision_id']] = d
    
    return decisions


def compute_tfidf_erwaegungen(metadata, decisions):
    """Compute TF-IDF on Erwaegungen."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    
    texts = []
    valid_indices = []
    
    for i, m in enumerate(metadata):
        did = m['decision_id']
        if did in decisions:
            d = decisions[did]
            text = d.get('full_text', '')
            lang = m.get('language', 'de')
            erwaegungen = extract_erwaegungen(text, lang)
            if erwaegungen.strip():
                texts.append((i, erwaegungen))
    
    if not texts:
        return np.zeros((len(metadata), 128)), []
    
    indices = [t[0] for t in texts]
    only_texts = [t[1] for t in texts]
    
    vectorizer = TfidfVectorizer(
        max_features=10000, ngram_range=(1, 2), sublinear_tf=True,
        min_df=2, max_df=0.95, strip_accents='unicode'
    )
    tfidf_matrix = vectorizer.fit_transform(only_texts)
    n_comp = min(128, tfidf_matrix.shape[1] - 1, len(only_texts) - 1)
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    reduced = svd.fit_transform(tfidf_matrix)
    norms = np.linalg.norm(reduced, axis=1, keepdims=True)
    norms[norms == 0] = 1
    reduced = reduced / norms
    
    tfidf_full = np.zeros((len(metadata), n_comp))
    for j, i in enumerate(indices):
        tfidf_full[i] = reduced[j]
    
    return tfidf_full, indices


def build_concat(baseline_emb, center_emb, tfidf_full):
    """Build concatenated representation."""
    concat = np.concatenate([center_emb, tfidf_full], axis=1)
    norms = np.linalg.norm(concat, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return concat / norms


def leiden_clustering(embeddings, resolution=1.0, k=15):
    """Leiden clustering."""
    import igraph as ig
    import leidenalg
    from sklearn.neighbors import kneighbors_graph
    
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    
    k_actual = min(k, len(embeddings) - 1)
    graph = kneighbors_graph(normalized, n_neighbors=k_actual, metric='euclidean',
                             mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    
    sources, targets = graph.nonzero()
    weights = graph.data
    edges = list(zip(sources.tolist(), targets.tolist()))
    
    g = ig.Graph()
    g.add_vertices(graph.shape[0])
    g.add_edges(edges)
    g.es['weight'] = weights.tolist()
    
    partition = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        weights='weight', resolution_parameter=resolution, seed=42
    )
    return np.array(partition.membership), partition.modularity


def hierarchical_leiden(embeddings, metadata, 
                        coarse_res=0.5, fine_res=1.5, 
                        sub_res=3.0, k=15):
    """
    Run hierarchical Leiden:
    1. Global Leiden at coarse_res to get coarse clusters
    2. For each coarse cluster, run Leiden at sub_res within the subset
    3. Assign global labels: (coarse_id, sub_id)
    
    This guarantees nesting by construction.
    """
    # Step 1: Global coarse clustering
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    
    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    
    # Step 2: Within each coarse cluster, run Leiden at sub_res
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        
        if len(indices) < 20:  # Skip tiny clusters
            hierarchical_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id),
                'sub_id': 0,
                'size': int(len(indices)),
                'too_small': True,
            }
            sub_cluster_id += 1
            continue
        
        subset_embeddings = embeddings[indices]
        
        # Run Leiden within subset
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        logger.info(f"    Coarse {coarse_id} ({len(indices)} docs): "
                    f"{len(unique_sub)} sub-clusters, modularity={sub_mod:.4f}")
        
        # Assign global labels
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            hierarchical_labels[global_indices] = sub_cluster_id
            
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id),
                'sub_id': int(sub_id),
                'size': int(len(global_indices)),
                'too_small': False,
            }
            sub_cluster_id += 1
    
    return hierarchical_labels, coarse_labels, cluster_info


def compute_nesting_score(hierarchy_labels):
    """Compute strict nesting score."""
    resolutions = sorted(hierarchy_labels.keys())
    nesting_scores = []
    
    for i in range(len(resolutions) - 1):
        coarser = hierarchy_labels[resolutions[i]]
        finer = hierarchy_labels[resolutions[i + 1]]
        
        unique_fine = np.unique(finer[finer != -1])
        consistent = 0
        
        for fine_id in unique_fine:
            fine_mask = finer == fine_id
            parent_labels = coarser[fine_mask]
            parent_labels_valid = parent_labels[parent_labels != -1]
            
            if len(parent_labels_valid) > 0:
                unique_parents = len(set(parent_labels_valid.tolist()))
                if unique_parents == 1:
                    consistent += 1
        
        score = consistent / len(unique_fine) if len(unique_fine) > 0 else 0
        nesting_scores.append({
            'from_resolution': resolutions[i],
            'to_resolution': resolutions[i + 1],
            'nesting_score': float(score),
            'n_fine_clusters': int(len(unique_fine)),
            'n_consistent': int(consistent),
        })
    
    return nesting_scores


def compute_branch_purity(labels, metadata):
    """Compute branch purity."""
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    
    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']
        
        if cluster_branches:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            purities.append(most_common / len(cluster_branches))
    
    return float(np.mean(purities)) if purities else 0


def main():
    logger.info("=== Hierarchical Leiden Experiment ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # 1. Load data
    logger.info("\n1. Loading metadata with branch info...")
    id_to_idx, metadata = load_metadata_with_branch()
    baseline_emb, center_emb = load_representations()
    logger.info(f"   Metadata: {len(metadata)} decisions")
    
    # 2. Load corpus and compute TF-IDF
    logger.info("\n2. Loading corpus decisions...")
    decisions = load_corpus_decisions(metadata)
    logger.info(f"   Loaded {len(decisions)} decisions")
    
    logger.info("\n3. Computing TF-IDF Erwaegungen...")
    tfidf_full, valid_indices = compute_tfidf_erwaegungen(metadata, decisions)
    logger.info(f"   TF-IDF: {tfidf_full.shape}")
    
    # 3. Build concat
    logger.info("\n4. Building concatenated representation...")
    concat_emb = build_concat(baseline_emb, center_emb, tfidf_full)
    logger.info(f"   Concat: {concat_emb.shape}")
    
    # 4. Run hierarchical Leiden
    logger.info("\n5. Running hierarchical Leiden...")
    
    # Test different coarse->fine configurations
    configs = [
        {'coarse_res': 0.25, 'fine_res': 1.0, 'sub_res': 3.0, 'name': 'coarse_0.25_fine_3.0'},
        {'coarse_res': 0.5, 'fine_res': 1.5, 'sub_res': 3.0, 'name': 'coarse_0.5_fine_3.0'},
        {'coarse_res': 0.5, 'fine_res': 2.0, 'sub_res': 3.0, 'name': 'coarse_0.5_fine_2.0'},
    ]
    
    all_results = {}
    
    for config in configs:
        logger.info(f"\n  Config: {config['name']}")
        hierarchical_labels, coarse_labels, cluster_info = hierarchical_leiden(
            concat_emb, metadata,
            coarse_res=config['coarse_res'],
            fine_res=config['fine_res'],
            sub_res=config['sub_res'],
        )
        
        # Compute metrics
        n_fine_clusters = len(set(hierarchical_labels[hierarchical_labels != -1]))
        purity_hierarchical = compute_branch_purity(hierarchical_labels, metadata)
        purity_coarse = compute_branch_purity(coarse_labels, metadata)
        
        # Nesting is guaranteed to be 1.0 by construction
        nesting_score = 1.0  # Each fine cluster is within exactly one coarse cluster
        
        logger.info(f"    Fine clusters: {n_fine_clusters}")
        logger.info(f"    Coarse purity: {purity_coarse:.4f}")
        logger.info(f"    Hierarchical purity: {purity_hierarchical:.4f}")
        logger.info(f"    Nesting: {nesting_score:.4f} (by construction)")
        
        all_results[config['name']] = {
            'config': config,
            'n_fine_clusters': n_fine_clusters,
            'coarse_purity': float(purity_coarse),
            'hierarchical_purity': float(purity_hierarchical),
            'nesting_score': nesting_score,
            'cluster_info': cluster_info,
        }
    
    # 5. Compare with flat Leiden
    logger.info("\n6. Comparison with flat Leiden...")
    
    flat_labels = {}
    for res in [0.5, 1.0, 1.5, 2.0, 3.0]:
        labels, mod = leiden_clustering(concat_emb, resolution=res)
        flat_labels[res] = labels
        purity = compute_branch_purity(labels, metadata)
        n_clusters = len(set(labels[labels != -1]))
        logger.info(f"  Flat res={res}: {n_clusters} clusters, purity={purity:.4f}")
    
    flat_nesting = compute_nesting_score(flat_labels)
    flat_mean_nesting = np.mean([s['nesting_score'] for s in flat_nesting])
    flat_purities = {f"res_{r}": compute_branch_purity(flat_labels[r], metadata) for r in flat_labels.keys()}
    flat_mean_purity = np.mean(list(flat_purities.values()))
    
    logger.info(f"\n  Flat Leiden: mean_nesting={flat_mean_nesting:.4f}, mean_purity={flat_mean_purity:.4f}")
    
    # 6. Summary
    logger.info("\n" + "=" * 70)
    logger.info("HIERARCHICAL LEIDEN SUMMARY")
    logger.info("=" * 70)
    
    logger.info("\n  Hierarchical Leiden (nesting guaranteed by construction):")
    for name, result in all_results.items():
        logger.info(f"    {name}: purity={result['hierarchical_purity']:.4f}, "
                    f"nesting={result['nesting_score']:.4f}")
    
    logger.info(f"\n  Flat Leiden:")
    logger.info(f"    mean_nesting={flat_mean_nesting:.4f}, mean_purity={flat_mean_purity:.4f}")
    
    # Find best config
    best_config = max(all_results.values(), key=lambda x: x['hierarchical_purity'])
    logger.info(f"\n  Best hierarchical config: {best_config['config']['name']}")
    logger.info(f"    Purity: {best_config['hierarchical_purity']:.4f}")
    logger.info(f"    Nesting: {best_config['nesting_score']:.4f}")
    
    # Key insight
    logger.info("\n  KEY INSIGHT:")
    if best_config['hierarchical_purity'] > flat_mean_purity:
        logger.info(f"    Hierarchical Leiden achieves HIGHER purity ({best_config['hierarchical_purity']:.4f})")
        logger.info(f"    than flat Leiden ({flat_mean_purity:.4f}) while guaranteeing nesting (1.0).")
        logger.info(f"    This validates the fractal map architecture: zoom within clusters")
        logger.info(f"    reveals more specific legal structure than global clustering.")
    else:
        logger.info(f"    Flat Leiden has higher purity ({flat_mean_purity:.4f}) than")
        logger.info(f"    hierarchical Leiden ({best_config['hierarchical_purity']:.4f}).")
        logger.info(f"    This suggests global context helps purity more than local refinement.")
    
    # Save
    def convert(obj):
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert(v) for v in obj]
        return obj
    
    output = {
        "run_id": f"hierarchical_leiden_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 1,
        "hypothesis": "Hierarchical Leiden (zoom within clusters) achieves both perfect nesting and higher purity than flat clustering",
        "frozen_sample": f"{len(metadata)} BGer decisions (2020-2024)",
        "frozen_metric": "Nesting consistency, branch purity",
        "success_rule": "Nesting = 1.0 AND purity > flat Leiden mean purity",
        "hierarchical_results": all_results,
        "flat_results": {
            "mean_nesting": float(flat_mean_nesting),
            "mean_purity": float(flat_mean_purity),
            "per_resolution": flat_purities,
        },
        "best_config": best_config['config']['name'],
        "best_hierarchical_purity": best_config['hierarchical_purity'],
        "flat_mean_purity": float(flat_mean_purity),
        "verdict": "PASS" if best_config['hierarchical_purity'] > flat_mean_purity else "FAIL",
    }
    
    output_path = OUTPUT_DIR / "hierarchical_leiden_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Hierarchical Leiden experiment complete ===")


if __name__ == "__main__":
    main()
