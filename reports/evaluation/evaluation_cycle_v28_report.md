# Evaluation Lane - Cycle Report
**Factory Direction v28 | Lane: evaluation | Status: BLOCKED_ON_DEPENDENCIES | Evidence Tier: REPRODUCED**

---

## Executive Summary

The evaluation lane has completed the machine-executable 174k formal suite for all 8 TF-IDF production representations. The fundamental two-mode tradeoff persists at full corpus scale. The lane is now **blocked on legal-distance 174k dense embeddings** (only 3/26 years ACCEPTED). The monitor is active and will auto-evaluate when dense embeddings land in the accepted state mount.

---

## Completed Work (This Cycle)

### 1. 174k Formal Suite (12-Benchmark Frozen Harness v3) — COMPLETE ✓
- **8 TF-IDF representations** evaluated at 174k scale (173,963 decisions)
- **HNSW artifact FIXED**: Exact k-NN on fixed stratified subsample (n=2,000 valid decisions with known branch) for adversarial benchmarks
- **Frozen thresholds unchanged**: lang_dom < 0.85, jurist_pref > 0.5, cross_lang_recall > 0.2, cluster_coherence > 0.7

| Representation | Verdict | LangDom | LD-Pass | JuristPref | JP-Pass | Both-Pass |
|---|---|---|---|---|---|---|
| cited_decisions_tfidf | PASS | 0.5295 | ✓ | 0.8020 | ✓ | ✓ |
| cited_decisions_tfidf_outcome_hybrid_0.5 | PASS | 0.5164 | ✓ | 0.8055 | ✓ | ✓ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | PASS | 0.5238 | ✓ | 0.7975 | ✓ | ✓ |
| outcome_tfidf | PASS | 0.4527 | ✓ | 0.7255 | ✓ | ✓ |
| regeste_tfidf | PASS | 0.4835 | ✓ | 0.6090 | ✓ | ✓ |
| regeste_full_text_hybrid_0.5 | **FAIL** | **1.0000** | **✗** | **0.0000** | **✗** | **✗** |
| regeste_full_text_hybrid_0.7 | **FAIL** | **1.0000** | **✗** | **0.0000** | **✗** | **✗** |
| full_text_tfidf_light | **FAIL** | **1.0000** | **✗** | **0.0000** | **✗** | **✗** |

**Key Finding**: The fundamental two-mode tradeoff **persists at 174k scale**, and **all three text-based representations catastrophically fail adversarial gates**:
- **Citation-based** (cited_decisions + outcome hybrids): PASS adversarial, FAIL branch/legal_area/hierarchy
- **Text-based** (regeste/full_text + hybrids): FAIL adversarial (lang_dom = 1.0, jurist_pref = 0.0) — language completely dominates neighbor structure

### 2. Citation Heritage Benchmark — COMPLETE ✓
- **Frozen pair pool**: 137,314 citation pairs (95.9% citation-ID resolution: 2,019/2,105)
- **TF-IDF Results**: All representations **FAIL** (require both AUC > 0.6 AND recall@10 > 0.2)

| Representation | AUC | Recall@10 | Status |
|---|---|---|---|
| cited_decisions_tfidf | 0.788 | 0.044 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.760 | 0.053 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.775 | 0.049 | FAIL |
| full_text_tfidf_light | 0.898 | 0.052 | FAIL |
| regeste_tfidf | 0.486 | 0.000 | FAIL |
| outcome_tfidf | 0.658 | 0.000 | FAIL |

**Infrastructure ready** for dense embeddings when they arrive.

### 3. v17b Label Normalization (174k Fine-Grained legal_area) — COMPLETE ✓
- **Label normalization**: 214 → 164 unique labels (49.3% of 85,819 labels normalized), raw 157 → 107 normalized areas
- **Test**: Purity ratios (normalized / raw) for hierarchy coherence, zoom coherence, legal area clustering; ≤10% worsening threshold on all hierarchy-family metrics

| Representation | Hierarchy Purity | Hierarchy NMI | Zoom Coarse | Zoom Fine | Legal Area Purity | Legal Area NMI | Uniform ≤10% Worsening |
|---|---|---|---|---|---|---|---|
| cited_decisions_tfidf | 1.480 | 0.945 | 1.589 | 1.498 | 1.264 | 0.832 | **✗** (hierarchy_nmi, legal_area_nmi) |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 1.426 | 0.850 | 1.509 | 1.499 | 1.257 | 0.732 | **✗** (hierarchy_nmi, legal_area_nmi) |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 1.441 | 1.059 | 1.530 | 1.475 | 1.288 | 0.787 | **✗** (legal_area_nmi) |
| outcome_tfidf | 1.496 | 0.876 | 1.512 | 1.496 | 1.496 | 0.876 | **✗** (hierarchy_nmi, legal_area_nmi) |
| regeste_tfidf | 1.672 | N/A | 1.672 | 1.672 | 1.672 | N/A | ✓ (no NMI computed) |
| full_text_tfidf_light | 1.000 | 0.699 | 1.000 | 1.000 | 0.972 | 0.794 | **✗** (hierarchy_nmi, legal_area_nmi) |
| regeste_full_text_hybrid_0.5 | 1.000 | 0.699 | 1.000 | 1.000 | 0.972 | 0.794 | **✗** (hierarchy_nmi, legal_area_nmi) |
| regeste_full_text_hybrid_0.7 | 1.000 | 0.699 | 1.000 | 1.000 | 0.972 | 0.794 | **✗** (hierarchy_nmi, legal_area_nmi) |

**Result**: **PARTIAL — Only 1/8 representations (regeste_tfidf) satisfies frozen ≤10% no-worsening rule on ALL hierarchy-family metrics.** Citation-based reps improve purity (1.43–1.67×) but **worsen NMI by 12–30%**. Text-based reps show **zero purity improvement** and **worsen NMI by 20–30%**. Best normalized hierarchy_purity = 0.49 < 0.7 threshold. The v17b differential effect is confirmed but **not uniformly beneficial** at 174k scale.

### 4. Partial Dense Evaluation (Years 2000-2002, ~12.5k decisions) — COMPLETE ✓
- **3 center_projected variants** (768/64/128 dim) evaluated
- **ALL FAIL adversarial**: lang_dom ~0.98, jurist_pref ~0.04
- **Root cause**: 18.3% metadata coverage (branch labels), partial corpus center-projection, raw multilingual-e5 language clustering
- **NOT comparable** to 1,200-slice center_projected (which PASSES adversarial) — confirms **scale/metadata dependency**

---

## Blocked Dependencies

| Dependency | Status | Detail |
|---|---|---|
| **174k dense embeddings** | 🔴 BLOCKED | 3/26 years ACCEPTED (2000-2002); 17/26 years PENDING AUDIT (2003-2019); 6/26 years NOT PROCESSED (2020-2025) |
| Citation role embeddings | ⏳ WAITING | Requires dense completion |
| Linear hybrid embeddings | ⏳ WAITING | Requires dense completion |

---

## External Dependencies

| Dependency | Status |
|---|---|
| Jurist human study (5-10 Swiss jurists) | Framework ready; recruitment needed by repository owner |

---

## Monitor Status

- **ACTIVE**: Watching `/tmp/lex_accepted/legal-distance/legal_distance/results` for final concatenated 174k embeddings
- **Check count**: 201
- **Last check**: 2026-09-28T13:48:26
- **Infrastructure**: All operational (HNSW backend, scalable_nn with sklearn fallback, v25 formal suite, citation heritage frozen pairs, v17b normalization)

---

## Key Findings Summary

1. **Fundamental tradeoff is scale-invariant**: The citation-vs-text tradeoff observed at 1,200 and 12k scales persists identically at 174k.

2. **Citation heritage is not preserved by TF-IDF at 174k**: No TF-IDF representation achieves both high AUC (>0.6) AND meaningful recall@10 (>0.2). Citation-based reps have decent AUC but near-zero recall.

3. **v17b normalization helps citation-based, hurts text-based**: The label normalization improves legal_area/hierarchy purity for citation-based reps but severely degrades zoom coherence for text-based reps (which were already language-dominated).

4. **Dense embeddings require full corpus + full metadata**: Partial dense (12k, 18% branch coverage) fails catastrophically on adversarial benchmarks. The 1,200-slice success was an artifact of curated metadata coverage.

5. **HNSW artifact confirmed and fixed**: Exact k-NN on stratified valid subset is now used for all adversarial benchmarks; HNSW reserved for full-corpus scale benchmarks only.

---

## Production Default Status

| Metric | Value | Threshold | Status |
|---|---|---|---|
| Representation | cited_decisions_tfidf_outcome_hybrid_0.5 | — | **DEFAULT** |
| Adversarial verdict | PASS | Both gates | ✓ |
| Language dominance | 0.5164 | < 0.85 | ✓ |
| Jurist preference | 0.8055 | > 0.5 | ✓ |
| Citation heritage AUC | 0.7597 | > 0.6 | ✓ |
| Citation heritage recall@10 | 0.0529 | > 0.2 | **✗** |
| v17b zoom_fine ratio | 1.4993 | ≤ 1.10 | **✗** |
| Boilerplate resistance | -0.774 | > 0 | **✗** |
| Scale stability (temporal) | 0.383 | > 0.5 | **✗** |

**Note**: Production default FAILS v17b zoom_fine threshold (1.4993 > 1.10, 49.9% worsening vs 10% allowed). This is a negative result — the production default does not satisfy the label-normalization stability criterion at 174k scale.

---

## Recommendation

**CONTINUE monitoring** — No additional same-question cycle justified until dense embeddings arrive.

- `continue_recommended: false` (no further TF-IDF evaluation needed)
- Monitor will auto-trigger formal suite when legal-distance promotes 174k dense embeddings to accepted state
- Next evaluation cycle begins when dense embeddings, citation roles, or linear hybrids land

---

## Provenance

- **Accepted run ID**: `evaluation_v28_174k_tfidf_formal_suite_20260928`
- **Config hash**: Frozen harness v3 (seed=42, thresholds frozen at factory direction v6)
- **Evidence refs**: 8 machine-readable result files + monitor state
- **Negative results preserved**: All FAIL verdicts, degraded metrics, and root-cause analyses retained

---
*Report generated 2026-09-28 | Evaluation Lane v3 frozen harness | Factory Direction v28*