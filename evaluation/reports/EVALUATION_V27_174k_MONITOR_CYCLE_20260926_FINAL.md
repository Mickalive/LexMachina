# Evaluation Lane — 174k Monitor Cycle Report (Factory Direction v27)

**Date:** 2026-09-26  
**Lane:** evaluation  
**Direction Version:** 27  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  

---

## Executive Summary

The evaluation lane monitor completed check #122. **No new awaited representations detected.** The TF-IDF family (8 representations) remains fully evaluated at 174k scale across all three machine-executable sub-questions of factory direction v27. Dense embeddings from legal-distance lane remain at 3/26 years complete (2000-2002 only); no final concatenated 174k embeddings have landed in accepted state.

### Sub-question Status (All COMPLETE for TF-IDF Family)

| Sub-question | Status | Key Result |
|---|---|---|
| **1. 12-Benchmark Formal Suite** | ✅ COMPLETE (8 reps) | No TF-IDF representation passes all 12. Fundamental two-mode tradeoff: citation-based pass adversarial_falsification/citation_heritage but fail branch_knn/hierarchy; text-based pass branch_knn/tf_metadata but fail adversarial_falsification/cross-lang. ALL fail hierarchy_coherence (max purity 0.465 < 0.7) and legal_area_clustering (max ~0.08 < 0.5). |
| **2. Citation Heritage** | ✅ COMPLETE (8 reps) | cited_decisions_tfidf AUC=0.973, nn_citation_rate@10=0.487. Citation-based signals dominate. Text-based pass AUC threshold but near-zero nn_citation_rate. |
| **3. v17b Label Normalization** | ✅ COMPLETE (8 reps) | **NOT uniformly confirmed** — only 2/8 reps (cited_decisions_tfidf, regeste_tfidf) satisfy frozen >10% no-worsening rule on ALL hierarchy-family metrics. v17b improves purity for citation-based (42-67%) but degrades NMI for 6/8 reps (11-30% worsening). Text-based show ZERO purity improvement and severe NMI degradation (-24% to -30%). |

---

## Monitor Check #122 Details

**Timestamp:** 2026-09-26T10:08:54.317Z  
**Watch Path:** `/tmp/lex_accepted/legal-distance/legal_distance/results`

### Representations Found (No Change Since Last Cycle)

| Category | Representations | Status |
|---|---|---|
| **TF-IDF Complete** (8) | cited_decisions_tfidf, outcome_tfidf, cited_decisions_tfidf_outcome_hybrid_0.5, cited_decisions_tfidf_outcome_hybrid_0.7, regeste_tfidf, full_text_tfidf_light, regeste_full_text_hybrid_0.5, regeste_full_text_hybrid_0.7 | ✅ All evaluated at 174k |
| **Dense Embeddings Awaited** (6) | center_projected_768dim, center_projected_64dim, center_projected_128dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | ❌ NOT in accepted state |
| **Citation Roles Awaited** (3) | citation_role_citing_alpha0.3, citation_role_following_alpha0.3, citation_role_criticizing_alpha0.3 | ❌ NOT in accepted state |
| **Linear Hybrids Awaited** (2) | linear_citation_concat, linear_hybrid05_concat | ❌ NOT in accepted state |

### Legal-Distance Dense Embeddings Progress

| Metric | Value |
|---|---|
| Completed Years | 2000, 2001, 2002 (3/26 = 11.5%) |
| Decisions Completed | 19,441 / 173,963 (11%) |
| Blocker | Corpus artifact publication gap — year-split normalized files and metadata_174k.jsonl exist in corpus workspace but NOT at `/tmp/lex_accepted/corpus/...` and `/tmp/lex_accepted/evaluation/...` mount paths where legal-distance expects them |
| Legal-Distance Status | Years 2000-2002 complete; Years 2003-2025 blocked missing upstream data |

---

## HNSW Artifact — Fix Confirmed and Operational

**Problem:** HNSW with fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) produced nearly identical k-NN graphs across different TF-IDF representations at 174k scale, masking true representation differences in adversarial benchmarks.

**Fix Implemented:** Exact k-NN (sklearn brute force) on fixed stratified subsample (n=2000, seed=42) from 90,632 valid decisions with known branch for adversarial benchmarks; HNSW reserved for full-corpus scale benchmarks (citation_heritage on 137k frozen pairs, temporal_stability on 30k subsample, hierarchy family on 15k stratified subsample, boilerplate on full corpus).

**Evidence of Fix:**
- v3 harness (HNSW on full 174k): all 8 reps showed identical jurist_pairwise=0.122, lang_dom ~0.606
- Exact k-NN on fixed stratified subsample: jurist_pairwise=0.71-0.80, lang_dom=0.43-0.53, differentiated across representations

**Impact:** Jurist pairwise collapse from 1200-scale (0.79) → 174k (0.12) was HNSW artifact, NOT representation failure. FIXED before dense 174k evaluation.

---

## Infrastructure Status

| Component | Status | Notes |
|---|---|---|
| HNSW Backend | OPERATIONAL_ON_GITHUB_RUNNERS | hnswlib M=16, ef_construction=200, ef_search=100 |
| Scalable NN | OPERATIONAL_WITH_SKLEARN_FALLBACK | Exact k-NN for adversarial, HNSW for full-corpus |
| v25 Formal Suite | OPERATIONAL | 12-benchmark + citation_heritage + v17b, config hash 4323f833fa72366a |
| Citation Heritage | FROZEN_137314_PAIRS_READY | Built from published 2,019/2,105 citation-ID resolution |
| v17b Normalization | OPERATIONAL | Conservative cross-lingual canonical map (164 concepts) |
| Monitor Script | ACTIVE_WITH_FORMAL_SUITE | Checks legal-distance accepted state every cycle |

---

## Frozen Configuration Hashes

| Config | Hash | Description |
|---|---|---|
| v25 Formal Suite | 4323f833fa72366a | 12-benchmark thresholds, scale adaptations |
| v3 Adversarial Harness | 4047da047fb339c1 | HNSW scale path, adversarial thresholds |
| v3_174k Fixed | b51701f5a9c11692 | Exact k-NN on stratified subsample for adversarial |

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

## External Dependencies

### Jurist Human Study — BLOCKED (Non-blocking for Machine Suite)
- **Requirement:** 5-10 Swiss jurists recruited by repository owner
- **Framework:** Ready (pairwise preference protocol, cross-language retrieval tasks, cluster coherence rating)
- **Status:** Reported as blocked when reachable; does not block machine-executable suite

---

## Recommendations

### Continue Monitoring (Monitor Active)
The evaluation lane monitor should remain active, watching the legal-distance accepted state for:
1. **Dense embeddings** — full 174k concatenated embeddings when years 2003-2025 complete
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

## Next Steps

1. **Monitor legal-distance accepted state** for dense embeddings completion (check_count: 122, last check: 2026-09-26T10:08:54.317Z)
2. **Auto-evaluate dense representations** when they land in accepted state (monitor script active)
3. **Report jurist human study status** when reachable (framework ready, external dependency)
4. **Update factory direction** when dense embeddings evaluation completes to inform next lane questions

---

*Report generated by evaluation lane autonomous monitoring cycle. All claim-bearing measurements frozen before observation. Negative results preserved as first-class evidence.*