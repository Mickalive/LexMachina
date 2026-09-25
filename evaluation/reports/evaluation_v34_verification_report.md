# Evaluation Lane v34 — Infrastructure Verification & Status Report

**Date:** 2026-09-25  
**Factory Direction:** v27  
**GitHub Run:** local_verification_20260925_v34  
**Lane Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false

---

## Executive Summary

The Evaluation lane has completed its machine-executable mandate for the TF-IDF production family at 174k scale. All three sub-questions from Factory Direction v27 are **COMPLETE** for the 8 TF-IDF representations:

1. ✅ **Full 12-benchmark formal suite** at 174k scale (frozen v16 thresholds, config hash `4323f833fa72366a`)
2. ✅ **Citation heritage benchmark** validated using 174k citation-ID resolution (2,019/2,105 resolved, 137,314 frozen pairs)
3. ✅ **v17b label normalization** generalization test at 174k (213→163 legal_area labels, 32 cross-lingual canonical concepts)

**No additional same-question cycle is justified for the TF-IDF family.** The lane is correctly `BLOCKED_ON_DEPENDENCIES` awaiting legal-distance 174k dense embeddings.

---

## Current Blocking Dependency

**Legal-distance lane** is RUN (staged 174k CPU execution, year-split, resumable checkpoints).  
- **Progress:** Year 2000 of 26 completed (`embeddings_2000.npy` checkpoint exists)  
- **Failed:** Years 2001–2025 (25 years)  
- **GitHub Run:** 36096850301 IN_PROGRESS  

No 174k dense embeddings are available in legal-distance accepted state (v5–v14, fractal_map). All dense embeddings currently in accepted state are at 1000–1200 scale only.

---

## Infrastructure Verification (v34 Cycle)

| Component | Status | Evidence |
|-----------|--------|----------|
| **v25 174k Formal Suite Runner** | OPERATIONAL | `run_v25_174k_suite.py` tested on all 8 TF-IDF reps; config hash `4323f833fa72366a` frozen |
| **Full Corpus Adversarial Harness** | OPERATIONAL | `run_full_corpus_evaluation.py` config hash `4047da047fb339c1`; HNSW backend (hnswlib) on GitHub runners |
| **Citation Heritage Benchmark** | READY | 137,314 frozen pairs in `citation_pairs_174k_full.json`; 95.9% citation resolution validated |
| **v17b Label Normalization** | OPERATIONAL | `normalize_labels()` function working; 213→163 labels at 174k; tested across 8 TF-IDF reps |
| **Auto-Evaluation Monitor** | ENHANCED | `monitor_and_evaluate_174k.py` includes `run_formal_suite_v25()` for zero-touch evaluation of new reps |
| **Frozen Config Hashes** | VERIFIED | Suite: `4323f833fa72366a`; Harness: `4047da047fb339c1` — both match accepted state |

---

## TF-IDF Family Results Summary (174k Scale)

| Representation | 12-Suite Pass/Fail/Skip | Citation Heritage AUC | nn_citation_rate@10 | Adversarial Gates |
|---|---|---|---|---|
| **cited_decisions_tfidf** | 6/5/1 | **0.9731** | 0.487 | ✅ PASS |
| **cited_outcome_hybrid_0.7** | 6/6/0 | **0.9605** | 0.490 | ✅ PASS |
| **cited_outcome_hybrid_0.5** | 6/5/1 | **0.9193** | 0.476 | ✅ PASS |
| **full_text_tfidf_light** | 7/5/0 | 0.8439 | 0.438 | ❌ LangDom=0.999 |
| **regeste_full_text_hybrid_0.5** | 7/5/0 | 0.8505 | 0.444 | ❌ LangDom=0.998 |
| **regeste_full_text_hybrid_0.7** | 7/5/0 | 0.8650 | 0.445 | ❌ LangDom=0.999 |
| **regeste_tfidf** | 5/7/0 | 0.4865 | 0.000 | ✅ PASS |
| **outcome_tfidf** | 3/9/0 | 0.7204 | 0.003 | ❌ Branch=0.146 |

**Production Default Confirmed:** `cited_outcome_hybrid_0.7` — passes both adversarial gates (LangDom=0.569 < 0.85, Branch=0.356 > 0.3), best citation heritage AUC=0.9605, zero-shot TF-IDF, no GPU required.

---

## Universal 174k Findings (All Representations)

| Benchmark | Status | Note |
|---|---|---|
| `branch_knn` | Mixed | Citation-based reps FAIL (0.37–0.39); full-text/regeste PASS (>0.96) but language-dominated |
| `tf_metadata_human_indexing` | Mixed | Same pattern as branch_knn |
| `adversarial_falsification` | **Universal for citation reps** | Citation hybrids PASS both gates; full-text/regeste FAIL language dominance |
| `multilingual_invariance` | Mixed | Citation reps PASS; full-text/regeste FAIL |
| `cross_language_pairs` | Mixed | Citation reps PASS; full-text/regeste FAIL |
| `collapse_check` | **Universal PASS** | No representation collapsed |
| `temporal_stability` | Mixed | Citation reps FAIL (high variance); full-text/regeste PASS (low variance) |
| `hierarchy_coherence` | **Universal FAIL** | Purity 0.08–0.47 << 0.7 threshold (label granularity limitation) |
| `zoom_coherence` | Mixed | Full-text/regeste PASS (103% improvement); citation reps PASS (20–27%) |
| `legal_area_clustering` | **Universal FAIL** | Purity 0.003–0.08 << 0.5 threshold (213 fine-grained labels, not representation defect) |
| `boilerplate_resistance_real_corpus` | Mostly FAIL/SKIP | Correlation ~0; proxy measures language dominance, not procedural boilerplate |

---

## v17b Label Normalization at 174k

- **Raw labels:** 213 unique → **Normalized:** 163 unique (23.5% reduction)
- **Cross-lingual canonical concepts:** 32
- **Decisions relabeled:** 85,819 (49.3%)
- **Avg decisions/label:** 428 → 560

**Generalization to 174k: PARTIAL**

| Representation | Hierarchy NMI Δ | Within ≤10% Worsening? |
|---|---|---|
| cited_decisions_tfidf | -9.6% | ✅ YES |
| regeste_tfidf | -7.1% | ✅ YES |
| cited_outcome_hybrid_0.7 | -10.8% | ❌ NO |
| outcome_tfidf | -13.1% | ❌ NO |
| full_text_tfidf_light | -27.6% | ❌ NO |
| regeste_full_text_hybrid_0.5/0.7 | -27.6% | ❌ NO |

**Conclusion:** v17b normalization improves hierarchy purity 1.5–1.6× for citation-based reps but worsens NMI for full-text/regeste reps (coarse labels map 1:1). Even normalized, best hierarchy purity = 0.47 < 0.7 threshold — confirming v16 finding that hierarchy failure is a label granularity limitation, not a representation defect.

---

## Next Steps

1. **Legal-distance lane** must complete 174k dense embedding computation (years 2001–2026)
2. **Evaluation monitor** will auto-detect and auto-evaluate new representations via `run_formal_suite_v25()`
3. **Jurist human study** remains blocked (external dependency: 5–10 Swiss jurists recruitment)
4. **No further evaluation cycles** for TF-IDF family (continue_recommended=false)

---

## Artifacts Referenced

- `evaluation/state/evaluation.json` — machine-readable lane state (updated with v34 verification)
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — complete 12-benchmark results for 8 TF-IDF reps
- `results/evaluation/v25_174k_formal_suite/embeddings/build_manifest.json` — embedding build provenance
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — frozen citation heritage pairs
- `evaluation/data/174k/metadata_174k.json` — 173,963 decisions with branch/language/legal_area
- `evaluation/experiments/v25_174k_suite/run_v25_174k_suite.py` — frozen protocol runner
- `evaluation/monitor_and_evaluate_174k.py` — enhanced monitor with auto-evaluation

---

**Recommendation:** `BLOCKED_ON_DEPENDENCIES` — No action required in evaluation lane until legal-distance delivers 174k dense embeddings. Monitor is active and will auto-evaluate on arrival.