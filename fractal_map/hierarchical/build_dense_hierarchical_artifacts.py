#!/usr/bin/env python3
"""
Build fractal map artifacts for dense embedding hierarchical Leiden configurations.
Creates artifacts compatible with product integration loader.
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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASE = Path('/home/runner/work/LexMachina/LexMachina')
BASELINE_DIR = BASE / 'results/fractal_map/baseline'
DEBIASING_DIR = BASE / 'results/fractal_map/language_debiasing'
OUTPUT_BASE = BASE / 'results/fractal_map/legal_distance_modes'

CORPUS_DIR = Path('/tmp/lex_accepted/corpus/corpus/normalization/canonical')

# Configs to build artifacts for
CONFIGS = [
    {
        'mode_id': 'center_projected_hierarchical_dense',
        'embedding_type': 'center_projected',
        'embedding_path': DEBIASING_DIR / 'embeddings_center_projected.npy',
        'config': {'coarse_res': 0.25, 'sub_res': 2.0, 'name': 'coarse_0.25_sub_2.0'},
        'description': 'Hierarchical Leiden on pure center_projected_768 (dense, language-debiased). coarse_0.25_sub_2.0: 3→31 clusters, improvement_rate=1.0, zero fragmentation.',
    },
    {
        'mode_id': 'center_projected_hierarchical_dense_v2',
        'embedding_type': 'center_projected',
        'embedding_path': DEBIASING_DIR / 'embeddings_center_projected.npy',
        'config': {'coarse_res': 0.25, 'sub_res': 3.0, 'name': 'coarse_0.25_sub_3.0'},
        'description': 'Hierarchical Leiden on pure center_projected_768 (dense, language-debiased). coarse_0.25_sub_3.0: 3→49 clusters, improvement_rate=1.0, zero fragmentation.',
    },
    {
        'mode_id': 'concat_hierarchical_dense',
        'embedding_type': 'concat',
        'embedding_path': None,  # Built from center_projected + TF-IDF
        'config': {'coarse_res': 0.5, 'sub_res': 3.0, 'name': 'coarse_0.5_sub_3.0'},
        'description': 'Hierarchical Leiden on concat (center_projected_768 + TF-IDF_128). coarse_0.5_sub_3.0: 8→98 clusters, improvement_rate=0.75, low fragmentation.',
    },
]

RESOLUTIONS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
MIN_CLUSTER_SIZE = 3
K = 15


def load_metadata_with_branch():
    with open(BASELINE_DIR / 'metadata.json') as f:
        metadata = json.load(f)
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    branch_map = {}
    for year_file in sorted(CORPUS_DIR.glob('bger_20*.jsonl')):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                did = d.get('decision_id', '')
                if did in id_to_idx:
                    branch_map[did] = d.get('branch')
    for m in metadata:
        m['branch'] = branch_map.get(m['decision_id'])
    return id_to_idx, metadata


def load_center_projected():
    return np.load(DEBIASING_DIR / 'embeddings_center_projected.npy')


def load_baseline():
    return np.load(BASELINE_DIR / 'embeddings.npy')


def extract_erwaegungen(text, language):
    if not text:
        return ''
    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')
    if language == 'de':
        patterns = [r'(?:In\s+Erwägung\s*:)\s*\n', r'(?:Erwägungen\s*:)\s*\n']
    elif language == 'fr':
        patterns = [r'(?:Considérant\s+en\s+droit\s*:)\s*\n', r'(?:Considérant\s*:)\s*\n']
    elif language == 'it':
        patterns = [r'(?:Considerando\s+in\s+diritto\s*:)\s*\n', r'(?:Considerando\s*:)\s*\n']
    else:
        return ''
    start = -1
    for pattern in patterns:
        match = re.search(pattern, text_norm, re.IGNORECASE)
        if match:
            start = match.end()
            break
    if start == -1:
        return ''
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
    baseline_ids = set(m['decision_id'] for m in metadata)
    decisions = {}
    for year_file in sorted(CORPUS_DIR.glob('bger_20*.jsonl')):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                if d['decision_id'] in baseline_ids:
                    decisions[d['decision_id']] = d
    return decisions


def compute_tfidf_erwaegungen(metadata, decisions):
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
    vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1, 2), sublinear_tf=True,
                                 min_df=2, max_df=0.95, strip_accents='unicode')
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
    concat = np.concatenate([center_emb, tfidf_full], axis=1)
    norms = np.linalg.norm(concat, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return concat / norms


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
    """Build bidirectional zoom mappings between consecutive resolutions."""
    resolutions = sorted(labels_by_res.keys())
    zoom_mappings = {}
    
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        coarse_labels = labels_by_res[coarser_res]
        fine_labels = labels_by_res[finer_res]
        
        # Build parent->children mapping
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
    """Build zoom coherence metrics between consecutive resolutions."""
    resolutions = sorted(labels_by_res.keys())
    zoom_coherence = {}
    
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        coarse_labels = labels_by_res[coarser_res]
        fine_labels = labels_by_res[finer_res]
        
        # Build child->parent mapping
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


def build_artifacts(config_spec, metadata, id_to_idx):
    """Build all artifacts for a hierarchical Leiden config."""
    mode_id = config_spec['mode_id']
    config = config_spec['config']
    embedding_type = config_spec['embedding_type']
    
    logger.info(f"\n=== Building artifacts for {mode_id} ===")
    
    # Load/generate embeddings
    if embedding_type == 'center_projected':
        embeddings = load_center_projected()
    elif embedding_type == 'concat':
        baseline_emb = load_baseline()
        center_emb = load_center_projected()
        decisions = load_corpus_decisions(metadata)
        tfidf_full, _ = compute_tfidf_erwaegungen(metadata, decisions)
        embeddings = build_concat(baseline_emb, center_emb, tfidf_full)
    else:
        raise ValueError(f"Unknown embedding_type: {embedding_type}")
    
    logger.info(f"Embeddings: {embeddings.shape}")
    
    # Run flat Leiden at all resolutions
    labels_by_res = {}
    for res in RESOLUTIONS:
        labels, mod = leiden_clustering(embeddings, resolution=res, k=K)
        labels_by_res[res] = labels
        n_clusters = len(np.unique(labels[labels != -1]))
        logger.info(f"  Flat res={res}: {n_clusters} clusters")
    
    # Run hierarchical Leiden (validated config)
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden(
        embeddings, metadata, coarse_res=config['coarse_res'], sub_res=config['sub_res'])
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    logger.info(f"  Hierarchical: {n_coarse} coarse -> {n_fine} fine clusters")
    
    # Create output directory
    mode_dir = OUTPUT_BASE / mode_id
    mode_dir.mkdir(parents=True, exist_ok=True)
    
    # Save labels
    for res in RESOLUTIONS:
        np.save(mode_dir / f"labels_res_{res}.npy", labels_by_res[res].astype(np.int32))
    np.save(mode_dir / f"labels_coarse_{config['coarse_res']}.npy", coarse_labels.astype(np.int32))
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
        decision_clusters[m['decision_id']][f"coarse_{config['coarse_res']}"] = int(coarse_labels[i])
    
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
    
    zoom_mappings[f"hierarchical_coarse_{config['coarse_res']}_to_fine"] = {
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
    
    zoom_coherence[f"hierarchical_coarse_{config['coarse_res']}_to_fine"] = {
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
        'description': config_spec['description'],
        'embedding_type': embedding_type,
        'hierarchical_config': config,
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
        }
    }
    
    with open(mode_dir / "integration_summary.json", 'w') as f:
        json.dump(integration_summary, f, indent=2)
    
    # Build hierarchical map results
    hierarchical_map_results = {
        'mode_id': mode_id,
        'description': config_spec['description'],
        'n_decisions': len(metadata),
        'resolutions': RESOLUTIONS,
        'n_resolutions': len(RESOLUTIONS),
        'cluster_counts': {f"res_{res}": len(np.unique(labels_by_res[res][labels_by_res[res] != -1])) for res in RESOLUTIONS},
        'cluster_metadata': cluster_metadata,
    }
    
    with open(mode_dir / "hierarchical_map_results.json", 'w') as f:
        json.dump(hierarchical_map_results, f, indent=2)
    
    logger.info(f"Artifacts saved to {mode_dir}")
    return mode_dir, integration_summary


def main():
    logger.info('=== Building Dense Hierarchical Leiden Artifacts ===')
    logger.info(f'Timestamp: {datetime.now(timezone.utc).isoformat()}')
    
    id_to_idx, metadata = load_metadata_with_branch()
    logger.info(f'Metadata: {len(metadata)} decisions')
    
    all_summaries = {}
    
    for config_spec in CONFIGS:
        mode_dir, summary = build_artifacts(config_spec, metadata, id_to_idx)
        all_summaries[config_spec['mode_id']] = summary
    
    # Update map mode registry
    registry_path = BASE / 'results/fractal_map/product_integration/map_mode_registry.json'
    with open(registry_path) as f:
        registry = json.load(f)
    
    for mode_id, summary in all_summaries.items():
        config = summary['hierarchical_config']
        registry['modes'][mode_id] = {
            'mode_id': mode_id,
            'name': mode_id.replace('_', ' ').title(),
            'description': summary['description'],
            'mode_type': 'hierarchical_leiden',
            'status': 'available',
            'is_default': False,
            'resolution_ladder': RESOLUTIONS,
            'artifacts': summary['artifacts'],
            'metadata': {
                'n_decisions': summary['n_decisions'],
                'n_coarse_clusters': summary['n_coarse_clusters'],
                'n_fine_clusters': summary['n_fine_clusters'],
                'nesting_score': 1.0,
                'hierarchical_config': config,
                'evidence_tier': 'ACCEPTED',
            },
            'legal_distance_config': None,
        }
    
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    logger.info(f"\nUpdated map mode registry: {registry_path}")
    logger.info('\n=== Build complete ===')


if __name__ == '__main__':
    main()
