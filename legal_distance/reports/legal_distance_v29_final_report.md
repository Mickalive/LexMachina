# Legal Distance Lane — Factory Direction v29 Final Report

**Lane**: legal-distance  
**Direction Version**: 29  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Evidence Tier**: REPRODUCED  
**Continue Recommended**: false  
**Run ID**: legal_distance_v29_174k_evaluation_final_20261003_section_crosslingual_complete  
**Date**: 2026-10-03

---

## Executive Summary

The legal-distance lane has executed the factory direction v29 question to its maximum feasible extent. All five deliverables have been addressed at the maximum available scale (22-year / 144,443 decisions, 2000-2021). **Fundamental upstream data blockers prevent completion at the 174k target scale** (173,963 decisions, 2000-2026).

### Deliverable Status

| # | Deliverable | Status | Max Scale Achieved |
|---|-------------|--------|-------------------|
| 1 | Complete 174k dense embedding assembly & evaluation | **BLOCKED** | 144k (22 years, 2000-2021) |
| 2 | Full-corpus adversarial evaluation (all representations) | **PARTIAL** | TF-IDF: 174k ✓; Dense: 144k |
| 3 | Section-specific cross-lingual evaluation (sachverhalt/erwaegungen/dispositiv) | **SAMPLE COMPLETE** | 1K sample (all 3 sections) |
| 4 | Scale linear_hybrid05_concat stability test | **BLOCKED** | 144k (22-year) ✓ |
| 5 | Production-vs-CV tradeoff (TF-IDF SVD leakage) | **COMPLETE** | 174k ✓ (v8 holdout) |

---

## Critical Findings

### 1. TF-IDF 174k Formal Suite — COMPLETE & VALIDATED ✓
- All 8 TF-IDF representations PASS both adversarial gates (LangDom, JuristPref) on frozen harness v3 at 173,963 decisions
- **Production default**: `cited_decisions_tfidf_outcome_hybrid_0.5` — LangDom=0.4773, JuristPref=0.7345
- Citation-based signals dominate legal relevance at 174k scale

### 2. Dense Embedding Blocker — FUNDAMENTAL 🚫
- Checkpoints cover 144,443/173,963 decisions (83.0%, years 2000-2021)
- **Missing**: Years 2022-2026 (29,520 decisions)
- **Root causes**: No parquet at `/tmp/bger.parquet`; no bge_↔bger_ ID mapping; `finalize_174k_embeddings.py` fails metadata order verification
- **Upstream**: Corpus lane PAUSED at v17 snapshot; data acquisition required

### 3. Center-Projected Embeddings FAIL Jurist Gate at ALL Scales ❌
| Scale | Decisions | center_projected JP | center_projected LangDom | Status |
|-------|-----------|---------------------|-------------------------|--------|
| 3-year (ACCEPTED) | 19,441 | 0.39-0.42 | ~0.85 | FAIL |
| 15-year | 91,929 | 0.288 | 0.8929 | FAIL |
| 19-year | 122,015 | 0.3685 | 0.8603 | FAIL |
| 20-year | 129,680 | **0.0475** | **0.9828** | CATASTROPHIC |
| 22-year | 144,443 | 0.4265 | 0.8319 | FAIL |

**Key insight**: Dense semantic embeddings do not pass jurist gate at any scale; catastrophic failure at 20-year; partial recovery at 22-year.

### 4. Linear Combinations — PASS at Scale but Below TF-IDF Baseline 📊
Weight sweep reveals **scale-dependent optimal weights**:

| Scale | Representation | Optimal w | JP | LangDom | vs TF-IDF Baseline |
|-------|---------------|-----------|-----|---------|-------------------|
| 19-year | linear_citation_concat | 0.3 | 0.6465 | 0.6264 | Below (0.7235) |
| 19-year | linear_hybrid05_concat | 0.3 | 0.6365 | 0.6617 | Below (0.7155) |
| **22-year** | **linear_citation_concat** | **0.4** | **0.6725** | **0.6539** | **Below (0.784)** |
| **22-year** | **linear_hybrid05_concat** | **0.3** | **0.6605** | **0.6395** | **Below (0.789)** |

- First dense-hybrids to PASS adversarial gates at 19yr and 22yr
- Optimal weight shifts toward TF-IDF dominance (w=0.3-0.4 dense / 0.6-0.7 TF-IDF) at larger scale
- Citation signals dominate jurist preference; semantic signals add cross-lingual benefit but dilute legal relevance

### 5. Section Cross-Lingual Evaluation — COMPLETE for 3 Sections at 1K Sample ✓

| Section | n (branch-known) | cp_64 cross_lang_same_branch | cp_64 invariance_gap | Rank |
|---------|------------------|------------------------------|----------------------|------|
| **Sachverhalt** (facts) | 359 | **0.282** | **0.187** | 1️⃣ BEST |
| **Dispositiv** (holding) | 538 | 0.150 | 0.397 | 2️⃣ INTERMEDIATE |
| **Erwaegungen** (reasoning) | 510 | 0.094 | 0.452 | 3️⃣ POOREST |

- Center projection improves all: Sachverhalt (0.304→0.187), Erwaegungen (0.538→0.452), Dispositiv (0.575→0.397)
- **Legal facts align best cross-lingually**; holdings retain some alignment; reasoning is most language-specific
- Full corpus density BLOCKED pending section extraction at 174k scale

### 6. Two-Mode Tradeoff REPRODUCED at All Scales ⚖️

| Mode | LangDom | JuristPref | CiteIndep |
|------|---------|------------|-----------|
| Citation/Outcome (TF-IDF hybrids) | ~0.48 | **~0.78** | ~14% |
| Semantic Embeddings (center_projected) | ~0.83-0.98 | ~0.05-0.43 | ~37% |
| Metric Learning | ~0.58-0.61 | ~0.53-0.61 | ~34-37% |
| Linear Hybrids (optimal weight) | ~0.58-0.80 | ~0.61-0.67 | intermediate |

**No single representation dominates all three metrics at any scale.**

### 7. Production-vs-CV Tradeoff — VALIDATED Minimal Leakage ✓
- v8 holdout (train-only TF-IDF/SVD on 80%): all 4 zero-shot hybrids PASS both gates on true holdout
- Leakage impact: LangDom +0.005, JP -0.015 to -0.020
- No significant information leakage from full-corpus SVD fitting

### 8. Dense Embeddings RECOVER Citation Heritage at Scale 🎯 **NEW FINDING**
- AUC 0.79-0.85 at 21-22yr (137k-144k decisions) — **BETTER than TF-IDF citation-based (0.71-0.74)**
- Center projection and PCA (64/128-dim) preserve this capability (AUC 0.79-0.82)
- Previously untested at sufficient scale (citation pair distribution requires recent years 2019+)
- Semantic embeddings capture doctrinal proximity through shared citations despite failing jurist gate

### 9. Legal TF-IDF from bge_ Corpus — NEGATIVE RESULT ❌
- 6,243 published decisions (2000-2021): FAILS adversarial suite (6-8/14 PASS vs 14/14 baseline)
- ALL variants FAIL citation heritage (AUC ~0.5), branch kNN (0.26-0.39), multilingual invariance
- Root cause: corpus mismatch (bge_ IDs don't map to bger_ evaluation); signal coverage deficits (cited decisions 0.06%, outcomes 0%, Erwägungen 64%)

### 10. Hierarchy & Boilerplate — NEGATIVE Results
- v18 coarse hierarchy: Even at 4-label branch level, best purity 0.65 < 0.7 threshold
- Boilerplate resistance: All representations score ≈ -0.74 to -0.93 (proxy measures language dominance, not procedural boilerplate)

---

## Orchestration Failure Diagnosis

### Root Causes (Unfixable in This Cycle)
1. **bger_YYYY.jsonl missing** from canonical corpus for 2000-2019; only 2020-2024 in raw acquisition
2. **finalize_174k_embeddings.py** asserts full 173k metadata match; checkpoints cover 144k
3. **bger_ (unpublished) vs bge_ (published) ID systems** with no cross-mapping
4. **Section extraction at 174k** requires full corpus text access

### What Went Well
- Year-split checkpointed computation (2000-2021) completed within CPU constraints
- All TF-IDF 174k formal suite evaluations completed and reproduced
- v8 holdout validation cleanly executed with exact k-NN (HNSW artifact fixed)
- Section cross-lingual evaluation COMPLETED for all three sections with clear hierarchy
- Scale dependency rigorously quantified at 15yr/19yr/20yr/21yr/22yr
- Two-mode tradeoff reproduced across all scales and representation families
- 19yr and 22yr linear combinations PASS adversarial gates — first dense-hybrids to do so
- Dense embeddings RECOVER citation heritage at scale (AUC 0.79-0.85)
- Weight sweep reveals optimal w=0.3 at 19yr, w=0.4 at 22yr — scale-dependent optimization
- Legal TF-IDF from bge_ corpus tested — NEGATIVE result with clear diagnosis

---

## Scale Evidence Summary

| Scale | Years | Decisions | Key Result |
|-------|-------|-----------|------------|
| 3-year (ACCEPTED) | 2000-2002 | 19,441 | center_projected JP=0.39-0.42 FAIL |
| 15-year | 2000-2014 | 91,929 | center_projected JP=0.288 FAIL; hybrid JP=0.473 FAIL |
| 19-year | 2000-2018 | 122,015 | Linear combos PASS at w=0.3; TF-IDF baseline dominates |
| 20-year | 2000-2019 | 129,680 | **Catastrophic**: center_projected JP=0.0475 |
| 21-year | 2000-2020 | 137,189 | Citation heritage AUC=0.8455 (raw) |
| **22-year** | **2000-2021** | **144,443** | **Linear combos PASS at optimal w; citation heritage AUC=0.79; center_projected FAIL** |
| **174k Target** | **2000-2026** | **173,963** | **BLOCKED: 29,520 missing decisions (2022-2026)** |

---

## Recommendation

**PIVOT_WITHIN_MISSION REQUIRED**

The legal-distance lane has exhausted all discriminating experiments possible with current data. The fundamental blockers are **upstream data acquisition issues** requiring corpus-lane coordination or a Frontier team:

1. **Parquet data for 2022-2026** (or full bger_ corpus with full_text)
2. **bge_ ↔ bger_ ID mapping** to align published and unpublished decision IDs
3. **Section extraction at 174k scale** from full corpus text

**No further same-question cycles are justified.** The Factory Director should decide the successor question, potentially:
- Frontier team for data acquisition/mapping
- Shift to fractal-map/product lanes using validated TF-IDF production defaults
- New hypothesis on legal-specific embedding approaches that don't require full corpus text

---

## Evidence References (Machine-Readable)

All evidence refs verified accessible:
- Dense embedding checkpoints: `legal_distance/results/174k_dense_embeddings/checkpoints/`
- Section cross-lingual (v3, all 3 sections): `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- Weight sweeps (19yr, 22yr): `linear_combinations_weight_sweep/`, `linear_combinations_weight_sweep_22year/`
- Citation heritage (21yr, 22yr): `citation_heritage_eval/`
- v8 holdout: `v8/holdout_zero_shot_validation_fixed/`
- TF-IDF 174k formal suite: `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/`
- Legal signals v3 (1K sample, 3 sections): `legal_distance/results/legal_signals_1000_v3.jsonl`

---

## Audit Readiness

✅ **AUDIT_READY**: true  
✅ All evidence_refs verified accessible  
✅ Negative results preserved (center_projected failures, bge_ corpus failure, hierarchy negative)  
✅ Provenance maintained (exact timestamps, parameters, seeds)  
✅ Frozen benchmarks not weakened (harness v3 thresholds unchanged)