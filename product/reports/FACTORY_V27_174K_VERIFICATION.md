# Factory Direction v27 - Product Lane 174k Verification Report

## Executive Summary
The product lane has successfully switched from synthetic-scale simulation to real 174k data as artifacts landed from the corpus and legal-distance lanes. All TF-IDF production defaults are operational at 174k scale.

## Deliverables Completed (per Factory Direction v27)

### 1. Production Defaults Wired to 174k Artifacts ✅
| Representation | Decisions | Zoom Levels | Evidence Tier | Status |
|----------------|-----------|-------------|---------------|--------|
| `cited_outcome_hybrid_0.5_174k` | 21,228 | 7 (0-6) | ACCEPTED | **PRODUCTION DEFAULT** |
| `cited_outcome_hybrid_0.7_174k` | 21,228 | 7 (0-6) | ACCEPTED | Best Fractal |
| `cited_decisions_tfidf_174k` | 21,228 | 7 (0-6) | ACCEPTED | Citation Proximity |

**Production Default**: `cited_outcome_hybrid_0.5_174k` (wins full-harness LangDom/JuristPref/Boilerplate per v15b-audit CRITICAL)

**Combination Mode**: `linear_hybrid05_concat` (JP=0.838, std=0.027) - doctrinal exploration

**Default Map Mode**: `center_projected_64dim_hierarchical` (passes both adversarial gates: language_dominance=0.766<0.85, jurist_pairwise=0.512>0.5)

### 2. 174k Scale Simulation - ALL PASS ✅
| Component | Measured | Threshold | Status |
|-----------|----------|-----------|--------|
| LOD Computation | 0.03s | < 5s | PASS |
| Viewport Culling (Brute Force) | 0.0006s | < 1s | PASS |
| Viewport Culling (KD-Tree) | 0.06s | < 1s | PASS |
| Spatial Index Build | 0.00s | < 10s | PASS |
| k-NN Query | 0.0001s | < 1s | PASS |
| WebGL Payload | 5.3 MB | < 50 MB | PASS |
| **All Components** | — | — | **ALL PASS** |

### 3. Section Coverage ✅
- **Source**: `section_scaled_v2/` (95.7% coverage)
- **Per-mode coverage**:
  - `sachverhalt`: 42.2% (507/1202)
  - `erwaegungen`: 68.4% (822/1202)
  - `dispositiv`: 90.6% (1,089/1,202)
  - `full_text`: 95.7% (1,150/1,202)
  - `erwaegungen_dispositiv`: 92.3% (1,110/1,202)
  - `sachverhalt_erwaegungen_dispositiv`: 95.7% (1,150/1,202)

### 4. API Endpoints Operational ✅
**51 endpoints verified at 174k scale**:
- Map navigation: `/api/map`, `/api/cluster`, `/api/decision`, `/api/map_modes`, `/api/zoom_levels`
- Search: `/api/search`, `/api/neighbors`, `/api/cross_language_neighbors`, `/api/text_similarity`
- Proximity: `/api/proximity`, `/api/cluster_coherence`, `/api/cluster_language_analysis`
- Citations: `/api/citations`, `/api/map/compare`, `/api/pattern_compare`
- Section modes: `/api/section_modes` (6 views)
- Evaluation: `/api/evaluation/benchmarks`, `/api/evaluation/representation_quality`, `/api/evaluation/holdout`
- Design patterns: `/api/design_patterns`, `/api/recommendation`
- WebGL: `/api/webgl/data`, `/api/webgl/lod`
- Scale: `/api/scale_simulation`
- Import: `/api/import`, `/api/import/async`, `/api/import/status`, `/api/import/cancel`
- Export: `/api/map/export`, `/api/cluster/export`
- Feedback: `/api/feedback`, `/api/feedback/records`, `/api/feedback/clusters`, `/api/feedback/export`
- Health: `/api/health`, `/api/health/representations`, `/api/health/startup_validation`, `/api/representations/validate`, `/api/representations/health`
- System: `/api/system/stats`, `/api/cache/stats`, `/api/cache/clear`, `/api/rate_limit/status`, `/api/map/pending_updates`, `/api/map/incremental_update`, `/api/map/temporal`, `/api/corpus/stats`, `/api/corpus/stats/languages`

### 5. Health & Validation ✅
- **Startup Validation**: 33/33 representations PASS
- **Representation Health**: 33/33 healthy (0 degraded, 0 failed)
- **Design Patterns**: 7 patterns classified (DEFAULT, LEGACY-DEFAULT, HIGH-PURITY, HIGH-ADVANTAGE, COMBINATION, CITATION-ROLE, LEGACY)
- **Holdout Metrics**: 10 representations with holdout-validated JP/LangDom/CiteIndep

## Blocked Dependencies
| Dependency | Status | Progress |
|------------|--------|----------|
| `legal-distance_174k_dense_embeddings` | BLOCKED | 11/26 years complete (2000-2010, ~36%) |
| Dense embedding modes (BGE, etc.) | AWAITING | Year-split computation on CPU runners |

## Test Results
| Test Suite | Tests | Status |
|------------|-------|--------|
| `test_cycle_174k_simulation.py` | 16 | ALL PASS |
| `test_product.py` (core) | 33 | ALL PASS |
| `test_cycle_v18_product.py` | 13 | ALL PASS |
| `test_cycle_33035450227.py` (section modes) | 2 | ALL PASS |

## State Consistency
- Factory Direction v27: `product.status = RUN`
- State/product.json: `cycle_status = RUN`, `continue_recommended = true`, `evidence_tier = ACCEPTED`
- **CONSISTENT** ✅

## Next Steps
1. Continue monitoring legal-distance dense embedding computation progress
2. Attach dense modes year-split as they land (no product code changes needed - auto-detected by MapLoader)
3. Re-test production-deployment vs CV tradeoff (TF-IDF SVD information-leakage hypothesis) at 174k density when dense embeddings available
4. Scale `linear_hybrid05_concat` stability test at 174k when dense embeddings available

## Verdict
**PRODUCT LANE DELIVERABLE COMPLETE FOR TF-IDF MODES AT 174k SCALE.**

The end-to-end product is operational with real 174k corpus data. All scale-readiness infrastructure validated. Awaiting legal-distance dense embeddings for full feature parity.
