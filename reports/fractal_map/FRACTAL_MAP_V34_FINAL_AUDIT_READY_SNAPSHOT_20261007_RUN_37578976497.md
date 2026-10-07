# FRACTAL MAP V34 — FINAL AUDIT-READY SNAPSHOT
**GitHub Run:** 37578976497 | **Factory Direction:** v34 | **Timestamp:** 2026-10-07T09:30:00.000000Z  
**Operational Resume From:** Producer snapshot run 37576522131

---

## EXECUTIVE SUMMARY

**NO ORCHESTRATION/VALIDATION FAILURE IN FRACTAL-MAP LANE.** The V28-pattern control plane mounting defect PERSISTS in the mounted `/tmp/lex_control/state/factory_direction.json` (shows `RUN` at line 16) while **workspace `state/factory_direction.json` and lane `state/fractal_map.json` correctly show `BLOCKED_ON_DEPENDENCIES`** — this is a PERSISTENT INFRASTRUCTURE DEFECT in the control plane mounting/persistence mechanism, NOT a lane failure.

**Lane status is AUTHORITATIVE and CORRECT:** `BLOCKED_ON_DEPENDENCIES` on upstream legal-distance 174k dense embeddings.

**All discriminating experiments for factory direction v34 question COMPLETE.**

---

## DISCRIMINATING EXPERIMENTS — FINAL STATUS

| # | Experiment | Status | Key Result |
|---|------------|--------|------------|
| 1 | **TF-IDF Hierarchical v1 (2-level) at 174k** | ✅ **OPERATIONAL** | 3 production modes at full 173,963 decisions; `fine_branch_purity` 0.906–0.930; 6/8 modes PASS |
| 2 | **Multi-level Recursive Protocol (4+ levels) at 174k** | ❌ **FAILS (valid negative)** | All 5 TF-IDF modes FAIL: Level 0 single cluster; Levels 1–3 multi-cluster but `level2 area_purity` ~0.134 < 0.15 threshold — NOT cluster collapse at all levels |
| 3 | **Calibration at 174k** | ❌ **FAILS (valid negative)** | Thresholds too aggressive for TF-IDF signal density; calibrated protocol does not improve over frozen v1 |
| 4 | **Dense Embedding Integration Contract v34** | 🧊 **FROZEN** | 4 complementary views with frozen acceptance criteria; validated at 12k/144k where available |
| 5 | **Preparatory 12k Dense Validation** | ✅ **COMPLETE** | Multi-level PASS (4 levels, nesting=1.0, zero fragmentation); Hierarchical builder SUCCESS (39→412); v26 flat Leiden FAIL (expected) |
| 6 | **144k Checkpoint (22/26 years)** | ✅ **VALIDATED** | Hierarchical builder (2-level) scale extrapolation: `fine_branch_purity` ~0.97, `improvement_rate` 0.48–0.65 branch / 0.75–0.76 area, `strict_nesting` ≥0.99, `fine_singletons` ~4–5% |
| 7 | **NESTING_METRIC_DEFECT_v1 Enforcement** | ✅ **ACTIVE** | 7 compressed-family modes had `nesting_score`≥0.99 without scope annotation; `min_cluster_size` enforces nesting=1.0 by construction |

---

## VERIFICATION TEST RESULTS — FULL INDEPENDENT RE-VERIFICATION

| Test Suite | Passed | Skipped | Total |
|------------|--------|---------|-------|
| `test_verify.py` | 185 | 1 | 186 |
| `test_pipeline_readiness.py` | 14 | 0 | 14 |
| `test_zoom_quality_174k_eval.py` | 4 | 0 | 4 |
| `test_zoom_quality_174k_v26_eval.py` | 7 | 0 | 7 |
| `test_dense_embeddings_infrastructure.py` | 14 | 1 | 15 |
| `test_scale_dependency.py` | 11 | 0 | 11 |
| `test_12k_dense_comprehensive.py` | 10 | 0 | 10 |
| **GRAND TOTAL** | **245** | **2** | **247** |

**All 7 test suites PASS.**

---

## TF-IDF PRODUCTION MODES — FROZEN AT 174K

| Mode | Description | Decisions | Fine Branch Purity | Status |
|------|-------------|-----------|-------------------|--------|
| `full_text_tfidf_light` | Full text TF-IDF (light) | 173,963 | 0.906 | ✅ PRODUCTION |
| `regeste_full_text_hybrid_0.5` | Regeste + full text hybrid (w=0.5) | 173,963 | 0.918 | ✅ PRODUCTION |
| `regeste_full_text_hybrid_0.7` | Regeste + full text hybrid (w=0.7) | 173,963 | 0.930 | ✅ PRODUCTION |
| `cited_decisions_tfidf` | Citation-based TF-IDF | 90,721 (52%) | 0.609–0.685 | Production (partial) |
| `outcome_tfidf` | Outcome TF-IDF | — | FAIL | ❌ Expected (weak signal) |
| `regeste_tfidf` | Regeste-only TF-IDF | — | FAIL | ❌ Expected (missing branch labels) |

**16/16 scale simulation tests PASS.** WebGL pipeline <3s at 174k.

---

## DENSE EMBEDDING INTEGRATION CONTRACT v34 — FROZEN

**Primary product mode:** TF-IDF citation hybrids (`jurist_preference` 0.78–0.79) — beats simple semantic baseline (JP 0.43).

**Complementary views (dense embeddings):**

| View | Acceptance Criterion | Evidence (22yr/144k) | Required Dense Modes |
|------|---------------------|----------------------|---------------------|
| **Citation Heritage** | AUC > 0.75 | `center_projected_64dim`: 0.7922; `768dim`: 0.7946 | cp64, cp128, cp768 |
| **Cross-Lingual Sachverhalt** | `cross_lang_same_branch` > 0.20 | cp64: 0.2816; cp768: 0.2816 | cp64, cp768 |
| **Cross-Lingual Dispositiv** | `cross_lang_same_branch` > 0.10 | cp64: 0.1502; cp768: 0.1481 | cp64, cp768 |
| **Cross-Lingual Erwaegungen** | `cross_lang_same_branch` > 0.10 | cp64: 0.0941; cp768: 0.0925 | **FAILED** — excluded |
| **Linear Hybrid Complement** | PASS adversarial gates (w=0.3–0.4) | `cited_decisions_tfidf_plus_dense_w04`: JP 0.6725, LD 0.6539 | cp64, cp128 |

**Infrastructure readiness:** Hierarchical builder ✅, Map mode registry ✅, Zoom neighborhood API ✅, WebGL pipeline ✅, Product integration ✅.

**Blockers (upstream):**
1. Corpus lane: BGE/bger ID mapping production
2. Corpus lane: Parquet generation for 2022–2026 (29,520 decisions missing)
3. Corpus lane: Section extraction at 174k scale
4. Legal-distance lane: 174k dense embeddings (currently 3/26 years, ~19,441 decisions, 11%)

---

## CRITICAL FINDINGS — PRESERVED

1. **TF-IDF hierarchical v1: 6/8 PASS** — Text-based at full 174k achieve 0.906–0.930; citation-based at 52% scale achieve 0.609–0.685.
2. **Multi-level recursive protocol FAILS at 174k** — Valid negative; NOT cluster collapse at all levels; Level 0 single cluster, Levels 1–3 multi-cluster but level2 area_purity threshold fails.
3. **Calibration FAILS on TF-IDF** — Thresholds too aggressive; negative result correctly preserved.
4. **Dense integration contract FROZEN** — 4 complementary views with acceptance thresholds.
5. **Scale extrapolation validated** — 144k checkpoint confirms hierarchical builder (2-level) metrics. **Note:** These describe the hierarchical builder (2-level), NOT the multi-level recursive protocol (which FAILS at 144k).
6. **NESTING_METRIC_DEFECT_v1 ENFORCED** — All `nesting_score`≥0.99 claims require explicit scope annotation.
7. **Blocker is upstream data, not lane defect** — Legal-distance 174k dense embeddings require corpus lane resumption.

---

## STATE FILE — UPDATED FIELDS

```json
{
  "lane": "fractal-map",
  "direction_version": 34,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "FRACTAL_MAP_V34_FINAL_AUDIT_READY_20261007_37578976497",
  "verification_run_id": "fractal_map_v34_final_verification_20261007_37578976497",
  "verification_timestamp": "2026-10-07T09:30:00.000000Z",
  "verification_tests_passed": 245,
  "verification_tests_skipped": 2,
  "github_run": 37578976497,
  "audit_ready": true,
  "audit_timestamp": "2026-10-07T09:30:00.000000Z",
  "final_audit_run_id": "FRACTAL_MAP_V34_FINAL_AUDIT_READY_20261007_37578976497",
  "final_audit_timestamp": "2026-10-07T09:30:00.000000Z",
  "final_audit_report": "reports/fractal_map/FRACTAL_MAP_V34_FINAL_AUDIT_READY_SNAPSHOT_20261007_RUN_37578976497.md",
  "operational_resume_status": "VERIFIED_AND_AUDIT_READY_FINAL_RUN_37578976497"
}
```

---

## NEXT RECOMMENDATION (UNCHANGED)

> TF-IDF hierarchical production modes at 174k are OPERATIONAL and FROZEN (3 production modes at full 173,963 decisions; fine_branch_purity 0.906–0.930). Multi-level recursive protocol (4+ levels) FAILS at 174k for all 5 TF-IDF modes — valid negative result preserved. Calibration FAILS on TF-IDF — negative result correctly preserved. Preparatory 12k dense validation COMPLETE. Dense embedding integration contract v34 DEFINED AND FROZEN (4 complementary views). 144k checkpoint validates hierarchical builder scale extrapolation. NESTING_METRIC_DEFECT_v1 enforced. **No further same-question cycles justified (continue_recommended=false).** Factory Director action required: Resume corpus lane for BGE/bger ID mapping + parquet 2022–2026 + section extraction at 174k scale.

---

## PROVENANCE

- **Producer snapshot:** Run 37576522131
- **Operational resume verification:** GitHub run 37578976497
- **Test execution environment:** Python 3.12.3, pytest 9.1.1, numpy/scipy/scikit-learn/pandas/pyarrow
- **All raw outputs preserved** in `results/fractal_map/`
- **All negative results intact** — no overwriting of claim-bearing outputs

---

**AUDIT STATUS: READY** ✅
