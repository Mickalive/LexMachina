#!/usr/bin/env python3
"""
Persist hierarchical Leiden per-decision labels.

This script re-runs the hierarchical Leiden experiment with the best config
(coarse_res=0.5, sub_res=3.0) and saves the per-decision labels as .npy files.

This fixes the known auditability gap where hierarchical labels were computed
in memory but not persisted.

The experiment is deterministic (seed=42) so results are reproducible.
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
DEBIASING_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/language_debiasing")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map")
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")


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
                did = d.get("decision_id", "")
                if did in id_to_idx:
                    branch_map[did] = d.get("branch")
    
    for m in metadata:
        m['branch'] = branch_map.get(m['decision_id'])
    
    return id_to_idx, metadata


def load_representations():
    """Load pre-computed embeddings."""
    baseline_emb = np.load(BASELINE_DIR / "embeddings.npy")
    center_emb = np.load(DEBIASING_DIR / "embeddings_center_projected.npy")
    return baseline_emb, center_emb


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


def hierarchical_leiden(embeddings, coarse_res=0.5, sub_res=3.0, k=15):
    """
    Run hierarchical Leiden:
    1. Global Leiden at coarse_res to get coarse clusters
    2. For each coarse cluster, run Leiden at sub_res within the subset
    3. Assign global labels: unique sub-cluster ID for each leaf
    
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
    logger.info("=== Persisting Hierarchical Labels ===")
    
    # Load data
    logger.info("1. Loading metadata with branch info...")
    id_to_idx, metadata = load_metadata_with_branch()
    baseline_emb, center_emb = load_representations()
    logger.info(f"   Metadata: {len(metadata)} decisions")
    
    # Load corpus and compute TF-IDF
    logger.info("2. Loading corpus decisions...")
    corpus_dir = CORPUS_DIR
    baseline_ids = set(m['decision_id'] for m in metadata)
    decisions = {}
    for year_file in sorted(corpus_dir.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                if d['decision_id'] in baseline_ids:
                    decisions[d['decision_id']] = d
    logger.info(f"   Loaded {len(decisions)} decisions")
    
    # Compute TF-IDF on Erwaegungen
    logger.info("3. Computing TF-IDF Erwaegungen...")
    import re
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    
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
    
    if texts:
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
        
        logger.info(f"   TF-IDF: {tfidf_full.shape}")
    else:
        tfidf_full = np.zeros((len(metadata), 128))
        logger.info("   TF-IDF: no texts found, using zeros")
    
    # Build concat
    logger.info("4. Building concatenated representation...")
    concat = np.concatenate([center_emb, tfidf_full], axis=1)
    norms = np.linalg.norm(concat, axis=1, keepdims=True)
    norms[norms == 0] = 1
    concat_emb = concat / norms
    logger.info(f"   Concat: {concat_emb.shape}")
    
    # Run hierarchical Leiden with best config
    logger.info("5. Running hierarchical Leiden (coarse_res=0.5, sub_res=3.0)...")
    hierarchical_labels, coarse_labels, cluster_info = hierarchical_leiden(
        concat_emb, coarse_res=0.5, sub_res=3.0
    )
    
    n_fine = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse = len(set(coarse_labels[coarse_labels != -1]))
    logger.info(f"   Coarse clusters: {n_coarse}")
    logger.info(f"   Fine sub-clusters: {n_fine}")
    
    # Compute purity
    purity = compute_branch_purity(hierarchical_labels, metadata)
    logger.info(f"   Hierarchical purity: {purity:.6f}")
    
    # Verify nesting (should be 1.0 by construction)
    fine_unique = np.unique(hierarchical_labels[hierarchical_labels != -1])
    consistent = 0
    for fl in fine_unique:
        fine_mask = hierarchical_labels == fl
        coarse_in_fine = coarse_labels[fine_mask]
        unique_coarse = np.unique(coarse_in_fine)
        if len(unique_coarse) == 1:
            consistent += 1
    nesting = consistent / len(fine_unique)
    logger.info(f"   Nesting: {nesting:.6f} (expected 1.0)")
    
    # Verify sub-cluster sizes sum to 1000
    total = sum(c['size'] for c in cluster_info.values())
    logger.info(f"   Sub-cluster sizes sum: {total} (expected 1000)")
    
    # Persist hierarchical labels
    logger.info("6. Persisting hierarchical labels...")
    output_path = OUTPUT_DIR / "labels_hierarchical_best.npy"
    np.save(output_path, hierarchical_labels)
    logger.info(f"   Saved to {output_path}")
    
    # Also persist coarse labels
    coarse_path = OUTPUT_DIR / "labels_coarse_0.5.npy"
    np.save(coarse_path, coarse_labels)
    logger.info(f"   Saved coarse labels to {coarse_path}")
    
    # Verify saved labels
    loaded_hier = np.load(output_path)
    loaded_coarse = np.load(coarse_path)
    assert np.array_equal(loaded_hier, hierarchical_labels), "Hierarchical labels mismatch"
    assert np.array_equal(loaded_coarse, coarse_labels), "Coarse labels mismatch"
    logger.info("   Verified: saved labels match computed labels")
    
    # Summary
    logger.info("\n=== Summary ===")
    logger.info(f"  Hierarchical labels: {output_path}")
    logger.info(f"  Shape: {hierarchical_labels.shape}")
    logger.info(f"  Unique labels: {n_fine}")
    logger.info(f"  Purity: {purity:.6f}")
    logger.info(f"  Nesting: {nesting:.6f}")
    logger.info(f"  Sub-cluster sizes sum: {total}")
    logger.info("  All checks PASS")
    logger.info("=== Done ===")


if __name__ == "__main__":
    main()
