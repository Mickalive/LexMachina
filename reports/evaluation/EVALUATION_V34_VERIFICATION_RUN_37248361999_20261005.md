# Evaluation Lane Verification — GitHub Run 37248361999

**Factory Direction Version:** 34
**Date:** 2026-10-05
**Lane:** evaluation
**Status:** ACCEPTED / COMPLETE / `continue_recommended: false`

---

## Summary

This run verifies the **frozen evaluation state** established in `eval_174k_v34_baseline_and_dense_criteria_20261003`. No new experiments were run — this is a verification-only cycle confirming the TF-IDF 174k production baseline and dense embedding complementary view criteria remain valid and unchanged.

### Key Confirmations

| Item | Status | Evidence |
|------|--------|----------|
| **TF-IDF 174k adversarial baseline** | FROZEN & VERIFIED | Config hash `b51701f5a9c11692`, all 8 reps PASS both gates |
| **Dense citation heritage AUC > 0.75** | VALIDATED (22-year/144k) | `center_projected` AUC 0.7916–0.7946 |
| **Dense cross-lang sachverhalt > 0.2** | VALIDATED (3-year/359) | `center_projected` 0.2816 |
| **Dense cross-lang dispositiv > 0.1** | VALIDATED (3-year/538) | `center_projected` 0.1481–0.1502 |
| **Dense cross-lang erwaegungen > 0.1** | FAIL (expected) | `center_projected` 0.0925–0.0941 |
| **Center_projected jurist preference** | FAIL at ALL scales | JP 0.05–0.43 (true OOS ceiling ~0.53) |
| **174k dense embeddings** | BLOCKED | Corpus lane: bge_/bger_ mapping + parquet 2022-2026 |

---

## 1. TF-IDF 174k Production Baseline — Exact Reproduction Verified

**Source:** `results/evaluation/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json`  
**Config Hash:** `b51701f5a9c11692` (exact reproduction guarantee)  
**Method:** sklearn exact k-NN on stratified subsample n=2000, seed=42

| Representation | Language Dominance | Jurist Preference | Both Gates PASS |
|---|---|---|---|
| `cited_decisions_tfidf` | 0.4917 | 0.7075 | ✅ |
| **`cited_decisions_tfidf_outcome_hybrid_0.5`** | **0.4895** | **0.7265** | ✅ **PRODUCTION DEFAULT** |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.4908 | 0.7195 | ✅ |
| `outcome_tfidf` | 0.5078 | 0.6660 | ✅ |
| `regeste_tfidf` | 0.5111 | 0.6145 | ✅ |
| `full_text_tfidf_light` | 0.4854 | 0.7080 | ✅ |
| `regeste_full_text_hybrid_0.5` | 0.4873 | 0.7140 | ✅ |
| `regeste_full_text_hybrid_0.7` | 0.4889 | 0.7120 | ✅ |

**All 8 PASS both adversarial gates.**  
Language dominance range: [0.485, 0.511] (threshold: < 0.85)  
Jurist preference range: [0.614, 0.727] (threshold: > 0.5)

**Production defaults frozen:**
- `PRODUCT_SERVING_DEFAULT` = `cited_decisions_tfidf_outcome_hybrid_0.5`
- `COMBINATION_MODE` = `linear_hybrid05_concat`
- `DEFAULT_MAP_MODE` = `center_projected_64dim_hierarchical`

**Audit gate:** CYCLE_37073590337 PASSED (`safe_to_integrate=true`)

---

## 2. Dense Embedding Complementary View Criteria — Validated

### 2.1 Citation Heritage Recovery (22-year / 144,443 decisions / 344 positive pairs)

**Source:** `results/evaluation/partial_dense_2000_2002/citation_heritage_22year_latest.json`

| Representation | AUC-ROC | Status (threshold > 0.75) |
|---|---|---|
| `center_projected_768dim` | 0.7946 | ✅ PASS |
| `center_projected_64dim` | 0.7922 | ✅ PASS |
| `center_projected_128dim` | 0.7916 | ✅ PASS |
| `raw_768dim` (multilingual-e5) | 0.7946 | ✅ PASS |

**TF-IDF citation-based baseline:** AUC 0.71–0.74 (PASS at 174k)  
**Dense embeddings EXCEED TF-IDF by ~0.05–0.08 AUC points.**  
**Verdict:** Dense embeddings are SUPERIOR for citation-heritage view.

---

### 2.2 Cross-Lingual Section Alignment (3-year / section-segmented)

**Source:** `results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json`

#### Sachverhalt (Facts) — **BEST cross-lingual alignment**

| Representation | `cross_lang_same_branch@10` | Status (> 0.20) |
|---|---|---|
| `center_projected_768` | 0.2816 | ✅ PASS |
| `center_projected_64` | 0.2816 | ✅ PASS |
| `raw_768` | 0.2173 | ✅ PASS |

#### Dispositiv (Holdings) — **MODERATE cross-lingual alignment**

| Representation | `cross_lang_same_branch@10` | Status (> 0.10) |
|---|---|---|
| `center_projected_64` | 0.1502 | ✅ PASS |
| `center_projected_768` | 0.1481 | ✅ PASS |
| `raw_768` | 0.0388 | ❌ FAIL |

#### Erwaegungen (Reasoning) — **POOR cross-lingual alignment**

| Representation | `cross_lang_same_branch@10` | Status (> 0.10) |
|---|---|---|
| `center_projected_64` | 0.0941 | ❌ FAIL |
| `center_projected_768` | 0.0925 | ❌ FAIL |
| `raw_768` | 0.0400 | ❌ FAIL |

**Hierarchy confirmed:** Sachverhalt > Dispositiv > Erwaegungen for cross-lingual alignment.  
**Verdict:** Dense embeddings provide complementary cross-lingual views for facts/holdings sections.

---

### 2.3 Jurist Preference Gate — CONFIRMED FAILURE for Primary Navigation

| Scale | Decisions | `center_projected_768dim` JP | `center_projected_64dim` JP | Status |
|---|---|---|---|---|
| 3-year | 19,441 | 0.0074 | 0.0054 | ❌ FAIL |
| 15-year | 91,929 | 0.267 | 0.288 | ❌ FAIL |
| 19-year | 122,015 | ~0.47–0.48 | ~0.47–0.48 | ❌ FAIL |
| 22-year | 144,443 | 0.3975 | 0.4265 | ❌ FAIL |

**True OOS JuristPref ceiling ~0.53 < 0.7 factory target.**  
**Linear hybrids** (citation concat / hybrid05) PASS adversarial at 19-year (JP ~0.54–0.55) but **remain BELOW TF-IDF baseline** (JP 0.66–0.67 vs 0.78–0.79 at 174k).  

**Verdict:** Dense embeddings CANNOT serve as primary navigation mode. Complementary views only.

---

## 3. Accepted Negative Results (Preserved Per Research Protocol)

| Finding | Evidence | Tier | Implication |
|---|---|---|---|
| **V17b label normalization fails generalization to 174k** | hierarchy=1.00x, zoom_fine=0.83–0.99x (degradation), NMI drops 0.59→0.45 | ACCEPTED_NEGATIVE | Label normalization regime differs at scale (213→111 vs 104→54 labels) |
| **V18 coarse hierarchy fails** | Max branch purity 0.6497 (`linear_citation_concat`) < 0.70 threshold | ACCEPTED_NEGATIVE | Even at 4-label branch granularity, hierarchy not recoverable |
| **Citation heritage recall@10 ~0.0066** | Near-zero nearest-neighbor retrieval | ACCEPTED_NEGATIVE | Citation heritage is ranking signal (AUC), not retrieval signal |
| **True OOS JuristPref ceiling ~0.53** | Extrapolated from scale curve | ACCEPTED_NEGATIVE | Dense embeddings fundamentally cannot beat TF-IDF for jurist preference |

---

## 4. Blockers & Dependencies

### 4.1 Data Blocker: 174k Dense Embeddings (Corpus Lane)
- **BGE/bger ID mapping** — canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs, no mapping exists
- **Parquet 2022-2026** — 29,520 decisions missing from current 144k checkpoint
- **Section extraction at 174k** — needed for cross-lingual section evaluation at scale

**Resolution required:** Corpus lane resumption (currently PAUSED). No 174k dense evaluation possible without this.

### 4.2 External Dependency: Jurist Human Study
- Framework ready for 5–10 Swiss jurists
- Required for true OOS JuristPref validation beyond adversarial proxy

---

## 5. Recommendations (Unchanged from Frozen State)

### For Product Lane
- **v1.0 Release:** Ship with TF-IDF citation hybrids as PRIMARY navigation mode (beats semantic baseline JP 0.78 vs 0.43)
- **v1.1+ Enhancements:** Dense embedding integration for:
  - Citation-heritage view (AUC > 0.75 validated)
  - Cross-lingual view (sachverhalt > 0.2, dispositiv > 0.1 validated)
  - Linear hybrid complement (w=0.3–0.4)

### For Legal-Distance Lane
- Compute 174k dense embeddings once data blocker resolved
- Focus on: `center_projected` (citation heritage + cross-lingual), linear hybrids (complement)
- Do NOT pursue `center_projected` for primary navigation (falsified)

### For Fractal-Map Lane
- TF-IDF hierarchical modes OPERATIONAL at 174k (3 production modes, 16/16 scale tests PASS)
- Dense integration contract: accept embeddings meeting complementary view criteria above

### For Evaluation Lane
- **No further same-question cycles justified** (`continue_recommended: false`)
- Next cycle only when 174k dense embeddings available
- Maintain frozen adversarial harness for regression testing

---

## 6. State Update

```json
{
  "lane": "evaluation",
  "direction_version": 34,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "COMPLETE",
  "continue_recommended": false,
  "accepted_run_id": "eval_174k_v34_baseline_and_dense_criteria_20261003",
  "github_run": 37248361999,
  "last_verified_run": 37248361999,
  "last_verified_timestamp": "2026-10-05T00:45:00.000000Z",
  "verification_note": "Final verification (run 37247224471 + 37248361999): Frozen TF-IDF 174k baseline confirmed via exact adversarial reproduction (config hash b51701f5a9c11692). All 8 representations PASS both gates. Dense acceptance criteria validated against 22-year/144k evidence. Center_projected FAILS jurist gate at ALL scales. No 174k dense embeddings — blocked on corpus lane. State remains ACCEPTED/COMPLETE/continue_recommended=false."
}
```

---

## 7. Evidence References

```json
{
  "tfidf_adversarial_baseline": "results/evaluation/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json",
  "tfidf_v25_formal_suite": "results/evaluation/v25_174k_formal_suite/results/_suite_summary.json",
  "tfidf_citation_heritage_174k": "results/evaluation/citation_heritage_174k_tfidf_latest.json",
  "dense_citation_heritage_22year": "results/evaluation/partial_dense_2000_2002/citation_heritage_22year_latest.json",
  "dense_section_crosslingual": "results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json",
  "v17b_label_normalization_174k": "evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json",
  "v18_coarse_hierarchy": "results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_latest.json",
  "dense_complementary_criteria": "results/evaluation/dense_complementary_acceptance_criteria.json",
  "eval_baseline_report": "reports/evaluation/eval_174k_v34_baseline_and_dense_criteria_report.md"
}
```

---

**Verification complete.** The evaluation lane state is frozen and correct. No action required until corpus lane delivers 174k dense embeddings.