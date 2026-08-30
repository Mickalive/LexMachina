# Operational Resume Audit — Fractal Map Lane

**Run ID:** 33282171375  
**Lane:** fractal-map  
**Factory Direction Version:** 9  
**Status:** PASS  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Recommendation:** PRODUCTIZE  
**Operational Resume From:** 33281955890  
**Timestamp:** 2026-08-30T00:00:00.000000Z

---

## Executive Summary

This operational resume successfully diagnoses and resolves the orchestration/validation failure caused by **ephemeral storage volatility** between GitHub runs. The `/tmp/lex_accepted/fractal_map/` mirroring directory was lost between runs, a known systemic issue with the current infrastructure. This run re-establishes mirroring (441 artifacts verified), re-runs all 90 verification tests (all PASS), validates the MapModeLoader/ProductMapLoader API end-to-end across all 18 modes, and confirms factory direction v9 requirements remain SATISFIED and FROZEN.

**Audit Gate: PASS** — Snapshot fully audit-ready for factory direction v9 completion.

---

## Orchestration Gap Diagnosis

### Root Cause
The `/tmp/lex_accepted/fractal_map/` directory is stored on ephemeral storage that does not persist between GitHub Actions runs. Each operational resume must re-establish mirroring from the persistent repository results directory.

### Evidence
- Prior run 33281955890: Mirroring re-established with 441 artifacts
- This run 33282171375: Mirroring was lost, re-established with 441 artifacts
- All prior operational resumes (33280747298, 33281057149, 33281628054, 33281955890) document the same pattern

### Permanent Mitigation (Recommended)
Factory launcher should include a **mirroring re-establishment step at the start of every operational resume for all lanes**. This is an infrastructure responsibility, not a scientific one.

---

## Verification Results

### Test Suite: 90/90 PASS

| Test Class | Tests | Passed | Failed |
|------------|-------|--------|--------|
| TestArtifactIntegrity (center_projected) | 13 | 13 | 0 |
| TestArtifactIntegrity (v9 modes) | 42 | 42 | 0 |
| TestHierarchicalLeiden | 5 | 5 | 0 |
| TestMetricConsistency | 8 | 8 | 0 |
| TestLegacyConcatPreserved | 10 | 10 | 0 |
| TestLegalDistanceModes | 12 | 12 | 0 |
| **Total** | **90** | **90** | **0** |

### Key Validations
- ✅ Center Projected Hierarchical Leiden DEFAULT (purity=0.9571, nesting=1.0, 108 clusters)
- ✅ All 6 v9 cited_decisions_tfidf + center_projected hybrids PASS both adversarial gates
- ✅ All 4 v7 modes (linear_metric_epoch4, mahalanobis_metric_epoch4, cited_decisions_tfidf, hybrid_cited_0.3) PASS both adversarial gates
- ✅ All 5 v6 legal-distance modes integrated with warnings appropriately marked
- ✅ Legacy concat mode preserved for comparison
- ✅ Placeholder center_projected mode available for legal-distance benchmarking

---

## Map Mode Registry: 18 Modes Total

| Category | Count | Modes |
|----------|-------|-------|
| **DEFAULT** | 1 | center_projected_hierarchical (REPRODUCED, purity=0.9571) |
| **LEGAL-DISTANCE (ACCEPTED, available)** | 15 | 5 v6 baseline + 4 v7 metric_learning/citation_signal + 6 v9 cited_decisions hybrids |
| **LEGACY** | 1 | hierarchical_leiden_concat (REPRODUCED, purity=0.9491) |
| **PLACEHOLDER** | 1 | center_projected (raw embedding, for legal-distance benchmarking) |

### v6 Baseline Modes (5)
- debiased_citation_blended — 14/14 benchmarks PASS
- legal_cited_decisions_only — 14/14 benchmarks PASS
- hybrid_alpha_03 — 13/14 PASS (fails adversarial_falsification) ⚠️
- hybrid_alpha_05 — 13/14 PASS (fails adversarial_falsification) ⚠️
- legal_issues_outcomes — 10/14 PASS (fails 4 benchmarks) ⚠️

### v7 Metric Learning + Citation Signal Modes (4) — ALL PASS BOTH ADVERSARIAL GATES
- linear_metric_epoch4 — JP=0.6847, LangDom=0.6802, hierarchical_purity=0.9868 (106 clusters)
- mahalanobis_metric_epoch4 — JP=0.6781, LangDom=0.6840, hierarchical_purity=0.9861 (111 clusters)
- cited_decisions_tfidf — JP=0.6889, LangDom=0.6086, hierarchical_purity=0.7967 (353 clusters) ⭐ HIGHEST JP, BEST LangDom
- hybrid_cited_0.3 — JP=0.955, LangDom=0.543, hierarchical_purity=0.9570 (136 clusters) ⭐ BEST BALANCE

### v9 Cited Decisions TF-IDF + Center Projected Hybrids (6) — ALL PASS BOTH ADVERSARIAL GATES
- cp64_0.3 — JP=0.5346, LangDom=0.7483
- cp64_0.5 — JP=0.6280, LangDom=0.6838
- **cp64_0.7 — JP=0.6564, LangDom=0.6518** ⭐ **BEST PRODUCTION HYBRID (cp64)**
- cp768_0.3 — JP=0.5254, LangDom=0.7604
- cp768_0.5 — JP=0.6105, LangDom=0.7062
- **cp768_0.7 — JP=0.6764, LangDom=0.6477** ⭐ **BEST JURIST PREFERENCE OF ALL HYBRIDS**

---

## Loader API Validation: End-to-End Across All 18 Modes

### MapModeLoader
- ✅ `list_modes()` returns all 18 modes with correct metadata
- ✅ `get_default_mode_id()` returns `center_projected_hierarchical`
- ✅ `load_mode()` loads all 18 modes successfully
- ✅ Default mode: 9 label arrays + full cluster_metadata + zoom_mappings + zoom_coherence + decision_clusters (1000 decisions)
- ✅ 10 v6/v7/v9 hierarchical Leiden modes: 9 label arrays (includes hierarchical_best + coarse_0.5)
- ✅ 5 v6 flat Leiden modes: 7 label arrays
- ✅ Legacy mode: 9 label arrays
- ✅ Placeholder mode: Minimal integration_summary with legal_distance_config

### ProductMapLoader
- ✅ Unified product-facing API functional
- ✅ All resolution label accessors work
- ✅ Cluster metadata, zoom mappings, coherence, decision clusters accessible
- ✅ Mode switching architecture validated

---

## Factory Direction v9 Requirements: SATISFIED & FROZEN

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Extend hierarchical Leiden to linear_metric_epoch4 | ✅ COMPLETE | v7 mode integrated, both gates PASS |
| Extend hierarchical Leiden to mahalanobis_metric_epoch4 | ✅ COMPLETE | v7 mode integrated, both gates PASS |
| Extend hierarchical Leiden to cited_decisions_tfidf | ✅ COMPLETE | v7 mode integrated, both gates PASS |
| Extend hierarchical Leiden to hybrid_cited_0.3 | ✅ COMPLETE | v7 mode integrated, both gates PASS |
| Extend hierarchical Leiden to 6 cited_decisions_tfidf + CP hybrids | ✅ COMPLETE | v9 modes integrated, all both gates PASS |
| Expose resolution ladder (7 levels) | ✅ COMPLETE | 0.25→0.5→0.75→1.0→1.5→2.0→3.0 |
| Cluster metadata at each zoom level | ✅ COMPLETE | cluster_metadata.json for all modes |
| Legal coherence at each zoom level | ✅ COMPLETE | branch/area/chamber/language per cluster |
| Default map structure integrated | ✅ COMPLETE | center_projected_hierarchical is DEFAULT |
| Legal-distance selectable modes | ✅ COMPLETE | 15 available modes via MapModeLoader |

---

## Artifact Inventory (441 files)

```
results/fractal_map/
├── audit/                                    (70 audit gates)
├── baseline/                                 (1 metadata)
├── hierarchical_map/                         (10 legacy concat artifacts)
├── hierarchical_map_center_projected/        (17 default mode artifacts)
├── legal_distance_modes/
│   ├── debiased_citation_blended/            (10 v6 artifacts)
│   ├── legal_cited_decisions_only/           (10 v6 artifacts)
│   ├── hybrid_alpha_03/                      (10 v6 artifacts)
│   ├── hybrid_alpha_05/                      (10 v6 artifacts)
│   ├── legal_issues_outcomes/                (10 v6 artifacts)
│   ├── linear_metric_epoch4/                 (7 v7 artifacts)
│   ├── mahalanobis_metric_epoch4/            (7 v7 artifacts)
│   ├── cited_decisions_tfidf/                (7 v7 artifacts)
│   ├── hybrid_cited_0.3/                     (7 v7 artifacts)
│   ├── cited_decisions_tfidf_hybrid_cp64_0.3/ (7 v9 artifacts)
│   ├── cited_decisions_tfidf_hybrid_cp64_0.5/ (7 v9 artifacts)
│   ├── cited_decisions_tfidf_hybrid_cp64_0.7/ (7 v9 artifacts)
│   ├── cited_decisions_tfidf_hybrid_cp768_0.3/ (7 v9 artifacts)
│   ├── cited_decisions_tfidf_hybrid_cp768_0.5/ (7 v9 artifacts)
│   └── cited_decisions_tfidf_hybrid_cp768_0.7/ (7 v9 artifacts)
├── product_integration/                      (13 integration artifacts)
└── evaluation/                               (2 validation artifacts)
```

**Total: 441 artifacts** (matches prior run 33281955890 count)

---

## State File Consistency

The state file `state/fractal-map.json` has been updated with:
- `direction_version`: 9
- `evidence_tier`: REPRODUCED
- `cycle_status`: COMPLETED
- `continue_recommended`: false
- `accepted_run_id`: v9_operational_resume_33282171375
- `github_run`: 33282171375
- `next_recommendation`: PRODUCTIZE
- All evidence_refs, key_findings, metrics_summary, validation_metrics, map_modes consistent with verified artifacts

---

## Provenance Chain

```
33253301963  → v6 completion (center_projected_hierarchical DEFAULT)
33263510038  → v7 completion (4 metric_learning/citation_signal modes)
33270668887  → v8 completion (audit gate)
33279699567  → v9 completion (6 cited_decisions_tfidf + CP hybrids)
33280747298  → operational resume (mirroring re-established: 637 artifacts)
33281057149  → operational resume (mirroring re-established: 613 artifacts)
33281628054  → operational resume (mirroring re-established: 444 artifacts)
33281955890  → operational resume (mirroring re-established: 441 artifacts)
33282171375  → THIS RUN (mirroring re-established: 441 artifacts, 90/90 tests PASS)
```

---

## Recommendation

**PRODUCTIZE** — Factory direction v9 deliverables are complete, validated, and frozen. The fractal map lane has produced:
1. A REPRODUCED default hierarchical fractal map (center_projected_hierarchical)
2. 15 ACCEPTED legal-distance selectable map modes spanning v6/v7/v9 breakthroughs
3. A unified loader API with full map mode switching capability
4. Complete artifact persistence and audit trail

No further fractal-map cycles are justified under the current factory direction question. The next factory direction should advance to full corpus scaling (192k decisions) and product hardening.

---

## Files Modified in This Run

1. `/tmp/lex_accepted/fractal_map/` — Mirroring re-established (441 artifacts + state.json)
2. `results/fractal_map/audit/CYCLE_operational_resume_33282171375_GATE.json` — Audit gate
3. `reports/fractal_map/OPERATIONAL_RESUME_33282171375_FINAL_AUDIT.md` — This report
4. `state/fractal-map.json` — Updated with current run metadata

---

*All metrics frozen before observation. Negative results preserved. Evidence tier: REPRODUCED.*
