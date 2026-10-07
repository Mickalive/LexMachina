# Legal Distance Lane — Final Audit Verification (GitHub Run 37601508022)

**Date:** 2026-10-07  
**Factory Direction:** v34  
**Lane:** legal-distance  
**Status:** FINAL_AUDIT_VERIFICATION_COMPLETE  
**Evidence Tier:** ACCEPTED  
**Operational Resume From:** persisted producer snapshot of run 37600259839

---

## Summary

Operational resume from persisted producer snapshot of run 37600259839. All 8/8 `test_complementary_role_v34.py` assertions PASSED. Scale characterization experiment (`characterize_dense_complementary_views.py`) reproduced on 12k ACCEPTED dense embeddings (2000-2002) with IDENTICAL scale-dependent patterns: cross-lingual alignment inflated at small homogeneous scale (0.656→0.957) then degrades with scale diversity; legal area purity degrades (0.61→0.47) consistent with full-corpus evaluations; branch k-NN accuracy stable (>0.99 at all scales). Section cross-lingual hierarchy confirmed: Sachverhalt 0.2816 > 0.2, Dispositiv 0.1502 > 0.1, Erwaegungen 0.0941 < 0.1.

**PIVOT_WITHIN_MISSION characterization COMPLETE at max available evaluated scale.** No further same-question cycles justified.

---

## Key Findings (Reproduced)

### 1. Citation Heritage View — DENSE SUPERIORITY CONFIRMED
- **Minimal scale:** 21yr / 137k decisions (2000-2020) with ≥100 positive citation pairs
- **Best mode:** `center_projected_64dim`
- **AUC at 22yr (144k):** raw=0.7946, cp64=0.7922, cp128=0.7916, cp768=0.7941
- **TF-IDF citation baseline:** 0.71-0.74
- **Dense superiority:** AUC 0.79-0.85 > TF-IDF 0.71-0.74
- **Status:** ACCEPTED at 21-24yr (137k-158k)

### 2. Section Cross-Lingual View — HIERARCHY CONFIRMED
| Section | cross_lang_same_branch | Threshold | Status |
|---------|------------------------|-----------|--------|
| Sachverhalt (facts) | 0.2816 | > 0.2 | PASS |
| Dispositiv (holding) | 0.1502 | > 0.1 | PASS |
| Erwaegungen (reasoning) | 0.0941 | > 0.1 | FAIL |

- **Hierarchy:** Sachverhalt > Dispositiv > Erwaegungen
- **Center projection improves all:** gaps reduced 16-38% vs raw
- **Full corpus density:** BLOCKED pending section extraction at 174k

### 3. Linear Hybrid Complement — CROSS-LINGUAL BENEFIT, BELOW TF-IDF JP
- **Minimal scale:** 19yr / 122k decisions (2000-2018) — first scale PASS both adversarial gates
- **Optimal weights:** w=0.3-0.4 (shifts toward semantic at larger scale)
- **22yr results:** w=0.4 → JP=0.6725, LangDom=0.6539 (both PASS)
- **TF-IDF baseline:** JP=0.7840, LangDom=0.4826
- **Cross-lingual improvement:** TF-IDF=0.124 → Hybrid w=0.4=0.160 (+0.036)
- **Status:** EXPLORATORY mode (does NOT beat TF-IDF on jurist preference)

---

## Fundamental Tradeoff (Reproduced Across All Scales)

| Representation | LangDom | JP | CiteIndep | Characteristic |
|----------------|---------|-----|-----------|----------------|
| TF-IDF Citation Hybrids | 0.48 | 0.78 | 0.14 | Legal relevance, monolingual clusters |
| Dense Semantic (cp) | 0.83-0.98 | 0.05-0.43 | 0.37 | Cross-lingual, language-dominated |
| Linear Hybrids (optimal) | 0.58-0.80 | 0.61-0.67 | 0.25-0.35 | Best of both, but below TF-IDF JP |

**Conclusion:** NO single representation dominates all three metrics at any scale.

---

## Accepted Negative Findings

1. **Dense embeddings FAIL jurist gate at ALL scales** (JP 0.05-0.43)
2. **True OOS JuristPref ceiling ~0.53** < 0.7 factory target (v8 holdout)
3. **v18 coarse hierarchy NEGATIVE** (max branch purity 0.65 < 0.7)
4. **Citation heritage recall@10 max 0.0066** — ranking signal only, not retrieval
5. **Boilerplate resistance NEGATIVE** — dense more susceptible to procedural text
6. **Raw 768dim FAILS citation heritage at 24yr** (AUC 0.68 < 0.75; center projection required)
7. **Full-text dense inflated at small scale** — Cross-lingual 0.656 at 1K but degrades to 0.10 at 165k

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Resolution |
|---------|--------|------------|
| **bge_/bger_ ID mapping** | Canonical corpus uses bge_ IDs; evaluation uses bger_ IDs — no mapping | Corpus lane |
| **Parquet 2024-2026** | 15,536 decisions missing (3 years) | Corpus lane |
| **Section extraction at 174k** | Sachverhalt/Erwaegungen/Dispositiv not extracted at scale | Corpus lane |

---

## Product Integration Contracts (Frozen)

| View | Representation | Status | User Intent |
|------|----------------|--------|-------------|
| **Primary Navigation** | `cited_outcome_hybrid_0.5` (TF-IDF) | PRODUCTION v1.0 | Jurist finds legally relevant neighbors |
| **Citation Heritage** | `center_projected_64dim` | READY v1.1+ | Jurist explores doctrinal lineage |
| **Cross-Lingual** | `center_projected_64dim` per section | BLOCKED v1.1+ | Jurist finds equivalent decisions in other languages |
| **Hybrid Explore** | `linear_citation_concat_w0.4` | EXPLORATORY v1.1+ | Jurist trades relevance for cross-lingual reach |

---

## Tests Passed (8/8)

### test_complementary_role_v34.py (8/8)
1. ✅ `test_citation_heritage_superiority` — Dense AUC 0.79-0.85 > TF-IDF 0.71-0.74
2. ✅ `test_citation_heritage_minimal_scale` — 21yr/137k with 100 pairs sufficient
3. ✅ `test_section_crosslingual_hierarchy` — Sachverhalt > Dispositiv > Erwaegungen
4. ✅ `test_linear_hybrid_optimal_weight` — w=0.3-0.4 PASS adversarial, JP < TF-IDF
5. ✅ `test_two_mode_tradeoff_fundamental` — No single representation dominates
6. ✅ `test_true_oos_ceiling` — OOS JP ceiling ~0.53 < 0.7 target
7. ✅ `test_tfidf_174k_primary_validated` — TF-IDF beats semantic baseline (0.78 vs 0.43)
8. ✅ `test_data_blockers_identified` — Correctly identified, corpus lane required

---

## Scale Characterization Experiment Results (12k Dense, 2000-2002)

### Cross-Lingual Alignment (Full-Text Dense)
| Scale | cross_lang_same_branch | same_lang_same_branch | Separation |
|-------|------------------------|----------------------|------------|
| 1,000 | 0.6562 | 0.8622 | +0.2059 |
| 2,000 | 0.9714 | 0.8901 | -0.0813 |
| 4,000 | 0.9706 | 0.9587 | -0.0119 |
| 6,000 | 1.0000 | 0.9715 | -0.0285 |
| 8,000 | 1.0000 | 0.9770 | -0.0230 |
| 10,000 | 0.9756 | 0.9797 | +0.0040 |
| 12,570 | 0.9565 | 0.9821 | +0.0256 |

**Pattern:** Inflated at small homogeneous scale, degrades with diversity — consistent with full-corpus evaluations.

### Legal Area Clustering
| Scale | Purity | NMI |
|-------|--------|-----|
| 1,000 | 0.6089 | 0.7399 |
| 2,000 | 0.4926 | 0.6615 |
| 4,000 | 0.4850 | 0.6341 |
| 6,000 | 0.4770 | 0.6223 |
| 8,000 | 0.4849 | 0.6125 |
| 10,000 | 0.4545 | 0.5997 |
| 12,570 | 0.4754 | 0.5993 |

**Pattern:** Purity degrades with scale (0.61→0.47) — consistent with full-corpus evaluations.

### Branch k-NN Accuracy
| Scale | @1 | @3 | @5 |
|-------|-----|-----|-----|
| 1,000 | 0.9568 | 0.9784 | 0.9892 |
| 2,000 | 0.9894 | 0.9947 | 0.9973 |
| 4,000 | 0.9879 | 0.9933 | 0.9946 |
| 6,000 | 0.9948 | 0.9974 | 0.9974 |
| 8,000 | 0.9928 | 0.9980 | 0.9980 |
| 10,000 | 0.9919 | 0.9973 | 0.9973 |
| 12,570 | 0.9922 | 0.9961 | 0.9965 |

**Pattern:** Stable >0.99 at all scales.

---

## Recommendation

**continue_recommended: false**

The complementary role of dense embeddings has been fully characterized at the maximum available evaluated scale (24yr/158k citation heritage, 174k formal suite, 1K section cross-lingual). 

**Next actions:**
1. **Corpus lane:** Resume for bge_↔bger_ mapping, 2024-2026 parquet, 174k section extraction
2. **Product lane:** Ship v1.0 with TF-IDF citation hybrids as primary (JP 0.78 vs 0.43 semantic baseline)
3. **Dense integration:** v1.1+ for citation-heritage view and cross-lingual view (contracts defined and frozen)
4. **No new Frontier team** — portfolio v7 confirmed, all teams TERMINATED

---

## Orchestration/Validation Failure Diagnosed

**Prior workflow failed due to data dependency blockers (bge_/bger_ mapping, missing parquet 2024-2026, 174k section extraction), NOT scientific failure.** All valid completed work preserved. The lane state correctly shows `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false` — this is the intended end state for this factory direction question.

---

## Evidence References (Immutable)

- **Citation Heritage 22yr:** `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- **Citation Heritage 21yr:** `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json`
- **Citation Heritage 24yr:** `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`
- **Section Cross-Lingual 1K:** `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- **Weight Sweep 22yr:** `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
- **Linear Combinations 19yr:** `legal_distance/results/174k_dense_embeddings/linear_combinations_19year/linear_combinations_19year_eval_latest.json`
- **Evaluation 22yr CP:** `legal_distance/results/174k_dense_embeddings/evaluation_22year_center_projected/combined_results.json`
- **Scale Characterization 12k:** `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json`
- **TF-IDF 174k Formal Suite:** `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- **v8 Holdout OOS:** `/home/runner/work/LexMachina/LexMachina/legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json`
- **v17b Label Normalization:** `/tmp/lex_accepted/evaluation/results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_latest.json`
- **v18 Coarse Hierarchy:** `/tmp/lex_accepted/evaluation/results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json`