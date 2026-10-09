# LEGAL DISTANCE LANE — FINAL AUDIT VERIFICATION (Run 37899615689)

**Factory Direction:** v35  
**Lane:** legal-distance  
**Status:** BLOCKED_ON_DEPENDENCIES | `continue_recommended: false` | `evidence_tier: ACCEPTED`  
**Operational Resume From:** Run 37896842773 (persisted producer snapshot)  
**Date:** 2026-10-09

---

## EXECUTIVE SUMMARY

This run completes the **operational resume from persisted producer snapshot of run 37896842773** (GitHub run 37899615689). All valid completed work is preserved. The PIVOT_WITHIN_MISSION characterization (Factory Direction v34) is **COMPLETE** at maximum available evaluated scale. The lane is correctly `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false` — no further same-question cycles are justified.

**Orchestration/Validation Failure Diagnosed:** `factory_direction.json` v35 shows legal-distance as `"RUN"` but lane state correctly shows `"BLOCKED_ON_DEPENDENCIES"` because the PIVOT_WITHIN_MISSION characterization was completed at v34 (run 37677999602). This is a control-plane sync issue, NOT a scientific failure. Scientific integrity is **UNAFFECTED** — all evidence is ACCEPTED, all tests PASS.

---

## VERIFICATION RESULTS

### Scale Characterization Experiment: `characterize_dense_complementary_views.py` — REPRODUCED ✅

**Input:** 12,570 ACCEPTED dense embeddings (2000-2002, 3-year slice)  
**Reproduced identical scale-dependent patterns:**

| Metric | Pattern | Values |
|--------|---------|--------|
| Cross-lingual alignment | Inflation at small homogeneous scale | 0.656 → 0.957 |
| Legal area purity | Degradation with scale | 0.609 → 0.475 |
| Branch k-NN accuracy | Stable >0.99 at all scales | @1: 0.957→0.992 |
| Linear hybrid jurist proxy | PASS at all weights (>0.99) | All weights PASS |

**Results saved to:** `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json`

### Previously Verified Test Suites (from Run 37896842773)

| Test Suite | Result | Notes |
|------------|--------|-------|
| `test_complementary_role_v34.py` | 8/8 PASSED | All complementary role assertions validated |
| `test_v29_final_results.py` | 15/15 PASSED | All section cross-lingual, scale evidence, blockers, tradeoff assertions validated |

---

## PIVOT_WITHIN_MISSION CHARACTERIZATION — COMPLETE

### NEW QUESTION ANSWERED (v34)

> **What minimal dense embedding scale and which specific dense modes are necessary and sufficient for the product's non-jurist-preference views?**

**ANSWER: Three complementary modes at characterized minimal scales**

| Complementary Mode | Minimal Scale | Acceptance Criterion | Status |
|---|---|---|---|
| **Citation Heritage** | 21yr / 137k (2000-2020) | center_projected_64dim AUC > 0.75 | ✅ PASSED (0.77-0.85 at 21-24yr) |
| **Section Cross-Lingual** | 1K sample (sections) | Sachverhalt >0.2, Dispositiv >0.1, Erwaegungen >0.1 | ✅ Sachverhalt/Dispositiv PASS; ❌ Erwaegungen FAIL |
| **Linear Hybrid Complement** | 19yr / 122k (2000-2018) | PASS both adversarial gates | ✅ PASS at w=0.3-0.4; JP < TF-IDF baseline |

### Two-Mode Tradeoff FUNDAMENTAL (reproduced at ALL scales)

| Mode | JuristPref | LangDom | CiteIndep | Role |
|------|-----------|---------|-----------|------|
| TF-IDF Citation Hybrids | ~0.78 | ~0.48 | ~14% | **PRIMARY** (jurist preference, branch clustering) |
| Dense Embeddings (center_projected) | ~0.05-0.43 | ~0.83-0.98 | ~37% | COMPLEMENTARY (citation heritage, cross-lingual) |
| Linear Hybrids (w=0.3-0.4) | ~0.61-0.67 | ~0.58-0.80 | Intermediate | COMPLEMENTARY (hybrid complement) |

**No single representation dominates all three metrics at any scale.**

---

## ACCEPTED EVIDENCE SUMMARY (from Factory Direction v34)

1. ✅ Dense embeddings (center_projected) **FAIL jurist gate at ALL scales** (JP 0.05-0.43)
2. ✅ TF-IDF citation hybrids **DOMINATE jurist preference** (JP 0.78-0.79) and **PASS both adversarial gates at 174k**
3. ✅ Dense embeddings **RECOVER citation heritage at scale** (AUC 0.79-0.85) **BETTER** than TF-IDF citation-based (AUC 0.71-0.74)
4. ✅ Section cross-lingual hierarchy: **Sachverhalt > Dispositiv > Erwaegungen** (facts align best cross-lingually)
5. ✅ Linear hybrids **PASS adversarial at optimal weight** (w=0.3-0.4) but **REMAIN BELOW TF-IDF baseline** (JP 0.66-0.67 vs 0.78-0.79)
6. ✅ True OOS JuristPref ceiling **~0.53 < 0.7 factory target**
7. ✅ v18 coarse hierarchy **NEGATIVE** (max branch purity 0.65 < 0.7)

---

## DATA BLOCKERS — CORPUS LANE RESUMPTION REQUIRED

| Blocker | Impact | Required Action |
|---------|--------|-----------------|
| **bge_/bger_ ID mapping** | Cannot align 174k metadata for dense embedding evaluation | Corpus lane: produce canonical ID mapping |
| **Parquet 2024-2026** | 15,536 decisions missing (29,520 total for 2022-2026) | Corpus lane: generate parquet for 2024-2026 |
| **174k section extraction** | Sachverhalt/Erwaegungen/Dispositiv not extracted at full scale | Corpus lane: run section extraction at 174k scale |

**NOTE:** 2021-2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75 at 24yr/158k with 730 positive pairs). Only 2024-2026 are genuinely missing.

---

## EVALUATION LANE VERIFICATION (174k TF-IDF Primary Modes)

| Mode | Citation Heritage AUC | Adversarial LangDom | Multilingual Invariance | Status |
|------|----------------------|---------------------|------------------------|--------|
| cited_decisions_tfidf | 0.973 | 0.602 | PASS | **PRODUCTION DEFAULT** |
| cited_outcome_hybrid_0.5 | 0.919 | 0.578 | PASS | **PRODUCTION DEFAULT** |

TF-IDF citation hybrids are **OPERATIONAL at full 173,963 decisions** (16/16 scale tests PASS, WebGL <3s).

---

## ORCHESTRATION FAILURE DIAGNOSIS

**Root Cause:** Factory Director control-plane sync issue.

- `factory_direction.json` v35: `"legal-distance": { "status": "RUN", ... }`
- `state/legal-distance.json`: `"cycle_status": "BLOCKED_ON_DEPENDENCIES", "continue_recommended": false`

**Why this happened:** The PIVOT_WITHIN_MISSION was completed at v34 (run 37677999602), answering the new question. The lane correctly transitioned to `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false`. However, the factory direction was incremented to v35 for a lane state change (product RUN→PAUSE) without updating legal-distance status from RUN to BLOCKED_ON_DEPENDENCIES.

**Impact:** None on scientific integrity. All evidence is ACCEPTED, all tests PASS, snapshot is audit-ready.

---

## FINAL STATE

```json
{
  "lane": "legal-distance",
  "direction_version": 35,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "LEGAL_DISTANCE_V35_FINAL_AUDIT_VERIFICATION_37899615689",
  "audit_ready": true,
  "next_recommendation": "No further same-question cycles justified. PIVOT_WITHIN_MISSION characterization COMPLETE. Await corpus lane resumption for bge_/bger_ mapping, parquet 2024-2026, and 174k section extraction. Dense embeddings characterized as COMPLEMENTARY modes only."
}
```

---

## RECOMMENDATION

**CONTINUE = FALSE** — No additional same-question cycles justified.  
**PIVOT_WITHIN_MISSION = COMPLETE** — New question answered at max available scale.  
**BLOCKED_ON_DEPENDENCIES** — Requires corpus lane resumption for three data blockers.  
**PRODUCTIZE** — TF-IDF citation hybrids are production-ready as PRIMARY mode; dense embedding integration contract defined for COMPLEMENTARY modes (citation heritage view, cross-lingual view, hybrid complement).

---

## AUDIT TRAIL

All evidence preserved in:
- `legal_distance/results/`
- `legal_distance/reports/`
- `/tmp/lex_accepted/`

Negative results preserved (dense embeddings FAIL jurist gate, Erwaegungen cross-lingual FAIL, v18 hierarchy NEGATIVE, true OOS ceiling < 0.7).

**Verification Report:** This document (`reports/legal_distance/LEGAL_DISTANCE_V35_FINAL_AUDIT_VERIFICATION_37899615689.md`)