# Evaluation Lane — 174k Formal Suite Final Report (v27)

**Status**: BLOCKED_ON_DEPENDENCIES (TF-IDF family COMPLETE, dense embeddings awaited)  
**Evidence Tier**: REPRODUCED  
**Config Hash**: `4323f833fa72366a` (frozen v16 spec)  
**Corpus**: 173,963 decisions  

---

## Results Summary

### Sub-question 1: 12-Benchmark Formal Suite ✅ COMPLETE
8 TF-IDF representations evaluated at 174k with HNSW (M=16, ef=200/100).

| Rep | Pass | Fail | Skip | Best (6/12) |
|-----|------|------|------|-------------|
| cited_decisions_tfidf | 6 | 5 | 1 | ✅ citation_heritage, adversarial, multilingual, cross_lang, collapse, zoom |
| cited_outcome_hybrid_0.5 | 6 | 5 | 1 | |
| cited_outcome_hybrid_0.7 | 6 | 6 | 0 | |
| full_text_tfidf_light | 7 | 5 | 0 | FAIL: adversarial (lang_dom=0.999) |
| outcome_tfidf | 3 | 9 | 0 | |
| regeste_tfidf | 5 | 7 | 0 | FAIL: citation_heritage (0.486) |
| regeste_full_text_hybrid_0.5 | 7 | 5 | 0 | FAIL: adversarial (lang_dom=0.998) |
| regeste_full_text_hybrid_0.7 | 7 | 5 | 0 | FAIL: adversarial (lang_dom=0.999) |

**Fundamental tradeoff persists**: Citation-based reps pass adversarial/citation but fail branch_knn/hierarchy; text-based reps pass branch_knn/temporal but fail adversarial/multilingual. **ALL fail hierarchy_coherence (max 0.465) and legal_area_clustering (max 0.08).**

### Sub-question 2: Citation Heritage ✅ COMPLETE
Frozen 137,314-pair pool (seed=42, 2,019/2,105 resolved).

| Rep | AUC | nn@10 | Status |
|-----|-----|-------|--------|
| cited_decisions_tfidf | **0.973** | **0.487** | ✅ |
| cited_outcome_hybrid_0.7 | 0.960 | 0.490 | ✅ |
| cited_outcome_hybrid_0.5 | 0.919 | 0.476 | ✅ |
| regeste_full_text_hybrid_0.7 | 0.865 | 0.445 | ✅ |
| regeste_full_text_hybrid_0.5 | 0.850 | 0.444 | ✅ |
| full_text_tfidf_light | 0.844 | 0.438 | ✅ |
| outcome_tfidf | 0.720 | 0.003 | ✅ |
| regeste_tfidf | 0.486 | 0.000 | ❌ |

Citation signals dominate. Text reps pass AUC but nn_citation_rate≈0.

### Sub-question 3: v17b Normalization ⚠️ NOT UNIFORMLY CONFIRMED
214→164 labels (49.3% changed). Frozen rule: no metric worsens >10%.

| Rep | Uniformity | Purity Δ | NMI Δ |
|-----|------------|----------|-------|
| cited_decisions_tfidf | ✅ PASS | +52% | -6% |
| regeste_tfidf | ✅ PASS | +64% | 0% |
| cited_outcome_hybrid_0.5 | ❌ FAIL | +53% | -10% |
| cited_outcome_hybrid_0.7 | ❌ FAIL | +54% | -11% |
| full_text_tfidf_light | ❌ FAIL | 0% | -28% |
| outcome_tfidf | ❌ FAIL | +51% | -13% |
| regeste_full_text_hybrid_0.5 | ❌ FAIL | 0% | -28% |
| regeste_full_text_hybrid_0.7 | ❌ FAIL | 0% | -28% |

Only 2/8 pass. Best normalized hierarchy_purity=0.465 < 0.7 threshold.

---

## Critical Artifact: HNSW Adversarial Collapse
HNSW (M=16, ef=200/100) produces **identical k-NN graphs** across all 8 reps at 174k:
- HNSW on 174k: jurist_pairwise=0.122 (identical), lang_dom≈0.606
- Exact k-NN on 1,199 valid: jurist_pairwise=0.73–0.80, lang_dom=0.43–0.50

**Fix required before dense eval**: Exact k-NN for adversarial benchmarks on valid subset; HNSW only for full-corpus benchmarks.

---

## Blockers
1. **Primary**: legal_distance_174k_dense_embeddings_not_in_accepted_state
2. **Root cause**: Corpus artifact publication gap (files at `/tmp/lex_accepted/core/...` not `/tmp/lex_accepted/corpus/...`)
3. **Methodological**: HNSW adversarial artifact requires exact k-NN fix
4. **External**: Jurist human study (framework ready, non-blocking)

---

## Awaited Representations (11 total)
- **Dense (6)**: center_projected_768/64, linear_metric_epoch4, mahalanobis_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3
- **Citation roles (3)**: citing/following/criticizing_alpha0.3
- **Linear hybrids (2)**: linear_citation_concat, linear_hybrid05_concat

---

## Evidence Locations
- Suite results: `results/evaluation/v25_174k_formal_suite/results/`
- Citation heritage: `results/evaluation/v25_174k_citation_heritage/`
- v17b: `results/evaluation/v25_174k_v17b/`
- Protocol: `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json`
- Runner: `evaluation/experiments/v25_174k_suite/run_v25_174k_suite.py`

---

## Recommendation
**continue_recommended = false** — All machine-executable work for v27 TF-IDF family complete. Lane correctly blocked awaiting dense embeddings.