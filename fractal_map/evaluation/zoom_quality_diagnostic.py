#!/usr/bin/env python3
"""
Zoom Quality Diagnostic — Comparative profiling across all legal-distance modes.

Measures zoom coherence quality across the full resolution ladder for every
validated legal-distance mode, going beyond simple branch-purity improvement
to identify:
  1. Per-transition zoom quality (which coarse→fine transitions are productive)
  2. Split vs merge analysis (how many clusters split vs stay unified at each zoom)
  3. Meaningful-split rate (do splits correspond to legal domain distinctions)
  4. Zoom stability score (consistency across all 6 transitions)
  5. Hierarchical vs flat advantage (does the tree structure help vs flat Leiden)

Product decision: Provides data to choose the best zoom parameters and modes
for 192k scaling and for the product zoom UI.

Frozen before observation:
  - Corpus: 1000 BGer decisions (2020-2024)
  - Modes: all 21 validated legal-distance modes
  - Metric: multi-dimensional zoom quality score
  - Success: produces actionable mode ranking and transition-quality profile
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASE = Path("/home/runner/work/LexMachina/LexMachina")
RESULTS_DIR = BASE / "results/fractal_map"
MODES_DIR = RESULTS_DIR / "legal_distance_modes"
CP_DIR = RESULTS_DIR / "hierarchical_map_center_projected"
OUTPUT_DIR = RESULTS_DIR / "evaluation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RESOLUTIONS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
TRANSITIONS = [
    ("0.25", "0.5"), ("0.5", "0.75"), ("0.75", "1.0"),
    ("1.0", "1.5"), ("1.5", "2.0"), ("2.0", "3.0"),
]

# All 21 available legal-distance modes
ALL_MODES = [
    "debiased_citation_blended",
    "legal_cited_decisions_only",
    "hybrid_alpha_03",
    "hybrid_alpha_05",
    "legal_issues_outcomes",
    "linear_metric_epoch4",
    "mahalanobis_metric_epoch4",
    "cited_decisions_tfidf",
    "hybrid_cited_0.3",
    "cited_decisions_tfidf_hybrid_cp64_0.3",
    "cited_decisions_tfidf_hybrid_cp64_0.5",
    "cited_decisions_tfidf_hybrid_cp64_0.7",
    "cited_decisions_tfidf_hybrid_cp768_0.3",
    "cited_decisions_tfidf_hybrid_cp768_0.5",
    "cited_decisions_tfidf_hybrid_cp768_0.7",
    "hybrid_stabilized_epoch1",
    "cited_decisions_tfidf_outcome_hybrid_0.5",
    "cited_decisions_tfidf_outcome_hybrid_0.7",
    "following_alpha0.3",
    "criticizing_alpha0.3",
    "citing_alpha0.3",
]


def load_branch_labels():
    """Load branch labels from corpus files."""
    metadata_path = RESULTS_DIR / "baseline/metadata.json"
    with open(metadata_path) as f:
        metadata = json.load(f)
    id_to_idx = {m['decision_id']: i for i, m in enumerate(metadata)}

    CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
    branch_map = {}
    for year_file in sorted(CORPUS_DIR.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                did = d.get('decision_id', '')
                if did in id_to_idx:
                    branch_map[did] = d.get('branch')

    return np.array([branch_map.get(m['decision_id'], 'unknown') for m in metadata])


def load_mode_labels(mode_id, resolution):
    """Load label array for a mode at a given resolution."""
    path = MODES_DIR / mode_id / f"labels_res_{resolution}.npy"
    if not path.exists():
        return None
    return np.load(path)


def compute_cluster_purity(labels, branch_labels):
    """Compute purity for each cluster (excluding noise label -1)."""
    unique_labels = np.unique(labels)
    unique_labels = unique_labels[unique_labels != -1]
    purities = []
    for cl in unique_labels:
        mask = labels == cl
        cl_branches = branch_labels[mask]
        if len(cl_branches) == 0:
            continue
        counts = Counter(cl_branches)
        most_common_count = counts.most_common(1)[0][1]
        purities.append(most_common_count / len(cl_branches))
    return purities


def compute_overall_purity(labels, branch_labels):
    """Compute weighted overall purity."""
    purities = compute_cluster_purity(labels, branch_labels)
    return float(np.mean(purities)) if purities else 0.0


def analyze_transition(labels_coarse, labels_fine, branch_labels):
    """
    Analyze a single coarse→fine zoom transition.
    
    Returns dict with:
      - n_coarse, n_fine: cluster counts
      - n_splits: coarse clusters that split into multiple fine clusters
      - n_unified: coarse clusters that stay as single fine cluster
      - split_rate: fraction of clusters that split
      - purity_coarse, purity_fine: overall purity at each level
      - purity_delta: fine - coarse purity
      - split_quality: purity improvement specifically in splitting clusters
      - unified_quality: purity change in unified clusters
    """
    coarse_ids = np.unique(labels_coarse)
    coarse_ids = coarse_ids[coarse_ids != -1]
    
    n_splits = 0
    n_unified = 0
    split_purity_deltas = []
    unified_purity_deltas = []
    total_coarse_size = len(labels_coarse)
    
    for cid in coarse_ids:
        coarse_mask = labels_coarse == cid
        coarse_size = coarse_mask.sum()
        fine_labels_in_coarse = labels_fine[coarse_mask]
        unique_fine = np.unique(fine_labels_in_coarse)
        unique_fine = unique_fine[unique_fine != -1]
        
        # Compute coarse cluster purity
        coarse_branches = branch_labels[coarse_mask]
        coarse_branches_valid = coarse_branches[coarse_branches != 'unknown']
        if len(coarse_branches_valid) == 0:
            continue
        coarse_pur = Counter(coarse_branches_valid).most_common(1)[0][1] / len(coarse_branches_valid)
        
        if len(unique_fine) > 1:
            # This cluster splits
            n_splits += 1
            # Compute weighted fine purity within this coarse cluster
            fine_purs = []
            for fid in unique_fine:
                fine_mask_in_coarse = fine_labels_in_coarse == fid
                fine_branches = coarse_branches_valid[fine_mask_in_coarse[fine_mask_in_coarse]] if False else \
                    branch_labels[np.where(coarse_mask)[0][fine_mask_in_coarse]]
                fine_branches_valid = fine_branches[fine_branches != 'unknown']
                if len(fine_branches_valid) > 0:
                    fine_pur = Counter(fine_branches_valid).most_common(1)[0][1] / len(fine_branches_valid)
                    fine_purs.append((fine_pur, len(fine_branches_valid)))
            
            if fine_purs:
                total_fine = sum(s for _, s in fine_purs)
                weighted_fine_pur = sum(p * s for p, s in fine_purs) / total_fine
                split_purity_deltas.append(weighted_fine_pur - coarse_pur)
        else:
            # Unified - no split
            n_unified += 1
            if len(unique_fine) == 1:
                fine_mask_in_coarse = fine_labels_in_coarse == unique_fine[0]
                fine_branches = branch_labels[np.where(coarse_mask)[0][fine_mask_in_coarse]]
                fine_branches_valid = fine_branches[fine_branches != 'unknown']
                if len(fine_branches_valid) > 0:
                    fine_pur = Counter(fine_branches_valid).most_common(1)[0][1] / len(fine_branches_valid)
                    unified_purity_deltas.append(fine_pur - coarse_pur)
    
    purity_coarse = compute_overall_purity(labels_coarse, branch_labels)
    purity_fine = compute_overall_purity(labels_fine, branch_labels)
    
    split_rate = n_splits / (n_splits + n_unified) if (n_splits + n_unified) > 0 else 0
    split_quality = float(np.mean(split_purity_deltas)) if split_purity_deltas else 0.0
    unified_quality = float(np.mean(unified_purity_deltas)) if unified_purity_deltas else 0.0
    
    # Meaningful split: splits where purity improves (not just noise splitting)
    meaningful_splits = sum(1 for d in split_purity_deltas if d > 0)
    meaningful_split_rate = meaningful_splits / n_splits if n_splits > 0 else 0
    
    return {
        'n_coarse': len(coarse_ids),
        'n_fine': len(np.unique(labels_fine[labels_fine != -1])),
        'n_splits': n_splits,
        'n_unified': n_unified,
        'split_rate': float(split_rate),
        'purity_coarse': float(purity_coarse),
        'purity_fine': float(purity_fine),
        'purity_delta': float(purity_fine - purity_coarse),
        'split_quality': split_quality,
        'unified_quality': unified_quality,
        'n_meaningful_splits': meaningful_splits,
        'meaningful_split_rate': float(meaningful_split_rate),
    }


def compute_zoom_stability(transition_results):
    """
    Compute zoom stability score: consistency of purity across transitions.
    Low variance in purity_delta across transitions = more stable zoom.
    """
    deltas = [t['purity_delta'] for t in transition_results]
    if not deltas:
        return 0.0
    
    # Stability = fraction of non-negative deltas * (1 - coefficient of variation)
    non_negative = sum(1 for d in deltas if d >= 0) / len(deltas)
    mean_delta = np.mean(deltas)
    std_delta = np.std(deltas)
    cv = std_delta / abs(mean_delta) if abs(mean_delta) > 1e-10 else 1.0
    cv_component = max(0, 1 - cv)
    
    return float(non_negative * 0.5 + cv_component * 0.5)


def compute_zoom_quality_score(mode_result):
    """
    Compute composite zoom quality score from transition results.
    
    Components:
      - mean_purity_delta: average purity improvement across transitions (weight: 0.3)
      - meaningful_split_rate: fraction of splits that improve purity (weight: 0.25)
      - stability: consistency across transitions (weight: 0.25)
      - max_purity: highest purity achieved at finest resolution (weight: 0.2)
    """
    transitions = mode_result['transitions']
    if not transitions:
        return 0.0
    
    mean_delta = np.mean([t['purity_delta'] for t in transitions])
    mean_meaningful = np.mean([t['meaningful_split_rate'] for t in transitions])
    stability = mode_result['stability_score']
    max_purity = max(t['purity_fine'] for t in transitions)
    
    score = (
        mean_delta * 0.3 +
        mean_meaningful * 0.25 +
        stability * 0.25 +
        max_purity * 0.2
    )
    return float(score)


def analyze_mode(mode_id, branch_labels):
    """Complete zoom quality analysis for a single mode."""
    logger.info(f"  Analyzing {mode_id}...")
    
    labels = {}
    for res in RESOLUTIONS:
        lbl = load_mode_labels(mode_id, res)
        if lbl is None:
            logger.warning(f"    Missing labels for res={res}")
            return None
        labels[res] = lbl
    
    transition_results = []
    for res_coarse, res_fine in TRANSITIONS:
        lc = labels[float(res_coarse)]
        lf = labels[float(res_fine)]
        result = analyze_transition(lc, lf, branch_labels)
        result['transition'] = f"{res_coarse}→{res_fine}"
        transition_results.append(result)
    
    stability = compute_zoom_stability(transition_results)
    
    mode_result = {
        'mode_id': mode_id,
        'n_decisions': int(len(branch_labels)),
        'cluster_counts': {f"res_{r}": int(len(np.unique(labels[r][labels[r] != -1]))) for r in RESOLUTIONS},
        'transitions': transition_results,
        'stability_score': stability,
        'mean_purity_delta': float(np.mean([t['purity_delta'] for t in transition_results])),
        'mean_split_rate': float(np.mean([t['split_rate'] for t in transition_results])),
        'mean_meaningful_split_rate': float(np.mean([t['meaningful_split_rate'] for t in transition_results])),
        'finest_purity': float(compute_overall_purity(labels[3.0], branch_labels)),
    }
    
    mode_result['zoom_quality_score'] = compute_zoom_quality_score(mode_result)
    
    return mode_result


def analyze_center_projected_hierarchical(branch_labels):
    """Analyze the default center_projected_hierarchical mode using its hierarchical labels."""
    logger.info("  Analyzing center_projected_hierarchical (default)...")
    
    # Load the hierarchical labels at each resolution
    labels = {}
    for res in RESOLUTIONS:
        path = CP_DIR / f"labels_res_{res}.npy"
        if path.exists():
            labels[res] = np.load(path)
        else:
            logger.warning(f"    Missing CP labels for res={res}")
            return None
    
    transition_results = []
    for res_coarse, res_fine in TRANSITIONS:
        lc = labels[float(res_coarse)]
        lf = labels[float(res_fine)]
        result = analyze_transition(lc, lf, branch_labels)
        result['transition'] = f"{res_coarse}→{res_fine}"
        transition_results.append(result)
    
    stability = compute_zoom_stability(transition_results)
    
    mode_result = {
        'mode_id': 'center_projected_hierarchical',
        'n_decisions': int(len(branch_labels)),
        'cluster_counts': {f"res_{r}": int(len(np.unique(labels[r][labels[r] != -1]))) for r in RESOLUTIONS},
        'transitions': transition_results,
        'stability_score': stability,
        'mean_purity_delta': float(np.mean([t['purity_delta'] for t in transition_results])),
        'mean_split_rate': float(np.mean([t['split_rate'] for t in transition_results])),
        'mean_meaningful_split_rate': float(np.mean([t['meaningful_split_rate'] for t in transition_results])),
        'finest_purity': float(compute_overall_purity(labels[3.0], branch_labels)),
    }
    
    mode_result['zoom_quality_score'] = compute_zoom_quality_score(mode_result)
    
    return mode_result


def main():
    logger.info("=" * 70)
    logger.info("ZOOM QUALITY DIAGNOSTIC — Comparative Mode Profiling")
    logger.info("=" * 70)
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Direction version: 10")
    logger.info(f"Corpus: 1000 BGer decisions (2020-2024)")
    logger.info(f"Modes: {len(ALL_MODES)} legal-distance + 1 center_projected_hierarchical")
    logger.info(f"Resolutions: {RESOLUTIONS}")
    logger.info(f"Transitions: {len(TRANSITIONS)}")
    
    # 1. Load branch labels
    logger.info("\n1. Loading branch labels...")
    branch_labels = load_branch_labels()
    branch_dist = Counter(branch_labels)
    logger.info(f"   {len(branch_labels)} decisions, branches: {dict(branch_dist)}")
    
    # 2. Analyze center_projected_hierarchical (default)
    logger.info("\n2. Analyzing center_projected_hierarchical (default)...")
    default_result = analyze_center_projected_hierarchical(branch_labels)
    if default_result:
        logger.info(f"   Zoom quality score: {default_result['zoom_quality_score']:.4f}")
        logger.info(f"   Mean purity delta: {default_result['mean_purity_delta']:+.4f}")
        logger.info(f"   Mean meaningful split rate: {default_result['mean_meaningful_split_rate']:.1%}")
        logger.info(f"   Stability: {default_result['stability_score']:.4f}")
        logger.info(f"   Finest purity: {default_result['finest_purity']:.4f}")
    
    # 3. Analyze all legal-distance modes
    logger.info("\n3. Analyzing legal-distance modes...")
    mode_results = {}
    for mode_id in ALL_MODES:
        result = analyze_mode(mode_id, branch_labels)
        if result:
            mode_results[mode_id] = result
            logger.info(f"   {mode_id}: quality={result['zoom_quality_score']:.4f}, "
                       f"delta={result['mean_purity_delta']:+.4f}, "
                       f"meaningful={result['mean_meaningful_split_rate']:.1%}")
    
    # 4. Rank modes
    logger.info("\n4. Ranking modes by zoom quality score...")
    all_results = list(mode_results.values())
    if default_result:
        all_results.append(default_result)
    
    all_results.sort(key=lambda x: x['zoom_quality_score'], reverse=True)
    
    logger.info(f"\n{'Rank':<5} {'Mode':<50} {'ZQ Score':<10} {'Purity Δ':<10} {'Splits':<8} {'Stability':<10}")
    logger.info("-" * 93)
    for i, r in enumerate(all_results, 1):
        logger.info(f"{i:<5} {r['mode_id']:<50} {r['zoom_quality_score']:<10.4f} "
                   f"{r['mean_purity_delta']:>+10.4f} {r['mean_split_rate']:<8.1%} "
                   f"{r['stability_score']:<10.4f}")
    
    # 5. Transition analysis (aggregate across modes)
    logger.info("\n5. Transition quality profile (aggregate)...")
    transition_agg = {}
    for t_key in [f"{c}→{f}" for c, f in TRANSITIONS]:
        deltas = []
        meaningful_rates = []
        for r in all_results:
            for t in r['transitions']:
                if t['transition'] == t_key:
                    deltas.append(t['purity_delta'])
                    meaningful_rates.append(t['meaningful_split_rate'])
        if deltas:
            transition_agg[t_key] = {
                'mean_delta': float(np.mean(deltas)),
                'std_delta': float(np.std(deltas)),
                'mean_meaningful_split_rate': float(np.mean(meaningful_rates)),
                'n_modes': len(deltas),
            }
            logger.info(f"  {t_key}: Δ={np.mean(deltas):+.4f}±{np.std(deltas):.4f}, "
                       f"meaningful_splits={np.mean(meaningful_rates):.1%}")
    
    # 6. Save results
    logger.info("\n6. Saving diagnostic results...")
    
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
        "run_id": f"zoom_quality_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 10,
        "hypothesis": "Multi-dimensional zoom quality profiling identifies best modes and transitions for 192k scaling",
        "frozen_sample": "1000 BGer decisions (2020-2024)",
        "frozen_metric": "Zoom quality score (composite: purity_delta, meaningful_split_rate, stability, max_purity)",
        "resolutions": RESOLUTIONS,
        "transitions": TRANSITIONS,
        "n_modes_evaluated": len(all_results),
        "ranking": [
            {
                'rank': i + 1,
                'mode_id': r['mode_id'],
                'zoom_quality_score': r['zoom_quality_score'],
                'mean_purity_delta': r['mean_purity_delta'],
                'mean_split_rate': r['mean_split_rate'],
                'mean_meaningful_split_rate': r['mean_meaningful_split_rate'],
                'stability_score': r['stability_score'],
                'finest_purity': r['finest_purity'],
                'cluster_counts': r['cluster_counts'],
            }
            for i, r in enumerate(all_results)
        ],
        "transition_profile": transition_agg,
        "per_mode_results": all_results,
    }
    
    output_path = OUTPUT_DIR / "zoom_quality_diagnostic_results.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)
    
    logger.info(f"\nResults saved to {output_path}")
    
    # 7. Summary
    logger.info("\n" + "=" * 70)
    logger.info("ZOOM QUALITY DIAGNOSTIC — SUMMARY")
    logger.info("=" * 70)
    if all_results:
        best = all_results[0]
        worst = all_results[-1]
        logger.info(f"\nBest mode: {best['mode_id']} (ZQ={best['zoom_quality_score']:.4f})")
        logger.info(f"Worst mode: {worst['mode_id']} (ZQ={worst['zoom_quality_score']:.4f})")
        logger.info(f"Score range: {worst['zoom_quality_score']:.4f} — {best['zoom_quality_score']:.4f}")
        
        # Identify best transition
        best_transition = max(transition_agg.items(), key=lambda x: x[1]['mean_delta'])
        worst_transition = min(transition_agg.items(), key=lambda x: x[1]['mean_delta'])
        logger.info(f"\nBest transition: {best_transition[0]} (Δ={best_transition[1]['mean_delta']:+.4f})")
        logger.info(f"Worst transition: {worst_transition[0]} (Δ={worst_transition[1]['mean_delta']:+.4f})")
    
    logger.info("\n=== Zoom quality diagnostic complete ===")
    
    return output


if __name__ == "__main__":
    main()
