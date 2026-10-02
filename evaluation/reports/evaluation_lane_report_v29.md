# Evaluation Lane Report — Factory Direction v29

## Executive Summary

The Evaluation Lane has completed its machine-executable formal suite on all **currently available** production representations at scale. The TF-IDF family (8 representations) is fully evaluated at 174k decisions. Dense embeddings from legal-distance are only partially available: 3/26 years (2000–2002, 12,570 decisions) are **ACCEPTED** post-audit; 15/26 years (2000–2014, 91,929 decisions) are **checkpointed pending audit**; 11/26 years (2015–2026) remain **unprocessed**. No dense representation at full 174k scale exists yet.

**Key finding**: The fundamental tradeoff identified in prior cycles persists at 174k scale:
- **Citation-based TF-IDF** (cited_decisions_tfidf, hybrids) passes adversarial gates (language_dominance ≈ 0.49, jurist_preference ≈ 0.71) and citation_heritage (AUC > 0.65), but fails branch/tf_metadata/hierarchy benchmarks.
- **Text-based TF-IDF** (regeste_tfidf, full_text_tfidf, hybrids) fails adversarial gates (language_dominance ≈ 0.999, jurist_preference ≈ 0.0).
- **Dense center_projected embeddings** (multilingual-e5 + language-center projection + PCA) fail adversarial gates at ALL scales tested (3-year, 15-year, and 174k-subsample): language_dominance 0.89–0.997, jurist_preference 0.005–0.29.
- **v17b label normalization** (15–25% purity gain reported at small scale) **does NOT generalize** to 174k fine-grained legal_area labels: uniform_improvement_or_matching = false; zoom_fine purity degrades 11–16% for citation-based representations.

## 1. Formal Suite at 174k Scale (TF-IDF Family)

**Harness**: `run_174k_formal_suite.py` (v3_174k_fixed, HNSW artifact fix via exact k-NN on stratified valid subset n≈2000, frozen seed=42)

| Representation | Verdict | LangDom | LD-Pass | JuristPref | JP-Pass | Both |
|---|---|---|---|---|---|---|
| cited_decisions_tfidf | PASS | 0.4917 | ✓ | 0.7075 | ✓ | ✓ |
| cited_decisions_tfidf_outcome_hybrid_0.5 | PASS | 0.4880 | ✓ | 0.7230 | ✓ | ✓ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | PASS | 0.5040 | ✓ | 0.6890 | ✓ | ✓ |
| outcome_tfidf | FAIL | 0.9990 | ✗ | 0.0000 | ✗ | ✗ |
| regeste_tfidf | FAIL | 0.9990 | ✗ | 0.0000 | ✗ | ✗ |
| full_text_tfidf_light | FAIL | 0.9990 | ✗ | 0.0000 | ✗ | ✗ |
| regeste_full_text_hybrid_0.5 | FAIL | 0.9990 | ✗ | 0.0000 | ✗ | ✗ |
| regeste_full_text_hybrid_0.7 | FAIL | 0.9990 | ✗ | 0.0000 | ✗ | ✗ |

**Thresholds (frozen)**: language_dominance < 0.85, jurist_pairwise > 0.5. Both must pass.

**Production default** (`cited_decisions_tfidf_outcome_hybrid_0.5`): **PASS** both adversarial gates.

### Cross-language & Jurist Usability (TF-IDF)

| Benchmark | cited_decisions_tfidf | cited_decisions_tfidf_outcome_hybrid_0.5 |
|---|---|---|
| cross_language_neighbor_quality (separation) | -0.596 | -0.605 |
| zero_shot_cross_language_transfer (NMI) | FAIL (0.022) | FAIL (0.017) |
| language_specific_representation_quality (NMI) | FAIL (0.038) | FAIL (0.038) |
| cluster_coherence_rating (branch purity) | FAIL (0.358) | FAIL (0.358) |
| cross_language_retrieval (recall@10) | FAIL (0.000) | FAIL (0.000) |
| temporal_stability (neighbor overlap) | PASS (0.78) | PASS (0.78) |
| hierarchy_coherence (level_1 NMI) | FAIL (0.02) | FAIL (0.02) |
| boilerplate_resistance | FAIL (-0.92) | FAIL (-0.92) |

**Observation**: TF-IDF citation-based representations excel at adversarial neighbor quality and citation heritage but **fail hierarchy/cluster coherence** — they do not organize decisions by legal area in a way that matches human indexing.

## 2. Citation Heritage Benchmark at 174k

**Frozen pair pool**: 137,314 positive + 137,314 negative pairs (built from resolved citation graph: 2,019/2,105 citations resolved).

| Representation | AUC-ROC | Status (AUC≥0.65) | Recall@10 |
|---|---|---|---|
| cited_decisions_tfidf | 0.7426 | PASS | 0.000 |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.7163 | PASS | 0.000 |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.7290 | PASS | 0.000 |
| outcome_tfidf | 0.6262 | FAIL | — |
| regeste_tfidf | 0.5030 | FAIL | — |
| full_text_tfidf_light | 0.6257 | FAIL | — |
| regeste_full_text_hybrid_0.5 | 0.6365 | FAIL | — |
| regeste_full_text_hybrid_0.7 | 0.6595 | FAIL | — |

**Note**: Recall@10 = 0.0 for all representations at 174k scale despite AUC > 0.65. This indicates that while citation-sharing pairs are ranked higher on average, the top-10 neighbors of a decision rarely include its direct citation targets at this corpus scale.

## 3. Dense Embeddings Evaluation (Partial Scale)

### 3-Year ACCEPTED (2000–2002, 12,570 decisions)

| Representation | Verdict | LangDom | JuristPref |
|---|---|---|---|
| center_projected_768dim | FAIL | 0.9964 | 0.0074 |
| center_projected_128dim | FAIL | 0.9974 | 0.0054 |
| center_projected_64dim | FAIL | 0.9975 | 0.0054 |

- **Citation heritage**: Only 2 positive pairs in subset → AUC=0.79, Recall@10=0.0 (insufficient pairs)
- **v17b label normalization**: hierarchy_purity=0.825–0.830, zoom_nesting=0.56–0.69, legal_area_purity=0.87–0.88; norm/raw ratio ≈ 1.0 (no improvement)

### 15-Year Checkpointed (2000–2014, 91,929 decisions)

| Representation | Verdict | LangDom | JuristPref |
|---|---|---|---|
| center_projected_768dim | FAIL | 0.8993 | 0.267 |
| center_projected_128dim | FAIL | 0.8973 | 0.275 |
| center_projected_64dim | FAIL | 0.8929 | 0.288 |
| linear_citation_concat | FAIL | 0.7943 | 0.481 |
| linear_hybrid05_concat | FAIL | 0.8086 | 0.473 |

- **Best dense representation**: `linear_citation_concat` (LangDom=0.794 PASS, JuristPref=0.481 FAIL — close but not passing both gates)
- **Citation heritage**: 10,248 positive pairs → AUC=0.91, Recall@10=0.0
- **v17b label normalization**: Not completed (timeout), but 3-year results suggest ratio ≈ 1.0

**Scale extrapolation**: Language dominance improves from ~0.996 (3-year) → ~0.89 (15-year) → ~0.90 (174k-subsample in 15-year eval), but remains above 0.85 threshold. Jurist preference improves from ~0.006 → ~0.27 → ~0.29, but remains far below 0.5.

## 4. v17b Label Normalization at 174k (TF-IDF)

**Test**: Does normalization of fine-grained legal_area labels (15–25% purity gain at small scale, reproduced across 4 seeds) generalize to 174k?

| Representation | hierarchy_ratio | zoom_fine_ratio | legal_area_ratio |
|---|---|---|---|
| cited_decisions_tfidf | 1.0000 | 0.8869 | 1.0000 |
| outcome_tfidf | 1.0000 | 0.9968 | 1.0000 |
| regeste_tfidf | 1.0000 | 0.9885 | 1.0018 |
| full_text_tfidf_light | 1.0000 | 0.8352 | 0.9997 |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 1.0000 | 0.8827 | 0.9997 |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 1.0000 | 0.8861 | 1.0000 |
| regeste_full_text_hybrid_0.5 | 1.0000 | 0.9060 | 1.0024 |
| regeste_full_text_hybrid_0.7 | 1.0000 | 0.9647 | 1.0016 |

**Result**: `uniform_improvement_or_matching = false`. Four representations worsen zoom_fine purity by >10% (0.83–0.89 ratio). **Conclusion**: v17b label normalization does not generalize to 174k fine-grained labels; it degrades zoom coherence for citation-based representations.

## 5. Scale Extrapolation Model

| Scale | Decisions | Best Dense LangDom | Best Dense JuristPref | TF-IDF Citation LangDom | TF-IDF Citation JuristPref |
|---|---|---|---|---|---|
| 3-year | 12,570 | 0.996 | 0.005 | — | — |
| 12k (2000-2002) | ~19k | — | — | 0.49 | 0.71 |
| 15-year | 91,929 | 0.899 (center) / 0.794 (linear_citation_concat) | 0.29 / 0.48 | — | — |
| 174k | 173,963 | N/A | N/A | 0.49 | 0.71 |

**Confirmed**: Flat Leiden fails at sub-62k scale (>99% singletons); hierarchical Leiden works at all scales (nesting=1.0 by construction, improvement_rate 57–90% structural). 28k checkpoint validates scale extrapolation (hier_impr ~0.67 at 174k).

## 6. Recommendations

### For Legal-Distance Lane
1. **Priority**: Complete 174k dense embeddings (remaining 11 years: 2015–2026)
2. **Investigate**: `linear_citation_concat` at 174k — only dense representation that passes language_dominance threshold (0.794 < 0.85)
3. **Investigate**: Metric learning / citation role embeddings at scale — 1000-scale showed promise (citing_alpha0.3 ZQ=0.5401)

### For Fractal-Map Lane
- TF-IDF hierarchical Leiden at 174k: 1/4 modes PASS (regeste_tfidf fine_branch_purity=0.566); 3/4 FAIL (~0.38–0.49)
- Dense modes blocked pending 174k embeddings

### For Product Lane
- 3 TF-IDF production modes operational at full 174k (metadata_174k_full.json complete, 16/16 scale tests PASS, 50+ endpoints)
- Safe to integrate per audit CYCLE_36461247941 (safe_to_integrate=true)
- **Blocked** on dense embeddings for enhanced map modes

### For Evaluation Lane
- **No further cycles justified** on current factory direction question. All available representations evaluated.
- **Next cycle**: Trigger when legal-distance delivers 174k dense embeddings (full corpus).
- **Preserve**: All negative results (dense FAIL, v17b NEGATIVE, citation_heritage Recall@10=0) as first-class evidence.

## 7. Evidence Preservation

All raw outputs preserved in:
- `evaluation/results/174k/formal_suite/` — 30+ formal suite runs
- `evaluation/results/174k/formal_suite/15year_dense/` — 15-year dense evals
- `evaluation/results/174k/dense_3year_formal_suite/` — 3-year dense evals
- `evaluation/results/174k_citation_heritage/` — citation heritage at 174k and partial
- `evaluation/results/174k_label_normalization/` — v17b at 174k TF-IDF

State file: `evaluation/state/evaluation.json` (machine-readable, includes all evidence_refs)

---

**Recommendation**: `PAUSE` evaluation lane until legal-distance delivers 174k dense embeddings. Current question fully answered for available representations.
