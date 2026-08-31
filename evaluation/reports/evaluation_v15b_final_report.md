# Evaluation v15b Final Report — BLOCKED_ON_DEPENDENCIES

**Lane**: evaluation  
**Factory Direction**: v13  
**Evidence Tier**: ACCEPTED  
**Cycle Status**: COMPLETED  
**Continue Recommended**: false  
**Accepted Run ID**: eval_v15b_cv_1788148695  
**GitHub Run**: 33366040188  
**Timestamp**: 2026-08-31T12:00:00.000000+00:00

---

## Executive Summary

The evaluation lane has **completed all achievable objectives** for the current factory direction question. The v15b experiment produced **NEW ACCEPTED EVIDENCE** that supervised combinations beat the best zero-shot hybrid on canonical 5-fold CV. However, **two critical dependencies remain BLOCKED**:

1. **Full corpus scale evaluation (192k)** — pending corpus lane OpenCaseLaw bulk ingestion
2. **Jurist human study** — framework ready, needs 5-10 Swiss jurists

**No further evaluation cycles should run on the same question** until dependencies resolve. The `continue_recommended=false` flag correctly reflects this.

---

## v15b ACCEPTED Findings (NEW)

### 5-Fold Cross-Validation: Combinations vs Best Zero-Shot Hybrid

**Configuration**: canonical frozen harness v3, config_hash=4323f833fa72366a, seed=42, 1200 BGer decisions  
**Success Rule**: JP improvement > 0.02 over cited_outcome_hybrid_0.5 (frozen before observation)

| Representation | JP Mean | JP Std | Adv Pass Rate | Beats Hybrid? |
|----------------|---------|--------|---------------|---------------|
| **linear_hybrid05_concat** | **0.838** | **0.027** | 1.0 | ✅ |
| linear_citation_concat | 0.838 | 0.030 | 1.0 | ✅ |
| linear_citation_ridge | 0.860 | 0.042 | 1.0 | ✅ (unstable) |
| linear_citation_w3070 | 0.817 | 0.036 | 1.0 | ✅ |
| cited_outcome_hybrid_0.5 (baseline) | 0.785 | 0.043 | 1.0 | — |
| center_projected_64dim | 0.799 | 0.020 | 1.0 | ❌ |

**Key Findings**:
- **ALL four combinations beat the best zero-shot hybrid** (cited_outcome_hybrid_0.5, JP=0.785)
- **linear_hybrid05_concat is BEST STABLE** — same JP as linear_citation_concat but LOWER variance (std=0.027 vs 0.030)
- linear_citation_ridge has highest JP (0.860) but **exceeds stability threshold** (std=0.042 > 0.03)
- **Two-mode tradeoff FULLY BROKEN**: combinations achieve BOTH higher JP AND competitive CiteIndep
- **Zero-shot hybrids no longer dominant** — supervised combinations are now BEST representations on CV
- **OOS ceiling ~0.53 CONFIRMED** (consistent with v10/v11 holdout validation)

**Test Result**: 64/64 tests PASS

---

## v15 Full Adversarial Harness: Production Deployment Reality Check

**Configuration**: Complete v3 adversarial harness (5 benchmarks) on full 1200-decision corpus

| Benchmark | cited_outcome_hybrid_0.5 | Combinations (range) |
|-----------|--------------------------|---------------------|
| Language Dominance | **0.575 PASS** | 0.672–0.750 PASS |
| Jurist Pairwise | **0.678 PASS** | 0.559–0.640 PASS |
| Jurivoc Alignment | 0.28 FAIL | **0.36–0.45 PASS** |
| Scale Stability | 1.0 PASS | 1.0 PASS |
| Boilerplate Resistance | **0.14 PASS** | 0.30–0.47 FAIL |

**Critical Tradeoff Documented**:
- **CV Generalization** (combinations win): Higher JP, better Jurivoc alignment
- **Production Deployment** (hybrid wins): Better LangDom, better JuristPref, passes Boilerplate
- **NO representation passes all 5 benchmarks**
- **Confirms v15 information leakage finding**: SVD fit on full data favors hybrid

**Test Result**: 73/73 tests PASS (9 new)

---

## Factory Direction v9 Objectives Status

| Objective | Status | Evidence |
|-----------|--------|----------|
| (1) Full corpus scale evaluation (192k) | **BLOCKED** | Pending corpus lane |
| (2) Citation role modeling | **COMPLETED** | 2,988 annotations, 8/9 role hybrids PASS |
| (3) Legal embeddings fine-tuning | **COMPLETED** | multilingual_e5_small tested, best adversarial but hierarchy collapse |
| (4) Jurist human study | **BLOCKED** | Framework ready, needs 5-10 Swiss jurists |
| (5) Cross-lingual alignment | **COMPLETED** | 52 representations tested, proc_pairs LOSSLESS |
| (6) User corpus import | **COMPLETED** | 45/45 tests PASS |

**4 of 6 objectives COMPLETED; 2 BLOCKED on dependencies**

---

## Orchestration Failure Diagnosed (Run 33366040188)

**Pattern**: 7 consecutive operational resume cycles (33354034841 → 33362815185) performed state synchronization and test verification **without new science**.

**Root Cause**: Factory direction listed evaluation as `status: "RUN"` while lane state correctly showed `cycle_status: "COMPLETED"` with `continue_recommended: false` and both dependencies BLOCKED.

**Resolution**: Lane state now explicitly documents BLOCKED_ON_DEPENDENCIES status. Future dispatches must respect `continue_recommended=false`.

**Wasted Cycles**: 6 redundant dispatches

---

## Product Integration Recommendations (from ACCEPTED Evidence)

1. **Integrate linear_citation_concat OR linear_hybrid05_concat** as new COMBINATION map mode
   - linear_hybrid05_concat preferred for lower variance (std=0.027)
   - Both have ACCEPTED evidence from 3 independent evaluations (v12, v13, v14)

2. **Keep cited_outcome_hybrid_0.5 as default** for production deployment
   - Wins on LangDom and JuristPref in full-harness evaluation
   - Remains best for user-imported corpora (no branch metadata)

3. **Document tradeoff explicitly**: CV generalization ≠ production deployment
   - Combinations: High-Jurivoc map modes for doctrinal exploration
   - Hybrid: Default for case retrieval and navigation

---

## Next Steps (When Dependencies Resolve)

1. **Full corpus adversarial evaluation at 192k scale** — all representations
2. **Multilingual-e5-small fine-tuned evaluation with hierarchy loss** — requires GPU
3. **Jurist human study execution** — framework validated, needs recruitment
4. **Section-specific cross-lingual evaluation** — needs sachverhalt/erwaegungen/dispositiv from full corpus
5. **Scale linear_hybrid05_concat stability test at 192k**

---

## Verification

- **All 86 evaluation tests PASS** (pytest, 2026-08-31)
- **Frozen harness v3 reproducibility CONFIRMED** (seed=42, config_hash=4323f833fa72366a)
- **No regressions** in validation metrics
- **Negative results preserved** as first-class evidence

---

## Recommendation

**BLOCKED_ON_DEPENDENCIES** — No further evaluation cycles on current question. Factory Director should update evaluation lane status to `BLOCKED_ON_DEPENDENCIES` until corpus 192k delivery or jurist recruitment unblocks new experiments.