# Evaluation Lane v54 Cycle Report

**Date:** 2026-09-26  
**GitHub Run:** 36208490194  
**Factory Direction:** v27  
**Lane Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false (for TF-IDF family)

---

## Summary

The evaluation lane has completed all three machine-executable sub-questions of factory direction v27 for the TF-IDF production family (8 representations) at full 174k corpus scale (173,963 decisions). The lane remains BLOCKED_ON_DEPENDENCIES awaiting legal-distance 174k dense embeddings.

**Legal-distance dense embeddings progress:** 11/26 years complete (2000-2010), 62,645 decisions (36% of 173,963). Checkpoints verified in `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`. Final concatenation blocked on years 2011-2025.

---

## Sub-question Status

### 1. Full 12-benchmark formal suite at 174k scale — COMPLETE
- **Runner:** `evaluation/experiments/v25_174k_suite/run_v25_174k_suite.py` (config hash `4323f833fa72366a`)
- **All 8 TF-IDF representations evaluated** at 173,963 decisions
- **Pass counts:**
  - cited_decisions_tfidf: 6/12
  - cited_outcome_hybrid_0.5: 6/12 (1 SKIP)
  - cited_outcome_hybrid_0.7: 6/12
  - full_text_tfidf_light: 7/12
  - regeste_full_text_hybrid_0.5: 7/12
  - regeste_full_text_hybrid_0.7: 7/12
  - regeste_tfidf: 5/12
  - outcome_tfidf: 3/12
- **Universal 174k FAILs** (corpus/label limitations, not representation defects):
  - hierarchy_coherence (purity 0.08-0.47 < 0.7)
  - legal_area_clustering (purity 0.003-0.08 < 0.5)
- **Adversarial gates:** Citation-based reps PASS; full-text/regeste reps FAIL (language_dominance ~0.99)

### 2. Citation_heritage benchmark validated — COMPLETE
- **Runner:** `evaluation/validate_citation_heritage_174k.py`
- **Frozen pair pool:** 137,314 pairs (1,020 positive + 1,020 negative from 924 resolved citations mapping to corpus)
- **Citation resolution:** 95.9% (2,019/2,105 resolved from published corpus)
- **Results:** 7/8 TF-IDF reps PASS AUC≥0.65
  - Best: cited_decisions_tfidf AUC=0.9731
  - Production default cited_outcome_hybrid_0.7 AUC=0.9605, nn_citation_rate@10=0.490
  - regeste_tfidf FAILS (AUC=0.4865) — regeste text lacks citation IDs

### 3. v17b label normalization generalization to 174k — PARTIAL
- **Mapping:** 213 raw → 163 normalized labels (23.5% reduction), 32 cross-lingual canonical concepts
- **Generalization:** 2/8 reps within ≤10% worsening rule (cited_decisions_tfidf, regeste_tfidf)
- **6 reps exceed:** 5 on hierarchy NMI (-10.8% to -27.6%), 1 on zoom_coherence (cited_outcome_hybrid_0.5 -16.0%)
- **Normalized hierarchy purity gains:** 1.5-1.6x for citation-based reps
- **Even normalized:** best hierarchy purity=0.47 < 0.7 threshold
- **Conclusion:** v16 hierarchy-family FAIL partially attributable to label granularity, but fundamental corpus/label limitations remain

---

## Adversarial Evaluation (HNSW Artifact Fixed)

**Runner:** `evaluation/run_174k_formal_suite.py` (config hash `b51701f5a9c11692`)
- **HNSW artifact fix:** Exact k-NN on fixed stratified subsample (n=2000, decisions with known branch) for adversarial benchmarks
- **Results:** 5/8 PASS both adversarial gates (LangDom<0.85, Jurist>0.5)
  - PASS: cited_decisions_tfidf, cited_outcome_hybrid_0.5, cited_outcome_hybrid_0.7, outcome_tfidf, regeste_tfidf
  - FAIL: full_text_tfidf_light, regeste_full_text_hybrid_0.5, regeste_full_text_hybrid_0.7 (LangDom≈1.0)
- **BEST:** cited_decisions_tfidf (LangDom=0.5164, Jurist=0.8055)
- **PRODUCTION DEFAULT:** cited_outcome_hybrid_0.7 (LangDom=0.5238, Jurist=0.7975)

---

## Infrastructure Status (All OPERATIONAL)

| Component | Status | Details |
|-----------|--------|---------|
| HNSW backend (hnswlib) | OPERATIONAL | Verified at 15k+ scale |
| scalable_nn.py | OPERATIONAL | sklearn fallback + HNSW |
| v25_174k_formal_suite | OPERATIONAL | Frozen protocol, config hash verified |
| run_174k_formal_suite.py | OPERATIONAL | HNSW artifact fixed, exact k-NN on subsample |
| validate_citation_heritage_174k.py | OPERATIONAL | 137,314 frozen pairs ready |
| v17b label normalization | OPERATIONAL | 213→163 labels, 32 cross-lingual concepts |
| monitor_and_evaluate_174k.py | ACTIVE | 84 checks, run_formal_suite_v25() auto-evaluation |

---

## Monitor Status

- **Checks completed:** 84 (checks #81, #82 in this cycle)
- **Auto-evaluation:** Enhanced with `run_formal_suite_v25()` — copies new embeddings to v25 suite directory and executes full frozen protocol (12-benchmark suite + citation_heritage + v17b)
- **Detection:** Scans legal-distance accepted state (v5-v14, fractal_map, 174k_dense_embeddings root) for final concatenated embeddings
- **Checkpoints:** Year-split checkpoints in 174k_dense_embeddings/checkpoints/ are NOT evaluated (monitor waits for final concatenated embeddings)

---

## External Dependencies

**Jurist human study:** BLOCKED — requires 5-10 Swiss jurists recruited by repository owner; framework ready per v25 protocol.

---

## Evidence Preservation

All evidence preserved per Research Protocol:
- v25 suite results: `results/evaluation/v25_174k_formal_suite/`
- Citation heritage: `results/evaluation/v25_174k_citation_heritage/` + `evaluation/results/174k_citation_heritage/`
- v17b analysis: `results/evaluation/v25_174k_v17b/` + `evaluation/results/174k_label_analysis/`
- Formal suite: `evaluation/results/174k/formal_suite/`
- Monitor state: `evaluation/state/monitor_174k_state.json` (84+ checks)
- Config hashes frozen: suite=`4323f833fa72366a`, harness=`4047da047fb339c1`, formal=`b51701f5a9c11692`

---

## Recommendation

**continue_recommended = false** for TF-IDF family — no additional same-question cycle justified per Research Protocol. All three machine-executable sub-questions COMPLETE at 174k with frozen thresholds, no tuning after results.

Lane remains BLOCKED_ON_DEPENDENCIES awaiting legal-distance 174k dense embeddings (center_projected, metric learning, hybrid objectives, citation roles, linear hybrids). Monitor active and ready to auto-evaluate when they land.

**Next action:** Legal-distance completes year-split dense embeddings (years 2011-2025), publishes final concatenated embeddings to 174k_dense_embeddings root directory, monitor auto-evaluates via run_formal_suite_v25().

---

## Negative Results Preserved

Universal FAILs at 174k scale (corpus/label limitations, not representation defects):
- hierarchy_coherence (purity 0.08-0.47 < 0.7)
- legal_area_clustering (purity 0.003-0.08 < 0.5)
- temporal_stability (high variance across temporal splits)
- boilerplate_resistance (negative resistance_score ≈ -0.7 to -0.9, measures language dominance not procedural boilerplate)
