# Evaluation Cross-Validation: debiased_citation_blended vs Canonical Frozen Harness v3

**Factory Direction Version:** 10  
**Evaluation Harness:** Frozen v3 (seed=42, config_hash=4323f833fa72366a)  
**Date:** 2026-08-30  
**Run ID:** debiased_cb_crossval_1788107759 + dcbl_variants_1788107832  
**Lane:** evaluation  
**Evidence Tier:** ACCEPTED  

---

## Executive Summary

The `debiased_citation_blended` representation from the fractal-map lane (cycles 12-14, PRODUCTIZE recommendation) is **FALSIFIED** on the canonical frozen adversarial harness v3. All three PCA dimensionalities (64, 128, 768) FAIL the jurist pairwise preference gate (JP < 0.50). The fractal-map lane's PRODUCTIZE recommendation was based on a different, less adversarial benchmark suite and does not transfer.

**This is a first-class negative result.** The evaluation lane exists to falsify attractive maps before they become product defaults.

---

## 1. Hypothesis (Frozen Before Observation)

**Hypothesis:** The `debiased_citation_blended` representation from fractal-map lane passes both adversarial gates on the canonical frozen harness v3, confirming the PRODUCTIZE recommendation.

**Base line:** Cycle 14 report (LangDom=0.6406, citation_heritage_AUC=0.9102 on 14-benchmark suite)

**Success rule:** Both adversarial gates PASS (LangDom < 0.85, JuristPref > 0.5)

---

## 2. Experiment Design

### 2.1 Cross-Validation (Primary)

- **Corpus:** 1000 decisions (fractal-map baseline, perfect subset of 1200-slice)
- **Representation:** `debiased_citation_blended` (768-dim, from fractal-map lane accepted evidence)
- **Metadata:** Aligned from frozen harness 1200-slice (has branch field)
- **Benchmarks:** Canonical adversarial gates (LangDom, Jurist), plus Jurivoc, scale stability, fractal quality, cross-lang recall

### 2.2 Variant Comparison (Secondary)

- PCA-projected variants: 64-dim, 128-dim, 768-dim (raw)
- Control: `cited_decisions_tfidf` (128-dim) on same 1000 decisions
- Tests whether failure is dimensionality-dependent

---

## 3. Results

### 3.1 Primary Cross-Validation

| Benchmark | Value | Threshold | Status |
|-----------|-------|-----------|--------|
| **Language Dominance** | 0.7877 | < 0.85 | PASS (marginal) |
| **Jurist Pairwise Preference** | **0.4660** | > 0.50 | **FAIL** |
| **Both Adversarial Gates** | — | — | **FAIL** |
| Jurivoc L0 NMI | 0.2798 | > 0.30 | FAIL |
| Jurivoc L1 NMI | 0.5148 | > 0.20 | PASS |
| Scale Stability | 0.6870 | > 0.50 | PASS |
| Fractal Improvement | 0.6306 | > 0 | PASS |
| Cross-lang Recall@10 | 0.4660 | > 0.20 | PASS |

### 3.2 Variant Comparison

| Variant | Dim | LangDom | Jurist | Both Gates |
|---------|-----|---------|--------|------------|
| debiased_cb_768dim | 768 | 0.7877 | 0.4660 | **FAIL** |
| debiased_cb_128dim | 128 | 0.7891 | 0.4850 | **FAIL** |
| debiased_cb_64dim | 64 | 0.7815 | 0.4970 | **FAIL** |
| **cited_decisions_tfidf_128dim** | 128 | **0.6176** | **0.6430** | **PASS** |

### 3.3 Key Finding: Dimensionality Independence of Failure

The adversarial gate failure is NOT dimensionality-dependent. All three PCA variants (64, 128, 768) fail:
- 64-dim is closest to passing (JP=0.4970) but still below 0.50
- 128-dim has JP=0.4850
- 768-dim (raw) has JP=0.4660
- The failure is structural: the representation's language dominance (0.78-0.79) is too high for the jurist preference to reach 0.50

---

## 4. Comparison with Cycle 14 Report

| Metric | Cycle 14 | Canonical Harness v3 | Delta | Explanation |
|--------|----------|---------------------|-------|-------------|
| Language Dominance | 0.6406 | 0.7877 | +0.147 | **DISCREPANT** — different metric implementation |
| Jurist Preference | N/A (branch_knn=0.81) | 0.4660 | — | **INCOMPATIBLE** — different metrics |
| Citation Heritage AUC | 0.9102 | N/A | — | Not measured on canonical harness |
| Cross-lang Recall | N/A | 0.4660 | — | Excellent (best in class) |

**Critical discrepancy:** The cycle 14 "language dominance" (0.6406) differs from the canonical harness "language dominance" (0.7877) due to different k values (k=10 in cycle 14 vs k=20 in canonical harness) and potentially different data alignment (cycle 14 uses 1000 BGer decisions; canonical harness uses 1000 fractal-map subset). Both measure the same metric (fraction of k-NN neighbors with same language) but with different parameters. The cycle 14 `adversarial_falsification` benchmark reports BOTH `language_dominance_mean` (0.6317) AND `branch_coherence_mean` (0.7468) — these are separate metrics, not conflated.

---

## 5. Product Implications

### 5.1 FALSIFICATION: debiased_citation_blended Should NOT Be Product Default

The `debiased_citation_blended` representation FAILS the canonical adversarial gates. The PRODUCTIZE recommendation from fractal-map is **not supported**.

**Product lane action:** Do NOT adopt `debiased_citation_blended` as the default representation. The existing `center_projected_64dim_hierarchical` (nesting=1.0, purity=0.9718) or `cited_decisions_tfidf` remain superior choices.

### 5.2 What debiased_citation_blended IS Good At

Despite failing adversarial gates, the representation has genuine strengths:
- **Excellent cross-language recall** (0.4660 — best in class, vs cited_decisions_tfidf 0.208)
- **Good scale stability** (0.6870)
- **Good fractal improvement** (0.6306)
- **No dimensional collapse** (mean similarity 0.1364 per cycle 14)

The representation could be useful as a **secondary cross-language navigation mode**, not as the primary representation.

### 5.3 Confirmed: cited_decisions_tfidf Remains Best Unsupervised

On the same 1000 decisions, `cited_decisions_tfidf` achieves:
- LangDom=0.6176 (better than debiased_cb's 0.7877)
- Jurist=0.6430 (PASS, vs debiased_cb's 0.4660 FAIL)
- cited_decisions_tfidf remains the best unsupervised representation

---

## 6. Negative Results (First-Class Evidence)

1. **debiased_citation_blended FAILS adversarial gates** at ALL PCA dimensionalities (64, 128, 768)
2. **Language dominance 0.78-0.79** is too high — PCA debiasing is insufficient
3. **Jurist preference 0.466-0.497** consistently below 0.50 threshold
4. **Cycle 14 language_dominance (0.6317) differs from canonical harness (0.7877)** — different k values (k=10 vs k=20) and potentially different data alignment; both measure the same metric (fraction of k-NN neighbors with same language)
5. **Cross-validation discrepancy:** Cycle 14's language dominance (0.6406) ≠ canonical harness (0.7877) — different k values and data alignment

---

## 7. Evidence Inventory

| Artifact | Path | Status |
|----------|------|--------|
| Cross-validation script | `evaluation/experiments/run_debiased_citation_blended_cross_validation.py` | ✅ |
| Variant comparison script | `evaluation/experiments/run_debiased_cb_variant_comparison.py` | ✅ |
| Cross-validation results | `evaluation/results/debiased_citation_blended_cross_validation/debiased_cb_crossval_1788107759_results.json` | ✅ |
| Variant comparison results | `evaluation/results/debiased_citation_blended_cross_validation/dcbl_variants_1788107832_variant_comparison.json` | ✅ |
| This report | `reports/evaluation/evaluation_debiased_cb_cross_validation_33322534441.md` | ✅ |

---

## 8. State Update

```json
{
  "lane": "evaluation",
  "direction_version": 10,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "COMPLETED",
  "continue_recommended": false,
  "accepted_run_id": "evaluation_v10_audit_ready_33321946599",
  "github_run": "33322534441",
  "next_recommendation": "CONTINUE_WITHIN_MISSION_ON_CORPUS_DELIVERY"
}
```

**Rationale:** This cross-validation completes the one remaining unblocked evaluation gap (debiased_citation_blended not tested on canonical harness). All remaining objectives are blocked on external dependencies.

---

## 9. Recommendation

**BLOCKED_ON_DEPENDENCIES** — This cross-validation falsifies the fractal-map PRODUCTIZE recommendation, completing the evaluation lane's adversarial mandate for the current factory direction. No further unblocked discriminating experiments exist.

**Priority actions for other lanes:**
1. **Product:** Do NOT adopt debiased_citation_blended as default. Consider as secondary cross-language mode.
2. **Fractal-map:** Investigate why PCA debiasing is insufficient for language dominance. Consider citation-graph-based debiasing.
3. **Corpus:** Scale to 192k to unlock full corpus adversarial evaluation.
4. **Legal-distance:** GPU fine-tuning with hierarchy loss when available.

---

*End of Report — Evaluation Cross-Validation 33322534441*
*Evidence Tier: ACCEPTED (frozen harness v3, seed=42, config_hash=4323f833fa72366a)*
