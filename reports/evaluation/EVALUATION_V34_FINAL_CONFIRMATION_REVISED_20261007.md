# Evaluation Lane V34 — Final Confirmation (Revised Post-Audit)

**Confirmation Run:** `EVALUATION_V34_FINAL_VERIFICATION_20261007_37634774564`  
**Factory Direction Version:** 34  
**Date:** 2026-10-07  
**Status:** CONFIRMED — Lane Complete, Audit-Ready  

---

## Confirmation Checklist

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Hypothesis frozen before observation | ✅ | Adversarial harness v3 config_hash=`b51701f5a9c11692` |
| Corpus/sample frozen | ✅ | 173,963 decisions, stratified n=2000, seed=42 |
| Baseline defined | ✅ | Semantic baseline (center_projected JP=0.43) |
| Metric defined | ✅ | Language Dominance < 0.85, Jurist Preference > 0.5 |
| Success rule defined | ✅ | Both gates PASS for production default |
| Experiment executed | ✅ | 8/8 TF-IDF representations evaluated |
| Raw outputs preserved | ✅ | All JSON artifacts in `results/evaluation/` |
| Failures preserved | ✅ | Dense FAIL at ALL scales, v18 FAIL, v17b FAIL generalization |
| Baseline comparison | ✅ | TF-IDF JP 0.735 vs semantic 0.43 |
| Machine-readable state | ✅ | `state/evaluation.json` |
| Human-readable report | ✅ | `EVALUATION_V34_FINAL_VERIFICATION_REPORT_REVISED_20261007.md` |
| Continue recommendation | ✅ | `continue_recommended: false` |
| Audit ready | ✅ | `audit_ready: true` |

---

## Key Metrics Summary (Frozen)

### TF-IDF 174k Production Baseline (ACCEPTED)

| Representation | LangDom | JP | Both Gates |
|---|---|---|---|
| cited_decisions_tfidf | 0.4917 | 0.7075 | ✅ |
| **cited_decisions_tfidf_outcome_hybrid_0.5** | **0.4895** | **0.7265** | ✅ **DEFAULT** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4908 | 0.7195 | ✅ |
| outcome_tfidf | 0.5078 | 0.6660 | ✅ |
| regeste_tfidf | 0.5111 | 0.6145 | ✅ |
| full_text_tfidf_light | 0.4854 | 0.7080 | ✅ |
| regeste_full_text_hybrid_0.5 | 0.4873 | 0.7140 | ✅ |
| regeste_full_text_hybrid_0.7 | 0.4889 | 0.7120 | ✅ |

**All 8 PASS both adversarial gates.**

### Dense Embedding Complementary Criteria (UNVALIDATED at 174k)

| Criterion | Threshold | 22yr/144k Evidence | 174k Status |
|---|---|---|---|
| Citation Heritage AUC | > 0.75 | 0.792-0.795 PASS | **0.482 FAIL** |
| Cross-Lingual Sachverhalt | > 0.20 | 0.282 PASS (n=359) | **BLOCKED** |
| Cross-Lingual Dispositiv | > 0.10 | 0.148-0.150 PASS (n=538) | **BLOCKED** |
| Cross-Lingual Erwaegungen | > 0.05 | 0.093-0.094 PASS (n=510) | **BLOCKED** |
| Jurist Preference | > 0.50 | 0.389-0.418 FAIL | **CONFIRMED FAIL** |

---

## Negative Results Confirmed (First-Class Evidence)

| Finding | Value | Threshold | Implication |
|---|---|---|---|
| True OOS JP Ceiling | 0.53 | 0.7 | Dense cannot be primary |
| V18 Coarse Hierarchy | 0.65 | 0.70 | Branch-level unrecoverable |
| Citation Heritage Recall@10 | 0.0066 | — | Ranking, not retrieval |
| Citation Heritage 174k AUC | 0.482 | 0.75 | Partial PASS ≠ full PASS |
| V17b Normalization | Degraded | — | No generalization to 174k |

---

## Orchestration Pathology Documented

**Defect:** Supervisor dispatches operational resumes to COMPLETE lanes without reading `state/<lane>.json`

**Impact:** 318+ monitor checks dispatched to Evaluation lane after COMPLETION (GitHub runs 37574492135 → 37634774564)

**Classification:** V28-pattern control plane mounting defect — infrastructure, not lane failure

**Resolution:** Supervisor must implement pre-dispatch guard: `if state[lane].cycle_status == COMPLETE and state[lane].continue_recommended == false: SKIP`

---

## State Files Updated (Consolidated)

| File | evidence_tier | cycle_status | continue_recommended | audit_ready |
|---|---|---|---|---|
| `state/evaluation.json` | TF-IDF_ACCEPTED_DENSE_UNVALIDATED | COMPLETE | false | true |
| `evaluation/state/evaluation.json` | TF-IDF_ACCEPTED_DENSE_UNVALIDATED | COMPLETE | false | N/A (monitor) |

**Both now consistent and audit-ready.**

---

## Next Actions

| Lane | Action | Trigger |
|---|---|---|
| Corpus | Resume for BGE/bger mapping, parquet 2022-2026, section extraction | Factory Director decision |
| Legal-Distance | Compute 174k dense embeddings | Corpus deliveries complete |
| Fractal-Map | Integrate dense embeddings meeting complementary criteria | Legal-Distance delivers 174k dense |
| Evaluation | Next cycle: validate 174k dense against frozen criteria | 174k dense embeddings available |
| Product | Ship v1.0 with TF-IDF defaults | Ready now |

---

## Sign-Off

**Evaluation Lane V34 — CONFIRMED COMPLETE**

All Research Protocol steps satisfied. All evidence preserved. State consolidated. Snapshot audit-ready. No further same-question work justified.

*Confirmed by operational resume from persisted producer snapshot run 37628448574.*