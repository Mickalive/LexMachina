# Evaluation Lane Cycle Report — Factory Direction v28

**Date**: 2026-09-29  
**Lane**: evaluation  
**Direction Version**: 28  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: MONITORING  
**Continue Recommended**: TRUE  

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions** of factory direction v28 for the currently available representations (TF-IDF family at 174k). The lane is now in active **MONITORING mode** (check_count=231), awaiting 174k dense embeddings, citation-role embeddings, and linear hybrid embeddings from legal-distance.

### Completed Work (All Three Sub-Questions)

| Sub-Question | Status | Details |
|--------------|--------|---------|
| **1. Full 12-benchmark formal suite at 174k** | ✅ COMPLETE | 8 TF-IDF representations evaluated with frozen harness v3 thresholds; HNSW artifact fixed via exact k-NN on stratified subsample (n=2000) |
| **2. Citation heritage benchmark at 174k** | ✅ COMPLETE | Frozen 2,040-pair pool (1,020 positive + 1,020 negative, seed=42) using 174k citation-ID resolution (2,019/2,105 resolved, 95.9%) |
| **3. v17b label normalization generalization to 174k** | ✅ COMPLETE | 85,819/173,963 labels normalized (214→164 unique areas); differential effect CONFIRMED and CORRECTED |

---

## Key Findings

### 1. Fundamental Two-Mode Tradeoff Reproduced at 174k Scale

| Mode | Language Dominance | Jurist Preference | Citation Heritage (AUC) | Citation Heritage (recall@10) |
|------|-------------------|-------------------|------------------------|-------------------------------|
| **Citation-based** (cited_decisions_tfidf, outcome hybrids) | PASS (0.44–0.53) | PASS (0.63–0.80) | PASS (0.72–0.76) | **FAIL** (<0.06) |
| **Text-based** (full_text_tfidf_light, regeste hybrids) | **FAIL** (~0.99) | **FAIL** (~0.02–0.08) | PASS (0.85–0.90) | **FAIL** (<0.06) |

**Production default** `cited_decisions_tfidf_outcome_hybrid_0.5`: LangDom=0.477, Jurist=0.735, CiteHeritage AUC=0.760

### 2. Citation Heritage: Systematic Failure at 174k

- **All 8 TF-IDF representations FAIL** recall@10 threshold (threshold ≥0.2)
- Best recall@10: `full_text_tfidf_light`=0.052, `cited_decisions_tfidf`=0.044
- Citation graph pair pool covers only 2,936 unique decisions (~1.69% of 173,963)
- Citation-independent retrieval near-zero for citation signals; text signals achieve AUC 0.85–0.90 at smaller scale but collapse on adversarial gates at full scale

### 3. v17b Label Normalization: Differential Effect Confirmed (Corrected)

- **49.3% labels normalized** (85,819/173,963 decisions, 214→164 unique legal_area values)
- **Citation-based reps**: Modest purity gains (3–10%, 1.03–1.10x) across hierarchy/zoom_fine/legal_area
- **Text-based reps**: Significant degradation on zoom_fine (16–34% loss, 0.66–0.84x), hierarchy/legal_area roughly stable (~1.0x)
- **NMI metrics**: Modest degradation for both families
- **Only `regeste_tfidf`** satisfies no-worsening on ALL hierarchy metrics
- **Prior report overstated gains by ~10x** — corrected per audit CYCLE_36527630008
- **V6 dense 12k**: NO improvement (hierarchy 1.00x, zoom 1.01x, legal_area 1.00x; NMI drops 0.59→0.45)
- **15-year partial dense**: NO improvement

### 4. Dense Embeddings: Scale Dependency Confirmed

| Scale | Adversarial (LangDom) | Hierarchy Purity | Legal Area Purity | Cross-Lang NMI |
|-------|----------------------|------------------|-------------------|----------------|
| 12k (3 years ACCEPTED) | **FAIL** (0.99) | **FAIL** (0.42) | **FAIL** (0.009) | PASS (~0.47) |
| 100k (15-year partial) | **FAIL** (0.98–0.99) | — | — | — |
| 174k TF-IDF (citation-based) | **PASS** (0.44–0.53) | FAIL (<0.3) | FAIL (<0.1) | PASS |

**Root cause**: 18.3% metadata coverage, partial corpus center-projection, raw multilingual-e5 language clustering. At all tested scales, dense embeddings cluster by language not law.

### 5. Infrastructure Verified Operational

- ✅ **Adversarial benchmarks**: Exact k-NN on stratified subsample (n=2000), production default reproduces LangDom=0.4794 PASS, JuristPref=0.7140 PASS
- ✅ **Citation heritage pairs**: 2,040 frozen pairs regenerated from resolved citation graph; evaluation re-run
- ✅ **v17b normalization**: Differential effect reproduced across all 8 TF-IDF reps; v6 dense 12k and 15-year partial tested: NO improvement
- ✅ **HNSW artifact fix**: Exact k-NN on valid subset avoids HNSW masking representation differences
- ✅ **V25 formal suite**: Frozen protocol v25 executed on all 8 TF-IDF reps at 174k (config hash 4323f833fa72366a); also executed on v6 dense 12k and 15-year partial dense
- ✅ **Scalable NN**: sklearn exact k-NN for adversarial (n=2000 subsample), HNSW for full-corpus citation heritage
- ✅ **Monitor script**: ACTIVE (check_count=231, last_check=2026-09-29T18:58:26Z)

---

## Blockers (External to Evaluation Lane)

| Blocker | Status | Impact |
|---------|--------|--------|
| **legal-distance dense 174k** | 15/26 years in checkpoints (2000-2014); final concatenation PENDING; only 3/26 years ACCEPTED | Cannot evaluate dense modes at 174k |
| **legal-distance citation roles** | Not yet available at 174k | Cannot evaluate citing/following/criticizing role embeddings |
| **legal-distance linear hybrids** | Not yet delivered at 174k | Cannot evaluate `linear_citation_concat`, `linear_hybrid05_concat` |
| **Fractal map** | Blocked on dense embeddings | Single remaining dependency per factory direction v28 |
| **Product** | Blocked on dense embeddings | Cannot switch production default to dense modes |
| **Jurist human study** | Framework ready; requires 5-10 Swiss jurists | External dependency, not technical |

---

## Readiness for Next Representations

All evaluation infrastructure is **READY** for auto-evaluation when representations land:

| Component | Status |
|-----------|--------|
| Formal suite script (`run_174k_formal_suite.py`) | OPERATIONAL — verified 2026-09-29T19:35:29 (production default PASS) |
| V25 formal suite runner | OPERATIONAL — verified 2026-09-27T22:04:04 |
| Scalable NN infrastructure | READY (exact k-NN on stratified subsample for adversarial, HNSW for full-corpus) |
| Citation heritage pipeline | READY (frozen 2,040 pair pool, 95.9% resolution) |
| v17b normalization pipeline | READY — differential effect verified |
| Metadata 174k | VERIFIED (173,963 entries, branch+legal_area 100% coverage) |
| Monitor script | ACTIVE (check_count=231) |

---

## Recommendation

**CONTINUE MONITORING** (`continue_recommended=true`)

The evaluation lane has a concrete discriminating purpose: automatically evaluate awaited representations (174k dense embeddings, citation roles, linear hybrids) as they land in accepted state from legal-distance. No additional same-question cycle is justified until new representations are available.

The fundamental two-mode tradeoff (citation-based vs. text-based) is **reproduced at full 174k scale** with frozen thresholds. Dense embeddings **fail adversarial gates at all tested scales** (12k, 100k partial) due to language clustering. The v17b label normalization shows a **differential effect** — it helps citation-based representations but harms text-based ones on zoom_fine.

---

## Evidence References

- `evaluation/state/evaluation.json` — Machine-readable lane state
- `evaluation/state/evaluation_state.json` — Detailed cycle state
- `evaluation/state/monitor_174k_state.json` — Monitor state (check_count=231)
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — Formal suite results
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` — Citation heritage results
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` — v17b normalization results
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — V25 suite summary
- `results/evaluation/v25_174k_formal_suite/partial_dense_results/dense_v6_2000_2002_12k.json` — V6 dense 12k results
- `evaluation/reports/EVALUATION_174K_CYCLE_REPORT_v28_COMPLETION_20260928.md` — Prior completion report

---

*Report generated: 2026-09-29T19:35:29Z*  
*Next monitor check: Automatic (continuous)*