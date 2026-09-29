# Evaluation Lane v28 Cycle Report
**Date:** 2026-09-29  
**Factory Direction:** v28  
**Lane Status:** MONITORING  
**Evidence Tier:** REPRODUCED  
**Continue Recommended:** YES (monitoring has concrete discriminating purpose)

---

## Executive Summary

The evaluation lane has **completed all machine-executable 174k formal suite tasks for currently available representations**. The TF-IDF family (8 representations) has been fully evaluated with the frozen v25 12-benchmark formal suite, citation heritage benchmark, and v17b label normalization test. All infrastructure is verified operational and the monitor is actively watching for new representations from legal-distance.

**No new production representations have landed since the last verification.** Dense embeddings remain at only 3/26 years ACCEPTED (2000-2002), with 22 years in checkpoints pending audit promotion.

---

## Work Completed (Frozen, Verified, Reproducible)

### 1. Full 12-Benchmark v25 Formal Suite at 174k Scale (8 TF-IDF Representations)
**Config Hash:** `4323f833fa72366a` (frozen protocol v25)  
**HNSW Parameters:** M=16, ef_construction=200, ef_search=100 (fixed)  
**Adversarial Artifact Fix:** Exact k-NN on stratified subsample (n=2000, seed=42) — CONFIRMED

| Representation | PASS | FAIL | SKIP | Adversarial (LangDom/Jurist) | Verdict |
|---|---:|---:|---:|---|---|
| `cited_decisions_tfidf` | 6 | 5 | 1 | **PASS/PASS** (0.602/0.354) | Citation-based |
| `cited_outcome_hybrid_0.5` | 6 | 5 | 1 | **PASS/PASS** (0.578/0.352) | Citation-based ⭐ Production Default |
| `cited_outcome_hybrid_0.7` | 6 | 6 | 0 | **PASS/PASS** (0.569/0.356) | Citation-based |
| `outcome_tfidf` | 3 | 9 | 0 | FAIL/FAIL (0.510/0.146) | — |
| `regeste_tfidf` | 5 | 7 | 0 | **PASS/PASS** (0.757/0.615) | Citation-based |
| `full_text_tfidf_light` | 7 | 5 | 0 | FAIL/FAIL (0.999/0.742) | Text-based |
| `regeste_full_text_hybrid_0.5` | 7 | 5 | 0 | FAIL/FAIL (0.998/0.956) | Text-based |
| `regeste_full_text_hybrid_0.7` | 7 | 5 | 0 | FAIL/FAIL (0.999/0.961) | Text-based |

**Fundamental Two-Mode Tradeoff REPRODUCED at 174k:**
- **Citation-based signals** (cited_decisions_tfidf + outcome hybrids): PASS adversarial gates, FAIL branch/tf_metadata/hierarchy/legal_area clustering
- **Text-based signals** (full_text, regeste, regeste+full_text hybrids): PASS branch/tf_metadata/hierarchy/legal_area, FAIL adversarial (language dominance ~0.999)

### 2. Citation Heritage Benchmark (Frozen 2,040 Pair Pool)
**Resolution:** 2,019/2,105 citation IDs resolved (95.9%)  
**Pair Pool:** 1,020 positive (direct + shared citations), 1,020 negative (balanced sampling, seed=42)

| Representation | AUC-ROC | nn_citation_rate@10 | Status (recall@10 ≥ 0.2) |
|---|---:|---:|---|
| `cited_decisions_tfidf` | 0.973 | 0.487 | **PASS AUC / FAIL recall@10** |
| `cited_outcome_hybrid_0.5` | 0.919 | 0.476 | **PASS AUC / FAIL recall@10** |
| `cited_outcome_hybrid_0.7` | 0.960 | 0.490 | **PASS AUC / FAIL recall@10** |
| `full_text_tfidf_light` | 0.844 | 0.438 | **PASS AUC / FAIL recall@10** |
| `regeste_full_text_hybrid_0.5` | 0.850 | 0.444 | **PASS AUC / FAIL recall@10** |
| `regeste_full_text_hybrid_0.7` | 0.865 | 0.445 | **PASS AUC / FAIL recall@10** |
| `regeste_tfidf` | 0.486 | 0.000 | FAIL/FAIL |
| `outcome_tfidf` | 0.720 | 0.003 | FAIL/FAIL |

**Finding:** All 8 representations FAIL the recall@10 threshold (0.2). Citation graph coverage is only 0.1% (174/173,963 decisions with direct/shared citations in pair pool). Citation-independent retrieval is near-zero for citation signals; text signals achieve high AUC but collapse on adversarial gates at full scale.

### 3. v17b Label Normalization Test (174k Fine-Grained legal_area)
**Normalization:** 85,819/173,963 labels normalized (49.3%), 214→164 unique areas (cross-lingual consolidation)  
**Differential Effect CONFIRMED at 174k:**

| Representation | Hierarchy Ratio | Zoom Fine Ratio | Legal Area Ratio | All Metrics Non-Worsening? |
|---|---:|---:|---:|---|
| `cited_decisions_tfidf` | 1.057 | 1.038 | 1.062 | ✓ |
| `cited_outcome_hybrid_0.5` | 1.056 | 1.037 | 1.063 | ✓ |
| `cited_outcome_hybrid_0.7` | 1.053 | 1.046 | 1.058 | ✓ |
| `outcome_tfidf` | 1.046 | 1.083 | 1.044 | ✓ |
| `regeste_tfidf` | 1.000 | 1.103 | 1.017 | ✓ **Only representation satisfying no-worsening on ALL metrics** |
| `full_text_tfidf_light` | 1.000 | **0.668** | 0.973 | ✗ (zoom_fine degrades 33%) |
| `regeste_full_text_hybrid_0.5` | 1.000 | **0.661** | 0.969 | ✗ (zoom_fine degrades 34%) |
| `regeste_full_text_hybrid_0.7` | 1.000 | **0.695** | 0.963 | ✗ (zoom_fine degrades 30%) |

**Finding:** Citation-based signals show uniform 3-10% purity gains across all hierarchy metrics. Text-based signals show hierarchy/legal_area stability but **zoom_fine DEGRADES 30-34%**. Uniform improvement claim is FALSE.

### 4. Infrastructure Verification (All OPERATIONAL)
- ✅ **Adversarial benchmarks:** Exact k-NN on stratified subsample n=2000 — production default reproduces LangDom=0.5167 PASS, Jurist=0.8050 PASS
- ✅ **Citation heritage pipeline:** Frozen 2,040 pair pool, 95.9% resolution — re-run verified
- ✅ **v17b normalization pipeline:** Differential effect reproduced across all 8 TF-IDF reps
- ✅ **HNSW artifact fix:** Exact k-NN on valid subset avoids HNSW masking representation differences — CONFIRMED
- ✅ **V25 formal suite runner:** Frozen protocol v25 executed on all 8 TF-IDF reps at 174k — VERIFIED
- ✅ **Monitor script:** ACTIVE — check_count=214, last_check=2026-09-29T00:17:30Z
- ✅ **Scalable NN:** sklearn exact k-NN for adversarial (n=2000 subsample), HNSW for full-corpus citation heritage

---

## Current Blockers (External Dependencies)

| Blocker | Status | Detail |
|---|---|---|
| **Dense embeddings 174k** | ⏳ PENDING AUDIT | Only 3/26 years (2000-2002) ACCEPTED; years 2003-2024 (22/26) in checkpoints pending audit promotion; years 2025-2026 not yet processed |
| **Citation role embeddings** | ⏳ NOT AVAILABLE | Citing/following/criticizing alpha0.3 not yet computed at 174k |
| **Linear hybrid embeddings** | ⏳ NOT AVAILABLE | `linear_citation_concat`, `linear_hybrid05_concat` not yet delivered at 174k |
| **Jurist human study** | 🔧 FRAMEWORK READY | Simulation infrastructure in `evaluation/tests/jurist_usability.py`; requires 5-10 Swiss jurists (external dependency) |

---

## Monitoring Status

**Monitor Check #214 completed:** 2026-09-29T00:17:30Z  
**Result:** No new awaited representations detected  

**Dense embeddings progress (checkpoints):**
- Completed years: 2000-2024 (25/26 years, 96.2% checkpoints, 100% decisions)
- **ACCEPTED years:** 2000-2002 only (3/26 years, ~19,441 decisions)
- Blocked on: years 2003-2024 pending audit promotion; years 2025-2026 not yet processed
- Monitor scans ONLY final concatenated directories in accepted state, NOT checkpoints

---

## Readiness for Next Representations

When legal-distance promotes dense embeddings, citation roles, or linear hybrids to accepted state, the evaluation lane is **ready to auto-evaluate**:

1. **Formal suite script:** `run_174k_formal_suite.py` operational (verified 2026-09-27, re-verified 2026-09-28)
2. **V25 formal suite runner:** Operational (verified 2026-09-27T22:04:04Z)
3. **Scalable NN infrastructure:** READY (exact k-NN for adversarial, HNSW for full-corpus)
4. **Citation heritage pipeline:** READY (frozen 2,040 pair pool, 95.9% resolution)
5. **v17b normalization pipeline:** READY
6. **Metadata 174k:** VERIFIED (173,963 entries, branch+legal_area 100% coverage)

---

## Next Recommendation

**CONTINUE MONITORING.** The lane is in active MONITORING mode with `continue_recommended=true` because monitoring has concrete discriminating purpose: auto-evaluate awaited representations (dense embeddings, citation roles, linear hybrids) as they land from legal-distance.

No additional same-question cycle is justified until new representations are promoted through the audit gate. The Factory Director should advance the legal-distance lane to complete audit promotion of the 22 years in checkpoints.

---

## Provenance & Reproducibility

- **Accepted Run ID:** `eval_174k_formal_suite_tfidf_complete_20260928_v28_reverified`
- **Frozen Config Hash (adversarial):** `b51701f5a9c11692`
- **Frozen Config Hash (v25 suite):** `4323f833fa72366a`
- **Global Seed:** 42
- **All raw outputs preserved** in `evaluation/results/174k_formal_suite/`, `evaluation/results/174k_citation_heritage/`, `evaluation/results/174k_label_normalization/`
- **Negative results preserved:** Citation heritage FAIL, v17b differential degradation, boilerplate resistance FAIL

---

*Report generated: 2026-09-29T00:18:00Z*