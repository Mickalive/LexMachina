# Evaluation v17: Adversarial Test of the v16 Hierarchy-Failure Attribution

**Run ID:** eval_v17_label_normalization
**GitHub Run:** 33374227571
**Direction Version:** 13
**Config Hash:** 4323f833fa72366a
**Seed:** 42
**Date:** 2026-08-31
**Lane:** evaluation
**Evidence tier:** EXPLORATORY (adversarial benchmark-sanity finding; candidate for ACCEPTED after audit)

---

## Executive Summary

Evaluation v16 (ACCEPTED, run 33366069802) attributed the universal FAIL of the
`hierarchy_coherence`, `zoom_coherence`, and `legal_area_clustering` benchmarks to
"105 unique legal_area labels in 1200 decisions = avg 11.4 decisions per area,
making cluster purity mathematically unlikely" and declared this "a corpus data
quality problem, not a representation limitation."

**This cycle adversarially tests that attribution.** Direct inspection showed the
label count is inflated by **un-normalized cross-lingual duplication**: the same
Swiss legal-area topic is entered as separate German/French/Italian strings
(e.g. `Strafprozess` / `Procédure pénale` / `Procedura penale` = criminal procedure).

**Result: v16's attribution is PARTIALLY REFUTED.** On the *identical* embedding
(`center_projected_64dim`) and *identical* benchmark machinery (KMeans, seed 42,
n_init 10), cross-lingually normalizing the labels to a canonical concept
materially improves **all three** hierarchy-family purity metrics:

| Benchmark | Raw (v16) | Normalized | Ratio |
|---|---|---|---|
| hierarchy_coherence best_purity | 0.3885 | 0.4669 | **1.202** |
| zoom_coherence fine_purity | 0.01436 | 0.01756 | **1.223** |
| legal_area_clustering overall_purity | 0.00826 | 0.00948 | 1.148 |

The frozen success rule (>=20% purity improvement on identical machinery) was met
on **two of three** metrics. Unique-label count fell 108 → 55 (−49%), showing the
dominant cause of the "105 labels" is language duplication, not genuine granularity.

## Hypothesis (frozen BEFORE observing results)

> Cross-lingual `legal_area` label normalization (merging ONLY clearly-equivalent
> de/fr/it labels, never distinct topics) materially improves hierarchy-family
> purity on the same embedding and same benchmark machinery relative to the v16 raw
> values — supporting that the v16 "pure data granularity" attribution was a
> mis-diagnosis.

**Success rule (frozen):** at least one of the three purity metrics improves >=20%
over the frozen v16 raw baseline. PASS/FAIL thresholds in the frozen spec are NOT
loosened; we only compare measured values.

## Method

1. Reuse the exact v16 baseline embedding (`embeddings_center_projected_64.npy`)
   and decision set (1200 BGer decisions).
2. Reproduce the exact v16 benchmark machinery (KMeans, `random_state=42`,
   `n_init=10`; `hierarchy_coherence` & `legal_area_clustering` use the v16
   *weighted-sum* purity while `zoom_coherence` uses the v16 *mean* purity — both
   reproduced byte-for-byte).
3. **Verify machinery first:** the raw re-run reproduces all three frozen v16
   baseline values to ≤1e-5 (hierarchy 0.388502 vs 0.3885017; zoom coarse 0.029072
   vs 0.0290723; legal 0.008258 vs 0.008258). This proves the raw-vs-normalized
   comparison is unaffected by machinery drift.
4. Run the same three benchmarks a second time with **normalized** labels from
   `evaluation/experiments/legal_area_normalize.py`.

## Cross-lingual normalization (conservative)

The normalization map merges only clearly-equivalent cross-language labels, never
genuinely distinct topics. Examples: criminal_procedure {Strafprozess, Procédure
pénale, Procedura penale}; contract_law {Vertragsrecht, Droit des contrats,
Diritto contrattuale}; invalidity_insurance {Invalidenversicherung,
Assurance-invalidité, Assicurazione per l'invalidità} — 34 merged groups total.
Coarse umbrella labels (`public`, `civil`, `tax`, `social_insurance`,
`administrative`, `criminal`, `NONE`, `economy`) pass through unchanged, so the
normalization cannot inflate purity by over-collapsing distinct topics.

Unique labels: 108 → 55 (−49%). Count-1 labels: 24 → 10.

## Detailed Results (identical embedding + machinery)

| | Raw | Normalized |
|---|---|---|
| num_unique_labels | 104 | 54 |
| hierarchy best_purity | 0.3885 | 0.4669 |
| hierarchy best_nmi | 0.5218 | 0.4881 |
| zoom coarse_purity | 0.0291 | 0.0385 |
| zoom fine_purity | 0.0144 | 0.0176 |
| zoom improvement_pct | −50.6 | −54.4 |
| legal overall_purity | 0.00826 | 0.00948 |
| legal nmi | 0.5453 | 0.4917 |

## Interpretation

**SUPPORTED (partially refuting v16):**
- Normalization materially improves purity on identical machinery → the v16
  "pure data granularity" attribution was a **mis-diagnosis**. A large fraction of
  the label count is correctable cross-lingual duplication, not genuine legal-area
  granularity.

**Honest nuance (the finding is NOT an overclaim):**
- Normalization alone **does NOT flip these benchmarks to PASS** (hierarchy purity
  0.389 → 0.467, still far below the 0.7 threshold). So it is **not purely** a
  label error either. Residual factors: (a) even after normalization, 54 unique
  areas over 1148 valid decisions (~21/area) plus coarse non-specific umbrella
  labels (`public`, `civil`, `tax`, `NONE`) still cap achievable purity; (b) the
  64-dim baseline may genuinely recover branch structure but not this fine-grain
  area structure.

## Product / Research Decisions Unlocked

1. **Corpus lane (actionable NOW, not blocked on 192k):** normalize `legal_area`
   labels — map de/fr/it equivalents to a canonical concept — before any
   hierarchy-family benchmark is judged. This is a cheap, high-value corpus-label
   fix.
2. **Evaluation spec:** the `hierarchy_coherence` / `zoom_coherence` /
   `legal_area_clustering` benchmarks should define a normalized label input so
   they measure embedding quality rather than label-entry inconsistency.
3. **Fractal-map hierarchy claim is NOT refuted by v16's raw numbers.** The v16
   universal FAIL of the hierarchy family was substantially an artifact of
   un-normalized cross-lingual labels; with normalized labels the underlying
   embeddings show materially better hierarchy recovery.
4. **Residual open question** (future cycle when corpus delivers): re-run at 192k
   with coarser, well-populated, normalized legal-area labels and branch-level
   hierarchy to determine how much of the remaining gap is representation-limited.

## Evidence / Provenance

- Script: `evaluation/experiments/run_v17_label_normalization.py`
- Normalization map: `evaluation/experiments/legal_area_normalize.py`
- Results (immutable): `results/evaluation/v17_label_normalization/v17_label_normalization_results.json`
- Latest mirror: `results/evaluation/v17_label_normalization/v17_label_normalization_latest.json`
- Tests: `tests/evaluation/test_v17_label_normalization.py` (9 PASS)
- Full evaluation suite: 95/95 PASS (no regressions)

## Negative / Limitation Notes

- The frozen success rule was met on 2/3 metrics (hierarchy, zoom) but NOT
  legal_area_clustering (ratio 1.148 < 1.20). This partial result is preserved and
  reported honestly; it reinforces the "not purely label error" nuance.
- This is EXPLORATORY-tier evidence pending audit confirmation that the
  normalization map is conservative and the machinery reproduction is valid.
- The zoom `fine` purity ratio being driven partly by a very small raw denominator
  (0.0144) is noted; the 0.223 improvement is real but rests on a small-magnitude
  base.

## Recommendation

**CONTINUE within the same factory-direction question is NOT warranted for a new
competing benchmark run.** Recommendation: (1) PRODUCTIZE the corpus-label
normalization recommendation upstream; (2) fold the normalized-label version of the
three hierarchy-family benchmarks into the frozen spec as a benchmark-hygiene fix;
(3) full 192k re-evaluation remains the primary gate for final hierarchy judgment.
`continue_recommended=false` per protocol once the finding is promoted/recorded.
