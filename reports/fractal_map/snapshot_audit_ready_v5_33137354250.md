# Fractal Map Lane — Factory Direction v5 Complete & Audit-Ready Snapshot

**Run ID:** center_projected_hierarchical_v5_33137354250  
**GitHub Run:** 33137354250  
**Lane:** fractal-map  
**Factory Direction Version:** 5  
**Timestamp:** 2026-08-28T03:00:00Z  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Recommendation:** PRODUCTIZE  

---

## Executive Summary

The fractal-map lane has **completed the factory direction v5 deliverable**: reproducing the validated hierarchical Leiden map on **center_projected embeddings** as the new default map mode, replacing the concat-based hierarchical_leiden. All 48 verification tests pass. State files are synchronized to direction_version=5, github_run=33137354250.

### Key Validated Metrics (Frozen)

| Metric | Value | Source |
|--------|-------|--------|
| **Hierarchical purity (global)** | 0.963847 | `center_projected_hierarchical_results.json` |
| **Hierarchical purity (local)** | 0.9638 | Evaluation lane metric |
| **Nesting consistency** | 1.0 | Hierarchical Leiden construction |
| **Resolution ladder** | 7 levels (0.25→3.0) | 5→7→9→11→14→16→19 clusters |
| **Hierarchical clusters** | 108 | coarse_0.5_fine_3.0 config |
| **Zoom coherence improvement rate** | 59.2% | Validated in evaluation |
| **Flat mean purity** | 0.9341 | 7 resolutions |
| **Purity improvement vs concat baseline** | +1.55% | 0.9638 vs 0.9491 |
| **Adversarial language dominance** | 0.7593 | < 0.85 threshold ✅ PASS |
| **Jurist pairwise preference** | 0.5215 | > 0.5 threshold ✅ PASS |
| **Jurivoc hierarchy alignment** | 4/5 | PASS |

---

## Deliverable Checklist (Factory Direction v5)

| v5 Requirement | Status | Evidence |
|----------------|--------|----------|
| REPRODUCE hierarchical Leiden on center_projected | ✅ | `hierarchical_map_center_projected/` |
| Nesting = 1.0 | ✅ | Guaranteed by construction; verified |
| Purity > concat baseline (0.949) | ✅ | 0.9638 (+1.55%) |
| Zoom coherence ~59.2% | ✅ | Validated |
| Resolution ladder exposed | ✅ | 7 resolutions in registry & artifacts |
| Cluster metadata with legal coherence | ✅ | branch/area/chamber/language per cluster |
| Legal coherence at each zoom level | ✅ | `zoom_coherence.json` per mode |
| center_projected as DEFAULT map structure | ✅ | Registry `default_mode = center_projected_hierarchical` |
| Legal-distance selectable modes integrated | ✅ | 5 modes at ACCEPTED tier |
| Map mode switching architecture | ✅ | Unified registry + loader API |
| Legacy concat mode preserved | ✅ | As `hierarchical_leiden_concat` (legacy) |

---

## Map Mode Registry (8 Selectable Modes)

| Mode ID | Type | Status | Benchmarks | Key Strength |
|---------|------|--------|------------|--------------|
| `center_projected_hierarchical` | hierarchical_leiden | ✅ **DEFAULT** | REPRODUCED tier | Pure center_projected, beats concat, passes adversarial + jurist tests |
| `debiased_citation_blended` | legal_distance | ✅ Available | 14/14 PASS | Balanced, multilingual invariance (gap 0.031) |
| `legal_cited_decisions_only` | legal_distance | ✅ Available | 14/14 PASS | Best citation heritage (AUC 0.97) |
| `hybrid_alpha_03` | legal_distance | ✅ Available | 13/14 PASS | Best branch classification (0.967) |
| `hybrid_alpha_05` | legal_distance | ✅ Available | 13/14 PASS | Strongest branch classification (0.972) |
| `legal_issues_outcomes` | legal_distance | ✅ Available | 10/14 PASS | Doctrinal similarity independent of citations |
| `center_projected` | legal_distance | ⏳ Placeholder | ACCEPTED tier | Raw embedding; map navigation uses hierarchical mode |
| `hierarchical_leiden_concat` | hierarchical_leiden | 📦 Legacy | REPRODUCED tier | Preserved for comparison (98 clusters) |

---

## Product Integration Package

**Location:** `results/fractal_map/product_integration/`

### Core Artifacts (Default Mode: center_projected_hierarchical)
- `cluster_metadata.json` — Legal context per cluster (branch, area, chamber, language, purity) at 7 resolutions + hierarchical
- `zoom_mappings.json` — Bidirectional parent-child navigation (6 resolution pairs)
- `zoom_coherence.json` — Per-cluster zoom improvement metrics
- `decision_clusters.json` — Decision-to-cluster index (1000 × 9 resolutions)
- `map_mode_registry.json` — Unified registry for all 8 modes
- `integration_summary.json` — Aggregate metadata
- `PRODUCT_INTEGRATION_SPEC.md` — Product integration specification
- `map_mode_loader.py` / `map_mode_registry.py` / `product_map_loader.py` — Loader API

### Label Arrays (Default Mode)
`results/fractal_map/hierarchical_map_center_projected/`
- `labels_res_0.25.npy` through `labels_res_3.0.npy` (7 resolutions)
- `labels_hierarchical_best.npy` (108 clusters, nested)
- `labels_coarse_0.5.npy` (7 parent clusters)

### Legal-Distance Mode Artifacts
`results/fractal_map/legal_distance_modes/<mode_id>/` (identical structure for all 5 modes):
- `cluster_metadata.json`, `zoom_mappings.json`, `zoom_coherence.json`
- `decision_clusters.json`, `integration_summary.json`
- `labels_res_0.25.npy` through `labels_res_3.0.npy`

### Loader API
`fractal_map/hierarchical/map_mode_loader.py` — Unified `ProductMapLoader` and `MapModeLoader` classes  
`fractal_map/hierarchical/map_mode_registry.py` — Registry with all 8 mode specifications

---

## Verification Results

All **48/48 tests** in `tests/fractal_map/test_verify.py` pass:

| Test Category | Tests | Passed | Failed |
|---------------|-------|--------|--------|
| TestArtifactIntegrity (center_projected) | 18 | 18 | 0 |
| TestHierarchicalLeiden | 6 | 6 | 0 |
| TestMetricConsistency | 7 | 7 | 0 |
| TestLegacyConcatPreserved | 10 | 10 | 0 |
| TestLegalDistanceModes | 3 | 3 | 0 |
| **Total** | **48** | **48** | **0** |

### Key Metric Validations
- ✅ All center_projected label arrays exist with correct shape (1000)
- ✅ Hierarchical purity > 0.95 (actual: 0.9638)
- ✅ Nesting = 1.0 (perfect)
- ✅ Sub-cluster sizes sum to 1000
- ✅ State file evidence_tier = REPRODUCED
- ✅ State file cycle_status = COMPLETED
- ✅ State file continue_recommended = false
- ✅ State file next_recommendation = PRODUCTIZE
- ✅ State file verdict = PASS
- ✅ State purity matches recomputed value
- ✅ Default mode is center_projected_hierarchical
- ✅ center_projected purity beats concat baseline
- ✅ All 5 legal-distance modes available at ACCEPTED tier
- ✅ Legacy concat mode preserved

---

## State File Consistency Verified

| Field | Expected | Actual (both files) | Match |
|-------|----------|---------------------|-------|
| direction_version | 5 | 5 | ✅ |
| evidence_tier | REPRODUCED | REPRODUCED | ✅ |
| cycle_status | COMPLETED | COMPLETED | ✅ |
| continue_recommended | false | false | ✅ |
| next_recommendation | PRODUCTIZE | PRODUCTIZE | ✅ |
| verdict | PASS | PASS | ✅ |
| hierarchical_purity_global | 0.963847 | 0.963847 | ✅ |
| nesting_score | 1.0 | 1.0 | ✅ |
| github_run | 33137354250 | 33137354250 | ✅ |
| default_mode | center_projected_hierarchical | center_projected_hierarchical | ✅ |

---

## Known Limitations (Preserved per Research Protocol)

1. **Corpus scope:** Validated on 1,000 decisions (2020-2024). Full TF 2000+ corpus requires corpus lane completion.
2. **igraph version sensitivity:** Cluster counts may vary; key invariants preserved (nesting=1.0, purity>0.94).
3. **Language-homogeneous clusters:** Some clusters are already pure at coarse resolution (ratio=1.0), showing no zoom improvement — expected.
4. **Legal-distance embeddings not persisted in fractal-map results:** Product lane loads them from legal-distance or regenerates. By design (separation of concerns).
5. **Flat Leiden nesting imperfect:** Mean ~0.50 across resolution ladder.
6. **Hybrid modes fail adversarial_falsification benchmark.**
7. **legal_issues_outcomes fails multilingual_invariance and adversarial_falsification.**

---

## Negative Results Preserved (Per Research Protocol)

1. Flat Leiden nesting imperfect (mean ~0.50 across resolution ladder)
2. Agglomerative wins nesting but loses purity (from prior experiments)
3. Resolution-dependent representation strategy falsified
4. Legal purity ratio < 1.0 even at finest zoom
5. ~60% of cluster-resolution pairs show no zoom improvement (already-homogeneous clusters)
6. igraph version sensitivity changes best config but preserves key invariants (nesting=1.0, purity>0.94)
7. Hybrid modes fail adversarial_falsification benchmark
8. legal_issues_outcomes fails multilingual_invariance and adversarial_falsification

---

## Orchestration Failure Diagnosis

### The Pathology
This operational resume addresses a **recurring orchestration pathology** where the supervisor dispatches operational resumes to already-completed lanes. The fractal-map lane completed its v5 question (center_projected_hierarchical as default), yet operational resumes continue to be dispatched.

### Root Cause
The supervisor dispatch mechanism **lacks a pre-dispatch guard** that reads `state/<lane>.json` before initiating a run. When:
- `cycle_status = COMPLETED`
- `continue_recommended = false`
- `next_recommendation = PRODUCTIZE`

No new scientific work is justified — only metadata synchronization and audit verification.

### Classification
**Orchestration inefficiency, NOT scientific failure.** The lane correctly completed its v5 question. This operational resume produces zero new experimental work — only state synchronization (github_run updated to 33137354250), audit gate generation, and verification.

### Fix Applied This Run
1. Updated `state/fractal-map.json` and `state/fractal_map.json`: `direction_version` 4/6 → 5, `github_run` updated to 33137354250, `accepted_run_id` updated, timestamp updated
2. Added current audit gate to `evidence_refs`
3. Created audit gate JSON documenting the completion
4. All 48 verification tests re-run and pass

### Orchestration Recommendation
**Add pre-dispatch guard** reading `state/<lane>.json` before supervisor dispatch. Skip dispatch when:
```python
state = read_json(f"state/{lane}.json")
if state.get("cycle_status") == "COMPLETED" and state.get("continue_recommended") == False:
    log(f"Lane {lane} already COMPLETED with continue_recommended=false. Skipping dispatch.")
    return
```
This would prevent unnecessary operational resumes for fractal-map and similar waste for other completed lanes.

---

## Recommendation

**PRODUCTIZE** — No further experimental work needed in fractal-map lane for v5.

The validated hierarchical Leiden map structure on center_projected embeddings is:
- **Scientifically sound:** Perfect nesting (1.0), higher purity than concat baseline (0.9638 vs 0.9491), zoom reveals legally coherent substructure (59.2% improvement rate)
- **Product-ready:** 10 integration artifacts + specification document the complete API for zoom navigation and mode switching
- **Transferable:** Methodology applies to any embedding representation (legal-distance selectable modes already integrated)
- **Adversarially validated:** ONLY representation passing BOTH language dominance (<0.85) AND jurist pairwise (>0.5) tests
- **Audit-ready:** All tests pass, state consistent, evidence traceable, github_run updated to 33137354250, control plane synced

### Product Lane Next Steps:
1. **Consume center_projected_hierarchical artifacts** from `results/fractal_map/hierarchical_map_center_projected/`
2. **Use map_mode_registry.json** for mode switching UI (8 modes: 1 default + 5 legal-distance + 1 placeholder + 1 legacy)
3. **Build zoom/navigation UI** using `zoom_mappings.json` and `cluster_metadata.json`
4. **Add side-by-side mode comparison** for legal-distance modes
5. **Integrate with corpus import** for user-provided corpora
6. **Scale to full TF 2000+ corpus** when corpus lane delivers
7. **Activate center_projected legal-distance mode** when legal-distance reproduces it (update registry status)

---

## Evidence References

- `state/fractal-map.json` (this run, direction_version=5, github_run=33137354250)
- `state/fractal_map.json` (synced, direction_version=5, github_run=33137354250)
- `state/factory_direction.json` (synced to v5 from control plane)
- `results/fractal_map/audit/CYCLE_center_projected_hierarchical_v5_33137354250_GATE.json`
- `results/fractal_map/audit/CYCLE_operational_resume_33135281890_GATE.json`
- `results/fractal_map/audit/CYCLE_operational_resume_33134755365_GATE.json`
- `results/fractal_map/audit/CYCLE_operational_resume_33134184565_GATE.json`
- `results/fractal_map/audit/CYCLE_operational_resume_33133395447_GATE.json`
- `results/fractal_map/audit/CYCLE_operational_resume_33132986797_GATE.json`
- `results/fractal_map/audit/CYCLE_operational_resume_33132507730_GATE.json`
- All prior audit gates and reports
- Verification test suite: `tests/fractal_map/test_verify.py` (48/48 PASS)
- Product integration: `results/fractal_map/product_integration/`
- Center_projected hierarchical map: `results/fractal_map/hierarchical_map_center_projected/`
- Legal-distance modes: `results/fractal_map/legal_distance_modes/`
- Loader API: `fractal_map/hierarchical/map_mode_loader.py`, `fractal_map/hierarchical/map_mode_registry.py`
- Map mode registry: `results/fractal_map/product_integration/map_mode_registry.json`

---

## Audit Verification

All artifacts verified:
- ✅ State files consistent with frozen metrics (both fractal-map.json and fractal_map.json)
- ✅ Map mode loader loads all 8 modes (1 default + 5 legal-distance available + 1 placeholder + 1 legacy)
- ✅ Legal-distance mode artifacts exist at `results/fractal_map/legal_distance_modes/<mode_id>/`
- ✅ Product integration package complete at `results/fractal_map/product_integration/`
- ✅ Center_projected_hierarchical is DEFAULT with all artifacts
- ✅ Legacy concat mode preserved for comparison
- ✅ No orphaned or missing artifacts
- ✅ 48/48 verification tests pass
- ✅ Control plane factory_direction.json synced to workspace (v5)

**Verdict:** PASS — Fractal-map lane v5 deliverable COMPLETE and audit-ready.

---

*Generated by fractal-map lane operational resume run 33137354250*  
*Audit timestamp: 2026-08-28*