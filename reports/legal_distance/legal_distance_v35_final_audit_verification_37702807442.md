# Legal Distance Lane — Final Audit Verification for GitHub Run 37702807442

**Date:** 2026-10-07  
**Factory Direction:** v35  
**Lane:** legal-distance  
**Status:** FINAL_AUDIT_VERIFICATION_COMPLETE  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  

---

## Executive Summary

Operational resume from persisted producer snapshot of run 37701901179. All valid completed work preserved. The lane has completed its PIVOT_WITHIN_MISSION characterization at the maximum available evaluated scale. The orchestration/validation failure diagnosed in prior runs was due to **data dependency blockers**, NOT scientific failure.

**Key verification results for this run:**
- ✅ All 8/8 `test_complementary_role_v34.py` assertions PASSED
- ✅ All 15/15 `test_v29_final_results.py` assertions PASSED  
- ✅ Scale characterization experiment (`characterize_dense_complementary_views.py`) REPRODUCED on 12k ACCEPTED dense embeddings (2000-2002) with IDENTICAL scale-dependent patterns
- ✅ PIVOT_WITHIN_MISSION characterization COMPLETE at max available evaluated scale

---

## Verified Findings (Reproduced This Run)

### 1. Citation Heritage Recovery — Dense Embeddings SUPERIOR
- **21yr/137k (2000-2020):** raw AUC 0.8455, center_projected_64dim AUC 0.8182 (100 positive pairs)
- **22yr/144k (2000-2021):** raw AUC 0.7946, center_projected_64dim AUC 0.7922 (344 positive pairs)
- **24yr/158k (2000-2023):** center_projected_768dim AUC 0.7696, center_projected_64dim AUC 0.7667 (730 positive pairs)
- **Acceptance criterion:** AUC > 0.75 — **PASSED at 21-24yr (137k-158k)**
- Superior to TF-IDF citation-based baseline (AUC 0.71-0.74) and TF-IDF text-based (AUC 0.50-0.63)
- Center projection and PCA (64/128/768-dim) preserve this capability
- Requires recent years (2019+) for sufficient citation pair density

### 2. Section Cross-Lingual Hierarchy — CONFIRMED
**1K sample with section extractions:**
- **Sachverhalt (facts, n=359):** cp_64 cross_lang_same_branch=0.282 > 0.2 threshold ✅ PASS, invariance_gap=0.187
- **Dispositiv (holding, n=538):** cp_64 cross_lang_same_branch=0.150 > 0.1 threshold ✅ PASS, invariance_gap=0.397
- **Erwaegungen (reasoning, n=510):** cp_64 cross_lang_same_branch=0.094 < 0.1 threshold ❌ FAIL, invariance_gap=0.452

**Hierarchy confirmed:** Sachverhalt > Dispositiv > Erwaegungen  
**Center projection improves all:** Sachverhalt gap 0.304→0.187, Erwaegungen 0.538→0.452, Dispositiv 0.575→0.397  
**Full corpus density BLOCKED** pending section extraction at 174k scale (corpus lane resumption required)

### 3. Linear Hybrid Complement — SCALE-DEPENDENT
- **15yr (92k):** FAIL (JP=0.473)
- **19yr (122k):** PASS both gates at w=0.3 (JP=0.6365-0.6465)
- **22yr (144k):** PASS at w=0.3-0.4 (JP=0.6115-0.6725)
- **Optimal weight shifts toward semantic at larger scale** but BOTH remain BELOW TF-IDF baseline (JP=0.78-0.79)
- Citation signals dominate jurist preference; semantic signals add cross-lingual benefit but dilute legal relevance

### 4. Two-Mode Tradeoff — FUNDAMENTAL
| Representation | LangDom | JP | CiteIndep |
|---|---|---|---|
| TF-IDF Citation Hybrids | ~0.48 | ~0.78 | ~14% |
| Dense Embeddings (center_projected) | ~0.83-0.98 | ~0.05-0.43 | ~37% |
| Linear Hybrids (optimal) | ~0.58-0.80 | ~0.61-0.67 | intermediate |

**NO single representation dominates all three metrics at any scale.**  
**TF-IDF = PRIMARY product mode** (jurist preference, branch clustering)  
**Dense = COMPLEMENTARY modes** (citation heritage view, cross-lingual view, linear hybrid complement)

### 5. Dense Embeddings FAIL Jurist Gate at ALL Scales
- 3yr ACCEPTED (19k): JP=0.39-0.42 FAIL
- 15yr (92k): JP=0.288 FAIL
- 19yr (122k): JP=0.37 FAIL
- 20yr (130k): JP=0.05 CATASTROPHIC FAIL
- 22yr (144k): JP=0.43 FAIL

### 6. True OOS JuristPref Ceiling ~0.53 < 0.7 Factory Target
Confirmed via v8 holdout zero-shot validation. No representation achieves factory target under true out-of-sample conditions.

### 7. Scale Characterization Experiment — REPRODUCED (12k ACCEPTED dense)
| Scale | Cross-Lingual | Legal Area Purity | Branch k-NN@1 |
|---|---|---|---|
| 1000 | 0.656 | 0.609 | 0.957 |
| 2000 | 0.971 | 0.493 | 0.989 |
| 4000 | 0.971 | 0.485 | 0.988 |
| 6000 | 1.000 | 0.477 | 0.995 |
| 8000 | 1.000 | 0.485 | 0.993 |
| 10000 | 0.976 | 0.455 | 0.992 |
| 12570 | 0.957 | 0.475 | 0.992 |

**Patterns IDENTICAL to prior runs:**
- Cross-lingual inflation at small homogeneous scale (0.656→0.957)
- Legal area purity degradation with scale (0.61→0.47) consistent with full-corpus evaluations
- Branch k-NN accuracy stable (>0.99 at all scales)
- Linear hybrid PASS jurist proxy at all weights

---

## Data Blockers Persisting (Require Corpus Lane Resumption)

1. **bge_ / bger_ ID mapping** — No cross-mapping between published (bge_) and unpublished (bger_) decision ID systems
2. **Parquet 2024-2026 missing** — 15,536 decisions (years 2024-2026) lack parquet artifacts
3. **174k section extraction** — Sachverhalt/Erwaegungen/Dispositiv not extracted at full corpus scale

**Note:** 2022-2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75), contradicting progress.json 'failed' flag. This is an orchestration artifact, not a scientific failure.

---

## Audit Repairs Completed (Prior Runs)

1. **Comprehensive Validation Baseline Fixed** — Now uses v5 baseline center_projected (768-dim, 1200 decisions) consistently
2. **Citation Role Integration Fixed** — Fractal evaluation detects overclustering and degenerate structure; alpha-blended variants PASS
3. **Overclustering Gate Fixed** — All evaluation scripts require `valid_representation=true` (not overclustered, not degenerate)

---

## Recommendation

**No further same-question cycles justified.** The PIVOT_WITHIN_MISSION question has been fully answered at the maximum available evaluated scale. The lane correctly remains `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false`.

**Next steps require Corpus lane resumption** to resolve:
- bge_/bger_ ID mapping
- Parquet generation for 2024-2026
- 174k section extraction (Sachverhalt/Erwaegungen/Dispositiv)

---

## Files Updated This Run

- `state/legal-distance.json` — Updated `current_run`, added verification entry for run 37702807442
- `reports/legal_distance/legal_distance_v35_final_audit_verification_37702807442.md` — This report
- `results/legal_distance/dense_complementary_characterization/scale_characterization_results.json` — Reproduced scale characterization results

---

## Verification Artifacts

| Artifact | Path |
|---|---|
| State file | `state/legal-distance.json` |
| Test: complementary role | `tests/legal_distance/test_complementary_role_v34.py` (8/8 PASS) |
| Test: v29 final results | `tests/legal_distance/test_v29_final_results.py` (15/15 PASS) |
| Scale characterization | `legal_distance/experiments/characterize_dense_complementary_views.py` |
| Scale results | `results/legal_distance/dense_complementary_characterization/scale_characterization_results.json` |
| Key report: minimal dense scale | `reports/legal_distance/legal_distance_v34_minimal_dense_scale_characterization.md` |
| Key report: complementary role | `reports/legal_distance/legal_distance_v34_complementary_role.md` |

---

## Orchestration/Validation Failure Diagnosis

The prior workflow failure (run 37701901179) was **not a scientific failure** but an **orchestration failure** caused by:
1. Missing bge_/bger_ ID mapping — preventing alignment of 174k dense embeddings with evaluation metadata
2. Missing parquet artifacts for 2024-2026 — blocking computation of final 174k dense embeddings
3. Missing 174k section extraction — blocking full-corpus cross-lingual evaluation

**All valid completed work is preserved and reproducible.** The PIVOT_WITHIN_MISSION characterization is complete and audit-ready.

---

## Snapshot Audit-Ready

All valid completed work preserved. Factory direction v34/v35 strategic pivot fully executed: TF-IDF citation hybrids = PRIMARY product mode (beats semantic baseline JP 0.78 vs 0.43); dense embeddings = COMPLEMENTARY modes for citation heritage, cross-lingual, and hybrid exploration views.

---

**Verification completed:** 2026-10-07T23:55:00.000000Z