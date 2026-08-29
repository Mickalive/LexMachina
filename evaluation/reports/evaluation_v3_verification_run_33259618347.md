# Evaluation Lane v3 — Verification Run 33259618347

**Factory Direction Version:** 6  
**Evaluation Version:** v3 (Frozen)  
**Config Hash:** `4323f833fa72366a`  
**Global Seed:** 42  
**GitHub Run:** 33259618347  
**Date:** 2026-08-29  
**Verification Type:** Fresh execution of frozen harness  

---

## Reproducibility Status: ✅ CONFIRMED

The frozen evaluation harness (v3, seed=42, config_hash=`4323f833fa72366a`) has been **successfully reproduced** in this run. All adversarial benchmark scores match the frozen reference results **exactly to 4 decimal places**.

### Comparison with Frozen Reference (GitHub Run 33232234741)

| Representation | Metric | Frozen Reference | This Run | Match |
|---|---|---|---|---|
| **center_projected_64dim** | Language Dominance | 0.7664 | 0.7664 | ✅ |
| | Jurist Pairwise | 0.5121 | 0.5121 | ✅ |
| | Both Gates | PASS | PASS | ✅ |
| **center_projected_768** | Language Dominance | 0.7738 | 0.7738 | ✅ |
| | Jurist Pairwise | 0.4912 | 0.4912 | ✅ |
| | Both Gates | FAIL | FAIL | ✅ |
| **linear_metric_epoch4** | Language Dominance | 0.6805 | 0.6805 | ✅ |
| | Jurist Pairwise | 0.6847 | 0.6847 | ✅ |
| | Both Gates | PASS | PASS | ✅ |
| **mahalanobis_metric_epoch4** | Language Dominance | 0.6843 | 0.6843 | ✅ |
| | Jurist Pairwise | 0.6781 | 0.6781 | ✅ |
| | Both Gates | PASS | PASS | ✅ |
| **hybrid_stabilized_epoch1** | Language Dominance | 0.6704 | 0.6704 | ✅ |
| | Jurist Pairwise | 0.6656 | 0.6656 | ✅ |
| | Both Gates | PASS | PASS | ✅ |
| **hybrid_v2_epoch3** | Language Dominance | 0.7115 | 0.7115 | ✅ |
| | Jurist Pairwise | 0.5988 | 0.5988 | ✅ |
| | Both Gates | PASS | PASS | ✅ |

### Supplementary Benchmarks (All Match)

| Representation | Jurivoc L0 NMI | Scale Stability | Cross-Lang Recall | Boilerplate Resist | Fractal Imp.Rate |
|---|---|---|---|---|---|
| center_projected_64dim | 0.0653 | 0.7071 | 0.1558 | -0.9012 | 64.7% |
| linear_metric_epoch4 | 0.6895 | 0.7037 | 0.2114 | -0.8879 | 72.0% |
| mahalanobis_metric_epoch4 | 0.7041 | 0.7154 | 0.2083 | -0.8954 | 65.2% |
| hybrid_stabilized_epoch1 | 0.6360 | 0.7067 | 0.2360 | -0.9194 | 73.8% |
| hybrid_v2_epoch3 | 0.7415 | 0.7092 | 0.2269 | -0.9144 | 59.6% |

**All supplementary metrics match exactly.**

---

## Key Findings Re-Validated

1. **Production default confirmed**: `center_projected_64dim` is the **ONLY pre-trained representation** passing BOTH adversarial gates with meaningful hierarchical structure
   - Language Dominance: 0.7664 (< 0.85) ✓
   - Jurist Pairwise: 0.5121 (> 0.5) ✓
   - 768-dim version FAILS jurist pairwise (0.4912)

2. **Metric learning breakthrough reproduced**:
   - Linear projection: JP=0.6847 (+33.7% relative improvement)
   - Mahalanobis metric: JP=0.6781 (+32.4% relative improvement)
   - Both pass BOTH adversarial gates with 18+ consecutive valid epochs

3. **Stabilized hybrids validated**:
   - hybrid_stabilized_epoch1: JP=0.6656, lowest language dominance (0.6704)
   - hybrid_v2_epoch3: Best Jurivoc L0 NMI (0.7415)

4. **Systematic boilerplate resistance limitation**: All representations score -0.75 to -0.92 (neighbors driven by procedural/language artifacts)

5. **Scale stability good**: All representations 0.70-0.72 neighbor overlap under 80% subsampling

6. **Cross-language retrieval**: Breakthrough representations PASS (>0.2), center_projected FAILS

7. **Jurivoc alignment**: Metric learning/hybrids PASS (L0 NMI 0.64-0.74), center_projected FAILS (~0.07)

---

## Environment Notes

- Python dependencies installed: `numpy`, `scikit-learn`, `scipy`, `python-igraph`, `leidenalg`
- The fractal quality benchmarks (hierarchical Leiden) require `igraph` + `leidenalg` — now available
- All 6 representations evaluated on 1,200-decision expanded slice
- Global seed 42 enforced throughout; config hash `4323f833fa72366a` unchanged

---

## Artifacts Updated

| Artifact | Path |
|---|---|
| Frozen harness results | `evaluation/results/v3/evaluation_v3_results.json` |
| Verification report | `evaluation/reports/evaluation_v3_verification_run_33259618347.md` |

---

## Conclusion

**The frozen evaluation harness v3 is mathematically reproducible.** This verification run (33259618347) produces **identical results** to the original frozen runs (33232234741, 33240972425) and the local reproduction (2026-08-29).

The evaluation lane v3 remains at **REPRODUCED** evidence tier with **COMPLETED** cycle status and **continue_recommended: false**. No further cycles under the same factory-direction question are justified.

**Next recommendation:** PRODUCTIZE — advance to Factory Direction v7 (corpus scale 192k, citation ID resolution, legal embeddings fine-tuning, jurist human study, product hardening at scale).

---

*Verification completed by Evaluation Lane — Config Hash: 4323f833fa72366a — Seed: 42 — Run: 33259618347*