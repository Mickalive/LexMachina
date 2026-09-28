# Evaluation Lane - 174k Formal Suite Monitoring Report
**Factory Direction Version:** 28  
**Report Generated:** 2026-09-28T03:28:00Z  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** MONITORING  
**Monitor Check Count:** 185  

---

## Executive Summary

The Evaluation Lane has **completed all machine-executable evaluation work** for currently available 174k-scale representations per Factory Direction v28. The three mandated sub-questions are **complete and verified reproducible**:

1. ✅ **Full 12-benchmark formal suite** at 174k scale on all 8 TF-IDF production representations (frozen harness v3 thresholds, HNSW artifact fixed)
2. ✅ **Citation heritage benchmark** validated using published 174k citation-ID resolution (2,019/2,105 resolved, 95.9%)
3. ✅ **v17b label normalization** tested on 174k fine-grained legal_area labels — differential effect confirmed

**No new production representations have landed** from legal-distance since the last evaluation cycle. The lane remains in active MONITORING mode (check_count=185) awaiting:
- 174k dense embeddings (3/26 years ACCEPTED; 17/26 pending audit; 6/26 not yet processed)
- 174k citation role embeddings
- 174k linear hybrid embeddings

---

## Completed Evaluations (REPRODUCED Tier)

### 1. TF-IDF Family — 8 Representations at 174k Scale

All 8 zero-shot TF-IDF production representations have been evaluated through **both** evaluation pipelines:

| Representation | Adversarial (v3 harness) | V25 Formal Suite (12 benchmarks) | Citation Heritage | v17b Normalization |
|---|---|---|---|---|
| `cited_decisions_tfidf` | PASS (LD=0.529, JP=0.802) | 6 PASS / 5 FAIL / 1 SKIP | AUC=0.79, recall@10=0.044 (FAIL) | Tested |
| `outcome_tfidf` | PASS (LD=0.453, JP=0.726) | 3 PASS / 9 FAIL | AUC=0.66, recall@10=0.000 (FAIL) | Tested |
| `regeste_tfidf` | PASS (LD=0.484, JP=0.609) | 5 PASS / 7 FAIL | AUC=0.49, recall@10=0.000 (FAIL) | Tested |
| `full_text_tfidf_light` | **FAIL** (LD=1.000, JP=0.000) | 7 PASS / 5 FAIL | AUC=0.90, recall@10=0.052 (FAIL) | Tested |
| `cited_outcome_hybrid_0.5` | PASS (LD=0.516, JP=0.806) | 6 PASS / 5 FAIL / 1 SKIP | AUC=0.76, recall@10=0.053 (FAIL) | Tested |
| `cited_outcome_hybrid_0.7` | PASS (LD=0.524, JP=0.798) | 6 PASS / 6 FAIL | AUC=0.77, recall@10=0.049 (FAIL) | Tested |
| `regeste_full_text_hybrid_0.5` | **FAIL** (LD=0.998, JP=0.000*) | 7 PASS / 5 FAIL | AUC=0.87, recall@10=0.035 (FAIL) | Tested |
| `regeste_full_text_hybrid_0.7` | **FAIL** (LD=0.999, JP=0.000*) | 7 PASS / 5 FAIL | AUC=0.85, recall@10=0.036 (FAIL) | Tested |

*Text-based hybrids fail jurist pairwise due to language dominance (cross-language recall FAIL)

**Key Finding — Fundamental Two-Mode Tradeoff REPRODUCED:**
- **Citation-based representations** (cited_decisions, outcome, hybrids): PASS adversarial gates, FAIL branch/tf_metadata/hierarchy
- **Text-based representations** (full_text, regeste, regeste-full_text hybrids): PASS branch/tf_metadata, **FAIL adversarial** (lang_dom ~0.999)

This tradeoff is **scale-invariant** — reproduced at 1,200, 21k, 99k, and 174k.

### 2. Citation Heritage Benchmark — 174k Scale

- **Pair pool:** 2,040 frozen pairs (1,020 positive direct+shared citations, 1,020 negative) — regenerated from resolved citation graph, seed=42
- **Resolution:** 2,019/2,105 citation IDs (95.9%)
- **Result:** ALL 8 TF-IDF representations **FAIL** recall@10 threshold (≥0.2 required)
  - Best: `cited_decisions_tfidf` — recall@10 = 0.044 (AUC=0.79 PASS but nn_citation_rate@10 fails)
  - Text-based: `full_text_tfidf_light` — recall@10 = 0.052 (AUC=0.90 PASS but nn_citation_rate@10 fails)
- **Conclusion:** Citation structure is partially preserved (AUC > 0.65) but **not recovered in top-10 neighbors** at 174k density for any TF-IDF representation

### 3. v17b Label Normalization — 174k Scale

- **Mapping:** 85,819 labels normalized, 214 → 164 unique legal_area labels (conservative cross-lingual canonical map)
- **Differential effect CONFIRMED at 174k (exact reproduction across 4 seeds):**

| Representation Type | Hierarchy Coherence | Zoom Coherence (fine) |
|---|---|---|
| **Citation-based** (cited_decisions, outcome, hybrids) | **Improve 1.04–1.10×** | **Improve 1.03–1.08×** |
| **Text-based** (full_text, regeste, regeste-full_text) | Degrade ~0.90× | **Degrade 0.66–0.70×** |

- **Interpretation:** Normalization helps representations that already encode legal structure (citation-based) but harms text-based representations that rely on surface-form clustering. The 174k results **exactly mirror** the 1,200-scale v17b findings.

### 4. V25 Formal Suite — Frozen Protocol at 174k

Executed on all 8 TF-IDF representations using frozen protocol (config hash: `4323f833fa72366a`):

| Representation | PASS | FAIL | SKIP | Key Failures |
|---|---|---|---|---|
| cited_decisions_tfidf | 6 | 5 | 1 | branch_knn, tf_metadata, boilerplate, temporal, hierarchy, legal_area |
| outcome_tfidf | 3 | 9 | 0 | citation_heritage(PASS), temporal(PASS), collapse(PASS) only |
| regeste_tfidf | 5 | 7 | 0 | adversarial, temporal, multilingual, cross_lang, collapse PASS |
| full_text_tfidf_light | 7 | 5 | 0 | adversarial(FAIL), multilingual, cross_lang, hierarchy, legal_area |
| cited_outcome_hybrid_0.5 | 6 | 5 | 1 | Same pattern as cited_decisions |
| cited_outcome_hybrid_0.7 | 6 | 6 | 0 | boilerplate FAIL (0.076 < 0.1) |
| regeste_full_text_hybrid_0.5 | 7 | 5 | 0 | adversarial(FAIL), multilingual, cross_lang, hierarchy, legal_area |
| regeste_full_text_hybrid_0.7 | 7 | 5 | 0 | Same pattern as _0.5 |

**Production Default (`cited_decisions_tfidf_outcome_hybrid_0.5`):** 6 PASS / 5 FAIL / 1 SKIP — matches `cited_decisions_tfidf` pattern exactly.

---

## Infrastructure Status (VERIFIED)

| Component | Status | Details |
|---|---|---|
| **Adversarial Benchmarks** | VERIFIED | Exact k-NN on stratified subsample (n=2000, seed=42); production default reproduces: lang_dom=0.4867 PASS, jurist_pref=0.5349 PASS |
| **Scalable NN (HNSW)** | OPERATIONAL | hnswlib M=16, ef_construction=200, ef_search=100; exact-cosine parity established |
| **Citation Heritage Pipeline** | READY | Frozen 2,040 pair pool; evaluation re-run on new pool verified |
| **v17b Normalization** | READY | Differential effect reproduced across all 8 TF-IDF reps |
| **V25 Formal Suite Runner** | OPERATIONAL | NoneType.lower bug fixed; all 8 reps complete |
| **Monitor Script** | ACTIVE | check_count=185; enhanced scan paths (fractal-map for TF-IDF, legal-distance for dense) |
| **HNSW Artifact Fix** | CONFIRMED | Exact k-NN on valid subset avoids HNSW masking representation differences |

---

## Awaited Representations (Not Yet Available at 174k)

### Dense Embeddings — Legal-Distance Lane
| Status | Years | Decisions | Note |
|---|---|---|---|
| **ACCEPTED** | 2000-2002 (3/26) | ~19,441 | 11% of corpus — per factory direction v28 |
| **PENDING AUDIT** | 2003-2019 (17/26) | ~79,884 | In checkpoints, not yet promoted |
| **NOT PROCESSED** | 2020-2025 (6/26) | ~74,638 | Blocked on legal-distance year-split execution |

**Total checkpoints:** 25 years (2000-2024), 137,325 decisions (79% coverage) — but only 3 years ACCEPTED for product use.

### Citation Role Embeddings
- Available at v5/v6 scale (~1,200 decisions): citing, following, criticizing, distinguishing, overruling, all_weighted
- **Not yet at 174k scale** — awaited per factory direction

### Linear Hybrid Embeddings
- `linear_citation_concat`, `linear_hybrid05_concat` — **not yet available at 174k**

---

## Blocker Summary

| Blocker | Owner | Impact |
|---|---|---|
| Dense embeddings 174k audit promotion | legal-distance | Critical path — blocks fractal-map, product, full evaluation |
| Citation roles 174k | legal-distance | Blocks citation-role evaluation |
| Linear hybrids 174k | legal-distance | Blocks hybrid evaluation |
| Jurist human study (5-10 Swiss jurists) | External | Required for human preference validation |

---

## Recommendation

**CONTINUE MONITORING** — The evaluation lane has concrete discriminating purpose: auto-evaluate awaited representations (dense embeddings, citation roles, linear hybrids) as they land in accepted state at 174k scale. All infrastructure is verified operational and frozen.

**No evaluation work is blocked** — the lane is correctly waiting for upstream dependencies. When legal-distance promotes 174k dense embeddings through audit, the monitor will detect them and execute the full formal suite automatically.

---

## Evidence References

1. **Formal Suite (v3 harness):** `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` (config hash: `b51701f5a9c11692`)
2. **Citation Heritage:** `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
3. **v17b Normalization:** `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
4. **V25 Formal Suite:** `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` (config hash: `4323f833fa72366a`)
5. **Dense Partial (2000-2015):** `evaluation/results/174k/dense_partial_2000_2015/dense_partial_2000_2015_eval_latest.json`
6. **Monitor State:** `evaluation/state/monitor_174k_state.json` (check_count=185)

---

## Next Actions (When Representations Land)

The monitor script (`monitor_and_evaluate_174k.py`) will automatically:
1. Detect new 174k representation directories in accepted state
2. Run full corpus adversarial evaluation (v3 harness, exact k-NN on valid subset)
3. Run V25 formal suite (12 benchmarks + citation_heritage + v17b)
4. Update state and generate report

No manual intervention required.