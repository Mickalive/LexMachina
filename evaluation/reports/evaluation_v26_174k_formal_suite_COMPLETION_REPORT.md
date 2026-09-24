# Evaluation Lane v26 — 174k Formal Suite Completion Report

**Factory Direction Version:** 26  
**Lane:** evaluation  
**Run ID:** eval_v26_174k_verification_20260924  
**GitHub Run:** 36069241455  
**Timestamp:** 2026-09-24T22:49:00Z  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions** for the TF-IDF production family at full 174k corpus scale (173,963 decisions). The lane is now **blocked on legal-distance lane delivering 174k dense embeddings** (center_projected, metric learning, hybrid objectives, citation roles, linear hybrids). No additional same-question cycle is justified for the TF-IDF family.

**Monitor Status:** `monitor_and_evaluate_174k.py` scan confirms **zero 174k dense embeddings** detected in legal-distance accepted state. The monitor is operational and will auto-evaluate when representations land.

---

## Sub-Question Completion Status

### ✅ Sub-Question 1: Full 12-Benchmark Formal Suite at 174k Scale
**Protocol:** Frozen v16 benchmark suite (config hash `4323f833fa72366a`), frozen adversarial thresholds, HNSW-backed k-NN at n>10k.

**Results:** All 8 TF-IDF representations evaluated at 173,963 decisions.

| Representation | Pass/12 | Adversarial Gates | Notes |
|---|---|---|---|
| `full_text_tfidf_light` | 7 | ❌ LangDom=0.9999 | Language-dominated |
| `regeste_full_text_hybrid_0.5` | 7 | ❌ LangDom=0.9982 | Language-dominated |
| `regeste_full_text_hybrid_0.7` | 7 | ❌ LangDom=0.9994 | Language-dominated |
| `cited_decisions_tfidf` | 6 | ✅ LangDom=0.60, JP=0.35 | **Citation-based, passes both gates** |
| `cited_outcome_hybrid_0.5` | 6 | ✅ LangDom=0.58, JP=0.35 | **Citation-based, passes both gates** |
| `cited_outcome_hybrid_0.7` | 6 | ✅ LangDom=0.57, JP=0.36 | **Citation-based, passes both gates (PRODUCTION DEFAULT)** |
| `regeste_tfidf` | 5 | ✅ LangDom=0.76, JP=0.62 | Passes both gates, no citation signal |
| `outcome_tfidf` | 3 | ❌ BranchCoherence=0.15 | Fails branch coherence |

**Universal 174k FAILs (corpus/label limitations, not representation defects):**
- `hierarchy_coherence`: purity 0.08–0.47 < 0.7 threshold
- `legal_area_clustering`: purity 0.003–0.08 < 0.5 threshold
- `boilerplate_resistance_real_corpus`: correlation ~-0.55 to +0.09 (proxy measures language dominance)

**Universal 174k PASSes:**
- `collapse_check`, `multilingual_invariance` (citation reps), `cross_language_pairs` (citation reps)

---

### ✅ Sub-Question 2: Citation Heritage Benchmark at 174k
**Protocol:** Frozen 137,314 positive + 137,314 negative pairs from published 174k citation-ID resolution (2,019/2,105 resolved, 95.9%).

| Representation | AUC-ROC | Status | nn_citation_rate@10 |
|---|---|---|---|
| `cited_decisions_tfidf` | **0.9731** | ✅ PASS | 0.487 |
| `cited_outcome_hybrid_0.7` | **0.9605** | ✅ PASS | 0.490 |
| `cited_outcome_hybrid_0.5` | 0.9193 | ✅ PASS | 0.476 |
| `full_text_tfidf_light` | 0.8439 | ✅ PASS | 0.438 |
| `regeste_full_text_hybrid_0.7` | 0.8650 | ✅ PASS | 0.445 |
| `regeste_full_text_hybrid_0.5` | 0.8505 | ✅ PASS | 0.444 |
| `outcome_tfidf` | 0.7204 | ✅ PASS | 0.003 |
| `regeste_tfidf` | 0.4865 | ❌ FAIL | 0.000 |

**Finding:** regeste_tfidf FAILS because regeste text lacks citation IDs — expected. Citation-based representations excel at citation heritage recovery (AUC > 0.96, nn_citation_rate@10 ≈ 0.49).

---

### ✅ Sub-Question 3: v17b Label Normalization Generalization to 174k
**Protocol:** Conservative cross-lingual legal_area normalization (213 raw → 163 normalized labels, 23.5% reduction, 49.3% of labels changed, 85,819 decisions affected, 32 cross-lingual canonical concepts). Success rule: no representation worsens by >10% on hierarchy-family metrics.

| Representation | Hierarchy Purity Δ | Zoom Coherence Δ | Legal Area Δ | Within 10% Rule? |
|---|---|---|---|---|
| `cited_decisions_tfidf` | +53% (0.13→0.20) | -16% (26.2%→22.0%) | +50% | ❌ **EXCEEDS on zoom** |
| `cited_outcome_hybrid_0.5` | +53% | -16% | +50% | ❌ **EXCEEDS on zoom** |
| `cited_outcome_hybrid_0.7` | +53% | -16% | +50% | ❌ **EXCEEDS on zoom** |
| `regeste_tfidf` | +53% | -16% | +50% | ❌ **EXCEEDS on zoom** |
| `full_text_tfidf_light` | +0% (coarse labels) | +0% | +0% | ✅ |
| `regeste_full_text_hybrid_0.5` | +0% | +0% | +0% | ✅ |
| `regeste_full_text_hybrid_0.7` | +0% | +0% | +0% | ✅ |
| `outcome_tfidf` | +0% | +0% | +0% | ✅ |

**Key Findings:**
- Citation-based reps: **1.5–1.6× hierarchy purity gains** but **16% worsening on zoom_coherence** (exceeds 10% threshold)
- Full-text/regeste reps: coarse labels map 1:1 → no change
- Even normalized, best hierarchy purity = 0.47 (full_text_tfidf_light) < 0.7 threshold
- **Conclusion:** v17b normalization partially generalizes; hierarchy-family FAILs at 174k are **not purely label artifacts** — fundamental granularity/coverage limits persist

---

## Production Default Confirmation

**`cited_outcome_hybrid_0.7` confirmed as production default (PRODUCT_SERVING_DEFAULT):**
- ✅ Passes both adversarial gates: LangDom=0.569 < 0.85, BranchCoherence=0.356 > 0.3
- ✅ Citation Heritage AUC=0.9605, nn_citation_rate@10=0.490
- ✅ Zero-shot TF-IDF, no GPU required
- ✅ Equivalent alternative: `cited_outcome_hybrid_0.5` (AUC=0.9193, nn_rate=0.476)

---

## Infrastructure Readiness for Dense Embeddings

| Component | Status | Validation |
|---|---|---|
| `run_full_corpus_evaluation.py` | ✅ OPERATIONAL | Tested on 1000/1200 scale, exact match with frozen v3 harness |
| `scalable_nn.py` (HNSW) | ✅ OPERATIONAL | hnswlib available, config hash `4047da047fb339c1` |
| Citation Heritage pairs | ✅ READY | 137,314 frozen pairs at 174k |
| v17b normalization | ✅ READY | Label mapping confirmed at 174k |
| `monitor_and_evaluate_174k.py` | ✅ OPERATIONAL | Scan detects 0 new representations; will auto-evaluate on arrival |
| Distributed evaluation | ✅ SUPPORTED | Model-level sharding via `DistributedEvaluator` |

**Pipeline Verification:** All evaluation pipelines verified against accepted dense embeddings from legal-distance lane (v6 metric_learning, v6 hybrid_objective_stabilized, v5 center_projected). Results match legal-distance reported adversarial gate outcomes exactly.

---

## Blockers & Dependencies

| Blocker | Type | Resolution |
|---|---|---|
| 174k dense embeddings not computed | **HARD BLOCKER** | legal-distance lane RUN (staged 174k CPU execution, year-split, TF-IDF first, gh run 35935612800) |
| Jurist human study (5–10 Swiss jurists) | EXTERNAL DEPENDENCY | Framework ready; blocked on recruitment by repository owner |

---

## Awaited Dense Representations (from legal-distance)

**Priority 1 — Core Dense Embeddings:**
- `center_projected_768dim`
- `center_projected_64dim`
- `linear_metric_epoch4` (best jurist_pref=0.6847 at 1200)
- `mahalanobis_metric_epoch4` (jurist_pref=0.6781)
- `hybrid_stabilized_epoch1` (jurist_pref=0.6656)
- `hybrid_v2_epoch3` (jurist_pref=0.5988)

**Priority 2 — Citation Role Hybrids:**
- `citation_role_citing_alpha0.3`
- `citation_role_following_alpha0.3`
- `citation_role_criticizing_alpha0.3`

**Priority 3 — Linear Combinations:**
- `linear_citation_concat` (v14 REPRODUCED: mean_delta=+0.0392, paired_std=0.0212)
- `linear_hybrid05_concat` (v14 DISCOVERED: highest JP=0.7925 but FAILS stability)

---

## Evidence References

- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — Complete 12-benchmark results for all 8 TF-IDF reps
- `results/evaluation/v25_174k_citation_heritage/*.json` — Dedicated citation heritage results
- `results/evaluation/v25_174k_v17b/*.json` — v17b normalization comparison (raw vs normalized)
- `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` — Frozen protocol specification
- `evaluation/state/evaluation.json` — Machine-readable lane state (updated with v26 verification)

---

## Next Recommendation

**BLOCKED_ON_DEPENDENCIES — No additional same-question cycle justified for TF-IDF family.**

The evaluation lane will **automatically evaluate** 174k dense embeddings when they land in legal-distance accepted state via `monitor_and_evaluate_174k.py`. Factory Director to decide successor question when dense embeddings are available.

**Jurist human study** remains an external dependency (framework ready, requires 5–10 Swiss jurists recruitment by repository owner).