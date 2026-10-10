# Legal Distance Lane — Final Audit Verification (Run 38023487726)

**Date**: 2026-10-10  
**Factory Direction Version**: 35  
**Lane**: legal-distance  
**Evidence Tier**: ACCEPTED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Continue Recommended**: false  

---

## Operational Resume

**Resumed from persisted producer snapshot**: Run 38008189963  
**Current verification run**: 38023487726  

---

## Test Results Summary

| Test Suite | Tests | Status |
|------------|-------|--------|
| `test_complementary_role_v34.py` | 8/8 | ✅ ALL PASSED |
| `test_v29_final_results.py` | 15/15 | ✅ ALL PASSED |
| **Total** | **23/23** | ✅ **ALL PASSED** |

---

## Scale Characterization Reproduction

**Experiment**: `characterize_dense_complementary_views.py` on 12,570 ACCEPTED dense embeddings (2000-2002)

### Reproduced Scale-Dependent Patterns

| Metric | Small Scale (1K) | Full Scale (12.6K) | Pattern |
|--------|------------------|---------------------|---------|
| Cross-lingual `cross_lang_same_branch` | 0.6562 | 0.9565 | **Inflation** with scale |
| Legal Area Purity | 0.6089 | 0.4754 | **Degradation** with scale |
| Branch k-NN @1 | 0.9568 | 0.9922 | **Stable >0.99** at all scales |
| Linear Hybrid Jurist Proxy | >0.99 (all weights) | >0.99 (all weights) | **PASS** at all weights |

**Result**: IDENTICAL patterns to prior verification runs — characterization is REPRODUCED and STABLE.

---

## 174k TF-IDF Evaluation Suite Verification

| Mode | Citation Heritage AUC | LangDom | Adversarial Status |
|------|----------------------|---------|-------------------|
| `cited_decisions_tfidf` | 0.973 | 0.602 | ✅ PASS |
| `cited_outcome_hybrid_0.5` | 0.919 | 0.578 | ✅ PASS |

**Status**: PRIMARY product modes OPERATIONAL at full 173,963 decisions.

---

## PIVOT_WITHIN_MISSION — Question Answered

**Original Question** (Factory Direction v34):  
*What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?*

**Answer** (ACCEPTED Evidence):

### 1. Citation Heritage View — READY at 137k (21yr)
- **Minimal scale**: 137k decisions (2000-2020), ≥100 positive citation pairs
- **Best mode**: `center_projected_64dim`
- **Performance**: AUC 0.77-0.85 (RAW 0.8455, CP64 0.8182 at 21yr; CP768 0.770, CP64 0.767 at 24yr)
- **vs TF-IDF**: Dense SUPERIOR (TF-IDF citation baseline AUC 0.71-0.74)
- **Product integration**: `citation_heritage` view, v1.1+

### 2. Section Cross-Lingual View — SAMPLE ONLY (1K), BLOCKED at 174k
- **Minimal scale**: 1K sample with section extraction
- **Hierarchy**: Sachverhalt > Dispositiv > Erwaegungen
- **Sachverhalt** (facts): `cross_lang_same_branch=0.282` ✅ > 0.2 threshold
- **Dispositiv** (holding): `cross_lang_same_branch=0.150` ✅ > 0.1 threshold  
- **Erwaegungen** (reasoning): `cross_lang_same_branch=0.094` ❌ < 0.1 threshold
- **Blocker**: Full corpus section extraction at 174k not available
- **Product integration**: `cross_lingual` view, BLOCKED v1.1+

### 3. Linear Hybrid Complement — READY at 122k (19yr), EXPLORATORY
- **Minimal scale**: 122k decisions (2000-2018) — first scale PASS both adversarial gates
- **Optimal weights** (22yr/144k): w=0.4 for `cited_decisions_tfidf`, w=0.3 for `outcome_hybrid_0.5`
- **Performance**: JP 0.61-0.67, LangDom 0.64-0.75 — PASS adversarial gates
- **vs TF-IDF**: BELOW baseline (TF-IDF JP 0.78-0.79)
- **Cross-lingual**: Improves over TF-IDF (0.160 vs 0.124) but < 0.2 useful threshold
- **Product integration**: `hybrid_complement` view, EXPLORATORY v1.1+

---

## Two-Mode Tradeoff — FUNDAMENTAL (Reproduced at All Scales)

| Representation | Jurist Pref | LangDom | CiteIndep | Characteristic |
|----------------|-------------|---------|-----------|----------------|
| TF-IDF Citation Hybrids | **0.78** | 0.48 | 0.14 | Legal relevance, monolingual |
| Dense Semantic (CP) | 0.05-0.43 | **0.83-0.98** | **0.37** | Cross-lingual, language-dominated |
| Linear Hybrids (optimal) | 0.61-0.67 | 0.58-0.80 | 0.20-0.30 | Intermediate, best of both |

**Conclusion**: NO single representation dominates all three metrics at any scale. Fundamental tradeoff between legal relevance (TF-IDF) and cross-lingual reach (dense).

---

## True OOS JuristPref Ceiling

- **Ceiling**: ~0.53 (v8 holdout validation, train-only TF-IDF/SVD on 80%)
- **Factory Target**: 0.7
- **Achievable**: ❌ NO
- **Implication**: Dense embeddings CANNOT be PRIMARY for jurist navigation

---

## Data Blockers (Require Corpus Lane Resumption)

1. **bge_ ↔ bger_ ID mapping**: Canonical corpus uses bge_ IDs, evaluation uses bger_ IDs — no mapping exists
2. **Parquet 2024-2026**: ~15.5k decisions missing (no parquet, no embeddings)
3. **Section extraction 174k**: Sachverhalt/Erwaegungen/Dispositiv not extracted at 174k scale

**Note**: 2021-2023 embeddings EXIST and PASS citation heritage quality checks (AUC > 0.75 at 24yr/158k with 730 positive pairs). Only 2024-2026 are genuinely missing.

---

## Orchestration/Validation Failure Diagnosis

**Factory Direction v35 inconsistency**:  
- `factory_direction.json` shows `legal-distance: { "status": "RUN" }`
- Lane state correctly shows `cycle_status: "BLOCKED_ON_DEPENDENCIES"` with `continue_recommended: false`

**Root Cause**: PIVOT_WITHIN_MISSION characterization COMPLETE at v34 (run 37677999602). The lane has answered its question and is correctly blocked on data dependencies. The factory direction status was not updated to reflect the lane's actual state.

**Scientific Integrity**: UNAFFECTED — all evidence ACCEPTED, all tests PASS, no claim-bearing results weakened or overwritten.

---

## Evidence References

All evidence files referenced in `state/legal-distance.json` `evidence_refs` are present and validated:
- 174k dense embedding checkpoints and evaluations
- Citation heritage evaluations (21yr, 22yr, 24yr)
- Section cross-lingual evaluation (1K sample)
- Linear combination weight sweeps (19yr, 22yr)
- TF-IDF 174k formal evaluation suite (evaluation lane v25)
- v8 holdout OOS validation
- v17b label normalization, v18 coarse hierarchy results

---

## Recommendation

**No further same-question cycles justified.**

**Next Actions**:
1. **Corpus lane**: Resume for bge_↔bger_ mapping, 2024-2026 parquet generation, 174k section extraction
2. **Product lane**: Ship v1.0 with TF-IDF citation hybrids as primary (JP 0.78 vs 0.43 semantic baseline)
3. **Dense integration**: v1.1+ for citation-heritage view and cross-lingual view (contracts defined in complementary_role_characterization_v34.json)
4. **Frontier portfolio**: v7 CONFIRMED — both teams TERMINATED; no ACCEPTED evidence opens credible independent path

---

## Audit Readiness

✅ **SNAPSHOT AUDIT-READY** for run 38023487726

- All tests pass (23/23)
- Scale characterization reproduced
- 174k TF-IDF primary modes validated
- PIVOT_WITHIN_MISSION question fully answered
- All evidence preserved with provenance
- Negative results preserved (Erwaegungen cross-lingual FAIL, True OOS ceiling 0.53, TF-IDF dominance)
- Orchestration failure diagnosed and documented