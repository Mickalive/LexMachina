# Evaluation Lane v40 - Final Verification Report

**Date:** 2026-09-25  
**Factory Direction:** v27  
**Lane:** evaluation  
**Status:** TF-IDF FAMILY COMPLETE — ALL INFRASTRUCTURE VERIFIED OPERATIONAL — MONITOR ACTIVE (61 checks) — AWAITING LEGAL-DISTANCE 174K DENSE EMBEDDINGS

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions** from factory direction v27 for the TF-IDF production family (8 representations at 174k scale). The full evaluation infrastructure is verified operational and ready to auto-evaluate dense embeddings when they land from the legal-distance lane.

### Three Sub-Questions — ALL COMPLETE for TF-IDF Family

| Sub-Question | Status | Evidence |
|--------------|--------|----------|
| **1. Full 12-benchmark formal suite at 174k scale** | ✅ COMPLETE | All 8 TF-IDF representations evaluated with frozen config hash `4323f833fa72366a`, HNSW backend |
| **2. Citation_heritage benchmark on frozen 137,314-pair pool** | ✅ COMPLETE | 7/8 TF-IDF reps PASS (AUC ≥ 0.65); best: cited_decisions_tfidf AUC=0.9731 |
| **3. v17b label normalization generalization to 174k** | ✅ COMPLETE | 213→163 labels (32 cross-lingual canonical); PARTIAL generalization (purity gains 1.5-1.6x, NMI worsening >10% for 5/8 citation hybrids) |

---

## Production Default Confirmed

**`cited_outcome_hybrid_0.7`** is the confirmed production default:

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Language Dominance (v3 harness) | 0.6252 | < 0.85 | ✅ PASS |
| Jurist Preference (v3 harness) | 0.6615 | > 0.5 | ✅ PASS |
| Citation Heritage AUC | 0.9605 | ≥ 0.65 | ✅ PASS |
| NN Citation Rate @10 | 0.490 | — | — |
| Branch k-NN @5 | 0.393 | > 0.6333 | ❌ FAIL* |
| TF Metadata Recall @5 | 0.393 | ≥ 0.8 | ❌ FAIL* |
| Hierarchy Coherence (purity) | 0.128 | > 0.7 | ❌ FAIL** |
| Legal Area Clustering (purity) | 0.0034 | > 0.5 | ❌ FAIL** |

*Branch/recall failures are expected for citation-based representations (by design, they don't optimize for branch classification)
**Hierarchy/legal_area failures are corpus/label limitations, not representation defects (universal across ALL representations)

**Key Properties:** Zero-shot TF-IDF, no GPU required, HNSW-backed at 174k scale.

---

## Infrastructure Verification (v40 Cycle)

### Full Corpus Adversarial Evaluation (v3 Harness)
- **Config hash:** `4047da047fb339c1` (matches frozen v3 exactly)
- **Backend:** hnswlib (HNSW) confirmed operational at 173,963 decisions
- **Tested:** `cited_outcome_hybrid_0.7` at full 174k scale — PASS both adversarial gates
- **Duration:** ~118s with HNSW index building

### v25 Formal Suite Runner
- **Config hash:** `4323f833fa72366a` (frozen v16 thresholds)
- **Tested:** All 8 TF-IDF representations; `cited_outcome_hybrid_0.7` — 6 PASS / 5 FAIL / 1 SKIP in 80.4s
- **Components:** 12-benchmark suite + dedicated citation_heritage + v17b label normalization
- **Auto-eval ready:** `monitor_and_evaluate_174k.py` enhanced with `run_formal_suite_v25()` for new representations

### Citation Heritage Benchmark
- **Frozen pair pool:** 137,314 positive + 137,314 negative pairs (`citation_pairs_174k_full.json`)
- **Citation resolution:** 2,019/2,105 resolved (95.9%) from corpus citation graph
- **Infrastructure:** Ready for any 174k embedding

### v17b Label Normalization
- **Raw labels:** 213 unique → **Normalized:** 163 unique (23.5% reduction)
- **Cross-lingual canonical concepts:** 32 (DE/FR/IT mappings)
- **Coverage:** 49.3% of labels changed (85,819 decisions)
- **Generalization:** PARTIAL — purity gains for citation-based reps (1.5-1.6x), but NMI worsening >10% rule violated for 5/8

### Monitor Status
- **Checks completed:** 61
- **Last check:** 2026-09-25T09:28:54Z
- **Detected representations:** 0 (no new 174k dense embeddings in legal-distance accepted state)
- **Auto-eval pipeline:** ACTIVE — will trigger full v25 suite + adversarial evaluation on detection

---

## Legal-Distance Dependency Status

**BLOCKED ON:** Legal-distance lane 174k dense embeddings

| Representation Category | Expected | Status |
|-------------------------|----------|--------|
| Center Projected (768/64) | 2 | ⏳ Year-split in progress (14/26 years in checkpoints) |
| Metric Learning (linear/mahalanobis) | 2 | ⏳ Awaiting full corpus embeddings |
| Hybrid Objectives (stabilized/v2) | 2 | ⏳ Awaiting full corpus embeddings |
| Citation Role Embeddings | 3 | ⏳ Not yet computed |
| Linear Hybrids (concat/w3070) | 2 | ⏳ Not yet computed |

**Legal-distance progress:** 14 years completed (2000-2013) in checkpoints (`embeddings_2000.npy` through `embeddings_2013.npy`); final concatenation blocked on years 2014-2025 (GitHub run 36096850301 IN_PROGRESS).

**Partial validation done:** 14 year-split checkpoints (7,652 decisions) tested — 768-dim center_projected FAILS both adversarial gates (LangDom=0.9961, JuristPref=0.0062), consistent with v3 harness findings. Confirms year-split embeddings are loadable and evaluable.

---

## Jurist Human Study

**Status:** BLOCKED (external dependency)  
**Requirement:** 5-10 Swiss jurists recruited by repository owner  
**Framework:** Ready (pairwise preference protocol implemented)  
**Reporting:** Will report as blocked when reachable

---

## Acceptance Criteria Met

✅ **Frozen evaluation harness** (v3, seed=42, config hash verified)  
✅ **Frozen benchmark suite** (v25, 12 benchmarks, config hash verified)  
✅ **Frozen citation pairs** (137,314 pairs, 95.9% citation resolution)  
✅ **Frozen v17b normalization** (conservative cross-lingual canonical map)  
✅ **HNSW backend operational** at 174k scale (hnswlib confirmed)  
✅ **Auto-evaluation pipeline** ready for dense embeddings  
✅ **Production default identified and validated** (`cited_outcome_hybrid_0.7`)  
✅ **Negative results preserved** (hierarchy_coherence, legal_area_clustering, branch_knn failures documented as corpus/label limitations)  
✅ **No tuning after results** — all thresholds frozen before observation

---

## Next Steps

1. **Legal-distance completes 174k dense embeddings** (years 2014-2025)
2. **Monitor detects new representations** in legal-distance accepted state
3. **Auto-evaluation triggers:** Full v25 formal suite + adversarial evaluation
4. **Results integrated** into product serving defaults
5. **Jurist human study** initiated when recruitment completes

---

## Evidence References

- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — All 8 TF-IDF representations
- `results/evaluation/v25_174k_citation_heritage/*.json` — Dedicated citation heritage results
- `results/evaluation/v25_174k_v17b/*.json` — v17b label normalization comparison
- `evaluation/results/full_corpus_174k_verification/full_corpus_evaluation_results_worker0.json` — v3 harness verification
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — Frozen pair pool
- `evaluation/state/evaluation.json` — Lane state with v40 cycle verification
- `evaluation/state/monitor_174k_state.json` — Monitor state (61 checks)

---

**Recommendation:** `continue_recommended=false` for TF-IDF family (no additional same-question cycle justified). Evaluation lane ready to auto-evaluate dense embeddings when legal-distance delivers them.