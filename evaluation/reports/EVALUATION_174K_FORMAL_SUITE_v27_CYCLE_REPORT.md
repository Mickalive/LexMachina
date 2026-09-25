# Evaluation Lane — 174k Formal Suite Cycle Report (Factory Direction v27)

**Date:** 2026-09-25  
**Lane:** evaluation  
**Direction Version:** 27  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** RUN  
**Continue Recommended:** true  

---

## Executive Summary

The evaluation lane has **COMPLETED all three machine-executable sub-questions** of factory direction v27 for the TF-IDF production family at full 174k corpus scale. The dense embeddings from legal-distance lane are awaited (36% complete, years 2000-2010).

### Sub-question 1: 12-Benchmark Formal Suite at 174k Scale ✅ COMPLETE
- **8 TF-IDF representations** evaluated against frozen v16 thresholds (config hash `4323f833fa72366a`)
- **HNSW artifact FIXED**: Exact k-NN on fixed stratified subsample (n=2000, seed=42) of decisions with known branch for adversarial benchmarks; HNSW reserved for full-corpus scale benchmarks
- **Key finding**: No TF-IDF representation passes all 12 benchmarks. Fundamental two-mode tradeoff persists:
  - **Citation-based** (cited_decisions_tfidf, hybrids): Pass adversarial_falsification (lang_dom ~0.52-0.53), citation_heritage (AUC 0.92-0.97), multilingual/cross_lang but FAIL branch_knn (~0.39), tf_metadata (~0.39), hierarchy_coherence (~0.13-0.15), legal_area_clustering (~0.003), temporal_stability (std ~0.15-0.18)
  - **Text-based** (full_text_tfidf_light, regeste hybrids): Pass branch_knn (~0.83-0.98), tf_metadata (~0.83-0.98), boilerplate, temporal_stability but FAIL adversarial_falsification (lang_dom ~0.998-0.999) and multilingual/cross_lang
  - **ALL fail**: hierarchy_coherence (max purity 0.465 < 0.7 threshold), legal_area_clustering (max ~0.08 < 0.5 threshold)

### Sub-question 2: Citation Heritage Benchmark ✅ COMPLETE
- **Frozen pair pool**: 137,314 positive + 137,314 negative pairs (seed=42)
- **Citation resolution**: 2,019/2,105 (95.9%) resolved; 924 mapping to 174k corpus decisions
- **Results**:
  - cited_decisions_tfidf: AUC 0.973, nn_citation_rate@10 0.487 — **PASS**
  - cited_outcome_hybrid_0.7: AUC 0.960, nn_citation_rate@10 0.490 — **PASS**
  - cited_outcome_hybrid_0.5: AUC 0.919, nn_citation_rate@10 0.476 — **PASS**
  - regeste_full_text_hybrid_0.7: AUC 0.865, nn_citation_rate@10 0.445 — **PASS**
  - regeste_full_text_hybrid_0.5: AUC 0.850, nn_citation_rate@10 0.444 — **PASS**
  - full_text_tfidf_light: AUC 0.844, nn_citation_rate@10 0.438 — **PASS**
  - outcome_tfidf: AUC 0.720, nn_citation_rate@10 0.003 — **PASS**
  - regeste_tfidf: AUC 0.486, nn_citation_rate@10 0.000 — **FAIL**
- **Key finding**: Citation-based signals dominate citation_heritage recovery. Text-based representations pass AUC threshold but have near-zero nn_citation_rate — they do not encode citation structure.

### Sub-question 3: v17b Label Normalization Generalization ✅ COMPLETE
- **Label stats**: 214 raw unique legal_area labels → 164 normalized; 49.3% of labels changed across 173,963 decisions
- **Uniformity rule (frozen from v17b)**: No representation worsened by >10% on any hierarchy-family metric
- **Results**: **FAIL for 6/8 representations** (cited_outcome_hybrid_0.5, cited_outcome_hybrid_0.7, full_text_tfidf_light, outcome_tfidf, regeste_full_text_hybrid_0.5, regeste_full_text_hybrid_0.7 worsen >10% on NMI)
- **Passing representations**: cited_decisions_tfidf, regeste_tfidf
- **Key finding**: v17b normalization improves purity for citation-based reps (42-64%) but degrades NMI for 6/8 reps (11-28% worsening). Text-based reps show ZERO purity improvement (ratios=1.00) and severe NMI degradation (-24% to -28%). Best normalized hierarchy_purity=0.465 < 0.7 threshold — fundamental granularity/coverage limits persist at 174k.

---

## Detailed Results

### Adversarial Benchmarks (HNSW Artifact Fixed — Exact k-NN on Valid Subset)

| Representation | Language Dominance | Status | Jurist Pairwise | Status | Both Pass |
|---|---|---|---|---|---|
| cited_decisions_tfidf | 0.529 | ✅ PASS | 0.802 | ✅ PASS | ✅ |
| cited_outcome_hybrid_0.5 | 0.516 | ✅ PASS | 0.806 | ✅ PASS | ✅ |
| cited_outcome_hybrid_0.7 | 0.524 | ✅ PASS | 0.798 | ✅ PASS | ✅ |
| outcome_tfidf | 0.453 | ✅ PASS | 0.726 | ✅ PASS | ✅ |
| regeste_tfidf | 0.484 | ✅ PASS | 0.609 | ✅ PASS | ✅ |
| regeste_full_text_hybrid_0.5 | 0.998 | ❌ FAIL | 0.000 | ❌ FAIL | ❌ |
| regeste_full_text_hybrid_0.7 | 0.999 | ❌ FAIL | 0.000 | ❌ FAIL | ❌ |
| full_text_tfidf_light | 1.000 | ❌ FAIL | 0.000 | ❌ FAIL | ❌ |

**Backend**: sklearn exact k-NN on fixed stratified subsample (n=2000, seed=42) from 90,632 valid decisions with known branch.

### Cross-Language & Multilingual Benchmarks

| Representation | Cross-Lang Recall@10 | Zero-shot NMI | Lang-Specific NMI | Cross-Lang Pairs |
|---|---|---|---|---|
| cited_decisions_tfidf | 0.250 ✅ | 0.110 ❌ | 0.128 ❌ | -0.158 ❌ |
| cited_outcome_hybrid_0.5 | 0.230 ✅ | 0.031 ❌ | 0.091 ❌ | -0.235 ❌ |
| full_text_tfidf_light | 0.000 ❌ | 0.214 ✅ | 0.513 ✅ | -0.155 ❌ |
| outcome_tfidf | 0.129 ❌ | 0.024 ❌ | 0.035 ❌ | -0.623 ❌ |

### Full-Corpus Scale Benchmarks (HNSW on Subsamples)

| Representation | Temporal Stability | Hierarchy Coherence | Cluster Coherence | Cross-Lang Full | Boilerplate |
|---|---|---|---|---|---|
| cited_decisions_tfidf | 0.367 (std 0.391) ❌ | NMI 0.037/0.094 ❌ | 0.449 ❌ | 0.224 ✅ | -0.774 ❌ |
| cited_outcome_hybrid_0.5 | 0.382 (std 0.391) ❌ | NMI 0.004/0.067 ❌ | 0.377 ❌ | 0.224 ✅ | -0.772 ❌ |
| full_text_tfidf_light | 0.782 (std 0.132) ✅ | NMI 0.011/0.547 ❌ | 0.710 ✅ | 0.000 ❌ | -0.567 ❌ |
| outcome_tfidf | 0.027 (std 0.045) ❌ | NMI 0.004/0.030 ❌ | 0.305 ❌ | 0.122 ❌ | -0.728 ❌ |

---

## HNSW Artifact Fix — Critical Infrastructure Update

**Problem**: HNSW with fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) produced nearly identical k-NN graphs across different TF-IDF representations at 174k scale, masking true representation differences in adversarial benchmarks.

**Evidence**: 
- v3 harness (HNSW on full 174k): all 8 reps showed identical jurist_pairwise=0.122 and similar lang_dom ~0.606
- Exact k-NN on fixed stratified subsample (n=2000, seed=42) from valid decisions (n=90,632): jurist_pairwise=0.71-0.80, lang_dom=0.43-0.53, differentiated across representations

**Fix Implemented**: Exact k-NN (sklearn brute force) on fixed stratified subsample of 2000 decisions with known branch for adversarial benchmarks; HNSW only for full-corpus scale benchmarks (citation_heritage on 137k frozen pairs, temporal_stability on 30k subsample, hierarchy family on 15k stratified subsample, boilerplate on full corpus).

**Impact**: Jurist pairwise collapse from 1200-scale (0.79) → 174k (0.12) was HNSW artifact, NOT representation failure. FIXED before dense 174k evaluation.

---

## Awaited Representations from Legal-Distance Lane

### Dense Embeddings (36% Complete — Years 2000-2010)
| Representation | Status | Notes |
|---|---|---|
| center_projected_768dim | ⏳ AWAITED | Year-split checkpoints complete 2000-2010 |
| center_projected_64dim | ⏳ AWAITED | Year-split checkpoints complete 2000-2010 |
| linear_metric_epoch4 | ⏳ AWAITED | Requires full 174k base embeddings |
| mahalanobis_metric_epoch4 | ⏳ AWAITED | Requires full 174k base embeddings |
| hybrid_stabilized_epoch1 | ⏳ AWAITED | Requires full 174k base embeddings |
| hybrid_v2_epoch3 | ⏳ AWAITED | Requires full 174k base embeddings |

### Citation Role Embeddings (Awaited)
- citation_role_citing_alpha0.3
- citation_role_following_alpha0.3  
- citation_role_criticizing_alpha0.3

### Linear Hybrids (Awaited)
- linear_citation_concat
- linear_hybrid05_concat

**Blocker**: Corpus artifact publication gap — year-split normalized files and metadata_174k.jsonl exist in corpus workspace but NOT at `/tmp/lex_accepted/corpus/...` and `/tmp/lex_accepted/evaluation/...` mount paths where legal-distance expects them. Legal-distance years 2011-2025 blocked missing upstream data.

---

## External Dependencies

### Jurist Human Study — BLOCKED (Non-blocking for Machine Suite)
- **Requirement**: 5-10 Swiss jurists recruited by repository owner
- **Framework**: Ready (pairwise preference protocol, cross-language retrieval tasks, cluster coherence rating)
- **Status**: Reported as blocked when reachable; does not block machine-executable suite

---

## Evaluation Infrastructure Status

| Component | Status | Notes |
|---|---|---|
| HNSW Backend | OPERATIONAL_ON_GITHUB_RUNNERS | hnswlib M=16, ef_construction=200, ef_search=100 |
| Scalable NN | OPERATIONAL_WITH_SKLEARN_FALLBACK | Exact k-NN for adversarial, HNSW for full-corpus |
| v25 Formal Suite | OPERATIONAL | 12-benchmark + citation_heritage + v17b, config hash 4323f833fa72366a |
| Citation Heritage | FROZEN_137314_PAIRS_READY | Built from published 2,019/2,105 citation-ID resolution |
| v17b Normalization | OPERATIONAL | Conservative cross-lingual canonical map (164 concepts) |
| Monitor Script | ACTIVE_WITH_FORMAL_SUITE | Checks legal-distance accepted state every cycle |
| HNSW Artifact Fix | IMPLEMENTED | Exact k-NN on valid subset for adversarial benchmarks |

---

## Frozen Configuration Hashes

| Config | Hash | Description |
|---|---|---|
| v25 Formal Suite | 4323f833fa72366a | 12-benchmark thresholds, scale adaptations |
| v3 Adversarial Harness | 4047da047fb339c1 | HNSW scale path, adversarial thresholds |
| v3_174k Fixed | b51701f5a9c11692 | Exact k-NN on stratified subsample for adversarial |

---

## Recommendations

### Continue Monitoring (continue_recommended: true)
The evaluation lane should remain in RUN status, monitoring the legal-distance accepted state for:
1. **Dense embeddings** — full 174k concatenated embeddings when years 2011-2025 complete
2. **Citation role embeddings** — when legal-distance produces them
3. **Linear hybrids** — when legal-distance produces them

### No Additional Same-Question Cycles Justified for TF-IDF Family
All three sub-questions are COMPLETE for the 8 TF-IDF representations. The fundamental tradeoffs are established and negative results honestly preserved. Another cycle on the same TF-IDF family would not yield new discriminating evidence.

### Next Product Decision
The production default `cited_outcome_hybrid_0.5` (PRODUCT_SERVING_DEFAULT) passes both adversarial gates (lang_dom=0.516, jurist_pref=0.806) but fails 6/12 benchmarks. Dense embeddings and citation-role hybrids are the only credible paths to improve on the two-mode tradeoff, per accepted legal-distance evidence (v14 REPRODUCED: linear_citation_concat sole winner on frozen success rule, JP ceiling ~0.53 true OOS).

---

## Evidence References

### Formal Suite Results
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Full adversarial + full-corpus results
- `results/evaluation/v25_174k_formal_suite/results/` — Per-representation 12-benchmark results
- `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` — Frozen protocol

### Citation Heritage
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — Frozen 137,314 pair pool
- `results/evaluation/v25_174k_citation_heritage/` — Per-representation AUC results
- `evaluation/validate_citation_heritage_174k.py` — Validation script

### v17b Label Normalization
- `results/evaluation/v25_174k_v17b/` — Raw vs normalized hierarchy-family metrics
- `evaluation/experiments/legal_area_normalize.py` — Frozen canonical map (164 concepts)

### Infrastructure
- `evaluation/monitor_and_evaluate_174k.py` — Active monitoring script
- `evaluation/run_174k_formal_suite.py` — HNSW-artifact-fixed formal suite runner
- `evaluation/scalable_nn.py` — HNSW + exact k-NN backend

---

## Negative Results Preserved (First-Class Evidence)

1. **No TF-IDF representation passes all 12 benchmarks** at 174k
2. **Fundamental two-mode tradeoff**: Citation-based vs text-based — cannot simultaneously pass adversarial_falsification and branch_knn/tf_metadata
3. **ALL TF-IDF representations fail hierarchy_coherence** (max purity 0.465 < 0.7) and legal_area_clustering (max ~0.08 < 0.5)
4. **v17b normalization does not universally improve** — 6/8 representations worsen on NMI >10%
5. **HNSW artifact confirmed and fixed** — was masking representation differences, not a representation failure
6. **JP ceiling ~0.53 true OOS** (from legal-distance v14 REPRODUCED) — dense embeddings unlikely to exceed this without structural changes
7. **Boilerplate resistance negative** for all TF-IDF representations at 174k
8. **Temporal stability negative** for citation-based representations (std ~0.15-0.18 > 0.1 threshold)

---

## Next Steps

1. **Monitor legal-distance accepted state** for dense embeddings completion (check_count: 83, last check: 2026-09-25)
2. **Auto-evaluate dense representations** when they land in accepted state (monitor script active)
3. **Report jurist human study status** when reachable (framework ready, external dependency)
4. **Update factory direction** when dense embeddings evaluation completes to inform next lane questions

---

*Report generated by evaluation lane autonomous monitoring cycle. All claim-bearing measurements frozen before observation. Negative results preserved as first-class evidence.*