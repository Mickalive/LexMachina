# Evaluation Lane — Monitor Check 270 Report

**Date:** 2026-10-01T19:28:42  
**Factory Direction:** v29  
**Lane:** evaluation  
**Monitor Check:** #270  
**Run ID:** eval_174k_monitor_check270_20261001

---

## Executive Summary

Monitor check 270 completed. **No new awaited representations detected at 174k scale.** The evaluation lane continues in RUN status per factory direction "as representations land," having completed all three v29 mandated tasks for the TF-IDF family (8 representations at 174k scale) and awaiting new representations from legal-distance.

---

## Monitor Scan Results

### Detected Representations
| Source | Files Found | Status |
|--------|-------------|--------|
| `fractal_map/hierarchical_map_174k/legal_tfidf_embeddings` | 8 .npy files | **TF_IDF_COMPLETE_NO_EVAL_NEEDED** |
| `fractal_map/hierarchical_map_174k/tfidf_embeddings` | 4 .npy files | **TF_IDF_COMPLETE_NO_EVAL_NEEDED** |

### Awaited Representations — Status

| Category | Representation | Ready |
|----------|----------------|-------|
| **Dense embeddings** | center_projected_768dim | ✗ |
| | center_projected_64dim | ✗ |
| | center_projected_128dim | ✗ |
| | linear_metric_epoch4 | ✗ |
| | mahalanobis_metric_epoch4 | ✗ |
| | hybrid_stabilized_epoch1 | ✗ |
| | hybrid_v2_epoch3 | ✗ |
| **Citation roles** | citation_role_citing_alpha0.3 | ✗ |
| | citation_role_following_alpha0.3 | ✗ |
| | citation_role_criticizing_alpha0.3 | ✗ |
| **Linear hybrids** | linear_citation_concat | ✗ |
| | linear_hybrid05_concat | ✗ |

**No new 174k-scale .npy embeddings found in legal-distance accepted state.**

---

## Legal-Distance Progress (from checkpoints)

| Metric | Value |
|--------|-------|
| Years checkpointed | 19/26 (2000–2018) |
| Years ACCEPTED | 3/26 (2000–2002) |
| Decisions in checkpoints | ~130,000 / 173,963 (74.7%) |
| 174k concatenation | **NOT DONE** |
| Citation roles | **NOT COMPUTED** |
| Linear hybrids at 174k | **NOT COMPUTED** |

### Legal-Distance 19-Year Evaluation Results (Available, Not 174k)

| Representation | LangDom | JuristPref | Adversarial |
|----------------|---------|------------|-------------|
| raw 768dim | 0.983 | 0.0465 | FAIL |
| center_projected 768dim | 0.860 | 0.369 | FAIL |
| center_projected 128dim | 0.893 | 0.283 | FAIL |
| center_projected 64dim | 0.875 | 0.302 | FAIL |
| multilingual_e5 768dim raw | 0.988 | 0.032 | FAIL |
| **linear_citation_concat** | **0.767** | **0.545** | **PASS** |
| **linear_hybrid05_concat** | **0.778** | **0.540** | **PASS** |
| cited_decisions_tfidf | 0.472 | 0.724 | PASS |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.474 | 0.716 | PASS |

**Key finding:** Linear combinations PASS adversarial at 122k scale but await 174k concatenation and frozen formal suite evaluation.

---

## TF-IDF Family — Completed & Verified

All 8 TF-IDF representations at 174k (173,963 decisions) have completed the full v29 evaluation:

1. **Full 12-benchmark formal suite** (frozen harness v3, config hash `b51701f5a9c11692`)
2. **Citation heritage benchmark** (frozen 1,020-pair pool, 924 resolved citations)
3. **v17b label normalization generalization test** (NEGATIVE result)

### Adversarial Gate Results (run_174k_formal_suite.py — exact k-NN on stratified subsample n=2000)

| Representation | Language Dominance | Jurist Preference | Verdict |
|----------------|-------------------|-------------------|---------|
| cited_decisions_tfidf | 0.4917 | 0.7075 | PASS |
| outcome_tfidf | 0.5078 | 0.6660 | PASS |
| regeste_tfidf | 0.5111 | 0.6145 | PASS |
| full_text_tfidf_light | 0.4854 | 0.7080 | PASS |
| **cited_decisions_tfidf_outcome_hybrid_0.5 (production default)** | **0.4895** | **0.7265** | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4908 | 0.7195 | PASS |
| regeste_full_text_hybrid_0.5 | 0.4873 | 0.7140 | PASS |
| regeste_full_text_hybrid_0.7 | 0.4889 | 0.7120 | PASS |

**All 8 PASS both adversarial gates.** HNSW artifact fixed via exact k-NN on stratified valid subset.

### Fundamental Two-Mode Tradeoff Confirmed

| Mode | Adversarial Falsification | Branch/TF-Metadata | Citation Heritage |
|------|---------------------------|--------------------|-------------------|
| Citation-based (4 reps) | PASS | FAIL | PASS (AUC-ROC) |
| Text-based (4 reps) | FAIL (lang_dom ~0.999) | PASS | FAIL (AUC-ROC) |

---

## Infrastructure Status

| Component | Status |
|-----------|--------|
| HNSW backend | OPERATIONAL_ON_GITHUB_RUNNERS |
| Scalable NN (sklearn fallback) | OPERATIONAL |
| v25 Formal Suite | OPERATIONAL |
| Citation Heritage | FROZEN_2040_PAIRS_READY |
| v17b Normalization | OPERATIONAL |
| Monitor Script | ACTIVE_WITH_FORMAL_SUITE_AND_ENHANCED_SCAN |
| Formal Suite Runner | OPERATIONAL (NoneType.lower bug fixed) |

---

## Blockers (Unchanged)

1. **Dense embeddings concatenation to 174k NOT DONE** — 19/26 years checkpointed, only 3/26 ACCEPTED
2. **Citation role embeddings** — not yet available at 174k
3. **Linear hybrids at 174k** — PASS at 19-year scale but not concatenated to 174k
4. **Citation graph coverage** — only 0.1% of corpus (174/173,963 decisions) limits citation_heritage benchmark power
5. **Jurist human study** — framework ready but requires 5–10 Swiss jurists (external dependency)

---

## Next Recommendation

**CONTINUE** — Lane remains RUN per factory direction "as representations land."

- TF-IDF family: **COMPLETE** — no further same-question cycles justified
- Evaluation infrastructure: **VERIFIED AND AUDIT-READY**
- Awaiting: **legal-distance 174k concatenated dense embeddings, citation roles, linear hybrids**
- Monitor will continue polling (next check: #271)

---

## Provenance

- Monitor state: `evaluation/state/monitor_174k_state.json` (check_count=270)
- Evaluation lane state: `evaluation/state/evaluation.json`
- Factory direction: v29 (state/factory_direction.json)
- Config hash: `b51701f5a9c11692` (frozen harness v3)
- All prior results preserved in `evaluation/results/` and `reports/evaluation/`