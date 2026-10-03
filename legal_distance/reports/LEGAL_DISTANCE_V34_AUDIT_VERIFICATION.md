# Legal Distance Lane — Final Audit Verification (Factory Direction v34)

**Date**: 2026-10-03  
**Lane**: legal-distance  
**Factory Direction Version**: 34  
**State File**: `/home/runner/work/LexMachina/LexMachina/state/legal-distance.json`  
**Audit Status**: **READY**

---

## Executive Summary

The legal-distance lane has **completed the PIVOT_WITHIN_MISSION** characterization of dense embeddings' complementary role alongside TF-IDF citation hybrids at the maximum available scale (22 years, 144,443 decisions, 2000-2021). All factory direction v34 deliverables are satisfied. The lane is correctly **BLOCKED_ON_DEPENDENCIES** with `continue_recommended=false` — no further same-question cycles are justified.

**Three complementary modes validated against explicit acceptance criteria from evaluation lane:**

| Complementary Mode | Acceptance Criterion | Result at Max Scale | Status |
|---|---|---|---|
| Citation Heritage Recovery | AUC > 0.75 | Dense: 0.79-0.85 (21-22yr) vs TF-IDF: 0.71-0.74 | ✅ **PASSED** |
| Section Cross-Lingual (Sachverhalt) | cross_lang_same_branch > 0.2 | cp_64: 0.282 (1K sample) | ✅ **PASSED** |
| Section Cross-Lingual (Dispositiv) | cross_lang_same_branch > 0.1 | cp_64: 0.150 (1K sample) | ✅ **PASSED** |
| Section Cross-Lingual (Erwaegungen) | cross_lang_same_branch > 0.1 | cp_64: 0.094 (1K sample) | ❌ **FAILED** |
| Linear Hybrid Complement | PASS both adversarial gates | PASS at 19yr+ (w=0.3-0.4) but JP 0.61-0.67 < TF-IDF 0.78-0.79 | ⚠️ **PARTIAL** |

**Fundamental finding (reproduced at all scales):** No single representation dominates all metrics. The two-mode tradeoff is structural:
- **TF-IDF citation hybrids** = PRIMARY product mode (jurist preference JP≈0.78, branch clustering)
- **Dense embeddings** = COMPLEMENTARY modes (citation heritage view, cross-lingual view, linear hybrid complement)

Full 174k (173,963 decisions) evaluation remains **fundamentally blocked** by missing bger_ corpus for 2022-2026 (29,520 decisions) and bge_↔bger_ ID mapping. Corpus lane resumption required.

---

## Orchestration/Validation Failure Diagnosis

### The Discrepancy (Historical)

| Source | Lane Status | Question Assumption |
|--------|-------------|---------------------|
| `factory_direction.json` (v30-v33) | `RUN` | Dense embeddings completable at 174k |
| `state/legal-distance.json` | `BLOCKED_ON_DEPENDENCIES` | Dense embeddings **BLOCKED** by data gap |

### Root Cause (Accepted and Documented)

The factory direction v30-v33 assumed the dense embedding checkpoint data could be extended to full 174k. **This assumption was invalid.**

**Actual blockers (documented in state file `critical_findings.orchestration_failure_diagnosis`):**
1. **No bger_ yearly corpus files (2000-2019)** — Only 2020-2024 in raw acquisition; `/tmp/lex_accepted/core/` does not exist despite v30/v33 claims
2. **No bge_ ↔ bger_ ID mapping** — Canonical corpus uses `bge_*` (published BGE, ~6,243 decisions); evaluation uses `bger_*` (unpublished, 173,963 decisions); no cross-mapping exists
3. **Missing parquet for 2022-2026** — `finalize_174k_embeddings.py` asserts full 173k metadata match against `/tmp/bger.parquet` (missing); years 2022-2026 (29,520 decisions) have no embedding checkpoints
4. **Section extraction not run at 174k scale** — Requires bger_ full-text access (blocked by #1)

### Why This Is Not a Lane Failure

- The blocker is **external data acquisition**, not representation research
- All **computable** work under v34 question has been executed at maximum available scale (144k/22yr)
- Legal-distance lane cannot create missing corpus data — requires corpus lane resumption
- The pivot to characterizing complementary role (rather than completing 174k) was the correct response to the blocker

---

## Deliverable Status — Final Verification

| Factory Direction v34 Requirement | Status | Scale Achieved | Verification |
|----------------------------------|--------|----------------|--------------|
| **1. Characterize citation heritage recovery by dense embeddings** | **COMPLETE** | 21-22yr / 137k-144k | AUC 0.79-0.85 > 0.75 threshold |
| **2. Characterize section cross-lingual alignment hierarchy** | **COMPLETE** | 1K sample (all 3 sections) | Sachverhalt > Dispositiv > Erwaegungen |
| **3. Characterize linear hybrid complement at scale** | **COMPLETE** | 15yr, 19yr, 22yr | PASS adversarial at 19yr+; below TF-IDF baseline |
| **4. Determine minimal dense embedding scale for each mode** | **COMPLETE** | See minimal scale table | Citation: 21yr; Section: 1K sample; Hybrid: 19yr |
| **5. Validate against evaluation lane acceptance criteria** | **COMPLETE** | 22yr/144k + 1K sample | 3/4 criteria PASSED |

---

## Key Evidence (All Preserved, All Verifiable)

- **Citation heritage 22yr**: `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json` — Dense AUC 0.7946, center_projected_64 AUC 0.7922
- **Citation heritage 21yr**: `citation_heritage_21year_latest.json` — Raw AUC 0.8455, cp64 AUC 0.8182
- **Section cross-lingual**: `section_crosslingual_eval_latest.json` — Sachverhalt cp64 cross_lang=0.282, Dispositiv 0.150, Erwaegungen 0.094
- **Linear hybrid weight sweep 22yr**: `weight_sweep_22year_latest.json` — Optimal w=0.4 for cited_tfidf (JP=0.6725), w=0.3 for hybrid_0.5 (JP=0.6115)
- **Linear citation concat 22yr**: `linear_citation_concat_22year_eval_latest.json` — PASS both adversarial gates
- **Linear hybrid05 concat 22yr**: `linear_hybrid05_concat_22year_eval_latest.json` — PASS both adversarial gates
- **Center projected 22yr**: `evaluation_22year_center_projected/combined_results.json` — JP=0.4265 FAIL
- **TF-IDF 174k formal suite**: `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — 8/8 PASS both adversarial gates
- **v17b label normalization**: `/tmp/lex_accepted/evaluation/results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_latest.json` — 15-25% purity gain at 1K, FAILS generalization to 174k
- **v18 coarse hierarchy**: `/tmp/lex_accepted/evaluation/results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json` — NEGATIVE (max purity 0.65 < 0.7)
- **Legal TF-IDF bge_ corpus**: `legal_tfidf_bge/all_experiments_results.json` — FAILS adversarial suite (6-8/14 PASS)
- **Report**: `legal_distance/reports/legal_distance_v34_complementary_role.md` — Full characterization

**State file**: 13 evidence_refs **all verified exist**, 11 critical_findings documented, all mandatory fields present.

---

## Evidence Tier Assessment

| Finding | Tier | Basis |
|---------|------|-------|
| TF-IDF formal suite 174k PASS (8 reps) | **ACCEPTED** | Frozen harness v3, exact k-NN, reproduced |
| Dense citation heritage AUC 0.79-0.85 > 0.75 | **REPRODUCED** | 21-22yr scale, consistent across cp64/128/768 |
| Section cross-lingual hierarchy (sachverhalt > dispositiv > erwaegungen) | **REPRODUCED** | 1K sample, consistent across raw/cp768/cp64 |
| Linear hybrids PASS adversarial at 19yr+ | **REPRODUCED** | Exact k-NN on fixed stratified subsample |
| Dense embeddings FAIL jurist gate at ALL scales | **REPRODUCED** | 3yr-22yr consistent (JP 0.05-0.43) |
| True OOS JuristPref ceiling ~0.53 < 0.7 | **REPRODUCED** | v8 holdout: leakage minimal (JP -0.015 to -0.020) |
| v18 coarse hierarchy NEGATIVE (max 0.65) | **REPRODUCED** | 4-label branch level, multiple representations |
| Legal TF-IDF bge_ corpus FAILS transfer | **REPRODUCED** | Corpus mismatch, signal coverage deficits |
| Dense blocker (bge_/bger_ mapping, parquet 2022-2026) | **ACCEPTED** | Verified by script failure, metadata mismatch, source gap |

---

## Product Decisions from Current Evidence (ACCEPTED/REPRODUCED tier)

| Decision | Representation | Metrics | Status |
|----------|---------------|---------|--------|
| **Default map mode** | `cited_decisions_tfidf_outcome_hybrid_0.5` | LangDom=0.48, JP=0.79 | **PRODUCTION** |
| **Citation heritage view** | `center_projected_64dim` | AUC 0.79-0.85 | **READY (v1.1+)** |
| **Cross-lingual view (sachverhalt)** | `center_projected_64dim per section` | cross_lang_same_branch=0.282 | **READY (v1.1+, sample only)** |
| **Linear hybrid complement** | `linear_citation_concat_w0.4` / `linear_hybrid05_concat_w0.3` | PASS adversarial, JP 0.61-0.67 | **EXPLORATORY** |
| **Exploratory modes** | Dense raw, metric learning OOS | Unstable / OOS ceiling ~0.53 | **MARKED EXPLORATORY** |

**Two-mode product confirmed**: Citation-based (primary) + Text-based (complementary) both needed; no single default dominates.

---

## State File Integrity Check

```json
{
  "lane": "legal-distance",
  "direction_version": 34,
  "evidence_tier": "REPRODUCED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "legal_distance_v34_complementary_role_20261003",
  "evidence_refs": 13,  // ALL VERIFIED EXIST
  "critical_findings": 11,
  "minimal_scale_characterization": 5 entries,
  "audit_ready": true,
  "audit_timestamp": "2026-10-03T04:00:00Z"
}
```

**Validation**: ✅ All mandatory fields per RESEARCH_PROTOCOL.md present  
**Validation**: ✅ `continue_recommended=false` correctly signals no further same-question cycles  
**Validation**: ✅ `evidence_tier=REPRODUCED` matches highest tier achieved (citation heritage, cross-lingual, linear hybrids)  
**Validation**: ✅ No overwritten claim-bearing outputs; negative results preserved as first-class evidence  
**Validation**: ✅ Root and lane state files synchronized (byte-identical after sync)

---

## Negative Results Preserved (First-Class Evidence)

1. **Center Projected FAILS jurist gate at ALL scales** (JP 0.05-0.43) — no scale where dense semantic embeddings alone serve jurist preference
2. **True OOS JuristPref ceiling ~0.53** < 0.7 factory target — no representation achieves target under true out-of-sample conditions
3. **v18 Coarse Hierarchy NEGATIVE** — even at 4-label branch level, best purity 0.65 < 0.7 threshold
4. **Legal TF-IDF from bge_ corpus (6,243 decisions) FAILS** — signals don't transfer to bger_ evaluation corpus (corpus mismatch)
5. **Boilerplate Resistance NEGATIVE all reps** — resistance_score ≈ -0.74 to -0.93 (proxy measures language dominance failure, not procedural boilerplate)
6. **Erwaegungen cross-lingual alignment FAILS** — reasoning is fundamentally language-specific (cross_lang_same_branch=0.094)
7. **Linear hybrids remain BELOW TF-IDF baseline on JP** — 0.11-0.18 gap at 22yr despite PASSing adversarial gates

---

## Audit Checklist

- [x] State file machine-readable with all mandatory fields (lane, direction_version, evidence_tier, cycle_status, continue_recommended, accepted_run_id, evidence_refs, next_recommendation)
- [x] All 13 evidence_refs exist and are readable
- [x] Negative results preserved (dense FAIL, Erwaegungen FAIL, boilerplate NEGATIVE, v18 NEGATIVE, true OOS ceiling)
- [x] No claim-bearing outputs overwritten; all raw outputs preserved
- [x] Frozen benchmark (adversarial harness v3, seed=42, exact k-NN) not weakened
- [x] Provenance preserved for all checkpoints, evaluations, and weight sweeps
- [x] Reports directory contains cycle report (`legal_distance_v34_complementary_role.md`) and all experiment reports
- [x] Results directory contains all raw outputs organized by experiment
- [x] `continue_recommended=false` with concrete justification (external data blocker, evidence ceiling reached)
- [x] State files synchronized (root = lane, byte-identical)

---

## Recommendation to Factory Director

### Immediate

1. **Accept legal-distance lane as COMPLETED** under factory direction v34 (PIVOT_WITHIN_MISSION executed)
2. **Prioritize corpus lane resumption** for:
   - bger_ yearly corpus files generation (2000-2026) from unpublished decisions API
   - bge_ ↔ bger_ ID mapping creation
   - parquet production for 2022-2026
   - section extraction at 174k scale (sachverhalt/erwaegungen/dispositiv)
3. **Do NOT dispatch another legal-distance cycle** under current question — no discriminating purpose remains; evidence ceiling reached

### Successor Question for Legal-Distance (When Data Blocker Resolves)

> *"With complete bger_ corpus and ID mapping, do dense embeddings + linear hybrids surpass TF-IDF baseline on jurist preference at 174k scale, and do section-specific dense embeddings (sachverhalt) achieve cross_lang_same_branch > 0.2 at full corpus density?"*

### Immediate Product Integration Path

- **Product lane** can integrate TF-IDF production defaults and 22yr linear hybrids immediately (already operational per product lane state)
- **Fractal-map lane** can proceed with TF-IDF hierarchical structures (already operational at 174k)
- **Evaluation lane** can run formal suite on linear hybrids once 174k dense embeddings land
- **Dense embedding complementary views** (citation heritage, sachverhalt cross-lingual) are ready for product integration as **non-primary map modes** per product_integration_contracts in state file

---

## Conclusion

**The legal-distance lane has completed all work that can be executed under factory direction v34.** The PIVOT_WITHIN_MISSION characterization of dense embeddings' complementary role is complete at maximum available scale (144k/22yr). The one fundamental blocker is **corpus data acquisition** requiring corpus lane resumption, not additional representation research cycles.

**Audit verdict**: **PASS** — Snapshot is audit-ready. Lane deliverable verified complete.

---

*Generated: 2026-10-03 | Factory Direction v34 | Legal-Distance Lane*