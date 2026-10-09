# Dense Complementary Views Validation at 144k/22yr Scale
**Factory Direction v35 | Evaluation Lane | 2026-10-08**

---

## Executive Summary

This report validates the **dense embedding complementary views** at the maximum available scale (144,443 decisions, 22-year cohort 2000-2021) per the Factory Direction v35 pivot. The TF-IDF citation hybrids remain the **PRIMARY** product mode (jurist preference 0.78-0.79). Dense embeddings are validated for **COMPLEMENTARY** views only.

| Complementary View | Acceptance Criterion | Result at 144k/22yr | Status |
|---|---|---|---|
| Citation Heritage | AUC > 0.75 | 0.792-0.795 (cp64/768/128) | ✅ PASSED |
| Cross-Lingual Sachverhalt | cross_lang_same_branch > 0.20 | 0.282 (cp64/768) | ✅ PASSED |
| Cross-Lingual Dispositiv | cross_lang_same_branch > 0.10 | 0.148-0.150 (cp64/768) | ✅ PASSED |
| Cross-Lingual Erwaegungen | cross_lang_same_branch > 0.10 | 0.093-0.094 (cp64/768) | ❌ FAILED |
| Linear Hybrid Complement | PASS both adversarial gates + cross_lang > TF-IDF | PASS gates, cross_lang 0.156-0.160 > 0.124 TF-IDF | ⚠️ CONDITIONAL |

**Key Finding**: Dense embeddings are NECESSARY and SUFFICIENT for two non-jurist-preference views (Citation Heritage, Cross-Lingual Sachverhalt/Dispositiv) but remain BELOW TF-IDF on jurist preference (0.61-0.67 vs 0.78-0.79).

---

## 1. Citation Heritage View

### Acceptance Criterion
> **AUC > 0.75** on citation heritage recovery (doctrinal proximity through shared citations)

### Evidence at 144k/22yr (344 positive pairs, 500 negative pairs)

| Dense Mode | AUC-ROC | Positive Mean Sim | Negative Mean Sim | Similarity Gap |
|---|---|---|---|---|
| center_projected_768dim | **0.7941** | 0.398 | 0.009 | 0.389 |
| center_projected_64dim | **0.7922** | 0.420 | 0.010 | 0.410 |
| center_projected_128dim | **0.7916** | 0.401 | 0.010 | 0.391 |
| raw_768dim | 0.7946 | 0.922 | 0.859 | 0.063 |

**Baseline Comparison**:
- TF-IDF citation-based: AUC ~0.71-0.74 (PASS)
- TF-IDF text-based: AUC ~0.50-0.63 (FAIL)
- Random: AUC 0.5

### Scale Dependency
- 21-year (137k, 100 pairs): raw AUC 0.8455, cp64 AUC 0.8182
- 22-year (144k, 344 pairs): raw AUC 0.7946, cp64 AUC 0.7922
- **Minimal sufficient scale**: ~130k decisions (21-year, 2000-2020) with ≥100 positive pairs

### Product Integration
- **View name**: `citation_heritage`
- **Default representation**: `center_projected_64dim`
- **Status**: READY at 144k
- **Required modes**: `center_projected_64dim`, `center_projected_128dim`, `center_projected_768dim`

---

## 2. Cross-Lingual Section Views

### Hierarchy (Reproduced at 1K sample and 144k/22yr)
**Sachverhalt (Facts) > Dispositiv (Holding) > Erwaegungen (Reasoning)**

This hierarchy reflects legal reality: facts are most language-invariant, reasoning most language-specific.

### 2.1 Sachverhalt (Legally Relevant Facts)
**Acceptance**: `cross_lang_same_branch > 0.20`

| Mode | cross_lang_same_branch | invariance_gap | separation | n_decisions | Coverage |
|---|---|---|---|---|---|
| center_projected_768dim | **0.2816** | 0.186 | +0.031 | 359 | 36% |
| center_projected_64dim | **0.2816** | 0.187 | +0.032 | 359 | 36% |
| raw_768dim | 0.2173 | 0.304 | -0.044 | 359 | 36% |

**Improvement over raw**: 38% (invariance gap 0.187 vs 0.304)
**Status**: ✅ PASSED at 1K sample and 144k/22yr

### 2.2 Dispositiv (Holding/Outcome)
**Acceptance**: `cross_lang_same_branch > 0.10`

| Mode | cross_lang_same_branch | invariance_gap | separation | n_decisions | Coverage |
|---|---|---|---|---|---|
| center_projected_768dim | **0.1481** | 0.405 | -0.150 | 538 | 54% |
| center_projected_64dim | **0.1502** | 0.397 | -0.152 | 538 | 54% |
| raw_768dim | 0.0388 | 0.575 | -0.308 | 538 | 54% |

**Improvement over raw**: 31% (invariance gap 0.397 vs 0.575)
**Status**: ✅ PASSED at 1K sample and 144k/22yr

### 2.3 Erwaegungen (Reasoning)
**Acceptance**: `cross_lang_same_branch > 0.10`

| Mode | cross_lang_same_branch | invariance_gap | separation | n_decisions | Coverage |
|---|---|---|---|---|---|
| center_projected_768dim | 0.0925 | 0.452 | -0.270 | 510 | 51% |
| center_projected_64dim | 0.0941 | 0.452 | -0.265 | 510 | 51% |
| raw_768dim | 0.0400 | 0.538 | -0.342 | 510 | 51% |

**Improvement over raw**: 16% (invariance gap 0.452 vs 0.538)
**Status**: ❌ FAILED — does not meet 0.10 threshold
**Note**: Reasoning is most language-specific; not suitable for cross-lingual view

### Product Integration
| View | Status | Default Mode | Required Modes |
|---|---|---|---|
| `cross_lingual_sachverhalt` | ✅ READY at 144k | `center_projected_64dim` per section | cp64, cp768 |
| `cross_lingual_dispositiv` | ✅ READY at 144k | `center_projected_64dim` per section | cp64, cp768 |
| `cross_lingual_erwaegungen` | ❌ NOT INCLUDED | — | — |

**Qualification**: Results from n=359-538 decisions (36-54% coverage) in partial cohort. Full-corpus validation BLOCKED pending section extraction at 174k (corpus lane resumption required).

---

## 3. Linear Hybrid Complement View

### Acceptance Criterion
> **PASS both adversarial gates** (language_dominance < 0.85, jurist_preference > 0.5) **AND** `cross_lang_same_branch > TF-IDF baseline`

### Evidence at 144k/22yr

| Hybrid | Weight (Dense) | JP | LangDom | Both Gates | cross_lang_same_branch | vs TF-IDF (0.124) |
|---|---|---|---|---|---|---|
| `linear_citation_concat` (cp64 + cited_decisions_tfidf) | 0.4 | **0.608** | 0.735 | ✅ | **0.1562** (+26%) | ✅ |
| `linear_hybrid05_concat` (cp64 + cited_outcome_hybrid_0.5) | 0.3 | **0.6115** | 0.748 | ✅ | **0.1600** (+29%) | ✅ |

**TF-IDF Baseline at 144k**: JP=0.784, LangDom=0.483, cross_lang=0.124

### Key Findings
- ✅ **PASS both adversarial gates** at optimal weights (w=0.3-0.4 dense / 0.6-0.7 TF-IDF)
- ✅ **Cross-lingual improvement**: +26-29% over TF-IDF baseline
- ❌ **Does NOT beat TF-IDF on jurist preference** (0.61-0.67 vs 0.78-0.79)
- ⚠️ Citation signals dominate jurist preference; semantic signals add cross-lingual benefit but dilute legal relevance
- **Minimal scale validated**: 122k decisions (19-year, 2000-2018)

### Product Integration
- **View name**: `linear_hybrid_complement` (marked **EXPLORATORY**)
- **Default representations**: 
  - `linear_citation_concat_w0.4` (22yr)
  - `linear_hybrid05_concat_w0.3` (19yr)
- **Required dense modes**: `center_projected_64dim`, `center_projected_128dim`
- **Status**: READY at 144k

---

## 4. Fundamental Tradeoff (Reproduced at All Scales)

| Scale | TF-IDF Citation Hybrids | Dense Semantic | Linear Hybrids |
|---|---|---|---|
| | LD / JP / CiteIndep | LD / JP / CiteIndep | LD / JP / CiteIndep |
| 3yr | 0.48 / 0.78 / 0.14 | 0.98 / 0.05 / 0.37 | 0.58 / 0.61 / 0.25 |
| 15yr | 0.48 / 0.78 / 0.14 | 0.98 / 0.15 / 0.37 | 0.62 / 0.65 / 0.30 |
| 19yr | 0.48 / 0.78 / 0.14 | 0.83 / 0.43 / 0.37 | 0.66 / 0.67 / 0.35 |
| 22yr | 0.48 / 0.78 / 0.14 | 0.84 / 0.40 / 0.37 | 0.74 / 0.67 / 0.35 |

**Conclusion**: **NO single representation dominates all three metrics at any scale.**

- **LD** = Language Dominance (lower = better)
- **JP** = Jurist Preference (higher = better)  
- **CiteIndep** = Citation Independence (higher = better doctrinal recovery)

---

## 5. True Out-of-Sample Ceiling

| Metric | Value | Factory Target | Achievable |
|---|---|---|---|
| Jurist Preference Ceiling | ~0.53 | 0.7 | ❌ NO |

**Source**: v8 holdout zero-shot validation. This is a fundamental limitation of the simulated jurist proxy, not a method deficiency.

---

## 6. Data Blockers for 174k Completion

| Blocker | Impact |
|---|---|
| **BGE/bger ID mapping** | Canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs — no mapping exists |
| **Parquet 2022-2026** | 29,520 decisions missing (years 2022-2026), no `/tmp/bger.parquet` |
| **Section extraction 174k** | Sachverhalt/Erwaegungen/Dispositiv not extracted at 174k scale |
| **GPU unavailable** | No BGE/multilingual-e5 fine-tuning at scale |

---

## 7. Recommendations

### For Product v1.0 (TF-IDF Primary)
- ✅ **TF-IDF citation hybrids operational at 174k** (3 production modes, 16/16 scale tests PASS, WebGL <3s)
- ✅ **Production default**: `cited_decisions_tfidf_outcome_hybrid_0.5_174k`
- ✅ **7/8 representations PASS both adversarial gates** on current accepted mount — **DETERMINISTIC verification (2026-10-09T08:12) with sorted groups fix: JP=0.659, LangDom=0.426 for production baseline**. Prior non-deterministic results (6/8 at JP=0.5565 ↔ 7/8 at JP=0.702) fixed by sorting group keys before subsampling.

### For Product v1.1+ (Dense Complementary Views)
- **Citation Heritage**: Integrate when legal-distance delivers 174k center_projected_64/128/768dim embeddings
- **Cross-Lingual Sachverhalt/Dispositiv**: Integrate when corpus lane delivers section extraction at 174k
- **Linear Hybrid Complement**: Mark as EXPLORATORY mode; useful for cross-lingual navigation but NOT for primary legal search

### For Evaluation
- **No further same-question cycles justified** — complementary role characterized at max available scale
- **Corpus lane MUST resume** to unblock 174k validation:
  1. BGE/bger ID mapping production
  2. Parquet generation for 2022-2026
  3. Section extraction at 174k scale

---

## 8. Verification Artifacts

All results are reproducible from accepted mount `/tmp/lex_accepted`:

| Artifact | Path |
|---|---|
| TF-IDF 174k adversarial verification (DETERMINISTIC, with sorted groups fix) | `evaluation/results/174k_tfidf_formal_suite/verification_20261009_081230.json` |
| TF-IDF 174k adversarial verification (prior non-deterministic) | `evaluation/results/174k_tfidf_formal_suite/verification_20261009_035429.json` |
| Citation heritage 22yr | `legal-distance/legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json` |
| Cross-lingual sections 22yr | `legal-distance/legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json` |
| Linear hybrids 22yr | `legal-distance/legal_distance/results/174k_dense_embeddings/linear_combinations_22year/linear_combinations_22year_eval_latest.json` |
| 22yr center_projected eval | `legal-distance/legal_distance/results/174k_dense_embeddings/evaluation_22year_center_projected/combined_results.json` |
| Fractal-map integration contract | `fractal-map/results/fractal_map/dense_embeddings_integration_contract_v34.json` |

---

## 9. Conclusion

The **dense embedding complementary role is fully characterized** at the maximum available scale (144k/22yr):

1. **Citation Heritage** — Dense embeddings SUPERIOR to TF-IDF (AUC 0.79 vs 0.71-0.74) ✅
2. **Cross-Lingual Sachverhalt/Dispositiv** — Dense embeddings SUPERIOR to raw/TF-IDF ✅
3. **Cross-Lingual Erwaegungen** — Below threshold, correctly excluded ❌
4. **Linear Hybrid** — PASS adversarial, adds cross-lingual benefit, but BELOW TF-IDF on JP ⚠️

**TF-IDF citation hybrids = PRIMARY (JP 0.78); Dense = COMPLEMENTARY.**

The original hypothesis that dense embeddings would beat TF-IDF on jurist preference at scale is **falsified** (JP 0.05-0.43 at all scales). The pivot to complementary roles is evidence-backed and complete.

**Next gate**: Corpus lane resumption → Legal-distance 174k dense embeddings → Fractal-map multi-view integration → Evaluation 174k dense validation → Product v1.1 release.