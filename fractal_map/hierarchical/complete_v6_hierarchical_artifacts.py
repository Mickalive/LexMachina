#!/usr/bin/env python3
"""
Complete missing hierarchical artifacts for v6 baseline modes.

The 5 v6 modes (debiased_citation_blended, hybrid_alpha_03, hybrid_alpha_05,
legal_cited_decisions_only, legal_issues_outcomes) were built before the
parameterized legal-distance builder existed. They have labels_res_*.npy at
all 7 resolutions but are missing:
  - labels_hierarchical_best.npy (= labels_res_3.0 for legal-distance modes)
  - labels_coarse_0.5.npy (= labels_res_0.5)
  - hierarchical_map_results.json (nesting, zoom coherence, branch purity)

This script derives the missing artifacts from existing resolution labels
and the baseline metadata, following the same provenance rules as
build_parameterized_legal_distance_map.py.

PROVENANCE RULE: For legal-distance modes, hierarchical_best := labels_res_3.0
(finest resolution). This was verified across all accepted modes.

Usage:
    python complete_v6_hierarchical_artifacts.py
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone

BASE = Path("/home/runner/work/LexMachina/LexMachina")
RESULTS_DIR = BASE / "results/fractal_map/legal_distance_modes"
BASELINE_DIR = BASE / "results/fractal_map/baseline"
CORPUS_DIR = Path("/tmp/lex_accepted/corpus/corpus/normalization/canonical")

RESOLUTIONS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
MIN_CLUSTER_SIZE = 3

# The 5 incomplete v6 modes
INCOMPLETE_MODES = [
    "debiased_citation_blended",
    "hybrid_alpha_03",
    "hybrid_alpha_05",
    "legal_cited_decisions_only",
    "legal_issues_outcomes",
]


def load_metadata():
    """Load baseline metadata and enrich with branch from corpus."""
    meta_file = BASELINE_DIR / "metadata.json"
    with open(meta_file) as f:
        metadata = json.load(f)
    # Take first 1000 for the standard corpus slice
    metadata = metadata[:1000]
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
    return metadata


def compute_branch_purity(labels, metadata, min_cluster_size=3):
    """Compute mean branch purity across clusters."""
    purities = []
    for label in np.unique(labels[labels != -1]):
        mask = labels == label
        indices = np.where(mask)[0]
        if len(indices) < min_cluster_size:
            continue
        branches = [metadata[i].get('branch') for i in indices]
        branches = [b for b in branches if b and b != 'null']
        if branches:
            purities.append(Counter(branches).most_common(1)[0][1] / len(branches))
    return float(np.mean(purities)) if purities else 0


def compute_nesting(hierarchy_labels):
    """Compute nesting consistency between adjacent resolutions."""
    resolutions = sorted(hierarchy_labels.keys())
    nesting = {}
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        coarser_labels = hierarchy_labels[coarser_res]
        finer_labels = hierarchy_labels[finer_res]
        child_to_parent = {}
        for fine_id in np.unique(finer_labels[finer_labels != -1]):
            fine_mask = finer_labels == fine_id
            parent_labels = coarser_labels[fine_mask]
            parent_labels_valid = parent_labels[parent_labels != -1]
            if len(parent_labels_valid) > 0:
                child_to_parent[int(fine_id)] = int(
                    Counter(parent_labels_valid.tolist()).most_common(1)[0][0])
            else:
                child_to_parent[int(fine_id)] = -1
        nesting[f"{coarser_res}_to_{finer_res}"] = {
            'coarser_resolution': coarser_res,
            'finer_resolution': finer_res,
            'nesting_consistency': (sum(1 for c, p in child_to_parent.items() if p != -1)
                                    / len(child_to_parent) if child_to_parent else 0),
        }
    return nesting


def compute_zoom_coherence(hierarchy_labels, metadata, min_cluster_size=3):
    """Compute zoom coherence improvement rate."""
    resolutions = sorted(hierarchy_labels.keys())
    zoom_coherence = {}
    for i in range(len(resolutions) - 1):
        coarser_res = resolutions[i]
        finer_res = resolutions[i + 1]
        coarser_labels = hierarchy_labels[coarser_res]
        finer_labels = hierarchy_labels[finer_res]
        improvements = []
        for coarse_id in np.unique(coarser_labels[coarser_labels != -1]):
            coarse_mask = coarser_labels == coarse_id
            coarse_indices = np.where(coarse_mask)[0]
            if len(coarse_indices) < min_cluster_size:
                continue
            coarse_branches = [metadata[i].get('branch') for i in coarse_indices]
            coarse_branches = [b for b in coarse_branches if b and b != 'null']
            if not coarse_branches:
                continue
            coarse_purity = Counter(coarse_branches).most_common(1)[0][1] / len(coarse_branches)
            child_clusters = []
            for fine_id in np.unique(finer_labels[finer_labels != -1]):
                fine_mask = finer_labels == fine_id
                parent_labels = coarser_labels[fine_mask]
                parent_labels_valid = parent_labels[parent_labels != -1]
                if len(parent_labels_valid) > 0 and \
                        Counter(parent_labels_valid.tolist()).most_common(1)[0][0] == coarse_id:
                    child_clusters.append(fine_id)
            if not child_clusters:
                continue
            child_purities = []
            for child_id in child_clusters:
                child_mask = finer_labels == child_id
                child_indices = np.where(child_mask)[0]
                if len(child_indices) < min_cluster_size:
                    continue
                child_branches = [metadata[i].get('branch') for i in child_indices]
                child_branches = [b for b in child_branches if b and b != 'null']
                if child_branches:
                    child_purities.append(Counter(child_branches).most_common(1)[0][1]
                                          / len(child_branches))
            if child_purities:
                mean_child_purity = np.mean(child_purities)
                improvements.append(mean_child_purity - coarse_purity)
        zoom_coherence[f"{coarser_res}_to_{finer_res}"] = {
            'coarser_resolution': coarser_res,
            'finer_resolution': finer_res,
            'mean_improvement': float(np.mean(improvements)) if improvements else 0,
            'improvement_rate': float(sum(1 for j in improvements if j > 0)
                                      / len(improvements)) if improvements else 0,
        }
    return zoom_coherence


def convert(obj):
    """Convert numpy types to Python types for JSON serialization."""
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert(v) for v in obj]
    return obj


def complete_mode(mode_id, metadata):
    """Generate missing hierarchical artifacts for one mode."""
    mode_dir = RESULTS_DIR / mode_id

    # Load existing resolution labels
    hierarchy_labels = {}
    for res in RESOLUTIONS:
        path = mode_dir / f"labels_res_{res}.npy"
        if not path.exists():
            print(f"  SKIP {mode_id}: missing labels_res_{res}.npy")
            return False
        hierarchy_labels[res] = np.load(path)

    # Verify all have correct size
    for res in RESOLUTIONS:
        if len(hierarchy_labels[res]) != 1000:
            print(f"  SKIP {mode_id}: labels_res_{res}.npy has {len(hierarchy_labels[res])} entries, expected 1000")
            return False

    # Generate labels_hierarchical_best (= labels_res_3.0 for legal-distance modes)
    hierarchical_labels = hierarchy_labels[3.0]
    np.save(mode_dir / "labels_hierarchical_best.npy", hierarchical_labels)

    # Generate labels_coarse_0.5 (= labels_res_0.5)
    coarse_labels = hierarchy_labels[0.5]
    np.save(mode_dir / "labels_coarse_0.5.npy", coarse_labels)

    # Compute hierarchical_map_results.json
    hier_purity = compute_branch_purity(hierarchical_labels, metadata, MIN_CLUSTER_SIZE)
    coarse_purity = compute_branch_purity(coarse_labels, metadata, MIN_CLUSTER_SIZE)

    nesting = compute_nesting(hierarchy_labels)
    mean_nesting = float(np.mean([n['nesting_consistency'] for n in nesting.values()]))

    branch_coherence = {}
    for res in RESOLUTIONS:
        branch_coherence[f"res_{res}"] = {
            'mean_branch_purity': compute_branch_purity(hierarchy_labels[res], metadata, MIN_CLUSTER_SIZE),
            'n_clusters': int(len(np.unique(hierarchy_labels[res][hierarchy_labels[res] != -1]))),
        }

    zoom_coherence = compute_zoom_coherence(hierarchy_labels, metadata, MIN_CLUSTER_SIZE)

    hierarchy_info = {}
    for res in RESOLUTIONS:
        hierarchy_info[f"res_{res}"] = {
            'resolution': res,
            'n_clusters': int(len(set(hierarchy_labels[res][hierarchy_labels[res] != -1]))),
        }

    output = {
        "run_id": f"complete_v6_artifacts_{mode_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction_version": 10,
        "mode_id": mode_id,
        "hypothesis": "Multi-resolution Leiden on legal-distance embeddings produces nested hierarchy",
        "frozen_sample": f"1000 decisions ({mode_id})",
        "frozen_metric": "Nesting consistency, branch purity per level, zoom improvement rate",
        "embeddings_source": f"labels_res_*.npy (derived from existing resolution labels)",
        "corpus_size": 1000,
        "resolutions_tested": RESOLUTIONS,
        "hierarchy_info": hierarchy_info,
        "nesting": nesting,
        "mean_nesting_score": mean_nesting,
        "branch_coherence": branch_coherence,
        "zoom_coherence": zoom_coherence,
        "hierarchical": {
            "config": "fine_3.0 (legal-distance rule: hierarchical_best := finest resolution)",
            "n_clusters": int(len(set(hierarchical_labels[hierarchical_labels != -1]))),
            "branch_purity": hier_purity,
            "coarse_0.5_purity": coarse_purity,
        },
        "summary": {
            "n_decisions": 1000,
            "n_resolutions": len(RESOLUTIONS),
            "mean_branch_purity_all_levels": float(np.mean(
                [branch_coherence[f"res_{r}"]['mean_branch_purity'] for r in RESOLUTIONS])),
        },
        "derived_from": "existing labels_res_*.npy + baseline metadata (no re-clustering)",
        "provenance_note": "labels_hierarchical_best = labels_res_3.0, labels_coarse_0.5 = labels_res_0.5",
    }

    with open(mode_dir / "hierarchical_map_results.json", 'w') as f:
        json.dump(convert(output), f, indent=2)

    n_fine = int(len(set(hierarchical_labels[hierarchical_labels != -1])))
    n_coarse = int(len(set(coarse_labels[coarse_labels != -1])))
    print(f"  OK {mode_id}: hier_best={n_fine} fine, coarse={n_coarse}, "
          f"nesting={mean_nesting:.4f}, hier_purity={hier_purity:.4f}")
    return True


def main():
    print("Loading baseline metadata...")
    metadata = load_metadata()
    print(f"Loaded {len(metadata)} decisions")

    print("\nCompleting missing hierarchical artifacts for v6 modes...")
    results = {}
    for mode_id in INCOMPLETE_MODES:
        mode_dir = RESULTS_DIR / mode_id
        hier_path = mode_dir / "labels_hierarchical_best.npy"
        if hier_path.exists():
            print(f"  SKIP {mode_id}: already has labels_hierarchical_best.npy")
            results[mode_id] = "ALREADY_COMPLETE"
            continue
        results[mode_id] = complete_mode(mode_id, metadata)

    print("\nSummary:")
    for mode_id, status in results.items():
        print(f"  {mode_id}: {status}")

    # Verify all 5 are now complete
    all_complete = True
    for mode_id in INCOMPLETE_MODES:
        mode_dir = RESULTS_DIR / mode_id
        for fname in ["labels_hierarchical_best.npy", "labels_coarse_0.5.npy", "hierarchical_map_results.json"]:
            if not (mode_dir / fname).exists():
                print(f"  STILL MISSING: {mode_dir / fname}")
                all_complete = False

    if all_complete:
        print("\nAll 5 v6 modes now have complete hierarchical artifacts.")
    else:
        print("\nSome modes still have missing artifacts.")


if __name__ == "__main__":
    main()
