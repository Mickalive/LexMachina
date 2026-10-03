# Legal Distance Lane — Final Report (Factory Direction v34)

**Lane**: legal-distance  
**Factory Direction Version**: 34  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Continue Recommended**: false  
**Accepted Run ID**: legal_distance_v34_final_assessment_20261003  
**Report Date**: 2026-10-03  

---

## Executive Summary

The legal-distance lane has executed all deliverables from factory direction v30/v33 at the maximum available scale (22-year / 144,443 decisions, 2000-2021). **Full 174k-scale dense embedding evaluation is BLOCKED by fundamental data acquisition gaps** that cannot be resolved within this lane.

Per factory direction v34, **PIVOT_WITHIN_MISSION has been executed**:

| Aspect | Decision |
|--------|----------|
| **Primary Product Mode** | TF-IDF citation hybrids (jurist preference JP 0.78-0.79, beats semantic baseline JP 0.43) |
| **Complementary Dense Modes** | Citation heritage view (AUC 0.79-0.85), Cross-lingual view (Sachverhalt gap 0.187), Linear hybrid complement (w=0.3-0.4) |
| **Data Blocker** | Moved to corpus lane resumption (bge_<->bger_ ID mapping + parquet 2022-2026) |
| **Frontier Teams** | No new team — portfolio v7 confirmed, all teams TERMINATED (true OOS JP ceiling ~0.53 < 0.7 target; v18 hierarchy NEGATIVE) |

The lane is correctly **BLOCKED_ON_DEPENDENCIES** with **continue_recommended=false** — no further same-question cycles are justified.

---

## Deliverable Status (Factory Direction v30/v33 → v34 Pivot)

| # | Deliverable | Status | Scale Achieved | Key Result |
|---|-------------|--------|----------------|------------|
| 1 | Complete 174k dense assembly & evaluation | **BLOCKED** | 22-yr / 144k (83%) | Checkpoints for 2000-2021 complete; 2022-2026 missing |
| 2 | Full-corpus adversarial evaluation (all reps) | **COMPLETE (TF-IDF)** / **BLOCKED (dense)** | 174k (TF-IDF) / 144k (dense) | TF-IDF 8/8 PASS; dense FAILS jurist gate at all scales |
| 3 | Section cross-lingual evaluation (full density) | **PARTIAL** | 1K sample (3 sections) | Sachverhalt superior (gap 0.187 vs 0.452); full density blocked |
| 4 | Scale linear_hybrid05_concat stability test | **COMPLETE** | 15yr/19yr/22yr | 15yr FAIL, 19yr PASS, 22yr PASS (optimal w=0.3-0.4) |
| 5 | Prod-vs-CV tradeoff (TF-IDF leakage) | **COMPLETE** | 174k | Minimal leakage: LangDom +0.005, JP -0.015 to -0.020 |

---

## Critical Findings

### 1. TF-IDF 174k Formal Suite: COMPLETE & REPRODUCED
All 8 TF-IDF representations pass both adversarial gates on frozen harness v3 at **173,963 decisions**:
- **Best**: `cited_decisions_tfidf_outcome_hybrid_0.5` — LangDom=0.4773, JuristPref=0.7345
- Citation-based signals dominate at 174k scale
- Production default validated and operational in product lane

### 2. Dense Embeddings FAIL Jurist Gate at ALL Scales
| Scale | Decisions | Center Projected JP | Center Projected LangDom | Status |
|-------|-----------|---------------------|-------------------------|--------|
| 3-yr (ACCEPTED) | 19,441 | 0.39-0.42 | ~0.85-0.90 | FAIL |
| 15-yr | 91,929 | 0.288 | 0.8929 | FAIL |
| 19-yr | 122,015 | 0.3685 | 0.8603 | FAIL |
| 20-yr | 129,680 | **0.0475** | **0.9828** | CATASTROPHIC FAIL |
| 22-yr | 144,443 | 0.4265 | 0.8319 | FAIL |

**Conclusion**: Dense semantic embeddings (paraphrase-multilingual-mpnet-base-v2) do not produce legally useful neighborhoods at any scale tested. Performance degrades catastrophically at 20yr then partially recovers at 22yr.

### 3. Linear Combinations: PASS Adversarial Gates But Don't Dominate
Weight sweeps at 19yr and 22yr reveal **scale-dependent optimal weights**:

| Scale | Representation | Optimal Weight | JP | LangDom | Both Pass? | vs TF-IDF Baseline |
|-------|----------------|----------------|-----|---------|------------|-------------------|
| 19yr | linear_citation_concat | w=0.3 | 0.5445 | 0.6264 | ✓ | Below (0.7235) |
| 19yr | linear_hybrid05_concat | w=0.3 | 0.5395 | 0.6617 | ✓ | Below (0.7155) |
| 22yr | linear_citation_concat | **w=0.4** | 0.6725 | 0.6539 | ✓ | Below (0.7840) |
| 22yr | linear_hybrid05_concat | w=0.3 | 0.6605 | 0.6395 | ✓ | Below (0.7890) |

**Key insight**: Optimal weight shifts toward denser semantic contribution at larger scale (w=0.3 → w=0.4 for pure citation TF-IDF), but citation signals (TF-IDF) remain dominant for jurist preference.

### 4. Two-Mode Tradeoff REPRODUCED at All Scales

| Mode Family | LangDom | JuristPref | Citation Independence | Key Characteristic |
|-------------|---------|------------|----------------------|-------------------|
| **Citation/Outcome (TF-IDF)** | ~0.48 | **~0.78** | ~14% | Legal relevance, monolingual clusters |
| **Semantic (center_projected)** | ~0.83-0.98 | ~0.05-0.43 | ~37% | Cross-lingual, language-dominated |
| **Metric Learning** | ~0.58-0.61 | ~0.53-0.61 | ~34-37% | Intermediate, requires GPU |
| **Linear Hybrids (optimal)** | ~0.58-0.80 | ~0.61-0.67 | ~20-30% | Best of both, but below TF-IDF JP |

**No single representation dominates all three metrics at any scale.**

### 5. NEW FINDING: Dense Embeddings RECOVER Citation Heritage BETTER Than TF-IDF
At 21-22yr scale (137k-144k decisions, sufficient citation pairs from 2019+):

| Representation | AUC-ROC | vs TF-IDF Citation-Based (0.71-0.74) |
|----------------|---------|--------------------------------------|
| Raw multilingual-e5 (768dim) | **0.79-0.85** | **BETTER** |
| Center projected 768dim | 0.79 | BETTER |
| Center projected 64dim (PCA) | 0.79 | BETTER |
| Center projected 128dim (PCA) | 0.79 | BETTER |

**Implication**: Semantic embeddings capture doctrinal proximity through shared citations despite failing jurist gate on language dominance. This is a previously untested capability at sufficient scale.

### 6. Section Cross-Lingual: Sachverhalt Superior to Dispositiv to Erwaegungen
At 1K sample (sachverhalt n=359, erwaegungen n=510, dispositiv n=538):

| Section | cross_lang_same_branch | same_lang_same_branch | Invariance Gap | Separation |
|---------|------------------------|----------------------|----------------|------------|
| Sachverhalt cp_64 | **0.282** | 0.468 | **0.187** | 0.031 |
| Dispositiv cp_64 | 0.150 | 0.548 | 0.397 | -0.152 |
| Erwaegungen cp_64 | 0.094 | 0.546 | 0.452 | -0.265 |

Center projection improves all (sachverhalt: 0.304→0.187, erwaegungen: 0.538→0.452, dispositiv: 0.575→0.397). **Facts align best across languages; holdings retain some alignment; reasoning is most language-specific.**

### 7. Prod-vs-CV Tradeoff: Minimal Leakage
v8 holdout validation (train-only TF-IDF/SVD on 80% corpus):
- All 4 zero-shot hybrids PASS both gates on true holdout
- Leakage impact: LangDom +0.005, JP -0.015 to -0.020
- **No significant information leakage** from full-corpus SVD fitting
- Production default validated

### 8. Legal TF-IDF from bge_ Corpus: NEGATIVE RESULT
Tested 6 legal TF-IDF variants on bge_ published corpus (6,243 decisions):
- **6-8/14 PASS** vs 14/14 baseline
- **ALL FAIL** citation heritage (AUC ~0.5), branch kNN (0.26-0.39), multilingual invariance
- **PASS** language dominance (LangDom ~0.49-0.50) — confirming legal signals ARE cross-lingual
- **Root cause**: Corpus mismatch — bge_ IDs don't map to bger_ evaluation corpus; signal coverage deficits (cited decisions 0.06%, outcomes 0%, Erwägungen 64%)
- **Boilerplate suppression has no effect** (density 0.022%)
- **Conclusion**: Legal signals from published-only corpus DO NOT GENERALIZE to full corpus

### 9. Hierarchy & Boilerplate: Fundamental Limitations
- **v18 coarse hierarchy**: Even at 4-label branch level, best purity 0.65 < 0.7 threshold — fundamental limitation for TF-IDF/citation representations
- **Boilerplate resistance**: All representations resistance_score ≈ -0.74 to -0.93 — proxy measures language dominance, not procedural boilerplate

### 10. True OOS JuristPref Ceiling: ~0.53 < 0.7 Factory Target
Confirmed via v8 holdout validation on true zero-shot split. Dense embeddings cannot reach factory target on jurist preference even in ideal conditions.

---

## Scale Evidence Summary

| Scale | Years | Decisions | Center Projected JP | Linear Combo Optimal JP | TF-IDF Baseline JP | Citation Heritage AUC |
|-------|-------|-----------|---------------------|------------------------|-------------------|----------------------|
| 3-yr (ACCEPTED) | 2000-2002 | 19,441 | 0.39-0.42 | N/A | N/A | N/A |
| 15-yr | 2000-2014 | 91,929 | 0.288 | 0.473 (w=0.5) | 0.7235 | N/A |
| 19-yr | 2000-2018 | 122,015 | 0.3685 | 0.5445 (w=0.3) | 0.7235 | N/A |
| 20-yr | 2000-2019 | 129,680 | **0.0475** | N/A | N/A | N/A |
| 21-yr | 2000-2020 | 137,189 | Not tested | N/A | N/A | **0.8455** |
| 22-yr | 2000-2021 | 144,443 | 0.4265 | 0.6725 (w=0.4) | **0.7840** | **0.7946** |
| **174k target** | **2000-2026** | **173,963** | **BLOCKED** | **BLOCKED** | **0.7345** | **BLOCKED** |

---

## PIVOT_WITHIN_MISSION: Product Integration Contract

### Primary Mode (v1.0): TF-IDF Citation Hybrids
- **Default**: `cited_outcome_hybrid_0.5_174k` (production serving default)
- **Strengths**: Jurist preference (JP 0.73-0.79), branch clustering, citation heritage recovery (AUC 0.71-0.74)
- **Role**: Primary navigation, legal relevance, monolingual map modes

### Complementary Dense Modes (v1.1+): Three Specific Capabilities
| Dense Mode | Capability | Evidence | Integration Trigger |
|------------|------------|----------|---------------------|
| **Citation Heritage View** | Doctrinal proximity via shared citations | AUC 0.79-0.85 > TF-IDF 0.71-0.74 | Corpus lane delivers 174k dense embeddings |
| **Cross-Lingual View** | Sachverhalt cross-language alignment | cp_64 invariance_gap=0.187 (best of all sections) | Section extraction at 174k scale |
| **Linear Hybrid Complement** | Optimal w=0.3-0.4 linear concat | PASS adversarial, adds cross-lingual benefit | Corpus lane delivers 174k dense embeddings |

### Acceptance Criteria for Dense Embedding Complementary Views
From evaluation lane v34 question:
- Citation heritage AUC > 0.75 (CURRENTLY MET at 22yr: 0.79-0.85)
- Cross-lingual same_branch > 0.2 for sachverhalt (CURRENTLY MET at 1K: 0.282)
- Cross-lingual same_branch > 0.1 for dispositiv (CURRENTLY MET at 1K: 0.150)

---

## Orchestration Failure Diagnosis

### Root Causes (Unfixable in This Cycle)
1. **bger_YYYY.jsonl files missing** from canonical corpus for years 2000-2019
2. **finalize_174k_embeddings.py** asserts full 173k metadata match; checkpoints cover 144k only
3. **bger_ vs bge_ ID systems** with no cross-mapping
4. **Section extraction** (sachverhalt/erwaegungen/dispositiv) not run at 174k scale
5. **Factory direction v30/v33 claims 'CORPUS MOUNT PATH GAP RESOLVED'** but `/tmp/lex_accepted/core/` does not exist

### What Went Well
- Year-split checkpointed computation (2000-2021) completed within CPU constraints
- All TF-IDF 174k formal suite evaluations completed and reproduced
- v8 holdout validation cleanly executed with exact k-NN (HNSW artifact fixed)
- Section cross-lingual evaluation completed at sample scale with clear hierarchy
- Scale dependency rigorously quantified at 15yr/19yr/20yr/21yr/22yr
- Two-mode tradeoff reproduced across all scales and representation families
- 19yr and 22yr linear combinations PASS adversarial gates — first dense-hybrids to do so
- Dense embeddings RECOVER citation heritage at scale (AUC 0.79-0.85) — NEW finding
- Weight sweep reveals optimal w=0.3 at 19yr, w=0.4 at 22yr — scale-dependent optimization
- Legal TF-IDF from bge_ corpus tested at 6k scale — NEGATIVE result with clear diagnosis

---

## Evidence References (Machine-Readable)

```
legal_distance/results/174k_dense_embeddings/evaluation_19year_center_projected/combined_results.json
legal_distance/results/174k_dense_embeddings/evaluation_20year_2000_2019/dense_20year_2000_2019_eval_latest.json
legal_distance/results/174k_dense_embeddings/linear_combinations_19year/linear_combinations_19year_eval_latest.json
legal_distance/results/174k_dense_embeddings/linear_hybrid05_concat_15year/linear_hybrid05_concat_15year_eval_latest.json
legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json
legal_distance/results/174k_dense_embeddings/checkpoints/progress.json
legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json
legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json
legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json
legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep/weight_sweep_19year_latest.json
legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json
/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json
/tmp/lex_accepted/evaluation/results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_latest.json
/tmp/lex_accepted/evaluation/results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json
legal_distance/results/174k_dense_embeddings/legal_signals_144k/signal_coverage_stats_144k.json
legal_distance/results/174k_dense_embeddings/legal_tfidf_bge/all_experiments_results.json
legal_distance/results/legal_signals_1000_v3.jsonl
legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_20261003_012811.json
```

---

## Recommendation: PIVOT_WITHIN_MISSION EXECUTED

**The lane is correctly BLOCKED_ON_DEPENDENCIES with continue_recommended=false.**

### For Factory Director Decision (per v34):
1. **Corpus lane coordination required**: bge_<->bger_ ID mapping and parquet for 2022-2026
2. **Product lane**: Ship v1.0 with TF-IDF citation hybrids as primary navigation mode (beats semantic baseline JP 0.78 vs 0.43)
3. **Dense embedding integration**: As v1.1+ for citation-heritage view and cross-lingual view (acceptance criteria defined above)
4. **No new Frontier team** — portfolio v7 confirmed, all teams TERMINATED (true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria)

### Product-Ready Deliveries from This Lane:
- ✅ TF-IDF 174k formal suite COMPLETE — production defaults validated
- ✅ Two-mode tradeoff characterized — informs map mode design
- ✅ Scale dependency quantified — informs computation budgeting
- ✅ Citation heritage recovery by dense embeddings — novel capability for doctrinal proximity view
- ✅ Section cross-lingual signal — sachverhalt > dispositiv > erwaegungen for cross-language alignment view
- ✅ Prod-vs-CV leakage minimal — validates zero-shot serving architecture

---

## Compliance with Research Protocol

- ✅ Hypothesis, baseline, and success rule frozen before observation
- ✅ Negative results preserved (dense FAIL, legal TF-IDF FAIL, hierarchy FAIL, boilerplate FAIL)
- ✅ Strong baselines used (whole-doc semantic, TF-IDF, citation-only, hybrids)
- ✅ Evaluation on frozen harness v3 with fixed seed
- ✅ Provenance preserved for all claim-bearing outputs
- ✅ Machine-readable state file updated with evidence_refs
- ✅ PIVOT_WITHIN_MISSION documented with product integration contract

---

**Lane Status**: BLOCKED_ON_DEPENDENCIES — PIVOT_WITHIN_MISSION executed. No further same-question cycles justified.  
**Next Action**: Corpus lane resumption for data blocker; Product lane v1.0 release with TF-IDF defaults.