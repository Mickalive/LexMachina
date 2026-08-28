# Evaluation Lane v3 — Final Report & Blocker Documentation

**Run ID:** `eval_v3_final_20260828`  
**Date:** 2026-08-28  
**Factory Direction Version:** 6  
**Lane:** evaluation  
**GitHub Run:** 33163438667  

---

## Executive Summary

The evaluation lane has **completed core baseline validation** on the expanded 1,200-decision slice. `center_projected` is validated as the **only representation passing BOTH critical adversarial gates** (language dominance < 0.85, jurist pairwise preference > 0.5).

However, **two validation dependencies from factory_direction v6 remain BLOCKED** on upstream delivery:

| Dependency | Status | Blocker |
|------------|--------|---------|
| Signal ablation variant validation (legal-distance v5) | **BLOCKED** | Embeddings not persisted as .npy files; only fractal-map zoom coherence results available |
| Frontier metric_learning_jurivoc validation | **BLOCKED** | No frontier team dispatched; frontier directory empty |

**Overall Verdict**: **EVALUATION V3 BASELINE VALIDATION COMPLETE — UPSTREAM BLOCKERS PREVENT FULL FACTORY DIRECTION V6 EXECUTION**

---

## V3 Objectives — Status

| Objective | Status | Evidence |
|-----------|--------|----------|
| Validate `center_projected` on adversarial benchmarks (1,200 decisions) | ✅ **COMPLETE** | `v3_evaluation_results.json`, `v4_evaluation_results.json`, `v5_evaluation_results.json` |
| Validate legal embeddings (3 models) on adversarial benchmarks | ✅ **COMPLETE** | All 3 FAIL language dominance gate (> 0.85) |
| Validate citation role embeddings (6 roles) on adversarial benchmarks | ✅ **COMPLETE** | All 6 DEGENERATE (identical embeddings, NMI=0.0) |
| Boilerplate resistance on `center_projected` | ✅ **COMPLETE** | PASS (correlation=0.126 in target range 0.1–0.4) |
| Scale stability (frozen PCA) on `center_projected` | ✅ **COMPLETE** | PERFECT (position drift mean cosine=1.0) |
| Jurivoc hierarchy alignment on `center_projected` | ✅ **COMPLETE** | PASS (separation=0.113 > 0.05) |
| Freeze evaluation harness with global seed=42 | ✅ **COMPLETE** | All benchmarks deterministic |
| **Validate signal ablation variants (adversarial)** | ❌ **BLOCKED** | Legal-distance did not persist embeddings |
| **Validate frontier metric learning (adversarial)** | ❌ **BLOCKED** | No frontier team dispatched |

---

## Critical Findings — Baseline Validation (COMPLETE)

### 1. `center_projected` Validated as Frozen Baseline

| Benchmark | Threshold | Result | Status |
|-----------|-----------|--------|--------|
| Adversarial Language Dominance | < 0.85 | **0.766** | ✅ PASS |
| Jurist Pairwise Preference | > 0.5 | **0.512** | ✅ PASS |
| Jurivoc Hierarchy Alignment | > 0.05 | **0.113** | ✅ PASS |
| Jurivoc L2 Descriptor Recovery (NMI) | > 0.3 | **0.441** | ✅ PASS |
| Boilerplate Resistance (correlation) | 0.1–0.4 | **0.126** | ✅ PASS |
| Scale Stability (frozen PCA position drift) | > 0.85 | **1.000** | ✅ PERFECT |
| Cluster Coherence (branch purity) | — | **0.873** | ✅ PASS |
| Zoom Task (purity improvement) | > 0% | **+4.6%** | ✅ PASS |
| Cross-Language Retrieval (recall@10) | > 0.2 | 0.156 | ❌ FAIL (known gap) |

**`center_projected` passes 7/8 adversarial benchmarks** — the only representation to pass BOTH critical gates.

### 2. Legal Embeddings — ALL FAIL Language Dominance Gate

| Model | Language Dominance | Jurist Pairwise | Jurivoc L2 NMI | Verdict |
|-------|-------------------|-----------------|----------------|---------|
| multilingual-e5-small | 0.999 | 0.003 | 0.502 | ❌ FAIL |
| paraphrase-multilingual-MiniLM | 0.972 | 0.058 | 0.384 | ❌ FAIL |
| xlm-roberta-base | 1.000 | 0.003 | 0.269 | ❌ FAIL |

Despite strong Jurivoc recovery and zero-shot transfer, **all fail catastrophically on language dominance** — they produce language maps, not legal maps.

### 3. Citation Role Embeddings — ALL DEGENERATE

All 6 roles (overruling, distinguishing, following, all_weighted, citing, criticizing) produce **identical embeddings**:
- Single cluster (branch_purity=0.467, branch_nmi=0.0)
- Jurivoc NMI=0.0 at both levels
- Cross-language retrieval PASS (0.256) but meaningless — embeddings are collapsed
- **Useless standalone without semantic blending**

---

## Blocked Dependencies — Detail

### Blocker 1: Signal Ablation Variant Validation

**Factory Direction v6 requirement**: "Validate legal-distance unsupervised signal ablation results (on center_projected baseline) ... using adversarial benchmarks"

**What legal-distance produced**: 24 signal ablation variants evaluated via fractal-map harness (hierarchical Leiden zoom coherence, branch purity, legal_area NMI). Key findings:

| Best Variants (fractal-map metrics) | Fine Purity | Legal Area NMI |
|-------------------------------------|-------------|----------------|
| sachverhalt_tfidf | 0.986 | 0.659 |
| hybrid_erwaegungen_07 | 0.986 | 0.659 |
| norm_embeddings | 0.974 | 0.606 |
| citation_weights | 1.000 | 0.688 |
| erwaegungen_tfidf | 0.972 | 0.634 |

**What evaluation needs**: The actual embedding matrices (.npy files) for each variant to run adversarial benchmarks (language dominance, jurist pairwise, Jurivoc hierarchy, scale stability, boilerplate resistance).

**Status**: Signal ablation script creates embeddings in-memory for fractal-map evaluation but **does NOT save .npy files**. No embedding artifacts available for adversarial validation.

**Required action**: Legal-distance lane must persist signal ablation variant embeddings (.npy files with aligned metadata) for evaluation validation.

### Blocker 2: Frontier Metric Learning Jurivoc Validation

**Factory Direction v6 requirement**: "frontier_metric_learning_jurivoc RUN — must beat center_projected on adversarial benchmarks"

**Expected deliverable**: Embeddings trained with supervised metric learning loss using Jurivoc descriptors as weak supervision.

**Status**: **Frontier directory empty** — no `frontier_metric_learning_jurivoc` team dispatched, no results produced.

**Required action**: Factory Director must dispatch `frontier_metric_learning_jurivoc` team per factory_direction v6.

---

## Evaluation Harness — Frozen & Reproducible

- **Global seed**: 42 (frozen across all v3/v4/v5 runs)
- **Slice**: 1,200 decisions (expanded: 1000 from 2024 + 50 each from 2020–2023)
- **Language distribution**: de=735, fr=403, it=62
- **Branch distribution**: strafrecht=306, zivilrecht=311, oeffentliches_recht=293, sozialversicherungsrecht=290
- **All thresholds pre-declared** in v3/v4 scripts before observation
- **All raw outputs preserved**: `v3_evaluation_results.json`, `v4_evaluation_results.json`, `v5_evaluation_results.json`
- **Negative results preserved as first-class evidence**: legal embeddings FAIL, citation roles DEGENERATE

---

## Evidence Chain — Complete & Immutable

### Primary Results
| Artifact | Path | Status |
|----------|------|--------|
| v3 baseline validation | `results/evaluation/v3_evaluation_results.json` | ✅ Verified |
| v4 alternative representations | `results/evaluation/v4_evaluation_results.json` | ✅ Verified |
| v5 integration summary | `results/evaluation/v5_evaluation_results.json` | ✅ Verified |

### Test Implementations
| Test | Path |
|------|------|
| Cross-language benchmarks | `evaluation/tests/cross_language_benchmarks.py` |
| Jurist usability simulation | `evaluation/tests/jurist_usability.py` |
| Jurivoc benchmarks | `evaluation/tests/jurivoc_benchmarks.py` |
| Scale benchmarks (frozen) | `evaluation/tests/scale_benchmarks_frozen.py` |
| Boilerplate resistance | `evaluation/tests/boilerplate_resistance.py` |

### Audit Gates (append-only)
- CYCLE_33138468914_GATE.json through CYCLE_33144769263_GATE.json
- All PASS, all preserved

### State File
- `state/evaluation.json` — Machine-readable, consistent with all audit gates
- `evidence_tier: "REPRODUCED"`
- `cycle_status: "COMPLETED"`
- `continue_recommended: false`
- `next_recommendation`: Documents blockers and required Factory Director action

---

## Recommendation to Factory Director

### 1. ADOPT `center_projected` as Frozen Baseline Representation
- Only representation passing BOTH adversarial gates on 1,200 decisions
- Passes boilerplate resistance, scale stability, Jurivoc hierarchy alignment
- Known gap: cross-language retrieval recall (0.156 < 0.2) — track for future improvement

### 2. MANDATE Frozen PCA for Production
- Product lane must use frozen PCA components (fit once on full corpus)
- Position drift = 1.0 perfect stability achieved

### 3. RESOLVE BLOCKER 1: Signal Ablation Embeddings
**Option A**: Coordinate with legal-distance to persist signal ablation variant embeddings (.npy files) for adversarial validation
**Option B**: Update factory direction to accept fractal-map zoom coherence results as sufficient validation for signal ablation variants
**Option C**: Defer signal ablation adversarial validation to next cycle

### 4. RESOLVE BLOCKER 2: Frontier Metric Learning
**Dispatch `frontier_metric_learning_jurivoc` team** with charter:
- Product capability: Supervised metric learning beating `center_projected` on adversarial benchmarks
- Precise question: Can Jurivoc-weakly-supervised metric learning produce embeddings with language dominance < 0.85 AND jurist pairwise > 0.5?
- Why-now evidence: `center_projected` validated as strong baseline; legal embeddings fail language dominance; citation roles degenerate
- Non-duplication: Not covered by legal-distance unsupervised work
- Acceptance test: Beat `center_projected` on both adversarial gates + Jurivoc hierarchy alignment

### 5. UPDATE FACTORY DIRECTION
Reflect that evaluation v3 **baseline validation is COMPLETE** and remaining validations require upstream delivery.

---

## Conclusion

**Evaluation v3 has successfully validated `center_projected` as the frozen baseline representation** for the fractal Google Maps of law. The adversarial benchmarks falsified all alternative representations tested (legal embeddings, citation roles).

**Two validation dependencies from factory_direction v6 remain blocked** on upstream delivery. The evaluation lane has done all it can with available artifacts. No further evaluation work is justified until blockers are resolved.

**The snapshot is audit-ready**: All claim-bearing outputs preserved, negative results documented as first-class evidence, complete traceability from v3 through v5, frozen global seed ensuring reproducibility.

---

**Verdict**: **EVALUATION LANE v3 BASELINE VALIDATION COMPLETE — AWAITING FACTORY DIRECTOR RESOLUTION OF UPSTREAM BLOCKERS**

---

*Generated by evaluation lane run 33163438667*  
*All evidence referenced in `state/evaluation.json` and results/evaluation/v3-5_evaluation_results.json*