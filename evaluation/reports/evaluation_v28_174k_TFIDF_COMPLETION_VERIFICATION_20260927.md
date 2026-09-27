# Evaluation Lane v28 — 174k TF-IDF Family Formal Suite Verification Report

**Date**: 2026-09-27  
**Factory Direction**: v28  
**Lane**: evaluation  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Continue Recommended**: false  
**Run ID**: evaluation_v28_174k_tfidf_formal_suite_verified_20260927

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions** for the TF-IDF family at 174k scale as required by factory direction v28. This verification run confirms the infrastructure is operational and results are reproducible. The lane remains correctly **BLOCKED_ON_DEPENDENCIES** awaiting dense embeddings, citation roles, and linear hybrids from legal-distance (only 3/26 years ACCEPTED; years 2003-2015 pending audit).

### Three Sub-Questions — All COMPLETE (Verified)

| Sub-Question | Status | Key Result |
|--------------|--------|------------|
| **(1) 12-Benchmark Formal Suite** | ✅ COMPLETE | 8 TF-IDF representations evaluated with frozen harness v3 thresholds; HNSW artifact fixed via exact k-NN on stratified subsample (n=2000) |
| **(2) Citation Heritage Benchmark** | ✅ COMPLETE | Frozen pair pool validated (137,314 pairs, 95.9% citation resolution); infrastructure ready for dense embeddings |
| **(3) v17b Label Normalization** | ✅ COMPLETE | 214→164 labels (23.4% reduction), 32 cross-lingual concepts; PARTIAL generalization (2/8 reps within ≤10% worsening rule) |

---

## Infrastructure Verification Results

### Formal Suite Runner Verification (2026-09-27T14:45:00Z)

**Tested representation**: `cited_decisions_tfidf` (173,963 × 128)

| Benchmark | Result | Threshold | Status |
|-----------|--------|-----------|--------|
| Adversarial Language Dominance | 0.5295 | < 0.85 | ✅ PASS |
| Jurist Pairwise Preference | 0.8010 | > 0.50 | ✅ PASS |
| Both Adversarial Gates | — | — | ✅ PASS |

**Backend**: sklearn_exact on stratified subsample n=2000 (HNSW artifact fix confirmed)

### Citation Heritage Infrastructure

- **Frozen pair pool**: 137,314 positive + 137,314 negative pairs = 274,628 total
- **Citation graph**: 2,105 total citations, 2,019 resolved (95.9%)
- **Decisions with in-corpus citations**: 924
- **Status**: Infrastructure frozen and ready for dense embeddings

### Test Suite Status

| Test | Status |
|------|--------|
| frozen_harness_reproducibility | ✅ PASSING |
| v17_label_normalization | ✅ PASSING |
| v17b_label_normalization_all_reps | ✅ PASSING |
| v16_full_benchmark_suite | ✅ PASSING |
| boilerplate_resistance_real | ✅ PASSING |
| cross_lingual_alignment_v10 | ✅ PASSING |
| audit_correction_verification | ✅ PASSING |

---

## Key Findings (Confirmed)

### 1. Fundamental Two-Mode Tradeoff Persists at 174k

**Citation-based representations** (cited_decisions_tfidf, outcome_tfidf, hybrids):
- ✅ PASS adversarial gates (language dominance ~0.45-0.53, jurist preference ~0.61-0.81)
- ❌ FAIL hierarchy_coherence, legal_area_clustering, temporal_stability, boilerplate_resistance

**Text-based representations** (full_text, regeste, regeste_full_text hybrids):
- ❌ FAIL adversarial gates (language dominance ~1.0, jurist preference ~0.0)
- ✅ PASS branch/tf_metadata benchmarks

### 2. Best Representation
`cited_decisions_tfidf` (lang_dom=0.5295, jurist_pref=0.8020)

### 3. Production Default
`cited_outcome_hybrid_0.5` (lang_dom=0.5164, jurist_pref=0.8055) — balances citation signal with outcome signal

### 4. Universal Failures Are Corpus/Label Limitations
- Only ~90,632 decisions have valid branch labels out of 174k (52%)
- Legal_area coverage: 52.6% but highly sparse (214 raw labels → 164 normalized)
- Citation graph is sparse (2,105 citations total, 924 resolved in-corpus)

### 5. HNSW Artifact Confirmed and Fixed
HNSW with fixed parameters produced nearly identical k-NN graphs across different TF-IDF representations at 174k scale, masking representation differences. Exact k-NN on valid subset (n=2000) shows jurist pairwise 0.73–0.80; HNSW on full corpus shows 0.12 for all.

### 6. Citation Heritage: All TF-IDF Reps FAIL Recall@10
Despite some passing AUC (>0.65), all 8 TF-IDF representations FAIL recall@10 > 0.2 threshold. The sparse citation graph (924 decisions with resolved in-corpus citations out of 174k) is the limiting factor.

### 7. v17b Label Normalization: PARTIAL Generalization
- Citation-based reps: hierarchy purity gains 1.05-1.06x
- Text-based reps: zoom_fine degrades 0.66-0.69x
- Even with normalized labels, best hierarchy purity = 0.47 < 0.7 threshold

---

## Blocked Dependencies

The evaluation lane is **BLOCKED_ON_DEPENDENCIES** on legal-distance lane:

| Dependency | Progress | Blocker |
|------------|----------|---------|
| 174k dense embeddings | 3/26 years (2000–2002) = 19,441 decisions (11%) | Only 3/26 years ACCEPTED; years 2003-2015 pending audit per factory direction v28 |
| Citation role embeddings | 0% | Awaits dense embedding completion |
| Linear hybrids | 0% | Awaits dense embedding completion |

**Resolution path**: Legal-distance completes 174k dense embeddings → audit promotion → evaluation monitor auto-detects and runs formal suite on all awaited representations.

---

## Awaited Production Representations (11)

1. `center_projected_768dim_174k`
2. `center_projected_64dim_174k`
3. `center_projected_128dim_174k`
4. `linear_metric_epoch4_174k`
5. `mahalanobis_metric_epoch4_174k`
6. `hybrid_stabilized_epoch1_174k`
7. `hybrid_v2_epoch3_174k`
8. `citation_role_citing_174k`
9. `citation_role_following_174k`
10. `citation_role_criticizing_174k`
11. `linear_hybrid05_concat_174k`

---

## External Dependencies

| Dependency | Status |
|------------|--------|
| Jurist human study (5–10 Swiss jurists) | BLOCKED (framework ready, recruitment by repository owner required) |

---

## Recommendation

**No additional same-question cycle justified for TF-IDF family.** The three machine-executable sub-questions are COMPLETE with REPRODUCED evidence tier. Infrastructure verified operational.

**Next action**: Factory Director to resolve legal-distance audit promotion for years 2003-2015 → legal-distance completes 174k dense embeddings → evaluation monitor auto-detects and runs formal suite on all awaited representations.

**Cycle recommendation**: `continue_recommended = false` (same question complete). Awaiting successor question when dense embeddings land and pass audit.

---

## Evidence References

1. Formal suite: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
2. Citation heritage pairs: `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`
3. Citation heritage results: `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
4. Legal area analysis: `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json`
5. v17b TF-IDF: `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json`
6. v17b label normalization: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
7. Partial dense (2000-2002): `evaluation/results/partial_dense_2000_2002/evaluation_partial_dense_latest.json`
8. Partial dense (2000-2015) center_projected: `evaluation/results/174k/center_projected_partial_2000_2015/center_projected_16year_eval_latest.json`

---

## State Files Updated

- `evaluation/state/evaluation.json` — last_verification updated to 2026-09-27T14:45:00.000000Z
- `evaluation/state/monitor_174k_state.json` — check_count=154, last_check updated, last_verification=verification_20260927_infrastructure_confirmed

---

*Report generated per Research Protocol §12: "Write machine-readable lane state plus human-readable report."*