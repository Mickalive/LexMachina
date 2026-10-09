# Legal Distance Lane — Final Audit Verification
**GitHub Run: 37876565088 | Factory Direction v35 | PIVOT_WITHIN_MISSION Complete**

---

## Executive Summary

**Status: ✅ AUDIT-READY — Lane deliverable complete, no further same-question cycles justified**

This operational resume from the persisted producer snapshot (run 37875715197) verifies that the legal-distance lane has successfully completed its **PIVOT_WITHIN_MISSION** characterization at maximum available evaluated scale. All valid completed work has been preserved. The orchestration/validation failure in prior workflows was diagnosed as **data dependency blockers, NOT scientific failure**.

---

## Verification Checklist

| Criterion | Status | Evidence |
|---|---|---|
| **Hypothesis frozen before measurement** | ✅ | Factory direction v34/v35, complementary_role_characterization_v34.json |
| **Baseline & success rule defined** | ✅ | TF-IDF citation hybrids (JP=0.78) as primary baseline |
| **Claim-bearing sample frozen** | ✅ | 12k ACCEPTED dense (2000-2002), 144k citation heritage, 1K section cross-lingual |
| **Raw outputs preserved** | ✅ | results/legal_distance/ dense_complementary_characterization/, complementary_role_characterization_v34.json |
| **Negative results preserved** | ✅ | Erwaegungen cross-lingual FAIL, dense jurist gate FAIL all scales, true OOS ceiling ~0.53 |
| **Baseline comparison** | ✅ | Dense vs TF-IDF vs Linear Hybrid across all three views |
| **Machine-readable state** | ✅ | state/legal-distance.json (all mandatory fields, direction_version=35) |
| **Human-readable report** | ✅ | reports/legal_distance/dense_embedding_complementary_role_v34_20261003.md |
| **Tests pass** | ✅ | test_complementary_role_v34.py: 8/8 PASS; test_v29_final_results.py: 15/15 PASS |
| **Audit gate** | ✅ | CYCLE_37848241090: PASS, safe_to_integrate=true |
| **continue_recommended** | ✅ | **FALSE** — no further same-question cycles justified |

---

## Key Findings (Reproduced & Frozen)

### 1. Citation Heritage View — Dense Embeddings SUPERIOR
- **Minimal sufficient scale**: ~130k decisions (21-year, 2000–2020) with ≥100 positive citation pairs
- **Best mode**: `center_projected_64dim` (AUC 0.79–0.85 > TF-IDF 0.71–0.74)
- **Similarity gap**: cp64=0.410 vs raw=0.063 (center projection essential)
- **Status**: ✅ **READY at 144k** — integration contract defined for product v1.1+

### 2. Section Cross-lingual View — Dense Embeddings NECESSARY
- **Hierarchy confirmed**: Sachverhalt (0.282) > Dispositiv (0.150) > Erwaegungen (0.094)
- **Center projection improvement**: 38% / 31% / 16% reduction in invariance gap
- **Current evidence**: 1K sample only (Sachverhalt n=359, Dispositiv n=538, Erwaegungen n=510)
- **Status**: ⚠️ **SAMPLE ONLY — BLOCKED** pending 174k section extraction + ID mapping

### 3. Linear Hybrid Complement — Dense Embeddings ADD Cross-lingual Benefit
- **Minimal sufficient scale**: ~122k decisions (19-year, 2000–2018) — first scale PASS both adversarial gates
- **Optimal weights**: w=0.3–0.4 (30–40% dense, 60–70% TF-IDF), shifts toward TF-IDF at larger scale
- **Cross-lingual improvement**: 0.124 → 0.160 recall@10 (but <0.2 threshold)
- **JP remains below TF-IDF**: 0.61–0.67 vs 0.78–0.79
- **Status**: ✅ **READY at 144k** — marked exploratory mode

### 4. Two-Mode Tradeoff — Fundamental at All Scales
| Representation | Jurist Preference | Language Dominance | Citation Independence |
|---|---|---|---|
| TF-IDF Citation Hybrids | **0.78** ✅ | **0.48** ✅ | 0.14 |
| Dense (center_projected) | 0.05–0.43 ❌ | 0.83–0.98 ❌ | **0.37** ✅ |
| Linear Hybrids (opt) | 0.61–0.67 | 0.58–0.80 | 0.25–0.35 |

**No single representation dominates all three metrics at any scale.**

### 5. True OOS Ceiling
- v8 holdout zero-shot validation: **JuristPref ceiling ~0.53 < 0.7 factory target**
- Factory target **unachievable** by any dense embedding method
- Confirms dense embeddings cannot be PRIMARY for jurist navigation

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Resolution |
|---|---|---|
| **bge_ ↔ bger_ ID mapping** | Cannot align canonical corpus with evaluation metadata | Corpus lane |
| **Parquet 2022–2026 missing** | 29,520 decisions (17%) absent from dense embeddings | Corpus lane |
| **Section extraction at 174k** | Cross-lingual view limited to 1K sample | Corpus lane |
| **GPU unavailable** | No BGE/multilingual-e5 finetuning at scale | Infrastructure |

---

## Product Integration Contracts (v1.1+)

| Map Mode | Primary | Complementary Dense Role | User Intent |
|---|---|---|---|
| **Primary Navigation** | `cited_outcome_hybrid_0.5` (TF-IDF) | — | Jurist finds legally relevant neighbors |
| **Citation Heritage** | — | `center_projected_64dim` | Jurist explores doctrinal lineage via shared citations |
| **Cross-lingual** | — | `center_projected_64dim` (sachverhalt > dispositiv) | Jurist finds equivalent decisions in other languages |
| **Hybrid Explore** | `linear_citation_concat_w0.4` | 30–40% dense contribution | Jurist trades some legal relevance for cross-lingual reach |

---

## Recommendation to Factory Director

**CONTINUE = FALSE for same question**

The complementary role is fully characterized at maximum available scale. Next actions:

1. **Corpus lane**: Resume for bge_↔bger_ mapping, 2022–2026 parquet, section extraction at 174k
2. **Product lane**: Ship v1.0 with TF-IDF citation hybrids as primary (JP 0.78 vs 0.43 semantic baseline)
3. **Dense integration**: v1.1+ for citation-heritage view and cross-lingual view (contracts defined above)
4. **No new Frontier team** — portfolio v7 confirmed, all teams terminated (true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria)

---

## Evidence References (Frozen)

All evidence from `state/legal-distance.json` evidence_refs:
- `174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- `174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
- `174k_dense_embeddings/evaluation_22year_center_projected/combined_results.json`
- `174k_dense_embeddings/linear_combinations_19year/linear_combinations_19year_eval_latest.json`
- `174k_dense_embeddings/linear_hybrid05_concat_15year/linear_hybrid05_concat_15year_eval_latest.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v8_holdout_zero_shot_validation/holdout_zero_shot_validation_fixed.json`

---

## Orchestration/Validation Failure Diagnosis

**Root cause**: Data dependency blockers (bge_/bger_ mapping, missing parquet 2024-2026, 174k section extraction), **NOT scientific failure**.

All valid completed work preserved across 20+ verification runs. The lane correctly remains BLOCKED_ON_DEPENDENCIES with `continue_recommended=false`.

---

*Final verification: 2026-10-09 | GitHub Run 37876565088 | Factory Direction v35 | Legal-Distance Lane*