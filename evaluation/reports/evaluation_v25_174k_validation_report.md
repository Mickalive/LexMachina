# Evaluation Lane — v25 174k Infrastructure Validation Report

**Factory Direction Version:** 25  
**Cycle Status:** COMPLETED (Infrastructure Validated)  
**Evidence Tier:** REPRODUCED  
**Date:** 2026-09-24  
**GitHub Run:** 35941619286  

---

## Executive Summary

This cycle validates the complete evaluation infrastructure for 174k-scale execution. All components are **READY** and await 174k production representations from the legal-distance lane. The evaluation lane is correctly statused as **BLOCKED_ON_LEGAL_DISTANCE_174K_EMBEDDINGS**.

### Validation Results

| Component | Status | Details |
|-----------|--------|---------|
| Frozen Harness v3 Config | ✅ VALIDATED | Hash `4047da047fb339c1` matches frozen specification |
| Scalable NN (HNSW) | ✅ VALIDATED | Exact NN <10k, HNSW ≥10k, batch size 5000 |
| Full Corpus Evaluation Harness | ✅ VALIDATED | 1200-scale test matches frozen harness exactly |
| 12-Benchmark Suite | ✅ VALIDATED | All 12 benchmarks implemented, frozen config hash `4323f833fa72366a` |
| Citation Heritage (174k) | ✅ READY | 804 positive pairs, 1,608 negative pairs, AUC threshold 0.65 |
| v17b Label Normalization | ✅ VALIDATED | 213→163 labels (23.5% reduction), uniform improvement across 6 reps |
| Distributed Evaluation | ✅ READY | Worker sharding, partial result merging |

### Key Metrics (1200-scale Validation)

| Representation | Verdict | LangDom | Jurist Pref | Both Gates |
|---------------|---------|---------|-------------|------------|
| center_projected_64dim | **PASS** | 0.7664 ✓ | 0.5121 ✓ | ✅ |
| center_projected_128dim | FAIL | 0.7725 ✓ | 0.4954 ✗ | ❌ |
| center_projected (768) | FAIL | 0.7738 ✓ | 0.4912 ✗ | ❌ |
| embeddings_768 | FAIL | 0.9541 ✗ | 0.0951 ✗ | ❌ |

**Production default `center_projected_64dim` is the ONLY representation passing both adversarial gates.**

---

## Infrastructure Components Validated

### 1. Frozen Evaluation Harness v3
- **Config Hash:** `4047da047fb339c1` (matches v3 harness exactly)
- **Global Seed:** 42 (frozen)
- **Adversarial Thresholds:** LangDom < 0.85, Jurist > 0.5 (unchanged)
- **Benchmark Parameters:** k=20 (LangDom), k=10 (Jurist), k=10 (Cross-lang), n_clusters=16

### 2. Scalable Nearest Neighbor Infrastructure (`scalable_nn.py`)
- **Exact NN (sklearn):** For corpuses < 10,000 decisions
- **HNSW (hnswlib):** For corpuses ≥ 10,000 decisions
  - M=16, ef_construction=200, ef_search=100
  - Cosine similarity via inner product on normalized vectors
- **Batch Processing:** 5,000 decisions per batch for memory efficiency
- **Distributed Support:** `DistributedEvaluator` class for worker sharding

### 3. Full Corpus Evaluation Harness (`run_full_corpus_evaluation.py`)
- Drop-in compatible with frozen harness v3 `evaluate_representation()`
- Returns identical output format: adversarial, jurivoc_alignment, scale_stability, boilerplate_resistance, fractal
- Validated at 1200 scale: results match frozen harness exactly
- Config hash verification built-in

### 4. 12-Benchmark Formal Suite (`run_v16_full_benchmark_suite.py`)
- Frozen config hash: `4323f833fa72366a`
- All 14 benchmarks from specification.json implemented:
  1. citation_heritage (AUC-ROC ≥ 0.65)
  2. branch_knn (kNN@5 > 0.6333)
  3. tf_metadata_human_indexing (Recall@5 ≥ 0.8)
  4. adversarial_falsification (LangDom < 0.85 AND BranchCoh > 0.3)
  5. boilerplate_resistance_real_corpus (Correlation > 0.1)
  6. multilingual_invariance (Separation > 0 AND InvarianceGap < 0.2)
  7. cross_language_pairs (Separation > 0)
  8. collapse_check (MeanSim < 0.99 AND StdSim > 0.01)
  9. temporal_stability (Std < 0.1)
  10. hierarchy_coherence (Purity > 0.7 AND NMI > 0.3)
  11. zoom_coherence (Improvement > 0%)
  12. legal_area_clustering (Purity > 0.5)
  13. citation_proximity (shared≥1, same as citation_heritage)
  14. citation_graph_neighborhood (shared≥2)
- Validated at 1200 scale: matches cycle 14 results exactly

### 5. Citation Heritage Benchmark at 174k
**Files Generated:**
- `evaluation/results/174k_citation_heritage/citation_graph_174k.json` — Full citation graph
- `evaluation/results/174k_citation_heritage/citation_graph_174k_incoming.json` — Incoming citations
- `evaluation/results/174k_citation_heritage/citation_pairs_174k.json` — 804 positive pairs
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — Full pair list

**Statistics:**
- 91,183 decisions (52.4%) have `cited_decisions` field
- 818,054 total citation strings
- 183,616 resolved (22.4%), 7,799 resolving to corpus decisions
- 5,031 source decisions with outgoing citations
- 804 positive pairs (resolved citations between corpus decisions)
- **Benchmark requirement:** ≥10 positive pairs → **PASSED** (80x margin)

### 6. v17b Label Normalization at 174k
**File:** `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json`

**Results:**
- Total decisions: 173,963
- Decisions with legal_area: 91,193
- Raw unique labels: 213 → Normalized: 163 (**23.5% reduction**)
- Labels changed by normalization: 85,819 (49.3%)
- Avg decisions/label: 428 → 560
- 42 cross-lingual mappings active (DE/FR/IT)
- **Uniform improvement confirmed** across all 6 representations at 1200 scale (v17b results):
  - center_projected_64dim: +20.2% hierarchy, +22.3% zoom fine, +14.8% legal_area
  - cited_outcome_hybrid_0.5: +21.5% / +20.4% / +15.1%
  - linear_citation_concat: +18.9% / +19.4% / +12.7%
  - **linear_hybrid05_concat: +24.0% / +27.7% / +15.3%** (largest improvement)
  - linear_citation_w3070: +15.6% / +17.9% / +13.0%
  - linear_citation_ridge: +19.4% / +21.5% / +15.2%

**Conclusion:** The v16 hierarchy-family FAIL was a shared label artifact (cross-lingual duplication), not a representation limitation.

---

## 174k Metadata

**Files:**
- `evaluation/data/174k/metadata_174k.json` — 173,963 decisions (33 MB)
- `evaluation/data/174k/metadata_174k.jsonl` — JSONL format (28 MB)
- `evaluation/data/174k/metadata_stats.json` — Summary statistics

**Language Distribution:**
- German (de): 106,501 (61.2%)
- French (fr): 57,489 (33.0%)
- Italian (it): 9,973 (5.7%)

**Branch Distribution:**
- oeffentliches_recht: ~55,000
- zivilrecht: ~48,000
- strafrecht: ~42,000
- sozialversicherungsrecht: ~15,000

---

## Production Representations Awaited from Legal-Distance

| Representation | Type | Status |
|---------------|------|--------|
| cited_decisions_tfidf | TF-IDF (unsupervised) | ⏳ Computing (year-split) |
| outcome_tfidf | TF-IDF (unsupervised) | ⏳ Computing |
| cited_outcome_hybrid_0.5 | Hybrid TF-IDF (default) | ⏳ Computing |
| cited_outcome_hybrid_0.7 | Hybrid TF-IDF | ⏳ Computing |
| center_projected_768dim | Dense embedding | ⏳ Computing (year-split) |
| center_projected_64dim | Dense embedding (prod default) | ⏳ Computing |
| linear_metric_epoch4 | Metric learning | ⏳ Computing |
| mahalanobis_metric_epoch4 | Metric learning | ⏳ Computing |
| hybrid_stabilized_epoch1 | Hybrid (ML + hierarchy) | ⏳ Computing |
| citation_role_citing_alpha0.3 | Citation role | ⏳ Computing |
| citation_role_following_alpha0.3 | Citation role | ⏳ Computing |
| citation_role_criticizing_alpha0.3 | Citation role | ⏳ Computing |
| linear_citation_concat | Static combination | ⏳ Computing |
| linear_hybrid05_concat | Static combination | ⏳ Computing |

**Legal-distance lane status:** RUN (staged 174k CPU execution, year-split, TF-IDF first)
**Expected delivery:** As year-split chunks complete on free public runners (65-min job ceilings)

---

## Execution Plan When Representations Land

1. **Run Full 12-Benchmark Suite at 174k** on all production representations
   - Use `run_full_corpus_evaluation.py` with HNSW backend
   - Frozen harness v3 thresholds unchanged
   - Distributed evaluation across workers if needed

2. **Execute Citation Heritage Benchmark** at 174k
   - Use 804 positive pairs + 1,608 negative pairs (frozen seed 42)
   - AUC-ROC threshold ≥ 0.65

3. **Test v17b Label Normalization Generalization** at 174k
   - Compare raw vs normalized legal_area on hierarchy/zoom/legal_area benchmarks
   - Validate uniform purity improvement across all representations

4. **Report Results** with full provenance
   - Config hashes, global seeds, embedding file hashes
   - Per-representation benchmark results
   - Best representation analysis (must pass both adversarial gates)

---

## Blockers & Dependencies

| Blocker | Status | Resolution |
|---------|--------|------------|
| 174k embeddings from legal-distance | ⏳ PENDING | Legal-distance actively computing (year-split, TF-IDF first) |
| Jurist human study (5-10 Swiss jurists) | 🔴 BLOCKED | Framework ready; requires owner recruitment |

---

## Evidence References

### Code
- `evaluation/run_full_corpus_evaluation.py` — Full corpus evaluation entry point
- `evaluation/scalable_nn.py` — HNSW scalable NN infrastructure
- `evaluation/evaluation_v3_harness.py` — Frozen adversarial harness
- `evaluation/experiments/run_v16_full_benchmark_suite.py` — 12-benchmark suite
- `evaluation/experiments/legal_area_normalize.py` — Cross-lingual label normalization

### Results (1200-scale validation)
- `evaluation/results/full_corpus_test/full_corpus_evaluation_results_worker0.json`
- `evaluation/results/v16_full_benchmark_suite/v16_full_benchmark_results.json`

### 174k Infrastructure
- `evaluation/data/174k/metadata_174k.json`
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`
- `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json`

### Reports
- `evaluation/reports/evaluation_v25_174k_readiness_report.md` — Previous readiness report
- `evaluation/reports/evaluation_v17b_label_normalization_all_reps.md` — v17b uniformity confirmation

---

## Next Recommendation: CONTINUE (when representations land)

**When 174k representations arrive:**
1. Execute full evaluation suite autonomously
2. No human intervention required for machine-executable benchmarks
3. Jurist human study remains external dependency (framework ready)

**Factory Director Action:** None required — evaluation lane will auto-execute when legal-distance delivers 174k representations.

---

*Report generated by Evaluation Lane — LexMachina Factory*