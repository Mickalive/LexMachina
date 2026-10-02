# Legal-Distance Lane — Factory Direction v29 Final Evaluation Report

**Run ID:** `legal_distance_v29_174k_evaluation_20261001`  
**Direction Version:** 29  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Date:** 2026-10-02

---

## Executive Summary

All five factory direction v29 deliverables have been addressed. The legal-distance lane has successfully executed CPU-feasible staged computation on the REPRODUCED corpus artifacts, achieving **122,015 decisions (19 years: 2000–2018)** with dense embeddings — 70.1% of the 174k target. The remaining 51,948 decisions (years 2019–2025) are **fundamentally blocked** by missing data infrastructure (no parquet, no bger_ corpus files, no bge_↔bger_ ID mapping).

**Key Result:** The **two-mode tradeoff is reproduced at all scales**. No single representation dominates all metrics:
- **Citation/Outcome (TF-IDF hybrids):** LangDom ≈ 0.48, JuristPref ≈ 0.73, CiteIndep ≈ 14%
- **Semantic Embeddings (center_projected):** LangDom ≈ 0.86–0.98, JuristPref ≈ 0.03–0.37, CiteIndep ≈ 37%
- **Linear Combinations:** Intermediate LangDom (0.77–0.81), JuristPref (0.47–0.54) — **still below TF-IDF baseline**

**Recommendation:** `continue_recommended: false`. No further same-question cycles justified. A **FRONTIER_TEAM** is required for dense embedding data acquisition (parquet 2019–2026 or bge_↔bger_ ID mapping) before 174k dense evaluation can proceed.

---

## Factory Direction v29 Deliverables — Status

| # | Deliverable | Status | Evidence |
|---|-------------|--------|----------|
| 1 | Complete assembly & evaluation of 174k dense embeddings | **BLOCKED** | 122,015/173,963 decisions (70.1%, years 2000–2018). Years 2019, 2020–2026 missing. Parquet `/tmp/bger.parquet` missing. Canonical corpus uses bge_ IDs, evaluation uses bger_ IDs — no mapping exists. `finalize_174k_embeddings.py` fails metadata order verification. |
| 2 | Full-corpus adversarial evaluation at 174k on all production representations | **BLOCKED** | Depends on (1). 19-year (122k) adversarial evaluation complete on all representations. |
| 3 | Section-specific cross-lingual evaluation at full corpus density | **COMPLETED at 1K sample** | Sachverhalt (facts) superior to Erwaegungen (reasoning): cp_64 cross_lang_same_branch 0.282 vs 0.094, invariance_gap 0.187 vs 0.452. Center projection improves both. Full density blocked by (1). |
| 4 | Scale linear_hybrid05_concat stability test at 174k | **15yr FAIL, 19yr PASS** | 15yr (91,929): FAILS jurist gate (JP=0.473, Δ=-0.2465 vs baseline). 19yr (122,015): PASSES both gates (JP=0.5395) but **below TF-IDF baseline (0.7235)**. 174k BLOCKED. Clear scale dependency. |
| 5 | Re-test production-deployment vs CV tradeoff (TF-IDF SVD leakage) | **VALIDATED** | v8 holdout (train-only TF-IDF/SVD): all 4 zero-shot hybrids PASS both gates on true holdout. Leakage impact minimal: LangDom +0.005, JP +0.015–0.020. |

---

## Detailed Findings

### 1. Two-Mode Tradeoff Reproduced at All Scales

| Representation | Scale | LangDom | JuristPref | CiteIndep | Verdict |
|----------------|-------|---------|------------|-----------|---------|
| `cited_decisions_tfidf_outcome_hybrid_0.5` (TF-IDF) | 174k | 0.477 | **0.735** | 14% | **PASS** |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | 19yr | 0.474 | **0.716** | — | **PASS** |
| `cited_decisions_tfidf` | 19yr | 0.472 | **0.724** | — | **PASS** |
| `linear_citation_concat` (cp_64 + cited_tfidf) | 19yr | 0.767 | 0.545 | — | PASS |
| `linear_hybrid05_concat` (cp_64 + hybrid_0.5) | 19yr | 0.778 | 0.540 | — | PASS |
| `center_projected_64` | 19yr | 0.860 | 0.369 | — | FAIL |
| `center_projected_768` | 19yr | 0.983 | 0.047 | — | FAIL |
| `center_projected_64` | 15yr | 0.893 | 0.288 | — | FAIL |
| `linear_hybrid05_concat` | 15yr | 0.809 | **0.473** | — | FAIL |

**Interpretation:** Citation-based signals dominate jurist preference at scale. Semantic embeddings fail on language dominance (neighbors dominated by same-language decisions) despite better cross-language transfer. Linear combinations improve over pure semantic but cannot match TF-IDF citation baseline on jurist preference.

### 2. Scale Dependency Confirmed

| Metric | 15-year (91,929) | 19-year (122,015) | Δ |
|--------|------------------|-------------------|---|
| `linear_hybrid05_concat` JuristPref | 0.473 (FAIL) | **0.540 (PASS)** | +0.067 |
| `linear_hybrid05_concat` LangDom | 0.809 (PASS) | 0.778 (PASS) | -0.031 |
| `center_projected_64` JuristPref | 0.288 | 0.369 | +0.081 |
| TF-IDF hybrid JuristPref | 0.720 | 0.716 | ~flat |

**Conclusion:** Scale helps semantic signals (more decisions → better language debiasing), but citation signals dominate jurist preference at ALL scales. The gap to TF-IDF baseline persists at 19yr.

### 3. Section-Specific Cross-Lingual Evaluation (1K Sample)

| Section | Variant | cross_lang_same_branch | invariance_gap | zero_shot_nmi | Coverage |
|---------|---------|------------------------|----------------|---------------|----------|
| **Sachverhalt** (facts) | cp_64 | **0.282** | **0.187** | 0.189 | 35.9% |
| Sachverhalt | raw_768 | 0.217 | 0.304 | 0.144 | 35.9% |
| **Erwaegungen** (reasoning) | cp_64 | 0.094 | 0.452 | 0.065 | 51.0% |
| Erwaegungen | raw_768 | 0.040 | 0.538 | 0.051 | 51.0% |

**Key Insight:** Sachverhalt (legally relevant facts) achieves **3× better cross-lingual alignment** than Erwaegungen (legal reasoning). Center projection reduces invariance gap from 0.304→0.187 (Sachverhalt) and 0.538→0.452 (Erwaegungen). Full-corpus density evaluation blocked by missing dense embeddings.

### 4. Production-Deployment vs CV Tradeoff (v8 Holdout Validation)

| Representation | Holdout LangDom | Holdout JP | CV LangDom | CV JP | Leakage (Δ) |
|----------------|-----------------|------------|------------|-------|-------------|
| `cited_decisions_tfidf_outcome_hybrid_0.5` | 0.48 | 0.71 | 0.48 | 0.72 | LangDom +0.005, JP +0.015 |
| `linear_hybrid05_concat` | 0.78 | 0.52 | 0.78 | 0.54 | LangDom +0.005, JP +0.020 |

**Conclusion:** Full-corpus SVD fitting introduces **minimal leakage** (+0.5% LangDom, +1.5–2.0% JP). Production deployment on full corpus is justified.

### 5. Citation Heritage at 174k (TF-IDF Family)

| Representation | AUC | Status |
|----------------|-----|--------|
| `cited_decisions_tfidf_outcome_hybrid_0.5` | 0.716 | PASS |
| `cited_decisions_tfidf` | 0.713 | PASS |
| `cited_decisions_only` | 0.738 | PASS |
| `outcome_tfidf` | 0.730 | PASS |
| Text-based (regeste, full_text, erwaegungen) | ~0.50–0.63 | FAIL |

**Conclusion:** Citation signals recover citation heritage; text signals do not. Production default validated.

### 6. Negative Results (Preserved as Evidence)

| Test | Result | Note |
|------|--------|------|
| Boilerplate resistance (all reps) | resistance_score ≈ -0.74 to -0.92 | Proxy measures language dominance, not procedural boilerplate |
| v18 coarse hierarchy (4 branches) | Best purity 0.65 (linear_citation_concat) < 0.7 threshold | Fundamental hierarchy limitation for TF-IDF/citation reps |
| Cross-language retrieval (all reps) | Recall@10 < 0.14 | No representation achieves >0.2 threshold |
| Hierarchy coherence (nesting) | TF-IDF: nesting_score ~0.30; Dense: ~0.59 | NESTING_METRIC_DEFECT_v1 enforced — compressed 5-level ladder NOT universally valid |

### 7. v17b Label Normalization

- **1K scale:** 15–25% purity gain REPRODUCED across 4 seeds
- **174k fine-grained (213→111 labels):** Purity ratios 4–10× but NMI decreases on normalized
- **Conclusion:** Different regime at scale — requires separate validation

---

## Blocker Analysis: Why 174k Dense Embeddings Cannot Complete

| Blocker | Details | Resolution Path |
|---------|---------|-----------------|
| **Missing parquet** | `/tmp/bger.parquet` does not exist. Required by `compute_174k_dense_from_parquet.py` | FRONTIER_TEAM: Generate parquet from raw acquisition or API |
| **Missing bger_ corpus files** | Canonical corpus `/tmp/lex_accepted/corpus/corpus/normalization/canonical/` has only `bge_YYYY.jsonl` (BGE published decisions). `bger_YYYY.jsonl` (unpublished) only exist for 2020–2024 in raw acquisition. Years 2000–2019, 2025–2026 missing. | FRONTIER_TEAM: Complete corpus acquisition/normalization for bger_ decisions 2000–2026 |
| **ID mapping (bge_ ↔ bger_)** | Checkpoints use bger_ IDs (matching metadata_174k). Canonical corpus uses bge_ for BGE decisions. No mapping exists. | FRONTIER_TEAM: Build authoritative ID mapping |
| **GPU unavailability** | Free public runners have no GPU. CPU-only paraphrase-multilingual-mpnet-base-v2 takes ~30 min/year at 128 batch. 7 missing years ≈ 3.5h compute (feasible) but data not available. | Not the primary blocker — data is |

**Checkpoint Progress (Actual):**
- ✅ Years 2000–2018: 122,015 decisions (19 years) — **COMPLETED**
- ❌ Years 2019–2025: 51,948 decisions (7 years) — **FAILED** (no corpus data)
- 📊 Total: 173,963 decisions in metadata_174k

---

## Recommendations

### Immediate (This Lane)
1. **No further cycles on same question** — `continue_recommended: false`
2. All evidence preserved in `legal_distance/results/174k_dense_embeddings/` and `reports/legal-distance/v29_final_174k_evaluation_report.md`
3. Lane state updated to reflect BLOCKED_ON_DEPENDENCIES with FRONTIER_TEAM recommendation

### FRONTIER_TEAM Charter (Required for 174k Dense)
- **Product Capability:** Full 174k dense embedding map enabling semantic map modes in product
- **Precise Question:** Can we acquire/normalize bger_ decisions for 2019–2026 and build bge_↔bger_ ID mapping to complete 174k dense embeddings?
- **Why Now Evidence:** 122k/174k checkpoints exist; 19-year evaluations prove pipeline works; only data acquisition blocks 174k completion
- **Non-Duplication:** Corpus lane PAUSED (acquisition complete for published BGE). This requires unpublished bger_ acquisition — distinct scope
- **Acceptance Test:** `finalize_174k_embeddings.py` passes metadata order verification; 174k dense adversarial evaluation runs to completion

### Product Integration (Unblocked)
- **TF-IDF 174k production defaults OPERATIONAL:** `cited_decisions_tfidf_outcome_hybrid_0.5` validated at full 173,963 decisions (LangDom=0.477, JP=0.735)
- Product can ship with TF-IDF modes now; dense modes deferred until FRONTIER_TEAM delivers

---

## Evidence References

| Artifact | Location |
|----------|----------|
| 19-year dense evaluation (center_projected) | `legal_distance/results/174k_dense_embeddings/evaluation_19year_2000_2018/dense_19year_2000_2018_eval_latest.json` |
| 19-year linear combinations evaluation | `legal_distance/results/174k_dense_embeddings/linear_combinations_19year/linear_combinations_19year_eval_latest.json` |
| 15-year linear_hybrid05_concat evaluation | `legal_distance/results/174k_dense_embeddings/linear_hybrid05_concat_15year/linear_hybrid05_concat_15year_eval_latest.json` |
| Section cross-lingual evaluation | `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json` |
| v8 holdout validation | `legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json` |
| TF-IDF 174k formal suite | `/tmp/lex_accepted/evaluation/evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` |
| Citation heritage 174k | `/tmp/lex_accepted/evaluation/evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json` |
| v17b label normalization | `/tmp/lex_accepted/evaluation/results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_latest.json` |
| v18 coarse hierarchy | `/tmp/lex_accepted/evaluation/results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json` |
| Checkpoint progress | `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json` |

---

## Lane State Update

```json
{
  "lane": "legal-distance",
  "direction_version": 29,
  "evidence_tier": "REPRODUCED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "legal_distance_v29_174k_evaluation_20261001",
  "evidence_refs": [
    "legal_distance/results/174k_dense_embeddings/evaluation_19year_2000_2018/dense_19year_2000_2018_eval_latest.json",
    "legal_distance/results/174k_dense_embeddings/linear_combinations_19year/linear_combinations_19year_eval_latest.json",
    "legal_distance/results/174k_dense_embeddings/linear_hybrid05_concat_15year/linear_hybrid05_concat_15year_eval_latest.json",
    "legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json",
    "legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json",
    "/tmp/lex_accepted/evaluation/evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json",
    "/tmp/lex_accepted/evaluation/evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json",
    "/tmp/lex_accepted/evaluation/results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_latest.json",
    "/tmp/lex_accepted/evaluation/results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json",
    "legal_distance/results/174k_dense_embeddings/checkpoints/progress.json",
    "reports/legal-distance/v29_final_174k_evaluation_report.md"
  ],
  "next_recommendation": "FRONTIER_TEAM_REQUIRED: Dense embedding data acquisition (parquet 2019-2026 or bge_<->bger_ ID mapping). TF-IDF 174k COMPLETE and production-ready (cited_decisions_tfidf_outcome_hybrid_0.5: LangDom=0.4773, JuristPref=0.7345). All 5 factory direction v29 deliverables addressed: (1) 174k dense assembly BLOCKED (122k/174k decisions, missing parquet); (2) full-corpus dense adversarial BLOCKED; (3) section cross-lingual COMPLETED at 1K sample (sachverhalt superior); (4) linear_hybrid05_concat scale test: 15yr FAIL (JP=0.473), 19yr PASS (JP=0.5395) but below TF-IDF baseline (0.7235), 174k BLOCKED; (5) prod-vs-CV tradeoff VALIDATED via v8 holdout (leakage minimal: LangDom +0.005, JP +0.015-0.020). Two-mode tradeoff REPRODUCED at all scales. No further same-question cycles justified."
}
```

---

## Conclusion

The legal-distance lane has **exhausted all CPU-feasible staged computation** on the available REPRODUCED corpus artifacts. The 19-year (122k) scale provides statistically robust evidence that:

1. **Citation-based TF-IDF hybrids are the production default** — they pass both adversarial gates at 174k with strong jurist preference (0.73)
2. **Dense semantic embeddings fail the jurist gate** due to language dominance, despite better cross-language transfer
3. **Linear combinations improve semantic signals but cannot close the gap** to citation-based baselines
4. **Scale dependency is real but insufficient** — 19yr helps linear_hybrid05_concat pass adversarial gates but jurist preference remains 25% below TF-IDF baseline
5. **Section-level analysis reveals Sachverhalt (facts) as superior cross-lingual signal** — 3× better than Erwaegungen (reasoning)

**The lane is correctly BLOCKED_ON_DEPENDENCIES.** The path forward requires a FRONTIER_TEAM for data acquisition, not more evaluation cycles. The product should proceed with TF-IDF 174k modes (already operational and audited) while dense mode completion is pursued separately.

---

*Report generated per Research Protocol §8: machine-readable lane state plus human-readable report. All raw outputs preserved. Negative results retained as first-class evidence.*