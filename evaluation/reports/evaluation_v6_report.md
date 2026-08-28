# Evaluation v6 Report — Adversarial Validation of Signal Ablation Variants

**Factory Direction Version:** 6  
**Evaluation Version:** 6  
**Date:** 2026-08-28  
**Global Seed:** 42 (frozen)  
**Slice:** Expanded 1,200 decisions (1000 from 2024 + 50 each from 2020-2023)  
**Baseline:** `center_projected` (768-dim pre-PCA from legal-distance v5)

---

## Executive Summary

Evaluation v6 completes the factory direction v6 mandate: **validate legal-distance unsupervised signal ablation results on the expanded 1,200-decision slice using adversarial benchmarks**, with `center_projected` as the frozen reference representation.

**Result: NEGATIVE.** No signal ablation variant beats `center_projected` on **both** adversarial gates (language dominance < 0.85 AND jurist pairwise > 0.5). The `citation_weights` variant passes both gates but is **degenerate** (collapses to single cluster, Jurivoc NMI=0.0, branch NMI=0.0).

**Critical Finding:** The v3 evaluation validated **64-dim `center_projected` (PCA-reduced)** which passes both gates (language_dom=0.766, pairwise=0.512). The v6 evaluation tests the **768-dim pre-PCA version** which fails jurist pairwise (0.491). This is a material discrepancy — **fractal-map and product must use the 64-dim frozen PCA version validated in v3**.

---

## Adversarial Gate Results

### Gate 1: Language Dominance (threshold < 0.85) — *Lower is better*
Measures fraction of k-NN (k=20) sharing the same language. Language should not dominate neighbors.

### Gate 2: Jurist Pairwise Preference (threshold > 0.5) — *Higher is better*
Simulated jurist prefers legally-relevant neighbors over language artifacts. Rate > 0.5 means majority of decisions have at least one legally-relevant neighbor in top-k.

| Variant | Language Dominance | Gate 1 | Jurist Pairwise | Gate 2 | Jurivoc L2 NMI | Hierarchy Sep | Notes |
|---------|-------------------|--------|----------------|--------|----------------|---------------|-------|
| **center_projected (768-dim)** | **0.774** | ✅ PASS | **0.491** | ❌ FAIL | 0.430 | 0.096 | Baseline; borderline on pairwise |
| **center_projected (64-dim, v3)** | **0.766** | ✅ PASS | **0.512** | ✅ PASS | 0.441 | 0.113 | **v3 validated version — USE THIS** |
| sachverhalt_tfidf | 0.770 | ✅ PASS | 0.269 | ❌ FAIL | 0.329 | 0.021 | v5 zoom-coherence winner |
| erwaegungen_tfidf | 0.904 | ❌ FAIL | 0.103 | ❌ FAIL | 0.309 | 0.032 | Language-dominated |
| norm_embeddings | 0.763 | ✅ PASS | 0.273 | ❌ FAIL | 0.205 | 0.005 | Weak legal structure |
| **citation_weights** | **0.459** | ✅ PASS | **0.729** | ✅ PASS | **0.000** | **0.000** | **DEGENERATE: single cluster** |
| sachverhalt+erwaegungen | 0.876 | ❌ FAIL | 0.123 | ❌ FAIL | 0.301 | 0.019 | Language-dominated |
| erwaegungen+norms | 0.917 | ❌ FAIL | 0.078 | ❌ FAIL | 0.319 | 0.024 | Language-dominated |
| erwaegungen+citations | 0.904 | ❌ FAIL | 0.103 | ❌ FAIL | 0.318 | 0.035 | Language-dominated |
| core_legal | 0.917 | ❌ FAIL | 0.078 | ❌ FAIL | 0.319 | 0.024 | Language-dominated |
| hybrid_erwaegungen_03 | 0.810 | ✅ PASS | 0.420 | ❌ FAIL | 0.422 | 0.094 | Best hybrid, still fails pairwise |
| hybrid_erwaegungen_05 | 0.912 | ❌ FAIL | 0.150 | ❌ FAIL | 0.371 | 0.069 | |
| hybrid_erwaegungen_07 | 0.929 | ❌ FAIL | 0.108 | ❌ FAIL | 0.349 | 0.048 | |
| hybrid_core_03 | 0.819 | ✅ PASS | 0.383 | ❌ FAIL | 0.437 | 0.092 | |
| hybrid_core_05 | 0.923 | ❌ FAIL | 0.128 | ❌ FAIL | 0.385 | 0.061 | |
| hybrid_core_07 | 0.938 | ❌ FAIL | 0.083 | ❌ FAIL | 0.364 | 0.034 | |

**Key:** ✅ = PASS, ❌ = FAIL. **Bold** = passes gate.

---

## Detailed Findings

### 1. Signal Ablation Variants — All Fail Adversarial Validation

**Legal-distance v5** (fractal-map harness) reported `sachverhalt_tfidf` as the best signal ablation variant (fine_purity=0.986, NMI=0.659). **On adversarial benchmarks, it fails jurist pairwise (0.269)** despite passing language dominance.

All `erwaegungen`-based variants **fail language dominance** (>0.85 threshold), confirming that the reasoning section is heavily language-contaminated without semantic blending.

**Norm embeddings** pass language dominance but fail jurist pairwise (0.273) and Jurivoc hierarchy alignment (separation=0.005), indicating weak legal topical structure.

**Citation weights** is the only variant passing both gates but collapses to a **single cluster** (1199 decisions in one cluster, branch_purity=0.474, branch_nmi=0.0). It has **zero Jurivoc recovery** (NMI=0.0 at both levels). It is useless as a standalone representation.

### 2. Center_Projected: 64-dim vs 768-dim Discrepancy

| Metric | 64-dim (v3, PCA output) | 768-dim (v6, pre-PCA) |
|--------|------------------------|----------------------|
| Language Dominance | 0.766 ✅ | 0.774 ✅ |
| Jurist Pairwise | **0.512 ✅** | **0.491 ❌** |
| Jurivoc L2 NMI | 0.441 | 0.430 |
| Jurivoc Hierarchy Sep | **0.113 ✅** | 0.096 ❌ |
| Cluster Coherence (branch NMI) | 0.373 | 0.280 |

**The 64-dim frozen PCA version (v3) is the validated baseline.** The 768-dim version degrades jurist usability and Jurivoc hierarchy alignment. **Fractal-map must use the 64-dim version.**

### 3. Cross-Language Transfer

- **erwaegungen_tfidf** achieves best zero-shot transfer (zero_shot_mean_nmi=0.259, PASS) but fails language dominance gate
- **center_projected (64-dim)** has negative transfer gap (-0.022), meaning zero-shot outperforms in-domain — strong multilingual invariance
- **citation_weights** has zero transfer (NMI=0.0) — completely degenerate

### 4. Jurivoc Hierarchy Alignment

Only **center_projected (64-dim)** and **hybrid_erwaegungen_03** / **hybrid_core_03** achieve meaningful hierarchy separation (>0.05 threshold). All erwaegungen-dominated variants fail.

### 5. Scale Stability (Frozen PCA)

All non-degenerate variants show **perfect position drift** (mean cosine similarity = 1.0 across all corpus sizes 200→1200). Neighbor preservation improves with corpus size as expected.

**Citation weights FAILS scale stability** (mean cosine=0.0) — embeddings change completely when corpus grows, confirming degeneracy.

### 6. Frontier Metric Learning — BLOCKED

No `frontier_metric_learning_jurivoc` team dispatched. Frontier directory empty in both `/tmp/lex_accepted/frontier/` and `/home/runner/work/LexMachina/LexMachina/frontier/`. Cannot validate supervised metric learning results.

### 7. Boilerplate Resistance — SKIPPED

Requires full decision text for perturbation test. Expanded slice metadata lacks full text. Corpus lane must provide.

---

## Comparison with Prior Evaluations

| Evaluation | Scope | Key Result |
|------------|-------|------------|
| v3 | center_projected (64-dim) on 1200 decisions | **PASSES both adversarial gates** (0.766, 0.512) |
| v4 | Legal embeddings (3 models) | All FAIL language dominance (>0.85) |
| v5 | Citation role embeddings (6 roles) | All DEGENERATE (identical, NMI=0.0) |
| v6 | Signal ablation variants (15) on 1200 decisions | **None beats center_projected on both gates** |

---

## Recommendations to Factory Director

### Immediate Actions

1. **Acknowledge evaluation v6 complete** with negative signal ablation result. No variant improves on center_projected.

2. **Direct legal-distance lane** to either:
   - Improve the **64-dim center_projected** baseline (which already passes both gates) by enhancing jurist pairwise from 0.512 → >0.6
   - Develop new signal combinations that pass both adversarial gates
   - Investigate why 768-dim degrades pairwise performance vs 64-dim

3. **Direct fractal-map lane** to use **64-dim center_projected (v3 frozen PCA version)**, NOT the 768-dim version tested in v6.

4. **Resolve frontier dependency**: Either dispatch `frontier_metric_learning_jurivoc` team with explicit charter, or remove from factory direction v7.

### Successor Evaluation Question (v7)

Focus on **improving jurist pairwise preference for center_projected** or **testing new hybrid formulations**:
- Can we boost center_projected jurist pairwise from 0.512 → 0.65+ while maintaining language dominance <0.85?
- Do new signal combinations (e.g., sachverhalt + outcome + legal_area) pass both gates?
- Can metric learning on Jurivoc descriptors (if frontier dispatched) beat center_projected on adversarial benchmarks?

---

## Evidence Preservation

All raw outputs preserved as first-class evidence:
- `results/evaluation/v3_evaluation_results.json` — 64-dim center_projected validation (PASSES both gates)
- `results/evaluation/v4_evaluation_results.json` — Legal embeddings validation (ALL FAIL)
- `results/evaluation/v5_evaluation_results.json` — Citation role validation (ALL DEGENERATE)
- `results/evaluation/v6_signal_ablation/v6_signal_ablation_adversarial_results.json` — Signal ablation adversarial validation (NEGATIVE RESULT)

Negative results are preserved per Research Protocol: "Accepted negative findings are first-class results."

---

## Reproducibility

- **Global seed:** 42 (frozen across all evaluations)
- **Slice:** Expanded 1,200 decisions (fixed composition)
- **Benchmarks:** Deterministic with frozen thresholds
- **Code:** `evaluation/run_v6_signal_ablation_adversarial.py` and benchmark modules in `evaluation/tests/`

---

## Audit Trail

- **Orchestration fix:** Fixed `run_all_cross_language_benchmarks` API mismatch (was passing 3 args, function takes 2) in `run_v6_signal_ablation_adversarial.py:427`
- **Re-run:** Completed successfully 2026-08-28 19:00:19
- **Prior failed run:** Logged in `evaluation/v6_run.log` (all variants ERROR due to API mismatch)
- **State file:** Updated `state/evaluation.json` with v6 results and REPRODUCED tier