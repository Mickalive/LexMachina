#!/usr/bin/env python3
"""
Test Hierarchical Leiden on 1000-scale dense embeddings (center_projected + TF-IDF concat).
This validates the evidence-backed zoom path: dense embeddings enable good hierarchical structure.
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
OUTPUT_DIR = BASE / 'results/fractal_map/hierarchical_dense_1000'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CORPUS_DIR = Path('/tmp/lex_accepted/corpus/corpus/normalization/canonical')

CONFIGS = [
    {'coarse_res': 0.25, 'sub_res': 2.0, 'name': 'coarse_0.25_sub_2.0'},
    {'coarse_res': 0.25, 'sub_res': 3.0, 'name': 'coarse_0.25_sub_3.0'},
    {'coarse_res': 0.5, 'sub_res': 2.0, 'name': 'coarse_0.5_sub_2.0'},
    {'coarse_res': 0.5, 'sub_res': 3.0, 'name': 'coarse_0.5_sub_3.0'},
    {'coarse_res': 1.0, 'sub_res': 3.0, 'name': 'coarse_1.0_sub_3.0'},
]

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


def load_representations():
    baseline_emb = np.load(BASELINE_DIR / 'embeddings.npy')
    center_emb = np.load(DEBIASING_DIR / 'embeddings_center_projected.npy')
    return baseline_emb, center_emb


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


def compute_purity(labels, metadata, field, min_cluster_size=MIN_CLUSTER_SIZE):
    purities = []
    for label in np.unique(labels[labels != -1]):
        mask = labels == label
        indices = np.where(mask)[0]
        if len(indices) < min_cluster_size:
            continue
        vals = [metadata[i].get(field) for i in indices]
        vals = [v for v in vals if v and v != 'unknown' and v != 'null']
        if vals:
            purities.append(Counter(vals).most_common(1)[0][1] / len(vals))
    return float(np.mean(purities)) if purities else 0


def compute_zoom_coherence_hierarchical(coarse_labels, fine_labels, metadata, min_cluster_size=MIN_CLUSTER_SIZE):
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])
    improvements = []
    n_parents = 0
    parent_details = {}
    for coarse_id in unique_coarse:
        coarse_mask = coarse_labels == coarse_id
        coarse_indices = np.where(coarse_mask)[0]
        if len(coarse_indices) < min_cluster_size:
            continue
        coarse_branches = [metadata[i].get('branch') for i in coarse_indices]
        coarse_branches = [b for b in coarse_branches if b and b != 'unknown' and b != 'null']
        if not coarse_branches:
            continue
        coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
        fine_labels_in_coarse = fine_labels[coarse_indices]
        unique_fine = np.unique(fine_labels_in_coarse[fine_labels_in_coarse != -1])
        child_purities = []
        for fine_id in unique_fine:
            fine_mask = fine_labels == fine_id
            fine_indices = np.where(fine_mask)[0]
            if len(fine_indices) < min_cluster_size:
                continue
            fine_branches = [metadata[i].get('branch') for i in fine_indices]
            fine_branches = [b for b in fine_branches if b and b != 'unknown' and b != 'null']
            if fine_branches:
                child_purities.append(Counter(fine_branches).most_common(1)[0][1] / len(fine_branches))
        if child_purities:
            mean_child_purity = np.mean(child_purities)
            improvements.append(mean_child_purity - coarse_purity)
            n_parents += 1
            parent_details[int(coarse_id)] = {
                'coarse_purity': round(float(coarse_purity), 4),
                'mean_child_purity': round(float(mean_child_purity), 4),
                'improvement': round(float(mean_child_purity - coarse_purity), 4),
                'n_children': len(child_purities),
            }
    return {
        'mean_improvement': round(float(np.mean(improvements)), 4) if improvements else None,
        'improvement_rate': round(float(sum(1 for j in improvements if j > 0) / len(improvements)), 4) if improvements else None,
        'n_parents': n_parents,
        'parent_details': parent_details,
    }


def compute_fragmentation(labels):
    vals, counts = np.unique(labels[labels != -1], return_counts=True)
    n = len(vals)
    if n == 0:
        return {'n_clusters': 0, 'median_size': None, 'singleton_fraction': None}
    return {
        'n_clusters': int(n),
        'median_size': float(np.median(counts)),
        'singleton_fraction': round(float(np.mean(counts == 1)), 4),
    }


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


def main():
    logger.info('=== Hierarchical Leiden on 1000-scale Dense Embeddings ===')
    logger.info(f'Timestamp: {datetime.now(timezone.utc).isoformat()}')
    
    id_to_idx, metadata = load_metadata_with_branch()
    baseline_emb, center_emb = load_representations()
    logger.info(f'Metadata: {len(metadata)} decisions')
    
    logger.info('Loading corpus decisions...')
    decisions = load_corpus_decisions(metadata)
    logger.info(f'Loaded {len(decisions)} decisions')
    
    logger.info('Computing TF-IDF Erwaegungen...')
    tfidf_full, valid_indices = compute_tfidf_erwaegungen(metadata, decisions)
    logger.info(f'TF-IDF: {tfidf_full.shape}, {len(valid_indices)} valid')
    
    logger.info('Building concatenated representation...')
    concat_emb = build_concat(baseline_emb, center_emb, tfidf_full)
    logger.info(f'Concat: {concat_emb.shape}')
    
    all_results = {}
    
    for config in CONFIGS:
        logger.info(f'\nConfig: {config["name"]}')
        hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden(
            concat_emb, metadata, coarse_res=config['coarse_res'], sub_res=config['sub_res'])
        
        n_fine_clusters = len(set(hierarchical_labels[hierarchical_labels != -1]))
        n_coarse_clusters = len(set(coarse_labels[coarse_labels != -1]))
        
        coarse_branch_purity = compute_purity(coarse_labels, metadata, 'branch')
        coarse_area_purity = compute_purity(coarse_labels, metadata, 'legal_area')
        fine_branch_purity = compute_purity(hierarchical_labels, metadata, 'branch')
        fine_area_purity = compute_purity(hierarchical_labels, metadata, 'legal_area')
        zoom_coherence = compute_zoom_coherence_hierarchical(coarse_labels, hierarchical_labels, metadata)
        frag_coarse = compute_fragmentation(coarse_labels)
        frag_fine = compute_fragmentation(hierarchical_labels)
        
        logger.info(f'  Coarse: {n_coarse_clusters} clusters, branch_pur={coarse_branch_purity:.4f}, area_pur={coarse_area_purity:.4f}')
        logger.info(f'  Fine: {n_fine_clusters} clusters, branch_pur={fine_branch_purity:.4f}, area_pur={fine_area_purity:.4f}')
        logger.info(f'  Zoom: mean_improvement={zoom_coherence["mean_improvement"]}, improvement_rate={zoom_coherence["improvement_rate"]}, n_parents={zoom_coherence["n_parents"]}')
        logger.info(f'  Frag coarse: median={frag_coarse["median_size"]}, singleton={frag_coarse["singleton_fraction"]}')
        logger.info(f'  Frag fine: median={frag_fine["median_size"]}, singleton={frag_fine["singleton_fraction"]}')
        logger.info(f'  Nesting: 1.0 (by construction)')
        
        config_result = {
            'config': config,
            'n_coarse_clusters': n_coarse_clusters,
            'n_fine_clusters': n_fine_clusters,
            'coarse_branch_purity': coarse_branch_purity,
            'fine_branch_purity': fine_branch_purity,
            'coarse_area_purity': coarse_area_purity,
            'fine_area_purity': fine_area_purity,
            'zoom_coherence': zoom_coherence,
            'fragmentation_coarse': frag_coarse,
            'fragmentation_fine': frag_fine,
            'nesting': 1.0,
            'cluster_info': cluster_info,
        }
        all_results[config['name']] = config_result
    
    # Also run flat Leiden for comparison
    logger.info('\nFlat Leiden comparison:')
    flat_labels = {}
    for res in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
        labels, mod = leiden_clustering(concat_emb, resolution=res)
        flat_labels[f'res_{res}'] = labels
        bp = compute_purity(labels, metadata, 'branch')
        ap = compute_purity(labels, metadata, 'legal_area')
        n_clusters = len(set(labels[labels != -1]))
        logger.info(f'  Flat res={res}: {n_clusters} clusters, branch_pur={bp:.4f}, area_pur={ap:.4f}')
    
    # Save
    output = {
        'run_id': f'hierarchical_dense_1000_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'direction_version': 27,
        'hypothesis': 'Hierarchical Leiden on dense embeddings (center_projected + TF-IDF concat) achieves perfect nesting and meaningful zoom refinement without over-fragmentation',
        'frozen_sample': f'{len(metadata)} BGer decisions (1000-scale)',
        'frozen_metric': 'Branch purity, area purity, zoom coherence (improvement rate), fragmentation (median cluster size), nesting',
        'success_rule': 'Fine branch purity > coarse branch purity AND improvement_rate > 0.5 AND fine median cluster size > 5 AND nesting = 1.0',
        'embedding': 'concat_center_projected_768_tfidf_128 (896-dim)',
        'configs_tested': [c['name'] for c in CONFIGS],
        'results': all_results,
        'flat_leiden_comparison': {k: {
            'n_clusters': len(set(v[v != -1])),
            'branch_purity': compute_purity(v, metadata, 'branch'),
            'area_purity': compute_purity(v, metadata, 'legal_area'),
        } for k, v in flat_labels.items()},
    }
    
    output_path = OUTPUT_DIR / f'hierarchical_dense_1000_results.json'
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    logger.info(f'\nResults saved to {output_path}')
    
    # Summary
    logger.info('\n' + '=' * 70)
    logger.info('SUMMARY')
    logger.info('=' * 70)
    for name, result in all_results.items():
        cr = result
        success = (cr['fine_branch_purity'] > cr['coarse_branch_purity'] and
                   (cr['zoom_coherence']['improvement_rate'] or 0) > 0.5 and
                   (cr['fragmentation_fine']['median_size'] or 0) > 5 and
                   cr['nesting'] == 1.0)
        logger.info(f'  {name}: branch_pur {cr["coarse_branch_purity"]:.4f}->{cr["fine_branch_purity"]:.4f}, '
                    f'rate={cr["zoom_coherence"]["improvement_rate"]}, '
                    f'fine_median={cr["fragmentation_fine"]["median_size"]}, '
                    f'singleton={cr["fragmentation_fine"]["singleton_fraction"]}, '
                    f'SUCCESS={success}')
    
    logger.info('\n=== Experiment complete ===')


if __name__ == '__main__':
    main()
