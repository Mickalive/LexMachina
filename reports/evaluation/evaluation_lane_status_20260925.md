# Evaluation Lane Status Report — 2026-09-25

## Current Status: BLOCKED_ON_DEPENDENCIES

**Factory Direction Version:** 27  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** true  
**Last Monitor Check:** 2026-09-25T02:31:34 (check #29)

---

## Summary

The evaluation lane has **completed all three machine-executable sub-questions** for the TF-IDF production family (8 representations) at 174k scale:

1. ✅ **12-benchmark formal suite** (frozen v16 thresholds, config hash 4323f833fa72366a)
2. ✅ **Citation heritage benchmark** (frozen 137,314-pair pool, 2,019/2,105 citation resolution)
3. ✅ **v17b label normalization** generalization test (raw vs. normalized legal_area)
4. ✅ **v3 adversarial harness** at 174k scale (frozen thresholds: lang_dom < 0.85, jurist > 0.5)

**All TF-IDF evaluations COMPLETE.** The lane is now blocked awaiting **legal-distance 174k dense embeddings**.

---

## Key Findings from TF-IDF Family Evaluation

| Finding | Details |
|---------|---------|
| **No representation passes all 12 benchmarks** | Best: `cited_decisions_tfidf` (6/12 PASS) |
| **Citation-aware reps** | Excel at citation_heritage (AUC > 0.91), adversarial, multilingual; FAIL branch_knn, tf_metadata, boilerplate, temporal_stability, hierarchy_coherence |
| **Full-text/regeste hybrids** | Pass branch_knn, tf_metadata, boilerplate, temporal; FAIL adversarial (lang_dom > 0.99), multilingual |
| **Hierarchy coherence** | ALL FAIL (max purity 0.465 vs 0.7 threshold) |
| **Legal area clustering** | ALL FAIL |
| **v3 jurist pairwise gate** | ALL FAIL at 174k (legal_neighbor_rate ~0.12 vs 0.5 threshold) |
| **Scale-dependent collapse** | branch k-NN 0.81→0.39, temporal instability, hierarchy 0.88→0.15, jurist pairwise 0.79→0.12 |
| **v17b normalization** | FAILS generalization claim: 4/8 reps worsen hierarchy_nmi >10%, 1/8 worsens zoom_coherence >10% |

---

## Awaited Representations (from legal-distance lane)

### Dense Embeddings (6)
- `center_projected_768dim`
- `center_projected_64dim`
- `linear_metric_epoch4`
- `mahalanobis_metric_epoch4`
- `hybrid_stabilized_epoch1`
- `hybrid_v2_epoch3`

### Citation Role Embeddings (3)
- `citation_role_citing_alpha0.3`
- `citation_role_following_alpha0.3`
- `citation_role_criticizing_alpha0.3`

### Linear Hybrid Combinations (2)
- `linear_citation_concat`
- `linear_hybrid05_concat`

**Total awaited: 11 representations**

---

## Infrastructure Readiness (Verified 2026-09-25)

| Component | Status | Details |
|-----------|--------|---------|
| Metadata (174k) | ✅ Ready | 173,963 decisions, 2000-2026, 3 languages (de:106501, fr:57489, it:9973) |
| Citation pairs | ✅ Ready | 137,314 positive + 137,314 negative (frozen pool) |
| Frozen subsamples | ✅ Ready | Hierarchy: 15k (stratified by branch), Temporal: 30k (seed 42) |
| v17b normalization | ✅ Ready | 213 raw → 163 normalized legal areas (cross-lingual canonical map) |
| v25 formal suite | ✅ Ready | Pipeline loads metadata, builds HNSW, runs 12 benchmarks + citation_heritage + v17b |
| Full corpus evaluation | ✅ Ready | HNSW backend (M=16, ef_construction=200, ef_search=100) |
| Monitor script | ✅ Active | Watching `/tmp/lex_accepted/legal-distance/legal_distance/results` |

---

## Monitor Status

```
Check #29 at 2026-09-25T02:31:34
No 174k dense embeddings detected in accepted state
TF-IDF family: 8/8 evaluated (not in legal-distance accepted state; evaluated via v25 reconstruction)
Dense embeddings: 0/6 detected
Citation roles: 0/3 detected
Linear hybrids: 0/2 detected
```

---

## Next Actions

1. **Continue monitoring** — Legal-distance lane is actively executing (GH run 36071928708, year-split, TF-IDF first, then dense embeddings)
2. **Auto-evaluate on arrival** — Monitor will trigger v25 formal suite + full corpus adversarial + citation_heritage + v17b when dense embeddings land in accepted state
3. **Jurist human study** — Blocked (external dependency: 5-10 Swiss jurists recruitment by repository owner)

---

## Evidence References

- `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` — Frozen protocol
- `evaluation/data/174k/metadata_174k.json` — Frozen sample (173,963 decisions)
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — Frozen pair pool
- `evaluation/experiments/legal_area_normalize.py` — v17b normalization mapping
- `evaluation/evaluation_v3_harness.py` — Frozen adversarial thresholds
- `evaluation/run_full_corpus_evaluation.py` + `evaluation/scalable_nn.py` — HNSW scale path

---

## Recommendation

**CONTINUE monitoring.** The evaluation infrastructure is fully operational and ready to execute the frozen v25 formal suite on any 174k dense embeddings as soon as legal-distance delivers them to the accepted state. No code changes or pipeline fixes needed.