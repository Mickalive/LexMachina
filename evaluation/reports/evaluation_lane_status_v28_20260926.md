# Evaluation Lane Status Report — Factory Direction v28

**Date**: 2026-09-26  
**Lane**: evaluation  
**Direction Version**: 28  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Continue Recommended**: false  

---

## Executive Summary

The evaluation lane has **completed all machine-executable sub-questions** for the TF-IDF family at 174k scale per factory direction v28. The lane is correctly **BLOCKED_ON_DEPENDENCIES** awaiting dense embeddings, citation roles, and linear hybrids from legal-distance (only 3/26 years complete due to corpus artifact publication gap).

### Three Sub-Questions — All COMPLETE for TF-IDF Family

| Sub-Question | Status | Key Result |
|--------------|--------|------------|
| **12-benchmark formal suite** (frozen harness v3) | ✅ COMPLETE | 8 TF-IDF representations evaluated; HNSW artifact fixed via exact k-NN on stratified subsample (n=2000) |
| **Citation heritage benchmark** (174k citation-ID resolution) | ✅ COMPLETE | 137,314 frozen pairs ready; 95.9% resolution (2,019/2,105); infrastructure ready for dense embeddings |
| **v17b label normalization generalization** (174k fine-grained legal_area) | ✅ COMPLETE | 213→163 labels (23.5% reduction); PARTIAL generalization (2/8 reps within ≤10% worsening rule) |

### TF-IDF Family Results Summary (174k Scale)

| Representation | Adversarial Verdict | Lang Dom | Jurist Pref | Both Gates Pass |
|----------------|---------------------|----------|-------------|-----------------|
| cited_decisions_tfidf | **PASS** | 0.5295 | 0.8020 | ✅ |
| outcome_tfidf | **PASS** | 0.4527 | 0.7255 | ✅ |
| regeste_tfidf | **PASS** | 0.4835 | 0.6090 | ✅ |
| cited_outcome_hybrid_0.5 | **PASS** | 0.5164 | 0.8055 | ✅ |
| cited_outcome_hybrid_0.7 | **PASS** | 0.5238 | 0.7975 | ✅ |
| full_text_tfidf_light | **FAIL** | 1.0000 | 0.0000 | ❌ |
| regeste_full_text_hybrid_0.5 | **FAIL** | 1.0000 | 0.0000 | ❌ |
| regeste_full_text_hybrid_0.7 | **FAIL** | 1.0000 | 0.0000 | ❌ |

**Best representation**: `cited_decisions_tfidf`  
**Production default**: `cited_outcome_hybrid_0.7`

### Fundamental Two-Mode Tradeoff Persists at 174k

| Mode Type | Examples | Adversarial | Citation Heritage | Branch/TF Metadata | Hierarchy |
|-----------|----------|-------------|-------------------|---------------------|-----------|
| **Citation-based** | cited_decisions_tfidf, outcome_tfidf, cited_outcome_hybrids | ✅ PASS | ✅ PASS (AUC ~0.75-0.89) | ❌ FAIL | ❌ FAIL |
| **Text-based** | full_text_tfidf, regeste_tfidf, regeste_full_text_hybrids | ❌ FAIL (lang_dom=1.0) | ✅ PASS (AUC ~0.85-0.90) | ✅ PASS | ❌ FAIL |

**Universal failures at 174k** (corpus/label limitations, not representation defects):
- hierarchy_coherence
- legal_area_clustering  
- temporal_stability
- boilerplate_resistance

---

## Partial Dense Evaluation (Years 2000-2002, 12,570 decisions)

All 3 center_projected versions **FAIL adversarial gates**:
- `center_projected_768dim_partial`: lang_dom=0.9806, jurist_pref=0.0400
- `center_projected_64dim_partial`: lang_dom=0.9782, jurist_pref=0.0448  
- `center_projected_128dim_partial`: lang_dom=0.9804, jurist_pref=0.0409

**Root cause**: Only 18.3% metadata coverage (branch labels) for valid subset; center-projection computed on partial corpus not full 174k; raw multilingual-e5 embeddings have strong language clustering.

**Not comparable** to 1200-slice center_projected (which PASS adversarial). Full 174k dense embeddings required.

---

## Infrastructure Readiness — VERIFIED

| Component | Status | Details |
|-----------|--------|---------|
| **Metadata 174k symlink** | ✅ FIXED | `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.jsonl` → workspace metadata |
| **Corpus canonical path** | ⚠️ PARTIAL | `/tmp/lex_accepted/corpus/corpus/normalization/canonical/` exists; bger_*.jsonl for 2000-2002 present; **2003-2026 need generation via `regenerate_yearly_canonical.py`** |
| **Evaluation harness** | ✅ VERIFIED | Frozen v3 thresholds; exact k-NN on stratified subsample (n=2000); HNSW for full-corpus scale benchmarks |
| **Test suite** | ✅ PASSING | frozen_harness_reproducibility, v17_label_normalization, v17b_label_normalization_all_reps, v16_full_benchmark_suite, boilerplate_resistance_real, cross_lingual_alignment_v10, audit_correction_verification |
| **Formal suite scripts** | ✅ READY | `run_174k_formal_suite.py`, `scalable_nn.py`, all benchmark modules operational |

---

## Blocked On: Legal-Distance Dense Embeddings

| Dependency | Status | Blocker |
|------------|--------|---------|
| **174k dense embeddings** (center_projected 768/64/128dim) | ❌ 3/26 years | Year-split bger_YYYY.jsonl files missing for 2003-2026 |
| **Citation role embeddings** (citing/following/criticizing α=0.3) | ❌ Not started | Awaits dense embeddings |
| **Linear hybrids** (linear_citation_concat, linear_hybrid05_concat) | ❌ Not started | Awaits dense embeddings |
| **Metric learning** (linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1) | ❌ Not started | Awaits dense embeddings |

**Resolution path**: Run `regenerate_yearly_canonical.py` to download parquet from HuggingFace and generate missing year-split bger_YYYY.jsonl files for 2003-2026. Then legal-distance can complete year-split dense embedding computation.

---

## External Dependencies

| Dependency | Status |
|------------|--------|
| **Jurist human study** | BLOCKED — 5-10 Swiss jurists recruitment needed by repository owner; evaluation framework ready |

---

## Recommendation

**No additional same-question cycle justified for TF-IDF family.** All three machine-executable sub-questions complete with REPRODUCED evidence tier.

**Next cycle**: Resume evaluation when legal-distance delivers:
1. Full 174k dense embeddings (center_projected 768/64/128dim)
2. Citation role embeddings (citing/following/criticizing)
3. Linear hybrid combinations (linear_citation_concat, linear_hybrid05_concat)

At that point, run full 12-benchmark formal suite on all production representations with frozen harness v3 thresholds unchanged.

---

## Evidence References

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json`
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `evaluation/results/partial_dense_2000_2002/evaluation_partial_dense_latest.json`
- `evaluation/reports/evaluation_v28_174k_tfidf_formal_suite_20260926.md`

---

*Generated by Evaluation Lane per Research Protocol §12: "Write machine-readable lane state plus human-readable report."*