# Fractal Map Lane — Audit-Ready Snapshot (Factory Direction v9)

**Run ID:** 33289164622  
**Lane:** fractal-map  
**Factory Direction Version:** 9  
**Timestamp:** 2026-08-30T03:03:00Z  
**Status:** PASS (Audit Gate)  
**Evidence Tier:** REPRODUCED  
**Operational Resume From:** 33288616347

---

## Executive Summary

This operational resume from the persisted producer snapshot of run 33288616347 (factory direction v9) completed successfully. The orchestration/validation failure was diagnosed and resolved: **/tmp/lex_accepted/fractal_map/ mirroring lost due to ephemeral storage volatility between GitHub runs**. Mirroring was re-established (541 artifacts), all 24 mode verification tests pass, and the MapModeLoader/ProductMapLoader API validates end-to-end across all modes. Factory direction v9 requirements remain SATISFIED and FROZEN. The snapshot is fully audit-ready.

---

## Orchestration Failure Diagnosis

**Root Cause:** Ephemeral `/tmp/lex_accepted/` storage volatility between GitHub Actions runs causes loss of mirrored artifacts required for loader API validation.

**Impact:** Without mirroring, loader API tests fail because artifacts are not accessible at the expected paths.

**Pattern:** Recurring across 13+ prior operational resumes (33288616347, 33287569320, 33286172433, 33285822955, 33285486319, 33282624299, 33282171375, 33281955890, 33281628054, 33281057149, 33280747298, 33277676851, 33275762305).

**Permanent Mitigation:** Factory launcher should include mirroring re-establishment step at start of every operational resume for all lanes.

---

## Remediation Actions (This Run)

1. **Mirroring Re-established:** Copied 541 artifacts from `results/fractal_map/` → `/tmp/lex_accepted/fractal_map/`
2. **Mode Verification:** All 24 modes load successfully via MapModeLoader/ProductMapLoader API
3. **API Validation:** End-to-end validation across all 24 modes (1 default + 21 legal-distance + 1 legacy + 1 placeholder)
4. **Adversarial Gates Confirmed:**
   - All v7 modes pass BOTH gates: `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `cited_decisions_tfidf`, `hybrid_cited_0.3`
   - All v9 cp-hybrids (6 modes) pass BOTH gates
   - All 6 NEW v9 breakthrough representations pass BOTH gates: `hybrid_stabilized_epoch1`, `cited_decisions_tfidf_outcome_hybrid_0.5`, `cited_decisions_tfidf_outcome_hybrid_0.7`, `following_alpha0.3`, `criticizing_alpha0.3`, `citing_alpha0.3`
5. **Zoom Validation Re-run:**
   - Center_projected hierarchical: **VERDICT PASS** (63.0% improvement rate, matching frozen benchmark)
   - Concat baseline hierarchical: **VERDICT PARTIAL** (59.2% improvement rate, legacy reference)
6. **Best Hybrids Confirmed:**
   - Best production: `cp64_0.7` (jurist=0.6564, lang_dom=0.6518)
   - Best jurist preference: `cp768_0.7` (jurist=0.6764, lang_dom=0.6477)

---

## Factory Direction v9 Requirements — ALL SATISFIED

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Extended hierarchical Leiden to 12 breakthrough representations | ✅ | 12 new modes built & validated |
| Two design patterns exposed as selectable map modes | ✅ | High-Purity (Metric Learning) + High-Advantage (Citation/Outcome + Citation Role) |
| High-Purity Metric Learning family complete | ✅ | `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1` |
| High-Advantage Citation/Outcome family complete | ✅ | `cited_decisions_tfidf`, `cited_outcome_hybrid_0.5`, `cited_outcome_hybrid_0.7` |
| High-Advantage Citation Role family complete | ✅ | `following_alpha0.3`, `criticizing_alpha0.3`, `citing_alpha0.3` |
| Default mode reproduced | ✅ | `center_projected_hierarchical` (nesting=1.0, purity=0.9571) |
| Resolution ladder exposed | ✅ | 7 levels (0.25 → 3.0) consistent across modes |
| Cluster metadata available | ✅ | Legal context per cluster at all resolutions |
| Legal coherence documented | ✅ | Branch purity, zoom coherence per level |
| Unified loader API implemented | ✅ | `MapModeLoader` + `ProductMapLoader` |
| Map mode switching architecture complete | ✅ | Registry with 24 modes, spec generated |
| Full corpus scale dependency noted | ✅ | Current: 1000 decisions (2020-2024); target: ~192k |

---

## Map Mode Registry — 24 Modes Total

### Default (1)
- `center_projected_hierarchical` — **DEFAULT** (REPRODUCED tier, nesting=1.0, purity=0.9571)

### Legal-Distance Available (21) — ALL ACCEPTED Tier
**v6 Baselines (5):**
- `debiased_citation_blended` — 14/14 benchmarks
- `legal_cited_decisions_only` — 14/14 benchmarks
- `hybrid_alpha_03` — 13/14 (⚠️ fails adversarial_falsification)
- `hybrid_alpha_05` — 13/14 (⚠️ fails adversarial_falsification)
- `legal_issues_outcomes` — 10/14 (⚠️ fails 4 benchmarks)

**v7 Metric Learning & Citation Signal (4) — ALL PASS BOTH ADVERSARIAL GATES:**
- `linear_metric_epoch4` — JP=0.6847, LangDom=0.6802, purity=0.9868
- `mahalanobis_metric_epoch4` — JP=0.6781, LangDom=0.6840, purity=0.9861
- `cited_decisions_tfidf` — JP=0.6889, LangDom=0.6086, purity=0.7967
- `hybrid_cited_0.3` — JP=0.955, LangDom=0.543, purity=0.9570

**v9 cp-Hybrids (6) — ALL PASS BOTH ADVERSARIAL GATES:**
- `cited_decisions_tfidf_hybrid_cp64_0.3` — JP=0.5346, LD=0.7483
- `cited_decisions_tfidf_hybrid_cp64_0.5` — JP=0.5521, LD=0.7192
- `cited_decisions_tfidf_hybrid_cp64_0.7` — **BEST PRODUCTION cp64** (JP=0.6564, LD=0.6518)
- `cited_decisions_tfidf_hybrid_cp768_0.3` — JP=0.5312, LD=0.7521
- `cited_decisions_tfidf_hybrid_cp768_0.5` — JP=0.5678, LD=0.7034
- `cited_decisions_tfidf_hybrid_cp768_0.7` — **BEST JURIST PREFERENCE** (JP=0.6764, LD=0.6477)

**v9 Breakthrough Representations (6) — ALL PASS BOTH ADVERSARIAL GATES:**
- `hybrid_stabilized_epoch1` — HIGH PURITY (Fine=0.9638, ImpRate=73.8%)
- `cited_decisions_tfidf_outcome_hybrid_0.5` — **BEST PRODUCTION** (HierAdv=+0.2918, LangDom=0.4911, JP=0.7990)
- `cited_decisions_tfidf_outcome_hybrid_0.7` — **BEST FRACTAL** (HierAdv=+0.3703, ImpRate=90.3%)
- `following_alpha0.3` — Citation Role (Fine=0.9501, ImpRate=82.2%)
- `criticizing_alpha0.3` — Citation Role (Fine=0.9619, HierAdv=+0.0815%)
- `citing_alpha0.3` — Citation Role (ImpRate=66.9%)

### Legacy (1)
- `hierarchical_leiden_concat` — REPRODUCED, preserved for comparison (purity=0.9491)

### Placeholder (1)
- `center_projected` — raw embedding, infrastructure ready

---

## Design Patterns Exposed as Selectable Map Modes

### HIGH-PURITY (Metric Learning Family)
| Mode | Fine Purity | Improvement Rate | Key Strength |
|------|-------------|------------------|--------------|
| `linear_metric_epoch4` | 0.9868 | 75.6% | Best jurist preference in family |
| `mahalanobis_metric_epoch4` | 0.9861 | 71.4% | Near-identical purity |
| `hybrid_stabilized_epoch1` | 0.9638 | 73.8% | Stabilized metric learning |

### HIGH-ADVANTAGE (Citation/Outcome Family)
| Mode | HierAdv | ImpRate | Key Strength |
|------|---------|---------|--------------|
| `cited_decisions_tfidf` | +0.1415 | 97.1% | Zero-shot, best LangDom |
| `cited_outcome_hybrid_0.5` | +0.2918 | 86.8% | **BEST PRODUCTION** (JP=0.7990) |
| `cited_outcome_hybrid_0.7` | +0.3703 | 90.3% | **BEST FRACTAL** (HierAdv) |

### HIGH-ADVANTAGE (Citation Role Family)
| Mode | Fine Purity | ImpRate | Key Strength |
|------|-------------|---------|--------------|
| `following_alpha0.3` | 0.9501 | 82.2% | Following precedent |
| `criticizing_alpha0.3` | 0.9619 | — | Criticizing precedent (+HierAdv) |
| `citing_alpha0.3` | 0.9203 | 66.9% | General citation |

---

## Verification Results

| Test | Result | Details |
|------|--------|---------|
| Artifacts mirrored | ✅ PASS | 541 files |
| Mode loadability (24/24) | ✅ PASS | All modes load via API |
| Default mode artifacts complete | ✅ PASS | 9 label arrays, 7 metadata, 6 zoom mappings |
| Breakthrough representations (12) | ✅ PASS | All built with hierarchical Leiden |
| v7 modes (4) adversarial gates | ✅ PASS | Both gates pass |
| v9 cp-hybrids (6) adversarial gates | ✅ PASS | Both gates pass |
| v9 breakthrough (6) adversarial gates | ✅ PASS | Both gates pass |
| Center_projected zoom validation | ✅ PASS | 63.0% improvement rate |
| Concat baseline zoom validation | ⚠️ PARTIAL | 59.2% (legacy reference) |
| ProductMapLoader API | ✅ PASS | Full end-to-end functional |

---

## Key Metrics (Frozen Benchmarks)

### Center Projected Hierarchical Leiden (DEFAULT)
- **Hierarchical Purity (global):** 0.9571 (+0.0080 vs concat baseline)
- **Nesting Score:** 1.0 (perfect, guaranteed by construction)
- **Hierarchical Clusters:** 108 (coarse_0.5_fine_3.0, min_cluster_size=3)
- **Resolution Ladder:** 7 levels [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
- **Zoom Coherence Improvement Rate:** 63.0% (per-resolution-step, 68/108 fine clusters improve)
- **Branch Purity Ladder:** 0.840 → 0.912 → 0.972 → 0.965 → 0.964 → 0.955 → 0.929
- **Adversarial Language Dominance:** 0.7593 (< 0.85) ✅ — *source: evaluation_v2_cycle_33137354250*
- **Jurist Pairwise Preference:** 0.5215 (> 0.5) ✅ — *source: evaluation_v2_cycle_33137354250*
- **Jurivoc Hierarchy Alignment:** 4/5 PASS — *source: evaluation_v2_cycle_33137354250*

### Concat Baseline (LEGACY)
- **Hierarchical Purity:** 0.9491
- **Zoom Coherence Improvement Rate:** 59.2% (different methodology)
- **Clusters:** 98

---

## Artifacts Inventory

**Total Mirrored:** 541 artifacts at `/tmp/lex_accepted/fractal_map/`

**Key Directories:**
- `hierarchical_map_center_projected/` — Default mode artifacts (labels, metadata, zoom mappings, coherence)
- `hierarchical_map/` — Concat baseline artifacts (legacy)
- `legal_distance_modes/<mode_id>/` — 21 legal-distance mode artifact directories
- `product_integration/` — Registry, loader API, integration spec
- `evaluation/` — Zoom validation results

---

## Next Recommendation

**PRODUCTIZE** — Factory direction v9 complete. The fractal map lane has delivered:
- Default hierarchical map with proven legal coherence
- 21 selectable legal-distance map modes across 3 design patterns
- Unified loader API for product integration
- Full artifact persistence for all modes
- Resolution ladder with documented legal coherence at each zoom level

**Dependencies for next phase:**
1. **Corpus Lane:** Scale to full 2000-2024 corpus (~192k decisions)
2. **Product Lane:** Consume artifacts, implement mode selector UI, side-by-side comparison
3. **Legal-Distance Lane:** Reproduce center_projected on full benchmark suite

---

## Evidence References

- `results/audit/fractal-map/CYCLE_operational_resume_33289164622_GATE.json`
- `results/audit/fractal-map/CYCLE_operational_resume_33288616347_GATE.json`
- `results/fractal_map/hierarchical_map_center_projected/`
- `results/fractal_map/legal_distance_modes/`
- `results/fractal_map/product_integration/`
- `state/fractal-map.json`

---

*This snapshot is generated from validated REPRODUCED/ACCEPTED evidence. All metrics are frozen before observation and match the accepted state files. Negative results (concat baseline PARTIAL, v6 mode warnings) are preserved as first-class evidence.*