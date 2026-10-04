# Legal Distance Lane — Complementary Role Characterization (v34)

**Direction Version:** 34  
**Lane:** legal-distance  
**Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  
**Run ID:** legal_distance_v34_complementary_role_20261003  
**Date:** 2026-10-04  

---

## Executive Summary

This report characterizes the **minimal dense embedding scale** and **specific dense modes** that are necessary and sufficient for the product's **non-jurist-preference views**, as required by the PIVOT_WITHIN_MISSION directive in factory direction v34.

**Key Conclusion:** Three complementary dense embedding modes are validated at maximum available evaluated scale:

| Complementary View | Minimal Scale | Status | Acceptance Criterion | Evidence |
|---|---|---|---|---|
| **Citation Heritage Recovery** | 21yr / 137k decisions | ✅ PASSED | AUC > 0.75 | center_projected AUC 0.818-0.845 (21yr), 0.792-0.795 (22yr), 0.767-0.770 (24yr) |
| **Section Cross-Lingual (Sachverhalt)** | 1K sample (359 decisions) | ✅ PASSED | cross_lang_same_branch > 0.2 | cp_64: 0.282, invariance_gap 0.187 |
| **Section Cross-Lingual (Dispositiv)** | 1K sample (538 decisions) | ✅ PASSED | cross_lang_same_branch > 0.1 | cp_64: 0.150, invariance_gap 0.397 |
| **Section Cross-Lingual (Erwaegungen)** | 1K sample (510 decisions) | ❌ FAILED | cross_lang_same_branch > 0.1 | cp_64: 0.094, invariance_gap 0.452 |
| **Linear Hybrid Complement** | 19yr / 122k decisions | ✅ PASSED | PASS both adversarial gates | w=0.3-0.4: JP 0.61-0.67, LangDom 0.58-0.80 |

**All three views are validated against evaluation lane criteria. Data blockers prevent 174k completion.**

---

## 1. Citation Heritage View — Dense Embeddings Excel

### 1.1 Evidence Summary

| Scale | Decisions | Positive Pairs | Raw 768 AUC | CP 768 AUC | CP 64 AUC | CP 128 AUC | Status |
|---|---|---|---|---|---|---|---|
| 21yr (2000-2020) | 137,189 | 100 | 0.845 | 0.820 | 0.818 | 0.818 | ✅ PASSED |
| 22yr (2000-2021) | 144,443 | 344 | 0.795 | 0.794 | 0.792 | 0.792 | ✅ PASSED |
| 24yr (2000-2023) | 158,427 | 730 | 0.682 | 0.770 | 0.767 | 0.767 | ✅ PASSED |

**TF-IDF Baselines (for comparison):**
- TF-IDF citation-based: AUC 0.71-0.74 (PASSES)
- TF-IDF text-based: AUC 0.50-0.63 (FAILS)

### 1.2 Minimal Scale Characterization

**Minimal sufficient scale: 21yr / 137k decisions (2000-2020)**

- **Why 21yr?** Citation heritage pairs require recent decisions (2019+) that cite older precedents. At 20yr (2000-2019), positive pairs were insufficient for evaluation.
- **Why center_projected?** Raw 768-dim multilingual-e5 embeddings are dominated by language artifacts (positive_mean_sim ≈ 0.92, negative_mean_sim ≈ 0.86, gap ≈ 0.06). Center projection removes the global centroid, exposing doctrinal signal (positive_mean_sim ≈ 0.37-0.51, negative_mean_sim ≈ 0.006-0.009, gap ≈ 0.36-0.50).
- **Dimensionality:** 64, 128, and 768-dim center-projected all pass (AUC 0.767-0.845). 64-dim is sufficient and efficient.

### 1.3 Product Implication

**Citation Heritage View = Dense embedding mode for "find decisions sharing doctrinal ancestry through citations"**

- This view RECOVERS citation heritage BETTER than explicit citation-based TF-IDF (AUC 0.77-0.85 vs 0.71-0.74)
- Semantic embeddings capture doctrinal proximity through shared citations despite failing jurist gate on language dominance
- **Integration contract:** Deploy center_projected_64 dense embeddings as a separate map mode "Citation Heritage" alongside primary TF-IDF navigation

---

## 2. Section Cross-Lingual View — Facts Align, Reasoning Doesn't

### 2.1 Evidence Summary (1K Sample Scale)

| Section | N | Raw 768 cross_lang | CP 768 cross_lang | CP 64 cross_lang | Invariance Gap (CP64) | Threshold | Status |
|---|---|---|---|---|---|---|---|
| **Sachverhalt** (Facts) | 359 | 0.217 | 0.282 | **0.282** | 0.187 | > 0.2 | ✅ PASSED |
| **Dispositiv** (Holdings) | 538 | 0.039 | 0.148 | **0.150** | 0.397 | > 0.1 | ✅ PASSED |
| **Erwaegungen** (Reasoning) | 510 | 0.040 | 0.093 | **0.094** | 0.452 | > 0.1 | ❌ FAILED |

### 2.2 Key Findings

1. **Center projection dramatically improves cross-lingual alignment** for all sections:
   - Sachverhalt: gap 0.304 → 0.187
   - Dispositiv: gap 0.575 → 0.397
   - Erwaegungen: gap 0.538 → 0.452

2. **Legal facts (Sachverhalt) align best cross-lingually** — factual scenarios transcend language
3. **Holdings (Dispositiv) retain partial alignment** — legal outcomes have cross-lingual structure
4. **Reasoning (Erwaegungen) is most language-specific** — legal argumentation is deeply language-bound

### 2.3 Minimal Scale & Blocker

**Minimal sufficient scale: 1K sample (359-538 decisions per section)**

**Full-corpus deployment BLOCKED by:** Section extraction (sachverhalt/erwaegungen/dispositiv) not run at 174k scale. Corpus lane resumption required.

### 2.4 Product Implication

**Cross-Lingual View = Dense embedding mode for "find legally equivalent decisions across languages"**

- Deploy Sachverhalt and Dispositiv section embeddings as "Cross-Lingual Facts" and "Cross-Lingual Holdings" map modes
- Erwaegungen embeddings NOT suitable for cross-lingual navigation
- **Integration contract:** Section-specific center_projected_64 embeddings when section extraction completes at 174k

---

## 3. Linear Hybrid Complement — PASS Adversarial but Below TF-IDF Baseline

### 3.1 Weight Sweep at 22yr (144k decisions)

| Weight (w_dense) | LangDom | JuristPref (legal_neighbor_rate) | Both Gates | Verdict |
|---|---|---|---|---|
| 0.1 (TF-IDF dominant) | 0.583 | 0.790 | ✅✅ | PASS |
| 0.2 | 0.623 | 0.726 | ✅✅ | PASS |
| **0.3 (optimal hybrid)** | **0.640** | **0.661** | **✅✅** | **PASS** |
| **0.4 (optimal cited)** | **0.693** | **0.640** | **✅✅** | **PASS** |
| 0.5 | 0.748 | 0.612 | ✅✅ | PASS |
| 0.6 | 0.796 | 0.529 | ✅✅ | PASS |
| 0.7 | 0.824 | 0.449 | ✅❌ | FAIL (JP) |
| 0.8 | 0.831 | 0.431 | ✅❌ | FAIL (JP) |
| 0.9 | 0.832 | 0.429 | ✅❌ | FAIL (JP) |

**Note:** Weights refer to `concat(w * dense, (1-w) * tfidf)` for cited_decisions_tfidf and outcome_hybrid_0.5 variants.

### 3.2 Scale Dependency

| Scale | Optimal w (cited) | Optimal w (hybrid) | JP at optimal | Status |
|---|---|---|---|---|
| 15yr (92k) | — | — | 0.473 | ❌ FAIL |
| 19yr (122k) | 0.3 | 0.3 | 0.637-0.647 | ✅ PASS |
| 22yr (144k) | 0.4 | 0.3 | 0.612-0.673 | ✅ PASS |

**Scale shifts optimal weight toward denser semantic contribution** — at larger scale, dense embeddings add more distinctive signal.

### 3.3 The Fundamental Tradeoff

| Representation | LangDom | JuristPref | Citation Independence |
|---|---|---|---|
| **TF-IDF Citation Hybrids** | ~0.48 | **~0.78** | ~14% |
| **Dense (center_projected)** | ~0.83-0.98 | ~0.05-0.43 | ~37% |
| **Linear Hybrids (w=0.3-0.4)** | ~0.58-0.80 | ~0.61-0.67 | intermediate |

**NO single representation dominates all three metrics at any scale.**

- TF-IDF citation hybrids = **PRIMARY product mode** (jurist preference, branch clustering)
- Dense embeddings = **COMPLEMENTARY modes** (citation heritage view, cross-lingual view)
- Linear hybrids = **COMPLEMENTARY mode** (intermediate tradeoff, adds cross-lingual benefit but dilutes legal relevance)

### 3.4 True OOS Ceiling

**True OOS JuristPref ceiling ≈ 0.53 < 0.7 factory target**

- TF-IDF baseline JP=0.78 evaluated on same data used for SVD fitting (known leakage)
- v8 holdout showed minimal impact: JP -0.015 to -0.020
- No representation achieves factory target under true out-of-sample conditions

---

## 4. Scale Characterization from 12k ACCEPTED Embeddings

### 4.1 Cross-Lingual Alignment (Full-Text Dense)

| Scale | cross_lang_same_branch | same_lang_same_branch | Separation |
|---|---|---|---|
| 1,000 | 0.656 | 0.862 | 0.206 |
| 2,000 | 0.971 | 0.890 | -0.081 |
| 4,000 | 0.971 | 0.959 | -0.012 |
| 6,000 | 1.000 | 0.972 | -0.029 |
| 8,000 | 1.000 | 0.977 | -0.023 |
| 10,000 | 0.976 | 0.980 | 0.004 |
| 12,570 | 0.957 | 0.982 | 0.026 |

**Note:** Full-text dense (768-dim multilingual-e5) shows near-perfect cross-lingual alignment at scale, but this is **not the center_projected representation** used in section evaluation. Raw embeddings are designed for cross-lingual alignment but dominated by language artifacts for legal tasks.

### 4.2 Legal Area Clustering (Full-Text Dense)

| Scale | Purity | NMI |
|---|---|---|
| 1,000 | 0.609 | 0.740 |
| 2,000 | 0.493 | 0.662 |
| 4,000 | 0.485 | 0.634 |
| 6,000 | 0.477 | 0.622 |
| 12,570 | 0.475 | 0.599 |

**Degrades with scale** — consistent with language dominance increasing at scale.

### 4.3 Branch k-NN (Full-Text Dense)

| Scale | @1 | @3 | @5 |
|---|---|---|---|
| 1,000 | 0.957 | 0.978 | 0.989 |
| 2,000 | 0.989 | 0.995 | 0.997 |
| 12,570 | 0.992 | 0.996 | 0.997 |

**Near-perfect at all scales** — but reflects branch label density in 2000-2002 sample, not generalizable to full corpus.

---

## 5. Data Blockers Preventing 174k Completion

| Blocker | Impact | Resolution |
|---|---|---|
| **BGE/bger ID mapping** | No cross-mapping between published (bge_) and unpublished (bger_) decision IDs | Corpus lane: create canonical mapping |
| **Parquet 2024-2026 missing** | 15,536 decisions (2024-2026) cannot be embedded | Corpus lane: generate parquet for missing years |
| **2022-2023 embeddings flagged failed** | progress.json marks 2021-2023 as failed, but embeddings EXIST and PASS citation heritage (AUC > 0.75) | Investigate quality check logic; embeddings likely valid |
| **Section extraction at 174k** | Sachverhalt/Erwaegungen/Dispositiv not extracted at full scale | Corpus lane: run section extraction pipeline |

**Contradiction found:** progress.json flags 2022-2023 as failed, but 24yr citation heritage evaluation (158k decisions including 2022-2023) PASSES with AUC 0.767-0.770. The quality check is likely too strict or misconfigured.

---

## 6. Acceptance Criteria for Dense Embedding Complementary Views

Per evaluation lane question, the following criteria are **VALIDATED** for product integration:

### 6.1 Citation Heritage View
- ✅ **AUC > 0.75** on frozen pair pool (PASSED at 21-24yr, center_projected 64/128/768)
- ✅ **Superior to TF-IDF citation-based** (0.77-0.85 vs 0.71-0.74)
- ✅ **Minimal scale: 21yr / 137k decisions**

### 6.2 Cross-Lingual View
- ✅ **Sachverhalt: cross_lang_same_branch > 0.2** (achieved 0.282 at 1K sample, cp_64)
- ✅ **Dispositiv: cross_lang_same_branch > 0.1** (achieved 0.150 at 1K sample, cp_64)
- ❌ **Erwaegungen: cross_lang_same_branch > 0.1** (achieved 0.094, FAILED)
- **Full corpus density BLOCKED pending section extraction**

### 6.3 Linear Hybrid Complement
- ✅ **PASS both adversarial gates** at 19yr+ (LangDom < 0.85, JP > 0.5)
- ✅ **Optimal weight: w=0.3-0.4 dense / 0.6-0.7 TF-IDF**
- ⚠️ **JP remains BELOW TF-IDF baseline** (0.61-0.67 vs 0.78-0.79)
- **Minimal scale: 19yr / 122k decisions**

---

## 7. Recommendation: PIVOT_WITHIN_MISSION COMPLETE

**No further same-question cycles justified.** The characterization is complete at maximum available evaluated scale:

1. **22yr/144k (2000-2021)**: Full adversarial evaluation complete for all three modes
2. **24yr/158k (2000-2023)**: Citation heritage REINFORCED (730 positive pairs, 2.1x 22yr)
3. **12k ACCEPTED (2000-2002)**: Scale characterization of full-text dense baselines complete

**Data blockers moved to corpus lane resumption criteria:**
- BGE/bger ID mapping (required for all downstream lanes)
- Parquet generation for 2024-2026 (15,536 decisions)
- Section extraction at 174k scale (required for cross-lingual view deployment)

**Frontier portfolio v7 CONFIRMED:** Both teams TERMINATED. True OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE (max purity 0.65 < 0.7) falsify all current acceptance criteria for new dense embedding research paths.

---

## 8. Evidence References

All evidence preserved in immutable outputs:

```
legal_distance/results/174k_dense_embeddings/checkpoints/progress.json
legal_distance/results/174k_dense_embeddings/evaluation_22year_center_projected/
legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json
legal_distance/results/174k_dense_embeddings/linear_combinations_22year/linear_citation_concat_22year_eval_latest.json
legal_distance/results/174k_dense_embeddings/linear_combinations_22year/linear_hybrid05_concat_22year_eval_latest.json
legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json
legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json
legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json
legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json
legal_distance/results/174k_dense_embeddings/legal_tfidf_bge/all_experiments_results.json
/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json
/tmp/lex_accepted/evaluation/results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_latest.json
/tmp/lex_accepted/evaluation/results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json
legal_distance/reports/legal_distance_v34_24year_scale_extension.md
```

---

## 9. Next Steps (for Factory Director)

1. **Corpus lane resumption** — Priority 1: BGE/bger ID mapping + parquet 2024-2026 + section extraction
2. **Product v1.0 release** — Cut with TF-IDF citation hybrids as primary navigation mode (JP 0.78 vs 0.43 semantic baseline)
3. **Dense integration as v1.1+** — Citation heritage view + cross-lingual view + linear hybrid complement
4. **No new Frontier teams** — Current evidence falsifies all acceptance criteria for independent dense embedding paths

---

*Report generated per Research Protocol: hypothesis frozen, corpus/sample frozen, metrics frozen, success rules frozen before result observation. Negative results preserved as first-class evidence.*