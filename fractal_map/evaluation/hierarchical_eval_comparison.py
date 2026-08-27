#!/usr/bin/env python3
"""
Evaluation comparison: Leiden hierarchical map vs agglomerative hierarchy baseline.

Uses the evaluation lane's methodology:
- Nesting score (child clusters fully within one parent)
- Branch purity per level
- Legal area NMI and purity

Frozen before observation:
- Corpus: 1000 BGer decisions (2020-2024)
- Embeddings: concat_center_tfidf (896-dim)
- Leiden resolutions: [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
- Agglomerative: n_clusters = [5, 8, 11, 16, 21, 24, 27] (matching Leiden)
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
HIERARCHICAL_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/hierarchical_map")
OUTPUT_DIR = Path("/home/runner/work/LexMachina/LexMachina/results/fractal_map/evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_metadata_with_branch():
    """Load baseline metadata and enrich with branch from corpus files."""
    with open(BASELINE_DIR / "metadata.json") as f:
        metadata = json.load(f)
    
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}
    
    corpus_dir = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
    branch_map = {}
    for year_file in sorted(corpus_dir.glob("bger_20*.jsonl")):
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
    corpus_dir = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
    baseline_ids = set(m['decision_id'] for m in metadata)
    decisions = {}
    
    for year_file in sorted(corpus_dir.glob("bger_20*.jsonl")):
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


def compute_purity(true_labels, pred_labels):
    """Compute clustering purity."""
    purity_scores = []
    for cid in set(pred_labels):
        mask = pred_labels == cid
        cluster_true = [true_labels[i] for i in range(len(true_labels)) if mask[i]]
        if cluster_true:
            most_common = Counter(cluster_true).most_common(1)[0][1]
            purity_scores.append(most_common / len(cluster_true))
    return float(np.mean(purity_scores)) if purity_scores else 0.0


def run_agglomerative_comparison(concat_emb, metadata):
    """Run agglomerative clustering at matching resolutions for comparison."""
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics import normalized_mutual_info_score
    
    # Normalize
    norms = np.linalg.norm(concat_emb, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = concat_emb / norms
    
    # Match Leiden cluster counts
    target_clusters = [5, 8, 11, 16, 21, 24, 27]
    resolutions = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    
    agglomerative_labels = {}
    
    for n_clust, res in zip(target_clusters, resolutions):
        clustering = AgglomerativeClustering(
            n_clusters=n_clust, metric="cosine", linkage="average"
        )
        labels = clustering.fit_predict(normalized)
        agglomerative_labels[res] = labels
        logger.info(f"   Agglomerative n_clusters={n_clust}: {len(set(labels))} clusters")
    
    return agglomerative_labels


def compute_nesting_score(hierarchy_labels):
    """Compute strict nesting score: each child cluster within one parent."""
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


def compute_branch_purity_per_level(hierarchy_labels, metadata):
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
    logger.info("=== Hierarchical Map Evaluation Comparison ===")
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
    logger.info(f"   TF-IDF: {tfidf_full.shape}")
    
    # 3. Build concat
    logger.info("\n4. Building concatenated representation...")
    concat_emb = build_concat(baseline_emb, center_emb, tfidf_full)
    logger.info(f"   Concat: {concat_emb.shape}")
    
    # 4. Load Leiden results
    logger.info("\n5. Loading Leiden hierarchical map results...")
    leiden_results_path = HIERARCHICAL_DIR / "hierarchical_map_results.json"
    with open(leiden_results_path) as f:
        leiden_results = json.load(f)
    
    # Reconstruct Leiden labels from assignments file
    assignments_path = HIERARCHICAL_DIR / "cluster_assignments.json"
    with open(assignments_path) as f:
        assignments = json.load(f)
    
    leiden_labels = {}
    for key, labels in assignments.items():
        res = float(key.replace('res_', ''))
        leiden_labels[res] = np.array(labels)
    
    logger.info(f"   Loaded {len(leiden_labels)} Leiden resolutions")
    
    # 5. Run agglomerative comparison
    logger.info("\n6. Running agglomerative clustering comparison...")
    agglo_labels = run_agglomerative_comparison(concat_emb, metadata)
    
    # 6. Compute nesting scores
    logger.info("\n7. Computing nesting scores...")
    leiden_nesting = compute_nesting_score(leiden_labels)
    agglo_nesting = compute_nesting_score(agglo_labels)
    
    leiden_mean_nesting = np.mean([s['nesting_score'] for s in leiden_nesting])
    agglo_mean_nesting = np.mean([s['nesting_score'] for s in agglo_nesting])
    
    logger.info(f"   Leiden mean nesting: {leiden_mean_nesting:.4f}")
    logger.info(f"   Agglomerative mean nesting: {agglo_mean_nesting:.4f}")
    
    # 7. Compute branch purity per level
    logger.info("\n8. Computing branch purity per level...")
    leiden_purity = compute_branch_purity_per_level(leiden_labels, metadata)
    agglo_purity = compute_branch_purity_per_level(agglo_labels, metadata)
    
    logger.info("\n   Leiden branch purity:")
    for res_key in sorted(leiden_purity.keys()):
        lp = leiden_purity[res_key]
        logger.info(f"     {res_key}: purity={lp['mean_branch_purity']:.4f}, n_clusters={lp['n_clusters']}")
    
    logger.info("\n   Agglomerative branch purity:")
    for res_key in sorted(agglo_purity.keys()):
        ap = agglo_purity[res_key]
        logger.info(f"     {res_key}: purity={ap['mean_branch_purity']:.4f}, n_clusters={ap['n_clusters']}")
    
    # 8. Compare with evaluation lane baselines
    logger.info("\n9. Comparison with evaluation lane baselines...")
    
    # Evaluation lane's hierarchy_coherence baseline:
    # baseline: nesting=1.0, purity=[0.691, 0.806, 0.889], mean=0.795
    # concat: nesting=1.0, purity=[0.547, 0.721, 0.867], mean=0.712
    
    eval_baseline_nesting = 1.0
    eval_baseline_purity = 0.795
    eval_concat_nesting = 1.0
    eval_concat_purity = 0.712
    
    logger.info(f"\n   Evaluation lane hierarchy_coherence baselines:")
    logger.info(f"     Baseline: nesting={eval_baseline_nesting}, purity={eval_baseline_purity}")
    logger.info(f"     Concat: nesting={eval_concat_nesting}, purity={eval_concat_purity}")
    
    # Our Leiden results
    leiden_mean_purity = np.mean([leiden_purity[f"res_{r}"]['mean_branch_purity'] 
                                   for r in sorted(leiden_labels.keys())])
    agglo_mean_purity = np.mean([agglo_purity[f"res_{r}"]['mean_branch_purity'] 
                                  for r in sorted(agglo_labels.keys())])
    
    logger.info(f"\n   Our results:")
    logger.info(f"     Leiden: nesting={leiden_mean_nesting:.4f}, purity={leiden_mean_purity:.4f}")
    logger.info(f"     Agglomerative: nesting={agglo_mean_nesting:.4f}, purity={agglo_mean_purity:.4f}")
    
    # 9. Summary
    logger.info("\n" + "=" * 70)
    logger.info("COMPARISON SUMMARY")
    logger.info("=" * 70)
    
    summary = {
        "leiden": {
            "mean_nesting": float(leiden_mean_nesting),
            "mean_branch_purity": float(leiden_mean_purity),
            "per_resolution": leiden_purity,
            "nesting_details": leiden_nesting,
        },
        "agglomerative": {
            "mean_nesting": float(agglo_mean_nesting),
            "mean_branch_purity": float(agglo_mean_purity),
            "per_resolution": agglo_purity,
            "nesting_details": agglo_nesting,
        },
        "evaluation_lane_baselines": {
            "hierarchy_coherence_baseline": {
                "nesting": eval_baseline_nesting,
                "purity": eval_baseline_purity,
            },
            "hierarchy_coherence_concat": {
                "nesting": eval_concat_nesting,
                "purity": eval_concat_purity,
            },
        },
    }
    
    # Determine winner
    if leiden_mean_nesting > agglo_mean_nesting:
        nesting_winner = "leiden"
    elif agglo_mean_nesting > leiden_mean_nesting:
        nesting_winner = "agglomerative"
    else:
        nesting_winner = "tie"
    
    if leiden_mean_purity > agglo_mean_purity:
        purity_winner = "leiden"
    elif agglo_mean_purity > leiden_mean_purity:
        purity_winner = "agglomerative"
    else:
        purity_winner = "tie"
    
    summary["winner"] = {
        "nesting": nesting_winner,
        "purity": purity_winner,
    }
    
    logger.info(f"\n  Nesting winner: {nesting_winner}")
    logger.info(f"    Leiden: {leiden_mean_nesting:.4f} vs Agglomerative: {agglo_mean_nesting:.4f}")
    logger.info(f"\n  Purity winner: {purity_winner}")
    logger.info(f"    Leiden: {leiden_mean_purity:.4f} vs Agglomerative: {agglo_mean_purity:.4f}")
    
    # Key insight
    logger.info("\n  Key insight:")
    if leiden_mean_nesting == 1.0 and agglo_mean_nesting < 1.0:
        logger.info("    Leiden achieves PERFECT nesting (1.0) while agglomerative does not.")
        logger.info("    This is a structural advantage: Leiden's resolution parameter")
        logger.info("    naturally produces nested partitions.")
    elif leiden_mean_nesting == agglo_mean_nesting:
        logger.info(f"    Both achieve equal nesting ({leiden_mean_nesting:.4f}).")
    
    if leiden_mean_purity > agglo_mean_purity:
        logger.info(f"    Leiden also has higher branch purity ({leiden_mean_purity:.4f} vs {agglo_mean_purity:.4f}).")
    elif agglo_mean_purity > leiden_mean_purity:
        logger.info(f"    Agglomerative has higher branch purity ({agglo_mean_purity:.4f} vs {leiden_mean_purity:.4f}).")
    
    # Save
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
        "run_id": f"hierarchical_eval_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 1,
        "hypothesis": "Leiden-based hierarchical map achieves better nesting and branch purity than agglomerative baseline",
        "frozen_sample": f"{len(metadata)} BGer decisions (2020-2024)",
        "frozen_metric": "Nesting consistency, branch purity per level",
        "success_rule": "Leiden nesting >= agglomerative nesting AND Leiden purity >= agglomerative purity",
        **summary,
    }
    
    output_path = OUTPUT_DIR / "hierarchical_eval_comparison.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    logger.info("\n=== Evaluation comparison complete ===")


if __name__ == "__main__":
    main()
