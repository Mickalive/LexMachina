# Evaluation Lane v34 Verification Report
**GitHub Run:** 37249314741  
**Date:** 2026-10-05  
**Factory Direction Version:** 34  
**Previous Verified Run:** 37248361999 (2026-10-05T00:45:00Z)

## Summary
This run verifies the **frozen ACCEPTED state** of the evaluation lane for factory direction v34. No new claim-bearing evaluation is performed — the lane remains `continue_recommended: false` as established in run 37202808358.

## Verification Results

### 1. Frozen TF-IDF 174k Baseline Confirmed
- **Test:** `test_v25_174k_suite_snapshot.py` — **PASSED**
- Validates the audit-ready snapshot under frozen protocol v25
- All 8 TF-IDF representations: shape (173963, 128), float32, finite
- Hybrid determinism: bitwise exact reconstruction verified
- Fixed subsample determinism: seed-42 stratified subsamples reproduce exactly
- Suite/summary consistency: all 12 benchmarks carry frozen thresholds
- Citation-heritage spot check: AUC-ROC matches frozen values within 0.005
- v17b label normalization record: 214→164 unique labels, 49.3% changed, 47.6% unknown
- v17b provenance gate: GATE_OVERALL=PASS (P1/P2/P4 PASS, confined P3 WARNs, NC_swap/NC_fileid PASS)

### 2. Frozen Harness v3 Reproducibility Confirmed
- **Test:** `test_frozen_harness_v3_reproducibility.py` — **PASSED**
- All 6 representations REPRODUCED within tolerance 0.001
- Config hash: `4323f833fa72366a` (frozen v16 suite config hash)
- Global seed: 42
- Adversarial thresholds unchanged: LangDom < 0.85, JP > 0.5

### 3. Cross-Lingual Alignment Findings Confirmed
- **Test:** `test_cross_lingual_alignment_v10.py` — **PASSED**
- Procedural pairs near-losslessness verified
- Joint PCA Jurivoc L0 reduction: 47.5% (matches ~48%)
- Section/outcome overfit confirmed across all variants (Jurivoc L0 0.007-0.011)

### 4. Boilerplate Resistance Correction Confirmed
- **Test:** `test_boilerplate_resistance_real.py` — **PASSED**
- All TF-IDF section representations ABOVE 85% neighbor preservation threshold
- Sachverhalt/Erwaegungen: 93.2%, Outcome: 89.2%, Full text: 93.2%
- Systemic challenge confirmed: cross-lingual alignment, NOT boilerplate

### 5. Product Integration Verification
- **State file:** `product_integration_verification_v11.json` (frozen from v10)
- BEST production hybrids correctly identified as NOT in product:
  - `cited_decisions_tfidf_outcome_hybrid_0.5`: JP=0.7965, LangDom=0.4941 ✓
  - `cited_decisions_tfidf_outcome_hybrid_0.7`: JP=0.7898, LangDom=0.4922 ✓
- Adversarial gate summary: 20/24 PASS (83.3%) — matches frozen state
- Known failures correctly identified: `center_projected_768`, `cited_decisions_tfidf_procrustes`, `cited_decisions_tfidf_cca`, `criticizing_alpha0.7`

## Dense Embedding Acceptance Criteria (Validated Against 22-Year/144k Evidence)
| Criterion | Threshold | Evidence (22yr/144k) | Status |
|-----------|-----------|---------------------|--------|
| Citation Heritage AUC | > 0.75 | center_projected: 0.7916-0.7946 | **PASS** |
| Cross-lang Sachverhalt | > 0.2 | 0.282 | **PASS** |
| Cross-lang Dispositiv | > 0.1 | 0.148-0.150 | **PASS** |
| Cross-lang Erwaegungen | > 0.1 | 0.093-0.094 | **FAIL** |
| Jurist Pairwise Preference | > 0.5 | 0.39-0.43 (all scales) | **FAIL** |

**Conclusion:** Dense embeddings are COMPLEMENTARY VIEWS ONLY (citation heritage, cross-lingual sachverhalt/dispositiv). They do NOT meet jurist preference baseline for primary navigation.

## Critical State Confirmation
| Field | Value | Source |
|-------|-------|--------|
| `evidence_tier` | ACCEPTED | state/evaluation.json |
| `cycle_status` | COMPLETE | state/evaluation.json |
| `continue_recommended` | false | state/evaluation.json |
| `accepted_run_id` | eval_174k_v34_baseline_and_dense_criteria_20261003 | state/evaluation.json |
| TF-IDF 174k baseline | FROZEN | All verification tests |
| Dense 174k embeddings | BLOCKED | Corpus lane: bge_/bger_ mapping + parquet 2022-2026 |

## Recommendation
**No further same-question cycles justified.** The evaluation lane has completed its v34 mandate:
1. TF-IDF 174k evaluation frozen as production baseline ✓
2. Dense embedding acceptance criteria defined and validated ✓
3. All evidence preserved at ACCEPTED tier ✓

Next factory direction decision: Await corpus lane resumption for 174k dense embeddings (requires bge_/bger_ ID mapping + parquet 2022-2026 + section extraction at 174k scale).

## Provenance
- Config hash (frozen harness): `4323f833fa72366a`
- Global seed: 42
- Factory direction: v34
- All tests executed with Python directly (no pytest dependency)
- Negative results honestly preserved (dense JP failure, Erwaegungen cross-lingual failure, v17b non-generalization)