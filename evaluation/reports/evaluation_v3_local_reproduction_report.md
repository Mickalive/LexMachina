# Evaluation v3 — Local Reproduction Report

**Date:** 2026-08-29  
**Factory Direction:** v6  
**Global Seed:** 42  
**Config Hash:** 4323f833fa72366a (matches GitHub runs 33232234741 and 33240972425)  
**Status:** REPRODUCED EXACTLY

---

## Summary

The frozen Evaluation v3 harness has been executed locally and produces **bit-identical results** to the two prior GitHub Actions runs. All adversarial benchmarks, Jurivoc alignment, scale stability, boilerplate resistance, and fractal quality metrics match exactly.

---

## Reproduction Verification

| Metric | GitHub Run 33232234741 | Local Run 2026-08-29 | Match |
|---|---|---|---|
| Config Hash | 4323f833fa72366a | 4323f833fa72366a | ✓ |
| center_projected_64dim lang_dom | 0.7663886572143453 | 0.7663886572143453 | ✓ |
| center_projected_64dim jurist_pref | 0.5121 | 0.5121 | ✓ |
| linear_metric_epoch4 jurist_pref | 0.6847 | 0.6847 | ✓ |
| mahalanobis_metric_epoch4 jurist_pref | 0.6781 | 0.6781 | ✓ |
| hybrid_stabilized_epoch1 jurist_pref | 0.6656 | 0.6656 | ✓ |
| hybrid_v2_epoch3 jurist_pref | 0.5988 | 0.5988 | ✓ |

---

## Adversarial Gate Results (Frozen Thresholds)

- **Language Dominance Threshold:** < 0.85 (lower = better)
- **Jurist Pairwise Preference Threshold:** > 0.5 (higher = better)
- **Both gates must PASS for representation to be valid**

| Representation | LangDom | LD Pass | Jurist Pref | JP Pass | Both Pass |
|---|---|---|---|---|---|
| center_projected_768 | 0.7738 | ✓ | 0.4912 | ✗ | ✗ |
| **center_projected_64dim** | **0.7664** | **✓** | **0.5121** | **✓** | **✓** |
| linear_metric_epoch4 | 0.6805 | ✓ | 0.6847 | ✓ | ✓ |
| mahalanobis_metric_epoch4 | 0.6843 | ✓ | 0.6781 | ✓ | ✓ |
| hybrid_stabilized_epoch1 | 0.6704 | ✓ | 0.6656 | ✓ | ✓ |
| hybrid_v2_epoch3 | 0.7115 | ✓ | 0.5988 | ✓ | ✓ |

---

## Key Findings (Reproduced)

### 1. Production Default Validated
**center_projected_64dim** (frozen 64-dim PCA) is the **only** unsupervised baseline representation passing both adversarial gates. This is the current production default map mode.

### 2. 768-dim Variant Fails
**center_projected_768** passes language dominance but **fails jurist pairwise** (0.491 < 0.5). Higher dimensionality introduces language artifacts that degrade legal relevance.

### 3. Metric Learning Breakthrough Confirmed
All four learned/hybrid representations **significantly beat** the reference baseline on jurist pairwise preference:
- `linear_metric_epoch4`: +0.1726 (33.7% relative improvement)
- `mahalanobis_metric_epoch4`: +0.1660
- `hybrid_stabilized_epoch1`: +0.1535
- `hybrid_v2_epoch3`: +0.0867

All pass both adversarial gates with 18+ consecutive valid epochs (per legal-distance v6).

### 4. Zero-Shot Citation Signal Competitive
`cited_decisions_tfidf` (pure TF-IDF on cited decisions, **no training**) achieves:
- Jurist preference: **0.6889** (highest of ALL representations)
- Language dominance: **0.6086** (best language invariance)
- Passes both adversarial gates
- Competitive with supervised linear_metric_epoch4 (0.6847)

All 6 hybrids with center_projected (α=0.3/0.5/0.7, 64/768-dim) also pass both gates.

### 5. Systematic Limitation: Boilerplate Resistance
**ALL representations fail boilerplate resistance** (resistance_score ≈ -0.74 to -0.92). Procedural neighbors dominate over legally-relevant neighbors. This is a fundamental limitation of current embedding approaches.

### 6. Scale Stability Good
All representations show 0.60–0.72 neighbor overlap under 80% corpus subsampling.

### 7. Signal Ablation Validation Complete
All 15 unsupervised signal ablation variants on center_projected baseline **FAIL** jurist pairwise preference. Only metric learning objectives (linear, Mahalanobis) and stabilized hybrids produce adversarial-robust representations.

---

## Files Updated

- `/home/runner/work/LexMachina/LexMachina/evaluation/results/v3/evaluation_v3_results.json` — Fresh execution results (identical to GitHub runs)
- Config hash verified: `4323f833fa72366a`

---

## Recommendation

**PRODUCTIZE** — Evaluation v3 is complete, frozen, and reproduced. No additional same-question cycles justified (`continue_recommended: false`).

The Factory Director should advance to the next factory direction version with new lane questions. The evaluation infrastructure (frozen harness, adversarial benchmarks, expanded 1,200-decision slice) is ready for evaluating future representations.

---

## Evidence References

- `evaluation/results/v3/evaluation_v3_results.json` (this run)
- `evaluation/evaluation_v3_harness.py` (frozen harness, seed=42)
- `evaluation/results/cited_decisions_validation/cited_decisions_validation_all_results.json` (cited_decisions_tfidf validation)
- `evaluation/results/v3_boilerplate_real/boilerplate_resistance_real_results.json` (boilerplate resistance)
- `results/evaluation/v6_signal_ablation/v6_signal_ablation_adversarial_results.json` (signal ablation validation)
- GitHub Run 33232234741 (original frozen harness execution)
- GitHub Run 33240972425 (verification run)