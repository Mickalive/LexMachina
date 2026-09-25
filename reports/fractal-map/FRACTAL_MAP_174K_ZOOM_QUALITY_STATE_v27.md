# Fractal Map Lane — 174k Zoom Quality State Report (Factory Direction v27)

**Date:** 2026-09-25  
**Lane:** fractal-map  
**Direction Version:** 27  
**Evidence Tier:** ACCEPTED (TF-IDF 174k evaluation) / BLOCKED (dense embeddings)  
**Cycle Status:** COMPLETED_TFIDF / BLOCKED_ON_DEPENDENCY  

---

## Executive Summary

The fractal-map lane has **completed all evaluable work for the TF-IDF 174k family** and is **blocked on a single dependency**: `legal-distance_174k_dense_embeddings`. No additional same-question cycle is justified.

### Current Status

| Component | Status | Evidence |
|-----------|--------|----------|
| TF-IDF 174k zoom-quality evaluation | ✅ COMPLETE | v26 evaluation: 0/4 modes PASS; all FAIL monotonic zoom-refinement |
| Hierarchical Leiden test at 174k | ✅ COMPLETE | Over-fragmentation persists (median cluster size = 1) despite zoom improvement |
| Citation-role 1000-scale zoom quality | ✅ CONFIRMED | citing_alpha0.3 ZQ=0.5401, following=0.5280, criticizing=0.4864 |
| Dense embeddings evaluation harness | ✅ READY | `evaluate_174k_dense_embeddings.py` verified against v26 TF-IDF results |
| 174k metadata (ACCEPTED) | ✅ AVAILABLE | 173,963 entries, branch+legal_area 100% coverage |
| Legal-distance 174k dense embeddings | 🔴 BLOCKED | Only year 2000 delivered; years 2001-2025 missing corpus artifacts |

---

## Key Findings

### 1. TF-IDF 174k Modes Encode Strong Legal Structure but Fail Zoom Refinement

**Evidence:** v26 frozen evaluation (run 36035695081, audit PASS CYCLE_36035695081_GATE.json)

| Mode | Branch Mono (res3>res0.25) | Area Mono | Improvement Rate >0.5 on ≥2/4 | Verdict |
|------|---------------------------|-----------|-------------------------------|---------|
| cited_decisions_tfidf_outcome_hybrid_0.5_174k | ❌ 0.5525→0.5273 | ❌ | ❌ (1/4) | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25 | ❌ 0.5491→0.5204 | ❌ | ❌ (1/4) | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25 | ❌ 0.5525→0.5273 | ❌ | ❌ (1/4) | FAIL |
| regeste_tfidf_174k | ❌ 0.3452→0.3434 | ✅ | ❌ (1/4) | FAIL |

**Structure signal is strong:** Branch purity 0.51-0.55 vs random baseline 0.25; legal_area purity 0.24-0.31 vs random ~0.005.

**But zoom refinement fails:** Fine ladder over-fragmented (median cluster size = 1, singleton fraction = 0.9956 at res_3.0).

### 2. Hierarchical Leiden Does Not Fix Over-Fragmentation at 174k

**Evidence:** `test_hierarchical_leiden_174k.py` run on cited_decisions_tfidf_outcome_hybrid_0.5_174k

| Config | Coarse Clusters | Fine Clusters | Coarse Branch Pur | Fine Branch Pur | Zoom Imp Rate | Fine Median Size |
|--------|----------------|---------------|------------------|----------------|---------------|-----------------|
| coarse_0.25_sub_2.0 | 22 | 83,844 | 0.337 | 0.392 | **0.947** | **1.0** (singleton 0.996) |

**Root cause:** One massive coarse cluster (83,089 decisions = 48% of corpus) fragments into 83,089 singletons at sub_res=2.0. The TF-IDF embedding space has a structurally skewed cluster distribution that no clustering algorithm can fix without better representations.

### 3. Evidence-Backed Zoom Path: Citation-Role / Dense Embedding Modes

**Evidence:** zoom_quality_diagnostic.py at 1000-scale (run 36083220945, audit PASS)

| Rank | Mode | Zoom Quality Score | Mean Purity Δ | Meaningful Split Rate |
|------|------|-------------------|---------------|----------------------|
| 1 | **citing_alpha0.3** | **0.5401** | +0.1212 | 80.0% |
| 2 | **following_alpha0.3** | **0.5280** | +0.1214 | 66.7% |
| 3 | **criticizing_alpha0.3** | **0.4864** | +0.1215 | 50.0% |
| 4 | cited_decisions_tfidf_hybrid_cp64_0.7 | 0.4781 | +0.0683 | 83.3% |
| ... | ... | ... | ... | ... |
| 21 | cited_decisions_tfidf_outcome_hybrid_0.5 (prod default) | 0.2798 | -0.0010 | 33.7% |

**Citation-role modes (citing/following/criticizing_alpha0.3) are the top 3 by zoom quality**, significantly outperforming the production default TF-IDF hybrid.

### 4. Nesting Metric Defect Documented and Corrected

**NESTING_METRIC_DEFECT_v1** (audit CYCLE_36027099305_GATE.json, PASS):
- Parameterized builders recorded `mean_nesting_score` as majority-parent **coverage** (~1.0 by construction), not strict nesting
- 37/46 audited modes over-claimed 1.0 vs honest strict nesting 0.04-1.0
- **Compressed 5-level ladder [0.25, 0.5, 1.0, 2.0, 3.0] does NOT preserve strict nesting** (honest mean change -0.00364, range [-0.0556, +0.1150], 21/22 modes nonzero)
- **nesting_score=1.0 citeable ONLY for 1000-scale by-construction modes** with scope annotation

---

## Infrastructure Readiness for Dense Embeddings

| Component | Status | Notes |
|-----------|--------|-------|
| ACCEPTED 174k metadata | ✅ Ready | `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries) |
| Parameterized builder | ✅ Fixed | Branch from chamber field; 'unknown' excluded; validated at 1000-scale |
| Evaluation harness | ✅ Verified | `evaluate_174k_dense_embeddings.py` reproduces v26 FAIL verdicts |
| Compressed 5-level ladder | ✅ Validated | 100% purity delta retention, identical zoom navigation at shared resolutions |
| Citation-role 174k validation | 🔴 BLOCKED | Placeholder builds (bger_placeholder_* IDs); row→id alignment unrecoverable (0.426 vs ~1.0 expected) |

---

## Blocker Analysis

### Primary Blocker: legal-distance_174k_dense_embeddings

**Status:** Only year 2000 delivered (3,839 decisions, 768-dim embeddings validated). Years 2001-2025 failed due to missing corpus artifacts (`/tmp/lex_accepted/corpus/.../bger_YYYY.jsonl` and `metadata_174k.jsonl` do not exist).

**Evidence:** CYCLE_36096850301_GATE.json (PASS, DATA_BLOCKED_NEGATIVE_RESULT) — honest record of external dependency failure.

**Resolution Path:** Corpus lane must deliver year-split normalized JSONL files. Legal-distance year-split computation is staged and ready.

### Secondary Blocker: Citation-Role 174k Validation

**Status:** Placeholder-keyed builds only. Requires full corpus JSONL delivery from corpus lane for row→id alignment.

---

## Recommendations

### For Factory Director (Next Direction)

1. **Legal-distance priority:** Complete 174k dense embeddings year-split computation (unblocks fractal-map, evaluation, product)
2. **Corpus priority:** Deliver year-split normalized JSONL artifacts to `/tmp/lex_accepted/corpus/...` mount paths
3. **Fractal-map:** No same-question cycle justified. Resume when dense embeddings land.
4. **Evaluation:** Auto-evaluate dense embeddings via `monitor_and_evaluate_174k.py` when available
5. **Product:** Wire production defaults (`cited_outcome_hybrid_0.5`, `linear_hybrid05_concat`, `center_projected_64dim_hierarchical`) to full-corpus artifacts as they land

### For Fractal Map Lane (When Unblocked)

1. Run `evaluate_174k_dense_embeddings.py` on all dense embedding modes (center_projected 768/64/128, metric learning, hybrid objectives, citation roles, linear hybrids)
2. Test citation-role embeddings at 174k scale (closest proxy: 1000-scale ZQ 0.54 → 0.49)
3. Validate hierarchical Leiden with dense embeddings (1000-scale: perfect nesting + hierarchical advantage)
4. Multi-view zoom UI already implemented with citation-role views (audit recommendation #4 satisfied)

---

## Negative Results Preserved (First-Class Evidence)

- ❌ **TF-IDF 174k zoom refinement:** No mode passes monotonic zoom-refinement checks
- ❌ **Hierarchical Leiden at 174k:** Over-fragmentation persists (singleton fraction 0.996) despite zoom improvement
- ❌ **Compressed ladder strict nesting:** Does NOT universally preserve nesting (honest mean change -0.00364)
- ❌ **Citation-role 174k:** Placeholder builds only; validation blocked by corpus artifact gap
- ❌ **Production default at 174k:** outcome_hybrid_0.5 ZQ=0.2798 (1000-scale), FAIL at 174k

---

## Provenance & Reproducibility

| Artifact | Path | Hash/Ref |
|----------|------|----------|
| v26 Frozen Spec | `results/fractal_map/zoom_quality_174k_eval/v26_frozen_spec.json` | config hash `4323f833fa72366a` |
| v26 Verdict | `results/fractal_map/zoom_quality_174k_eval/v26_verdict.json` | run 36035695081 |
| Zoom Quality Diagnostic | `results/fractal_map/evaluation/zoom_quality_diagnostic_results.json` | run 36083220945 |
| Hierarchical Leiden Test | `results/fractal_map/hierarchical_174k_test/hierarchical_leiden_174k_all_results.json` | run 20260925_023152 |
| Dense Embeddings Harness | `fractal_map/evaluation/evaluate_174k_dense_embeddings.py` | verified vs v26 |
| 174k Census | `results/fractal_map/legal_distance_modes/174k_CENSUS_v26_frozen_spec.json` | 4 true-174k, 2 placeholder, 6 misnamed 21k |
| ACCEPTED Metadata | `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` | 173,963 entries |

All claim-bearing outputs frozen before outcome inspection. Negative results preserved as first-class evidence per Research Protocol.

---

## State Update

```json
{
  "lane": "fractal-map",
  "direction_version": 27,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED_ON_DEPENDENCY",
  "continue_recommended": false,
  "blocked_on": "legal-distance_174k_dense_embeddings",
  "tfidf_174k_completed": true,
  "dense_embeddings_awaited": true,
  "next_recommendation": "BLOCKED on legal-distance_174k_dense_embeddings. Resume when dense embeddings delivered. No same-question cycle justified."
}
```