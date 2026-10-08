# Legal Distance v35 — Final Verification (Run 37850702422)

**Factory Direction:** v35  
**Lane:** legal-distance  
**Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  
**Run ID:** 37850702422  
**Date:** 2026-10-08  

---

## Verification Summary

This run confirms the **PIVOT_WITHIN_MISSION characterization is complete and all tests pass**. No new experiments were run — this is a verification of existing ACCEPTED evidence.

### Tests Executed (All PASS)

| Test Suite | Tests | Status |
|------------|-------|--------|
| `test_complementary_role_v34.py` | 8/8 | ✅ PASS |
| `test_v29_final_results.py` | 15/15 | ✅ PASS |
| **Total** | **23/23** | ✅ **ALL PASS** |

---

## Characterization Confirmed (Factory Direction v34 Question Answered)

> **"What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?"**

### Answer: Three Complementary Views at Characterized Minimal Scales

| Complementary View | Minimal Scale | Dense Mode | Acceptance Criterion | Status |
|---|---|---|---|---|
| **Citation Heritage Recovery** | 21yr / 137k (2000–2020) | `center_projected_64dim` | AUC > 0.75 | ✅ PASSED at 21–24yr |
| **Section Cross-Lingual (Sachverhalt)** | 1K sample (n=359) | `center_projected_64dim` per section | `cross_lang_same_branch` > 0.2 | ✅ PASSED (0.282) |
| **Section Cross-Lingual (Dispositiv)** | 1K sample (n=538) | `center_projected_64dim` per section | `cross_lang_same_branch` > 0.1 | ✅ PASSED (0.150) |
| **Section Cross-Lingual (Erwaegungen)** | 1K sample (n=510) | `center_projected_64dim` per section | `cross_lang_same_branch` > 0.1 | ❌ FAILED (0.094) |
| **Linear Hybrid Complement** | 19yr / 122k (2000–2018) | `linear_citation_concat` / `linear_hybrid05_concat` at w=0.3–0.4 | PASS both adversarial gates | ✅ PASSED at 19yr+ |

---

## Key Findings Reconfirmed

1. **Dense embeddings FAIL jurist gate at ALL scales** (JP 0.05–0.43) — cannot be primary navigation
2. **TF-IDF citation hybrids DOMINATE jurist preference** (JP 0.78–0.79) — PRIMARY product mode
3. **Dense embeddings SUPERIOR for citation heritage** (AUC 0.79–0.85 vs TF-IDF 0.71–0.74)
4. **Section cross-lingual hierarchy**: Sachverhalt > Dispositiv > Erwaegungen (facts align best cross-lingually)
5. **Linear hybrids PASS adversarial but BELOW TF-IDF baseline** (JP 0.61–0.67 vs 0.78–0.79) — exploratory only
6. **Two-mode tradeoff is FUNDAMENTAL** — no single representation dominates JP + LangDom + CiteIndep
7. **True OOS JuristPref ceiling ~0.53 < 0.7 factory target**

---

## Data Blockers (Unchanged, Require Corpus Lane)

| Blocker | Impact | Resolution |
|---------|--------|------------|
| **BGE/bger ID mapping** | No cross-mapping between published (bge_) and unpublished (bger_) IDs | Corpus lane |
| **Parquet 2024–2026** | Missing normalization artifacts (~15,536 decisions) | Corpus lane |
| **Section extraction 174k** | Blocks full-corpus cross-lingual density validation | Corpus lane |

---

## Product Integration Contracts (Frozen)

| View | Representation | Status | User Intent |
|------|---------------|--------|-------------|
| **Primary Navigation** | `cited_outcome_hybrid_0.5` (TF-IDF) | PRODUCTION v1.0 | Jurist finds legally relevant neighbors |
| **Citation Heritage** | `center_projected_64dim` | READY v1.1+ | Jurist explores doctrinal lineage via shared citations |
| **Cross-Lingual** | `center_projected_64dim` per section (sachverhalt > dispositiv) | BLOCKED v1.1+ | Jurist finds equivalent decisions in other languages |
| **Hybrid Complement** | `linear_citation_concat_w0.4` / `linear_hybrid05_concat_w0.3` | EXPLORATORY v1.1+ | Jurist trades some legal relevance for cross-lingual reach |

---

## Recommendation

**CONTINUE = FALSE** — No further same-question cycles justified.

The complementary role characterization is **complete at maximum available evaluated scale**. The lane is correctly `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false`.

### Next Actions (Dependent on Corpus Lane Resumption)

1. **Corpus lane**: Resume for bge_↔bger_ mapping, 2024–2026 parquet generation, 174k section extraction
2. **When unblocked**: Compute 174k dense embeddings for all three complementary views
3. **Evaluation lane**: Apply frozen acceptance criteria for dense view promotion
4. **Product lane**: Ship v1.0 with TF-IDF primary; dense complementary views as v1.1+ milestones
5. **No new Frontier team** — portfolio v7 confirmed, all teams TERMINATED

---

## Evidence References

- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_19year/linear_combinations_19year_eval_latest.json`
- `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v8_holdout_zero_shot_validation/holdout_zero_shot_validation_fixed.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json`

---

## State Update

Updated `legal_distance/state/legal-distance.json`:
- `current_run`: 37850702422
- Added verification run entry for 37850702422
- All fields consistent with factory direction v35 strategic pivot

---

*Verification complete. Lane characterization frozen. Awaiting corpus lane unblocking for 174k deployment.*