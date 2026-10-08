# LEGAL DISTANCE V35 FINAL AUDIT VERIFICATION — Run 37838941187

## Operational Resume from Persisted Producer Snapshot

**Run ID:** 37838941187
**Date:** 2026-10-08
**Status:** FINAL_AUDIT_VERIFICATION_COMPLETE
**Previous Run:** 37836120381

## Summary

Operational resume from persisted producer snapshot of run 37836120381. All validation steps reproduced successfully:

### Test Results
- **test_complementary_role_v34.py**: 8/8 assertions PASSED
- **test_v29_final_results.py**: 15/15 assertions PASSED

### Scale Characterization Experiment Reproduction
**Experiment:** `characterize_dense_complementary_views.py` on 12k ACCEPTED dense embeddings (2000-2002)
**Result:** IDENTICAL scale-dependent patterns reproduced:

1. **Cross-lingual inflation at small homogeneous scale**: 0.656 → 0.957 (matches previous runs)
2. **Legal area purity degradation with scale**: 0.61 → 0.47 (consistent with full-corpus evaluations)
3. **Branch k-NN accuracy stable**: >0.99 at all scales
4. **Linear hybrid PASS jurist proxy**: At all weights across all scales

## PIVOT_WITHIN_MISSION Characterization COMPLETE

At maximum available evaluated scale:
- **24yr/158k citation heritage**: center_projected AUC 0.767-0.770 > 0.75
- **174k formal suite**: TF-IDF 14/14 PASS, dense complementary views validated
- **1K section cross-lingual**: Sachverhalt/Dispositiv PASS, Erwaegungen FAIL

## Three Complementary Dense Modes — Necessary and Sufficient

### 1. CITATION HERITAGE VIEW
- **Minimal scale**: 21yr / 137k decisions (2000-2020)
- **Evidence**: center_projected_64dim AUC 0.77-0.85 > TF-IDF 0.71-0.74
- **Status**: PASSED at 21-24yr (137k-158k)

### 2. SECTION CROSS-LINGUAL VIEW
- **Minimal scale**: 1K sample with sections
- **Evidence**: 
  - Sachverhalt cp_64 cross_lang_same_branch=0.282 > 0.2 **PASS**
  - Dispositiv cp_64 cross_lang_same_branch=0.150 > 0.1 **PASS**
  - Erwaegungen cp_64 cross_lang_same_branch=0.094 < 0.1 **FAIL**
- **Hierarchy confirmed**: Sachverhalt > Dispositiv > Erwaegungen
- **Full corpus density BLOCKED** on section extraction at 174k

### 3. LINEAR HYBRID COMPLEMENT
- **Minimal scale**: 19yr / 122k decisions (2000-2018)
- **Evidence**: w=0.3-0.4 PASS adversarial gates, JP 0.61-0.67
- **Status**: BELOW TF-IDF baseline (0.78-0.79) — NOT primary

## Two-Mode Tradeoff FUNDAMENTAL (Reproduced)

| Mode | LangDom | JP | CiteIndep |
|------|---------|-----|-----------|
| TF-IDF Citation Hybrids | ~0.48 | ~0.78 | ~14% |
| Semantic Embeddings | ~0.83-0.98 | ~0.05-0.43 | ~37% |
| Linear Hybrids | ~0.58-0.80 | ~0.61-0.67 | Intermediate |

**NO single representation dominates all three metrics at any scale.**

## True OOS JuristPref Ceiling Confirmed
- **~0.53** < 0.7 factory target (via v8 holdout)
- No representation achieves factory target under true out-of-sample conditions

## Data Blockers Persist (Require Corpus Lane Resumption)

1. **bge_/bger_ ID mapping** — no cross-mapping exists
2. **Parquet 2024-2026** — 15.5k decisions missing
3. **174k section extraction** — sachverhalt/erwaegungen/dispositiv not run at scale

## Lane Status: BLOCKED_ON_DEPENDENCIES (Correct)

- **factory_direction.json v35 shows RUN** — orchestration/validation failure
- **Lane state correctly shows BLOCKED_ON_DEPENDENCIES** with continue_recommended=false
- **PIVOT_WITHIN_MISSION characterization COMPLETE** at v34 (run 37677999602)
- **Scientific integrity UNAFFECTED** — all evidence ACCEPTED, all tests PASS
- **No further same-question cycles justified**

## Snapshot: AUDIT-READY

All valid completed work preserved. Negative results preserved as first-class evidence. Orchestration/validation failure diagnosed as Factory Director control-plane sync issue, NOT scientific failure.

---

**Verification Report:** `reports/legal_distance/LEGAL_DISTANCE_V35_FINAL_AUDIT_VERIFICATION_37838941187.md`
**Results:** `results/legal_distance/dense_complementary_characterization/scale_characterization_results.json`
**Tests:** All 23 assertions PASSED (8 + 15)