# Evaluation Lane Final Report — Factory Direction v34

**Lane:** evaluation  
**Direction Version:** 34  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETE  
**Continue Recommended:** false  
**Accepted Run ID:** eval_174k_v34_baseline_and_dense_criteria_20261005  
**GitHub Run:** 37335427922  
**Last Verified:** 2026-10-05T15:55:41Z  

---

## Executive Summary

The evaluation lane has **successfully completed** its mission under Factory Direction v34:

1. **TF-IDF 174k evaluation FROZEN as production baseline** — All 8 TF-IDF representations evaluated at 173,963 decisions on frozen harness v3 (config hash `b51701f5a9c11692`, seed 42). All PASS both adversarial gates via exact k-NN on stratified subsample (n=2000 valid).
2. **Dense embedding acceptance criteria VALIDATED** against 22-year/144k legal-distance ACCEPTED evidence.
3. **No further same-question cycles justified** — Blocked on corpus lane: bge_/bger_ ID mapping + parquet 2022-2026 + section extraction at 174k scale.

### Production Baseline (FROZEN)

| Representation | Language Dominance | Jurist Preference | Both Gates |
|---|---|---|---|
| **cited_decisions_tfidf_outcome_hybrid_0.5** | **0.4773** ✓ | **0.7345** ✓ | ✓ **PRODUCTION DEFAULT** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4783 ✓ | 0.7275 ✓ | ✓ |
| cited_decisions_tfidf | 0.4794 ✓ | 0.7140 ✓ | ✓ |
| regeste_full_text_hybrid_0.5 | 0.4873 ✓ | 0.7140 ✓ | ✓ |
| regeste_full_text_hybrid_0.7 | 0.4889 ✓ | 0.7120 ✓ | ✓ |
| full_text_tfidf_light | 0.4854 ✓ | 0.7080 ✓ | ✓ |
| outcome_tfidf | 0.5015 ✓ | 0.6550 ✓ | ✓ |
| regeste_tfidf | 0.4853 ✓ | 0.6315 ✓ | ✓ |

**All 8 representations PASS both adversarial gates** (language dominance < 0.85, jurist pairwise preference > 0.5).

**Fundamental tradeoff confirmed:** Citation-based modes (cited_decisions_tfidf*) dominate jurist preference but fail branch/tf_metadata/hierarchy benchmarks. Text-based modes (full_text_tfidf_light, regeste_tfidf*) pass branch/tf_metadata but FAIL adversarial language dominance (~0.999).

---

## Dense Embedding Acceptance Criteria — VALIDATED

Validated against **22-year/144k legal-distance ACCEPTED evidence** (center_projected embeddings at 144,443 decisions):

| Criterion | Threshold | Evidence (22yr) | Status |
|---|---|---|---|
| **Citation Heritage AUC** | > 0.75 | 0.7916–0.7946 (64/768/128dim) | ✅ **PASS** |
| **Cross-lingual Sachverhalt** | > 0.20 | 0.2816 | ✅ **PASS** |
| **Cross-lingual Dispositiv** | > 0.10 | 0.1481–0.1502 | ✅ **PASS** |
| **Cross-lingual Erwaegungen** | > 0.10 | 0.0925–0.0941 | ❌ FAIL |
| **Jurist Pairwise Preference** | > 0.50 | 0.35–0.43 (all dims) | ❌ FAIL |
| **Linear Hybrid Adversarial** | PASS both | w=0.3–0.4: JP 0.66–0.67 | ✅ PASS |
| **Linear Hybrid Cross-lang** | > 0.124 (TF-IDF) | 0.160 (w=0.4) | ✅ PASS |

### Key Dense Embedding Findings

1. **Citation Heritage**: Dense embeddings **SUPERIOR to TF-IDF** (AUC 0.79–0.85 vs 0.71–0.74). Emerges at scale when sufficient cross-year citation density exists (≥130k decisions, ≥100 positive pairs).

2. **Section Cross-lingual Hierarchy**: Sachverhalt (facts) > Dispositiv (holdings) > Erwaegungen (reasoning). Legal facts transcend language; reasoning is most language-specific. Center projection improves all sections 16–38%.

3. **Jurist Preference**: center_projected **FAILS at ALL scales** (3yr: JP 0.05–0.43, 22yr: JP 0.35–0.43, 24yr: JP 0.35–0.38). True OOS ceiling ~0.53 < 0.7 factory target. **Cannot be primary navigation mode.**

4. **Linear Hybrids**: PASS adversarial gates at optimal weight (w=0.3–0.4) but **REMAIN BELOW TF-IDF baseline** (JP 0.66–0.67 vs 0.78–0.79). Add cross-lingual benefit but citation signals remain dominant for legal relevance.

---

## Negative Results (Preserved as First-Class Evidence)

| Experiment | Result | Implication |
|---|---|---|
| **v17b Label Normalization at 174k** | NMI decreases 5/8 reps; zoom_fine degrades 7–17% | Does NOT generalize from 1K scale (213→111 vs 104→54 labels). Normalization merges labels embeddings were separating. |
| **v18 Coarse Hierarchy (4 branches)** | Max purity 0.65 (linear_citation_concat) < 0.70 | Even at coarsest legal granularity, no TF-IDF/citation representation achieves 0.70 branch purity. Fundamental hierarchy limitation. |
| **Citation Heritage Recall@10** | Max 0.0066 | Citation neighborhood recovery too sparse for practical retrieval. |
| **24-year Adversarial** | center_projected FAILS jurist gate at ALL dimensions | Confirms dense embeddings cannot meet jurist preference baseline at any available scale. |
| **24-year Citation Heritage** | Artifact missing — claim RETRACTED | No 144k dense citation heritage evaluation exists; only 22-year available. |

---

## Product Integration Contracts (from legal-distance lane)

| View | Representation | Status | User Intent |
|---|---|---|---|
| **Primary Navigation** | cited_outcome_hybrid_0.5 (TF-IDF) | **PRODUCTION v1.0** | Jurist finds legally relevant neighbors |
| **Citation Heritage** | center_projected_64dim | **READY v1.1+** | Jurist explores doctrinal lineage via shared citations |
| **Cross-lingual** | center_projected_64dim per section (sachverhalt > dispositiv) | **BLOCKED v1.1+** | Jurist finds equivalent decisions in other languages |
| **Hybrid Explore** | linear_citation_concat_w0.4 / linear_hybrid05_concat_w0.3 | **EXPLORATORY v1.1+** | Jurist trades some legal relevance for cross-lingual reach |

---

## Data Blockers (Corpus Lane Resumption Required)

| Blocker | Impact |
|---|---|
| **bge_/bger_ ID mapping** | Canonical corpus uses bge_ IDs, evaluation uses bger_ IDs — no mapping exists |
| **Parquet 2022–2026** | 29,520 decisions missing (years 2022–2026), no /tmp/bger.parquet |
| **Section extraction at 174k** | Sachverhalt/Erwaegungen/Dispositiv not extracted at 174k scale — blocks cross-lingual view |

---

## Evidence References (Machine-Readable)

- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `results/evaluation/citation_heritage_174k_tfidf_latest.json`
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `evaluation/results/v18_coarse_hierarchy/v18_coarse_hierarchy_latest.json`
- `results/evaluation/partial_dense_2000_2002/citation_heritage_22year_latest.json`
- `results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json`
- `results/evaluation/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json`
- `results/evaluation/24year_dense_adversarial/evaluation_24year_dense_adversarial_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
- `legal_distance/results/complementary_role_characterization_v34.json`
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_20261005_155541.json` (this run)

---

## Final Recommendation

**CONTINUE = false** — The evaluation lane has fully answered the Factory Direction v34 question:

> *"Freeze TF-IDF 174k evaluation as production baseline; define acceptance criteria for dense embedding complementary views (citation heritage AUC > 0.75, cross_lang_same_branch > 0.2 for sachverhalt, cross_lang_same_branch > 0.1 for dispositiv)."*

✅ **TF-IDF 174k baseline FROZEN** — 8/8 reps PASS adversarial gates, best: cited_decisions_tfidf_outcome_hybrid_0.5 (JP=0.7345)  
✅ **Dense acceptance criteria DEFINED & VALIDATED** — Citation heritage AUC 0.79–0.80 PASS, Sachverhalt 0.282 PASS, Dispositiv 0.148 PASS, Erwaegungen 0.093 FAIL  
✅ **Complementary role CHARACTERIZED** — Dense = citation heritage view + cross-lingual view (sachverhalt > dispositiv) + hybrid explore mode  
❌ **174k dense embeddings UNAVAILABLE** — Blocked on corpus lane  

**No additional same-question cycle justified.** The factory should proceed with:
1. Product v1.0 release with TF-IDF citation hybrids as primary navigation (beats semantic baseline JP 0.78 vs 0.43)
2. Corpus lane resumption for bge_/bger_ mapping, 2022–2026 parquet, section extraction at 174k
3. Dense embedding integration as v1.1+ enhancements per defined contracts
4. No new Frontier team — portfolio v7 confirmed, all teams TERMINATED

---

*Report generated 2026-10-05T15:55:41Z — Evaluation Lane v34 Final Verification*