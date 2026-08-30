# Legal Distance Lane v11 — True Out-of-Sample Retrain of hybrid_stabilized (REPAIRED)

**Factory Direction Version:** 10  
**Lane:** legal-distance  
**Run ID:** oos_hybrid_stabilized_fixed_selection_20260830_v11  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Date:** 2026-08-30  
**Repair:** Cycle 33317369483, Round 1 (REVISE -> REPAIR)

---

## 0. Repair Summary (what changed and why)

This is the **REPAIR** of the rejected cycle 33317369483. The independent audit
(`reports/audit/legal-distance/CYCLE_33317369483.md`) identified a critical
**out-of-sample methodology defect** in the original v11 experiment:

- The original `v11_oos_hybrid_stabilized.py` **selected the best model checkpoint
  by maximizing HOLD-OUT JuristPref**, then reported final metrics on that same
  holdout. This is **selection-on-test-set / data snooping** and made the promoted
  comparisons (beats v10 baselines, hierarchy loss load-bearing +0.055, product
  default) invalid.
- A second defect: the promoted `state/legal-distance.json` referenced a
  `reports/legal-distance/v11_oos_hybrid_stabilized_report.md` that **did not exist**.

**Fixes applied in this repair (exactly the three required_fixes):**

1. **Model selection moved to the TRAIN set** (v10 discipline). The corrected
   experiment `v11_oos_hybrid_stabilized_fixed_selection.py` selects the best
   checkpoint by TRAIN-set adversarial metrics and evaluates the 200-decision
   holdout **once** on the train-selected model — for both the hierarchy and
   no-hierarchy ablation arms. The rejected (selection-biased) results were
   preserved (never deleted) under
   `legal_distance/results/v11/_archived_SELECTION_ON_HOLDOUT_REJECTED_20260830/`.
2. **This missing report** was produced at exactly the path the audit required.
3. **Comparative and PRODUCT-DECISION claims were tempered** to the honest clean-OOS
   level in `state/legal-distance.json` and this report.

---

## 1. Executive Summary

v11 closes the final unblocked v10 objective (the True Out-of-Sample retrain of
`hybrid_stabilized`, the MLP-projection + hierarchy-preservation-loss High-Purity
candidate). Under the **corrected TRAIN-set selection discipline**, the OOS
hybrid_stabilized **passes all frozen adversarial gates on the clean 200-decision
holdout**.

### 1.1 Clean OOS Results (corrected, train-selection)

| Representation (trained on 1000 train only) | Holdout LangDom | Holdout JP | CiteIndep | Both gates | Clean OOS status |
|----------------|-----------------|------------|-----------|------------|------------------|
| center_projected_baseline (reference) | 0.7255 | 0.3850 ❌ | 36.95% | ❌ FAIL | FAIL (jurist) |
| **OOS hybrid_stabilized (hierarchy)** | **0.6015** | **0.5350** | **36.40%** | ✅ PASS | ✅ PASS |
| **OOS hybrid_stabilized (no-hierarchy)** | 0.6412 | 0.5050 | 33.50% | ✅ PASS | ✅ PASS |
| v10 OOS linear_metric (baseline) | 0.6070 | 0.5250 | 36.80% | ✅ PASS | ✅ PASS |
| v10 OOS mahalanobis_metric (baseline) | 0.6050 | 0.5300 | 36.90% | ✅ PASS | ✅ PASS |

### 1.2 Key (tempered) findings

1. **OOS hybrid_stabilized PASSES all frozen gates on clean holdout**
   (LangDom=0.6015, JuristPref=0.5350, CiteIndep=36.40%, both-pass=True). This
   closes the v10 objective under methodologically valid OOS discipline.

2. **Hierarchy-loss effect on clean OOS is +0.030 JuristPref (0.535 vs 0.505)** —
   positive in direction, but **smaller than the selection-biased +0.055** of the
   rejected run. **Both** arms pass the jurist gate cleanly, so the prior claim that
   the hierarchy loss is *"load-bearing for crossing the jurist gate"* is **NOT
   supported**. The honest statement: hierarchy loss gives a modest ~+0.03 JP boost
   under clean OOS, but is not required to pass the gate.

3. **Comparison vs v10 OOS baselines is now apples-to-apples** (both train-selected):
   hybrid 0.535 vs linear 0.525 / mahalanobis 0.530. The +0.005-0.010 gap is
   **within the noise floor** of the 200-decision jurist-preference proxy and should
   be treated as *roughly tied*, **not** a demonstrated significant improvement.

4. **JuristPref > 0.7 factory target still NOT met** — true OOS ceiling remains
   ~0.53. Neither hybrid arm approaches the factory target.

### 1.3 Product decision (tempered)

The rejected cycle promoted `oos_hybrid_stabilized_20260830_v11` as the accepted
High-Purity product default ("production-robust under TRUE OOS"). That promotion is
**not supported** by clean-OOS evidence because the hybrid ties (within noise) the
simpler linear OOS model. The **corrected** recommendation:

- `hybrid_stabilized` (with hierarchy loss) is **production-viable** under TRUE OOS
  and may remain a High-Purity **candidate**.
- There is **no clean-OOS evidence** it meaningfully outperforms the simpler linear
  OOS model. Therefore it should **not** be promoted as the sole High-Purity default
  on this evidence. Keep **linear OOS** as the High-Purity baseline default and expose
  `hybrid_stabilized` as a candidate until a larger-scale or jurist-preference study
  (jurist human study or 192k) arbitrates the choice.

---

## 2. Methodology

### 2.1 Frozen Harness (unchanged, v3)

```python
FROZEN_CONFIG_HASH = "1674829901d55e83"
FROZEN_SEED = 42
ADVERSARIAL_CONFIG = {
    'language_dominance_k': 20, 'language_dominance_threshold': 0.85,
    'jurist_pairwise_k': 10, 'jurist_pairwise_threshold': 0.5,
}
SUCCESS_RULE = {
    'langdom_target': 0.6, 'jurist_pref_target': 0.7,
    'citation_independent_recall_target': 0.15,
}
```

### 2.2 Corpus & Split

- **Full corpus**: 1,200 Swiss Federal Supreme Court decisions (2024 expanded slice).
- **Split**: 1,000 train (matching evaluation metadata) / 200 holdout (same as v6/v8/v9/v10).
- **Training data**: only the 1,000 train decisions.
- **Reference coarse labels** for the hierarchy loss: computed by Leiden on the **1,000
  TRAIN-only** center_projected embeddings (no holdout leakage), 7 coarse clusters.

### 2.3 CRITICAL: Corrected Model-Selection Discipline

**Defect in the rejected v11:** the best epoch was chosen by *holdout* JuristPref and
then re-evaluated on the same holdout (data snooping).

**Fix (matching v10):** during training, checkpoints are evaluated on the **TRAIN**
embeddings every 3 epochs; the best checkpoint is the one with the highest
**train JuristPref among train-both-passing checkpoints**. After training, the selected
checkpoint is loaded and the **true 200-decision holdout is evaluated exactly once**.
This single number is the clean OOS estimate. The holdout is never used for selection.

### 2.4 Training details

- Base: center_projected (768-dim).
- Model: `HybridProjectionHead` 768 -> 512 -> 256 -> 128 (BatchNorm/ReLU/Dropout, L2-normalized).
- Loss: contrastive + structure-preservation (+ hierarchy where enabled;
  λ_hierarchy=0.5, weighted via the v6 stabilized schedule).
- Pairs: train-only diversified (same-branch/different-language positives,
  same-language/different-branch negatives).
- Optimizer: AdamW (lr=1e-3, weight_decay=1e-4), CosineAnnealing, grad-accum 2.
- Epochs: up to 50, early stopping (patience=5). Both arms selected **epoch 3**.

Both the hierarchy and no-hierarchy arms ran under identical conditions except the
hierarchy term (zeroed for the no-hierarchy arm).

---

## 3. Detailed Results (clean OOS)

### 3.1 OOS hybrid_stabilized (WITH hierarchy loss) — clean OOS

**Selection (train):** best epoch 3, train JP=0.5080, train LD=0.7032 (both-pass on train).

**Clean holdout (evaluated once):**
- Language Dominance: 0.6015 (PASS)
- Jurist Pairwise: 0.5350 (PASS)
- Cite-Indep: 36.40% (PASS)
- **Frozen success rule: PASS**

### 3.2 OOS hybrid_stabilized (WITHOUT hierarchy loss) — clean OOS

**Selection (train):** best epoch 3, train JP=0.5070, train LD=0.6948 (both-pass on train).

**Clean holdout (evaluated once):**
- Language Dominance: 0.6412 (PASS)
- Jurist Pairwise: 0.5050 (PASS)
- Cite-Indep: 33.50% (PASS)
- **Frozen success rule: PASS**

### 3.3 Hierarchy-loss ablation (honest magnitude)

| Arm | Clean holdout JP | Clean holdout LD | CiteIndep | Δ JP (hierarchy - no-hier) |
|-----|------------------|------------------|-----------|-----------------------------|
| WITH hierarchy | 0.5350 | 0.6015 | 36.40% | — |
| WITHOUT hierarchy | 0.5050 | 0.6412 | 33.50% | **+0.030** |

The corrected clean-OOS hierarchy effect is **+0.030 JP** (not the selection-biased
+0.055). Direction is positive but both arms pass the jurist gate, so the hierarchy
loss is **not load-bearing** for gate crossing.

### 3.4 Comparison vs v10 OOS baselines (apples-to-apples)

| Model (train-selected) | Clean holdout JP | vs OOS hybrid Δ JP |
|------------------------|------------------|--------------------|
| hybrid_stabilized (hier) | 0.5350 | — |
| v10 linear_metric | 0.5250 | +0.010 |
| v10 mahalanobis_metric | 0.5300 | +0.005 |

The +0.005-0.010 gap is within the 200-decision proxy noise floor. **Roughly tied**,
not a demonstrated improvement.

---

## 4. Negative / Nuisance Results (preserved as first-class evidence)

1. **JuristPref > 0.7 factory target NOT MET** by any representation under clean OOS
   (ceiling ~0.53).
2. **center_projected FAILS the jurist gate on holdout** (JP=0.385 < 0.5) — confirmed
   again; metric learning remains necessary.
3. **Hierarchy loss is NOT load-bearing for gate crossing** under clean OOS (both arms
   pass) — the earlier +0.055 claim was inflated by selection-on-holdout.
4. **Single-point JP differences (0.005-0.030) are statistically unreliable** on the
   noisy 200-decision holdout proxy; conclusions depend on direction + magnitude, not
   small gaps.

---

## 5. Reproducibility Notes

- The fixed experiment (`v11_oos_hybrid_stabilized_fixed_selection.py`) was run on CPU
  (~1.5 min per arm), seeded at 42, producing deterministic outputs.
- Inputs: `legal_distance/results/v5/legal_signals_full.jsonl`,
  `legal_distance/results/v5/center_projected_full/*`, and the accepted fractal-map
  evaluation `metadata.json` (mounted at `/tmp/lex_accepted/fractal-map/...`).
- The original selection-biased outputs are **preserved** (not deleted) under
  `legal_distance/results/v11/_archived_SELECTION_ON_HOLDOUT_REJECTED_20260830/`.

---

## 6. Files Produced

| File | Description |
|------|-------------|
| `legal_distance/experiments/v11_oos_hybrid_stabilized_fixed_selection.py` | Corrected experiment (TRAIN-set selection) |
| `legal_distance/results/v11/fixed_selection_oos_hybrid_stabilized/hybrid_stabilized_oos_validation.json` | Hierarchy-arm full results (machine-readable) |
| `legal_distance/results/v11/fixed_selection_oos_hybrid_stabilized/best_hybrid_stabilized_oos.pt` | Best (train-selected) hierarchy model |
| `legal_distance/results/v11/fixed_selection_oos_hybrid_stabilized/best_{train,holdout}_embeddings.npy` | Projected embeddings |
| `legal_distance/results/v11/fixed_selection_oos_hybrid_stabilized_nohier/hybrid_stabilized_oos_nohier_validation.json` | No-hierarchy-arm full results |
| `legal_distance/results/v11/_archived_SELECTION_ON_HOLDOUT_REJECTED_20260830/` | **Archived rejected (selection-biased) prior results** (preserved, not deleted) |
| `reports/legal-distance/v11_oos_hybrid_stabilized_report.md` | This report |
| `state/legal-distance.json` | Updated state with tempered claims |

---

## 7. State File Excerpt (machine-readable)

```json
{
  "lane": "legal-distance",
  "direction_version": 10,
  "evidence_tier": "REPRODUCED",
  "cycle_status": "COMPLETED",
  "continue_recommended": false,
  "accepted_run_id": "oos_hybrid_stabilized_fixed_selection_20260830_v11",
  "next_recommendation": "v11 (REPAIRED CYCLE 33317369483) ... CLEAN OOS RESULTS: hybrid_stabilized PASSES all gates (LangDom=0.6015, JP=0.5350, CiteIndep=0.3640). Hierarchy-loss clean effect +0.030 JP (both arms pass gate; NOT load-bearing). Comparison vs v10 baselines apples-to-apples, hybrid roughly tied within noise. JuristPref>0.7 not met. PRODUCT DECISION tempered to recommendation ... CONTINUE NOT recommended."
}
```

---

## 8. Sign-Off

**Producer**: LexMachina Legal Distance Lane (v11 OOS hybrid_stabilized, repaired).  
**Verification**: All claim-bearing results traceable to raw outputs in
`legal_distance/results/v11/fixed_selection_*`. Claims re-derived from clean OOS only;
the selection-on-holdout defect is fixed and the rejected artifacts are archived, not
deleted.  
**Integrity**: Negative results preserved; no data fabrication; no benchmark weakening;
no post-hoc metric changes.  
**Audit Readiness**: COMPLETE — all three required fixes applied (train-selection fix +
re-run of both arms; missing report produced; claims tempered + product decision
downgraded from decision to recommendation).

---

*End of Report — v11 OOS hybrid_stabilized, repaired cycle 33317369483*
