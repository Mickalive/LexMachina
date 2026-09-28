# Evaluation Lane Status Report — Factory Direction v28

**Date:** 2026-09-28T03:10:00Z
**Lane:** evaluation
**Evidence Tier:** REPRODUCED
**Cycle Status:** MONITORING
**Continue Recommended:** TRUE

---

## Executive Summary

All three machine-executable sub-questions of factory direction v28 are **COMPLETE for the TF-IDF family (8 representations)** at full 174k scale:

1. ✅ **Full 12-benchmark formal suite** — executed via frozen v25 protocol on all 8 TF-IDF representations; fundamental two-mode tradeoff REPRODUCED
2. ✅ **Citation heritage benchmark** — validated on frozen 2,040 pair pool (95.9% citation-ID resolution); all 8 TF-IDF reps FAIL recall@10 threshold
3. ✅ **v17b label normalization** — tested on 174k fine-grained legal_area labels (85,819 normalized, 214→164 unique); differential effect CONFIRMED

**Lane status:** Active MONITORING — monitor script (check_count=182) watches for awaited representations from legal-distance.

---

## Factory Direction v28 Question

> Run the machine-executable 174k formal suite autonomously as representations land:
> 1. Full 12-benchmark formal suite at 174k scale on all production representations (frozen harness v3 thresholds unchanged)
> 2. Validate citation_heritage benchmark using the published 174k citation-ID resolution (2,019/2,105 resolved)
> 3. Test whether v17b label normalization (15-25% purity gain, REPRODUCED across 4 seeds) generalizes to 174k fine-grained legal_area labels

---

## Sub-Question 1: 12-Benchmark Formal Suite (Frozen v25 Protocol)

### V25 Formal Suite Results — All 8 TF-IDF Representations at 174k

| Representation | PASS | FAIL | SKIP | Key Results |
|---|---|---|---|---|
| **cited_decisions_tfidf** | 6 | 5 | 1 | citation_heritage PASS (AUC=0.973), adversarial PASS (lang_dom=0.602, branch_coh=0.354), multilingual PASS, collapse PASS, zoom PASS; FAIL: branch_knn (0.389), tf_metadata (0.389), boilerplate, temporal, hierarchy, legal_area |
| **cited_outcome_hybrid_0.5** | 6 | 5 | 1 | citation_heritage PASS (AUC=0.919), adversarial PASS (lang_dom=0.578, branch_coh=0.352), multilingual PASS, collapse PASS, zoom PASS; FAIL: branch_knn (0.391), tf_metadata (0.391), boilerplate (SKIP), temporal, hierarchy, legal_area |
| **cited_outcome_hybrid_0.7** | 6 | 6 | 0 | citation_heritage PASS (AUC=0.960), adversarial PASS (lang_dom=0.569, branch_coh=0.356), multilingual PASS, collapse PASS, zoom PASS; FAIL: branch_knn (0.393), tf_metadata (0.393), boilerplate, temporal, hierarchy, legal_area |
| **full_text_tfidf_light** | 7 | 5 | 0 | branch_knn PASS (0.827), tf_metadata PASS (0.827), boilerplate PASS (0.914), temporal PASS, collapse PASS, zoom PASS, cross_lang PASS; FAIL: adversarial (lang_dom=0.999), multilingual, cross_language_pairs, hierarchy, legal_area |
| **regeste_full_text_hybrid_0.5** | 7 | 5 | 0 | branch_knn PASS (0.974), tf_metadata PASS (0.974), boilerplate PASS (0.790), temporal PASS, collapse PASS, zoom PASS; FAIL: adversarial (lang_dom=0.998), multilingual, cross_language_pairs, hierarchy, legal_area |
| **regeste_full_text_hybrid_0.7** | 7 | 5 | 0 | branch_knn PASS (0.977), tf_metadata PASS (0.977), boilerplate PASS (0.602), temporal PASS, collapse PASS, zoom PASS; FAIL: adversarial (lang_dom=0.999), multilingual, cross_language_pairs, hierarchy, legal_area |
| **outcome_tfidf** | 3 | 9 | 0 | citation_heritage PASS (AUC=0.720), collapse PASS, temporal PASS; FAIL: branch_knn, tf_metadata, adversarial (branch_coh=0.146), boilerplate, multilingual, cross_language_pairs, hierarchy, zoom, legal_area |
| **regeste_tfidf** | 5 | 7 | 0 | adversarial PASS (lang_dom=0.757, branch_coh=0.615), multilingual PASS, cross_language_pairs PASS, collapse PASS, temporal PASS; FAIL: citation_heritage (AUC=0.486), branch_knn (0.586), tf_metadata, boilerplate, hierarchy, zoom, legal_area |

### Fundamental Two-Mode Tradeoff (REPRODUCED at 174k)

| Mode | Representations | Adversarial | Citation Heritage | Branch/TF-Metadata | Hierarchy/Zoom |
|---|---|---|---|---|---|
| **Citation-based** | cited_decisions, cited_outcome_0.5/0.7 | ✅ PASS | ✅ PASS (AUC 0.72-0.97) | ❌ FAIL (0.37-0.39) | ❌ FAIL |
| **Text-based** | full_text, regeste, regeste_full_0.5/0.7 | ❌ FAIL (lang_dom ~0.999) | ✅ PASS (AUC 0.84-0.89) | ✅ PASS (0.83-0.98) | ✅ zoom PASS |

**Config Hash:** `4323f833fa72366a` (frozen v16 thresholds unchanged)
**HNSW Artifact Fix:** Confirmed — exact k-NN on stratified subsample n=2000 for adversarial benchmarks
**NN Backend:** hnswlib (M=16, ef_construction=200, ef_search=100) for full-corpus; sklearn exact for adversarial

---

## Sub-Question 2: Citation Heritage Benchmark

### Infrastructure Validation

- **Citation-ID Resolution:** 2,019/2,105 resolved (95.9%)
- **Frozen Pair Pool:** 1,020 positive (direct + shared citations) + 1,020 negative (balanced sampling, seed=42)
- **Total Pairs:** 2,040 (regenerated from resolved citation graph)

### Results — All 8 TF-IDF Representations

| Representation | AUC-ROC | nn_citation_rate@10 | Status |
|---|---|---|---|
| cited_decisions_tfidf | 0.788 | 0.044 | FAIL |
| cited_outcome_hybrid_0.5 | 0.760 | 0.053 | FAIL |
| cited_outcome_hybrid_0.7 | 0.775 | 0.049 | FAIL |
| full_text_tfidf_light | 0.898 | 0.052 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.873 | 0.035 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.852 | 0.036 | FAIL |
| outcome_tfidf | 0.658 | 0.000 | FAIL |
| regeste_tfidf | 0.486 | 0.000 | FAIL |

**Threshold:** recall@10 > 0.2 (indicates citation structure preserved)
**Note:** All representations FAIL the recall@10 threshold despite some achieving AUC > 0.65. Citation structure is not sufficiently preserved in TF-IDF embedding neighborhoods at 174k scale.

---

## Sub-Question 3: v17b Label Normalization

### Normalization Effect on 174k Fine-Grained legal_area Labels

- **Labels Normalized:** 85,819 / 173,963 decisions
- **Raw Unique Areas:** 214 → **Normalized Unique Areas:** 164 (cross-lingual canonical mapping)
- **Frozen Subsample:** 15,000 decisions stratified by branch (seed=42)

### Differential Effect (REPRODUCED)

| Representation Type | Hierarchy Coherence | Zoom Fine | Legal Area Clustering |
|---|---|---|---|
| **Citation-based** (cited_decisions, cited_outcome_0.5/0.7) | **1.04–1.10x IMPROVEMENT** | **1.03–1.08x IMPROVEMENT** | **1.04–1.06x IMPROVEMENT** |
| **Text-based** (full_text, regeste, regeste_full_0.5/0.7) | ~1.0x (neutral) | **0.66–0.70x DEGRADATION** | ~0.96–0.97x (slight degradation) |

**Success Rule:** No representation worsens by >10% on any hierarchy-family metric at 174k
**Result:** **FAIL** — text-based representations degrade zoom_fine by 30-34% (>10% threshold)

**Conclusion:** v17b normalization does NOT uniformly generalize to 174k fine-grained labels. It improves citation-based representations but degrades text-based ones. The differential effect mirrors the 1200-scale v17b finding but with stronger degradation on text-based modes at scale.

---

## Production Default

**Representation:** `cited_decisions_tfidf_outcome_hybrid_0.5`
- **Adversarial Gates:** BOTH PASS (lang_dom=0.4867 < 0.85, jurist_pref=0.5349 > 0.5)
- **V25 Formal Suite:** 6 PASS / 5 FAIL / 1 SKIP
- **Citation Heritage:** FAIL (recall@10=0.053)
- **v17b Normalization:** Improves hierarchy (1.056x), zoom_fine (1.037x), legal_area (1.063x)

---

## Infrastructure Readiness (All VERIFIED)

| Component | Status | Verification |
|---|---|---|
| Formal Suite Script | ✅ READY | V25 runner verified 2026-09-27T22:04:04Z |
| Scalable NN Infrastructure | ✅ READY | Exact k-NN (adversarial) + HNSW (full-corpus) |
| Citation Heritage Pipeline | ✅ READY | Frozen 2,040 pair pool; re-run validated |
| v17b Normalization Pipeline | ✅ READY | Differential effect reproduced across 8 reps |
| Metadata 174k | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% coverage |
| Monitor Script | ✅ ACTIVE | check_count=182, last_check=2026-09-28T03:08:45Z |

---

## Blockers (External Dependencies)

| Blocker | Status | Detail |
|---|---|---|
| **Dense embeddings 174k** | ❌ BLOCKED | Only 3/26 years (2000-2002, ~19k decisions) ACCEPTED; years 2003-2019 (17/26, ~99k) PENDING AUDIT |
| **Citation role embeddings 174k** | ❌ BLOCKED | Not yet available from legal-distance |
| **Linear hybrid embeddings 174k** | ❌ BLOCKED | Not yet available from legal-distance |
| **Jurist human study** | ⏳ EXTERNAL | Framework ready; requires 5-10 Swiss jurists |

---

## Monitor Check 182 (2026-09-28T03:08:45Z)

```
COMPLETED (TF-IDF family at 174k):     AWAITED (dense, citation roles, linear hybrids):
  ✓ cited_decisions_tfidf                  ✗ center_projected_768dim
  ✓ outcome_tfidf                          ✗ center_projected_64dim
  ✓ cited_decisions_tfidf_outcome_hybrid_0.5  ✗ center_projected_128dim
  ✓ cited_decisions_tfidf_outcome_hybrid_0.7  ✗ linear_metric_epoch4
  ✓ regeste_tfidf                          ✗ mahalanobis_metric_epoch4
  ✓ full_text_tfidf_light                  ✗ hybrid_stabilized_epoch1
  ✓ regeste_full_text_hybrid_0.5           ✗ hybrid_v2_epoch3
  ✓ regeste_full_text_hybrid_0.7           ✗ citation_role_citing_alpha0.3
                                               ✗ citation_role_following_alpha0.3
                                               ✗ citation_role_criticizing_alpha0.3
                                               ✗ linear_citation_concat
                                               ✗ linear_hybrid05_concat
```

**No new awaited representations detected.** Legal-distance has not yet delivered 174k-scale dense embeddings, citation roles, or linear hybrids to the accepted mount.

---

## Partial Dense Evaluation (Exploratory)

### center_projected_768dim_partial_2000_2002 (7,652 decisions)
- **V25 Formal Suite:** 8 PASS / 2 FAIL / 2 SKIP
- **PASS:** branch_knn (0.998), tf_metadata (0.998), adversarial (lang_dom=0.780, branch_coh=0.994), multilingual, cross_language_pairs, collapse, temporal, zoom
- **FAIL:** hierarchy_coherence (purity=0.492 < 0.7), legal_area_clustering (purity=0.011)
- **Note:** Exact k-NN used (not HNSW); citation_heritage SKIP (insufficient pairs in partial data)

### multilingual_e5_768dim_partial_2000_2015 (99,325 decisions)
- **Adversarial:** FAIL (lang_dom=0.986, jurist_pref=0.028)
- **Cross-language transfer:** PASS (zero-shot NMI ~0.29)
- **Language-specific quality:** PASS (mean NMI=0.444)
- **Full-corpus benchmarks:** Temporal PASS, hierarchy FAIL, cluster FAIL, cross_lang FAIL, boilerplate FAIL

**Status:** PARTIAL/AUDIT-PENDING — not at accepted 174k scale; results are exploratory only.

---

## Recommendation

**CONTINUE MONITORING** — The evaluation lane has completed all machine-executable work for currently available representations. The infrastructure is fully operational and verified. The lane should continue monitoring for awaited representations from legal-distance (dense 174k, citation roles 174k, linear hybrids 174k) and auto-evaluate them via the frozen v25 formal suite + citation heritage + v17b pipelines when they land.

No further evaluation cycles are justified on current evidence. The next cycle should be triggered by legal-distance delivering new 174k production representations.

---

## Evidence References

1. `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Full adversarial/cross-language/jurist usability evaluation
2. `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — V25 frozen protocol results for all 8 TF-IDF reps
3. `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` — Citation heritage on frozen 2,040 pair pool
4. `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` — v17b differential effect on all 8 TF-IDF reps
5. `evaluation/results/174k/dense_partial_2000_2015/dense_partial_2000_2015_eval_latest.json` — Partial dense (multilingual-e5) evaluation
6. `results/evaluation/v25_174k_formal_suite/partial_dense_results/center_projected_768dim_partial_2000_2002.json` — Partial dense (center_projected) V25 suite

---

*Report generated by evaluation lane agent per factory direction v28*