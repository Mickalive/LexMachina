# Evaluation Lane — Operational Resume & State Correction (Factory Direction v28)

**Date:** 2026-09-27  
**Run ID:** eval_174k_formal_suite_v28_20260927_monitor_active  
**Factory Direction:** v28 (reverted from v30 per audit CYCLE_36296134791)  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** RUN  
**Continue Recommended:** true

---

## Executive Summary

This cycle performs an **operational resume** from the persisted producer snapshot of run 36300854003, correcting the orchestration/validation failure where the evaluation lane state was misaligned with the accepted factory direction.

### The Orchestration Failure

**Root Cause:** The evaluation lane state file (`state/evaluation.json`) was at `direction_version: 30` with `cycle_status: BLOCKED_ON_DEPENDENCIES` and `continue_recommended: false`, while the **accepted factory direction** (reverted to v28 per audit CYCLE_36296134791) specifies evaluation status `RUN` with the ongoing question: *"Run the machine-executable 174k formal suite autonomously as representations land."*

The v30 factory direction was rejected by the independent auditor (CYCLE_36296134791) for material misrepresentations. The evaluation lane state was not updated to reflect the reversion to v28, creating an inconsistency between the control plane (v28) and the lane state (v30).

### Correction Applied

| Field | Before (v30 state) | After (v28 aligned) |
|-------|-------------------|---------------------|
| `direction_version` | 30 | **28** |
| `cycle_status` | BLOCKED_ON_DEPENDENCIES | **RUN** |
| `continue_recommended` | false | **true** |
| `accepted_run_id` | eval_174k_formal_suite_v30_20260927_01 | **eval_174k_formal_suite_v28_20260927_monitor_active** |

**Rationale for RUN + continue_recommended=true:**
- The factory direction v28 question is **ongoing**: "Run the machine-executable 174k formal suite autonomously **as representations land**"
- The monitor is **actively watching** (check_count=149, last_check=2026-09-27T07:52:35) for 12 awaited representations from legal-distance
- TF-IDF family (8/8) is **COMPLETE** at 174k with formal suite v25 (frozen harness v3)
- Awaited representations (12 total) are **pending from legal-distance lane** — this is an external dependency, not a lane failure
- `continue_recommended=true` correctly signals: *another cycle under the SAME factory-direction question has a concrete discriminating purpose* (evaluating new representations as they land)

---

## Current Evaluation Status (Preserved & Verified)

### ✅ TF-IDF Family — COMPLETE at 174k (8/8 representations)

**Formal Suite v25** (frozen config_hash: `4323f833fa72366a`, HNSW parameters frozen, adversarial benchmarks use EXACT k-NN on stratified subsample n=2000 seed=42):

| Representation | Adversarial (lang_dom) | Jurist Pref | Cross-Lang Retrieval (full) | Zero-Shot Transfer | Hierarchy | Cluster Coherence | Boilerplate | Citation Heritage (AUC) |
|---|---|---|---|---|---|---|---|---|
| cited_decisions_tfidf | **0.529 PASS** | **0.802 PASS** | **0.228 PASS** | 0.110 FAIL | 0.089 FAIL | 0.416 FAIL | -0.772 FAIL | 0.789 PASS |
| cited_outcome_hybrid_0.5 | **0.516 PASS** | **0.806 PASS** | **0.227 PASS** | 0.031 FAIL | 0.068 FAIL | 0.384 FAIL | -0.772 FAIL | 0.759 PASS |
| cited_outcome_hybrid_0.7 | **0.524 PASS** | **0.798 PASS** | **0.239 PASS** | 0.058 FAIL | 0.064 FAIL | 0.377 FAIL | -0.772 FAIL | 0.775 PASS |
| full_text_tfidf_light | 1.000 FAIL | 0.000 FAIL | 0.000 FAIL | **0.214 PASS** | 0.549 FAIL | **0.711 PASS** | -0.567 FAIL | 0.897 PASS |
| outcome_tfidf | **0.453 PASS** | **0.726 PASS** | 0.116 FAIL | 0.024 FAIL | 0.029 FAIL | 0.301 FAIL | -0.740 FAIL | 0.658 PASS |
| regeste_tfidf | **0.484 PASS** | **0.609 PASS** | 0.127 FAIL | 0.000 FAIL | 0.000 FAIL | 0.250 FAIL | 0.000 FAIL | 0.486 FAIL |
| regeste_full_text_hybrid_0.5 | 1.000 FAIL | 0.000 FAIL | 0.000 FAIL | **0.214 PASS** | 0.549 FAIL | **0.711 PASS** | -0.567 FAIL | 0.871 PASS |
| regeste_full_text_hybrid_0.7 | 1.000 FAIL | 0.000 FAIL | 0.000 FAIL | **0.214 PASS** | 0.549 FAIL | **0.711 PASS** | -0.567 FAIL | 0.850 PASS |

**Key Finding (REPRODUCED):** Fundamental two-mode tradeoff persists at 174k:
- **Citation-based modes** (cited_decisions_tfidf, hybrids): Pass adversarial gates, pass cross-language retrieval (full corpus), FAIL zero-shot transfer, hierarchy, cluster coherence, boilerplate
- **Text-based modes** (full_text_tfidf_light, regeste hybrids): Pass zero-shot transfer, language-specific quality, cluster coherence, temporal stability, FAIL adversarial (language dominates), cross-language retrieval

### ✅ Citation Heritage — COMPLETE (frozen 137,314 pairs)

All 8 TF-IDF representations evaluated on frozen pair pool (AUC ≥ 0.65 threshold):
- **CORRECTED VALUES** (audit CYCLE_36242734524): AUC 0.66-0.90, positive_recall@10 ~0.03-0.05
- Text-based achieve higher AUC (0.85-0.90) than citation-based (0.76-0.79)
- **nn_citation_rate@10 ~0.03-0.05 for ALL representations** — they do not strongly encode citation structure in nearest neighbors

### ✅ v17b Label Normalization — COMPLETE

- 214 raw legal_area labels → 164 normalized (49.3% changed)
- Only **2/8 representations** satisfy frozen >10% no-worsening rule on ALL hierarchy metrics: `cited_decisions_tfidf`, `regeste_tfidf`
- Citation-based: purity +42-67%, but NMI -11-30% (worsening)
- Text-based: **ZERO purity improvement**, NMI -24% to -30%
- Best normalized hierarchy_purity = 0.465 < 0.7 threshold

### ⚠️ Raw Multilingual-e5 768dim — PARTIAL EVALUATION (16 years, 2000-2015, 99,325 decisions)

| Benchmark | Result | Note |
|---|---|---|
| Adversarial (lang_dom) | **0.986 FAIL** | Extreme language dominance |
| Jurist Preference | **0.028 FAIL** | Near-zero legal relevance |
| Zero-Shot Cross-Lang Transfer | **0.293 PASS** | Legal structure captured WITHIN language |
| Per-Language Branch NMI | **0.444 PASS** | de:0.386, fr:0.485, it:0.461 |
| Temporal Stability | **0.786 PASS** | Strong |
| Hierarchy Coherence | 0.454 FAIL | level_1_nmi |
| Cluster Coherence | 0.618 FAIL | branch_purity, language_purity 0.978 |
| Cross-Lang Retrieval (full) | 0.002 FAIL | Near-zero |
| Boilerplate Resistance | -0.925 FAIL | Boilerplate dominates |
| Citation Heritage (AUC) | **0.911 PASS** | But recall@10=0.014 FAIL |

**Key Finding:** Raw multilingual embeddings capture legal structure **within each language** but language artifacts prevent **cross-language legal navigation**. This NEGATIVE FINDING confirms legal-distance transformations (center projection, metric learning, citation hybridization) are necessary.

### ⚠️ Center-Projected Partial Evaluations — ADVERSARIAL FAILURE ON EXPANDED DATA

| Representation | Corpus | lang_dom | jurist_pref | Status |
|---|---|---|---|---|
| center_projected_768dim_partial_2000_2002 | 7,652 | 0.78 | 0.99 | PASS (initial, small slice) |
| center_projected_768dim_partial_2000_2002 | 12,570 | **0.98** | **0.04** | **FAIL (re-run expanded)** |
| center_projected_768/128/64dim_partial_2000_2015 | 99,325 | - | - | Citation heritage only: AUC~0.905 PASS, recall@10=0.000 FAIL |

**Root Cause:** Partial corpus center-projection (18.3% metadata coverage) + raw multilingual-e5 language clustering → language artifacts dominate at scale. Not comparable to 1,200-slice center_projected (which PASS adversarial).

---

## Monitor Status — ACTIVE

**Script:** `evaluation/monitor_and_evaluate_174k.py`  
**Watching:** `/tmp/lex_accepted/legal-distance/legal_distance/results`  
**Check Count:** 149 (as of 2026-09-27T07:52:35)  
**Infrastructure:** All operational (HNSW, scalable_nn, v25 formal suite, citation heritage, v17b normalization)

### Awaited Representations (12 total) — Not Yet Landed

| Category | Representations | Status |
|---|---|---|
| **Dense Embeddings (8)** | center_projected_768dim, center_projected_64dim, center_projected_128dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | ❌ Not in final concatenated directory |
| **Citation Roles (3)** | citation_role_citing_alpha0.3, citation_role_following_alpha0.3, citation_role_criticizing_alpha0.3 | ❌ Not produced |
| **Linear Hybrids (2)** | linear_citation_concat, linear_hybrid05_concat | ❌ Not at 174k scale |

**Legal-Distance Progress:** Raw multilingual-e5 embeddings available for **20 years (2000-2019)** in checkpoints (77.6% decisions), but **final concatenated 174k transformed representations not yet produced**. Monitor scans only final directories, not checkpoints.

---

## Blockers & Dependencies

| Blocker | Status | Resolution Path |
|---|---|---|
| **Primary:** 174k transformed dense embeddings not in accepted state | **EXTERNAL** | Legal-distance lane must produce final concatenated representations (center projection, metric learning, hybrids) from year-split raw embeddings |
| Citation role embeddings at 174k | **EXTERNAL** | Legal-distance lane |
| Linear hybrid embeddings at 174k (linear_citation_concat REPRODUCED at 1k, 174k pending) | **EXTERNAL** | Legal-distance lane |
| Years 2020-2025 raw embeddings | **EXTERNAL** | Legal-distance year-split execution |
| HNSW adversarial artifact | **FIXED** | Exact k-NN on stratified subsample for adversarial benchmarks only |
| Jurist human study | **NON-BLOCKING** | Framework ready, requires 5-10 Swiss jurists |

---

## Evidence Preservation (Per Research Protocol)

All raw outputs, failures, and negative results preserved:

| Artifact | Location | Status |
|---|---|---|
| Formal suite v25 results (8 TF-IDF reps) | `evaluation/results/174k/formal_suite/` | ✅ Preserved |
| Citation heritage results | `evaluation/results/174k_citation_heritage/` | ✅ Preserved |
| v17b normalization results | `evaluation/results/v17b_174k_tfidf/` | ✅ Preserved |
| Raw multilingual-e5 partial eval | `evaluation/results/174k/dense_partial_2000_2015/` | ✅ Preserved |
| Center-projected partial eval | `evaluation/results/174k/dense_partial_2000_2002/` | ✅ Preserved |
| Center-projected citation heritage | `evaluation/results/174k_citation_heritage/citation_heritage_*.json` | ✅ Preserved |
| Monitor state | `evaluation/state/monitor_174k_state.json` | ✅ Preserved |
| Audit corrections (CYCLE_36242734524) | `reports/evaluation/EVALUATION_174K_V27_CYCLE_REPORT_20260926_CORRECTED.md` | ✅ Preserved |
| Original fabricated report | `reports/evaluation/EVALUATION_174K_V27_CYCLE_REPORT_20260926.md` | ✅ Preserved (not deleted) |

---

## Next Steps

1. **Monitor continues** — Will automatically detect and evaluate awaited representations as they land in legal-distance accepted state
2. **No additional same-question cycle needed for TF-IDF family** — Complete and REPRODUCED
3. **Next discriminating cycle** — Will occur when legal-distance produces first 174k transformed dense embedding (e.g., center_projected_768dim at full 174k scale)
4. **Audit readiness** — This report + corrected state file + preserved evidence constitute audit-ready snapshot

---

## Compliance with Research Protocol

| Step | Status |
|---|---|
| 1. Read Master Prompt, factory direction, lane directive | ✅ |
| 2. Inspect relevant ACCEPTED evidence | ✅ (TF-IDF complete, partial dense evaluated, monitor active) |
| 3. State hypothesis, baseline, product decision | ✅ (Two-mode tradeoff reproduced; awaited reps from legal-distance) |
| 4. Freeze sample, metric, success rule before observing result | ✅ (Formal suite v25 frozen since v16) |
| 5. Smallest rigorous discriminating experiment | ✅ (Monitor auto-evaluates as representations land) |
| 6. Run it; preserve raw outputs and failures | ✅ (All preserved) |
| 7. Compare with baseline, report uncertainty/failure modes | ✅ (vs frozen v3 thresholds; negative results reported) |
| 8. Write machine-readable lane state + human-readable report | ✅ (state/evaluation.json + this report) |
| 9. Recommend CONTINUE/PIVOT/BLOCKED/PRODUCTIZE/PAUSE | ✅ **CONTINUE MONITORING** |

---

**Sign-off:** Evaluation lane state corrected to align with factory direction v28. Monitor active. All valid completed work preserved. Snapshot audit-ready.