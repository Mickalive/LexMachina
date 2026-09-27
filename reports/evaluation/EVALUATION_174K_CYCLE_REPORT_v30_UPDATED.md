# Evaluation Lane Cycle Report - v30 Update

**Date**: 2026-09-27  
**Factory Direction**: v30  
**Lane Status**: BLOCKED_ON_DEPENDENCIES (unchanged)  
**Evidence Tier**: REPRODUCED  

## Summary

Completed citation_heritage benchmark evaluation on 16-year partial dense embeddings (2000-2015, 99,325 decisions). This advances the machine-executable 174k formal suite sub-question (2): "validate citation_heritage benchmark using the published 174k citation-ID resolution" to the available dense representations as they land.

## Work Completed

### Citation Heritage on Partial Dense Embeddings (2000-2015)

| Representation | AUC-ROC | Recall@10 | AUC Pass (≥0.65) | Recall Pass (≥0.2) | Status |
|----------------|---------|-----------|------------------|--------------------|--------|
| multilingual_e5_768dim_partial_2000_2015 | 0.9105 | 0.014 | ✅ | ❌ | FAIL |
| center_projected_768dim_partial_2000_2015 | 0.9047 | 0.000 | ✅ | ❌ | FAIL |
| center_projected_128dim_partial_2000_2015 | 0.9053 | 0.000 | ✅ | ❌ | FAIL |
| center_projected_64dim_partial_2000_2015 | 0.9057 | 0.000 | ✅ | ❌ | FAIL |

**Key Findings**:
- All 4 dense partial representations **PASS AUC** (>0.65 threshold) with stable scores ~0.90-0.91
- All 4 **FAIL recall@10** (>0.2 threshold) with near-zero recall (0.000-0.014)
- Pattern **consistent with TF-IDF 174k results**: all 8 TF-IDF representations at full 174k scale also passed AUC but failed recall@10
- Center-projection does not significantly change citation heritage performance (AUC stable, recall remains near zero)
- 13,648 positive citation pairs and 45,070 negative pairs in the 2000-2015 subset

### Infrastructure & Methods

- **Frozen pair pool**: 137,314 positive + 137,314 negative pairs from 174k citation graph (95.9% resolution: 2,019/2,105)
- **Subset filtering**: Pairs filtered to decisions in 2000-2015 subset (99,325 decisions)
- **AUC computation**: Vectorized cosine similarity on filtered pairs
- **Recall@10**: HNSW/Exact k-NN via scalable_nn infrastructure (1,000 sampled queries)
- **HNSW artifact fix**: Exact k-NN (sklearn) used for 99k-scale evaluation (no HNSW approximation)

### Previously Completed (Unchanged)

1. **12-benchmark formal suite at 174k** (TF-IDF family): COMPLETE - 8 representations, 5 PASS both adversarial gates
2. **Citation heritage at 174k** (TF-IDF family): COMPLETE - all 8 FAIL recall@10
3. **v17b label normalization at 174k**: COMPLETE - PARTIAL generalization (2/8 reps within ≤10% worsening)
4. **16-year center-projected formal suite**: COMPLETE - significant improvement over 3-year partial (lang_dom 0.98→0.87, jurist_pref 0.04→0.30)

## Current Blockers

**Lane remains BLOCKED_ON_DEPENDENCIES** for:
- Full 174k dense embeddings (legal-distance: 16/26 years complete, 2000-2015; years 2016-2025 pending)
- Citation role embeddings (citing, following, criticizing) at 174k scale
- Linear hybrids (linear_metric, mahalanobis, hybrid_stabilized, hybrid_v2, linear_citation_concat, linear_hybrid05_concat) at 174k scale

## Evidence Artifacts

- `/evaluation/results/174k_citation_heritage/citation_heritage_multilingual_e5_768dim_partial_2000_2015.json`
- `/evaluation/results/174k_citation_heritage/citation_heritage_center_projected_768dim_partial_2000_2015.json`
- `/evaluation/results/174k_citation_heritage/citation_heritage_center_projected_128dim_partial_2000_2015.json`
- `/evaluation/results/174k_citation_heritage/citation_heritage_center_projected_64dim_partial_2000_2015.json`
- `/evaluation/run_citation_heritage_partial_dense_fast.py` (new evaluation script)
- `/evaluation/state/evaluation.json` (updated with sub_question_results.partial_dense_2000_2015_citation_heritage)
- `/evaluation/state/monitor_174k_state.json` (check_count=144, completed_evaluations updated)

## Next Steps

1. **Monitor legal-distance progress**: Wait for years 2016-2025 dense embedding checkpoints
2. **When full 174k dense embeddings land**: Run full formal suite (12 benchmarks) + citation_heritage on:
   - center_projected_{64,128,768}dim_174k
   - linear_metric_epoch4_174k, mahalanobis_metric_epoch4_174k
   - hybrid_stabilized_epoch1_174k, hybrid_v2_epoch3_174k
   - citation_role_{citing,following,criticizing}_174k
   - linear_citation_concat_174k, linear_hybrid05_concat_174k
3. **Jurist human study**: Framework ready, blocked on recruitment (5-10 Swiss jurists)

## Recommendation

**CONTINUE monitoring** (continue_recommended=false in state = no additional same-question cycle justified; Factory Director decides successor question). The three machine-executable sub-questions from factory direction v30 are COMPLETE for all available representations. Lane correctly remains BLOCKED_ON_DEPENDENCIES pending legal-distance deliverables.