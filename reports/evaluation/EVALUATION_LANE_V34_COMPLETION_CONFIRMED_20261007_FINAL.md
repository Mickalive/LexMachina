# Evaluation Lane v34 — Completion Confirmed (Final)

**Lane**: evaluation
**Factory Direction**: v34
**Status**: COMPLETE — audit-ready, no further same-question cycles justified
**Date**: 2026-10-07
**GitHub Run**: 37601204212

---

## Summary

The evaluation lane has **successfully completed** its mandate for factory direction v34:

| Deliverable | Status | Evidence Tier |
|-------------|--------|---------------|
| TF-IDF 174k production baseline frozen | ✅ COMPLETE | ACCEPTED |
| Dense embedding complementary acceptance criteria defined | ✅ COMPLETE | CRITERIA_FROZEN (UNVALIDATED at 174k) |
| All negative findings preserved | ✅ COMPLETE | ACCEPTED_NEGATIVE |
| Data blockers identified and documented | ✅ COMPLETE | — |
| Validation protocol frozen for unblocking | ✅ COMPLETE | — |
| Independent verification passes | ✅ COMPLETE (2 runs) | VERIFIED |
| Audit revision applied | ✅ COMPLETE | REVISED |

---

## TF-IDF 174k Production Baseline — FROZEN (ACCEPTED)

**Mode**: `cited_decisions_tfidf_outcome_hybrid_0.5`
- **Jurist Preference Rate**: 0.7345 (threshold: > 0.5) ✅
- **Language Dominance**: 0.477 (threshold: < 0.85) ✅
- **Beats semantic baseline**: 0.7345 vs 0.43 ✅
- **All 8 TF-IDF modes PASS both adversarial gates** ✅

**Known TF-IDF Limitations (documented, not blockers for v1.0)**:
- Cross-language retrieval: FAIL (recall@10 = 0.141 < 0.2)
- Hierarchy coherence: FAIL (nesting_score = 0.317)
- Cluster coherence: FAIL (branch_purity = 0.316, language_purity = 0.612)
- Temporal stability: FAIL (neighbor_overlap = 0.381)
- Boilerplate resistance: FAIL (resistance_score = -0.834)
- Zero-shot cross-language transfer: FAIL

---

## Dense Embedding Complementary Criteria — DEFINED BUT UNVALIDATED at 174k

| Criterion | Threshold | 174k Status | Blocker |
|-----------|-----------|-------------|---------|
| Citation heritage AUC | > 0.75 | **FAIL** (0.482 on cited_outcome_hybrid_0.5_174k) | Full 174k FAIL; partial 22yr PASS (0.79-0.85) does not generalize |
| Cross-lingual sachverhalt | > 0.2 | Full-doc: 0.0 FAIL; Partial subset (n=359): 0.282 PASS | Section extraction at 174k required |
| Cross-lingual dispositiv | > 0.1 | Full-doc: 0.0 FAIL; Partial subset (n=538): 0.150 PASS | Section extraction at 174k required |
| Linear hybrid complement (w=0.3-0.4) | JP > 0.60 | **BLOCKED** — no 174k legal-distance dense embeddings exist | bge/bger mapping + parquet 2022-2026 + section extraction |

**Key distinction**: Cross-lingual PASS evidence is from **partial subsets** (36-54% coverage, n=359-538), NOT full 174k scale. Linear hybrid evidence is from **obsolete v6-v10 embeddings**, not target 174k legal-distance embeddings.

---

## Accepted Negative Findings (First-Class Evidence)

| Finding | Value | Implication |
|---------|-------|-------------|
| True OOS jurist preference ceiling | 0.53 < 0.7 target | Dense embeddings cannot be primary navigation mode |
| v18 coarse hierarchy max branch purity | 0.65 < 0.7 | Coarse legal taxonomy recovery fails for all representations |
| Citation heritage recall@10 | 0.0066 | Citation heritage is ranking signal, not retrieval signal |
| Full 174k citation heritage AUC | 0.482 < 0.75 | Partial 22yr cohort PASS does not generalize to full corpus |

---

## Data Blockers (Corpus Lane Resumption Required)

1. **BGE/BGER ID Mapping** — Cannot align 174k dense embeddings with evaluation metadata (canonical corpus uses `bge_`, evaluation uses `bger_`)
2. **Parquet 2022-2026** — 29,520 decisions missing from parquet; cannot compute 174k dense embeddings
3. **Section Extraction at 174k** — Cross-lingual section alignment needs sachverhalt/erwaegungen/dispositiv extraction at full scale

---

## Next Evaluation Cycle Trigger

**Conditional**: Next cycle triggers **ONLY** when legal-distance delivers 174k dense embeddings for validation against the **frozen** acceptance criteria defined in `dense_complementary_acceptance_criteria.json`.

No further same-question cycles are justified. The TF-IDF baseline is production-ready; dense validation waits on data unblocking.

---

## Artifacts (All Preserved, Provenance Maintained)

```
results/evaluation/
├── tfidf_174k_formal_suite_baseline.json          # Frozen production baseline
├── dense_complementary_acceptance_criteria.json   # Frozen dense criteria (REVISED post-audit)
├── citation_heritage_174k.json                    # AUC 0.482 FAIL at 174k
├── v18_coarse_hierarchy/v18_coarse_hierarchy_results.json  # Max purity 0.65 FAIL
├── bootstrap_ci_dense_metrics_20261006.json       # CIs for partial dense metrics
├── v17b_label_normalization_174k_latest.json      # Normalization stability REPRODUCED
└── tfidf_174k_adversarial_gates_formal_suite_latest.json # 8/8 PASS
```

**State File**: `state/evaluation.json` — authoritative machine-readable record

**Verification Runs**:
- `EVALUATION_V34_FINAL_VERIFICATION_20261007_37574492135` — 12 tests passed
- `EVALUATION_V34_VERIFICATION_20261007_37598492933` — Independent audit, 12 tests passed

---

## Audit Trail

**Audit Gate**: CYCLE_37591874490 → REVISE
**Corrections Applied**:
- Evidence tier: `ACCEPTED` → `TF-IDF_ACCEPTED_DENSE_UNVALIDATED`
- Continue recommended: `false` → `conditional`
- Dense criteria status: `VALIDATED` → `UNVALIDATED/BLOCKED at 174k`
- Citation heritage 174k AUC 0.482 FAIL preserved as negative evidence
- Cross-lingual partial subset limitations documented
- Linear hybrid evidence on obsolete embeddings documented

**Infrastructure Note**: `/tmp/lex_control/state/factory_direction.json` shows `evaluation.status="RUN"` — this is a persistent V28-pattern control plane mounting defect, NOT a lane failure. Workspace state and lane state correctly show COMPLETE.

---

## Conclusion

**Evaluation lane v34 work is complete.** The product has a frozen, verified TF-IDF 174k production baseline that beats the semantic-map baseline on jurist preference (0.735 vs 0.43). Dense embedding complementary views have explicit, frozen acceptance criteria awaiting data unblocking. All evidence — positive and negative — is preserved with full provenance.