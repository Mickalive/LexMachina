# Legal Distance Lane — Factory Direction v34
## Dense Embedding Complementary Role Characterization (COMPLETE)

**Status:** BLOCKED_ON_DEPENDENCIES | **Evidence Tier:** REPRODUCED | **Continue Recommended:** false

---

## Executive Summary

The PIVOT_WITHIN_MISSION executed per CYCLE_37090665528 audit has been fully characterized. Dense embeddings (multilingual-e5 center_projected) **do not beat TF-IDF citation hybrids on jurist preference at any scale** (JP 0.05–0.43 vs 0.78–0.79), but they **excel at three complementary capabilities** essential for the product's multi-view map:

| Complementary View | Acceptance Criterion | Status | Minimal Scale |
|---|---|---|---|
| **Citation Heritage Recovery** | AUC > 0.75 | ✅ PASSED | 21yr / 137k (2000–2020) |
| **Section Cross-Lingual (Sachverhalt)** | cross_lang_same_branch > 0.2 | ✅ PASSED | 1K sample (359 decisions) |
| **Section Cross-Lingual (Dispositiv)** | cross_lang_same_branch > 0.1 | ✅ PASSED | 1K sample (538 decisions) |
| **Section Cross-Lingual (Erwaegungen)** | cross_lang_same_branch > 0.1 | ❌ FAILED | — (reasoning most language-specific) |
| **Linear Hybrid Complement** | PASS both adversarial gates | ✅ PASSED | 19yr / 122k (w=0.3–0.4) |

**Product Decision:** TF-IDF citation hybrids = PRIMARY mode (jurist preference, branch clustering). Dense embeddings = COMPLEMENTARY modes (citation heritage view, cross-lingual fact/holding view, linear hybrid complement). v1.0 ships with TF-IDF; dense integration is v1.1+.

---

## Evidence Summary (All REPRODUCED)

### 1. Citation Heritage Recovery — Dense Superiority CONFIRMED

| Representation | AUC (22yr/144k) | AUC (21yr/137k) | Similarity Gap (cp64) |
|---|---|---|---|
| Dense raw (768) | **0.795** | **0.845** | 0.063 |
| Dense cp64 | **0.792** | **0.818** | **0.410** |
| Dense cp128 | **0.792** | **0.818** | 0.391 |
| TF-IDF citation-based | ~0.71–0.74 | — | — |
| TF-IDF text-based | ~0.50–0.63 | — | — |

- **Finding:** Dense embeddings recover citation heritage **better than TF-IDF citation-based** (0.79–0.85 vs 0.71–0.74) at scale where sufficient citation pairs exist (≥100 positive pairs requires 2019+ decisions).
- **Center projection (cp64)** preserves AUC while dramatically improving similarity gap (0.410 vs 0.063), making the view usable for navigation.
- **Minimal scale:** 21 years / 137k decisions (2000–2020). Below this, positive citation pairs too sparse.

### 2. Section Cross-Lingual Hierarchy — Sachverhalt > Dispositiv > Erwaegungen

| Section | N | cp64 cross_lang_same_branch | cp64 invariance_gap | Status |
|---|---|---|---|---|
| **Sachverhalt** (facts) | 359 | **0.282** | **0.187** | ✅ PASS (>0.2) |
| **Dispositiv** (holding) | 538 | **0.150** | **0.397** | ✅ PASS (>0.1) |
| **Erwaegungen** (reasoning) | 510 | **0.094** | **0.452** | ❌ FAIL (<0.1) |

- **Finding:** Legal facts align best cross-lingually; holdings retain some alignment; reasoning is most language-specific.
- **Center projection improves all:** Sachverhalt gap 0.304→0.187 (38% improvement), Erwaegungen 0.538→0.452, Dispositiv 0.575→0.397.
- **Full-corpus density BLOCKED** pending section extraction at 174k scale (corpus lane).

### 3. Linear Hybrid Complement — Scale-Dependent Optimal Weight

| Scale | Optimal Weight (cited_decisions_tfidf) | JP at Optimal | LangDom at Optimal | Both Gates |
|---|---|---|---|---|
| 15yr (92k) | w=0.3 | 0.473 | 0.809 | ❌ FAIL |
| 19yr (122k) | w=0.3 | **0.647** | **0.626** | ✅ PASS |
| 22yr (144k) | **w=0.4** | **0.673** | **0.654** | ✅ PASS |

| Scale | Optimal Weight (outcome_hybrid_0.5) | JP at Optimal | LangDom at Optimal | Both Gates |
|---|---|---|---|---|
| 19yr (122k) | w=0.3 | **0.637** | **0.662** | ✅ PASS |
| 22yr (144k) | **w=0.3** | **0.612** | **0.748** | ✅ PASS |

- **Finding:** Linear hybrids PASS adversarial gates at ≥19yr but **remain below TF-IDF baseline** (JP 0.61–0.67 vs 0.78–0.79).
- **Scale shifts weight toward semantic:** 19yr→22yr shifts cited_decisions_tfidf optimal from w=0.3 to w=0.4.
- **Tradeoff:** Adding semantic improves cross-lingual (0.160 vs 0.124) but dilutes legal relevance.

### 4. Fundamental Two-Mode Tradeoff — No Single Representation Dominates

| Mode | Jurist Preference | Language Dominance | Citation Independence |
|---|---|---|---|
| TF-IDF Citation Hybrids | **0.78–0.79** | **0.48** | ~14% |
| Dense (center_projected) | 0.05–0.43 | 0.83–0.98 | ~37% |
| Linear Hybrid (w=0.3–0.4) | 0.61–0.67 | 0.58–0.75 | Intermediate |

**No representation dominates all three metrics.** This necessitates multi-view product.

### 5. True OOS Jurist Preference Ceiling

- **v8 holdout zero-shot validation:** True OOS JP ceiling ~0.53 < 0.7 factory target.
- TF-IDF baseline JP=0.78 evaluated on same data used for SVD fitting (known leakage, but v8 showed minimal impact: JP −0.015 to −0.020).

### 6. TF-IDF 174k Primary Mode Validated

- **v25 174k formal suite:** 8/8 reps PASS both adversarial gates.
- Best hybrid (cited_outcome_hybrid_0.5): JP ≈ 0.735, LangDom = 0.578 PASS.
- Beats semantic baseline (center_projected JP=0.43) decisively.
- **Product default:** `cited_outcome_hybrid_0.5_174k` operational at 173,963 decisions.

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Decisions Affected |
|---|---|---|
| **BGE/bger ID mapping** | No cross-mapping between published (bge_) and unpublished (bger_) IDs; evaluation uses bger_, canonical corpus uses bge_ | All 174k |
| **Parquet 2024–2026** | Missing normalization artifacts for 3 years | ~15,536 decisions |
| **Parquet 2022–2023** | Embeddings computed (158k total) but flagged FAILED in progress.json; quality validation needed | 2022–2023 |
| **Section extraction 174k** | Sachverhalt/Erwaegungen/Dispositiv not extracted at full scale; blocks cross-lingual density validation | All 174k |

**Corpus lane status:** PAUSED. Resume ONLY for (a) BGE/bger mapping, (b) parquet 2022–2026, (c) section extraction 174k.

---

## 12k Scale Characterization (Supplementary)

Additional scale-dependence analysis on 12k ACCEPTED dense embeddings (2000–2002):

- **Cross-lingual (full-text dense):** cross_lang_same_branch 0.66–1.00 across scales (different metric from section-specific eval)
- **Legal area clustering:** Purity declines with scale (0.61 @1k → 0.48 @12k); NMI 0.74→0.60
- **Branch k-NN:** Extremely high (>0.95) at all scales (2000–2002 sample has strong branch separation)
- **Linear hybrid (concat):** JP proxy ~1.0 at all weights (different proxy than adversarial test)
- **Key insight:** 12k sample (3 years) behaves differently than full corpus — adversarial tests at 144k are gold standard.

---

## Verification

- ✅ All 8 tests in `test_complementary_role_v34.py` PASS
- ✅ All 13 evidence_refs verified
- ✅ PIVOT_WITHIN_MISSION characterization complete at max available evaluated scale (22yr/144k, 2000–2021)
- ✅ Three complementary modes validated against evaluation lane acceptance criteria
- ✅ Negative results preserved (Erwaegungen cross-lingual FAIL, dense JP FAIL at all scales, true OOS ceiling < 0.7)

---

## Recommendation

**PIVOT_WITHIN_MISSION COMPLETE.** No further same-question cycles justified.

- **Legal-distance lane:** BLOCKED_ON_DEPENDENCIES, continue_recommended=false
- **Corpus lane:** Must resume for BGE/bger mapping + parquet 2022–2026 + section extraction
- **Fractal-map / Evaluation / Product:** BLOCKED on 174k dense embeddings for multi-view deployment
- **Frontier portfolio v7 CONFIRMED:** Both teams TERMINATED (true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria; no ACCEPTED evidence opens credible independent path)

The product ships v1.0 with TF-IDF citation hybrids as primary navigation mode. Dense embedding integration for citation-heritage view and cross-lingual view is v1.1+ contingent on corpus lane unblocking.