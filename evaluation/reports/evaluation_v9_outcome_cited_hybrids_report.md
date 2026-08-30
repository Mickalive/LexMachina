# Evaluation v9 Report: v7 Outcome-Cited Hybrids on Frozen Harness v3

**Date:** 2026-08-29  
**GitHub Run:** 33281425835  
**Factory Direction:** v8  
**Evaluation Harness:** v3 (frozen, seed=42, config_hash=4323f833fa72366a)

---

## Executive Summary

Evaluated **7 representations** from legal-distance v7 `outcome_cited_hybrids` plus 2 baselines against the frozen adversarial evaluation harness v3 (1,200-decision expanded slice). All 5 v7 hybrid representations **PASS both adversarial gates** (language dominance < 0.85, jurist pairwise > 0.5), significantly outperforming the production baseline `center_projected_64dim` on jurist preference.

### Key Findings

| Representation | Verdict | LangDom | Jurist Pref | Jurivoc L0 | Scale Stab | Cross-Lang | Best For |
|---|---|---|---|---|---|---|---|
| `outcome_tfidf` (2-dim) | PASS | **0.455** ✓ | **0.832** ✓ | 0.005 ✗ | 0.000 ✗ | 0.159 ✗ | Adversarial only (overfits) |
| `cited_decisions_tfidf_outcome_hybrid_0.3` (2-dim) | PASS | 0.509 ✓ | 0.764 ✓ | 0.068 ✗ | 0.634 ✓ | 0.207 ✓ | Good balance |
| `cited_decisions_tfidf_outcome_hybrid_0.5` (2-dim) | PASS | 0.494 ✓ | **0.797** ✓ | 0.116 ✗ | 0.647 ✓ | **0.236** ✓ | **Best cross-lang retrieval** |
| `cited_decisions_tfidf_outcome_hybrid_0.7` (2-dim) | PASS | 0.492 ✓ | 0.790 ✓ | **0.164** ✗ | **0.663** ✓ | 0.231 ✓ | **Best Jurivoc L0 + scale** |
| `cited_decisions_tfidf` (128-dim) | PASS | 0.609 ✓ | 0.689 ✓ | **0.246** ✗ | 0.597 ✓ | 0.208 ✓ | Best Jurivoc alignment |
| `center_projected_64dim` (baseline) | PASS | 0.766 ✓ | 0.512 ✓ | 0.065 ✗ | 0.707 ✓ | 0.156 ✗ | Production default |
| `center_projected_768` (baseline) | **FAIL** | 0.774 ✓ | 0.491 ✗ | 0.095 ✗ | 0.710 ✓ | 0.146 ✗ | Fails jurist gate |

---

## Detailed Results

### Adversarial Benchmarks (Frozen Gates)

**Language Dominance Threshold:** < 0.85 (PASS = lower is better)  
**Jurist Pairwise Threshold:** > 0.5 (PASS = higher is better)

| Representation | LangDom | Status | Jurist Pref | Status | Both Gates |
|---|---|---|---|---|---|
| outcome_tfidf | 0.4548 | ✓ PASS | 0.8324 | ✓ PASS | ✓ PASS |
| cited_decisions_tfidf_outcome_hybrid_0.3 | 0.5085 | ✓ PASS | 0.7640 | ✓ PASS | ✓ PASS |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.4941 | ✓ PASS | 0.7965 | ✓ PASS | ✓ PASS |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4922 | ✓ PASS | 0.7898 | ✓ PASS | ✓ PASS |
| cited_decisions_tfidf | 0.6087 | ✓ PASS | 0.6889 | ✓ PASS | ✓ PASS |
| center_projected_64dim | 0.7664 | ✓ PASS | 0.5121 | ✓ PASS | ✓ PASS |
| center_projected_768 | 0.7738 | ✓ PASS | 0.4912 | ✗ FAIL | ✗ FAIL |

**All 5 v7 hybrids beat the production baseline on both adversarial metrics.**  
The 2-dim hybrids achieve dramatically better language invariance (0.49-0.51 vs 0.77) and jurist preference (0.76-0.80 vs 0.51).

### Structural Benchmarks (Informational)

| Representation | Jurivoc L0 NMI | Scale Stability | Cross-Lang Recall@10 | Fractal Imp. Rate | Cluster Coherence |
|---|---|---|---|---|---|
| outcome_tfidf | 0.005 | 0.000 | 0.159 | 99.9% | FAIL (0.485) |
| cited_decisions_tfidf_outcome_hybrid_0.3 | 0.068 | 0.634 | 0.207 | 89.2% | FAIL (0.549) |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.116 | 0.647 | **0.236** | 84.9% | FAIL (0.616) |
| cited_decisions_tfidf_outcome_hybrid_0.7 | **0.164** | **0.663** | 0.231 | 89.4% | FAIL (0.612) |
| cited_decisions_tfidf | **0.246** | 0.597 | 0.208 | **92.3%** | **PASS (0.831)** |
| center_projected_64dim | 0.065 | 0.707 | 0.156 | 64.7% | **PASS (0.861)** |
| center_projected_768 | 0.095 | 0.710 | 0.146 | 60.0% | **PASS (0.854)** |

---

## Analysis

### 1. The `outcome_tfidf` Overfitting Problem

The `outcome_tfidf` representation (2-dim, only outcome labels) achieves the **best adversarial scores** (LangDom=0.455, Jurist=0.832) but **catastrophically fails all structural benchmarks**:
- Jurivoc L0 NMI = 0.005 (no legal taxonomy alignment)
- Scale stability = 0.000 (neighbors completely unstable under subsampling)
- Cross-language retrieval = 0.159 (below 0.2 threshold)
- Cluster coherence = 0.485 (below 0.7 threshold)
- Fractal: 3 coarse → 1200 fine clusters (each decision its own cluster)

This mirrors the `multilingual_e5_small_pretrained` finding from v8 extended: **passing adversarial gates is necessary but not sufficient** for a production-viable representation. The 2-dim outcome space overfits to the adversarial proxies.

### 2. The Hybrid Sweet Spot: `cited_decisions_tfidf_outcome_hybrid_0.7`

The `cited_decisions_tfidf_outcome_hybrid_0.7` (70% cited decisions, 30% outcome) achieves the **best balance** among 2-dim hybrids:
- **Adversarial:** LangDom=0.492 ✓, Jurist=0.790 ✓ (both strong)
- **Jurivoc L0:** 0.164 (highest among 2-dim hybrids, approaching cited_decisions_tfidf's 0.246)
- **Scale stability:** 0.663 (highest among all hybrids, approaching center_projected_64dim's 0.707)
- **Cross-language retrieval:** 0.231 (well above 0.2 threshold)
- **Fractal improvement rate:** 89.4% (zoom reveals legal substructure)
- **Hierarchical advantage:** 0.274 (hierarchical Leiden significantly beats flat)

This representation preserves the language invariance and jurist preference gains from outcome blending while recovering meaningful legal structure from the cited_decisions_tfidf component.

### 3. Trade-off: Dimensionality vs. Structure

| Dim | Representation | Jurist Pref | LangDom | Jurivoc L0 | Scale Stab | Production Viable? |
|---|---|---|---|---|---|---|
| 2 | outcome_tfidf | 0.832 | 0.455 | 0.005 | 0.000 | **NO** (overfits) |
| 2 | cited_decisions_tfidf_outcome_hybrid_0.7 | 0.790 | 0.492 | 0.164 | 0.663 | **MAYBE** (needs Jurivoc boost) |
| 128 | cited_decisions_tfidf | 0.689 | 0.609 | 0.246 | 0.597 | **YES** (passes cluster coherence) |
| 64 | center_projected_64dim | 0.512 | 0.766 | 0.065 | 0.707 | **YES** (current default) |

The 128-dim `cited_decisions_tfidf` remains the **only unsupervised representation passing cluster coherence** (branch purity 0.831 > 0.7 threshold) while also passing both adversarial gates. The 2-dim hybrids sacrifice cluster coherence for better adversarial scores.

### 4. Comparison with v8 Extended Results

| Metric | v8 Best (cited_decisions_tfidf_proc_pairs) | v9 Best Hybrid (0.7) | v9 Best 128-dim (cited_decisions_tfidf) |
|---|---|---|---|
| LangDom | 0.680 | **0.492** | 0.609 |
| Jurist Pref | 0.698 | **0.790** | 0.689 |
| Jurivoc L0 | **0.313** | 0.164 | 0.246 |
| Scale Stab | 0.630 | **0.663** | 0.597 |
| Cross-Lang | 0.208 | **0.231** | 0.208 |
| Fractal Imp. | 81.3% | 89.4% | **92.3%** |

The v9 2-dim hybrids **dominate on adversarial metrics** (language invariance, jurist preference) but **lag on Jurivoc alignment** compared to the v8 Procrustes-aligned 128-dim representation.

---

## Recommendations

### For Production Map Modes (Fractal Map Integration)

1. **Add `cited_decisions_tfidf_outcome_hybrid_0.7` as "Outcome-Aware Citation" map mode**
   - Label: "Precedent + Outcome" 
   - Rationale: Best balance of adversarial robustness + structural coherence among 2-dim hybrids
   - Caveat: Jurivoc L0 (0.164) below PASS threshold (0.3) — monitor in jurist study

2. **Retain `cited_decisions_tfidf` (128-dim) as "Doctrinal Lineage" mode**
   - Only unsupervised representation passing cluster coherence gate
   - Strongest Jurivoc alignment (0.246) among unsupervised

3. **Retain `center_projected_64dim` as default "General Legal" mode**
   - Best scale stability (0.707), cluster coherence (0.861)
   - Weakest adversarial scores — clearly label as baseline

### For Next Evaluation Cycle (v10)

1. **Jurist Human Study** (framework ready per factory direction)
   - Test pairwise preferences on these 3 map modes + metric learning modes
   - Validate simulated jurist proxy against real jurist judgments

2. **Cross-lingual alignment deeper investigation**
   - Apply Procrustes/Joint PCA to `cited_decisions_tfidf_outcome_hybrid_0.7` to boost Jurivoc L0
   - Test section-specific embeddings (sachverhalt, erwaegungen, dispositiv) for cross-lingual coherence

3. **Fine-tuned legal embeddings evaluation**
   - Await multilingual-e5-small fine-tuned on Swiss legal corpus (legal-distance dependency)
   - Evaluate with hierarchy preservation loss to avoid overclustering

4. **Full corpus scale evaluation**
   - Pending corpus lane delivery of 192k decisions
   - Test scale stability of top representations at production scale

---

## Provenance

- **Harness:** evaluation_v3_harness.py (frozen, seed=42, config_hash=4323f833fa72366a)
- **Metadata:** evaluation/data/bger_expanded_1200_metadata.jsonl (1,200 decisions)
- **Embeddings:** /tmp/lex_accepted/legal-distance/legal_distance/results/v7/outcome_cited_hybrids/*.npy
- **Baselines:** /tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/*.npy
- **Results:** evaluation/results/v3_extended/evaluation_v9_outcome_cited_hybrids_results.json
- **Fractal module:** /tmp/lex_accepted/fractal-map/fractal_map/hierarchical/hierarchical_leiden.py

---

## Next Recommendation

**CONTINUE** — The v7 outcome-cited hybrids provide valuable new map modes with superior adversarial robustness. Next cycle should execute jurist human study (factory direction v8 item 4) and test cross-lingual alignment methods on the best hybrid (item 5).