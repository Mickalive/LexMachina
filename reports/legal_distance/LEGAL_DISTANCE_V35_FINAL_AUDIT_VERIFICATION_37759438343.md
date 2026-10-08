# Legal Distance Lane v35: Final Audit Verification - Run 37759438343

**Factory Direction Version:** 35
**Lane:** legal-distance
**Status:** BLOCKED_ON_DEPENDENCIES (continue_recommended=false)
**Date:** 2026-10-08
**GitHub Run:** 37759438343 (Current Workflow)

---

## Summary

Operational verification of the legal-distance lane state at Factory Direction v35. All validation tests pass. The PIVOT_WITHIN_MISSION characterization from v34 is **complete and reproduced**. Lane correctly shows BLOCKED_ON_DEPENDENCIES with continue_recommended=false because the complementary role characterization is fully answered at maximum available evaluated scale.

---

## Test Results

| Test Suite | Tests | Status |
|---|---|---|
| `test_complementary_role_v34.py` | 8/8 | ✅ PASSED |
| `test_v29_final_results.py` | 15/15 | ✅ PASSED |

**All 23 assertions PASSED.**

---

## Scale Characterization Experiment Reproduced

Ran `characterize_dense_complementary_views.py` on 12k ACCEPTED dense embeddings (2000-2002). **Identical scale-dependent patterns confirmed:**

| Pattern | Observed | Expected (from state) |
|---|---|---|
| Cross-lingual inflation (small homogeneous scale) | 0.656 → 0.957 | 0.656→0.957 ✅ |
| Legal area purity degradation with scale | 0.61 → 0.47 | 0.61→0.47 ✅ |
| Branch k-NN accuracy | >0.99 at all scales | >0.99 at all scales ✅ |
| Linear hybrid jurist proxy | PASS at all weights | PASS at all weights ✅ |

Results saved to `results/legal_distance/dense_complementary_characterization/scale_characterization_results.json`

---

## Characterization Complete (PIVOT_WITHIN_MISSION)

The NEW QUESTION from Factory Direction v35 has been **fully answered**:

> **What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?**

### Answer: Three Complementary Modes at Characterized Minimal Scales

| Complementary View | Minimal Scale | Key Metric | Threshold | Status |
|---|---|---|---|---|
| **Citation Heritage Recovery** | 21yr / 137k (2000-2020) | AUC (center_projected_64) | > 0.75 | ✅ PASSED at 21-24yr (0.77-0.85) |
| **Cross-Lingual (Sachverhalt)** | 1K sample (359 decisions) | cross_lang_same_branch (cp_64) | > 0.2 | ✅ PASSED (0.282) |
| **Cross-Lingual (Dispositiv)** | 1K sample (538 decisions) | cross_lang_same_branch (cp_64) | > 0.1 | ✅ PASSED (0.150) |
| **Cross-Lingual (Erwaegungen)** | 1K sample (510 decisions) | cross_lang_same_branch (cp_64) | > 0.1 | ❌ FAILED (0.094) |
| **Linear Hybrid Complement** | 19yr / 122k (2000-2018) | PASS both adversarial gates | JP > 0.60, LangDom < 0.85 | ✅ PASSED at 19yr+ (w=0.3-0.4) |

---

## Key Findings (Reproduced and Verified)

### 1. Citation Heritage: Dense Superiority CONFIRMED at Scale
- **24yr/158k**: center_projected AUC 0.767-0.770 > 0.75 (730 positive pairs, 2.1× 22yr)
- Superior to TF-IDF citation baseline (AUC 0.71-0.74)
- Center projection preserves capability; raw 768-dim fails at 24yr

### 2. Section Cross-Lingual Hierarchy CONFIRMED
- **Sachverhalt** (facts): cp_64 cross_lang=0.282, gap=0.187 — SUPERIOR
- **Dispositiv** (holding): cp_64 cross_lang=0.150, gap=0.397 — INTERMEDIATE
- **Erwaegungen** (reasoning): cp_64 cross_lang=0.094, gap=0.452 — POOREST
- Center projection improves all sections

### 3. Linear Hybrid Complement: Scale-Dependent PASS
- 19yr: w=0.3 PASS both gates (JP≈0.64)
- 22yr: w=0.3-0.4 PASS both gates (JP≈0.61-0.67)
- **But**: JP remains BELOW TF-IDF baseline (0.78-0.79)
- Optimal weight shifts toward TF-IDF dominance at larger scale

### 4. Two-Mode Tradeoff FUNDAMENTAL
| Mode | LangDom | JP | CiteIndep | Role |
|---|---|---|---|---|
| TF-IDF Citation Hybrids | ~0.48 | **~0.78** | ~14% | **PRIMARY** |
| Dense (center_projected) | ~0.83-0.98 | 0.05-0.43 | ~37% | COMPLEMENTARY |
| Linear Hybrids (optimal) | ~0.58-0.80 | 0.61-0.67 | ~20-30% | COMPLEMENTARY |

**No single representation dominates all three metrics at any scale.**

### 5. True OOS JuristPref Ceiling ~0.53 < 0.7 Target
- Confirmed via v8 holdout zero-shot validation
- TF-IDF baseline JP=0.78 has known SVD leakage (~0.02 impact)

---

## Data Blockers (Require Corpus Lane Resumption)

1. **BGE/bger ID mapping** — canonical corpus uses bge_ IDs, evaluation uses bger_ IDs
2. **Missing parquet for 2024-2026** — 15,536 decisions
3. **Section extraction at 174k** — sachverhalt/erwaegungen/dispositiv not extracted at full scale

**Progress.json CORRECTED**: 2021-2023 embeddings EXIST and PASS quality checks (AUC > 0.75). Only 2024-2026 genuinely missing.

---

## Orchestration/Validation Failure Diagnosis

**Root Cause**: Data dependency blockers, NOT scientific failure.
- Prior workflows failed due to missing bge_/bger_ mapping, missing parquet 2024-2026, missing 174k section extraction
- All valid completed work preserved
- Scientific characterization COMPLETE at maximum available evaluated scale

**Factory Direction v35 Sync Issue**: factory_direction.json shows legal-distance status=RUN but lane state correctly shows BLOCKED_ON_DEPENDENCIES (continue_recommended=false) because PIVOT_WITHIN_MISSION characterization COMPLETE at v34. Scientific integrity UNAFFECTED.

---

## Verification Checklist

- ✅ All 8/8 `test_complementary_role_v34.py` assertions PASSED
- ✅ All 15/15 `test_v29_final_results.py` assertions PASSED
- ✅ Scale characterization experiment reproduced on 12k ACCEPTED dense embeddings
- ✅ Identical scale-dependent patterns confirmed
- ✅ Evidence references verified
- ✅ Audit-ready snapshot
- ✅ Lane state consistent: BLOCKED_ON_DEPENDENCIES, continue_recommended=false

---

## Recommendation

**No further same-question cycles justified.** The PIVOT_WITHIN_MISSION characterization is complete.

**Next Steps** (require Corpus Lane resumption):
1. BGE/bger ID mapping production
2. Parquet generation for 2024-2026 (15,536 decisions)
3. Section extraction at 174k scale
4. 174k dense embedding computation and evaluation

**Product Integration Contract (Post-v1.0):**
- v1.0: TF-IDF citation hybrids as primary navigation mode (beats semantic baseline JP 0.78 vs 0.43)
- v1.1+: Dense embedding integration for citation-heritage view and cross-lingual view

---

*Generated by Legal Distance Lane | Factory Direction v35 | Run 37759438343*