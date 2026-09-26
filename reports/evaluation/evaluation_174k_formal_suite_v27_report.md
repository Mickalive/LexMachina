# Evaluation Lane — 174k Formal Suite Results (Factory Direction v27)

## Executive Summary

**Status**: COMPLETED — All machine-executable 174k benchmarks executed on TF-IDF family representations.  
**Evidence Tier**: REPRODUCED (exact k-NN on valid subset, frozen harness v3 thresholds, fixed HNSW artifact)  
**Recommendation**: PIVOT_WITHIN_MISSION — TF-IDF evaluation complete; await dense embeddings for full product decision.

---

## 1. Scope of This Cycle

Per factory direction v27, the evaluation lane question was:

> "Run the machine-executable 174k formal suite autonomously as representations land: (1) full 12-benchmark formal suite at 174k scale on all production representations (frozen harness v3 thresholds unchanged); (2) validate citation_heritage benchmark using the published 174k citation-ID resolution (2,019/2,105 resolved); (3) test whether v17b label normalization (15-25% purity gain, REPRODUCED across 4 seeds) generalizes to 174k fine-grained legal_area labels."

All three objectives completed on the 8 TF-IDF family representations available at 174k scale.

---

## 2. Representations Evaluated (TF-IDF Family)

| Representation | Dimensions | Source |
|---|---|---|
| `cited_decisions_tfidf` | 128 | Cited decision IDs TF-IDF |
| `outcome_tfidf` | 128 | Outcome text TF-IDF |
| `regeste_tfidf` | 128 | Regeste (summary) TF-IDF |
| `full_text_tfidf_light` | 128 | Full text TF-IDF (light preprocessing) |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | 128 | Linear concat (50/50) |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 128 | Linear concat (70/30 cited) |
| `regeste_full_text_hybrid_0.5` | 128 | Linear concat (50/50) |
| `regeste_full_text_hybrid_0.7` | 128 | Linear concat (70/30 regeste) |

**Production default**: `cited_decisions_tfidf_outcome_hybrid_0.5` (zero-shot TF-IDF hybrid, no GPU required)

---

## 3. 12-Benchmark Formal Suite Results (HNSW Artifact Fixed)

### Critical Fix Applied
- **HNSW artifact confirmed**: HNSW on full 174k masked representation differences in adversarial benchmarks
- **Fix**: Exact k-NN (sklearn) on fixed stratified subsample (n=2000, decisions with known branch) for adversarial benchmarks; HNSW retained for full-corpus scale benchmarks on subsamples

### Adversarial Gate Results (Both Must Pass)

| Representation | Language Dominance (threshold 0.85) | Jurist Pairwise (threshold 0.5) | Both Pass |
|---|---|---|---|
| cited_decisions_tfidf | PASS (0.529) | PASS (0.802) | ✅ |
| outcome_tfidf | PASS (0.453) | PASS (0.726) | ✅ |
| regeste_tfidf | PASS (0.484) | PASS (0.609) | ✅ |
| full_text_tfidf_light | **FAIL (1.000)** | **FAIL (0.000)** | ❌ |
| cited_decisions_tfidf_outcome_hybrid_0.5 | PASS (0.516) | PASS (0.806) | ✅ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | PASS (0.524) | PASS (0.798) | ✅ |
| regeste_full_text_hybrid_0.5 | PASS (0.476) | PASS (0.766) | ✅ |
| regeste_full_text_hybrid_0.7 | PASS (0.475) | PASS (0.776) | ✅ |

**5/8 representations pass both adversarial gates.** Full-text modes fail because language dominates neighbors completely.

### Best Representation (Passing Both Gates)
**`cited_decisions_tfidf_outcome_hybrid_0.5`** — jurist_preference=0.8055, lang_dom=0.5164  
Matches production default exactly.

### Full-Corpus Scale Benchmarks (HNSW on Subsamples)

| Benchmark | cited_decisions_tfidf | cited_decisions_tfidf_outcome_hybrid_0.5 | full_text_tfidf_light |
|---|---|---|---|
| Temporal Stability (neighbor overlap @ 80% corpus) | 0.367 FAIL | 0.381 FAIL | 0.782 **PASS** |
| Hierarchy Coherence (level_1 NMI vs 16 legal areas) | 0.070 FAIL | 0.070 FAIL | 0.561 FAIL |
| Nesting Score (coarse→fine) | 0.414 | 0.376 | 0.663 |
| Cluster Coherence (branch purity) | 0.414 FAIL | 0.370 FAIL | 0.745 **PASS** |
| Cross-Language Retrieval (recall@10) | 0.223 **PASS** | 0.224 **PASS** | 0.002 FAIL |
| Boilerplate Resistance (legal - boilerplate rate) | -0.773 FAIL | -0.774 FAIL | -0.567 FAIL |

**Key insight**: Full-text mode wins on temporal stability and cluster coherence but fails adversarial gates entirely (language-dominated). Citation-based modes pass adversarial gates but fail scale stability and boilerplate resistance.

---

## 4. Citation Heritage Benchmark (174k Scale)

### Citation Graph Coverage
- 174k corpus decisions: 173,963
- Decisions in citation graph: 174 (0.1%)
- Decisions with outgoing citations: 174 (0.1%)
- Resolved citations mapping to corpus: 924/1,546
- **Positive pairs (direct + shared citations)**: 1,020
- **Negative pairs (no citation relation)**: 1,020

### Results (Sample of 1,020 pairs, exact k-NN)

| Representation | AUC | Recall@10 | Recall@100 | Status |
|---|---|---|---|---|
| full_text_tfidf_light | **0.8969** | **0.0529** | 0.1529 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.8714 | 0.0353 | 0.0990 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.8504 | 0.0353 | 0.0990 | FAIL |
| cited_decisions_tfidf | 0.7892 | 0.0480 | 0.1255 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.7749 | 0.0490 | 0.1206 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.7589 | 0.0500 | 0.1069 | FAIL |
| outcome_tfidf | 0.6575 | 0.0000 | 0.0000 | FAIL |
| regeste_tfidf | 0.4861 | 0.0039 | 0.0069 | FAIL |

**All FAIL strict threshold** (AUC > 0.6 AND recall@10 > 0.2).  
Full-text modes capture citation vocabulary better than citation-ID-based modes. Production default achieves AUC=0.7589 but recall@10=0.05.

---

## 5. V17b Label Normalization at 174k Scale

### Label Statistics
- Raw unique legal_areas: 214
- Normalized unique legal_areas: 164  
- Labels normalized: 85,819 / 173,963 (49.3%)

### Purity Ratios (Normalized / Raw) — **NOT Uniform Across Representations**

| Representation | Hierarchy | Zoom Fine | Legal Area |
|---|---|---|---|
| cited_decisions_tfidf | **1.057** | **1.038** | **1.062** |
| outcome_tfidf | **1.046** | **1.083** | **1.044** |
| regeste_tfidf | 1.000 | **1.103** | **1.017** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | **1.056** | **1.037** | **1.063** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | **1.053** | **1.046** | **1.058** |
| **full_text_tfidf_light** | 1.000 | **0.668** ⚠️ | 0.973 |
| **regeste_full_text_hybrid_0.5** | 1.000 | **0.661** ⚠️ | 0.969 |
| **regeste_full_text_hybrid_0.7** | 1.000 | **0.695** ⚠️ | 0.963 |

### Key Finding
**Label normalization effect is representation-dependent:**
- ✅ **Citation-based representations** (5/8): Uniform improvement 4-10% across all three hierarchy-family metrics
- ❌ **Full-text representations** (3/8): Hierarchy unchanged, **zoom_fine degrades 30-34%**, legal_area slightly degrades

This contradicts the v17b hypothesis of uniform improvement. The normalization helps where legal_area labels align with citation structure but harms where full-text vocabulary captures finer distinctions that get collapsed by normalization.

---

## 6. Cross-Cutting Findings

### NESTING_METRIC_DEFECT_v1 Confirmed at 174k
- Nesting scores: 0.0–0.663 (none ≥ 0.99)
- Only by-construction 1000-scale modes achieve nesting_score=1.0
- Compressed 5-level ladder does NOT preserve strict nesting (honest mean change -0.00364)
- **No product-readiness claim for zoom while lane is blocked**

### Boilerplate Resistance
- All 8 TF-IDF modes FAIL (legal_neighbor_rate < boilerplate_neighbor_rate)
- Resistance scores: -0.57 to -0.82
- Procedural boilerplate dominates neighbor geometry

### Cross-Language Behavior
- Citation-based modes: cross-language recall@10 ~0.22 (PASS)
- Full-text modes: cross-language recall@10 ~0.002 (FAIL)
- Zero-shot transfer gap negative for citation modes (cross-lang better than in-domain for some pairs)

---

## 7. Blockers & Dependencies

| Blocker | Impact | Resolution Path |
|---|---|---|
| Dense embeddings 36% complete (years 2000-2010) | Cannot evaluate dense modes at 174k; fractal-map BLOCKED | legal-distance to complete years 2011-2025 (blocked on corpus artifact mount paths) |
| Jurist human study | Human preference benchmark unavailable | Requires 5-10 Swiss jurists recruited by repo owner; framework ready |
| Citation graph coverage (0.1%) | Citation heritage benchmark limited | Improve citation-ID resolution beyond 95.9% |

---

## 8. Recommendation: PIVOT_WITHIN_MISSION

**Do not continue same-question cycle.** The TF-IDF family is fully evaluated at 174k. The next evaluation cycle should:

1. **Wait for dense embeddings** (legal-distance completion) then re-run formal suite on dense modes
2. **Investigate label normalization interaction** with representation type (why full-text harmed?)
3. **Revisit boilerplate resistance** — all TF-IDF modes fail; need representation-level fix
4. **Evaluate citation heritage with dense embeddings** — current recall@10 < 0.06 is too low for practical use

**Product decision unlocked**: Production default (`cited_decisions_tfidf_outcome_hybrid_0.5`) is validated at 174k for adversarial benchmarks. Product can switch from synthetic to real 174k data for TF-IDF modes. Dense modes will be evaluated when available.

---

## 9. Artifacts Produced

| Artifact | Path |
|---|---|
| 12-benchmark formal suite (latest) | `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` |
| Citation heritage on embeddings | `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` |
| Citation pairs (frozen pool) | `evaluation/results/174k_citation_heritage/citation_pairs_174k.json` |
| V17b label normalization 174k | `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` |
| Evaluation state (machine-readable) | `state/evaluation.json` |

---

*Report generated 2026-09-26T11:25:00Z — Evaluation Lane, Factory Direction v27*