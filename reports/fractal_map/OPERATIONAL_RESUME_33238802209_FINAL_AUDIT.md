# Fractal Map Lane — Operational Resume Run 33238802209 — Final Audit Gate

**Lane:** fractal-map  
**Factory Direction Version:** 6  
**GitHub Run:** 33238802209  
**Timestamp:** 2026-08-29T06:45:00Z  
**Audit Status:** PASS  
**Resumed From:** 33238505034  

---

## Summary

This operational resume run successfully re-established the `/tmp/lex_accepted/fractal_map/` mirroring (323 artifacts), validated all 15 verification tests, confirmed loader API functionality across all 8 map modes, and updated the lane state file for the current run. The snapshot is fully audit-ready for factory direction v6 completion.

---

## Orchestration Gap Diagnosis (Recurring)

**Diagnosis:** Ephemeral storage volatility between GitHub runs causes `/tmp/lex_accepted/fractal_map/` mirroring loss. This is a persistent infrastructure issue, not a scientific failure.

**Fix Applied:** Re-established mirroring in this run (run 33238802209), verified artifact count (323), all verification tests pass.

**Verification:** Artifact count stable, all 15 tests pass, loader API functional across all 8 modes.

---

## Factory Direction v6 Requirements — All Satisfied

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Center Projected Hierarchical Leiden as DEFAULT map structure | ✅ REPRODUCED | `center_projected_hierarchical_results.json`, purity=0.9571, nesting=1.0 |
| 7-resolution ladder with legal coherence metrics exposed | ✅ | Resolutions 0.25→3.0 (5→7→9→11→14→16→19 clusters) |
| Perfect nesting (1.0) guaranteed for hierarchical mode | ✅ | Hierarchical construction enforces nesting=1.0 |
| Zoom coherence improvement rate validated | ✅ | 62.96% (per-resolution-step, 68/108 fine clusters improve) |
| Hierarchical purity 0.9571 (+0.0080 vs concat baseline) | ✅ | min_cluster_size=3, validated on 1000 decisions |
| Adversarial language dominance < 0.85 | ✅ | 0.7593 PASS (carried forward from evaluation v2) |
| Jurist pairwise preference > 0.5 | ✅ | 0.5215 PASS (carried forward from evaluation v2) |
| Jurivoc 4/5 PASS | ✅ | (carried forward from evaluation v2) |
| Map mode registry with 8 modes | ✅ | 1 default + 5 legal-distance ACCEPTED + 1 legacy + 1 placeholder |
| Unified loader API for all modes | ✅ | `MapModeLoader` and `ProductMapLoader` operational |
| Product integration specification complete | ✅ | `PRODUCT_INTEGRATION_SPEC.md` generated |
| Map mode switching architecture designed | ✅ | Registry supports mode switching with warnings |

---

## Verification Test Results (15/15 PASS)

| Test | Description | Result |
|------|-------------|--------|
| 1 | 8 modes listed correctly | ✅ PASS |
| 2 | Default mode = center_projected_hierarchical | ✅ PASS |
| 3 | All 7 available/legacy modes load | ✅ PASS |
| 4 | Placeholder mode loads with warning | ✅ PASS |
| 5 | Resolution labels work (1.0) | ✅ PASS |
| 6 | Hierarchical labels work (91 valid clusters, size≥3) | ✅ PASS |
| 7 | Coarse labels work (7 clusters) | ✅ PASS |
| 8 | Cluster metadata works (res 0.5 = 7 clusters) | ✅ PASS |
| 9 | Zoom mappings work (7 parent, 9 child at 0.5→0.75) | ✅ PASS |
| 10 | Decision clusters work (7 resolutions) | ✅ PASS |
| 11 | Zoom coherence works | ✅ PASS |
| 12 | ProductMapLoader works | ✅ PASS |
| 13 | Key metrics match state file (purity 0.9571, flat 0.9341, config coarse_0.5_fine_3.0) | ✅ PASS |
| 14 | Zoom coherence validation PASS (62.96% vs concat 59.2%) | ✅ PASS |
| 15 | All 5 legal-distance modes load (7 resolution arrays each) | ✅ PASS |

---

## Key Metrics (Frozen Before Observation)

### Center Projected Hierarchical Leiden (DEFAULT)
- **Hierarchical purity (global):** 0.9571 (min_cluster_size=3)
- **Nesting score:** 1.0 (perfect, guaranteed by construction)
- **Resolution ladder:** [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
- **Hierarchical clusters:** 108 total (91 valid with size≥3)
- **Decisions:** 1000 (BGer 2020-2024)
- **Zoom coherence improvement rate:** 62.96% (68 improvements, 11 deteriorations, 29 no-change)
- **Concat baseline zoom coherence:** 59.18%
- **Branch purity ladder:** 0.840 → 0.912 → 0.972 → 0.965 → 0.964 → 0.955 → 0.929
- **Embeddings:** center_projected (768 dim, pure, no TF-IDF)
- **Adversarial language dominance:** 0.7593 (< 0.85 threshold) ✅
- **Jurist pairwise preference:** 0.5215 (> 0.5 threshold) ✅
- **Jurivoc benchmarks:** 4/5 PASS

### Legal-Distance Modes (ACCEPTED Tier)
1. **debiased_citation_blended** — 14/14 benchmarks PASS
2. **legal_cited_decisions_only** — 14/14 benchmarks PASS
3. **hybrid_alpha_03** — 13/14 PASS (fails adversarial_falsification) ⚠️
4. **hybrid_alpha_05** — 13/14 PASS (fails adversarial_falsification) ⚠️
5. **legal_issues_outcomes** — 10/14 PASS (fails 4 benchmarks) ⚠️

### Legacy Mode (Preserved for Comparison)
- **hierarchical_leiden_concat** — purity 0.9491, 98 clusters, zoom coherence 59.2%

---

## Artifacts Mirrored to /tmp/lex_accepted/fractal_map/ (323 files)

- `hierarchical_map_center_projected/` — 15 files (results, labels, metadata, zoom)
- `hierarchical_map/` — 9 files (legacy concat labels)
- `product_integration/` — 11 files (spec, registry, loaders, metadata, zoom, decisions)
- `legal_distance_modes/` — 5 mode directories with full artifacts
- `evaluation/` — 2 validation result files
- `audit/` — 38 audit gate files
- `reports/` — 18 markdown reports

---

## Next Recommendation

**PRODUCTIZE** — All factory direction v6 objectives for fractal-map lane are COMPLETED. The default center_projected_hierarchical map mode is validated, the unified loader API is operational, the map mode registry is complete with 8 modes, and the product integration specification is ready for consumption by the product lane.

No further same-question cycles are justified. The Factory Director should advance to the next phase: corpus scale to 192k, legal embeddings fine-tuning, jurist human study, and product hardening for full corpus scale.

---

## Provenance

All metrics frozen before observation. Negative results preserved (hybrid modes fail adversarial_falsification, legal_issues_outcomes fails 4/14). Comparison against strong concat baseline maintained. Evaluation v2 adversarial gates (language dominance, jurist pairwise) carried forward from independent evaluation lane run 33137354250.

