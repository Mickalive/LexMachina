# Evaluation Lane v34 — Completion Confirmation

**Run ID**: EVALUATION_V34_COMPLETION_CONFIRMATION_20261007
**GitHub Run**: 37638810035
**Timestamp**: 2026-10-07
**Direction Version**: 34

## Executive Summary

The evaluation lane has **completed** all work required by factory direction v34 question:

> "Freeze TF-IDF 174k evaluation as production baseline; define acceptance criteria for dense embedding complementary views (citation heritage AUC > 0.75, cross_lang_same_branch > 0.2 for sachverhalt, cross_lang_same_branch > 0.1 for dispositiv)."

Both deliverables are **DONE**, **FROZEN**, and **AUDIT-READY**.

---

## Deliverable 1: TF-IDF 174k Production Baseline FROZEN ✅

**Evidence**: `results/evaluation/tfidf_174k_formal_suite_baseline.json`

| Metric | Result | Threshold | Status |
|--------|--------|-----------|--------|
| Modes evaluated | 8 | — | COMPLETE |
| Adversarial gates PASS | 8/8 | 8/8 | PASS |
| Best JP (hybrid_0.5) | 0.7345 | > 0.5 | PASS |
| Best LangDom (hybrid_0.5) | 0.477 | < 0.85 | PASS |
| Beats semantic baseline (JP 0.43) | YES | — | MISSION SATISFIED |

**Production default**: `cited_decisions_tfidf_outcome_hybrid_0.5` (173,963 decisions)

**Known limitations** (documented, not blockers for primary mode):
- Cross-language retrieval: FAIL (recall@10 0.141 < 0.2)
- Hierarchy coherence: FAIL (nesting_score 0.317)
- Cluster coherence: FAIL (branch_purity 0.316)
- Temporal stability: FAIL (neighbor_overlap 0.381)
- Boilerplate resistance: FAIL (resistance_score -0.834)

---

## Deliverable 2: Dense Complementary Acceptance Criteria FROZEN ✅

**Evidence**: `results/evaluation/dense_complementary_acceptance_criteria.json` (REVISED per Audit CYCLE_37591874490)

### Criterion 1: Citation Heritage View
- **Metric**: AUC for recovering cited precedent pairs (frozen 137k pair pool)
- **Threshold**: > 0.75
- **174k result**: AUC 0.482 FAIL (`cited_outcome_hybrid_0.5_174k` embedding)
- **Partial 22yr (2000-2002) cohort**: AUC 0.792-0.794 PASS — **does not generalize to 174k**
- **TF-IDF citation-based at 174k**: 0.70-0.74
- **Status**: CRITERION_DEFINED_FROZEN — VALIDATION BLOCKED at 174k

### Criterion 2: Cross-Lingual View (Section-Segmented)
| Section | Metric | Threshold | 174k Status | Partial Sample Evidence |
|---------|--------|-----------|-------------|------------------------|
| Sachverhalt (facts) | cross_lang_same_branch | > 0.2 | BLOCKED | n=359: 0.282 PASS |
| Dispositiv (holdings) | cross_lang_same_branch | > 0.1 | BLOCKED | n=538: 0.150 PASS |
| Erwaegungen (reasoning) | cross_lang_same_branch | > 0.05 | BLOCKED | n=510: 0.094 PASS |

- **Blocker**: Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale required
- **Status**: CRITERION_DEFINED_FROZEN — VALIDATION BLOCKED

### Criterion 3: Linear Hybrid Complement
- **Metric**: Jurist pairwise preference at hybrid weight w=0.3-0.4
- **Threshold**: > 0.60 (below TF-IDF 0.735, above dense-only 0.43)
- **174k evidence**: BLOCKED — no 174k legal-distance dense embeddings exist
- **Obsolete embeddings (v6-v10)**: JP 0.66-0.68 — NOT target embeddings
- **Status**: CRITERION_DEFINED_FROZEN — VALIDATION BLOCKED

---

## Accepted Negative Findings (First-Class Evidence)

| Finding | Value | Implication |
|---------|-------|-------------|
| True OOS JuristPref ceiling | ~0.53 | Dense cannot be primary navigation (factory target 0.7) |
| v18 coarse hierarchy max purity | 0.65 < 0.7 | Coarse legal taxonomy recovery fails for all representations |
| Citation heritage recall@10 | 0.0066 | Citation heritage is ranking signal, not retrieval signal |
| Citation heritage 174k AUC | 0.482 < 0.75 | Full corpus FAILS; partial PASS doesn't generalize |

---

## Validation Protocol (Frozen for Future Cycle)

```python
# Citation Heritage
validate_citation_heritage_174k.py on frozen 137k pair pool with 174k dense embeddings

# Cross-Lingual
Compute section-segmented embeddings (sachverhalt/dispositiv/erwaegungen)
Evaluate cross_lang_same_branch per section at full 174k

# Linear Hybrid
Run formal suite adversarial gates on weights 0.3, 0.35, 0.4 with 174k dense + TF-IDF

# Scale Requirement
All criteria must hold at full 174k (not subsampled)
```

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Resolution |
|---------|--------|------------|
| bge_/bger_ ID mapping | Cannot align 174k dense embeddings with evaluation metadata (bger_ IDs) | Corpus lane resumption |
| parquet 2022-2026 | 29,520 decisions missing; cannot compute 174k dense embeddings | Corpus lane resumption |
| section extraction 174k | Cross-lingual section alignment needs sachverhalt/erwaegungen/dispositiv at 174k | Corpus lane resumption |

---

## Lane State

```json
{
  "lane": "evaluation",
  "direction_version": 34,
  "evidence_tier": "TF-IDF_ACCEPTED_DENSE_UNVALIDATED",
  "cycle_status": "COMPLETE",
  "continue_recommended": false,
  "accepted_run_id": "EVALUATION_V34_PRODUCTION_BASELINE_FROZEN_20261007",
  "next_recommendation": "TF-IDF 174k evaluation FROZEN as production baseline (COMPLETE, no further cycles). Dense embedding complementary view acceptance criteria DEFINED and FROZEN but UNVALIDATED at 174k scale — validation BLOCKED pending corpus lane deliveries. Next evaluation cycle triggers ONLY when legal-distance delivers 174k dense embeddings for validation against frozen criteria."
}
```

---

## Verification History

| Run | Date | Type | Status |
|-----|------|------|--------|
| 37574492135 | 2026-10-07 | Final verification | VERIFIED |
| 37598492933 | 2026-10-07 | Independent state & artifact audit | VERIFIED (12 tests passed) |
| 37608530998 | 2026-10-07 | Monitor check #318 | CONFIRMED_FROZEN |

---

## Conclusion

**Evaluation lane v34 work is COMPLETE.** No further cycles justified under current factory direction. The TF-IDF 174k production baseline is frozen and operational. Dense complementary criteria are frozen but unvalidated at 174k scale, blocked on corpus lane data deliveries. All negative results preserved as first-class evidence. Lane is audit-ready.