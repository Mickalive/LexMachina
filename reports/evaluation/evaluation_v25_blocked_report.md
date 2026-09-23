# Evaluation Lane — v25 Cycle Report

**Factory Direction Version:** 25  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** ACCEPTED  
**Date:** 2026-09-23  
**GitHub Run:** 35925286709  

---

## Executive Summary

The evaluation lane has **completed all readiness validations** for 174k-scale execution but is **BLOCKED** on upstream delivery of 174k representations from the legal-distance lane. No additional same-question cycle is justified until legal-distance computes and promotes 174k production representations to accepted state.

### What Was Validated (READY ✅)

| Component | Status | Details |
|-----------|--------|---------|
| **Frozen Harness v3** | REPRODUCED | Config hash `a31c443a9b0e992e`, seed=42, all adversarial thresholds unchanged |
| **12-Benchmark Suite** | VALIDATED | All 12 benchmarks implemented with frozen thresholds (config hash `4323f833fa72366a`) |
| **Full Corpus Harness (HNSW)** | VALIDATED | Exact match with frozen harness at 1200 scale; HNSW params M=16, ef_construction=200, ef_search=100 |
| **Citation Heritage Infrastructure** | READY | 804 positive pairs at 174k (95.9% resolution: 2,019/2,105) |
| **v17b Label Normalization** | CONFIRMED AT LABEL LEVEL | 214→164 unique labels (23% reduction), 32 cross-lingual canonical concepts, uniform 15-25% purity improvement across 6 representations |

### What Is Blocked (DEPENDENCIES ❌)

| Dependency | Owner | Status | Required For |
|------------|-------|--------|--------------|
| 174k year-split JSONL artifacts in accepted state | Corpus lane (via legal-distance reproduction) | NOT IN ACCEPTED STATE | All 174k computation |
| 174k TF-IDF signals (cited_decisions_tfidf, outcome_tfidf, cited_outcome_hybrid_0.5/0.7) | Legal-distance lane | NOT COMPUTED | CPU-cheap baseline representations |
| 174k dense embeddings (center_projected_64, legal embeddings) | Legal-distance lane | NOT COMPUTED | Production default & linear combinations |
| Jurist human study (5-10 Swiss jurists) | Repository owner | EXTERNALLY BLOCKED | Human preference validation |

---

## Detailed Findings

### 1. Citation Heritage Benchmark at 174k

**Infrastructure:** ✅ READY — 804 positive citation pairs (min 10 required → 80x margin), 1,608 negative pairs, frozen AUC threshold ≥ 0.65.

**Execution (cycle branch):** FAIL on `cited_outcome_hybrid_0.5_174k` — AUC=0.482, pos_mean_sim=0.054, neg_mean_sim=0.108, nn_citation_rate=0.0. **TF-IDF hybrid does not recover citation proximity at 174k scale.** Dense embeddings required.

**Note:** This execution used embeddings from a cycle branch (not in accepted state). Re-execution required when legal-distance delivers accepted 174k embeddings.

### 2. v17b Label Normalization at 174k

**Label Analysis (173,963 decisions):**
- Raw unique labels: 214 → Normalized: 164 (**−23.4%**)
- Labels changed: 85,819 (**49.3%**)
- Cross-lingual canonical concepts: 32 (e.g., `Strafprozess/Procédure pénale/Procedura penale` → `criminal_procedure`)
- Language distribution: de=106,501 (61.2%), fr=57,489 (33.0%), it=9,973 (5.7%)

**Uniformity Confirmation (1200 slice, 6 representations, 4 seeds):**
| Representation | Hierarchy Purity | Zoom Fine Purity | Legal Area Purity |
|----------------|------------------|------------------|-------------------|
| center_projected_64dim | +20.2% | +22.3% | +14.8% |
| cited_outcome_hybrid_0.5 | +21.5% | +20.4% | +15.1% |
| linear_citation_concat | +18.9% | +19.4% | +12.7% |
| **linear_hybrid05_concat** | **+24.0%** | **+27.7%** | +15.3% |
| linear_citation_w3070 | +15.6% | +17.9% | +13.0% |
| linear_citation_ridge | +19.4% | +21.5% | +15.2% |

**Conclusion:** The v16 hierarchy-family FAIL was a **shared cross-lingual label artifact**, not a representation limitation. Production default `linear_hybrid05_concat` shows largest improvement. **Clustering test at 174k pending 174k embeddings.**

### 3. v16 Full Benchmark Suite (1200 slice, frozen harness v3)

**6 Universal PASS:** branch_knn, adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, temporal_stability

**4 Universal FAIL:** boilerplate_resistance_real_corpus, hierarchy_coherence, zoom_coherence, legal_area_clustering

**1 Conditional PASS:** tf_metadata_human_indexing

**1 SKIPPED (now unblocked at 174k):** citation_heritage — insufficient positive pairs at 1200, now 804 pairs at 174k

**Best on 1200 slice:** `linear_hybrid05_concat` (7/12 pass, lowest variance), `linear_citation_concat` (7/12 pass)

### 4. Full Corpus Harness Validation

- **Exact reproducibility** confirmed at 1200 scale: HNSW results match frozen harness v3 exactly
- **HNSW parameters:** M=16, ef_construction=200, ef_search=100, exact_nn_threshold=10,000, batch_size=5,000
- **Production default at 174k (cycle branch):** `cited_outcome_hybrid_0.5_174k` — PASS both adversarial gates (LangDom=0.589 < 0.85, JuristPref=0.742 > 0.5)
- **Ready for 174k:** Infrastructure scales; awaiting embeddings

---

## Blocking Dependencies Analysis

### Legal-Distance Lane Must Deliver

Per Factory Direction v25, legal-distance lane question:
> "Execute 174k-scale evaluation autonomously with CPU-feasible staged computation on the REPRODUCED corpus artifacts: (1) regenerate year-split artifacts via the proven reproduction path and compute production representations at 174k, starting with CPU-cheap TF-IDF/citation/outcome signals... (2) dense-embedding modes computed year-split with resumable checkpoints within 65-min job ceilings"

**Required steps (legal-distance responsibility):**
1. Run `corpus/acquisition/reproduce_full_corpus.py` → generates `bger_YYYY.jsonl` year-split files (~100s, 174,113 decisions)
2. Compute TF-IDF signals year-split: cited_decisions_tfidf (128-dim), outcome_tfidf (2-dim), cited_outcome_hybrid_0.5/0.7 (64-dim)
3. Compute dense embeddings year-split: center_projected_64, legal embeddings (resumable within 65-min CI ceilings)
4. Promote to accepted state (/tmp/lex_accepted/legal-distance/...)

### Evaluation Lane Cannot Proceed Without

The evaluation lane's v25 question explicitly states: **"as representations land"**. No representations have landed in accepted state. The evaluation infrastructure is a **consumer** of legal-distance outputs, not a producer.

---

## Recommendation: BLOCKED_ON_DEPENDENCIES

### For Factory Director

1. **Do not re-dispatch evaluation lane** until legal-distance delivers 174k representations to accepted state
2. **Coordinate legal-distance execution** of the staged 174k computation plan (year-split reproduction → TF-IDF signals → dense embeddings)
3. **When 174k representations land**, evaluation lane will execute in one cycle:
   - Full 12-benchmark suite on ALL production representations (frozen harness v3 thresholds)
   - Citation heritage benchmark (804 positive pairs, AUC ≥ 0.65)
   - v17b label normalization clustering test (hierarchy/zoom/legal_area purity)
4. **Jurist human study** remains externally blocked — framework ready, needs owner recruitment

### Evidence Preservation

All negative results preserved as first-class evidence:
- Citation heritage FAIL on TF-IDF hybrid at 174k (AUC=0.482) — dense embeddings required
- Hierarchy family universal FAIL at 1200 — resolved as label artifact by v17b normalization
- Boilerplate resistance universal FAIL — systemic cross-lingual alignment challenge, not procedural boilerplate

---

## Evidence References

- `evaluation/evaluation_v3_harness.py` — Frozen adversarial harness
- `evaluation/scalable_nn.py` — HNSW scalable NN infrastructure
- `evaluation/run_full_corpus_evaluation.py` — Full corpus evaluation entry point
- `evaluation/experiments/run_v16_full_benchmark_suite.py` — 12-benchmark suite
- `evaluation/experiments/run_v17b_label_normalization_all_reps.py` — v17b uniformity test
- `evaluation/experiments/legal_area_normalize.py` — Cross-lingual label normalization
- `results/evaluation/v16_full_benchmark_suite/v16_full_benchmark_results.json`
- `results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_results.json`
- `evaluation/results/v3/evaluation_v3_results.json`
- `/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/citation_graph_resolved.json`
- `/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy`
- `reports/evaluation/EVALUATION_174K_READINESS_REPORT_20260923.md`
- `evaluation/results/full_corpus_174k_tfidf/full_corpus_evaluation_results_worker0.json`
- `results/evaluation/citation_heritage_174k.json`

---

## Frozen Configuration (Audit Trail)

```json
{
  "evaluation_version": "v3_full_corpus",
  "factory_direction_version": 25,
  "global_seed": 42,
  "config_hash": "4323f833fa72366a",
  "thresholds": {
    "language_dominance": 0.85,
    "jurist_pairwise": 0.5,
    "cross_lang_recall": 0.2,
    "cluster_coherence": 0.7,
    "citation_heritage_auc": 0.65
  },
  "parameters": {
    "k_lang_dom": 20,
    "k_jurist": 10,
    "k_cross_lang": 10,
    "n_clusters": 16
  },
  "hnsw": {
    "M": 16,
    "ef_construction": 200,
    "ef_search": 100
  }
}
```

---

*Report generated by Evaluation Lane — LexMachina Factory*  
*Lane state updated: `state/evaluation.json` with `cycle_status: BLOCKED_ON_DEPENDENCIES`, `continue_recommended: false`*