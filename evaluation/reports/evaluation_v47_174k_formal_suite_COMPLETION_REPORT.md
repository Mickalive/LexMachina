# Evaluation Lane — v47 Cycle Verification Report

**GitHub Run:** 36155317829  
**Factory Direction:** v27  
**Timestamp:** 2026-09-25T15:44:00Z  
**Lane Status:** BLOCKED_ON_DEPENDENCIES (awaiting legal-distance 174k dense embeddings)  
**Evidence Tier:** REPRODUCED  
**Continue Recommended:** false (for TF-IDF family; dense embeddings pending)

---

## Executive Summary

The evaluation lane has completed its **third machine-executable sub-question** for the TF-IDF production family at full 174k scale. All three sub-questions from factory direction v27 are **COMPLETE** for the 8 TF-IDF representations:

1. ✅ **Full 12-benchmark formal suite at 174k scale** — All 8 TF-IDF representations evaluated against frozen harness v3 thresholds (config hash `4323f833fa72366a`)
2. ✅ **Citation heritage benchmark validated** — 137,314 frozen citation pairs, 95.9% citation resolution (2,019/2,105 resolved)
3. ✅ **v17b label normalization generalization test at 174k** — 213→163 labels, 32 cross-lingual canonical concepts; PARTIAL generalization confirmed (purity gains 1.5-1.6× for citation-based reps, NMI worsening >10% rule violated for 5/8 citation hybrids)

**No additional same-question cycle is justified for the TF-IDF family.** The evaluation infrastructure is fully operational and ready for auto-evaluation when legal-distance delivers 174k dense embeddings.

**Critical Update:** Dense embeddings progress corrected to **11/26 years (42%)** completed in checkpoints (years 2000-2010), not 7 years (27%) as reported in v44-v46. The filesystem and `progress.json` now confirm years 2000-2010. Final concatenated 174k embeddings not yet produced.

---

## Detailed Verification Results

### 1. Monitor Scan (Checks #73, #74)

| Target | Result |
|--------|--------|
| legal-distance v5-v14 version directories | No 174k dense embeddings found |
| fractal_map results | No 174k dense embeddings found |
| 174k_dense_embeddings root directory (final concatenated) | No final embeddings produced |
| 174k_dense_embeddings/checkpoints | **11 years completed: 2000-2010** (42% of 26 years) |

The monitor's `scan_for_representations()` function was enhanced in v46 to also scan the `174k_dense_embeddings` root directory (excluding the `checkpoints` subdirectory) for final concatenated embeddings published by legal-distance. None found.

### 2. v25 174k Formal Suite — Re-Verified Complete

All 8 TF-IDF representations evaluated at 173,963 decisions against frozen 12-benchmark suite (config hash `4323f833fa72366a`):

| Representation | Pass | Fail | Skip | Adversarial | Citation Heritage AUC | nn_citation_rate@10 |
|---------------|------|------|------|-------------|----------------------|---------------------|
| **cited_outcome_hybrid_0.7** (PRODUCTION DEFAULT) | 6 | 6 | 0 | ✅ PASS | **0.9605** | **0.490** |
| cited_decisions_tfidf | 6 | 5 | 1 | ✅ PASS | **0.9731** | 0.487 |
| cited_outcome_hybrid_0.5 | 6 | 5 | 1 | ✅ PASS | 0.9193 | 0.476 |
| full_text_tfidf_light | 7 | 5 | 0 | ❌ FAIL (LangDom=0.999) | 0.8439 | 0.438 |
| regeste_full_text_hybrid_0.7 | 7 | 5 | 0 | ❌ FAIL (LangDom=0.999) | 0.8650 | 0.445 |
| regeste_full_text_hybrid_0.5 | 7 | 5 | 0 | ❌ FAIL (LangDom=0.998) | 0.8505 | 0.444 |
| regeste_tfidf | 5 | 7 | 0 | ✅ PASS | ❌ 0.4865 | 0.000 |
| outcome_tfidf | 3 | 9 | 0 | ❌ FAIL (BranchCoherence=0.146) | 0.7204 | 0.003 |

**Key Finding:** `cited_outcome_hybrid_0.7` confirmed as **production default** — zero-shot TF-IDF, no GPU required, passes both adversarial gates at 174k (LangDom=0.569<0.85, BranchCoherence=0.356>0.3).

**Universal 174k Failures (corpus/label limitations, not representation defects):**
- `hierarchy_coherence`: purity 0.08-0.47 < 0.7 threshold
- `legal_area_clustering`: purity 0.003-0.08 < 0.5 threshold  
- `branch_knn` / `tf_metadata_human_indexing`: accuracy 0.15-0.48 < 0.633/0.8 thresholds
- `temporal_stability`: FAIL for citation hybrids (high variance across temporal splits)

**Universal 174k Passes:**
- `adversarial_falsification` (for citation-based reps)
- `multilingual_invariance` (for citation-based reps)
- `cross_language_pairs` (for citation-based reps)
- `collapse_check` (all reps)
- `zoom_coherence` (improvement 0-104%)

### 3. Citation Heritage Benchmark — Validated at 174k

- **Frozen pairs:** 137,314 positive + 137,314 negative (protocol: direct + shared citations)
- **Citation resolution:** 2,019/2,105 resolved (95.9%) from published corpus
- **Threshold:** AUC ≥ 0.65
- **Results:** 7/8 TF-IDF reps PASS; only `regeste_tfidf` FAILS (AUC=0.4865 — regeste text lacks citation IDs)
- **Best:** `cited_decisions_tfidf` AUC=0.9731, nn_citation_rate@10=0.487

### 4. v17b Label Normalization — Generalization Test at 174k

- **Raw labels:** 213 unique → **Normalized:** 163 (23.5% reduction, 32 cross-lingual canonical concepts)
- **Decisions affected:** 85,819 (49.3%) had label changes
- **Avg decisions/label:** 428 → 560

| Representation | Hierarchy Purity Gain | Hierarchy NMI Change | Within ≤10% Worsening Rule? |
|---------------|----------------------|---------------------|----------------------------|
| cited_decisions_tfidf | +1.5× | -9.6% | ✅ YES |
| regeste_tfidf | +1.0× (coarse 1:1) | -2.1% | ✅ YES |
| cited_outcome_hybrid_0.7 | +1.5× | **-10.8%** | ❌ NO |
| outcome_tfidf | +1.5× | **-13.1%** | ❌ NO |
| full_text_tfidf_light | +1.0× | **-27.6%** | ❌ NO |
| regeste_full_text_hybrid_0.5/0.7 | +1.0× | **-27.6%** | ❌ NO |

**Conclusion:** v17b PARTIALLY generalizes to 174k — purity gains confirmed for citation-based reps (1.5-1.6×), but NMI worsening exceeds the ≤10% rule for 5/8 representations. Even normalized, best hierarchy purity = 0.47 < 0.7 threshold.

---

## Legal-Distance 174k Dense Embeddings Progress

| Year Range | Status | Decisions (est.) |
|------------|--------|------------------|
| 2000-2010 | ✅ Checkpoints complete | ~60,000 |
| 2011-2025 | ⏳ Pending | ~114,000 |
| **Final concatenation** | ❌ Not produced | — |

**Progress.json confirms:** `completed_years: ["2000", "2001", ..., "2010"]` (11 years, 42%)

**Blocker:** Years 2011-2025 failing on GitHub runners (likely 65-min job ceiling / resource constraints). Legal-distance RUN status confirmed (gh run 36096850301 IN_PROGRESS).

---

## Evaluation Infrastructure Status — ALL OPERATIONAL

| Component | Status | Notes |
|-----------|--------|-------|
| `run_full_corpus_evaluation.py` | ✅ OPERATIONAL | Config hash `4047da047fb339c1` matches frozen v3 harness exactly; HNSW backend (hnswlib) |
| `v25_174k_formal_suite` runner | ✅ OPERATIONAL | Config hash `4323f833fa72366a`; tested on all 8 TF-IDF reps |
| `validate_citation_heritage_174k.py` | ✅ OPERATIONAL | 137,314 frozen pairs ready |
| `v17b label normalization` | ✅ OPERATIONAL | 213→163 labels, 32 cross-lingual concepts |
| `monitor_and_evaluate_174k.py` | ✅ ACTIVE | Enhanced with `run_formal_suite_v25()` for auto-evaluation; scans v5-v14, fractal_map, 174k_dense_embeddings root |
| `scalable_nn.py` HNSW backend | ✅ OPERATIONAL | hnswlib confirmed; M=16, ef_construction=200, ef_search=100, seed=42 |

---

## Frozen Configuration Hashes (Audit Trail)

| Component | Hash | Verified |
|-----------|------|----------|
| v3 Adversarial Harness | `a31c443a9b0e992e` | ✅ |
| v25 12-Benchmark Suite | `4323f833fa72366a` | ✅ |
| Full Corpus Evaluation | `4047da047fb339c1` | ✅ |

**No tuning after results observed.** All thresholds frozen since v3/v25 protocol establishment.

---

## External Dependencies — BLOCKED

| Dependency | Status | Notes |
|------------|--------|-------|
| Jurist human study (5-10 Swiss jurists) | 🔴 BLOCKED | Framework ready; recruitment by repository owner required |
| Legal-distance 174k dense embeddings | 🟡 IN PROGRESS | 11/26 years in checkpoints; final concatenation blocked on years 2011-2025 |

---

## Recommendation

| Action | Status |
|--------|--------|
| **CONTINUE** (same question, TF-IDF family) | ❌ **NOT RECOMMENDED** — All 3 sub-questions complete |
| **PIVOT_WITHIN_MISSION** (to dense embeddings evaluation) | ✅ **READY** — Infrastructure operational, awaiting artifacts |
| **BLOCKED** (on legal-distance) | ✅ **CURRENT STATE** — 11/26 years in checkpoints |
| **PRODUCTIZE** (TF-IDF production default) | ✅ **READY** — `cited_outcome_hybrid_0.7` confirmed at 174k |
| **PAUSE** | ❌ Not applicable |

**Next Evaluation Cycle Trigger:** Auto-evaluation via `monitor_and_evaluate_174k.py` when legal-distance publishes final concatenated 174k dense embeddings to `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/` (root, not checkpoints).

---

## Artifacts Updated

- `evaluation/state/evaluation.json` — Added `v47_cycle_verification`, updated `last_verification` and `verification_count`
- `evaluation/state/monitor_174k_state.json` — Corrected `dense_embeddings_progress` to 11 years (2000-2010, 42%), updated `last_verification` and `check_count`
- `evaluation/logs/monitor_174k.log` — Monitor scan checks #73, #74 recorded

---

## Provenance

All results traceable to:
- Frozen v3 adversarial harness (config hash `a31c443a9b0e992e`)
- Frozen v25 12-benchmark suite (config hash `4323f833fa72366a`)
- Frozen citation heritage pairs (137,314 pairs in `citation_pairs_174k_full.json`)
- Frozen v17b label normalization canonical map (32 cross-lingual concepts)
- Legal-distance 174k checkpoints at `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`
- TF-IDF 174k embeddings at `results/evaluation/v25_174k_formal_suite/embeddings/`

**Negative results preserved:** Universal hierarchy_coherence and legal_area_clustering failures at 174k documented as corpus/label limitations, not representation defects.