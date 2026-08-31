# Evaluation v17b: Label-Normalization Effect Across All 6 Representations

**Run ID:** eval_v17b_label_normalization_all_reps
**GitHub Run:** 33374227571
**Direction Version:** 13
**Config Hash:** 4323f833fa72366a
**Seed:** 42
**Date:** 2026-08-31
**Lane:** evaluation
**Evidence tier:** EXPLORATORY (companion to v17)

---

## Purpose

v17 (this cycle) showed the baseline `center_projected_64dim` hierarchy-family
benchmarks improve materially when the noisy cross-lingual `legal_area` labels are
normalized. This companion extends that finding to **all 6 representations** that
v16 evaluated (baseline + best zero-shot hybrid + 4 v15 supervised combinations),
to confirm the effect is (a) uniform, and (b) does NOT distort the relative product
ranking among combinations.

## Frozen hypothesis

> For EVERY representation, normalized labels improve (or at least match) the raw
> values on all three hierarchy-family purity metrics; no representation is made
> worse by a material (>10%) margin.

## Result: CONFIRMED (uniform improvement)

| Representation | hier ratio | zoomfine ratio | legal ratio |
|---|---|---|---|
| center_projected_64dim | 1.202 | 1.223 | 1.148 |
| cited_outcome_hybrid_0.5 | 1.215 | 1.204 | 1.151 |
| linear_citation_concat | 1.189 | 1.194 | 1.127 |
| **linear_hybrid05_concat** | **1.240** | **1.277** | **1.153** |
| linear_citation_w3070 | 1.156 | 1.180 | 1.130 |
| linear_citation_ridge | 1.194 | 1.215 | 1.152 |

- `uniform_improvement_or_matching = True`; no representation worsened by >10%.
- Normalized unique labels = 54 for every representation (label count independent of
  embedding, as expected).
- **linear_hybrid05_concat — the product-designated default COMBINATION — shows the
  LARGEST improvement** (hierarchy +24.0%, zoom fine +27.7%, legal +15.3%).

## Interpretation

1. The v16 hierarchy-family **universal FAIL** (all 6 representations) was a shared,
   **representation-agnostic label artifact**. It hit every representation equally and
   did NOT differentially penalize any specific candidate.
2. Therefore the **relative product ranking is NOT distorted** by the label issue:
   `linear_hybrid05_concat` (best stable, lowest JP variance) remains the best default,
   and it actually benefits most from label normalization.
3. Raw-machinery re-run again reproduces v16 per-representation values (e.g.
   linear_hybrid05_concat raw hier best_purity=0.3084 ≈ v16), confirming machinery fairness.

## Evidence / Provenance

- Script: `evaluation/experiments/run_v17b_label_normalization_all_reps.py`
- Results: `results/evaluation/v17b_label_normalization_all_reps/`
- Tests: `tests/evaluation/test_v17b_label_normalization_all_reps.py` (6 PASS)

## Recommendation

Same as v17: corpus lane normalize `legal_area` labels; evaluation spec use a
normalized label input for the hierarchy-family benchmarks. Product integration of
`linear_hybrid05_concat` is unchanged and reinforced. No new benchmark run is
warranted under this factory-direction question this cycle.
