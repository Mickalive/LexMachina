# LEGAL DISTANCE LANE — FINAL AUDIT VERIFICATION
## GitHub Run: 37707256864 | Factory Direction v35 | 2026-10-08

---

## Executive Summary

**STATUS: FINAL_AUDIT_VERIFICATION_COMPLETE — SNAPSHOT AUDIT-READY**

This run completes the operational resume from persisted producer snapshot of run 37706462845. All validation tests pass, the PIVOT_WITHIN_MISSION characterization is complete at maximum available evaluated scale, and the lane deliverable is finalized with `audit_ready: true`, `continue_recommended: false`, `cycle_status: BLOCKED_ON_DEPENDENCIES`.

**Orchestration/Validation Failure Diagnosis**: Prior workflow failures were due to **data dependency blockers** (bge_/bger_ ID mapping, missing parquet 2024-2026, 174k section extraction), **NOT scientific failure**. All valid completed work is preserved.

---

## Test Results — All Passed

| Test Suite | Tests | Status |
|------------|-------|--------|
| `test_complementary_role_v34.py` | 8/8 | ✅ PASSED |
| `test_v29_final_results.py` | 15/15 | ✅ PASSED |
| `characterize_dense_complementary_views.py` | Scale characterization | ✅ REPRODUCED |

### `test_complementary_role_v34.py` — 8/8 Assertions PASSED

1. **Citation Heritage Superiority** — Dense AUCs: raw_768dim=0.7946, cp64=0.7922, cp128=0.7916, cp768=0.7941 (all > 0.75). Dense beats TF-IDF citation baseline (0.71-0.74). cp64 similarity gap 6.5x raw.

2. **Citation Heritage Minimal Scale** — 21yr (137k decisions): raw AUC=0.8455, cp64 AUC=0.8182, n_pairs=100 ≥ threshold.

3. **Section Cross-Lingual Hierarchy** — Sachverhalt (gap=0.187, cross_lang=0.282) > Dispositiv (gap=0.397, cross_lang=0.150) > Erwaegungen (gap=0.452, cross_lang=0.094). All center projection improvements >10%.

4. **Linear Hybrid Optimal Weight** — w=0.3, 0.4 PASS both adversarial gates; w=0.4 JP=0.6725, w=0.3 JP=0.6715; both below TF-IDF baseline 0.784; cross-lingual improvement 0.160 vs TF-IDF 0.124.

5. **Two-Mode Tradeoff Fundamental** — Dense: JP=0.426, LangDom=0.832; TF-IDF: JP=0.784, LangDom=0.483; Hybrid w=0.4: JP=0.672, LangDom=0.654 (intermediate). No single representation dominates all three metrics.

6. **True OOS Ceiling** — Holdout validation confirms OOS JuristPref < 0.6, well below 0.7 factory target.

7. **TF-IDF 174k Primary Validated** — LangDom=0.5785 PASS (<0.85), beats semantic baseline.

8. **Data Blockers Identified** — Completed years=24 (2000-2023), Failed=['2024','2025','2026'], Missing=['2024','2025','2026']. 2021-2023 embeddings EXIST and PASS quality checks.

### `test_v29_final_results.py` — 15/15 Assertions PASSED

All section cross-lingual (5), scale evidence (4), fundamental blockers (3), two-mode tradeoff (3) tests pass.

### `characterize_dense_complementary_views.py` — Scale Characterization REPRODUCED

**On 12k ACCEPTED dense embeddings (2000-2002):**

| Metric | Scale 1K | Scale 12.5K | Pattern |
|--------|----------|-------------|---------|
| Cross-lingual same_branch | 0.656 | 0.957 | **Inflation at small homogeneous scale** |
| Legal area purity | 0.609 | 0.475 | **Degradation with scale** |
| Branch k-NN @1 | 0.957 | 0.992 | **Stable >0.99 at all scales** |
| Linear hybrid JP (all weights) | >0.99 | >0.99 | **PASS jurist proxy at all weights** |

**IDENTICAL scale-dependent patterns** to full-corpus evaluations confirmed.

---

## PIVOT_WITHIN_MISSION Characterization — COMPLETE

### NEW QUESTION ANSWERED (Factory Direction v34)
> *What minimal dense embedding scale and which specific dense modes are necessary and sufficient for the product's non-jurist-preference views?*

### ANSWER: Three Complementary Modes at Characterized Minimal Scales

| View | Minimal Scale | Key Metric | Status |
|------|---------------|------------|--------|
| **Citation Heritage** | 21yr / 137k (2000-2020) | cp64 AUC > 0.75 (0.77-0.85 at 21-24yr) | ✅ PASSED |
| **Section Cross-Lingual** | 1K sample (sections) | Sachverhalt cross_lang=0.282>0.2 ✓, Dispositiv=0.150>0.1 ✓, Erwaegungen=0.094<0.1 ✗ | ✅ Sachverhalt/Dispositiv PASSED |
| **Linear Hybrid Complement** | 19yr / 122k (2000-2018) | w=0.3-0.4 PASS adversarial, JP=0.61-0.67 | ✅ PASSED adversarial, BELOW TF-IDF |

### Two-Mode Tradeoff — FUNDAMENTAL
- **TF-IDF Citation Hybrids** = PRIMARY (LangDom~0.48, JP~0.78, CiteIndep~14%)
- **Semantic Embeddings** = COMPLEMENTARY (LangDom~0.83-0.98, JP~0.05-0.43, CiteIndep~37%)
- **Linear Hybrids** = INTERMEDIATE (LangDom~0.58-0.80, JP~0.61-0.67)
- **NO single representation dominates JP + LangDom + CiteIndep at any scale**

### Accepted Negative Findings (First-Class Results)
- True OOS JuristPref ceiling ~0.53 < 0.7 factory target
- v18 coarse hierarchy NEGATIVE (max branch purity 0.65 < 0.7)
- Citation heritage recall@10 max 0.0066 (ranking signal, not retrieval)
- Dense embeddings FAIL jurist gate at ALL scales (JP 0.05-0.43)
- Cross-language retrieval recall@10 max 0.11 < 0.2 threshold

---

## Data Blockers — Require Corpus Lane Resumption

| Blocker | Impact | Resolution |
|---------|--------|------------|
| bge_ (published) ↔ bger_ (unpublished) ID mapping | Cannot align 174k dense embeddings with evaluation metadata | Corpus lane resumption required |
| Parquet 2024-2026 (15,536 decisions missing) | Cannot compute 174k dense embeddings | Corpus lane resumption required |
| Section extraction at 174k scale | Cross-lingual section alignment needs all sections | Corpus lane resumption required |

**Note**: 2021-2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75 at 24yr/158k with 730 pairs). Only 2024-2026 genuinely missing.

---

## Factory Direction v34/v35 Strategic Pivot — FULLY EXECUTED

| Lane | Status | Alignment |
|------|--------|-----------|
| **Corpus** | PAUSE | Resumption criteria: bge_/bger_ mapping + parquet 2022-2026 + 174k section extraction |
| **Legal-Distance** | BLOCKED_ON_DEPENDENCIES | PIVOT_WITHIN_MISSION complete; continue_recommended=false |
| **Fractal-Map** | RUN | TF-IDF modes OPERATIONAL at 174k; blocked on dense embeddings for multi-view |
| **Evaluation** | RUN | TF-IDF 174k formal suite COMPLETE; dense acceptance criteria defined |
| **Product** | PAUSE | v1.0 RELEASED with TF-IDF primary; dense integration v1.1+ |

**Product Defaults Frozen**:
- `PRODUCT_SERVING_DEFAULT=cited_outcome_hybrid_0.5_174k`
- `COMBINATION_MODE=linear_hybrid05_concat`
- `DEFAULT_MAP_MODE=center_projected_64dim_hierarchical`

---

## Verification Artifacts

| Artifact | Path |
|----------|------|
| State file | `state/legal-distance.json` |
| Test results | `tests/legal_distance/test_complementary_role_v34.py`, `tests/legal_distance/test_v29_final_results.py` |
| Scale characterization | `results/legal_distance/dense_complementary_characterization/scale_characterization_results.json` |
| Evidence refs | 31 entries in state file (see `evidence_refs`) |

---

## Recommendation

**NO FURTHER SAME-QUESTION CYCLES JUSTIFIED.**

The PIVOT_WITHIN_MISSION characterization is complete at the maximum available evaluated scale. The lane is correctly `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false`. All valid completed work is preserved. The snapshot is audit-ready.

**Next action**: Factory Director to resume Corpus lane per documented blockers, then re-evaluate dense embedding deployment at 174k.

---

*Verification completed: 2026-10-08T00:00:00.000000Z*
*Operational resume from: run 37706462845*
*Lane: legal-distance | Factory Direction: v35*