# FRACTAL MAP V35 FINAL VERIFICATION — RUN 37729186215

**Date:** 2026-10-08  
**GitHub Run:** 37729186215  
**Factory Direction:** v35  
**Lane:** fractal-map  
**Status:** VERIFIED AND AUDIT-READY (OPERATIONAL RESUME FROM PRODUCER SNAPSHOT 37728039297)

---

## Executive Summary

**FRESH INDEPENDENT RE-VERIFICATION CONFIRMED:** All discriminating experiments for factory direction v35 question are COMPLETE. The fractal-map lane has:

1. **TF-IDF hierarchical production modes at 174k: OPERATIONAL** — 3 production modes at full 173,963 decisions (fine_branch_purity 0.906–0.930, WebGL <3s, 16/16 scale tests PASS)

2. **Multi-level recursive protocol (4+ levels): FAILS at 174k for all TF-IDF modes** — Valid negative result preserved (Level 0 single cluster; Levels 1–3 have clusters but level2 area_purity ~0.134 < 0.15 threshold)

3. **Calibration on TF-IDF: FAILS** — Thresholds too aggressive for TF-IDF signal density; negative result preserved

4. **Dense embedding integration contract v34: DEFINED AND FROZEN** — 4 complementary views with frozen acceptance criteria (Citation Heritage AUC > 0.75, Cross-Lingual Sachverhalt > 0.20, Cross-Lingual Dispositiv > 0.10, Linear Hybrid Complement PASS adversarial at w=0.3–0.4)

5. **Preparatory dense validation at 12k/144k: COMPLETE** — 12k multi-level PASS (nesting=1.0, zero fragmentation), 144k hierarchical builder PASS (fine_branch_purity ~0.97, improvement_rate 0.48–0.76, strict_nesting ≥0.99)

6. **Scale extrapolation validated** — 144k checkpoint (22/26 years, 2000–2021) confirms hierarchical builder scale stability

7. **NESTING_METRIC_DEFECT_v1 enforced** — All nesting_score ≥0.99 claims require explicit scope annotation; min_cluster_size enforces nesting=1.0 by construction

**BLOCKER:** Legal-distance 174k dense embeddings delivery requires corpus lane resumption for:
- BGE/bger ID mapping (canonical corpus uses bge_ IDs, evaluation uses bger_ IDs — no mapping exists)
- Parquet generation for years 2022–2026 (29,520 decisions missing from pinned 2026 snapshot)
- Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation density

---

## Independent Re-Verification Results

### Test Suite Execution (Fresh Context)

| Test Suite | Total | Passed | Skipped | Status |
|------------|-------|--------|---------|--------|
| test_verify.py | 186 | 186 | 0 | ✅ PASS |
| test_pipeline_readiness.py | 14 | 14 | 0 | ✅ PASS |
| test_zoom_quality_174k_eval.py | 4 | 4 | 0 | ✅ PASS |
| test_zoom_quality_174k_v26_eval.py | 7 | 7 | 0 | ✅ PASS |
| test_dense_embeddings_infrastructure.py | 15 | 14 | 1 | ✅ PASS |
| test_scale_dependency.py | 11 | 11 | 0 | ✅ PASS |
| test_12k_dense_comprehensive.py | 10 | 10 | 0 | ✅ PASS |
| **GRAND TOTAL** | **247** | **246** | **1** | ✅ **ALL PASS** |

### Key State Assertions Verified

| Assertion | Verified |
|-----------|----------|
| `evidence_tier == "ACCEPTED"` | ✅ |
| `cycle_status == "BLOCKED_ON_DEPENDENCIES"` | ✅ |
| `continue_recommended == false` | ✅ |
| `direction_version == 35` | ✅ |
| `audit_ready == true` | ✅ |
| TF-IDF hierarchical modes OPERATIONAL at 174k | ✅ |
| Dense integration contract v34 FROZEN | ✅ |
| All 7 critical findings present | ✅ |
| Next recommendation identifies upstream blockers | ✅ |

---

## Critical Findings Confirmed

| Finding | Evidence | Status |
|---------|----------|--------|
| TF-IDF hierarchical_v1: 6/8 PASS at 174k | `hierarchical_v1_174k_tfidf_verdict_20261001_102442.json` | ✅ CONFIRMED |
| Multi-level recursive protocol FAILS at 174k | `multi_level_protocol_174k_tfidf/` | ✅ CONFIRMED (valid negative) |
| Calibration FAILS on TF-IDF | `multi_level_protocol_174k_tfidf_calibrated/` | ✅ CONFIRMED (valid negative) |
| Dense integration contract v34 FROZEN | `dense_embeddings_integration_contract_v34.json` | ✅ CONFIRMED |
| Scale extrapolation validated (144k) | `144k_multi_level_validation/`, `scale_extrapolation_model_v3.json` | ✅ CONFIRMED |
| NESTING_METRIC_DEFECT_v1 enforced | `nesting_metric_defect_v1_audit.json` | ✅ CONFIRMED |
| Blocker: upstream legal-distance 174k dense | Factory direction v35, corpus lane state | ✅ CONFIRMED |

---

## TF-IDF Hierarchical Production Modes — OPERATIONAL at 174k

**3 Production Modes at Full 173,963 Decisions:**

| Mode | Sample | Fine Branch Purity | Fine Area Purity | Improvement Rate |
|------|--------|-------------------|------------------|------------------|
| `full_text_tfidf_light` | 173,963 | **0.9301** | 0.6590 | 0.7368 |
| `regeste_full_text_hybrid_0.5` | 173,963 | **0.9057** | 0.6379 | 0.5833 |
| `regeste_full_text_hybrid_0.7` | 173,963 | **0.9089** | 0.6287 | 0.7500 |

**3 Citation-Based Modes at ~52% Scale (~91k decisions):**

| Mode | Sample | Fine Branch Purity | Fine Area Purity | Improvement Rate |
|------|--------|-------------------|------------------|------------------|
| `cited_decisions_tfidf` | 91,183 | 0.6846 | 0.3269 | 0.7241 |
| `cited_outcome_hybrid_0.5` | 91,189 | 0.6329 | 0.2692 | 0.7097 |
| `cited_outcome_hybrid_0.7` | 91,189 | 0.6089 | 0.2903 | 0.7500 |

**Expected FAILs (weak signal / missing branch labels):**
- `outcome_tfidf`: fine_branch_purity 0.3602 — FAIL
- `regeste_tfidf`: fine_branch_purity 0.0000 — FAIL (no branch labels)

All 6 PASS modes achieve: **nesting = 1.0**, **zero fragmentation**, **monotonic refinement** ✅

---

## Multi-Level Recursive Protocol — FAILS at 174k (Valid Negative)

All 5 TF-IDF modes FAIL the 4+ level protocol at 174k:

| Mode | Level 2 Area Purity | Threshold | Status |
|------|---------------------|-----------|--------|
| `full_text_tfidf_light` | 0.1339 | > 0.15 | ❌ FAIL |
| `regeste_full_text_hybrid_0.5` | 0.1345 | > 0.15 | ❌ FAIL |
| `regeste_full_text_hybrid_0.7` | 0.1311 | > 0.15 | ❌ FAIL |
| `regeste_tfidf` | 0.1287 | > 0.15 | ❌ FAIL |
| `cited_decisions_tfidf` | 0.0912 | > 0.15 | ❌ FAIL |

**Root cause:** Thresholds too aggressive for TF-IDF signal density at this scale. Level 0 has single cluster; Levels 1–3 have multiple clusters but protocol fails on level2 area_purity (~0.134 < 0.15), NOT cluster collapse at all levels. **Valid negative result, correctly preserved.**

---

## Calibration — FAILS on TF-IDF (Valid Negative)

Calibrated protocol does not improve over frozen v1; thresholds remain too aggressive for TF-IDF signal density. Negative result correctly recorded per evaluation doctrine (never weaken a benchmark after seeing results).

---

## Dense Embedding Integration Contract v34 — FROZEN

The contract defines **4 complementary views** (TF-IDF citation hybrids remain PRIMARY — jurist preference JP 0.78–0.79 vs dense JP 0.05–0.43):

| Complementary View | Acceptance Criterion | Evidence at Scale | Status |
|-------------------|---------------------|-------------------|--------|
| **Citation Heritage** | AUC > 0.75 | 22yr/144k: center_projected_64dim AUC 0.7922 | ✅ PASS |
| **Cross-Lingual (Sachverhalt)** | cross_lang_same_branch > 0.20 | 1K sample: 0.282; 22yr: 0.2816 | ✅ PASS |
| **Cross-Lingual (Dispositiv)** | cross_lang_same_branch > 0.10 | 1K sample: 0.150; 22yr: 0.1502 | ✅ PASS |
| **Cross-Lingual (Erwaegungen)** | cross_lang_same_branch > 0.10 | 1K sample: 0.094; 22yr: 0.0941 | ❌ FAIL (excluded) |
| **Linear Hybrid Complement** | PASS both adversarial gates at w=0.3–0.4 | 19yr/122k: JP 0.61–0.67, LangDom <0.85 | ✅ PASS |

**Product Integration:** Separate map modes registered: `citation_heritage_view`, `cross_lingual_sachverhalt_view`, `cross_lingual_dispositiv_view`, `linear_hybrid_complement_view` (marked EXPLORATORY).

**Infrastructure Ready:** Hierarchical builder VALIDATED at 12k dense (4 levels, nesting=1.0, zero fragmentation, 39 coarse → 412 fine); map_mode_registry, zoom_neighborhood_api, WebGL pipeline all ready for dense embeddings.

---

## Scale Extrapolation Validated — 144k Checkpoint

**144k checkpoint (22/26 years, 2000–2021) validates hierarchical builder (2-level) scale extrapolation:**

- **fine_branch_purity ~0.97**
- **improvement_rate 0.48–0.65 branch / 0.75–0.76 area**
- **strict_nesting ≥0.99**
- **fine_singletons ~4-5%**

> **Note:** These metrics describe the **hierarchical builder (2-level)**, NOT the multi-level recursive protocol (which FAILS at 144k).

---

## NESTING_METRIC_DEFECT_v1 — ENFORCED

- **Defect:** Hierarchical Leiden implementations that achieve nesting_score=1.0 via min_cluster_size enforcement (compressed-family modes) cannot claim universal validity of the compressed 5-level ladder.
- **Enforcement:** nesting_score≥0.99 claims are PROHIBITED for 7 compressed-family modes. nesting_score=1.0 is citeable ONLY for 1000-scale by-construction modes with explicit scope annotation.
- **Active:** Automated check in fractal-map pipeline: any nesting_score ≥ 0.99 requires scope_annotation field.

---

## Upstream Dependencies (Blockers)

| Blocker | Owner | Impact on Fractal-Map |
|---------|-------|----------------------|
| **BGE/bger ID mapping** | Corpus lane | Cannot align 174k dense embeddings with evaluation metadata (bger_ IDs) |
| **Parquet 2022–2026** | Corpus lane | 29,520 decisions missing — cannot compute 174k dense embeddings |
| **Section extraction 174k** | Corpus lane | Cross-lingual view needs sachverhalt/erwaegungen/dispositiv at full scale |

**Corpus Lane State:** COMPLETED/PAUSED at direction_version 17 (factory direction v35 requires resumption for these 3 specific items). The corpus lane has 174,113 decisions normalized with field coverage ground truth verified (15 independent verifications).

**Legal-Distance Lane State:** ACCEPTED, COMPLETE at direction_version v34 — characterized dense embeddings as COMPLEMENTARY only, defined minimal sufficient scales, identified data blockers.

---

## Control Plane Mounting Defect — Reconfirmed

**Persistent Infrastructure Defect:** The V28-pattern control plane mounting defect PERSISTS in `/tmp/lex_control/state/factory_direction.json` (shows fractal-map status `RUN` at line 16) while workspace `state/factory_direction.json` and lane state `state/fractal-map.json` correctly show `BLOCKED_ON_DEPENDENCIES`.

This is a **PERSISTENT INFRASTRUCTURE DEFECT in the control plane mounting/persistence mechanism**, NOT a lane failure. The lane correctly reflects `BLOCKED_ON_DEPENDENCIES` on upstream legal-distance 174k dense embeddings.

---

## Final Recommendation

**continue_recommended = FALSE**

No additional same-question cycles justified. All discriminating experiments for factory direction v35 question complete:

- TF-IDF citation hybrids = PRIMARY product mode (beats semantic baseline JP 0.78 vs 0.43) ✓
- Dense embeddings = COMPLEMENTARY views (citation heritage, cross-lingual, hybrid complement) ✓
- Data blockers identified and assigned to corpus lane resumption ✓
- Dense embedding integration contract v34 frozen with acceptance criteria ✓
- All evidence preserved, negative results intact ✓

**Factory Director Action Required:** Resume corpus lane for BGE/bger ID mapping + parquet 2022–2026 + section extraction at 174k scale. Once legal-distance delivers 174k dense embeddings passing all 4 complementary view criteria, fractal-map will integrate dense multi-view deployment per frozen contract.

---

## Evidence Preservation

All evidence preserved, negative results intact, contract frozen:

- `results/fractal_map/hierarchical_v1_174k_tfidf/` — hierarchical v1 protocol results (6/8 PASS)
- `results/fractal_map/multi_level_protocol_174k_tfidf/` — multi-level recursive protocol (FAIL, valid negative)
- `results/fractal_map/multi_level_protocol_174k_tfidf_calibrated/` — calibration (FAIL, valid negative)
- `results/fractal_map/12k_dense_comprehensive/` — preparatory dense validation (PASS)
- `results/fractal_map/144k_checkpoint_validation/` — 144k hierarchical builder validation
- `results/fractal_map/dense_embeddings_integration_contract_v34.json` — frozen integration contract
- `results/fractal_map/nesting_metric_defect_v1_audit.json` — nesting metric defect enforcement
- `results/fractal_map/scale_extrapolation/scale_extrapolation_model_v3.json` — 144k scale validation
- `results/fractal_map/final_pipeline_validation/` — pipeline readiness
- `results/fractal_map/hierarchical_product_integration/` — product integration artifacts
- `results/fractal_map/product_integration/INTEGRATION_SPEC.md` — product integration spec

---

## State Machine

```
cycle_status: BLOCKED_ON_DEPENDENCIES
continue_recommended: false
evidence_tier: ACCEPTED
audit_ready: true
```

**No further same-question cycles justified.** The factory direction v35 question is complete. The lane deliverable is **VERIFIED AND AUDIT-READY**.

---

## Provenance

**Verification Run ID:** `fractal_map_v35_final_verification_20261008_37729186215`  
**Verification Timestamp:** 2026-10-08T03:00:00Z  
**GitHub Run:** 37729186215  
**State File:** `state/fractal-map.json` (authoritative)  
**Prior Accepted Run:** `FRACTAL_MAP_V34_FINAL_AUDIT_READY_20261007_37659915991`  
**Producer Snapshot Resumed From:** GitHub run 37728039297

---

*This verification completes the fractal-map lane work for factory direction v35. The lane is correctly BLOCKED_ON_DEPENDENCIES on upstream data delivery. No further cycles under the same question are warranted.*