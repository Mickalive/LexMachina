# Evaluation Lane - cited_decisions_tfidf Validation Report

**Run ID:** `eval_v3_cited_decisions_validation_20260829`  
**Date:** 2026-08-29  
**Factory Direction:** v6  
**Global Seed:** 42 (frozen)  
**Config Hash:** `4323f833fa72366a`  
**Evidence Tier:** REPRODUCED  

---

## Executive Summary

Evaluated the `cited_decisions_tfidf` representation (TF-IDF on cited decision IDs) against the **frozen Evaluation v3 adversarial harness** on the expanded 1,200-decision slice. This representation was identified in the legal-distance lane's `hybrids_adversarial_test` as a **new candidate passing both adversarial gates** with meaningful hierarchical structure (LangDom=0.6086, JP=0.6889).

**Key Finding:** `cited_decisions_tfidf` **PASSES both critical adversarial gates** and achieves the **best scores of any representation tested to date** on the two primary adversarial metrics:

| Metric | cited_decisions_tfidf | linear_metric_epoch4 | center_projected_64dim |
|--------|----------------------|---------------------|------------------------|
| **Language Dominance** | **0.6117** ⭐ (best) | 0.6805 | 0.7664 |
| **Jurist Preference** | **0.6922** ⭐ (best) | 0.6847 | 0.5121 |
| **Both Gates** | ✅ PASS | ✅ PASS | ✅ PASS |

**However, it FAILS two secondary benchmarks:**
- **Jurivoc Level 0 NMI:** 0.2237 (FAIL, threshold 0.3) — does not recover 4-branch legal taxonomy
- **Cross-Language Retrieval:** 0.1798 (FAIL, threshold 0.2) — cannot reliably find cross-language legal equivalents

---

## Detailed Benchmark Results

### 1. Adversarial Language Dominance (Threshold: < 0.85) ✅ PASS
**Mean dominance: 0.6117** — Lowest of all representations tested. 10.5% better than linear_metric_epoch4 (0.6805), 20.2% better than baseline (0.7664). Language plays minimal role in nearest neighbors.

### 2. Jurist Pairwise Preference (Threshold: > 0.5) ✅ PASS
**Legal neighbor rate: 0.6922** — Highest of all representations tested. 0.75% better than linear_metric_epoch4 (0.6847), 35.2% better than baseline (0.5121). Simulated jurist would succeed in 69.2% of decisions.

### 3. Jurivoc Hierarchy Alignment ❌ FAIL (Level 0)
| Level | NMI | Threshold | Status |
|-------|-----|-----------|--------|
| Level 0 (4 branches) | **0.2237** | > 0.3 | ❌ FAIL |
| Level 1 (16 legal areas) | 0.3358 | > 0.2 | ✅ PASS |
| Nesting Score | 0.7006 | — | — |

**Critical weakness:** Cannot recover the high-level 4-branch legal taxonomy (öffentliches_recht, zivilrecht, strafrecht, sozialversicherungsrecht). Breakthrough representations achieve 0.64–0.74.

### 4. Cross-Language Retrieval ❌ FAIL
**Mean Recall@10: 0.1798** — Below 0.2 threshold. A jurist searching for French/Italian equivalents of a German decision finds <1 in 5 relevant cases. All breakthrough representations pass this (0.21–0.24).

### 5. Scale Stability ✅ PASS
**Mean neighbor overlap: 0.6025** — Acceptable stability under corpus subsampling. Lower than breakthrough representations (0.70–0.72) but passes threshold (>0.5).

### 6. Boilerplate Resistance (proxy) ❌ FAIL
**Resistance score: -0.7472** — This chamber/legal_area proxy metric fails for ALL representations (including breakthroughs). The perturbation-based test (separate) shows all representations highly resistant. This proxy may not discriminate well.

### 7. Fractal Quality (Hierarchical Leiden) ⭐ EXCEPTIONAL
| Metric | Value | Assessment |
|--------|-------|------------|
| Coarse clusters | 7 | Good domain structure |
| Fine clusters | 278 | Rich substructure |
| Coarse purity | 0.6253 | Moderate |
| Fine purity | 0.9164 | High |
| **Improvement rate** | **97.1%** | **HIGHEST of all representations** |
| Legal area NMI | 0.5631 | Good |
| Hierarchical advantage | 0.1682 | **High** (vs 0.025 for linear_metric) |

**Zoom reveals dramatic legal structure refinement** — 97.1% of coarse clusters show purity improvement when zoomed to fine level. This is the most "zoom-revealing" representation tested.

### 8. Cluster Coherence (Simulated Jurist) ✅ PASS
- Mean branch purity: 0.8121 (threshold 0.7)
- Branch NMI: 0.3283
- Mean language purity: 0.7461

---

## Comparative Analysis

### vs. Production Baseline (center_projected_64dim)
| Metric | Delta | Assessment |
|--------|-------|------------|
| Language Dominance | -0.1547 | **Significantly better** |
| Jurist Preference | +0.1801 | **Significantly better** |
| Jurivoc L0 NMI | +0.1584 | Improved but still FAIL |
| Cross-lang Retrieval | +0.0240 | Improved but still FAIL |
| Fractal Imp. Rate | +32.5% | **Dramatically better** |

### vs. Best Breakthrough (linear_metric_epoch4)
| Metric | Delta | Assessment |
|--------|-------|------------|
| Language Dominance | **-0.0689** | **Better (more language-invariant)** |
| Jurist Preference | **+0.0075** | **Slightly better** |
| Jurivoc L0 NMI | **-0.4658** | **Much worse** |
| Cross-lang Retrieval | -0.0316 | **Worse (FAIL vs PASS)** |
| Fractal Imp. Rate | **+25.1%** | **Better** |
| Hier. Advantage | **+0.143** | **Much better** |

---

## Interpretation

### What cited_decisions_tfidf EXCELS at:
1. **Pure legal relevance** — Cited decisions are inherently legal signals, free from procedural boilerplate
2. **Language invariance** — Citation IDs (BGE/ATF numbers) are language-agnostic by nature
3. **Fractal zoom coherence** — Hierarchical structure reveals increasingly specific legal topics at finer resolutions
4. **Jurist utility** — Highest simulated jurist success rate (69.2%)

### What cited_decisions_tfidf LACKS:
1. **High-level legal taxonomy recovery** — Doesn't naturally cluster by the 4 main legal branches
2. **Cross-language legal equivalence** — Cannot reliably map German↔French↔Italian decisions on the same legal issue
3. **Broad legal area structure** — Fine-grained (278 clusters) but coarse structure (7 clusters) doesn't align with Jurivoc L0

### Why this happens:
Cited decisions form a **citation network** that reflects precedent relationships and doctrinal lineages, not statutory subject-matter classification. Two decisions citing the same precedent may be in different legal branches. The citation graph captures *doctrinal* proximity, not *taxonomic* proximity.

---

## Recommendations

### FOR PRODUCT LANE — CONDITIONAL INTEGRATION
**Add as "Doctrinal Lineage" map mode (specialized):**
- ✅ Exposes unique view: precedent/citation-based proximity
- ✅ Best language invariance and jurist preference scores
- ✅ Exceptional fractal zoom behavior (97.1% improvement rate)
- ⚠️ **Must be clearly labeled**: "Optimized for doctrinal lineage, NOT for legal taxonomy browsing or cross-language search"
- ⚠️ Should NOT replace linear_metric_epoch4 as "Cross-Lingual Legal" default

### FOR LEGAL-DISTANCE LANE
- **Investigate hybrid with center_projected**: Combine citation signal (doctrinal) + center_projected (taxonomic/language-invariant) to get best of both
- The cited_decisions_tfidf + center_projected hybrid at α=0.3–0.5 could potentially:
  - Retain high jurist preference (>0.65)
  - Improve Jurivoc L0 NMI toward 0.5+
  - Improve cross-language retrieval above 0.2
  - Maintain strong fractal structure

### FOR EVALUATION LANE
- **No further v3 cycles needed** — frozen harness has validated this candidate
- **Recommendation**: `continue_recommended = false` for current factory direction question
- **Next factory direction** should consider: "Evaluate citation-semantic hybrids against full benchmark suite"

---

## Evidence Preservation

All raw outputs preserved per Research Protocol:
- Embeddings: `evaluation/results/v3_cited_decisions/cited_decisions_tfidf_1200.npy`
- Full evaluation: `evaluation/results/v3_cited_decisions/cited_decisions_tfidf_v3_evaluation.json`
- Source experiment: `legal_distance/experiments/v6_test_hybrids_adversarial.py`
- Adversarial test result: `legal_distance/results/v6/hybrids_adversarial_test/hybrid_adv_cited_decisions_tfidf_results.json`

Negative results (Jurivoc L0 FAIL, Cross-language FAIL, Boilerplate proxy FAIL) preserved as first-class evidence.

---

## Reproducibility Confirmation

- **Global seed:** 42 (frozen in harness)
- **Config hash:** `4323f833fa72366a` (immutable, matches all prior v3 runs)
- **Prior verifications:** Run 33226955300, 33228419477, 33234209188 — exact match on critical adversarial tests
- **This run:** Deterministic reproduction of v3 adversarial benchmarks + new candidate evaluation

---

## Next Steps for Factory Director

1. **Product Lane**: Integrate `linear_metric_epoch4` as "Cross-Lingual Legal" default map mode (passes ALL gates)
2. **Product Lane**: Add `cited_decisions_tfidf` as "Doctrinal Lineage" specialized mode with clear labeling
3. **Legal-Distance Lane**: Test cited_decisions_tfidf + center_projected hybrids (α=0.3, 0.5) against full v3 suite
4. **Evaluation Lane**: Frozen — no further cycles under current factory direction v6
5. **Corpus Lane**: Scale to 192k to unlock citation role density (current 4.5% resolution at 1,200 decisions)
6. **Frontier**: Decide on `frontier_metric_learning_jurivoc` dispatch or removal

---

*Generated: 2026-08-29 | Factory Direction v6 | Evaluation Lane*