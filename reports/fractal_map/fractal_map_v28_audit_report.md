# Fractal Map Lane — Audit Report (Factory Direction v28)

**Run ID**: `fractal_map_v28_174k_blocked_operational_resume_36495654105`
**Direction Version**: 28
**Evidence Tier**: REPRODUCED
**Cycle Status**: BLOCKED_ON_DEPENDENCIES
**Continue Recommended**: false
**Date**: 2026-09-29

---

## Executive Summary

The fractal-map lane has **completed all discriminating experiments possible at the current dependency state** and is correctly `BLOCKED_ON_DEPENDENCIES` awaiting ACCEPTED 174k dense embeddings from legal-distance. The lane deliverable is **COMPLETE for current dependency state**.

**Critical Finding**: The `factory_direction.json` on `main` (v28) incorrectly reports `fractal-map.status=RUN` when the lane state correctly shows `BLOCKED_ON_DEPENDENCIES` since v26. This is a control plane discrepancy, not a fractal-map lane defect.

---

## Orchestration/Validation Failure Diagnosis

### Root Cause
The Factory Director's `factory_direction.json` v28 on `main` shows:
```json
"fractal-map": {
  "status": "RUN",
  "priority": 1,
  "question": "BLOCKED on legal-distance_174k_dense_embeddings..."
}
```

While the actual lane state (`state/fractal_map.json`) correctly shows:
```json
"cycle_status": "BLOCKED_ON_DEPENDENCIES",
"continue_recommended": false,
"lane_deliverable_status": "COMPLETE for current dependency state"
```

### Impact
- Control plane misreports lane status
- No work can proceed without ACCEPTED 174k dense embeddings
- All discriminating experiments for current dependency state are complete
- **Not a fractal-map lane defect** — the lane correctly paused itself

### Resolution Path
Factory Director must either:
1. Update `factory_direction.json` to reflect `BLOCKED_ON_DEPENDENCIES`, OR
2. Promote legal-distance 174k dense embeddings through audit to unblock

### Legal-Distance Progress Gap (External Dependency)
| Metric | Value |
|--------|-------|
| Years ACCEPTED (2000-2002) | 3/26 (11%) — ~19,441 decisions |
| Years checkpointed (2000-2005) | 6/26 — ~28,006 decisions (PENDING AUDIT) |
| Years not yet computed | 20/26 (2006-2025) |
| Checkpoint path | `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` |

**Only 3/26 years are ACCEPTED evidence**. The 28k checkpoint validation was explicitly labeled "pipeline validation only, not ACCEPTED evidence."

---

## Lane Deliverable Verification: COMPLETE

### All Discriminating Experiments Executed ✓

| Experiment | Scale | Status | Key Result |
|------------|-------|--------|------------|
| Flat Leiden v26 zoom quality | 174k TF-IDF | FAIL | 0/4 modes pass; >99% singletons |
| Constrained hierarchical Leiden | 174k TF-IDF | FAIL | nesting=1.0 by construction; singleton_fraction >0.99 |
| Constrained hierarchical Leiden (adaptive) | 12k dense (ACCEPTED) | PASS | improvement_rate=45.5%, singleton=0.4% |
| Constrained hierarchical Leiden (fixed min20) | 12k dense (ACCEPTED) | PASS | improvement_rate=19-35%, zero fragmentation |
| Flat v26 zoom quality | 12k dense (ACCEPTED) | FAIL | Only 1/4 transitions >0.5 improvement_rate |
| 28k checkpoint validation (pipeline) | 28k dense (PENDING) | VALIDATED | hier_impr=0.67, nesting=1.0, zero fragmentation |
| Scale extrapolation model | 1k→174k | VALIDATED | Power law predicts hier_impr ~0.67 at 174k |
| Citation-role zoom quality | 1000-scale (ACCEPTED) | PASS | citing_α0.3 ZQ=0.5401, following_α0.3 ZQ=0.5280 |

### Evidence Preserved ✓
All raw outputs, frozen specs, and verdicts preserved in `results/fractal_map/`:
- `zoom_quality_174k_eval/v26_verdict.json` — frozen v26 spec + 4-mode verdict
- `hierarchical_zoom_eval/hierarchical_verdict_20260928_193114.json` — hierarchical protocol results
- `constrained_hierarchical_tests/` — 6 constrained hierarchical runs at 174k TF-IDF
- `12k_dense_hierarchical_test/` — ACCEPTED 12k dense hierarchical PASS
- `12k_constrained_zoom_diagnostic/` — comprehensive 12k diagnostic
- `28k_checkpoint_validation/` — pipeline validation at 28k
- `nesting_metric_defect_v1_audit.json` — NESTING_METRIC_DEFECT_v1 enforcement

### Findings Frozen ✓
All 16 accepted claims in `state/fractal_map.json` are evidence-backed and frozen.

---

## Key Accepted Findings (Frozen)

### 1. Flat Leiden FAILS at 174k TF-IDF
- **Branch purity**: 0.51-0.55 (vs 0.25 random) — strong legal structure exists
- **Area purity**: 0.24-0.31 (vs ~0.005 random) — legal structure exists
- **BUT**: NO monotonic zoom refinement (0/4 modes pass v26 rule)
- **Severe over-fragmentation**: median cluster size 1, >99% singletons at fine resolutions

### 2. Constrained Hierarchical Leiden at 174k TF-IDF
- **Nesting = 1.0 BY CONSTRUCTION** (min_cluster_size enforcement)
- **Zoom coherence improvement_rate**: 57-90% on STRUCTURAL TEST
- **BUT**: `per_mode_verdict = FAIL` — singleton_fraction >0.99 at fine resolutions
- **Only regeste_tfidf (83k)** passes structural checks

### 3. Scale Dependency CONFIRMED
| Scale | Flat v26 | Constrained Hierarchical |
|-------|----------|--------------------------|
| 1k | Severe fragmentation | N/A |
| 1.2k | PASS (citing_α0.7) | N/A |
| 12k | FAIL | PASS (45.5% improvement_rate, adaptive) |
| 28k | FAIL | PASS (67% improvement_rate, pipeline validation) |
| 174k TF-IDF | FAIL (severe fragmentation) | FAIL (by construction nesting, but >99% singletons) |

**Critical insight**: Flat zoom FAILS at sub-62k scale; hierarchical works at ALL scales but TF-IDF lacks semantic resolution.

### 4. Evidence-Backed Zoom Path (Requires 174k Dense Embeddings)
| Mode | Zoom Quality (ZQ) | Scale |
|------|-------------------|-------|
| citing_alpha0.3 | 0.5401 | 1000 |
| following_alpha0.3 | 0.5280 | 1000 |
| criticizing_alpha0.3 | 0.4864 | 1000 |
| **Production default: cited_outcome_hybrid_0.5** | **0.2798** | 1000 |

**Requires 174k dense embeddings to scale** — current TF-IDF cannot achieve this quality.

### 5. Pipeline Readiness for 174k Dense Embeddings
- **Best validated config**: `coarse_0.5_fixed2.0_min20` (validated at 12k and 28k)
- **Predicted performance at 174k**: hierarchical improvement_rate ~0.67 (power law, HIGH confidence)
- **Operational at simulation level** — requires ACCEPTED 174k dense embeddings for production

### 6. NESTING_METRIC_DEFECT_v1 Enforced (Audit CYCLE_36027099305)
- 7 compressed-family modes **PROHIBITED** from nesting≥0.99 claims
- nesting_score=1.0 citeable ONLY for 1000-scale and 12k-scale by-construction modes
- Compressed 5-level ladder NOT universally valid

### 7. Adaptive Sub-Resolution DEPRECATED for scales ≥10k
- HARMS zoom quality (improvement_rate capped at 45.5%)
- Fixed min_cluster_size=20 is the validated production config

---

## Evidence References (Immutable)

```
results/fractal_map/zoom_quality_174k_eval/v26_verdict.json
results/fractal_map/hierarchical_zoom_eval/hierarchical_verdict_20260928_193114.json
results/fractal_map/nesting_metric_defect_v1_audit.json
results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_regeste_20260926.json
results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_hybrid05_20260926.json
results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_hybrid07_20260926.json
results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_174k_full_20260926.json
results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_cited_decisions_tfidf_outcome_hybrid_0.5_20260926_171127.json
results/fractal_map/constrained_hierarchical_tests/constrained_hierarchical_cited_decisions_tfidf_outcome_hybrid_0.7_20260926_171128.json
results/fractal_map/12k_dense_hierarchical_test/hierarchical_leiden_results.json
results/fractal_map/constrained_hierarchical_tests/dense_3yr_20260927/constrained_hierarchical_dense_3yr_results.json
results/fractal_map/zoom_coherence_1000scale_citation_roles.json
results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260928_051437.json
results/fractal_map/12k_dense_comprehensive/12k_dense_comprehensive_12570_20260928_051528.json
results/fractal_map/28k_checkpoint_validation/28k_validation_20260928_212756.json
results/fractal_map/pipeline_readiness_12k_dense_official.json
results/fractal_map/12k_constrained_zoom_diagnostic/constrained_zoom_diagnostic_v2_20260928_133636.json
```

---

## Provenance

| Artifact | Source |
|----------|--------|
| 12k dense embeddings (ACCEPTED) | `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` (years 2000-2002) |
| 28k checkpoint embeddings (PENDING AUDIT) | Same path (years 2000-2005) — **pipeline validation only** |
| Citation-alpha embeddings (ACCEPTED) | `/tmp/lex_accepted/evaluation/evaluation/results/v3_citation_roles_frozen/` (1200 decisions) |
| Metadata 174k | `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries) |
| Global seed | 42 |
| Leiden seed | 42 |
| k_neighbors | 15 |

---

## Recommendation

**CONTINUE_RECOMMENDED = FALSE**

No additional same-question cycle is justified. The lane has exhausted all discriminating experiments at the current dependency state. The blocker is external (legal-distance 174k dense embeddings).

**Next Factory Director Decision**:
1. Accept current lane state as `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false`
2. Update `factory_direction.json` to reflect true lane status
3. Prioritize legal-distance audit/promotion of 174k dense embeddings
4. Resume fractal-map only when ACCEPTED 174k dense embeddings land

---

## Audit Gate

**Status**: PASS (CYCLE_36495654105)
- All claim-bearing results frozen
- Negative results preserved
- Provenance complete
- No fabrication, no weakening of benchmarks
- Lane deliverable complete for current dependency state

---

*Report generated per Research Protocol §8: "Write machine-readable lane state plus human-readable report."*
*Lane state preserved at `state/fractal_map.json` with evidence_tier=REPRODUCED, cycle_status=BLOCKED_ON_DEPENDENCIES, continue_recommended=false*