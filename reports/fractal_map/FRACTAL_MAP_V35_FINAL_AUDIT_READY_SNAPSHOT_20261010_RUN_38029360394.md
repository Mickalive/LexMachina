# FRACTAL MAP LANE — V35 FINAL AUDIT-READY SNAPSHOT

**Run ID:** 38029360394
**Timestamp:** 2026-10-10
**Factory Direction Version:** 35
**Lane:** fractal-map
**Evidence Tier:** ACCEPTED
**Cycle Status:** BLOCKED_ON_DEPENDENCIES
**Continue Recommended:** false
**Audit Ready:** true

---

## EXECUTIVE SUMMARY

The fractal-map lane deliverable for factory direction v35 is **COMPLETE, VERIFIED, AND AUDIT-READY**.

All discriminating experiments for the v34/v35 question ("Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves") have been executed, validated, and preserved. The lane is correctly BLOCKED_ON_DEPENDENCIES on upstream legal-distance 174k dense embeddings, which in turn depend on corpus lane resumption.

**No orchestration/validation failure exists in the fractal-map lane.** The V28-pattern control plane mounting defect persists in `/tmp/lex_control/state/factory_direction.json` (shows RUN at line 16) while workspace state (`state/fractal_map.json`) and `state/factory_direction.json` correctly show BLOCKED_ON_DEPENDENCIES. This is a persistent infrastructure defect in the control plane mounting/persistence mechanism, NOT a lane failure.

---

## ACCEPTED EVIDENCE SUMMARY

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL AT 174k (3 modes, 6/8 PASS)

| Mode | Scale | Fine Branch Purity | Status |
|------|-------|-------------------|--------|
| `cited_decisions_tfidf` | 173,963 (full) | 0.906-0.930 | ✅ PASS |
| `cited_outcome_hybrid_0.5` | 173,963 (full) | 0.906-0.930 | ✅ PASS |
| `cited_outcome_hybrid_0.7` | 173,963 (full) | 0.906-0.930 | ✅ PASS |
| `regeste_tfidf` | 90,461 (52%) | 0.609-0.685 | ✅ PASS |
| `full_text_tfidf_light` | 90,461 (52%) | 0.609-0.685 | ✅ PASS |
| `regeste_full_text_hybrid_0.5` | 90,461 (52%) | 0.609-0.685 | ✅ PASS |
| `regeste_full_text_hybrid_0.7` | 90,461 (52%) | — | ⚠️ Below threshold |
| `outcome_tfidf` | 90,461 (52%) | — | ⚠️ Below threshold |

**Artifacts:** `results/fractal_map/hierarchical_v1_174k_tfidf/`
- `hierarchical_v1_174k_tfidf_verdict_20261001_102442.json` — full protocol verdict
- `hierarchical_v1_frozen_spec.json` — frozen protocol specification

### 2. Multi-Level Recursive Protocol — STRUCTURALLY VALIDATED, CALIBRATION FAILS (Valid Negative)

| Criterion | Result |
|-----------|--------|
| Perfect nesting (≥0.95) | ✅ PASS (nesting=1.0 for constrained hierarchical) |
| Zero fragmentation | ✅ PASS |
| Monotonic refinement | ✅ PASS |
| Calibration (thresholds for signal density) | ❌ FAIL — thresholds too aggressive for TF-IDF signal density |

**Artifacts:**
- `results/fractal_map/multi_level_protocol_174k_tfidf/` — structural validation
- `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/` — calibration failure (valid negative preserved)

### 3. 12k Dense Embeddings Preparatory Validation — PASS

| Criterion | Result |
|-----------|--------|
| 4-level hierarchy | ✅ PASS |
| Nesting = 1.0 | ✅ PASS |
| Zero fragmentation | ✅ PASS |
| Hierarchical builder (39 coarse → 412 fine) | ✅ PASS |
| Frozen v26 flat Leiden FAIL | ✅ CONFIRMED (expected) |

**Artifacts:** `results/fractal_map/dense_12k_prep_validation/`
- `multi_level_12k_results.json` — full validation results
- `center_projected_12k_hierarchical/` — hierarchical artifacts
- `v26_12k_dense_verdict.json` — flat baseline failure confirmed

### 4. 144k Checkpoint — SCALE EXTRAPOLATION VALIDATED

| Metric | Value |
|--------|-------|
| Decisions | 144,443 (years 2000-2021, 22/26 years) |
| Fine branch purity | ~0.97 |
| Branch improvement rate | 0.48-0.65 |
| Area improvement rate | 0.75-0.76 |
| Strict nesting | ≥0.99 |
| Fine singletons | ~4-5% |

**Artifact:** `results/fractal_map/144k_checkpoint_validation/144k_validation_144443decisions.json`

### 5. Dense Embedding Integration Contract v34 — FROZEN

**Primary Product Mode:** TF-IDF citation hybrids (cited_decisions_tfidf, cited_outcome_hybrid_0.5, cited_outcome_hybrid_0.7) — Jurist Preference 0.78-0.79

**Complementary Views (4):**

| View | Acceptance Criterion | Evidence Status |
|------|---------------------|-----------------|
| Citation Heritage | AUC > 0.75 | ✅ PASSED at 144k (0.79-0.85) |
| Cross-Lingual (Sachverhalt) | cross_lang_same_branch > 0.20 | ✅ PASSED at 144k (0.28) |
| Cross-Lingual (Dispositiv) | cross_lang_same_branch > 0.10 | ✅ PASSED at 144k (0.15) |
| Cross-Lingual (Erwaegungen) | cross_lang_same_branch > 0.10 | ❌ FAILED (0.09) — excluded |
| Linear Hybrid Complement | PASS adversarial gates at w=0.3-0.4 | ✅ PASSED (JP 0.61-0.67, LD 0.65-0.75) |

**Artifact:** `results/fractal_map/dense_embeddings_integration_contract_v34.json`

### 6. NESTING_METRIC_DEFECT_v1 — ENFORCED

- 7 compressed-family modes prohibited from claiming nesting_score ≥ 0.99 without scope annotation
- nesting_score=1.0 citeable ONLY for 1000-scale and 12k-scale by-construction modes with explicit scope annotation
- Automated enforcement in fractal-map pipeline

**Artifact:** `results/fractal_map/nesting_metric_defect_v1_audit.json`

### 7. Product Readiness — OPERATIONAL

- 3 production modes at full 173,963 decisions
- 16/16 scale simulation tests PASS
- WebGL pipeline <3s
- Metadata: `results/fractal_map/multi_level_protocol_174k_tfidf/metadata_174k_aligned.json`

---

## CRITICAL FINDINGS (Preserved from State)

| Finding | Status |
|---------|--------|
| TF-IDF hierarchical_v1: 6/8 PASS at 174k | ✅ ACCEPTED |
| Multi-level protocol: structurally valid, calibration FAILS | ✅ VALID NEGATIVE |
| Calibration FAILS on TF-IDF — thresholds too aggressive | ✅ VALID NEGATIVE |
| Dense integration contract v34: FROZEN with 4 complementary views | ✅ FROZEN |
| Scale extrapolation validated at 144k checkpoint | ✅ VALIDATED |
| NESTING_METRIC_DEFECT_v1 enforced | ✅ ENFORCED |
| **BLOCKER**: Upstream dense embeddings need corpus lane resumption | 🔴 BLOCKED |
| Dense embeddings FAIL jurist preference at ALL scales (JP 0.05-0.43) | ✅ ACCEPTED |
| TF-IDF citation hybrids DOMINATE jurist preference (JP 0.78-0.79) | ✅ ACCEPTED |
| Dense EXCELS at citation heritage (AUC 0.79-0.85) & cross-lingual | ✅ ACCEPTED |
| True OOS JuristPref ceiling ~0.53 < 0.7 factory target | ✅ ACCEPTED |
| v18 coarse hierarchy NEGATIVE (max purity 0.65 < 0.7) | ✅ ACCEPTED |
| V28 control plane mounting defect persists in /tmp/lex_control | ⚠️ INFRASTRUCTURE DEFECT |

---

## TEST SUITE VERIFICATION (Run 38029360394)

| Test Suite | Passed | Skipped | Failed | Total |
|------------|--------|---------|--------|-------|
| test_verify.py | 185 | 1 | 0 | 186 |
| test_pipeline_readiness.py | 14 | 0 | 0 | 14 |
| test_zoom_quality_174k_eval.py | 4 | 0 | 0 | 4 |
| test_zoom_quality_174k_v26_eval.py | 7 | 0 | 0 | 7 |
| test_12k_dense_comprehensive.py | 10 | 0 | 0 | 10 |
| test_dense_embeddings_infrastructure.py | 14 | 1 | 0 | 15 |
| test_scale_dependency.py | 11 | 0 | 0 | 11 |
| **GRAND TOTAL** | **245** | **2** | **0** | **247** |

---

## BLOCKERS (Require Factory Director Action)

1. **Corpus Lane Resumption Required:**
   - BGE/bger ID mapping production (canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists)
   - Parquet generation for years 2022-2026 (29,520 decisions missing from pinned 2026 snapshot)
   - Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation density

2. **Legal-Distance Lane:** 174k dense embeddings computation (currently ~3/26 years complete, ~19,441 decisions, ~11%)

---

## RECOMMENDATION

**continue_recommended = false** — No further same-question cycles justified. All discriminating experiments for v34/v35 question COMPLETE.

**Factory Director Action Required:** Resume corpus lane for the three blockers above. Once corpus lane delivers, legal-distance can compute 174k dense embeddings, unblocking fractal-map multi-view deployment per the frozen v34 contract.

---

## EVIDENCE REFERENCES

- `results/fractal_map/hierarchical_v1_174k_tfidf/` — TF-IDF hierarchical production modes at 174k
- `results/fractal_map/multi_level_protocol_174k_tfidf/` — Multi-level recursive protocol validation
- `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/` — Calibration FAILURE (valid negative)
- `results/fractal_map/dense_12k_prep_validation/` — 12k dense embeddings preparatory validation (PASS)
- `results/fractal_map/144k_checkpoint_validation/` — Scale extrapolation validation
- `results/fractal_map/144k_multi_level_validation/` — 144k multi-level validation
- `results/fractal_map/hierarchical_map_174k/` — 174k hierarchical map products
- `results/fractal_map/product_integration_174k/` — 16/16 scale tests PASS
- `results/fractal_map/dense_embeddings_integration_contract_v34.json` — Frozen dense contract
- `results/fractal_map/nesting_metric_defect_v1_audit.json` — Nesting metric defect enforcement
- `reports/fractal_map/CONSTRAINED_HIERARCHICAL_174K_FULL_VALIDATION_20260926.md`
- `reports/fractal_map/SCALE_VALIDATION_EXTRAPOLATION_v28.md`

---

## PROVENANCE

This snapshot was generated from an operational resume of persisted producer snapshot (run 38028835493) with fresh independent re-verification in a clean environment with fresh dependency install. All 7 test suites PASS (245 passed, 2 skipped, 0 failed).

**Previous verification runs confirming identical state:**
- 37951129930, 37952999658, 37954297692, 37956182695, 37957990046, 37971101560, 37972411481, 37989790872, 37990082999, 37992362367, 37996442507, 37997353959, 38002296609, 38003948885, 38004888068, 38016248186, 38016675847, 38017982357, 38026475551, 38027023776

All confirm: **Lane deliverable VERIFIED AND AUDIT-READY.**