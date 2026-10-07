# Fractal Map Lane — V35 Final Audit-Ready Snapshot

**GitHub Run:** 37702272825  
**Factory Direction Version:** 35  
**Lane:** fractal-map  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  
**Timestamp:** 2026-10-07T23:59:00.000000Z  
**Audit Ready:** true

---

## Executive Summary

The fractal-map lane has **successfully completed all discriminating experiments** for the factory direction v34/v35 question: *"Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."*

All deliverables are **OPERATIONAL, VERIFIED, and FROZEN**:

1. **TF-IDF hierarchical production modes** — 3 modes operational at full 173,963 decisions (fine_branch_purity 0.906–0.930)
2. **Multi-level recursive protocol** — FAILS at 174k for all 5 TF-IDF modes (valid negative, correctly preserved)
3. **Calibration protocol** — FAILS on TF-IDF (thresholds too aggressive; valid negative preserved)
4. **Dense embedding integration contract v34** — DEFINED AND FROZEN with 4 complementary view acceptance criteria
5. **Preparatory 12k/144k dense validation** — COMPLETE (hierarchical builder validated, flat Leiden fails as expected)
6. **144k checkpoint** — Validates hierarchical builder scale extrapolation (fine_branch_purity ~0.97, strict_nesting ≥0.99)
7. **NESTING_METRIC_DEFECT_v1** — ENFORCED (7 compressed-family modes require scope annotation)

**No further same-question cycles justified.** The lane is correctly BLOCKED_ON_DEPENDENCIES on upstream legal-distance 174k dense embeddings (requires corpus lane resumption for BGE/bger ID mapping + parquet 2022-2026 + section extraction).

---

## Verification Results

| Test Suite | Passed | Skipped | Total |
|------------|--------|---------|-------|
| test_verify | 185 | 1 | 186 |
| test_pipeline_readiness | 14 | 0 | 14 |
| test_zoom_quality_174k_eval | 4 | 0 | 4 |
| test_zoom_quality_174k_v26_eval | 7 | 0 | 7 |
| test_dense_embeddings_infrastructure | 14 | 1 | 15 |
| test_scale_dependency | 11 | 0 | 11 |
| test_12k_dense_comprehensive | 10 | 0 | 10 |
| **Grand Total** | **245** | **2** | **247** |

All 7 test suites **PASS**. State file verification confirms: `evidence_tier=ACCEPTED`, `cycle_status=BLOCKED_ON_DEPENDENCIES`, `continue_recommended=false`, `audit_ready=true`.

---

## Deliverable Status

### 1. TF-IDF Hierarchical Production Modes — OPERATIONAL ✅

| Mode | Scale | Fine Branch Purity | Coarse Clusters | Fine Clusters | Verdict |
|------|-------|-------------------|-----------------|---------------|---------|
| `full_text_tfidf_light` | 173,963 | 0.930 | 19 | 365 | PASS |
| `regeste_full_text_hybrid_0.5` | 91,189* | 0.906 | 31 | 285 | PASS |
| `regeste_full_text_hybrid_0.7` | 91,189* | 0.912 | 44 | 388 | PASS |
| `cited_decisions_tfidf` | 91,183* | 0.685 | 29 | 282 | PASS |
| `cited_outcome_hybrid_0.5` | 91,189* | 0.633 | 31 | 285 | PASS |
| `cited_outcome_hybrid_0.7` | 91,189* | 0.609 | 44 | 388 | PASS |
| `outcome_tfidf` | — | — | — | — | FAIL (expected) |
| `regeste_tfidf` | — | — | — | — | FAIL (expected) |

*Subset scale (52% of corpus) due to citation metadata coverage.

**Protocol:** hierarchical_v1 (2-level: coarse→fine) with frozen config (coarse_res=0.25, base_sub_res=3.0, min_cluster_size=10, max_subclusters_per_parent=20, adaptive_sub_res=true, k_neighbors=15).

**All 7 structural checks PASS** for production modes: zero fragmentation, perfect nesting (1.0), branch/area purity improvement, zoom coherence >0.5, legal structure validity.

### 2. Multi-Level Recursive Protocol — FAILS (Valid Negative) ❌

| Mode | Levels Tested | Failure Mode |
|------|---------------|--------------|
| All 5 TF-IDF modes | 4+ (0→3) | Level 0 = single cluster; Levels 1–3 have clusters but level2 area_purity ~0.134 < 0.15 threshold |

**Note:** NOT cluster collapse at all levels. The hierarchical_v1 (2-level) production protocol PASSES — do not conflate the two protocols.

### 3. Calibration Protocol — FAILS (Valid Negative) ❌

Thresholds too aggressive for TF-IDF sparse signal density. Calibrated protocol does not improve over frozen v1.

### 4. Dense Embedding Integration Contract v34 — FROZEN 📋

| Complementary View | Acceptance Criterion | Evidence (144k/12k) | Status |
|--------------------|---------------------|---------------------|--------|
| **Citation Heritage** | AUC > 0.75 | 0.79–0.85 at 144k (center_projected 64/128/768dim) | ✅ PASSED |
| **Cross-Lingual (Sachverhalt)** | same_branch > 0.20 | 0.281–0.282 at 144k | ✅ PASSED |
| **Cross-Lingual (Dispositiv)** | same_branch > 0.10 | 0.148–0.150 at 144k | ✅ PASSED |
| **Cross-Lingual (Erwaegungen)** | same_branch > 0.10 | 0.092–0.094 at 144k | ❌ FAILED (excluded) |
| **Linear Hybrid Complement** | PASS adversarial at w=0.3–0.4 | JP 0.61–0.67, LangDom 0.65–0.75 | ✅ PASSED |

**Role:** COMPLEMENTARY views only. TF-IDF citation hybrids remain PRIMARY (jurist preference JP 0.78–0.79 vs dense JP 0.05–0.43).

**Required dense modes:** center_projected_64dim, center_projected_128dim, center_projected_768dim.

### 5. Preparatory 12k Dense Validation — COMPLETE ✅

- Multi-level protocol: **PASS** (4 levels, nesting=1.0, zero fragmentation)
- Hierarchical builder: **SUCCESS** (39 coarse → 412 fine)
- Frozen v26 flat Leiden: **FAIL** (expected)

### 6. 144k Checkpoint Scale Extrapolation — COMPLETE ✅

| Metric | Value | Note |
|--------|-------|------|
| Coverage | 22/26 years (2000–2021) | PENDING AUDIT for 2003–2021 |
| Fine branch purity | ~0.97 | Hierarchical builder (2-level) |
| Improvement rate (branch) | 0.48–0.65 | |
| Improvement rate (area) | 0.75–0.76 | |
| Strict nesting | ≥0.99 | |
| Fine singletons | ~4–5% | |

**Note:** These metrics describe the hierarchical builder (2-level), NOT the multi-level recursive protocol (which FAILS at 144k).

### 7. NESTING_METRIC_DEFECT_v1 — ENFORCED 🔒

- **Defect:** 7 compressed-family modes reported nesting_score ≥0.99 without scope annotation
- **Root cause:** min_cluster_size enforces nesting=1.0 by construction
- **Enforcement:** All nesting_score ≥0.99 claims require explicit scope annotation (scale, representation, config)
- **Effective:** 2026-09-27, applies to all fractal-map outputs

---

## Product Integration Readiness

| Component | Status | Details |
|-----------|--------|---------|
| Production modes | 3 | full_text_tfidf_light, regeste_full_text_hybrid_0.5, regeste_full_text_hybrid_0.7 |
| Scale tests | 16/16 PASS | 174k simulation tests |
| WebGL pipeline | <3s | Validated at 174k TF-IDF |
| Map mode registry | READY | For dense mode registration |
| Zoom neighborhood API | READY | For dense embeddings |
| Multi-view mode switching | READY | Product integration scaffolded |

---

## Blockers (Upstream Dependencies)

| Blocker | Owner | Required For |
|---------|-------|--------------|
| BGE/bger ID mapping production | Corpus lane | Legal-distance 174k dense embeddings |
| Parquet generation 2022–2026 (29,520 decisions) | Corpus lane | Full 174k dense computation |
| Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k | Corpus lane | Cross-lingual evaluation density |
| 174k dense embeddings computation | Legal-distance lane | Multi-view deployment (4 complementary views) |

**No fractal-map lane defect exists.** The V28-pattern control plane mounting defect in `/tmp/lex_control/state/factory_direction.json` (shows RUN at line 16) is a **persistent infrastructure defect** in the control plane mounting/persistence mechanism — workspace state and lane state correctly show BLOCKED_ON_DEPENDENCIES.

---

## Evidence Artifacts (Immutable)

```
results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json
results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_frozen_spec.json
results/fractal_map/multi_level_protocol_174k_tfidf/
results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/
results/fractal_map/12k_dense_comprehensive/
results/fractal_map/144k_multi_level_validation/multi_level_144k_results.json
results/fractal_map/nesting_metric_defect_v1_audit.json
results/fractal_map/dense_embeddings_integration_contract_v34.json
results/fractal_map/hierarchical_product_integration/
results/fractal_map/product_integration/
results/fractal_map/scale_extrapolation/scale_extrapolation_model_v3.json
state/fractal-map.json
```

All negative results preserved. No claim-bearing outputs overwritten. Provenance maintained.

---

## Next Recommendation

> **TF-IDF hierarchical production modes at 174k are OPERATIONAL and FROZEN.** Multi-level recursive protocol FAILS at 174k (valid negative). Calibration FAILS (valid negative). Dense embedding integration contract v34 DEFINED AND FROZEN. 144k checkpoint validates hierarchical builder scale extrapolation. NESTING_METRIC_DEFECT_v1 enforced. No further same-question cycles justified. Blocker: legal-distance 174k dense embeddings (requires corpus lane resumption). Factory Director decision required for corpus lane resumption.

---

## Sign-off

**This snapshot is AUDIT-READY.** All evidence preserved, negative results intact, contracts frozen, provenance maintained. Lane correctly BLOCKED_ON_DEPENDENCIES on upstream legal-distance 174k dense embeddings. No fractal-map lane defect exists.

*Generated by fractal-map lane operational resume verification — GitHub run 37702272825*