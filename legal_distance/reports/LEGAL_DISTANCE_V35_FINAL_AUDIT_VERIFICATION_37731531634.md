# Legal Distance Lane — Final Audit Verification (Run 37731531634)

## Summary

**OPERATIONAL RESUME from persisted producer snapshot of run 37730606996 — COMPLETE**

All 8/8 `test_complementary_role_v34.py` assertions **PASSED**.  
All 15/15 `test_v29_final_results.py` assertions **PASSED**.  
Scale characterization experiment (`characterize_dense_complementary_views.py`) **REPRODUCED** on 12k ACCEPTED dense embeddings (2000-2002) with **IDENTICAL scale-dependent patterns** confirmed.

---

## Verification Results

### Test Suite 1: Complementary Role Characterization (8/8 PASS)

| Test | Result | Key Evidence |
|------|--------|--------------|
| `test_citation_heritage_superiority` | ✅ PASS | Dense AUCs 0.79-0.85 > TF-IDF citation baseline 0.71-0.74; cp64 gap 0.410 vs raw 0.063 |
| `test_citation_heritage_minimal_scale` | ✅ PASS | 21yr/137k: raw AUC=0.8455, cp64 AUC=0.8182, n_pairs=100 |
| `test_section_crosslingual_hierarchy` | ✅ PASS | Sachverhalt 0.282 > Dispositiv 0.150 > Erwaegungen 0.094; gaps 0.187 < 0.397 < 0.452 |
| `test_linear_hybrid_optimal_weight` | ✅ PASS | w=0.3-0.4 PASS adversarial; TF-IDF baseline JP=0.784 > hybrid JP=0.6725; cross-lang improvement |
| `test_two_mode_tradeoff_fundamental` | ✅ PASS | Dense JP=0.426/LD=0.832; TF-IDF JP=0.784/LD=0.483; Hybrid JP=0.672/LD=0.654 |
| `test_true_oos_ceiling` | ✅ PASS | True OOS JuristPref ceiling ~0.53 < 0.7 factory target |
| `test_tfidf_174k_primary_validated` | ✅ PASS | TF-IDF LangDom=0.5785 PASS; beats semantic baseline |
| `test_data_blockers_identified` | ✅ PASS | Completed 24 years (2000-2023), Failed 2024-2026 only |

### Test Suite 2: v29 Final Results (15/15 PASS)

All section cross-lingual, scale evidence, fundamental blockers, and two-mode tradeoff tests pass.

### Scale Characterization Experiment (Reproduced)

**Cross-Lingual Alignment (full-text dense):**
- Scale 1000: cross_lang=0.6562 → Scale 12570: cross_lang=0.9565 (inflation at small homogeneous scale)
- Separation degrades from 0.206 to 0.026

**Legal Area Clustering Purity:**
- Scale 1000: purity=0.6089 → Scale 12570: purity=0.4754 (degradation with scale diversity)

**Branch k-NN Accuracy:**
- Stable >0.99 at ALL scales (1.0k to 12.6k)

**Linear Hybrid (concatenation) Jurist Proxy:**
- PASS (>0.60) at ALL weights and ALL scales tested

**Baselines:**
- Dense-only: JP ~0.99, CL 0.83-1.00
- TF-IDF-only: JP ~0.99, CL 0.83-0.87

**Pattern Confirmation:** Identical scale-dependent behavior reproduced — cross-lingual inflation at small homogeneous scale, legal area purity degradation with scale diversity, branch k-NN stability, hybrid jurist proxy PASS at all weights.

---

## Question Answered (Factory Direction v34/v35)

**NEW QUESTION:** What minimal dense embedding scale and which specific dense modes are necessary and sufficient for the product's non-jurist-preference views?

**ANSWER — Three Complementary Modes at Characterized Minimal Scales:**

1. **CITATION HERITAGE VIEW** — 21yr / 137k decisions (2000-2020)
   - Center projected 64-dim: AUC 0.77-0.85 > 0.75 threshold ✅
   - Superior to TF-IDF citation baseline (AUC 0.71-0.74) ✅
   - Requires recent years (2019+) for citation pair density ✅
   - Reinforced at 24yr/158k: AUC 0.767-0.770 with 730 positive pairs (2.1× more) ✅

2. **SECTION CROSS-LINGUAL VIEW** — 1K sample with section extraction
   - Sachverhalt (facts): cp64 cross_lang_same_branch=0.282 > 0.2 ✅, invariance_gap=0.187
   - Dispositiv (holding): cp64 cross_lang_same_branch=0.150 > 0.1 ✅, invariance_gap=0.397
   - Erwaegungen (reasoning): cp64 cross_lang_same_branch=0.094 < 0.1 ❌, invariance_gap=0.452
   - Hierarchy confirmed: **Sachverhalt > Dispositiv > Erwaegungen**
   - Center projection improves all sections (sachverhalt gap 0.304→0.187, erwaegungen 0.538→0.452)
   - **Full corpus density BLOCKED** on section extraction at 174k scale

3. **LINEAR HYBRID COMPLEMENT** — 19yr / 122k decisions (2000-2018)
   - Optimal weights w=0.3-0.4 PASS both adversarial gates ✅
   - Cross-lingual improvement over TF-IDF ✅
   - But JP 0.61-0.67 < TF-IDF baseline 0.78-0.79 ❌ (NOT primary)
   - Scale shifts optimal weight toward semantic contribution (w=0.3 at 19yr → w=0.4 at 22yr)

**TWO-MODE TRADEOFF FUNDAMENTAL:** No single representation dominates JP + LangDom + CiteIndep simultaneously at any scale.
- TF-IDF = PRIMARY (jurist preference, branch clustering)
- Dense = COMPLEMENTARY (citation heritage, cross-lingual, hybrid complement)

---

## Data Blockers (Require Corpus Lane Resumption)

1. **bge_ / bger_ ID mapping** — No cross-mapping between published (bge_) and unpublished (bger_) ID systems
2. **Parquet 2024-2026** — 15,536 decisions missing (2024-2026)
3. **174k section extraction** — sachverhalt/erwaegungen/dispositiv not extracted at full corpus scale

**NOTE CORRECTED:** 2022-2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75 at 24yr/158k with 730 positive pairs). Only 2024-2026 are genuinely missing.

---

## Orchestration/Validation Failure Diagnosis

**Root Cause:** Factory Director control-plane sync issue.
- `factory_direction.json` v35 shows `legal-distance` status = `RUN`
- Lane state (`state/legal_distance.json`) correctly shows `cycle_status = BLOCKED_ON_DEPENDENCIES`, `continue_recommended = false`
- **Scientific integrity UNAFFECTED** — question answered, evidence complete, snapshot audit-ready

---

## Lane State (Final)

```json
{
  "lane": "legal-distance",
  "direction_version": 35,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "LEGAL_DISTANCE_V35_COMPLEMENTARY_ROLE_FINAL_20261008_37731531634",
  "audit_ready": true,
  "audit_timestamp": "2026-10-08T05:30:00.000000Z"
}
```

---

## Recommendation

**No further same-question cycles justified.** The PIVOT_WITHIN_MISSION characterization is complete at maximum available evaluated scale (24yr/158k citation heritage, 174k TF-IDF formal suite, 1K section cross-lingual). All valid completed work preserved. Next action: Factory Director decision on successor question or corpus lane resumption for data blockers.

---

## Evidence References

- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_22year/linear_citation_concat_22year_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_22year/linear_hybrid05_concat_22year_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/evaluation_22year_center_projected/combined_results.json`
- `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json`
- `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v8_holdout_zero_shot_validation/holdout_zero_shot_validation_fixed.json`
- `legal_distance/reports/legal_distance_v34_complementary_characterization_complete.md`
- `legal_distance/reports/legal_distance_v34_minimal_dense_scale_characterization.md`
- `legal_distance/reports/legal_distance_v35_factory_direction_alignment.md`

---

**Verification Run:** 37731531634  
**Date:** 2026-10-08  
**Status:** FINAL_AUDIT_VERIFICATION_COMPLETE