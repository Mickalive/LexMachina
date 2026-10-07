# Evaluation Cycle v45 Report: Factory Direction v35 State Confirmation

**Cycle ID:** 37663031169  
**Date:** 2026-10-07  
**Lane:** evaluation  
**Factory Direction:** v35  
**Status:** CONFIRMED — TF-IDF 174k baseline FROZEN, dense criteria DEFINED/UNVALIDATED, lane COMPLETE (continue_recommended=false)

---

## Executive Summary

This cycle confirms the evaluation lane state aligns with Factory Direction v35. The lane question has been **fully answered**:

1. **TF-IDF 174k evaluation FROZEN as production baseline** — COMPLETE (8/8 representations evaluated at full 173,963 decisions, all PASS both adversarial gates, best `cited_decisions_tfidf_outcome_hybrid_0.5` JP=0.7345 vs semantic baseline 0.43)

2. **Dense embedding complementary view acceptance criteria DEFINED and FROZEN** — COMPLETE (citation heritage AUC > 0.75, cross_lang_sachverhalt > 0.2, cross_lang_dispositiv > 0.1, cross_lang_erwaegungen > 0.05)

3. **Validation of dense criteria at 174k scale BLOCKED** — on corpus lane deliveries (bge_/bger_ ID mapping, parquet 2024-2026, section extraction at 174k)

**No further same-question cycles justified.** `continue_recommended = false`. Next evaluation cycle triggers ONLY when legal-distance delivers concatenated 174k dense embeddings for validation against frozen criteria.

---

## Current State Verification

### TF-IDF 174k Production Baseline (ACCEPTED, FROZEN)

| Representation | Language Dominance | Jurist Pairwise | Both Gates |
|----------------|-------------------|-----------------|------------|
| cited_decisions_tfidf | 0.479 PASS (<0.85) | 0.714 PASS (>0.5) | ✅ |
| outcome_tfidf | 0.502 PASS | 0.655 PASS | ✅ |
| regeste_tfidf | 0.485 PASS | 0.632 PASS | ✅ |
| full_text_tfidf_light | 0.485 PASS | 0.708 PASS | ✅ |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.477 PASS | **0.7345 PASS** | ✅ **BEST** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.478 PASS | 0.7275 PASS | ✅ |
| regeste_full_text_hybrid_0.5 | 0.480 PASS | 0.720 PASS | ✅ |
| regeste_full_text_hybrid_0.7 | 0.482 PASS | 0.715 PASS | ✅ |

**Production default:** `cited_decisions_tfidf_outcome_hybrid_0.5` — beats simple semantic-map baseline (center_projected JP=0.43) by +0.30 JP margin.

**Evidence:** `results/evaluation/tfidf_174k_formal_suite_baseline.json`, `results/evaluation/tfidf_174k_adversarial_gates_formal_suite_latest.json`

---

### Dense Embedding Complementary Criteria (DEFINED, FROZEN, UNVALIDATED at 174k)

| View | Metric | Threshold | Current Evidence | Status |
|------|--------|-----------|------------------|--------|
| Citation Heritage | AUC (frozen 137k pair pool) | > 0.75 | **Partial 24yr/158k: 0.792 [0.762,0.824] PASS**<br>Full 174k: AUC 0.482 FAIL (cited_outcome_hybrid_0.5) | CRITERION_FROZEN<br>VALIDATION_BLOCKED |
| Cross-Lingual (Sachverhalt) | cross_lang_same_branch_mean | > 0.2 | **Partial n=359: 0.282 [0.267,0.296] PASS**<br>Full-doc 174k: 0.0 FAIL | CRITERION_FROZEN<br>VALIDATION_BLOCKED |
| Cross-Lingual (Dispositiv) | cross_lang_same_branch_mean | > 0.1 | **Partial n=538: 0.150 [0.141,0.160] PASS**<br>Full-doc 174k: 0.0 FAIL | CRITERION_FROZEN<br>VALIDATION_BLOCKED |
| Cross-Lingual (Erwaegungen) | cross_lang_same_branch_mean | > 0.05 | Partial n=510: 0.094 [0.086,0.102] PASS<br>Full-doc 174k: 0.0 FAIL | CRITERION_FROZEN<br>VALIDATION_BLOCKED |
| Linear Hybrid Complement | jurist_pairwise_preference (w=0.3-0.4) | > 0.60 | Obsolete v6-v10 embeddings: 0.66-0.68<br>Target 174k embeddings: NOT COMPUTED | CRITERION_FROZEN<br>VALIDATION_BLOCKED |

**Key clarification (per Audit CYCLE_37591874490):** The citation heritage AUC 0.70-0.74 "PASS at 174k" claim in the original criteria was **incorrect** — actual 174k run on `cited_outcome_hybrid_0.5_174k` embedding yielded AUC 0.482 FAIL. The PASS evidence (0.792) comes from **partial 24-year/158k cohort** (center_projected embeddings), NOT the full 174k corpus.

**Evidence:** `results/evaluation/dense_complementary_acceptance_criteria.json`, `results/evaluation/bootstrap_ci_dense_metrics_20261006.json`, `results/evaluation/citation_heritage_174k.json`

---

### Accepted Negative Findings (FROZEN)

| Finding | Value | Implication |
|---------|-------|-------------|
| True OOS JuristPref ceiling | ~0.53 < 0.7 factory target | Dense embeddings cannot be primary navigation mode |
| v18 coarse hierarchy max purity | 0.65 < 0.7 threshold | Coarse legal taxonomy recovery fails for dense |
| Citation heritage recall@10 | max 0.0066 | Citation heritage is ranking signal, not retrieval |
| Boilerplate resistance (dense) | FAIL | Dense embeddings more susceptible to procedural boilerplate |
| Citation heritage 174k AUC | 0.482 < 0.75 | Full 174k FAILS; partial PASS does not generalize |

---

### Legal-Distance Checkpoint Progress (Monitor Check #321)

| Metric | Value |
|--------|-------|
| Completed checkpoint years | 24/26 (2000-2023) |
| Decisions in checkpoints | ~158,000 (90.8%) |
| Accepted years (in fractal-map) | 3/26 (2000-2002) |
| Citation heritage quality (24yr) | center_projected AUC > 0.75 PASS (730 positive pairs) |
| Failed/missing years | 2024, 2025, 2026 (no parquet, no embeddings) |
| Center-projected concatenation | NOT PERFORMED |
| Citation roles 174k | NOT COMPUTED |
| Linear hybrids 174k | NOT COMPUTED |

**Data Blockers (unchanged):**
1. **bge_/bger_ ID mapping** — Cannot align 174k dense embeddings with evaluation metadata
2. **parquet 2024-2026** — ~15,963 decisions missing from parquet, cannot compute final 174k embeddings
3. **section extraction at 174k** — Cross-lingual section alignment needs sachverhalt/erwaegungen/dispositiv at full scale

---

### Monitor Infrastructure Status (OPERATIONAL)

| Component | Status |
|-----------|--------|
| HNSW backend (hnswlib) | OPERATIONAL_ON_GITHUB_RUNNERS |
| scalable_nn.py | OPERATIONAL_WITH_SKLEARN_FALLBACK |
| v25 formal suite | OPERATIONAL (8 TF-IDF reps evaluated at 174k) |
| Citation heritage benchmark | FROZEN_137k_PAIRS_READY |
| v17b label normalization | OPERATIONAL (213→163 labels, 32 cross-lingual concepts) |
| Monitor script | ACTIVE (check #321 completed) |

---

## Recommendation

**CONTINUE_RECOMMENDED = false** for the current factory-direction question (v35). 

The evaluation lane has:
- ✅ Frozen TF-IDF 174k evaluation as production baseline (COMPLETE)
- ✅ Defined and frozen dense embedding complementary acceptance criteria (COMPLETE)
- ✅ Documented all data blockers and validation protocol
- ✅ Active monitor watching for 174k dense embeddings delivery

**Next cycle trigger:** When legal-distance lane produces concatenated 174k dense embeddings (center_projected variants, metric learning, citation roles, linear hybrids), the monitor's `run_formal_suite_v25()` will auto-execute the full v25 protocol against frozen criteria.

---

## Evidence References

- `evaluation/state/evaluation.json` — direction_version 35, evidence_tier=TF-IDF_ACCEPTED_DENSE_UNVALIDATED, cycle_status=COMPLETE, continue_recommended=false
- `evaluation/state/monitor_174k_state.json` — check_count=321, dense_embeddings_progress=24yr/158k checkpoints
- `results/evaluation/tfidf_174k_formal_suite_baseline.json` — 8/8 PASS both adversarial gates
- `results/evaluation/dense_complementary_acceptance_criteria.json` — frozen criteria with bootstrap 95% CIs
- `results/evaluation/bootstrap_ci_dense_metrics_20261006.json` — partial cohort validation evidence
- `results/evaluation/citation_heritage_174k.json` — full 174k AUC 0.482 FAIL (accepted negative)
- `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/progress.json` — 24 completed years

---

## Compliance with Research Protocol

| Step | Status |
|------|--------|
| 1. Read Master Prompt, factory direction, lane directive | ✅ |
| 2. Inspect ACCEPTED evidence from other lanes | ✅ (legal-distance, fractal-map, product) |
| 3. State hypothesis, baseline, product decision | ✅ (TF-IDF primary, dense complementary) |
| 4. Freeze sample, metric, success rule before result | ✅ (done in v34, confirmed in v35) |
| 5. Smallest rigorous discriminating experiment | ✅ (monitor scan — no new representations) |
| 6. Run; preserve raw outputs and failures | ✅ (monitor log, state files updated) |
| 7. Compare with baseline, report uncertainty | ✅ (TF-IDF frozen, dense unvalidated at 174k) |
| 8. Write machine-readable lane state + report | ✅ (this cycle) |
| 9. Recommend CONTINUE/PIVOT/BLOCKED/PRODUCTIZE/PAUSE | ✅ **PAUSE (continue_recommended=false)** |

---

## Conclusion

The evaluation lane has completed its work for Factory Direction v35. The strategic pivot (legal-distance audit CYCLE_37090665528) is fully reflected:

- **TF-IDF citation hybrids = PRIMARY** product mode (jurist preference, branch clustering)
- **Dense embeddings = COMPLEMENTARY** modes (citation heritage view, cross-lingual view, linear hybrid complement)

The lane enters a **monitoring/waiting state** until corpus lane deliveries unblock legal-distance 174k dense embedding production. No further evaluation cycles on this question are warranted.