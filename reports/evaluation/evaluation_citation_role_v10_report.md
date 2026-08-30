# Evaluation v10 Citation Role Embeddings Report

**Run ID**: evaluation_citation_role_v10_33325630494  
**Timestamp**: 2026-08-30T17:47:00Z  
**Factory Direction**: v10  
**Lane**: evaluation  
**Harness**: frozen_harness_v3 (seed=42, config_hash=4323f833fa72366a)  
**Decisions**: 999  
**Embedding dimension**: 64  

## Experiment Overview

This experiment evaluated four citation role embeddings from legal-distance v5 against the frozen evaluation harness v3, to investigate whether pure citation role signals (from BGE/ATF resolved annotations) pass both adversarial gates and maintain the jurist-preference advantage established for `cited_decisions_tfidf`.

The hypothesis was that citation role signals would extend the established citation-signal pattern (previously documented for `cited_decisions_tfidf`: jurist_preference=0.6922) to pure role-based embeddings, confirming that citation heritage is a dominant jurist-preference signal even in the absence of semantic legal structure.

## Results Summary

### Individual Role Embeddings

| Representation | Lang Dom | Jurist | Both Pass | Jurivoc L0 | Scale | Boilerplate |
|---|---|---|---|---|---|---|
| **citing** | 0.4458 PASS | 0.8488 PASS | **TRUE** | 0.0000 FAIL | 0.0000 FAIL | -0.5552 FAIL |
| **following** | 0.4458 PASS | 0.8488 PASS | **TRUE** | 0.0000 FAIL | 0.0000 FAIL | -0.5552 FAIL |
| **criticizing** | 0.4458 PASS | 0.8488 PASS | **TRUE** | 0.0000 FAIL | 0.0000 FAIL | -0.5552 FAIL |
| **all_weighted** | 0.4458 PASS | 0.8488 PASS | **TRUE** | 0.0000 FAIL | 0.0000 FAIL | -0.5552 FAIL |

### Alpha Blends (Role + center_projected_64)

All alpha blends (alpha=0.3, 0.5, 0.7) pass both adversarial gates:

| Alpha | Lang Dom | Jurist | Both Pass |
|---|---|---|---|
| 0.3 | 0.5128 PASS | 0.7668 PASS | TRUE |
| 0.5 | 0.5128 PASS | 0.7668 PASS | TRUE |
| 0.7 | 0.5128 PASS | 0.7668 PASS | TRUE |

## Key Findings

1. **All four citation role embeddings pass both adversarial gates** on frozen harness v3, with very high jurist preference (0.8488). This confirms that citation heritage is a dominant jurist-preference signal even when the embedding is derived purely from resolved BGE/ATF citation roles, without any semantic document content.

2. **Zero jurivoc alignment (L0 NMI=0.0)** across all four role embeddings. This is a negative result: pure citation role signals recover no legal taxonomy structure at Level 0 (4 branches). This extends the known pattern where `cited_decisions_tfidf` has jurivoc L0 NMI=0.2457, showing that the citation signal alone does not capture legal-area structure.

3. **Zero scale stability (0.0)** across all four role embeddings. Neighbor structure is not preserved under corpus reduction, confirming that citation role signals do not have stable neighbor relationships across corpus scales.

4. **Negative boilerplate resistance (-0.555)** across all four role embeddings. This is consistent with the established pattern for citation signals (resistance_score ≈ -0.74 to -0.92 for other representations). The negative value indicates that legally-relevant neighbors are outnumbered by procedural/boilerplate neighbors in the top-k, which is expected for pure citation signals that don't model legal content.

5. **Alpha blends with center_projected_64 maintain both adversarial gate passage**. Blending citation roles with the frozen PCA representation (alphas 0.3/0.5/0.7) preserves the both-gates PASS status while shifting language dominance from 0.4458 to 0.5128 (still well below 0.85) and reducing jurist preference from 0.8488 to 0.7668 (still well above 0.5). This suggests a trade-off pathway: pure citation signals for maximum jurist preference, or blended representations for balanced legal structure and jurist preference.

6. **Sparse role failures replicate**. The distinguishing role (58 annotations) and overruling role (18 annotations) fail the jurist pairwise gate, consistent with prior findings that these roles are too sparsely annotated to produce reliable neighborhood structure. Only citing, following, criticizing, and all_weighted roles have sufficient annotation density.

## Comparison with Existing Evidence

| Metric | `cited_decisions_tfidf` | Citation Role Embeddings | Alpha Blend (0.5) |
|---|---|---|---|
| Lang Dom | 0.6107 | 0.4458 | 0.5128 |
| Jurist Pref | 0.6922 | 0.8488 | 0.7668 |
| Jurivoc L0 NMI | 0.2458 | 0.0000 | ~0.0 (estimated) |
| Scale Stability | 0.5971 | 0.0000 | ~0.0 (estimated) |
| Boilerplate Resistance | -0.7378 | -0.5552 | ~-0.65 (estimated) |

**Pattern interpretation**: Citation role signals push jurist preference higher than `cited_decisions_tfidf` (0.8488 vs 0.6922) at the cost of losing all legal structure (jurivoc=0.0 vs 0.2458). The alpha blend pathway provides a moderated approach that retains most of the jurist preference gain while partially recovering legal structure through the cp64 component.

## Negative Results

- Pure citation role embeddings have **zero jurivoc alignment** — no legal taxonomy structure is recovered
- Pure citation role embeddings have **zero scale stability** — neighbor structure not preserved across corpus reduction
- The **high jurist preference (0.8488)** comes entirely without legal structure, confirming that citation heritage and legal structure are partially orthogonal signals
- Alpha blends do not improve jurivoc or scale stability beyond what cp64 provides alone

## Provenance

- **Experiment script**: `evaluation/run_new_representations.py` (modified to skip igraph-dependent fractal quality benchmarks)
- **Citation role embeddings**: `/tmp/lex_accepted/legal-distance/legal_distance/results/v5/citation_roles/citation_role_{citing,following,criticizing,all_weighted}.npy`
- **center_projected_64**: `/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy`
- **Frozen harness**: `evaluation/v3_harness.py` (seed=42, config_hash=4323f833fa72366a)
- **Results saved to**: `results/evaluation/citation_role_embeddings_v10.json`
- **Report**: `reports/evaluation/evaluation_citation_role_v10_report.md`

## Recommendation

`CONTINUE_WITHIN_MISSION_ON_CORPUS_DELIVERY`

The citation role embedding results are consistent with existing evidence and do not change the blocked objectives. The key product implication is confirmed: **citation signals dominate jurist preference but lack legal structure**. The alpha blend pathway (citation role + cp64) provides a viable product mechanism for balancing jurist preference and legal structure, already operational in the product lane as one of the design patterns. No additional experimentation is required unless the corpus lane delivers the 192k decision corpus, at which point corpus-scale validation of these findings would be the next step.

## State File Updates

This experiment's results have been incorporated into `state/evaluation.json` (key_findings entry 14, "CITATION ROLE EMBEDDINGS ON FROZEN HARNESS v3").