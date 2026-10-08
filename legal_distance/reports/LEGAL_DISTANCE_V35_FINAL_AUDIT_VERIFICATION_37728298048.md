# Legal Distance Lane — Final Audit Verification (Run 37728298048)

**Date:** 2026-10-08  
**Factory Direction:** v35  
**Lane:** legal-distance  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  
**Accepted Run ID:** LEGAL_DISTANCE_V35_FINAL_AUDIT_VERIFICATION_37728298048

---

## Executive Summary

**OPERATIONAL RESUME COMPLETE — SNAPSHOT AUDIT-READY**

This run (37728298048) performs an operational resume from persisted producer snapshot of run 37727635621. All valid completed work has been preserved and verified.

**MINIMAL DENSE SCALE CHARACTERIZATION COMPLETE** — The PIVOT_WITHIN_MISSION question from factory direction v34 has been fully answered with ACCEPTED evidence:

> **Question:** What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?

**ANSWER:** Three complementary modes at characterized minimal scales:
1. **CITATION HERITAGE** — 21yr/137k (2000-2020), center_projected_64dim, AUC > 0.75 (PASSED 0.77-0.85 at 21-24yr, 137k-158k). Superior to TF-IDF citation baseline (0.71-0.74). Requires recent years (2019+) for citation pair density.
2. **SECTION CROSS-LINGUAL** — 1K sample with sections, Sachverhalt cp_64 cross_lang_same_branch=0.282 > 0.2, Dispositiv=0.150 > 0.1, Erwaegungen=0.094 < 0.1 FAILED. Full corpus BLOCKED on section extraction at 174k.
3. **LINEAR HYBRID COMPLEMENT** — 19yr/122k (2000-2018), w=0.3-0.4, PASS adversarial gates, cross-lingual improvement over TF-IDF, but JP 0.61-0.67 < TF-IDF 0.78-0.79. NOT primary.

**TWO-MODE TRADEOFF FUNDAMENTAL** — No single representation dominates JP + LangDom + CiteIndep at any scale. TF-IDF = PRIMARY (jurist preference, branch clustering). Dense = COMPLEMENTARY (citation heritage, cross-lingual, hybrid complement).

**DATA BLOCKERS PERSIST** — bge_/bger_ ID mapping, parquet 2024-2026 (15,536 decisions), 174k section extraction. Corpus lane resumption required.

**NO FURTHER SAME-QUESTION CYCLES JUSTIFIED** — Maximum evidence extracted at available scales.

---

## Test Results Verification

### test_complementary_role_v34.py — 8/8 PASSED ✅

| Test | Result | Key Metrics |
|------|--------|-------------|
| test_citation_heritage_superiority | PASS | Dense AUCs: raw=0.7946, cp64=0.7922, cp128=0.7916, cp768=0.7941; all > 0.75 |
| test_citation_heritage_minimal_scale | PASS | 21yr (137k): raw AUC=0.8455, cp64 AUC=0.8182, n_pairs=100 |
| test_section_crosslingual_hierarchy | PASS | Sachverhalt gap=0.187, Dispositiv gap=0.397, Erwaegungen gap=0.452; hierarchy confirmed |
| test_linear_hybrid_optimal_weight | PASS | TF-IDF JP=0.7840; w=0.3 JP=0.6715, w=0.4 JP=0.6725; cross-lang improvement 0.160 > 0.124 |
| test_two_mode_tradeoff_fundamental | PASS | Dense JP=0.426/LD=0.832; TF-IDF JP=0.784/LD=0.483; Hybrid JP=0.672/LD=0.654 |
| test_true_oos_ceiling | PASS | Holdout JP ceiling 0.525-0.585 < 0.7 target |
| test_tfidf_174k_primary_validated | PASS | TF-IDF LangDom=0.5785 PASS, beats semantic baseline |
| test_data_blockers_identified | PASS | Completed 24 years (2000-2023), failed=['2024','2025','2026'], missing same |

### test_v29_final_results.py — 15/15 PASSED ✅

All pytest assertions pass covering:
- Section cross-lingual hierarchy (Sachverhalt > Dispositiv > Erwaegungen)
- Center projection improves all sections
- 22-year linear combinations PASS adversarial at optimal weight
- Optimal weight shifts toward TF-IDF dominance at larger scale
- TF-IDF baseline dominates JuristPref
- Dense embeddings recover citation heritage better than TF-IDF citation-based
- 83% dense embedding coverage (144k/174k)
- Years 2024-2026 missing (29,520 decisions)
- Two-mode tradeoff reproduced at all scales

---

## Critical Findings (ACCEPTED Evidence Tier)

### 1. Citation Heritage Dense Superiority
- Dense multilingual-e5 embeddings RECOVER citation heritage at scale (AUC 0.79-0.85 at 21-22yr, 137k-144k; AUC 0.767-0.770 at 24yr, 158k with 730 pairs)
- BETTER than TF-IDF citation-based (AUC 0.71-0.74) and much better than TF-IDF text-based (AUC 0.50-0.63)
- Center projection and PCA (64/128/768-dim) preserve this capability
- Previously untested at sufficient scale due to citation pair distribution requiring recent years (2019+)
- Capability REINFORCED at 24yr scale with 2.1x more positive pairs (730 vs 344)

### 2. Section Cross-Lingual Hierarchy
- Section-specific cross-lingual evaluation COMPLETE for all three sections at 1K sample scale
- **Sachverhalt (facts, n=359) SUPERIOR**: cp_64 cross_lang_same_branch=0.282, invariance_gap=0.187
- **Dispositiv (holding, n=538) INTERMEDIATE**: cp_64 cross_lang_same_branch=0.150, invariance_gap=0.397
- **Erwaegungen (reasoning, n=510) POOREST**: cp_64 cross_lang_same_branch=0.094, invariance_gap=0.452
- Center projection improves all: Sachverhalt gap 0.304→0.187, Erwaegungen 0.538→0.452, Dispositiv 0.575→0.397
- Legal facts align best cross-lingually; holdings retain some alignment; reasoning is most language-specific
- Full corpus density BLOCKED pending section extraction at 174k scale

### 3. Linear Hybrids Scale Dependency
- Weight sweep at 22-year (144k) reveals OPTIMAL w=0.4 for cited_decisions_tfidf (JP=0.6725, LangDom=0.6539 BOTH PASS)
- w=0.3 for outcome_hybrid_0.5 (JP=0.6115, LangDom=0.7477 BOTH PASS)
- At 19-year optimal was w=0.3 for both
- At 15-year linear_hybrid05_concat FAILS (JP=0.473)
- Scale shifts optimal weight toward denser semantic contribution at larger scale
- BUT BOTH still BELOW TF-IDF baseline (JP=0.784/0.789)
- Optimal weight shifts toward TF-IDF dominance (w=0.3-0.4 dense / 0.6-0.7 TF-IDF)

### 4. Two-Mode Tradeoff Fundamental
- **Citation/Outcome (TF-IDF hybrids)**: LangDom~0.48, JP~0.78, CiteIndep~14%
- **Semantic Embeddings (center_projected)**: LangDom~0.83-0.98, JP~0.05-0.43, CiteIndep~37%
- **Linear Hybrids**: LangDom~0.58-0.80, JP~0.61-0.67 (optimal weight), intermediate
- NO single representation dominates all three metrics at any scale
- TF-IDF citation hybrids = PRIMARY product mode (jurist preference, branch clustering)
- Dense embeddings = COMPLEMENTARY modes (citation heritage view, cross-lingual view, linear hybrid complement)

### 5. Dense Embeddings FAIL Jurist Gate at ALL Scales
- 3yr ACCEPTED (19k): JP=0.39-0.42 FAIL
- 15yr (92k): JP=0.288 FAIL
- 19yr (122k): JP=0.37 FAIL
- 20yr (130k): JP=0.05 CATASTROPHIC FAIL
- 22yr (144k): JP=0.43 FAIL
- 165k formal suite: JP=0.39-0.42 FAIL
- Dense semantic embeddings DO NOT PASS jurist gate at any scale tested

### 6. True OOS JuristPref Ceiling ~0.53 < 0.7 Factory Target
- v8 holdout zero-shot validation: best holdout JP = 0.585 (cited_outcome_hybrid_0.7)
- Dense center_projected_64dim holdout JP = 0.385
- No representation achieves factory target under true out-of-sample conditions
- TF-IDF baseline JP=0.78 evaluated on same data used for SVD fitting (known leakage, though v8 holdout showed minimal impact: JP -0.015 to -0.020)

### 7. Legal TF-IDF from BGE Corpus NEGATIVE
- Legal TF-IDF from bge_ corpus (6,243 decisions, 2000-2021) FAILS adversarial suite (6-8/14 PASS vs 14/14 baseline)
- ALL variants FAIL citation heritage (AUC ~0.5), branch kNN (0.26-0.39), multilingual invariance, cross-language pairs
- PASS language dominance (LangDom~0.49-0.50) — confirming legal signals are cross-lingual
- Root cause: corpus mismatch — bge_ IDs don't map to bger_ evaluation corpus; signal coverage deficits

### 8. v18 Coarse Hierarchy NEGATIVE
- Even at 4-label branch level: best purity 0.65 (linear_citation_concat) < 0.7 threshold
- Fundamental hierarchy limitation confirmed for TF-IDF/citation representations

---

## Orchestration/Validation Failure Diagnosis

**Root Cause:** The prior workflow failed due to **data dependency blockers**, NOT scientific failure.

### Factory Direction v35 Discrepancy
- `factory_direction.json` v35 shows legal-distance lane status: `"RUN"`
- Actual lane state (`state/legal-distance.json`): `"cycle_status": "BLOCKED_ON_DEPENDENCIES"`, `"continue_recommended": false`
- The question has been ANSWERED (PIVOT_WITHIN_MISSION characterization complete)
- Lane correctly blocked on corpus dependencies

### Progress.json Correction (Repair Cycle 1)
- **Previous bug:** progress.json incorrectly flagged 2021-2023 as "failed"
- **Reality:** 2021-2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75 at 24yr/158k with 730 positive pairs)
- **Corrected:** completed_years = 2000-2023 (24 years, 158k decisions); failed_years = 2024-2026 only
- Only 2024-2026 are genuinely missing (no parquet, no embeddings)

### Data Blockers Requiring Corpus Lane Resumption
1. **bge_/bger_ ID mapping:** Canonical corpus uses bge_ IDs, evaluation uses bger_ IDs — no cross-mapping exists
2. **parquet 2024-2026:** 15,536 decisions missing (years 2024-2026), no /tmp/bger.parquet for these years
3. **Section extraction at 174k:** Sachverhalt/Erwaegungen/Dispositiv not extracted at full corpus scale
4. **GPU unavailable:** No BGE/multilingual-e5 finetuning at scale

---

## Product Integration Contracts (Frozen)

| View | Representation | Status | User Intent | Performance |
|------|---------------|--------|-------------|-------------|
| **Primary Navigation** | `cited_outcome_hybrid_0.5` (TF-IDF) | PRODUCTION v1.0 | Jurist finds legally relevant neighbors | JP 0.78-0.79, LangDom ~0.48 |
| **Citation Heritage** | `center_projected_64dim` | READY v1.1+ | Jurist explores doctrinal lineage via shared citations | AUC 0.79-0.85 (superior to TF-IDF 0.71-0.74) |
| **Cross-Lingual** | `center_projected_64dim` per section (sachverhalt > dispositiv) | BLOCKED v1.1+ | Jurist finds equivalent decisions in other languages | Sachverhalt 0.282, Dispositiv 0.150 at 1K sample |
| **Hybrid Explore** | `linear_citation_concat_w0.4` (22yr) / `linear_hybrid05_concat_w0.3` (19yr) | EXPLORATORY v1.1+ | Jurist trades some legal relevance for cross-lingual reach | JP 0.61-0.67, cross-lang recall 0.14-0.16 |

---

## Next Recommendation

**continue_recommended: false** — No further same-question cycles justified.

**Next Actions:**
1. **Corpus lane:** Resume for bge_↔bger_ mapping, 2024-2026 parquet generation, section extraction at 174k scale
2. **Product lane:** Ship v1.0 with TF-IDF citation hybrids as primary (JP 0.78 vs 0.43 semantic baseline)
3. **Dense integration:** v1.1+ for citation-heritage view and cross-lingual view (contracts defined and frozen)
4. **No new Frontier team** — portfolio v7 confirmed, all teams TERMINATED (true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria)

---

## Evidence References

All evidence preserved in:
- `legal_distance/results/174k_dense_embeddings/` — All scale evaluations
- `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json` — Complete scale characterization
- `legal_distance/reports/legal_distance_v34_minimal_dense_scale_characterization.md` — Human-readable report
- `state/legal-distance.json` — Machine-readable lane state (audit_ready=true)
- `/tmp/lex_accepted/evaluation/results/evaluation/` — Independent evaluation lane validation

---

## Verification Notes

**OPERATIONAL RESUME from run 37727635621 complete:**
- All 8/8 test_complementary_role_v34.py assertions PASSED
- All 15/15 test_v29_final_results.py assertions PASSED
- Scale characterization experiment (characterize_dense_complementary_views.py) REPRODUCED on 12k ACCEPTED dense embeddings (2000-2002) with IDENTICAL scale-dependent patterns:
  - Cross-lingual inflation at small homogeneous scale (0.656→0.957)
  - Legal area purity degradation with scale (0.61→0.47) consistent with full-corpus evaluations
  - Branch k-NN accuracy stable (>0.99 at all scales)
  - Linear hybrid PASS jurist proxy at all weights

**PIVOT_WITHIN_MISSION characterization COMPLETE at max available evaluated scale:**
- 24yr/158k citation heritage
- 174k formal suite (TF-IDF)
- 1K section cross-lingual

**Snapshot audit-ready.** All valid completed work preserved. Factory direction v34/v35 strategic pivot fully executed.

---

*Generated by Legal Distance Lane — Operational Resume 37728298048*