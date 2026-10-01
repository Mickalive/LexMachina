# Evaluation Lane — Status Report v29
**Factory Direction Version**: 29 | **Lane**: evaluation | **Date**: 2026-10-01  
**Evidence Tier**: REPRODUCED | **Cycle Status**: COMPLETED | **Continue Recommended**: false

---

## Executive Summary

The Evaluation Lane has **completed all three machine-executable tasks** mandated by Factory Direction v29 for the **TF-IDF family (8 representations)** at full 174k scale (173,963 decisions). No new production representations have landed from the legal-distance lane since the last verification.

| Task | Status | Evidence Tier | Key Result |
|------|--------|---------------|------------|
| **1. Full 12-benchmark formal suite at 174k** | ✅ COMPLETE | REPRODUCED | 8/8 TF-IDF representations evaluated; HNSW artifact fixed via exact k-NN on stratified 2000-decision valid subset |
| **2. Citation heritage benchmark validation** | ✅ COMPLETE | REPRODUCED | Frozen 1,020-pair pool validated (924 resolved citations); ALL 8 representations FAIL recall@10 < 0.2 |
| **3. v17b label normalization generalization test** | ✅ COMPLETE | REPRODUCED | **NEGATIVE RESULT**: 15-25% purity gain at smaller scale does NOT generalize to 174k; zoom coherence DEGRADES for 4/8 representations |

**Lane State**: `COMPLETED` | **Continue Recommended**: `false` | **Next Action**: `PIVOT_WITHIN_MISSION` (awaiting new representations from legal-distance)

---

## Current Representation Readiness (Monitor Check #261)

### ✅ COMPLETED — TF-IDF Family (8/8 evaluated at 174k)

| Representation | Adversarial Gates (run_174k) | v25 Formal Suite | Citation Heritage | v17b Normalization |
|----------------|------------------------------|------------------|-------------------|-------------------|
| `cited_decisions_tfidf` | PASS (LD=0.492, JP=0.708) | 6/11 pass | AUC=0.722 ✓, R@10=0.006 ✗ | zoom_fine ratio 0.887 |
| `outcome_tfidf` | PASS (LD=0.508, JP=0.666) | 3/11 pass | AUC=0.586 ✗, R@10=0.000 ✗ | zoom_fine ratio 0.997 |
| `regeste_tfidf` | PASS (LD=0.511, JP=0.615) | 5/11 pass | AUC=0.836 ✓, R@10=0.001 ✗ | zoom_fine ratio 0.989 |
| `full_text_tfidf_light` | PASS (LD=0.485, JP=0.708) | 7/11 pass | AUC=0.626 ✗, R@10=0.001 ✗ | zoom_fine ratio 0.835 |
| `cited_outcome_hybrid_0.5` | **PASS (LD=0.490, JP=0.727)** | 6/11 pass | AUC=0.649 ✗, R@10=0.007 ✗ | zoom_fine ratio 0.883 |
| `cited_outcome_hybrid_0.7` | PASS (LD=0.491, JP=0.720) | 6/11 pass | AUC=0.676 ✓, R@10=0.006 ✗ | zoom_fine ratio 0.886 |
| `regeste_full_text_hybrid_0.5` | PASS (LD=0.487, JP=0.714) | 7/11 pass | AUC=0.637 ✗, R@10=0.001 ✗ | zoom_fine ratio 0.906 |
| `regeste_full_text_hybrid_0.7` | PASS (LD=0.489, JP=0.712) | 7/11 pass | AUC=0.660 ✓, R@10=0.001 ✗ | zoom_fine ratio 0.965 |

**Production Default**: `cited_decisions_tfidf_outcome_hybrid_0.5` — best jurist preference (0.7265) with low language dominance (0.4895)

### ❌ AWAITED — No New Representations Landed (12/12 missing)

| Category | Representations | Status |
|----------|----------------|--------|
| **Dense embeddings** | `center_projected_768dim`, `center_projected_64dim`, `center_projected_128dim`, `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1`, `hybrid_v2_epoch3` | **BLOCKED** — Fundamental data acquisition issue |
| **Citation roles** | `citation_role_citing_alpha0.3`, `citation_role_following_alpha0.3`, `citation_role_criticizing_alpha0.3` | Not computed at 174k |
| **Linear hybrids** | `linear_citation_concat`, `linear_hybrid05_concat` | Tested at 15-year scale (91k) — FAIL jurist gate |

---

## Critical Blocker: Dense Embeddings at 174k

**Legal-distance lane state confirms**: Dense embedding checkpoints cover only **122,265/173,963 decisions (70.4%)**

| Issue | Detail |
|-------|--------|
| **Years completely missing** | 2019, 2025, 2026 (not in BGE published volumes) |
| **Years severely underrepresented** | 2020-2024: only 50 decisions each in checkpoints vs thousands expected |
| **Metadata ID mismatch** | Checkpoints computed from `bge_` (published BGE volumes) but canonical metadata uses `bger_` (unpublished) decision IDs |
| **Finalize script fails** | `finalize_174k_embeddings.py` FAILS metadata order verification (122,265 vs 173,963) |
| **Concatenation not done** | No full 174k center_projected embeddings produced |

**Resolution requires**: Frontier team for bger_ corpus acquisition or metadata realignment. This is a **fundamental data acquisition blocker**, not a computational one.

---

## Key Findings (Preserved from v29 Completion)

### 1. Fundamental Two-Mode Tradeoff CONFIRMED at 174k
- **Citation-based reps** (cited_decisions, regeste, cited_outcome hybrids) → PASS adversarial + citation_heritage AUC; FAIL branch/tf_metadata/hierarchy/legal_area
- **Text-based reps** (full_text_tfidf_light, regeste_full_text hybrids) → PASS branch/tf_metadata/boilerplate/temporal/zoom; FAIL adversarial_falsification (LangDom ~0.999), multilingual, cross_language
- **No single representation dominates all benchmarks** — two map modes needed

### 2. Citation Heritage Benchmark LIMITED at 174k
- Citation graph covers only **174/173,963 decisions (0.1% of corpus)**
- Resolved citations: 924/2,019 published
- ALL 8 representations FAIL recall@10 (max 0.0066 << 0.2 threshold)
- Benchmark severely underpowered at corpus scale

### 3. v17b Label Normalization NEGATIVE at 174k
- Uniform improvement: **FALSE** — 4/8 reps degraded >10% on zoom_fine
- Hierarchy coherence: No change (ratio = 1.0)
- Legal area clustering: No change (ratio ≈ 1.0)
- **Substantive positive**: Enables fine-grained legal_area clustering at scale (raw purities ~0.016-0.035 → normalized ~0.16, **5-10x gain**)

### 4. Dense Embeddings FAIL at All Tested Scales
| Scale | Representation | LangDom | Jurist Pref | Verdict |
|-------|----------------|---------|-------------|---------|
| 12k (2000-2002) | center_projected 768/64/128 | ~0.997 | ~0.005 | CATASTROPHIC FAIL |
| 92k (2000-2014) | center_projected 768/64/128 | 0.875-0.899 | 0.267-0.302 | FAIL |
| 165k (partial) | center_projected 768/64/128 | 0.855-0.875 | 0.389-0.418 | FAIL |

**Scale dependency confirmed**: Center-projection helps vs raw embeddings but does NOT solve language dominance at scale. Metric learning required.

### 5. Universal Benchmark Failures (All Representations)
- **Boilerplate resistance**: ALL FAIL (resistance_score ~ -0.76 to -0.89)
- **Cross-language retrieval**: ALL FAIL (recall@10 ~0.12-0.14 < 0.2)
- **Hierarchy coherence (Jurivoc proxy)**: ALL FAIL (Level 0 NMI ~0.001-0.011 < 0.3)
- **Cluster coherence**: ALL FAIL (branch purity ~0.28-0.34 < 0.7)

---

## Infrastructure Status (ALL VERIFIED OPERATIONAL)

| Component | Status | Verification |
|-----------|--------|--------------|
| Formal suite script (`run_174k_formal_suite.py`) | ✅ OPERATIONAL | Config hash `b51701f5a9c11692` exact reproduction confirmed |
| Scalable NN (exact k-NN + HNSW) | ✅ OPERATIONAL | Exact k-NN on stratified subsample for adversarial; HNSW for full-corpus |
| Citation heritage pipeline | ✅ OPERATIONAL | Frozen 1,020-pair pool, 95.9% corpus resolution |
| v17b normalization pipeline | ✅ OPERATIONAL | Differential effect reproduced across all 8 TF-IDF reps |
| Metadata 174k | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% coverage |
| Monitor script | ✅ ACTIVE | check_count=261, last_check=2026-10-01T07:03:29 |

---

## Evidence References (Immutable)

| Artifact | Path |
|----------|------|
| Formal suite results (latest) | `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` |
| Citation pairs (frozen) | `evaluation/results/174k_citation_heritage/citation_pairs_174k.json` |
| Citation heritage benchmark | `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json` |
| v17b label normalization | `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` |
| Lane state (machine-readable) | `evaluation/state/evaluation.json` |
| Lane state (canonical) | `evaluation/state/evaluation_state.json` |
| Monitor state | `evaluation/state/monitor_174k_state.json` |
| Completion report | `reports/evaluation/EVALUATION_174K_FORMAL_SUITE_COMPLETION_v29.md` |
| Audit-ready verification | `reports/evaluation/eval_174k_formal_suite_v29_20261001_AUDIT_READY_REPORT.md` |

---

## Next Steps / Recommendation

### For Factory Director (v30 direction):

**No further same-question cycle justified** for evaluation lane. All v29 tasks complete for available representations.

**Next factory direction should target:**
1. **Dense embeddings at 174k** — Requires frontier team to resolve bge_/bger_ metadata ID mismatch (fundamental data acquisition blocker)
2. **Citation role embeddings at 174k** — When legal-distance produces them
3. **Linear hybrid embeddings at 174k** — When legal-distance produces them (15-year proxy tests NEGATIVE)
4. **Metric learning embeddings at 174k** — When legal-distance produces them
5. **Jurist human study** — Framework ready; requires 5-10 Swiss jurists (external dependency)

### For Evaluation Lane:
- **Maintain monitoring readiness** — Infrastructure frozen and verified
- **Trigger for next cycle**: Detection of any awaited representation in legal-distance accepted state
- **No re-evaluation of TF-IDF family needed** — Already complete with frozen thresholds

---

## Lane Deliverable Status: COMPLETE & AUDIT-READY

- ✅ All three v29 tasks executed and verified reproducible
- ✅ Negative results preserved (citation heritage FAIL, v17b NEGATIVE, dense FAIL)
- ✅ State files consistent (`evaluation.json` ≡ `evaluation_state.json`)
- ✅ Config hash frozen (`b51701f5a9c11692`) for exact reproduction
- ✅ No same-question cycle justified — awaiting upstream delivery
- ✅ All evidence artifacts preserved with provenance

**Signed**: Evaluation Lane | **Evidence Tier**: REPRODUCED | **Next Recommendation**: PIVOT_WITHIN_MISSION