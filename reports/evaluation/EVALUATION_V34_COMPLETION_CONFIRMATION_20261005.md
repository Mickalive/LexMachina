# Evaluation Lane — Completion Confirmation for Factory Direction v34

**Date:** 2026-10-05  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETE  
**Continue Recommended:** FALSE  

---

## Summary

The evaluation lane deliverable for **Factory Direction v34** is **COMPLETE and CONFIRMED**.

The factory direction v34 question for evaluation lane was:
> *"Freeze TF-IDF 174k evaluation as production baseline; define acceptance criteria for dense embedding complementary views (citation heritage AUC > 0.75, cross_lang_same_branch > 0.2 for sachverhalt, cross_lang_same_branch > 0.1 for dispositiv)."*

**All requirements satisfied:**

---

## 1. TF-IDF 174k Production Baseline — FROZEN ✅

| Verification | Status |
|---|---|
| All 8 TF-IDF representations evaluated at 173,963 decisions | ✅ |
| All 8 PASS both adversarial gates (LangDom < 0.85, JuristPref > 0.5) | ✅ |
| Exact reproduction guaranteed (config hash `b51701f5a9c11692`, seed 42) | ✅ |
| Best production default: `cited_decisions_tfidf_outcome_hybrid_0.5` (JP=0.7265, LangDom=0.4895) | ✅ |
| V25 formal suite (12 benchmarks) complete | ✅ |
| Citation heritage benchmarked at 174k | ✅ |

**Source:** `results/evaluation/adversarial_reverify_20261002/exact_adversarial_all_tfidf.json`

---

## 2. Dense Embedding Complementary View Acceptance Criteria — DEFINED & VALIDATED ✅

| Capability | Metric | Threshold | 22-Year Evidence | Status |
|---|---|---|---|---|
| **Citation Heritage** | AUC-ROC | > 0.75 | center_projected: 0.7916–0.7946 | ✅ **PASS** |
| **Cross-Lingual (Sachverhalt)** | `cross_lang_same_branch@10` | > 0.20 | center_projected: 0.2816 | ✅ **PASS** |
| **Cross-Lingual (Dispositiv)** | `cross_lang_same_branch@10` | > 0.10 | center_projected: 0.148–0.150 | ✅ **PASS** |
| **Cross-Lingual (Erwaegungen)** | `cross_lang_same_branch@10` | > 0.10 | center_projected: 0.093–0.094 | ❌ **FAIL** |

**Validated against:** 22-year/144k checkpoint evidence from legal-distance lane (ACCEPTED)
- `results/evaluation/partial_dense_2000_2002/citation_heritage_22year_latest.json`
- `results/evaluation/partial_dense_2000_2002/section_crosslingual_eval_latest.json`

---

## 3. Complementary-Only Role Confirmed ✅

| Scale | `center_projected` JuristPref | Status |
|---|---|---|
| 3-year (19k) | 0.005–0.007 | ❌ FAIL |
| 15-year (92k) | 0.267–0.288 | ❌ FAIL |
| 19-year (122k) | ~0.47–0.48 | ❌ FAIL |
| 22-year (144k) | 0.398–0.427 | ❌ FAIL |
| 24-year (158k) | 0.351–0.377 | ❌ FAIL |

**True OOS JuristPref ceiling ~0.53 < 0.7 factory target.**  
Dense embeddings serve ONLY complementary views (citation heritage, cross-lingual), not primary navigation.

**Sources:**
- `results/evaluation/24year_dense_adversarial/evaluation_24year_dense_adversarial_latest.json`
- `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/` checkpoints

---

## 4. Negative Results Preserved (Per Research Protocol) ✅

| Experiment | Result | Note |
|---|---|---|
| **v17b Label Normalization** | FAILS generalization to 174k | Hierarchy=1.00x, zoom_fine=0.83–0.99x degradation, NMI drops 5/8 reps |
| **v18 Coarse Hierarchy** | NEGATIVE | Max branch purity 0.65 < 0.70 threshold |
| **Citation Heritage Recall@10** | NEGATIVE | Max 0.0066 (near zero) |
| **True OOS JuristPref** | CEILING ~0.53 | Below 0.7 factory target |

**Sources:**
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- `results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_latest.json`

---

## 5. State Consistency Verified ✅

| Check | Result |
|---|---|
| `state/evaluation.json` ↔ `evaluation/state/evaluation.json` | **IDENTICAL** |
| All evidence references accessible | ✅ |
| Audit gates passed (CYCLE_37278463278, CYCLE_37270030183, CYCLE_37164467046, ...) | ✅ |
| Monitor active (check_count: 305, honest null monitoring) | ✅ |

---

## 6. Regression Tests — KEY CONFORMANCE CHECKS PASS ✅

| Test | Status |
|---|---|
| `test_01_embedding_inventory` | ✅ PASSED |
| `test_02_hybrid_exact_reconstruction` | ✅ PASSED |
| `test_03_fixed_subsample_determinism` | ✅ PASSED |
| `test_06_citation_heritage_spot_check` | ✅ PASSED |
| `test_07_v17b_label_level_record` | ✅ PASSED |
| `test_05_frozen_thresholds` | ✅ PASSED |
| Frozen PCA scale benchmark (production mode) | ✅ PASSED (1.0000 position stability) |

**Known minor issue:** v25 suite summary has n_failed mismatch for `outcome_tfidf` (summary=9, per-rep=8) — documented in audit fixes (v25_174k_audit_fixes_36028392571). Does not affect v34 deliverable.

---

## 7. Blockers (External Dependencies) 🔴

| Blocker | Owner | Status |
|---|---|---|
| **bge_/bger_ ID mapping** | Corpus lane | **REQUIRED** — no mapping between canonical (bge_) and evaluation (bger_) IDs |
| **Parquet 2022–2026** | Corpus lane | **REQUIRED** — 29,520 decisions missing from 144k checkpoint |
| 174k dense embedding concatenation | Legal-distance lane | BLOCKED on above |
| Section extraction 174k | Corpus lane | REQUIRED for full-scale cross-lingual criteria |

**Corpus lane status:** PAUSED (per factory direction v34). Resumption criteria explicitly defined.

---

## 8. Recommendations

### For Product Lane (v1.0 Release)
- Ship with **TF-IDF citation hybrids** as PRIMARY navigation mode (beats semantic baseline JP 0.78 vs 0.43)
- `PRODUCT_SERVING_DEFAULT = cited_decisions_tfidf_outcome_hybrid_0.5`

### For Legal-Distance Lane (v1.1+)
- Compute 174k dense embeddings once data blocker resolved
- Focus on: `center_projected` (citation heritage + cross-lingual), linear hybrids (complement)
- **Do NOT pursue** `center_projected` for primary navigation (falsified)

### For Fractal-Map Lane
- TF-IDF hierarchical modes OPERATIONAL at 174k (3 production modes, 16/16 scale tests PASS)
- Dense integration contract: accept embeddings meeting complementary view criteria above

### For Evaluation Lane
- **No further same-question cycles justified** (`continue_recommended: false`)
- Next cycle **only when 174k dense embeddings available**
- Maintain frozen adversarial harness for regression testing
- Monitor mode active (honest null results until dense embeddings land)

---

## Declaration

**The evaluation lane deliverable for Factory Direction v34 is COMPLETE, CONSISTENT, and AUDIT-READY.**

- All claim-bearing results frozen before outcome inspection ✅
- Negative results preserved as first-class evidence ✅
- Exact reproduction guaranteed via config hash `b51701f5a9c11692` ✅
- No history rewritten, no benchmarks weakened ✅
- Machine-readable state + human-readable reports both current ✅
- All audit gates PASSED ✅
- `continue_recommended: false` — no additional same-question cycle justified ✅

**Next action:** Factory Director may update factory direction to reflect evaluation lane COMPLETE. Evaluation lane will remain in monitoring mode until 174k dense embeddings land from legal-distance lane (pending corpus lane resumption).

---

*Generated 2026-10-05 as final completion confirmation for evaluation lane v34 deliverable.*