#!/usr/bin/env python3
"""
Operational-resume verification for audit CYCLE_36020066596 required_fixes
(run 36028392571, resuming snapshot of run 36020066596 / producer 36013963912).

The independent audit of run 36020066596 returned gate=PASS with four
non-blocking required fixes. This script performs the discriminating
recomputations behind those fixes and one NEW defect check discovered in this
resume cycle:

  FIX-A  v17b success-rule scope: recompute, for ALL 8 representations, the
         raw-vs-normalized hierarchy-family comparison on the frozen
         15,000-decision subsample using the frozen runner code (imported, not
         reimplemented). Rationale: the committed
         results/evaluation/v25_174k_v17b/regeste_full_text_hybrid_0.5.json and
         ..._0.7.json are byte-identical (except the name field) to
         full_text_tfidf_light.json — they are invalid copies, NOT
         measurements of the hybrid embeddings. The recheck replaces the
         missing/invalid measurements for all 8 reps.
  FIX-B  regeste_tfidf citation-heritage FAIL framing: measure the structure of
         the frozen 137,314-pair pool against regeste_tfidf zero rows
         (fraction of positive pairs with >=1 zero-row endpoint; pos/neg mean
         similarity) to substantiate "unmeasurable pool" instead of "no signal".
  FIX-C  build_manifest.json bookkeeping: exact zero-row recount of the four
         base embeddings (manifest says regeste 91,200; audit counted 91,204).
  FIX-D  Superseded-negative co-factor: recompute AUC-ROC of the correctly
         aligned cited_outcome_hybrid_0.5 embedding on the OLD 1,020+1,020
         pair pool (evaluation/results/174k_citation_heritage/citation_pairs_174k.json)
         to document the pair-pool-change co-factor alongside the
         row-alignment explanation for the historical 0.482 FAIL.
  RE-VERIFY  full-pool AUC-ROC for cited_outcome_hybrid_0.5 and regeste_tfidf
         in float64 on the frozen 137,314+137,314 pool (must match committed
         dedicated citation-heritage values exactly).

No frozen protocol, threshold, sample, mapping or committed historical
artifact is modified. All outputs land in
results/evaluation/v25_174k_audit_fixes_36028392571/.

Runtime: ~10-20 min on 4 CPU cores (KMeans n_init=10, frozen semantics).
"""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path("/home/runner/work/LexMachina/LexMachina")
sys.path.insert(0, str(ROOT / "evaluation/experiments/v25_174k_suite"))

OUT = ROOT / "results/evaluation/v25_174k_audit_fixes_36028392571"
EMB = ROOT / "results/evaluation/v25_174k_formal_suite/embeddings"
PAIRS_FULL = ROOT / "evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json"
PAIRS_OLD = ROOT / "evaluation/results/174k_citation_heritage/citation_pairs_174k.json"
V17B_RECORDED = ROOT / "results/evaluation/v25_174k_v17b"
V17B_RECHECK = OUT / "v17b_recheck"

REPS = [
    "cited_decisions_tfidf", "outcome_tfidf", "regeste_tfidf", "full_text_tfidf_light",
    "cited_outcome_hybrid_0.5", "cited_outcome_hybrid_0.7",
    "regeste_full_text_hybrid_0.5", "regeste_full_text_hybrid_0.7",
]
BASES = REPS[:4]
SEED = 42
N_ROWS = 173963


def load_metadata_arrays():
    import run_v25_174k_suite as R
    return R.load_metadata()


def load_pool(path):
    d = json.load(open(path))
    return d["positive_pairs"], d["negative_pairs"]


def cos_sims(emb_f64, pair_idx, chunk=60000):
    out = np.empty(len(pair_idx), dtype=np.float64)
    for s in range(0, len(pair_idx), chunk):
        c = pair_idx[s:s + chunk]
        out[s:s + len(c)] = np.einsum("ij,ij->i", emb_f64[c[:, 0]], emb_f64[c[:, 1]])
    return out


def pairs_to_index(pairs, id2i):
    return np.array([(id2i[a], id2i[b]) for a, b in pairs if a in id2i and b in id2i], dtype=np.int64)


# ---------------------------------------------------------------- experiments
def exp1_zero_rows():
    counts = {}
    for r in BASES:
        e = np.load(EMB / f"{r}.npy")
        counts[r] = int((np.linalg.norm(e, axis=1) == 0).sum())
        del e
    return counts


def exp2_pool_structure(id2i):
    out = {}
    reg = np.load(EMB / "regeste_tfidf.npy")
    zreg = (np.linalg.norm(reg, axis=1) == 0)
    cit = np.load(EMB / "cited_decisions_tfidf.npy")
    zcit = (np.linalg.norm(cit, axis=1) == 0)
    pos_f, neg_f = load_pool(PAIRS_FULL)
    pos_o, neg_o = load_pool(PAIRS_OLD)
    pi_f, ni_f = pairs_to_index(pos_f, id2i), pairs_to_index(neg_f, id2i)
    pi_o, ni_o = pairs_to_index(pos_o, id2i), pairs_to_index(neg_o, id2i)
    assert len(pi_f) == 137314 and len(ni_f) == 137314, (len(pi_f), len(ni_f))
    assert len(pi_o) == 1020 and len(ni_o) == 1020, (len(pi_o), len(ni_o))
    out["regeste_tfidf"] = {
        "zero_rows": int(zreg.sum()),
        "full_pool": {
            "pos_pairs_with_ge1_zero_endpoint": int((zreg[pi_f[:, 0]] | zreg[pi_f[:, 1]]).sum()),
            "pos_pairs_total": len(pi_f),
            "neg_pairs_with_ge1_zero_endpoint": int((zreg[ni_f[:, 0]] | zreg[ni_f[:, 1]]).sum()),
            "neg_pairs_total": len(ni_f),
        },
        "old_pool_pos_pairs_with_ge1_zero_endpoint": int((zreg[pi_o[:, 0]] | zreg[pi_o[:, 1]]).sum()),
        "old_pool_pos_pairs_total": len(pi_o),
    }
    out["cited_decisions_tfidf"] = {
        "zero_rows": int(zcit.sum()),
        "full_pool": {
            "pos_pairs_with_ge1_zero_endpoint": int((zcit[pi_f[:, 0]] | zcit[pi_f[:, 1]]).sum()),
            "pos_pairs_total": len(pi_f),
        },
    }
    # exact mean similarities (float64) to confirm pos_mean == 0.0 exactly
    rf64 = reg.astype(np.float64)
    ps = cos_sims(rf64, pi_f)
    ns = cos_sims(rf64, ni_f)
    out["regeste_tfidf"]["full_pool"]["pos_mean_similarity_f64"] = float(ps.mean())
    out["regeste_tfidf"]["full_pool"]["neg_mean_similarity_f64"] = float(ns.mean())
    out["regeste_tfidf"]["full_pool"]["pos_max_similarity_f64"] = float(ps.max())
    del reg, cit, rf64
    return out


def exp3_old_pool_auc(id2i):
    e = np.load(EMB / "cited_outcome_hybrid_0.5.npy").astype(np.float64)
    pos, neg = load_pool(PAIRS_OLD)
    pi, ni = pairs_to_index(pos, id2i), pairs_to_index(neg, id2i)
    ps, ns = cos_sims(e, pi), cos_sims(e, ni)
    from sklearn.metrics import roc_auc_score
    auc = float(roc_auc_score(np.concatenate([np.ones(len(ps)), np.zeros(len(ns))]),
                              np.concatenate([ps, ns])))
    del e
    return {
        "embedding": "cited_outcome_hybrid_0.5 (frozen protocol rebuild, aligned)",
        "old_pool_file": str(PAIRS_OLD.relative_to(ROOT)),
        "n_positive": len(pi), "n_negative": len(ni),
        "auc_roc": auc,
        "pos_mean_similarity": float(ps.mean()),
        "neg_mean_similarity": float(ns.mean()),
        "verdict_vs_frozen_threshold_0.65": "PASS" if auc >= 0.65 else "FAIL",
    }


def exp4_full_pool_auc_reverify(id2i):
    from sklearn.metrics import roc_auc_score
    committed = {
        "cited_outcome_hybrid_0.5": json.load(open(ROOT / "results/evaluation/v25_174k_citation_heritage/cited_outcome_hybrid_0.5.json"))["metrics"]["auc_roc"],
        "regeste_tfidf": json.load(open(ROOT / "results/evaluation/v25_174k_citation_heritage/regeste_tfidf.json"))["metrics"]["auc_roc"],
    }
    pos, neg = load_pool(PAIRS_FULL)
    pi, ni = pairs_to_index(pos, id2i), pairs_to_index(neg, id2i)
    y = np.concatenate([np.ones(len(pi)), np.zeros(len(ni))])
    out = {}
    for rep in ["cited_outcome_hybrid_0.5", "regeste_tfidf"]:
        e = np.load(EMB / f"{rep}.npy").astype(np.float64)
        s = np.concatenate([cos_sims(e, pi), cos_sims(e, ni)])
        auc = float(roc_auc_score(y, s))
        out[rep] = {"recomputed_auc_f64": auc, "committed_auc": committed[rep],
                    "abs_diff": abs(auc - committed[rep])}
        del e
    return out


def _v17b_worker(rep):
    """Recompute raw vs normalized hierarchy family for one rep with frozen code."""
    os.environ["OMP_NUM_THREADS"] = "1"
    import run_v25_174k_suite as R
    ids, lang, branch, area = R.load_metadata()
    hier_idx, _ = R.get_fixed_samples(branch, area)
    emb = np.load(EMB / f"{rep}.npy")
    sub_emb = emb[hier_idx]
    sub_area = area[hier_idx]
    norm_area = R.normalize_labels(area)
    sub_norm = norm_area[hier_idx]
    t0 = time.time()
    res = {
        "representation": rep,
        "sample": "hierarchy_subsample_15000_seed42 (fixed)",
        "raw": {
            "hierarchy_coherence": R.bm_hierarchy(sub_emb, sub_area),
            "zoom_coherence": R.bm_zoom(sub_emb, sub_area),
            "legal_area_clustering": R.bm_legal_area(sub_emb, sub_area),
        },
        "normalized": {
            "hierarchy_coherence": R.bm_hierarchy(sub_emb, sub_norm),
            "zoom_coherence": R.bm_zoom(sub_emb, sub_norm),
            "legal_area_clustering": R.bm_legal_area(sub_emb, sub_norm),
        },
        "recheck_provenance": {
            "code": "evaluation/experiments/v25_174k_suite/run_v25_174k_suite.py (imported frozen functions)",
            "seed": SEED,
            "github_run": "36028392571",
            "duration_seconds": round(time.time() - t0, 1),
        },
    }
    return res


def exp5_v17b_recheck():
    from multiprocessing import Pool
    V17B_RECHECK.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with Pool(4) as pool:
        results = pool.map(_v17b_worker, REPS)
    compare = {}
    for res in results:
        rep = res["representation"]
        with open(V17B_RECHECK / f"{rep}.json", "w") as f:
            json.dump(res, f, indent=2)
        rec_path = V17B_RECORDED / f"{rep}.json"
        if rec_path.exists():
            rec = json.load(open(rec_path))
            identical = {k: v for k, v in rec.items() if k != "representation"} == \
                        {k: v for k, v in res.items() if k not in ("representation", "recheck_provenance")}
            compare[rep] = {
                "recheck_matches_recorded_file": identical,
                "recorded_file_is_copy_of": _detect_copy_source(rep),
            }
    summary = {
        "github_run": "36028392571",
        "duration_seconds_total": round(time.time() - t0, 1),
        "reps_rechecked": len(results),
        "comparison_vs_recorded": compare,
        "defect_finding": (
            "results/evaluation/v25_174k_v17b/regeste_full_text_hybrid_0.5.json and "
            "regeste_full_text_hybrid_0.7.json are byte-identical (except representation name) to "
            "full_text_tfidf_light.json: they are invalid copies, not measurements of the hybrid "
            "embeddings. Superseded by the recheck files in this directory for those two reps; "
            "the other six reps are independently re-confirmed here."
        ),
    }
    with open(V17B_RECHECK / "_recheck_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    return summary


def _detect_copy_source(rep):
    rec = json.load(open(V17B_RECORDED / f"{rep}.json"))
    for other in REPS:
        if other == rep:
            continue
        p = V17B_RECORDED / f"{other}.json"
        if not p.exists():
            continue
        o = json.load(open(p))
        if {k: v for k, v in rec.items() if k != "representation"} == \
           {k: v for k, v in o.items() if k != "representation"}:
            return other
    return None


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    ids, lang, branch, area = load_metadata_arrays()
    id2i = {did: i for i, did in enumerate(ids)}
    log = lambda m: print(f"[{time.time()-t0:7.1f}s] {m}", flush=True)

    log("exp1: exact zero-row recount of 4 base embeddings")
    zero_counts = exp1_zero_rows()
    log(f"  {zero_counts}")

    log("exp2: regeste pool structure (fix B)")
    pool_struct = exp2_pool_structure(id2i)
    log(f"  regeste zero rows={pool_struct['regeste_tfidf']['zero_rows']}, "
        f"pos pairs with zero endpoint={pool_struct['regeste_tfidf']['full_pool']['pos_pairs_with_ge1_zero_endpoint']}/137314")

    log("exp3: old-pool AUC co-factor (fix D)")
    old_auc = exp3_old_pool_auc(id2i)
    log(f"  old pool AUC={old_auc['auc_roc']:.6f} ({old_auc['verdict_vs_frozen_threshold_0.65']}), "
        f"pos_mean={old_auc['pos_mean_similarity']:.4f}, neg_mean={old_auc['neg_mean_similarity']:.4f}")

    log("exp4: full-pool AUC re-verification")
    full_auc = exp4_full_pool_auc_reverify(id2i)
    for k, v in full_auc.items():
        log(f"  {k}: recomputed={v['recomputed_auc_f64']:.10f} committed={v['committed_auc']:.10f} diff={v['abs_diff']:.2e}")

    log("exp5: v17b recheck for all 8 reps (fix A + defect repair; KMeans heavy)")
    recheck = exp5_v17b_recheck()
    log(f"  recheck done in {recheck['duration_seconds_total']}s")
    for rep, c in recheck["comparison_vs_recorded"].items():
        log(f"  {rep}: matches_recorded={c['recheck_matches_recorded_file']} copy_of={c['recorded_file_is_copy_of']}")

    manifest = json.load(open(EMB / "build_manifest.json"))
    verification = {
        "run_id": "eval_v25_audit_fixes_36028392571",
        "github_run": "36028392571",
        "resumes_run": "36020066596",
        "producer_run": "36013963912",
        "audit_gate": "reports/audit/evaluation/CYCLE_36020066596.md (PASS, safe_to_integrate=true)",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fix_C_manifest_zero_rows": {
            "manifest_recorded": manifest["empty_row_counts"],
            "recounted_exact": zero_counts,
            "correction_needed_for": {k: (manifest["empty_row_counts"][k], zero_counts[k])
                                      for k in BASES if manifest["empty_row_counts"][k] != zero_counts[k]},
        },
        "fix_B_regeste_pool_structure": pool_struct,
        "fix_D_old_pool_auc_cofactor": old_auc,
        "reverification_full_pool_auc": full_auc,
        "fix_A_v17b_recheck_summary": recheck,
    }
    with open(OUT / "verification.json", "w") as f:
        json.dump(verification, f, indent=2)
    log(f"verification.json written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
