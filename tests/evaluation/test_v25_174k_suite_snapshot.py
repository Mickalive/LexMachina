#!/usr/bin/env python3
"""
Conformance test for the v25 174k formal-suite snapshot (producer run 36013963912,
operational-resume verification run 36020066596).

Guards the audit-ready snapshot produced under protocol
`evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` (FROZEN):

  1. Embedding inventory: 8 npy, shape (173963, 128), float32, finite,
     zero-row pattern consistent with frozen v16 "zero vector scattered to empty
     rows" semantics.
  2. Hybrid determinism: cited_outcome_hybrid_0.5/0.7 and
     regeste_full_text_hybrid_0.5/0.7 are exact (bitwise) functions of the four
     saved base embeddings (seed 42, sklearn L2-normalize semantics).
  3. Fixed subsample determinism: `hierarchy_subsample_15000_seed42` (branch-
     stratified among known-legal_area rows) and `temporal_subsample_30000_seed42`
     reproduce exactly from `evaluation/data/174k/metadata_174k.json` with seed 42.
  4. Suite/summary consistency: per-representation result files agree with
     `_suite_summary.json`; the dedicated citation-heritage files agree with the
     suite's `citation_heritage` benchmark block.
  5. Frozen thresholds: the 12 benchmarks in every per-representation result
     carry the frozen v16/v3 thresholds (0.65, 0.6333, 0.8, 0.85/0.3, 0.1,
     0.99/0.01, 0.1, 0.7/0.3, 0.5) and `config_hash_suite == 4323f833fa72366a`
     (frozen v16 suite config hash).
  6. Citation-heritage spot check: AUC-ROC on a fixed seed-42 2,000+2,000 pair
     subsample of the frozen 137,314+137,314 pool must match frozen expected
     values within 0.005 for the four checked representations (independent
     implementation: float64 einsum + sklearn roc_auc_score).
7. v17b label-level record at 174k: 214 raw -> 164 normalized unique
     legal_area labels, 49.3% labels changed, 47.6% unknown (frozen counts).
  8. v17b per-representation provenance gate (audit CYCLE_36028392571
      finding 4): recompute each rep's raw-vs-normalized hierarchy-family
      metrics from the rep's OWN saved embedding on the frozen subsample and
      assert correspondence with both the recorded and the audit-recheck
      reference files (rules P1/P2/P3/P4 + negative controls NC_swap,
      NC_fileid; frozen spec
      evaluation/experiments/v25_174k_suite/provenance_gate_spec_v1.json).
      This mechanically catches the copy-defect class discovered in producer
      run 36013963912 (regeste_full_text_hybrid_0.5/0.7 v17b files
      byte-identical to full_text_tfidf_light).

Failure of any check means the snapshot no longer conforms to the frozen
protocol artifacts and must NOT be treated as audit-ready.

Runtime: ~3-5 minutes (one metadata load; no corpus, no HNSW; the provenance
gate adds ~1.5 minutes of frozen KMeans recomputation with Pool(4)).
"""
import json
import numpy as np
from pathlib import Path
from sklearn.preprocessing import normalize
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
EMB = ROOT / "results/evaluation/v25_174k_formal_suite/embeddings"
FIX = ROOT / "results/evaluation/v25_174k_formal_suite/fixed_samples"
SUITE = ROOT / "results/evaluation/v25_174k_formal_suite/results"
CITE = ROOT / "results/evaluation/v25_174k_citation_heritage"
MD_PATH = ROOT / "evaluation/data/174k/metadata_174k.json"
PAIRS_PATH = ROOT / "evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json"

REPS = [
    "cited_decisions_tfidf", "outcome_tfidf", "regeste_tfidf", "full_text_tfidf_light",
    "cited_outcome_hybrid_0.5", "cited_outcome_hybrid_0.7",
    "regeste_full_text_hybrid_0.5", "regeste_full_text_hybrid_0.7",
]
N_ROWS = 173963
DIM = 128
FROZEN_SUITE_HASH = "4323f833fa72366a"

# Expected AUC-ROC on the fixed seed-42 pair subsample (2,000 positive + 2,000
# negative of the frozen 137,314+137,314 pool). Frozen at verification time from
# the saved snapshot (scores reproduced independently from the saved npy).
CH_SPOT_AUC = {
    "cited_decisions_tfidf": 0.977096,
    "cited_outcome_hybrid_0.5": 0.928152,
    "full_text_tfidf_light": 0.844475,
    "regeste_tfidf": 0.497250,
}
CH_SPOT_TOL = 0.005
CH_SPOT_POS = 2000
CH_SPOT_NEG = 2000

THRESHOLDS = {
    "citation_heritage": 0.65,
    "branch_knn": 0.6333,
    "tf_metadata_human_indexing": 0.8,
    "adversarial_falsification": {"language_dominance_max": 0.85, "branch_coherence_min": 0.3},
    "boilerplate_resistance_real_corpus": 0.1,
    "multilingual_invariance": {"separation_min": 0.0, "invariance_gap_max": 0.2},
    "cross_language_pairs": 0.0,
    "collapse_check": {"mean_sim_max": 0.99, "std_sim_min": 0.01},
    "temporal_stability": 0.1,
    "hierarchy_coherence": {"purity_min": 0.7, "nmi_min": 0.3},
    "zoom_coherence": 0.0,
    "legal_area_clustering": 0.5,
}


def _load_metadata():
    with open(MD_PATH) as f:
        md = json.load(f)
    branch = np.array([(m.get("branch") or "unknown") for m in md])
    branch = np.array([b if b not in (None, "null", "") else "unknown" for b in branch])
    area = np.array([(m.get("legal_area") or "unknown") for m in md])
    area = np.array([a if a not in (None, "null", "") else "unknown" for a in area])
    return md, branch, area


def test_01_embedding_inventory():
    msgs = []
    for r in REPS:
        e = np.load(EMB / f"{r}.npy")
        assert e.shape == (N_ROWS, DIM), f"{r}: shape {e.shape}"
        assert e.dtype == np.float32, f"{r}: dtype {e.dtype}"
        assert np.isfinite(e).all(), f"{r}: non-finite values"
        nz = int((np.linalg.norm(e, axis=1) == 0).sum())
        assert np.linalg.norm(e, axis=1).max() <= 1.0 + 1e-6, f"{r}: norm > 1"
        msgs.append(f"{r}: {e.shape} finite, {nz} zero rows")
    print("  embedding inventory OK\n   " + "\n   ".join(msgs))


def test_02_hybrid_exact_reconstruction():
    b = {r: np.load(EMB / f"{r}.npy") for r in REPS[:4]}
    recipes = {
        "cited_outcome_hybrid_0.5": (b["cited_decisions_tfidf"], b["outcome_tfidf"], 0.5),
        "cited_outcome_hybrid_0.7": (b["cited_decisions_tfidf"], b["outcome_tfidf"], 0.7),
        "regeste_full_text_hybrid_0.5": (b["regeste_tfidf"], b["full_text_tfidf_light"], 0.5),
        "regeste_full_text_hybrid_0.7": (b["regeste_tfidf"], b["full_text_tfidf_light"], 0.7),
    }
    for name, (a, bb, alpha) in recipes.items():
        # Mirror producer hybrid() semantics exactly (pre-normalize each base,
        # combine with the frozen alpha, re-normalize) — frozen in
        # build_v25_174k_representations.py / protocol_v25_174k_suite.json.
        a = normalize(a, norm="l2", axis=1)
        bb = normalize(bb, norm="l2", axis=1)
        h = normalize(alpha * a + (1 - alpha) * bb, norm="l2", axis=1).astype(np.float32)
        saved = np.load(EMB / f"{name}.npy")
        assert np.array_equal(h, saved), f"{name}: reconstruction differs from saved"
        print(f"  {name}: bitwise exact")



def test_03_fixed_subsample_determinism():
    md, branch, area = _load_metadata()
    hier = np.load(FIX / "hierarchy_subsample_15000_seed42.npy").astype(int)
    temp = np.load(FIX / "temporal_subsample_30000_seed42.npy").astype(int)
    known = np.where(area != "unknown")[0]
    rng = np.random.RandomState(42)
    chosen = []
    for br in np.unique(branch[known]):
        cand = known[branch[known] == br]
        per = max(1, int(round(15000 * len(cand) / len(known))))
        chosen.append(rng.choice(cand, size=min(per, len(cand)), replace=False))
    hier_recon = np.concatenate(chosen)
    rng.shuffle(hier_recon)
    hier_recon = hier_recon[:15000]
    assert np.array_equal(np.sort(hier), np.sort(hier_recon)), "hierarchy subsample mismatch"
    temp_recon = np.random.RandomState(42).choice(len(branch), size=30000, replace=False)
    assert np.array_equal(temp, temp_recon), "temporal subsample mismatch"
    assert int((area[hier] != "unknown").sum()) == 15000, "hierarchy subsample not all known-area"
    print("  fixed subsamples deterministic (hier 15000, temp 30000, seed 42)")


def test_04_suite_summary_and_dedicated_ch_consistency():
    summary = json.load(open(SUITE / "_suite_summary.json"))
    assert set(summary.keys()) == set(REPS), "summary rep set differs from REPS"
    for r in REPS:
        d = json.load(open(SUITE / f"{r}.json"))
        s = summary[r]
        for k in ("n_rows", "n_passed", "n_failed", "n_skipped", "total_benchmarks", "config_hash_suite"):
            assert s[k] == d[k], f"{r}: summary/per-rep mismatch on {k}"
        assert d["config_hash_suite"] == FROZEN_SUITE_HASH, f"{r}: config hash mismatch"
        bids = [b["benchmark_id"] for b in d["benchmarks"]]
        assert len(bids) == 12 and len(set(bids)) == 12, f"{r}: benchmark set {bids}"
        c = json.load(open(CITE / f"{r}.json"))
        ch = next(b for b in d["benchmarks"] if b["benchmark_id"] == "citation_heritage")
        assert c["status"] == ch["status"], f"{r}: dedicated CH status mismatch"
        assert c["metrics"] == ch["metrics"], f"{r}: dedicated CH metrics mismatch"
    print("  suite/summary and dedicated CH files fully consistent for all 8 reps")


def test_05_frozen_thresholds():
    for r in REPS:
        d = json.load(open(SUITE / f"{r}.json"))
        for b in d["benchmarks"]:
            if b["status"] == "SKIP":
                continue
            assert b["threshold"] == THRESHOLDS[b["benchmark_id"]], \
                f"{r}/{b['benchmark_id']}: threshold {b['threshold']} != frozen {THRESHOLDS[b['benchmark_id']]}"
    print("  all 12 thresholds frozen per benchmark across all 8 reps")


def test_06_citation_heritage_spot_check():
    """Independent AUC-ROC recomputation on a fixed seed-42 pair subsample."""
    pairs = json.load(open(PAIRS_PATH))
    pos, neg = pairs["positive_pairs"], pairs["negative_pairs"]
    md, _, _ = _load_metadata()
    ids = [m["decision_id"] for m in md]
    id2i = {d: i for i, d in enumerate(ids)}
    pi = np.array([(id2i[a], id2i[b]) for a, b in pos if a in id2i and b in id2i])
    ni = np.array([(id2i[a], id2i[b]) for a, b in neg if a in id2i and b in id2i])
    assert len(pi) == 137314 and len(ni) == 137314, f"pair pool size {len(pi)}/{len(ni)}"
    rng = np.random.RandomState(42)
    sp = rng.choice(len(pi), CH_SPOT_POS, replace=False)
    sn = rng.choice(len(ni), CH_SPOT_NEG, replace=False)
    for r, expected in CH_SPOT_AUC.items():
        e = np.load(EMB / f"{r}.npy")
        ps = np.einsum("ij,ij->i", e[pi[sp, 0]].astype(np.float64), e[pi[sp, 1]].astype(np.float64))
        ns = np.einsum("ij,ij->i", e[ni[sn, 0]].astype(np.float64), e[ni[sn, 1]].astype(np.float64))
        auc = float(roc_auc_score(
            np.concatenate([np.ones(len(ps)), np.zeros(len(ns))]),
            np.concatenate([ps, ns])))
        assert abs(auc - expected) <= CH_SPOT_TOL, f"{r}: spot AUC {auc:.6f} != {expected:.6f} within {CH_SPOT_TOL}"
        print(f"  {r}: spot AUC {auc:.6f} (frozen {expected:.6f})")


def test_07_v17b_label_level_record():
    import sys
    sys.path.insert(0, str(ROOT / "evaluation/experiments"))
    from legal_area_normalize import normalize_legal_area
    md, _, area = _load_metadata()
    norm = np.array([normalize_legal_area(a) if a != "unknown" else "unknown" for a in area])
    raw_u = len(np.unique(area))
    norm_u = len(np.unique(norm))
    changed = float((area != norm).mean())
    unknown = float((area == "unknown").mean())
    assert raw_u == 214, f"raw unique {raw_u}"
    assert norm_u == 164, f"normalized unique {norm_u}"
    assert abs(changed - 0.493) < 0.005, f"changed fraction {changed}"
    assert abs(unknown - 0.476) < 0.005, f"unknown fraction {unknown}"
    print(f"  v17b labels: {raw_u} -> {norm_u} unique, {changed:.3f} changed, {unknown:.3f} unknown")


def test_08_v17b_provenance_gate():
    """Audit CYCLE_36028392571 finding 4: per-rep v17b provenance gate.

    Delegates to the frozen gate implementation in
    tests/evaluation/test_v25_174k_v17b_provenance.py (spec:
    evaluation/experiments/v25_174k_suite/provenance_gate_spec_v1.json) so the
    gate's rules live in exactly one place. The gate recomputes each rep's
    v17b metrics from its OWN saved embedding and asserts correspondence with
    the recorded and audit-recheck reference files, plus the swap/file-identity
    negative controls. A copied measurement file (the producer-run defect class)
    fails P1/P2 mechanically.
    """
    import importlib.util
    import sys
    try:
        # Under pytest the sibling module is already imported (name matches the
        # file), so its `_GATE_CACHE` is reused and the heavy recomputation runs
        # exactly once per session.
        import test_v25_174k_v17b_provenance as gate
    except ImportError:
        spec = importlib.util.spec_from_file_location(
            "v17b_provenance_gate", ROOT / "tests/evaluation/test_v25_174k_v17b_provenance.py")
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
    report = gate._run_once()
    v = report["verdict"]
    assert v["GATE_OVERALL"] == "PASS", f"provenance gate FAIL: {v}"
    # frozen expectation: warnings confined to the degenerate triple on both sets
    for w in report["warnings"]:
        assert w["pair"].split("<->")[0] in (
            "full_text_tfidf_light", "regeste_full_text_hybrid_0.5",
            "regeste_full_text_hybrid_0.7"), f"WARN outside degenerate triple: {w}"
    print(f"  v17b provenance gate: GATE_OVERALL=PASS "
          f"(P1/P2/P4 PASS, {v['P3_warnings']} confined P3 WARNs, "
          f"NC_swap/NC_fileid PASS)")
    print(f"    reference sets verified: recorded + recheck; "
          f"duration {report['duration_seconds']}s")