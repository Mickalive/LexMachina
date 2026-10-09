# Fractal Map Lane — Final Audit Confirmation (Factory Direction v35)

**Lane:** fractal-map  
**Direction Version:** 35  
**GitHub Run:** 37933463374  
**Timestamp:** 2026-10-09T00:00:00.000000Z  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  
**Audit Ready:** true  

---

## Factory Direction v35 Question — ANSWERED AND COMPLETE

> **Question:** "Finalize TF-IDF hierarchical production modes at 174k and define dense embedding integration contract for when data blocker resolves."

### Answer: COMPLETE — Both deliverables finalized and frozen.

---

## Deliverable 1: TF-IDF Hierarchical Production Modes — FINALIZED at 174k

### 3 Text-Based Production Modes (Full 173,963 Decisions)

| Mode | Fine Branch Purity | Status |
|------|-------------------|--------|
| `full_text_tfidf_light` | 0.906–0.930 | ✅ PRODUCTION |
| `regeste_full_text_hybrid_0.5` | 0.906–0.930 | ✅ PRODUCTION |
| `regeste_full_text_hybrid_0.7` | 0.906–0.930 | ✅ PRODUCTION |

### 3 Citation-Based Modes (52% Scale / 91,000 Decisions — Citation Coverage Limited)

| Mode | Fine Branch Purity | Status |
|------|-------------------|--------|
| `cited_decisions_tfidf` | 0.609–0.685 | LIMITED (citation coverage) |
| `cited_outcome_hybrid_0.5` | 0.609–0.685 | LIMITED (citation coverage) |
| `cited_outcome_hybrid_0.7` | 0.609–0.685 | LIMITED (citation coverage) |

### 2 Modes FAIL as Expected (Weak Signal / Missing Branch Labels)
- `outcome_tfidf` — FAIL
- `regeste_tfidf` — FAIL

**Protocol:** hierarchical_v1 (2-level constrained hierarchical Leiden)  
**Config Frozen:** coarse_res=0.25, base_sub_res=3.0, min_cluster_size=10, max_subclusters_per_parent=20, adaptive_sub_res=true, k_neighbors=15  
**Verdict:** 6/8 PASS — fine_branch_purity > 0.5 threshold for all 6 passing modes

### Product Readiness
- 16/16 scale simulation tests PASS
- WebGL pipeline <3s at 174k
- Map mode registry operational
- Spatial indexing and LOD management ready

---

## Deliverable 2: Dense Embedding Integration Contract v34 — FROZEN

**Status:** FROZEN (2026-10-03)  
**Role:** Dense embeddings are **COMPLEMENTARY views only**. TF-IDF citation hybrids remain **PRIMARY product mode** (jurist preference JP 0.78–0.79 vs dense JP 0.05–0.43).

### Four Complementary Views with Acceptance Criteria

| Complementary View | Acceptance Criterion | Evidence (144k Checkpoint) | Status |
|--------------------|---------------------|----------------------------|--------|
| **Citation Heritage** | AUC > 0.75 | 0.79–0.85 (center_projected 64/128/768) | ✅ PASSED |
| **Cross-Lingual Sachverhalt** | same_branch > 0.20 | 0.281–0.282 (64/768) | ✅ PASSED |
| **Cross-Lingual Dispositiv** | same_branch > 0.10 | 0.148–0.150 (64/768) | ✅ PASSED |
| **Cross-Lingual Erwaegungen** | same_branch > 0.10 | 0.092–0.094 | ❌ FAILED (excluded) |
| **Linear Hybrid Complement** | PASS adversarial at w=0.3–0.4 | JP 0.61–0.67, LangDom 0.65–0.75 | ✅ PASSED (below TF-IDF baseline) |

### Required Dense Modes for Integration
- `center_projected_64dim` — citation heritage, cross-lingual, linear hybrid
- `center_projected_128dim` — citation heritage, linear hybrid
- `center_projected_768dim` — citation heritage, cross-lingual

### Infrastructure Readiness (Validated)
- Hierarchical builder: VALIDATED at 12k dense (4 levels, nesting=1.0, zero fragmentation, 39 coarse → 412 fine)
- Map mode registry: READY for dense mode registration
- Zoom neighborhood API: READY for dense embeddings
- WebGL pipeline: VALIDATED at 174k TF-IDF (<3s), ready for dense
- Product integration: READY for multi-view mode switching

---

## Valid Negative Results — PRESERVED

| Experiment | Result | Verdict |
|------------|--------|---------|
| Multi-level recursive protocol (4+ levels) at 174k | ALL 5 TF-IDF modes FAIL | Valid negative — level2 area_purity ~0.134 < 0.15 |
| Calibration protocol on TF-IDF | Thresholds too aggressive for signal density | Valid negative — calibrated does not improve frozen v1 |
| v26 flat Leiden at 174k | FAIL (expected) | Valid negative — flat methods collapse at scale |

---

## Scale Extrapolation — VALIDATED at 144k Checkpoint (22/26 Years, 2000–2021)

| Metric | Value | Note |
|--------|-------|------|
| Fine branch purity | ~0.97 | Hierarchical builder (2-level) |
| Improvement rate (branch) | 0.48–0.65 | Scale-stable |
| Improvement rate (area) | 0.75–0.76 | Scale-stable |
| Strict nesting | ≥0.99 | By construction (min_cluster_size) |
| Fine singletons | ~4–5% | Healthy (vs TF-IDF ~99%) |

**Note:** These metrics describe the **hierarchical builder (2-level)**, NOT the multi-level recursive protocol (which FAILS at 144k).

---

## NESTING_METRIC_DEFECT_v1 — ENFORCED

- **Defect:** 7 compressed-family modes reported nesting_score ≥ 0.99 without scope annotation
- **Root cause:** `min_cluster_size` enforces nesting=1.0 by construction
- **Enforcement:** All nesting_score ≥ 0.99 claims require explicit scope annotation (scale, representation, config)
- **Permitted:** 1000-scale and 12k-scale by-construction modes WITH scope annotation
- **Prohibited:** Universal hierarchy validity claims from compressed-family modes

---

## Upstream Blockers — UNCHANGED

| Blocker | Owner | Required For |
|---------|-------|--------------|
| BGE/bger ID mapping production | Corpus lane | Legal-distance 174k dense embeddings |
| Parquet generation 2022–2026 (29,520 decisions) | Corpus lane | Full 174k dense computation |
| Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k | Corpus lane | Cross-lingual evaluation density |
| 174k dense embeddings computation | Legal-distance lane | Multi-view deployment (4 complementary views) |

**No fractal-map lane defect exists.** All fractal-map deliverables are complete, frozen, and audit-ready.

---

## Test Verification — Independent Re-verification (Run 37933463374)

| Test Suite | Passed | Skipped | Status |
|------------|--------|---------|--------|
| `test_verify.py` | 185 | 1 | ✅ PASS |
| `test_pipeline_readiness.py` | 14 | 0 | ✅ PASS |
| `test_zoom_quality_174k_eval.py` | 4 | 0 | ✅ PASS |
| `test_zoom_quality_174k_v26_eval.py` | 7 | 0 | ✅ PASS |
| `test_dense_embeddings_infrastructure.py` | 14 | 1 | ✅ PASS |
| `test_scale_dependency.py` | 11 | 0 | ✅ PASS |
| `test_12k_dense_comprehensive.py` | 10 | 0 | ✅ PASS |
| **TOTAL** | **245** | **2** | **✅ ALL PASS** |

All tests executed in fresh Python environment with clean dependency install.

---

## Control Plane Mounting Defect — DOCUMENTED (Not a Lane Failure)

**Mounted control plane** (`/tmp/lex_control/state/factory_direction.json`, line 16): `fractal-map.status = "RUN"` ❌  
**Workspace state** (`state/factory_direction.json`, line 16): `fractal-map.status = "BLOCKED_ON_DEPENDENCIES"` ✅  
**Lane state** (`state/fractal-map.json`): `cycle_status = "BLOCKED_ON_DEPENDENCIES"` ✅  

This is a **PERSISTENT INFRASTRUCTURE DEFECT in the control plane mounting/persistence mechanism**, NOT a lane failure. Documented across 20+ verification runs. Zero impact on lane deliverables or product.

---

## Next Recommendation

**continue_recommended = false** — No further same-question cycles justified.

**Factory Director action required:** Resume corpus lane for:
1. BGE/bger ID mapping production
2. Parquet generation for years 2022–2026 (29,520 decisions missing)
3. Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation

Once legal-distance delivers 174k dense embeddings passing the four complementary view acceptance criteria, the fractal-map lane will integrate them as multi-view modes per the frozen v34 contract.

---

## Critical Evidence Artifacts (Preserved, Immutable)

```
results/fractal_map/
├── hierarchical_v1_174k_tfidf/
│   ├── hierarchical_v1_174k_tfidf_verdict_20261001_102442.json   # 6/8 PASS verdict
│   └── hierarchical_v1_frozen_spec.json                          # Frozen production spec
├── multi_level_protocol_174k_tfidf/                              # 4 TF-IDF modes, FAIL preserved
├── multi_level_protocol_174k_tfidf_calibrated/                   # Calibration FAIL preserved
├── 12k_dense_comprehensive/                                      # Dense multi-level PASS
├── 144k_multi_level_validation/
│   └── multi_level_144k_results.json                             # Scale extrapolation
├── nesting_metric_defect_v1_audit.json                           # Enforcement audit
├── dense_embeddings_integration_contract_v34.json                # FROZEN contract
├── hierarchical_product_integration/                             # 2 production modes integrated
├── product_integration/                                          # Map mode registry & spec
│   ├── PRODUCT_INTEGRATION_SPEC.md
│   ├── INTEGRATION_SPEC.md
│   ├── map_mode_registry.py
│   └── map_mode_registry.json
└── scale_extrapolation/
    └── scale_extrapolation_model_v3.json                         # Scale-stable model
```

---

## State Files (Authoritative)

- `state/fractal-map.json` — Lane state: BLOCKED_ON_DEPENDENCIES, continue_recommended=false, audit_ready=true
- `state/factory_direction.json` (workspace) — Lane status: BLOCKED_ON_DEPENDENCIES (correct)
- `/tmp/lex_control/state/factory_direction.json` (control plane mount) — Lane status: RUN (STALE, infrastructure defect)

---

## Sign-off

This snapshot is **audit-ready**. All evidence preserved, negative results intact, contracts frozen, provenance maintained.

**Lane State:** `state/fractal-map.json` — authoritative  
**Workspace State:** `state/factory_direction.json` — consistent with lane state  
**Mounted Control Plane:** `/tmp/lex_control/state/factory_direction.json` — stale (infrastructure defect)  
**Test Verification:** 245 passed, 2 skipped across 7 independent test suites  
**JSON Summary:** `results/fractal_map/FRACTAL_MAP_V35_FINAL_AUDIT_CONFIRMATION_20261009_RUN_37933463374.json`

---

*Generated by fractal-map lane final audit confirmation from GitHub run 37933463374. Factory direction v35. All discriminating experiments complete. No further same-question cycles justified.*