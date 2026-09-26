# Evaluation v27: 174k Monitor Update and Infrastructure Fix

**Lane:** evaluation  
**Factory Direction:** v27  
**Status:** TF-IDF family COMPLETE; dense embeddings BLOCKED_ON_DEPENDENCIES; monitor infrastructure FIXED  
**Date:** 2026-09-26  
**Run ID:** eval_v27_174k_monitor_fix_20260926

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions for the TF-IDF family at 174k scale** and is now **blocked on legal-distance dense embeddings** (3/26 years complete). The monitor infrastructure has been **fixed to correctly detect representations in accepted mounts** and will auto-evaluate awaited representations when they land.

| Sub-Question | Status | Representations Tested | Key Result |
|--------------|--------|----------------------|------------|
| **1. 12-Benchmark Formal Suite** | ✅ COMPLETE | 8/8 TF-IDF | No representation passes all 12. Citation-aware excel at citation_heritage/adversarial/multilingual; text-based excel at branch_knn/tf_metadata/boilerplate. **ALL fail hierarchy_coherence** (max purity 0.465 vs 0.7). |
| **2. Citation Heritage (137k pairs)** | ✅ COMPLETE | 8/8 TF-IDF | 7/8 PASS. **cited_decisions_tfidf AUC=0.973**, nn_citation_rate@10=0.487. Only regeste_tfidf FAILS (AUC=0.487). |
| **3. v17b Label Normalization** | ✅ COMPLETE | 8/8 TF-IDF | **PARTIAL generalization**. 5/8 improve (46-64% purity gains); 3/8 unchanged; 0 worsen. Best normalized hierarchy_purity=0.47 < 0.7 threshold. |

**Critical Scale Finding (Confirmed & Fixed):** TF-IDF jurist pairwise preference **collapsed from 0.79 (1200-scale) → 0.12 (174k-scale)** in v3 adversarial harness. Root cause: **HNSW artifact** — HNSW with fixed parameters produced nearly identical k-NN graphs across all TF-IDF representations. **FIXED** by using exact k-NN on fixed stratified subsample (n=2000) for adversarial benchmarks; HNSW retained for full-corpus scale benchmarks.

---

## Monitor Infrastructure Fixes

### Problem
The monitor script (`monitor_and_evaluate_174k.py`) was:
1. Scanning incorrect paths for embeddings (looking in `/tmp/lex_accepted/legal-distance/results/fractal_map/` instead of `/tmp/lex_accepted/fractal-map/results/fractal_map/`)
2. Attempting to re-evaluate already-completed TF-IDF representations
3. Using mismatched representation names vs actual filenames

### Fixes Applied
1. **Corrected path scanning** — Now scans:
   - `/tmp/lex_accepted/fractal-map/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/` for TF-IDF
   - `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/` for dense embeddings
   - Legal-distance version directories for citation roles and linear hybrids

2. **Skip completed TF-IDF** — Monitor now only evaluates representations in `AWAITED_REPRESENTATIONS` list (dense, citation roles, linear hybrids)

3. **Aligned representation names** — Updated `EXPECTED_REPRESENTATIONS.completed_tfidf_174k` to match actual filenames (e.g., `cited_decisions_tfidf_outcome_hybrid_0.5`)

4. **Correct path mapping** — `execute_evaluation_suite` now maps found directories to correct filesystem paths

### Verification
Monitor run confirms:
- All 8 TF-IDF representations detected ✓
- 0 awaited representations detected (correct — none landed yet)
- No spurious evaluation attempts

---

## Current State

### TF-IDF Family (8 representations) — FULLY EVALUATED at 174k
All three sub-questions complete. Results preserved in:
- `evaluation/results/174k/formal_suite/` — 12-benchmark suite results
- `evaluation/results/evaluation/v25_174k_formal_suite/results/` — v25 suite per-representation
- `evaluation/results/evaluation/v25_174k_citation_heritage/` — citation heritage dedicated
- `evaluation/results/evaluation/v25_174k_v17b/` — v17b normalization comparison
- `evaluation/results/full_corpus_174k_tfidf/` — v3 adversarial harness (HNSW artifact fixed)

### Dense Embeddings 174k — IN PROGRESS (legal-distance lane)
| Year | Decisions | Status |
|------|-----------|--------|
| 2000 | 3,839 | ✅ Complete (checkpoint) |
| 2001 | 4,332 | ✅ Complete (checkpoint) |
| 2002 | 4,399 | ✅ Complete (checkpoint) |
| 2003–2025 | ~155,000 | ⏳ Pending |
| **Total** | **12,570 / 173,963** | **11.5% years, 11% decisions** |

**Location:** `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`
**Finalization:** Requires `finalize_174k_embeddings.py` to concatenate all 26 years and publish to `174k_dense_embeddings/` root (where monitor watches)

### Awaited Representations (11) — BLOCKED on legal-distance
| Category | Representations | Dependencies |
|----------|-----------------|--------------|
| **Dense (6)** | center_projected_768dim, center_projected_64dim, center_projected_128dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | full 174k dense embeddings finalized |
| **Citation Roles (3)** | citing_alpha0.3, following_alpha0.3, criticizing_alpha0.3 | legal-distance 174k citation role pipeline |
| **Linear Hybrids (2)** | linear_citation_concat, linear_hybrid05_concat | dense + citation embeddings available |

---

## Evaluation Readiness for Dense Embeddings

### Infrastructure Status: ✅ OPERATIONAL
| Component | Status | Notes |
|-----------|--------|-------|
| HNSW backend | ✅ OPERATIONAL | Tested on GitHub runners |
| Scalable NN module | ✅ OPERATIONAL | Batched processing with sklearn fallback |
| v25 formal suite runner | ✅ OPERATIONAL | 12-benchmark + citation_heritage + v17b, frozen config hash `4323f833fa72366a` |
| Citation heritage pairs | ✅ FROZEN | 137,314 pos + 137,314 neg, path fixed |
| v17b normalization | ✅ OPERATIONAL | Cross-lingual canonical map |
| Monitor script | ✅ ACTIVE | Enhanced scan, correct paths, check_count=114 |
| run_174k_formal_suite.py | ✅ OPERATIONAL | HNSW artifact fixed (exact k-NN on valid subset) |

### Evaluation Protocol (Frozen, Ready to Execute)
When dense embeddings land in `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/`:
1. **Monitor detects** new .npy files in `174k_dense_embeddings/` root
2. **Auto-executes** for each awaited representation:
   - Full corpus adversarial evaluation (v3 harness, exact k-NN on valid subset)
   - v25 formal suite (12-benchmark + citation_heritage + v17b)
3. **Results saved** to `evaluation/results/174k_formal_suite/`
4. **State updated** in `evaluation/state/monitor_174k_state.json` and `state/evaluation.json`

### Priority Evaluation Order (per factory direction v27)
1. **Metric learning / hybrid objectives first** (highest 1200-scale jurist pairwise: 0.60-0.68)
   - linear_metric_epoch4, mahalanobis_metric_epoch4
   - hybrid_stabilized_epoch1, hybrid_v2_epoch3
2. **Center projected variants** (center_projected_64dim validated at 1200-scale: JP=0.982)
3. **Citation role embeddings** (citing/following_alpha0.3 passed adversarial at 1200-scale)
4. **Linear hybrids** (linear_citation_concat REPRODUCED at v13/v14)

---

## Blockers and Dependencies

### Primary Blocker
**legal_distance_174k_dense_embeddings_not_in_accepted_state** — Year-split computation at 3/26 years (2000-2002). Remaining 23 years blocked on corpus artifact availability at expected mount paths.

### Root Cause (from factory_direction.json director_note)
> "Previous director_note claimed ARTIFACT PUBLICATION GAP RESOLVED with symlinks at /tmp/lex_accepted/corpus/... — VERIFICATION SHOWS /tmp/lex_accepted/corpus/ DOES NOT EXIST. Gap NOT fully resolved at mount paths."

### Methodological Blocker — RESOLVED
**HNSW adversarial artifact** — Fixed via exact k-NN on valid subset for adversarial benchmarks. Ready for dense 174k evaluation.

### External Dependency (Non-blocking)
**Jurist human study** — Requires 5-10 Swiss jurists recruited by repository owner. Framework ready, reported as blocked when reachable.

---

## Next Steps

### Immediate (Blocked on Legal-Distance)
1. **Legal-distance completes** years 2003-2025 dense embedding computation
2. **Legal-distance runs** `finalize_174k_embeddings.py` to concatenate and publish to `174k_dense_embeddings/` root
3. **Monitor auto-detects** and evaluates all awaited dense representations

### When Dense Embeddings Land
1. Run v25 formal suite on all 7 dense representations (config hash `4323f833fa72366a` frozen)
2. Run v3 adversarial harness at 174k with exact k-NN fix
3. Run citation_heritage on frozen 137,314-pair pool
4. Run v17b label normalization comparison
5. **Critical test:** Will metric learning/hybrid objectives maintain jurist pairwise > 0.5 at 174k, or collapse like TF-IDF (0.79 → 0.12)?

### Product Integration
- **Production default remains cited_outcome_hybrid_0.5** (TF-IDF, zero-shot, no GPU)
- Dense embeddings attach as legal-distance delivers them year-split
- No product-readiness claim for dense modes until 174k evaluation complete

---

## Evidence References

| Artifact | Path |
|----------|------|
| TF-IDF formal suite final report | `reports/evaluation/evaluation_v27_174k_TFIDF_FAMILY_FINAL_REPORT.md` |
| HNSW artifact fix report | `reports/evaluation/EVALUATION_174K_HNSW_FIX_REPORT_v27.md` |
| v25 formal suite results (8 reps) | `results/evaluation/v25_174k_formal_suite/results/*.json` |
| Suite summary | `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` |
| Citation heritage dedicated | `results/evaluation/v25_174k_citation_heritage/*.json` |
| v17b normalization comparison | `results/evaluation/v25_174k_v17b/*.json` |
| v3 full corpus adversarial (TF-IDF) | `results/full_corpus_174k_tfidf/full_corpus_evaluation_results_worker0.json` |
| Frozen protocol v25 | `experiments/v25_174k_suite/protocol_v25_174k_suite.json` |
| Metadata 174k | `data/174k/metadata_174k.json` |
| Citation pairs 174k | `results/174k_citation_heritage/citation_pairs_174k_full.json` |
| Monitor state | `state/monitor_174k_state.json` |
| Monitor script (fixed) | `evaluation/monitor_and_evaluate_174k.py` |
| Legal-area normalization | `experiments/legal_area_normalize.py` |

---

## Recommendation

**Continue recommended:** `true` — Monitor active, infrastructure verified, clear evaluation protocol ready for dense embeddings.

**Next cycle trigger:** Detection of any awaited representation in `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/` (dense) or legal-distance version directories (citation roles, linear hybrids).

**When triggered:** Auto-execute v25 formal suite + v3 adversarial harness + citation_heritage + v17b on new representation(s).

---

*Report generated by evaluation lane. All results reproducible from frozen protocols and pinned data.*