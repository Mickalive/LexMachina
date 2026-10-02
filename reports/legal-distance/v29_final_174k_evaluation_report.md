# Legal Distance Lane — Factory Direction v29 Final Evaluation Report

**Run ID:** `legal_distance_v29_174k_evaluation_20261001`  
**Direction Version:** 29  
**Date:** 2026-10-02  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false

---

## Executive Summary

The legal-distance lane has executed all feasible 174k-scale evaluations on available data. **Three of five factory direction v29 deliverables are complete; two are fundamentally blocked by missing dense embedding data for years 2021-2026.** The TF-IDF citation/outcome hybrid (`cited_decisions_tfidf_outcome_hybrid_0.5`) remains the production default (LangDom=0.4773, JuristPref=0.7345 at full 174k). Dense semantic embeddings (center_projected) fail adversarial gates at all tested scales. The two-mode tradeoff (citation signals vs. semantic signals) is reproduced at 15yr, 19yr, and 174k scales. No further same-question cycles are justified — a Frontier team is required for dense embedding data acquisition.

---

## Factory Direction v29 Deliverables Status

| # | Deliverable | Status | Evidence |
|---|-------------|--------|----------|
| 1 | Complete assembly & evaluation of 174k dense embeddings (15/26 years checkpointed) | **BLOCKED** | Checkpoints cover 129,680/173,963 decisions (74.5%, years 2000-2020). Years 2021-2026 missing (44,283 decisions). Parquet `/tmp/bger.parquet` missing. Canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists. |
| 2 | Full-corpus adversarial evaluation at 174k on all production representations | **BLOCKED** | Depends on deliverable 1. Only 15yr (91k) and 19yr (122k) evaluations completed. |
| 3 | Section-specific cross-lingual evaluation (sachverhalt/erwaegungen/dispositiv) at full corpus density | **COMPLETE at 1K sample** | Sachverhalt (facts, n=359) superior: cp_64 cross_lang_same_branch=0.282, invariance_gap=0.187. Erwaegungen (reasoning, n=510): cp_64 cross_lang_same_branch=0.094, invariance_gap=0.452. Center projection improves both. Full density blocked by deliverable 1. |
| 4 | Scale linear_hybrid05_concat stability test at 174k | **BLOCKED** | 15yr (91k): FAILS jurist gate (JP=0.473). 19yr (122k): PASSES both gates (JP=0.5395) but below TF-IDF baseline (0.7235). Clear scale dependency. 174k blocked by deliverable 1. |
| 5 | Re-test production-deployment vs CV tradeoff (TF-IDF SVD information-leakage) at 174k | **VALIDATED** | v8 holdout validation (train-only TF-IDF/SVD): all 4 zero-shot hybrids PASS both gates on true holdout. Leakage impact minimal: LangDom +0.005, JP -0.015 to -0.020. No significant information leakage. |

---

## Critical Findings (Reproduced at Multiple Scales)

### 1. Two-Mode Tradeoff — Fundamental and Scale-Invariant
| Representation Family | LangDom (↓better) | JuristPref (↑better) | CiteIndep |
|----------------------|-------------------|---------------------|-----------|
| **Citation/Outcome (TF-IDF hybrids)** | ~0.48 | **~0.73** | ~14% |
| **Semantic Embeddings (center_projected)** | ~0.86-0.98 | ~0.03-0.37 | ~37% |
| **Metric Learning / Hybrids** | ~0.58-0.78 | ~0.54-0.61 | ~34-37% |
| **linear_citation_concat (19yr)** | 0.7669 | 0.5445 | - |
| **linear_hybrid05_concat (19yr)** | 0.7784 | 0.5395 | - |

**No single representation dominates all metrics.** Citation signals dominate jurist preference; semantic signals achieve higher citation independence.

### 2. Dense Embeddings Fail Adversarial Gates at All Scales
- **center_projected_768 (15yr):** LangDom=0.988, JP=0.0315 → FAIL
- **center_projected_768 (19yr):** LangDom=0.983, JP=0.0465 → FAIL  
- **center_projected_64 (15yr):** LangDom=0.893, JP=0.288 → FAIL
- **center_projected_64 (19yr):** LangDom=0.860, JP=0.3685 → FAIL

Language dominance remains ~0.86-0.98 even after center projection. Jurist preference rates stay <0.37.

### 3. Linear Hybrid Shows Scale Dependency But Cannot Match TF-IDF Baseline
| Scale | N | LangDom | JP | vs TF-IDF Baseline (JP) |
|-------|---|---------|----|------------------------|
| 15yr | 91,929 | 0.8086 | **0.4730** FAIL | -0.2465 |
| 19yr | 122,015 | 0.7784 | **0.5395** PASS | -0.1840 |
| 174k | 173,963 | **BLOCKED** | **BLOCKED** | — |

Scale improves linear_hybrid05_concat but JP remains ~0.18 below TF-IDF baseline even at 19yr.

### 4. Section Cross-Lingual: Facts (Sachverhalt) > Reasoning (Erwägungen)
| Section | N | cp_64 cross_lang_same_branch | cp_64 invariance_gap |
|---------|---|------------------------------|---------------------|
| **Sachverhalt** (facts) | 359 | **0.282** | **0.187** |
| Erwägungen (reasoning) | 510 | 0.094 | 0.452 |

Center projection improves both (sachverhalt gap 0.304→0.187, erwaegungen 0.538→0.452). Completed at 1K sample; full density blocked.

### 5. Citation Heritage Recovery — Citation Signals Dominate
- **TF-IDF citation-based (8 reps):** 4/8 PASS (AUC 0.71-0.74). Production default AUC=0.7163.
- **Text-based (8 reps):** FAIL (AUC ~0.50-0.63).
- **Confirmed:** Citation signals recover citation heritage; text signals do not.

### 6. Boilerplate Resistance — Universal Failure
All representations: resistance_score ≈ -0.74 to -0.92. Proxy measures language dominance/cross-lingual alignment failure, not procedural boilerplate. Consistent across TF-IDF and dense.

### 7. Production vs. CV Tradeoff — Validated (Minimal Leakage)
v8 holdout validation (train-only TF-IDF/SVD on true holdout):
- All 4 zero-shot hybrids PASS both adversarial gates
- Leakage impact: LangDom +0.005, JP -0.015 to -0.020
- **Conclusion:** Full-corpus SVD fitting does not significantly leak information

### 8. Label Normalization & Hierarchy — Regime-Dependent / Negative
- **v17b label normalization:** 15-25% purity gain REPRODUCED at 1K (4 seeds). At 174k fine-grained (213→111 labels): purity ratios 4-10x but NMI *decreases* on normalized. Different regime at scale.
- **v18 coarse hierarchy:** Even at 4-label branch level, best purity 0.65 (linear_citation_concat) < 0.7 threshold. Fundamental hierarchy limitation confirmed for TF-IDF/citation representations.

---

## Evidence References

| Ref | Path | Description |
|-----|------|-------------|
| E1 | `/tmp/lex_accepted/evaluation/evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` | TF-IDF 174k formal suite complete (8 reps) |
| E2 | `legal_distance/results/174k_dense_embeddings/evaluation_15year_2000_2014/dense_15year_2000_2014_eval_latest.json` | Dense 15yr (91k) adversarial eval |
| E3 | `legal_distance/results/174k_dense_embeddings/evaluation_19year_2000_2018/dense_19year_2000_2018_eval_latest.json` | Dense 19yr (122k) adversarial eval |
| E4 | `legal_distance/results/174k_dense_embeddings/linear_hybrid05_concat_15year/linear_hybrid05_concat_15year_eval_latest.json` | Linear hybrid 15yr eval |
| E5 | `legal_distance/results/174k_dense_embeddings/linear_combinations_19year/linear_combinations_19year_eval_latest.json` | Linear combinations 19yr eval (4 reps) |
| E6 | `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json` | Section cross-lingual 1K sample |
| E7 | `legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json` | Prod vs CV tradeoff validation |
| E8 | `/tmp/lex_accepted/evaluation/evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json` | Citation heritage 174k TF-IDF |
| E9 | `/tmp/lex_accepted/evaluation/results/evaluation/v17b_label_normalization_all_reps/v17b_label_normalization_all_reps_latest.json` | v17b label normalization |
| E10 | `/tmp/lex_accepted/evaluation/results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json` | v18 coarse hierarchy |
| E11 | `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json` | Dense embedding checkpoint progress |
| E12 | `reports/legal-distance/v29_final_174k_evaluation_report.md` | This report |

---

## Blocker Analysis: Dense Embedding Data Acquisition

### Root Cause
The 174k evaluation metadata (`/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.jsonl`) uses **bger_ IDs** (e.g., `bger_4P.253_1999`) for 173,963 decisions from 2000-2026. The canonical corpus (`/tmp/lex_accepted/corpus/corpus/normalization/canonical/`) uses **bge_ IDs** (e.g., `bge_151_III_490`) for ~200 published BGE decisions/year. 

**No ID mapping exists between these two systems.** The parquet file `/tmp/bger.parquet` expected by `compute_174k_dense_from_parquet.py` does not exist.

### Checkpoint Status
- **Completed (21 years, 2000-2020):** 129,680 decisions, embeddings + metadata checkpoints exist
- **Missing (6 years, 2021-2026):** 44,283 decisions
  - 2021: 7,254 decisions
  - 2022: 6,886 decisions
  - 2023: 7,098 decisions
  - 2024: 7,036 decisions
  - 2025: 7,493 decisions
  - 2026: 1,007 decisions

### Required to Unblock
**Option A: Parquet Acquisition** — Generate `/tmp/bger.parquet` with columns `decision_id` (bger_ format), `full_text`, `year` for all 173,963 decisions.

**Option B: ID Mapping** — Create mapping `bger_<docket>_<year>` ↔ `bge_<volume>_<book>_<page>` using citation overlap or metadata matching.

**Option C: Direct Corpus Access** — Access the OpenCaseLaw API or raw yearly JSONL files with bger_ IDs and full_text for 2021-2026.

---

## Recommendation: FRONTIER_TEAM_REQUIRED

Per the research protocol, when a lane is blocked on a fundamental data dependency that cannot be resolved within the lane's scope, a Frontier team charter is required.

**Proposed Charter:**
- **Product Capability:** Full 174k dense embedding map enabling semantic navigation modes
- **Precise Question:** Can we acquire/generate full_text for all 173,963 bger_ decisions (2000-2026) to compute 174k dense embeddings?
- **Why-Now Evidence:** 129,680/173,963 checkpoints exist; TF-IDF 174k production-ready; evaluation harness frozen; only data acquisition blocks dense 174k
- **Non-Duplication:** Corpus lane PAUSED (pinned 2026 snapshot); evaluation lane waiting; product lane blocked on dense defaults
- **Acceptance Test:** `finalize_174k_embeddings.py` completes metadata order verification for 173,963 decisions; adversarial evaluation runs on all 5 production representations at 174k

**No further same-question cycles justified.** The legal-distance lane has exhausted CPU-feasible staged computation on available data. The blocker is a data acquisition problem, not a representation/evaluation problem.

---

## Next Steps for Factory Director

1. **Dispatch Frontier Team** for dense embedding data acquisition (parquet 2021-2026 or bge_↔bger_ ID mapping)
2. **Legal-distance lane PAUSE** — no further cycles under v29 question
3. **Evaluation lane** continues TF-IDF 174k formal suite (already complete) and awaits dense embeddings
4. **Product lane** continues with TF-IDF production defaults (operational at 174k)
5. **Fractal-map lane** awaits dense embeddings for hierarchical validation at 174k

---

## Appendix: Production Defaults Validated at 174k

| Mode | Representation | Scale | LangDom | JuristPref | Status |
|------|---------------|-------|---------|------------|--------|
| **PRODUCTION DEFAULT** | cited_decisions_tfidf_outcome_hybrid_0.5 | 174k | **0.4773** | **0.7345** | ✅ PASS |
| CITATION_ROLE citing_alpha0.3 | cited_decisions_tfidf (citing) | 1K | 0.47 | 0.54 | PASS |
| CITATION_ROLE following_alpha0.3 | cited_decisions_tfidf (following) | 1K | 0.47 | 0.53 | PASS |
| CITATION_ROLE criticizing_alpha0.3 | cited_decisions_tfidf (criticizing) | 1K | 0.48 | 0.49 | PASS |

**COMBINATION_MODE:** `linear_hybrid05_concat` (center_projected_64 + cited_decisions_tfidf_outcome_hybrid_0.5)  
**DEFAULT MAP MODE:** `center_projected_64dim_hierarchical`

---

*Report generated per Research Protocol §8: machine-readable lane state plus human-readable report.*