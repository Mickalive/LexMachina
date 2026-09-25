# Evaluation Lane v43 — Operational Resume & Verification Cycle Report

**Factory Direction Version:** 27  
**Lane:** evaluation  
**Run ID:** eval_v27_174k_verification_36127454643  
**Date:** 2026-09-25  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  

---

## Executive Summary

This cycle performs an **operational resume from persisted producer snapshot (run 36126729759)**, verifies all completed work is preserved and audit-ready, diagnoses the orchestration/validation failure, and confirms the lane deliverable status. No new representations have landed since the last cycle.

### Current Status

| Workstream | Status | Details |
|------------|--------|---------|
| **TF-IDF Family (8 reps) at 174k** | ✅ **COMPLETE** | All 3 machine-executable sub-questions fully evaluated |
| **Dense 1200 Baselines (7 reps)** | ✅ **ESTABLISHED** | 5/7 pass both adversarial gates |
| **Dense Embeddings 174k (6 reps)** | ⏳ **PARTIAL (52%)** | 14/27 years computed (2000-2013); blocked on corpus artifact publication |
| **Citation Roles 174k (3 reps)** | ❌ **NOT STARTED** | Awaiting legal-distance |
| **Linear Hybrids 174k (2 reps)** | ❌ **NOT STARTED** | Awaiting legal-distance |
| **Jurist Human Study** | 🔒 **BLOCKED (external)** | Requires 5-10 Swiss jurists; framework ready |

---

## Verification of Completed Work (Audit-Ready)

All evidence from prior cycles is **preserved and verifiable**:

### 1. 12-Benchmark Formal Suite (v25 Frozen Protocol)
- **Config hash:** `4323f833fa72366a`
- **Sample:** 173,963 decisions (frozen row order from `metadata_174k.json`)
- **NN Backend:** HNSW (M=16, ef_construction=200, ef_search=100)
- **Results:** `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- **Key finding:** No representation passes all 12 benchmarks. Best: `cited_decisions_tfidf` (6/12 PASS)

### 2. Citation Heritage Benchmark
- **Pair pool:** 137,314 positive + 137,314 negative (frozen)
- **Citation resolution:** 2,019/2,105 (95.9%)
- **Results:** `results/evaluation/v25_174k_citation_heritage/*.json`
- **Key finding:** 7/8 PASS (AUC ≥ 0.65). Top: `cited_decisions_tfidf` AUC=0.973

### 3. v17b Label Normalization
- **Normalization:** Conservative cross-lingual canonical map (frozen)
- **Sample:** Fixed 15,000-decision hierarchy subsample (seed 42)
- **Results:** `results/evaluation/v25_174k_v17b/*.json`
- **Key finding:** 5/8 show 45-64% purity gains; 0 worsen. Best normalized hierarchy_purity=0.465 < 0.7 threshold

### 4. Full Corpus Adversarial Evaluation (v3 Harness)
- **Config hash:** `4047da047fb339c1`
- **Results:** `results/full_corpus_174k_tfidf/full_corpus_evaluation_results_worker0.json`
- **Key finding:** **HNSW methodological artifact confirmed** — identical k-NN graphs across representations

### 5. Dense 1200 Baselines
- **Config hash:** `4047da047fb339c1`
- **Results:** `results/dense_1200_baseline/full_corpus_evaluation_results_worker0.json`
- **Key finding:** 5/7 pass both adversarial gates. Best: `linear_metric_epoch4` (jurist_pref=0.6847, lang_dom=0.6805)

---

## Critical Findings (Confirmed & Documented)

### 1. HNSW Methodological Artifact (MUST FIX before dense embeddings arrive)

**What happens:** HNSW with fixed parameters (M=16, ef_construction=200, ef_search=100, seed=42) produces nearly identical k-NN graphs across different TF-IDF representations at 174k scale.

**Evidence:**
- v3 adversarial harness (HNSW on full 174k): ALL 8 TF-IDF reps show jurist pairwise = **0.122**, lang_dom ≈ **0.606**
- Full corpus evaluation (exact k-NN on valid 1199 decisions with known branch): jurist pairwise = **0.73-0.80**, lang_dom = **0.43-0.50**
- 6/8 representations show **identical** HNSW k-NN graphs

**Impact:** The jurist pairwise "collapse" from 1200→174k (0.79→0.12) is an **artifact**, not a real representation failure.

**Required fix before dense embeddings arrive:** Use exact k-NN for adversarial benchmarks (computationally feasible on valid subset n≈1200) or implement per-representation HNSW seeds.

### 2. Fundamental Citation vs Full-Text Tradeoff

| Representation Type | Strengths | Weaknesses |
|---------------------|-----------|------------|
| **Citation-aware** (`cited_decisions_tfidf`, `cited_outcome_hybrid_*`) | citation_heritage (AUC>0.91), adversarial_falsification, multilingual | FAIL: branch_knn, tf_metadata, boilerplate, temporal, hierarchy_coherence |
| **Full-text/regeste hybrids** (`full_text_tfidf_light`, `regeste_full_text_hybrid_*`) | branch_knn, tf_metadata (recall@5>0.82), boilerplate, temporal, zoom_coherence | FAIL: adversarial (lang_dom>0.99), multilingual, cross_language, hierarchy_coherence |
| **ALL** | — | FAIL: hierarchy_coherence (max purity 0.465 vs 0.7), legal_area_clustering |

### 3. Hierarchy Coherence Ceiling = Granularity Limit

Even with v17b normalization (which generalizes robustly: 45-64% gains, 0 worsen), best hierarchy_purity = **0.465 < 0.7 threshold**. This is a **fundamental granularity/coverage limit** of legal_area labels at 174k, not a representation failure.

### 4. Dense 1200 Baselines — Extrapolation Risk

| Representation | Jurist Pairwise | Lang Dom | Both Gates | Boilerplate Resist | Jurivoc L0 NMI | Cross-Lang Recall |
|----------------|-----------------|----------|------------|-------------------|----------------|-------------------|
| `linear_metric_epoch4` | **0.6847** ✅ | **0.6805** ✅ | ✅ | -0.888 ❌ | 0.688 ✅ | 0.211 ✅ |
| `mahalanobis_metric_epoch4` | **0.6781** ✅ | **0.6843** ✅ | ✅ | -0.895 ❌ | 0.705 ✅ | 0.208 ✅ |
| `hybrid_stabilized_epoch1` | **0.6656** ✅ | **0.6704** ✅ | ✅ | -0.919 ❌ | 0.633 ✅ | 0.236 ✅ |
| `hybrid_v2_epoch3` | **0.5988** ✅ | **0.7115** ✅ | ✅ | -0.914 ❌ | 0.743 ✅ | 0.227 ✅ |
| `center_projected_64dim` | **0.5121** ✅ | **0.7664** ✅ | ✅ | -0.901 ❌ | 0.065 ❌ | 0.156 ❌ |
| `center_projected_768dim` | 0.4912 ❌ | 0.7738 ✅ | ❌ | -0.896 ❌ | 0.086 ❌ | 0.146 ❌ |
| `center_projected_128dim` | 0.4954 ❌ | 0.7725 ✅ | ❌ | -0.897 ❌ | 0.083 ❌ | 0.149 ❌ |

**Critical questions for 174k dense evaluation:**
1. Will jurist pairwise hold or collapse like TF-IDF (HNSW artifact)?
2. Will boilerplate resistance improve or stay at ~-0.9?
3. Will metric learning maintain Jurivoc L0 NMI > 0.6?

---

## Dense Embeddings 174k Progress

**Location:** `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`

| Year | Embeddings | Metadata | Status |
|------|------------|----------|--------|
| 2000 | 11.8 MB | 667 KB | ✅ Complete |
| 2001 | 0.97 MB | 88 KB | ✅ Complete |
| 2002 | 1.1 MB | 100 KB | ✅ Complete |
| 2003 | 0.96 MB | 88 KB | ✅ Complete |
| 2004 | 0.92 MB | 84 KB | ✅ Complete |
| 2005 | 0.90 MB | 82 KB | ✅ Complete |
| 2006 | 0.72 MB | 66 KB | ✅ Complete |
| 2007 | 0.97 MB | 79 KB | ✅ Complete |
| 2008 | 0.88 MB | 68 KB | ✅ Complete |
| 2009 | 0.75 MB | 75 KB | ✅ Complete |
| 2010 | 0.83 MB | 75 KB | ✅ Complete |
| 2011 | 0.88 MB | 80 KB | ✅ Complete |
| 2012 | 0.99 MB | 90 KB | ✅ Complete |
| 2013 | 0.83 MB | 76 KB | ✅ Complete |
| 2014-2025 | — | — | ❌ Failed (corpus artifact publication gap) |

**Total:** 14/27 years (52%) computed. Legal-distance pipeline blocked on corpus artifact publication to expected mount paths.

---

## Infrastructure Status

| Component | Status | Notes |
|-----------|--------|-------|
| HNSW Backend | ✅ OPERATIONAL | On GitHub runners |
| Scalable NN (sklearn fallback) | ✅ OPERATIONAL | Exact k-NN for n<10k |
| v25 Formal Suite | ✅ OPERATIONAL | Frozen protocol, HNSW-backed |
| Citation Heritage | ✅ FROZEN | 137,314 pairs ready |
| v17b Normalization | ✅ OPERATIONAL | Conservative cross-lingual map |
| Monitor Script | ✅ ACTIVE | check_count=66, watching for 11 awaited reps |
| 174k Metadata | ✅ AVAILABLE | 173,963 decisions, frozen row order |

---

## Blocker Analysis

### Primary Blocker: Legal-Distance 174k Dense Embeddings Not in Accepted State

**Root cause:** Corpus artifact publication gap — year-split normalized files and `metadata_174k.jsonl` exist in corpus workspace but **NOT at `/tmp/lex_accepted/corpus/...` and `/tmp/lex_accepted/evaluation/...` mount paths** where legal-distance expects them.

**Legal-distance status:** Year 2000 checkpoint only; years 2001-2025 failed missing upstream data.

**Impact:** Evaluation lane cannot proceed with 11 awaited representations until legal-distance delivers combined 174k embeddings in expected format.

### External Blocker: Jurist Human Study

**Status:** Framework ready, requires 5-10 Swiss jurists recruited by repository owner. Non-blocking for machine suite.

---

## Recommendations

### Immediate (When Dense Embeddings Land)
1. **FIX HNSW ARTIFACT** before evaluating dense embeddings:
   - Use exact k-NN for adversarial benchmarks (valid subset n≈1200 with known branch)
   - Or implement per-representation HNSW seeds with documented variance
   - Exact k-NN is preferred for scientific honesty

2. **Run full evaluation suite** on each new representation via monitor:
   - v25 formal suite (12 benchmarks)
   - Citation heritage (frozen 137k pairs)
   - v17b normalization (hierarchy-family)
   - Full corpus adversarial (exact k-NN for adversarial, HNSW for scale)

### Strategic
1. **Jurist pairwise collapse** is the central risk — 174k evaluation of dense embeddings will determine if learned metrics generalize or suffer same HNSW artifact.

2. **Boilerplate resistance failure** for ALL dense representations at 1200 scale suggests learned metrics may overfit procedural patterns. Must validate at 174k.

3. **Hierarchy coherence ceiling** (0.47 max) appears fundamental — adjust threshold expectations or develop finer-grained legal taxonomies.

---

## Next Actions

1. **Monitor active** — `monitor_and_evaluate_174k.py` watching for 11 awaited representations (check_count=66)
2. **Legal-distance 174k pipeline** — blocked on corpus artifact publication to expected mount paths
3. **When dense embeddings arrive** — run full evaluation suite automatically via monitor (with HNSW artifact fix)
4. **No further same-question cycles justified** for TF-IDF family — all machine-executable sub-questions complete

---

## Provenance

- **Frozen Protocol:** `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json`
- **Frozen Harness:** `evaluation/evaluation_v3_harness.py` (v3, seed=42)
- **Frozen Sample:** `evaluation/data/174k/metadata_174k.json` (173,963 decisions from pinned parquet)
- **Citation Pairs:** `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` (built from 2,019/2,105 resolved)
- **Config Hashes:** 
  - Formal suite: `4323f833fa72366a`
  - Adversarial harness: `4047da047fb339c1`
- **Source Run ID:** `eval_v27_174k_tfidf_and_dense1200_36097406309`
- **Monitor State:** `evaluation/state/monitor_174k_state.json` (updated check_count=66)

---

**Recommendation:** `BLOCKED_ON_DEPENDENCIES` — continue_recommended=true (monitor for dense embeddings), but no additional same-question cycles justified for TF-IDF family. Factory Director to decide successor question when dense embeddings land.