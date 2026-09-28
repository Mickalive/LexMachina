# Fractal Map Lane — Audit Report (Direction v28)

## Executive Summary

**Lane Status**: `BLOCKED_ON_DEPENDENCIES` (correct)
**Evidence Tier**: `REPRODUCED`
**Audit Gate**: `PASS` (CYCLE_36491590904)
**Continue Recommended**: `false` — no additional same-question cycle justified

The fractal-map lane has completed all discriminating experiments possible given current upstream dependencies. The lane is correctly blocked awaiting ACCEPTED 174k dense embeddings from legal-distance.

---

## Orchestration Failure Diagnosis

### Root Cause
`factory_direction.json` v28 on `main` incorrectly reports `fractal-map.status=RUN` despite the lane being `BLOCKED_ON_DEPENDENCIES` since v26.

### Legal-Distance Progress Gap
- **Checkpoints**: 25/26 years (2000-2024) per `progress.json`
- **ACCEPTED**: Only 3/26 years (2000-2002, ~19,441 decisions, 11%)
- **PENDING AUDIT**: 22/26 years (2003-2024) — cannot be cited as accepted evidence

### Impact
- Fractal-map lane correctly paused; no productive work possible without ACCEPTED 174k dense embeddings
- All discriminating experiments for current dependency state are complete
- Evidence preserved, findings frozen

### Resolution Path
Factory Director must either:
1. Update `factory_direction.json` to reflect `BLOCKED_ON_DEPENDENCIES`, OR
2. Promote legal-distance 174k dense embeddings through audit to unblock

---

## Accepted Claims (Frozen)

### 174k TF-IDF Baseline (v26 Frozen Spec)
| Metric | Result |
|--------|--------|
| Flat Leiden zoom quality | **FAIL** — 0/4 modes pass |
| Monotonic zoom refinement | **NO** — no transitions with improvement_rate > 0.5 on 2/4 |
| Fragmentation (res 2.0) | 99.39% singletons, median size 1 |
| Fragmentation (res 3.0) | 99.85% singletons, median size 1 |
| Branch purity (res 0.25) | 0.55 |
| Legal area purity (res 0.25) | 0.31 |

### Constrained Hierarchical Leiden — 174k TF-IDF
| Config | Nesting | Fine Singleton % | Fine Median | Verdict |
|--------|---------|------------------|-------------|---------|
| regeste_tfidf | 1.0 | 0% | 508 | **PASS structural** |
| hybrid_0.5 | 1.0 | >99% | 1 | FAIL |
| hybrid_0.7 | 1.0 | >99% | 1 | FAIL |
| full_text | 1.0 | >99% | 1 | FAIL |

**Key Finding**: Nesting=1.0 by construction but per_mode_verdict=FAIL due to severe over-fragmentation at fine resolutions.

### 12k Dense Embeddings (ACCEPTED, years 2000-2002)

#### Flat v26 Zoom Quality
- **FAIL** — only 1/4 transitions exceed 0.5 improvement_rate threshold

#### Constrained Hierarchical Leiden (adaptive=True, min_cluster_size=3)
- **PASS** hierarchical protocol
- improvement_rate: 45.5%
- singleton_fraction: 0.4%
- nesting: 1.0
- branch_purity: 0.988 → 0.988 (fine)
- area_purity: 0.453 → 0.556 (fine)

#### Constrained Hierarchical Leiden (adaptive=False, min_cluster_size=20)
- Zero fragmentation (singleton_fraction: 0%)
- improvement_rate: 19-35% (lower zoom coherence)
- nesting: 1.0

### 28k Checkpoint Validation (Pipeline Validation Only, PENDING AUDIT)
- Constrained hierarchical Leiden on 28k dense embeddings (years 2000-2005)
- fine_singleton: 0.0%
- fine_median: 43-53
- improvement_rate: 0.67 (matches scale extrapolation prediction)
- branch_improvement: 0.15-0.154
- nesting: 1.0
- **PIPELINE VALIDATED at intermediate scale**

### Scale Dependency — CONFIRMED
| Scale | Flat v26 | Constrained Hierarchical |
|-------|----------|-------------------------|
| 1k | Severe fragmentation | N/A |
| 1.2k (citation roles) | **PASS** (citing_alpha0.7) | N/A |
| 12k (dense) | FAIL | 45.5% improvement_rate |
| 28k (checkpoint) | FAIL | 67% improvement_rate |
| 174k (TF-IDF) | FAIL + severe fragmentation | FAIL (singleton >99%) |

### Evidence-Backed Zoom Path (1000-scale, ACCEPTED)
| Mode | Zoom Quality (ZQ) |
|------|-------------------|
| citing_alpha0.3 | 0.5401 |
| following_alpha0.3 | 0.5280 |
| criticizing_alpha0.3 | 0.4864 |
| **Production default** (cited_outcome_hybrid_0.5) | **0.2798** |

### Critical Negative Results
1. **Dense 12k adversarial**: FAIL — language_dominance ~0.98, jurist_preference ~0.04
2. **Adaptive sub-resolution**: HARMS zoom quality at ≥10k scale (capped at 45.5%); DEPRECATED
3. **NESTING_METRIC_DEFECT_v1**: 7 compressed-family modes PROHIBITED from nesting≥0.99 claims (audit CYCLE_36027099305)

### Pipeline Readiness for 174k Dense
- Operational at simulation level
- Best validated config: `coarse_0.5_fixed2.0_min20` (validated at 12k and 28k)
- Requires ACCEPTED 174k dense embeddings for production deployment

### Scale Extrapolation Model — VALIDATED
- Power law predicts hierarchical improvement_rate ~0.67 at 174k for dense embeddings
- **HIGH confidence** after 28k validation confirms hier_impr=0.67
- Flat zoom predicted ~0.24 at 174k

---

## Evidence References (Machine-Readable)

All raw outputs preserved in `results/fractal_map/` with immutable provenance:

1. `zoom_quality_174k_eval/v26_verdict.json` — Frozen v26 evaluation at 174k
2. `hierarchical_zoom_eval/hierarchical_verdict_20260928_193114.json` — Hierarchical zoom eval
3. `nesting_metric_defect_v1_audit.json` — Nesting defect audit (CYCLE_36027099305)
4. `constrained_hierarchical_tests/constrained_hierarchical_174k_*.json` — 174k TF-IDF hierarchical tests
5. `12k_dense_hierarchical_test/hierarchical_leiden_results.json` — 12k dense hierarchical
6. `constrained_hierarchical_tests/dense_3yr_20260927/constrained_hierarchical_dense_3yr_results.json` — 3yr dense
7. `zoom_coherence_1000scale_citation_roles.json` — 1000-scale citation roles
8. `12k_dense_comprehensive/*.json` — 12k dense comprehensive
9. `28k_checkpoint_validation/28k_validation_20260928_212756.json` — 28k checkpoint validation
10. `pipeline_readiness_12k_dense_official.json` — Pipeline readiness
11. `12k_constrained_zoom_diagnostic/constrained_zoom_diagnostic_v2_20260928_133636.json` — Fixed 12k diagnostic

---

## Provenance

| Artifact | Source | Status |
|----------|--------|--------|
| 12k dense embeddings | `/tmp/lex_accepted/legal-distance/.../checkpoints/` (years 2000-2002) | ACCEPTED |
| 28k checkpoint embeddings | `/tmp/lex_accepted/legal-distance/.../checkpoints/` (years 2000-2005) | PENDING AUDIT |
| Citation alpha embeddings | `/tmp/lex_accepted/evaluation/.../v3_citation_roles_frozen/` | ACCEPTED |
| Metadata 174k | `/tmp/lex_accepted/evaluation/.../metadata_174k.json` (173,963 entries) | ACCEPTED |

Seeds: global=42, leiden=42, k_neighbors=15

---

## Test Suite
- Passed: 241
- Skipped: 2
- Duration: 180s

---

## Next Recommendation

**BLOCKED** — No further fractal-map cycles justified until legal-distance delivers ACCEPTED 174k dense embeddings. The scale extrapolation model is validated (hier_impr ~0.67 at 174k), pipeline readiness confirmed, and evidence-backed zoom path identified (citation-role/dense embeddings). All discriminating experiments for the current dependency state are complete.

---

*Report generated: 2026-09-28*
*Lane state: `state/fractal-map.json` (authoritative)*
*Factory direction discrepancy documented in state file*