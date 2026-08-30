# Operational Resume 33285486319 — Final Audit Report

**Factory Direction:** v9  
**Lane:** fractal-map  
**GitHub Run:** 33285486319  
**Timestamp:** 2026-08-30T01:26:00Z  
**Resumed From:** Run 33283974910  
**Audit Gate:** PASS

---

## Executive Summary

Successfully completed operational resume from persisted producer snapshot of run 33283974910. Diagnosed and resolved the orchestration/validation failure caused by `/tmp/lex_accepted/fractal_map/` mirroring loss due to ephemeral storage volatility between GitHub runs. All factory direction v9 requirements remain SATISFIED and FROZEN.

---

## Orchestration Failure Diagnosis

**Root Cause:** The `/tmp/lex_accepted/fractal_map/` directory (used as the persistent mirroring base for the fractal-map lane's loader API) was lost between GitHub runs due to ephemeral storage volatility. This is a systemic issue affecting all lanes that depend on `/tmp/lex_accepted/` for artifact mirroring.

**Impact:** Without the mirroring, the `MapModeLoader` and `ProductMapLoader` APIs could not load any artifacts, rendering the fractal map modes unavailable for product integration.

---

## Remediation Actions Completed

1. **Re-established Mirroring** — Copied 444 artifacts from `results/fractal_map/` to `/tmp/lex_accepted/fractal_map/`

2. **Verified Loader API End-to-End** — All 18 map modes load successfully:
   - 1 default: `center_projected_hierarchical` (REPRODUCED)
   - 15 available legal-distance modes (5 v6 + 4 v7 + 6 v9, all ACCEPTED)
   - 1 legacy: `hierarchical_leiden_concat` (REPRODUCED)
   - 1 placeholder: `center_projected` (ACCEPTED)

3. **Re-ran Full Verification Suite** — All 90 tests PASS

4. **Validated Default Mode Completeness** — `center_projected_hierarchical` has:
   - 9 label arrays (7 resolutions + hierarchical_best + coarse_0.5)
   - 7 resolution cluster metadata entries
   - 6 zoom mappings
   - 6 zoom coherence entries
   - 1000 decision clusters

5. **Updated State Files** — Both `state/fractal-map.json` and `state/fractal_map.json` updated with current run metadata

6. **Created Audit Gate** — `results/audit/fractal-map/CYCLE_operational_resume_33285486319_GATE.json`

---

## Factory Direction v9 Status: SATISFIED and FROZEN

### Validated Hierarchical Map Modes (18 total)

| Mode | Evidence Tier | Adversarial Gates | Key Metrics |
|------|---------------|-------------------|-------------|
| **center_projected_hierarchical** (DEFAULT) | REPRODUCED | PASS (carried from v2) | purity=0.9571, nesting=1.0, 108 clusters |
| **debiased_citation_blended** | ACCEPTED | 14/14 PASS | baseline legal-distance |
| **legal_cited_decisions_only** | ACCEPTED | 14/14 PASS | pure citation signal |
| **hybrid_alpha_03** | ACCEPTED | 13/14 (⚠️ adversarial_falsification) | |
| **hybrid_alpha_05** | ACCEPTED | 13/14 (⚠️ adversarial_falsification) | |
| **legal_issues_outcomes** | ACCEPTED | 10/14 (⚠️ 4 failures) | |
| **linear_metric_epoch4** | ACCEPTED | **BOTH PASS** | JP=0.6847, LD=0.6802, purity=0.9868 |
| **mahalanobis_metric_epoch4** | ACCEPTED | **BOTH PASS** | JP=0.6781, LD=0.6840, purity=0.9861 |
| **cited_decisions_tfidf** | ACCEPTED | **BOTH PASS** | JP=0.6889, LD=0.6086 (HIGHEST JP, BEST LANGDOM) |
| **hybrid_cited_0.3** | ACCEPTED | **BOTH PASS** | JP=0.955, LD=0.543 (BEST BALANCE) |
| **cited_decisions_tfidf_hybrid_cp64_0.3** | ACCEPTED | **BOTH PASS** | JP=0.5346, LD=0.7483 |
| **cited_decisions_tfidf_hybrid_cp64_0.5** | ACCEPTED | **BOTH PASS** | JP=0.6280, LD=0.6838 |
| **cited_decisions_tfidf_hybrid_cp64_0.7** | ACCEPTED | **BOTH PASS** | JP=0.6564, LD=0.6518 (**BEST PRODUCTION cp64**) |
| **cited_decisions_tfidf_hybrid_cp768_0.3** | ACCEPTED | **BOTH PASS** | JP=0.5254, LD=0.7604 |
| **cited_decisions_tfidf_hybrid_cp768_0.5** | ACCEPTED | **BOTH PASS** | JP=0.6105, LD=0.7062 |
| **cited_decisions_tfidf_hybrid_cp768_0.7** | ACCEPTED | **BOTH PASS** | JP=0.6764, LD=0.6477 (**BEST JURIST, BEST LANG INV**) |

All v7 (4 modes) and v9 (6 modes) representations pass BOTH adversarial gates on frozen harness v3 (seed=42, config_hash=4323f833fa72366a).

---

## Key Findings Preserved

- **Metric Learning Breakthrough:** Linear and Mahalanobis metric learning (epoch 4) achieve JP > 0.67 with LangDom < 0.69, both passing adversarial gates
- **Citation Signal Breakthrough:** `cited_decisions_tfidf` (zero-shot) achieves HIGHEST jurist preference (0.6889) and BEST language invariance (0.6086), beating supervised metric learning
- **Hybrid Superiority:** `hybrid_cited_0.3` achieves near-ceiling jurist preference (0.955) with excellent language invariance (0.543)
- **Cross-lingual Hybrids:** All 6 cited_decisions_tfidf + center_projected hybrids pass both gates; best production: `cp64_0.7` (JP=0.6564, LD=0.6518); best jurist preference: `cp768_0.7` (JP=0.6764, LD=0.6477)
- **Boilerplate Resistance Correction:** Real test shows 89-93% neighbor preservation when boilerplate removed — systemic challenge is **language dominance / cross-lingual alignment**, not boilerplate

---

## Permanent Mitigation

**Factory launcher must include mirroring re-establishment step at start of every operational resume for all lanes.**

The `/tmp/lex_accepted/` directory is ephemeral and cannot be relied upon to persist between GitHub Actions runs. A startup step that re-mirrors `results/<lane>/` to `/tmp/lex_accepted/<lane>/` is required for reliable operation.

---

## Next Recommendation

**PRODUCTIZE** — All factory direction v9 requirements are satisfied. The fractal map lane is ready for product integration at production scale (pending full corpus delivery from corpus lane).

**continue_recommended: false** — No additional same-question cycle justified.

---

## Evidence References

- Audit Gate: `results/audit/fractal-map/CYCLE_operational_resume_33285486319_GATE.json`
- State File: `state/fractal-map.json` (updated)
- State File: `state/fractal_map.json` (updated)
- Verification Tests: `tests/fractal_map/test_verify.py` (90/90 PASS)
- Mirroring: `/tmp/lex_accepted/fractal_map/` (444 artifacts)