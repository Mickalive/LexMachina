#!/usr/bin/env python3
"""
Experiment: Citation-Graph Embeddings for Fractal Map

Hypothesis: The citation graph encodes legal proximity that is language-agnostic.
Two decisions that cite each other are legally related regardless of the language
they're written in. Citation-graph embeddings (node2vec) should produce a
language-debiased representation of legal proximity.

Product decision: If citation-graph embeddings improve legal-area purity or
language-agnosticism, they become a candidate for the fractal map.

Evidence tier: EXPLORATORY

Note: The citation graph covers 250 of the 1000 baseline decisions. For decisions
not in the graph, we use the mean embedding of their citing neighbors, or fall
back to the original embedding.
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
import logging
import networkx as nx

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/citation_graph")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_baseline():
    embeddings = np.load(BASELINE_DIR / "embeddings.npy")
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    return embeddings, metadata


def load_citation_graph():
    with open(CORPUS_DIR / "citation_graph.json") as f:
        return json.load(f)


def build_networkx_graph(citation_data):
    """Build a NetworkX graph from the citation data."""
    G = nx.DiGraph()

    # Add edges from outgoing citations
    outgoing = citation_data.get('outgoing', {})
    for source_id, targets in outgoing.items():
        for target in targets:
            G.add_edge(source_id, target)

    logger.info(f"Directed graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def map_decision_ids_to_indices(metadata):
    """Map decision_id strings to indices in the baseline arrays."""
    id_to_idx = {}
    for i, m in enumerate(metadata):
        did = m.get('decision_id', '')
        id_to_idx[did] = i
    return id_to_idx


def node2vec_embeddings(G, dimensions=64, walk_length=40, num_walks=10,
                         p=1.0, q=1.0, workers=1):
    """
    Compute node2vec embeddings on the citation graph.

    Parameters:
    - p: Return parameter (controls likelihood of returning to previous node)
    - q: In-out parameter (controls search behavior: BFS-like for q<1, DFS-like for q>1)
    """
    try:
        from node2vec import Node2Vec
        logger.info("Using node2vec library")
        node2vec = Node2Vec(G, dimensions=dimensions, walk_length=walk_length,
                            num_walks=num_walks, p=p, q=q, workers=workers,
                            quiet=True)
        model = node2vec.fit(window=10, min_count=1, batch_words=4)
        return model
    except ImportError:
        logger.warning("node2vec not available, using manual random walks + skipgram")
        return manual_node2vec(G, dimensions, walk_length, num_walks, p, q)


def manual_node2vec(G, dimensions=64, walk_length=40, num_walks=10,
                     p=1.0, q=1.0):
    """
    Manual node2vec implementation using networkx random walks + SVD.
    Falls back to spectral embedding if walks fail.
    """
    logger.info("Using manual node2vec (random walks + SVD)")

    # Convert to undirected for walks
    G_undirected = G.to_undirected()

    # Generate walks
    walks = []
    nodes = list(G_undirected.nodes())
    for _ in range(num_walks):
        np.random.shuffle(nodes)
        for node in nodes:
            walk = [node]
            for _ in range(walk_length - 1):
                current = walk[-1]
                neighbors = list(G_undirected.neighbors(current))
                if not neighbors:
                    break
                # Simple random walk (node2vec bias would require more complex logic)
                next_node = np.random.choice(neighbors)
                walk.append(next_node)
            walks.append(walk)

    logger.info(f"Generated {len(walks)} walks of length {walk_length}")

    # Build co-occurrence matrix
    from scipy.sparse import lil_matrix
    vocab = {n: i for i, n in enumerate(nodes)}
    cooccur = lil_matrix((len(nodes), len(nodes)))

    for walk in walks:
        for i, node in enumerate(walk):
            for j in range(max(0, i - 5), min(len(walk), i + 6)):
                if i != j:
                    cooccur[vocab[node], vocab[walk[j]]] += 1

    cooccur = cooccur.tocsr()

    # SVD on log co-occurrence
    from sklearn.decomposition import TruncatedSVD
    svd = TruncatedSVD(n_components=dimensions, random_state=42)
    node_embeddings = svd.fit_transform(cooccur)

    # L2 normalize
    norms = np.linalg.norm(node_embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    node_embeddings = node_embeddings / norms

    return node_embeddings, vocab


def compute_graph_embeddings(embeddings, metadata, citation_data, id_to_idx):
    """
    Combine citation-graph embeddings with text embeddings.

    Strategy: For decisions in the citation graph, blend text embedding with
    graph embedding. For decisions not in the graph, use text embedding only.

    Blend formula: alpha * text_embedding + (1-alpha) * graph_embedding
    """
    G = build_networkx_graph(citation_data)

    # Get the nodes that are in our baseline
    baseline_nodes = set(id_to_idx.keys())
    graph_nodes = set(G.nodes())
    common_nodes = baseline_nodes & graph_nodes

    logger.info(f"Common nodes (in both baseline and graph): {len(common_nodes)}")
    logger.info(f"Graph nodes not in baseline: {len(graph_nodes - baseline_nodes)}")
    logger.info(f"Baseline nodes not in graph: {len(baseline_nodes - graph_nodes)}")

    # Compute node2vec on the full graph
    dims = 64
    try:
        node_emb, node_vocab = node2vec_embeddings(G, dimensions=dims,
                                                    walk_length=20, num_walks=5)
        logger.info(f"Node2vec embeddings: {len(node_vocab)} nodes, dim={dims}")
    except Exception as e:
        logger.error(f"Node2vec failed: {e}")
        logger.info("Falling back to degree-based features")
        # Fallback: use degree centrality as features
        node_emb = {}
        in_deg = dict(G.in_degree())
        out_deg = dict(G.out_degree())
        pagerank = nx.pagerank(G, alpha=0.85)
        betweenness = nx.betweenness_centrality(G)

        for node in G.nodes():
            node_emb[node] = np.array([
                in_deg.get(node, 0),
                out_deg.get(node, 0),
                pagerank.get(node, 0),
                betweenness.get(node, 0),
            ])
        node_vocab = {n: i for i, n in enumerate(G.nodes())}
        # Stack into matrix
        emb_matrix = np.stack([node_emb[n] for n in G.nodes()])
        # Pad to dims
        if emb_matrix.shape[1] < dims:
            emb_matrix = np.pad(emb_matrix, ((0, 0), (0, dims - emb_matrix.shape[1])))
        node_emb = emb_matrix[:, :dims]

    # Map graph embeddings to baseline indices
    graph_embeddings = np.zeros((len(metadata), dims))
    in_graph_mask = np.zeros(len(metadata), dtype=bool)

    for node in common_nodes:
        idx = id_to_idx[node]
        node_idx = node_vocab[node]
        if isinstance(node_emb, np.ndarray) and node_emb.ndim == 2:
            graph_embeddings[idx] = node_emb[node_idx]
        else:
            graph_embeddings[idx] = node_emb[node]
        in_graph_mask[idx] = True

    # Compute PageRank on the graph for each node
    try:
        pagerank = nx.pagerank(G, alpha=0.85)
    except Exception:
        pagerank = {n: 1.0 / G.number_of_nodes() for n in G.nodes()}

    # Blend: for in-graph nodes, combine text + graph
    # Use alpha = 0.5 (equal weight)
    alpha = 0.5
    blended = np.copy(embeddings[:, :dims] if embeddings.shape[1] > dims else embeddings)

    # Pad text embeddings if needed
    text_768 = embeddings
    if text_768.shape[1] > dims:
        # PCA-project text to lower dim for fair comparison
        from sklearn.decomposition import PCA
        pca = PCA(n_components=dims, random_state=42)
        text_768 = pca.fit_transform(text_768)

    for i in range(len(metadata)):
        if in_graph_mask[i]:
            blended[i] = alpha * text_768[i] + (1 - alpha) * graph_embeddings[i]
        else:
            blended[i] = text_768[i]

    # Also create a graph-only version for in-graph nodes
    graph_only = np.zeros((len(metadata), dims))
    for i in range(len(metadata)):
        if in_graph_mask[i]:
            graph_only[i] = graph_embeddings[i]
        else:
            graph_only[i] = text_768[i]

    return blended, graph_only, in_graph_mask, dims


def compute_purity(labels, metadata, target_field):
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


def leiden_clustering(embeddings, resolution=1.0, k=15):
    from sklearn.neighbors import kneighbors_graph
    import igraph as ig
    import leidenalg

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms

    graph = kneighbors_graph(normalized, n_neighbors=min(k, len(embeddings) - 1),
                             metric='euclidean', mode='connectivity',
                             include_self=False)
    graph = graph.maximum(graph.T)

    sources, targets = graph.nonzero()
    weights = graph.data
    edges = list(zip(sources.tolist(), targets.tolist()))

    g = ig.Graph()
    g.add_vertices(graph.shape[0])
    g.add_edges(edges)
    g.es['weight'] = weights.tolist()

    partition = leidenalg.find_partition(
        g,
        leidenalg.RBConfigurationVertexPartition,
        weights='weight',
        resolution_parameter=resolution,
        seed=42
    )
    return np.array(partition.membership), partition.modularity


def evaluate_representation(embeddings, metadata, name,
                            resolutions=[0.5, 1.0, 2.0, 3.0]):
    logger.info(f"Evaluating {name}")
    results = {}
    for res in resolutions:
        labels, modularity = leiden_clustering(embeddings, resolution=res)
        legal_purity = compute_purity(labels, metadata, 'legal_area')
        lang_purity = compute_purity(labels, metadata, 'language')
        branch_purity = compute_purity(labels, metadata, 'branch')
        n_clusters = len(set(labels[labels != -1]))

        results[f"resolution_{res}"] = {
            'n_clusters': n_clusters,
            'modularity': modularity,
            'legal_area_purity': legal_purity,
            'language_purity': lang_purity,
            'branch_purity': branch_purity,
            'ratio': legal_purity / lang_purity if lang_purity > 0 else 0,
        }
        logger.info(f"  res={res}: {n_clusters} clusters, "
                    f"legal={legal_purity:.3f}, lang={lang_purity:.3f}, "
                    f"ratio={legal_purity/lang_purity:.3f}")
    return results


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
    logger.info("=== Citation-Graph Embeddings Experiment ===")

    baseline_embeddings, metadata = load_baseline()
    citation_data = load_citation_graph()
    id_to_idx = map_decision_ids_to_indices(metadata)

    logger.info(f"Baseline: {baseline_embeddings.shape[0]} decisions")

    # Compute graph-based embeddings
    blended, graph_only, in_graph_mask, dims = compute_graph_embeddings(
        baseline_embeddings, metadata, citation_data, id_to_idx
    )
    logger.info(f"In-graph decisions: {np.sum(in_graph_mask)}/{len(metadata)}")

    # Save
    np.save(OUTPUT_DIR / "embeddings_blended.npy", blended)
    np.save(OUTPUT_DIR / "embeddings_graph_only.npy", graph_only)

    # Evaluate
    results_blended = evaluate_representation(blended, metadata, "blended")
    results_graph = evaluate_representation(graph_only, metadata, "graph_only")

    # Baseline for comparison
    logger.info("\n--- Baseline (text-only, PCA to same dim) ---")
    from sklearn.decomposition import PCA
    pca = PCA(n_components=dims, random_state=42)
    baseline_64d = pca.fit_transform(baseline_embeddings)
    results_baseline = evaluate_representation(baseline_64d, metadata, "baseline_64d")

    all_results = {
        'baseline_64d': results_baseline,
        'blended': results_blended,
        'graph_only': results_graph,
    }

    logger.info("\n=== Summary at resolution 1.0 ===")
    for name, res in all_results.items():
        r = res.get('resolution_1.0', {})
        if r:
            logger.info(f"  {name}: legal={r.get('legal_area_purity', 0):.3f}, "
                        f"lang={r.get('language_purity', 0):.3f}, "
                        f"ratio={r.get('ratio', 0):.3f}")

    with open(OUTPUT_DIR / "citation_results.json", 'w') as f:
        json.dump(convert(all_results), f, indent=2)

    logger.info(f"\nResults saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
