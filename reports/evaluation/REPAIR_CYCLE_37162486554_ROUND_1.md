# Repair Report: Evaluation Cycle 37162486554, Round 1

**Lane:** evaluation  
**Original Cycle:** 37162486554  
**Repair Round:** 1  
**Date:** 2026-10-04  
**Audit Reference:** CYCLE_37162486554_GATE.json (REVISE gate)

---

## Required Fixes from Audit

| Fix | Status | Details |
|-----|--------|---------|
| `restore_v17b_latest_symlink_to_frozen_baseline` | ✅ COMPLETE | Copied frozen baseline from `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` (direction_version 27, 15k sample, 8 reps, full coherence metrics) to `results/evaluation/v17b_label_normalization_174k_latest.json` |
| `remove_or_isolate_partial_v17b_run` | ✅ COMPLETE | Removed all three protocol drift files: `v17b_label_normalization_174k_20261003_234303.json`, `v17b_label_normalization_174k_20261003_010407.json`, `v17b_label_normalization_174k_20261003_010430.json` |
| `preserve_state_evaluation_json_sync` | ✅ COMPLETE | Synchronized root `state/evaluation.json` to match canonical `evaluation/state/evaluation.json` (verified with `diff` - no differences) |

---

## Verification of Frozen Baseline Restoration

**Restored file:** `results/evaluation/v17b_label_normalization_174k_latest.json`

**Key properties confirming frozen baseline:**
- `direction_version`: 27 (frozen protocol version)
- `n_labels_normalized`: 85,819 (15k subsample, not 5k)
- `per_representation`: 8 representations (all TF-IDF modes, not 3)
- Metrics: Full `hierarchy_coherence`, `zoom_coherence`, `legal_area_clustering` (not simple NMI/purity)
- `uniform_improvement_or_matching`: `false`
- 4/8 representations degraded >10% on `zoom_fine`:
  - cited_decisions_tfidf: 0.8869
  - full_text_tfidf_light: 0.8352
  - cited_decisions_tfidf_outcome_hybrid_0.5: 0.8827
  - cited_decisions_tfidf_outcome_hybrid_0.7: 0.8861
- NMI decreases on normalized labels for ALL 8 reps
- `regeste_tfidf` only representation with no-worsening on ALL hierarchy metrics

---

## Protocol Drift Eliminated

**Removed partial runs (direction_version 29):**
- Sample size: 5,000 (vs frozen 15,000)
- Representations: 3 of 8 (cited_decisions_tfidf, hybrid_0.5, hybrid_0.7)
- Missing: outcome_tfidf, regeste_tfidf, full_text_tfidf_light, regeste_full_text_hybrid_0.5, regeste_full_text_hybrid_0.7
- Metrics: Simple clustering (nmi, purity, n_clusters) — NOT frozen coherence suite
- Critical omission: `regeste_tfidf` (only no-worsening representation in frozen protocol)

---

## State File Synchronization

**Root `state/evaluation.json`** now exactly matches **canonical `evaluation/state/evaluation.json`** (v34 frozen baseline with all critical findings, dense acceptance criteria, v17b/v18 negative results, infrastructure verification).

---

## Claim Ceiling (Unchanged from Audit)

> TF-IDF 174k production baseline FROZEN (8 reps, all PASS adversarial gates, best: cited_decisions_tfidf_outcome_hybrid_0.5 JP=0.7265, LangDom=0.4895). Dense embedding complementary view criteria DEFINED and PARTIALLY VALIDATED against 22-year/144k checkpoint evidence: (1) Citation heritage AUC > 0.75 — PASS (center_projected 768/64/128dim AUC 0.79-0.80); (2) Cross-lingual sachverhalt > 0.2 — PASS (center_projected ~0.282); (3) Cross-lingual dispositiv > 0.1 — PASS (center_projected ~0.148-0.150); (4) Cross-lingual erwaegungen > 0.1 — FAIL (center_projected ~0.093-0.094). Center_projected FAILS jurist preference gate at ALL scales (JP 0.39-0.43), confirming complementary-only role. v17b label normalization NEGATIVE at 174k (regime difference from 1k: 15k sample, 8 reps, full coherence metrics, 213->111 labels). v18 coarse hierarchy NEGATIVE (max branch purity 0.65 < 0.7). No 174k dense embeddings — blocked on bge_/bger_ ID mapping + parquet 2022-2026.

---

## Next Steps

No further repair cycles needed. All required fixes executed with durable delta. The evaluation lane state is now consistent with the frozen v34 baseline and ready for factory direction progression.
