# Evaluation Lane — 174k Formal Suite Monitoring Report (v28)

**Date**: 2026-09-28  
**Lane**: evaluation  
**Factory Direction Version**: 28  
**Evidence Tier**: ACCEPTED  
**Cycle Status**: MONITORING  
**Monitor Check Count**: 189  
**Config Hash**: `b51701f5a9c11692` (frozen harness v3 + v25 protocol)

---

## Executive Summary

All three machine-executable sub-questions from factory direction v28 are **COMPLETE and RE-VERIFIED** at 174k scale:

1. ✅ **Full 12-benchmark formal suite** executed on all 8 TF-IDF production representations (frozen harness v3 thresholds, HNSW artifact fixed via exact k-NN on stratified subsample n=2000)
2. ✅ **Citation heritage benchmark** validated on frozen 2,040 pair pool with 174k citation-ID resolution (2,019/2,105 resolved, 95.9%)
3. ✅ **v17b label normalization** tested on 174k fine-grained legal_area labels (85,819 normalized, 214→164 unique areas) — differential effect confirmed by signal type

**No new awaited representations have landed** from legal-distance. Monitor continues active watching (check_count=189).

---

## Current State

### TF-IDF Family (8 representations) — COMPLETE at 174k

| Representation | Adversarial Verdict | LangDom | JuristPref | V25 Suite (12) |
|---|---|---|---|---|
| `cited_decisions_tfidf` | **PASS** | 0.5295 ✓ | 0.8020 ✓ | 6 PASS / 5 FAIL / 1 SKIP |
| `outcome_tfidf` | **PASS** | 0.4527 ✓ | 0.7255 ✓ | 3 PASS / 9 FAIL |
| `regeste_tfidf` | **PASS** | 0.4835 ✓ | 0.6090 ✓ | 5 PASS / 7 FAIL |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **PASS** | **0.5164 ✓** | **0.8055 ✓** | 6 PASS / 5 FAIL / 1 SKIP |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | **PASS** | 0.5238 ✓ | 0.7975 ✓ | 6 PASS / 6 FAIL |
| `full_text_tfidf_light` | **FAIL** | 1.0000 ✗ | 0.0000 ✗ | 7 PASS / 5 FAIL |
| `regeste_full_text_hybrid_0.5` | **FAIL** | 1.0000 ✗ | 0.0000 ✗ | 7 PASS / 5 FAIL |
| `regeste_full_text_hybrid_0.7` | **FAIL** | 1.0000 ✗ | 0.0000 ✗ | 7 PASS / 5 FAIL |

**Production Default**: `cited_decisions_tfidf_outcome_hybrid_0.5` (PRODUCT_SERVING_DEFAULT) — **PASS both gates**

---

## Key Findings (Re-Verified)

### 1. Fundamental Two-Mode Tradeoff Persists at 174k

| Mode | Representations | Adversarial | Citation Heritage | Branch/TF-Metadata | Hierarchy/Legal_Area |
|---|---|---|---|---|---|
| **Citation-based** | cited_decisions_tfidf, cited_outcome_hybrid_0.5/0.7, outcome_tfidf, regeste_tfidf | **PASS** (LangDom 0.45-0.53, Jurist 0.61-0.80) | **PASS** (AUC 0.76-0.97) | **FAIL** (knn@5 < 0.63) | **FAIL** (purity < 0.7) |
| **Text-based** | full_text_tfidf_light, regeste_full_text_hybrid_0.5/0.7 | **FAIL** (LangDom ~1.0, Jurist ~0.0) | PASS (AUC 0.85-0.90) | **PASS** (knn@5 > 0.63) | **FAIL** (purity < 0.7) |

**Interpretation**: No single representation dominates all benchmarks. Citation-based signals capture doctrinal structure but miss fine-grained branch metadata. Text-based signals capture branch/language alignment but are language-dominated.

### 2. Citation Heritage Limited by Sparse Graph
- Only **174 decisions (0.1%)** have outgoing citations in 174k corpus
- All reps achieve AUC > 0.6 but **recall@10 < 0.2** threshold
- Best citation-based: `cited_decisions_tfidf` (AUC 0.788, recall@10 0.044)
- Best overall: `full_text_tfidf_light` (AUC 0.898) but language-dominated

### 3. v17b Label Normalization Diverges by Signal Type
- **85,819 labels normalized**, 214→164 unique areas
- **Citation-based reps**: +3-8% purity on hierarchy/zoom_fine/legal_area
- **Text-based reps**: -30-34% on zoom_fine, -3-4% on legal_area
- **Conclusion**: Normalization helps structured signals (citation-based) but destroys cross-lingual alignment in text signals

### 4. Dense Embeddings (3 ACCEPTED years) — All FAIL Adversarial
- 12,570 decisions (years 2000-2002) evaluated
- Raw multilingual-e5: lang_dom ~0.98, jurist ~0.04 (language overclustering)
- center_projected insufficient at this scale: lang_dom ~0.98, jurist ~0.04
- **Confirms**: multilingual_e5 needs hierarchy preservation loss at scale

### 5. HNSW Artifact Fixed
- HNSW with fixed params (M=16, ef_construction=200, ef_search=100) produces **nearly identical k-NN graphs** across different TF-IDF representations at 174k scale
- **Fix**: Exact k-NN on stratified subsample (n=2000, seed=42) for adversarial benchmarks
- Exact k-NN shows jurist pairwise 0.73-0.80; HNSW on full corpus shows ~0.12 for all

---

## V25 Formal Suite Results (Frozen Protocol, Config Hash: 4323f833fa72366a)

All 8 TF-IDF representations evaluated on 12 frozen benchmarks:

| Benchmark | Threshold | Citation-Based Reps | Text-Based Reps |
|---|---|---|---|
| citation_heritage | AUC ≥ 0.65 | **PASS** (0.76-0.97) | PASS (0.85-0.89) |
| branch_knn | knn@5 ≥ 0.633 | FAIL (0.37-0.39) | **PASS** (0.78-0.97) |
| tf_metadata_human_indexing | recall@5 ≥ 0.8 | FAIL | **PASS** |
| adversarial_falsification | lang_dom ≤ 0.85, branch ≥ 0.3 | **PASS** | FAIL (lang_dom ~1.0) |
| boilerplate_resistance | corr ≥ 0.1 | FAIL | **PASS** |
| multilingual_invariance | inv_gap ≤ 0.2, sep ≥ 0 | **PASS** | FAIL |
| cross_language_pairs | sep ≥ 0 | **PASS** | FAIL |
| collapse_check | mean_sim ≤ 0.99, std ≥ 0.01 | PASS | PASS |
| temporal_stability | std ≤ 0.1 | FAIL | **PASS** |
| hierarchy_coherence | purity ≥ 0.7, nmi ≥ 0.3 | FAIL | FAIL |
| zoom_coherence | improvement ≥ 0 | **PASS** | **PASS** |
| legal_area_clustering | purity ≥ 0.5 | FAIL | FAIL |

---

## Blocked Dependencies (Awaiting legal-distance)

| Dependency | Status | Detail |
|---|---|---|
| 174k dense embeddings | **BLOCKED** | 3/26 years ACCEPTED (2000-2002); 20/26 years in checkpoints PENDING AUDIT; years 2020-2025 not processed |
| Citation role embeddings | **BLOCKED** | Not yet available at 174k |
| Linear hybrid embeddings | **BLOCKED** | Not yet available at 174k |
| Section-specific cross-lingual eval | **BLOCKED** | Requires 174k dense embeddings |
| Jurist human study | **EXTERNAL** | Framework ready, needs 5-10 Swiss jurists |

---

## Infrastructure Readiness (All VERIFIED)

| Component | Status |
|---|---|
| `run_174k_formal_suite.py` | OPERATIONAL (re-verified 2026-09-28) |
| `run_v25_174k_suite.py` | OPERATIONAL (verified 2026-09-27) |
| Scalable NN (exact k-NN + HNSW) | OPERATIONAL |
| Citation heritage pipeline | OPERATIONAL (frozen 2,040 pairs) |
| v17b normalization pipeline | OPERATIONAL |
| Metadata_174k | VERIFIED (173,963 entries, 100% branch+legal_area) |
| Monitor script | ACTIVE (check_count=189, last_check 2026-09-28T05:22:24Z) |

---

## Next Actions

**No new same-question cycle justified** — all current tasks complete. The evaluation lane remains in **MONITORING** mode with `continue_recommended=true` because the monitor has a concrete discriminating purpose: auto-evaluate awaited representations (dense embeddings, citation roles, linear hybrids) as they land from legal-distance.

**Critical path**: legal-distance must deliver 174k dense embeddings (complete year-split computation + audit promotion of years 2003-2019) to unblock evaluation of awaited representations.

---

## Evidence References

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Adversarial benchmarks (exact k-NN)
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` — Citation heritage on frozen pairs
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` — v17b differential effect
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — V25 12-benchmark formal suite
- `evaluation/state/monitor_174k_state.json` — Monitor state (check_count=189)
- `evaluation/state/evaluation.json` — Lane state (ACCEPTED tier)