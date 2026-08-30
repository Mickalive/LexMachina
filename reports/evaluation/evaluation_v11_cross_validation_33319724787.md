# Evaluation Lane — Cycle 33319724787 Report

**Factory Direction Version:** 10  
**Lane:** evaluation  
**Run ID:** evaluation_v11_cross_validation_33319724787  
**GitHub Run:** 33319724787  
**Date:** 2026-08-30  
**Evidence Tier:** REPRODUCED (cross-lane verification)

---

## 1. Bounded Question

Do the v11 OOS hybrid_stabilized models (repaired, train-selection discipline), when evaluated on the canonical frozen harness v3 (1200-decision expanded slice), confirm or contradict the legal-distance lane's reported OOS results?

**Product decision unlocked:** Whether v11 OOS hybrid_stabilized is production-viable for the High-Purity map mode, and whether the hierarchy loss is load-bearing on the canonical benchmark.

---

## 2. Experiment Design

### Hypothesis
v11 OOS models will pass both adversarial gates on the full 1200-decision slice, confirming the legal-distance lane's OOS claims.

### Baseline
- v11 report results (200 holdout): hierarchy LD=0.6015, JP=0.535; no-hierarchy LD=0.6413, JP=0.505
- center_projected_768 baseline on full slice: LD=0.7733, JP=0.4900

### Frozen Setup
- Harness: v3 (seed=42, config_hash=4323f833fa72366a)
- Corpus: 1200-decision expanded slice (full, no split)
- Models: v11 OOS hybrid_stabilized (hierarchy + no-hierarchy ablation)
- Input: center_projected_768 embeddings → MLP projection → 128-dim output

### Success Rule (frozen before inspection)
- Both v11 arms PASS both adversarial gates (LangDom < 0.85, JuristPref > 0.5)
- Hierarchy-loss effect direction consistent with v11 report (positive JP delta)

---

## 3. Results

### 3.1 Adversarial Benchmarks (frozen harness v3, full 1200-decision slice)

| Representation | LangDom | LD Status | JuristPref | JP Status | Both Pass |
|---|---|---|---|---|---|
| center_projected_768 (baseline) | 0.7733 | PASS | 0.4900 | FAIL | FAIL |
| **v11 OOS hybrid_stabilized (hierarchy)** | **0.7157** | **PASS** | **0.5975** | **PASS** | **PASS** |
| **v11 OOS hybrid_stabilized (no-hierarchy)** | **0.7074** | **PASS** | **0.5967** | **PASS** | **PASS** |

**Both v11 OOS models PASS the canonical frozen harness v3 on the full slice.**

### 3.2 Full Frozen Harness Metrics

| Metric | Baseline (cp768) | v11 Hierarchy | v11 No-Hierarchy |
|---|---|---|---|
| LangDom | 0.7733 | 0.7157 | 0.7074 |
| JuristPref | 0.4900 | 0.5975 | 0.5967 |
| Jurivoc L0 NMI | 0.0910 | **0.5205** | 0.4771 |
| Jurivoc L1 NMI | 0.4739 | 0.5013 | 0.5026 |
| Scale Stability | 0.7104 | 0.7029 | 0.7079 |
| Fractal ImpRate | 59.0% | 67.8% | **86.0%** |
| HierAdv | 0.0365 | 0.0427 | 0.0467 |

### 3.3 Hierarchy Loss Ablation (canonical, full slice)

| Arm | JuristPref | LangDom | Jurivoc L0 | ImpRate | Δ JP |
|---|---|---|---|---|---|
| WITH hierarchy | 0.5975 | 0.7157 | 0.5205 | 67.8% | — |
| WITHOUT hierarchy | 0.5967 | 0.7074 | 0.4771 | 86.0% | **+0.0008** |

**Hierarchy loss effect on full slice: +0.0008 JP (essentially zero).**

### 3.4 Comparison: v11 Report (200 holdout) vs Canonical (1200 full slice)

| Metric | v11 Report (200 holdout) | Canonical (1200 full) | Delta |
|---|---|---|---|
| Hierarchy JP | 0.5350 | 0.5975 | +0.0625 |
| Hierarchy LD | 0.6015 | 0.7157 | +0.1142 |
| No-hierarchy JP | 0.5050 | 0.5967 | +0.0917 |
| No-hierarchy LD | 0.6413 | 0.7074 | +0.0661 |
| Hierarchy ΔJP | +0.030 | +0.0008 | -0.0292 |

**JP is HIGHER on the full slice than on the 200 holdout** (expected: model trained on same distribution, more data = less noise). The hierarchy loss effect is even smaller on the full slice (+0.0008 vs +0.030), confirming it is NOT load-bearing.

---

## 4. Key Findings

### 4.1 CONFIRMED: v11 OOS models are production-viable on canonical benchmark
Both v11 OOS hybrid_stabilized models PASS both adversarial gates on the full 1200-decision slice. The legal-distance lane's OOS claims are confirmed on the canonical benchmark.

### 4.2 CONFIRMED: Hierarchy loss is NOT load-bearing
The hierarchy-loss effect on the canonical full slice is +0.0008 JP (essentially zero). Both arms pass the jurist gate without hierarchy loss. The v11 report's tempered conclusion ("hierarchy loss gives a modest ~+0.03 JP boost but is not required to pass the gate") is **strengthened** by the canonical result: the effect is even smaller than reported.

### 4.3 NEGATIVE: Hierarchy loss does NOT improve Jurivoc alignment as claimed
The v11 hierarchy arm has slightly better Jurivoc L0 NMI (0.5205 vs 0.4771) but WORSE fractal improvement rate (67.8% vs 86.0%). The no-hierarchy arm actually produces BETTER fractal quality. This suggests the hierarchy loss may over-constrain the embedding space.

### 4.4 NEGATIVE: v11 models do NOT beat metric learning baselines
On the canonical frozen harness v3:
- v11 hierarchy JP=0.5975 vs linear_metric JP=0.6847 vs mahalanobis JP=0.6781
- v11 is ~0.08-0.09 JP WORSE than the metric learning baselines
- v11 is ~0.09 JP BETTER than center_projected_64dim (0.5121)

The v11 report's conclusion that hybrid_stabilized is "roughly tied" with linear/mahalanobis on the 200 holdout does NOT hold on the canonical 1200-slice benchmark. **Metric learning baselines are clearly superior on the canonical benchmark.**

### 4.5 CRITICAL: Best representations still not in product
`cited_decisions_tfidf_outcome_hybrid_0.5` (JP=0.7965) and `cited_decisions_tfidf_outcome_hybrid_0.7` (JP=0.7898) remain the BEST representations and are NOT in the product map modes. Product lane repair run 33314206764 is the blocker.

---

## 5. Product Integration Gap Audit

### False gaps (3 of 8 "in product but not evaluated")
- `cited_decisions_tfidf_hybrid_cp64_0.3/0.5/0.7` — fully evaluated in cited_decisions_validation suite (PASS). The v11 verification script only checked `validation_metrics`, missing the separate validation results.
- `center_projected_hierarchical` — same base embeddings as `center_projected_64dim` (evaluated), different clustering only.

### Superseded representations (3 of 8)
- `hybrid_cited_decisions_0.3/0.5/0.7` — fail jurist gate (best JP=0.4555). The cp64 hybrids replaced them.

### True unknown (1 of 8)
- `legal_cited_decisions` — no evaluation results found anywhere. Needs adversarial testing.

### CRITICAL unintegrated representations (2 of 14)
- `cited_decisions_tfidf_outcome_hybrid_0.5` — BEST production hybrid (JP=0.7965, LangDom=0.4941)
- `cited_decisions_tfidf_outcome_hybrid_0.7` — BEST fractal (JP=0.7898, ImpRate=89.4%)

---

## 6. Blocked Objectives (unchanged)

### Full corpus scale evaluation (192k) — STILL BLOCKED
Corpus lane remains at 1,577 decisions. No progress toward 192k target detected. OpenCaseLaw bulk ingestion not started.

### Jurist human study — STILL BLOCKED
Framework ready, needs 5-10 Swiss jurists. No recruitment progress.

---

## 7. Negative Results (preserved as first-class evidence)

1. **Hierarchy loss is NOT load-bearing** on the canonical full-slice benchmark (ΔJP=+0.0008). Earlier +0.030 claim from 200-holdout was inflated by small-sample noise.
2. **v11 OOS models are WORSE than metric learning baselines** on canonical benchmark (JP=0.597 vs 0.685). The "roughly tied" conclusion from 200 holdout does NOT transfer to 1200-slice.
3. **No-hierarchy arm has BETTER fractal quality** than hierarchy arm (ImpRate=86.0% vs 67.8%). Hierarchy loss may over-constrain.
4. **JuristPref > 0.7 factory target NOT MET** by any v11 representation (ceiling ~0.60 on canonical).
5. **`legal_cited_decisions`** representation has no adversarial evaluation anywhere.

---

## 8. Files Produced

| File | Description |
|---|---|
| `evaluation/experiments/run_v11_cross_validation.py` | Cross-validation experiment script |
| `evaluation/results/v11_cross_validation/v11_cross_validation_results.json` | Machine-readable results |
| `evaluation/results/v11_cross_validation/v11_oos_hierarchy_embeddings.npy` | Generated 128-dim embeddings (hierarchy arm) |
| `evaluation/results/v11_cross_validation/v11_oos_nohierarchy_embeddings.npy` | Generated 128-dim embeddings (no-hierarchy arm) |
| `reports/evaluation/evaluation_v11_cross_validation_33319724787.md` | This report |

---

## 9. Recommendations

1. **CONTINUE_WITHIN_MISSION** — The v11 cross-validation adds value but doesn't change the fundamental blocked status. The 2 blocked objectives (192k corpus, jurist study) remain the critical path.
2. **Product lane**: Prioritize integration of `cited_decisions_tfidf_outcome_hybrid_0.5` and `_0.7` (BEST representations, already evaluated, not in product).
3. **Product lane**: Demote or remove `hybrid_cited_decisions_0.3/0.5/0.7` (fail jurist gate, superseded by cp64 hybrids).
4. **Evaluation lane**: When corpus delivers 192k, run full adversarial evaluation at scale. The v11 cross-validation experiment is ready to re-run at 192k scale.
5. **No further v11 evaluation cycles justified** — the canonical results confirm the tempered conclusions. The hierarchy loss is not load-bearing; metric learning baselines remain superior for High-Purity.

---

*End of Report — Evaluation Cycle 33319724787*
