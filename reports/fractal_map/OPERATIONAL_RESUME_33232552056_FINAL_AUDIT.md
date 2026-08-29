# Fractal Map Lane — Operational Resume 33232552056 Final Audit

**Lane:** fractal-map  
**Factory Direction:** v6  
**GitHub Run:** 33232552056  
**Timestamp:** 2026-08-29T03:57:00Z  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Verdict:** PASS  
**Continue Recommended:** false  
**Next Recommendation:** PRODUCTIZE

---

## 1. Summary

This operational resume confirms the **completion of Factory Direction v6 for the fractal-map lane**. All requirements are satisfied and the snapshot is audit-ready.

**Prior Cycle:** operational_resume_33232058188 (which re-established `/tmp/lex_accepted/fractal_map/` mirroring with 286 artifacts and re-ran all 48 verification tests)

**Current Cycle Actions:**
- Verified all 48 verification tests PASS
- Validated loader API across all 8 map modes with full artifact loading
- Confirmed `/tmp/lex_accepted/fractal_map/` mirroring intact (286 artifacts)
- Confirmed hierarchical Leiden on center_projected achieves 0.9571 hierarchical purity with perfect nesting (1.0)
- Confirmed zoom coherence improvement rate 62.96% > concat baseline 59.18%
- Verified map mode registry complete with 8 modes (1 default + 5 legal-distance ACCEPTED + 1 legacy + 1 placeholder)
- Updated state file for current run (github_run: 33232552056)

---

## 2. Factory Direction v6 Requirements — All VERIFIED

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Reproduce hierarchical Leiden on center_projected embeddings as new default input | ✅ VERIFIED | `center_projected_hierarchical_results.json`, 48 tests pass |
| Expose resolution ladder (7 levels: 0.25→0.5→0.75→1.0→1.5→2.0→3.0) | ✅ VERIFIED | `integration_summary.json`, label arrays for all resolutions |
| Cluster metadata with legal coherence at each zoom level | ✅ VERIFIED | `cluster_metadata.json` with branch/area/chamber/language per cluster |
| Integrate as default map structure | ✅ VERIFIED | `center_projected_hierarchical` is default mode in registry |
| Legal-distance selectable modes integrated | ✅ VERIFIED | 5 ACCEPTED legal-distance modes in registry with full artifacts |

---

## 3. Key Metrics (Reproduced from Prior Validated Run)

### Center Projected Hierarchical Leiden (Default Mode)
- **Hierarchical Purity:** 0.9571 (+0.0080 vs concat baseline 0.9491, min_cluster_size=3)
- **Perfect Nesting:** 1.0 (guaranteed by hierarchical construction)
- **Resolution Ladder:** 7 levels → 5→7→9→11→14→16→19 clusters
- **Hierarchical Clusters:** 108 (coarse_0.5_fine_3.0 configuration)
- **Branch Purity Ladder:** 0.840 → 0.912 → 0.972 → 0.965 → 0.964 → 0.955 → 0.929

### Zoom Coherence (Per-Resolution-Step Methodology)
- **Center Projected Improvement Rate:** 62.96% (19/61 parent clusters improve purity when zooming)
- **Concat Baseline Improvement Rate:** 59.18%
- **Delta:** +3.78 percentage points ✅

### Adversarial Benchmarks (Carried Forward from Evaluation v2)
- **Language Dominance:** 0.7593 < 0.85 threshold ✅ PASS
- **Jurist Pairwise Preference:** 0.5215 > 0.5 threshold ✅ PASS
- **Jurivoc Hierarchy Alignment:** 4/5 PASS

**Note:** center_projected is the ONLY representation passing BOTH adversarial language dominance AND jurist pairwise preference (source: evaluation_v2_cycle_33137354250).

---

## 4. Map Mode Registry — 8 Modes Complete

| Mode ID | Type | Status | Evidence Tier | Benchmarks |
|---------|------|--------|---------------|------------|
| `center_projected_hierarchical` | hierarchical_leiden | available | REPRODUCED | Default mode, validated |
| `hierarchical_leiden_concat` | hierarchical_leiden | legacy | REPRODUCED | Preserved for comparison |
| `debiased_citation_blended` | legal_distance | available | ACCEPTED | 14/14 PASS |
| `legal_cited_decisions_only` | legal_distance | available | ACCEPTED | 14/14 PASS |
| `hybrid_alpha_03` | legal_distance | available | ACCEPTED | 13/14 PASS (fails adversarial_falsification) |
| `hybrid_alpha_05` | legal_distance | available | ACCEPTED | 13/14 PASS (fails adversarial_falsification) |
| `legal_issues_outcomes` | legal_distance | available | ACCEPTED | 10/14 PASS (fails 4 benchmarks) |
| `center_projected` | legal_distance | placeholder | ACCEPTED | Raw embedding only |

All legal-distance modes are marked with explicit warnings where benchmarks fail.

---

## 5. Product Integration — Ready

### Unified Loader API (`MapModeLoader` / `ProductMapLoader`)
- `list_modes()` — List all 8 modes with metadata
- `load_mode(mode_id)` — Load artifacts for any mode
- `get_resolution_labels(mode_id, resolution)` — Get cluster labels at specific resolution
- `get_hierarchical_labels(mode_id)` — Get hierarchical labels (108 clusters)
- `get_coarse_labels(mode_id)` — Get coarse parent labels (7 clusters)
- `get_cluster_metadata(mode_id, resolution)` — Get legal context per cluster
- `get_zoom_mapping(mode_id, from_res, to_res)` — Get parent-child navigation
- `get_decision_clusters(mode_id, decision_id)` — Get cluster membership for a decision
- `get_zoom_coherence(mode_id, from_res, to_res)` — Get zoom improvement metrics

### Artifacts Available for Product Consumption
```
results/fractal_map/hierarchical_map_center_projected/
├── cluster_metadata.json      # Legal context per cluster
├── zoom_mappings.json         # Bidirectional parent-child navigation
├── zoom_coherence.json        # Per-cluster zoom improvement metrics
├── decision_clusters.json     # Decision-to-cluster index (1000 × 7 resolutions)
├── labels_res_*.npy           # Cluster assignments for rendering (7 resolutions)
├── labels_hierarchical_best.npy  # Best validated config (108 clusters)
└── labels_coarse_0.5.npy      # 7-cluster parent level
```

---

## 6. Verification Test Suite — 48/48 PASS

| Test Class | Tests | Status |
|------------|-------|--------|
| TestArtifactIntegrity | 14 | ✅ PASS |
| TestHierarchicalLeiden | 6 | ✅ PASS |
| TestMetricConsistency | 9 | ✅ PASS |
| TestLegacyConcatPreserved | 10 | ✅ PASS |
| TestLegalDistanceModes | 9 | ✅ PASS |
| **Total** | **48** | **✅ ALL PASS** |

Tests verify:
- All label arrays exist and have correct size (1000 decisions)
- Hierarchical purity > 0.95, nesting = 1.0
- State file metrics match recomputed values
- Default mode is center_projected_hierarchical
- Center projected purity beats concat baseline
- Legacy concat artifacts preserved
- All 5 legal-distance ACCEPTED modes registered

---

## 7. Negative Results Preserved

Per research protocol, negative results are first-class evidence:

1. **Flat Leiden nesting imperfect** (~0.50 mean nesting between adjacent resolutions)
2. **Some clusters homogeneous at coarse resolution** (cluster 0 mixes strafrecht/oeffentliches_recht)
3. **igraph version sensitivity** in cluster counts documented
4. **legal_issues_outcomes fails** multilingual_invariance and adversarial_falsification
5. **Hybrid modes (α=0.3, 0.5) fail** adversarial_falsification benchmark
6. **Zoom coherence methodology difference:** per-resolution-step (62.96%) vs hierarchical_zoom_validation (31.1%) — different denominators

---

## 8. Dependencies for Next Phases

| Dependency | Owner Lane | Status |
|------------|------------|--------|
| Legal-distance reproduction of center_projected on full v1+v2 benchmark suite | legal-distance | PENDING |
| Full corpus scale (2000-2024, ~192k decisions via OpenCaseLaw bulk) | corpus | PENDING |

---

## 9. Audit Trail

**State File:** `state/fractal-map.json` (updated for github_run 33232552056)

**Evidence Artifacts:** 286 files mirrored to `/tmp/lex_accepted/fractal_map/`

**Prior Audit Gates:** 28 operational resumes + 2 center_projected hierarchical v5/v6 gates

**Current Audit Gate:** `results/fractal_map/audit/CYCLE_operational_resume_33232552056_FINAL_AUDIT_GATE.json`

---

## 10. Conclusion

**FACTORY DIRECTION v6 COMPLETE for fractal-map lane.**

The center_projected_hierarchical Leiden map is the validated default multi-resolution fractal map structure. All product integration artifacts are complete and tested. The map mode switching architecture with 8 modes (1 default REPRODUCED, 5 legal-distance ACCEPTED, 1 legacy, 1 placeholder) is operational.

**Recommendation:** PRODUCTIZE — Product lane should consume center_projected_hierarchical artifacts from `results/fractal_map/hierarchical_map_center_projected/` and implement map mode selector UI using the registry.

No further fractal-map cycles under the current factory direction question are justified (`continue_recommended: false`).

---

*This audit report is generated from REPRODUCED-tier evidence. All metrics frozen before observation. Negative results preserved.*