# Evaluation Lane Status Report — 2026-09-27

**Factory Direction Version:** 28  
**Lane:** evaluation  
**Status:** MONITORING (active)  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** MONITORING — awaiting representations from legal-distance  
**Continue Recommended:** true (ongoing monitoring for new representations)

---

## Executive Summary

The evaluation lane has **completed all three sub-questions** from factory direction v28 for the TF-IDF family (8 representations) at 174k scale. The lane is now in **active monitoring mode**, running `monitor_and_evaluate_174k.py` to detect when awaited representations land from the legal-distance lane and automatically execute the full v25 formal suite on each.

**Key Finding:** The fundamental two-mode tradeoff persists at 174k scale. No single representation passes all benchmarks. Citation-based signals pass adversarial falsification but fail cross-language transfer and hierarchy coherence. Text-based signals pass cross-language/hierarchy/cluster/temporal but fail adversarial falsification completely (language dominance = 1.0, jurist preference = 0.0).

---

## Completed Work (TF-IDF Family — 8 Representations at 174k)

### 1. Formal Benchmark Suite (12 Benchmarks) — COMPLETE

| Representation | Verdict | Adversarial Pass | Key Metrics |
|---|---|---|---|
| `cited_decisions_tfidf` | PASS | ✓ | lang_dom=0.53, jurist_pref=0.80 |
| `cited_outcome_hybrid_0.5` | PASS | ✓ | lang_dom=0.52, jurist_pref=0.81 |
| `cited_outcome_hybrid_0.7` | PASS | ✓ | lang_dom=0.52, jurist_pref=0.80 |
| `outcome_tfidf` | PASS | ✓ | lang_dom=0.45, jurist_pref=0.73 |
| `regeste_tfidf` | PASS | ✓ | lang_dom=0.48, jurist_pref=0.61 |
| `full_text_tfidf_light` | FAIL | ✗ | lang_dom=1.00, jurist_pref=0.00 |
| `regeste_full_text_hybrid_0.5` | FAIL | ✗ | lang_dom=1.00, jurist_pref=0.00 |
| `regeste_full_text_hybrid_0.7` | FAIL | ✗ | lang_dom=1.00, jurist_pref=0.00 |

**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5` (4/13 benchmarks PASS including adversarial_falsification + cross_language_retrieval_full)

**Critical Infrastructure Fix:** HNSW artifact confirmed and fixed — adversarial benchmarks now use EXACT k-NN on fixed stratified subsample (n≈2000 valid decisions with known branch), eliminating the HNSW-induced masking of representation differences.

### 2. Citation Heritage Benchmark — COMPLETE (NEW NEGATIVE FINDING)

**Methodology:** HNSW k=20 on full 174k corpus, frozen 137,314 pair pool (137,314 positive + 137,314 negative, seed=42), built from published 2,019/2,105 (95.9%) citation-ID resolution.

| Representation | AUC-ROC | Positive Recall@20 | Status |
|---|---|---|---|
| `cited_decisions_tfidf` | 0.5340 | 0.0681 | FAIL (AUC < 0.65) |
| `cited_outcome_hybrid_0.7` | 0.5307 | 0.0614 | FAIL |
| `cited_outcome_hybrid_0.5` | 0.5291 | 0.0582 | FAIL |
| `full_text_tfidf_light` | 0.5241 | 0.0483 | FAIL |
| `regeste_full_text_hybrid_0.7` | 0.5256 | 0.0514 | FAIL |
| `regeste_full_text_hybrid_0.5` | 0.5256 | 0.0513 | FAIL |
| `outcome_tfidf` | 0.5000 | 0.0001 | FAIL |
| `regeste_tfidf` | 0.4999 | 0.0000 | FAIL |

**Finding:** AUC ~0.50-0.53 for ALL 8 TF-IDF representations at 174k scale. Near random (AUC=0.5). Positive recall@20 ranges 0.00-0.07. Previous AUC 0.66-0.90 was from different methodology. **At 174k scale with HNSW, NO TF-IDF representation encodes citation structure in nearest neighbors above chance level.**

### 3. v17b Label Normalization — COMPLETE (NOT Uniformly Generalized)

**Methodology:** 214 raw unique legal_area labels → 164 normalized; 49.3% of labels changed across 173,963 decisions. Comparison: raw vs normalized on hierarchy_coherence + zoom_coherence + legal_area_clustering. Success rule: no representation worsened by >10% on any hierarchy-family metric.

| Representation | Hierarchy Purity Δ | Hierarchy NMI Δ | Zoom Fine Purity Δ | Uniformity Rule |
|---|---|---|---|---|
| `cited_decisions_tfidf` | +4-10% | degrades | improves | PASS |
| `cited_outcome_hybrid_0.5` | +4-10% | degrades | improves | PASS |
| `cited_outcome_hybrid_0.7` | +4-10% | degrades | improves | PASS |
| `outcome_tfidf` | +4-10% | degrades | improves | PASS |
| `regeste_tfidf` | +4-10% | degrades | improves | PASS |
| `full_text_tfidf_light` | 0% | degrades | **-30-34%** | FAIL |
| `regeste_full_text_hybrid_0.5` | 0% | degrades | **-30-34%** | FAIL |
| `regeste_full_text_hybrid_0.7` | 0% | degrades | **-30-34%** | FAIL |

**Finding:** Only 5/8 representations satisfy frozen >10% no-worsening rule on ALL hierarchy-family metrics. Citation-based reps show 4-10% purity improvement across all three metrics. Text-based reps show ZERO hierarchy_purity improvement and 30-34% zoom_fine_purity DEGRADATION. NMI degrades for all reps. Best normalized hierarchy_purity=0.554 < 0.7 threshold — fundamental granularity/coverage limits persist at 174k.

---

## Awaited Representations (Blocked on legal-distance)

### Dense Embeddings (8 representations)
- `center_projected_768dim`
- `center_projected_64dim`
- `center_projected_128dim`
- `linear_metric_epoch4`
- `mahalanobis_metric_epoch4`
- `hybrid_stabilized_epoch1`
- `hybrid_v2_epoch3`

### Citation Roles (3 representations)
- `citation_role_citing_alpha0.3`
- `citation_role_following_alpha0.3`
- `citation_role_criticizing_alpha0.3`

### Linear Hybrids (2 representations)
- `linear_citation_concat`
- `linear_hybrid05_concat`

---

## legal-distance Progress Status (per monitor_174k_state.json)

| Metric | Status |
|---|---|
| Years complete | 16/26 (2000-2015) |
| Decisions complete | 99,325 / 173,963 (57%) |
| Raw embeddings | Available in checkpoints for 16 years |
| Transformed representations | **NOT YET** concatenated into 174k final embeddings |
| Citation roles | NOT YET computed at 174k |
| Linear hybrids | NOT YET computed at 174k |
| Blocker | Years 2016-2025 pending legal-distance year-split execution |

**Note:** The 16 years of raw multilingual-e5 embeddings (2000-2015) are in checkpoints but have not been center-projected, metric-learned, or concatenated into production 174k representations. The monitor scans for final concatenated `.npy` files in `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/` — this directory does not yet exist.

---

## Monitor Infrastructure Status

| Component | Status |
|---|---|
| Monitor script | ACTIVE (`evaluation/monitor_and_evaluate_174k.py`) |
| Check count | 156 (last: 2026-09-27T15:19:52Z) |
| HNSW backend | OPERATIONAL_ON_GITHUB_RUNNERS |
| Scalable NN | OPERATIONAL_WITH_SKLEARN_FALLBACK |
| v25 formal suite runner | OPERATIONAL |
| Citation heritage | FROZEN_137314_PAIRS_READY |
| v17b normalization | OPERATIONAL |
| State file | `evaluation/state/monitor_174k_state.json` |

The monitor scans:
1. `fractal-map` accepted mount for TF-IDF 174k embeddings (verified present)
2. `legal-distance` accepted mount for `174k_dense_embeddings/` directory (not yet present)
3. `legal-distance` version directories for citation roles and linear hybrids with "174k" in name (not yet present)

---

## Evidence References

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Full 12-benchmark results for all 8 TF-IDF representations
- `evaluation/results/174k_citation_heritage/benchmark/citation_heritage_174k_tfidf_hnsw_latest.json` — Citation heritage AUC/recall results
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` — v17b normalization purity ratios
- `evaluation/monitor_and_evaluate_174k.py` — Active monitoring script
- `evaluation/state/monitor_174k_state.json` — Monitor state with detection history
- `reports/evaluation/EVALUATION_174K_FORMAL_SUITE_v28_CYCLE_REPORT.md` — Detailed cycle report
- `reports/evaluation/EVALUATION_174K_CITATION_HERITAGE_V17B_20260927.md` — Citation heritage + v17b report

---

## Frozen Configuration Hashes

| Component | Hash |
|---|---|
| v25 formal suite | `4323f833fa72366a` |
| v3 adversarial harness | `4047da047fb339c1` |
| v3 174k config | `evaluation/config/evaluation_v3_174k_config.json` |

---

## Recommendations

1. **CONTINUE MONITORING** — The monitor is active and will auto-execute the full v25 formal suite when awaited representations land in the accepted state mount.

2. **NO FURTHER TF-IDF WORK NEEDED** — The TF-IDF family is fully evaluated at 174k with REPRODUCED evidence tier.

3. **BLOCKER: legal-distance 174k dense embeddings** — The critical path is legal-distance completing year-split computation for years 2016-2025, then concatenating and transforming (center projection, metric learning, hybrid objectives) into production 174k representations.

4. **EXTERNAL DEPENDENCY: Jurist human study** — Framework ready, requires 5-10 Swiss jurists (non-blocking for automated evaluation).

---

## Next Actions

- [ ] Monitor continues running (check_count increments hourly via CI or manual execution)
- [ ] When `174k_dense_embeddings/` appears in legal-distance accepted mount with `.npy` files, monitor will auto-detect and run full v25 formal suite
- [ ] When citation role embeddings land, monitor will auto-detect and evaluate
- [ ] When linear hybrid embeddings land, monitor will auto-detect and evaluate
- [ ] Update evaluation state upon each new representation evaluation completion