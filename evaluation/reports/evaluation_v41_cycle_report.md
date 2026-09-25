# Evaluation Lane — Cycle v41 Verification Report

**Factory Direction Version:** 27  
**GitHub Run:** 36119702329  
**Timestamp:** 2026-09-25T09:43:00Z  
**Monitor Check:** #62

---

## Executive Summary

The evaluation lane remains **BLOCKED_ON_DEPENDENCIES** awaiting 174k dense embeddings from the legal-distance lane. All three machine-executable sub-questions for the TF-IDF production family are **COMPLETE** at 174k scale. Evaluation infrastructure is fully operational and ready for auto-evaluation when dense embeddings land.

---

## Verification Results

### 1. Monitor Scan (Check #62)
- **Scan executed:** `monitor_and_evaluate_174k.py` 
- **Result:** No 174k dense embeddings detected in legal-distance accepted state
- **Locations scanned:** v5-v14 version directories, fractal_map results, 174k_dense_embeddings/checkpoints
- **Checkpoints status:** 14 years completed (2000-2013, 7,652 decisions, ~4.4% of 173,963); years 2014-2025 failing (GitHub run 36096850301 IN_PROGRESS)

### 2. Full Corpus Adversarial Harness (run_full_corpus_evaluation.py)
- **Config hash:** `4047da047fb339c1` ✓ (matches frozen v3 harness exactly)
- **HNSW backend:** OPERATIONAL (hnswlib available, EXACT_NN_THRESHOLD=10,000)
- **Scalable NN module:** OPERATIONAL with sklearn exact fallback
- **Production default validated:** `cited_outcome_hybrid_0.7` passes both adversarial gates at 174k (LangDom=0.569<0.85, Jurist=0.6675>0.5)

### 3. v25 174k Formal Suite Runner
- **Config hash:** `4323f833fa72366a` ✓ (frozen v16 thresholds)
- **Status:** CONFIRMED OPERATIONAL at 174k scale
- **TF-IDF family:** All 8 representations fully evaluated (suite_summary.json: 8 entries)
- **Protocol:** 12-benchmark suite + citation_heritage + v17b label normalization

### 4. Citation Heritage Benchmark Infrastructure
- **Pairs file:** `citation_pairs_174k_full.json` (137,314 frozen positive + negative pairs)
- **Citation resolution:** 95.9% (2,019/2,105 resolved citations from published 174k map)
- **Status:** VALIDATED and ready

### 5. v17b Label Normalization Test Infrastructure
- **Label normalization:** 213 raw → 163 normalized legal_area labels (23.5% reduction)
- **Cross-lingual canonical concepts:** 32
- **Normalization function:** `normalize_labels()` working, conservative cross-lingual canonical map frozen
- **Status:** OPERATIONAL at 174k

### 6. Monitor Enhancement
- **`run_formal_suite_v25()`** function active: copies new embeddings to v25 suite directory and executes full frozen protocol (12-benchmark + citation_heritage + v17b)
- **`execute_evaluation_suite()`** updated to run BOTH full corpus adversarial evaluation AND v25 formal suite for each new representation

### 7. Frozen Config Hashes Verified
| Component | Hash |
|-----------|------|
| v16 Benchmark Suite | `4323f833fa72366a` |
| Full Corpus Harness | `4047da047fb339c1` |
| v3 Harness (reference) | `a31c443a9b0e992e` |

---

## Legal-Distance Pipeline Progress

| Metric | Status |
|--------|--------|
| Years completed | 14/26 (2000-2013) |
| Decisions embedded | 7,652 / 173,963 (~4.4%) |
| Checkpoint files | `embeddings_2000.npy` through `embeddings_2013.npy` + metadata |
| Years failing | 2014-2025 (likely 65-min job ceiling / resource constraints) |
| GitHub run | 36096850301 IN_PROGRESS |

**Note:** The year-split checkpoints are in a subdirectory (`checkpoints/`) and are not detected by the monitor (which expects final concatenated embeddings in a 174k-named directory at version-root level).

---

## TF-IDF Family — 174k Evaluation Complete

All three machine-executable sub-questions from factory direction v27 **COMPLETE**:

1. ✅ **Full 12-benchmark formal suite** at 174k scale on all 8 TF-IDF representations (frozen thresholds, config hash 4323f833fa72366a)
2. ✅ **Citation heritage benchmark** validated using published 174k citation-ID resolution (137,314 pairs, 95.9% resolution)
3. ✅ **v17b label normalization generalization** tested at 174k: PARTIAL (purity gains 1.5-1.6x for citation-based reps; NMI worsening >10% rule violated for 5/8 citation hybrids)

**No additional same-question cycle justified** (`continue_recommended=false`).

---

## Production Default Confirmed

| Representation | Type | Adversarial Gates | Citation Heritage | Notes |
|----------------|------|-------------------|-------------------|-------|
| `cited_outcome_hybrid_0.7` | Zero-shot TF-IDF | **PASS** (LangDom=0.569, Jurist=0.6675) | AUC=0.9605, nn@10=0.490 | **PRODUCTION DEFAULT** — no GPU required |

---

## Blocked Items

| Item | Blocker | Status |
|------|---------|--------|
| 174k dense embeddings evaluation | Legal-distance year-split computation incomplete (14/26 years) | **BLOCKED** |
| Jurist human study | External: 5-10 Swiss jurists recruitment by repository owner | **BLOCKED** (framework ready) |

---

## Recommendation

**CONTINUE monitoring** — No code changes needed. Evaluation infrastructure is production-ready. The monitor script (check #62) will auto-detect and auto-evaluate 174k dense embeddings when legal-distance lane produces final concatenated artifacts.

The legal-distance lane should prioritize completing years 2014-2025 (likely requires addressing 65-minute GitHub Actions job ceiling via chunking or resource optimization).

---

## Evidence References

- `evaluation/state/evaluation.json` — Machine-readable lane state (v41_cycle_verification)
- `evaluation/state/monitor_174k_state.json` — Monitor state (check_count=62)
- `evaluation/monitor_and_evaluate_174k.py` — Auto-evaluation monitor (enhanced with v25 formal suite)
- `evaluation/run_full_corpus_evaluation.py` — Full corpus adversarial harness (config hash verified)
- `evaluation/experiments/v25_174k_suite/run_v25_174k_suite.py` — Formal suite runner (frozen protocol)
- `evaluation/validate_citation_heritage_174k.py` — Citation heritage benchmark
- `evaluation/experiments/run_v17b_label_normalization_all_reps.py` — v17b label normalization test
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — TF-IDF family suite summary

---

*Report generated per Research Protocol §8: "Write machine-readable lane state plus human-readable report."*