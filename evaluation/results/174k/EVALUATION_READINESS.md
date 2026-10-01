# Evaluation Lane Readiness for 174k Dense Embeddings

## Status: READY

The evaluation lane is fully prepared to run the 174k formal suite on new representations as they land from legal-distance.

## Verified Infrastructure

### 1. Formal Suite Harness (run_174k_formal_suite.py)
- **Status**: Operational
- **HNSW Artifact Fix**: Exact k-NN on fixed stratified subsample (n≈2000) for adversarial benchmarks
- **Full-corpus benchmarks**: HNSW on subsamples (temporal_stability: 30k, hierarchy: 15k)
- **Frozen thresholds**: Language dominance < 0.85, Jurist pairwise > 0.5, Cross-lang recall > 0.2, Cluster coherence > 0.7
- **Config hash**: b51701f5a9c11692 (direction_version 29)

### 2. Citation Heritage Validation (validate_citation_heritage_174k.py)
- **Status**: Validated
- **Frozen pair pool**: 1,020 positive + 1,020 negative citation pairs
- **Citation resolution**: 2,019/2,105 (95.9%) resolved
- **Ready for**: Any 174k-scale embeddings

### 3. Adversarial Benchmarks
- **Language dominance**: Verified working (PASS at 0.482 for production default)
- **Jurist pairwise preference**: Verified working (PASS at 0.860 for production default)
- **Cross-language**: Exact k-NN on stratified subsample
- **Cluster coherence**: 16 clusters, branch vs language purity
- **Cross-language retrieval**: Top-10 recall at k=10

### 4. Full-Corpus Benchmarks (HNSW)
- **Temporal stability**: 30k subsample, neighbor overlap on 80% corpus reduction
- **Hierarchy coherence**: 15k stratified subsample, Jurivoc proxy (4 branches → 16 legal areas)
- **Cluster coherence**: 15k subsample, 16 clusters, branch/language purity
- **Cross-language retrieval full**: 15k subsample, HNSW index
- **Boilerplate resistance**: Full corpus HNSW, legal vs boilerplate neighbor rates

### 5. v17b Label Normalization Pipeline
- **Status**: Tested and documented
- **1000-scale**: REPRODUCED (15-25% gain, 4 seeds, 6 representations)
- **174k generalization**: TESTED NEGATIVE (different regime: 213→111 labels, purity ratios 4-10x but NMI decreases)
- **Pipeline**: Ready for new representations if needed

### 6. v18 Coarse Hierarchy Test
- **Status**: Validated as NEGATIVE result
- **4-label branch level**: Best purity 0.65 < 0.7 threshold
- **Representations tested**: 6 (all TF-IDF/citation families)
- **Conclusion**: Fundamental hierarchy limitation confirmed

## Awaiting From Legal-Distance

The following representations are expected when legal-distance delivers 174k dense embeddings:

| Representation | Scale | Status | Expected Evaluation |
|---------------|-------|--------|---------------------|
| center_projected (768/128/64 dim) | 174k | BLOCKED (ID mismatch) | Full formal suite |
| Metric learning (linear/Mahalanobis/hybrid) | 174k | PENDING | Full formal suite |
| Citation role (citing/following/criticizing/neutral) | 174k | PENDING | Full formal suite + citation heritage |
| Linear hybrids (linear_hybrid05_concat, etc.) | 174k | PENDING | Full formal suite |
| Section-specific (sachverhalt/erwaegungen/dispositiv) | 174k | PENDING | Cross-lingual + formal suite |

## Current Checkpointed (PENDING AUDIT) - Legal-Distance
- 19 years checkpointed (2000-2018, ~122k decisions): center_projected evaluated at 15yr/19yr
- 3 years ACCEPTED (2000-2002, ~19k decisions): 12k dense embeddings available
- Missing: 2019, 2025, 2026 (not processed)

## Execution Protocol for New Representations

When a new 174k representation lands:

1. **Place embedding file** in `/home/runner/work/LexMachina/LexMachina/evaluation/results/174k/embeddings/`
2. **Update REPRESENTATIONS dict** in `run_174k_formal_suite.py` with new entry
3. **Run formal suite**: `python evaluation/run_174k_formal_suite.py`
4. **Run citation heritage**: `python evaluation/validate_citation_heritage_174k.py` (then run citation_heritage benchmark)
5. **Results saved** to `evaluation/results/174k/formal_suite/` with timestamp
6. **Update evaluation.json state** with new evidence_refs and findings

## Production Default (Baseline for Comparison)

**cited_decisions_tfidf_outcome_hybrid_0.5**
- Language dominance: 0.4773 (PASS)
- Jurist preference: 0.7345 (PASS)
- Citation heritage AUC: 0.7163 (PASS)
- Temporal stability: 0.381 (FAIL) - but full_text_tfidf_light: 0.781 (PASS)
- Production serving default in product lane

## Key Findings to Communicate to Legal-Distance

1. **Two-mode tradeoff persists at all scales**: Citation-based signals dominate jurist preference and citation heritage; text-based signals have poor cross-language retrieval
2. **Center_projected FAILS jurist gate at 174k** (JP=0.39-0.42) - needs metric learning or hybrid to improve
3. **Linear_hybrid05_concat shows scale dependency**: 15yr FAIL, 19yr PASS but below TF-IDF baseline
4. **Sachverhalt section superior** for cross-lingual alignment - should be prioritized in section-specific embeddings
5. **All dense embeddings show negative boilerplate resistance** (-0.84 to -0.93) - proxy measures language dominance, not procedural boilerplate

## Next Actions

- [ ] Monitor legal-distance for 174k dense embedding delivery
- [ ] Run formal suite immediately when new representations land
- [ ] Update evaluation state with new results
- [ ] Report to Factory Director for integration decisions