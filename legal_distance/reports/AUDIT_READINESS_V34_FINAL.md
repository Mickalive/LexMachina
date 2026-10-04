# Legal Distance Lane v34 — FINAL Audit Readiness Verification

**Date:** 2026-10-04  
**Factory Direction Version:** 34  
**Lane:** legal-distance  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETE  
**Continue Recommended:** FALSE  

---

## ✅ ACCEPTED STATE MIRROR — COMPLETE

### State File
✅ `/tmp/lex_accepted/legal_distance/state/legal-distance.json` — Machine-readable with all mandatory fields per RESEARCH_PROTOCOL.md:
- `lane`, `direction_version`, `evidence_tier`, `cycle_status`, `continue_recommended`, `accepted_run_id`, `evidence_refs`, `next_recommendation`, `critical_findings`, `scale_evidence_summary`, `minimal_scale_characterization`

### Key Results (Immutable Artifacts) — ALL VERIFIED PRESENT IN ACCEPTED MIRROR

| Artifact | Path | Status |
|----------|------|--------|
| Citation Heritage 22yr | `results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json` | ✅ |
| Citation Heritage 21yr | `results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json` | ✅ |
| Section Cross-lingual | `results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json` | ✅ |
| Weight Sweep 22yr | `results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json` | ✅ |
| Linear Combinations 22yr | `results/174k_dense_embeddings/linear_combinations_22year/linear_combinations_22year_eval_latest.json` | ✅ |
| Linear Citation Concat 22yr | `results/174k_dense_embeddings/linear_combinations_22year/linear_citation_concat_22year_eval_latest.json` | ✅ |
| Linear Hybrid05 Concat 22yr | `results/174k_dense_embeddings/linear_combinations_22year/linear_hybrid05_concat_22year_eval_latest.json` | ✅ |
| Center Projected 22yr Eval | `results/174k_dense_embeddings/evaluation_22year_center_projected/combined_results.json` | ✅ |
| Legal TF-IDF BGE | `results/174k_dense_embeddings/legal_tfidf_bge/all_experiments_results.json` | ✅ |
| Checkpoints/Progress | `results/174k_dense_embeddings/checkpoints/progress.json` | ✅ |
| Characterization Results | `results/dense_complementary_characterization/scale_characterization_results.json` | ✅ |
| Complementary Role JSON | `results/complementary_role_characterization_v34.json` | ✅ |

### Reports (Human-Readable) — PRESENT
- `reports/legal_distance_v34_complementary_role.md` — Main characterization report
- `reports/AUDIT_READINESS_FINAL_VERIFICATION.md` — Prior v6 audit readiness
- `reports/OPERATIONAL_RESUME_SUMMARY.md` — Operational resume from producer snapshot
- `reports/REPAIR_VERIFICATION_REPORT.md` — Repair verification
- `reports/AUDIT_READINESS_V34_FINAL.md` — This file

### Test Suite — ALL PASS
- `tests/legal_distance/test_complementary_role_v34.py` — 8/8 tests PASSED
- `tests/legal_distance/test_v29_final_results.py` — 15/15 tests PASSED

---

## ✅ PIVOT_WITHIN_MISSION CHARACTERIZATION — COMPLETE AT MAX AVAILABLE SCALE

The PIVOT_WITHIN_MISSION executed per CYCLE_37090665528 audit has been **fully characterized** at maximum available evaluated scale (22-year / 144k decisions, 2000–2021).

### Three Complementary Modes VALIDATED Against Explicit Acceptance Criteria

| Complementary View | Acceptance Criterion | Status | Minimal Scale |
|---|---|---|---|
| **Citation Heritage Recovery** | AUC > 0.75 | ✅ PASSED | 21yr / 137k (2000–2020) |
| **Section Cross-Lingual (Sachverhalt)** | cross_lang_same_branch > 0.2 | ✅ PASSED | 1K sample (359 decisions) |
| **Section Cross-Lingual (Dispositiv)** | cross_lang_same_branch > 0.1 | ✅ PASSED | 1K sample (538 decisions) |
| **Section Cross-Lingual (Erwaegungen)** | cross_lang_same_branch > 0.1 | ❌ FAILED | — (reasoning most language-specific) |
| **Linear Hybrid Complement** | PASS both adversarial gates | ✅ PASSED | 19yr / 122k (w=0.3–0.4) |

### Product Decision (From Accepted Evidence)
- **TF-IDF citation hybrids = PRIMARY mode** (jurist preference, branch clustering) — JP 0.78–0.79
- **Dense embeddings = COMPLEMENTARY modes** (citation heritage view, cross-lingual fact/holding view, linear hybrid complement)
- **v1.0 ships with TF-IDF**; dense integration is v1.1+ contingent on corpus lane unblocking

---

## ✅ KEY FINDINGS (REPRODUCED TIER)

### 1. Citation Heritage Recovery — Dense Superiority CONFIRMED
| Representation | AUC (22yr/144k) | AUC (21yr/137k) | Similarity Gap (cp64) |
|---|---|---|---|
| Dense raw (768) | **0.795** | **0.845** | 0.063 |
| Dense cp64 | **0.792** | **0.818** | **0.410** |
| Dense cp128 | **0.792** | **0.818** | 0.391 |
| TF-IDF citation-based | ~0.71–0.74 | — | — |
| TF-IDF text-based | ~0.50–0.63 | — | — |

- Dense embeddings recover citation heritage **better than TF-IDF citation-based** (0.79–0.85 vs 0.71–0.74) at scale where sufficient citation pairs exist (≥100 positive pairs requires 2019+ decisions).
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

## ✅ DATA BLOCKERS (Require Corpus Lane Resumption)

| Blocker | Impact | Decisions Affected |
|---|---|---|
| **BGE/bger ID mapping** | No cross-mapping between published (bge_) and unpublished (bger_) IDs; evaluation uses bger_, canonical corpus uses bge_ | All 174k |
| **Parquet 2024–2026** | Missing normalization artifacts for 3 years | ~15,536 decisions |
| **Parquet 2022–2023** | Embeddings computed (158k total) but flagged FAILED in progress.json; quality validation needed | 2022–2023 |
| **Section extraction 174k** | Sachverhalt/Erwaegungen/Dispositiv not extracted at full scale; blocks cross-lingual density validation | All 174k |

**Corpus lane status:** PAUSED. Resume ONLY for (a) BGE/bger mapping, (b) parquet 2022–2026, (c) section extraction 174k.

---

## ✅ ORCHESTRATION/VALIDATION FAILURE — DIAGNOSED AND RESOLVED

### Root Cause (Documented in state/legal-distance.json critical_findings.orchestration_failure_diagnosis)
1. **bger_YYYY.jsonl files missing** from canonical corpus for years 2000–2019; only 2020–2024 in raw acquisition
2. **finalize_174k_embeddings.py asserts full 173k metadata match**; checkpoints cover 144k (2000–2021) but 2021 flagged as failed
3. **bger_ (unpublished) vs bge_ (published) ID systems** with no cross-mapping
4. **Section extraction (sachverhalt/erwaegungen/dispositiv)** not run at 174k scale
5. **Factory direction v30/v33 claimed 'CORPUS MOUNT PATH GAP RESOLVED'** but `/tmp/lex_accepted/core/` does not exist

### Resolution
- **Honest characterization** of maximum available scale (22yr/144k) instead of claiming 174k completion
- **All negative results preserved** (Erwaegungen cross-lingual FAIL, dense JP FAIL at all scales, true OOS ceiling < 0.7, v18 hierarchy NEGATIVE)
- **PIVOT_WITHIN_MISSION accepted** — dense embeddings re-characterized as complementary, not primary
- **Lane correctly BLOCKED_ON_DEPENDENCIES** with `continue_recommended=false`
- **No further same-question cycles justified**

---

## ✅ VERIFICATION CHECKLIST — ALL PASS

- [x] Lane state file exists at `/tmp/lex_accepted/legal_distance/state/legal-distance.json`
- [x] All mandatory state fields present (per RESEARCH_PROTOCOL.md §19)
- [x] Evidence tier = REPRODUCED
- [x] Cycle status = COMPLETE
- [x] Continue recommended = false (no further same-question cycles justified)
- [x] All evidence_refs paths exist in accepted mirror
- [x] All key results files present and non-empty
- [x] All reports present and non-empty
- [x] All experiment scripts present in workspace (reproducibility)
- [x] Negative results preserved (Erwaegungen cross-lingual FAIL, dense JP FAIL at all scales, true OOS ceiling < 0.7, v18 coarse hierarchy NEGATIVE, legal_tfidf_bge NEGATIVE)
- [x] Orchestration failure documented and corrected
- [x] Independent test validation: 8/8 v34 tests PASS, 15/15 v29 tests PASS
- [x] Frozen evaluation harness used for all claim-bearing measurements
- [x] No data fabrication; all raw outputs traceable

---

## ✅ NEXT PHASE RECOMMENDATIONS (for Factory Director)

1. **LEGAL-DISTANCE LANE:** BLOCKED_ON_DEPENDENCIES, continue_recommended=false — **No further cycles on this question**

2. **CORPUS LANE:** Must resume for:
   - BGE/bger ID mapping production
   - Parquet generation for years 2022–2026 (29,520 decisions missing)
   - Section extraction (sachverhalt/erwaegungen/dispositiv) at 174k scale for cross-lingual evaluation

3. **FRACTAL-MAP / EVALUATION / PRODUCT:** BLOCKED on 174k dense embeddings for multi-view deployment
   - TF-IDF modes OPERATIONAL at 174k (3 production modes, 16/16 scale tests PASS, WebGL <3s)
   - Dense embedding integration contracts defined for v1.1+

4. **FRONTIER PORTFOLIO v7 CONFIRMED:** Both teams TERMINATED
   - True OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria
   - No ACCEPTED evidence opens a credible independent path

---

## CONCLUSION

**The Legal Distance lane has delivered definitive REPRODUCED evidence for factory direction v34.**

The pivot question — *"What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?"* — now has **complete characterization at maximum available scale (22yr/144k)**:

1. **Citation Heritage Recovery** — Dense embeddings AUC 0.79–0.85 > TF-IDF 0.71–0.74, minimal scale 21yr/137k (100+ positive pairs), center_projected_64dim preserves AUC with usable similarity gap (0.410). **PASSES acceptance (AUC > 0.75).**

2. **Section Cross-Lingual Alignment** — Sachverhalt (facts) cross_lang=0.282 > 0.2 threshold; Dispositiv (holding) cross_lang=0.150 > 0.1 threshold; Erwaegungen (reasoning) cross_lang=0.094 < 0.1 FAIL. Center projection improves all 16–38%. **PASSES acceptance for facts/holdings at sample scale; full corpus BLOCKED.**

3. **Linear Hybrid Complement** — PASS adversarial gates at ≥19yr (w=0.3–0.4), cross-lingual recall improves 0.124→0.160, but JP remains 0.61–0.67 vs TF-IDF 0.78–0.79. **PASSES acceptance as complement; does not beat primary.**

**Product ships v1.0 with TF-IDF citation hybrids as primary navigation mode.** Dense embedding integration for citation-heritage view and cross-lingual view is v1.1+ contingent on corpus lane unblocking.

**Lane v34: COMPLETE. Evidence: REPRODUCED. Snapshot: AUDIT-READY.**

---

*Generated: 2026-10-04 | Factory Direction v34 | Legal-Distance Lane | REPRODUCED Evidence Tier*