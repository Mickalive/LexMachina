#!/usr/bin/env python3
"""
Build fractal map artifacts for PARTIAL dense embeddings (years 2000-2002, ~12k decisions).
This is a scale validation test using available data while waiting for full 174k dense embeddings.
Does NOT claim 174k results - explicitly partial scale validation.
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import logging
import igraph as ig
import leidenalg
from sklearn.neighbors import kneighbors_graph
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASE = Path('/home/runner/work/LexMachina/LexMachina')
OUTPUT_BASE = BASE / 'results/fractal_map/legal_distance_modes'

# Available checkpoint data
CHECKPOINT_DIR = Path('/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints')
META_174K_PATH = Path('/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json')

# Years available
AVAILABLE_YEARS = ['2000', '2001', '2002']

# Hierarchical Leiden config (validated at 62k scale)
COARSE_RES = 0.25
SUB_RES = 3.0
K = 15
RESOLUTIONS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
MIN_CLUSTER_SIZE = 3

MODE_ID = 'center_projected_768_hierarchical_12k_partial'


def load_partial_embeddings_and_metadata():
    """Load and concatenate available year embeddings and metadata."""
    all_embeddings = []
    all_metadata = []
    
    for year in AVAILABLE_YEARS:
        emb_path = CHECKPOINT_DIR / f'embeddings_{year}.npy'
        meta_path = CHECKPOINT_DIR / f'metadata_{year}.json'
        
        embeddings = np.load(emb_path)
        with open(meta_path) as f:
            metadata = json.load(f)
        
        logger.info(f'Loaded {year}: embeddings {embeddings.shape}, metadata {len(metadata)}')
        all_embeddings.append(embeddings)
        all_metadata.extend(metadata)
    
    # Concatenate
    all_embeddings = np.vstack(all_embeddings)
    logger.info(f'Total partial embeddings: {all_embeddings.shape}, metadata: {len(all_metadata)}')
    
    return all_embeddings, all_metadata


def compute_center_projected(embeddings, metadata):
    """Compute language-debiased center_projected embeddings on partial data."""
    languages = sorted(set(m['language'] for m in metadata))
    logger.info(f'Languages in partial data: {languages}')
    
    centers = {}
    for lang in languages:
        mask = np.array([m.get('language') == lang for m in metadata])
        if np.sum(mask) > 0:
            centers[lang] = embeddings[mask].mean(axis=0)
            logger.info(f'  {lang}: {np.sum(mask)} decisions, center norm={np.linalg.norm(centers[lang]):.4f}')
    
    debiased = np.copy(embeddings)
    for i, m in enumerate(metadata):
        lang = m.get('language')
        if lang in centers:
            debiased[i] = embeddings[i] - centers[lang]
    
    # L2 normalize
    norms = np.linalg.norm(debiased, axis=1, keepdims=True)
    norms[norms == 0] = 1
    debiased = debiased / norms
    
    logger.info(f'Center projected shape: {debiased.shape}')
    norms = np.linalg.norm(debiased, axis=1)
    logger.info(f'Norm stats: min={norms.min():.6f}, max={norms.max():.6f}, mean={norms.mean():.6f}')
    
    return debiased


def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
    k_actual = min(k, len(embeddings) - 1)
    graph = kneighbors_graph(embeddings, n_neighbors=k_actual, metric='euclidean',
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
        weights='weight', resolution_parameter=resolution, seed=seed)
    return np.array(partition.membership), partition.modularity


def hierarchical_leiden(embeddings, metadata, coarse_res=0.5, sub_res=3.0, k=15):
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    logger.info(f'  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}')
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    coarse_to_fine = defaultdict(list)
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        if len(indices) < 20:
            hierarchical_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': 0, 'size': int(len(indices)), 'too_small': True}
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
            continue
        subset_embeddings = embeddings[indices]
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        logger.info(f'    Coarse {coarse_id} ({len(indices)} docs): {len(unique_sub)} sub-clusters, modularity={sub_mod:.4f}')
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            hierarchical_labels[global_indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': int(sub_id),
                'size': int(len(global_indices)), 'too_small': False}
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
    return hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine


def compute_cluster_metadata(labels, metadata):
    unique_labels = np.unique(labels[labels != -1])
    cluster_info = {}
    for label in unique_labels:
        mask = labels == label
        indices = np.where(mask)[0]
        cluster_meta = [metadata[i] for i in indices]
        
        langs = Counter(m.get('language') for m in cluster_meta if m.get('language'))
        dominant_lang = langs.most_common(1)[0] if langs else (None, 0)
        lang_purity = dominant_lang[1] / len(indices) if len(indices) > 0 else 0
        
        branches = Counter(m.get('branch') for m in cluster_meta if m.get('branch'))
        dominant_branch = branches.most_common(1)[0] if branches else (None, 0)
        branch_purity = dominant_branch[1] / len(indices) if len(indices) > 0 else 0
        
        areas = Counter(m.get('legal_area') for m in cluster_meta if m.get('legal_area'))
        dominant_area = areas.most_common(1)[0] if areas else (None, 0)
        
        years = Counter(m.get('year') for m in cluster_meta if m.get('year'))
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
            'decision_indices': indices.tolist(),
        }
    return cluster_info


def build_zoom_mappings(labels_by_res):
    resolutions = sorted(labels_by_res.keys())
    zoom_mappings = {}
    
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        coarse_labels = labels_by_res[coarser_res]
        fine_labels = labels_by_res[finer_res]
        
        parent_to_children = defaultdict(list)
        child_to_parent = {}
        
        for fine_id in np.unique(fine_labels[fine_labels != -1]):
            fine_mask = fine_labels == fine_id
            parent_labels = coarse_labels[fine_mask]
            parent_labels_valid = parent_labels[parent_labels != -1]
            if len(parent_labels_valid) > 0:
                parent = int(Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
                child_to_parent[int(fine_id)] = parent
                parent_to_children[parent].append(int(fine_id))
        
        zoom_mappings[f"{coarser_res}_to_{finer_res}"] = {
            'parent_to_children': {str(k): v for k, v in parent_to_children.items()},
            'child_to_parent': {str(k): v for k, v in child_to_parent.items()},
        }
    
    return zoom_mappings


def build_zoom_coherence(labels_by_res, metadata):
    resolutions = sorted(labels_by_res.keys())
    zoom_coherence = {}
    
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        coarse_labels = labels_by_res[coarser_res]
        fine_labels = labels_by_res[finer_res]
        
        child_to_parent = {}
        for fine_id in np.unique(fine_labels[fine_labels != -1]):
            fine_mask = fine_labels == fine_id
            parent_labels = coarse_labels[fine_mask]
            parent_labels_valid = parent_labels[parent_labels != -1]
            if len(parent_labels_valid) > 0:
                child_to_parent[int(fine_id)] = int(
                    Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
        
        parent_details = {}
        improvements = []
        
        for coarse_id in np.unique(coarse_labels[coarse_labels != -1]):
            coarse_mask = coarse_labels == coarse_id
            coarse_indices = np.where(coarse_mask)[0]
            if len(coarse_indices) < MIN_CLUSTER_SIZE:
                continue
            coarse_branches = [metadata[j].get('branch') for j in coarse_indices]
            coarse_branches = [b for b in coarse_branches if b and b != 'unknown' and b != 'null']
            if not coarse_branches:
                continue
            coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
            
            child_clusters = [fc for fc, pc in child_to_parent.items() if pc == coarse_id]
            child_purities = []
            for fc in child_clusters:
                fine_mask = fine_labels == fc
                fine_indices = np.where(fine_mask)[0]
                if len(fine_indices) < MIN_CLUSTER_SIZE:
                    continue
                fine_branches = [metadata[j].get('branch') for j in fine_indices]
                fine_branches = [b for b in fine_branches if b and b != 'unknown' and b != 'null']
                if fine_branches:
                    child_purities.append(Counter(fine_branches).most_common(1)[0][1] / len(fine_branches))
            
            if child_purities:
                mean_child_purity = np.mean(child_purities)
                improvements.append(mean_child_purity - coarse_purity)
                parent_details[int(coarse_id)] = {
                    'coarse_purity': float(coarse_purity),
                    'mean_child_purity': float(mean_child_purity),
                    'improvement': float(mean_child_purity - coarse_purity),
                    'n_children': len(child_clusters),
                }
        
        zoom_coherence[f"{coarser_res}_to_{finer_res}"] = {
            'parent_details': parent_details,
            'overall': {
                'mean_improvement': float(np.mean(improvements)) if improvements else 0.0,
                'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)) if improvements else 0.0,
                'n_parents': len(parent_details),
            }
        }
    
    return zoom_coherence


def build_artifacts(embeddings, metadata):
    """Build all artifacts for the partial dense hierarchical config."""
    mode_id = MODE_ID
    logger.info(f'\n=== Building artifacts for {mode_id} ===')
    logger.info(f'Embeddings: {embeddings.shape}')
    logger.info(f'Metadata: {len(metadata)} decisions')
    
    # Run flat Leiden at all resolutions
    labels_by_res = {}
    for res in RESOLUTIONS:
        labels, mod = leiden_clustering(embeddings, resolution=res, k=K)
        labels_by_res[res] = labels
        n_clusters = len(np.unique(labels[labels != -1]))
        logger.info(f'  Flat res={res}: {n_clusters} clusters')
    
    # Run hierarchical Leiden (validated config)
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden(
        embeddings, metadata, coarse_res=COARSE_RES, sub_res=SUB_RES)
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    logger.info(f'  Hierarchical: {n_coarse} coarse -> {n_fine} fine clusters')
    
    # Create output directory
    mode_dir = OUTPUT_BASE / mode_id
    mode_dir.mkdir(parents=True, exist_ok=True)
    
    # Save labels
    for res in RESOLUTIONS:
        np.save(mode_dir / f"labels_res_{res}.npy", labels_by_res[res].astype(np.int32))
    np.save(mode_dir / f"labels_coarse_{COARSE_RES}.npy", coarse_labels.astype(np.int32))
    np.save(mode_dir / f"labels_hierarchical_best.npy", hierarchical_labels.astype(np.int32))
    
    # Build cluster metadata
    cluster_metadata = {}
    for res in RESOLUTIONS:
        cluster_metadata[f"res_{res}"] = compute_cluster_metadata(labels_by_res[res], metadata)
    
    # Hierarchical metadata
    cluster_metadata['hierarchical'] = compute_cluster_metadata(hierarchical_labels, metadata)
    cluster_metadata['coarse'] = compute_cluster_metadata(coarse_labels, metadata)
    
    with open(mode_dir / "cluster_metadata.json", 'w') as f:
        json.dump(cluster_metadata, f, indent=2)
    
    # Build decision clusters
    decision_clusters = {}
    for i, m in enumerate(metadata):
        decision_clusters[m['decision_id']] = {}
        for res in RESOLUTIONS:
            decision_clusters[m['decision_id']][f"res_{res}"] = int(labels_by_res[res][i])
        decision_clusters[m['decision_id']][f"hierarchical"] = int(hierarchical_labels[i])
        decision_clusters[m['decision_id']][f"coarse_{COARSE_RES}"] = int(coarse_labels[i])
    
    with open(mode_dir / "decision_clusters.json", 'w') as f:
        json.dump(decision_clusters, f, indent=2)
    
    # Build zoom mappings
    zoom_mappings = build_zoom_mappings(labels_by_res)
    # Add hierarchical zoom mappings
    child_to_parent = {}
    for fine_id in np.unique(hierarchical_labels[hierarchical_labels != -1]):
        fine_mask = hierarchical_labels == fine_id
        parent_labels = coarse_labels[fine_mask]
        parent_labels_valid = parent_labels[parent_labels != -1]
        if len(parent_labels_valid) > 0:
            child_to_parent[int(fine_id)] = int(Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
    
    parent_to_children = defaultdict(list)
    for child, parent in child_to_parent.items():
        parent_to_children[parent].append(child)
    
    zoom_mappings[f"hierarchical_coarse_{COARSE_RES}_to_fine"] = {
        'parent_to_children': {str(k): v for k, v in parent_to_children.items()},
        'child_to_parent': {str(k): v for k, v in child_to_parent.items()},
    }
    
    with open(mode_dir / "zoom_mappings.json", 'w') as f:
        json.dump(zoom_mappings, f, indent=2)
    
    # Build zoom coherence
    zoom_coherence = build_zoom_coherence(labels_by_res, metadata)
    
    # Add hierarchical zoom coherence
    parent_details = {}
    improvements = []
    for coarse_id in np.unique(coarse_labels[coarse_labels != -1]):
        coarse_mask = coarse_labels == coarse_id
        coarse_indices = np.where(coarse_mask)[0]
        if len(coarse_indices) < MIN_CLUSTER_SIZE:
            continue
        coarse_branches = [metadata[j].get('branch') for j in coarse_indices]
        coarse_branches = [b for b in coarse_branches if b and b != 'unknown' and b != 'null']
        if not coarse_branches:
            continue
        coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
        
        fine_labels_in_coarse = hierarchical_labels[coarse_indices]
        unique_fine = np.unique(fine_labels_in_coarse[fine_labels_in_coarse != -1])
        child_purities = []
        for fine_id in unique_fine:
            fine_mask = hierarchical_labels == fine_id
            fine_indices = np.where(fine_mask)[0]
            if len(fine_indices) < MIN_CLUSTER_SIZE:
                continue
            fine_branches = [metadata[j].get('branch') for j in fine_indices]
            fine_branches = [b for b in fine_branches if b and b != 'unknown' and b != 'null']
            if fine_branches:
                child_purities.append(Counter(fine_branches).most_common(1)[0][1] / len(fine_branches))
        
        if child_purities:
            mean_child_purity = np.mean(child_purities)
            improvements.append(mean_child_purity - coarse_purity)
            parent_details[int(coarse_id)] = {
                'coarse_purity': float(coarse_purity),
                'mean_child_purity': float(mean_child_purity),
                'improvement': float(mean_child_purity - coarse_purity),
                'n_children': len(child_purities),
            }
    
    zoom_coherence[f"hierarchical_coarse_{COARSE_RES}_to_fine"] = {
        'parent_details': parent_details,
        'overall': {
            'mean_improvement': float(np.mean(improvements)) if improvements else 0.0,
            'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)) if improvements else 0.0,
            'n_parents': len(parent_details),
        }
    }
    
    with open(mode_dir / "zoom_coherence.json", 'w') as f:
        json.dump(zoom_coherence, f, indent=2)
    
    # Build integration summary
    integration_summary = {
        'mode_id': mode_id,
        'description': f'PARTIAL SCALE VALIDATION: Hierarchical Leiden on center_projected_768 (language-debiased) for years 2000-2002 (~12k decisions). coarse_res={COARSE_RES}, sub_res={SUB_RES}. NOT 174k scale.',
        'embedding_type': 'center_projected_768_partial',
        'hierarchical_config': {'coarse_res': COARSE_RES, 'sub_res': SUB_RES, 'name': f'coarse_{COARSE_RES}_sub_{SUB_RES}'},
        'n_decisions': len(metadata),
        'n_coarse_clusters': n_coarse,
        'n_fine_clusters': n_fine,
        'nesting': 1.0,
        'resolutions': RESOLUTIONS,
        'artifacts': {
            'cluster_metadata': f'legal_distance_modes/{mode_id}/cluster_metadata.json',
            'zoom_mappings': f'legal_distance_modes/{mode_id}/zoom_mappings.json',
            'zoom_coherence': f'legal_distance_modes/{mode_id}/zoom_coherence.json',
            'decision_clusters': f'legal_distance_modes/{mode_id}/decision_clusters.json',
        },
        'scale_note': 'PARTIAL - years 2000-2002 only (~12k decisions). Full 174k awaits legal-distance year-split completion.',
    }
    
    with open(mode_dir / "integration_summary.json", 'w') as f:
        json.dump(integration_summary, f, indent=2)
    
    # Build hierarchical map results
    hierarchical_map_results = {
        'mode_id': mode_id,
        'description': integration_summary['description'],
        'n_decisions': len(metadata),
        'resolutions': RESOLUTIONS,
        'n_resolutions': len(RESOLUTIONS),
        'cluster_counts': {f"res_{res}": len(np.unique(labels_by_res[res][labels_by_res[res] != -1])) for res in RESOLUTIONS},
        'cluster_metadata': cluster_metadata,
    }
    
    with open(mode_dir / "hierarchical_map_results.json", 'w') as f:
        json.dump(hierarchical_map_results, f, indent=2)
    
    logger.info(f'Artifacts saved to {mode_dir}')
    return mode_dir, integration_summary, labels_by_res, hierarchical_labels, coarse_labels, zoom_coherence


def main():
    logger.info('=' * 70)
    logger.info('PARTIAL SCALE VALIDATION: Dense Hierarchical Leiden on Years 2000-2002')
    logger.info('=' * 70)
    logger.info(f'Timestamp: {datetime.now(timezone.utc).isoformat()}')
    logger.info(f'Scale: ~12k decisions (years 2000-2002)')
    logger.info(f'Full 174k awaits legal-distance_174k_dense_embeddings completion')
    logger.info('=' * 70)
    
    # Load partial embeddings and metadata
    embeddings, metadata = load_partial_embeddings_and_metadata()
    
    # Compute center_projected on partial data
    center_projected = compute_center_projected(embeddings, metadata)
    
    # Build artifacts
    mode_dir, summary, labels_by_res, hierarchical_labels, coarse_labels, zoom_coherence = build_artifacts(center_projected, metadata)
    
    # Print key results
    logger.info('\n=== KEY RESULTS ===')
    logger.info(f'Mode: {MODE_ID}')
    logger.info(f'Decisions: {summary["n_decisions"]}')
    logger.info(f'Coarse clusters (res={COARSE_RES}): {summary["n_coarse_clusters"]}')
    logger.info(f'Fine clusters (sub_res={SUB_RES}): {summary["n_fine_clusters"]}')
    logger.info(f'Nesting (by construction): 1.0')
    
    # Hierarchical zoom coherence
    h_key = f"hierarchical_coarse_{COARSE_RES}_to_fine"
    if h_key in zoom_coherence:
        hc = zoom_coherence[h_key]['overall']
        logger.info(f'Hierarchical improvement_rate: {hc["improvement_rate"]:.4f}')
        logger.info(f'Hierarchical mean_improvement: {hc["mean_improvement"]:.4f}')
        logger.info(f'Hierarchical n_parents: {hc["n_parents"]}')
    
    # Flat zoom coherence
    logger.info('\nFlat zoom coherence (branch):')
    for res_key, zc in zoom_coherence.items():
        if res_key.startswith('0.') or res_key.startswith('1.') or res_key.startswith('2.'):
            o = zc['overall']
            logger.info(f'  {res_key}: improvement_rate={o["improvement_rate"]:.4f}, mean_improvement={o["mean_improvement"]:.4f}, n_parents={o["n_parents"]}')
    
    # Fragmentation check
    logger.info('\nFragmentation (singleton fraction):')
    for res in RESOLUTIONS:
        labels = labels_by_res[res]
        vals, counts = np.unique(labels[labels != -1], return_counts=True)
        singleton_frac = np.mean(counts == 1)
        logger.info(f'  res_{res}: {len(vals)} clusters, median_size={np.median(counts):.1f}, singleton_frac={singleton_frac:.4f}')
    
    logger.info('\n=== PARTIAL SCALE VALIDATION COMPLETE ===')
    logger.info('NOTE: This is NOT a 174k evaluation. Full 174k awaits legal-distance year-split completion.')
    
    return mode_dir, summary


if __name__ == '__main__':
    main()