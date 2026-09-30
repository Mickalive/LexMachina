# Evaluation Lane — Cycle Report (Factory Direction v29)

**Date**: 2026-09-30T02:05:00Z  
**Factory Direction**: v29  
**Lane Status**: MONITORING  
**Evidence Tier**: REPRODUCED  
**Continue Recommended**: false  
**Accepted Run ID**: `eval_174k_formal_suite_tfidf_complete_20260930_v29_monitor_242_verified`

---

## Executive Summary

The evaluation lane has **completed all deliverables for the current factory direction (v29)**. The TF-IDF family (8 representations) has been fully evaluated at 174k scale with the formal suite, citation heritage benchmark, and v17b label normalization test. All infrastructure is verified reproducible and audit-ready.

The lane is in **MONITORING** status, waiting for new representations from legal-distance:
- Dense embeddings at 174k scale (only 3/26 years ACCEPTED; 15/26 years checkpointed pending audit)
- Citation role embeddings
- Linear hybrid embeddings

No new representations detected since monitor check #240. Infrastructure re-verified at check #242.

---

## Work Completed (v29 Cycle)

| Task | Status | Details |
|------|--------|---------|
| **174k Formal Suite (TF-IDF, 8 reps)** | ✅ COMPLETE | All 8 representations evaluated with frozen harness v3 (HNSW artifact fixed via exact k-NN on stratified subsample n=2000). Config hash: `b51701f5a9c11692` |
| **Citation Heritage Benchmark** | ✅ COMPLETE | Re-run on frozen 137,314-pair pool (95.9% citation-ID resolution: 2,019/2,105). All 8 TF-IDF reps FAIL recall@10 threshold. |
| **v17b Label Normalization** | ✅ COMPLETE | Tested on 174k fine-grained legal_area labels (85,819 labels, 214→164 unique). Differential effect confirmed per audit CYCLE_36527630008. |
| **Adversarial Re-verification** | ✅ COMPLETE | Production default `cited_decisions_tfidf_outcome_hybrid_0.5`: LangDom=0.4895 PASS, JuristPref=0.7265 PASS (exact k-NN, n=2000). |
| **Monitor Check #242** | ✅ COMPLETE | No new awaited representations. All infrastructure VERIFIED. |

---

## Key Results (Frozen Config Hash: `b51701f5a9c11692`)

### Production Default: `cited_decisions_tfidf_outcome_hybrid_0.5`

| Benchmark | Score | Threshold | Status |
|-----------|-------|-----------|--------|
| Language Dominance (k=20) | 0.4895 | < 0.85 | ✅ PASS |
| Jurist Pairwise Preference (k=10) | 0.7265 | > 0.5 | ✅ PASS |
| **Both Adversarial Gates** | — | — | ✅ PASS |

### TF-IDF Family Summary (8 representations)

| Representation | LangDom | LangDom-P | JuristPref | JuristPref-P | Both |
|----------------|---------|-----------|------------|--------------|------|
| cited_decisions_tfidf | 0.5295 | ✅ | 0.8010 | ✅ | ✅ |
| outcome_tfidf | 0.6320 | ✅ | 0.7410 | ✅ | ✅ |
| regeste_tfidf | 0.4395 | ✅ | 0.7885 | ✅ | ✅ |
| full_text_tfidf_light | 0.9990 | ❌ | 0.0400 | ❌ | ❌ |
| cited_outcome_hybrid_0.5 | 0.4895 | ✅ | 0.7265 | ✅ | ✅ |
| cited_outcome_hybrid_0.7 | 0.5180 | ✅ | 0.7320 | ✅ | ✅ |
| regeste_full_text_hybrid_0.5 | 0.9990 | ❌ | 0.0420 | ❌ | ❌ |
| regeste_full_text_hybrid_0.7 | 0.9990 | ❌ | 0.0410 | ❌ | ❌ |

**Fundamental tradeoff reproduced**: Citation-based representations PASS adversarial gates; text-based (full_text) FAIL due to language dominance.

### Citation Heritage (all 8 TF-IDF reps at 174k)

All representations **FAIL** recall@10 threshold (production default: 0.053). AUC values range 0.49–0.90, but positive pair recall@10 << 0.2 threshold.

### v17b Label Normalization (174k legal_area labels)

| Representation Family | Hierarchy Purity | Zoom Fine Purity | Legal Area Purity |
|----------------------|------------------|------------------|-------------------|
| Citation-based (3 reps) | ~1.0x (modest gains 3-10%) | ~0.88-0.89x (degradation) | ~1.0x |
| Text-based (4 reps) | ~1.0x | **0.66-0.84x** (significant degradation) | ~1.0x |
| Hybrid (1 rep: regeste_tfidf) | **1.0x** | **0.99x** (no worsening) | **1.002x** |

**regeste_tfidf** is the only representation with no worsening on ALL hierarchy metrics.

### Dense Embeddings (Partial Evaluations)

| Evaluation | Scale | Adversarial | Hierarchy | Legal Area | v17b Effect |
|------------|-------|-------------|-----------|------------|-------------|
| center_projected (64/128/768) | 12k (3 yrs) | FAIL (LangDom~0.98) | FAIL | FAIL | — |
| V6 dense (2000-2002) | 12,570 | FAIL (LangDom=0.99) | FAIL (0.42) | FAIL (0.009) | NO improvement |
| center_projected partial | 100k (15 yrs) | FAIL (LangDom~0.98) | — | — | — |

**Finding**: Dense embeddings cluster by language, not law, at all tested scales (12k–100k).

---

## Blockers (Unchanged from v28)

1. **Dense embeddings at 174k**: Only 3/26 years (2000-2002) ACCEPTED; years 2003-2014 pending audit promotion in legal-distance
2. **Citation role embeddings**: Not yet computed at 174k
3. **Linear hybrid embeddings**: Not yet computed at 174k
4. **Jurist human study**: Framework ready; requires 5-10 Swiss jurists (external dependency)

---

## Infrastructure Readiness (All VERIFIED)

| Component | Status | Notes |
|-----------|--------|-------|
| Formal suite script | OPERATIONAL | `run_174k_formal_suite.py` - exact reproduction verified |
| Scalable NN (exact k-NN + HNSW) | OPERATIONAL | Adversarial: exact on n=2000; full-corpus: HNSW |
| Citation heritage pipeline | READY | Frozen 137,314 pairs, 95.9% resolution |
| v17b normalization pipeline | READY | Differential effect reproduced |
| Metadata (174k) | VERIFIED | 173,963 entries, 100% branch+legal_area coverage |
| Monitor script | ACTIVE | check_count=242, last_check=2026-09-30T02:03:33Z |

---

## Factory Direction v29 Changes

Corrected from v28 (per audit of rejected Director proposal 36655613802):
- ✅ Corrected checkpoint progress: "15/26 years (2000-2014, ~100k decisions)" NOT "25/26 years (2000-2024, ~160k)"
- ✅ Removed non-existent audit gate citations
- ✅ Updated lane status assessments to reflect corrected questions
- ✅ Incremented factory_direction to v29

---

## Recommendation

**continue_recommended: false** — No additional same-question cycle justified. The TF-IDF 174k deliverable is complete and verified. The lane should remain in MONITORING until legal-distance produces:
1. 174k dense embeddings (concatenated from 26 years, post-audit)
2. Citation role embeddings at 174k
3. Linear hybrid embeddings at 174k

When new representations land, the frozen formal suite, citation heritage, and v17b pipelines are ready for immediate execution.

---

## Evidence References

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json`
- `evaluation/state/evaluation_state.json` (updated to v29)
- `evaluation/state/monitor_174k_state.json` (check_count=242)

---

*Report generated per Research Protocol §12: "Write machine-readable lane state plus human-readable report."*