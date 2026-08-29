# Evaluation v3 Final Confirmation — Run 33234209188

**Date**: 2026-08-29
**Factory Direction**: v6
**Lane**: evaluation
**Global Seed**: 42
**Config Hash**: 4323f833fa72366a

## Summary

This run confirms the **exact reproducibility** of the Evaluation v3 Frozen Harness results. All adversarial benchmarks produce identical outputs to the accepted run `eval_v3_breakthrough_validation_33232724333`.

## Verification Results

| Representation | Verdict | Language Dominance | Jurist Pairwise | Both Gates | Jurivoc L0 NMI | Scale Stability | Fractal Imp. Rate |
|----------------|---------|-------------------|-----------------|------------|----------------|-----------------|-------------------|
| **linear_metric_epoch4** | ✅ PASS | 0.6805 ✓ | 0.6847 ✓ | ✅ **BEST** | 0.6895 | 0.7037 | 71.95% |
| **mahalanobis_metric_epoch4** | ✅ PASS | 0.6843 ✓ | 0.6781 ✓ | ✅ | 0.7041 | 0.7154 | 65.18% |
| **hybrid_stabilized_epoch1** | ✅ PASS | 0.6704 ✓ | 0.6656 ✓ | ✅ | 0.6360 | 0.7067 | 73.83% |
| **hybrid_v2_epoch3** | ✅ PASS | 0.7115 ✓ | 0.5988 ✓ | ✅ | 0.7415 | 0.7092 | 59.65% |
| **center_projected_64dim** | ✅ PASS | 0.7664 ✓ | 0.5121 ✓ | ✅ *baseline* | 0.0653 | 0.7071 | 64.66% |
| **center_projected_768** | ❌ FAIL | 0.7738 ✓ | 0.4912 ✗ | ❌ | 0.0945 | 0.7104 | 60.00% |

**Thresholds (frozen)**:
- Language Dominance: < 0.85 (lower = better)
- Jurist Pairwise: > 0.5 (higher = better)

## Key Findings Confirmed

1. **center_projected_64dim** remains the **only original representation** passing both adversarial gates (LangDom=0.766<0.85, JP=0.512>0.5)

2. **Four breakthrough representations** from legal-distance lane **all pass both adversarial gates** with **significantly higher jurist preference** (0.60–0.68 vs 0.512 baseline):
   - `linear_metric_epoch4`: JP=0.6847 (+33.7% relative improvement)
   - `mahalanobis_metric_epoch4`: JP=0.6781 (+32.4%)
   - `hybrid_stabilized_epoch1`: JP=0.6656 (+29.9%)
   - `hybrid_v2_epoch3`: JP=0.5988 (+17.0%)

3. **center_projected_768dim FAILS** jurist pairwise gate (0.491) — confirms 64-dim frozen PCA is required for production default

4. **All breakthrough representations pass cross-language retrieval** (recall@10: 0.21–0.24 vs baseline 0.16 FAIL)

5. **All breakthrough representations show strong Jurivoc L0 alignment** (NMI: 0.64–0.74 vs baseline 0.07)

6. **All breakthrough representations show meaningful fractal structure** (improvement_rate: 60–74%)

7. **v6 signal ablation dimension bug confirmed**: The v6 signal ablation compared 768-dim baseline against 64-dim hybrids, invalidating direct comparison. The v3 evaluation (64-dim baseline) is the authoritative result.

8. **Frontier metric learning remains BLOCKED** — no `frontier_metric_learning_jurivoc` team was dispatched. The legal-distance lane's metric learning breakthrough (linear + Mahalanobis on center_projected space) is separate and has been validated.

## Boilerplate Resistance

All representations show **highly resistant** behavior (resistance_score = 1 - cosine_similarity, lower = better):
- TF-IDF variants: ~0.017
- multilingual-e5-small: ~0.004
- paraphrase-MiniLM: ~0.016
- xlm-roberta-base: ~0.00007
- center_projected: 0.050
- All breakthrough variants: 0.04–0.05

All far exceed the corrected threshold (resistance_score < 0.3 = PASS).

## State

The evaluation lane state remains:
- **evidence_tier**: ACCEPTED
- **cycle_status**: COMPLETED
- **continue_recommended**: false
- **next_recommendation**: PRODUCTIZE
- **accepted_run_id**: eval_v3_breakthrough_validation_33232724333

## Conclusion

The frozen evaluation harness v3 is **fully reproducible** with global seed=42. All critical adversarial benchmarks produce bit-identical results. The evaluation validates:

- center_projected_64dim as production default (only original passing both gates)
- Four breakthrough representations from legal-distance lane as superior alternatives (all pass both gates with 17–34% higher jurist preference)
- The 64-dim frozen PCA requirement (768-dim fails)
- Cross-language retrieval, Jurivoc alignment, scale stability, and fractal coherence for breakthrough representations

No additional same-question cycle is justified. The Factory Director should decide the successor question for factory direction v7.