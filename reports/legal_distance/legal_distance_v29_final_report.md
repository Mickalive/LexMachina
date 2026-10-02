# Legal Distance Lane — Factory Direction v29 Final Report

**Cycle Status:** BLOCKED_ON_DEPENDENCIES | **Evidence Tier:** REPRODUCED | **Continue Recommended:** FALSE
**Audit Ready:** TRUE | **Timestamp:** 2026-10-02

---

## Executive Summary

All five factory direction v29 deliverables have been addressed at the maximum available scale (22-year / 144,443 decisions on bger_ corpus). The fundamental blocker preventing full 174k evaluation on the canonical bge_ corpus remains unresolved: **dense embeddings were computed on the wrong corpus (bger_ unpublished decisions) with no ID mapping to the evaluation corpus (bge_ published BGE volumes)**. No further same-question discriminating experiments are justified. **PIVOT_WITHIN_MISSION REQUIRED.**

---

## Factory Direction v29 Deliverables — Status

| # | Deliverable | Status | Scale Achieved | Key Result |
|---|-------------|--------|----------------|------------|
| 1 | 174k dense embedding assembly & evaluation | **BLOCKED** | 144k/174k (83%) on bger_ | Wrong corpus (bger_ vs bge_), no ID mapping, 2022-2026 missing |
| 2 | Full-corpus adversarial evaluation (all reps) | **COMPLETE** (TF-IDF) | 173,963 decisions (bge_) | 8/8 TF-IDF reps PASS both gates. Best: cited_decisions_tfidf_outcome_hybrid_0.5 (LangDom=0.477, JP=0.735) |
| 3 | Section cross-lingual at full density | **BLOCKED** | 1K sample (bger_) | Sachverhalt superior (gap 0.187) vs Erwaegungen (gap 0.452). Center projection helps both. |
| 4 | linear_hybrid05_concat scale stability | **COMPLETE** | 15yr/19yr/22yr (bger_) | Scale dependency confirmed: 15yr FAIL (JP=0.473), 19yr PASS (JP=0.540), 22yr PASS (JP=0.661). Below TF-IDF baseline. |
| 5 | Prod vs CV tradeoff (TF-IDF SVD leakage) | **COMPLETE** | 174k (bge_) | v8 holdout: leakage minimal (LangDom +0.005, JP -0.015 to -0.020). Production default validated. |

---

## Critical Findings (REPRODUCED Tier)

### 1. TF-IDF 174k Formal Suite — COMPLETE ✅
- All 8 TF-IDF representations PASS both adversarial gates on frozen harness v3 at 173,963 decisions
- **Production default validated**: `cited_decisions_tfidf_outcome_hybrid_0.5` (LangDom=0.4773, JuristPref=0.7345)
- Citation-based signals dominate at 174k scale; text-based signals fail citation heritage

### 2. Dense Embedding Blocker — FUNDAMENTAL ❌
- Checkpoints cover 144,443/173,963 decisions (83%, years 2000-2021) on **bger_ corpus** (unpublished)
- Evaluation corpus uses **bge_ IDs** (published BGE volumes) — **no mapping exists**
- Parquet `/tmp/bger.parquet` missing for 2022-2026 (29,520 decisions)
- `finalize_174k_embeddings.py` FAILS metadata order verification
- **Root cause**: Dense embeddings computed on wrong corpus; corpus-lane coordination required

### 3. Center Projected FAILS Jurist Gate at ALL Scales ❌
| Scale | Decisions | LangDom | JP | Status |
|-------|-----------|---------|-----|--------|
| 3-yr (ACCEPTED) | 19,441 | 0.83-0.86 | 0.39-0.42 | FAIL |
| 15-yr | 91,929 | 0.893 | 0.288 | FAIL |
| 19-yr | 122,015 | 0.860 | 0.369 | FAIL |
| 20-yr | 129,680 | 0.983 | 0.048 | **CATASTROPHIC** |
| 22-yr | 144,443 | 0.832 | 0.427 | FAIL |

**Dense semantic embeddings DO NOT PASS jurist gate at any scale tested.** Performance degrades catastrophically at 20yr then partially recovers at 22yr.

### 4. Linear Combinations Improve But Don't Dominate ⚠️
- `linear_citation_concat` (cp64 + cited_tfidf): 22yr w=0.4 → JP=0.6725, LangDom=0.6539 (both PASS)
- `linear_hybrid05_concat` (cp64 + hybrid_0.5): 22yr w=0.3 → JP=0.6605, LangDom=0.6395 (both PASS)
- **Both PASS adversarial gates at 22yr but remain BELOW TF-IDF baseline** (JP=0.784/0.789)
- Scale dependency: 15yr FAIL → 19yr PASS → 22yr PASS
- **Optimal weight shifts toward TF-IDF dominance** (w=0.3-0.4 dense / 0.6-0.7 TF-IDF) at larger scale
- Citation signals dominate jurist preference; semantic signals add cross-lingual benefit but dilute legal relevance

### 5. Two-Mode Tradeoff REPRODUCED at All Scales 📊
| Mode | LangDom | JP | CiteIndep |
|------|---------|-----|-----------|
| Citation/Outcome (TF-IDF hybrids) | ~0.48 | ~0.78 | ~14% |
| Semantic (center_projected) | ~0.83-0.98 | ~0.05-0.43 | ~37% |
| Metric Learning | ~0.58-0.61 | ~0.53-0.61 | ~34-37% |
| Linear Hybrids (optimal) | ~0.64-0.65 | ~0.66-0.67 | ~25-30% |

**NO single representation dominates all three metrics at any scale.**

### 6. Dense Embeddings RECOVER Citation Heritage at Scale 🎯 **NEW FINDING**
- Multilingual-e5 embeddings recover citation heritage at scale: **AUC 0.79-0.85** (21-22yr, 137k-144k decisions)
- **BETTER than TF-IDF citation-based** (AUC 0.71-0.74) and much better than TF-IDF text-based (AUC 0.50-0.63)
- Center projection and PCA (64/128-dim) preserve this capability (AUC 0.79-0.82)
- Previously untested at sufficient scale due to citation pair distribution requiring recent years (2019+)
- Semantic embeddings capture doctrinal proximity through shared citations despite failing jurist gate on language dominance

### 7. Legal TF-IDF from bge_ Corpus — NEGATIVE RESULT ❌
- Tested on published BGE volumes (6,243 decisions, 2000-2021)
- **FAILS adversarial suite** (6-8/14 PASS vs 14/14 baseline)
- **ALL variants FAIL** citation heritage (AUC ~0.5), branch kNN (0.26-0.39), multilingual invariance, cross-language pairs
- They PASS language dominance (LangDom~0.49-0.50) — confirming legal signals are cross-lingual
- **Root cause**: Corpus mismatch (bge_ IDs don't map to bger_ evaluation) + signal coverage deficits:
  - Cited decisions: 0.06% density
  - Outcomes: 0% density
  - Erwägungen: 64% coverage
  - Boilerplate suppression: no effect (density 0.022%)
- **Legal signals from published-only corpus DO NOT GENERALIZE to full corpus**

### 8. Prod vs CV Tradeoff Validated — Minimal Leakage ✅
- v8 holdout validation (train-only TF-IDF/SVD on 80% corpus): all 4 zero-shot hybrids PASS both gates on true holdout
- Leakage impact minimal: LangDom +0.005, JP -0.015 to -0.020
- **No significant information leakage from full-corpus SVD fitting**
- Production default (`cited_decisions_tfidf_outcome_hybrid_0.5`) validated

### 9. Section Cross-Lingual: Sachverhalt Superior 📝
- Sachverhalt (facts, n=359): cross_lang_same_branch=0.282, invariance_gap=0.187
- Erwaegungen (reasoning, n=510): cross_lang_same_branch=0.094, invariance_gap=0.452
- Center projection improves both (sachverhalt gap 0.304→0.187, erwaegungen 0.538→0.452)
- Completed at 1K sample; full density blocked pending section extraction at 174k scale

### 10. v17b Label Normalization — Regime Dependent 📊
- 1000-scale: 15-25% purity gain REPRODUCED (4 seeds)
- 174k fine-grained (213→111 labels): purity ratios 4-10x but NMI decreases on normalized
- **Different regime at scale — requires separate validation**

### 11. v18 Coarse Hierarchy — NEGATIVE ❌
- Even at 4-label branch level: best purity 0.65 (linear_citation_concat) < 0.7 threshold
- **Fundamental hierarchy limitation confirmed** for TF-IDF/citation representations

### 12. Boilerplate Resistance — NEGATIVE All Reps ❌
- All representations resistance_score ≈ -0.74 to -0.93
- Proxy measures language dominance/cross-lingual alignment failure, not procedural boilerplate
- Consistent across TF-IDF and dense

---

## Orchestration Failure Diagnosis

### Root Causes
1. **bger_YYYY.jsonl files missing** from canonical corpus for years 2000-2019; only 2020-2024 in raw acquisition
2. **finalize_174k_embeddings.py asserts full 173k metadata match**; checkpoints cover 144k (2000-2021) but 2021 flagged as failed
3. **bger_ (unpublished) vs bge_ (published) ID systems with no cross-mapping**
4. **Section extraction (sachverhalt/erwaegungen/dispositiv) not run at 174k scale**

### What Went Well
- Year-split checkpointed computation (2000-2021) completed within CPU constraints
- All TF-IDF 174k formal suite evaluations completed and reproduced
- v8 holdout validation cleanly executed with exact k-NN (HNSW artifact fixed)
- Section cross-lingual evaluation completed at sample scale with clear result
- Scale dependency rigorously quantified at 15yr/19yr/20yr/21yr/22yr
- Two-mode tradeoff reproduced across all scales and representation families
- 19-year (122k) and 22-year (144k) linear combinations PASS adversarial gates — first dense-hybrids to do so
- Dense embeddings RECOVER citation heritage at scale (AUC 0.79-0.85) — NEW finding at 21-22yr scale
- Weight sweep reveals optimal w=0.3 at 19yr, w=0.4 at 22yr — scale-dependent optimization
- 22-year weight sweep (144k) completed as final discriminating experiment
- Legal TF-IDF from bge_ corpus tested at 6k scale — NEGATIVE result with clear diagnosis (corpus mismatch)

### Unfixable in This Cycle
- Data acquisition is upstream (corpus lane PAUSED at v17 snapshot)
- GPU unavailability prevents BGE/multilingual-e5 finetuning at scale
- No bge_<->bger_ mapping — requires corpus-lane coordination
- Section extraction at 174k requires full corpus text access

---

## Scale Evidence Summary

| Scale | Years | Decisions | Key Metrics | Status |
|-------|-------|-----------|-------------|--------|
| 3-yr ACCEPTED | 2000-2002 | 19,441 | cp_JP=0.39-0.42 FAIL | ACCEPTED post-audit |
| 15-yr | 2000-2014 | 91,929 | cp_JP=0.288, hybrid_JP=0.473 | FAIL both |
| 19-yr | 2000-2018 | 122,015 | cp_JP=0.369, concat_JP=0.647, hybrid_JP=0.637 | Linear PASS; TF-IDF dominates |
| 20-yr | 2000-2019 | 129,680 | cp_768_JP=0.048 (catastrophic) | FAIL |
| 21-yr | 2000-2020 | 137,189 | cite_heritage AUC=0.846 (PASS) | JP not tested |
| 22-yr | 2000-2021 | 144,443 | cp_JP=0.427 FAIL; concat_w04_JP=0.673 PASS; hybrid_w03_JP=0.661 PASS | Linear PASS; cite_heritage AUC=0.795 |
| 174k target | 2000-2026 | 173,963 | **BLOCKED**: 29,520 missing, no parquet, no ID mapping | — |

---

## Evidence References

All evidence preserved in `legal_distance/results/174k_dense_embeddings/` and `/tmp/lex_accepted/evaluation/results/`:

1. `evaluation_19year_center_projected/combined_results.json`
2. `evaluation_20year_2000_2019/dense_20year_2000_2019_eval_latest.json`
3. `linear_combinations_19year/linear_combinations_19year_eval_latest.json`
4. `linear_hybrid05_concat_15year/linear_hybrid05_concat_15year_eval_latest.json`
5. `section_crosslingual_eval/section_crosslingual_eval_latest.json`
6. `checkpoints/progress.json`
7. `v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json`
8. `citation_heritage_eval/citation_heritage_22year_latest.json`
9. `citation_heritage_eval/citation_heritage_21year_latest.json`
10. `linear_combinations_weight_sweep/weight_sweep_19year_latest.json`
11. `linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
12. `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
13. `/tmp/lex_accepted/evaluation/results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_latest.json`
14. `/tmp/lex_accepted/evaluation/results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json`
15. `legal_signals_144k/signal_coverage_stats_144k.json`
16. `legal_tfidf_bge/all_experiments_results.json`

---

## Next Recommendation

**BLOCKED — PIVOT_WITHIN_MISSION REQUIRED**

Dense embedding data acquisition (parquet 2022-2026 or bge_<->bger_ ID mapping) is a fundamental blocker requiring corpus-lane coordination or Frontier team. All 5 factory direction v29 deliverables addressed with maximum available evidence at 22-year scale (144,443 decisions, 2000-2021).

**No further same-question cycles justified.** The Factory Director should define a successor question addressing the corpus alignment blocker, potentially via:
- Frontier team for bge_<->bger_ ID mapping and dense embedding recomputation on canonical corpus
- Corpus lane resumption for 2022-2026 parquet acquisition
- GPU-enabled dense embedding computation on bge_ corpus

---

## State File (Machine-Readable)

See `legal_distance/state/legal-distance.json` for machine-readable state with:
- `lane: "legal-distance"`
- `direction_version: 29`
- `evidence_tier: "REPRODUCED"`
- `cycle_status: "BLOCKED_ON_DEPENDENCIES"`
- `continue_recommended: false`
- `accepted_run_id: "legal_distance_v29_174k_evaluation_final_20261002_legal_tfidf_bge"`
- `audit_ready: true`
- Full `critical_findings`, `orchestration_failure_diagnosis`, `scale_evidence_summary`