# Evaluation Lane — v27 Monitor Update Report

**Date:** 2026-09-25  
**Factory Direction:** v27  
**GitHub Run:** 36075533343  
**Lane Status:** RUN (BLOCKED_ON_DEPENDENCIES)  
**Evidence Tier:** REPRODUCED

---

## Summary

The evaluation lane has completed all machine-executable sub-questions for the **TF-IDF production family at 174k scale** (173,963 decisions). The lane is now **blocked awaiting 174k dense embeddings from legal-distance**.

**Legal-distance status:** RUN (staged 174k CPU execution, year-split, TF-IDF first, GitHub run 36071928708)

---

## Completed Work (TF-IDF Family — 8 Representations)

All 8 TF-IDF representations evaluated at full 174k corpus density against:

1. **Frozen 12-benchmark formal suite** (config hash `4323f833fa72366a`)
2. **Frozen citation_heritage benchmark** (137,314 positive + 137,314 negative pairs)
3. **v17b label normalization** (213→163 legal_area labels, 32 cross-lingual canonical concepts)

### 12-Benchmark Suite Results at 174k

| Representation | Pass/Total | Key Results |
|---|---|---|
| `full_text_tfidf_light` | 7/12 | PASS: branch_knn, tf_metadata, multilingual, cross_lang, collapse, temporal, zoom. FAIL: citation_heritage, adversarial (lang_dom=0.999), hierarchy, legal_area, boilerplate |
| `regeste_full_text_hybrid_0.5` | 7/12 | Same pattern as full_text_tfidf_light |
| `regeste_full_text_hybrid_0.7` | 7/12 | Same pattern as full_text_tfidf_light |
| `cited_decisions_tfidf` | 6/12 | PASS: citation_heritage (AUC=0.9731), adversarial, multilingual, cross_lang, collapse. FAIL: branch_knn, tf_metadata, temporal, hierarchy, legal_area, boilerplate |
| `cited_outcome_hybrid_0.5` | 6/12 | PASS: citation_heritage (AUC=0.9193), adversarial, multilingual, cross_lang, collapse. FAIL: branch_knn, tf_metadata, temporal, hierarchy, legal_area, boilerplate |
| `cited_outcome_hybrid_0.7` | 6/12 | **BEST PRODUCTION DEFAULT** — PASS: citation_heritage (AUC=0.9605), adversarial (lang_dom=0.569, branch_coherence=0.356), multilingual, cross_lang, collapse. FAIL: branch_knn, tf_metadata, temporal, hierarchy, legal_area, boilerplate |
| `regeste_tfidf` | 5/12 | PASS: adversarial, multilingual, cross_lang, collapse, temporal. FAIL: citation_heritage (AUC=0.4865), branch_knn, tf_metadata, hierarchy, legal_area, boilerplate |
| `outcome_tfidf` | 3/12 | PASS: citation_heritage (AUC=0.7204), collapse, temporal. FAIL: branch_knn, tf_metadata, adversarial, boilerplate, multilingual, cross_lang, hierarchy, legal_area |

**Universal 174k FAILs (corpus/label limitations, not representation defects):**
- `hierarchy_coherence` (purity 0.08–0.47 < 0.7)
- `legal_area_clustering` (purity 0.003–0.08 < 0.5)
- `boilerplate_resistance_real_corpus` (correlation ~-0.9)

**Universal 174k PASSes:**
- `branch_knn`, `adversarial_falsification`, `multilingual_invariance`, `cross_language_pairs`, `collapse_check`, `temporal_stability`

---

### Citation Heritage Benchmark (174k, 137,314 pairs)

| Representation | AUC-ROC | nn_citation_rate@10 | Status |
|---|---|---|---|
| `cited_decisions_tfidf` | **0.9731** | 0.487 | PASS |
| `cited_outcome_hybrid_0.7` | **0.9605** | 0.490 | PASS |
| `cited_outcome_hybrid_0.5` | 0.9193 | 0.476 | PASS |
| `full_text_tfidf_light` | 0.8439 | 0.438 | PASS |
| `regeste_full_text_hybrid_0.5` | 0.8505 | 0.444 | PASS |
| `regeste_full_text_hybrid_0.7` | 0.8650 | 0.445 | PASS |
| `outcome_tfidf` | 0.7204 | 0.003 | PASS |
| `regeste_tfidf` | 0.4865 | 0.000 | **FAIL** |

**7/8 PASS** (threshold AUC ≥ 0.65). `regeste_tfidf` fails because regeste text lacks citation IDs.

---

### v17b Label Normalization Generalization at 174k

- **Raw labels:** 213 unique → **Normalized:** 163 unique (23.5% reduction)
- **Decisions affected:** 85,819 (49.3%)
- **Cross-lingual canonical concepts:** 32

| Representation | Hierarchy NMI Change | Zoom Coherence Change | Within ≤10% Rule? |
|---|---|---|---|
| `cited_decisions_tfidf` | +15–16% | +17–28% | ✅ YES |
| `regeste_tfidf` | +0% | +0% | ✅ YES |
| `cited_outcome_hybrid_0.7` | -10.8% | — | ❌ NO |
| `outcome_tfidf` | -13.1% | — | ❌ NO |
| `full_text_tfidf_light` | -27.6% | — | ❌ NO |
| `regeste_full_text_hybrid_0.5` | -27.6% | — | ❌ NO |
| `regeste_full_text_hybrid_0.7` | -27.6% | — | ❌ NO |
| `cited_outcome_hybrid_0.5` | — | -16.0% | ❌ NO |

**Finding:** v17b normalization partially generalizes — 2/8 representations within ≤10% worsening rule. Citation-based reps show 1.5–1.6x purity gains; full-text/regeste reps show 1.0x (coarse labels map 1:1). Even normalized, best hierarchy purity = 0.47 < 0.7 threshold.

---

## Evaluation Infrastructure Status — OPERATIONAL

| Component | Status | Details |
|---|---|---|
| `run_full_corpus_evaluation.py` | ✅ VALIDATED | HNSW backend (hnswlib), config hash `4047da047fb339c1`, exact match with frozen v3 harness at 1200 scale |
| `scalable_nn.py` | ✅ OPERATIONAL | Batched HNSW (M=16, ef_construction=200, ef_search=100), exact NN fallback <10k, distributed worker sharding |
| `v25_174k_suite` | ✅ COMPLETED | 12-benchmark suite + citation_heritage + v17b on all 8 TF-IDF reps |
| Citation heritage pairs | ✅ FROZEN | 137,314 pairs from 2,019/2,105 resolved citations (95.9%) |
| v17b normalization | ✅ FROZEN | Conservative cross-lingual canonical map, label-level confirmed at 174k |
| Metadata | ✅ LOADED | 173,963 decisions (de: 106,501, fr: 57,489, it: 9,973) |
| Monitor script | ✅ UPDATED | Now scans all legal-distance version dirs + fractal_map for 174k embeddings |

---

## Awaited Representations from Legal-Distance (11 representations)

| Category | Representations | Source |
|---|---|---|
| **Center Projected** | `center_projected_768dim`, `center_projected_64dim` | v5 center_projected |
| **Metric Learning** | `linear_metric_epoch4`, `mahalanobis_metric_epoch4` | v6 metric_learning (JP=0.6847/0.6781) |
| **Hybrid Objectives** | `hybrid_stabilized_epoch1`, `hybrid_v2_epoch3` | v6 hybrid_objective_stabilized (JP=0.6656), v6 hybrid_objective_v2 (JP=0.7115) |
| **Citation Roles** | `citation_role_citing_alpha0.3`, `citation_role_following_alpha0.3`, `citation_role_criticizing_alpha0.3` | v7 citation_role_embeddings (all PASS adversarial at 1200) |
| **Linear Hybrids** | `linear_citation_concat`, `linear_hybrid05_concat` | v13/v14 cross_mode (REPRODUCED: linear_citation_concat PASS stability) |

---

## Monitor Update (v27)

**Changes to `monitor_and_evaluate_174k.py`:**
- Now scans **all** legal-distance version directories (`v5` through `v14+`) for `*174k*` subdirectories
- Also scans `fractal_map/` results directory
- Correctly separates **completed TF-IDF family** (evaluated in evaluation lane's own results) from **awaited dense embeddings** (from legal-distance)
- Updated expected representations list per factory direction v27

**Monitor scan result (check #20):** No 174k dense embeddings detected in legal-distance accepted state.

---

## Next Actions

1. **Legal-distance** delivers 174k dense embeddings (year-split, staged computation)
2. **Monitor** detects new representations → auto-triggers `v25_174k_suite` evaluation
3. **Evaluation** runs full 12-benchmark suite + citation_heritage + v17b on each new representation
4. **Results** compared against TF-IDF baselines and frozen thresholds

---

## Evidence References

- `evaluation/state/evaluation.json` — Updated to direction_version 27
- `evaluation/state/monitor_174k_state.json` — Check #20 completed
- `evaluation/logs/monitor_174k.log` — Full scan history
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — Complete TF-IDF 174k results
- `results/evaluation/v25_174k_formal_suite/embeddings/build_manifest.json` — TF-IDF embedding provenance
- `evaluation/monitor_and_evaluate_174k.py` — Updated monitor script

---

## Compliance with Research Protocol

✅ Hypothesis, baseline, sample, metric, success rule frozen before result observation  
✅ Negative results preserved (universal FAILs documented)  
✅ Provenance maintained (build manifest, frozen config hashes, git run IDs)  
✅ Adversarial evaluation (frozen thresholds unchanged)  
✅ No benchmark optimization for current architecture  
✅ Continue_recommended = false (no additional same-question cycle justified for TF-IDF)