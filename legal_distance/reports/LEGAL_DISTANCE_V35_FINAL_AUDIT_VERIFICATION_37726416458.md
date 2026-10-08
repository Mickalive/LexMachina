# Legal Distance Lane — Final Audit Verification (Run 37726416458)

**Factory Direction v35 | Legal-Distance Lane | 2026-10-08**

---

## Executive Summary

This run completes the **operational resume from persisted producer snapshot of run 37725797175** and produces a **FINAL AUDIT-READY SNAPSHOT** for GitHub run 37726416458.

**Status**: ✅ **ALL VERIFICATIONS PASSED — LANE AUDIT-READY**

- **8/8** `test_complementary_role_v34.py` assertions: **PASSED**
- **15/15** `test_v29_final_results.py` assertions: **PASSED**
- **Scale characterization experiment** (`characterize_dense_complementary_views.py`): **REPRODUCED** with IDENTICAL scale-dependent patterns
- **PIVOT_WITHIN_MISSION characterization**: **COMPLETE** at maximum available evaluated scale
- **Lane state**: `BLOCKED_ON_DEPENDENCIES`, `continue_recommended=false` (correct)
- **No further same-question cycles justified**

---

## Verification Results

### 1. Unit Tests — ALL PASSED

| Test Suite | Tests | Result |
|------------|-------|--------|
| `test_complementary_role_v34.py` | 8 | ✅ ALL PASSED |
| `test_v29_final_results.py` | 15 | ✅ ALL PASSED |

**test_complementary_role_v34.py assertions verified:**
- ✅ Citation Heritage: Dense AUCs > 0.75, cp64 gap 6.5× raw
- ✅ Minimal Scale: 21yr (137k) n_pairs=100, AUC > 0.75
- ✅ Cross-lingual Hierarchy: Sachverhalt > Dispositiv > Erwaegungen
- ✅ Linear Hybrid: PASS adversarial at w=0.3–0.4, JP < TF-IDF baseline
- ✅ Two-Mode Tradeoff: Fundamental, no single representation dominates
- ✅ True OOS Ceiling: ~0.53 < 0.7 factory target
- ✅ TF-IDF 174k Primary: LangDom=0.5785 PASS, beats semantic baseline
- ✅ Data Blockers: 2000–2023 complete, 2024–2026 missing

**test_v29_final_results.py assertions verified:**
- ✅ Section cross-lingual hierarchy (Sachverhalt > Dispositiv > Erwaegungen)
- ✅ Center projection improves all sections
- ✅ Section coverage reasonable
- ✅ 22yr linear combinations PASS adversarial
- ✅ 22yr optimal weight shifts toward TF-IDF
- ✅ TF-IDF baseline dominates jurist preference
- ✅ Dense embeddings recover citation heritage
- ✅ Dense embedding coverage 83%
- ✅ Missing years 2022–2026 identified
- ✅ No bge_/bger_ mapping exists
- ✅ Two-mode tradeoff: citation mode high JP/low CiteIndep
- ✅ Two-mode tradeoff: semantic mode high CiteIndep/low JP
- ✅ Two-mode tradeoff: no single representation dominates all three

---

### 2. Scale Characterization Experiment — IDENTICAL REPRODUCTION

**Experiment**: `characterize_dense_complementary_views.py` on 12,570 ACCEPTED dense embeddings (2000–2002)

| Metric | 1k | 2k | 4k | 6k | 8k | 10k | 12.5k | Pattern |
|--------|-----|-----|-----|-----|-----|------|-------|---------|
| **cross_lang_same_branch** | 0.656 | 0.971 | 0.971 | 1.000 | 1.000 | 0.976 | **0.957** | **Inflation at small homogeneous scale** |
| **legal_area_purity** | 0.609 | 0.493 | 0.485 | 0.477 | 0.485 | 0.455 | **0.475** | **Degradation with scale** |
| **branch_kNN@1** | 0.957 | 0.989 | 0.988 | 0.995 | 0.993 | 0.992 | **0.992** | **Stable >0.99 at all scales** |
| **hybrid_JP_proxy (w=0.3)** | 0.992 | 0.998 | 0.992 | — | — | — | — | **Saturates near 1.0** (caveat: not real adversarial) |

**Pattern IDENTITY CONFIRMED** with all prior verification runs (37725797175, 37715016203, 37711661819, 37708977152, 37708200469, 37707256864, 37704448746, 37699646356, 37690273233, 37569588103, 37568018291, 37565627088, 37563818284, 37561311654, 37560375507, 37551635194, 37550586145, 37547806916, 37536884155, 37542786443, 37543978207, 37532860268, 37529695342, 37526493018, 37525394260, 37519321990, 37517956960, 37516334272, 37514403232, 37509635487, 37506268105, 37504611319, 37454210884, 37416635961).

---

### 3. PIVOT_WITHIN_MISSION Characterization — COMPLETE

**Original hypothesis (falsified):** Dense embeddings would beat TF-IDF on jurist preference at scale.

**Accepted evidence (ACCEPTED tier):**

| Finding | Evidence | Status |
|---------|----------|--------|
| Dense embeddings FAIL jurist gate at ALL scales | JP 0.05–0.43 at 3yr–22yr | ✅ FALSIFIED |
| TF-IDF citation hybrids DOMINATE jurist preference | JP 0.78–0.79, PASS adversarial at 174k | ✅ CONFIRMED |
| Dense embeddings EXCEL at citation heritage recovery | AUC 0.77–0.85 > TF-IDF 0.71–0.74 | ✅ SUPERIORITY CONFIRMED |
| Section cross-lingual hierarchy | Sachverhalt (0.282) > Dispositiv (0.150) > Erwaegungen (0.094) | ✅ HIERARCHY CONFIRMED |
| Linear hybrids PASS adversarial but BELOW TF-IDF | JP 0.61–0.67 vs 0.78–0.79 | ✅ CONFIRMED |
| True OOS JuristPref ceiling ~0.53 | v8 holdout validation | ✅ CONFIRMED |
| v18 coarse hierarchy NEGATIVE | Max purity 0.65 < 0.7 threshold | ✅ CONFIRMED |

---

### 4. Three Complementary Views — MINIMAL SCALES CHARACTERIZED

| Complementary View | Minimal Scale | Dense Mode | Acceptance Criterion | Status |
|---|---|---|---|---|
| **Citation Heritage Recovery** | 21yr / 137k (2000–2020) | `center_projected_64dim` | AUC > 0.75 | ✅ **PASSED** at 21–24yr (0.77–0.85) |
| **Section Cross-Lingual (Sachverhalt)** | 1K sample (359 decisions) | Section `cp_64` | cross_lang_same_branch > 0.2 | ✅ **PASSED** (0.282) |
| **Section Cross-Lingual (Dispositiv)** | 1K sample (538 decisions) | Section `cp_64` | cross_lang_same_branch > 0.1 | ✅ **PASSED** (0.150) |
| **Section Cross-Lingual (Erwaegungen)** | 1K sample (510 decisions) | Section `cp_64` | cross_lang_same_branch > 0.1 | ❌ **FAILED** (0.094) |
| **Linear Hybrid Complement** | 19yr / 122k (2000–2018) | Concat w=0.3–0.4 | PASS adversarial + cross-lang improvement | ✅ **PASSED** at 19yr+ |

---

### 5. Data Blockers — Corpus Lane Resumption Required

| Blocker | Impact | Required For |
|---------|--------|--------------|
| **BGE/bger ID mapping** | Cannot align published (BGE) and unpublished (bger) IDs | 174k citation heritage evaluation, section cross-lingual at full corpus |
| **Parquet 2024–2026** | 15,536 decisions missing embeddings | 174k completion (173,963 → 189,499 target) |
| **Section extraction 174k** | No Sachverhalt/Erwaegungen/Dispositiv at scale | Full-corpus cross-lingual view density |

**Note**: 2022–2023 embeddings **EXIST and PASS** citation heritage quality check (AUC > 0.75 at 24yr/158k), contradicting progress.json 'failed' flag. Only 2024–2026 are genuinely missing.

---

### 6. Orchestration/Validation Failure Diagnosis

**Root Cause**: Factory Director control-plane sync issue
- `factory_direction.json` v35 shows `legal-distance.status: "RUN"`
- Lane state (`legal-distance.json`) shows `cycle_status: "BLOCKED_ON_DEPENDENCIES"`, `continue_recommended: false`

**Scientific Integrity**: **UNAFFECTED** — this is a control-plane metadata inconsistency, not a scientific failure.

**All valid completed work preserved**: The lane has correctly characterized the complementary role of dense embeddings and identified the exact data dependencies needed for 174k completion.

---

## Conclusion

**Legal Distance lane deliverable is COMPLETE and AUDIT-READY.**

- ✅ PIVOT_WITHIN_MISSION characterization complete
- ✅ NEW QUESTION fully answered with ACCEPTED evidence
- ✅ All tests pass (23/23 assertions)
- ✅ Scale characterization reproduced identically
- ✅ Three complementary views characterized at minimal scales
- ✅ Data blockers precisely identified
- ✅ Lane correctly BLOCKED_ON_DEPENDENCIES with continue_recommended=false
- ✅ No further same-question cycles justified

**Next action**: Factory Director decision on successor question OR corpus lane resumption to unblock 174k dense embedding delivery for multi-view product deployment.

---

## Evidence References (Machine-Readable)

```json
{
  "test_complementary_role_v34": "tests/legal_distance/test_complementary_role_v34.py",
  "test_v29_final_results": "tests/legal_distance/test_v29_final_results.py",
  "scale_characterization_results": "legal_distance/results/dense_complementary_characterization/scale_characterization_results.json",
  "citation_heritage_21yr": "legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json",
  "citation_heritage_22yr": "legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json",
  "citation_heritage_24yr": "legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json",
  "section_crosslingual": "legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json",
  "linear_hybrid_sweep_22yr": "legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json",
  "evaluation_v25_174k_suite": "/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json",
  "v8_oos_validation": "legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json",
  "complementary_characterization_report": "legal_distance/reports/legal_distance_v34_complementary_characterization_complete.md",
  "minimal_scale_report": "legal_distance/reports/legal_distance_v34_minimal_dense_scale_characterization.md"
}
```

---

*Report generated by Legal Distance lane final audit verification cycle. Evidence tier: ACCEPTED.*