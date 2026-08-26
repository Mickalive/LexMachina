# Evaluation Lane Repair Report — Cycle 33023404622, Round 2

**Run ID:** eval_repair_33023404622_r2  
**Date:** 2026-08-26  
**Lane:** evaluation  
**Direction version:** 1  
**Prior Audit:** CYCLE_33023404622 (REVISE gate)  
**Repair Target:** Two required_fixes items from prior audit

---

## 1. Executive Summary

This repair addresses two defects flagged in audit CYCLE_33023404622 (round 2):

1. **REQUIRED FIX — branch_distribution labeling** (medium severity, recurring): The `branch_distribution` field in legal-area clustering results reported the full embedding set composition (1,000 decisions) instead of the sampled subset (500 decisions) used in the benchmark. Fixed in both `run_cycle_5.py` (line 428) and `evaluation/tests/legal_area_clustering.py` (line 212).

2. **MINOR — state metrics not updated after verification** (low severity): The state file `metrics_summary` referenced original run values for citation proximity AUC (0.5102) and neighbor relevance AUC (0.5564) while the verification file contained updated values (0.5737, 0.5174). Fixed in `state/evaluation.json`.

**Gate Decision:** All required fixes applied. No frozen baselines, data, metrics, success rules, or scope weakened.

---

## 2. Required Fix 1: branch_distribution Labeling

### Problem
The `branch_distribution` field in legal-area clustering results was computed from `valid_branches` — the full set of decisions per branch across the entire embedding set (1,000 decisions). The benchmark itself operates on a sampled subset of 500 balanced decisions. This made the reported distribution misleading: it showed the corpus composition, not the benchmark sample composition.

**Root cause:** Line 428 in `run_cycle_5.py` (and line 212 in `legal_area_clustering.py`) used:
```python
"branch_distribution": {b: len(ids) for b, ids in valid_branches.items()},
```

### Fix Applied
Changed to compute distribution from `sampled_labels` (the branch assignment for each sampled decision) filtered to `valid_ids` (decisions that successfully obtained embeddings):
```python
"branch_distribution": dict(Counter(sampled_labels[did] for did in valid_ids)),
```

### Files Modified
| File | Line | Change |
|------|------|--------|
| `evaluation/run_cycle_5.py` | 428 | `valid_branches` → `Counter(sampled_labels[did] for did in valid_ids)` |
| `evaluation/tests/legal_area_clustering.py` | 212 | Same fix in shared benchmark class |

### Why This Is Correct
- `sampled_labels` is populated at lines 335-343 (run_cycle_5.py) / lines 103-112 (legal_area_clustering.py) during balanced sampling across branches
- `valid_ids` is a subset of `sampled_ids`, all of which are keys in `sampled_labels`
- The resulting distribution sums to `len(valid_ids)`, matching `num_decisions`
- `Counter` is already imported in both files (line 33 and line 25 respectively)

### Impact
- **Does NOT affect** NMI, purity, or any other benchmark calculation (these use `true_labels` derived from `sampled_labels` — already correct)
- **Affects only** the `branch_distribution` metadata field, which is informational
- The reported distribution will now correctly sum to the sampled subset size (~500) instead of the full embedding set (1,000)

### Verification
- Syntax check: both files parse without errors
- All remaining `valid_branches` references in both files are legitimate (used for sampling, filtering, and counting branches — not for distribution reporting)

---

## 3. Required Fix 2: State Metrics Update

### Problem
The state file `state/evaluation.json` had `metrics_summary.neural_multilingual_baseline` and `baselines_established.neural_multilingual` referencing original run values:
- `citation_proximity_auc`: 0.5102 (original) vs 0.5737 (verification)
- `neighbor_relevance_auc`: 0.5564 (original) vs 0.5174 (verification)

### Fix Applied
Updated both locations to reflect verification values (from run `eval_cycle_5_1787786969`):
- `citation_proximity_auc`: 0.5102 → **0.5737**
- `neighbor_relevance_auc`: 0.5564 → **0.5174**
- Added note to `neural_multilingual_baseline` clarifying values are from verification run

### Impact
State file now consistently reflects the latest verified values. No change to benchmark logic or results files.

---

## 4. What Did NOT Change

Per the audit gate, the following were verified as unchanged:
- **Frozen baselines:** All benchmark thresholds (AUC > 0.75, NMI > 0.3, purity > 0.7, drift < 0.3) remain identical
- **Frozen corpus:** Same 1,000 BGer decisions (2020-2024)
- **Frozen model:** sentence-transformers/paraphrase-multilingual-mpnet-base-v2 (768-dim)
- **Benchmark results:** All NMI, purity, AUC, drift, and separation values unchanged
- **Claim ceiling:** Unchanged ("Two baselines established...")
- **Scope:** Evaluation lane only; no cross-lane modifications

---

## 5. Files Modified This Cycle

| File | Purpose | Delta |
|------|---------|-------|
| `evaluation/run_cycle_5.py` | Cycle 5 execution script | 1 line changed (L428) |
| `evaluation/tests/legal_area_clustering.py` | Shared benchmark | 1 line changed (L212) |
| `state/evaluation.json` | Lane state | 4 values updated, 3 lines added to required_fixes_addressed, 1 cycle_history entry added |
| `reports/evaluation/evaluation_repair_33023404622_r2.md` | This report | New file |

---

## 6. Recommendation

**PASS** — Both required fixes from audit CYCLE_33023404622 are applied. The branch_distribution field now correctly reports the sampled subset composition. The state file metrics reflect verification values. No frozen baselines, data, metrics, or scope were weakened. The evaluation lane remains DONE with all 7 benchmarks and 2 baselines intact.

---

*Prepared by: evaluation_lane_repair*  
*Provenance: Code edit + state file update, verified via syntax check and logic trace*
