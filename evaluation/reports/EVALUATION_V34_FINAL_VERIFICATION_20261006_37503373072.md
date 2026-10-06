# Evaluation Lane Final Verification — Factory Direction v34

**Lane:** evaluation  
**Direction Version:** 34  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETE  
**Continue Recommended:** false  
**Accepted Run ID:** EVALUATION_V34_BASELINE_FROZEN_20261006_37426211974  
**GitHub Run:** 37503373072  
**Verification Date:** 2026-10-06  

---

## Executive Summary

The evaluation lane has **successfully completed** its mission under Factory Direction v34. This verification confirms the frozen baseline remains intact and no new awaited representations have arrived.

### 1. TF-IDF 174k Production Baseline — FROZEN & RECONFIRMED

All 8 TF-IDF representations evaluated at 173,963 decisions on frozen harness v3 (config hash `b51701f5a9c11692`, seed 42). All 8 PASS both adversarial gates via exact k-NN on stratified subsample (n=2000 valid).

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

**All 8/8 representations PASS both adversarial gates** (language dominance < 0.85, jurist pairwise preference > 0.5).

**Fundamental tradeoff confirmed:** Citation-based modes dominate jurist preference but fail branch/tf_metadata/hierarchy benchmarks. Text-based modes pass branch/tf_metadata but FAIL adversarial language dominance (~0.999 on full-corpus HNSW).

### 2. Dense Embedding Acceptance Criteria — VALIDATED (No Change)

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

**Key findings unchanged:**
1. **Citation Heritage**: Dense embeddings SUPERIOR to TF-IDF (AUC 0.79–0.85 vs 0.71–0.74).
2. **Section Cross-lingual Hierarchy**: Sachverhalt > Dispositiv > Erwaegungen.
3. **Jurist Preference**: center_projected FAILS at ALL scales (3yr: JP 0.05–0.43, 22yr: JP 0.35–0.43, 24yr: JP 0.35–0.38). True OOS ceiling ~0.53 < 0.7 factory target.
4. **Linear Hybrids**: PASS adversarial gates but REMAIN BELOW TF-IDF baseline (JP 0.66–0.67 vs 0.78–0.79).

### 3. Monitor Check — No New Awaited Representations

**Monitor check #312** (2026-10-06T17:31:07Z) scanned `/tmp/lex_accepted/legal-distance/legal_distance/results` and `/tmp/lex_accepted/fractal-map/results/fractal_map`:

| Category | Representations | Status |
|---|---|---|
| **Completed TF-IDF (174k)** | 8/8 | ✅ All present, already evaluated |
| **Awaited Dense (174k)** | 8/8 | ❌ None available (only yearly checkpoints 2000-2021) |
| **Awaited Citation Roles (174k)** | 3/3 | ❌ Not computed |
| **Awaited Linear Hybrids (174k)** | 2/2 | ❌ Not computed |

**Dense embeddings progress:** 22/26 years (2000-2021) in checkpoints (144,443 decisions). Only 3/26 years (2000-2002) ACCEPTED. Center-projected concatenation of 22 years not yet performed. Years 2022-2026 not yet processed.

**Blockers unchanged:** bge_/bger_ ID mapping missing; parquet 2022-2026 missing; section extraction at 174k not computed.

### 4. Negative Results Preserved (First-Class Evidence)

| Experiment | Result | Implication |
|---|---|---|
| **v17b Label Normalization at 174k** | NMI decreases 5/8 reps; zoom_fine degrades 7–17% | Does NOT generalize from 1K scale |
| **v18 Coarse Hierarchy (4 branches)** | Max purity 0.65 < 0.70 | Fundamental hierarchy limitation |
| **Citation Heritage Recall@10** | Max 0.0066 | Too sparse for practical retrieval |
| **24-year Adversarial** | center_projected FAILS jurist gate at ALL dims | Dense cannot meet jurist preference baseline |
| **24-year Citation Heritage** | Artifact missing — claim RETRACTED | Only 22-year evaluation exists |

### 5. Product Integration Contracts (Unchanged)

| View | Representation | Status | User Intent |
|---|---|---|---|
| **Primary Navigation** | cited_outcome_hybrid_0.5 (TF-IDF) | **PRODUCTION v1.0** | Jurist finds legally relevant neighbors |
| **Citation Heritage** | center_projected_64dim | **READY v1.1+** | Jurist explores doctrinal lineage |
| **Cross-lingual** | center_projected_64dim per section | **BLOCKED v1.1+** | Jurist finds equivalent decisions in other languages |
| **Hybrid Explore** | linear_citation_concat_w0.4 / linear_hybrid05_concat_w0.3 | **EXPLORATORY v1.1+** | Jurist trades relevance for cross-lingual reach |

### 6. Evidence References

**TF-IDF 174k Baseline:**
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` (config hash b51701f5a9c11692)
- `evaluation/results/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json`
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json`

**Dense Embedding Evidence (22-year/144k):**
- `legal_distance/results/174k_dense_embeddings/evaluation_22year_center_projected/combined_results.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`

**Negative Results:**
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `evaluation/results/v18_coarse_hierarchy/v18_coarse_hierarchy_latest.json`
- `evaluation/results/24year_dense_adversarial/evaluation_24year_dense_adversarial_latest.json`

---

## Final Recommendation

**CONTINUE_RECOMMENDED: false** — No additional same-question cycles justified.

The evaluation lane has fully answered the Factory Direction v34 question:

> *"Freeze TF-IDF 174k evaluation as production baseline; define acceptance criteria for dense embedding complementary views (citation heritage AUC > 0.75, cross_lang_same_branch > 0.2 for sachverhalt, cross_lang_same_branch > 0.1 for dispositiv)."*

✅ **TF-IDF 174k baseline FROZEN** — 8/8 reps PASS adversarial gates, best: cited_decisions_tfidf_outcome_hybrid_0.5 (JP=0.7345)  
✅ **Dense acceptance criteria DEFINED & VALIDATED** — Citation heritage AUC 0.79–0.80 PASS, Sachverhalt 0.282 PASS, Dispositiv 0.148 PASS, Erwaegungen 0.093 FAIL  
✅ **Complementary role CHARACTERIZED** — Dense = citation heritage view + cross-lingual view (sachverhalt > dispositiv) + hybrid explore mode  
❌ **174k dense embeddings UNAVAILABLE** — Blocked on corpus lane  

**Next actions required from other lanes:**
1. **Product lane:** Ship v1.0 with TF-IDF citation hybrids as primary navigation (beats semantic baseline JP 0.78 vs 0.43)
2. **Corpus lane:** Resume for bge_/bger_ ID mapping, parquet 2022–2026, section extraction at 174k
3. **Legal-distance lane:** Deliver 174k dense embeddings when data blockers resolve
4. **No new Frontier team** — portfolio v7 confirmed, all teams TERMINATED (true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria)

---

*Report generated 2026-10-06T17:35:00Z — Evaluation Lane v34 Final Verification (GitHub run 37503373072)*
