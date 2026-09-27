# Evaluation Lane — 174k Cycle Report (v31 Update)

**Date**: 2026-09-27  
**Factory Direction**: v28  
**Lane Status**: BLOCKED_ON_DEPENDENCIES  
**Evidence Tier**: REPRODUCED  
**Continue Recommended**: false  

---

## Executive Summary

This cycle extends the 16-year partial (2000-2015, 99,325 decisions) evaluation with two new completed evaluations:

1. **RAW multilingual-e5 768dim formal suite** — Full 12-benchmark evaluation of raw embeddings at 99k scale
2. **RAW multilingual-e5 768dim citation heritage** — Citation proximity benchmark on raw embeddings

**Key finding**: RAW multilingual-e5 embeddings at 99k scale **FAIL all adversarial and legal-structure benchmarks** (lang_dom=0.9855, jurist_pref=0.0275), confirming that center-projection is **necessary and effective**. Only cross-language transfer (transfer_gap=0.0066) and scale stability (0.786 overlap) pass.

The TF-IDF family at full 174k remains the only production-ready representation family (5/8 pass both adversarial gates). The lane remains correctly **BLOCKED_ON_DEPENDENCIES** awaiting legal-distance 174k dense embeddings (16/26 years of checkpoints available; years 2016-2026 pending).

---

## Completed Evaluations

### 1. TF-IDF Family at 174k (COMPLETE — 8 representations)

| Representation | Verdict | LangDom | JuristPref | Both Gates |
|----------------|---------|---------|------------|------------|
| cited_decisions_tfidf | PASS | 0.5295 | 0.802 | ✓ |
| outcome_tfidf | PASS | 0.4527 | 0.7255 | ✓ |
| regeste_tfidf | PASS | 0.4835 | 0.609 | ✓ |
| cited_outcome_hybrid_0.5 | PASS | 0.5164 | 0.8055 | ✓ |
| cited_outcome_hybrid_0.7 | PASS | 0.5238 | 0.7975 | ✓ |
| full_text_tfidf_light | FAIL | 1.0 | 0.0 | ✗ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0 | 0.0 | ✗ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0 | 0.0 | ✗ |

**Production default**: `cited_outcome_hybrid_0.7` (best balance of legal signal and stability)  
**Universal failures at 174k**: hierarchy_coherence, legal_area_clustering, temporal_stability, boilerplate_resistance — corpus/label limitations, not representation defects.

---

### 2. Citation Heritage at 174k (COMPLETE — TF-IDF family)

| Representation | AUC-ROC | Recall@10 | Status |
|----------------|---------|-----------|--------|
| cited_decisions_tfidf | 0.7892 | 0.048 | FAIL |
| full_text_tfidf_light | 0.8969 | 0.0529 | FAIL |
| cited_outcome_hybrid_0.7 | 0.7749 | 0.049 | FAIL |
| ... | ... | ... | FAIL |

All 8 TF-IDF representations **FAIL recall@10 > 0.2** (best: 0.048). Some pass AUC (>0.65) but recall@10 near zero indicates citation neighborhood recovery fails at 174k density for TF-IDF.

---

### 3. v17b Label Normalization at 174k (COMPLETE)

- Raw labels: 213 → Normalized: 163 (23.5% reduction)
- Cross-lingual concepts merged: 32
- Purity gains: 15-25% REPRODUCED across 4 seeds
- **Generalization**: PARTIAL — only 2/8 TF-IDF reps within ≤10% worsening on hierarchy-family metrics
- Even normalized, hierarchy purity < 0.7 threshold

---

### 4. 3-Year Partial Dense (2000-2002, 12,570 decisions) — COMPLETE

| Representation | Verdict | LangDom | JuristPref |
|----------------|---------|---------|------------|
| center_projected_768dim | FAIL | 0.9806 | 0.040 |
| center_projected_64dim | FAIL | 0.9782 | 0.045 |
| center_projected_128dim | FAIL | 0.9804 | 0.041 |

Metadata coverage only 18.3% — insufficient for valid adversarial evaluation.

---

### 5. 16-Year Partial Center_Projected (2000-2015, 99,325 decisions) — COMPLETE

| Representation | Verdict | LangDom | JuristPref | Δ vs 3-yr |
|----------------|---------|---------|------------|-----------|
| center_projected_768dim | FAIL | 0.8774 | 0.297 | -0.103 / +0.257 |
| center_projected_64dim | FAIL | 0.868 | **0.327** | -0.110 / +0.282 |
| center_projected_128dim | FAIL | 0.8746 | 0.302 | -0.106 / +0.261 |

**Significant improvement** with 8× more data: language dominance dropped from ~0.98 → ~0.87 (approaching 0.85 threshold); jurist preference rose from ~0.04 → ~0.30 (still below 0.5 threshold).

**Cross-language**: All PASS transfer (gap 0.033-0.041), lang-specific quality PASS (mean_nmi 0.38-0.40)  
**64dim cross-language retrieval**: PASS on 15k subsample (recall=0.274)  
**Hierarchy**: FAIL (L0 NMI 0.27-0.30, L1 NMI 0.40-0.42)  
**Best**: `center_projected_64dim_partial_2000_2015` — closest to both adversarial gates

---

### 6. 16-Year Partial Citation Heritage (COMPLETE — 4 representations)

| Representation | AUC | Recall@10 | Status |
|----------------|-----|-----------|--------|
| raw_multilingual_e5_768dim | 0.9105 | 0.014 | FAIL |
| center_projected_768dim | 0.9047 | 0.0 | FAIL |
| center_projected_128dim | 0.9053 | 0.0 | FAIL |
| center_projected_64dim | 0.9057 | 0.0 | FAIL |

**Pattern**: ALL PASS AUC (~0.90-0.91) but ALL FAIL recall@10 (~0.0) — citation proximity preserved in similarity space but not recovered in top-10 neighbors at this scale/density for dense embeddings.

---

### 7. 16-Year Partial RAW Formal Suite (NEW — 1 representation)

| Metric | Value | Status | Threshold |
|--------|-------|--------|-----------|
| **Adversarial Language Dominance** | 0.9855 | FAIL | < 0.85 |
| **Jurist Pairwise Preference** | 0.0275 | FAIL | > 0.5 |
| Cross-Language Transfer Gap | 0.0066 | PASS | < 0.15 |
| Language-Specific Quality (mean NMI) | 0.4439 | PASS | > 0.4 |
| Hierarchy Level 0 NMI (branch) | 0.0152 | FAIL | > 0.3 |
| Hierarchy Level 1 NMI (legal_area) | 0.4604 | — | > 0.2 |
| Nesting Score | 0.6320 | — | — |
| Scale Stability (neighbor overlap) | 0.7861 | PASS | > 0.5 |
| Boilerplate Resistance | -0.9249 | FAIL | > 0 |
| Cluster Coherence (branch purity) | 0.6205 | FAIL | > 0.7 |
| Cross-Language Retrieval (15k) | 0.0022 | FAIL | > 0.2 |

**Key findings**:
- Language dominance **0.9855** — language artifacts completely dominate neighborhood
- Jurist preference **0.0275** — virtually no legally relevant neighbors in top-10
- Only cross-language transfer and scale stability pass
- Hierarchy L0 NMI near zero (0.015) — branch-level legal structure absent
- Confirms center-projection is **necessary and effective** (cp_64dim: lang_dom=0.868, jurist_pref=0.327)

---

### 8. 16-Year Partial RAW Citation Heritage (NEW)

| Representation | AUC | Recall@10 | Status |
|----------------|-----|-----------|--------|
| raw_multilingual_e5_768dim | 0.9105 | 0.0 | FAIL |

Same pattern as center-projected: high AUC, zero recall@10.

---

## Scale Trajectory Analysis

| Corpus Scale | Best Representation | LangDom | JuristPref | Both Gates |
|--------------|---------------------|---------|------------|------------|
| 1.2k (1200-slice) | center_projected_64dim | 0.531 | 0.982 | ✓ |
| 12k (3-year) | center_projected_64dim | 0.978 | 0.045 | ✗ |
| 99k (16-year) | center_projected_64dim | **0.868** | **0.327** | ✗ |
| 174k (full) | — | — | — | **PENDING** |

**Critical insight**: The 1200-slice results **do not generalize** to larger scale. Language dominance improves significantly from 12k→99k (0.98→0.87), but jurist preference remains far below threshold (0.33 vs 0.5). The trajectory suggests full 174k may approach lang_dom threshold but jurist_pref gap persists.

---

## Infrastructure Readiness

| Component | Status |
|-----------|--------|
| 174k metadata symlink | VERIFIED |
| Corpus canonical path (2003-2025 symlinks) | VERIFIED |
| Frozen v3 harness (exact k-NN on n=2000 stratified subsample) | OPERATIONAL |
| HNSW artifact fix | CONFIRMED (exact k-NN for adversarial) |
| Formal suite scripts | READY |
| Monitor | ACTIVE (check_count=143) |
| Citation heritage benchmark | READY (frozen 137k pair pool) |
| v17b label normalization | REPRODUCED |
| Jurist human study framework | READY (blocked on recruitment) |

---

## Blocked Dependencies

| Dependency | Status | Details |
|------------|--------|---------|
| 174k dense embeddings (center_projected) | 16/26 years | Checkpoints ready for 2000-2015; 2016-2026 pending |
| 174k metric learning (linear/mahalanobis) | AWAITED | Requires full 174k center_projected |
| 174k hybrid_stabilized | AWAITED | Requires full 174k center_projected |
| 174k citation role embeddings | AWAITED | Evaluated at 1k only (v7) |
| 174k linear hybrids | AWAITED | Evaluated at 1k only (v12/v13/v14) |

---

## Recommendation

**No additional same-question cycle justified** — `continue_recommended: false`

The evaluation lane has completed all machine-executable sub-questions from factory direction v28:
1. ✅ 12-benchmark formal suite at 174k on TF-IDF family (8 reps)
2. ✅ Citation heritage validated on frozen 137k pair pool
3. ✅ v17b label normalization generalization at 174k
4. ✅ 16-year partial center_projected formal suite
5. ✅ 16-year partial RAW formal suite (NEW)
6. ✅ 16-year partial citation heritage (including RAW, NEW)

**Next action**: Factory Director should prioritize unblocking legal-distance dense embedding computation (years 2016-2026 concatenation and promotion to accepted state). The evaluation infrastructure is fully ready to run the formal suite on all awaited representations as they land.

---

## Evidence References

- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — TF-IDF 174k formal suite
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` — TF-IDF 174k citation heritage
- `evaluation/results/174k/center_projected_partial_2000_2015/center_projected_16year_eval_latest.json` — 16-yr center_projected
- `evaluation/results/174k/raw_multilingual_e5_partial_2000_2015/raw_multilingual_e5_16year_eval_latest.json` — **NEW**: 16-yr RAW formal suite
- `evaluation/results/174k_citation_heritage/citation_heritage_raw_multilingual_e5_768dim_partial_2000_2015.json` — **NEW**: 16-yr RAW citation heritage
- `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json` — v17b label normalization
- `evaluation/monitor_and_evaluate_174k.py` — Autonomous monitor
- `evaluation/evaluate_raw_16year.py` — **NEW**: RAW 16-yr formal suite script
- `evaluation/run_citation_heritage_raw_16year.py` — **NEW**: RAW 16-yr citation heritage script

---

*Report generated per Research Protocol: freeze hypothesis/sample/metric/success rule before observing result; preserve negative results; compare against strong baselines.*