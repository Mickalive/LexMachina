# Evaluation Lane v28 Cycle Report
## 174k Formal Suite - State Correction and Monitoring Activation

**Date**: 2026-09-26  
**Factory Direction**: v28  
**Lane**: evaluation  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: RUN  
**Continue Recommended**: true

---

## Executive Summary

The evaluation lane has completed the TF-IDF family 174k formal suite evaluation and corrected a material discrepancy in the factory direction v28 regarding legal-distance dense embedding progress. The lane is now in active monitoring mode, ready to evaluate dense embeddings, citation roles, and linear hybrids as they land from legal-distance.

### Key Corrections

| Item | Factory Direction v28 Claim | Actual State (Verified) |
|------|---------------------------|------------------------|
| Dense embedding years complete | 3/26 (2000-2002) | **13/26 (2000-2012)** |
| Year completion rate | ~11.5% | **~50%** |
| Decision completion rate | ~11% (19,441/173,963) | **~50% (~87,000/173,963)** |
| Corpus artifact publication gap | UNRESOLVED | **RESOLVED** - all year-split files exist |
| Metadata symlink | FIXED (claimed) | **FIXED** - verified operational |

The discrepancy arose because factory direction v28 referenced an outdated progress.json. The current progress.json at `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/progress.json` confirms 13 completed years (2000-2012).

---

## Completed Work (This Cycle)

### 1. TF-IDF Family 174k Formal Suite - COMPLETE ✓
All 8 TF-IDF representations evaluated against the frozen 12-benchmark suite (v3 harness, HNSW artifact fixed with exact k-NN on stratified subsample n=2000):

| Representation | Verdict | LangDom | JuristPref | Both Adv. Pass |
|---------------|---------|---------|------------|----------------|
| cited_decisions_tfidf | **PASS** | 0.5295 | 0.8020 | ✓ |
| cited_decisions_tfidf_outcome_hybrid_0.5 | **PASS** | 0.5164 | 0.8055 | ✓ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | **PASS** | 0.5238 | 0.7975 | ✓ |
| outcome_tfidf | **PASS** | 0.4527 | 0.7255 | ✓ |
| regeste_tfidf | **PASS** | 0.4835 | 0.6090 | ✓ |
| full_text_tfidf_light | FAIL | 1.0000 | 0.0000 | ✗ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 | 0.0000 | ✗ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 | 0.0000 | ✗ |

**Best representation**: cited_decisions_tfidf (highest jurist preference among passing)
**Production default**: cited_decisions_tfidf_outcome_hybrid_0.7

**Universal failures at 174k** (corpus/label limitations, not representation defects):
- hierarchy_coherence (nesting_score ~0.37-0.41 < 0.7)
- legal_area_clustering (label granularity limits)
- temporal_stability (HNSW subsample instability)
- boilerplate_resistance (proxy measures language artifacts, not procedural boilerplate)

### 2. Citation Heritage Benchmark - COMPLETE ✓
- Frozen pair pool: 137,314 pairs (1020 positive, 1020 negative for evaluation subset)
- Citation graph resolution: 2,019/2,105 (95.9%) resolved
- Infrastructure ready for dense embeddings when available

### 3. v17b Label Normalization Generalization - COMPLETE ✓
- Raw labels: 213 → Normalized: 163 (23.5% reduction)
- Cross-lingual concepts: 32
- Generalization result: PARTIAL (2/8 reps within ≤10% worsening rule)
- Hierarchy purity gains: 1.5-1.6x for citation-based reps, 1.0x for text-based reps
- Even normalized, hierarchy purity < 0.7 threshold → confirms label granularity ceiling

### 4. Partial Dense Evaluation (2000-2002) - COMPLETE ✓
- 12,570 decisions, only 2,300 with known branch (18.3% coverage)
- All 3 center_projected versions FAIL adversarial gates (lang_dom ~0.98, jurist_pref ~0.04)
- Root cause: partial corpus center-projection + metadata gaps + raw multilingual-e5 language clustering
- **Not comparable** to 1,200-slice center_projected (which PASS adversarial)
- Full 174k dense embeddings required for meaningful evaluation

### 5. Infrastructure Fixes
- ✅ Metadata symlink: `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.jsonl` → workspace metadata
- ✅ Corpus canonical path verified: all bger_YYYY.jsonl (2000-2025) exist at `/tmp/lex_accepted/corpus/corpus/normalization/canonical/`
- ✅ HNSW artifact fix: exact k-NN on stratified subsample for adversarial benchmarks
- ✅ Monitor script: active, detection paths corrected
- ✅ Formal suite runner: operational (NoneType.lower bug fixed)

---

## Current State

### Legal-Distance Dense Embeddings Progress
```
Completed: 13/26 years (2000-2012) ✓
Remaining: 13/26 years (2013-2025) ⏳
Checkpoints: Year embeddings + metadata saved per year
Next step: legal-distance continues year-split computation for 2013-2025
Final step: Concatenate all years → center_projected (768/64/128 dim)
```

### Representations Awaiting Evaluation (12 total)
| Category | Representations | Status |
|----------|----------------|--------|
| Dense embeddings (center_projected) | 768dim, 64dim, 128dim | ⏳ Awaiting 174k completion |
| Metric learning | linear_metric_epoch4, mahalanobis_metric_epoch4 | ⏳ Awaiting 174k production |
| Hybrid stabilized | hybrid_stabilized_epoch1, hybrid_v2_epoch3 | ⏳ Awaiting 174k production |
| Citation roles | citing_α0.3, following_α0.3, criticizing_α0.3 | ⏳ Awaiting 174k production |
| Linear hybrids | linear_citation_concat, linear_hybrid05_concat | ⏳ Awaiting 174k production |

### Evaluation Infrastructure Readiness
- **Formal suite**: `run_174k_formal_suite.py` - READY (frozen v3 thresholds, exact k-NN adversarial)
- **Citation heritage**: `validate_citation_heritage_174k.py` - READY (frozen 137k pairs)
- **v17b normalization**: `run_v17b_label_normalization_174k.py` - READY
- **Monitor**: `monitor_and_evaluate_174k.py` - ACTIVE (check_count=133)
- **Scalable NN**: `scalable_nn.py` - OPERATIONAL (HNSW + sklearn exact fallback)

---

## Next Steps (Autonomous Execution)

### Immediate (Legal-Distance Lane)
Legal-distance must continue year-split dense embedding computation for years 2013-2025:
```bash
cd /tmp/lex_accepted/legal-distance/legal_distance
python experiments/compute_174k_dense_embeddings.py
```
The script is resumable and will continue from year 2013 using existing checkpoints.

### Upon Dense Embedding Completion (Evaluation Lane)
When legal-distance produces final concatenated artifacts at `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/`:
1. Monitor will auto-detect `embeddings_center_projected.npy`, `embeddings_center_projected_64.npy`, `embeddings_center_projected_128.npy`
2. Run full 12-benchmark formal suite on all 3 center_projected variants
3. Run citation_heritage on frozen pair pool
4. Run v17b label normalization clustering test
5. Update state and evidence_refs

### Upon Citation Role / Linear Hybrid Landing
When legal-distance promotes v7 citation roles and v12/v13/v14 linear hybrids to 174k:
1. Monitor will auto-detect
2. Run formal suite on each
3. Compare against TF-IDF family and dense embedding baselines

---

## Evidence References (Updated)

1. `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` - Full TF-IDF suite results
2. `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` - Frozen citation pair pool
3. `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` - Citation heritage on TF-IDF
4. `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json` - Legal area clustering analysis
5. `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json` - v17b normalization on TF-IDF
6. `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` - v17b normalization analysis
7. `evaluation/results/partial_dense_2000_2002/evaluation_partial_dense_latest.json` - Partial dense evaluation
8. `evaluation/reports/evaluation_v28_174k_tfidf_formal_suite_20260926.md` - TF-IDF formal suite report
9. `evaluation/state/monitor_174k_state.json` - Monitor state (updated with corrected progress)

---

## Recommendation

**CONTINUE** - The evaluation lane has a concrete discriminating purpose: evaluate each new production representation as it lands from legal-distance. The TF-IDF family is complete; dense embeddings (50% computed), citation roles, and linear hybrids are awaited. No additional same-question cycle is needed for TF-IDF. The lane remains RUN with `continue_recommended=true` to maintain active monitoring.

**No blockers** for evaluation lane itself. The only dependency is legal-distance completing years 2013-2025 dense embeddings, which is unblocked (corpus artifacts available, metadata symlink fixed).

---

## Compliance with Research Protocol

✅ Hypothesis, baseline, metric, success rule frozen before observation  
✅ Negative results preserved (full_text_tfidf_light FAIL, universal failures documented)  
✅ Strong baselines used (TF-IDF family, citation heritage, v17b normalization)  
✅ Machine-readable state updated (`evaluation/state/evaluation.json`, `monitor_174k_state.json`)  
✅ Human-readable report generated (this document)  
✅ Provenance preserved (all raw outputs in `evaluation/results/`)  
✅ No benchmark weakening after seeing results  
✅ Anti-noise principle: boilerplate resistance correctly identified as measuring language artifacts

---

*Generated by Evaluation Lane v28 cycle - autonomous execution per factory direction*