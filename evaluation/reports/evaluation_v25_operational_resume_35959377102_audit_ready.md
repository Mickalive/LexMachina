# Evaluation Lane v25 — Operational Resume Audit-Ready Report

**Factory Direction:** v25  
**Lane:** evaluation  
**GitHub Run:** 35959377102  
**Timestamp:** 2026-09-24T05:27:00Z  
**Status:** BLOCKED_ON_DEPENDENCIES  
**Evidence Tier:** ACCEPTED  
**Prior Snapshot:** Run 35955974732 (infrastructure re-verification)

---

## Executive Summary

This operational resume from persisted producer snapshot **run 35955974732** completes the evaluation lane's v25 cycle. All evaluation infrastructure for the 174k formal suite has been **re-verified, confirmed operational, and frozen**. The evaluation lane remains correctly statused as `BLOCKED_ON_DEPENDENCIES` awaiting 174k representations from the legal-distance lane (currently executing gh run 35935612800).

**No additional same-question cycle is justified.** Infrastructure is audit-ready for immediate execution when representations land in accepted state.

---

## Verifications Performed (This Cycle)

| Verification | Status | Details |
|--------------|--------|---------|
| Frozen Harness v3 Full Reproduction | ✅ PASS | Config hash `a31c443a9b0e992e` verified, all 6 representations match accepted state exactly |
| Frozen Harness v3 Config Hash Match | ✅ PASS | `a31c443a9b0e992e` matches canonical |
| Full Corpus Harness --force-exact 1200 Match | ✅ PASS | Adversarial benchmarks match frozen harness exactly at 1200 scale |
| V17b Label Normalization All-Reps Uniformity | ✅ PASS | Uniform improvement confirmed across all 6 representations (788 labels normalized) |
| Citation Heritage 174k Infrastructure | ✅ READY | 1,020 positive + 1,020 negative pairs ready for 174k embeddings |
| Scalable NN (HNSW) | ✅ OPERATIONAL | hnswlib available, validated at 1200 with force_exact |
| Legal-Distance GH Run 35935612800 | ✅ CONFIRMED | Year-split TF-IDF computation in progress |

---

## Frozen Configuration Hashes (All Verified)

| Harness | Config Hash | Seed | Factory Direction |
|---------|-------------|------|-------------------|
| Frozen Adversarial Harness v3 | `a31c443a9b0e992e` | 42 | v6 (canonical) |
| Scalable Full Corpus Harness v3 | `4047da047fb339c1` | 42 | v10 |
| V16 Full Benchmark Suite | `4323f833fa72366a` | 42 | v13 |

**All three config hashes match the accepted state exactly.**

---

## Frozen Harness v3 Reproduction Results

**6 representations tested, 5 pass both adversarial gates, 1 fails jurist pairwise**

| Representation | Verdict | Lang Dominance | Jurist Preference | Both Gates |
|----------------|---------|----------------|-------------------|------------|
| linear_metric_epoch4 | PASS | 0.6805 | 0.6847 | ✅ |
| mahalanobis_metric_epoch4 | PASS | 0.6843 | 0.6781 | ✅ |
| hybrid_stabilized_epoch1 | PASS | 0.6704 | 0.6656 | ✅ |
| hybrid_v2_epoch3 | PASS | 0.7115 | 0.5988 | ✅ |
| **center_projected_64dim (production default)** | **PASS** | **0.7664** | **0.5121** | ✅ |
| center_projected_768 | FAIL | 0.7738 | 0.4912 | ❌ |

**Exact match with accepted state:** All values match the frozen_harness_v3_reproduction verification from 2026-09-23T20:47:15Z.

---

## Full Corpus Harness --force-exact Validation (1200 scale)

| Representation | Verdict | Lang Dominance | Jurist Preference | Backend |
|----------------|---------|----------------|-------------------|---------|
| embeddings_center_projected_64 | PASS | 0.7664 | 0.5121 | sklearn_exact |
| embeddings_center_projected_128 | FAIL | 0.7725 | 0.4954 | sklearn_exact |
| embeddings_center_projected | FAIL | 0.7738 | 0.4912 | sklearn_exact |
| embeddings_768 | FAIL | 0.9541 | 0.0951 | sklearn_exact |

**Adversarial benchmarks match frozen harness exactly.** Scale stability differs slightly (0.7658 vs 0.7071) due to different random split in scale stability test, but this is expected and does not affect adversarial gate results.

---

## V17b Label Normalization Re-verification (1200 scale)

**Uniform improvement confirmed across ALL 6 production representations**

| Representation | Hierarchy Ratio | Zoom Fine Ratio | Legal Area Ratio |
|----------------|-----------------|-----------------|------------------|
| center_projected_64dim | 1.2018 | 1.2233 | 1.1476 |
| cited_outcome_hybrid_0.5 | 1.2145 | 1.2041 | 1.1514 |
| linear_citation_concat | 1.1891 | 1.1941 | 1.1273 |
| **linear_hybrid05_concat (production default)** | **1.2401** | **1.2768** | **1.1528** |
| linear_citation_w3070 | 1.1559 | 1.1798 | 1.13 |
| linear_citation_ridge | 1.194 | 1.2145 | 1.1524 |

**Key finding:** Zero representations worsened by >10% (`representations_worsened_by_gt10pct: {}`). The v16 hierarchy-family FAIL was a **shared label artifact**, not representation-specific.

---

## Citation Heritage 174k Infrastructure Re-verification

| Metric | Value |
|--------|-------|
| Positive pairs (direct + shared citations) | 1,020 |
| Negative pairs (sampled no-relation) | 1,020 |
| Citation resolution rate | 95.9% (2,019/2,105) |
| Decisions in citation graph | 174 |
| Decisions with outgoing citations | 174 |
| Resolved citations mapping to 174k corpus | 924 |
| Corpus decisions | 173,963 |

**Benchmark executable when 174k embeddings available.** Previous execution on cited_outcome_hybrid_0.5_174k (from cycle branch) returned FAIL (AUC=0.482, threshold=0.65) — TF-IDF hybrid does not recover citation proximity at 174k scale. Dense embeddings required.

---

## Infrastructure Readiness Status

| Component | Status | Notes |
|-----------|--------|-------|
| Frozen Harness v3 | OPERATIONAL | Config hash verified, exact reproduction confirmed |
| Scalable NN (HNSW) | OPERATIONAL | hnswlib available, validated at 1200 with force_exact |
| Full Corpus Harness | VALIDATED | 1200 scale, exact adversarial match with frozen v3 |
| V16 Benchmark Suite | IMPLEMENTED | 12 benchmarks, frozen thresholds, config hash verified |
| Citation Heritage 174k | READY | 1,020 positive + 1,020 negative pairs rebuilt |
| V17b Normalization 174k | LABEL LEVEL CONFIRMED | 214→164 labels, 32 cross-lingual concepts; clustering pending embeddings |
| Distributed Evaluation | SUPPORTED | Model-level sharding via DistributedEvaluator |

---

## Awaiting From Legal-Distance Lane

### Priority 1: CPU-Cheap TF-IDF/Citation/Outcome Signals
- `cited_decisions_tfidf`
- `outcome_tfidf`
- `cited_outcome_hybrid_0.5`
- `cited_outcome_hybrid_0.7`
- `linear_citation_concat`
- `linear_hybrid05_concat` (PRODUCTION DEFAULT COMBINATION_MODE)
- `linear_citation_w3070`
- `linear_citation_ridge`

### Priority 2: Dense Embeddings
- `center_projected_768dim`
- `center_projected_64dim` (PRODUCTION DEFAULT map mode)
- `linear_metric_epoch4`
- `mahalanobis_metric_epoch4`
- `hybrid_stabilized_epoch1`

### Priority 3: Citation Role Embeddings
- `citation_role_citing_alpha0.3`
- `citation_role_following_alpha0.3`
- `citation_role_criticizing_alpha0.3`
- `citation_role_distinguishing_alpha0.3`
- `citation_role_overruling_alpha0.3`

**Legal-distance is actively executing gh run 35935612800 with year-split computation.**

---

## Negative Results Preserved (Per Research Protocol)

| Benchmark | Result | Note |
|-----------|--------|------|
| Boilerplate resistance | NEGATIVE (~ -0.9) | Measures language dominance, not procedural boilerplate |
| Hierarchy coherence | NEGATIVE | v18 confirmed fundamental branch-level limitation (purity ~0.65) |
| Zoom coherence | NEGATIVE | No improvement from coarse to fine at branch level |
| Legal area clustering | NEGATIVE | Fine-grained label granularity prevents purity > 0.5 |
| Citation heritage on TF-IDF | NEGATIVE (AUC=0.482) | TF-IDF cannot recover citation proximity at 174k scale |
| center_projected_768 | FAILS jurist gate | 0.4912 < 0.5 threshold — confirmed across all verifications |

These negative results are **first-class evidence** and must not be suppressed.

---

## Production Decision Gates (When Representations Land)

| Gate | Requirement |
|------|-------------|
| PRODUCT_SERVING_DEFAULT (`cited_outcome_hybrid_0.5`) | Must pass BOTH adversarial gates at 174k |
| COMBINATION_MODE (`linear_hybrid05_concat`) | Must pass BOTH adversarial gates + stability test at 174k |
| DEFAULT Map Mode (`center_projected_64dim_hierarchical`) | Validated PASS both gates at 1200, must re-verify at 174k |

---

## External Blocker

**Jurist Human Study:** Framework ready, externally blocked (requires 5-10 Swiss jurists recruited by repository owner). Report as blocked when reachable.

---

## Orchestration/Validation Failure Diagnosis

The prior workflow (run 35955974732) completed successfully — it was a re-verification cycle that confirmed all infrastructure operational. The "failure" is not in evaluation infrastructure but in the **cross-lane dependency**: legal-distance lane has not yet delivered 174k representations in accepted state.

**Root cause:** Legal-distance year-split computation at 174k scale (gh run 35935612800) is still in progress. Evaluation lane correctly remains BLOCKED_ON_DEPENDENCIES per factory direction v25.

**No evaluation-side defect exists.** All three v25 sub-questions have READY infrastructure:
1. Full 12-benchmark formal suite at 174k → READY (harness validated, config frozen)
2. Citation heritage benchmark at 174k → READY (1,020 pairs, 95.9% resolution)
3. V17b label normalization clustering test at 174k → READY (labels normalized, clustering pending embeddings)

---

## Conclusion

**Evaluation infrastructure is FROZEN, VALIDATED, and AUDIT-READY for 174k execution.**

The evaluation lane is correctly statused as `BLOCKED_ON_DEPENDENCIES` with `continue_recommended: false`. No additional same-question cycle is justified. The Factory Director should await legal-distance delivery of 174k representations in accepted state before authorizing the next evaluation cycle.

All valid completed work preserved. All negative results preserved. All config hashes verified. Snapshot is audit-ready.

---

*Generated: 2026-09-24 | Factory Direction v25 | Evaluation Lane State: BLOCKED_ON_DEPENDENCIES | Evidence Tier: ACCEPTED*