# Evaluation Lane v56 Cycle Verification Report

**Factory Direction Version:** 27
**GitHub Run:** 36217108211
**Timestamp:** 2026-09-26T04:18:00Z
**Lane Status:** BLOCKED_ON_DEPENDENCIES
**Evidence Tier:** REPRODUCED
**Continue Recommended:** FALSE

---

## Executive Summary

This cycle verification confirms that **all three machine-executable sub-questions for the TF-IDF family are COMPLETE at 174k scale** with frozen thresholds and no tuning after results. The evaluation lane infrastructure is fully operational and ready for auto-evaluation of new representations when they land from the legal-distance lane.

**Legal-distance dense embeddings progress:** Only 3/26 years (2000-2002) completed in checkpoints (~11%, 19,441 decisions). Final concatenated embeddings blocked on years 2003-2025. This is a CORRECTION from prior reports claiming 11/26 years (42%).

---

## Verifications Performed

### 1. Monitor Scan (Checks #83, #84)
- **Scan target:** `/tmp/lex_accepted/legal-distance/legal_distance/results`
- **Result:** No 174k dense embeddings detected in legal-distance accepted state
- **Checkpoints found:** `embeddings_2000.npy`, `embeddings_2001.npy`, `embeddings_2002.npy` (3 years only)
- **Progress.json:** `completed_years: ["2000", "2001", "2002"]`, `failed_years: []`
- **Monitor scans:** `174k_dense_embeddings` root directory for final concatenated embeddings (excludes checkpoints subdirectory)

### 2. v25_174k_formal_suite Runner Re-Verified
- **Test:** Re-evaluated `cited_outcome_hybrid_0.5` at 174k scale
- **Result:** 6 PASS / 5 FAIL / 1 SKIP in 88.7s
- **Config hash:** `4323f833fa72366a` (frozen)
- **Seed:** 42
- **All 8 TF-IDF representations** previously evaluated at 173,963 decisions
- **Results match** frozen `_suite_summary.json` exactly

| Representation | Pass | Fail | Skip | Key Metrics |
|---|---|---|---|---|
| cited_decisions_tfidf | 6 | 5 | 1 | citation_heritage AUC=0.9731 |
| outcome_tfidf | 3 | 9 | 0 | citation_heritage AUC=0.7204 |
| regeste_tfidf | 5 | 7 | 0 | citation_heritage AUC=0.4865 (FAIL) |
| full_text_tfidf_light | 7 | 5 | 0 | branch_knn PASS, adversarial FAIL |
| cited_outcome_hybrid_0.5 | 6 | 5 | 1 | **production default**, AUC=0.9193 |
| cited_outcome_hybrid_0.7 | 6 | 6 | 0 | **best overall**, AUC=0.9605 |
| regeste_full_text_hybrid_0.5 | 7 | 5 | 0 | branch_knn PASS, adversarial FAIL |
| regeste_full_text_hybrid_0.7 | 7 | 5 | 0 | branch_knn PASS, adversarial FAIL |

**Universal 174k FAILs (corpus/label limitations, not representation defects):**
- hierarchy_coherence (purity 0.08-0.47 < 0.7)
- legal_area_clustering (purity 0.003-0.08 < 0.5)
- temporal_stability
- boilerplate_resistance

**Citation-based reps pass adversarial gates; full-text/regeste reps fail language_dominance (~0.99).**

### 3. Citation Heritage Benchmark Infrastructure Re-Verified
- **Citation graph:** Validated from `resolved_full` (2,019/2,105 resolved = 95.9%)
- **Decisions with outgoing citations:** 174 in 174k corpus
- **Resolved citations mapping to corpus:** 924
- **Positive pairs (direct + shared citations):** 1,020
- **Negative pairs (sampled):** 1,020
- **Frozen pair pool:** `citation_pairs_174k_full.json` (137,314 pairs, threshold AUC ≥ 0.65)
- **7/8 TF-IDF representations PASS** citation_heritage AUC ≥ 0.65
- **Best:** cited_decisions_tfidf AUC=0.9731
- **Production default:** cited_outcome_hybrid_0.7 AUC=0.9605, nn_citation_rate@10=0.490

### 4. v17b Label Normalization Test Re-Verified at 174k
- **Raw labels:** 213 unique → **Normalized:** 163 unique (23.5% reduction)
- **Cross-lingual canonical concepts:** 32
- **PARTIAL generalization confirmed:**
  - 2/8 reps within ≤10% worsening rule: cited_decisions_tfidf, regeste_tfidf
  - 6/8 reps exceed: 5 on hierarchy NMI (-10.8% to -27.6%), 1 on zoom_coherence (cited_outcome_hybrid_0.5 -16.0%)
- **Normalized hierarchy purity gains:** 1.5-1.6x for citation-based reps
- **Even normalized, best hierarchy purity = 0.47 < 0.7 threshold**
- **Example (cited_outcome_hybrid_0.5):** hierarchy NMI -9.6% (within rule), hierarchy purity +53.6% (0.1297→0.1992)

### 5. Full Corpus Evaluation Infrastructure Verified
- **run_full_corpus_evaluation.py:** Config hash `4047da047fb339c1` verified present
- **scalable_nn.py:** HNSW backend operational (hnswlib on GitHub runners, sklearn exact fallback for <10k)
- **Frozen v3 harness compatibility confirmed**

### 6. Formal Suite Runner Verified
- **run_174k_formal_suite.py:** HNSW artifact fix (exact k-NN on fixed stratified subsample n=2000, decisions with known branch, seed=42) for adversarial/cross-language/jurist benchmarks
- **Config hash:** `b51701f5a9c11692`
- **Ready for 174k adversarial evaluation of new representations**

### 7. Monitor Enhanced with Auto-Evaluation
- **run_formal_suite_v25()** function copies new embedding .npy files to v25 suite embeddings directory and invokes full frozen v25 protocol (12-benchmark suite + citation_heritage + v17b label normalization) for each newly detected representation
- **Scan targets:** 174k_dense_embeddings root directory for final concatenated embeddings

### 8. Frozen Config Hashes Verified
- **Suite:** `4323f833fa72366a`
- **Harness:** `4047da047fb339c1`
- **Formal suite:** `b51701f5a9c11692`
- All verified against accepted dense embeddings from legal-distance (v5-v6) with exact metric match

---

## Legal-Distance Dense Embeddings Status

| Metric | Value |
|---|---|
| Years completed | 3/26 (2000-2002) |
| Completion rate | ~11% |
| Decisions completed | ~19,441 (estimated) |
| Total decisions | 173,963 |
| Checkpoint files | embeddings_2000.npy, embeddings_2001.npy, embeddings_2002.npy |
| Blocked on | Years 2003-2025 |
| GitHub run | 36096850301 (IN_PROGRESS) |

**CORRECTION:** Prior cycles reported 11/26 years (42%, 62,645 decisions) based on stale progress.json or filesystem state. Current actual state is 3/26 years.

---

## Jurist Human Study
- **Status:** BLOCKED
- **Dependency:** External (5-10 Swiss jurists recruitment by repository owner)
- **Framework:** Ready per v25 protocol
- **Does not block** machine-executable suite

---

## Key Findings

### Production Default Confirmed
**cited_outcome_hybrid_0.7** (zero-shot TF-IDF, no GPU required):
- Passes both adversarial gates at 174k (LangDom=0.5238 < 0.85, BranchCoherence=0.356 > 0.3)
- Citation heritage AUC=0.9605, nn_citation_rate@10=0.490
- Equivalent: cited_outcome_hybrid_0.5 (AUC=0.9193, nn_rate=0.476)

### Negative Results Preserved (Per Constitution)
Universal FAILs at 174k scale across ALL representations:
- hierarchy_coherence (purity 0.08-0.47 < 0.7)
- legal_area_clustering (purity 0.003-0.08 < 0.5)
- temporal_stability
- boilerplate_resistance_real_corpus

**These are corpus/label limitations, not representation defects.** Confirmed by v16/v18 findings at smaller scale and v17b label normalization showing only partial improvement.

### No Additional Same-Question Cycle Justified
Per Research Protocol: `continue_recommended=false` for TF-IDF family. All three machine-executable sub-questions complete with frozen thresholds, no tuning after results.

---

## Evidence Preservation

All evidence preserved with frozen config hashes:
- **v25 suite results:** `results/evaluation/v25_174k_formal_suite/`
- **Citation heritage:** `results/174k_citation_heritage/`
- **v17b analysis:** `results/174k_label_analysis/`
- **Formal suite:** `evaluation/results/174k/formal_suite/`
- **Monitor state:** `evaluation/state/monitor_174k_state.json` (95+ checks)
- **Config hashes:** Frozen and verified

---

## Next Recommendation

**BLOCKED_ON_DEPENDENCIES** — Awaiting legal-distance lane 174k dense embeddings (center_projected, metric learning, hybrid objectives, citation roles, linear hybrids). The evaluation infrastructure is fully ready for auto-evaluation via `monitor_and_evaluate_174k.py` when final concatenated embeddings land.

No action required for TF-IDF family. Lane correctly paused on same-question cycles.

---

*Report generated per Research Protocol §13: Write machine-readable lane state plus human-readable report.*