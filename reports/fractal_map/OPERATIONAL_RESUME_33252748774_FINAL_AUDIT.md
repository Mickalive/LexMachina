# Operational Resume — Run 33252748774 — Fractal Map Lane

**Date:** 2026-08-29T12:40:00Z  
**Lane:** fractal-map  
**Direction Version:** 6  
**Previous Run:** 33250903956  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Audit Status:** PASS  

---

## Summary

Successfully completed operational resume from persisted producer snapshot of run 33250903956. The orchestration/validation failure was diagnosed and resolved — caused by **ephemeral storage volatility** in `/tmp/lex_accepted/` between GitHub Actions runs.

**Resolution Applied:**
1. Re-established `/tmp/lex_accepted/fractal_map/` mirroring (278 artifacts verified)
2. Re-ran all 48 verification tests — **ALL PASS**
3. Validated `ProductMapLoader`/`MapModeLoader` API end-to-end across all 8 modes
4. Independent recomputation of zoom coherence confirms **63.0% improvement rate** (68/108 fine clusters improve), exceeding concat baseline 59.2% by +3.8%
5. Updated state file for current run (33252748774) with `audit_status: PASS`

All factory direction v6 requirements remain **satisfied and frozen**.

---

## Factory Direction v6 Requirements — STATUS: COMPLETE

| Requirement | Status | Evidence |
|-------------|--------|----------|
| REPRODUCE validated hierarchical Leiden map on center_projected embeddings | ✅ COMPLETE | `center_projected_hierarchical_results.json` |
| Nesting = 1.0 | ✅ PASS | Hierarchical construction guarantees perfect nesting |
| Purity ≥ concat baseline (0.9491) | ✅ PASS | 0.9571 (+0.0080, min_cluster_size=3) |
| 7-resolution ladder exposed | ✅ COMPLETE | 0.25 → 0.5 → 0.75 → 1.0 → 1.5 → 2.0 → 3.0 |
| 108 hierarchical clusters (coarse_0.5_fine_3.0) | ✅ COMPLETE | Branch purity 0.9571 |
| Zoom coherence improvement rate validated | ✅ PASS | 63.0% (per-resolution-step), baseline 59.2% |
| Cluster metadata at each zoom level | ✅ COMPLETE | `cluster_metadata.json` with branch/area/chamber/language |
| Legal coherence at each zoom level documented | ✅ COMPLETE | Branch purity ladder: 0.840→0.912→0.972→0.965→0.964→0.955→0.929 |
| Default map structure integrated with legal-distance selectable modes | ✅ COMPLETE | 8 modes in registry (1 default + 5 legal-distance ACCEPTED + 1 legacy + 1 placeholder) |
| Map mode switching architecture | ✅ COMPLETE | Unified `MapModeLoader`/`ProductMapLoader` API |

---

## Key Metrics (Revalidated)

### Center Projected Hierarchical Leiden (DEFAULT)
- **Hierarchical Purity:** 0.9571 (global, min_cluster_size=3)
- **Flat Mean Purity:** 0.9341
- **Concat Baseline Purity:** 0.9491
- **Improvement vs Concat:** +0.0080 (0.84%)
- **Nesting Score:** 1.0 (perfect, guaranteed by construction)
- **Hierarchical Clusters:** 108 (7 coarse → 108 fine)
- **Resolution Ladder:** 7 levels (5→7→9→11→14→16→19 flat clusters)
- **Zoom Coherence Improvement Rate:** 63.0% (68 improvements, 11 deteriorations, 29 no change)
- **Concat Baseline Zoom Coherence:** 59.2%
- **Improvement over Baseline:** +3.8%
- **Adversarial Language Dominance:** 0.7593 < 0.85 ✅ (source: evaluation_v2)
- **Jurist Pairwise Preference:** 0.5215 > 0.5 ✅ (source: evaluation_v2)
- **Jurivoc Hierarchy Alignment:** 4/5 PASS ✅ (source: evaluation_v2)

### Map Mode Registry (8 Modes)
| Mode ID | Type | Status | Evidence Tier | Benchmarks |
|---------|------|--------|---------------|------------|
| `center_projected_hierarchical` | hierarchical_leiden | available | REPRODUCED | DEFAULT |
| `debiased_citation_blended` | legal_distance | available | ACCEPTED | 14/14 PASS |
| `legal_cited_decisions_only` | legal_distance | available | ACCEPTED | 14/14 PASS |
| `hybrid_alpha_03` | legal_distance | available | ACCEPTED | 13/14 PASS ⚠️ fails adversarial_falsification |
| `hybrid_alpha_05` | legal_distance | available | ACCEPTED | 13/14 PASS ⚠️ fails adversarial_falsification |
| `legal_issues_outcomes` | legal_distance | available | ACCEPTED | 10/14 PASS ⚠️ fails 4 benchmarks |
| `center_projected` | legal_distance | placeholder | ACCEPTED | Raw embedding only |
| `hierarchical_leiden_concat` | hierarchical_leiden | legacy | REPRODUCED | Preserved for comparison |

---

## Orchestration/Validation Failure Diagnosis

**Root Cause:** `/tmp/lex_accepted/` is ephemeral storage in GitHub Actions. Each new run gets a fresh `/tmp/` directory, causing the `/tmp/lex_accepted/fractal_map/` mirror to be lost between runs.

**Impact:** Without mirroring, the accepted state cannot be verified by downstream lanes or audits.

**Mitigation (Applied & Verified):**
- Re-establish mirroring at start of every operational resume: `cp -r results/fractal_map/* /tmp/lex_accepted/fractal_map/`
- Run full verification suite (48 tests) after mirroring
- Validate `MapModeLoader`/`MapModeRegistry` API end-to-end
- Update state file with current `github_run` and `operational_resume_id`

**Persistence Verified:** This mitigation has been successfully applied and verified across **15+ consecutive operational resume runs** (33234274417 → 33252748774).

---

## Verification Results

### Test Suite: `tests/fractal_map/test_verify.py`
```
48 passed in 0.13s
```
- **TestArtifactIntegrity**: 12/12 PASS — All label arrays exist with correct shapes (1000 decisions)
- **TestHierarchicalLeiden**: 5/5 PASS — Best config validated, purity > 0.95, nesting = 1.0, 108 fine clusters sum to 1000
- **TestMetricConsistency**: 7/7 PASS — State file metrics match recomputed values, evidence_tier=REPRODUCED, PRODUCTIZE recommendation
- **TestLegacyConcatPreserved**: 8/8 PASS — All legacy concat artifacts preserved
- **TestLegalDistanceModes**: 3/3 PASS — 5 legal-distance modes at ACCEPTED tier, legacy preserved

### API Validation: `MapModeLoader` / `MapModeRegistry`
```
8/8 modes loaded successfully
- center_projected_hierarchical: 9 label arrays (7 resolutions + hierarchical_best + coarse_0.5)
- hierarchical_leiden_concat: 9 label arrays (legacy)
- debiased_citation_blended: 7 label arrays (7 resolutions)
- legal_cited_decisions_only: 7 label arrays
- hybrid_alpha_03: 7 label arrays
- hybrid_alpha_05: 7 label arrays
- legal_issues_outcomes: 7 label arrays
- center_projected: placeholder (minimal artifacts)
```

### Independent Recomputation: Zoom Coherence
```
Center Projected Hierarchical Leiden (coarse_0.5_fine_3.0):
- Overall coarse purity: 0.9123
- Overall fine purity: 0.9638
- Overall improvement: 0.0515 (5.6%)
- Total improvements: 68
- Total deteriorations: 11
- Total no change: 29
- Improvement rate: 63.0%
- Concat baseline: 59.2%
- Difference: +3.8%
VERDICT: PASS
```

---

## Artifacts Verified

| Category | Count |
|----------|-------|
| Hierarchical map artifacts (center_projected) | 33 |
| Legacy concat artifacts | 10 |
| Legal-distance mode artifacts | 5 directories × 7+ files |
| Product integration artifacts | 11 |
| Evaluation artifacts | 2 |
| Audit gate records | 60+ |
| Reports | 13 |
| **Total** | **278** |

---

## Next Recommendation

**PRODUCTIZE** — All factory direction v6 objectives completed. The fractal-map lane has:

1. **Reproduced** the validated hierarchical Leiden map on center_projected embeddings as the new default
2. **Exposed** the full 7-resolution ladder with cluster metadata and legal coherence metrics
3. **Integrated** 5 legal-distance ACCEPTED modes + legacy concat mode + placeholder
4. **Implemented** unified loader API for product consumption
5. **Verified** all artifacts persist and load correctly across operational resumes

The product lane should now consume `center_projected_hierarchical` artifacts from `results/fractal_map/hierarchical_map_center_projected/` as the default map mode, with the map mode registry enabling user-selectable legal-distance views.

---

## State File Consistency

- ✅ Repo state (`state/fractal-map.json`) matches `/tmp/lex_accepted/fractal_map/fractal-map.json`
- ✅ `evidence_tier: REPRODUCED`
- ✅ `cycle_status: COMPLETED`
- ✅ `continue_recommended: false`
- ✅ `next_recommendation: PRODUCTIZE`
- ✅ `audit_status: PASS`
- ✅ `tests_passed: 48`
- ✅ `artifacts_verified: 278`
- ✅ `modes_loaded: 8`

---

*Signed off by Fractal Map Lane — Operational Resume 33252748774*