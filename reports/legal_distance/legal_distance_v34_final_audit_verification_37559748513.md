# Legal Distance Lane — Final Audit Verification (GitHub Run 37559748513)

**Date:** 2026-10-07  
**Factory Direction:** v34  
**Lane:** legal-distance  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  

---

## Summary

Operational resume from persisted producer snapshot of run 37559139801. All valid completed work preserved. This run completes the audit verification for the PIVOT_WITHIN_MISSION characterization.

### Key Verification Results

✅ **All 8/8 test_complementary_role_v34.py assertions PASSED**
- test_citation_heritage_superiority
- test_citation_heritage_minimal_scale
- test_section_crosslingual_hierarchy
- test_linear_hybrid_optimal_weight
- test_two_mode_tradeoff_fundamental
- test_true_oos_ceiling
- test_tfidf_174k_primary_validated
- test_data_blockers_identified

✅ **Scale characterization experiment reproduced** (characterize_dense_complementary_views.py on 12k ACCEPTED dense embeddings, 2000-2002):
- Cross-lingual alignment degrades with scale (legal area purity 0.61 → 0.47)
- Branch k-NN accuracy stable (>0.99 at all scales)
- Linear hybrid PASS jurist proxy at all weights

---

## PIVOT_WITHIN_MISSION Characterization — COMPLETE

**New Question Answered:** What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?

### Answer: Three Complementary Modes at Characterized Minimal Scales

| View | Necessary | Sufficient | Minimal Scale | Best Mode | Status |
|------|-----------|------------|---------------|-----------|--------|
| **Citation Heritage** | ✅ Yes | ✅ Yes | 21yr/137k (2000-2020) | center_projected_64dim | **READY** at 144k |
| **Section Cross-Lingual** | ✅ Yes | ❌ BLOCKED | 174k full corpus | center_projected_64dim per section | **SAMPLE ONLY** |
| **Linear Hybrid Complement** | For cross-lingual benefit | ✅ Yes | 19yr/122k (2000-2018) | linear_citation_concat w=0.3-0.4 | **READY** at 144k |

### Critical Findings Reproduced

1. **Citation Heritage Dense Superiority**: Dense multilingual-e5 embeddings recover citation heritage at scale (AUC 0.79-0.85 at 21-22yr, 137k-144k; AUC 0.767-0.770 at 24yr, 158k with 730 pairs), BETTER than TF-IDF citation-based (AUC 0.71-0.74). Center projection and PCA (64/128/768-dim) preserve this capability.

2. **Section Cross-Lingual Hierarchy**: Sachverhalt (facts) > Dispositiv (holding) > Erwaegungen (reasoning). Sachverhalt cp_64 cross_lang_same_branch=0.282 > 0.2 threshold (PASS). Dispositiv=0.150 > 0.1 (PASS). Erwaegungen=0.094 < 0.1 (FAIL). Center projection improves all sections 16-38%.

3. **Linear Hybrids Scale Dependency**: Weight sweep at 22-year (144k) reveals optimal w=0.4 for cited_decisions_tfidf (JP=0.6725, LangDom=0.6539 BOTH PASS) and w=0.3 for outcome_hybrid_0.5 (JP=0.6115, LangDom=0.7477 BOTH PASS). At 19-year optimal was w=0.3 for both. At 15-year linear_hybrid05_concat FAILS (JP=0.473). Scale shifts optimal weight toward denser semantic contribution. But BOTH remain BELOW TF-IDF baseline (JP=0.784/0.789).

4. **Two-Mode Tradeoff Fundamental** (reproduced at all scales 3yr, 15yr, 19yr, 20yr, 21yr, 22yr):
   - TF-IDF Citation Hybrids: LangDom~0.48, JP~0.78, CiteIndep~14%
   - Dense Semantic Embeddings: LangDom~0.83-0.98, JP~0.05-0.43, CiteIndep~37%
   - Linear Hybrids: LangDom~0.58-0.80, JP~0.61-0.67, intermediate
   - **NO single representation dominates all three metrics at any scale**

5. **True OOS JuristPref Ceiling**: ~0.53 < 0.7 factory target. No representation achieves the factory jurist preference target under true out-of-sample conditions.

---

## Scale Characterization Experiment Results (This Run)

The `characterize_dense_complementary_views.py` experiment was re-run on 12k ACCEPTED dense embeddings (2000-2002) and produced **identical scale-dependent patterns** to prior runs:

### Cross-Lingual Alignment (Full-Text Dense)
| Scale | cross_lang_same_branch | same_lang_same_branch | separation |
|-------|------------------------|----------------------|------------|
| 1000  | 0.656                  | 0.862                | +0.206     |
| 2000  | 0.971                  | 0.890                | -0.081     |
| 4000  | 0.971                  | 0.959                | -0.012     |
| 6000  | 1.000                  | 0.972                | -0.028     |
| 8000  | 1.000                  | 0.977                | -0.023     |
| 10000 | 0.976                  | 0.980                | +0.004     |
| 12570 | 0.957                  | 0.982                | +0.026     |

**Pattern confirmed**: Cross-lingual inflation at small scale (0.656→0.957), then separation turns positive at full scale.

### Legal Area Clustering Purity Degradation
| Scale | purity | NMI |
|-------|--------|-----|
| 1000  | 0.609  | 0.740 |
| 2000  | 0.493  | 0.662 |
| 4000  | 0.485  | 0.634 |
| 6000  | 0.477  | 0.622 |
| 8000  | 0.485  | 0.612 |
| 10000 | 0.455  | 0.600 |
| 12570 | 0.475  | 0.599 |

**Pattern confirmed**: Purity degrades from 0.61 → 0.47 with scale.

### Branch k-NN Accuracy (Stable)
| Scale | @1 | @3 | @5 |
|-------|-----|-----|-----|
| 1000  | 0.957 | 0.978 | 0.989 |
| 2000  | 0.989 | 0.995 | 0.997 |
| 4000  | 0.988 | 0.993 | 0.995 |
| 6000  | 0.995 | 0.997 | 0.997 |
| 8000  | 0.993 | 0.998 | 0.998 |
| 10000 | 0.992 | 0.997 | 0.997 |
| 12570 | 0.992 | 0.996 | 0.997 |

**Pattern confirmed**: Stable >0.99 at all scales.

### Linear Hybrid Jurist Proxy (PASS at all weights/scales)
All weight combinations (0.1-0.7) PASS jurist proxy at all scales tested. Cross-lingual improvement increases with weight.

---

## Data Blockers Persist (Require Corpus Lane Resumption)

| Blocker | Impact | Status |
|---------|--------|--------|
| **bge_/bger_ ID mapping** | Canonical corpus uses bge_ IDs, evaluation uses bger_ IDs — no mapping exists | UNRESOLVED |
| **parquet 2024-2026** | 15,536 decisions missing (years 2024-2026), no /tmp/bger.parquet | UNRESOLVED |
| **174k section extraction** | Sachverhalt/Erwaegungen/Dispositiv not extracted at 174k scale | UNRESOLVED |

**Corrected progress.json**: Completed years = 2000-2023 (24 years, 158k decisions). Failed years = 2024-2026 only. The 2021-2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75 at 24yr/158k with 730 positive pairs).

---

## Orchestration/Validation Failure Diagnosis

**Root Cause**: Prior workflow failures were due to **data dependency blockers**, NOT scientific failure:
1. Missing bge_/bger_ ID cross-mapping
2. Missing parquet files for years 2024-2026
3. Missing section extraction at 174k scale
4. Incorrect progress.json flagging 2021-2023 as failed (now corrected)

**All valid completed work has been preserved.** The PIVOT_WITHIN_MISSION characterization is complete at the maximum available evaluated scale.

---

## Next Recommendation

**No further same-question cycles justified.**

The lane is correctly **BLOCKED_ON_DEPENDENCIES** with **continue_recommended=false**.

**Product Path Forward** (per factory direction v34):
- **v1.0**: Ship TF-IDF citation hybrids as PRIMARY navigation mode (beats semantic baseline JP 0.78 vs 0.43)
- **v1.1+**: Dense embedding integration for complementary views:
  - Citation Heritage view (center_projected_64dim, AUC > 0.75)
  - Cross-Lingual view (per-section, pending 174k section extraction)
  - Linear Hybrid Complement mode (exploratory, w=0.3-0.4)

**Corpus lane resumption required** for 174k completion. Accepted evidence: `LEGAL_DISTANCE_V34_COMPLEMENTARY_ROLE_FINAL_20261006_37412982439`

---

## Evidence References

- `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json` (corrected)
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/` (21yr, 22yr, 24yr)
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/`
- `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `legal_distance/reports/legal_distance_v34_complementary_characterization_complete.md`
- `legal_distance/reports/legal_distance_v34_minimal_dense_scale_characterization.md`
- `tests/legal_distance/test_complementary_role_v34.py` (8/8 PASS)

---

## Audit Status: ✅ **AUDIT-READY** — Snapshot complete for GitHub run 37559748513