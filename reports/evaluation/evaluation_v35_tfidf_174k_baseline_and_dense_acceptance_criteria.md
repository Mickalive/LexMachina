# Evaluation v35: TF-IDF 174k Production Baseline Freeze and Dense Embedding Complementary View Acceptance Criteria

**Lane:** evaluation  
**Direction Version:** 35  
**Run ID:** evaluation_v35_baseline_freeze_20261007  
**Timestamp:** 2026-10-07  
**Evidence Tier:** REPRODUCED (TF-IDF baseline) / ACCEPTED (dense criteria from legal-distance/fractal-map)  
**Cycle Status:** COMPLETE  

---

## Executive Summary

This cycle **freezes the TF-IDF 174k evaluation as the production baseline** and **defines acceptance criteria for dense embedding complementary views** based on ACCEPTED evidence from legal-distance (complementary_role_characterization_v34) and fractal-map (dense_embeddings_integration_contract_v34) lanes.

### Key Decisions

| Decision | Status | Evidence Source |
|----------|--------|-----------------|
| TF-IDF 174k formal suite = PRODUCTION BASELINE | **FROZEN** | legal-distance/evaluation/results/174k/formal_suite (8/8 reps PASS both adversarial gates) |
| Dense citation heritage view | **ACCEPTANCE CRITERIA DEFINED** | AUC > 0.75 (PASSED at 144k: center_projected_64dim AUC 0.7922) |
| Dense cross-lingual Sachverhalt view | **ACCEPTANCE CRITERIA DEFINED** | cross_lang_same_branch > 0.2 (PASSED at 1K: 0.282) |
| Dense cross-lingual Dispositiv view | **ACCEPTANCE CRITERIA DEFINED** | cross_lang_same_branch > 0.1 (PASSED at 1K: 0.150) |
| Dense cross-lingual Erwaegungen view | **REJECTED** | cross_lang_same_branch 0.094 < 0.1 threshold |
| Dense linear hybrid complement view | **ACCEPTANCE CRITERIA DEFINED** | PASS adversarial + cross_lang_same_branch > TF-IDF baseline |

---

## 1. TF-IDF 174k Production Baseline — FROZEN

### 1.1 Formal Suite Results (8/8 Representations PASS Both Adversarial Gates)

| Representation | Adversarial Language Dominance | Jurist Pairwise Preference | Both Pass | JP Rate |
|----------------|--------------------------------|----------------------------|-----------|---------|
| cited_decisions_tfidf | PASS (0.479) | PASS | ✓ | 0.714 |
| outcome_tfidf | PASS (0.502) | PASS | ✓ | 0.655 |
| regeste_tfidf | PASS (0.485) | PASS | ✓ | 0.632 |
| full_text_tfidf_light | PASS (0.485) | PASS | ✓ | 0.708 |
| **cited_decisions_tfidf_outcome_hybrid_0.5** | **PASS (0.477)** | **PASS** | **✓** | **0.735** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | PASS (0.478) | PASS | ✓ | 0.728 |
| (2 additional modes) | PASS | PASS | ✓ | 0.63-0.73 |

**Source:** `/tmp/lex_accepted/legal-distance/evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`

### 1.2 Production Baseline Selection

**DEFAULT MAP MODE:** `cited_decisions_tfidf_outcome_hybrid_0.5_174k`  
**Rationale:** Highest jurist preference (0.735) among modes passing both adversarial gates at full 174k scale (173,963 decisions).

**Product Integration Status:** OPERATIONAL at 174k
- 16/16 scale simulation tests PASS
- 50+ endpoints
- 95.7% section coverage
- WebGL pipeline <3s
- Audit gate CYCLE_37073590337 PASSED (safe_to_integrate=true)

### 1.3 Baseline Metrics Frozen for Regression Testing

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Jurist Preference (JP) | 0.735 | > 0.5 | PASS |
| Language Dominance | 0.477 | < 0.85 | PASS |
| Citation Heritage AUC (TF-IDF citation-based) | 0.71-0.74 | > 0.65 | PASS |
| Cross-language Recall@10 | ~0.14 | > 0.2 (target) | FAIL (known limitation) |
| Boilerplate Resistance | -0.83 | > 0 (target) | FAIL (known limitation) |
| Hierarchy Coherence NMI | ~0.03 | > 0.3 (target) | FAIL (known limitation) |

**Note:** The TF-IDF baseline has known weaknesses in cross-lingual retrieval, boilerplate resistance, and hierarchy coherence — precisely the views where dense embeddings are designated as COMPLEMENTARY.

---

## 2. Dense Embedding Complementary Views — Acceptance Criteria

Based on ACCEPTED evidence from:
- **legal-distance:** `complementary_role_characterization_v34.json` (REPRODUCED at 144k/22yr)
- **fractal-map:** `dense_embeddings_integration_contract_v34.json` (FROZEN contract)

### 2.1 View 1: Citation Heritage (Doctrinal Proximity via Shared Citations)

| Criterion | Value | Evidence | Status |
|-----------|-------|----------|--------|
| **Acceptance Threshold** | AUC > 0.75 | Factory target from integration contract | DEFINED |
| **Best Dense Mode** | center_projected_64dim | Minimal sufficient representation | DEFINED |
| **Evidence at 144k (22yr)** | AUC 0.7922 | legal-distance citation_heritage_eval | **PASSED** |
| **TF-IDF Citation Baseline** | AUC 0.71-0.74 | legal-distance formal suite | BASELINE |
| **TF-IDF Text Baseline** | AUC 0.50-0.63 | legal-distance formal suite | FAILS |
| **Minimal Sufficient Scale** | 130k decisions (21yr) | legal-distance scale dependency | VALIDATED |
| **Required Dense Modes** | cp64, cp128, cp768 | Integration contract | SPECIFIED |

**Product Integration:** Separate map mode `citation_heritage_view`  
**Status:** READY at 144k checkpoint; BLOCKED at 174k pending corpus lane (BGE/bger ID mapping + parquet 2022-2026)

### 2.2 View 2: Cross-Lingual Sachverhalt (Legally Relevant Facts)

| Criterion | Value | Evidence | Status |
|-----------|-------|----------|--------|
| **Acceptance Threshold** | cross_lang_same_branch > 0.20 | Factory target from integration contract | DEFINED |
| **Best Dense Mode** | center_projected_64dim per section | Section-specific embeddings | DEFINED |
| **Evidence at 1K Sample** | 0.282 (gap 0.187, 38% improvement) | legal-distance section cross-lingual | **PASSED** |
| **Evidence at 144k (22yr)** | 0.2816 | fractal-map 144k checkpoint validation | **PASSED** |
| **Hierarchy Position** | #1 (Sachverhalt > Dispositiv > Erwaegungen) | Reproduced across scales | CONFIRMED |
| **Full Corpus Density** | BLOCKED | Section extraction at 174k required | BLOCKED |

**Product Integration:** Separate map mode `cross_lingual_sachverhalt_view`  
**Status:** SAMPLE ONLY — BLOCKED pending section extraction at 174k

### 2.3 View 3: Cross-Lingual Dispositiv (Holding/Outcome)

| Criterion | Value | Evidence | Status |
|-----------|-------|----------|--------|
| **Acceptance Threshold** | cross_lang_same_branch > 0.10 | Factory target from integration contract | DEFINED |
| **Best Dense Mode** | center_projected_64dim per section | Section-specific embeddings | DEFINED |
| **Evidence at 1K Sample** | 0.150 (gap 0.397, 31% improvement) | legal-distance section cross-lingual | **PASSED** |
| **Evidence at 144k (22yr)** | 0.1502 | fractal-map 144k checkpoint validation | **PASSED** |
| **Hierarchy Position** | #2 (Sachverhalt > Dispositiv > Erwaegungen) | Reproduced across scales | CONFIRMED |
| **Full Corpus Density** | BLOCKED | Section extraction at 174k required | BLOCKED |

**Product Integration:** Separate map mode `cross_lingual_dispositiv_view`  
**Status:** SAMPLE ONLY — BLOCKED pending section extraction at 174k

### 2.4 View 4: Cross-Lingual Erwaegungen (Reasoning) — REJECTED

| Criterion | Value | Evidence | Status |
|-----------|-------|----------|--------|
| **Acceptance Threshold** | cross_lang_same_branch > 0.10 | Factory target | DEFINED |
| **Evidence at 1K Sample** | 0.094 (gap 0.452, 16% improvement) | legal-distance section cross-lingual | **FAILED** |
| **Evidence at 144k (22yr)** | 0.0941 | fractal-map 144k checkpoint validation | **FAILED** |
| **Note** | Reasoning is most language-specific | Consistent across scales | CONFIRMED |

**Product Integration:** NOT INCLUDED — does not meet acceptance criterion

### 2.5 View 5: Linear Hybrid Complement (TF-IDF + Dense)

| Criterion | Value | Evidence | Status |
|-----------|-------|----------|--------|
| **Acceptance Threshold** | PASS both adversarial gates AND cross_lang_same_branch > TF-IDF baseline | Integration contract | DEFINED |
| **Optimal Weight (22yr)** | w=0.4 dense / 0.6 TF-IDF (cited_decisions_tfidf) | legal-distance linear_hybrid | VALIDATED |
| **Optimal Weight (19yr)** | w=0.3 dense / 0.7 TF-IDF (outcome_hybrid_0.5) | legal-distance linear_hybrid | VALIDATED |
| **JP at Optimal (22yr)** | 0.6725 | legal-distance linear_hybrid | PASS adversarial |
| **TF-IDF Baseline JP (22yr)** | 0.7840 | legal-distance formal suite | BASELINE |
| **Cross-lingual Improvement** | +0.036 recall@10 | legal-distance linear_hybrid | MEASURED |
| **Minimal Scale Validated** | 122k decisions (19yr) | legal-distance scale dependency | VALIDATED |
| **Required Dense Modes** | cp64, cp128 | Integration contract | SPECIFIED |

**Product Integration:** Separate map mode `linear_hybrid_complement_view` (marked **EXPLORATORY**)  
**Status:** READY at 144k; REMAINS BELOW TF-IDF baseline on JP (0.61-0.67 vs 0.78-0.79)

---

## 3. Fundamental Trade-off Confirmed (Reproduced at All Scales)

| Representation | Language Dominance | Jurist Preference | Citation Independence |
|----------------|-------------------|-------------------|----------------------|
| TF-IDF Citation Hybrids | 0.48 | **0.78** | 0.14 |
| Dense Semantic (center_projected) | **0.83-0.98** | 0.05-0.43 | **0.37** |
| Linear Hybrids (w=0.3-0.4) | 0.58-0.80 | 0.61-0.67 | 0.25-0.35 |

**Conclusion:** NO single representation dominates all three metrics at any scale (3yr through 22yr tested). This validates the multi-view architecture.

**Source:** legal-distance `complementary_role_characterization_v34.json` → `two_mode_tradeoff`

---

## 4. True OOS Juror Preference Ceiling

| Metric | Value | Factory Target | Achievable |
|--------|-------|----------------|------------|
| True OOS JuristPref Ceiling | ~0.53 | 0.7 | **NO** |

**Source:** legal-distance v8 holdout zero-shot validation  
**Implication:** No embedding method can reach factory target of 0.7 on true out-of-sample jurist preference. The 0.73-0.78 JP on TF-IDF is an in-distribution estimate.

---

## 5. Data Blockers for 174k Dense Embedding Completion

| Blocker | Impact | Owner |
|---------|--------|-------|
| BGE/bger ID mapping | Canonical corpus uses bge_ IDs, evaluation uses bger_ IDs — no mapping exists | Corpus lane |
| Parquet 2022-2026 | 29,520 decisions missing from pinned 2026 snapshot | Corpus lane |
| Section extraction 174k | Sachverhalt/Erwaegungen/Dispositiv not extracted at scale for cross-lingual density | Corpus lane |
| 174k dense embeddings | Currently 3/26 years complete (~19,441 decisions, 11%) | Legal-distance lane |

**Resolution:** Corpus lane resumption required per factory direction v35.

---

## 6. Evaluation Framework Validation Status

### 6.1 Adversarial Gates (Primary Quality Control)
- **Gate 1:** Language Dominance < 0.85 — TF-IDF 174k: PASS (0.47-0.50)
- **Gate 2:** Jurist Preference > 0.5 — TF-IDF 174k: PASS (0.63-0.735)
- **Both Gates Required:** Yes — TF-IDF 174k: 8/8 reps PASS both

### 6.2 Complementary View Gates (New for Dense Modes)
- **Citation Heritage:** AUC > 0.75 — Dense: PASS at 144k (0.7922)
- **Cross-Lingual Sachverhalt:** cross_lang_same_branch > 0.2 — Dense: PASS at 1K/144k (0.282/0.2816)
- **Cross-Lingual Dispositiv:** cross_lang_same_branch > 0.1 — Dense: PASS at 1K/144k (0.150/0.1502)
- **Linear Hybrid:** PASS both adversarial + cross_lang > TF-IDF — Dense: PASS adversarial at 144k, cross_lang +0.036

### 6.3 RECORDED EXTERNAL DEPENDENCY
**Jurist Human Study:** Framework ready for 5-10 Swiss jurists. Not yet executed. This is the ultimate validation of simulated jurist proxy.

---

## 7. Recommendations

| Recommendation | Rationale |
|----------------|-----------|
| **FREEZE** TF-IDF 174k formal suite as production baseline | 8/8 reps PASS both adversarial gates at full 174k scale; JP=0.735 beats semantic baseline 0.43 |
| **DEFINE** dense acceptance criteria as specified above | ACCEPTED evidence from legal-distance/fractal-map characterizes complementary role |
| **BLOCK** dense 174k completion on corpus lane resumption | BGE/bger ID mapping + parquet 2022-2026 + section extraction are hard dependencies |
| **NO NEW FRONTIER TEAM** | Portfolio v7 CONFIRMED: true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria |
| **PRODUCT v1.0** with TF-IDF primary; dense v1.1+ per integration contracts | Strategic pivot executed per factory direction v34/v35 |

---

## 8. Next Recommendation

**continue_recommended: false**

No additional same-question cycles justified. The TF-IDF baseline is frozen and dense acceptance criteria are defined from max available scale evidence (144k/22yr checkpoint). Next cycle should be triggered only when corpus lane resolves data blockers and legal-distance delivers 174k dense embeddings for formal acceptance testing against these criteria.

---

## Appendix: Evidence References

| Ref ID | Path | Tier | Description |
|--------|------|------|-------------|
| E1 | legal-distance/evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json | REPRODUCED | TF-IDF 174k formal suite (8 modes, full corpus) |
| E2 | legal-distance/results/legal_distance/complementary_role_characterization_v34.json | REPRODUCED | Dense complementary role characterization at 144k |
| E3 | legal-distance/results/legal_distance/dense_complementary_characterization/scale_characterization_results.json | REPRODUCED | Scale characterization for linear hybrids |
| E4 | legal-distance/legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json | REPRODUCED | Citation heritage AUC at 144k |
| E5 | fractal-map/results/fractal_map/dense_embeddings_integration_contract_v34.json | ACCEPTED | Frozen integration contract for dense views |
| E6 | fractal-map/results/fractal_map/144k_checkpoint_validation/144k_validation_144443decisions.json | REPRODUCED | 144k hierarchical validation on dense embeddings |
| E7 | product/results/audit/product/CYCLE_37073590337_GATE.json | ACCEPTED | Product v1.0 audit gate PASS |

---

*Report generated per Research Protocol: freeze hypothesis/corpus/metric/success rule before outcome inspection. Negative results preserved as evidence.*