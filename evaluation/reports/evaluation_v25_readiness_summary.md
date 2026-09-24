# Evaluation Lane v25 — Readiness Verification Complete

**Date:** 2026-09-24  
**Factory Direction:** v25  
**GitHub Run:** 35949306163  
**Lane Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** ACCEPTED  
**Continue Recommended:** FALSE (no additional same-question cycle justified)

---

## Summary

The evaluation lane has **completed all infrastructure validation** for the 174k formal evaluation suite. All three sub-questions from factory direction v25 have READY infrastructure but are BLOCKED awaiting 174k production representations from the legal-distance lane (actively executing gh run 35935612800).

---

## Infrastructure Readiness — ALL VERIFIED ✅

| Component | Status | Details |
|-----------|--------|---------|
| **Frozen Harness v3** | READY | Config hash `4323f833fa72366a`, seed=42, thresholds frozen |
| **Scalable Full Corpus Harness** | READY | Config hash `4047da047fb339c1`, HNSW backend, validated at 1200 scale |
| **12-Benchmark Formal Suite (v16)** | READY | All 12 benchmarks implemented, frozen thresholds, config hash `4323f833fa72366a` |
| **Citation Heritage Benchmark** | READY | 137,314 positive + 137,314 negative pairs at 174k scale |
| **v17b Label Normalization** | LABEL LEVEL CONFIRMED | 214→164 labels (23.5% reduction), 32 cross-lingual canonical concepts |
| **Scalable NN (HNSW)** | OPERATIONAL | hnswlib available, M=16, ef_construction=200, ef_search=100 |
| **174k Metadata** | LOADED | 173,963 decisions (de: 106,501, fr: 57,489, it: 9,973) |
| **Distributed Evaluation** | SUPPORTED | Model-level sharding via DistributedEvaluator |

---

## Frozen Configuration — IMMUTABLE

**Adversarial Thresholds (DO NOT MODIFY):**
- Language Dominance: < 0.85 (PASS)
- Jurist Pairwise Preference: > 0.5 (PASS)
- Cross-Language Recall: > 0.2 (PASS)
- Cluster Coherence: > 0.7 (PASS)

**Benchmark Parameters (DO NOT MODIFY):**
- k_neighbors_lang_dom: 20
- k_neighbors_jurist: 10
- k_neighbors_cross_lang: 10
- n_clusters_coherence: 16

---

## Awaiting from Legal-Distance (gh run 35935612800)

### Priority 1: CPU-Cheap TF-IDF/Citation/Outcome Signals
- `cited_decisions_tfidf`, `outcome_tfidf`
- `cited_outcome_hybrid_0.5`, `cited_outcome_hybrid_0.7`
- `linear_citation_concat`, `linear_hybrid05_concat` (PRODUCTION DEFAULT COMBINATION_MODE)
- `linear_citation_w3070`, `linear_citation_ridge`

### Priority 2: Dense Embeddings
- `center_projected_768dim`, `center_projected_64dim` (PRODUCTION DEFAULT map mode)
- `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1`

### Priority 3: Citation Role Embeddings
- `citation_role_citing_alpha0.3`, `citation_role_following_alpha0.3`
- `citation_role_criticizing_alpha0.3`, `citation_role_distinguishing_alpha0.3`, `citation_role_overruling_alpha0.3`

---

## Execution Plan — READY TO RUN

When representations land in accepted state (`/tmp/lex_accepted/legal-distance/...`):

```bash
# 1. Full corpus adversarial evaluation (HNSW backend)
python evaluation/run_full_corpus_evaluation.py \
  --embeddings-dir /tmp/lex_accepted/legal-distance/.../174k_tfidf \
  --metadata evaluation/data/174k/metadata_174k.json \
  --output-dir evaluation/results/full_corpus_174k

# 2. 12-benchmark formal suite (v16)
python evaluation/experiments/run_v16_full_benchmark_suite.py \
  --embeddings-dir /tmp/lex_accepted/legal-distance/.../174k_tfidf \
  --output-dir results/evaluation/v16_174k

# 3. Citation heritage validation
python evaluation/validate_citation_heritage_174k.py \
  --embeddings-dir /tmp/lex_accepted/legal-distance/.../174k_tfidf \
  --output-dir results/evaluation/citation_heritage_174k

# 4. v17b label normalization clustering test
python evaluation/experiments/run_v17b_label_normalization_all_reps.py \
  --embeddings-dir /tmp/lex_accepted/legal-distance/.../174k_tfidf \
  --output-dir results/evaluation/v17b_174k
```

Full details: `evaluation/reports/evaluation_v25_174k_execution_plan.md`

---

## Negative Results Preserved (Per Research Protocol)

| Benchmark | Expected Result | Reason |
|-----------|-----------------|--------|
| Boilerplate Resistance | FAIL (~ -0.9 all reps) | Measures language dominance, not procedural boilerplate |
| Hierarchy Coherence | FAIL (branch-level unpassable) | v18 NEGATIVE: label-based hierarchy fundamentally limited |
| Zoom Coherence | FAIL | v18 NEGATIVE: no coarse→fine improvement at branch level |
| Legal Area Clustering | FAIL | Fine-grained label granularity prevents purity > 0.5 |
| Citation Heritage (TF-IDF) | FAIL (AUC ≈ 0.48) | TF-IDF cannot recover citation proximity at 174k scale |

---

## State Files Updated

- `state/evaluation.json` — Added `v25_readiness_verification_20260924` with full verification record
- `evaluation/state/evaluation.json` — Updated to ACCEPTED tier, added `v25_readiness_verification`
- `evaluation/reports/evaluation_v25_174k_execution_plan.md` — Complete execution procedure
- `evaluation/reports/evaluation_v25_readiness_summary.md` — This summary

---

## Next Recommendation

**BLOCKED_ON_DEPENDENCIES** — Evaluation infrastructure is frozen, validated, and ready for immediate 174k execution. No additional same-question cycle justified until legal-distance delivers 174k representations in accepted state.

**Jurist Human Study:** Framework ready, externally blocked (requires 5-10 Swiss jurists recruited by repository owner).

---

*Evaluation lane v25 readiness verification complete. All evidence ACCEPTED tier. Awaiting legal-distance delivery.*