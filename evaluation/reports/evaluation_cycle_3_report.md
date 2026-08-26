# Evaluation Cycle Report — Real Corpus TF-IDF Baseline

**Run ID:** eval_real_tfidf_20260826  
**Lane:** evaluation  
**Direction version:** 1  
**Date:** 2026-08-26  
**Evidence tier:** REPRODUCED (first baseline on real corpus data)

---

## 1. Hypothesis & Product Decision

**Question:** What baseline performance does TF-IDF achieve on the evaluation benchmarks, using real Swiss Federal Supreme Court (BGer) decisions? This establishes the floor that any legally-structured representation must beat.

**Product decision:** If TF-IDF already captures legal structure, the legal-distance lane can focus on marginal improvements. If TF-IDF fails on key benchmarks (boilerplate resistance, multilingual invariance, hierarchy coherence), those become primary targets for legally-structured representations.

**Baseline frozen before observation:**
- Representation: TF-IDF (10K features, 1-2 grams, sublinear TF, min_df=2, max_df=0.95)
- Corpus: 1,200 BGer decisions (2020-2024) from OpenCaseLaw API
- Weak supervision: Citation graph (99 in-corpus citation pairs), legal branch metadata
- Success rule: AUC-ROC > 0.7 for neighbor relevance; resistance > 0.5 for boilerplate; separation > 0 for multilingual; drift < 0.3 for stability; purity > 0.5 and NMI > 0.3 for hierarchy

## 2. Corpus Summary

| Property | Value |
|----------|-------|
| Total decisions | 1,200 |
| Languages | DE: 735, FR: 403, IT: 62 |
| Years | 2020: 50, 2021: 50, 2022: 50, 2023: 50, 2024: 1,000 |
| Legal branches | zivilrecht: 18, strafrecht: 9, oeffentliches_recht: 20, sozialversicherungsrecht: 5 (+ 1,148 with specific legal_area labels) |
| In-corpus citation pairs | 99 |
| Decisions with citations | 1,121/1,200 |
| With Sachverhalt (structured) | 63 |
| With Erwägungen (structured) | 89 |

**Provenance:** Canonical JSONL files from `/tmp/lex_accepted/corpus/corpus/normalization/canonical/`. Schema v1 from `corpus/schema/decision_schema.json`.

## 3. Benchmark Results

### 3.1 Neighbor Relevance (Citation-Based) — PASSED

Measures whether citing decisions are closer in embedding space than random pairs.

| Metric | Full TF-IDF | Reasoning TF-IDF |
|--------|-------------|------------------|
| **AUC-ROC** | **0.9519** | **0.9462** |
| MRR | 0.6126 | 0.5861 |
| Precision@1 | 0.5038 | 0.4887 |
| Precision@5 | 0.1774 | 0.1609 |
| Precision@10 | 0.0955 | 0.0895 |
| Positive mean sim | 0.5813 | 0.5618 |
| Negative mean sim | 0.1305 | 0.1272 |

**Interpretation:** TF-IDF strongly separates citing from non-citing decisions (AUC > 0.95). This is because citing decisions share vocabulary (same legal domain, same cited precedents). Full TF-IDF slightly outperforms reasoning-only TF-IDF, suggesting boilerplate text actually helps citation matching (shared procedural language).

**Baseline for legal-distance lane:** AUC > 0.95 for citation relevance. Legal embeddings should match or exceed this without relying on shared boilerplate.

### 3.2 Boilerplate Resistance — FAILED

Measures embedding stability when procedural boilerplate is injected.

| Metric | Value |
|--------|-------|
| **Resistance score** | **0.0113** |
| Mean stability | 0.0113 |
| Std stability | 0.0132 |
| Min stability | 0.0013 |
| Max stability | 0.0708 |
| Test decisions | 80 |

**Interpretation:** TF-IDF is extremely sensitive to boilerplate injection. Adding ~100 words of standard BGer boilerplate changes the embedding by 99% (stability = 0.01). This is a critical weakness: any representation that can't resist boilerplate will have its geometry dominated by procedural text rather than legal substance.

**Baseline for legal-distance lane:** Resistance must exceed 0.5 (SBERT-like) and ideally > 0.7 (legally-structured). The gap from 0.01 to >0.7 is the core challenge.

### 3.3 Multilingual Invariance — FAILED

Tests whether same legal content in different languages produces similar embeddings.

| Metric | Value |
|--------|-------|
| Cross-lang same-area similarity | 0.0268 |
| Same-lang diff-area similarity | 0.2642 |
| **Separation** | **-0.2374** |
| Cross-lang pairs | 1,200 |
| Same-lang pairs | 101 |

**Interpretation:** TF-IDF is completely language-specific. Cross-language pairs from the same legal branch have near-zero similarity (0.03), while same-language pairs from different branches have moderate similarity (0.26). The negative separation (-0.24) means language dominates over legal content.

**Baseline for legal-distance lane:** Separation must become positive (>0.1) and ideally >0.3. Cross-language similarity should reach >0.7 with multilingual legal embeddings.

### 3.4 Corpus Stability — FAILED

Tests embedding stability when the corpus grows and the representation is retrained.

| Metric | Value |
|--------|-------|
| **Mean position drift** | **0.8733** |
| Std drift | 0.0383 |
| Anchor decisions | 20 |
| Corpus sizes tested | 200, 400, 600, 800, 1,200 |

**Interpretation:** TF-IDF retrained on growing subsets has very high drift (0.87). As new vocabulary is introduced, the feature space shifts dramatically, repositioning existing decisions. This means a TF-IDF map would need complete recomputation as the corpus grows.

**Note:** Static pre-computed embeddings have drift ~0 by construction. The high drift here measures TF-IDF's instability under retraining, not embedding persistence.

**Baseline for legal-distance lane:** Drift < 0.3 with retraining, or use fixed embeddings that don't require retraining.

### 3.5 Hierarchy Coherence — FAILED

Tests whether hierarchical clustering recovers legal branch structure.

| Clusters | Purity | NMI |
|----------|--------|-----|
| 4 (= branches) | 0.4720 | 0.0115 |
| 8 | 0.6222 | 0.0193 |
| 12 | 0.6482 | 0.0283 |

**Interpretation:** Purity is moderate (0.47-0.65), meaning clusters tend to contain decisions from the same branch. However, NMI is extremely low (0.01-0.03), indicating the cluster assignments don't align well with branch labels. This confirms the fractal-map finding: current representations primarily separate by language, not legal area.

**Baseline for legal-distance lane:** Purity > 0.7 and NMI > 0.5 for legal branch recovery.

## 4. Comparison with Fractal-Map Results

The fractal-map lane found that Leiden clustering at resolution 3.0 achieves legal_area_purity of 0.43 but language_purity of 0.99. The TF-IDF baseline achieves similar purity (0.47-0.65) but with even lower NMI, confirming that:

1. The primary geometric signal is language, not law
2. TF-IDF captures enough lexical similarity for citation matching but not enough legal structure for meaningful hierarchy
3. The legal-distance lane must produce representations where legal content dominates over language and boilerplate

## 5. Negative Results (Preserved)

1. **Boilerplate resistance is catastrophically low for TF-IDF (0.01)** — This is expected and confirms that TF-IDF cannot serve as the final representation. Any legal representation must resist boilerplate by >50x.

2. **Multilingual invariance is negative (-0.24 separation)** — TF-IDF is inherently monolingual. Cross-language legal similarity requires language-agnostic representations (multilingual embeddings, citation-only, or norms/articles).

3. **Corpus stability under retraining is very poor (0.87 drift)** — TF-IDF vocabulary shifts with every new document. Fixed embeddings or incremental methods are needed for stable maps.

4. **Hierarchy coherence NMI is near zero (0.03)** — TF-IDF clusters don't correspond to legal structure. The moderate purity is an artifact of language dominance, not legal understanding.

## 6. Recommendations

**CONTINUE** — The evaluation framework now produces reproducible, interpretable results on real corpus data. The TF-IDF baseline establishes clear floors for each benchmark. Next steps:

1. **Legal-distance lane:** Test whether legal embeddings (Legal-BERT, multilingual models, citation-graph methods) beat TF-IDF baselines on boilerplate resistance, multilingual invariance, and hierarchy coherence.

2. **Evaluation lane improvements:**
   - Add a TF-IDF-on-erwaegungen-only variant that excludes headers and procedural text
   - Implement citation-role-aware supervision (distinguishing "cited approvingly" from "cited to distinguish")
   - Test against Jurivoc descriptors when real TF metadata is available (SCD Parquet download)

3. **Corpus lane:** Acquire structured sections (Sachverhalt/Erwägungen) for more decisions to enable section-level evaluation.

## 7. Files Produced

- `evaluation/results/real_corpus_tfidf_baseline_results.json` — Machine-readable results
- `evaluation/data/real_corpus.py` — Real corpus adapter
- `evaluation/reports/evaluation_cycle_3_report.md` — This report
- `state/evaluation.json` — Updated lane state
