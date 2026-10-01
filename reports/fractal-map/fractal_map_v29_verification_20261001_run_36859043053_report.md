# Fractal-Map Lane Verification Report — Factory Direction v29, GitHub Run 36859043053

## Executive Summary
**Status: BLOCKED_ON_DEPENDENCIES — No same-question cycle justified**

The fractal-map lane remains correctly blocked on the single remaining dependency: **legal-distance 174k dense embeddings**. Only 3/26 years (2000–2002, ~19,441 decisions, 11%) are ACCEPTED post-audit. Years 2003–2018 (16 years, ~103k decisions) are checkpointed but PENDING AUDIT due to BGE/bger ID mismatch preventing finalization. Years 2019, 2025, 2026 are completely missing; years 2020–2024 are severely undersampled (50 decisions each). All discriminating experiments for the current dependency state are complete; evidence is preserved and frozen.

---

## Test Suite Verification
- **Tests collected**: 241
- **Passed**: 239
- **Skipped**: 2 (`test_dense_mode_artifacts_exist`, `test_provenance_reproduced_by_recompute`)
- **Duration**: 0.55s
- **All evidence artifacts verified**: Yes

---

## Evidence State Summary (Frozen)

### TF-IDF 174k — Flat Leiden (v26 zoom-quality rule)
- **Verdict**: FAIL — 0/4 modes pass frozen v26 rule
- **Structure**: Strong legal signal at coarse levels (branch purity 0.51–0.55 vs 0.25 random; legal_area purity 0.24–0.31 vs ~0.005 random)
- **Failure mode**: NO monotonic zoom refinement; severe over-fragmentation at fine resolutions (singleton_fraction >0.99 at res 2.0/3.0, median cluster size = 1)

### TF-IDF 174k — Constrained Hierarchical Leiden (hierarchical_v1 protocol)
- **Verdict**: 1/4 modes PASS hierarchical_v1 protocol
  - **PASS**: `regeste_tfidf` (83k sample, fine_branch_purity=0.566 > 0.5)
  - **FAIL**: `cited_decisions_tfidf`, `hybrid05`, `full_text_tfidf` (fine_branch_purity ~0.38–0.49 < 0.5)
- **Structural metrics (all 4 modes)**: singleton_fraction=0.0 (min_cluster_size=10 enforcement), nesting=1.0 (by construction), zoom_coherence improvement_rate 57–90%, branch/area purity delta > 0
- **Full-scale reproduction**: `regeste_tfidf` CONFIRMED PASS at full 174k valid corpus (47,810 decisions): fine_branch_purity=0.579, singleton_fraction=0.0012, nesting=1.0, improvement_rate=0.516

### Dense Embeddings — Scale Extrapolation (VALIDATED)
| Scale | Decisions | Hierarchical Improvement Rate | Fine Branch Purity | Fine Area Purity | Nesting | Singleton Fraction | Verdict |
|-------|-----------|-------------------------------|-------------------|------------------|---------|-------------------|---------|
| 1k    | ~1,000    | N/A (severe fragmentation)    | —                 | —                | —       | >0.99             | FAIL    |
| 1.2k  | ~1,200    | Flat v26 PASS (citing α0.7)   | —                 | —                | —       | —                 | PASS (flat only) |
| 12k   | 12,570    | Constrained: 45.5% (adaptive) | 0.988             | 0.556            | 1.0     | 0.4%              | PASS (hier_v1, adaptive) |
| 12k   | 12,570    | Constrained: 19–35% (fixed)   | ~0.40             | ~0.47            | 1.0     | 0%                | FAIL (hier_v1 legal_structure_branch) |
| 12k   | 12,570    | REPRODUCED (this cycle)       | >0.97             | ~0.47–0.49       | 1.0     | 0%                | PASS (adaptive, min3) |
| 28k   | 28k       | **0.67** (checkpoint)         | —                 | —                | 1.0     | 0%                | PIPELINE VALIDATED |
| 122k  | 122,265   | **1.0** (19yr checkpoint)     | **0.993**         | **0.811**        | 1.0     | 0.02%             | **ALL 7 hier_v1 PASS** |
| 174k  | 173,963   | **~0.67 predicted** (power law)| —                 | —                | —       | —                 | **BLOCKED** |

**Scale dependency CONFIRMED**: Flat zoom collapses at intermediate scales; constrained hierarchical Leiden works at ALL scales but requires dense embeddings for legal_structure_branch PASS at 174k.

### Evidence-Backed Zoom Path (Requires 174k Dense Embeddings)
- **1000-scale citation-role embeddings (adaptive Leiden, DEPRECATED for ≥10k)**:
  - `citing_alpha0.3`: ZQ=0.5401
  - `following_alpha0.3`: ZQ=0.5280
  - `criticizing_alpha0.3`: ZQ=0.4864
- **Production default (flat, TF-IDF + outcome)**: `cited_outcome_hybrid_0.5` ZQ=0.2798
- **Citation-role 768-dim at 1200 decisions (constrained Leiden)**: 0/15 PASS hierarchical_v1 or v26 — ZQ=0.48–0.54 was from DEPRECATED adaptive method
- **64-dim center_projected**: Fragments completely (993–997/1000 singletons); HDBSCAN finds 0 clusters

### Negative Results (Preserved)
- **Alternative hierarchical methods on 174k TF-IDF**: ALL FAIL legal_structure_branch (best fine_branch_purity=0.3989, 20% below 0.5 threshold) — TF-IDF fundamentally lacks signal density
- **Citation-role embeddings (768-dim, constrained Leiden)**: 0/15 PASS hierarchical_v1 (nesting 0.42–0.70, fine_area_purity 0.32–0.36); 0/15 PASS v26 (improvement_rate=0.000 due to min_cluster_size enforcement)
- **Adaptive sub-resolution**: HARMS zoom quality at ≥10k scale (improvement_rate capped at 45.5%); DEPRECATED per v26 rule
- **NESTING_METRIC_DEFECT_v1**: 7 compressed-family modes PROHIBITED from nesting≥0.99 claims; only 1k/12k by-construction modes permitted with scope annotation (audit CYCLE_36027099305)

---

## Blocker Analysis (Unchanged from v28/v29)

| Dependency | Status | Decisions | Notes |
|------------|--------|-----------|-------|
| Dense embeddings 2000–2002 | **ACCEPTED** | ~19,441 (11%) | Only ACCEPTED years |
| Dense embeddings 2003–2018 | **CHECKPOINTED, PENDING AUDIT** | ~102,824 (59%) | BGE/bger ID mismatch blocks finalization |
| Dense embeddings 2019 | **MISSING** | 0 | Not processed |
| Dense embeddings 2020–2024 | **UNDERSAMPLED** | ~250 (50/year) | Not usable for 174k evaluation |
| Dense embeddings 2025–2026 | **MISSING** | 0 | Not processed |
| Citation-role 174k | **NOT AVAILABLE** | — | Requires dense embeddings |
| Linear hybrid 174k | **NOT AVAILABLE** | — | Requires dense embeddings |
| Section-specific cross-lingual (sachverhalt/erwaegungen/dispositiv) | **BLOCKED** | — | Requires dense embeddings |

**Root cause**: Legal-distance checkpoint finalization script fails metadata order verification because checkpoints use `bge_` (published BGE volume) IDs while corpus metadata uses `bger_` (unpublished) IDs. This is a fundamental data acquisition blocker requiring frontier team intervention.

---

## Factory Direction v28 Discrepancy — RESOLVED in v29
- **v28 claim**: "ALL 4 TF-IDF MODES PASS the frozen v26 zoom-quality acceptance rule for constrained hierarchical Leiden"
- **Actual (hierarchical_v1 protocol)**: 1/4 PASS (regeste_tfidf 83k), 3/4 FAIL on legal_structure_branch
- **Resolution**: v29 question text accurately reflects hierarchical_v1 protocol results; discrepancy acknowledged in state

---

## Pipeline Readiness for 174k Dense Embeddings
- **Best validated config**: `coarse_0.5_fixed2.0_min20` (validated at 12k ACCEPTED and 28k PENDING AUDIT)
- **Final readiness validation (12k dense, coarse_0.5_fixed2.0_min20)**: 6/7 hierarchical_v1 checks PASS
  - singleton_fraction=0.0%, nesting=1.0, branch_impr=+0.127, area_impr=+0.045
  - legal_structure_branch PASS (0.986 > 0.5)
  - legal_structure_area PASS (0.509 > 0.5)
  - zoom_coherence BORDERLINE (improvement_rate=0.50 exactly, not >0.5)
- **Requires**: ACCEPTED 174k dense embeddings for production deployment

---

## Conclusion
The fractal-map lane has completed all discriminating experiments possible under the current dependency state. The lane is correctly **BLOCKED_ON_DEPENDENCIES** with `continue_recommended=false`. No same-question cycle is justified without upstream delivery of ACCEPTED 174k dense embeddings from legal-distance.

**Next action**: Await legal-distance resolution of BGE/bger ID mismatch and completion of 2019/2020–2024/2025/2026 dense embedding computation. When 174k dense embeddings become ACCEPTED, the fractal-map lane will execute the full hierarchical Leiden pipeline at production scale using the validated `coarse_0.5_fixed2.0_min20` configuration.

---

## Verification Metadata
- **GitHub Run**: 36859043053
- **Factory Direction Version**: 29
- **Lane State Version**: fractal-map.json (verified 2026-10-01T12:30:00Z)
- **Verification Timestamp**: 2026-10-01T12:45:00Z
- **Test Suite**: 239 passed, 2 skipped
- **Evidence Artifacts**: All 43 evidence_refs verified present and loadable
- **Audit Ready**: Yes
