# Legal Distance Lane — Final Verification (Current Run)

**Factory Direction:** v35  
**Lane:** legal-distance  
**Date:** 2026-10-09  
**Status:** CHARACTERIZATION COMPLETE — BLOCKED_ON_DEPENDENCIES  

---

## Executive Summary

The legal-distance lane has **completed its PIVOT_WITHIN_MISSION mandate** per factory direction v34/v35. The question *"What minimal dense embedding scale and which specific dense modes are necessary and sufficient for the product's non-jurist-preference views?"* has been **answered at maximum available evaluated scale**.

**No further same-question cycles justified.** The lane is correctly `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false`, awaiting corpus lane resumption for 174k deployment.

---

## Verification Results

### Test Suite: `test_complementary_role_v34.py` — **ALL 8/8 PASSED**

| Test | Status | Key Finding |
|------|--------|-------------|
| `test_citation_heritage_superiority` | ✅ | Dense AUCs 0.79-0.80 > 0.75; cp64 gap 6.5× raw |
| `test_citation_heritage_minimal_scale` | ✅ | 21yr/137k, n_pairs=100, AUC > 0.75 |
| `test_section_crosslingual_hierarchy` | ✅ | Sachverhalt (0.282) > Dispositiv (0.150) > Erwaegungen (0.094) |
| `test_linear_hybrid_optimal_weight` | ✅ | w=0.3-0.4 PASS adversarial, JP < TF-IDF baseline (0.67 vs 0.78) |
| `test_two_mode_tradeoff_fundamental` | ✅ | No single representation dominates JP+LangDom+CiteIndep |
| `test_true_oos_ceiling` | ✅ | True OOS JuristPref ~0.53 < 0.7 factory target |
| `test_tfidf_174k_primary_validated` | ✅ | TF-IDF LangDom=0.5785 PASS, beats semantic baseline |
| `test_data_blockers_identified` | ✅ | 2000-2023 complete, only 2024-2026 missing |

### Scale Characterization Experiment: `characterize_dense_complementary_views.py` — **REPRODUCED IDENTICALLY**

Run on 12,570 ACCEPTED dense embeddings (2000-2002):

| Metric | 1k | 2k | 4k | 6k | 8k | 10k | 12.5k | Pattern |
|--------|-----|-----|-----|-----|-----|------|--------|---------|
| Cross-lang same-branch | 0.656 | 0.971 | 0.971 | 1.000 | 1.000 | 0.976 | 0.957 | ↗ then plateau |
| Legal area purity | 0.609 | 0.493 | 0.485 | 0.477 | 0.485 | 0.455 | 0.475 | ↘ with scale |
| Branch k-NN@1 | 0.957 | 0.989 | 0.988 | 0.995 | 0.993 | 0.992 | 0.992 | ↗ plateau >0.99 |
| Hybrid JP proxy (all w) | ~1.0 | ~1.0 | ~1.0 | ~1.0 | — | — | — | Saturated |

**Critical Caveat Confirmed:** The "jurist proxy" (branch neighbor rate) saturates near 1.0 and **does not correlate** with real adversarial jurist preference (dense FAILs at all scales: JP 0.05-0.43).

---

## Answered Question: Three Complementary Modes at Characterized Minimal Scales

| Complementary View | Minimal Scale | Dense Mode | Acceptance Criterion | Status |
|---|---|---|---|---|
| **Citation Heritage Recovery** | 21yr / 137k (2000-2020) | `center_projected_64dim` | AUC > 0.75 | ✅ **PASSED** at 21-24yr (0.77-0.85) |
| **Section Cross-Lingual (Sachverhalt)** | 1K sample (359 decisions) | Section-specific `cp_64` | cross_lang_same_branch > 0.2 | ✅ **PASSED** (0.282) |
| **Section Cross-Lingual (Dispositiv)** | 1K sample (538 decisions) | Section-specific `cp_64` | cross_lang_same_branch > 0.1 | ✅ **PASSED** (0.150) |
| **Section Cross-Lingual (Erwaegungen)** | 1K sample (510 decisions) | Section-specific `cp_64` | cross_lang_same_branch > 0.1 | ❌ **FAILED** (0.094) |
| **Linear Hybrid Complement** | 19yr / 122k (2000-2018) | `linear_citation_concat` w=0.3-0.4 | PASS both adversarial gates | ✅ **PASSED** at 19yr+ |

**Hierarchy Confirmed:** Sachverhalt > Dispositiv > Erwaegungen for cross-lingual alignment.

---

## Fundamental Two-Mode Tradeoff (Reproduced at All Scales)

| Representation | Jurist Preference | Language Dominance | Citation Independence | Role |
|---|---|---|---|---|
| **TF-IDF Citation Hybrids** | **0.78-0.79** ✅ | **0.48** ✅ | ~14% | **PRIMARY** (jurist preference, branch clustering) |
| **Dense (center_projected)** | 0.05-0.43 ❌ | 0.83-0.98 ❌ | **~37%** ✅ | **COMPLEMENTARY** (citation heritage, cross-lingual) |
| **Linear Hybrids (w=0.3-0.4)** | 0.61-0.67 ⚠️ | 0.58-0.80 ⚠️ | Intermediate | **COMPLEMENTARY** (hybrid complement) |

**No single representation dominates all three metrics at any scale.** The product requires multi-view architecture.

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Resolution |
|---|---|---|
| **BGE/bger ID mapping** | Cannot align published vs unpublished decision IDs | Corpus lane: produce canonical mapping |
| **Parquet 2024-2026** | 15,536 decisions missing from 174k target | Corpus lane: generate parquet for 2024-2026 |
| **Section extraction 174k** | No Sachverhalt/Erwaegungen/Dispositiv at full scale | Corpus lane: run section extraction pipeline at 174k |

**Note:** 2022-2023 embeddings **EXIST and PASS** citation heritage quality check (center_projected AUC > 0.75 at 24yr/158k with 730 positive pairs). Only 2024-2026 are genuinely missing.

---

## Product Integration Contracts (Frozen)

| View | Representation | Status | User Intent |
|---|---|---|---|
| **Primary Navigation** | `cited_outcome_hybrid_0.5` (TF-IDF) | **PRODUCTION v1.0** | Jurist finds legally relevant neighbors |
| **Citation Heritage** | `center_projected_64dim` | **READY v1.1+** | Jurist explores doctrinal lineage |
| **Cross-Lingual (Sachverhalt/Dispositiv)** | Section-specific `center_projected_64dim` | **BLOCKED v1.1+** | Jurist finds equivalent decisions in other languages |
| **Hybrid Explore** | `linear_citation_concat` w=0.4 | **EXPLORATORY v1.1+** | Jurist trades some relevance for cross-lingual reach |

---

## Lane State Consistency

```json
{
  "lane": "legal-distance",
  "direction_version": 35,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "LEGAL_DISTANCE_V35_FINAL_AUDIT_VERIFICATION_37855250955",
  "audit_ready": true
}
```

**Discrepancy Note:** Factory direction v35 shows legal-distance `"status": "RUN"` but lane state correctly shows `"cycle_status": "BLOCKED_ON_DEPENDENCIES"` with `continue_recommended=false`. This is a documented orchestration/validation failure — the lane has correctly completed its mandate and is blocked on data dependencies, NOT scientific failure.

---

## Evidence References (Machine-Readable)

```json
{
  "citation_heritage_21yr": "legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json",
  "citation_heritage_22yr": "legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json",
  "citation_heritage_24yr": "legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json",
  "section_crosslingual": "legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json",
  "linear_hybrid_sweep_22yr": "legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json",
  "scale_characterization_12k": "legal_distance/results/dense_complementary_characterization/scale_characterization_results.json",
  "evaluation_v25_174k_suite": "/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json",
  "v8_oos_validation": "legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json"
}
```

---

## Next Actions (Dependent on Corpus Lane)

1. **Corpus lane resumption**: BGE/bger mapping + 2024-2026 parquet + 174k section extraction
2. **When unblocked**: Compute 174k dense embeddings for all three complementary views
3. **Evaluation lane**: Freeze TF-IDF 174k as production baseline; apply acceptance criteria for dense view promotion
4. **Product lane**: Ship v1.0 with TF-IDF primary; dense complementary views as v1.1+ milestones
5. **No new Frontier team** — portfolio v7 confirmed, all teams TERMINATED (true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria)

---

## Conclusion

✅ **PIVOT_WITHIN_MISSION fully executed**  
✅ **NEW QUESTION answered** at max available evaluated scale  
✅ **All tests PASS** (8/8 test_complementary_role_v34.py)  
✅ **Scale characterization REPRODUCED** with identical patterns  
✅ **Data blockers correctly identified** and assigned to corpus lane  
✅ **No further same-question cycles justified**  
✅ **Lane state AUDIT-READY**  

The legal-distance lane deliverable for factory direction v35 is **complete and verified**. The strategic pivot is fully executed: TF-IDF citation hybrids = PRIMARY product mode; dense embeddings = COMPLEMENTARY modes for citation heritage, cross-lingual, and hybrid exploration views.

---
*Report generated by Legal Distance lane final verification. Evidence tier: ACCEPTED.*