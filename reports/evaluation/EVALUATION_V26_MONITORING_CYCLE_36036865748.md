# Evaluation Lane Monitoring Cycle — Factory Direction v26

**GitHub Run:** 36036865748  
**Timestamp:** 2026-09-24T18:47:28Z  
**Lane:** evaluation  
**Direction Version:** 26  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** MONITORING_DEPENDENCIES  

---

## Executive Summary

The evaluation lane has **completed the v25 TF-IDF 174k formal suite question** (REPRODUCED, audit-ready) and is now **monitoring for dense 174k representations** from the legal-distance lane (gh run 35935612800 active). All evaluation infrastructure is frozen, validated, and operational. No additional same-question cycle on TF-IDF representations is justified.

---

## v25 Question Status: COMPLETED & REPRODUCED

### 174k Formal Suite Execution (eval_v25_174k_formal_suite_36013963912)
- **Representations evaluated:** 8 TF-IDF-family representations at full 174k scale
  - `cited_decisions_tfidf` — 6 PASS / 6 FAIL
  - `outcome_tfidf` — 3 PASS / 9 FAIL
  - `regeste_tfidf` — 5 PASS / 7 FAIL
  - `full_text_tfidf_light` — 7 PASS / 5 FAIL
  - `cited_outcome_hybrid_0.5` — 6 PASS / 6 FAIL
  - `cited_outcome_hybrid_0.7` — 6 PASS / 6 FAIL
  - `regeste_full_text_hybrid_0.5` — 7 PASS / 5 FAIL
  - `regeste_full_text_hybrid_0.7` — 7 PASS / 5 FAIL
- **All 12 frozen benchmarks executed** with unchanged thresholds (config hash: `4323f833fa72366a`)
- **Citation heritage validated:** 137,314 positive + 137,314 negative pairs at 174k scale
  - `cited_outcome_hybrid_0.5`: AUC=0.919341 PASS (supersedes prior AUC=0.482 FAIL on broken row alignment)
  - `cited_outcome_hybrid_0.7`: AUC=0.960489 PASS
- **v17b label normalization at 174k:** Label level confirmed (213→163 unique labels, 23.5% reduction, 49.3% changed, 32 cross-lingual canonical concepts). Clustering test pending dense embeddings.

### Independent Verification (REPRODUCED Tier)
- **Bitwise-exact embedding rebuild** from pinned parquet: max_abs_diff=0.0 for all 8 `.npy` files
- **7/7 conformance checks PASS** (`tests/evaluation/test_v25_174k_suite_snapshot.py`)
- **Provenance gate hardened & verified** (eval_v25_provenance_gate_36035803010): 12/12 pytest PASS, catches copy-defect class mechanically

---

## Current Dependencies: BLOCKED on Legal-Distance Dense 174k Representations

| Priority | Representations | Status |
|----------|-----------------|--------|
| **1. TF-IDF Signals** | 8 representations (already evaluated) | ✅ **COMPLETE** in accepted state |
| **2. Dense Embeddings** | `center_projected_768dim`, `center_projected_64dim`, `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1` | ⏳ **ACTIVE** — legal-distance gh run 35935612800 executing year-split CPU computation |
| **3. Citation Roles** | `citing/following/criticizing/distinguishing/overruling_alpha0.3` | ⏳ **PENDING** — after dense embeddings |

**Legal-distance lane** is actively running staged 174k computation:
1. Year-split artifact regeneration via proven `reproduce_full_corpus.py` (~100s)
2. CPU-cheap TF-IDF/citation/outcome signals (Priority 1) — **already delivered**
3. Dense embeddings year-split with resumable checkpoints within 65-min job ceilings (Priority 2) — **IN PROGRESS**

---

## Infrastructure Readiness: FROZEN & VALIDATED

All evaluation components are **operational and config-hash verified**:

| Component | Status | Config Hash |
|-----------|--------|-------------|
| Frozen Harness v3 | OPERATIONAL (exact reproduction confirmed) | `a31c443a9b0e992e` |
| Scalable NN (HNSW) | OPERATIONAL (validated at 174k scale, 90k+ decisions) | — |
| Full Corpus Harness | VALIDATED at 1200 scale (exact adversarial match) | `4047da047fb339c1` |
| V16 Benchmark Suite | IMPLEMENTED (12 benchmarks, frozen thresholds) | `4323f833fa72366a` |
| Citation Heritage 174k | READY (137,314 pos + 137,314 neg pairs) | — |
| v17b Normalization 174k | LABEL LEVEL CONFIRMED | — |
| Distributed Evaluation | SUPPORTED (model-level sharding) | — |
| Auto-Monitor Script | OPERATIONAL | — |

**Corpus readiness confirmed:** 173,963 decisions (90,632 with known branch, 91,193 with legal_area)

---

## Monitor Check — 2026-09-24 18:47:28

**Script:** `evaluation/monitor_and_evaluate_174k.py`  
**Watch Path:** `/tmp/lex_accepted/legal-distance/legal_distance/results/v5`

**Result:** No 174k dense representation directories found yet. Priority 1 TF-IDF representations were already evaluated and accepted (v25 cycle). Monitor correctly reports all Priority 2/3 representations as not yet available.

---

## Negative Results Preserved (Per Research Protocol)

| Benchmark | Result | Note |
|-----------|--------|------|
| Boilerplate Resistance | NEGATIVE (~ -0.9) | Measures language dominance, not procedural boilerplate |
| Hierarchy Coherence | NEGATIVE | v18 confirmed fundamental branch-level limitation (purity ~0.65) |
| Zoom Coherence | NEGATIVE | No improvement from coarse to fine at branch level |
| Legal Area Clustering | NEGATIVE | Fine-grained label granularity prevents purity > 0.5 |
| Citation Heritage (TF-IDF) | SUPERSEDED | Prior AUC=0.482 on broken alignment; frozen protocol gives AUC=0.919 PASS |
| center_projected_768 | FAIL | Jurist pairwise gate 0.4912 < 0.5 (confirmed across all verifications) |

---

## Production Decision Gates (Unchanged)

| Gate | Requirement | Status |
|------|-------------|--------|
| `PRODUCT_SERVING_DEFAULT_cited_outcome_hybrid_0.5` | Pass BOTH adversarial gates at 174k | Awaiting dense reps |
| `COMBINATION_MODE_linear_hybrid05_concat` | Pass BOTH adversarial gates + stability test at 174k | Awaiting dense reps |
| `DEFAULT_map_mode_center_projected_64dim_hierarchical` | Re-verify PASS both gates at 174k | Validated at 1200; 174k pending |

---

## External Blockers

| Blocker | Status |
|---------|--------|
| Jurist Human Study | Framework ready; externally blocked (requires 5–10 Swiss jurists recruited by repository owner) |

---

## Next Recommendation

**MONITORING_DEPENDENCIES** — The v25 TF-IDF question is **COMPLETED and REPRODUCED**. The evaluation lane will:

1. **Continue monitoring** `/tmp/lex_accepted/legal-distance/legal_distance/results/v5` for dense 174k representation directories
2. **Auto-execute** the full 12-benchmark suite + citation heritage + v17b clustering test when Priority 2/3 representations land in accepted state
3. **Report results** with full provenance (config hashes, embedding hashes, frozen thresholds)

**No additional same-question cycle on TF-IDF representations is justified** (question fully answered at 174k). Factory Director should await legal-distance delivery of dense 174k representations in accepted state before authorizing the next evaluation cycle.

---

## Evidence References

- `state/evaluation.json` — Updated to direction_version 26
- `evaluation/monitor_and_evaluate_174k.py` — Operational monitoring script
- `results/evaluation/v25_174k_formal_suite/` — 174k TF-IDF suite execution artifacts
- `results/evaluation/v25_174k_provenance_gate_36035803010/` — Provenance gate verification
- `tests/evaluation/test_v25_174k_suite_snapshot.py` — 7/7 conformance checks
- `/tmp/lex_accepted/legal-distance/state/legal-distance.json` — Legal-distance accepted state (v10, REPRODUCED)

---

*Generated by evaluation lane monitoring cycle per Research Protocol step 12: "Write machine-readable lane state plus human-readable report."*