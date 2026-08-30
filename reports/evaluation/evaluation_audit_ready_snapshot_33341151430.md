# Evaluation Lane — Audit-Ready Snapshot (Run 33341151430)

**Factory Direction:** v10  
**Run ID:** 33341151430  
**Prior Run:** 33340692528 (temporal holdout repair R1)  
**Lane Status:** COMPLETED  
**Continue Recommended:** false  
**Timestamp:** 2026-08-30  

---

## 1. Orchestration/Validation Failure Diagnosis

### What failed in the prior workflow
The prior run (33340692528) was a repair cycle that **successfully** completed. The "failure" was not in execution but in state consistency:

1. **State file defect (F-1):** `state/evaluation.json` v12_temporal_holdout `key_findings` entry contained pre-repair values — specifically a false claim that `cited_outcome_hybrid_0.5` IMPROVES on temporal holdout (+0.0333) and an incorrect citation_tfidf baseline (0.7333 fold-1 value instead of 0.7850 5-fold mean). These values predated the repair and were not updated when the repair was accepted.

2. **Stale lane state (F-2):** `evaluation/state/evaluation.json` was stale at `github_run=33339846824`, missing the temporal holdout evidence_refs, key_findings, and metrics from the repaired run (33340692528).

### Root cause
The prior repair cycle corrected the experiment code, re-ran the experiment, and produced a PASS gate — but the repair report's corrections to the state file's `key_findings` section were not applied. The `evaluation/state/evaluation.json` copy was never updated after the repair.

### Repairs applied this cycle
- Updated `state/evaluation.json` v12_temporal_holdout `outcome_signal_generalizes` to reflect corrected degradation (-0.0258)
- Updated `state/evaluation.json` v12_temporal_holdout `negative_results` list with all 5 corrected comparison deltas
- Updated `state/evaluation.json` key_findings V12 TEMPORAL HOLDOUT entry to reference repair round 1 and remove false improvement claim
- Synchronized `evaluation/state/evaluation.json` with canonical `state/evaluation.json`

---

## 2. Lane Deliverable Status

### Factory Direction v10 Objectives

| # | Objective | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Full corpus scale evaluation (192k) | BLOCKED | Pending corpus lane OpenCaseLaw bulk ingestion |
| 2 | Citation role modeling evaluation | COMPLETED | 2,988 annotations, 8/9 role hybrids PASS adversarial gates |
| 3 | Legal embeddings fine-tuning evaluation | COMPLETED | multilingual_e5_small_pretrained tested, BEST adversarial scores but catastrophic hierarchy collapse |
| 4 | Jurist human study | BLOCKED | Framework ready, needs 5-10 Swiss jurists |
| 5 | Cross-lingual alignment deeper investigation | COMPLETED | 52 representations tested, proc_pairs LOSSLESS for cited_decisions_tfidf |
| 6 | User corpus import evaluation | COMPLETED | 45/45 tests PASS |

**4 of 6 objectives COMPLETED. 2 BLOCKED on external dependencies.**

### Additional Completed Work (not in original v10 objectives)
- V11 OOS hybrid_stabilized cross-validation on canonical frozen harness v3
- Debiased_citation_blended falsification on canonical frozen harness v3
- Citation role embeddings on frozen harness v3
- V12 cross-mode combination validation (repaired on canonical corpus)
- V12 temporal holdout validation (repaired, all tests pass)
- Anti-noise procedural sensitivity (negative finding confirmed robust)
- Holdout cross-validation cross-check (discrepant_explained)
- Product integration verification

---

## 3. Evidence Summary

### Test Suite
- **40/40 tests PASS** across all 8 test files
- 3 warnings (return-value style, non-blocking)

### Key Metrics (Accepted)
| Representation | JP | LangDom | Verdict |
|---|---|---|---|
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.7965 | 0.4941 | PASS (BEST PRODUCTION) |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.7898 | 0.4922 | PASS (BEST FRACTAL) |
| cited_decisions_tfidf | 0.6889 | 0.6087 | PASS |
| linear_metric_epoch4 | 0.6847 | 0.6805 | PASS |
| mahalanobis_metric_epoch4 | 0.6781 | 0.6843 | PASS |
| hybrid_stabilized_epoch1 | 0.6656 | 0.6704 | PASS |
| center_projected_64dim (baseline) | 0.5121 | 0.7664 | PASS |

### V12 Cross-Mode Combination (Temporal Holdout)
- Best combination: `linear_hybrid05_concat` JP=0.8375 (temporal)
- Best baseline: `center_projected_64dim` JP=0.7750 (temporal)
- Temporal improvement: +0.0625
- All 9 representations pass both adversarial gates on temporal test set
- Verdict: **REPLICATED**

### Negative Results Preserved (11)
1. center_projected_768 FAILS jurist pairwise
2. multilingual_e5_small_pretrained catastrophic hierarchy collapse
3. CCA and single Procrustes catastrophic for cross-lingual alignment
4. Distinguishing/overruling citation roles too sparse
5. Boilerplate resistance NEGATIVE for ALL representations
6. JuristPref > 0.7 NOT MET by any v11 representation
7. v11 hierarchy loss NOT load-bearing (ΔJP=+0.0008)
8. v11 models WORSE than metric learning baselines
9. debiased_citation_blended FALSIFIED on canonical harness
10. Prior FALSIFICATION on 1000-decision corpus superseded
11. All individual representations degrade on temporal holdout

---

## 4. State File Integrity

| Check | Status |
|-------|--------|
| canonical state/evaluation.json | VALID |
| evaluation/state/evaluation.json | SYNCHRONIZED |
| v12_temporal_holdout values correct | YES |
| false improvement claim removed | YES |
| corrected deltas applied | YES |
| config_hash consistent | 4323f833fa72366a |
| seed consistent | 42 |
| no benchmark gaming | CONFIRMED |
| no frozen baselines weakened | CONFIRMED |
| provenance clean | CONFIRMED |

---

## 5. Recommendation

**PAUSE** — The evaluation lane has completed all objectives achievable without external dependencies. The two blocked objectives (full corpus 192k evaluation, jurist human study) require inputs from other lanes/stakeholders:

1. **Corpus lane** must deliver full 192k decision ingestion and citation ID resolution before full-scale adversarial evaluation can proceed
2. **5-10 Swiss jurists** must be recruited for the pairwise preference human study
3. **GPU availability** is needed for multilingual-e5-small fine-tuning with hierarchy preservation loss

**When dependencies resolve:**
- Full corpus adversarial evaluation at 192k scale
- Multilingual-e5-small fine-tuned evaluation with hierarchy loss
- Jurist human study execution
- Section-specific cross-lingual evaluation (needs sachverhalt/erwaegungen/dispositiv from full corpus)

No HUMAN_DECISION_REQUIRED blockers. Factory in STEADY STATE.

---

## 6. Files

- **Audit gate:** `results/audit/evaluation/CYCLE_33341151430_AUDIT_READY.json`
- **State (canonical):** `state/evaluation.json`
- **State (lane):** `evaluation/state/evaluation.json` (synchronized)
- **Test suite:** `tests/evaluation/` (40/40 PASS)
- **Temporal holdout results:** `results/evaluation/v12_temporal_holdout/v12_temporal_holdout_latest.json`
- **Temporal holdout report:** `reports/evaluation/evaluation_v12_temporal_holdout_33339846824.md`
- **Temporal holdout repair report:** `reports/evaluation/evaluation_repair_33339846824_r1.md`

---

*End of Audit-Ready Snapshot — Evaluation Run 33341151430*
