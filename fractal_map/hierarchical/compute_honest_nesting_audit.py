#!/usr/bin/env python3
"""Honest nesting audit for all fractal-map compressed-ladder / multi-resolution modes.

Purpose (run 36014970673, operational resume of failed run 36008005345):
  The parameterized legal-distance builders (build_parameterized_legal_distance_map*.py,
  build_21k_hierarchical_map.py, build_174k_hierarchical_map_chamber.py,
  complete_v6_hierarchical_artifacts.py) recorded `mean_nesting_score` as the mean of
  `nesting_consistency`, defined as the fraction of fine clusters whose MAJORITY parent
  label is valid (>= 0). That quantity is ~1.0 by construction for any two independent
  Leiden partitions and does NOT measure nesting.

  The reference implementation of TRUE strict nesting
  (fractal_map/hierarchical/hierarchical_leiden.py::compute_nesting_score,
   fractal_map/hierarchical/hierarchical_map_builder.py::compute_hierarchy_nesting_score)
  counts a fine cluster as nested only if every one of its (non--1) members shares ONE
  unique coarse parent label.

  This audit recomputes BOTH quantities from the committed label arrays
  (labels_res_<res>.npy) for every mode directory, so the discrepancy between recorded
  and honest nesting is quantified, preserved as a negative result, and made
  reproducible.

  Output: results/fractal_map/evaluation/resume_36014970673_nesting_audit.json

  Re-run:
    python3 fractal_map/hierarchical/compute_honest_nesting_audit.py
  """
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[2]
RESULTS = BASE / "results" / "fractal_map"
AUDIT_RUN = "36014970673"

MODE_ROOTS = [
    RESULTS / "legal_distance_modes",
    RESULTS / "hierarchical_map_21k" / "legal_distance_modes",
]
# Reference dirs outside the legal_distance_modes roots (claims audited in earlier gates)
REFERENCE_DIRS = [
    RESULTS / "hierarchical_map_center_projected",
    RESULTS / "scalability" / "legal_distance" / "cited_decisions_tfidf_outcome_hybrid_0.5_n1200",
    RESULTS / "scalability" / "legal_distance" / "cited_decisions_tfidf_outcome_hybrid_0.7_n1200",
]


def strict_nesting_transition(coarser_labels, finer_labels):
    """True strict nesting (identical semantics to hierarchical_leiden.compute_nesting_score).

    A fine cluster counts as nested iff all of its members with a valid (non -1) coarse
    label share ONE unique coarse parent label.
    """
    unique_fine = np.unique(finer_labels[finer_labels != -1])
    consistent = 0
    n_orphans = 0
    for fine_id in unique_fine:
        fine_mask = finer_labels == fine_id
        parent_labels = coarser_labels[fine_mask]
        parent_valid = parent_labels[parent_labels != -1]
        if len(parent_valid) == 0:
            n_orphans += 1
            continue
        if len(set(parent_valid.tolist())) == 1:
            consistent += 1
    score = consistent / len(unique_fine) if len(unique_fine) > 0 else 0.0
    return {
        "nesting_score": float(score),
        "n_fine_clusters": int(len(unique_fine)),
        "n_strictly_consistent": int(consistent),
        "n_orphan_fine_clusters": int(n_orphans),
    }


def majority_coverage_transition(coarser_labels, finer_labels):
    """Legacy 'nesting_consistency': fraction of fine clusters with a valid MAJORITY
    parent (the metric recorded by the parameterized compressed builders)."""
    unique_fine = np.unique(finer_labels[finer_labels != -1])
    covered = 0
    for fine_id in unique_fine:
        fine_mask = finer_labels == fine_id
        parent_labels = coarser_labels[fine_mask]
        parent_valid = parent_labels[parent_labels != -1]
        if len(parent_valid) > 0:
            covered += 1
    score = covered / len(unique_fine) if len(unique_fine) > 0 else 0.0
    return {
        "majority_coverage": float(score),
        "n_majority_covered": int(covered),
    }


def load_resolutions(mode_dir, recorded):
    res = recorded.get("resolutions_tested")
    if res:
        return list(res)
    # fallback: derive from committed label files
    files = sorted(mode_dir.glob("labels_res_*.npy"))
    return [float(f.stem.replace("labels_res_", "")) for f in files]


def audit_dir(mode_dir):
    hjson = mode_dir / "hierarchical_map_results.json"
    if not hjson.exists():
        return {"status": "missing_hierarchical_map_results", "mode": mode_dir.name}
    recorded = json.loads(hjson.read_text())
    res = load_resolutions(mode_dir, recorded)
    rec_mean = recorded.get("mean_nesting_score")
    corpus = recorded.get("corpus_size", recorded.get("n_decisions"))

    transitions = []
    honest_scores, coverage_scores = [], []
    cluster_counts, n_labeled = {}, {}
    labels_ok = True
    for r in res:
        lp = mode_dir / f"labels_res_{r}.npy"
        if not lp.exists():
            labels_ok = False
            break
        a = np.load(lp)
        n_labeled[f"res_{r}"] = int((a != -1).sum())
        cluster_counts[f"res_{r}"] = int(len(np.unique(a[a != -1])))
    if not labels_ok:
        return {"status": "missing_label_arrays", "mode": mode_dir.name}

    for i in range(len(res) - 1):
        coarser = np.load(mode_dir / f"labels_res_{res[i]}.npy")
        finer = np.load(mode_dir / f"labels_res_{res[i + 1]}.npy")
        strict = strict_nesting_transition(coarser, finer)
        coverage = majority_coverage_transition(coarser, finer)
        transitions.append({
            "coarser_resolution": res[i],
            "finer_resolution": res[i + 1],
            **strict,
            **coverage,
        })
        honest_scores.append(strict["nesting_score"])
        coverage_scores.append(coverage["majority_coverage"])

    honest_mean = float(np.mean(honest_scores)) if honest_scores else None
    coverage_mean = float(np.mean(coverage_scores)) if coverage_scores else None
    return {
        "status": "audited",
        "mode": mode_dir.name,
        "corpus_size": corpus,
        "n_labeled_per_resolution": n_labeled,
        "cluster_counts": cluster_counts,
        "resolutions": res,
        "recorded_mean_nesting_score": rec_mean,
        "honest_mean_strict_nesting": honest_mean,
        "legacy_mean_majority_coverage": coverage_mean,
        "recorded_minus_honest": (
            None if rec_mean is None or honest_mean is None else round(rec_mean - honest_mean, 6)),
        "transitions": transitions,
    }


def main():
    out = {
        "audit_run": AUDIT_RUN,
        "direction_version": 25,
        "produced_by": "fractal_map/hierarchical/compute_honest_nesting_audit.py",
        "timestamp": "2026-09-24T00:00:00Z",
        "defect": {
            "id": "NESTING_METRIC_DEFECT_v1",
            "summary": (
                "Parameterized compressed builders recorded mean_nesting_score as mean of "
                "'nesting_consistency' = fraction of fine clusters with a valid MAJORITY parent "
                "label. For independent Leiden partitions this is ~1.0 by construction and is "
                "not nestedness. Honest definition (hierarchical_leiden.compute_nesting_score): "
                "a fine cluster is nested iff all its non--1 members share ONE unique coarse "
                "parent label."
            ),
            "affected_builders": [
                "fractal_map/hierarchical/build_parameterized_legal_distance_map_compressed.py",
                "fractal_map/hierarchical/build_parameterized_legal_distance_map.py",
                "fractal_map/hierarchical/build_21k_hierarchical_map.py",
                "fractal_map/hierarchical/build_174k_hierarchical_map_chamber.py",
                "fractal_map/hierarchical/complete_v6_hierarchical_artifacts.py",
            ],
            "honest_reference_implementations": [
                "fractal_map/hierarchical/hierarchical_leiden.py::compute_nesting_score",
                "fractal_map/hierarchical/hierarchical_map_builder.py::compute_hierarchy_nesting_score",
                "fractal_map/hierarchical/run_center_projected_hierarchical.py::compute_hierarchy_nesting_score",
            ],
            "routing_tables_unaffected": (
                "zoom_mappings.json child_to_parent/parent_to_children remain valid navigation "
                "data (majority-parent routing); only the METRIC NAME over-claimed nesting."
            ),
        },
        "modes": {},
        "reference_dirs": {},
        "summary": {},
    }

    n_audited = 0
    n_recorded_overclaim = 0
    for root in MODE_ROOTS:
        if not root.exists():
            continue
        for mode_dir in sorted(root.iterdir()):
            if not mode_dir.is_dir():
                continue
            rec = audit_dir(mode_dir)
            out["modes"][mode_dir.name] = rec
            if rec["status"] == "audited":
                n_audited += 1
                if (rec["recorded_mean_nesting_score"] is not None
                        and rec["honest_mean_strict_nesting"] is not None
                        and rec["recorded_mean_nesting_score"] - rec["honest_mean_strict_nesting"] > 1e-9):
                    n_recorded_overclaim += 1
            elif rec["status"] == "missing_hierarchical_map_results":
                out["modes"][mode_dir.name] = {"status": "missing_hierarchical_map_results"}

    for ref in REFERENCE_DIRS:
        if ref.exists():
            out["reference_dirs"][ref.name] = audit_dir(ref)

    out["summary"] = {
        "n_modes_audited": n_audited,
        "n_modes_recorded_nesting_overclaim": n_recorded_overclaim,
        "mode_roots": [str(r.relative_to(RESULTS)) for r in MODE_ROOTS],
        "note": (
            "For independent-Leiden multi-resolution ladders, strict nesting is NOT guaranteed by "
            "construction; zoom navigation uses majority-parent routing (child_to_parent). "
            "Strict nesting >= 0.99 signals a clean zoom transition; low values at coarse "
            "resolutions reflect boundary decisions split across coarse parents."
        ),
    }

    out_path = RESULTS / "evaluation" / f"resume_{AUDIT_RUN}_nesting_audit.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {out_path}")
    print(json.dumps(out["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())