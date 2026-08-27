#!/usr/bin/env python3
"""
Zoom Coherence Experiment

Tests whether zooming from coarse to fine clustering resolution reveals
legally coherent substructure, or merely splits clusters arbitrarily.

Hypothesis: Finer resolutions reveal more specific legal structure within
language-homogeneous clusters. The legal purity ratio (legal purity / language
purity) should improve at finer resolutions within clusters that are already
language-homogeneous.

Product decision: If zoom reveals coherent substructure, the fractal map
architecture is justified. If not, a flat map may suffice.

Frozen before observation:
- Corpus: 1000 BGer decisions (2020-2024)
- Embeddings: concat_center_tfidf (768-dim center-projected + 128-dim TF-IDF)
- Clustering: Leiden at resolutions [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
- Success: Legal purity ratio improves at finer resolutions within clusters

Evidence tier: EXPLORATORY
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
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_metadata_with_branch():
    """Load baseline metadata and enrich with branch from corpus files."""
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    # Load branch info from corpus files
    branch_map = {}
    for year_file in sorted(CORPUS_DIR.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                did = d.get('decision_id', '')
                if did in id_to_idx:
                    branch_map[did] = d.get('branch')
    
    # Enrich metadata
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


def compute_purity(labels, metadata, target_field):
    """Compute clustering purity for a specific field."""
    labels = np.array(labels)
    unique_labels = np.unique(labels[labels != -1])
    total_purity = 0
    total_size = 0
    for label in unique_labels:
        mask = labels == label
        cluster_meta = [metadata[i] for i in np.where(mask)[0]]
        values = [m.get(target_field) for m in cluster_meta if m.get(target_field)]
        if not values:
            continue
        counter = Counter(values)
        total_purity += max(counter.values())
        total_size += len(values)
    return total_purity / total_size if total_size > 0 else 0


def compute_legal_area_mapping(metadata):
    """Map language-specific legal areas to canonical categories."""
    # Create a mapping from language-specific to canonical legal areas
    area_map = {}
    
    # Group by (branch, language) to find translations
    branch_lang_areas = defaultdict(lambda: defaultdict(list))
    for m in metadata:
        branch = m.get('branch')
        lang = m.get('language')
        area = m.get('legal_area')
        if branch and lang and area:
            branch_lang_areas[branch][lang].append(area)
    
    # For each branch, map all language variants to the German name (most common)
    for branch, lang_areas in branch_lang_areas.items():
        de_areas = lang_areas.get('de', [])
        if de_areas:
            canonical = Counter(de_areas).most_common(1)[0][0]
            for lang, areas in lang_areas.items():
                for area in areas:
                    area_map[(lang, area)] = canonical
    
    return area_map


def compute_zoom_coherence(embeddings, metadata, resolutions, area_map):
    """
    Test zoom coherence: does zooming from coarse to fine reveal
    legally coherent substructure?
    
    For each coarse cluster at resolution r_coarse:
    1. Subset embeddings to that cluster
    2. Run Leiden at finer resolutions within the subset
    3. Measure legal purity ratio at each fine resolution
    4. Compare with flat clustering at the same resolution
    """
    results = {}
    
    # Map legal areas to canonical
    canonical_areas = []
    for m in metadata:
        lang = m.get('language', 'de')
        area = m.get('legal_area', '')
        canonical = area_map.get((lang, area), area)
        canonical_areas.append(canonical)
    
    # Run clustering at all resolutions
    clusterings = {}
    for res in resolutions:
        labels, modularity = leiden_clustering(embeddings, resolution=res)
        clusterings[res] = (labels, modularity)
    
    # For each coarse resolution, test zoom coherence
    coarse_resolutions = [0.25, 0.5]
    fine_resolutions = [1.0, 1.5, 2.0, 3.0]
    
    for coarse_res in coarse_resolutions:
        coarse_labels, coarse_mod = clusterings[coarse_res]
        coarse_clusters = np.unique(coarse_labels[coarse_labels != -1])
        
        logger.info(f"\nCoarse resolution {coarse_res}: {len(coarse_clusters)} clusters")
        
        zoom_results = {}
        
        for cluster_id in coarse_clusters:
            cluster_mask = coarse_labels == cluster_id
            cluster_indices = np.where(cluster_mask)[0]
            cluster_size = len(cluster_indices)
            
            if cluster_size < 20:  # Skip tiny clusters
                continue
            
            # Get cluster metadata
            cluster_meta = [metadata[i] for i in cluster_indices]
            cluster_areas = [canonical_areas[i] for i in cluster_indices]
            cluster_langs = [m.get('language') for m in cluster_meta]
            
            # Compute coarse cluster stats
            lang_counter = Counter(cluster_langs)
            dominant_lang = lang_counter.most_common(1)[0][0]
            lang_purity_coarse = lang_counter.most_common(1)[0][1] / cluster_size
            
            area_counter = Counter(cluster_areas)
            dominant_area = area_counter.most_common(1)[0][0] if area_counter else None
            legal_purity_coarse = area_counter.most_common(1)[0][1] / cluster_size if area_counter else 0
            
            # For each fine resolution, cluster within this coarse cluster
            fine_cluster_results = {}
            for fine_res in fine_resolutions:
                # Get the full clustering labels
                fine_labels, fine_mod = clusterings[fine_res]
                
                # Extract subcluster labels for this coarse cluster
                sub_labels = fine_labels[cluster_mask]
                unique_sub = np.unique(sub_labels[sub_labels != -1])
                
                if len(unique_sub) < 2:
                    # No substructure - single subcluster
                    fine_cluster_results[f"res_{fine_res}"] = {
                        'n_subclusters': 1,
                        'legal_purity': legal_purity_coarse,
                        'language_purity': lang_purity_coarse,
                        'ratio': legal_purity_coarse / lang_purity_coarse if lang_purity_coarse > 0 else 0,
                        'subcluster_legal_purities': [legal_purity_coarse],
                        'subcluster_sizes': [cluster_size],
                    }
                    continue
                
                # Compute subcluster purity
                sub_legal_purities = []
                sub_lang_purities = []
                sub_sizes = []
                sub_areas = []
                
                for sub_id in unique_sub:
                    sub_mask = sub_labels == sub_id
                    sub_indices = np.where(sub_mask)[0]
                    sub_size = len(sub_indices)
                    
                    sub_meta = [cluster_meta[i] for i in sub_indices]
                    sub_area_list = [canonical_areas[cluster_indices[i]] for i in sub_indices]
                    sub_lang_list = [m.get('language') for m in sub_meta]
                    
                    # Subcluster purity
                    sub_area_counter = Counter(sub_area_list)
                    sub_legal_purity = sub_area_counter.most_common(1)[0][1] / sub_size if sub_area_counter else 0
                    
                    sub_lang_counter = Counter(sub_lang_list)
                    sub_lang_purity = sub_lang_counter.most_common(1)[0][1] / sub_size if sub_lang_counter else 0
                    
                    sub_legal_purities.append(sub_legal_purity)
                    sub_lang_purities.append(sub_lang_purity)
                    sub_sizes.append(sub_size)
                    sub_areas.append(sub_area_counter.most_common(1)[0][0] if sub_area_counter else None)
                
                # Weighted average purity
                total_in_sub = sum(sub_sizes)
                avg_legal = sum(p * s for p, s in zip(sub_legal_purities, sub_sizes)) / total_in_sub if total_in_sub > 0 else 0
                avg_lang = sum(p * s for p, s in zip(sub_lang_purities, sub_sizes)) / total_in_sub if total_in_sub > 0 else 0
                ratio = avg_legal / avg_lang if avg_lang > 0 else 0
                
                fine_cluster_results[f"res_{fine_res}"] = {
                    'n_subclusters': len(unique_sub),
                    'legal_purity': avg_legal,
                    'language_purity': avg_lang,
                    'ratio': ratio,
                    'subcluster_legal_purities': sub_legal_purities,
                    'subcluster_sizes': sub_sizes,
                    'subcluster_areas': sub_areas,
                }
            
            zoom_results[f"cluster_{cluster_id}"] = {
                'size': cluster_size,
                'dominant_lang': dominant_lang,
                'lang_purity': lang_purity_coarse,
                'dominant_area': dominant_area,
                'legal_purity': legal_purity_coarse,
                'fine_results': fine_cluster_results,
            }
        
        results[f"coarse_res_{coarse_res}"] = zoom_results
    
    return results, clusterings


def compute_flat_baseline(embeddings, metadata, resolutions, area_map):
    """Compute flat clustering baseline for comparison."""
    # Map legal areas to canonical
    canonical_areas = []
    for m in metadata:
        lang = m.get('language', 'de')
        area = m.get('legal_area', '')
        canonical = area_map.get((lang, area), area)
        canonical_areas.append(canonical)
    
    results = {}
    for res in resolutions:
        labels, modularity = leiden_clustering(embeddings, resolution=res)
        legal_purity = compute_purity(labels, metadata, 'legal_area')
        lang_purity = compute_purity(labels, metadata, 'language')
        n_clusters = len(set(labels[labels != -1]))
        
        results[f"resolution_{res}"] = {
            'n_clusters': n_clusters,
            'modularity': modularity,
            'legal_area_purity': legal_purity,
            'language_purity': lang_purity,
            'ratio': legal_purity / lang_purity if lang_purity > 0 else 0,
        }
    
    return results


def analyze_zoom_improvement(zoom_results, flat_results):
    """
    Analyze whether zooming reveals legally coherent substructure.
    
    Key metric: Does the legal purity ratio improve at finer resolutions
    within language-homogeneous clusters?
    """
    analysis = {}
    
    for coarse_key, coarse_data in zoom_results.items():
        coarse_res = float(coarse_key.split('_')[-1])
        
        improvements = []
        deterioration = []
        no_change = []
        
        for cluster_key, cluster_data in coarse_data.items():
            if cluster_data['lang_purity'] < 0.8:  # Skip language-mixed clusters
                continue
            
            cluster_size = cluster_data['size']
            coarse_ratio = cluster_data['legal_purity'] / cluster_data['lang_purity'] if cluster_data['lang_purity'] > 0 else 0
            
            for fine_key, fine_data in cluster_data['fine_results'].items():
                fine_res = float(fine_key.split('_')[-1])
                if fine_res <= coarse_res:
                    continue
                
                fine_ratio = fine_data['ratio']
                improvement = (fine_ratio - coarse_ratio) / coarse_ratio if coarse_ratio > 0 else 0
                
                if improvement > 0.05:  # >5% improvement
                    improvements.append({
                        'cluster': cluster_key,
                        'size': cluster_size,
                        'coarse_res': coarse_res,
                        'fine_res': fine_res,
                        'coarse_ratio': coarse_ratio,
                        'fine_ratio': fine_ratio,
                        'improvement_pct': improvement * 100,
                    })
                elif improvement < -0.05:  # >5% deterioration
                    deterioration.append({
                        'cluster': cluster_key,
                        'size': cluster_size,
                        'coarse_res': coarse_res,
                        'fine_res': fine_res,
                        'coarse_ratio': coarse_ratio,
                        'fine_ratio': fine_ratio,
                        'deterioration_pct': improvement * 100,
                    })
                else:
                    no_change.append({
                        'cluster': cluster_key,
                        'size': cluster_size,
                        'coarse_res': coarse_res,
                        'fine_res': fine_res,
                        'coarse_ratio': coarse_ratio,
                        'fine_ratio': fine_ratio,
                    })
        
        analysis[coarse_key] = {
            'n_improvements': len(improvements),
            'n_deteriorations': len(deterioration),
            'n_no_change': len(no_change),
            'improvements': improvements,
            'deteriorations': deterioration,
            'no_change': no_change,
            'improvement_rate': len(improvements) / (len(improvements) + len(deterioration) + len(no_change)) if (len(improvements) + len(deterioration) + len(no_change)) > 0 else 0,
        }
    
    return analysis


def main():
    logger.info("=== Zoom Coherence Experiment ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # 1. Load data
    logger.info("\n1. Loading metadata with branch info...")
    id_to_idx, metadata = load_metadata_with_branch()
    baseline_emb, center_emb = load_representations()
    logger.info(f"   Metadata: {len(metadata)} decisions")
    
    # Branch distribution
    branches = Counter(m.get('branch') for m in metadata if m.get('branch'))
    logger.info(f"   Branches: {dict(branches)}")
    
    # 2. Load corpus
    logger.info("\n2. Loading corpus decisions...")
    decisions = load_corpus_decisions(metadata)
    logger.info(f"   Loaded {len(decisions)} decisions")
    
    # 3. Compute TF-IDF
    logger.info("\n3. Computing TF-IDF Erwaegungen...")
    tfidf_full, valid_indices = compute_tfidf_erwaegungen(metadata, decisions)
    logger.info(f"   TF-IDF: {tfidf_full.shape}, {len(valid_indices)} valid")
    
    # 4. Build concat
    logger.info("\n4. Building concatenated representation...")
    concat_emb = build_concat(baseline_emb, center_emb, tfidf_full)
    logger.info(f"   Concat: {concat_emb.shape}")
    
    # 5. Compute legal area mapping
    logger.info("\n5. Computing legal area mapping...")
    area_map = compute_legal_area_mapping(metadata)
    logger.info(f"   Mapped {len(area_map)} area variants")
    
    # 6. Run zoom coherence analysis
    logger.info("\n6. Running zoom coherence analysis...")
    resolutions = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    zoom_results, clusterings = compute_zoom_coherence(concat_emb, metadata, resolutions, area_map)
    
    # 7. Compute flat baseline
    logger.info("\n7. Computing flat baseline...")
    flat_results = compute_flat_baseline(concat_emb, metadata, resolutions, area_map)
    
    # 8. Analyze improvements
    logger.info("\n8. Analyzing zoom improvements...")
    improvement_analysis = analyze_zoom_improvement(zoom_results, flat_results)
    
    # 9. Print summary
    logger.info("\n" + "=" * 80)
    logger.info("ZOOM COHERENCE SUMMARY")
    logger.info("=" * 80)
    
    for coarse_key, analysis in improvement_analysis.items():
        logger.info(f"\n{coarse_key}:")
        logger.info(f"  Improvements: {analysis['n_improvements']}")
        logger.info(f"  Deteriorations: {analysis['n_deteriorations']}")
        logger.info(f"  No change: {analysis['n_no_change']}")
        logger.info(f"  Improvement rate: {analysis['improvement_rate']:.1%}")
        
        if analysis['improvements']:
            logger.info(f"\n  Top improvements:")
            for imp in sorted(analysis['improvements'], key=lambda x: x['improvement_pct'], reverse=True)[:5]:
                logger.info(f"    Cluster {imp['cluster']} (size {imp['size']}): "
                          f"res {imp['coarse_res']}->{imp['fine_res']}: "
                          f"{imp['coarse_ratio']:.3f}->{imp['fine_ratio']:.3f} "
                          f"(+{imp['improvement_pct']:.1f}%)")
    
    # 10. Flat baseline comparison
    logger.info("\n" + "=" * 80)
    logger.info("FLAT BASELINE COMPARISON")
    logger.info("=" * 80)
    
    for res_key, res_data in flat_results.items():
        logger.info(f"  {res_key}: {res_data['n_clusters']} clusters, "
                   f"legal={res_data['legal_area_purity']:.3f}, "
                   f"lang={res_data['language_purity']:.3f}, "
                   f"ratio={res_data['ratio']:.3f}")
    
    # 11. Save results
    logger.info("\n9. Saving results...")
    
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
        "run_id": f"zoom_coherence_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 1,
        "hypothesis": "Zooming from coarse to fine reveals legally coherent substructure",
        "frozen_sample": f"{len(metadata)} BGer decisions (2020-2024)",
        "frozen_metric": "Legal purity ratio improvement within language-homogeneous clusters",
        "success_rule": "Majority of language-homogeneous clusters show >5% ratio improvement at finer resolutions",
        "resolutions_tested": resolutions,
        "flat_baseline": flat_results,
        "zoom_results": zoom_results,
        "improvement_analysis": improvement_analysis,
        "overall_improvement_rate": np.mean([a['improvement_rate'] for a in improvement_analysis.values()]) if improvement_analysis else 0,
        "total_improvements": sum(a['n_improvements'] for a in improvement_analysis.values()),
        "total_deteriorations": sum(a['n_deteriorations'] for a in improvement_analysis.values()),
    }
    
    output_path = OUTPUT_DIR / "zoom_coherence_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Zoom coherence experiment complete ===")
    
    return output


if __name__ == "__main__":
    main()
