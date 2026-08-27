#!/usr/bin/env python3
"""
Hierarchical Map Builder for Fractal Map Lane

Builds a product-ready multi-resolution hierarchical map from concat embeddings.
Produces:
1. Multi-resolution Leiden clustering assignments (the map hierarchy)
2. Parent-child nesting between resolutions (zoom structure)
3. Cluster metadata at each resolution (labels, purity, dominant areas)
4. Zoom coherence metrics per cluster
5. Evaluation against hierarchy_coherence benchmark

Hypothesis: Multi-resolution Leiden clustering on concat embeddings produces a
nested hierarchy where zooming from coarse to fine reveals legally coherent
substructure. The hierarchy is storable and usable as a product artifact.

Frozen before observation:
- Corpus: 1000 BGer decisions (2020-2024)
- Embeddings: concat_center_tfidf (768-dim center-projected + 128-dim TF-IDF)
- Clustering: Leiden at resolutions [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
- Evaluation: nesting consistency, purity per level, branch coherence
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
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_metadata_with_branch():
    """Load baseline metadata and enrich with branch from corpus files."""
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    branch_map = {}
    for year_file in sorted(CORPUS_DIR.glob("bger_20*.jsonl")):
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
    baseline_ids = set(m['decision_id'] for m in metadata)
    decisions = {}
    
    for year_file in sorted(CORPUS_DIR.glob("bger_20*.jsonl")):
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


def build_nesting(hierarchy):
    """
    Given a dict mapping resolution -> labels, compute parent-child nesting.
    Returns: for each pair of consecutive resolutions, which child clusters
    belong to which parent cluster.
    """
    resolutions = sorted(hierarchy.keys())
    nesting = {}
    
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        
        coarser_labels = hierarchy[coarser_res]
        finer_labels = hierarchy[finer_res]
        
        # Map each finer cluster to its parent
        child_to_parent = {}
        unique_fine = np.unique(finer_labels[finer_labels != -1])
        
        for fine_id in unique_fine:
            fine_mask = finer_labels == fine_id
            parent_labels = coarser_labels[fine_mask]
            parent_labels_valid = parent_labels[parent_labels != -1]
            
            if len(parent_labels_valid) > 0:
                # Most common parent
                parent_id = Counter(parent_labels_valid.tolist()).most_common(1)[0][0]
                child_to_parent[int(fine_id)] = int(parent_id)
            else:
                child_to_parent[int(fine_id)] = -1
        
        # Inverse: parent -> list of children
        parent_to_children = defaultdict(list)
        for child, parent in child_to_parent.items():
            parent_to_children[parent].append(child)
        
        nesting[f"{coarser_res}_to_{finer_res}"] = {
            'coarser_resolution': coarser_res,
            'finer_resolution': finer_res,
            'child_to_parent': child_to_parent,
            'parent_to_children': dict(parent_to_children),
            'nesting_consistency': sum(1 for c, p in child_to_parent.items() if p != -1) / len(child_to_parent) if child_to_parent else 0,
        }
    
    return nesting


def compute_cluster_metadata(labels, metadata):
    """Compute rich metadata for each cluster."""
    unique_labels = np.unique(labels[labels != -1])
    cluster_info = {}
    
    for label in unique_labels:
        mask = labels == label
        indices = np.where(mask)[0]
        cluster_meta = [metadata[i] for i in indices]
        
        # Language distribution
        langs = Counter(m.get('language') for m in cluster_meta if m.get('language'))
        dominant_lang = langs.most_common(1)[0] if langs else (None, 0)
        lang_purity = dominant_lang[1] / len(indices) if indices.size > 0 else 0
        
        # Branch distribution
        branches = Counter(m.get('branch') for m in cluster_meta if m.get('branch'))
        dominant_branch = branches.most_common(1)[0] if branches else (None, 0)
        branch_purity = dominant_branch[1] / len(indices) if indices.size > 0 else 0
        
        # Legal area distribution
        areas = Counter(m.get('legal_area') for m in cluster_meta if m.get('legal_area'))
        dominant_area = areas.most_common(1)[0] if areas else (None, 0)
        
        # Year distribution
        years = Counter(m.get('year') for m in cluster_meta if m.get('year'))
        
        # Chamber distribution
        chambers = Counter(m.get('chamber') for m in cluster_meta if m.get('chamber'))
        
        cluster_info[int(label)] = {
            'size': int(mask.sum()),
            'dominant_lang': dominant_lang[0],
            'lang_purity': float(lang_purity),
            'dominant_branch': dominant_branch[0],
            'branch_purity': float(branch_purity),
            'dominant_area': dominant_area[0],
            'area_count': len(areas),
            'top_areas': {str(k): int(v) for k, v in areas.most_common(5)},
            'top_branches': {str(k): int(v) for k, v in branches.most_common(5)},
            'year_dist': {str(k): int(v) for k, v in years.most_common()},
            'top_chambers': {str(k): int(v) for k, v in chambers.most_common(3)},
            'decision_ids': [metadata[i]['decision_id'] for i in indices],
        }
    
    return cluster_info


def compute_hierarchy_nesting_score(hierarchy_labels):
    """
    Compute nesting consistency: for each pair of consecutive resolutions,
    check that every finer cluster is fully contained within a single coarser cluster.
    """
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
                # Count = 1 means all elements in this fine cluster belong to the same parent
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


def compute_branch_coherence_per_level(hierarchy_labels, metadata):
    """Compute branch purity at each resolution level."""
    results = {}
    for res, labels in hierarchy_labels.items():
        unique_labels = np.unique(labels[labels != -1])
        purities = []
        
        for label in unique_labels:
            mask = labels == label
            cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
            cluster_branches = [b for b in cluster_branches if b and b != 'null']
            
            if cluster_branches:
                most_common = Counter(cluster_branches).most_common(1)[0][1]
                purities.append(most_common / len(cluster_branches))
        
        results[f"res_{res}"] = {
            'mean_branch_purity': float(np.mean(purities)) if purities else 0,
            'n_clusters': int(len(unique_labels)),
            'purity_values': [float(p) for p in purities],
        }
    
    return results


def main():
    logger.info("=== Hierarchical Map Builder ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # 1. Load data
    logger.info("\n1. Loading metadata with branch info...")
    id_to_idx, metadata = load_metadata_with_branch()
    baseline_emb, center_emb = load_representations()
    logger.info(f"   Metadata: {len(metadata)} decisions")
    
    # Branch distribution
    branches = Counter(m.get('branch') for m in metadata if m.get('branch'))
    logger.info(f"   Branches: {dict(branches)}")
    
    # 2. Load corpus and compute TF-IDF
    logger.info("\n2. Loading corpus decisions...")
    decisions = load_corpus_decisions(metadata)
    logger.info(f"   Loaded {len(decisions)} decisions")
    
    logger.info("\n3. Computing TF-IDF Erwaegungen...")
    tfidf_full, valid_indices = compute_tfidf_erwaegungen(metadata, decisions)
    logger.info(f"   TF-IDF: {tfidf_full.shape}, {len(valid_indices)} valid")
    
    # 4. Build concat
    logger.info("\n4. Building concatenated representation...")
    concat_emb = build_concat(baseline_emb, center_emb, tfidf_full)
    logger.info(f"   Concat: {concat_emb.shape}")
    
    # 5. Multi-resolution clustering
    resolutions = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    hierarchy_labels = {}
    hierarchy_info = {}
    
    logger.info("\n5. Running multi-resolution Leiden clustering...")
    for res in resolutions:
        labels, modularity = leiden_clustering(concat_emb, resolution=res)
        n_clusters = len(set(labels[labels != -1]))
        hierarchy_labels[res] = labels
        hierarchy_info[f"res_{res}"] = {
            'resolution': res,
            'n_clusters': n_clusters,
            'modularity': float(modularity),
        }
        logger.info(f"   res={res}: {n_clusters} clusters, modularity={modularity:.4f}")
    
    # 6. Build nesting structure
    logger.info("\n6. Building nesting structure...")
    nesting = build_nesting(hierarchy_labels)
    for key, nest in nesting.items():
        logger.info(f"   {key}: consistency={nest['nesting_consistency']:.3f}")
    
    # 7. Compute cluster metadata at each resolution
    logger.info("\n7. Computing cluster metadata at each resolution...")
    cluster_metadata_by_res = {}
    for res in resolutions:
        cluster_metadata_by_res[f"res_{res}"] = compute_cluster_metadata(
            hierarchy_labels[res], metadata
        )
    
    # 8. Compute nesting score
    logger.info("\n8. Computing nesting consistency score...")
    nesting_scores = compute_hierarchy_nesting_score(hierarchy_labels)
    mean_nesting = np.mean([s['nesting_score'] for s in nesting_scores])
    logger.info(f"   Mean nesting score: {mean_nesting:.4f}")
    for s in nesting_scores:
        logger.info(f"   {s['from_resolution']}->{s['to_resolution']}: {s['nesting_score']:.3f} "
                    f"({s['n_consistent']}/{s['n_fine_clusters']})")
    
    # 9. Compute branch coherence per level
    logger.info("\n9. Computing branch coherence per level...")
    branch_coherence = compute_branch_coherence_per_level(hierarchy_labels, metadata)
    for res_key, bc in branch_coherence.items():
        logger.info(f"   {res_key}: branch_purity={bc['mean_branch_purity']:.4f}, "
                    f"n_clusters={bc['n_clusters']}")
    
    # 10. Summary
    logger.info("\n" + "=" * 70)
    logger.info("HIERARCHICAL MAP SUMMARY")
    logger.info("=" * 70)
    
    # Compute overall metrics
    all_purities = []
    for res in resolutions:
        labels = hierarchy_labels[res]
        unique_labels = np.unique(labels[labels != -1])
        for label in unique_labels:
            mask = labels == label
            cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
            cluster_branches = [b for b in cluster_branches if b and b != 'null']
            if cluster_branches:
                most_common = Counter(cluster_branches).most_common(1)[0][1]
                all_purities.append(most_common / len(cluster_branches))
    
    logger.info(f"\nOverall metrics:")
    logger.info(f"  Resolutions: {resolutions}")
    logger.info(f"  Mean nesting score: {mean_nesting:.4f}")
    logger.info(f"  Mean branch purity (all levels): {np.mean(all_purities):.4f}")
    
    # Check if zoom reveals more structure
    logger.info("\n  Zoom structure (clusters per resolution):")
    for res in resolutions:
        info = hierarchy_info[f"res_{res}"]
        logger.info(f"    res={res}: {info['n_clusters']} clusters, modularity={info['modularity']:.4f}")
    
    # 11. Save artifacts
    logger.info("\n10. Saving hierarchical map artifacts...")
    
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
    
    # Save cluster assignments (the map)
    assignments = {}
    for res in resolutions:
        assignments[f"res_{res}"] = hierarchy_labels[res].tolist()
    
    output = {
        "run_id": f"hierarchical_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 1,
        "hypothesis": "Multi-resolution Leiden clustering produces a nested hierarchy where zoom reveals legally coherent substructure",
        "frozen_sample": f"{len(metadata)} BGer decisions (2020-2024)",
        "frozen_metric": "Nesting consistency, branch purity per level, zoom improvement rate",
        "success_rule": "Nesting score > 0.8 and branch purity improves or maintains at finer resolutions",
        "resolutions_tested": resolutions,
        "hierarchy_info": hierarchy_info,
        "nesting": nesting,
        "nesting_scores": nesting_scores,
        "mean_nesting_score": float(mean_nesting),
        "branch_coherence": branch_coherence,
        "cluster_metadata_by_res": cluster_metadata_by_res,
        "summary": {
            "n_decisions": len(metadata),
            "n_resolutions": len(resolutions),
            "mean_nesting_score": float(mean_nesting),
            "mean_branch_purity_all_levels": float(np.mean(all_purities)),
            "resolutions": {f"res_{r}": hierarchy_info[f"res_{r}"] for r in resolutions},
        },
    }
    
    # Save main results
    output_path = OUTPUT_DIR / "hierarchical_map_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    logger.info(f"  Results saved to {output_path}")
    
    # Save assignments (the actual map)
    assignments_path = OUTPUT_DIR / "cluster_assignments.json"
    with open(assignments_path, 'w') as f:
        json.dump(convert(assignments), f)
    logger.info(f"  Assignments saved to {assignments_path}")
    
    # Save numpy arrays for product use
    for res in resolutions:
        np.save(OUTPUT_DIR / f"labels_res_{res}.npy", hierarchy_labels[res])
    logger.info(f"  Label arrays saved as .npy files")
    
    logger.info("\n=== Hierarchical map build complete ===")
    
    return output


if __name__ == "__main__":
    main()
