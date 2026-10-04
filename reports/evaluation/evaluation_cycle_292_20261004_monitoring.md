# Evaluation Lane — Monitoring Cycle 292 Report

**Run ID:** `eval_monitor_292_20261004`  
**GitHub Run:** 37177870655 (monitoring cycle)  
**Date:** 2026-10-04  
**Direction Version:** 34  
**Evidence Tier:** ACCEPTED (baseline frozen)  
**Cycle Status:** MONITORING (honest null result)  
**Continue Recommended:** FALSE  

---

## Executive Summary

**No new 174k awaited representations detected.** The evaluation lane remains in monitoring mode with the TF-IDF 174k production baseline frozen and dense embedding complementary criteria defined. All 12 awaited representations (dense embeddings, citation roles, linear hybrids) remain blocked on corpus lane dependencies (bge_/bger_ ID mapping + parquet 2022-2026).

---

## Scan Results

| Category | Expected | Found | Status |
|----------|----------|-------|--------|
| **TF-IDF (completed)** | 8 | 8 | ✅ ALL EVALUATED |
| Dense embeddings 174k | 7 | 0 | ❌ BLOCKED |
| Citation roles 174k | 3 | 0 | ❌ BLOCKED |
| Linear hybrids 174k | 2 | 0 | ❌ BLOCKED |

**TF-IDF representations confirmed present and evaluated:**
- `cited_decisions_tfidf` ✓
- `outcome_tfidf` ✓
- `cited_decisions_tfidf_outcome_hybrid_0.5` ✓ (production default)
- `cited_decisions_tfidf_outcome_hybrid_0.7` ✓
- `regeste_tfidf` ✓
- `full_text_tfidf_light` ✓
- `regeste_full_text_hybrid_0.5` ✓
- `regeste_full_text_hybrid_0.7` ✓

**Awaited representations — all absent:**
- `center_projected_768dim` ✗
- `center_projected_64dim` ✗
- `center_projected_128dim` ✗
- `linear_metric_epoch4` ✗
- `mahalanobis_metric_epoch4` ✗
- `hybrid_stabilized_epoch1` ✗
- `hybrid_v2_epoch3` ✗
- `citation_role_citing_alpha0.3` ✗
- `citation_role_following_alpha0.3` ✗
- `citation_role_criticizing_alpha0.3` ✗
- `linear_citation_concat` ✗
- `linear_hybrid05_concat` ✗

---

## Blocker Status (Unchanged)

| Blocker | Owner | Status |
|---------|-------|--------|
| bge_/bger_ ID mapping | Corpus lane | REQUIRED — no mapping between canonical (bge_) and evaluation (bger_) IDs |
| Parquet 2022-2026 | Corpus lane | REQUIRED — 29,520 decisions missing from 144k checkpoint |
| 174k dense embedding concatenation | Legal-distance lane | BLOCKED on above |
| Citation role embeddings 174k | Legal-distance lane | BLOCKED on above |
| Linear hybrid embeddings 174k | Legal-distance lane | BLOCKED on above |

**Corpus lane status:** PAUSED (per factory direction v34). Resumption required for any further dense evaluation.

---

## Dense Embeddings Progress (Checkpointed, Not Accepted)

Per legal-distance progress (2026-10-02):
- **22/26 years** (2000-2021) in checkpoints: 144,443 decisions (83% of 173,963)
- **Only 3/26 years** (2000-2002) ACCEPTED: 19,441 decisions
- Center-projected concatenation of 22 years: NOT YET PERFORMED
- Years 2022-2026: NOT YET PROCESSED

**Evaluation-validated criteria (against 22-year/144k checkpoint evidence):**
| Criterion | Threshold | 22-Year Evidence | Status |
|-----------|-----------|------------------|--------|
| Citation heritage AUC | > 0.75 | 0.79-0.80 (center_projected) | ✅ PASS |
| Cross-lang sachverhalt | > 0.2 | ~0.282 | ✅ PASS |
| Cross-lang dispositiv | > 0.1 | ~0.148-0.150 | ✅ PASS |
| Cross-lang erwaegungen | > 0.1 | ~0.093-0.094 | ❌ FAIL |
| Jurist preference (primary) | > 0.5 | 0.39-0.43 (FAIL) | ❌ FAIL — COMPLEMENTARY ONLY |

---

## TF-IDF 174k Production Baseline (FROZEN, Unchanged)

**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5`
- Jurist Preference: 0.7265 (beats semantic baseline 0.43 by +0.297)
- Language Dominance: 0.4895 (well below 0.85 threshold)
- **Audit Gate:** CYCLE_37073590337 PASSED (`safe_to_integrate=true`)

**All 8 TF-IDF reps PASS both adversarial gates** on frozen harness v3 (config hash: `b51701f5a9c11692`):
- Language Dominance range: [0.485, 0.511] — all PASS (< 0.85)
- Jurist Preference range: [0.614, 0.727] — all PASS (> 0.5)

---

## State Consistency

**Monitor State:** `evaluation/state/monitor_174k_state.json`
- Check count: **292** (incremented from 291)
- Last check: 2026-10-04T04:47:43
- Infrastructure: All OPERATIONAL (HNSW, v25 suite, citation heritage, v17b, monitor detection)

**Lane State:** `state/evaluation.json`
- `evidence_tier`: "ACCEPTED"
- `cycle_status`: "COMPLETE"
- `continue_recommended`: false
- `accepted_run_id`: "eval_174k_v34_baseline_and_dense_criteria_20261003"

---

## Recommendation

**No action required.** The evaluation lane v34 deliverable is complete. Continue honest null monitoring until 174k dense embeddings land (pending corpus lane resumption). No further same-question evaluation cycles justified.

---

## Evidence References

1. Monitor state: `evaluation/state/monitor_174k_state.json` (check_count=292)
2. Lane state: `state/evaluation.json` (COMPLETE, continue_recommended=false)
3. TF-IDF 174k formal suite: `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
4. Adversarial reproduction: `results/evaluation/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json` (config hash: `b51701f5a9c11692`)
5. Dense acceptance criteria validation: `reports/evaluation/eval_174k_v34_baseline_and_dense_criteria_report.md`
6. Factory direction v34: `/tmp/lex_control/state/factory_direction.json`

---

*Generated 2026-10-04 as monitoring cycle 292 — honest null result, no new awaited representations detected.*