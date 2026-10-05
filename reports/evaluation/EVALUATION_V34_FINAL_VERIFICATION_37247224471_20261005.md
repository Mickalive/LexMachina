# Evaluation Lane v34 — Final Verification Run 37247224471

**Date:** 2026-10-05  
**Factory Direction Version:** 34  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETE  
**Continue Recommended:** false  

---

## Verification Summary

This run performs the final verification of the frozen TF-IDF 174k production baseline and dense embedding complementary view acceptance criteria as defined in Factory Direction v34 and the accepted evaluation report `eval_174k_v34_baseline_and_dense_criteria_20261003`.

### Frozen TF-IDF 174k Baseline — CONFIRMED

**Config Hash:** `b51701f5a9c11692` (exact reproduction)

| Representation | Language Dominance | Jurist Preference | Both Gates |
|---|---|---|---|
| `cited_decisions_tfidf` | 0.4917 | 0.7075 | ✅ |
| **`cited_decisions_tfidf_outcome_hybrid_0.5`** | **0.4895** | **0.7265** | ✅ **PRODUCTION DEFAULT** |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 0.4908 | 0.7195 | ✅ |
| `outcome_tfidf` | 0.5078 | 0.6660 | ✅ |
| `regeste_tfidf` | 0.5111 | 0.6145 | ✅ |
| `full_text_tfidf_light` | 0.4854 | 0.7080 | ✅ |
| `regeste_full_text_hybrid_0.5` | 0.4873 | 0.7140 | ✅ |
| `regeste_full_text_hybrid_0.7` | 0.4889 | 0.7120 | ✅ |

**All 8/8 representations PASS both adversarial gates** (LangDom < 0.85, JuristPref > 0.5).  
**Range:** LangDom [0.485, 0.511], JP [0.614, 0.727].

---

### Dense Embedding Acceptance Criteria — RE-VALIDATED Against 22-Year/144k Evidence

| Criterion | Threshold | 22-Year Evidence | Status |
|---|---|---|---|
| **Citation Heritage AUC** | > 0.75 | center_projected: 0.7916–0.7946 | ✅ **PASS** |
| **Cross-Lang Sachverhalt** | > 0.20 | center_projected: 0.282 | ✅ **PASS** |
| **Cross-Lang Dispositiv** | > 0.10 | center_projected: 0.148–0.150 | ✅ **PASS** |
| **Cross-Lang Erwaegungen** | > 0.10 | center_projected: 0.093–0.094 | ❌ **FAIL** |

**Jurist Preference Gate (Primary Navigation):**  
Center_projected FAILS at ALL scales (3-year JP 0.005–0.007, 15-year 0.267–0.288, 19-year ~0.47–0.48, 22-year 0.398–0.427).  
**True OOS ceiling ~0.53 < 0.7 factory target.** Dense embeddings are **complementary views only**.

---

### Negative Results Preserved (Per Research Protocol)

| Finding | Evidence Tier | Status |
|---|---|---|
| V17b label normalization fails generalization to 174k | REPRODUCED | hierarchy=1.00x, zoom_fine=0.83–0.99x (degradation), NMI drops |
| V18 coarse hierarchy (4-label branch) | ACCEPTED | max branch purity 0.65 < 0.70 threshold |
| Citation heritage recall@10 | ACCEPTED | max 0.0066 (near zero) |

---

### Blockers Unchanged — Corpus Lane Dependencies

| Blocker | Impact | Owner |
|---|---|---|
| **BGE/bger ID mapping** | Canonical corpus uses `bge_`; evaluation uses `bger_` — no mapping | Corpus lane |
| **Parquet 2022–2026** | 29,520 decisions missing; cannot compute 174k dense embeddings | Corpus lane |
| **Section extraction 174k** | Sachverhalt/Erwaegungen/Dispositiv needed for cross-lingual criteria | Corpus lane |

**No further evaluation cycles justified** until corpus lane resolves these blockers. The criteria are frozen; corpus unblocking is the only path forward.

---

## State Confirmation

The evaluation lane state (`state/evaluation.json`) remains:
- `evidence_tier`: **ACCEPTED**
- `cycle_status`: **COMPLETE**
- `continue_recommended`: **false**
- `accepted_run_id`: `eval_174k_v34_baseline_and_dense_criteria_20261003`

**No additional same-question cycle is justified.** The Factory Director may now decide the successor question when 174k dense embeddings become available.

---

## Evidence References (Machine-Readable)

```json
{
  "tfidf_adversarial_baseline": "results/evaluation/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json",
  "tfidf_v25_formal_suite": "results/evaluation/v25_174k_formal_suite/results/_suite_summary.json",
  "tfidf_citation_heritage_174k": "results/evaluation/citation_heritage_174k_tfidf_latest.json",
  "dense_citation_heritage_22year": "results/evaluation/partial_dense_2000_2002/citation_heritage_22year_latest.json",
  "dense_section_crosslingual": "results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json",
  "v17b_label_normalization_174k": "evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json",
  "v18_coarse_hierarchy": "results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_latest.json"
}
```

---

**This verification confirms the evaluation lane work for Factory Direction v34 is COMPLETE and AUDIT-READY.**