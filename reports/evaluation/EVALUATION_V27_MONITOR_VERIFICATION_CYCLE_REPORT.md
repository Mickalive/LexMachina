# Evaluation Lane v27 — Monitor Verification Cycle Report

**Date:** 2026-09-26  
**Factory Direction Version:** 27  
**Lane:** evaluation  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES (correct)  
**Continue Recommended:** false (no additional same-question cycle justified for TF-IDF family)

---

## Summary

Verified the 174k evaluation monitoring infrastructure is operational and correctly detecting representation availability. The monitor ran successfully (check #118), confirming:

1. **TF-IDF family evaluation COMPLETE** — All 8 production representations evaluated across all three machine-executable sub-questions of factory direction v27
2. **Dense embeddings NOT YET AVAILABLE** — Only 3/26 years complete (2000-2002) in legal-distance lane; final concatenation blocked on years 2003-2025
3. **Monitor correctly ignores incomplete artifacts** — Year-split checkpoints in `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` are NOT treated as evaluable representations
4. **Infrastructure fully operational** — v25 formal suite, citation_heritage, v17b normalization, HNSW artifact fix (exact k-NN on valid subset) all verified working

---

## Sub-Question Completion Status (Factory Direction v27)

| Sub-Question | Status | Details |
|--------------|--------|---------|
| **1. 12-benchmark formal suite at 174k** | ✅ COMPLETE | 8 TF-IDF representations evaluated with frozen harness v3 thresholds (config hash `4323f833fa72366a`). HNSW artifact fixed via exact k-NN on fixed stratified subsample (n=2000, seed=42). |
| **2. Citation heritage benchmark** | ✅ COMPLETE | Frozen 137,314-pair pool validated. 2,019/2,105 citations resolved (95.9%). `cited_decisions_tfidf` achieves AUC 0.973, nn_citation_rate@10 0.487. |
| **3. v17b label normalization generalization** | ✅ COMPLETE (PARTIAL) | 214 raw → 164 normalized labels. Only 2/8 representations satisfy frozen >10% no-worsening rule on ALL hierarchy-family metrics. Best normalized hierarchy_purity = 0.465 < 0.7 threshold. |

---

## Monitor Verification Results

```
REPRESENTATION READINESS:
  COMPLETED (TF-IDF family at 174k):
    ✓ cited_decisions_tfidf
    ✓ outcome_tfidf
    ✓ cited_decisions_tfidf_outcome_hybrid_0.5
    ✓ cited_decisions_tfidf_outcome_hybrid_0.7
    ✓ regeste_tfidf
    ✓ full_text_tfidf_light
    ✓ regeste_full_text_hybrid_0.5
    ✓ regeste_full_text_hybrid_0.7
  AWAITED (dense embeddings, citation roles, linear hybrids):
    awaited_dense_174k:
      ✗ center_projected_768dim
      ✗ center_projected_64dim
      ✗ center_projected_128dim
      ✗ linear_metric_epoch4
      ✗ mahalanobis_metric_epoch4
      ✗ hybrid_stabilized_epoch1
      ✗ hybrid_v2_epoch3
    awaited_citation_roles_174k:
      ✗ citation_role_citing_alpha0.3
      ✗ citation_role_following_alpha0.3
      ✗ citation_role_criticizing_alpha0.3
    awaited_linear_hybrids_174k:
      ✗ linear_citation_concat
      ✗ linear_hybrid05_concat
```

---

## Dense Embeddings Progress (Legal-Distance Lane)

| Metric | Value |
|--------|-------|
| Years Complete | 3/26 (2000, 2001, 2002) |
| Completion Rate | 11.5% |
| Decisions Complete | 19,441 / 173,963 (11%) |
| Blocked On | Years 2003-2025 pending year-split execution |
| Checkpoint Location | `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` |

---

## Infrastructure Status (Frozen, Verified)

| Component | Status |
|-----------|--------|
| HNSW Backend | OPERATIONAL_ON_GITHUB_RUNNERS |
| Scalable NN (sklearn fallback) | OPERATIONAL_WITH_SKLEARN_FALLBACK |
| v25 Formal Suite Runner | OPERATIONAL (NoneType.lower bug fixed) |
| Citation Heritage Pair Pool | FROZEN_137314_PAIRS_READY |
| v17b Label Normalization | OPERATIONAL |
| Monitor Script | ACTIVE_WITH_FORMAL_SUITE_AND_ENHANCED_SCAN |
| HNSW Artifact Fix | IMPLEMENTED (exact k-NN on valid subset for adversarial) |

---

## HNSW Artifact Fix (Critical, Pre-Validated)

**Problem:** HNSW with fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) produces nearly identical k-NN graphs across different TF-IDF representations at 174k scale, masking true representation differences in adversarial benchmarks.

**Evidence:** 
- HNSW on full 174k: all 8 reps show identical `jurist_pairwise=0.122`, similar `lang_dom ~0.606`
- Exact k-NN on fixed stratified subsample (n≈1200 with known branch): `jurist_pairwise=0.71-0.80`, `lang_dom=0.43-0.53`, differentiated across representations

**Fix Implemented:** Exact k-NN (sklearn brute force) on fixed stratified subsample of 2000 decisions with known branch for adversarial benchmarks; HNSW only for full-corpus scale benchmarks (citation_heritage, temporal_stability, hierarchy family on subsample, boilerplate).

**Status:** FIXED and verified before dense 174k evaluation.

---

## Blocker Analysis

**Primary Blocker:** `legal_distance_174k_dense_embeddings_not_in_accepted_state`

**Root Cause:** Corpus artifact publication gap — year-split normalized files and metadata exist in corpus workspace but NOT at `/tmp/lex_accepted/corpus/...` mount paths where legal-distance expects them.

**Legal-Distance Status:** Years 2000-2002 complete; years 2003-2025 blocked missing upstream data.

**Methodological Blocker:** HNSW adversarial artifact requires exact k-NN fix before dense 174k eval — **RESOLVED**.

**External Dependencies:** Jurist human study requires 5-10 Swiss jurists (framework ready, non-blocking).

---

## Recommendation

**No additional same-question cycle justified for TF-IDF family.** 

The evaluation lane has:
- Completed all three machine-executable sub-questions at 174k scale for the TF-IDF production family
- Frozen negative results preserved (no TF-IDF representation passes all 12 benchmarks; fundamental two-mode tradeoff established; hierarchy_coherence and legal_area_clustering universally fail at 174k due to label granularity/coverage limits)
- Monitoring infrastructure operational and ready for autonomous evaluation when legal-distance 174k dense embeddings land
- Factory direction v27 correctly statused: evaluation lane RUN but BLOCKED_ON_DEPENDENCIES

**Next Action:** Factory Director to monitor legal-distance lane progress. Evaluation lane will auto-evaluate dense representations (center_projected, metric learning, hybrid, citation roles, linear hybrids) as they appear in accepted state via the verified monitor.

---

## Evidence References

- `evaluation/state/monitor_174k_state.json` (check_count=118, last_check=2026-09-26T08:29:29)
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`
- `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` (frozen protocol)
- `evaluation/run_174k_formal_suite.py` (HNSW artifact fixed runner)
- `evaluation/monitor_and_evaluate_174k.py` (verified monitor)
- `state/evaluation.json` (accepted lane state, BLOCKED_ON_DEPENDENCIES)

---

**Signed:** Evaluation Lane (autonomous verification cycle)