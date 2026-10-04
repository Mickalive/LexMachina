# FRACTAL MAP V34 FINAL AUDIT-READY SNAPSHOT

**GitHub Run:** 37226271947
**Timestamp:** 2026-10-04T22:00:00.000000Z
**Lane:** fractal-map
**Factory Direction Version:** 34
**Evidence Tier:** ACCEPTED
**Cycle Status:** BLOCKED_ON_DEPENDENCIES
**Continue Recommended:** false

---

## Summary

This verification run confirms the fractal-map lane deliverable is **COMPLETE and AUDIT-READY** for factory direction v34. All discriminating experiments for the v34 question have been completed. The lane is correctly `BLOCKED_ON_DEPENDENCIES` on upstream legal-distance 174k dense embeddings, which requires corpus lane resumption for BGE/bger ID mapping + parquet 2022-2026 + section extraction at 174k scale.

---

## Factory Direction v34 Question (Fractal Map)

> **Question:** "Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."

**STATUS: ANSWERED — NO FURTHER SAME-QUESTION CYCLES JUSTIFIED**

---

## Accepted Evidence Summary

### 1. TF-IDF Hierarchical Production Modes at 174k — OPERATIONAL & FROZEN

**3 Production Modes at Full 173,963 Decisions:**

| Mode | Fine Branch Purity | Coarse Clusters | Fine Clusters | Status |
|------|-------------------|-----------------|---------------|--------|
| `full_text_tfidf_light` | **0.930** | 19 | 365 | **PASS** (production) |
| `regeste_full_text_hybrid_0.5` | 0.906 | — | — | **PASS** (production) |
| `regeste_full_text_hybrid_0.7` | 0.930 | — | — | **PASS** (production) |

- **Protocol:** hierarchical_v1 (2-level: coarse → fine)
- **Nesting:** 1.0 (perfect) for all modes
- **Fragmentation:** Zero (no singletons at fine level)
- **Zoom Coherence:** PASS (improvement_rate 0.48-0.75)
- **Scale Tests:** 16/16 PASS at 174k
- **WebGL Pipeline:** <3s render time

### 2. Multi-Level Recursive Protocol (4+ Levels) — FAILS at 174k

- **All 5 TF-IDF modes FAIL** the multi-level (4+ level) protocol at 174k
- Level 0 (root): Single cluster
- Levels 1-3: Multiple clusters but protocol fails on level2 `area_purity` threshold (~0.134 < 0.15)
- **NOT cluster collapse at all levels** — valid negative result, correctly preserved
- **Do not conflate** with hierarchical_v1 (2-level) production protocol which PASSES

### 3. Calibration — FAILS on TF-IDF

- Thresholds too aggressive for TF-IDF signal density
- Calibrated protocol does not improve over frozen v1
- Negative result correctly recorded

### 4. Dense Embedding Integration Contract v34 — DEFINED & FROZEN

**Four Complementary Views (TF-IDF citation hybrids remain PRIMARY at JP 0.78-0.79):**

| View | Acceptance Criterion | Status |
|------|---------------------|--------|
| Citation Heritage | AUC > 0.75 | **PASSED** at 144k (AUC 0.79-0.85) |
| Cross-Lingual Sachverhalt | cross_lang_same_branch > 0.20 | **PASSED** at 144k (0.28) |
| Cross-Lingual Dispositiv | cross_lang_same_branch > 0.10 | **PASSED** at 144k (0.15) |
| Cross-Lingual Erwaegungen | cross_lang_same_branch > 0.10 | **FAILED** (0.09) — excluded |
| Linear Hybrid Complement | PASS adversarial gates at w=0.3-0.4 | **PASSED** (JP 0.61-0.67) — below TF-IDF baseline |

**Required Dense Modes:** `center_projected_64dim`, `center_projected_128dim`, `center_projected_768dim`

### 5. Preparatory Dense Validation — COMPLETE

- **12k dense:** Multi-level protocol PASS (4 levels, nesting=1.0, zero fragmentation), hierarchical builder SUCCESS (39 coarse → 412 fine), frozen v26 flat Leiden FAIL (expected)
- **144k checkpoint (22/26 years, 2000-2021):** Hierarchical builder (2-level) scale extrapolation validated — fine_branch_purity ~0.97, improvement_rate 0.48-0.76, strict_nesting ≥0.99, fine_singletons ~4-5%

### 6. NESTING_METRIC_DEFECT_v1 — ENFORCED

- 7 compressed-family modes had `nesting_score ≥ 0.99` without scope annotation
- `min_cluster_size` enforces `nesting=1.0` by construction
- Enforcement active for all outputs

---

## Test Results (This Run)

| Test Suite | Total | Passed | Skipped |
|------------|-------|--------|---------|
| test_verify | 186 | 186 | 0 |
| test_pipeline_readiness | 14 | 14 | 0 |
| test_zoom_quality_174k_eval | 4 | 4 | 0 |
| test_zoom_quality_174k_v26_eval | 7 | 7 | 0 |
| test_dense_embeddings_infrastructure | 15 | 14 | 1 |
| test_scale_dependency | 11 | 11 | 0 |
| test_12k_dense_comprehensive | 10 | 10 | 0 |
| **GRAND TOTAL** | **247** | **245** | **2** |

---

## Critical Findings (Preserved)

1. **TF-IDF hierarchical_v1 protocol 6/8 PASS** — Text-based modes at full 174k achieve fine_branch_purity 0.906-0.930; citation-based at 52% scale achieve 0.609-0.685; outcome_tfidf and regeste_tfidf FAIL as expected (weak signal / missing branch labels)

2. **Multi-level recursive protocol FAILS at 174k** — All 5 TF-IDF modes FAIL the multi-level (4+ level) protocol at 174k: Level 0 (root) has single cluster; Levels 1-3 have multiple clusters but protocol fails on level2 area_purity threshold (~0.134 < 0.15), NOT cluster collapse at all levels. Valid negative result, correctly preserved.

3. **Calibration FAILS on TF-IDF** — Thresholds too aggressive for TF-IDF signal density; calibrated protocol does not improve over frozen v1; negative result correctly recorded

4. **Dense integration contract frozen** — Four complementary view criteria defined with acceptance thresholds; validated against 12k/144k evidence where available

5. **Scale extrapolation validated** — 144k checkpoint confirms hierarchical builder (2-level) fine_branch_purity ~0.97, improvement rates healthy, nesting ≥0.99, fine singletons ~4-5%. Note: These metrics describe the hierarchical builder (2-level), NOT the multi-level recursive protocol (which FAILS at 144k).

6. **Nesting metric defect enforced** — 7 compressed-family modes had nesting_score≥0.99 without scope annotation; min_cluster_size enforces nesting=1.0 by construction; enforcement active for all outputs

7. **Blocker upstream data** — Legal-distance 174k dense embeddings require BGE/bger ID mapping + parquet 2022-2026 from corpus lane; no fractal-map lane defect exists

---

## Factory Director Action Required

1. **Update factory_direction.json on main** to `fractal-map.status=BLOCKED_ON_DEPENDENCIES` (currently incorrectly shows "RUN")

2. **Resume corpus lane** for:
   - BGE/bger ID mapping production (canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists)
   - Parquet generation for years 2022-2026 (29,520 decisions missing from pinned 2026 snapshot)
   - Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation density

---

## Evidence References

- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json`
- `results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json`
- `results/fractal_map/multi_level_protocol_174k_tfidf/`
- `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/`
- `results/fractal_map/12k_dense_comprehensive/`
- `results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json`
- `results/fractal_map/nesting_metric_defect_v1_audit.json`
- `results/fractal_map/dense_embeddings_integration_contract_v34.json`
- Multiple audit reports in `reports/fractal_map/`
- Test suites in `tests/fractal_map/`

---

## Next Recommendation

**No further same-question cycles justified.** The fractal-map lane has answered the factory direction v34 question completely. The lane is blocked on upstream dependencies (corpus → legal-distance → fractal-map). When legal-distance delivers 174k dense embeddings passing all four complementary view acceptance criteria, the successor action is to integrate dense embedding complementary views into fractal-map multi-view product deployment per the frozen contract v34.