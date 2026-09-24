#!/usr/bin/env python3
"""
v25 174k v17b provenance gate (audit CYCLE_36028392571 finding 4).

Guards the v17b label-normalization measurements against the copy-defect class
discovered in producer run 36013963912 (regeste_full_text_hybrid_0.5/0.7 v17b
files byte-identical to full_text_tfidf_light). Frozen spec:
evaluation/experiments/v25_174k_suite/provenance_gate_spec_v1.json.

Rules (frozen):
  P1  own-embedding correspondence        HARD FAIL, |delta| <= 0.02 per metric
  P2  file-identity => on-sample emb id   HARD FAIL, max_abs_diff <= 1e-4
  P3  degeneracy probe on regeste-active  WARN only, probe diff > 1e-3
  P4  status consistency                  HARD FAIL

Negative controls (frozen):
  NC_swap       swap-corruption matrix over non-identical file pairs: P1 must FAIL
  NC_fileid     crafted identical file over different embeddings: P2 must FAIL

Run:  PYTHONPATH=. python tests/evaluation/test_v25_174k_v17b_provenance.py
Also runnable under pytest (test_* functions).
Output: results/evaluation/v25_174k_provenance_gate_36035803010/gate_results.json
"""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluation/experiments/v25_174k_suite"))
sys.path.insert(0, str(ROOT / "evaluation/experiments"))

OUT = ROOT / "results/evaluation/v25_174k_provenance_gate_36035803010"
EMB = ROOT / "results/evaluation/v25_174k_formal_suite/embeddings"
FIX = ROOT / "results/evaluation/v25_174k_formal_suite/fixed_samples"
V17B_RECORDED = ROOT / "results/evaluation/v25_174k_v17b"
V17B_RECHECK = ROOT / "results/evaluation/v25_174k_audit_fixes_36028392571/v17b_recheck"

REPS = [
    "cited_decisions_tfidf", "outcome_tfidf", "regeste_tfidf", "full_text_tfidf_light",
    "cited_outcome_hybrid_0.5", "cited_outcome_hybrid_0.7",
    "regeste_full_text_hybrid_0.5", "regeste_full_text_hybrid_0.7",
]
P1_TOL = 0.02
P2_EMB_TOL = 1e-4
P3_PROBE_SIZE = 10000
P3_PROBE_SEED = 42
P3_DIFF_TOL = 1e-3

# Fields compared per metric group (14 numeric fields total, 7 raw + 7 normalized).
GROUP_FIELDS = {
    "hierarchy_coherence": ["best_purity", "best_nmi"],
    "zoom_coherence": ["coarse_purity", "fine_purity", "improvement_pct"],
    "legal_area_clustering": ["overall_purity", "nmi"],
}

DEGENERATE_TRIPLE = {
    "full_text_tfidf_light", "regeste_full_text_hybrid_0.5", "regeste_full_text_hybrid_0.7",
}


# ---------------------------------------------------------------- frozen imports
def _frozen():
    import run_v25_174k_suite as R
    return R


def extract_metric_vector(file_dict):
    """14-element vector (7 raw + 7 normalized) from a v17b file dict, plus statuses."""
    vals, statuses = [], []
    for group in ("raw", "normalized"):
        for bm_id, fields in GROUP_FIELDS.items():
            bm = file_dict[group][bm_id]
            statuses.append(bm["status"])
            for f in fields:
                vals.append(float(bm["metrics"][f]))
    return np.array(vals, dtype=np.float64), statuses


def recompute_rep(rep, hier_idx, area_raw, area_norm):
    """Frozen v17b recomputation of rep's saved embedding on the frozen subsample."""
    R = _frozen()
    emb = np.load(EMB / f"{rep}.npy", mmap_mode="r")
    sub_emb = np.asarray(emb[hier_idx])
    sub_raw = area_raw[hier_idx]
    sub_norm = area_norm[hier_idx]
    out = {"representation": rep, "sample": "hierarchy_subsample_15000_seed42 (fixed)"}
    for label, labels in (("raw", sub_raw), ("normalized", sub_norm)):
        out[label] = {
            "hierarchy_coherence": R.bm_hierarchy(sub_emb, labels),
            "zoom_coherence": R.bm_zoom(sub_emb, labels),
            "legal_area_clustering": R.bm_legal_area(sub_emb, labels),
        }
    # extract_metric_vector returns (14-vector, statuses); only the vector is
    # needed here (the worker's dict is the authoritative recomputed record).
    return rep, out, extract_metric_vector(out)[0]


# ---------------------------------------------------------------- gate
def run_gate():
    t0 = time.time()
    R = _frozen()
    _, _, _, area = R.load_metadata()
    hier_idx = np.load(FIX / "hierarchy_subsample_15000_seed42.npy").astype(int)
    area_raw = np.array([a if a not in (None, "null", "") else "unknown" for a in area])
    area_norm = R.normalize_labels(area_raw)

    # ---- per-rep recomputation (deterministic; parallelized)
    from multiprocessing import Pool
    with Pool(4) as pool:
        jobs = [(rep, hier_idx, area_raw, area_norm) for rep in REPS]
        recomputed = {rep: (out, vec) for rep, out, vec in pool.starmap(recompute_rep, jobs)}

    # ---- reference files
    refs = {"recorded": {}, "recheck": {}}
    for set_name, base in (("recorded", V17B_RECORDED), ("recheck", V17B_RECHECK)):
        for rep in REPS:
            d = json.load(open(base / f"{rep}.json"))
            vec, st = extract_metric_vector(d)
            refs[set_name][rep] = {"vector": vec, "statuses": st, "file": base / f"{rep}.json"}

    report = {
        "protocol_id": "eval_v25_v17b_provenance_gate_v1",
        "github_run": "36035803010",
        "rules_frozen": {
            "P1_tolerance": P1_TOL, "P2_embedding_tolerance": P2_EMB_TOL,
            "P3_probe_size": P3_PROBE_SIZE, "P3_probe_seed": P3_PROBE_SEED,
            "P3_probe_diff_tolerance": P3_DIFF_TOL,
        },
        "results": {}, "warnings": [], "controls": {}, "verdict": None,
    }

    # ---- P1 + P4
    p1, p4 = {}, {}
    for rep in REPS:
        vec, st = recomputed[rep][1], recomputed[rep][0]
        statuses = [st[group][bm]["status"] for group in ("raw", "normalized")
                    for bm in GROUP_FIELDS]
        p1[rep], p4[rep] = {}, {}
        for set_name in refs:
            d_max = float(np.max(np.abs(vec - refs[set_name][rep]["vector"])))
            p1[rep][set_name] = {"max_abs_delta": d_max, "pass": d_max <= P1_TOL}
            mism = [s for s, (a, b) in enumerate(zip(statuses, refs[set_name][rep]["statuses"]))
                    if a != b]
            p4[rep][set_name] = {"status_mismatches": mism, "pass": not mism}
    report["results"]["P1"] = p1
    report["results"]["P4"] = p4

    # ---- P2 + P3: identical-file groups per reference set
    p2, p3 = {}, {}
    for set_name in refs:
        vecs = {rep: refs[set_name][rep]["vector"] for rep in REPS}
        identical_pairs = []
        for i, a in enumerate(REPS):
            for b in REPS[i + 1:]:
                if np.array_equal(vecs[a], vecs[b]):
                    identical_pairs.append((a, b))
        p2[set_name] = {"identical_file_pairs": identical_pairs, "checks": {}, "pass": True}
        p3[set_name] = {"probe_warnings": []}
        for a, b in identical_pairs:
            ea = np.load(EMB / f"{a}.npy", mmap_mode="r")[hier_idx]
            eb = np.load(EMB / f"{b}.npy", mmap_mode="r")[hier_idx]
            on_sample_diff = float(np.max(np.abs(np.asarray(ea) - np.asarray(eb))))
            ok = on_sample_diff <= P2_EMB_TOL
            p2[set_name]["checks"][f"{a}<->{b}"] = {
                "max_abs_diff_on_sample": on_sample_diff, "pass": ok}
            p2[set_name]["pass"] = p2[set_name]["pass"] and ok
            # P3 probe: seed-42 subsample among regeste-active rows (base embedding non-zero)
            reg = np.load(EMB / "regeste_tfidf.npy", mmap_mode="r")
            active = np.where(np.linalg.norm(np.asarray(reg), axis=1) > 0)[0]
            rng = np.random.RandomState(P3_PROBE_SEED)
            probe = rng.choice(active, size=min(P3_PROBE_SIZE, len(active)), replace=False)
            pa = np.asarray(np.load(EMB / f"{a}.npy", mmap_mode="r")[probe])
            pb = np.asarray(np.load(EMB / f"{b}.npy", mmap_mode="r")[probe])
            probe_diff = float(np.max(np.abs(pa - pb)))
            if probe_diff > P3_DIFF_TOL:
                warn = {
                    "pair": f"{a}<->{b}", "reference_set": set_name,
                    "probe_max_abs_diff": probe_diff,
                    "note": "file equality not explained by probe embedding equality - "
                            "measurement provenance must be documented (degenerate-sample copy class)",
                }
                p3[set_name]["probe_warnings"].append(warn)
                report["warnings"].append(warn)
    report["results"]["P2"] = p2
    report["results"]["P3"] = p3

    # ---- NC_swap corruption matrix (recorded files only)
    nc_swap = {"unexpected_passes": [], "cells": {}}
    for victim in REPS:
        vvec, _ = extract_metric_vector(json.load(open(V17B_RECORDED / f"{victim}.json")))
        recomputed_victim_vec = recomputed[victim][1]
        for donor in REPS:
            if victim == donor:
                continue
            dvec, _ = extract_metric_vector(json.load(open(V17B_RECORDED / f"{donor}.json")))
            identical_files = bool(np.array_equal(vvec, dvec))
            # corrupted slot: donor's file content in victim's slot
            delta = float(np.max(np.abs(recomputed_victim_vec - dvec)))
            p1_fail = delta > P1_TOL
            in_triple = victim in DEGENERATE_TRIPLE and donor in DEGENERATE_TRIPLE
            expected = not in_triple  # non-degenerate swaps must FAIL P1
            cell = {"victim": victim, "donor": donor, "max_abs_delta": delta,
                    "p1_would_fail": p1_fail, "identical_files": identical_files,
                    "in_degenerate_triple": in_triple, "expected_fail": expected,
                    "unexpected_pass": (not p1_fail) and expected}
            nc_swap["cells"][f"{victim}<-{donor}"] = cell
            if cell["unexpected_pass"]:
                nc_swap["unexpected_passes"].append(cell)
    report["controls"]["NC_swap_corruption_matrix"] = nc_swap

    # ---- NC_fileid: crafted identical file over different on-sample embeddings
    nc_fid = {"unexpected_passes": []}
    for victim in REPS:
        vvec, _ = extract_metric_vector(json.load(open(V17B_RECORDED / f"{victim}.json")))
        for donor in REPS:
            if victim == donor:
                continue
            dvec, _ = extract_metric_vector(json.load(open(V17B_RECORDED / f"{donor}.json")))
            if np.array_equal(vvec, dvec):
                continue  # already identical; P2 handles
            ea = np.asarray(np.load(EMB / f"{victim}.npy", mmap_mode="r")[hier_idx])
            eb = np.asarray(np.load(EMB / f"{donor}.npy", mmap_mode="r")[hier_idx])
            diff = float(np.max(np.abs(ea - eb)))
            p2_fail_expected = diff > P2_EMB_TOL
            if not p2_fail_expected:
                nc_fid["unexpected_passes"].append(
                    {"victim": victim, "donor": donor, "max_abs_diff_on_sample": diff})
    report["controls"]["NC_file_identity_implies_embedding_identity"] = nc_fid

    # ---- verdict
    p1_pass = all(p1[r][s]["pass"] for r in REPS for s in refs)
    p4_pass = all(p4[r][s]["pass"] for r in REPS for s in refs)
    p2_pass = all(p2[s]["pass"] for s in refs)
    nc_ok = len(nc_swap["unexpected_passes"]) == 0 and len(nc_fid["unexpected_passes"]) == 0
    report["verdict"] = {
        "P1": "PASS" if p1_pass else "FAIL",
        "P2": "PASS" if p2_pass else "FAIL",
        "P4": "PASS" if p4_pass else "FAIL",
        "P3_warnings": len(report["warnings"]),
        "NC_swap": "PASS" if len(nc_swap["unexpected_passes"]) == 0 else "FAIL",
        "NC_fileid": "PASS" if len(nc_fid["unexpected_passes"]) == 0 else "FAIL",
        "GATE_OVERALL": "PASS" if (p1_pass and p2_pass and p4_pass and nc_ok) else "FAIL",
    }
    report["duration_seconds"] = round(time.time() - t0, 1)

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "gate_results.json", "w") as f:
        json.dump(report, f, indent=2)
    with open(OUT / "per_rep_recomputation.json", "w") as f:
        json.dump({rep: recomputed[rep][0] for rep in REPS}, f, indent=2)
    return report


# ---------------------------------------------------------------- pytest entry
_GATE_CACHE = {}


def _run_once():
    if "report" not in _GATE_CACHE:
        _GATE_CACHE["report"] = run_gate()
    return _GATE_CACHE["report"]


def test_P1_own_embedding_correspondence():
    rep = _run_once()
    assert rep["verdict"]["P1"] == "PASS", rep["results"]["P1"]


def test_P2_file_identity_implies_embedding_identity():
    rep = _run_once()
    assert rep["verdict"]["P2"] == "PASS", rep["results"]["P2"]


def test_P4_status_consistency():
    rep = _run_once()
    assert rep["verdict"]["P4"] == "PASS", rep["results"]["P4"]


def test_negative_controls():
    rep = _run_once()
    assert rep["verdict"]["NC_swap"] == "PASS", rep["controls"]["NC_swap_corruption_matrix"]
    assert rep["verdict"]["NC_fileid"] == "PASS", rep["controls"]["NC_file_identity_implies_embedding_identity"]


if __name__ == "__main__":
    rep = run_gate()
    print(json.dumps(rep["verdict"], indent=2))
    print(f"warnings: {len(rep['warnings'])}")
    for w in rep["warnings"]:
        print("  WARN", w["pair"], w["reference_set"], "probe_diff", w["probe_max_abs_diff"])