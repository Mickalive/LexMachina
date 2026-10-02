# v17b Label Normalization at 174k — Two Normalization Regimes Clarification

**Date:** 2026-10-02  
**Lane:** evaluation  
**Factory Direction Version:** 29  
**Purpose:** Clarify audit finding that two distinct v17b normalization experiments exist at 174k with different label regimes.

---

## Summary of Two Experiments

| Aspect | Experiment A: `v17b_174k_generalization` | Experiment B: `v17b_174k_tfidf` |
|--------|------------------------------------------|----------------------------------|
| **Script** | `test_v17b_174k_generalization.py` | `run_v17b_label_normalization_174k.py` / `experiments/run_v17b_174k_tfidf.py` |
| **Normalization Function** | Inline v17b method (keyword-based, ~16 categories) | `legal_area_normalize.py` (different keyword mapping) |
| **Raw Unique Labels** | 213 | 157 |
| **Normalized Unique Labels** | 111 | 107 |
| **Compression Ratio** | 213 → 111 (1.9x) | 157 → 107 (1.5x) |
| **Purity Ratios (norm/raw)** | 4.7x – 10x (hierarchy/zoom/legal_area) | 1.0x – 1.67x (hierarchy/zoom/legal_area) |
| **NMI Change** | Decreases for all reps | Decreases for most metrics |
| **Subsample** | Stratified by legal_area (15k) | Stratified by branch (15k) |
| **Key Difference** | Raw labels include all 213 legal_area values; normalization maps to ~16 coarse categories | Raw labels filtered to 157 (decisions with known branch+legal_area); normalization uses different keyword rules |

---

## Why They Differ

1. **Different normalization functions**: 
   - `test_v17b_174k_generalization.py` defines its own inline `normalize_legal_area()` with ~16 coarse categories (steuerrecht, sozialversicherungsrecht, verwaltungsrecht, etc.)
   - `legal_area_normalize.py` (used by `run_v17b_174k_tfidf.py`) has a different keyword mapping that produces 107 categories from 157 raw

2. **Different label populations**:
   - Experiment A uses ALL decisions with legal_area labels (213 unique raw labels)
   - Experiment B uses only decisions that ALSO have known branch metadata (157 unique raw labels) — this is a subset filtered by the branch-stratified subsampling

3. **Different subsampling strategies**:
   - Experiment A: stratified by legal_area label
   - Experiment B: stratified by court branch

---

## Results Comparison

### Experiment A (`v17b_174k_generalization`) — 213 → 111 labels

| Representation | Hierarchy Ratio | Zoom Fine Ratio | Legal Area Ratio | Generalization |
|----------------|-----------------|-----------------|------------------|----------------|
| cited_decisions_tfidf | 5.18x | 6.47x | 6.47x | FAIL |
| outcome_tfidf | 10.07x | 10.07x | 10.07x | FAIL |
| regeste_tfidf | 6.64x | 7.84x | 7.84x | FAIL |
| full_text_tfidf_light | 4.70x | 5.89x | 5.89x | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 5.20x | 6.68x | 6.68x | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 5.20x | 6.60x | 6.60x | FAIL |
| regeste_full_text_hybrid_0.5 | 5.09x | 6.31x | 6.31x | FAIL |
| regeste_full_text_hybrid_0.7 | 5.53x | 7.27x | 7.27x | FAIL |

**Overall:** Large purity gains (4.7x-10x) but NMI decreases → **does not generalize** v17b 1K findings to 174k fine-grained regime.

### Experiment B (`v17b_174k_tfidf`) — 157 → 107 labels

| Representation | Hierarchy Purity | Zoom Fine | Legal Area | NMI (hierarchy) | NMI (legal_area) |
|----------------|------------------|-----------|------------|-----------------|------------------|
| cited_decisions_tfidf | 1.48x | 1.50x | 1.26x | 0.95x | 0.83x |
| outcome_tfidf | 1.50x | 1.50x | 1.50x | 0.88x | 0.88x |
| regeste_tfidf | 1.67x | 1.67x | 1.67x | N/A | N/A |
| full_text_tfidf_light | 1.00x | 1.00x | 0.97x | 0.70x | 0.79x |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 1.43x | 1.50x | 1.26x | 0.85x | 0.73x |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 1.44x | 1.47x | 1.29x | 1.06x | 0.79x |
| regeste_full_text_hybrid_0.5 | 1.00x | 1.00x | 0.97x | 0.70x | 0.79x |
| regeste_full_text_hybrid_0.7 | 1.00x | 1.00x | 0.97x | 0.70x | 0.79x |

**Overall:** Modest purity gains (1.0x-1.67x) but NMI consistently decreases → **uniform improvement FALSE**; normalization helps purity but hurts semantic coherence (NMI).

---

## Correct Characterization

**Previous reports conflated these two experiments**, citing Experiment A's large ratios (4-10x) while not acknowledging Experiment B's different normalization and results.

**Correct statement:**
- v17b label normalization was REPRODUCED at 1K scale (15-25% purity gain, 4 seeds, using `legal_area_normalize.py`)
- At 174k, two different normalization regimes were tested:
  1. **Experiment A (inline v17b keywords)**: 213→111 labels, 4.7x-10x purity ratios, but NMI decreases — **different regime from v17b 1K, does not generalize**
  2. **Experiment B (legal_area_normalize.py)**: 157→107 labels, 1.0x-1.67x purity ratios, NMI decreases — **same normalization as v17b 1K but different label population; uniform improvement FALSE**

**Conclusion:** v17b label normalization does not robustly generalize to 174k fine-grained legal_area labels under either normalization regime. The 15-25% gain observed at 1K scale (with coarser labels and different corpus) does not replicate at 174k scale with 157-213 fine-grained labels.

---

## Evidence References

- Experiment A: `evaluation/results/v17b_174k_generalization/v17b_174k_generalization_20260930_011927.json`
- Experiment B: `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json`
- v17b 1K reference: `results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_results.json`
- Normalization functions: `evaluation/experiments/legal_area_normalize.py` and inline in `test_v17b_174k_generalization.py`