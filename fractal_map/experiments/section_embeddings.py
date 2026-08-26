#!/usr/bin/env python3
"""
Experiment: Test whether legally structured sections (Sachverhalt, Erwägungen, Dispositiv)
produce more legally coherent embeddings than full_text.

Hypothesis: Procedural boilerplate and language-specific formatting in full_text dominate
the embedding space. Structured sections (especially Erwägungen = legal reasoning) should
yield higher legal_area_purity / language_purity ratio.

Baseline: full_text embeddings (legal_area_purity ~0.35, language_purity ~0.98, ratio ~0.36)
Success criterion: Any section-based representation achieves ratio > 0.5 (meaning legal
coherence exceeds language coherence)
"""
import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
import umap
import logging
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
STRUCTURED_CORPUS = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical/bger_eval_structure.jsonl")
BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/section_experiment")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

def load_structured_corpus():
    """Load decisions with structured sections."""
    decisions = []
    with open(STRUCTURED_CORPUS) as f:
        for line in f:
            decisions.append(json.loads(line))
    logger.info(f"Loaded {len(decisions)} structured decisions")
    return decisions

def prepare_section_texts(decisions):
    """Extract different text representations from decisions."""
    texts = {
        'full_text': [],
        'sachverhalt': [],
        'erwaegungen': [],
        'dispositiv': [],
        'erwaegungen_dispositiv': [],  # Combined legally-relevant
        'sachverhalt_erwaegungen_dispositiv': [],  # All structured sections
    }
    metadata = []
    
    for d in decisions:
        # Full text (baseline)
        full = d.get('full_text', '')
        texts['full_text'].append(full)
        
        # Sachverhalt (facts)
        sach = d.get('sachverhalt', '') or ''
        texts['sachverhalt'].append(sach)
        
        # Erwägungen (reasoning) - combine all paragraphs
        erwaeg = d.get('erwaegungen', []) or []
        erwaeg_text = ' '.join([p.get('text', '') for p in erwaeg if isinstance(p, dict)])
        texts['erwaegungen'].append(erwaeg_text)
        
        # Dispositiv (outcome/orders)
        dispositiv = d.get('dispositiv', '') or ''
        texts['dispositiv'].append(dispositiv)
        
        # Combined legally-relevant: reasoning + outcome
        texts['erwaegungen_dispositiv'].append(erwaeg_text + ' ' + dispositiv)
        
        # All structured sections combined
        texts['sachverhalt_erwaegungen_dispositiv'].append(sach + ' ' + erwaeg_text + ' ' + dispositiv)
        
        metadata.append({
            'decision_id': d.get('decision_id'),
            'language': d.get('language'),
            'legal_area': d.get('legal_area'),
            'year': d.get('decision_date', '')[:4] if d.get('decision_date') else None,
            'court': d.get('court'),
            'chamber': d.get('chamber'),
        })
    
    # Log text lengths
    for key, ts in texts.items():
        lengths = [len(t) for t in ts]
        logger.info(f"  {key}: mean_len={np.mean(lengths):.0f}, median={np.median(lengths):.0f}, min={np.min(lengths)}, max={np.max(lengths)}")
        empty = sum(1 for t in ts if not t.strip())
        if empty:
            logger.warning(f"  {key}: {empty} empty texts!")
    
    return texts, metadata

def compute_embeddings(texts, model_name=MODEL_NAME, batch_size=16):
    """Compute embeddings for each text representation."""
    logger.info(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    embeddings = {}
    for key, ts in texts.items():
        logger.info(f"Computing embeddings for {key} ({len(ts)} texts)...")
        emb = model.encode(ts, batch_size=batch_size, show_progress_bar=True, convert_to_numpy=True)
        embeddings[key] = emb
        logger.info(f"  Shape: {emb.shape}")
    return embeddings

def compute_umap(embeddings_dict, n_neighbors=15, min_dist=0.1, n_components=2, metric='cosine', random_state=42):
    """Compute UMAP projections for each embedding set."""
    projections = {}
    reducers = {}
    for key, emb in embeddings_dict.items():
        logger.info(f"UMAP for {key}...")
        reducer = umap.UMAP(
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            n_components=n_components,
            metric=metric,
            random_state=random_state
        )
        proj = reducer.fit_transform(emb)
        projections[key] = proj
        reducers[key] = reducer
        logger.info(f"  Projection shape: {proj.shape}")
    return projections, reducers

def build_knn_graph(embeddings, k=15, metric='cosine'):
    """Build k-NN graph for Leiden clustering."""
    from sklearn.neighbors import kneighbors_graph
    if metric == 'cosine':
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        embeddings = embeddings / norms
        metric = 'euclidean'
    graph = kneighbors_graph(embeddings, n_neighbors=k, metric=metric, mode='connectivity', include_self=False)
    graph = graph.maximum(graph.T)
    return graph

def leiden_clustering(graph, resolution=1.0, random_state=42):
    """Run Leiden clustering."""
    try:
        import igraph as ig
        import leidenalg
        sources, targets = graph.nonzero()
        weights = graph.data
        edges = list(zip(sources, targets))
        g = ig.Graph()
        g.add_vertices(graph.shape[0])
        g.add_edges(edges)
        g.es['weight'] = weights
        partition = leidenalg.find_partition(
            g, leidenalg.RBConfigurationVertexPartition,
            weights='weight', resolution_parameter=resolution, seed=random_state
        )
        labels = np.array(partition.membership)
        modularity = partition.modularity
        return labels, modularity
    except ImportError:
        import community as community_louvain
        import networkx as nx
        sources, targets = graph.nonzero()
        weights = graph.data
        G = nx.Graph()
        G.add_nodes_from(range(graph.shape[0]))
        for s, t, w in zip(sources, targets, weights):
            G.add_edge(s, t, weight=w)
        partition = community_louvain.best_partition(G, resolution=resolution, random_state=random_state)
        labels = np.array([partition[i] for i in range(graph.shape[0])])
        modularity = community_louvain.modularity(partition, G, weight='weight')
        return labels, modularity

def compute_purity(labels, metadata, target_field):
    """Compute cluster purity for a target metadata field."""
    labels = np.array(labels)
    unique_labels = np.unique(labels)
    unique_labels = unique_labels[unique_labels != -1]
    
    total_purity = 0
    total_size = 0
    for label in unique_labels:
        mask = labels == label
        cluster_meta = [metadata[i] for i in np.where(mask)[0]]
        values = [m.get(target_field) for m in cluster_meta if m.get(target_field)]
        if not values:
            continue
        counter = Counter(values)
        max_count = max(counter.values())
        cluster_purity = max_count / len(values)
        cluster_size = len(values)
        total_purity += cluster_purity * cluster_size
        total_size += cluster_size
    return total_purity / total_size if total_size > 0 else 0

def analyze_coherence(labels, metadata):
    """Analyze legal vs language coherence."""
    legal_purity = compute_purity(labels, metadata, 'legal_area')
    lang_purity = compute_purity(labels, metadata, 'language')
    chamber_purity = compute_purity(labels, metadata, 'chamber')
    ratio = legal_purity / lang_purity if lang_purity > 0 else 0
    return {
        'legal_area_purity': legal_purity,
        'language_purity': lang_purity,
        'chamber_purity': chamber_purity,
        'legal_vs_language_ratio': ratio
    }

def run_clustering_analysis(embeddings_dict, metadata, resolutions=[0.5, 1.0, 1.5, 2.0]):
    """Run Leiden clustering at multiple resolutions for each embedding type."""
    results = {}
    for key, emb in embeddings_dict.items():
        logger.info(f"Clustering analysis for {key}...")
        graph = build_knn_graph(emb, k=15, metric='cosine')
        key_results = {}
        for res in resolutions:
            labels, mod = leiden_clustering(graph, resolution=res)
            coherence = analyze_coherence(labels, metadata)
            key_results[f'resolution_{res}'] = {
                'labels': labels.tolist(),
                'n_clusters': int(len(set(labels))),
                'modularity': mod,
                'coherence': coherence
            }
            logger.info(f"  res={res}: clusters={key_results[f'resolution_{res}']['n_clusters']}, "
                       f"legal_purity={coherence['legal_area_purity']:.4f}, "
                       f"lang_purity={coherence['language_purity']:.4f}, "
                       f"ratio={coherence['legal_vs_language_ratio']:.4f}")
        results[key] = key_results
    return results

def save_results(embeddings_dict, projections_dict, clustering_results, metadata):
    """Save all results."""
    # Save embeddings
    for key, emb in embeddings_dict.items():
        np.save(OUTPUT_DIR / f"embeddings_{key}.npy", emb)
    
    # Save projections
    for key, proj in projections_dict.items():
        np.save(OUTPUT_DIR / f"projection_{key}.npy", proj)
    
    # Save clustering results
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
    
    with open(OUTPUT_DIR / "clustering_results.json", 'w') as f:
        json.dump(convert(clustering_results), f, ensure_ascii=False, indent=2)
    
    with open(OUTPUT_DIR / "metadata.json", 'w') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved all results to {OUTPUT_DIR}")

def main():
    logger.info("=" * 60)
    logger.info("Section-based Embedding Experiment")
    logger.info("=" * 60)
    
    # Load structured corpus
    decisions = load_structured_corpus()
    
    # Prepare texts
    logger.info("Preparing section texts...")
    texts, metadata = prepare_section_texts(decisions)
    
    # Compute embeddings
    logger.info("Computing embeddings...")
    embeddings = compute_embeddings(texts)
    
    # Compute UMAP projections
    logger.info("Computing UMAP projections...")
    projections, reducers = compute_umap(embeddings)
    
    # Run clustering analysis
    logger.info("Running clustering analysis...")
    clustering_results = run_clustering_analysis(embeddings, metadata)
    
    # Save results
    save_results(embeddings, projections, clustering_results, metadata)
    
    # Print summary comparison
    logger.info("=" * 60)
    logger.info("SUMMARY: Legal vs Language Coherence Comparison")
    logger.info("=" * 60)
    logger.info(f"{'Representation':<35} {'Res':<8} {'Clusters':<10} {'Legal':<8} {'Lang':<8} {'Ratio':<8}")
    logger.info("-" * 80)
    
    for key, key_results in clustering_results.items():
        for res_key, result in key_results.items():
            res = res_key.split('_')[1]
            coh = result['coherence']
            logger.info(f"{key:<35} {res:<8} {result['n_clusters']:<10} "
                       f"{coh['legal_area_purity']:<8.4f} {coh['language_purity']:<8.4f} "
                       f"{coh['legal_vs_language_ratio']:<8.4f}")
    
    logger.info("Experiment complete!")

if __name__ == "__main__":
    main()