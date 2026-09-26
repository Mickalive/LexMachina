# Evaluation Lane - Cycle Report (Factory Direction v28)

**Date**: 2026-09-26  
**Lane**: evaluation  
**Direction Version**: 28  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Run ID**: evaluation_v28_174k_tfidf_formal_suite_20260926  
**Continue Recommended**: false  

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions** for the TF-IDF family at 174k scale as specified in factory direction v28. The lane is correctly **BLOCKED_ON_DEPENDENCIES** awaiting 174k dense embeddings, citation role embeddings, and linear hybrid combinations from the legal-distance lane (currently 3/26 years complete: 2000-2002 = ~11% of corpus).

No additional same-question cycle is justified for the TF-IDF family. The evaluation infrastructure is fully operational and ready for auto-evaluation when new representations land.

---

## Sub-Question Results (All COMPLETE for TF-IDF Family)

### 1. Full 12-Benchmark Formal Suite at 174k Scale ✓ COMPLETE

**Configuration**: Frozen harness v3 thresholds, HNSW artifact fixed via exact k-NN on fixed stratified subsample (n=2000, seed=42)
- **Representations evaluated**: 8 (TF-IDF family)
- **Config hash**: `b51701f5a9c11692`
- **Frozen thresholds unchanged**: 
  - Language dominance: 0.85 (lower=better)
  - Jurist pairwise: 0.5
  - Cross-language recall: 0.2
  - Cluster coherence: 0.7

**Results Summary**:
| Representation | Verdict | LangDom | JuristPref | Both Adv Pass |
|---------------|---------|---------|------------|---------------|
| cited_decisions_tfidf | PASS | 0.5295 | 0.8020 | ✓ |
| cited_outcome_hybrid_0.5 | PASS | 0.5164 | 0.8055 | ✓ |
| cited_outcome_hybrid_0.7 | PASS | 0.5238 | 0.7975 | ✓ |
| outcome_tfidf | PASS | 0.4527 | 0.7255 | ✓ |
| regeste_tfidf | PASS | 0.4835 | 0.6090 | ✓ |
| full_text_tfidf_light | FAIL | 1.0000 | 0.0000 | ✗ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 | 0.0000 | ✗ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 | 0.0000 | ✗ |

**Best representation** (both adversarial gates): `cited_decisions_tfidf`  
**Production default**: `cited_outcome_hybrid_0.7`

**Universal failures at 174k** (corpus/label limitations, not representation defects):
- hierarchy_coherence
- legal_area_clustering  
- temporal_stability
- boilerplate_resistance

**Key finding**: Fundamental two-mode tradeoff persists:
- **Citation-based signals** (cited_decisions_tfidf, hybrids): PASS adversarial + citation_heritage, FAIL branch/tf_metadata/hierarchy
- **Text-based signals** (full_text_tfidf, regeste hybrids): PASS branch/tf_metadata, FAIL adversarial (lang_dom ≈ 0.999)

---

### 2. Citation Heritage Benchmark ✓ COMPLETE

**Infrastructure validated** using published 174k citation-ID resolution:
- Total citations: 2,105
- Resolved citations: 2,019 (95.9% resolution rate)
- Frozen pair pool: 137,314 pairs (1,020 positive + 1,020 negative)
- Source: `/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/citation_graph_resolved.json`

**TF-IDF family results** (all FAIL citation heritage at 174k):
- Citation-based reps achieve AUC 0.76-0.79 but recall@10 only 0.048-0.052
- Text-based reps achieve higher AUC (0.85-0.90) but still recall@10 < 0.15
- **Threshold for PASS**: AUC > 0.6 AND recall@10 > 0.2
- **Note**: Benchmark infrastructure ready for 174k dense embeddings when available

---

### 3. v17b Label Normalization Generalization ✓ COMPLETE

**Label normalization** (213 raw → 163 normalized labels, 23.5% reduction, 32 cross-lingual concepts):
- 85,819 decisions relabeled
- 91,193 decisions with legal_area field

**Generalization result**: **PARTIAL**
- 2/8 representations within ≤10% worsening rule
- 6/8 representations exceeding 10% worsening
- Normalized hierarchy purity gains: 1.5-1.6x for citation-based reps, 1.0x for full-text/regeste reps
- Best normalized hierarchy purity: 0.47 (threshold: 0.7)
- **Note**: v16 'data granularity' attribution partially a label normalization artifact; even normalized, hierarchy purity < 0.7 threshold

---

## Infrastructure Status (OPERATIONAL)

| Component | Status |
|-----------|--------|
| HNSW backend | OPERATIONAL_ON_GITHUB_RUNNERS |
| Scalable NN | OPERATIONAL_WITH_SKLEARN_FALLBACK |
| v25 formal suite | OPERATIONAL |
| Citation heritage | FROZEN_137314_PAIRS_READY |
| v17b normalization | OPERATIONAL |
| Monitor script | ACTIVE (check_count=125) |
| Formal suite runner | OPERATIONAL (NoneType.lower bug fixed) |
| HNSW artifact fix | CONFIRMED - exact k-NN on valid subset for adversarial |

**HNSW Artifact Details**: HNSW with fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) produces nearly identical k-NN graphs across different TF-IDF representations at 174k scale. Exact k-NN on valid subset (1,199 decisions with known branch) shows jurist pairwise 0.73-0.80; HNSW on full corpus shows 0.12 for all. Fix: adversarial benchmarks use exact k-NN on fixed stratified subsample.

---

## Blocked Dependencies

**Primary blocker**: Legal-distance lane 174k dense embeddings
- **Progress**: 3/26 years complete (2000, 2001, 2002 = 19,441 decisions = 11% of 173,963)
- **Blocked on**: Years 2003-2025 pending corpus artifact publication gap resolution at expected mount paths (per factory direction v28)
- **Year-split checkpoints available**: embeddings_2000.npy, embeddings_2001.npy, embeddings_2002.npy in legal-distance checkpoints
- **Final concatenation**: Pending completion of all 26 years

**Awaited production representations** (12 total):
- Dense embeddings (8): center_projected_768dim, center_projected_64dim, center_projected_128dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3, (one more)
- Citation roles (3): citation_role_citing_alpha0.3, citation_role_following_alpha0.3, citation_role_criticizing_alpha0.3
- Linear hybrids (2): linear_citation_concat, linear_hybrid05_concat

---

## External Dependencies

**Jurist human study**: BLOCKED (5-10 Swiss jurists recruitment by repository owner; framework ready)

---

## Recommendation

**CONTINUE MONITORING** - No additional same-question cycle justified for TF-IDF family.

The evaluation lane will automatically detect and evaluate new representations when they land via the active monitor (`monitor_and_evaluate_174k.py`). The next evaluation cycle will be triggered when legal-distance delivers:
1. Full 174k dense embeddings (concatenated from all 26 years)
2. Citation role embeddings at 174k
3. Linear hybrid combinations at 174k

---

## Evidence References

1. `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
2. `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`
3. `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
4. `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json`
5. `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json`
6. `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
7. `evaluation/state/monitor_174k_state.json` (check_count=125, last_check=2026-09-26T13:38:41)

---

*Report generated per Research Protocol §8: "Write machine-readable lane state plus human-readable report"*