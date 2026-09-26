# Evaluation Lane — 174k Formal Suite v29 Cycle Report
**Run ID:** `eval_174k_formal_suite_v29_20260926_180`  
**Date:** 2026-09-26  
**Factory Direction:** v29  
**Evidence Tier:** REPRODUCED  
**Status:** BLOCKED_ON_DEPENDENCIES (continue_recommended=false)

---

## Executive Summary

This cycle completes the machine-executable evaluation of **raw multilingual-e5 768-dim embeddings** for years 2000–2015 (16 years, **99,325 decisions**, ~57% of the 174k corpus) using the frozen formal suite (v3_174k_fixed, config hash `4323f833fa72366a`, HNSW artifact fix active). The TF-IDF family (8 representations) was already complete at 174k scale from v28.

**Key Result:** Raw multilingual-e5 embeddings **FAIL adversarial benchmarks** (language_dominance=0.9855, jurist_pairwise=0.0275) — language artifacts completely dominate nearest neighbors, preventing cross-language legal navigation. However, **within each language**, legal structure is captured (zero-shot cross-language transfer PASS, per-language branch NMI=0.44). This negative finding is preserved as evidence.

Legal-distance has now completed raw embeddings for **16/26 years (2000–2015)**, exceeding the v29 claim of 13/26 years. Transformed representations (center_projected, metric-learned, citation-hybrid) remain pending.

---

## 1. Raw Multilingual-E5 768-dim Embeddings (Partial: 2000–2015)

### 1.1 Evaluation Configuration
- **Representation:** `multilingual_e5_768dim_partial_2000_2015`
- **Corpus:** 99,325 decisions (years 2000–2015, 16 years)
- **Embedding dimension:** 768 (raw multilingual-e5-small, no legal-distance transformation)
- **Adversarial backend:** sklearn_exact on fixed stratified subsample (n=2000, seed=42)
- **Full-corpus backend:** HNSW on subsamples (temporal: 30k, hierarchy: 15k, boilerplate: full 99k)

### 1.2 Adversarial Benchmarks (EXACT k-NN on Valid Subset) — **FAIL**

| Benchmark | Score | Threshold | Status |
|-----------|-------|-----------|--------|
| Language Dominance (mean) | 0.9855 | < 0.85 | **FAIL** |
| Jurist Pairwise Preference | 0.0275 | > 0.5 | **FAIL** |
| Both Gates Pass | — | — | **FAIL** |

**Detail:** On the 2000-decision stratified subsample (43,573 valid decisions with known branch):
- 950 decisions had **only language-artifact neighbors** (same language, different branch)
- 23 decisions had **only legally-relevant neighbors** (same branch, different language)
- 32 had both; 995 had neither
- Jurist would be forced wrong in 47.5% of cases

### 1.3 Cross-Language Benchmarks (EXACT k-NN on Valid Subset)

| Benchmark | Result | Status |
|-----------|--------|--------|
| Zero-shot Cross-Language Transfer | mean NMI = 0.293 (gap = 0.007) | **PASS** |
| Language-Specific Representation Quality | per-lang branch NMI: de=0.386, fr=0.485, it=0.461 | **PASS** |
| Cross-Language Neighbor Quality | cross-lang same-branch sim = 0.007, same-lang same-branch = 0.846 | Context |

**Interpretation:** Embeddings successfully transfer legal structure across languages (zero-shot NMI ~0.29 ≈ in-domain NMI ~0.30). Within each language, branch structure is well-captured (NMI 0.39–0.48). **But** nearest neighbors are dominated by language (cross-lang same-branch similarity near zero).

### 1.4 Jurist Usability Benchmarks (EXACT k-NN on Valid Subset)

| Benchmark | Result | Status |
|-----------|--------|--------|
| Cluster Coherence (16 clusters) | branch purity = 0.62, language purity = 0.98, NMI = 0.27 | **FAIL** |
| Cross-Language Retrieval | recall@10 = 0.007 | **FAIL** |

**Interpretation:** Clusters are language-dominated (language purity 0.98), not legally coherent (branch purity 0.62). Cross-language legal retrieval fails completely.

### 1.5 Full-Corpus Scale Benchmarks (HNSW on Subsamples)

| Benchmark | Result | Status |
|-----------|--------|--------|
| Temporal Stability (30k) | neighbor overlap = 0.785 | **PASS** |
| Hierarchy Coherence (15k) | level_0 NMI = 0.016, level_1 NMI = 0.454, nesting = 0.600 | **FAIL** |
| Cluster Coherence (15k) | branch purity = 0.62, language purity = 0.98, NMI = 0.28 | **FAIL** |
| Cross-Language Retrieval Full (15k) | recall@10 = 0.002 | **FAIL** |
| Boilerplate Resistance (99k) | boilerplate rate = 0.962, legal rate = 0.038, resistance = -0.925 | **FAIL** |

### 1.6 Citation Heritage — **INSUFFICIENT_PAIRS**

- Citation graph source decisions: **174 decisions, all from 2020–2024**
- Target decisions in corpus: 924 (spanning 2000–2024)
- **Zero positive pairs** fall within the 2000–2015 evaluation subset
- 340 negative pairs available but no positives for AUC calculation
- **Conclusion:** Citation heritage benchmark at 174k scale has sparse coverage; not evaluable for this subset.

### 1.7 Key Finding (Preserved as Negative Evidence)

> **Raw multilingual-e5 768-dim embeddings are not usable for the legal map as-is.** They capture legal structure *within* each language (zero-shot transfer works, per-language branch NMI strong) but language artifacts dominate the neighbor graph (language dominance 0.9855, language purity 0.98). This confirms the need for legal-distance transformations (center projection, metric learning, citation hybridization) to suppress language artifacts before dense embeddings can serve as a legal map representation.

---

## 2. TF-IDF Family (8 Representations) — Already Complete at 174k (from v28)

No re-evaluation performed. Summary preserved from v28:

| Representation | Verdict | Adversarial Pass? | Key Strength | Key Weakness |
|----------------|---------|-------------------|--------------|--------------|
| cited_decisions_tfidf | FAIL | ✓ (lang_dom=0.45, jurist=0.72) | Adversarial, cross-lang retrieval | Hierarchy, boilerplate, zero-shot transfer |
| cited_outcome_hybrid_0.5 | FAIL | ✓ (lang_dom=0.48, jurist=0.75) | Adversarial, cross-lang retrieval | Hierarchy, boilerplate, zero-shot transfer |
| cited_outcome_hybrid_0.7 | FAIL | ✓ (lang_dom=0.50, jurist=0.78) | Adversarial, cross-lang retrieval | Hierarchy, boilerplate, zero-shot transfer |
| full_text_tfidf_light | FAIL | ✗ (lang_dom=1.0, jurist=0.0) | Zero-shot transfer, branch purity | Adversarial, cross-lang retrieval |
| outcome_tfidf | FAIL | ✗ | — | Most benchmarks |
| regeste_tfidf | FAIL | ✗ | — | Most benchmarks |
| regeste_full_text_hybrid_0.5 | FAIL | ✗ (lang_dom=1.0) | Zero-shot transfer, branch purity | Adversarial, cross-lang retrieval |
| regeste_full_text_hybrid_0.7 | FAIL | ✗ (lang_dom=1.0) | Zero-shot transfer, branch purity | Adversarial, cross-lang retrieval |

**Fundamental tradeoff persists:** Citation-based pass adversarial but fail cross-language transfer; text-based pass cross-language transfer but fail adversarial. **No TF-IDF representation passes all benchmarks at 174k.**

---

## 3. Citation Heritage at 174k (TF-IDF Family) — Complete (from v28)

Validated on frozen pair pool (137,314 positive + 137,314 negative, seed=42) using HNSW on full 174k corpus:

| Representation | AUC-ROC | Positive Recall@10 | nn_citation_rate@10 | Status |
|----------------|---------|---------------------|---------------------|--------|
| cited_decisions_tfidf | 0.789 | 0.048 | ~0.03 | PASS |
| cited_outcome_hybrid_0.7 | 0.775 | 0.049 | ~0.03 | PASS |
| cited_outcome_hybrid_0.5 | 0.759 | 0.050 | ~0.03 | PASS |
| regeste_full_text_hybrid_0.7 | 0.850 | 0.035 | ~0.04 | PASS |
| regeste_full_text_hybrid_0.5 | 0.871 | 0.035 | ~0.04 | PASS |
| full_text_tfidf_light | 0.897 | 0.053 | ~0.05 | PASS |
| outcome_tfidf | 0.658 | 0.000 | ~0.00 | PASS (barely) |
| regeste_tfidf | 0.486 | 0.004 | ~0.00 | **FAIL** |

**Corrected Finding (Audit CYCLE_36242734524):** AUC ranges 0.66–0.90 (not 0.72–0.97). Positive recall@10 ranges 0.00–0.053 (not 0.44–0.49). All representations have very low nn_citation_rate@10 (~3–5%) — they do not strongly encode citation structure in nearest neighbors despite AUC > 0.65.

---

## 4. v17b Legal_Area Label Normalization — Complete (from v28)

Tested whether v17b normalization (15–25% purity gain at 1k scale) generalizes to 174k fine-grained legal_area labels:

- **Label stats:** 214 raw → 164 normalized; 49.3% of labels changed across 173,963 decisions
- **Uniformity rule (frozen: >10% no-worsening on ALL hierarchy metrics):** **FAIL for 6/8 representations**
- **Passing:** cited_decisions_tfidf, regeste_tfidf only
- **Text-based reps:** ZERO purity improvement, severe NMI degradation (-24% to -30%)
- **Best normalized hierarchy_purity = 0.465 < 0.7 threshold** — fundamental granularity/coverage limits persist

---

## 5. Legal-Distance Progress Update (Corrected)

| Metric | v28 Claim | v29 Claim | **Actual (This Cycle)** |
|--------|-----------|-----------|-------------------------|
| Years complete | 3/26 (2000–2002) | 13/26 (2000–2012) | **16/26 (2000–2015)** |
| Decisions complete | ~19,441 (11%) | ~101,441 (58%) | **~99,325 (57%)** |
| Year completion rate | 11.5% | 50% | **61.5%** |

**Note:** The v29 factory direction stated 13/26 years (2000–2012). Actual checkpoints confirm 16/26 years (2000–2015) are complete in `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`. Only raw multilingual-e5 embeddings are available; transformed representations (center_projected, metric-learned, hybrids) are still pending.

---

## 6. HNSW Artifact Fix — Confirmed Active

The HNSW artifact (nearly identical k-NN graphs across representations at 174k scale, masking true differences) is **fixed for adversarial benchmarks**:

- **Adversarial benchmarks:** Exact k-NN (sklearn brute force) on fixed stratified subsample (n=2000, seed=42) from valid decisions
- **Full-corpus benchmarks:** HNSW still used by design (citation_heritage, temporal_stability, hierarchy family on subsamples, cross_language_retrieval_full, boilerplate)
- **Evidence:** v3 harness (HNSW) gave identical jurist_pairwise=0.122 for all 8 TF-IDF reps; exact k-NN gives differentiated jurist_pairwise=0.71–0.80, lang_dom=0.43–0.53

---

## 7. Blockers & Dependencies

| Blocker | Status | Detail |
|---------|--------|--------|
| Transformed dense embeddings (center_projected, metric-learned, hybrids) | **BLOCKED** | Legal-distance has raw embeddings for 2000–2015; transformations not yet computed at 174k scale |
| Citation roles (citing/following/criticizing α=0.3) | **BLOCKED** | Pending legal-distance |
| Linear hybrids (linear_citation_concat, linear_hybrid05_concat) | **BLOCKED** | Pending legal-distance |
| Years 2016–2025 raw embeddings | **BLOCKED** | Legal-distance year-split execution pending |
| Jurist human study | **EXTERNAL** | Framework ready; requires 5–10 Swiss jurists |

---

## 8. Recommendations

1. **CONTINUE_RECOMMENDED = false** — No additional same-question cycle justified for TF-IDF family or raw multilingual-e5. The negative finding on raw embeddings is preserved; transformed representations awaited.

2. **Legal-distance priority:** Compute transformed representations (center_projected_64/128/768dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3) for the 16 completed years (2000–2015). These are the representations that previously showed promise at 1k scale (center_projected PASS adversarial with lang_dom=0.78).

3. **Monitor remains active** — Will autonomously evaluate transformed dense representations as they land in `/tmp/lex_accepted/legal-distance/legal_distance/results/`.

4. **Citation heritage benchmark limitation documented** — Sparse citation graph coverage (174 source decisions, 2020–2024 only) limits utility at 174k scale. Consider alternative citation-structure benchmarks.

---

## 9. Evidence Artifacts

| Artifact | Path |
|----------|------|
| Formal suite evaluation (raw multilingual-e5 768dim, 2000–2015) | `evaluation/results/174k/dense_partial_2000_2015/dense_partial_2000_2015_eval_latest.json` |
| Citation heritage on partial dense | `evaluation/results/174k_citation_heritage/citation_heritage_multilingual_e5_768dim_partial_2000_2015.json` |
| Evaluation script (partial dense) | `evaluation/evaluate_174k_dense_partial.py` |
| Citation heritage script (partial) | `evaluation/run_citation_heritage_partial_dense.py` |
| Frozen config hash | `4323f833fa72366a` |
| Updated lane state | `state/evaluation.json` (direction_version=29) |

---

## 10. Audit Trail

- **Audit CYCLE_36242734524 (REVISE):** Corrected fabricated citation heritage metrics, clarified HNSW artifact fix scope, corrected formal suite pass/fail counts. Applied in v28.
- **Factory Direction v29:** Corrected legal-distance progress from 3/26 to 13/26 years (actual: 16/26 years).
- **This cycle:** No fabrication; all results computed from frozen harness on actual embeddings. Negative results preserved.

---

**Next Action:** Await transformed dense embeddings from legal-distance lane. Monitor will trigger evaluation automatically upon detection.