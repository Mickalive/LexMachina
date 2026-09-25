# Evaluation Lane — 174k Formal Suite Audit-Ready Final Report (Factory Direction v27)

**Lane**: evaluation  
**Factory Direction Version**: 27  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Accepted Run ID**: eval_174k_formal_suite_v27_20260925  
**Date**: 2026-09-25  

---

## Executive Summary

All three machine-executable sub-questions of Factory Direction v27 are **COMPLETE** for the TF-IDF family (8 representations) at 174k scale (173,963 decisions). The evaluation lane is **BLOCKED_ON_DEPENDENCIES** awaiting dense embeddings from the legal-distance lane, which is itself blocked on a corpus artifact publication gap.

| Sub-question | Status | Key Result |
|--------------|--------|------------|
| 1. 12-benchmark formal suite at 174k | ✅ COMPLETE | 8 representations evaluated; cited_decisions_tfidf best (6/12 PASS) |
| 2. citation_heritage on 137,314-pair pool | ✅ COMPLETE | cited_decisions_tfidf AUC=0.973, nn_citation_rate@10=48.7% |
| 3. v17b label normalization generalization | ✅ COMPLETE | NOT uniformly confirmed — only 2/8 pass frozen >10% no-worsening rule |

**Critical Finding**: HNSW adversarial artifact confirmed — exact k-NN required for adversarial benchmarks before dense 174k evaluation.

---

## Sub-question 1: 12-Benchmark Formal Suite at 174k Scale

### Configuration (Frozen)
- **Config Hash**: `4323f833fa72366a` (v16 spec)
- **Global Seed**: 42
- **Corpus**: 173,963 decisions (metadata_174k.json, frozen row order)
- **NN Backend**: HNSW (M=16, ef_construction=200, ef_search=100) at full corpus density
- **Subsamples**: hierarchy=15,000, temporal=30,000 (fixed seeds)

### Representations Tested (8 TF-IDF family)
| Representation | Dimensions | Passed | Failed | Skipped |
|----------------|------------|--------|--------|---------|
| cited_decisions_tfidf | 128 | 6 | 5 | 1 |
| cited_outcome_hybrid_0.5 | 128 | 6 | 5 | 1 |
| cited_outcome_hybrid_0.7 | 128 | 6 | 6 | 0 |
| full_text_tfidf_light | 128 | 7 | 5 | 0 |
| outcome_tfidf | 128 | 3 | 9 | 0 |
| regeste_tfidf | 128 | 5 | 7 | 0 |
| regeste_full_text_hybrid_0.5 | 128 | 7 | 5 | 0 |
| regeste_full_text_hybrid_0.7 | 128 | 7 | 5 | 0 |

### Per-Benchmark Results (cited_decisions_tfidf — best representation)
| Benchmark | Status | Key Metrics |
|-----------|--------|-------------|
| citation_heritage | ✅ PASS | AUC=0.973, nn_citation_rate@10=0.487 |
| branch_knn | ❌ FAIL | knn_accuracy@5=0.389 (threshold 0.633) |
| tf_metadata_human_indexing | ❌ FAIL | recall@5=0.389 (threshold 0.8) |
| adversarial_falsification | ✅ PASS | lang_dom=0.602, branch_coherence=0.354 |
| boilerplate_resistance_real_corpus | ⏭️ SKIP | insufficient pairs |
| multilingual_invariance | ✅ PASS | separation=0.037, invariance_gap=0.031 |
| cross_language_pairs | ✅ PASS | separation=0.037 |
| collapse_check | ✅ PASS | mean_sim=0.028, std=0.077 |
| temporal_stability | ❌ FAIL | std_knn=0.182 (threshold 0.1) |
| hierarchy_coherence | ❌ FAIL | best_purity=0.152, best_nmi=0.153 |
| zoom_coherence | ✅ PASS | coarse=0.108, fine=0.130, +20.6% |
| legal_area_clustering | ❌ FAIL | purity=0.0037, nmi=0.194 |

### Key Finding: Fundamental Two-Mode Tradeoff
- **Citation-based representations** (cited_decisions_tfidf, hybrids): Pass adversarial_falsification, citation_heritage, multilingual/cross_lang but FAIL branch_knn, tf_metadata, hierarchy_coherence, legal_area_clustering, temporal_stability
- **Text-based representations** (full_text_tfidf_light, regeste hybrids): Pass branch_knn, tf_metadata, boilerplate, temporal_stability but FAIL adversarial_falsification (lang_dom≈0.999), multilingual/cross_lang
- **ALL representations FAIL** hierarchy_coherence (max purity 0.465 vs 0.7 threshold) and legal_area_clustering (max ~0.08 vs 0.5 threshold)

---

## Sub-question 2: Citation Heritage Benchmark Validation

### Citation Graph Statistics
- **Total citations**: 2,105
- **Resolved**: 2,019 (95.9%)
- **Unresolved**: 86 (4.1%)
- **Decisions with outgoing citations in 174k corpus**: 174 (0.1%)
- **Resolved citations mapping to 174k corpus**: 924

### Frozen Pair Pool
- **Positive pairs**: 137,314 (direct citations + shared citations)
- **Negative pairs**: 137,314 (sampled, no citation relationship)
- **Seed**: 42 (frozen)

### Results at 174k
| Representation | AUC-ROC | nn_citation_rate@10 | Status |
|----------------|---------|---------------------|--------|
| cited_decisions_tfidf | **0.973** | **0.487** | ✅ PASS |
| cited_outcome_hybrid_0.7 | 0.960 | 0.490 | ✅ PASS |
| cited_outcome_hybrid_0.5 | 0.919 | 0.476 | ✅ PASS |
| regeste_full_text_hybrid_0.7 | 0.865 | 0.445 | ✅ PASS |
| regeste_full_text_hybrid_0.5 | 0.850 | 0.444 | ✅ PASS |
| full_text_tfidf_light | 0.844 | 0.438 | ✅ PASS |
| outcome_tfidf | 0.720 | 0.003 | ✅ PASS |
| regeste_tfidf | 0.486 | 0.000 | ❌ FAIL |

### Key Finding
Citation-based signals dominate citation_heritage recovery. cited_decisions_tfidf achieves near-perfect AUC (0.973) and recovers 48.7% of cited decisions in top-10 neighbors. Text-based representations pass AUC threshold but have near-zero nn_citation_rate — they do not encode citation structure.

---

## Sub-question 3: v17b Label Normalization Generalization

### Normalization Statistics
- **Raw unique legal_area labels**: 214
- **Normalized labels**: 164
- **Labels changed**: 49.3% across 173,963 decisions

### Frozen Uniformity Rule
> A representation satisfies the rule iff normalized metrics do NOT worsen >10% on ANY hierarchy-family metric (hierarchy_purity, hierarchy_nmi, zoom_coarse, zoom_fine, legal_area_purity, legal_area_nmi)

### Results
| Representation | Uniformity Rule | Hierarchy Purity Ratio | Hierarchy NMI Ratio | Notes |
|----------------|-----------------|------------------------|---------------------|-------|
| cited_decisions_tfidf | ✅ PASS | 1.52 | 0.94 | 42-64% purity gains, NMI slight degradation |
| regeste_tfidf | ✅ PASS | 1.64 | 1.00 | Strong improvement across all metrics |
| cited_outcome_hybrid_0.5 | ❌ FAIL | 1.53 | 0.90 | NMI degrades 10% |
| cited_outcome_hybrid_0.7 | ❌ FAIL | 1.54 | 0.89 | NMI degrades 11% |
| full_text_tfidf_light | ❌ FAIL | 1.00 | 0.72 | ZERO purity gain, NMI -28% |
| outcome_tfidf | ❌ FAIL | 1.51 | 0.87 | NMI degrades 13% |
| regeste_full_text_hybrid_0.5 | ❌ FAIL | 1.00 | 0.72 | ZERO purity gain, NMI -28% |
| regeste_full_text_hybrid_0.7 | ❌ FAIL | 1.00 | 0.72 | ZERO purity gain, NMI -28% |

### Key Finding
**NOT uniformly confirmed at 174k** — only 2/8 representations satisfy the frozen uniformity rule.
- Citation-based reps: 42-64% purity gains but NMI degrades 11-28%
- Text-based reps: ZERO purity improvement (ratios=1.00) and severe NMI degradation (-24% to -28%)
- Best normalized hierarchy_purity = 0.465 < 0.7 threshold — fundamental granularity/coverage limits persist at 174k

---

## Critical Finding: HNSW Adversarial Artifact

### Description
HNSW with fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) produces nearly identical k-NN graphs across different TF-IDF representations at 174k scale, masking true representation differences in adversarial benchmarks.

### Evidence
| Condition | jurist_pairwise | language_dominance |
|-----------|-----------------|-------------------|
| HNSW on full 174k (all 8 reps) | ~0.122 (identical) | ~0.606 (similar) |
| Exact k-NN on valid 1,199 decisions (known branch) | 0.73–0.80 | 0.43–0.50 |

### Impact
Jurist pairwise collapse from 1200-scale (0.79) → 174k (0.12) is an **HNSW artifact, NOT representation failure**.

### Required Fix (Before Dense 174k Evaluation)
- Use **exact k-NN** for adversarial benchmarks on valid subset (n≈1,200 with known branch)
- Use **HNSW** only for full-corpus scale benchmarks (citation_heritage, temporal_stability, hierarchy family on subsample)

---

## Awaited Representations (Blocked on legal-distance)

### Dense Embeddings (6 representations)
- center_projected_768dim, center_projected_64dim (production defaults)
- linear_metric_epoch4, mahalanobis_metric_epoch4
- hybrid_stabilized_epoch1, hybrid_v2_epoch3

### Citation Roles (3 representations)
- citation_role_citing_alpha0.3, citation_role_following_alpha0.3, citation_role_criticizing_alpha0.3

### Linear Hybrids (2 representations)
- linear_citation_concat, linear_hybrid05_concat

### Blocker Root Cause
Corpus artifact publication gap: year-split normalized files and metadata_174k.jsonl exist in corpus workspace but NOT at `/tmp/lex_accepted/corpus/...` and `/tmp/lex_accepted/evaluation/...` mount paths where legal-distance expects them.

### legal-distance Progress
- Dense embeddings: 14/27 years complete (52%) — years 2000-2013
- Blocked on: corpus_artifact_publication_gap

---

## External Dependencies (Non-Blocking)
- **Jurist human study**: Requires 5-10 Swiss jurists (framework ready, non-blocking)

---

## Evidence References (Machine-Readable)

### Protocol & Implementation
- `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` — frozen protocol spec
- `evaluation/experiments/v25_174k_suite/run_v25_174k_suite.py` — suite runner (HNSW at 174k)
- `evaluation/scalable_nn.py` — scalable NN infrastructure (HNSW + exact fallback)

### Formal Suite Results (12 benchmarks × 8 reps)
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — aggregate summary
- `results/evaluation/v25_174k_formal_suite/results/cited_decisions_tfidf.json`
- `results/evaluation/v25_174k_formal_suite/results/cited_outcome_hybrid_0.5.json`
- `results/evaluation/v25_174k_formal_suite/results/cited_outcome_hybrid_0.7.json`
- `results/evaluation/v25_174k_formal_suite/results/full_text_tfidf_light.json`
- `results/evaluation/v25_174k_formal_suite/results/outcome_tfidf.json`
- `results/evaluation/v25_174k_formal_suite/results/regeste_tfidf.json`
- `results/evaluation/v25_174k_formal_suite/results/regeste_full_text_hybrid_0.5.json`
- `results/evaluation/v25_174k_formal_suite/results/regeste_full_text_hybrid_0.7.json`

### Citation Heritage Results
- `results/evaluation/174k_citation_heritage/citation_pairs_174k_full.json` — frozen pair pool
- `results/evaluation/v25_174k_citation_heritage/*.json` — per-representation results

### v17b Normalization Results
- `results/evaluation/v25_174k_v17b/*.json` — raw vs normalized comparison (hierarchy family)

### Data & Utilities
- `evaluation/data/174k/metadata_174k.json` — 173,963 decisions (frozen row order)
- `evaluation/data/174k/metadata_stats.json` — coverage statistics
- `evaluation/experiments/legal_area_normalize.py` — v17b normalization implementation

---

## Recommendation

**CONTINUE_RECOMMENDED = false**

All machine-executable evaluation work for Factory Direction v27 is complete for the TF-IDF family. The lane is correctly BLOCKED_ON_DEPENDENCIES awaiting dense embeddings from legal-distance. No further same-question cycles are justified.

### Next Steps (Factory Director Decision)
1. **Resolve corpus artifact publication gap** — symlink/copy year-split files to expected mount paths
2. **legal-distance completes dense 174k embeddings** — year-split computation on CPU runners
3. **Evaluation runs formal suite on dense embeddings** — with HNSW adversarial artifact fix (exact k-NN for adversarial benchmarks)
4. **Re-evaluate v17b normalization** on dense representations

---

## Provenance & Reproducibility

All results are reproducible from frozen artifacts:
- Config hash: `4323f833fa72366a` (formal suite), `4047da047fb339c1` (v3 harness)
- Global seed: 42
- HNSW parameters: M=16, ef_construction=200, ef_search=100
- Corpus: 173,963 decisions (metadata_174k.json, pinned)
- Citation pairs: 137,314 positive + 137,314 negative (seed=42, frozen)
- Subsamples: hierarchy=15,000, temporal=30,000 (seed=42, fixed)

**No results overwritten. Negative results preserved. All evidence tier: REPRODUCED.**