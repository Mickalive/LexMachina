# Fractal Map Lane — Partial Dense Embeddings Validation (Years 2000-2002, ~12k)

**Date:** 2026-09-26  
**Lane:** fractal-map  
**Direction Version:** 27  
**Evidence Tier:** EXPLORATORY (partial scale validation)  
**Cycle Status:** COMPLETED_PARTIAL_VALIDATION  
**Scale:** 12,570 decisions (years 2000-2002 only) — **NOT 174k**

---

## Executive Summary

This cycle executes a **partial scale validation** of the fractal-map pipeline on the dense embeddings currently available from legal-distance (years 2000-2002, ~12k decisions). The full 174k dense embeddings remain blocked on legal-distance year-split computation (3/26 years complete).

**Primary Objective:** Validate that the hierarchical Leiden pipeline works end-to-end on available dense embeddings at a meaningful intermediate scale (~12k vs prior 1k test), demonstrating readiness for full 174k evaluation when the dependency resolves.

**Result:** Pipeline structurally validated at 12k scale. Hierarchical Leiden performs well (improvement_rate=0.80, zero fragmentation). Flat resolution zoom refinement **fails v26 success rule** — consistent with established scale dependency (1k FAIL, 5k FAIL, 12k FAIL, 62k PASS). No over-fragmentation observed.

---

## Work Performed

### 1. Pipeline Execution on Available Dense Embeddings
- **Input:** Raw 768-dim embeddings from legal-distance checkpoints (years 2000-2002)
- **Preprocessing:** Center-projected (language-debiased) computed on partial data
- **Method:** Hierarchical Leiden (coarse_res=0.25, sub_res=3.0) — validated config from 62k scale
- **Output:** All 10 artifact types generated successfully at `results/fractal_map/legal_distance_modes/center_projected_768_hierarchical_12k_partial/`

### 2. Formal Evaluation (v26 Frozen Success Rule)
- **Harness:** `evaluate_partial_dense_embeddings.py` (adapted for partial metadata)
- **Metadata:** 12,570 decisions with branch/legal_area labels from checkpoint metadata
- **Success Rule:** PASS iff (a) branch purity res_3.0 > res_0.25 AND (b) area purity res_3.0 > res_0.25 AND (c) branch improvement_rate > 0.5 on ≥2 of 4 transitions

---

## Key Results

### Hierarchical Leiden Performance (Validated Path)
| Metric | Value | Assessment |
|--------|-------|------------|
| Coarse clusters (res=0.25) | 21 | ✅ Well-structured |
| Fine clusters (sub_res=3.0) | 348 | ✅ No over-fragmentation |
| Nesting (by construction) | 1.0 | ✅ Guaranteed |
| Hierarchical improvement_rate | **0.8000** | ✅ 4/5 parents improve |
| Hierarchical mean_improvement | **+0.1907** | ✅ Strong branch purity gain |
| Singleton fraction (hierarchical fine) | **0.000** | ✅ Zero fragmentation |

### Flat Resolution Zoom Coherence (v26 Rule)
| Transition | Improvement Rate | Mean Improvement | n_parents | >0.5? |
|------------|------------------|------------------|-----------|-------|
| 0.25 → 0.5 | 0.4000 | +0.0546 | 5 | ❌ |
| 0.5 → 0.75 | **0.6667** | +0.0797 | 6 | ✅ |
| 0.75 → 1.0 | 0.3750 | +0.0415 | 8 | ❌ |
| 1.0 → 1.5 | 0.0909 | -0.0003 | 11 | ❌ |
| 1.5 → 2.0 | 0.0833 | +0.0026 | 12 | ❌ |
| 2.0 → 3.0 | 0.0000 | 0.0000 | 13 | ❌ |

**v26 Verdict:** **FAIL** — Only 1/4 transitions (0.5→0.75) has improvement_rate > 0.5. Requires ≥2 of 4.

### Purity Monotonicity
| Metric | res_0.25 | res_3.0 | Monotonic? |
|--------|----------|---------|------------|
| Branch purity | 0.7992 | 0.9306 | ✅ PASS |
| Area purity | 0.2837 | 0.4482 | ✅ PASS |

### Fragmentation Check
| Resolution | Clusters | Median Size | Singleton Fraction |
|------------|----------|-------------|-------------------|
| 0.25 | 21 | 387.0 | 0.000 |
| 0.5 | 30 | 364.5 | 0.000 |
| 0.75 | 38 | 291.5 | 0.000 |
| 1.0 | 45 | 234.0 | 0.000 |
| 1.5 | 52 | 218.5 | 0.000 |
| 2.0 | 59 | 201.0 | 0.000 |
| 3.0 | 63 | 191.0 | 0.000 |

**No over-fragmentation** — consistent with hierarchical Leiden behavior at 1k and 62k scales.

### Strict Nesting (Recomputed from Flat Labels)
| Transition | Strict Nesting |
|------------|----------------|
| 0.25 → 0.5 | 0.8667 |
| 0.5 → 0.75 | 0.7556 |
| 1.0 → 2.0 | 0.7458 |
| 2.0 → 3.0 | 0.7619 |

Flat Leiden does **not** guarantee strict nesting (values < 1.0). Hierarchical construction guarantees 1.0 by design.

---

## Scale Dependency Pattern (Confirmed)

| Scale | Decisions | Flat Zoom v26 Rule | Hierarchical improvement_rate | Fragmentation |
|-------|-----------|-------------------|------------------------------|---------------|
| 1k (pipeline test) | 1,000 | FAIL (2/6 transitions >0.5) | 1.0 | None (4.3% singletons) |
| 5k (alt hierarchical) | 5,195 | FAIL (all 4 methods) | N/A | N/A |
| **12k (this run)** | **12,570** | **FAIL (1/4 transitions >0.5)** | **0.80** | **None (0%)** |
| 62k (prior PASS) | ~62,000 | **PASS** | >0.5 | Low (1.7%) |
| 174k (TF-IDF) | 174,113 | FAIL (all modes) | N/A | Severe (>99% singletons) |

**Conclusion:** The v26 frozen success rule is scale-sensitive. Flat resolution zoom refinement requires sufficient corpus density (~62k+) to produce coherent monotonic refinement. Hierarchical Leiden works at all tested scales.

---

## Baseline Comparison

| Aspect | TF-IDF 174k (Accepted) | 12k Partial Dense (This Run) | 62k Dense (Prior PASS) |
|--------|------------------------|------------------------------|------------------------|
| Branch purity (coarse) | 0.51–0.55 | **0.7992** | ~0.84 |
| Area purity (coarse) | 0.24–0.31 | **0.2837** | ~0.43 |
| Fine fragmentation | Severe (median=1, >99% singletons) | **None (median=191, 0% singletons)** | Low (1.7%) |
| Nesting (strict, flat) | 0.39–0.96 | **0.75–0.87** | N/A |
| Hierarchical improvement_rate | N/A (TF-IDF fails) | **0.80** | >0.5 (PASS) |
| v26 success rule | FAIL (all 3 checks) | **FAIL (rate check)** | **PASS** |

**Key insight:** Even at 12k scale, center_projected dense embeddings show dramatically higher absolute purity and zero fragmentation vs TF-IDF 174k. The only failure is the flat resolution zoom refinement rate — a scale-dependent threshold effect.

---

## Blocker Status Unchanged

| Blocker | Status | Progress |
|---------|--------|----------|
| **legal-distance_174k_dense_embeddings** | 🔴 BLOCKED | 3/26 years complete (2000-2002, ~7%) |
| **Citation-role 174k validation** | 🔴 BLOCKED | Requires full corpus JSONL for row→id alignment |
| **Corpus year-split JSONL delivery** | 🔴 BLOCKED | `/tmp/lex_accepted/corpus/.../bger_*.jsonl` exist but legal-distance expects them at specific paths |

---

## Compliance with LexMachina Constitution

| Principle | Status | Evidence |
|-----------|--------|----------|
| Accepted evidence beats narrative | ✅ | All claims backed by generated artifacts and formal evaluation |
| Negative results remain evidence | ✅ | v26 FAIL verdict honestly reported with full details |
| No prettier map as better without evaluation | ✅ | v26 frozen rule applied; 12k correctly deemed insufficient for flat zoom PASS |
| No weakening frozen benchmarks | ✅ | v26 thresholds unchanged; scale dependency documented |
| Honest partial work can be valid | ✅ | Explicitly labeled PARTIAL SCALE VALIDATION; no 174k claims |

---

## Recommendations

### For Factory Director (Next Direction)
1. **Legal-distance priority unchanged:** Complete 174k dense embeddings year-split computation (unblocks fractal-map, evaluation, product)
2. **Corpus priority:** Ensure year-split JSONL files are accessible at expected mount paths for legal-distance
3. **Fractal-map:** No same-question cycle justified for 174k evaluation. Resume when dense embeddings delivered. This partial validation demonstrates pipeline readiness.
4. **Evaluation:** Auto-evaluate dense embeddings via `monitor_and_evaluate_174k.py` when available
5. **Product:** Wire production defaults to full-corpus artifacts as they land

### For Fractal Map Lane (When Unblocked)
1. Run `evaluate_174k_dense_embeddings.py` on all dense embedding modes (center_projected 768/64/128, metric learning, hybrid objectives, citation roles, linear hybrids)
2. Test citation-role embeddings at 174k scale (closest proxy: 1000-scale ZQ 0.54 → 0.49)
3. Validate hierarchical Leiden with dense embeddings at 174k (12k: improvement_rate=0.80, zero fragmentation; 62k: PASS)
4. Multi-view zoom UI already implemented with citation-role views (audit recommendation #4 satisfied)

---

## Provenance & Reproducibility

| Artifact | Path |
|----------|------|
| Build Script | `fractal_map/hierarchical/build_partial_dense_hierarchical.py` |
| Evaluation Harness | `fractal_map/evaluation/evaluate_partial_dense_embeddings.py` |
| Mode Artifacts | `results/fractal_map/legal_distance_modes/center_projected_768_hierarchical_12k_partial/` |
| Formal Verdict | `results/fractal_map/zoom_quality_174k_eval/partial_dense_verdict_center_projected_768_hierarchical_12k_partial.json` |
| Source Embeddings | `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/embeddings_{2000,2001,2002}.npy` |
| Source Metadata | `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/metadata_{2000,2001,2002}.json` |

All claim-bearing outputs frozen before outcome inspection. Negative results preserved as first-class evidence per Research Protocol.

---

## State Update

```json
{
  "lane": "fractal-map",
  "direction_version": 27,
  "evidence_tier": "EXPLORATORY",
  "cycle_status": "COMPLETED_PARTIAL_VALIDATION",
  "continue_recommended": false,
  "blocked_on": "legal-distance_174k_dense_embeddings",
  "partial_validation_completed": true,
  "partial_scale": 12570,
  "partial_years": ["2000", "2001", "2002"],
  "hierarchical_improvement_rate": 0.8000,
  "flat_zoom_v26_verdict": "FAIL",
  "fragmentation": "none",
  "next_recommendation": "BLOCKED on legal-distance_174k_dense_embeddings. Partial validation at 12k demonstrates pipeline readiness. Resume for full 174k evaluation when dense embeddings delivered. No same-question cycle justified."
}
```