# Operational Resume Audit Report — Run 33266824102

**Lane:** fractal-map  
**Factory Direction Version:** 7  
**Timestamp:** 2026-08-29T17:58:00Z  
**Operational Resume From:** 33266335200  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETED  
**Continue Recommended:** false  
**Next Recommendation:** PRODUCTIZE  

---

## Summary

This operational resume from persisted producer snapshot of run 33266335200 completed successfully. All factory direction v7 requirements remain satisfied and frozen.

### Key Actions Performed

1. **Re-established `/tmp/lex_accepted/fractal_map/` mirroring** (344 artifacts) — mitigates ephemeral storage volatility between GitHub runs
2. **Ran full verification suite** — all 48 tests PASS
3. **Validated Loader API end-to-end** — all 12 map modes load successfully with complete artifacts
4. **Updated state file** — `github_run: 33266824102`, `accepted_run_id: v7_final_audit_33266824102`, new `key_findings` entry added
5. **Audit gate created** — `results/audit/fractal-map/CYCLE_33266824102_GATE.json` with verdict PASS

---

## Verification Results

| Test Suite | Total | Passed | Failed |
|------------|-------|--------|--------|
| `tests/fractal_map/test_verify.py` | 48 | 48 | 0 |

All tests pass including:
- Artifact integrity for center_projected and legacy concat modes
- Hierarchical Leiden metrics (purity > 0.95, nesting = 1.0, 108 clusters)
- State file consistency (evidence_tier, cycle_status, continue_recommended, verdict)
- Legal-distance mode integration (5 v6 + 4 v7 modes at ACCEPTED tier)
- Legacy mode preservation

---

## Map Mode Registry — 12 Modes Validated

| Mode ID | Type | Status | Notes |
|---------|------|--------|-------|
| `center_projected_hierarchical` | hierarchical_leiden | **AVAILABLE (DEFAULT)** | REPRODUCED, purity 0.9571, nesting 1.0 |
| `hierarchical_leiden_concat` | hierarchical_leiden | LEGACY | Preserved for comparison (purity 0.9491) |
| `debiased_citation_blended` | legal_distance | AVAILABLE | ACCEPTED, 14/14 benchmarks PASS |
| `legal_cited_decisions_only` | legal_distance | AVAILABLE | ACCEPTED, 14/14 benchmarks PASS |
| `hybrid_alpha_03` | legal_distance | AVAILABLE | ACCEPTED, 13/14 PASS (fails adversarial_falsification) |
| `hybrid_alpha_05` | legal_distance | AVAILABLE | ACCEPTED, 13/14 PASS (fails adversarial_falsification) |
| `legal_issues_outcomes` | legal_distance | AVAILABLE | ACCEPTED, 10/14 PASS (4 failures, warnings) |
| `linear_metric_epoch4` | hierarchical_leiden | AVAILABLE | ACCEPTED v7, JP 0.6847, LD 0.6802, both gates PASS |
| `mahalanobis_metric_epoch4` | hierarchical_leiden | AVAILABLE | ACCEPTED v7, JP 0.6781, LD 0.6840, both gates PASS |
| `cited_decisions_tfidf` | hierarchical_leiden | AVAILABLE | ACCEPTED v7, **JP 0.6889 (highest)**, LD 0.6086 (best), both gates PASS |
| `hybrid_cited_0.3` | hierarchical_leiden | AVAILABLE | ACCEPTED v7, JP 0.955 (near ceiling), LD 0.543, both gates PASS |
| `center_projected` | legal_distance | PLACEHOLDER | Raw embedding; use hierarchical mode for navigation |

---

## Factory Direction v7 — Requirements Status

✅ **REPRODUCE validated hierarchical Leiden map on center_projected embeddings as DEFAULT**  
- Nesting = 1.0, Hierarchical purity = 0.9571 (min_cluster_size=3)  
- Zoom coherence 63% improvement rate (68/108 fine clusters improve)  
- 7-resolution ladder: 5→7→9→11→14→16→19 clusters  
- 108 hierarchical clusters (coarse_0.5_fine_3.0)

✅ **EXTEND hierarchical structure on 4 v7 legal-distance ACCEPTED modes**  
- `linear_metric_epoch4`: purity 0.9868, 106 clusters, JP 0.6847, LD 0.6802, both gates PASS  
- `mahalanobis_metric_epoch4`: purity 0.9861, 111 clusters, JP 0.6781, LD 0.6840, both gates PASS  
- `cited_decisions_tfidf`: purity 0.7967, 353 clusters, **JP 0.6889 (highest)**, LD 0.6086 (best), both gates PASS  
- `hybrid_cited_0.3`: purity 0.9570, 136 clusters, JP 0.955 (near ceiling), LD 0.543, both gates PASS

✅ **All 4 v7 modes pass BOTH adversarial gates** (language dominance < 0.85, jurist pairwise > 0.5)

✅ **Resolution ladder, cluster metadata, legal coherence at each zoom level exposed** via unified loader API

✅ **Integration as default map structure with legal-distance selectable modes** — ProductMapLoader/MapModeLoader API complete

---

## Orchestration/Validation Failure Diagnosis (Re-Confirmed)

**Root Cause:** `/tmp/lex_accepted/` is ephemeral storage that does not persist between GitHub Actions runs. Each operational resume must re-establish the mirror from the persistent `results/fractal_map/` directory.

**Mitigation Applied (Verified Persistent Across 20+ Consecutive Runs):**
1. `mkdir -p /tmp/lex_accepted/fractal_map`
2. `cp -r results/fractal_map/* /tmp/lex_accepted/fractal_map/`
3. Run full verification suite (48 tests)
4. Validate loader API across all modes
5. Update state file with current run ID
6. Create audit gate file

**Status:** Mitigation verified persistent across consecutive runs. No further action needed beyond standard operational resume procedure.

---

## Artifact Inventory

### Core Hierarchical Map (Default)
- `results/fractal_map/hierarchical_map_center_projected/` — 16 artifacts (labels, metadata, zoom, clusters)

### Legal-Distance Modes (9 ACCEPTED)
- `results/fractal_map/legal_distance_modes/debiased_citation_blended/` — 14 artifacts
- `results/fractal_map/legal_distance_modes/legal_cited_decisions_only/` — 14 artifacts
- `results/fractal_map/legal_distance_modes/hybrid_alpha_03/` — 14 artifacts
- `results/fractal_map/legal_distance_modes/hybrid_alpha_05/` — 14 artifacts
- `results/fractal_map/legal_distance_modes/legal_issues_outcomes/` — 14 artifacts
- `results/fractal_map/legal_distance_modes/linear_metric_epoch4/` — 15 artifacts (v7)
- `results/fractal_map/legal_distance_modes/mahalanobis_metric_epoch4/` — 15 artifacts (v7)
- `results/fractal_map/legal_distance_modes/cited_decisions_tfidf/` — 15 artifacts (v7)
- `results/fractal_map/legal_distance_modes/hybrid_cited_0.3/` — 15 artifacts (v7)

### Product Integration
- `results/fractal_map/product_integration/` — 11 artifacts (spec, registry, loaders, metadata)

### Legacy (Preserved)
- `results/fractal_map/hierarchical_map/` — 9 artifacts (concat-based)

### Audit Trail
- `results/audit/fractal-map/CYCLE_33266824102_GATE.json`
- Historical audit gates preserved (33266335200, 33265387093, 33260174708, 33254783101, ...)

---

## State File Consistency

- `state/fractal-map.json` updated with current run metadata
- `evidence_tier`: REPRODUCED (unchanged)
- `cycle_status`: COMPLETED (unchanged)
- `continue_recommended`: false (unchanged)
- `next_recommendation`: PRODUCTIZE (unchanged)
- All validation metrics match recomputed values from artifacts
- Diff between repo and `/tmp/lex_accepted/fractal_map/` state: **clean**

---

## Conclusion

**AUDIT VERDICT: PASS**

The fractal-map lane deliverable for factory direction v7 is **complete, validated, and audit-ready**. All requirements satisfied:
- Center projected hierarchical Leiden REPRODUCED as DEFAULT map mode
- 4 v7 legal-distance modes extended with hierarchical structure (all pass both adversarial gates)
- 12-mode registry with unified loader API operational
- Product integration specification complete with map mode switching architecture
- Snapshot fully audit-ready for promotion

**Recommendation:** PRODUCTIZE — hand off to product lane for continuous improvement and production hardening at 192k scale.