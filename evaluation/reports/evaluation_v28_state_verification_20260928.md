# Evaluation Lane - State Verification Report (Factory Direction v28)

**Date**: 2026-09-28  
**Direction Version**: 28  
**Run ID**: evaluation_v28_174k_tfidf_formal_suite_20260928  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Continue Recommended**: false  

---

## Executive Summary

The evaluation lane has completed all three assigned sub-questions for the 174k formal suite and is now **blocked on legal-distance 174k dense embeddings audit promotion**. Only 3/26 years (2000-2002, ~19,441 decisions) of dense embeddings are ACCEPTED; 22/26 years (2003-2024, ~154k decisions) exist in checkpoints but remain PENDING AUDIT; years 2025-2026 not yet processed.

**Monitor verification (check #206)**: No new awaited representations detected in accepted mount. Legal-distance checkpoints confirm 25/26 years completed but only 2000-2002 promoted through audit gate.

---

## Sub-Question Status

| Sub-Question | Status | Key Result |
|--------------|--------|------------|
| 1. 12-benchmark formal suite at 174k | **COMPLETE** | 8 TF-IDF representations evaluated with frozen harness v3; HNSW artifact fixed via exact k-NN on stratified subsample (n=2000 valid decisions) |
| 2. Citation heritage benchmark | **COMPLETE** | Frozen pair pool validated (137,314 pairs, 95.9% citation resolution); TF-IDF citation-based AUC 0.76-0.79 but recall@10 < 0.2 (FAIL); text-based AUC ~0.49 (FAIL) |
| 3. v17b label normalization | **COMPLETE** | 213→163 labels (23.5% reduction), 32 cross-lingual concepts; PARTIAL generalization (5/8 reps within ≤10% worsening on zoom_fine; text-based reps degrade 30-34%) |
| 4. Partial dense evaluation (2000-2002) | **COMPLETE** | 3 center_projected variants (768/64/128dim) on 12,570 decisions: ALL FAIL adversarial (lang_dom ~0.98, jurist_pref ~0.04). Root cause: 18.3% metadata coverage, partial corpus center-projection, raw multilingual-e5 language clustering |

---

## TF-IDF Formal Suite Results at 174k (Frozen Harness v3, HNSW Artifact Fixed)

### Adversarial Gate Results (EXACT k-NN on stratified subsample n=2000)

| Representation | Language Dominance | Jurist Preference | Both Pass | Verdict |
|---------------|-------------------|-------------------|-----------|---------|
| cited_decisions_tfidf | 0.529 ✓ | 0.802 ✓ | ✓ | **PASS** |
| outcome_tfidf | 0.453 ✓ | 0.726 ✓ | ✓ | **PASS** |
| regeste_tfidf | 0.484 ✓ | 0.609 ✓ | ✓ | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.516 ✓ | 0.806 ✓ | ✓ | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.524 ✓ | 0.798 ✓ | ✓ | **PASS** |
| full_text_tfidf_light | 1.000 ✗ | 0.000 ✗ | ✗ | FAIL |
| regeste_full_text_hybrid_0.5 | 1.000 ✗ | 0.000 ✗ | ✗ | FAIL |
| regeste_full_text_hybrid_0.7 | 1.000 ✗ | 0.000 ✗ | ✗ | FAIL |

**Thresholds (frozen)**: Language dominance < 0.85, Jurist preference > 0.5

### Production Default
- **Representation**: `cited_decisions_tfidf_outcome_hybrid_0.5`
- **Status**: PASS (both adversarial gates)
- **Language dominance**: 0.5164
- **Jurist preference**: 0.8055
- **Citation heritage AUC**: 0.7597
- **Citation heritage recall@10**: 0.0529
- **v17b zoom_fine ratio**: 1.0366 (within ≤10% worsening rule)

---

## Citation Heritage Benchmark (174k)

**Frozen pair pool**: 137,314 pairs, 95.9% citation resolution (2,019/2,105 resolved)

| Representation | AUC | Recall@10 | Status |
|---------------|-----|-----------|--------|
| cited_decisions_tfidf | 0.788 | 0.044 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.760 | 0.053 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.775 | 0.049 | FAIL |
| full_text_tfidf_light | 0.898 | 0.052 | FAIL |
| regeste_tfidf | 0.486 | 0.000 | FAIL |
| outcome_tfidf | 0.658 | 0.000 | FAIL |

**Finding**: NEGATIVE at 174k for ALL TF-IDF representations. No representation achieves both AUC > 0.6 AND recall@10 > 0.2. Citation-based representations have good AUC but extremely low recall; text-based representations have higher AUC but near-zero recall.

---

## v17b Label Normalization (174k Legal Areas)

- **Raw labels**: 213 → **Normalized**: 163 (23.5% reduction)
- **Cross-lingual mappings**: 32 concepts (e.g., contract_law: "Vertragsrecht"/"Droit des contrats"/"Diritto contrattuale")
- **Labels changed**: 85,819 decisions

### Generalization Results

| Representation | Hierarchy Purity Δ | Zoom Fine Δ | Legal Area Purity Δ | Within ≤10% Rule |
|---------------|-------------------|-------------|---------------------|------------------|
| cited_decisions_tfidf | +5.7% | +3.8% | +6.2% | ✓ |
| outcome_tfidf | +4.6% | +8.3% | +4.4% | ✓ |
| regeste_tfidf | 0% | +10.3% | +1.7% | ✗ (zoom_fine) |
| full_text_tfidf_light | 0% | **-33.2%** | -2.7% | ✗ (zoom_fine) |
| cited_outcome_hybrid_0.5 | +5.6% | +3.7% | +6.3% | ✓ |
| cited_outcome_hybrid_0.7 | +5.3% | +4.6% | +5.8% | ✓ |
| regeste_full_text_hybrid_0.5 | 0% | **-33.9%** | -2.8% | ✗ (zoom_fine) |
| regeste_full_text_hybrid_0.7 | 0% | **-30.5%** | -3.7% | ✗ (zoom_fine) |

**Finding**: v17b normalization **improves** hierarchy/legal_area purity for citation-based representations (5-7% gain) but **degrades** zoom_fine for text-based representations (30-34% loss). 5/8 representations pass the ≤10% worsening rule on zoom_fine.

---

## Partial Dense Evaluation (Years 2000-2002, 12,570 decisions)

All three center_projected variants **FAIL adversarial gates**:

| Variant | Language Dominance | Jurist Preference | Verdict |
|---------|-------------------|-------------------|---------|
| center_projected_768dim | 0.981 ✗ | 0.040 ✗ | FAIL |
| center_projected_64dim | 0.978 ✗ | 0.045 ✗ | FAIL |
| center_projected_128dim | 0.980 ✗ | 0.041 ✗ | FAIL |

**Root cause analysis**:
- Only 18.3% metadata coverage (2,300/12,570 decisions have known branch)
- Partial corpus center-projection (not full 174k)
- Raw multilingual-e5 embeddings cluster by language, not legal content
- **NOT comparable** to 1,200-slice center_projected (which PASSES adversarial with proper full-corpus projection)

---

## Key Findings (Reproduced)

1. **Fundamental Tradeoff**: TF-IDF at 174k shows persistent two-mode tradeoff:
   - Citation-based reps: PASS adversarial (lang_dom~0.53, jurist_pref~0.80) but FAIL branch/hierarchy
   - Text-based reps: PASS branch/legal_area but FAIL adversarial (lang_dom=1.0)

2. **Citation Heritage**: NEGATIVE at 174k for all TF-IDF reps - no representation achieves both AUC>0.6 AND recall@10>0.2

3. **v17b Normalization**: Improves hierarchy/legal_area purity for citation-based reps (5-7% gain) but DEGRADES zoom_fine for text-based reps (30-34% loss)

4. **HNSW Artifact**: CONFIRMED AND FIXED - HNSW with fixed params produces nearly identical k-NN graphs across TF-IDF reps at 174k; exact k-NN on valid subset used for adversarial benchmarks

5. **Scale Dependency**: Partial dense (12k) FAILS adversarial; 1,200-slice center_projected PASSES. Scale/metadata coverage critical for dense embeddings.

---

## Blocked Dependencies

1. **legal-distance: 174k dense embeddings**
   - 3/26 years ACCEPTED (2000-2002, ~19,441 decisions)
   - 22/26 years (2003-2024, ~154k decisions) in checkpoints PENDING AUDIT
   - 2/26 years (2025-2026) not yet processed

2. **legal-distance: citation role embeddings at 174k** (awaits dense completion)

3. **legal-distance: linear hybrid embeddings at 174k** (awaits dense completion)

---

## External Dependencies

- **Jurist human study**: Framework ready, requires 5-10 Swiss jurists (recruitment by repository owner required)

---

## Next Steps

**No further evaluation cycles recommended** under current factory direction v28. The evaluation lane will remain BLOCKED_ON_DEPENDENCIES until legal-distance promotes 174k dense embeddings through audit. Upon promotion, `monitor_and_evaluate_174k.py` will auto-detect and evaluate new representations.

**Recommendation to Factory Director**: Prioritize legal-distance audit promotion for years 2003-2024 dense embeddings to unblock evaluation, fractal-map, and product lanes.

---

## Evidence References (Machine-Readable)

All results preserved in:
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json`
- `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json`
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `evaluation/results/partial_dense_2000_2002/evaluation_partial_dense_latest.json`
- `evaluation/state/monitor_174k_state.json` (check_count=206)

---

*This report accompanies machine-readable state at `state/evaluation.json`. Negative results preserved as first-class evidence per Research Protocol.*