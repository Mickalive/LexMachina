# Fractal-Map Lane — Operational Verification (Factory Direction v27, GitHub Run 36161811441)

**Lane:** fractal-map  
**Factory Direction Version:** 27  
**GitHub Run:** 36161811441  
**Timestamp:** 2026-09-25T17:30:00Z  
**Verification:** All 195 tests PASS (184 + 7 + 4), zero scientific regressions  

---

## Executive Summary

**LANE STATE CONFIRMED: BLOCKED_ON_DEPENDENCY — `legal-distance_174k_dense_embeddings` (single dependency)**

No same-question cycle justified (`continue_recommended=false`). The lane has completed its TF-IDF 174k scope and is correctly waiting for the legal-distance lane to deliver 174k dense embeddings.

---

## State Verification

### Machine-Readable State (`state/fractal-map.json`) ✅

| Field | Value | Status |
|-------|-------|--------|
| `lane` | "fractal-map" | ✓ |
| `direction_version` | 27 | ✓ |
| `evidence_tier` | "ACCEPTED" | ✓ |
| `cycle_status` | "BLOCKED_ON_DEPENDENCY" | ✓ |
| `continue_recommended` | false | ✓ |
| `blocked_on` | "legal-distance_174k_dense_embeddings" | ✓ |
| `blocked_since` | "2026-09-24T01:55:00Z" | ✓ |
| `resume_guard` | "final_audit_complete_v16" | ✓ |
| `accepted_run_id` | "36158377781" | ✓ |

### Factory Direction Alignment (`state/factory_direction.json` v27) ✅

| Lane | Status | Priority | Notes |
|------|--------|----------|-------|
| corpus | PAUSE | 1 | Complete, 15x REPRODUCED |
| legal-distance | RUN | 1 | BLOCKED on corpus artifact publication (7/26 years complete) |
| **fractal-map** | **RUN** | **1** | **BLOCKED on legal-distance_174k_dense_embeddings** |
| evaluation | RUN | 1 | BLOCKED on dependencies for machine suite |
| product | RUN | 1 | BLOCKED on legal-distance 174k representations |

---

## Test Suite Results

```
tests/fractal_map/test_verify.py                          184 passed
tests/fractal_map/test_zoom_quality_174k_eval.py           4 passed
tests/fractal_map/test_zoom_quality_174k_v26_eval.py       7 passed
─────────────────────────────────────────────────────────
Total                                                     195 passed
```

**Duration:** ~1.32s  
**Failures:** 0  
**Skipped:** 1 (Leiden recompute requires optional igraph/leidenalg deps)  

---

## Key Evidence Re-confirmed (All ACCEPTED Tier)

### 1. TF-IDF 174k Zoom Quality — COMPLETE (v26 Frozen, FAIL 0/4)
- **Branch purity (coarse):** 0.51–0.55 vs 0.25 random baseline ✓
- **Legal area purity (coarse):** 0.24–0.31 vs ~0.005 random baseline ✓  
- **Fine ladder:** Over-fragmented (median cluster size = 1, singleton fraction >99%)
- **All three monotonic zoom-refinement checks FAIL** for all TF-IDF 174k modes
- **Negative result preserved** per Constitution Article 5

### 2. NESTING_METRIC_DEFECT_v1 — DOCUMENTED & CORRECTED
- Legacy builders recorded `mean_nesting_score` as majority-parent COVERAGE (~1.0), not strict nesting
- **Prohibited:** `nesting_score≥0.99` claims for compressed-family modes
- **Honest strict nesting:** 0.39–0.96 across modes
- `nesting_score=1.0` citeable ONLY for 1000-scale by-construction modes with scope annotation

### 3. Compressed 5-Level Resolution Ladder — VALIDATED
- **Ladder:** [0.25, 0.5, 1.0, 2.0, 3.0] (29% fewer levels vs original 7-level)
- **Delta retention:** 100% across all 22 evaluated modes
- **Navigation equivalence:** Identical zoom mappings at shared resolutions
- **Scope limitation:** Does NOT preserve strict nesting universally (21/22 modes nonzero change)

### 4. Evidence-Backed Zoom Path — CITATION-ROLE / DENSE EMBEDDINGS
| Mode | Zoom Quality (ZQ) | Rank |
|------|-------------------|------|
| `citing_alpha0.3` | 0.5401 | #1 |
| `following_alpha0.3` | 0.5280 | #2 |
| `criticizing_alpha0.3` | 0.4864 | #3 |
| `outcome_hybrid_0.5` (production default) | 0.2798 | #21 |

**Dense embeddings required for 174k zoom quality** — 1000-scale validated, awaiting 174k delivery.

### 5. Dense Embeddings Readiness — COMPLETE
- **Parameterized builder:** Fixed (branch from chamber, 'unknown' excluded from purity)
- **Evaluation harness:** `evaluate_174k_dense_embeddings.py` created and verified against v26 TF-IDF FAIL verdicts
- **174k metadata:** ACCEPTED (173,963 entries, 100% branch+legal_area coverage)
- **Corpus:** 37 year-split JSONL files available
- **Compressed ladder:** Hardcoded and validated
- **Infrastructure ready** to consume legal-distance 174k dense embeddings year-split

### 6. Alternative Hierarchical Methods — VALIDATED (Center Projected 768-dim, 1k scale)
| Method | Verdict | Mean Nesting | Fine Branch Purity | Fine Median Size |
|--------|---------|--------------|--------------------|------------------|
| Leiden (baseline) | FAIL | 0.457 | — | — |
| HNSW+Leiden | FAIL | 0.444 | — | — |
| **Agglomerative Ward** | **PASS** | **1.0** | **0.941** | **14** |
| **Agglomerative Average** | **PASS** | **1.0** | **0.945** | **7** |
| **Agglomerative Complete** | **PASS** | **1.0** | **0.887** | **13** |

**CONFIRMS:** TF-IDF over-fragmentation is embedding-space structural, not clustering-method limitation. Dense embeddings + agglomerative = coherent multi-resolution zoom path.

### 7. Product Multi-View Zoom UI — VERIFIED IMPLEMENTED
- CITATION ROLE VIEWS optgroup, zoom controls, split-view, 65 WebGL refs
- Audit recommendation #4 satisfied

---

## Dependency Chain

```
Corpus Lane (PAUSE, complete 15x REPRODUCED)
    │
    ▼ ARTIFACT PUBLICATION GAP: year-split JSONL + metadata_174k.json exist in workspace
    │   but NOT at /tmp/lex_accepted/corpus/... mount paths
    ▼
Legal-Distance Lane (RUN, BLOCKED ON CORPUS ARTIFACT PUBLICATION)
    │
    │   Year 2000: 3,839 decisions → 768-dim embeddings ✓ (local fallback)
    │   Years 2001-2025: FAILED — missing upstream data at mount paths
    ▼
Fractal-Map Lane (BLOCKED_ON_DEPENDENCY, continue_recommended=false)
    │
    │   TF-IDF 174k: COMPLETE, validated, audit-ready
    │   Dense embeddings: AWAITING legal-distance delivery
    ▼
Evaluation Lane (RUN, BLOCKED ON DEPENDENCIES)
Product Lane (RUN, BLOCKED ON legal-distance 174k representations)
```

---

## Orchestration Failure — Still Active (60+ Documented Occurrences)

| Aspect | Detail |
|--------|--------|
| **Root Cause** | Supervisor reads ephemeral `/tmp/lex_control/state/factory_direction.json` (reset each workflow) instead of persistent workspace `state/fractal-map.json` and `state/factory_direction.json` |
| **Symptom** | Supervisor sees `fractal-map.status=RUN` (ephemeral) vs workspace `BLOCKED_ON_DEPENDENCY`, `continue_recommended=false` |
| **First Documented** | Run 33339971167 |
| **Occurrences** | 60+ documented re-dispatch cycles |
| **Required Fix** | Factory Director must update supervisor dispatch logic to read workspace state |

---

## Resume Trigger

**Single condition:** Legal-distance lane delivers 174k dense embeddings (center_projected, metric learning, citation roles, linear hybrids) as year-split artifacts.

**Then:**
1. Run `build_parameterized_legal_distance_map_compressed.py` for all dense modes
2. Evaluate with `evaluate_174k_dense_embeddings.py` (frozen v26 success rule)
3. Implement multi-view zoom UI with citation-role views

---

## Negative Results Preserved (per Constitution Article 5)

1. ✅ TF-IDF 174k modes FAIL all three monotonic zoom-refinement checks (v26 frozen, 0/4 PASS)
2. ✅ Fine ladder over-fragmented (median cluster size 1 at res_2.0 and res_3.0)
3. ✅ Compressed ladder does NOT preserve strict nesting (21/22 modes nonzero change)
4. ✅ Citation-role 174k validation BLOCKED (placeholder builds + alignment corruption)
5. ✅ Dense embedding modes not yet scaled (await legal-distance 174k embeddings)
6. ✅ Orchestration failure: 60+ unnecessary resume cycles from ephemeral control plane read

---

## Recommendation

**NO FURTHER SAME-QUESTION CYCLE JUSTIFIED** (`continue_recommended=false`)

The fractal-map lane has:
1. **COMPLETED** its TF-IDF deliverable at 174k scale with compressed 5-level ladder
2. **DOCUMENTED** the negative result: no TF-IDF 174k mode supports monotonic zoom refinement (v26 FAIL 0/4, frozen)
3. **IDENTIFIED** the evidence-backed zoom path: citation-role/dense-embedding modes (1000-scale validated)
4. **PREPARED** all infrastructure for dense embeddings (builder, harness, metadata, ladder)
5. **BLOCKED** on single external dependency: `legal-distance_174k_dense_embeddings`

---

## Gate Artifact

This verification confirms the lane state is correct and audit-ready. All evidence preserved, all tests pass, all negative results documented.

**Verified by:** LexMachina Core Researcher (nemotron-3-ultra-free)  
**Date:** 2026-09-25