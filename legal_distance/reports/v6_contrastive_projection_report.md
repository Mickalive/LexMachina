# Legal Distance Lane v6 — Contrastive Projection Head Fine-Tuning Report

## Executive Summary

This cycle executes **Factory Direction v6 Objective 3**: "Legal embeddings: test multilingual-e5-small fine-tuning on Swiss legal corpus for multilingual invariance WITH coarse legal structure."

A CPU-efficient contrastive projection head (384 → 256 → 128) was trained on frozen `multilingual-e5-small` embeddings using a contrastive objective directly targeting the two adversarial gates:
- **Positive pairs**: Same legal branch, different language (multilingual legal invariance)
- **Negative pairs**: Same language, different branch (language artifact suppression)

**Key Finding**: The contrastive projection **passes both adversarial benchmarks** (LangDom=0.459, JuristPref=0.850) but exhibits **severe overclustering** (1 coarse → 1000 fine clusters), making the adversarial PASS a **false positive artifact** — identical pathology to `signal_outcome_tfidf` and the pretrained model.

---

## 1. Method

### Architecture
- **Backbone**: `intfloat/multilingual-e5-small` (384-dim, frozen)
- **Projection Head**: 384 → 256 (BN+ReLU) → 128 (L2-normalized) = ~50K trainable params
- **Loss**: Contrastive loss with temperature τ=0.07
- **Training**: 20 epochs, batch=64 (effective=256 w/ grad accum), LR=1e-3, cosine annealing
- **Device**: CPU (feasible for ~50K params)

### Contrastive Pairs (from 1,000 decisions with branch/language metadata)
| Pair Type | Criterion | Count |
|-----------|-----------|-------|
| Positive | Same branch, different language | ~12,000 |
| Negative | Same language, different branch | ~12,000 |

### Evaluation Harness (identical to adversarial validation)
1. **Adversarial Language Dominance** (k=20, threshold < 0.85)
2. **Jurist Pairwise Preference** (k=10, threshold > 0.5)
3. **Fractal Quality** (Hierarchical Leiden: coarse_res=0.5, sub_res=3.0)

---

## 2. Results

### 2.1 Adversarial Benchmarks

| Model | Language Dominance | LD Status | Jurist Preference | JP Status | Both Pass |
|-------|-------------------|-----------|------------------|-----------|-----------|
| **center_projected (ref)** | **0.763** | ✅ | **0.528** | ✅ | ✅ **VALID** |
| multilingual-e5-small (pretrained) | 0.446 | ✅ | 0.850 | ✅ | ✅ **ARTIFACT** |
| **multilingual-e5 contrastive projection** | **0.459** | ✅ | **0.850** | ✅ | ✅ **ARTIFACT** |

### 2.2 Fractal Quality

| Model | Coarse | Fine | Coarse Purity | Fine Purity | Imp Rate | Legal Area NMI | Hier. Adv. | Overclustering |
|-------|--------|------|---------------|-------------|----------|----------------|------------|----------------|
| center_projected | 7 | 105 | 0.774 | 0.947 | 59% | 0.600 | +0.027 | ❌ No |
| multilingual-e5 pretrained | **1** | **1000** | 0.271 | 1.000 | 100% | 0.704 | 0.000 | ⚠️ **YES** |
| **contrastive projection** | **1** | **1000** | 0.466 | 1.000 | 100% | 0.704 | 0.000 | ⚠️ **YES** |

### 2.3 Training Dynamics

- **Loss decreased steadily** from ~0.69 to ~0.31 over 20 epochs
- **No epoch produced a valid representation** (all had overclustering)
- Best jurist preference: 0.850 (epoch 20), but always with n_coarse=1

---

## 3. Root Cause Analysis

### Why Does Contrastive Training Fail to Produce Valid Structure?

| Factor | Analysis |
|--------|----------|
| **Objective mismatch** | Contrastive loss pulls same-branch-diff-lang together, pushes same-lang-diff-branch apart. This optimizes neighbor-level metrics but **destroys global cluster structure** — every decision becomes its own fine cluster. |
| **No structure preservation term** | Unlike center_projected (which subtracts language centroids from pretrained semantic space), contrastive training has no constraint to preserve the pretrained model's semantic topology. |
| **Insufficient positive diversity** | Positive pairs only cover branch-level alignment. Finer legal structure (legal_area, chamber, outcome) is not represented in the loss. |
| **Projection head capacity** | 50K params may be too small to learn a non-degenerate mapping that both satisfies contrastive constraints AND preserves hierarchy. |

### The Fundamental Trade-off Identified

```
┌─────────────────────────────────────────────────────────────────┐
│  ADVERSARIAL ROBUSTNESS          vs.   FRACTAL STRUCTURE        │
│  (neighbor-level multilingual    │   (cluster-level taxonomic    │
│   invariance + legal relevance)  │    alignment + zoom coherence)│
├─────────────────────────────────────────────────────────────────┤
│  center_projected                │   ✅ BOTH PASS                │
│  (language centroid subtraction) │   ✅ 7→105 clusters, 59% imp  │
├─────────────────────────────────────────────────────────────────┤
│  Pure legal signals (TF-IDF)     │   ❌ LangDom ≈ 1.0            │
│  (sachverhalt, erwaegungen, etc) │   ✅ High NMI, fine purity    │
├─────────────────────────────────────────────────────────────────┤
│  Hybrids (α=0.3)                 │   ❌ LangDom ✅, JP ❌        │
│  (legal + center_projected)      │   ✅ Good fractal quality     │
├─────────────────────────────────────────────────────────────────┤
│  Contrastive projection /        │   ✅ BOTH PASS (ARTIFACT)     │
│  signal_outcome_tfidf            │   ❌ 1→1000 overclustering    │
└─────────────────────────────────────────────────────────────────┘
```

**Center_projected remains the ONLY representation that simultaneously:**
1. Passes adversarial language dominance (< 0.85)
2. Passes jurist pairwise preference (> 0.5)
3. Maintains meaningful fractal hierarchy (n_coarse ≥ 3, improvement_rate > 0)

---

## 4. Negative Results Preserved (First-Class Evidence)

| Experiment | Adversarial | Fractal | Verdict |
|------------|-------------|---------|---------|
| Contrastive projection (20 epochs) | PASS (0.459, 0.850) | FAIL (1→1000) | **False positive** |
| Pretrained multilingual-e5-small | PASS (0.446, 0.850) | FAIL (1→1000) | **False positive** |
| signal_outcome_tfidf | PASS (0.446, 0.850) | FAIL (1→1000) | **False positive** |

**Pattern**: Any representation that achieves LangDom << 0.5 and JuristPref >> 0.5 via aggressive contrastive/lexical separation collapses to 1 coarse cluster. The adversarial benchmarks alone cannot distinguish valid structure from overclustering artifacts.

---

## 5. Recommendations for Next Factory Direction

### 1. Objective 3 — REVISE APPROACH: Hybrid Objective Required ⚠️
**Current**: Pure contrastive loss on frozen backbone → overclustering artifact
**Proposed**: Multi-objective training that **preserves pretrained structure** while improving adversarial metrics:

```python
loss = λ_contrastive * L_contrastive + λ_preserve * L_preserve + λ_hierarchy * L_hierarchy
```

Where:
- `L_preserve` = MSE between projected and center_projected embeddings (or cosine similarity preservation)
- `L_hierarchy` = Cluster coherence loss (e.g., pull same-branch pairs closer at coarse level)
- Center_projected embeddings serve as **structure anchor** — don't destroy what works

### 2. Alternative: Contrastive Fine-tuning WITH Language Centroid Subtraction
- Fine-tune backbone (not just projection head) with contrastive loss
- **Then** apply language centroid subtraction (center_projected pipeline)
- This combines learned legal invariance with proven multilingual debiasing

### 3. Alternative: Metric Learning on center_projected Space
- Train a Mahalanobis metric / linear projection **on top of center_projected**
- Objective: Improve JuristPref while constraining LangDom < 0.85 and n_coarse ≥ 3
- Lower risk: Starting from valid structure, not destroying it

### 4. CPU Fine-tuning of Full Model (Deferred)
- Full `multilingual-e5-small` fine-tuning (33M params) requires GPU
- Code ready in `v6_cpu_contrastive_finetune.py` (2 epochs, contrastive loss)
- Honestly documented as BLOCKED in `finetune_gpu_limitation.md`

---

## 6. Evidence Preservation

All raw outputs preserved per Research Protocol:
- `results/v6/contrastive_projection/final_embeddings.npy` — Final 128-dim embeddings (1000×128)
- `results/v6/contrastive_projection/final_projection_head.pt` — Trained projection head weights
- `results/v6/contrastive_projection/training_results.json` — Full training/evaluation log
- `results/v6/adversarial_signal_validation/adversarial_signal_validation_results.json` — Updated with contrastive projection results (32 representations total)

---

## 7. Conclusion

**Contrastive projection head fine-tuning on CPU is technically feasible but scientifically invalid as a standalone approach.**

The method passes adversarial benchmarks by collapsing all decisions into isolated fine clusters (1 coarse → 1000 fine), destroying the fractal hierarchy essential for a zoomable legal map. This confirms the **fundamental gap** identified in the adversarial validation report: neighbor-level multilingual invariance and cluster-level taxonomic structure are **different properties** requiring different optimization strategies.

**Center_projected (language centroid subtraction on pretrained sentence transformer embeddings) remains the sole validated reference representation** — the only one that simultaneously satisfies all three criteria:
1. ✅ Multilingual invariance (LangDom = 0.763 < 0.85)
2. ✅ Legal neighbor relevance (JuristPref = 0.528 > 0.5)
3. ✅ Meaningful fractal hierarchy (7→105 clusters, 59% improvement rate)

**Next cycle should explore hybrid objectives that preserve center_projected structure while improving legal relevance, not destroy it.**

---

*Generated: 2026-08-29 | Factory Direction v6 | Legal-Distance Lane*