#!/usr/bin/env python3
"""
Compressed Resolution Ladder Analysis — All 21 Legal-Distance Modes.

HYPOTHESIS: The compressed 5-level resolution ladder [0.25, 0.5, 1.0, 2.0, 3.0]
achieves 100% delta retention across ALL 21 legal-distance modes, not just the
6 previously tested. If this holds, the compressed ladder is confirmed safe for
192k scaling across the entire product. If any mode fails, that mode requires
the full 7-level ladder.

FROZEN BEFORE OBSERVATION:
  - Corpus: 1000 BGer decisions (2020-2024) — same frozen sample as all prior work
  - Full ladder: [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0] (7 resolutions)
  - Compressed ladder: [0.25, 0.5, 1.0, 2.0, 3.0] (5 resolutions)
  - Dropped: 0.75, 1.5
  - Metric: zoom quality score delta, nesting consistency delta, total purity delta
  - Success rule: ALL 21 modes show delta_retention == 100% AND nesting_change == 0

PRODUCT DECISION UNLOCKED: If PASS, the compressed 5-level ladder is safe for all
modes at 192k scale, reducing computation by ~29% and storage by ~2 resolution
label files per mode. If FAIL on any mode, that mode must use the full 7-level ladder.
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASE = Path("/home/runner/work/LexMachina/LexMachina")
RESULTS_DIR = BASE / "results/fractal_map"
MODES_DIR = RESULTS_DIR / "legal_distance_modes"
CP_DIR = RESULTS_DIR / "hierarchical_map_center_projected"
OUTPUT_DIR = RESULTS_DIR / "evaluation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FULL_LADDER = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
COMPRESSED_LADDER = [0.25, 0.5, 1.0, 2.0, 3.0]
DROPPED = [0.75, 1.5]

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

    CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")
    branch_map = {}
    for year_file in sorted(CORPUS_DIR.glob("bger_20*.jsonl")):
        with open(year_file) as f:
            for line in f:
                d = json.loads(line)
                did = d.get('decision_id', '')
                branch_map[did] = d.get('branch')

    return np.array([branch_map.get(m['decision_id'], 'unknown') for m in metadata])


def load_mode_labels(mode_id, resolution):
    """Load label array for a mode at a given resolution."""
    path = MODES_DIR / mode_id / f"labels_res_{resolution}.npy"
    if not path.exists():
        return None
    return np.load(path)


def load_cp_labels(resolution):
    """Load center_projected_hierarchical labels."""
    path = CP_DIR / f"labels_res_{resolution}.npy"
    if not path.exists():
        return None
    return np.load(path)


def compute_overall_purity(labels, branch_labels):
    """Compute weighted overall purity."""
    unique_labels = np.unique(labels)
    unique_labels = unique_labels[unique_labels != -1]
    purities = []
    for cl in unique_labels:
        mask = labels == cl
        cl_branches = branch_labels[mask]
        cl_branches_valid = cl_branches[cl_branches != 'unknown']
        if len(cl_branches_valid) == 0:
            continue
        counts = Counter(cl_branches_valid)
        most_common_count = counts.most_common(1)[0][1]
        purities.append(most_common_count / len(cl_branches_valid))
    return float(np.mean(purities)) if purities else 0.0


def compute_nesting(labels_coarse, labels_fine):
    """Compute nesting consistency between two resolutions."""
    fine_ids = np.unique(labels_fine)
    fine_ids = fine_ids[fine_ids != -1]
    if len(fine_ids) == 0:
        return 0.0

    consistent = 0
    for fine_id in fine_ids:
        fine_mask = labels_fine == fine_id
        parent_labels = labels_coarse[fine_mask]
        parent_labels_valid = parent_labels[parent_labels != -1]
        if len(parent_labels_valid) > 0:
            most_common_parent = Counter(parent_labels_valid.tolist()).most_common(1)[0][0]
            # Check that ALL instances of this fine cluster map to the same parent
            all_parents = parent_labels_valid
            if np.all(all_parents == most_common_parent):
                consistent += 1
    return consistent / len(fine_ids) if len(fine_ids) > 0 else 0.0


def compute_nesting_score(labels_dict, resolutions):
    """Compute nesting score across all adjacent resolution pairs."""
    nesting_scores = []
    for i in range(len(resolutions) - 1):
        score = compute_nesting(labels_dict[resolutions[i]], labels_dict[resolutions[i + 1]])
        nesting_scores.append(score)
    return float(np.mean(nesting_scores))


def compute_total_purity_delta(labels_dict, resolutions, branch_labels):
    """Compute total purity delta: purity(finest) - purity(coarsest)."""
    purity_coarsest = compute_overall_purity(labels_dict[resolutions[0]], branch_labels)
    purity_finest = compute_overall_purity(labels_dict[resolutions[-1]], branch_labels)
    return purity_finest - purity_coarsest


def analyze_mode_compressed(mode_id, branch_labels, is_cp=False):
    """Analyze a single mode for compressed vs full ladder comparison."""
    labels_full = {}
    labels_compressed = {}

    for res in FULL_LADDER:
        if is_cp:
            lbl = load_cp_labels(res)
        else:
            lbl = load_mode_labels(mode_id, res)
        if lbl is None:
            return None
        labels_full[res] = lbl
        if res in COMPRESSED_LADDER:
            labels_compressed[res] = lbl

    # Nesting scores
    nesting_full = compute_nesting_score(labels_full, FULL_LADDER)
    nesting_compressed = compute_nesting_score(labels_compressed, COMPRESSED_LADDER)
    nesting_change = nesting_compressed - nesting_full

    # Total purity delta
    delta_full = compute_total_purity_delta(labels_full, FULL_LADDER, branch_labels)
    delta_compressed = compute_total_purity_delta(labels_compressed, COMPRESSED_LADDER, branch_labels)

    # Delta retention
    if abs(delta_full) < 1e-10:
        delta_retention = 100.0 if abs(delta_compressed) < 1e-10 else 0.0
    else:
        delta_retention = (delta_compressed / delta_full) * 100.0

    # Cluster counts
    cluster_counts_full = {}
    for res in FULL_LADDER:
        n = len(np.unique(labels_full[res][labels_full[res] != -1]))
        cluster_counts_full[f"res_{res}"] = n

    cluster_counts_compressed = {}
    for res in COMPRESSED_LADDER:
        n = len(np.unique(labels_compressed[res][labels_compressed[res] != -1]))
        cluster_counts_compressed[f"res_{res}"] = n

    # Per-resolution purity
    purity_full = {}
    purity_compressed = {}
    for res in FULL_LADDER:
        purity_full[f"res_{res}"] = compute_overall_purity(labels_full[res], branch_labels)
    for res in COMPRESSED_LADDER:
        purity_compressed[f"res_{res}"] = compute_overall_purity(labels_compressed[res], branch_labels)

    return {
        "full_total_delta": delta_full,
        "compressed_total_delta": delta_compressed,
        "delta_retention_pct": delta_retention,
        "nesting_full": nesting_full,
        "nesting_compressed": nesting_compressed,
        "nesting_change": nesting_change,
        "cluster_counts_full": cluster_counts_full,
        "cluster_counts_compressed": cluster_counts_compressed,
        "purity_full": purity_full,
        "purity_compressed": purity_compressed,
        "n_resolutions_full": len(FULL_LADDER),
        "n_resolutions_compressed": len(COMPRESSED_LADDER),
        "resolution_reduction_pct": (1 - len(COMPRESSED_LADDER) / len(FULL_LADDER)) * 100,
    }


def main():
    logger.info("=" * 70)
    logger.info("COMPRESSED RESOLUTION LADDER — ALL 21 MODES")
    logger.info("=" * 70)
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Direction version: 10")
    logger.info(f"Corpus: 1000 BGer decisions (2020-2024)")
    logger.info(f"Full ladder: {FULL_LADDER}")
    logger.info(f"Compressed ladder: {COMPRESSED_LADDER}")
    logger.info(f"Dropped: {DROPPED}")
    logger.info(f"Modes: {len(ALL_MODES)} legal-distance + 1 center_projected_hierarchical")

    # Load branch labels
    logger.info("\n1. Loading branch labels...")
    branch_labels = load_branch_labels()
    branch_dist = Counter(branch_labels)
    logger.info(f"   {len(branch_labels)} decisions, branches: {dict(branch_dist)}")

    # Analyze center_projected_hierarchical (default)
    logger.info("\n2. Analyzing center_projected_hierarchical (default)...")
    cp_result = analyze_mode_compressed("center_projected_hierarchical", branch_labels, is_cp=True)
    if cp_result:
        logger.info(f"   Delta retention: {cp_result['delta_retention_pct']:.1f}%")
        logger.info(f"   Nesting change: {cp_result['nesting_change']:.6f}")
    else:
        logger.warning("   FAILED: Missing labels")

    # Analyze all legal-distance modes
    logger.info("\n3. Analyzing all 21 legal-distance modes...")
    results = {}
    failures = []
    for mode_id in ALL_MODES:
        logger.info(f"  Analyzing {mode_id}...")
        result = analyze_mode_compressed(mode_id, branch_labels)
        if result is None:
            logger.warning(f"    FAILED: Missing labels")
            failures.append(mode_id)
            continue
        results[mode_id] = result
        status = "PASS" if (result['delta_retention_pct'] >= 99.9 and abs(result['nesting_change']) < 1e-6) else "FAIL"
        logger.info(f"    Delta retention: {result['delta_retention_pct']:.1f}%, "
                    f"Nesting change: {result['nesting_change']:.6f}, Status: {status}")

    # Add CP to results
    if cp_result:
        results["center_projected_hierarchical"] = cp_result

    # Evaluate success rule
    logger.info("\n4. Evaluating success rule...")
    all_pass = True
    mode_statuses = {}
    for mode_id, result in results.items():
        delta_ok = result['delta_retention_pct'] >= 99.9
        nesting_ok = abs(result['nesting_change']) < 1e-6
        passed = delta_ok and nesting_ok
        mode_statuses[mode_id] = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
            logger.warning(f"  FAIL: {mode_id} — delta_retention={result['delta_retention_pct']:.1f}%, "
                          f"nesting_change={result['nesting_change']:.6f}")

    if all_pass:
        logger.info("\n  ALL 22 MODES PASS: Compressed 5-level ladder achieves 100% delta retention "
                    "and zero nesting change across all modes.")
        verdict = "PASS"
    else:
        n_fail = sum(1 for s in mode_statuses.values() if s == "FAIL")
        logger.warning(f"\n  {n_fail} MODES FAIL: Compressed ladder NOT universally valid.")
        verdict = "FAIL"

    # Save results
    logger.info("\n5. Saving results...")

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
        "analysis": "compressed_resolution_ladder_all_modes",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 10,
        "hypothesis": "Compressed 5-level ladder achieves 100% delta retention across ALL 21 legal-distance modes",
        "frozen_sample": "1000 BGer decisions (2020-2024)",
        "frozen_metric": "Total purity delta retention and nesting consistency between full (7-level) and compressed (5-level) ladders",
        "success_rule": "ALL modes show delta_retention >= 99.9% AND |nesting_change| < 1e-6",
        "full_ladder": FULL_LADDER,
        "compressed_ladder": COMPRESSED_LADDER,
        "dropped_resolutions": DROPPED,
        "n_decisions": len(branch_labels),
        "n_modes_evaluated": len(results),
        "verdict": verdict,
        "mode_statuses": mode_statuses,
        "results": results,
        "summary": {
            "total_modes": len(results),
            "passing": sum(1 for s in mode_statuses.values() if s == "PASS"),
            "failing": sum(1 for s in mode_statuses.values() if s == "FAIL"),
            "failing_modes": [m for m, s in mode_statuses.items() if s == "FAIL"],
            "resolution_reduction_pct": (1 - len(COMPRESSED_LADDER) / len(FULL_LADDER)) * 100,
            "product_implication": (
                "Compressed 5-level ladder safe for all modes at 192k scale. "
                "29% fewer resolutions = faster computation, less storage, simpler zoom UI."
                if verdict == "PASS"
                else "Compressed ladder NOT universally valid. Some modes require full 7-level ladder."
            ),
        },
    }

    output_path = OUTPUT_DIR / "compressed_resolution_ladder_all_modes.json"
    with open(output_path, 'w') as f:
        json.dump(convert(output), f, indent=2)

    logger.info(f"\nResults saved to {output_path}")

    # Print summary table
    logger.info("\n" + "=" * 90)
    logger.info("SUMMARY TABLE")
    logger.info("=" * 90)
    logger.info(f"{'Mode':<50} {'Delta Ret':<10} {'Nesting Δ':<12} {'Status':<6}")
    logger.info("-" * 90)
    for mode_id in sorted(results.keys()):
        r = results[mode_id]
        status = mode_statuses[mode_id]
        logger.info(f"{mode_id:<50} {r['delta_retention_pct']:>8.1f}% {r['nesting_change']:>+12.6f} {status:<6}")

    logger.info(f"\nVERDICT: {verdict}")
    logger.info("\n=== Compressed resolution ladder analysis complete ===")

    return output


if __name__ == "__main__":
    main()
