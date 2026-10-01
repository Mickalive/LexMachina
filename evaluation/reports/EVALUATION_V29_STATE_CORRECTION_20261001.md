# Evaluation Lane — State Correction v29

**Lane:** evaluation  
**Factory Direction:** v29  
**Date:** 2026-10-01  
**Run ID:** `eval_174k_state_correction_20261001`

---

## Issue Identified

The evaluation lane state file (`state/evaluation.json`) was incorrectly set to:
- `cycle_status: "COMPLETED"`
- `continue_recommended: false`
- `next_recommendation: "PIVOT_WITHIN_MISSION"` / "No further same-question cycles justified"

**This contradicts:**
1. **Factory Direction v29** — Explicitly lists evaluation lane status as `"RUN"` with priority 1
2. **Factory Direction Question** — *"Run the machine-executable 174k formal suite autonomously **as representations land**"* — the lane must remain active
3. **Audit-Ready Snapshot v29** — Documents the same error and required correction

---

## Root Cause

The TF-IDF family evaluation (8 representations) is **complete** at 174k scale. The state machine conflated "TF-IDF portion complete" with "lane question complete." The factory direction question spans **all representations as they land from legal-distance**, not just TF-IDF.

---

## Corrected State

| Field | Before (Incorrect) | After (Corrected) |
|-------|---|---|
| `cycle_status` | `"COMPLETED"` | `"RUN"` |
| `continue_recommended` | `false` | `true` |
| `next_recommendation` | `"PIVOT_WITHIN_MISSION"` | `"CONTINUE"` |

---

## Current Deliverable Status (v29)

| # | Deliverable | Status | Notes |
|---|---|---|---|
| 1 | Full 12-benchmark formal suite at 174k on all production representations | **COMPLETE for TF-IDF** | 8/8 PASS adversarial gates; dense embeddings awaited |
| 2 | Validate citation_heritage using 174k citation-ID resolution | **COMPLETE** | 4/8 TF-IDF PASS (citation-based); text-based FAIL |
| 3 | Test v17b label normalization generalization to 174k | **COMPLETE (NEGATIVE)** | Different regime at 174k (213→111 labels vs 104→54 at 1k) |

**Awaiting from legal-distance:**
- 174k dense embeddings (3/26 years ACCEPTED, 15/26 checkpointed PENDING AUDIT, fundamental ID mismatch blocker)
- Citation-role specific embeddings (citing/following/criticizing)
- Linear hybrid families (linear_citation_concat, linear_hybrid05_concat)
- Metric learning results

---

## Evidence Preserved (No Data Loss)

All completed work remains intact:
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — 8 TF-IDF reps × 12 benchmarks
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json` — Citation heritage results
- `evaluation/results/v17b_174k_generalization/v17b_174k_generalization_20260930_011927.json` — Generalization test
- Dense 3yr and 15yr partial evaluations preserved in `evaluation/results/174k/`

---

## Next Evaluation Cycle Trigger

Resume evaluation when **any** new representations land in accepted state from legal-distance:
1. 174k dense embeddings (full corpus, not partial)
2. Citation-role specific embeddings at 174k
3. Linear hybrid families at 174k
4. Any new representation family from frontier teams

---

## Audit Readiness Checklist

- [x] State file corrected to align with factory direction v29
- [x] `cycle_status: "RUN"` (matches factory direction)
- [x] `continue_recommended: true` (aligned with "as representations land")
- [x] `next_recommendation: "CONTINUE"` (not PIVOT)
- [x] All raw outputs preserved (no overwrites)
- [x] Config hash frozen (`b51701f5a9c11692`)
- [x] Global seed fixed (42)
- [x] Negative results retained and documented
- [x] Evidence references in state.json match actual files
- [x] Blocker dependencies explicitly listed with lane ownership

---

## Provenance

- **Factory Direction:** v29 (material correction from v28: corrected checkpoint progress from 25/26 to 15/26 years)
- **Evaluation Harness:** Frozen v3 with HNSW artifact fix (exact k-NN on stratified n=2000)
- **Adversarial Thresholds:** LangDom < 0.85, JuristPairwise > 0.5 (frozen since direction v6)
- **Corpus:** 173,963 decisions from canonical yearly files (2000-2026)
- **Previous Audit-Ready Snapshot:** `EVALUATION_AUDIT_READY_SNAPSHOT_v29_20261001.md` (documents same correction)

---

**Signed:** Evaluation Lane — State Correction  
**Evidence Tier:** REPRODUCED (formal suite), REPRODUCED (state correction verified against factory direction)  
**Audit Ready:** **YES** — state.json now accurately reflects RUN status per factory direction v29