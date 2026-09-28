# Evaluation Lane — Factory Direction v28 Completion Report

**Lane:** evaluation  
**Factory Direction Version:** 28  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETED  
**Continue Recommended:** false  
**Date:** 2026-09-28  
**Accepted Run ID:** `eval_174k_formal_suite_v28_20260928`

---

## Executive Summary

The evaluation lane has **completed all work** required by the factory direction v28 question. The formal benchmark suite has been executed at 174k scale on all available production representations. The lane is now **blocked on legal-distance** delivering additional dense embeddings beyond the 3 ACCEPTED years (2000-2002).

---

## Factory Direction v28 Question — Compliance Status

| Requirement | Status | Evidence |
|-------------|--------|----------|
| (1) Full 12-benchmark formal suite at 174k on all production representations (frozen harness v3) | ✅ **COMPLETE** | 8/8 TF-IDF reps evaluated; exact k-NN on stratified subsample (HNSW artifact fixed) |
| (2) Validate citation_heritage benchmark using 174k citation-ID resolution (2,019/2,105 resolved) | ✅ **COMPLETE** | Benchmark run on frozen 137k pair pool; all reps AUC 0.50-0.53 (TF-IDF), limited by 0.1% citation coverage |
| (3) Test v17b label normalization (15-25% purity gain) generalizes to 174k fine-grained legal_area labels | ✅ **COMPLETE** | Tested on all 8 TF-IDF reps; divergent results by signal type (citation-based gain 3-8%, text-based zoom_fine loss 30-34%) |

**Additional work completed:** 3-year dense embeddings (2000-2002) evaluated — all FAIL adversarial gates.

---

## Key Findings (Reproduced at 174k Scale)

### 1. Two-Mode Tradeoff Persists
- **Citation-based reps** (`cited_decisions_tfidf`, `cited_decisions_tfidf_outcome_hybrid_0.5/0.7`): **PASS both adversarial gates**
  - Language dominance: 0.45–0.53 (threshold: <0.85)
  - Jurist preference: 0.72–0.81 (threshold: >0.5)
- **Text-based reps** (`full_text_tfidf_light`, `regeste_full_text_hybrid_0.5/0.7`): **FAIL both gates**
  - Language dominance: ~1.0
  - Jurist preference: ~0.0

### 2. Citation Heritage Limited by Sparse Graph
- Only 174 decisions (0.1%) have outgoing citations in 174k corpus
- All reps achieve AUC 0.50–0.53 (TF-IDF) — no meaningful discrimination
- `cited_decisions_tfidf` best citation-based (AUC 0.788 on resolved pairs); `full_text_tfidf_light` best overall (AUC 0.898) but language-dominated

### 3. v17b Normalization Diverges by Signal Type
| Representation Type | Hierarchy Purity | Zoom Fine Purity | Legal Area Purity |
|---------------------|------------------|------------------|-------------------|
| Citation-based (5 reps) | **+3–8%** | **+3–8%** | **+4–6%** |
| Text-based (3 reps) | ~0% | **−30 to −34%** | **−3 to −4%** |

**Interpretation:** Normalization helps structured signals (citations, outcomes) but destroys cross-lingual alignment in full-text/regeste signals.

### 4. Dense Embeddings (3yr) Fail Adversarial Gates
- Raw multilingual-e5 embeddings: lang_dom 0.997, jurist 0.008
- center_projected (64/128/768 dim): lang_dom 0.97–0.99, jurist 0.04
- **Confirms:** Language overclustering persists at 12.5k scale; center_projected insufficient without hierarchy preservation loss

### 5. Production Default Validated
- `cited_decisions_tfidf_outcome_hybrid_0.5` (PRODUCT_SERVING_DEFAULT): **PASS** (lang_dom=0.516, jurist_pref=0.806)
- Best stable combination per v15b evidence

---

## Blocked Dependencies

The lane cannot proceed with further evaluation cycles until legal-distance delivers:

1. **174k dense embeddings** — only 3/26 years ACCEPTED (2000-2002, ~12,570 decisions, 7.2%); years 2003-2019 pending audit
2. **Citation role embeddings** (citing/following/criticizing) — not yet available at 174k scale
3. **Linear hybrid embeddings** — not yet available at 174k scale
4. **Section-specific cross-lingual evaluation** — requires 174k dense embeddings

---

## Evidence References (ACCEPTED)

1. `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Full formal suite results
2. `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` — Citation heritage benchmark
3. `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` — v17b normalization test
4. `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json` — 3-year dense evaluation

---

## Recommendation

**BLOCKED_ON_DEPENDENCIES** — No further same-question cycle justified. The Factory Director should:
- Wait for legal-distance to promote additional dense embedding years through audit
- Then dispatch a successor evaluation cycle for the new representations
- Consider jurist human study (framework ready, requires 5-10 Swiss jurists) as parallel track

---

## Provenance

- Config hash (frozen harness v3): Verified in all result files
- Global seed: 42 (reproducible)
- HNSW artifact fix: Exact k-NN on stratified subsample (n=2000) for adversarial benchmarks
- All results preserved; negative results retained as first-class evidence