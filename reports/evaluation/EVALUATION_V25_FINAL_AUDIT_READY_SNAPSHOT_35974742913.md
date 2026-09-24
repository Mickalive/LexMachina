# Evaluation Lane — Final Audit-Ready Snapshot (v25)

**GitHub Run:** 35974742913  
**Factory Direction:** v25  
**Lane Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** ACCEPTED  
**Timestamp:** 2026-09-24T08:36:00Z  
**Continue Recommended:** FALSE — No additional same-question cycle justified

---

## Executive Summary

The evaluation lane has completed all infrastructure validation for the v25 174k formal suite. All three sub-questions are **INFRASTRUCTURE-READY** but **BLOCKED** on legal-distance lane delivery of 174k production representations (gh run 35935612800 active). The evaluation lane is correctly paused; no additional same-question cycle is justified.

### v25 Sub-Questions Status

| Sub-Question | Infrastructure | Status |
|--------------|----------------|--------|
| 1. Full 12-benchmark formal suite at 174k on all production representations (frozen harness v3) | ✅ FROZEN & VALIDATED | BLOCKED on embeddings |
| 2. Citation_heritage benchmark (174k, 804/1020 positive pairs) | ✅ READY (137,314 full pairs available) | BLOCKED on embeddings |
| 3. v17b label normalization clustering test at 174k | ✅ LABEL LEVEL CONFIRMED (213→163 labels) | BLOCKED on embeddings |

---

## Infrastructure Verification (All REPRODUCED This Cycle)

### 1. Frozen Harness v3 — EXACT REPRODUCTION ✅
- **Config Hash:** `a31c443a9b0e992e` (verified)
- **Seed:** 42 (frozen)
- **Representations Tested:** 6
- **Results:** Exact match with accepted state

| Representation | Verdict | LangDom | JuristPref | Both Gates |
|---------------|---------|---------|------------|------------|
| linear_metric_epoch4 | PASS | 0.6805 ✓ | 0.6847 ✓ | ✓ |
| mahalanobis_metric_epoch4 | PASS | 0.6843 ✓ | 0.6781 ✓ | ✓ |
| hybrid_stabilized_epoch1 | PASS | 0.6704 ✓ | 0.6656 ✓ | ✓ |
| hybrid_v2_epoch3 | PASS | 0.7115 ✓ | 0.5988 ✓ | ✓ |
| **center_projected_64dim** (reference baseline) | **PASS** | **0.7664 ✓** | **0.5121 ✓** | **✓** |
| center_projected_768 | FAIL | 0.7738 ✓ | 0.4912 ✗ | ✗ |

### 2. Full Corpus Harness (HNSW) — VALIDATED at 1200 Scale ✅
- **Config Hash:** `4047da047fb339c1` (verified)
- **Backend:** HNSW (hnswlib) with exact NN fallback <10k
- **Force-Exact Validation:** Exact match with frozen harness v3 adversarial results
- **Production Default at 174k:** `cited_outcome_hybrid_0.5_174k` (awaited)

### 3. V16 Full Benchmark Suite (12 Benchmarks) — REPRODUCED at 1200 Scale ✅
- **Config Hash:** `4323f833fa72366a` (verified)
- **Representations:** 6 (baseline + hybrid + 4 v15 combinations)
- **Results:** Exact match with accepted state

| Benchmark | Universal Result |
|-----------|------------------|
| branch_knn | PASS (all 6) |
| adversarial_falsification | PASS (all 6) |
| multilingual_invariance | PASS (all 6) |
| cross_language_pairs | PASS (all 6) |
| collapse_check | PASS (all 6) |
| temporal_stability | PASS (all 6) |
| boilerplate_resistance_real_corpus | FAIL (all 6) |
| hierarchy_coherence | FAIL (all 6) |
| zoom_coherence | FAIL (all 6) |
| legal_area_clustering | FAIL (all 6) |
| tf_metadata_human_indexing | CONDITIONAL (4/6 PASS) |
| citation_heritage | SKIP (0 pairs in 1200 slice) |

**Pass Counts:** center_projected_64dim=7/12, cited_outcome_hybrid_0.5=6/12, linear_citation_concat=7/12, linear_hybrid05_concat=7/12, linear_citation_w3070=6/12, linear_citation_ridge=7/12

### 4. V17b Label Normalization — UNIFORM IMPROVEMENT CONFIRMED ✅
- **At 1200 Scale:** 788/1200 labels normalized, 104→54 unique (-48%), uniform 15-28% purity improvement across ALL 6 representations
- **At 174k Scale:** 213→163 unique labels (-23.5%), 85,819 decisions changed (49.3%), 32 cross-lingual canonical concepts
- **Uniformity:** NO representation worsens by >10% on any hierarchy-family metric
- **Conclusion:** v16 hierarchy-family FAIL was a shared label artifact, not representation-specific

### 5. Citation Heritage 174k — INFRASTRUCTURE READY ✅
- **Positive Pairs:** 1,020 (direct + shared citations)
- **Negative Pairs:** 1,020 (sampled, no citation relation)
- **Full Pairs Available:** 137,314 positive + 137,314 negative
- **Citation Resolution:** 95.9% (2,019/2,105)
- **Decisions in Graph:** 174 with outgoing citations
- **Previous Test (cycle branch):** cited_outcome_hybrid_0.5_174k → AUC=0.482 (FAIL, threshold=0.65) — TF-IDF insufficient at 174k scale; dense embeddings required

### 6. Auto-Monitor Script — OPERATIONAL ✅
- **Script:** `evaluation/monitor_and_evaluate_174k.py`
- **Function:** Watches legal-distance accepted state, auto-runs full evaluation suite when 174k representations appear
- **Status:** Created and operational

---

## Negative Results Preserved (Per Research Protocol)

| Benchmark | Result | Interpretation |
|-----------|--------|----------------|
| boilerplate_resistance | ~ -0.9 (all reps) | Measures language dominance, not procedural boilerplate |
| hierarchy_coherence | FAIL (purity ~0.25-0.39) | v18 confirmed fundamental branch-level limitation |
| zoom_coherence | FAIL (negative improvement) | No improvement from coarse to fine at branch level |
| legal_area_clustering | FAIL (purity ~0.006-0.009) | Fine-grained label granularity prevents purity > 0.5 |
| citation_heritage on TF-IDF | FAIL (AUC=0.482) | TF-IDF cannot recover citation proximity at 174k scale |
| center_projected_768 | FAILS jurist gate (0.4912 < 0.5) | Confirmed across all verifications |

---

## Production Decision Gates (Frozen)

| Gate | Requirement | Status |
|------|-------------|--------|
| PRODUCT_SERVING_DEFAULT (cited_outcome_hybrid_0.5) | Must pass BOTH adversarial gates at 174k | PENDING embeddings |
| COMBINATION_MODE (linear_hybrid05_concat) | Must pass BOTH adversarial gates + stability test at 174k | PENDING embeddings |
| DEFAULT_MAP_MODE (center_projected_64dim_hierarchical) | Validated PASS both gates at 1200, must re-verify at 174k | PENDING embeddings |

---

## External Blockers

| Blocker | Status |
|---------|--------|
| Jurist human study (5-10 Swiss jurists) | Framework ready, externally blocked (requires repository owner recruitment) |

---

## Awaiting from Legal-Distance (gh run 35935612800)

### Priority 1: TF-IDF Signals (CPU-cheap, year-split)
- cited_decisions_tfidf
- outcome_tfidf
- cited_outcome_hybrid_0.5
- cited_outcome_hybrid_0.7
- linear_citation_concat
- linear_hybrid05_concat
- linear_citation_w3070
- linear_citation_ridge

### Priority 2: Dense Embeddings (year-split)
- center_projected_768dim
- center_projected_64dim
- linear_metric_epoch4
- mahalanobis_metric_epoch4
- hybrid_stabilized_epoch1

### Priority 3: Citation Roles
- citation_role_citing_alpha0.3
- citation_role_following_alpha0.3
- citation_role_criticizing_alpha0.3
- citation_role_distinguishing_alpha0.3
- citation_role_overruling_alpha0.3

---

## Evidence References (Immutable)

### Core Infrastructure
- `evaluation/evaluation_v3_harness.py` — Frozen harness v3 (config hash a31c443a9b0e992e)
- `evaluation/scalable_nn.py` — HNSW scalable NN (config hash 4047da047fb339c1)
- `evaluation/run_full_corpus_evaluation.py` — Full corpus harness
- `evaluation/experiments/run_v16_full_benchmark_suite.py` — 12-benchmark suite (config hash 4323f833fa72366a)
- `evaluation/experiments/run_v17b_label_normalization_all_reps.py` — Label normalization test
- `evaluation/experiments/legal_area_normalize.py` — Cross-lingual normalization map
- `evaluation/validate_citation_heritage_174k.py` — Citation heritage infrastructure
- `evaluation/monitor_and_evaluate_174k.py` — Auto-monitor for 174k representations

### Accepted Results (Immutable)
- `results/evaluation/v3/evaluation_v3_results.json` — Frozen harness v3 results
- `results/evaluation/v16_full_benchmark_suite/v16_full_benchmark_results.json` — V16 results
- `results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_results.json` — V17b results
- `evaluation/results/174k_citation_heritage/citation_pairs_174k.json` — 174k citation pairs (1,020 pos/neg)
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — 174k full citation pairs (137k pos/neg)
- `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json` — 174k label analysis

### Accepted Corpus State
- `/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/citation_graph_resolved.json`
- `/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/citation_to_decision_id.json`
- `/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/citation_resolution_report.md`
- `/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy`

---

## Next Recommendation

**BLOCKED_ON_DEPENDENCIES** — All evaluation infrastructure FROZEN, VALIDATED, and AUDIT-READY for 174k execution. Three v25 sub-questions blocked on legal-distance 174k representations (gh run 35935612800 active). No additional same-question cycle justified. Factory Director to await legal-distance delivery in accepted state before authorizing next evaluation cycle. Snapshot is audit-ready.

---

## Verification Checklist (All ✅)

- [x] Frozen harness v3 config hash verified: `a31c443a9b0e992e`
- [x] Full corpus harness config hash verified: `4047da047fb339c1`
- [x] V16 benchmark suite config hash verified: `4323f833fa72366a`
- [x] Frozen harness v3 exact reproduction confirmed
- [x] Full corpus harness force-exact 1200-scale validation confirmed
- [x] V16 full benchmark suite reproduction confirmed (6 representations, 12 benchmarks)
- [x] V17b label normalization uniformity confirmed across all 6 representations
- [x] V17b label normalization 174k label-level confirmed (213→163 labels, 32 cross-lingual concepts)
- [x] Citation heritage 174k infrastructure validated (1,020 pos/neg pairs, 137k full pairs)
- [x] Auto-monitor script created and operational
- [x] All negative results preserved
- [x] All config hashes frozen and verified
- [x] No additional same-question cycle justified

---

**AUDIT STATUS: READY**  
This snapshot captures the complete, validated evaluation infrastructure state for v25. All claim-bearing results are frozen with verified config hashes. The lane is correctly blocked on upstream dependencies with no further work justified until 174k representations land in accepted state.
