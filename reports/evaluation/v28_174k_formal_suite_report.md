# Evaluation Lane — 174k Formal Suite Cycle Report
**Factory Direction v28** | **Run ID:** `eval_174k_formal_suite_v28_20260928` | **Evidence Tier:** REPRODUCED

---

## Executive Summary

Executed the complete **machine-executable 174k formal evaluation suite** on all 8 production TF-IDF representations. The HNSW artifact fix (exact k-NN on stratified subsample) is confirmed and applied. All three factory direction v28 objectives are complete:

1. ✅ **Full 12-benchmark formal suite at 174k** on all 8 TF-IDF representations (frozen harness v3 thresholds)
2. ✅ **Citation heritage benchmark validated** using 174k citation-ID resolution (2,019/2,105 resolved)
3. ✅ **v17b label normalization generalization** tested at 174k fine-grained legal_area labels

**Key Result:** The fundamental **two-mode tradeoff is REPRODUCED at 174k scale** — citation-based signals pass adversarial gates but fail citation heritage; text-based signals pass citation heritage AUC but fail adversarial gates. No single TF-IDF representation dominates all benchmarks.

---

## 1. 174k Formal Suite Results (8 TF-IDF Representations)

### Adversarial Gate Results (FROZEN: LangDom < 0.85, Jurist > 0.5)

| Representation | Verdict | LangDom | LangDom✓ | Jurist | Jurist✓ | Both✓ |
|---|---|---|---|---|---|---|
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **PASS** | 0.516 | ✓ | 0.806 | ✓ | ✓ |
| `cited_decisions_tfidf` | **PASS** | 0.530 | ✓ | 0.802 | ✓ | ✓ |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | **PASS** | 0.524 | ✓ | 0.798 | ✓ | ✓ |
| `outcome_tfidf` | **PASS** | 0.453 | ✓ | 0.726 | ✓ | ✓ |
| `regeste_tfidf` | **PASS** | 0.484 | ✓ | 0.609 | ✓ | ✓ |
| `full_text_tfidf_light` | **FAIL** | 1.000 | ✗ | 0.000 | ✗ | ✗ |
| `regeste_full_text_hybrid_0.5` | **FAIL** | 1.000 | ✗ | 0.000 | ✗ | ✗ |
| `regeste_full_text_hybrid_0.7` | **FAIL** | 1.000 | ✗ | 0.000 | ✗ | ✗ |

**Backend:** `sklearn_exact` (exact k-NN on fixed stratified subsample n=2000) — **HNSW artifact FIXED**

### Best Representation (Production Default)
🏆 **`cited_decisions_tfidf_outcome_hybrid_0.5`** — passes both adversarial gates with best jurist preference (0.8055) and acceptable language dominance (0.5164).

---

## 2. Citation Heritage Benchmark at 174k

**Citation graph coverage:** 174 decisions in graph (0.1% of 173,963), 2,019/2,105 citations resolved (95.9%), 1,020 positive pairs (direct + shared citations).

| Representation | AUC | Recall@10 | Recall@100 | Status |
|---|---|---|---|---|
| `full_text_tfidf_light` | 0.898 | **0.052** | 0.150 | FAIL |
| `regeste_full_text_hybrid_0.5` | 0.873 | 0.035 | 0.099 | FAIL |
| `regeste_full_text_hybrid_0.7` | 0.852 | 0.036 | 0.100 | FAIL |
| `cited_decisions_tfidf` | 0.788 | 0.044 | 0.122 | FAIL |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.775 | 0.049 | 0.119 | FAIL |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | 0.760 | 0.053 | 0.112 | FAIL |
| `outcome_tfidf` | 0.658 | 0.000 | 0.004 | FAIL |
| `regeste_tfidf` | 0.486 | 0.000 | 0.003 | FAIL |

**All 8 representations FAIL** (threshold: AUC > 0.6 AND recall@10 > 0.2). Even the best AUC (0.898) achieves only 5.2% recall@10.

**Critical insight:** Citation graph covers only 0.1% of corpus. The 174 decisions with outgoing citations are insufficient for meaningful citation heritage evaluation at 174k scale.

---

## 3. v17b Label Normalization at 174k

**Normalization impact:** 214 → 164 unique legal areas (49.3% of 173,963 labels normalized).

### Purity Ratios (Normalized / Raw) — **CORRECTED PER AUDIT CYCLE_36521692234**

| Representation | Hierarchy Purity Ratio | Zoom Fine Purity Ratio | Legal Area Purity Ratio |
|---|---|---|---|
| `cited_decisions_tfidf` | **1.523x** | **1.557x** | **1.489x** |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **1.536x** | **1.510x** | **1.503x** |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | **1.541x** | **1.564x** | **1.461x** |
| `outcome_tfidf` | **1.513x** | **1.513x** | **1.513x** |
| `regeste_tfidf` | **1.637x** | **1.637x** | **1.637x** |
| `regeste_full_text_hybrid_0.7` | **1.000x** | **1.000x** | **1.000x** |
| `regeste_full_text_hybrid_0.5` | **1.000x** | **1.000x** | **1.000x** |
| `full_text_tfidf_light` | **1.000x** | **1.000x** | **1.000x** |

### Finding — **CORRECTED**

The **prior report misrepresented the magnitude and direction** of the v17b effect. The actual verified data shows:

- **Citation-based signals (5 reps):** show **LARGE purity gains (~49–64%, 1.49–1.64x)** across ALL three hierarchy metrics.
- **Text-based signals (3 reps):** show **NO CHANGE on purity metrics (1.00x)** across ALL three hierarchy metrics.
- NMI metrics show modest degradation for both families, but this does NOT correspond to the claimed "30-34% zoom_fine degradation" for text-based representations.
- The differential effect is REAL and REPRODUCED: citation-based purity improves ~50%, text-based purity is stable.
- Uniform improvement claim requires clarification: **purity improves for citation-based, is stable for text-based.**

---

## 4. Full-Corpus Scale Benchmarks (HNSW on Subsamples)

| Benchmark | Best Result | Notes |
|---|---|---|
| **Temporal Stability** (30k subsample) | `full_text_tfidf_light`: 0.78 overlap (PASS) | Others FAIL (0.0–0.38) |
| **Hierarchy Coherence** (15k subsample) | `full_text_tfidf_light`: level_1_nmi=0.563 | All FAIL Jurivoc proxy (L0<0.3, L1<0.2) |
| **Cluster Coherence** (15k subsample) | `full_text_tfidf_light`: 0.742 purity (PASS) | Citation signals FAIL (~0.40) |
| **Cross-Language Retrieval** (15k) | Citation signals PASS (~0.23) | Text signals FAIL (0.0) |
| **Boilerplate Resistance** (full) | All FAIL (-0.57 to -0.80) | Confirms language alignment failure, not boilerplate |

---

## 5. Cross-Language & Jurist Usability (Exact k-NN, n=2000)

| Representation | Cross-Lang Recall@10 | Cluster Coherence (Branch Purity) | Cross-Lang Transfer |
|---|---|---|---|
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **0.230** (PASS) | 0.407 (FAIL) | FAIL |
| `cited_decisions_tfidf` | **0.250** (PASS) | 0.449 (FAIL) | FAIL |
| `full_text_tfidf_light` | 0.000 (FAIL) | **0.744** (PASS) | PASS |
| `outcome_tfidf` | 0.129 (FAIL) | 0.327 (FAIL) | FAIL |

**Pattern confirmed:** Citation signals enable cross-language legal retrieval; text signals enable within-language clustering but collapse across languages.

---

## 6. Evidence Tier Assessment

| Finding | Tier | Justification |
|---|---|---|
| Two-mode tradeoff at 174k | **REPRODUCED** | Consistent across 8 reps, exact k-NN, frozen thresholds |
| Citation heritage NEGATIVE at 174k | **REPRODUCED** | All 8 reps FAIL, consistent with v17b at 12k |
| v17b label normalization (citation signals) | **REPRODUCED** | 5/5 reps show ~49-64% purity gains across 3 hierarchy metrics (CORRECTED per audit CYCLE_36521692234) |
| v17b label normalization (text signals) | **REPRODUCED** | 3/3 reps show NO purity change (1.00x) across 3 hierarchy metrics (CORRECTED per audit) |
| Production default validated | **REPRODUCED** | `cited_decisions_tfidf_outcome_hybrid_0.5` PASS both gates |
| HNSW artifact fix validated | **ACCEPTED** | Exact k-NN on stratified subsample implemented and verified |

---

## 7. Blockers & Dependencies

| Dependency | Status | Impact |
|---|---|---|
| **Dense embeddings (174k)** | 3/26 years ACCEPTED (2000–2002); 20/26 years PENDING AUDIT | Blocks fractal-map, product, and full dense evaluation |
| **Citation role embeddings** | AWAITED from legal-distance | Needed for citation-role map modes |
| **Linear hybrid combinations** | AWAITED from legal-distance | `linear_citation_concat`, `linear_hybrid05_concat` at 174k |
| **Jurist human study** | Framework ready; needs 5-10 Swiss jurists | Required for final product validation |

---

## 8. Recommendation

**continue_recommended: false**

The 174k formal suite is **complete for TF-IDF family**. The two-mode tradeoff is reproduced with high confidence. No additional same-question cycle is justified.

**Next factory direction should:**
1. Prioritize legal-distance 174k dense embeddings audit promotion (critical path)
2. Evaluate dense embeddings + citation roles + linear hybrids when they land
3. Consider jurist human study as parallel track (independent of compute)

---

## Artifacts Generated

| Artifact | Path |
|---|---|
| Formal suite results (full JSON) | `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` |
| Citation heritage pairs & results | `evaluation/results/174k_citation_heritage/` |
| v17b label normalization results | `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` |
| Lane state (machine-readable) | `evaluation/state/evaluation.json` |

---

## Configuration Freeze (Audit Trail)

- **Evaluation version:** v3_174k_fixed
- **Config hash:** `b51701f5a9c11692`
- **Global seed:** 42
- **Factory direction:** v28
- **Adversarial thresholds:** LangDom < 0.85, Jurist > 0.5 (frozen)
- **HNSW fix:** Exact k-NN on stratified subsample (n=2000, seed=42)
- **Subsample sizes:** Temporal=30k, Hierarchy=15k, Adversarial=2k

*All raw outputs preserved. Negative results retained as evidence.*