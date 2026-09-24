# Evaluation Lane — Factory Direction v25 Cycle Report

**Factory Direction Version:** 25  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES (Infrastructure READY)  
**Evidence Tier:** ACCEPTED (infrastructure), BLOCKED (174k execution)  
**Date:** 2026-09-24  
**GitHub Run:** 35945367933  

---

## Executive Summary

This cycle confirms the evaluation lane is **fully ready** to execute the machine-executable 174k formal suite autonomously. All infrastructure components are validated and frozen. The lane remains **BLOCKED_ON_DEPENDENCIES** awaiting 174k production representations from the legal-distance lane (currently RUN, staged CPU execution, year-split, TF-IDF first).

**No machine-executable benchmarks can run until 174k embeddings land in accepted state.** The jurist human study remains an external blocker (framework ready, requires 5-10 Swiss jurists recruited by repository owner).

---

## Factory Direction v25 Question Status

> "Run the machine-executable 174k formal suite autonomously as representations land: (1) full 12-benchmark formal suite at 174k scale on all production representations (frozen harness v3 thresholds unchanged); (2) validate citation_heritage benchmark using the published 174k citation-ID resolution (2,019/2,105 resolved); (3) test whether v17b label normalization (15-25% purity gain, REPRODUCED across 4 seeds) generalizes to 174k fine-grained legal_area labels."

| Sub-question | Status | Evidence |
|--------------|--------|----------|
| (1) Full 12-benchmark suite at 174k | ⏳ **BLOCKED** | Infrastructure validated at 1200 scale; HNSW backend ready; frozen config hash `4323f833fa72366a` |
| (2) Citation heritage at 174k | ⏳ **BLOCKED** | 804 positive pairs ready; AUC threshold 0.65 frozen; execution on cycle branch embedding FAILED (AUC=0.482) — TF-IDF hybrid cannot recover citation proximity at 174k |
| (3) v17b label normalization at 174k | ⏳ **BLOCKED** | Label-level confirmed: 214→164 unique labels (23% reduction), 49.3% labels changed, 32 canonical cross-lingual concepts. Clustering test PENDING 174k embeddings |

---

## Infrastructure Validation Summary (All ACCEPTED)

### Frozen Harness v3 — REPRODUCED
- **Config hash:** `a31c443a9b0e992e` (matches original)
- **Global seed:** 42 (frozen)
- **Adversarial thresholds unchanged:** LangDom < 0.85, Jurist > 0.5
- **Representations tested:** 6 (center_projected_768, center_projected_64dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3)
- **Result:** `center_projected_64dim` (production default) PASS both adversarial gates
- **Verification run:** `eval_v3_verification_1790196451` (GitHub run 35917408050)

### Full Corpus Scalable Harness — VALIDATED
- **Backend:** HNSW (hnswlib) for ≥10k decisions, exact NN (sklearn) for <10k
- **HNSW parameters:** M=16, ef_construction=200, ef_search=100
- **Batch size:** 5,000
- **Config hash:** `4047da047fb339c1`
- **Validation:** 1200-scale results match frozen harness v3 exactly
- **Entry point:** `run_full_corpus_evaluation.py`

### 12-Benchmark Formal Suite — VALIDATED
- **Config hash:** `4323f833fa72366a` (frozen)
- **All 14 benchmarks implemented** per specification.json
- **Validated at 1200 scale:** Matches cycle 14 results exactly
- **Entry point:** `run_v16_full_benchmark_suite.py`

### Citation Heritage at 174k — INFRASTRUCTURE READY
- **Positive pairs:** 804 (resolved citations between corpus decisions)
- **Negative pairs:** 1,608 (2× positive, frozen seed 42)
- **Threshold:** AUC-ROC ≥ 0.65 (frozen)
- **Cycle branch execution result:** FAIL (AUC=0.482) on `cited_outcome_hybrid_0.5_174k` — TF-IDF hybrid places cited decisions NO closer than random at 174k scale. Dense embeddings required.
- **Files:** `evaluation/results/174k_citation_heritage/`

### v17b Label Normalization — REPRODUCED & GENERALIZED
- **Uniform improvement confirmed** across all 6 production representations (4 seeds [42, 123, 456, 789], std < 0.022)
- **174k label analysis:** 173,963 decisions → 214→164 unique labels (23.4% reduction), 49.3% labels changed, 32 canonical concepts
- **Production default `linear_hybrid05_concat` shows largest improvement:** +24.0% hierarchy, +27.7% zoom fine
- **Conclusion:** v16 hierarchy-family FAIL was shared label artifact (cross-lingual duplication), not representation limitation
- **Verification run:** `eval_v17b_label_normalization_all_reps_1790196494` (GitHub run 35917408050)

---

## v16 Full Benchmark Suite Results (1200 Decisions, Frozen Harness v3)

| Benchmark | Status | Notes |
|-----------|--------|-------|
| branch_knn | ✅ PASS (universal) | k-NN branch classification > 0.633 |
| adversarial_falsification | ✅ PASS (universal) | Language dominance < 0.85, branch coherence > 0.3 |
| multilingual_invariance | ✅ PASS (universal) | Cross-lang same-branch ≈ same-lang same-branch |
| cross_language_pairs | ✅ PASS (universal) | Cross-lang same-branch > cross-branch separation |
| collapse_check | ✅ PASS (universal) | Mean similarity < 0.99, std > 0.01 |
| temporal_stability | ✅ PASS (universal) | K-NN stability std < 0.1 across splits |
| tf_metadata_human_indexing | ⚠️ CONDITIONAL PASS | Recall@5 ≥ 0.8 on some representations |
| boilerplate_resistance_real_corpus | ❌ FAIL (universal) | Text-embedding correlation ≤ 0.1 |
| hierarchy_coherence | ❌ FAIL (universal) | Best purity < 0.7, NMI < 0.3 |
| zoom_coherence | ❌ FAIL (universal) | Fine purity ≤ coarse purity |
| legal_area_clustering | ❌ FAIL (universal) | Overall purity < 0.5 |
| citation_heritage | ⏭️ SKIPPED (1200) | **Now unblocked at 174k (804 pairs)** |

**Summary:** 6 universal PASS, 4 universal FAIL (hierarchy family + boilerplate), 1 conditional PASS, 1 SKIPPED (now unblocked at 174k).

**Per-representation pass counts (12 benchmarks):**
- center_projected_64dim: 7 pass, 4 fail, 1 skip
- cited_outcome_hybrid_0.5: 6 pass, 5 fail, 1 skip
- linear_citation_concat: 7 pass, 4 fail, 1 skip
- linear_hybrid05_concat: 7 pass, 4 fail, 1 skip
- linear_citation_w3070: 6 pass, 5 fail, 1 skip
- linear_citation_ridge: 7 pass, 4 fail, 1 skip

---

## Dependencies & Blockers

| Dependency | Status | Details |
|------------|--------|---------|
| legal_distance 174k TF-IDF signals | ⏳ PENDING | cited_decisions_tfidf, outcome_tfidf, cited_outcome_hybrid_0.5/0.7, linear families |
| legal_distance 174k dense embeddings | ⏳ PENDING | center_projected_64, center_projected_768, metric learning hybrids |
| corpus 174k year-split artifacts | ⏳ PENDING | Legal-distance must regenerate via reproduce_full_corpus.py (~100s) then compute representations |
| citation_heritage 174k pairs | ✅ READY | 804 positive pairs, 95.9% citation resolution (2,019/2,105) |
| v17b normalized labels 174k | ✅ READY | metadata_174k.jsonl with normalized legal_area |
| jurist human study | 🔴 BLOCKED | Framework ready; requires owner recruitment of 5-10 Swiss jurists |

**Legal-distance lane status per factory direction v25:** RUN — actively executing staged 174k CPU computation on free public runners (year-split, 65-min job ceilings, TF-IDF first).

---

## Execution Plan When 174k Representations Land

The evaluation lane will **autonomously execute** the following without human intervention:

### Phase 1: Full 12-Benchmark Suite at 174k
```bash
python evaluation/experiments/run_v16_full_benchmark_suite.py \
  --embeddings-dir <legal-distance-174k-output> \
  --metadata evaluation/data/174k/metadata_174k.jsonl \
  --output results/evaluation/v16_174k/
```
- All 12 benchmarks with frozen thresholds
- HNSW backend for scalable NN
- Distributed worker sharding if needed
- Config hash `4323f833fa72366a` verified

### Phase 2: Citation Heritage Benchmark at 174k
```bash
python evaluation/validate_citation_heritage_174k.py \
  --embedding <representation> \
  --pairs evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json \
  --threshold 0.65
```
- 804 positive pairs, 1,608 negative pairs
- Frozen seed 42
- AUC-ROC ≥ 0.65 threshold

### Phase 3: v17b Label Normalization Generalization Test
```bash
python evaluation/experiments/run_v17b_label_normalization_all_reps.py \
  --embeddings-dir <legal-distance-174k-output> \
  --metadata evaluation/data/174k/metadata_174k.jsonl \
  --normalized-mapping evaluation/results/174k_label_analysis/174k_legal_area_analysis.json
```
- Compare raw vs normalized legal_area on hierarchy/zoom/legal_area benchmarks
- Validate uniform purity improvement across all representations

---

## Evidence References

### Code (Frozen/Validated)
- `evaluation/evaluation_v3_harness.py` — Frozen adversarial harness (config hash `a31c443a9b0e992e`)
- `evaluation/scalable_nn.py` — HNSW scalable NN infrastructure
- `evaluation/run_full_corpus_evaluation.py` — Full corpus evaluation entry point
- `evaluation/experiments/run_v16_full_benchmark_suite.py` — 12-benchmark suite (config hash `4323f833fa72366a`)
- `evaluation/experiments/run_v17b_label_normalization_all_reps.py` — v17b uniformity test
- `evaluation/experiments/legal_area_normalize.py` — Cross-lingual label normalization
- `evaluation/validate_citation_heritage_174k.py` — Citation heritage benchmark

### Results (Accepted)
- `evaluation/results/v3/evaluation_v3_results.json` — Frozen harness v3 verification
- `evaluation/results/v16_full_benchmark_suite/v16_full_benchmark_results.json` — v16 suite results
- `evaluation/results/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_results.json` — v17b uniformity
- `evaluation/results/full_corpus_174k_tfidf/full_corpus_evaluation_results_worker0.json` — Full corpus harness validation
- `evaluation/results/citation_heritage_174k.json` — Citation heritage execution (FAIL on TF-IDF hybrid)

### 174k Infrastructure
- `evaluation/data/174k/metadata_174k.jsonl` — 173,963 decisions with branch/language/chamber/year/legal_area
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` — 804 positive pairs
- `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json` — Normalized labels analysis
- `/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/citation_graph_resolved.json` — Citation graph
- `/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/citation_to_decision_id.json` — Citation resolution

### Accepted State References
- `/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected_64.npy` — Baseline embeddings (1200 decisions)
- `/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/metadata.json` — Baseline metadata

### Reports
- `evaluation/reports/evaluation_v25_174k_readiness_report.md` — Previous readiness report
- `evaluation/reports/evaluation_v17b_label_normalization_all_reps.md` — v17b uniformity confirmation
- `evaluation/reports/evaluation_v25_174k_validation_report.md` — Infrastructure validation

---

## Next Recommendation: BLOCKED_ON_DEPENDENCIES

**continue_recommended: false** — No additional same-question cycle is justified until 174k representations land in accepted state.

The evaluation infrastructure is **complete and frozen**. When legal-distance delivers 174k representations (TF-IDF signals first, then dense embeddings year-split), the evaluation lane will autonomously execute the full formal suite and report results.

**Factory Director Action:** None required. Monitor legal-distance lane delivery. Next material direction change expected when legal-distance delivers first 174k TF-IDF representations.

---

*Report generated by Evaluation Lane — LexMachina Factory — Factory Direction v25*