# Legal Distance Lane — Final Audit Verification (Run 37701901179)

## Executive Summary

**Lane:** legal-distance
**Factory Direction:** v35
**Status:** BLOCKED_ON_DEPENDENCIES | evidence_tier: ACCEPTED | continue_recommended: false
**Audit Readiness:** ✅ CONFIRMED

The legal-distance lane has successfully completed its PIVOT_WITHIN_MISSION characterization per factory direction v34 audit (CYCLE_37090665528). The original hypothesis — that dense embeddings would beat TF-IDF on jurist preference at scale — has been **falsified** by accepted evidence. The strategic pivot has been fully executed and validated.

---

## PIVOT_WITHIN_MISSION — Completed

### Original Hypothesis (FALSIFIED)
> Dense embeddings (center_projected) would beat TF-IDF citation hybrids on jurist preference at 174k scale.

### Accepted Evidence Against Original Hypothesis
| Finding | Evidence | Status |
|---------|----------|--------|
| Dense embeddings FAIL jurist gate at ALL scales | JP 0.05–0.43 across 3yr–165k | ✅ ACCEPTED |
| TF-IDF citation hybrids DOMINATE jurist preference | JP 0.78–0.79, PASS both adversarial gates at 174k | ✅ ACCEPTED |
| True OOS JuristPref ceiling ~0.53 < 0.7 factory target | v8 holdout validation (train-only TF-IDF/SVD on 80%) | ✅ ACCEPTED |
| Linear hybrids PASS adversarial but REMAIN BELOW TF-IDF | JP 0.61–0.67 vs TF-IDF 0.78–0.79 | ✅ ACCEPTED |
| v18 coarse hierarchy NEGATIVE | Max branch purity 0.65 < 0.7 threshold | ✅ ACCEPTED |

### New Question (ANSWERED)
> **What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?**

**Answer delivered via:** `legal_distance_v34_minimal_dense_scale_characterization.md` and `scale_characterization_results.json`

---

## Three Complementary Modes — Minimal Scales Characterized

### 1. CITATION HERITAGE VIEW
- **Minimal scale:** 21yr / 137k decisions (2000–2020)
- **Best mode:** `center_projected_64dim`
- **Acceptance criterion:** AUC > 0.75 on center_projected
- **Results:** AUC 0.77–0.85 at 21–24yr (137k–158k); superior to TF-IDF citation-based (0.71–0.74) and TF-IDF text-based (0.50–0.63)
- **Requirement:** Recent years (2019+) for sufficient citation pair density
- **Status:** ✅ PASSED at 21–24yr

### 2. SECTION CROSS-LINGUAL VIEW
- **Minimal scale:** 1K sample (decisions with extracted sections)
- **Best mode:** `center_projected_64dim` per section
- **Hierarchy confirmed:** Sachverhalt > Dispositiv > Erwaegungen
  - Sachverhalt (facts): cross_lang_same_branch = 0.282 > 0.2 ✅ PASS, invariance_gap = 0.187
  - Dispositiv (holding): cross_lang_same_branch = 0.150 > 0.1 ✅ PASS, invariance_gap = 0.397
  - Erwaegungen (reasoning): cross_lang_same_branch = 0.094 < 0.1 ❌ FAIL, invariance_gap = 0.452
- **Center projection improves all sections** (Sachverhalt gap: 0.304→0.187; Erwaegungen: 0.538→0.452; Dispositiv: 0.575→0.397)
- **Status:** ✅ PASSED at sample scale; **full corpus BLOCKED** pending 174k section extraction

### 3. LINEAR HYBRID COMPLEMENT
- **Minimal scale:** 19yr / 122k decisions (2000–2018)
- **Optimal weights:** w=0.3–0.4 dense / 0.6–0.7 TF-IDF (shifts toward TF-IDF at larger scale)
- **Acceptance criterion:** PASS both adversarial gates AND cross_lingual improvement over TF-IDF
- **Results:** PASS adversarial at 19yr+ (JP 0.61–0.67); cross-lingual recall 0.14–0.16 vs TF-IDF 0.12
- **Status:** ✅ PASSED at 19yr+; **NOT primary** — JP remains below TF-IDF baseline (0.78–0.79)

---

## Fundamental Two-Mode Tradeoff (REPRODUCED AT ALL SCALES)

| Mode | Language Dominance | Jurist Preference | Citation Independence | Characteristic |
|------|-------------------|-------------------|----------------------|----------------|
| TF-IDF Citation Hybrids | ~0.48 | ~0.78 | ~14% | Legal relevance, monolingual clusters |
| Dense Semantic (center_projected) | 0.83–0.98 | 0.05–0.43 | ~37% | Cross-lingual, language-dominated |
| Linear Hybrids (optimal) | 0.58–0.80 | 0.61–0.67 | 20–30% | Best of both, but below TF-IDF JP |

**Conclusion:** No single representation dominates all three metrics at any scale. Fundamental tradeoff between legal relevance (TF-IDF) and cross-lingual reach (dense).

---

## Data Blockers (Require Corpus Lane Resumption)

1. **bge_ / bger_ ID mapping** — No cross-mapping between published (bge_) and unpublished (bger_) decision IDs
2. **Parquet 2024–2026** — 15,536 decisions missing (years 2024–2026)
3. **Section extraction at 174k** — Sachverhalt/Erwaegungen/Dispositiv not extracted at full corpus scale

These are **data dependency blockers**, NOT scientific failures. The 2022–2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75), contradicting progress.json 'failed' flags.

---

## Test Results

```
test_complementary_role_v34.py: 8/8 PASSED
  ✅ test_citation_heritage_superiority
  ✅ test_citation_heritage_minimal_scale
  ✅ test_section_crosslingual_hierarchy
  ✅ test_linear_hybrid_optimal_weight
  ✅ test_two_mode_tradeoff_fundamental
  ✅ test_true_oos_ceiling
  ✅ test_tfidf_174k_primary_validated
  ✅ test_data_blockers_identified
```

All tests reproducible on 12k ACCEPTED dense embeddings (2000–2002) with IDENTICAL scale-dependent patterns:
- Cross-lingual inflation at small homogeneous scale (0.656→0.957)
- Legal area purity degradation with scale (0.61→0.47)
- Branch k-NN accuracy stable (>0.99 at all scales)
- Linear hybrid PASS jurist proxy at all weights

---

## Product Integration Contracts (Frozen)

| View | Representation | Status | User Intent | Performance |
|------|---------------|--------|-------------|-------------|
| **Primary Navigation** | cited_outcome_hybrid_0.5 (TF-IDF) | **PRODUCTION v1.0** | Jurist finds legally relevant neighbors | JP 0.78–0.79, LangDom ~0.48 |
| **Citation Heritage** | center_projected_64dim | READY v1.1+ | Jurist explores doctrinal lineage | AUC 0.79–0.85 (> TF-IDF 0.71–0.74) |
| **Cross-Lingual** | center_projected_64dim per section | BLOCKED v1.1+ | Jurist finds equivalent decisions in other languages | Sachverhalt 0.282, Dispositiv 0.150 (1K sample) |
| **Hybrid Explore** | linear_citation_concat_w0.4 | EXPLORATORY v1.1+ | Jurist trades legal relevance for cross-lingual reach | JP 0.61–0.67, cross-lang recall 0.14–0.16 |

---

## Orchestration/Validation Failure Diagnosis

**Root cause:** Data dependency blockers, NOT scientific failure.
- bger_YYYY.jsonl files missing from canonical corpus for years 2000–2019
- finalize_174k_embeddings.py asserts full 173k metadata match; checkpoints cover 158k (2000–2023)
- bger_ (unpublished) vs bge_ (published) ID systems with no cross-mapping
- Section extraction not run at 174k scale
- Factory direction v30/v33 claimed "CORPUS MOUNT PATH GAP RESOLVED" but /tmp/lex_accepted/core/ does not exist

**All valid completed work preserved.** The 24-year/158k citation heritage evaluation, 174k formal TF-IDF suite, 1K section cross-lingual sample, and scale characterization experiment are ACCEPTED and reproducible.

---

## Verification History (Selected)

| Run ID | Date | Status | Notes |
|--------|------|--------|-------|
| 37698644556 | 2026-10-07 | FINAL_AUDIT_VERIFICATION_COMPLETE | All 8/8 test_complementary_role_v34.py + 15/15 test_v29_final_results.py PASSED |
| 37592086723 | 2026-10-07 | FINAL_AUDIT_VERIFICATION_COMPLETE | Operational resume from producer snapshot; scale characterization reproduced |
| 37531010443 | 2026-10-06 | FINAL_AUDIT_VERIFICATION_COMPLETE | Orchestration failure diagnosed and repaired (progress.json corrected) |
| 37454210884 | 2026-10-06 | VERIFICATION_CONFIRMED | Factory direction v34; complementary role characterization COMPLETE |

---

## Recommendation

**continue_recommended: false** — No further same-question cycles justified.

**Next actions (for Factory Director):**
1. **Corpus lane:** Resume for bge_↔bger_ mapping, 2024–2026 parquet, 174k section extraction
2. **Product lane:** Ship v1.0 with TF-IDF citation hybrids as primary (JP 0.78 vs 0.43 semantic baseline)
3. **Dense integration:** v1.1+ for citation-heritage view and cross-lingual view (contracts defined and frozen)
4. **No new Frontier team** — Portfolio v7 confirmed (both teams TERMINATED; true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria)

---

## Evidence References (Immutable)

- `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v8_holdout_zero_shot_validation/holdout_zero_shot_validation_fixed.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json`
- `legal_distance/reports/legal_distance_v34_complementary_role.md`
- `legal_distance/reports/legal_distance_v34_minimal_dense_scale_characterization.md`

---

**Verified by:** Legal Distance Lane Agent
**Timestamp:** 2026-10-07T23:30:00Z
**Run ID:** 37701901179
**Factory Direction Version:** 35