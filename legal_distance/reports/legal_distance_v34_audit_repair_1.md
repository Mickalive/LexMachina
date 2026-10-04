# Legal Distance Lane v34 - Audit Repair Cycle 1 Report

**Audit Cycle**: 37239653489  
**Repair Round**: 1  
**Timestamp**: 2026-10-04  
**Status**: REPAIRS APPLIED - Ready for re-audit

---

## Summary

All three required fixes from audit CYCLE_37239653489 (gate=REVISE) have been implemented and verified:

| Issue | Severity | Status | Verification |
|-------|----------|--------|--------------|
| Comprehensive validation JP anomaly | HIGH | ✅ FIXED | v5 baseline JP=0.4892 (consensus ~0.53) |
| Citation role integration fractal collapse | HIGH | ✅ FIXED | Base roles FAIL_DEGENERATE, alpha-blended PASS |
| Overclustering gate missing | MEDIUM | ✅ FIXED | Verdict requires valid_representation=true |

---

## Fix 1: Comprehensive Validation JP Anomaly

### Root Cause
The `v6_comprehensive_validation.py` script created a NEW `center_projected` representation from 384-dim ST embeddings (paraphrase-multilingual-MiniLM-L12-v2 on erwaegungen section) instead of using the SAME v5 baseline `center_projected` (768-dim, 1200 decisions) used by all other evaluations.

The ST-based embeddings gave anomalously high JP=0.9817 because the multilingual model is optimized for cross-lingual alignment on reasoning text, creating artificially high cross-lingual legal relevance.

### Fix Applied
Created `v6_comprehensive_validation_fixed.py` that:
1. Loads the v5 baseline `center_projected` (768-dim) as the PRIMARY baseline experiment
2. Adds the ST-based variant as a SEPARATE experiment labeled `center_projected_st_erwaegungen`
3. Uses v5 baseline for all hybrid experiments (consistent with other evaluations)
4. Adds overclustering detection to fractal verdict logic

### Results (Verified)
| Experiment | JP | LangDom | Verdict | Notes |
|------------|-----|---------|---------|-------|
| center_projected_v5_baseline | **0.4892** | 0.7733 | FAIL | Consistent with other evaluations (~0.53) |
| center_projected_st_erwaegungen | 0.9817 | 0.5310 | PASS | Labeled as separate representation |
| cited_decisions_tfidf | 0.6158 | 0.5964 | PASS | Valid representation |
| hybrid_cited_0.3 | 0.5242 | 0.7588 | PASS | Valid representation |
| hybrid_cited_0.5 | 0.5917 | 0.7065 | PASS | Valid representation |
| hybrid_cited_0.7 | 0.6292 | 0.6540 | PASS | Valid representation |

---

## Fix 2: Citation Role Integration Fractal Collapse

### Root Cause
Base citation role embeddings ("following", "distinguishing", "overruling", "criticizing", "citing", "all_weighted") collapsed to a single coarse cluster (n_coarse=1, coarse_purity=0.271) with 1000 fine clusters (one per decision). The fractal verdict logic incorrectly returned "PASS" because improvement_rate=1.0 (fine_purity=1.0 > coarse_purity=0.271).

### Fix Applied
Created `v6_citation_role_integration_fixed.py` that:
1. Detects overclustering: `n_fine >= 0.9 * n_samples`
2. Detects degenerate structure: `n_coarse == 1 AND coarse_purity < 0.5`
3. Sets `valid_representation = False` for degenerate cases
4. Updates verdict logic: requires `valid_representation=true` for PASS
5. Degenerate variants marked as `FAIL_DEGENERATE`

### Results (Verified)
| Experiment | n_coarse | n_fine | Coarse Purity | Verdict | Valid Rep |
|------------|----------|--------|---------------|---------|-----------|
| following | 1 | 1000 | 0.271 | FAIL_DEGENERATE | ❌ |
| distinguishing | 1 | 1000 | 0.271 | FAIL_DEGENERATE | ❌ |
| overruling | 1 | 1000 | 0.271 | FAIL_DEGENERATE | ❌ |
| criticizing | 1 | 1000 | 0.271 | FAIL_DEGENERATE | ❌ |
| citing | 1 | 1000 | 0.271 | FAIL_DEGENERATE | ❌ |
| all_weighted | 1 | 1000 | 0.271 | FAIL_DEGENERATE | ❌ |
| following_alpha0.3 | 8 | 142 | 0.913 | PASS | ✅ |
| following_alpha0.5 | 8 | 142 | 0.913 | PASS | ✅ |
| following_alpha0.7 | 8 | 142 | 0.913 | PASS | ✅ |
| ... (all alpha-blended variants) | 8 | 142 | 0.913 | PASS | ✅ |

---

## Fix 3: Overclustering Gate

### Root Cause
The fractal evaluation verdict logic in evaluation scripts did not check for `valid_representation`. Representations like `multilingual_e5_contrastive_projection` could pass adversarial gates (LangDom=0.459, JP=0.850) but have `overclustering=true`, `valid_representation=false`, `n_fine=1000` (one cluster per decision).

### Fix Applied
Updated fractal verdict logic in both fixed scripts (`v6_comprehensive_validation_fixed.py`, `v6_citation_role_integration_fixed.py`):
```python
# Detect overclustering
overclustering = n_fine >= n_samples * 0.9
single_coarse_cluster = n_coarse == 1
low_coarse_purity = coarse_overall < 0.5
degenerate_structure = single_coarse_cluster and low_coarse_purity

valid_representation = not overclustering and not degenerate_structure

# Verdict: must pass improvement criteria AND have valid representation
if not valid_representation:
    verdict = "FAIL_DEGENERATE"
elif improvement_rate > 0.5 and overall_improvement > 0:
    verdict = "PASS"
```

### Impact
- All future evaluations will reject overclustered representations
- Prevents false positives from representations that memorize decisions rather than learning legal similarity

---

## Updated Artifacts

### Result Files (Copied to /tmp/lex_prior_audit/)
- `legal_distance/results/v6/comprehensive_validation/comprehensive_validation_all_results.json`
- `legal_distance/results/v6/citation_role_integration/citation_role_integration_all_results.json`

### State File (Updated)
- `state/legal-distance.json` - Updated with repair documentation, new evidence_refs, and corrected critical_findings

### New Scripts (For Future Runs)
- `legal_distance/experiments/v6_comprehensive_validation_fixed.py`
- `legal_distance/experiments/v6_citation_role_integration_fixed.py`
- `legal_distance/experiments/debug_comprehensive_validation.py` (diagnostic)

---

## Product Impact

### No Change to Product Decisions
The core findings remain valid:
1. **TF-IDF citation hybrids = PRIMARY product mode** (JP 0.78-0.79)
2. **Dense embeddings = COMPLEMENTARY modes** (citation heritage AUC 0.77-0.85, cross-lingual Sachverhalt 0.282)
3. **Linear hybrids = EXPLORATORY** (JP 0.61-0.67, below TF-IDF baseline)

### Evaluation Integrity Improved
- JP anomaly resolved: v5 baseline now consistent across all evaluations
- Degenerate representations correctly rejected
- Overclustering gate prevents future false positives

---

## Next Steps

1. **Re-audit**: Submit repaired artifacts for independent audit verification
2. **No further same-question cycles**: Continue_recommended=false (per factory direction v34)
3. **Data blocker**: Corpus lane resumption required for bge_/bger_ mapping, parquet 2024-2026, section extraction at 174k scale

---

## Verification Commands

```bash
# Verify comprehensive validation fix
python3 -c "
import json
with open('legal_distance/results/v6/comprehensive_validation/comprehensive_validation_all_results.json') as f:
    d = json.load(f)
print('v5 baseline JP:', d['center_projected_v5_baseline']['adversarial']['jurist_preference_rate'])
print('ST variant JP:', d['center_projected_st_erwaegungen']['adversarial']['jurist_preference_rate'])
"

# Verify citation role fix
python3 -c "
import json
with open('legal_distance/results/v6/citation_role_integration/citation_role_integration_all_results.json') as f:
    d = json.load(f)
for k in ['following', 'distinguishing', 'overruling', 'criticizing', 'citing', 'all_weighted']:
    print(k, d[k]['fractal']['verdict'], 'valid_rep=', d[k]['fractal'].get('valid_representation'))
"
```