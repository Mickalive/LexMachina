# LEGAL DISTANCE LANE — FINAL AUDIT VERIFICATION (GitHub Run 37725797175)

## Operational Resume from Persisted Producer Snapshot
- **Resume source run**: 37725225003
- **Current run**: 37725797175
- **Date**: 2026-10-08
- **Factory direction version**: 35
- **Lane status**: BLOCKED_ON_DEPENDENCIES (correct)
- **Continue recommended**: false (no further same-question cycles justified)

---

## Verification Results

### Test Suite Execution: ALL PASSED
- **test_complementary_role_v34.py**: 8/8 assertions PASSED
- **test_v29_final_results.py**: 15/15 assertions PASSED
- **Total**: 23/23 tests PASSED

### Scale Characterization Experiment: REPRODUCED
**Experiment**: `characterize_dense_complementary_views.py` on 12k ACCEPTED dense embeddings (2000-2002)

**IDENTICAL scale-dependent patterns confirmed**:
| Metric | Small Scale (1K) | Full Scale (12.5K) | Pattern |
|--------|------------------|-------------------|---------|
| Cross-lingual alignment | 0.656 | 0.957 | Inflation at small homogeneous scale |
| Legal area purity | 0.609 | 0.475 | Degradation with scale |
| Branch k-NN @1 | 0.957 | 0.992 | Stable >0.99 at all scales |
| Linear hybrid jurist proxy | >0.99 | >0.99 | PASS at all weights |

---

## PIVOT_WITHIN_MISSION Characterization: COMPLETE

### Three Complementary Dense Embedding Views (Necessary & Sufficient)

| View | Minimal Scale | Evidence | Acceptance | Status |
|------|---------------|----------|------------|--------|
| **Citation Heritage** | 21yr / 137k (2000-2020) | center_projected_64 AUC 0.77-0.85 > TF-IDF 0.71-0.74 | AUC > 0.75 | ✅ PASSED |
| **Section Cross-Lingual** | 1K sample (sections) | Sachverhalt 0.282 > 0.2, Dispositiv 0.150 > 0.1, Erwaegungen 0.094 < 0.1 | cross_lang_same_branch thresholds | ✅ Sachverhalt/Dispositiv PASS, ❌ Erwaegungen FAIL |
| **Linear Hybrid Complement** | 19yr / 122k (2000-2018) | w=0.3-0.4 PASS adversarial, JP 0.61-0.67 < TF-IDF 0.78-0.79 | PASS both gates | ✅ PASSED (complement only) |

### Two-Mode Tradeoff: FUNDAMENTAL & REPRODUCED
| Mode | JuristPref | LangDom | CiteIndep | Role |
|------|------------|---------|-----------|------|
| TF-IDF Citation Hybrids | ~0.78 | ~0.48 | ~0.14 | PRIMARY (product default) |
| Dense Embeddings (center_projected) | ~0.05-0.43 | ~0.83-0.98 | ~0.37 | COMPLEMENTARY |
| Linear Hybrids (w=0.3-0.4) | ~0.61-0.67 | ~0.58-0.80 | intermediate | COMPLEMENTARY |

**No single representation dominates all three metrics at any scale.**

### True OOS JuristPref Ceiling: CONFIRMED ~0.53 < 0.7 Factory Target
- Verified via v8 holdout zero-shot validation
- TF-IDF baseline JP=0.78 evaluated on SVD-fitted data (known leakage ~0.015-0.020)
- No representation achieves factory target under true out-of-sample conditions

---

## Data Blockers: PERSIST (Require Corpus Lane Resumption)

| Blocker | Impact | Resolution |
|---------|--------|------------|
| **bge_/bger_ ID mapping** | No mapping between published (bge_) and unpublished (bger_) decision IDs | Corpus lane: create canonical mapping |
| **Parquet 2024-2026** | ~15.5k decisions missing embeddings | Corpus lane: generate parquet for 2024-2026 |
| **174k section extraction** | Sachverhalt/Erwaegungen/Dispositiv not extracted at full scale | Corpus lane: run section extraction at 174k |

**Note**: 2021-2023 embeddings EXIST and PASS citation heritage quality checks (AUC > 0.75 at 24yr/158k with 730 positive pairs). Only 2024-2026 are genuinely missing.

---

## Orchestration/Validation Failure Diagnosis

**Root Cause**: Factory Director control-plane sync issue
- `factory_direction.json` v35 shows `legal-distance` status = `"RUN"`
- Lane state (`legal-distance.json`) shows `cycle_status` = `"BLOCKED_ON_DEPENDENCIES"` with `continue_recommended = false`
- **Scientific integrity**: UNAFFECTED — all evidence preserved, all tests pass
- **Resolution**: Factory direction should align with lane state (BLOCKED_ON_DEPENDENCIES)

---

## Factory Direction v34/v35 Strategic Pivot: FULLY EXECUTED

Per audit CYCLE_37090665528 (gate=PASS, safe_to_integrate=true):
1. **TF-IDF citation hybrids** = PRIMARY product mode (jurist preference, branch clustering) — beats semantic baseline JP 0.78 vs 0.43
2. **Dense embeddings** = COMPLEMENTARY modes (citation heritage view, cross-lingual view, hybrid complement)
3. **Data blockers** moved to corpus lane resumption criteria
4. **No new Frontier team** justified — portfolio v7 confirmed (both teams TERMINATED)

---

## Evidence Preservation

All ACCEPTED evidence preserved in:
- `state/legal-distance.json` (machine-readable, updated with run 37725797175)
- `results/legal_distance/dense_complementary_characterization/scale_characterization_results.json`
- `results/legal_distance/174k_dense_embeddings/` (all checkpoints and evaluations)
- `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/` (174k formal suite)
- Test files: `tests/legal_distance/test_complementary_role_v34.py`, `test_v29_final_results.py`

---

## Audit Readiness: CONFIRMED ✅

- [x] All tests pass (23/23)
- [x] Scale characterization reproduced with identical patterns
- [x] PIVOT_WITHIN_MISSION characterization complete at max available evaluated scale
- [x] Three complementary views characterized at minimal sufficient scales
- [x] Two-mode tradeoff fundamental reproduced across all scales
- [x] True OOS ceiling confirmed
- [x] Data blockers correctly identified and documented
- [x] Lane state machine-readable and consistent
- [x] No further same-question cycles justified (`continue_recommended = false`)
- [x] Orchestration discrepancy diagnosed and documented

**Snapshot audit-ready for GitHub run 37725797175.**