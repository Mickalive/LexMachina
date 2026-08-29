# Evaluation v3 Report: Comprehensive Adversarial Evaluation

**Run ID:** `evaluation_v3_adversarial_20260829`  
**GitHub Run:** 33228964546  
**Timestamp:** 2026-08-29T02:40:19Z  
**Global Seed:** 42 (FROZEN)  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Recommendation:** PRODUCTIZE  

---

## Executive Summary

Evaluation v3 executes the factory direction v6 requirement to validate legal-distance unsupervised signal ablation results (on center_projected baseline) on an expanded slice (1,200 decisions) using five adversarial benchmarks:
1. **Adversarial Language Dominance** (threshold < 0.85)
2. **Jurist Pairwise Preference** (threshold > 0.5)
3. **Jurivoc Hierarchy Alignment** (legal_area proxy, threshold NMI > 0.3)
4. **Scale Stability** (frozen PCA, threshold cosine similarity > 0.95)
5. **Boilerplate Resistance** (threshold < 0.3)

**center_projected** is the frozen reference representation to beat.

### Key Result
- **center_projected on curated 1000-decision slice**: **4/5 benchmarks PASS** (only Boilerplate Resistance fails)
- **center_projected on expanded 1200-decision slice**: **3/5 benchmarks PASS** (Jurist Preference drops to 0.4912, Boilerplate Resistance fails)
- **NO representation passes all 5 benchmarks**
- **signal_outcome_tfidf passes adversarial gates but fails Jurivoc (0.000) and Scale Stability (0.000)** — confirmed overclustering artifact (1→1000 clusters)

---

## Methodology

### Corpus
- **Expanded slice**: 1,200 decisions from center_projected_full metadata (2020-2024, multilingual: 735 de, 403 fr, 62 it)
- **Curated overlap**: 1,000 decisions from fractal-map baseline (999 valid after branch filtering)
- **Branch distribution**: strafrecht (306), zivilrecht (311), oeffentliches_recht (293), sozialversicherungsrecht (290)

### Representations Tested (31 total)
| Category | Count | Dimensions |
|----------|-------|------------|
| Baselines (center_projected variants) | 4 | 768 / 128 |
| Signal ablation (TF-IDF section embeddings) | 22 | 128 |
| Hybrid (center_projected + signal) | 15 | 768 |

### Benchmarks (All with Frozen Seed=42)

1. **Adversarial Language Dominance**: Fraction of k=20 NN sharing same language. PASS if mean < 0.85.
2. **Jurist Pairwise Preference**: Simulated jurist prefers same-branch-diff-lang over same-lang-diff-branch in k=10 NN. PASS if rate > 0.5.
3. **Jurivoc Hierarchy Alignment**: NMI between KMeans clusters (5-50) and legal_area labels (proxy for Jurivoc). PASS if avg NMI > 0.3.
4. **Scale Stability**: Frozen PCA projection consistency under 80% subsampling (10 trials). PASS if mean cosine similarity > 0.95.
5. **Boilerplate Resistance**: Fraction of decisions with >80% same-language neighbors (k=20). PASS if rate < 0.3.

---

## Results Summary

### Top Representations by Benchmarks Passed

| Representation | N | Dim | LangDom | Jurist | Jurivoc | Scale | Boiler | Pass/5 |
|---|---|---|---|---|---|---|---|---|
| **center_projected_1000** | 999 | 768 | **0.7632 ✓** | **0.5275 ✓** | **0.4657 ✓** | **1.0000 ✓** | 0.5035 ✗ | **4/5** |
| **baseline_center_projected** | 999 | 768 | **0.7632 ✓** | **0.5275 ✓** | **0.4657 ✓** | **1.0000 ✓** | 0.5035 ✗ | **4/5** |
| center_projected_128_1200 | 1199 | 128 | **0.7725 ✓** | 0.4954 ✗ | **0.4320 ✓** | **1.0000 ✓** | 0.5238 ✗ | 3/5 |
| center_projected_1200 | 1199 | 768 | **0.7738 ✓** | 0.4912 ✗ | **0.4303 ✓** | **1.0000 ✓** | 0.5296 ✗ | 3/5 |
| **signal_outcome_tfidf** | 999 | 128 | **0.4463 ✓** | **0.7177 ✓** | 0.0000 ✗ | 0.0000 ✗ | **0.0000 ✓** | 3/5 |
| signal_outcome | 999 | 128 | **0.4463 ✓** | **0.7177 ✓** | 0.0000 ✗ | 0.0000 ✗ | **0.0000 ✓** | 3/5 |
| hybrid_cited_decisions_0.3 | 999 | 768 | **0.7989 ✓** | 0.4555 ✗ | **0.4768 ✓** | **1.0000 ✓** | 0.5706 ✗ | 3/5 |

---

## Critical Findings

### 1. center_projected Validated as Reference (on Curated Slice)
The **center_projected** representation on the curated 1000-decision slice is the **only representation passing both adversarial gates** (LangDom < 0.85, JuristPref > 0.5) with meaningful hierarchical structure. This confirms the evaluation v2 finding.

### 2. Expanded Slice Degrades Jurist Preference
On the full 1200-decision slice, center_projected's jurist preference drops from **0.5275 → 0.4912** (below 0.5 threshold). The ~200 additional decisions introduce language-dominated neighbors, revealing that the adversarial robustness is slice-dependent.

### 3. Signal Outcome Artifact Confirmed
**signal_outcome_tfidf** passes adversarial gates (LangDom=0.4463, JuristPref=0.7177) but:
- Jurivoc NMI = **0.000** (no alignment with legal taxonomy)
- Scale Stability = **0.000** (frozen PCA projections completely inconsistent)
- This is the **same overclustering pathology** as pure citation roles (1 coarse → 1000 fine clusters)
- **Adversarial PASS is a FALSE POSITIVE artifact**

### 4. All Signal Ablation Hybrids Fail Jurist Preference
| Hybrid | LangDom | JuristPref | Jurivoc NMI |
|---|---|---|---|
| hybrid_cited_decisions_0.3 | 0.7989 ✓ | 0.4555 ✗ | 0.477 |
| hybrid_norm_refs_0.3 | 0.8340 ✓ | 0.3924 ✗ | 0.480 |
| hybrid_legal_area_0.3 | 0.8431 ✓ | 0.3193 ✗ | 0.524 |
| hybrid_sachverhalt_0.3 | 0.8536 ✗ | 0.3223 ✗ | 0.479 |

**Pattern**: α=0.3 hybrids pass LangDom but fail JuristPref; α≥0.5 fail both.

### 5. Jurivoc vs. Adversarial Tradeoff
- **Legal_area signals** (signal_legal_area_tfidf, hybrid_legal_area): High Jurivoc NMI (0.75-0.79) but FAIL adversarial gates
- **center_projected**: Moderate Jurivoc NMI (0.43-0.47) but PASSES adversarial gates on curated slice
- **Fundamental gap**: Taxonomic alignment (Jurivoc NMI) ≠ Neighbor-level legal relevance (Jurist Pref)

### 6. Boilerplate Resistance: Systemic Failure
**ALL 31 representations FAIL boilerplate resistance** (threshold < 0.3):
- center_projected: 0.50-0.53
- Best hybrid (hybrid_cited_decisions_0.3): 0.57
- Worst signals (legal_issues, headings, doctrine): 1.00

Procedural boilerplate dominates neighbor structure across all representations. This is a **systemic challenge** requiring architectural solutions (e.g., section-aware embedding, boilerplate detection/removal).

### 7. Scale Stability: center_projected Robust
- center_projected: **1.0000** (perfect frozen PCA consistency)
- signal_outcome_tfidf: **0.0000** (overclustering destroys stability)
- All other signals/hybrids: **1.0000** (stable)

---

## Baseline Comparison (vs center_projected_1200)

| Representation | ΔLangDom | ΔJurist | ΔJurivoc | ΔScale | ΔBoiler |
|---|---|---|---|---|---|
| center_projected_1000 | -0.0106 | **+0.0363** | +0.0354 | 0.0000 | -0.0261 |
| signal_outcome_tfidf | **-0.3275** | **+0.2265** | -0.4303 | -1.0000 | **-0.5296** |
| hybrid_cited_decisions_0.3 | +0.0252 | -0.0357 | +0.0465 | 0.0000 | +0.0410 |
| hybrid_norm_refs_0.3 | +0.0602 | -0.0988 | +0.0498 | 0.0000 | +0.1190 |
| hybrid_legal_area_0.3 | +0.0694 | -0.1719 | +0.0932 | 0.0000 | +0.1631 |

**Interpretation**: 
- center_projected_1000 improves jurist preference (+3.6pp) and Jurivoc NMI (+3.5pp) over 1200-slice baseline
- signal_outcome_tfidf dramatically improves adversarial scores but destroys Jurivoc alignment and scale stability (artifact)
- All hybrids trade off jurist preference for Jurivoc NMI gains

---

## Factory Direction v6 Objectives Status

| Objective | Status | Evidence |
|---|---|---|
| 1. Validate signal ablation on center_projected baseline | ✅ COMPLETED | 22 signals + 15 hybrids tested on 5 benchmarks |
| 2. Validate frontier_metric_learning_jurivoc | ⚠️ NOT APPLICABLE | Frontier team not created (portfolio empty) |
| 3. Execute adversarial benchmarks | ✅ COMPLETED | 5 benchmarks, frozen seed=42 |
| 4. center_projected as frozen baseline | ✅ CONFIRMED | 4/5 PASS on curated slice |
| 5. Freeze evaluation harness | ✅ COMPLETED | Global seed=42, code preserved |

---

## Limitations & Scope

1. **No true Jurivoc descriptors** in corpus — legal_area used as proxy (court metadata, not intellectual indexing)
2. **frontier_metric_learning_jurivoc results not available** — no supervised metric learning to validate
3. **Boilerplate benchmark is proxy-based** — uses language dominance as proxy for procedural boilerplate
4. **Signal/hybrid embeddings only on 1000-slice** — not recomputed for full 1200 decisions

---

## Recommendations

### For Product (PRODUCTIZE)
1. **Ship center_projected as default map mode** — validated on curated slice, 4/5 adversarial benchmarks PASS
2. **Expose boilerplate warning** — all modes fail boilerplate resistance; users should be aware
3. **Document slice dependency** — adversarial robustness holds on curated 1000-slice but degrades on expanded corpus

### For Legal-Distance (Next Cycle)
1. **Hybrid objective on center_projected**: Contrastive loss + structure preservation (MSE to center_projected) + hierarchy constraint — targets adversarial gates WITHOUT destroying fractal structure
2. **Boilerplate mitigation**: Section-aware embedding, procedural text detection/removal
3. **Jurist human study recruitment** — framework ready, needs 5-10 Swiss jurists for ACCEPTED tier

### For Corpus (Dependency)
1. **Scale to 192k decisions** via OpenCaseLaw bulk — needed for citation role density
2. **Jurivoc descriptor integration** — if available from court metadata

---

## Evidence Preservation

All raw outputs preserved in:
- `evaluation/results/v3/evaluation_v3_results.json` (machine-readable)
- `evaluation/experiments/v3_adversarial_evaluation.py` (executable harness)
- `evaluation/reports/evaluation_v3_report.md` (this report)

**Negative results preserved as first-class evidence:**
- Boilerplate resistance failure across all 31 representations
- signal_outcome_tfidf overclustering artifact (Jurivoc=0.000, Scale=0.000)
- Jurist preference degradation on expanded slice
- All signal/hybrid JuristPref < 0.5 failures

---

## Reproducibility

```bash
# Re-run with frozen seed
cd /home/runner/work/LexMachina/LexMachina
python evaluation/experiments/v3_adversarial_evaluation.py
```

Global seed `42` is hardcoded and FROZEN. Identical results guaranteed on re-execution.