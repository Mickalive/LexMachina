# Legal Distance Lane — Audit-Ready Verification (Factory Direction v34)
**GitHub Run**: 37509635487  
**Lane**: legal-distance  
**Status**: BLOCKED_ON_DEPENDENCIES | continue_recommended=false | audit_ready=true  
**Evidence Tier**: ACCEPTED  
**Verification Date**: 2026-10-06  

---

## Executive Summary

The legal-distance lane has **completed all deliverables** for factory direction v34. The PIVOT_WITHIN_MISSION (per CYCLE_37090665528 audit) has been executed and characterized at maximum available scale (24-year / 158,427 decisions).

**All 8 test assertions in `test_complementary_role_v34.py` PASSED** — confirming the complementary role characterization is complete, reproducible, and audit-ready.

---

## Verification Results

| Test | Status | Key Finding |
|------|--------|-------------|
| `test_citation_heritage_superiority` | ✅ PASS | Dense embeddings AUC 0.79-0.85 > TF-IDF citation baseline 0.71-0.74 at 22yr (144k) |
| `test_citation_heritage_minimal_scale` | ✅ PASS | Minimal sufficient scale: 21yr/137k with ≥100 positive citation pairs |
| `test_section_crosslingual_hierarchy` | ✅ PASS | Sachverhalt (0.282) > Dispositiv (0.150) > Erwaegungen (0.094) hierarchy confirmed |
| `test_linear_hybrid_optimal_weight` | ✅ PASS | w=0.3-0.4 PASS adversarial, cross-lingual improvement, but JP < TF-IDF baseline |
| `test_two_mode_tradeoff_fundamental` | ✅ PASS | No single representation dominates JP + LangDom + CiteIndep at any scale |
| `test_true_oos_ceiling` | ✅ PASS | True OOS JuristPref ceiling ~0.53 < 0.7 factory target confirmed |
| `test_tfidf_174k_primary_validated` | ✅ PASS | TF-IDF citation hybrids beat semantic baseline (JP 0.78 vs 0.43) at 174k |
| `test_data_blockers_identified` | ✅ PASS | 2024-2026 missing (15.5k decisions); 2021-2023 embeddings EXIST and PASS quality |

---

## PIVOT_WITHIN_MISSION Deliverables (Factory Direction v34)

### Primary Product Mode (v1.0)
- **TF-IDF Citation Hybrids** (`cited_outcome_hybrid_0.5_174k`)
- **Jurist Preference**: 0.73-0.79 (beats semantic baseline 0.43)
- **Status**: OPERATIONAL at full 173,963 decisions

### Complementary Dense Modes (v1.1+)
| View | Capability | Minimal Scale | Acceptance Criteria | Status |
|------|------------|---------------|---------------------|--------|
| **Citation Heritage** | Doctrinal proximity via shared citations | 21yr/137k | AUC > 0.75 | ✅ READY at 144k |
| **Cross-Lingual** | Sachverhalt cross-language alignment | 174k (full) | cross_lang > 0.2 (sachverhalt) | ⚠️ SAMPLE ONLY (1K) |
| **Linear Hybrid Complement** | Cross-lingual benefit in hybrid | 19yr/122k | PASS both gates + cross-lang > TF-IDF | ✅ READY at 144k |

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Resolution |
|---------|--------|------------|
| **bge_ ↔ bger_ ID mapping** | Cannot align canonical corpus with evaluation | Corpus lane |
| **Parquet 2024-2026 missing** | 15.5k decisions (2024-2026) absent | Corpus lane |
| **Section extraction at 174k** | Cross-lingual view limited to 1K sample | Corpus lane |

**Note**: 2021-2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75 at 24yr/158k with 730 positive pairs). Only 2024-2026 are genuinely missing.

---

## Evidence Provenance (Immutable)

All claim-bearing outputs preserved with provenance:

```
legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json
legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json
legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json
legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json
legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json
legal_distance/results/174k_dense_embeddings/evaluation_22year_center_projected/combined_results.json
legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json
/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json
legal_distance/results/dense_complementary_characterization/scale_characterization_results.json
```

---

## Machine-Readable State

`/tmp/lex_control/state/legal-distance.json` — synchronized and verified:
- `evidence_tier: "ACCEPTED"`
- `cycle_status: "BLOCKED_ON_DEPENDENCIES"`
- `continue_recommended: false`
- `audit_ready: true`
- `accepted_run_id: "LEGAL_DISTANCE_V34_COMPLEMENTARY_ROLE_FINAL_20261006_37412982439"`

---

## Compliance with Research Protocol

- ✅ Hypothesis, baseline, and success rule frozen before observation
- ✅ Negative results preserved (dense FAIL jurist gate, legal TF-IDF FAIL, hierarchy FAIL)
- ✅ Strong baselines used (whole-doc semantic, TF-IDF, citation-only, hybrids)
- ✅ Evaluation on frozen harness with fixed seed
- ✅ Provenance preserved for all claim-bearing outputs
- ✅ Machine-readable state file updated with evidence_refs
- ✅ PIVOT_WITHIN_MISSION documented with product integration contract

---

## Recommendation: NO FURTHER SAME-QUESTION CYCLES

The lane is correctly **BLOCKED_ON_DEPENDENCIES** with **continue_recommended=false**.

**Next Actions (Factory Director)**:
1. **Corpus lane**: Resume for bge_↔bger_ mapping, 2024-2026 parquet, section extraction at 174k
2. **Product lane**: Ship v1.0 with TF-IDF citation hybrids as primary (JP 0.78 vs 0.43 semantic baseline)
3. **Dense integration**: v1.1+ for citation-heritage view and cross-lingual view (contracts defined)
4. **No new Frontier team** — portfolio v7 confirmed, all teams terminated (true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria)

---

*Verification complete. Snapshot audit-ready for GitHub run 37509635487.*