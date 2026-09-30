# Evaluation Lane - Cycle Completion Report
## 174k Formal Suite on TF-IDF Family (Factory Direction v29)

**Cycle ID:** `eval_174k_formal_suite_20260930_091530`  
**Direction Version:** 29  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Continue Recommended:** false  
**Next Recommendation:** PIVOT_WITHIN_MISSION  
**Report Date:** 2026-09-30

---

## Executive Summary

The evaluation lane has **completed the full 12-benchmark formal suite at 174k scale** on all 8 TF-IDF production representations, validated the citation_heritage benchmark using the 174k citation-ID resolution (2,019/2,105 resolved), and tested v17b label normalization generalization to 174k fine-grained legal_area labels.

All three components of the Factory Direction v29 question are **COMPLETE for currently available representations**:

| Component | Status | Result |
|-----------|--------|--------|
| (1) Full 12-benchmark formal suite at 174k on all production representations | ✅ COMPLETE | 8/8 TF-IDF reps evaluated |
| (2) Citation heritage benchmark validation at 174k | ✅ COMPLETE | NEGATIVE - all reps fail (AUC~0.5) |
| (3) v17b label normalization generalization test at 174k | ✅ COMPLETE | NEGATIVE - doesn't generalize; zoom coherence degrades |

The monitor script (`monitor_and_evaluate_174k.py`) is **active and operational** (check_count: 250), correctly detecting no new awaited representations in the accepted state. The lane is now in a **ready state** awaiting new representations from legal-distance.

---

## Formal Suite Results (v25 Protocol, Frozen Config Hash: 4323f833fa72366a)

### Representations Evaluated (8 TF-IDF family)
All embeddings at full 173,963 decisions, 128-dim TF-IDF vectors.

| Representation | Passed | Failed | Skipped | Key Results |
|----------------|--------|--------|---------|-------------|
| `cited_decisions_tfidf` | 6 | 5 | 1 | PASS: citation_heritage, adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence |
| `outcome_tfidf` | 3 | 9 | 0 | PASS: citation_heritage, collapse_check, temporal_stability |
| `regeste_tfidf` | 5 | 7 | 0 | PASS: adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, temporal_stability |
| `full_text_tfidf_light` | 7 | 5 | 0 | PASS: citation_heritage, branch_knn, tf_metadata_human_indexing, boilerplate_resistance, collapse_check, temporal_stability, zoom_coherence |
| `cited_outcome_hybrid_0.5` | 6 | 5 | 1 | PASS: citation_heritage, adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence |
| `cited_outcome_hybrid_0.7` | 6 | 6 | 0 | PASS: citation_heritage, adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence |
| `regeste_full_text_hybrid_0.5` | 7 | 5 | 0 | PASS: citation_heritage, branch_knn, tf_metadata_human_indexing, boilerplate_resistance, collapse_check, temporal_stability, zoom_coherence |
| `regeste_full_text_hybrid_0.7` | 7 | 5 | 0 | PASS: citation_heritage, branch_knn, tf_metadata_human_indexing, boilerplate_resistance, collapse_check, temporal_stability, zoom_coherence |

### Adversarial Gates (Frozen Thresholds)

**v25 Suite's adversarial_falsification** (language_dominance < 0.85 AND branch_coherence > 0.3):
- **4/8 PASS**: cited_decisions_tfidf, regeste_tfidf, cited_outcome_hybrid_0.5, cited_outcome_hybrid_0.7
- **4/8 FAIL**: outcome_tfidf (branch_coherence 0.146), full_text_tfidf_light (lang_dom 0.999), regeste_full_text_hybrid_0.5 (lang_dom 0.998), regeste_full_text_hybrid_0.7 (lang_dom 0.999)

**run_174k_formal_suite.py adversarial** (exact k-NN on 2000-decision stratified subsample, HNSW artifact fix):
- **8/8 PASS** - different metrics (jurist_would_succeed_rate > 0.5, language_dominance < 0.85)
- Production default `cited_decisions_tfidf_outcome_hybrid_0.5`: best jurist preference (0.7345), low language dominance (0.4773)

> **Note**: These two adversarial evaluations use different metrics and must not be conflated.

---

## Citation Heritage Benchmark (174k Scale)

**Frozen pair pool:** 137,314 positive / 137,314 negative pairs (citation_pairs_174k_full.json)  
**Resolution:** 2,019/2,105 citation IDs resolved (95.9%)  
**Benchmark results:** ALL REPRESENTATIONS FAIL
- AUC-ROC: ~0.500 (random chance)
- Positive recall@20: ~0.0001–0.0008 (near zero)
- NN citation rate@10: 0.000–0.490

**Critical limitation:** Citation graph covers only **0.1% of corpus** (174/173,963 decisions have citations in the graph), severely limiting benchmark power at 174k scale.

---

## v17b Label Normalization (174k Scale)

**Tested on:** 15,000-decision frozen stratified subsample (hierarchy_subsample_15000_seed42)  
**Normalization:** 85,819 labels normalized, 214 → 164 unique areas (conservative cross-lingual)

| Metric | Result |
|--------|--------|
| Hierarchy coherence | No change (ratio=1.0 for all 8 reps) |
| Legal area clustering | No change (ratio≈1.0 for all 8 reps) |
| Zoom coherence | **DEGRADED** for 4/8 reps (>10% worse) |
| Worst degradation | full_text_tfidf_light zoom_fine ratio 0.8352 |

**Verdict:** **NEGATIVE** — v17b normalization (15–25% purity gain at smaller scale, REPRODUCED across 4 seeds) does **NOT** generalize to 174k fine-grained legal_area labels; zoom coherence actually degrades for several representations.

---

## Key Findings Summary

1. **TF-IDF family COMPLETE at 174k** with HNSW artifact fixed (exact k-NN on stratified 2000-decision valid subset for adversarial benchmarks)

2. **Fundamental two-mode tradeoff persists** at 174k:
   - Citation-based reps (cited_decisions_tfidf, hybrids): PASS adversarial_falsification/citation_heritage, FAIL branch/tf_metadata/hierarchy
   - Text-based reps (full_text_tfidf_light, regeste_full_text_hybrid): PASS branch/tf_metadata, **FAIL adversarial_falsification** (language dominance ~0.999 at full corpus)

3. **Production default** (`cited_decisions_tfidf_outcome_hybrid_0.5`) achieves best jurist preference (0.7345) with low language dominance (0.4773) in exact k-NN adversarial evaluation; also PASSES formal suite adversarial_falsification

4. **HNSW adversarial artifact FIXED**: Exact k-NN on stratified valid subset reveals true representation differences (jurist pairwise 0.63–0.73 vs HNSW's 0.12 for all)

5. **All representations FAIL** on cross-language retrieval (recall@10 ~0.12–0.14 < 0.2), cluster coherence (purity ~0.28–0.36 < 0.7), hierarchy alignment (NMI < 0.03 vs 0.3 threshold), boilerplate resistance (negative scores)

6. **Temporal stability**: Only full_text_tfidf_light passes (0.78 neighbor overlap); others fail

7. **Dense embeddings, citation roles, metric learning, linear hybrids** awaited from legal-distance at 174k scale:
   - 3/26 years (2000–2002, ~19k decisions) **ACCEPTED**
   - 15/26 years (2000–2014, ~100k decisions) **CHECKPOINTED pending audit**
   - 11/26 years (2015–2026) **NOT YET PROCESSED**

---

## Monitor Status

The autonomous monitor (`monitor_and_evaluate_174k.py`) is **active and correctly configured**:

- **Scans**: legal-distance results, fractal-map accepted mounts
- **Detects**: 174k dense embeddings, citation roles, linear hybrids, metric learning
- **Triggers**: v25 formal suite + citation_heritage + v17b automatically on new representations
- **Last check**: 2026-09-30T11:00:16 (check_count: 250)
- **Current detection**: Only TF-IDF family (8 reps, already evaluated, status: TF_IDF_COMPLETE_NO_EVAL_NEEDED)

### Awaited Representations (Not Yet Landed in Accepted State)
| Category | Representations | Status |
|----------|----------------|--------|
| Dense embeddings | center_projected_768dim, _64dim, _128dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | ⏳ Checkpointed 15yr, pending audit |
| Citation roles | citing_alpha0.3, following_alpha0.3, criticizing_alpha0.3 | ⏳ Not computed at 174k |
| Linear hybrids | linear_citation_concat, linear_hybrid05_concat | ⏳ Not computed at 174k |

---

## Recommendation

**Cycle complete.** No further evaluation cycles justified for current representations.

**Next cycle trigger:** When legal-distance promotes the 15-year (2000–2014) checkpoint to ACCEPTED and/or completes remaining 11 years, the monitor will automatically:
1. Detect new 174k dense embeddings in accepted state
2. Run full v25 formal suite (12 benchmarks + citation_heritage + v17b)
3. Update evaluation state with results

**Factory Director action:** Await legal-distance audit completion for 15-year checkpoint promotion. Then resume evaluation cycle for dense embeddings at ~100k scale, followed by full 174k when all 26 years complete.

---

## Evidence References

- Formal suite results: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- v25 suite detailed results: `results/evaluation/v25_174k_formal_suite/results/`
- Citation heritage benchmark: `evaluation/results/174k_citation_heritage/benchmark/citation_heritage_174k_tfidf_hnsw_20260930_093143.json`
- v17b label normalization: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- Monitor state: `evaluation/state/monitor_174k_state.json`
- Evaluation state: `evaluation/state/evaluation.json`

---

## Provenance

- **Config hash (v25 suite):** 4323f833fa72366a (frozen)
- **Config hash (run_174k_formal_suite):** b51701f5a9c11692 (frozen, exact k-NN on stratified subsample)
- **Global seed:** 42 (all evaluations)
- **HNSW params:** M=16, ef_construction=200, ef_search=100 (frozen)
- **Subsamples:** hierarchy=15,000, temporal=30,000 (frozen, stratified by branch)