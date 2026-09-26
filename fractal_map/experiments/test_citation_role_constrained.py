#!/usr/bin/env python3
"""
Test Constrained Hierarchical Leiden on citation-role hybrid embeddings
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
from sklearn.preprocessing import normalize

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def load_center_projected():
    """Load center_projected embeddings and metadata."""
    emb_path = '/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy'
    meta_path = '/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/metadata.json'
    
    embeddings = np.load(emb_path)
    with open(meta_path) as f:
        metadata = json.load(f)
    
    logger.info(f"Loaded center_projected: {embeddings.shape}")
    return embeddings, metadata

def load_resolved_roles():
    """Load resolved role annotations."""
    roles_path = '/tmp/lex_accepted/legal-distance/legal_distance/results/v7/citation_id_resolution_bge/citation_roles_resolved.json'
    with open(roles_path) as f:
        roles = json.load(f)
    logger.info(f"Loaded {len(roles)} resolved role annotations")
    return roles

def build_role_vectors(roles, decision_ids, role_name):
    """Build role count vector for a specific role."""
    did_to_idx = {did: i for i, did in enumerate(decision_ids)}
    n = len(decision_ids)
    vec = np.zeros(n, dtype=np.float32)
    
    for role_anno in roles:
        if not role_anno.get('resolved', False):
            continue
        if role_anno.get('role') != role_name:
            continue
        target_did = role_anno.get('resolved_decision_id')
        if target_did in did_to_idx:
            vec[did_to_idx[target_did]] += 1
    
    # Normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    
    return vec

def create_hybrid_role_embeddings(center_projected, role_vectors, alpha=0.3):
    """Create hybrid embeddings: alpha * center_projected + (1-alpha) * role_vector."""
    n = center_projected.shape[0]
    cp_norm = normalize(center_projected, axis=1)
    
    hybrids = {}
    for role, rv in role_vectors.items():
        rv_2d = rv.reshape(-1, 1)
        hybrid = alpha * cp_norm + (1 - alpha) * rv_2d
        hybrid = normalize(hybrid, axis=1)
        hybrids[f"{role}_alpha{alpha:.1f}"] = hybrid
    
    return hybrids

def leiden_clustering(embeddings, resolution=1.0, k=15, seed=42):
    """Leiden clustering on embeddings."""
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

def constrained_hierarchical_leiden(embeddings, metadata, 
                                    coarse_res=0.5,  # Use 0.5 as in legal-distance validation
                                    base_sub_res=3.0,
                                    min_cluster_size=10,
                                    max_subclusters_per_parent=20,
                                    adaptive_sub_res=True,
                                    k=15):
    """Constrained Hierarchical Leiden."""
    logger.info(f"Running constrained hierarchical Leiden: coarse_res={coarse_res}, base_sub_res={base_sub_res}")
    
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")
    
    hierarchical_labels = np.full(len(embeddings), -1, dtype=int)
    sub_cluster_id = 0
    cluster_info = {}
    coarse_to_fine = defaultdict(list)
    
    for coarse_id in unique_coarse:
        mask = coarse_labels == coarse_id
        indices = np.where(mask)[0]
        cluster_size = len(indices)
        
        if cluster_size < min_cluster_size * 2:
            hierarchical_labels[indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': 0,
                'size': cluster_size, 'too_small': True,
                'sub_res_used': None
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
            continue
        
        subset_embeddings = embeddings[indices]
        
        if adaptive_sub_res:
            if cluster_size < 500:
                sub_res = 1.5
            elif cluster_size < 2000:
                sub_res = 2.0
            else:
                sub_res = base_sub_res
        else:
            sub_res = base_sub_res
        
        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])
        
        valid_sub = []
        for sub_id in unique_sub:
            sub_mask = sub_labels == sub_id
            sub_size = sub_mask.sum()
            if sub_size >= min_cluster_size:
                valid_sub.append(sub_id)
        
        if len(valid_sub) > max_subclusters_per_parent:
            logger.warning(f"    Coarse {coarse_id}: {len(valid_sub)} sub-clusters > max {max_subclusters_per_parent}, merging smallest")
            sub_sizes = [(sid, (sub_labels == sid).sum()) for sid in valid_sub]
            sub_sizes.sort(key=lambda x: x[1], reverse=True)
            valid_sub = [sid for sid, _ in sub_sizes[:max_subclusters_per_parent]]
        
        logger.info(f"    Coarse {coarse_id} ({cluster_size} docs): {len(valid_sub)} sub-clusters (sub_res={sub_res:.1f}), modularity={sub_mod:.4f}")
        
        for sub_id in valid_sub:
            sub_mask = sub_labels == sub_id
            global_indices = indices[sub_mask]
            hierarchical_labels[global_indices] = sub_cluster_id
            
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': int(sub_id),
                'size': int(len(global_indices)), 'too_small': False,
                'sub_res_used': sub_res
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
        
        assigned_mask = np.isin(sub_labels, valid_sub)
        unassigned_indices = indices[~assigned_mask]
        if len(unassigned_indices) > 0:
            hierarchical_labels[unassigned_indices] = sub_cluster_id
            cluster_info[sub_cluster_id] = {
                'coarse_id': int(coarse_id), 'sub_id': -1,
                'size': int(len(unassigned_indices)), 'too_small': False,
                'sub_res_used': sub_res, 'is_remainder': True
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
    
    logger.info(f"  Hierarchical: {len(unique_coarse)} coarse -> {sub_cluster_id} fine clusters")
    return hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine

def compute_branch_purity(labels, metadata):
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'unknown' and b != 'null']
        if cluster_branches:
            purities.append(Counter(cluster_branches).most_common(1)[0][1] / len(cluster_branches))
    return float(np.mean(purities)) if purities else 0

def compute_area_purity(labels, metadata):
    unique_labels = np.unique(labels[labels != -1])
    purities = []
    for label in unique_labels:
        mask = labels == label
        cluster_areas = [metadata[i].get('legal_area') for i in np.where(mask)[0]]
        cluster_areas = [a for a in cluster_areas if a and a != 'unknown' and a != 'null']
        if cluster_areas:
            purities.append(Counter(cluster_areas).most_common(1)[0][1] / len(cluster_areas))
    return float(np.mean(purities)) if purities else 0

def compute_fragmentation(labels):
    vals, counts = np.unique(labels[labels != -1], return_counts=True)
    n = len(vals)
    if n == 0:
        return {'n_clusters': 0, 'median_size': None, 'singleton_fraction': None}
    size_dist = Counter(counts.tolist())
    return {
        'n_clusters': int(n),
        'median_size': float(np.median(counts)),
        'mean_size': float(np.mean(counts)),
        'singleton_fraction': round(float(np.mean(counts == 1)), 4),
        'size_distribution': {str(k): int(v) for k, v in sorted(size_dist.items())},
        'max_size': int(np.max(counts)),
        'min_size': int(np.min(counts)),
    }

def compute_zoom_coherence_hierarchical(coarse_labels, hierarchical_labels, metadata, min_cluster_size=10):
    parent_details = {}
    improvements = []
    
    child_to_parent = {}
    for fine_id in np.unique(hierarchical_labels[hierarchical_labels != -1]):
        fine_mask = hierarchical_labels == fine_id
        parent_labels = coarse_labels[fine_mask]
        parent_labels_valid = parent_labels[parent_labels != -1]
        if len(parent_labels_valid) > 0:
            child_to_parent[int(fine_id)] = int(Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
    
    for coarse_id in np.unique(coarse_labels[coarse_labels != -1]):
        coarse_mask = coarse_labels == coarse_id
        coarse_indices = np.where(coarse_mask)[0]
        if len(coarse_indices) < min_cluster_size:
            continue
        coarse_branches = [metadata[j].get('branch') for j in coarse_indices]
        coarse_branches = [b for b in coarse_branches if b and b != 'unknown' and b != 'null']
        if not coarse_branches:
            continue
        coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
        
        child_clusters = [fc for fc, pc in child_to_parent.items() if pc == coarse_id]
        child_purities = []
        for fc in child_clusters:
            fine_mask = hierarchical_labels == fc
            fine_indices = np.where(fine_mask)[0]
            if len(fine_indices) < min_cluster_size:
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
    
    return {
        'parent_details': parent_details,
        'overall': {
            'mean_improvement': float(np.mean(improvements)) if improvements else 0.0,
            'improvement_rate': float(sum(1 for j in improvements if j > 0) / len(improvements)) if improvements else 0.0,
            'n_parents': len(parent_details),
        }
    }

def main():
    # Load center_projected embeddings
    center_projected, metadata = load_center_projected()
    decision_ids = [m['decision_id'] for m in metadata]
    logger.info(f"Center projected: {len(center_projected)} decisions, {center_projected.shape[1]} dims")
    
    # Load resolved roles
    roles = load_resolved_roles()
    
    # Build role vectors for citing, following, criticizing
    role_names = ['citing', 'following', 'criticizing']
    role_vectors = {}
    for role in role_names:
        vec = build_role_vectors(roles, decision_ids, role)
        non_zero = (vec != 0).sum()
        logger.info(f"  {role}: {non_zero}/{len(vec)} non-zero")
        role_vectors[role] = vec
    
    # Create hybrids at alpha=0.3 (as used in legal-distance validation)
    hybrids = create_hybrid_role_embeddings(center_projected, role_vectors, alpha=0.3)
    
    # Test each hybrid
    OUTPUT_DIR = Path('/home/runner/work/LexMachina/LexMachina/results/fractal_map/constrained_hierarchical_tests')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    for name, embeddings in hybrids.items():
        logger.info(f"\n=== Testing {name} ===")
        
        hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = constrained_hierarchical_leiden(
            embeddings, metadata,
            coarse_res=0.5,  # Match legal-distance validation
            base_sub_res=3.0,
            min_cluster_size=10,
            max_subclusters_per_parent=20,
            adaptive_sub_res=True,
            k=15
        )
        
        coarse_purity = compute_branch_purity(coarse_labels, metadata)
        hierarchical_purity = compute_branch_purity(hierarchical_labels, metadata)
        coarse_area_purity = compute_area_purity(coarse_labels, metadata)
        hierarchical_area_purity = compute_area_purity(hierarchical_labels, metadata)
        
        frag_hierarchical = compute_fragmentation(hierarchical_labels)
        frag_coarse = compute_fragmentation(coarse_labels)
        
        zoom_coherence = compute_zoom_coherence_hierarchical(coarse_labels, hierarchical_labels, metadata)
        
        logger.info(f"Coarse clusters: {len(set(coarse_labels[coarse_labels != -1]))}")
        logger.info(f"Hierarchical fine clusters: {len(set(hierarchical_labels[hierarchical_labels != -1]))}")
        logger.info(f"Coarse branch purity: {coarse_purity:.4f}")
        logger.info(f"Hierarchical branch purity: {hierarchical_purity:.4f}")
        logger.info(f"Hierarchical fragmentation: singleton_fraction={frag_hierarchical['singleton_fraction']:.4f}")
        logger.info(f"Zoom coherence: improvement_rate={zoom_coherence['overall']['improvement_rate']:.4f}, "
                    f"mean_improvement={zoom_coherence['overall']['mean_improvement']:.4f}")
        
        # Save results
        output = {
            'run_id': f"constrained_hierarchical_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'mode': name,
            'sample_size': len(embeddings),
            'config': {
                'coarse_res': 0.5,
                'base_sub_res': 3.0,
                'min_cluster_size': 10,
                'max_subclusters_per_parent': 20,
                'adaptive_sub_res': True,
            },
            'coarse': {
                'n_clusters': len(set(coarse_labels[coarse_labels != -1])),
                'branch_purity': coarse_purity,
                'area_purity': coarse_area_purity,
                'fragmentation': frag_coarse,
            },
            'hierarchical': {
                'n_clusters': len(set(hierarchical_labels[hierarchical_labels != -1])),
                'branch_purity': hierarchical_purity,
                'area_purity': hierarchical_area_purity,
                'fragmentation': frag_hierarchical,
                'nesting': 1.0,
            },
            'zoom_coherence': zoom_coherence,
            'cluster_info': cluster_info,
        }
        
        output_path = OUTPUT_DIR / f"constrained_hierarchical_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        logger.info(f"Results saved to {output_path}")

if __name__ == '__main__':
    main()
