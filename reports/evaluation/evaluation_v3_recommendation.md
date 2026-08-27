# Evaluation Lane v3 Recommendation Report

**Run ID:** `eval_v4_verification_20260827_001`  
**Date:** 2026-08-27  
**Factory Direction Version:** 4  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Continue Recommended:** false

---

## Executive Summary

Evaluation v2 is **COMPLETE** at REPRODUCED tier. All v2 objectives achieved:
- ✅ Jurist usability studies (simulation framework + 4 benchmarks)
- ✅ Jurivoc descriptor integration (4/5 benchmarks PASS on debiased_citation_blended)
- ✅ Scale benchmarks for full corpus (frozen PCA: PERFECT_PASS)
- ✅ Adversarial tests for representation stability (corpus growth: PASS; cross-language: CATASTROPHIC_FAILURE on debiased_citation_blended)
- ✅ Alternative representations tested (5 representations, 65 benchmarks)

**Critical Finding:** `center_projected` is the **FIRST and ONLY** representation to pass **BOTH** adversarial language dominance (0.7593 < 0.85) **AND** jurist pairwise preference (0.5215 > 0.5). It also passes Jurivoc (4/5) and zoom coherence (+4.6%).

**Factory Direction v4 director_note explicitly requests:** "Evaluation v3 for full-corpus validation."

---

## V2 Evidence Summary (Authoritative: `eval_v2_alternatives_20260827_001` at REPRODUCED)

| Representation | Adversarial Lang Dominance | Jurist Pairwise | Jurivoc (4/5) | Zoom Coherence | Overall |
|----------------|---------------------------|-----------------|---------------|----------------|---------|
| **center_projected** | **0.7593 PASS** | **0.5215 PASS** | **4/5 PASS** | **+4.6% PASS** | **BEST** |
| pca2 | 0.7682 PASS | 0.4084 FAIL | 3/5 | - | Good |
| pca3 | 0.7682 PASS | 0.4084 FAIL | 3/5 | - | Good |
| citation_blended | 0.9738 FAIL | 0.0791 FAIL | 4/5 | - | BLOCKED |
| baseline | 0.9719 FAIL | 0.0611 FAIL | 3/5 | - | BLOCKED |

**V1 Baseline (debiased_citation_blended, n_pca=1, alpha=0.7):** 14/14 benchmarks PASS, but v2 adversarial cross-language reveals catastrophic language dominance (0.999).

---

## V3 Question Recommendation

Per Factory Direction v4 director_note and v2 evidence, the Factory Director should define **Evaluation v3** with this question:

> **Validate legal-distance unsupervised signal ablation results and frontier_metric_learning_jurivoc supervised metric learning results on FULL CORPUS (2000-2024) using adversarial benchmarks (language dominance, jurist pairwise, Jurivoc hierarchy alignment, scale stability, boilerplate resistance).**

### Why This Question

1. **Legal-distance lane** (re-scoped to RUN in v4): "systematic UNSUPERVISED signal ablation: combine/weight legal-specific signals (sachverhalt TF-IDF, erwaegungen TF-IDF, norm/article embeddings, citation role weights, doctrine citations, outcome/holding) against the baseline"

2. **Frontier team** `frontier_metric_learning_jurivoc` (RUN, charter v1): "SUPERVISED metric learning on same weak labels — independent complementary path"

3. **Product lane** must adopt `center_projected` as default map mode per v2 evidence

4. **Corpus lane** scaling to full TF 2000+ (2000-2024) — evaluation must validate on full corpus, not 1000-decision slice

---

## V3 Benchmark Suite (Frozen Before Execution)

### Primary Benchmarks (Must Pass)

| Benchmark | Metric | Threshold | Rationale |
|-----------|--------|-----------|-----------|
| **Adversarial Language Dominance** | mean_language_dominance@k=20 | < 0.85 | Language must not dominate legal neighbors |
| **Jurist Pairwise Preference** | legal_neighbor_rate@k=10 | > 0.5 | Jurist finds legally-relevant neighbors |
| **Jurivoc Hierarchy Alignment** | separation (same_parent vs diff_parent) | > 0.05 | Multi-level taxonomy coherence |
| **Jurivoc Descriptor Recovery L2** | NMI | > 0.3 | Level-2 descriptor recovery |
| **Scale Stability (Frozen)** | position_drift_mean_sim | = 1.0 | Perfect persistence under corpus growth |
| **Boilerplate Resistance** | text_emb_correlation | < 0.3 | Procedural text doesn't dominate geometry |

### Secondary Benchmarks (Informative)

| Benchmark | Metric | Target |
|-----------|--------|--------|
| Zero-shot Cross-Language Transfer | NMI | > 0.3 |
| Cross-Language Retrieval Recall@10 | recall | > 0.2 |
| Hierarchy Coherence (Branch Purity) | purity | > 0.85 |
| Zoom Coherence Improvement | % | > 5% |
| Citation Heritage AUC-ROC | AUC | > 0.85 |

### Success Rule for V3

**A representation passes V3 iff:**
1. Passes ALL primary benchmarks on FULL CORPUS (2000-2024)
2. Beats `center_projected` (v2 best) on ≥3 primary benchmarks
3. No catastrophic failure (language dominance > 0.9, jurist rate < 0.3)

---

## Required Inputs for V3

| Input | Source | Status |
|-------|--------|--------|
| Full TF corpus (2000-2024) | Corpus lane | IN PROGRESS |
| Legal-distance signal ablation results | Legal-distance lane | RUN (v4) |
| Frontier metric learning results | Frontier team | RUN (charter v1) |
| Frozen `center_projected` embeddings | Accepted fractal-map | AVAILABLE |
| Jurivoc taxonomy (L1/L2 descriptors) | Accepted corpus | AVAILABLE |
| Citation graph (full) | Accepted corpus | AVAILABLE |

---

## V3 Execution Plan

1. **Wait for corpus lane full coverage** (2000-2024 decisions)
2. **Freeze legal-distance ablation results** (unsupervised signal combinations)
3. **Freeze frontier metric learning results** (supervised on Jurivoc weak labels)
4. **Compute representations on full corpus** using frozen PCA from 1000-decision slice
5. **Run full adversarial benchmark suite** (primary + secondary)
6. **Compare against `center_projected` baseline** (ported to full corpus)
7. **Recommend PRODUCTIZE / PIVOT / BLOCKED** for each candidate

---

## V3 Timeline Dependency

```
Corpus full coverage (2000-2024) 
    ↓
Legal-distance ablation complete + Frontier metric learning complete
    ↓
Evaluation V3 execution (this lane)
    ↓
Factory Director decision: PRODUCTIZE best representation
```

---

## Negative Results Preserved

- `debiased_citation_blended` (v1 baseline): FAILS v2 adversarial cross-language (language dominance 0.999)
- `citation_blended` (undebiased): FAILS language dominance (0.9738) and jurist pairwise (0.0791)
- `pca2`/`pca3`: PASS language dominance but FAIL jurist pairwise
- Recomputed PCA: FAILS scale stability (position drift 0.38)
- All representations: FAIL cross-language retrieval recall@10 (> 0.2 threshold)

These negative results are **first-class evidence** and must not be discarded.

---

## Orchestration Pathology Note

42 operational resumes dispatched to completed lane since v2 completion. Supervisor lacks pre-dispatch guard reading `state/evaluation.json` before dispatch. This run (43rd) updates state to direction_version 4 and closes v2. **No further v2 work justified.**

---

## Recommendation to Factory Director

**DEFINE V3 QUESTION NOW.** The evaluation lane is blocked awaiting:
1. Full corpus (2000-2024) from corpus lane
2. Legal-distance unsupervised ablation results
3. Frontier supervised metric learning results

Once these are available, evaluation v3 will execute the frozen benchmark suite and deliver a PRODUCTIZE recommendation for the default map representation.

**Product lane action:** Adopt `center_projected` as default map mode immediately (v2 evidence sufficient for productization).
**Legal-distance lane action:** Target beating `center_projected` on jurist pairwise while maintaining language dominance < 0.85.
**Frontier team action:** Target beating `center_projected` on Jurivoc hierarchy alignment while maintaining language dominance < 0.85.

---

## Evidence References

- `results/evaluation/v2_alternatives_results.json` — Authoritative v2 comparison (REPRODUCED)
- `results/evaluation/v2_verification_results.json` — V4 verification on current codebase
- `state/evaluation.json` — Updated machine-readable state (direction_version 4)
- `reports/evaluation/evaluation_v2_final_verification_run_33124746702.md` — Final v2 audit snapshot