# Evaluation Lane v34 Verification Report
**GitHub Run:** 37258323239  
**Date:** 2026-10-05  
**Factory Direction Version:** 34  
**Previous Verified Run:** 37254477262 (2026-10-05T01:15:00Z)

## Summary
This run verifies the **frozen ACCEPTED state** of the evaluation lane for factory direction v34. No new claim-bearing evaluation is performed — the lane remains `continue_recommended: false` as established in run 37202808358 and confirmed in verification runs 37249314741, 37254477262, and now 37258323239.

## Verification Results

### 1. Frozen TF-IDF 174k Baseline Confirmed
- **Test:** `tests/evaluation/test_v25_174k_suite_snapshot.py` — **PASSED** (exit code 0)
- Validates the audit-ready snapshot under frozen protocol v25
- All 8 TF-IDF representations: shape (173963, 128), float32, finite
- Hybrid determinism: bitwise exact reconstruction verified
- Fixed subsample determinism: seed-42 stratified subsamples reproduce exactly
- Suite/summary consistency: all 12 benchmarks carry frozen thresholds
- Citation-heritage spot check: AUC-ROC matches frozen values within 0.005
- v17b label normalization record: 214→164 unique labels, 49.3% changed, 47.6% unknown
- v17b provenance gate: GATE_OVERALL=PASS (P1/P2/P4 PASS, confined P3 WARNs, NC_swap/NC_fileid PASS)

### 2. Frozen Harness v3 Reproducibility Confirmed
- **Test:** `tests/evaluation/test_frozen_harness_v3_reproducibility.py` — **PASSED** (exit code 0)
- All 6 representations REPRODUCED within tolerance 0.001
- Config hash: `4323f833fa72366a` (frozen v16 suite config hash)
- Global seed: 42
- Adversarial thresholds unchanged: LangDom < 0.85, JP > 0.5

### 3. Cross-Lingual Alignment Findings Confirmed
- **Test:** `tests/evaluation/test_cross_lingual_alignment_v10.py` — **PASSED** (exit code 0)
- Procedural pairs near-losslessness verified
- Joint PCA Jurivoc L0 reduction: 47.5% (matches ~48%)
- Section/outcome overfit confirmed across all variants (Jurivoc L0 0.007-0.011)

### 4. Boilerplate Resistance Correction Confirmed
- **Test:** `tests/evaluation/test_boilerplate_resistance_real.py` — **PASSED** (exit code 0)
- All TF-IDF section representations ABOVE 85% neighbor preservation threshold
- Sachverhalt/Erwaegungen: 93.2%, Outcome: 89.2%, Full text: 93.2%
- Systemic challenge confirmed: cross-lingual alignment, NOT boilerplate

### 5. Adversarial Re-verification (2026-10-02) — 8/8 TF-IDF PASS
- **Evidence:** `results/evaluation/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json`
- Method: exact k-NN on stratified subsample n=2000, seed=42
- Config hash: `b51701f5a9c11692`
- All 8 TF-IDF representations PASS both gates:
  | Representation | LangDom | JP | Both Pass |
  |----------------|---------|-----|-----------|
  | cited_decisions_tfidf_outcome_hybrid_0.5 | 0.4895 | 0.7265 | ✓ |
  | cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4908 | 0.7195 | ✓ |
  | cited_decisions_tfidf | 0.4917 | 0.7075 | ✓ |
  | full_text_tfidf_light | 0.4854 | 0.7080 | ✓ |
  | regeste_full_text_hybrid_0.5 | 0.4873 | 0.7140 | ✓ |
  | regeste_full_text_hybrid_0.7 | 0.4889 | 0.7120 | ✓ |
  | outcome_tfidf | 0.5078 | 0.6660 | ✓ |
  | regeste_tfidf | 0.5111 | 0.6145 | ✓ |
- LangDom range: [0.485, 0.511] all < 0.85 ✓
- JP range: [0.614, 0.727] all > 0.5 ✓

## Legal-Distance 24-Year Dense Embedding Evaluation CONFIRMED
The legal-distance lane has extended evaluation to 24-year scale (2000-2023, 158,427 decisions) with **730 positive citation pairs** (2.1x more than 22-year's 344 pairs). This reinforces the dense embedding acceptance criteria validation:

| Criterion | Threshold | 22-Year Evidence | 24-Year Evidence | Status |
|-----------|-----------|------------------|------------------|--------|
| Citation Heritage AUC | > 0.75 | 0.7916-0.7946 | 0.7667-0.7696 | **PASS** (reinforced) |
| Cross-lang Sachverhalt | > 0.2 | 0.282 | (3-year sample) | **PASS** |
| Cross-lang Dispositiv | > 0.1 | 0.148-0.150 | (3-year sample) | **PASS** |
| Cross-lang Erwaegungen | > 0.1 | 0.093-0.094 | (3-year sample) | **FAIL** |
| Jurist Pairwise Preference | > 0.5 | 0.39-0.43 | 0.35-0.38 | **FAIL** |

### 24-Year Dense Adversarial Results (EXACT k-NN, n=2000 subsample):
| Representation | LangDom | LangDom Status | JP | JP Status | Both Pass |
|----------------|---------|----------------|-----|-----------|-----------|
| center_projected_768dim | 0.8535 | FAIL | 0.3510 | FAIL | ✗ |
| center_projected_64dim | 0.8438 | **PASS** | 0.3765 | FAIL | ✗ |
| center_projected_128dim | 0.8508 | FAIL | 0.3565 | FAIL | ✗ |

**Key Reinforcement:** Citation heritage AUC remains > 0.75 at 24-year scale with substantially more positive pairs (730 vs 344), confirming dense embeddings' superior citation heritage recovery is robust to scale extension. However, center_projected FAILS jurist gate at ALL dimensions at 24-year scale — true OOS ceiling ~0.38 < 0.5.

## Dense Embedding Acceptance Criteria (Validated Against 22-Year/144k + 24-Year/158k Evidence)
| Criterion | Threshold | Evidence | Status |
|-----------|-----------|----------|--------|
| Citation Heritage AUC | > 0.75 | 22yr: 0.7916-0.7946; 24yr: 0.7667-0.7696 | **PASS** |
| Cross-lang Sachverhalt | > 0.2 | 0.282 (3yr sample) | **PASS** |
| Cross-lang Dispositiv | > 0.1 | 0.148-0.150 (3yr sample) | **PASS** |
| Cross-lang Erwaegungen | > 0.1 | 0.093-0.094 (3yr sample) | **FAIL** |
| Jurist Pairwise Preference | > 0.5 | 0.35-0.43 (all scales) | **FAIL** |

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
4. Legal-distance 24-year extension reinforces citation heritage validation ✓

Next factory direction decision: Await corpus lane resumption for 174k dense embeddings (requires bge_/bger_ ID mapping + parquet 2022-2026 + section extraction at 174k scale).

## Provenance
- Config hash (frozen harness): `4323f833fa72366a` (v25 suite), `b51701f5a9c11692` (adversarial)
- Global seed: 42
- Factory direction: v34
- All tests executed with Python directly (no pytest dependency)
- Negative results honestly preserved (dense JP failure, Erwaegungen cross-lingual failure, v17b non-generalization)
- Legal-distance 24-year extension evidence incorporated as reinforcing validation