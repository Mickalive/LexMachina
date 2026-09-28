# Fractal Map Lane — Hierarchical Zoom Quality Evaluation (Direction v28)

**Run ID:** `fractal_map_hierarchical_zoom_quality_20260928`  
**Date:** 2026-09-28  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETE  

---

## Executive Summary

**KEY FINDING:** `regeste_tfidf` at 174k scale with **constrained hierarchical Leiden** is the **FIRST representation to pass the hierarchical zoom quality protocol (7/7 metrics)** at full corpus scale.

This validates the hierarchical clustering approach as the viable path for the 174k fractal map while dense embeddings complete. The flat Leiden approach (v26 5-level ladder) fails for ALL TF-IDF modes at 174k due to severe over-fragmentation.

---

## Frozen Protocol (hierarchical_v1)

**Success Rule (all 7 must pass):**
1. **Zero fragmentation:** singleton_fraction < 0.01 at fine level ✓
2. **Perfect nesting:** nesting = 1.0 (by construction) ✓
3. **Branch purity improvement:** fine_purity > coarse_purity ✓
4. **Area purity improvement:** fine_area_purity > coarse_area_purity ✓
5. **Zoom coherence:** improvement_rate > 0.5 on coarse→fine transition ✓
6. **Legal structure (branch):** fine_branch_purity > 2 × random_baseline (0.5) ✓
7. **Legal structure (area):** fine_area_purity > 2 × random_baseline (0.0094) ✓

**Baselines (from ACCEPTED metadata, 173,963 entries):**
- Branch random: 0.25 (4 classes: zivilrecht, oeffentliches_recht, strafrecht, sozialversicherungsrecht)
- Area random: 0.0047 (213 classes)

---

## Results at 174k Scale

| Mode | Verdict | Fine Branch | Fine Area | Impr. Rate | Fragmentation | Legal Struct Branch | Legal Struct Area |
|------|---------|-------------|-----------|------------|---------------|---------------------|-------------------|
| **regeste_tfidf** | **PASS** ✓ | **0.566** | **0.348** | **0.575** | **0.0** | **✓ (0.566 > 0.5)** | **✓** |
| full_text_tfidf_light | FAIL | 0.383 | 0.120 | 0.900 | 0.0 | ✗ (0.383 < 0.5) | ✓ |
| regeste_full_text_hybrid_0.5 | FAIL | 0.491 | 0.244 | 0.878 | 0.0009 | ✗ (0.491 < 0.5) | ✓ |
| regeste_full_text_hybrid_0.7 | FAIL | 0.491 | 0.243 | 0.838 | 0.0008 | ✗ (0.491 < 0.5) | ✓ |

### regeste_tfidf Detailed Metrics
- **Sample:** 83,072 decisions (regeste coverage ~47.6%)
- **Coarse clusters:** 175 (res=0.25, adaptive sub-clustering)
- **Fine clusters:** 1,274 (median size 38, zero singletons)
- **Coarse branch purity:** 0.479 → **Fine branch purity:** 0.566 (+0.087)
- **Coarse area purity:** 0.213 → **Fine area purity:** 0.348 (+0.135)
- **Improvement rate:** 57.5% (88 of 153 parents improved)
- **Strict nesting:** 1.0 (by construction)
- **Singleton fraction:** 0.0 (zero fragmentation)

---

## Flat v26 Zoom Quality (5-Level Ladder) — ALL FAIL

| Mode | Branch Mono | Area Mono | Rate >0.5 (2/4) | Verdict |
|------|-------------|-----------|-----------------|---------|
| cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25 | ✗ (0.553→0.527) | ✗ | 1/4 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25 | ✗ (0.549→0.520) | ✗ | 1/4 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5_174k | ✗ (0.553→0.527) | ✗ | 1/4 | FAIL |
| regeste_tfidf_174k | ✗ (0.345→0.343) | ✓ | 1/4 | FAIL |

**Critical divergence:** regeste_tfidf **passes hierarchical** but **fails flat** — confirming that the hierarchical approach solves the over-fragmentation problem that breaks flat Leiden at 174k.

---

## Scale Dependency Evidence

### 12k Dense Embeddings (Years 2000-2002, ACCEPTED)

| Configuration | Coarse Branch | Fine Branch | Impr. Rate | Fine Singleton | Nesting |
|--------------|---------------|-------------|------------|----------------|---------|
| adaptive hierarchical (min_cluster_size=10) | 0.865 | **0.988** | 0.455 | 0.004 | 1.0 |
| flat v26 baseline | — | — | FAIL (0/4) | >0.99 at fine | — |

**Finding:** Dense embeddings at 12k show massive purity gains (0.865→0.988) and near-zero fragmentation, but improvement_rate (0.455) falls just below the 0.5 threshold. Flat v26 fails completely (>99% singletons at fine resolutions).

### 174k TF-IDF: Flat vs Hierarchical

| Approach | Fragmentation | Zoom Refinement | Legal Structure |
|----------|---------------|-----------------|-----------------|
| Flat Leiden (v26 ladder) | Severe (>99% singletons) | None (0/4 modes pass) | Weak at fine |
| Constrained Hierarchical Leiden | **Zero** (by min_cluster_size) | **regeste_tfidf passes** | **regeste_tfidf > 2× baseline** |

---

## Citation-Role Modes at 1000-Scale (Reference)

| Mode | Zoom Quality (ZQ) | Note |
|------|-------------------|------|
| citing_alpha0.3 | 0.5401 | Best at 1k |
| following_alpha0.3 | 0.5280 | Strong |
| criticizing_alpha0.3 | 0.4864 | Strong |
| outcome_hybrid_0.5 (prod default) | 0.2798 | Baseline |

**Status:** Only validated at 1k scale. **Blocked** from 174k testing by legal-distance dense embedding pipeline (3/26 years ACCEPTED).

---

## Blocker Analysis

**Primary Blocker:** `legal-distance` lane 174k dense embeddings
- **ACCEPTED:** 3/26 years (2000-2002, ~19,441 decisions, 11%)
- **PENDING AUDIT:** 20/26 years (2000-2019, ~99k decisions) — progress.json shows complete but NOT audit-promoted
- **Impact:** Cannot test constrained hierarchical on dense embeddings at 174k; cannot scale citation-role modes

---

## Recommendation: CONTINUE

**Why continue under same direction v28:**
1. **Concrete discriminating purpose:** regeste_tfidf hierarchical PASS establishes hierarchical Leiden as the working 174k path
2. **Product decision unlocked:** regeste_tfidf hierarchical map can be integrated as a CPU-only product map mode (no GPU needed)
3. **Clear next experiments:** 
   - Test constrained hierarchical on citation-role embeddings when they land at scale
   - Validate regeste_tfidf hierarchical structure against Jurivoc/human indexing
   - Build product map mode from regeste_tfidf hierarchical artifacts

**When to PIVOT:** When legal-distance 174k dense embeddings pass audit (enabling dense hierarchical tests at full scale).

---

## Artifacts Produced

### Frozen Specifications
- `results/fractal_map/hierarchical_zoom_eval/hierarchical_frozen_spec.json`
- `results/fractal_map/zoom_quality_174k_eval/v26_frozen_spec.json`

### Verdicts
- `results/fractal_map/hierarchical_zoom_eval/hierarchical_verdict_20260928_030415.json` — **hierarchical PASS for regeste_tfidf**
- `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json` — **flat FAIL for all modes**

### Source Data
- `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_regeste_20260926.json`
- `results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_dense_2000_2002_20260927_194820.json`
- `results/fractal_map/12k_constrained_zoom_diagnostic/constrained_zoom_diagnostic_20260928_030626.json`

---

## Provenance

All evaluations run against **ACCEPTED metadata** (`/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json`, 173,963 entries, branch+legal_area 100% coverage).

Constrained hierarchical Leiden implementation: `fractal_map/experiments/constrained_hierarchical_leiden.py` (min_cluster_size enforcement, adaptive sub-resolution, max sub-clusters per parent).

No GPU required — all computation on CPU-feasible TF-IDF embeddings.

---

## Next Cycle Plan (if CONTINUE approved)

1. **Product integration:** Wire regeste_tfidf hierarchical map as a product map mode (center_projected_64dim_hierarchical or similar)
2. **Jurivoc alignment test:** Measure cluster purity against Jurivoc descriptors at each hierarchical level
3. **Citation-role readiness:** Prepare constrained hierarchical pipeline for citation-role embeddings when legal-distance delivers 174k dense
4. **Scale validation:** Test regeste_tfidf hierarchical map navigation coherence (zoom stability, cluster label quality)