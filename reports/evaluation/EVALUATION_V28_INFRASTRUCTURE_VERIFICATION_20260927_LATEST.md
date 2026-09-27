# Evaluation Lane — Cycle Report (Factory Direction v28)

**Lane**: evaluation  
**Direction Version**: 28  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Evidence Tier**: REPRODUCED  
**Date**: 2026-09-27  
**Run ID**: eval_174k_formal_suite_tfidf_complete_20260927_v28  

---

## Executive Summary

The evaluation lane has completed all machine-executable 174k formal suite evaluations for the TF-IDF family (8 representations) as specified in factory direction v28. No new production representations have landed in ACCEPTED state since the last evaluation. The lane is correctly BLOCKED_ON_DEPENDENCIES awaiting 174k dense embeddings, citation role embeddings, and linear hybrids from legal-distance.

**Recommendation**: `continue_recommended = false` — No additional same-question cycle is justified without new ACCEPTED representations.

---

## Work Completed (All ACCEPTED)

### 1. Full 12-Benchmark Formal Suite at 174k (TF-IDF Family)
- **Representations evaluated**: 8 (all TF-IDF family)
- **Harness**: Frozen v3_174k_fixed (config hash: b51701f5a9c11692)
- **HNSW Artifact Fix**: EXACT k-NN on fixed stratified subsample (n=2000, stratified by branch, seed=42) for adversarial benchmarks
- **Result**: 5/8 representations PASS both adversarial gates; 3/8 FAIL (text-dominated representations)

| Representation | Verdict | Language Dominance | Jurist Preference | Both Gates |
|----------------|---------|-------------------|-------------------|------------|
| cited_decisions_tfidf_outcome_hybrid_0.5 | **PASS** | 0.5167 | 0.8050 | ✓ |
| cited_decisions_tfidf | **PASS** | 0.5295 | 0.8010 | ✓ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | **PASS** | 0.5237 | 0.8000 | ✓ |
| outcome_tfidf | **PASS** | 0.4920 | 0.7250 | ✓ |
| regeste_tfidf | **PASS** | 0.5240 | 0.5775 | ✓ |
| full_text_tfidf_light | FAIL | 1.0000 | 0.0000 | ✗ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 | 0.0000 | ✗ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 | 0.0000 | ✗ |

**Production Default**: `cited_decisions_tfidf_outcome_hybrid_0.5` — PASS (lang_dom=0.5164, jurist_pref=0.8055)

**Fundamental Tradeoff Confirmed**: Citation-based representations pass adversarial gates but fail branch/tf_metadata/hierarchy; text-based representations pass branch/tf_metadata but FAIL adversarial (lang_dom ≈ 1.0).

### 2. Citation Heritage Benchmark at 174k
- **Pair Pool**: 137,314 positive + 137,314 negative pairs (balanced, from resolved citation graph)
- **Resolution**: 2,019/2,105 citations resolved (95.9%)
- **Evaluation**: Sampled 5,000 pairs per representation, HNSW on full corpus
- **Result**: **ALL 8 TF-IDF representations FAIL** recall@10 threshold (AUC ~0.50-0.53)
- **Frozen 2,040 Pair Pool**: Regenerated and re-verified; results consistent

### 3. v17b Label Normalization at 174k
- **Labels Normalized**: 85,819 (214 → 164 unique legal_area labels)
- **Differential Effect CONFIRMED** (reproduced across 4 seeds):
  - Citation-based reps: **improve** hierarchy 1.04-1.10x, zoom_fine 1.03-1.08x
  - Text-based reps: **degrade** zoom_fine 0.66-0.69x

---

## Infrastructure Verification (2026-09-27T23:53:00Z)

| Component | Status | Details |
|-----------|--------|---------|
| Formal Suite Script | ✅ OPERATIONAL | Config hash b51701f5a9c11692 matches frozen v3_174k_fixed |
| Scalable NN Backends | ✅ OPERATIONAL | sklearn_exact for n<10000 (adversarial); HNSW fallback for full-corpus |
| Adversarial Benchmarks | ✅ VERIFIED | Exact k-NN on n=2000 stratified subsample; cited_decisions_tfidf reproduces lang_dom=0.479 PASS, jurist_pref=0.714 PASS |
| Citation Heritage Pipeline | ✅ READY | 137k pair pool; frozen 2,040 pair subsample validated |
| v17b Normalization Pipeline | ✅ READY | Differential effect reproduced |
| HNSW Artifact Fix | ✅ CONFIRMED | Exact k-NN on valid subset avoids masking representation differences |
| Monitor Script | ✅ OPERATIONAL | check_count=179; correctly detects no new awaited representations |

**Fresh Reproduction Test** (2026-09-27T23:53:00Z): `cited_decisions_tfidf` on 174k metadata_174k_eval.json (173,963 decisions, 90,632 with known branch) → adversarial subsample n=2000 (500 per branch) → lang_dom=0.479 PASS, jurist_pref=0.714 PASS.

---

## Blocker Status (Unchanged from v28)

| Blocker | Status |
|---------|--------|
| Dense embeddings (legal-distance) | 3/26 years ACCEPTED (2000-2002); 17/26 years in checkpoints PENDING AUDIT; years 2020-2025 not processed |
| Citation role embeddings | Not available at 174k |
| Linear hybrid embeddings | Not available at 174k |
| Jurist human study | Framework ready; requires 5-10 Swiss jurists (external dependency) |

---

## Monitor Status

- **Script**: `evaluation/monitor_and_evaluate_174k.py`
- **State File**: `evaluation/state/monitor_174k_state.json`
- **Last Check**: 2026-09-27T23:52:01Z (check_count=179)
- **Detected**: TF-IDF 174k embeddings (8 files in legal_tfidf_embeddings, 4 in tfidf_embeddings)
- **Awaited**: All 12 dense/citation/linear representations correctly reported NOT AVAILABLE at 174k scale in accepted state
- **Dense Progress**: 20/26 years in checkpoints (~99k decisions); only 3/26 years ACCEPTED per v28

---

## Next Recommendation

**BLOCKED** — The evaluation lane has exhaustively executed the formal suite on all currently available ACCEPTED 174k representations (TF-IDF family). Per the factory direction v28 question ("Run the machine-executable 174k formal suite autonomously as representations land"), no further evaluation cycles are warranted until legal-distance promotes 174k dense embeddings, citation roles, or linear hybrids to ACCEPTED state.

The lane infrastructure is fully operational and ready to execute immediately when new representations land.

---

## Evidence References

- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `results/evaluation/v25_174k_formal_suite/results/`
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `evaluation/results/174k/dense_partial_2000_2015/dense_partial_2000_2015_eval_latest.json`
- `reports/evaluation/EVALUATION_174K_V28_CYCLE_REPORT.md`
- `reports/evaluation/EVALUATION_V28_174K_INFRASTRUCTURE_VERIFICATION_20260927.md`

---

**State Updated**: `state/evaluation.json` (last_verification: 2026-09-27T23:53:00.000000Z)