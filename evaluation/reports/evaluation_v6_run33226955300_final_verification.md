# Evaluation v6 — Final Verification Report (Run 33226955300)

**Factory Direction Version:** 6  
**Lane:** evaluation  
**GitHub Run:** 33226955300  
**Date:** 2026-08-29  
**Global Seed:** 42 (frozen)

---

## Executive Summary

This run **re-verifies the evaluation v3 adversarial benchmark suite** on the expanded 1,200-decision slice with the frozen global seed (42). All critical benchmarks reproduce **exactly** (bit-for-bit for adversarial gates), confirming the evaluation harness is frozen, deterministic, and reproducible.

**Verdict: REPRODUCIBILITY CONFIRMED — EVALUATION HARNESS FROZEN AND VALIDATED**

---

## Reproduction Results

### Critical Adversarial Gates (Exact Match)

| Benchmark | Threshold | Authoritative (Run 33226158716) | This Run (33226955300) | Delta | Status |
|-----------|-----------|--------------------------------|------------------------|-------|--------|
| Adversarial Language Dominance | < 0.85 | **0.7659583333333334** | **0.7659583333333334** | 0.0 | ✅ EXACT MATCH |
| Jurist Pairwise Preference | > 0.5 | **0.5121** | **0.5121** | 0.0 | ✅ EXACT MATCH |
| Jurivoc Hierarchy Alignment | > 0.05 | **0.11275120079517365** | **0.11275120079517365** | 0.0 | ✅ EXACT MATCH |

### Full Benchmark Suite Reproduction

| Benchmark Family | Benchmarks | Authoritative | This Run | Status |
|------------------|------------|---------------|----------|--------|
| Cross-Language | 4 | 3/4 PASS | 3/4 PASS | ✅ IDENTICAL |
| Jurist Usability | 4 | 2/4 PASS | 2/4 PASS | ✅ IDENTICAL |
| Jurivoc | 5 | 4/5 PASS | 4/5 PASS | ✅ IDENTICAL |
| Scale Stability | 5 growth steps | COMPLETED | COMPLETED | ✅ IDENTICAL |
| Boilerplate Resistance | — | SKIP (no full text) | SKIP (no full text) | ✅ CONSISTENT |

All numerical values match to full floating-point precision. No variance observed.

---

## Center_Projected Baseline — Validated Configuration

The **64-dim frozen PCA version** of `center_projected` is the authoritative baseline:

| Property | Value |
|----------|-------|
| Embedding dimension | 64 (frozen PCA from 768-dim) |
| Slice | 1,200 decisions (expanded: 1000 from 2024 + 50 each 2020–2023) |
| Language distribution | de=735, fr=403, it=62 |
| Branch distribution | strafrecht=306, zivilrecht=311, oeffentliches_recht=293, sozialversicherungsrecht=290 |
| Global seed | 42 (frozen) |
| PCA variance removed (debias) | 0.2165 |
| PCA cumulative variance (64-dim) | 0.8545 |

**Key Finding Re-confirmed:** The 768-dim pre-PCA version fails jurist pairwise (0.491), while the 64-dim frozen PCA version passes (0.512). **Fractal-map and product MUST use the 64-dim frozen PCA version.**

---

## Signal Ablation Validation — Negative Result Confirmed

The v6 signal ablation adversarial validation (15 variants + baseline) remains the authoritative negative result:

- **No signal ablation variant beats `center_projected` on both adversarial gates**
- `citation_weights` passes both gates but is **degenerate** (single cluster, Jurivoc NMI=0.0)
- All `erwaegungen`-based variants fail language dominance (>0.85)
- `sachverhalt_tfidf` (fractal-map winner) fails jurist pairwise (0.269)
- `hybrid_erwaegungen_0.3` (best hybrid) fails jurist pairwise (0.420)

**This negative result is preserved as first-class evidence per Research Protocol.**

---

## Frontier Metric Learning — Still Blocked

| Dependency | Status | Required Action |
|------------|--------|-----------------|
| `frontier_metric_learning_jurivoc` team | **BLOCKED** | Factory Director must dispatch team with explicit charter |
| Embeddings for validation | **NOT AVAILABLE** | Frontier team must produce supervised metric learning embeddings |
| Adversarial validation | **CANNOT PROCEED** | Requires frontier team delivery |

The frontier directory remains empty in both `/tmp/lex_accepted/frontier/` and `/home/runner/work/LexMachina/LexMachina/frontier/`.

---

## Boilerplate Resistance — Confirmed from Prior Run

Boilerplate resistance for `center_projected` was validated in run 33221325181 (100-decision sample with full text):

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Mean cosine similarity (after boilerplate injection) | 0.95 | — | — |
| Resistance score (1 - cosine) | 0.050 | < 0.3 | ✅ PASS |
| Interpretation | HIGHLY RESISTANT | — | ✅ PASS |

**Note:** Expanded slice (1,200 decisions) lacks full text. Corpus lane must provide for full validation.

---

## Frozen Harness Specification

The evaluation harness is **frozen** with the following immutable properties:

1. **Global seed:** 42 (set before any numpy/random operations)
2. **Slice:** Expanded 1,200 decisions (fixed composition, fixed order)
3. **Benchmarks:** All thresholds pre-declared in code before observation
4. **Determinism:** All benchmarks produce identical results across runs
5. **Code version:** `evaluation/run_v3_evaluation.py` and `evaluation/tests/*.py` modules

### Benchmark Thresholds (Immutable)

| Benchmark | Threshold | Direction |
|-----------|-----------|-----------|
| Adversarial Language Dominance | 0.85 | Lower = better (PASS if < 0.85) |
| Jurist Pairwise Preference | 0.5 | Higher = better (PASS if > 0.5) |
| Jurivoc L1 Descriptor Recovery (NMI) | 0.3 | Higher = better |
| Jurivoc L2 Descriptor Recovery (NMI) | 0.3 | Higher = better |
| Jurivoc L1 k-NN Purity | 0.4 | Higher = better |
| Jurivoc L2 k-NN Purity | 0.4 | Higher = better |
| Jurivoc Hierarchy Alignment (separation) | 0.05 | Higher = better |
| Cross-Language Retrieval (recall@10) | 0.2 | Higher = better |
| Boilerplate Resistance Score | 0.3 | Lower = better (PASS if < 0.3) |

---

## Evidence Chain — Complete & Immutable

### Primary Results (This Run)
- `results/evaluation/v3_evaluation_results.json` — Complete v3 benchmark suite on 1,200 decisions

### Prior Results (Preserved)
- `results/evaluation/v3_evaluation_results.json` (authoritative, run 33226158716)
- `results/evaluation/v4_evaluation_results.json` — Legal embeddings validation (ALL FAIL)
- `results/evaluation/v5_evaluation_results.json` — Citation roles validation (ALL DEGENERATE)
- `results/evaluation/v6_signal_ablation/v6_signal_ablation_adversarial_results.json` — Signal ablation adversarial validation (NEGATIVE RESULT)
- `results/evaluation/center_projected_boilerplate_resistance.json` — Boilerplate resistance on 100 decisions

### Test Implementations (Frozen)
- `evaluation/tests/cross_language_benchmarks.py`
- `evaluation/tests/jurist_usability.py`
- `evaluation/tests/jurivoc_benchmarks.py`
- `evaluation/tests/scale_benchmarks_frozen.py`
- `evaluation/tests/boilerplate_resistance.py`

### State File
- `state/evaluation.json` — Machine-readable, updated with this run's verification

---

## Recommendation to Factory Director

### 1. ACCEPT Evaluation Lane v6 as COMPLETE
- `center_projected` (64-dim frozen PCA) validated as the **sole representation passing both adversarial gates**
- All signal ablation variants **falsified** on adversarial benchmarks
- Legal embeddings **falsified** on language dominance
- Citation roles **falsified** (degenerate)
- Evaluation harness **frozen and reproducible** (global seed 42)

### 2. MANDATE 64-dim Frozen PCA for Production
- Product lane must use the 64-dim PCA output, NOT the 768-dim pre-PCA embeddings
- Frozen PCA components must be persisted and reused (not re-fit)

### 3. RESOLVE FRONTIER DEPENDENCY
**Option A:** Dispatch `frontier_metric_learning_jurivoc` team with charter:
- Product capability: Supervised metric learning beating `center_projected` on adversarial benchmarks
- Precise question: Can Jurivoc-weakly-supervised metric learning achieve language dominance < 0.85 AND jurist pairwise > 0.5?
- Why-now evidence: `center_projected` validated; all unsupervised alternatives falsified
- Acceptance test: Beat `center_projected` on both adversarial gates + Jurivoc hierarchy alignment

**Option B:** Remove from factory direction v7 if metric learning is deprioritized

### 4. CORPUS LANE DEPENDENCY
Provide full decision text for expanded 1,200-decision slice to enable boilerplate resistance validation at scale.

### 5. SUCCESSOR EVALUATION QUESTION (v7)
Focus on **improving jurist pairwise for center_projected** or **new hybrid formulations**:
- Can we boost center_projected jurist pairwise from 0.512 → 0.65+ while maintaining language dominance < 0.85?
- Do new signal combinations (sachverhalt + outcome + legal_area) pass both gates?
- Can metric learning (if frontier dispatched) beat center_projected?

---

## Conclusion

**Evaluation v3/v6 is COMPLETE and REPRODUCIBLE.** The frozen harness with global seed 42 produces identical results across independent runs. `center_projected` (64-dim) is the validated baseline. All alternative representations have been falsified on adversarial benchmarks.

The only remaining factory direction v6 dependency is the `frontier_metric_learning_jurivoc` team, which requires Factory Director action.

**No further evaluation work is justified on the current question.** The lane state `continue_recommended: false` is correct.

---

## Audit Trail

- **Run 33226158716:** Authoritative v3/v6 results (verified)
- **Run 33226955300:** This verification run — **EXACT REPRODUCTION CONFIRMED**
- **All raw outputs preserved** as first-class evidence
- **Negative results preserved** per Research Protocol
- **State file updated** with this run's verification

---

*Generated by evaluation lane run 33226955300*  
*All evidence referenced in `state/evaluation.json` and `results/evaluation/v3_evaluation_results.json`*