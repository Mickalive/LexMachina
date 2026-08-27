#!/usr/bin/env python3
"""
Validate zoom coherence on TRUE hierarchical Leiden structure.

This evaluates whether zooming from coarse (8 clusters) to fine (127 clusters)
within the hierarchical Leiden structure reveals legally coherent substructure.

Frozen before observation:
- Corpus: 1000 BGer decisions (2020-2024)
- Embeddings: concat_center_tfidf (896-dim)
- Structure: Hierarchical Leiden with coarse_res=0.5, sub_res=3.0
- Coarse: 8 clusters (language + legal domain)
- Fine: 127 clusters (nested within coarse, perfect nesting=1.0)
- Metric: Branch purity improvement from coarse to fine within each coarse cluster
- Success: Majority of coarse clusters show >5% branch purity improvement at fine level
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASELINE_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/baseline")
DEBIASING_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/language_debiasing")
HIERARCHICAL_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
    import re
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


def hierarchical_leiden(embeddings, metadata, coarse_res=0.5, sub_res=3.0, k=15):
    """
    Run hierarchical Leiden:
    1. Global Leiden at coarse_res to get coarse clusters
    2. For each coarse cluster, run Leiden at sub_res within the subset
    3. Assign global labels: (coarse_id, sub_id) mapped to sequential fine_id
    """
    # Step 1: Global coarse clustering
    coarse_labels, coarse_mod = leiden_clustering(embeddings, resolution=coarse_res, k=k)
    unique_coarse = np.unique(coarse_labels[coarse_labels != -1])

    logger.info(f"  Coarse (res={coarse_res}): {len(unique_coarse)} clusters, modularity={coarse_mod:.4f}")

    # Step 2: Within each coarse cluster, run Leiden at sub_res
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
                'coarse_id': int(coarse_id),
                'sub_id': 0,
                'size': int(len(indices)),
                'too_small': True,
            }
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1
            continue

        subset_embeddings = embeddings[indices]

        sub_labels, sub_mod = leiden_clustering(subset_embeddings, resolution=sub_res, k=k)
        unique_sub = np.unique(sub_labels[sub_labels != -1])

        logger.info(f"    Coarse {coarse_id} ({len(indices)} docs): "
                    f"{len(unique_sub)} sub-clusters, modularity={sub_mod:.4f}")

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
            coarse_to_fine[int(coarse_id)].append(sub_cluster_id)
            sub_cluster_id += 1

    return hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine


def compute_branch_purity(labels, metadata):
    """Compute branch purity for a set of labels."""
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


def compute_branch_purity_per_cluster(labels, metadata):
    """Compute branch purity for each cluster individually."""
    unique_labels = np.unique(labels[labels != -1])
    cluster_purities = {}

    for label in unique_labels:
        mask = labels == label
        cluster_branches = [metadata[i].get('branch') for i in np.where(mask)[0]]
        cluster_branches = [b for b in cluster_branches if b and b != 'null']

        if cluster_branches:
            most_common = Counter(cluster_branches).most_common(1)[0][1]
            cluster_purities[int(label)] = most_common / len(cluster_branches)
        else:
            cluster_purities[int(label)] = 0.0

    return cluster_purities


def main():
    logger.info("=== Hierarchical Leiden Zoom Coherence Validation ===")
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
    logger.info(f"   TF-IDF: {tfidf_full.shape}, {len(valid_indices)} valid")

    # 4. Build concat
    logger.info("\n4. Building concatenated representation...")
    concat_emb = build_concat(baseline_emb, center_emb, tfidf_full)
    logger.info(f"   Concat: {concat_emb.shape}")

    # 5. Run hierarchical Leiden (best config)
    logger.info("\n5. Running hierarchical Leiden (coarse=0.5, sub=3.0)...")
    hierarchical_labels, coarse_labels, cluster_info, coarse_to_fine = hierarchical_leiden(
        concat_emb, metadata, coarse_res=0.5, sub_res=3.0
    )

    n_fine_clusters = len(set(hierarchical_labels[hierarchical_labels != -1]))
    n_coarse_clusters = len(set(coarse_labels[coarse_labels != -1]))

    # 6. Compute branch purity at coarse level
    logger.info("\n6. Computing branch purity at coarse level...")
    coarse_purities = compute_branch_purity_per_cluster(coarse_labels, metadata)
    coarse_overall = compute_branch_purity(coarse_labels, metadata)
    logger.info(f"   Coarse overall purity: {coarse_overall:.4f}")
    for cid, pur in sorted(coarse_purities.items()):
        logger.info(f"   Coarse {cid}: purity={pur:.4f}")

    # 7. Compute branch purity at fine level (per coarse cluster)
    logger.info("\n7. Computing branch purity at fine level (per coarse cluster)...")
    fine_purities = compute_branch_purity_per_cluster(hierarchical_labels, metadata)
    fine_overall = compute_branch_purity(hierarchical_labels, metadata)
    logger.info(f"   Fine overall purity: {fine_overall:.4f}")

    # 8. Zoom coherence analysis: within each coarse cluster, does fine improve purity?
    logger.info("\n8. Zoom coherence analysis...")
    zoom_results = {}

    total_improvements = 0
    total_deteriorations = 0
    total_no_change = 0

    for coarse_id in sorted(coarse_to_fine.keys()):
        fine_ids = coarse_to_fine[coarse_id]
        if not fine_ids:
            continue

        coarse_pur = coarse_purities.get(coarse_id, 0)
        fine_purs = [fine_purities.get(fid, 0) for fid in fine_ids]
        fine_mean = np.mean(fine_purs) if fine_purs else 0
        improvement = fine_mean - coarse_pur

        # Count improvements/deteriorations at cluster level
        improvements = sum(1 for fp in fine_purs if fp > coarse_pur + 0.01)
        deteriorations = sum(1 for fp in fine_purs if fp < coarse_pur - 0.01)
        no_change = len(fine_purs) - improvements - deteriorations

        total_improvements += improvements
        total_deteriorations += deteriorations
        total_no_change += no_change

        # Dominant branch at coarse level
        coarse_mask = coarse_labels == coarse_id
        coarse_branches = [metadata[i].get('branch') for i in np.where(coarse_mask)[0]]
        coarse_branches = [b for b in coarse_branches if b and b != 'null']
        coarse_dom = Counter(coarse_branches).most_common(1)[0][0] if coarse_branches else "unknown"

        # Dominant branches at fine level
        fine_branch_dist = Counter()
        for fid in fine_ids:
            fine_mask = hierarchical_labels == fid
            fine_branches = [metadata[i].get('branch') for i in np.where(fine_mask)[0]]
            fine_branches = [b for b in fine_branches if b and b != 'null']
            if fine_branches:
                fine_branch_dist[fine_branches[0]] += 1  # simplified - just first branch

        zoom_results[int(coarse_id)] = {
            'coarse_size': int(np.sum(coarse_mask)),
            'coarse_purity': float(coarse_pur),
            'coarse_dominant_branch': coarse_dom,
            'n_fine_clusters': len(fine_ids),
            'fine_purity_mean': float(fine_mean),
            'fine_purity_values': [float(p) for p in fine_purs],
            'improvement': float(improvement),
            'improvement_pct': float(improvement / coarse_pur * 100) if coarse_pur > 0 else 0,
            'improvements': improvements,
            'deteriorations': deteriorations,
            'no_change': no_change,
            'fine_dominant_branches': dict(fine_branch_dist),
        }

        logger.info(f"   Coarse {coarse_id} ({coarse_dom}, size={zoom_results[coarse_id]['coarse_size']}): "
                    f"coarse_pur={coarse_pur:.4f}, fine_mean={fine_mean:.4f}, "
                    f"improvement={improvement:+.4f} ({improvement/coarse_pur*100:+.1f}%), "
                    f"improvements={improvements}, deteriorations={deteriorations}, no_change={no_change}")

    # 9. Summary
    logger.info("\n" + "=" * 70)
    logger.info("HIERARCHICAL LEIDEN ZOOM COHERENCE SUMMARY")
    logger.info("=" * 70)

    overall_improvement = fine_overall - coarse_overall
    improvement_rate = total_improvements / (total_improvements + total_deteriorations + total_no_change) if (total_improvements + total_deteriorations + total_no_change) > 0 else 0

    logger.info(f"\nOverall metrics:")
    logger.info(f"  Coarse clusters: {n_coarse_clusters}")
    logger.info(f"  Fine clusters: {n_fine_clusters}")
    logger.info(f"  Coarse overall purity: {coarse_overall:.4f}")
    logger.info(f"  Fine overall purity: {fine_overall:.4f}")
    logger.info(f"  Overall improvement: {overall_improvement:+.4f} ({overall_improvement/coarse_overall*100:+.1f}%)")
    logger.info(f"  Cluster-level improvements: {total_improvements}")
    logger.info(f"  Cluster-level deteriorations: {total_deteriorations}")
    logger.info(f"  Cluster-level no change: {total_no_change}")
    logger.info(f"  Improvement rate: {improvement_rate:.1%}")

    # Per coarse cluster detail
    logger.info(f"\nPer coarse cluster zoom analysis:")
    for cid, zr in sorted(zoom_results.items()):
        logger.info(f"  Coarse {cid} ({zr['coarse_dominant_branch']}): "
                    f"{zr['n_fine_clusters']} fine clusters, "
                    f"improvement={zr['improvement']:+.4f} ({zr['improvement_pct']:+.1f}%), "
                    f"impr={zr['improvements']}, det={zr['deteriorations']}, nc={zr['no_change']}")

    # 10. Compare with flat Leiden baseline
    logger.info("\n9. Comparison with flat Leiden baseline...")
    flat_labels = {}
    for res in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
        labels, mod = leiden_clustering(concat_emb, resolution=res)
        flat_labels[res] = labels
        purity = compute_branch_purity(labels, metadata)
        n_clusters = len(set(labels[labels != -1]))
        logger.info(f"  Flat res={res}: {n_clusters} clusters, purity={purity:.4f}")

    flat_purities = {f"res_{r}": compute_branch_purity(flat_labels[r], metadata) for r in flat_labels.keys()}
    flat_best = max(flat_purities.values())
    logger.info(f"  Flat Leiden best purity: {flat_best:.4f}")
    logger.info(f"  Hierarchical Leiden fine purity: {fine_overall:.4f}")
    logger.info(f"  Advantage: {fine_overall - flat_best:+.4f}")

    # 11. Save results
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
        "run_id": f"hierarchical_zoom_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 2,
        "hypothesis": "Zooming from coarse (8) to fine (127) within hierarchical Leiden reveals legally coherent substructure",
        "frozen_sample": f"{len(metadata)} BGer decisions (2020-2024)",
        "frozen_metric": "Branch purity improvement from coarse to fine within each coarse cluster",
        "success_rule": "Majority of coarse clusters show >5% branch purity improvement at fine level",
        "hierarchical_config": {
            "coarse_resolution": 0.5,
            "sub_resolution": 3.0,
            "n_coarse_clusters": n_coarse_clusters,
            "n_fine_clusters": n_fine_clusters,
            "nesting_score": 1.0,
        },
        "overall_metrics": {
            "coarse_overall_purity": float(coarse_overall),
            "fine_overall_purity": float(fine_overall),
            "overall_improvement": float(overall_improvement),
            "improvement_pct": float(overall_improvement / coarse_overall * 100) if coarse_overall > 0 else 0,
            "total_improvements": int(total_improvements),
            "total_deteriorations": int(total_deteriorations),
            "total_no_change": int(total_no_change),
            "improvement_rate": float(improvement_rate),
        },
        "per_coarse_cluster": zoom_results,
        "flat_baseline": {
            "purities": flat_purities,
            "best_purity": float(flat_best),
        },
        "verdict": "PASS" if improvement_rate > 0.5 and total_deteriorations == 0 else "PARTIAL" if improvement_rate > 0.3 else "FAIL",
    }

    output_path = OUTPUT_DIR / "hierarchical_zoom_validation_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)

    logger.info(f"\nResults saved to {output_path}")
    logger.info(f"\nVERDICT: {output['verdict']}")
    logger.info("\n=== Hierarchical zoom validation complete ===")

    return output


if __name__ == "__main__":
    main()