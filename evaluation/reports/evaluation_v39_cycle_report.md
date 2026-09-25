# Evaluation Lane v39 Cycle Report

**Date:** 2026-09-25T09:05:00Z  
**GitHub Run:** 36115527958  
**Factory Direction:** v27  
**Lane Status:** BLOCKED_ON_DEPENDENCIES (TF-IDF family complete, awaiting legal-distance 174k dense embeddings)

---

## Summary

This cycle executed real evaluation work on the **evaluation lane's machine-executable mandate**: running the frozen 12-benchmark formal suite, citation_heritage benchmark, and v17b label normalization test at 174k scale on production representations as they become available.

### Key Accomplishments

1. **Full Corpus Adversarial Evaluation** on cited_outcome_hybrid_0.7 (production default) at 173,963 decisions: **PASS** both frozen adversarial gates
   - Language Dominance: 0.6254 (< 0.85 threshold) ✓
   - Jurist Pairwise Preference: 0.6675 (> 0.5 threshold) ✓
   - Backend: HNSW (hnswlib), duration: 99.6s

2. **v25 Formal Suite (12-benchmark + citation_heritage + v17b)** on cited_outcome_hybrid_0.7 at 174k: **6 PASS / 5 FAIL / 1 SKIP**
   - PASS: citation_heritage (AUC=0.9605), adversarial_falsification, multilingual_invariance, cross_language_pairs, collapse_check, zoom_coherence
   - FAIL: branch_knn, tf_metadata_human_indexing, temporal_stability, hierarchy_coherence, legal_area_clustering
   - SKIP: boilerplate_resistance_real_corpus (corpus full_text unavailable in this environment)

3. **Citation Heritage Benchmark** validated on 137,314 frozen pairs: **PASS**
   - cited_outcome_hybrid_0.7: AUC=0.9605, nn_citation_rate@10=0.490
   - Threshold: AUC ≥ 0.65

4. **v17b Label Normalization** on cited_outcome_hybrid_0.7 at 174k: **PARTIALLY GENERALIZES**
   - Hierarchy purity: 0.1278 → 0.1970 (**+54.1% gain**)
   - Hierarchy NMI: 0.1078 → 0.0962 (**-10.8% worsening**, exceeds ≤10% rule)
   - Zoom coherence: 26.9% → 28.9% improvement
   - Confirms v17b label normalization yields purity gains but NMI worsening for citation-based representations at 174k scale

5. **Partial Dense Embedding Evaluation** on available legal-distance checkpoints
   - Concatenated 14 years (2000-2013) of center_projected_768dim checkpoints: 7,652 decisions
   - Evaluation: **FAIL** both adversarial gates (LangDom=0.9961, Jurist=0.0062)
   - Consistent with v3 harness finding: 768-dim center_projected fails jurist gate
   - Validates year-split checkpoint embeddings are loadable and evaluable

---

## Infrastructure Verification (All Operational)

| Component | Status | Details |
|-----------|--------|---------|
| `run_full_corpus_evaluation.py` | ✅ OPERATIONAL | Config hash 4047da047fb339c1 matches frozen v3 harness exactly |
| `v25_174k_formal_suite` runner | ✅ OPERATIONAL | Config hash 4323f833fa72366a, all 8 TF-IDF reps previously evaluated |
| `scalable_nn.py` HNSW backend | ✅ OPERATIONAL | hnswlib confirmed at 174k scale |
| `validate_citation_heritage_174k.py` | ✅ OPERATIONAL | 137,314 frozen pairs, 95.9% citation resolution |
| v17b label normalization test | ✅ OPERATIONAL | 213→163 labels, 32 cross-lingual canonical concepts |
| `monitor_and_evaluate_174k.py` | ✅ ENHANCED | Auto-runs full v25 protocol for new representations via `run_formal_suite_v25()` |

---

## Legal-Distance Lane Dependency Status

**BLOCKED ON:** 174k dense embeddings (center_projected, metric learning, hybrid objectives, citation roles, linear hybrids)

- **Checkpoints available:** 14/26 years (2000-2013) in `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`
- **Missing:** Years 2014-2025 (failures likely due to 65-min job ceiling on GitHub runners)
- **Final concatenated embeddings:** NOT YET PRODUCED (pending completion of all years)
- **Legal-distance pipeline:** RUN (gh run 36096850301 IN_PROGRESS for year-split dense embeddings)

---

## TF-IDF Family: EVALUATION COMPLETE

All 8 TF-IDF representations fully evaluated at 174k scale against frozen v25 protocol:

| Representation | 12-Benchmark Pass | Citation Heritage AUC | v17b Normalization (hierarchy NMI) |
|----------------|-------------------|----------------------|-------------------------------------|
| full_text_tfidf_light | 7/12 | 0.8439 | -27.6% |
| regeste_full_text_hybrid_0.5 | 7/12 | 0.8505 | -27.6% |
| regeste_full_text_hybrid_0.7 | 7/12 | 0.8650 | -27.6% |
| cited_decisions_tfidf | 6/12 | **0.9731** | -3.1% (within ≤10% rule) |
| cited_outcome_hybrid_0.5 | 6/12 | 0.9193 | -9.6% (within ≤10% rule) |
| cited_outcome_hybrid_0.7 | 6/12 | 0.9605 | **-10.8%** (violates ≤10% rule) |
| regeste_tfidf | 5/12 | 0.4865 (FAIL) | +0.0% (within ≤10% rule) |
| outcome_tfidf | 3/12 | 0.7204 | -13.1% |

**Production Default Confirmed:** `cited_outcome_hybrid_0.7`
- Zero-shot TF-IDF, no GPU required
- Passes both adversarial gates at 174k
- Citation heritage AUC=0.9605, nn_citation_rate@10=0.490

---

## Universal Benchmark Patterns (Confirmed at 174k)

### Universal PASS (all representations)
- adversarial_falsification (citation-based reps)
- multilingual_invariance (citation-based reps)
- cross_language_pairs (citation-based reps)
- collapse_check

### Universal FAIL (all representations)
- hierarchy_coherence (purity 0.08-0.47 < 0.7) — corpus/label limitation
- legal_area_clustering (purity 0.003-0.08 < 0.5) — corpus/label limitation
- temporal_stability (high variance across year splits)

### Conditional PASS
- branch_knn / tf_metadata_human_indexing: PASS only for full-text/regeste reps
- boilerplate_resistance_real_corpus: SKIP (corpus unavailable) or FAIL (correlation ~0)
- zoom_coherence: PASS for citation-based reps, FAIL for regeste/outcome reps

---

## Next Steps

1. **No additional same-question cycle justified for TF-IDF family** (continue_recommended=false)
2. **Await legal-distance 174k dense embeddings** — monitor active (58 checks), will auto-evaluate via `run_formal_suite_v25()` when they land
3. **Jurist human study remains BLOCKED** — external dependency: 5-10 Swiss jurists recruitment by repository owner; framework ready

---

## Evidence Artifacts Generated This Cycle

- `evaluation/results/partial_174k_center_projected/full_corpus_evaluation_results_worker0.json` — partial center_projected_768dim evaluation
- `evaluation/results/full_174k_tfidf_verification/full_corpus_evaluation_results_worker0.json` — full 174k cited_outcome_hybrid_0.7 evaluation
- `results/evaluation/v25_174k_formal_suite/results/cited_outcome_hybrid_0.7.json` — v25 formal suite results
- `results/evaluation/v25_174k_citation_heritage/cited_outcome_hybrid_0.7.json` — dedicated citation heritage
- `results/evaluation/v25_174k_v17b/cited_outcome_hybrid_0.7.json` — v17b label normalization comparison
- `evaluation/state/evaluation.json` — updated with v39 cycle verification (verification_count: 39)

---

## Configuration Hashes (Frozen)

- **v3 Harness:** `4047da047fb339c1` (matches original frozen harness exactly)
- **v16/v25 Suite:** `4323f833fa72366a` (frozen thresholds unchanged since v16)
- **Global Seed:** 42 (all evaluations)

All evaluations executed with frozen thresholds, no tuning after observing results.