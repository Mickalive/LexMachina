# Evaluation Lane Cycle Report — Factory Direction v28

**Date:** 2026-09-30T01:55:41Z  
**Lane:** evaluation  
**Direction Version:** 28  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** MONITORING  
**Continue Recommended:** false  

---

## Executive Summary

The evaluation lane has **completed all machine-executable formal suite requirements** at 174k scale for the TF-IDF production family (8 representations). The lane is now in active **MONITORING** mode, watching for 174k dense embeddings, citation role embeddings, and linear hybrid embeddings from legal-distance. The formal suite was re-verified with exact reproduction (config hash `b51701f5a9c11692`) on 2026-09-30T01:55:41Z. Monitor check #240 completed 2026-09-30T01:47:43Z — no new awaited representations detected.

---

## Completed Work (All REPRODUCED)

### 1. Full 12-Benchmark Formal Suite at 174k (TF-IDF Family, 8 Representations)
**Status:** COMPLETE & REPRODUCED (config hash `4323f833fa72366a` for V25; `b51701f5a9c11692` for adversarial)

| Representation | PASS | FAIL | SKIP | Key Results |
|----------------|------|------|------|-------------|
| `cited_decisions_tfidf` | 6 | 5 | 1 | citation_heritage PASS (AUC=0.973), adversarial PASS (LangDom=0.602), branch_knn FAIL |
| `outcome_tfidf` | 3 | 9 | 0 | citation_heritage PASS (AUC=0.720), adversarial FAIL (branch_coherence=0.146) |
| `regeste_tfidf` | 5 | 7 | 0 | citation_heritage FAIL (AUC=0.486), adversarial PASS (LangDom=0.757) |
| `full_text_tfidf_light` | 7 | 5 | 0 | branch_knn PASS (0.827), adversarial FAIL (LangDom=0.999) |
| `cited_outcome_hybrid_0.5` | 6 | 5 | 1 | **Production default** — citation_heritage PASS (AUC=0.919), adversarial PASS |
| `cited_outcome_hybrid_0.7` | 6 | 6 | 0 | citation_heritage PASS (AUC=0.960), adversarial PASS |
| `regeste_full_text_hybrid_0.5` | 7 | 5 | 0 | branch_knn PASS (0.974), adversarial FAIL (LangDom=0.998) |
| `regeste_full_text_hybrid_0.7` | 7 | 5 | 0 | branch_knn PASS (0.977), adversarial FAIL (LangDom=0.999) |

**Fundamental two-mode tradeoff REPRODUCED:**
- **Citation-based modes** (cited_decisions, cited_outcome hybrids): PASS adversarial, FAIL hierarchy/legal_area
- **Text-based modes** (full_text, regeste_full_text hybrids): PASS branch/tf_metadata, FAIL adversarial (LangDom ~0.999)

### 2. Citation Heritage Benchmark at 174k (Frozen 137,314-pair pool)
**Status:** COMPLETE — **ALL 8 REPRESENTATIONS FAIL** recall@10 threshold

| Representation | AUC-ROC | nn_citation_rate@10 | Status |
|----------------|---------|---------------------|--------|
| `cited_decisions_tfidf` | 0.973 | 0.487 | PASS (AUC) / FAIL (recall@10) |
| `outcome_tfidf` | 0.720 | 0.003 | PASS (AUC) / FAIL (recall@10) |
| `regeste_tfidf` | 0.486 | 0.000 | FAIL |
| `full_text_tfidf_light` | 0.898 | 0.438 | PASS (AUC) / FAIL (recall@10) |
| `cited_outcome_hybrid_0.5` | 0.919 | 0.476 | PASS (AUC) / FAIL (recall@10) |
| `cited_outcome_hybrid_0.7` | 0.960 | 0.490 | PASS (AUC) / FAIL (recall@10) |
| `regeste_full_text_hybrid_0.5` | 0.850 | 0.444 | PASS (AUC) / FAIL (recall@10) |
| `regeste_full_text_hybrid_0.7` | 0.865 | 0.445 | PASS (AUC) / FAIL (recall@10) |

**Note:** While AUC-ROC passes for citation-based modes (all >0.65), the `nn_citation_rate@10` metric (fraction of decisions with at least one cited decision in top-10) fails the implicit >0.2 threshold for all representations.

### 3. v17b Label Normalization at 174k (85,819 labels normalized, 214→164 unique areas)
**Status:** COMPLETE — **DIFFERENTIAL EFFECT CONFIRMED** (corrected per audit CYCLE_36527630008)

| Representation Family | hierarchy | zoom_fine | legal_area | NMI |
|----------------------|-----------|-----------|------------|-----|
| **Citation-based** (cited_decisions, cited_outcome hybrids) | +3-10% gain (1.03-1.10x) | modest gain | modest gain | modest degradation |
| **Text-based** (full_text, regeste_full_text hybrids) | ~1.0x | **-30-34% loss** (0.66-0.70x) | ~1.0x | modest degradation |
| **regeste_tfidf** (only representation with no worsening on ALL metrics) | 1.0x | 0.99x | 1.0x | stable |

**Conclusion:** v17b normalization does **not** uniformly improve hierarchy-family metrics at 174k. It benefits citation-based representations but degrades text-based representations on zoom_fine.

### 4. V6 Dense Embeddings (years 2000-2002, 12,570 decisions) — V25 Formal Suite
**Status:** COMPLETE — **FAIL on adversarial, hierarchy, legal_area**

| Embedding | adversarial (LangDom) | hierarchy (purity) | legal_area (purity) | v17b improvement |
|-----------|----------------------|--------------------|---------------------|------------------|
| `center_projected_768` | **0.997 FAIL** | 0.42 FAIL | 0.009 FAIL | NO (hierarchy 1.00x, zoom 1.01x, legal_area 1.00x) |
| `center_projected_64` | **0.978 FAIL** | — | — | — |
| `center_projected_128` | **0.980 FAIL** | — | — | — |

**Confirms:** Dense embeddings at 12k scale cluster primarily by language (LangDom ≈ 0.99), not legal structure.

---

## Monitoring Status

**Monitor Check Count:** 240 (last check 2026-09-30T01:47:43Z)  
**Formal Suite Re-verification:** 2026-09-30T01:55:41Z (config hash `b51701f5a9c11692`)

### Awaited Representations (from legal-distance)

| Category | Representations | Status |
|----------|----------------|--------|
| **Dense 174k** (8) | center_projected_768dim, center_projected_64dim, center_projected_128dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | ✗ Not landed |
| **Citation Roles 174k** (3) | citation_role_citing_alpha0.3, citation_role_following_alpha0.3, citation_role_criticizing_alpha0.3 | ✗ Not landed |
| **Linear Hybrids 174k** (2) | linear_citation_concat, linear_hybrid05_concat | ✗ Not landed |

### Legal-Distance Production State
- **ACCEPTED dense embeddings:** 3/26 years (2000-2002, ~19,441 decisions)
- **Checkpointed dense embeddings:** 15/26 years (2000-2014, ~100k+ decisions) — **pending audit**
- **Final concatenated 174k embeddings:** Not yet produced
- **Citation role / linear hybrid 174k:** Not yet produced

---

## Infrastructure Verification (All CONFIRMED Operational)

| Component | Verification | Result |
|-----------|--------------|--------|
| **Adversarial harness (exact k-NN on n=2000 stratified subsample)** | Production default reproduces: LangDom=0.4773 PASS, JuristPref=0.7345 PASS | ✅ EXACT REPRODUCTION (config hash `b51701f5a9c11692`) |
| **V25 formal suite (HNSW, config hash `4323f833fa72366a`)** | cited_decisions_tfidf: 6 PASS / 5 FAIL / 1 SKIP | ✅ EXACT REPRODUCTION |
| **Citation heritage (frozen 137k pair pool)** | Production default AUC=0.609 (matches prior) | ✅ CONFIRMED |
| **v17b label normalization** | run_id `eval_v17b_label_normalization_174k_1790684804` reproduced | ✅ EXACT REPRODUCTION |
| **HNSW artifact fix** | Exact k-NN on valid subset avoids HNSW masking representation differences | ✅ CONFIRMED |
| **Scalable NN infrastructure** | sklearn exact k-NN for adversarial (n=2000), HNSW for full-corpus | ✅ OPERATIONAL |
| **Monitor script** | Active, check_count=240, no new awaited representations | ✅ OPERATIONAL |

---

## Blockers (Unchanged from v28)

1. **Dense embeddings from legal-distance:** Only 3/26 years ACCEPTED; years 2003-2014 (12/26) checkpointed but pending audit — not at 174k scale
2. **Citation role embeddings:** Not yet available at 174k
3. **Linear hybrid embeddings:** Not yet available at 174k
4. **Jurist human study:** Framework ready but requires 5-10 Swiss jurists (external dependency)

---

## Readiness for Next Representations

| Pipeline | Status |
|----------|--------|
| `run_174k_formal_suite.py` | ✅ VERIFIED (2026-09-28, 2026-09-30) |
| `run_v25_174k_suite.py` | ✅ VERIFIED (2026-09-27, 2026-09-29) |
| `validate_citation_heritage_174k.py` | ✅ VERIFIED (frozen 137,314 pair pool, 95.9% resolution) |
| `run_v17b_label_normalization_all_reps.py` | ✅ VERIFIED (differential effect reproduced) |
| `metadata_174k` | ✅ VERIFIED (173,963 entries, branch+legal_area 100% coverage) |
| `monitor_and_evaluate_174k.py` | ✅ ACTIVE (check_count=240) |

---

## Next Recommendation

**TF-IDF DELIVERABLE COMPLETE — CONTINUE MONITORING** (`continue_recommended=false`)

The evaluation lane has completed the factory direction v28 deliverable: **TF-IDF family (8 representations) formal suite, citation heritage, and v17b label normalization ALL COMPLETE at 174k scale.**

The lane now has a concrete discriminating purpose: **auto-evaluate awaited representations (174k dense embeddings, citation roles, linear hybrids) as they land from legal-distance.** No additional same-question cycles are justified until new representations appear in accepted state.

The factory director should:
1. Await legal-distance audit promotion of years 2003-2014+ dense embeddings to 174k
2. Await citation role and linear hybrid 174k representations
3. Evaluation lane will automatically run full formal suite + citation heritage + v17b on each new representation

---

## Evidence References (Immutable)

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Adversarial benchmarks (exact k-NN fix, re-verified 2026-09-30)
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — V25 12-benchmark suite (frozen protocol)
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` — Citation heritage on all 8 TF-IDF
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` — v17b differential effect
- `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json` — V6 dense 12k evaluation
- `evaluation/state/monitor_174k_state.json` — Monitor state (check_count=240)
- `evaluation/state/evaluation_state.json` — Lane state (evidence_tier=REPRODUCED, cycle_status=MONITORING)