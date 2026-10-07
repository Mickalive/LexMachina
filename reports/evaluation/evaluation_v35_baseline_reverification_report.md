# Evaluation Lane V35: TF-IDF 174k Baseline Re-Verification Report

**Date**: 2026-10-07  
**Factory Direction**: v35  
**Lane**: evaluation  
**Run ID**: EVALUATION_V35_BASELINE_REVERIFIED_20261007  
**Evidence Tier**: TF-IDF_REVERIFIED_MUTATED_DENSE_UNVALIDATED  

---

## Executive Summary

The TF-IDF 174k production baseline has been **re-verified against the current accepted mount** (fractal-map embeddings). The original baseline freeze (2026-10-03) has been **compromised by post-freeze mutation** of the accepted mount embeddings during a fractal-map rebuild on 2026-10-07.

**Key Finding**: The accepted mount TF-IDF embeddings were modified after the original baseline freeze, invalidating the originally reported metrics. The production baseline **still passes both adversarial gates** but with degraded Jurist Preference (JP=0.556 vs 0.7345 originally).

---

## Mutation Timeline

| Event | Date | Details |
|-------|------|---------|
| Original baseline freeze | 2026-10-03 | 8/8 representations PASS, production JP=0.7345 |
| Fractal-map rebuild | 2026-10-07T21:16:21 | Accepted mount embeddings regenerated |
| Re-verification | 2026-10-07T21:35:34 | 6/8 PASS, production JP=0.556 |

The accepted mount files in `/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map_174k/` were last modified **2026-10-07T21:16:21**, four days **after** the original baseline freeze (2026-10-03).

---

## Re-Verified Adversarial Gate Results (Current Accepted Mount)

| Representation | Language Dominance | Status | Jurist Pairwise | Status | Both Pass |
|----------------|-------------------|--------|-----------------|--------|-----------|
| cited_decisions_tfidf | 0.445 | PASS | 0.558 | PASS | ✅ |
| **cited_decisions_tfidf_outcome_hybrid_0.5** | **0.448** | **PASS** | **0.556** | **PASS** | ✅ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.445 | PASS | 0.566 | PASS | ✅ |
| outcome_tfidf | 0.502 | PASS | 0.254 | **FAIL** | ❌ |
| regeste_tfidf | 0.421 | PASS | 0.359 | **FAIL** | ❌ |
| full_text_tfidf_light | 0.485 | PASS | 0.732 | PASS | ✅ |
| regeste_full_text_hybrid_0.5 | 0.483 | PASS | 0.732 | PASS | ✅ |
| regeste_full_text_hybrid_0.7 | 0.481 | PASS | 0.742 | PASS | ✅ |

**Summary**: 6/8 representations PASS both adversarial gates (vs 8/8 originally).

---

## Production Baseline Comparison

| Metric | Original Freeze (2026-10-03) | Re-Verified (2026-10-07) | Delta |
|--------|------------------------------|---------------------------|-------|
| Jurist Pairwise Preference | 0.7345 | 0.5560 | **-0.1785** |
| Language Dominance | 0.477 | 0.448 | -0.029 |
| Both Gates Pass | ✅ | ✅ | — |
| Beats Semantic Baseline (JP=0.43) | ✅ (0.7345 > 0.43) | ✅ (0.556 > 0.43) | — |

The production baseline **remains functionally valid** (passes both adversarial gates, beats semantic baseline) but Jurist Preference has degraded by 24%.

---

## Citation Heritage Benchmark (Production Baseline)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| AUC-ROC | 0.6492 | 0.65 | **FAIL** |
| Positive pairs (valid) | 710 | — | — |
| Negative pairs (valid) | 252 | — | — |
| Pos mean similarity | 0.514 | — | — |
| Neg mean similarity | 0.331 | — | — |

The citation heritage benchmark **barely misses** the threshold (0.6492 vs 0.65). Note: 30% of positive pairs and 75% of negative pairs were excluded due to zero-norm embeddings in the TF-IDF vectors.

---

## Dense Embedding Complementary Criteria (Unchanged, Unvalidated at 174k)

| Criterion | Threshold | Status | Evidence |
|-----------|-----------|--------|----------|
| Citation Heritage AUC | > 0.75 | **UNVALIDATED** | 24yr/158k: 0.792 [0.762, 0.824] PASS |
| Cross-lang Sachverhalt | > 0.2 | **UNVALIDATED** | 1K sample: 0.282 [0.267, 0.296] PASS |
| Cross-lang Dispositiv | > 0.1 | **UNVALIDATED** | 1K sample: 0.150 [0.141, 0.160] PASS |
| Cross-lang Erwaegungen | > 0.1 | **UNVALIDATED** | 1K sample: 0.094 [0.086, 0.102] FAIL |
| Linear Hybrid JP | > 0.60 | **UNVALIDATED** | 19-22yr: 0.61-0.67 PASS |

**Validation BLOCKED** pending corpus lane deliveries:
- bge_/bger_ ID mapping
- Parquet 2022-2026 (29,520 decisions missing)
- Section extraction at 174k scale

---

## Accepted Negative Findings

### 1. TF-IDF Baseline Mutation Post-Freeze (ACCEPTED_NEGATIVE)
- **Description**: Accepted mount TF-IDF embeddings mutated after original baseline freeze via fractal-map rebuild
- **Impact**: Original frozen baseline results (8/8 PASS, JP=0.7345) no longer reflect current accepted mount state
- **Reverified State**: 6/8 PASS, production baseline JP=0.556 (still PASS), citation_heritage AUC=0.649 (FAIL)
- **Remediation**: Baseline re-frozen with current accepted mount values; mutation documented for provenance

### 2. True OOS Jurist Preference Ceiling ~0.53 (ACCEPTED_NEGATIVE)
- **Value**: 0.53
- **Factory Target**: 0.7
- **Implication**: Dense embeddings cannot be primary navigation mode (confirmed by legal-distance v34)

### 3. V18 Coarse Hierarchy Failure (ACCEPTED_NEGATIVE)
- **Max Branch Purity**: 0.65
- **Threshold**: 0.7
- **Implication**: Coarse legal taxonomy recovery fails for dense embeddings

### 4. Citation Heritage Recall@10 Failure (ACCEPTED_NEGATIVE)
- **Max**: 0.0066
- **Implication**: Citation heritage is ranking signal, not retrieval signal

### 5. Boilerplate Resistance Dense Failure (ACCEPTED_NEGATIVE)
- **Implication**: Dense embeddings more susceptible to procedural boilerplate

---

## Data Blockers (Unchanged)

| Blocker | Status | Impact |
|---------|--------|--------|
| bge_/bger_ ID mapping | BLOCKING | Cannot align 174k dense embeddings with evaluation metadata |
| Parquet 2022-2026 | BLOCKING | 29,520 decisions missing, cannot compute 174k dense embeddings |
| Section extraction 174k | REQUIRED | Cross-lingual section alignment needs sachverhalt/erwaegungen/dispositiv at 174k |

---

## Recommendation

**continue_recommended: false** — The factory direction v35 question has been answered:
1. ✅ TF-IDF 174k evaluation re-verified and re-frozen as production baseline (with documented mutation)
2. ✅ Dense embedding complementary view acceptance criteria defined and frozen

**Next evaluation cycle triggers ONLY when legal-distance delivers 174k dense embeddings** for validation against the frozen complementary criteria.

The mutation is documented as an accepted negative finding. The production baseline remains functionally valid for product use (passes adversarial gates, beats semantic baseline). No further same-question cycles justified.

---

## Files Updated

- `evaluation/state/evaluation.json` — Machine-readable lane state (updated)
- `results/evaluation/tfidf_174k_formal_suite_baseline_reverified.json` — Re-verified baseline
- `reports/evaluation/evaluation_v35_baseline_reverification_report.md` — This report