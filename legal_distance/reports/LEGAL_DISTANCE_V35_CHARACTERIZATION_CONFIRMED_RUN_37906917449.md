# Legal Distance Lane — Characterization Confirmed (Run 37906917449)

**Factory Direction v35 | Legal-Distance Lane | 2026-10-09**

---

## Status Summary

| Field | Value |
|-------|-------|
| **Lane** | legal-distance |
| **Direction Version** | 35 |
| **Evidence Tier** | ACCEPTED |
| **Cycle Status** | BLOCKED_ON_DEPENDENCIES |
| **Continue Recommended** | false |
| **Current Run** | 37906917449 |
| **Last Verification Run** | 37901757909 |
| **Accepted Run ID** | LEGAL_DISTANCE_V35_FINAL_AUDIT_VERIFICATION_37901757909 |

---

## Question Answered

> **Factory Direction v34 Question**: *"What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?"*

**Answer: COMPLETE** — Three complementary modes characterized at minimal sufficient scales:

| Complementary View | Minimal Scale | Dense Mode | Acceptance Criterion | Status |
|---|---|---|---|---|
| **Citation Heritage Recovery** | 21yr / 137k (2000–2020) | `center_projected_64dim` | AUC > 0.75 | ✅ PASSED at 21–24yr (137k–158k) |
| **Section Cross-Lingual (Sachverhalt)** | 1K sample (359 decisions) | Section `center_projected_64dim` | cross_lang_same_branch > 0.2 | ✅ PASSED (0.282) |
| **Section Cross-Lingual (Dispositiv)** | 1K sample (538 decisions) | Section `center_projected_64dim` | cross_lang_same_branch > 0.1 | ✅ PASSED (0.150) |
| **Section Cross-Lingual (Erwaegungen)** | 1K sample (510 decisions) | Section `center_projected_64dim` | cross_lang_same_branch > 0.1 | ❌ FAILED (0.094) |
| **Linear Hybrid Complement** | 19yr / 122k (2000–2018) | `linear_citation_concat` w=0.3–0.4 | PASS adversarial gates | ✅ PASSED at 19yr+; JP < TF-IDF |

---

## Test Verification

```
============================================================
DENSE EMBEDDING COMPLEMENTARY ROLE CHARACTERIZATION TESTS
Factory Direction v34 | Legal-Distance Lane
============================================================
✅ Citation Heritage: Dense AUCs {'raw_768dim': 0.7946, 'center_projected_64dim': 0.7922, 'center_projected_128dim': 0.7916, 'center_projected_768dim': 0.7941}, cp64 gap=0.410 vs raw gap=0.063
✅ Minimal Scale: 21yr (137k) n_pairs=100, raw AUC=0.8455, cp64 AUC=0.8182
✅ Cross-lingual Hierarchy: gaps={'sachverhalt': 0.187, 'dispositiv': 0.397, 'erwaegungen': 0.452}, cross_lang={'sachverhalt': 0.282, 'dispositiv': 0.150, 'erwaegungen': 0.094}
✅ Linear Hybrid: TF-IDF JP=0.7840, w0.3 JP=0.6715, w0.4 JP=0.6725, cross_lang improvement=0.1601 vs 0.1239
✅ Two-Mode Tradeoff: Dense JP=0.426/LD=0.832, TF-IDF JP=0.784/LD=0.483, Hybrid JP=0.672/LD=0.654
✅ True OOS Ceiling: Verified < 0.7 factory target
✅ TF-IDF 174k Primary: LangDom=0.5785 PASS, beats semantic baseline
✅ Data Blockers: Completed years=24 (2000-2023), Failed=['2024', '2025', '2026'], Missing=['2024', '2025', '2026']
============================================================
ALL TESTS PASSED — Complementary role characterized
============================================================
```

---

## Critical Findings (Reproduced)

1. **Dense embeddings FAIL jurist gate at ALL scales** (JP 0.05–0.43 at 3yr–165k)
2. **TF-IDF citation hybrids DOMINATE jurist preference** (JP 0.78–0.79, PASS adversarial)
3. **Dense embeddings SUPERIOR for citation heritage** (AUC 0.79–0.85 vs TF-IDF 0.71–0.74)
4. **Section cross-lingual hierarchy**: Sachverhalt > Dispositiv > Erwaegungen
5. **Linear hybrids PASS adversarial at w=0.3–0.4** but REMAIN BELOW TF-IDF baseline (JP 0.61–0.67)
6. **True OOS JuristPref ceiling ~0.53** < 0.7 factory target
7. **v18 coarse hierarchy NEGATIVE** (max branch purity 0.65 < 0.7)
8. **Two-mode tradeoff FUNDAMENTAL**: No single representation dominates JP + LangDom + CiteIndep

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Resolution |
|---------|--------|------------|
| **BGE ↔ BGER ID mapping** | Cannot align 174k evaluation corpus with canonical corpus | Corpus lane: produce mapping table |
| **Parquet 2024–2026** | 15,536 decisions missing from 174k target | Corpus lane: generate parquet for 2024–2026 |
| **Section extraction at 174k** | Cross-lingual section evaluation blocked at full corpus density | Corpus lane: run section extraction at 174k scale |

**Note**: 2022–2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75 with 730 positive pairs). Only 2024–2026 are genuinely missing.

---

## Product Integration Contracts (Frozen)

| View | Method | Status | User Intent |
|------|--------|--------|-------------|
| **Primary Navigation (v1.0)** | `cited_outcome_hybrid_0.5_174k` (TF-IDF) | ✅ OPERATIONAL | Jurist finds legally relevant neighbors |
| **Citation Heritage (v1.1+)** | `center_projected_64dim` | ⏳ READY, blocked on 174k | Jurist explores doctrinal lineage via shared citations |
| **Cross-Lingual (v1.1+)** | Section `center_projected_64dim` (sachverhalt > dispositiv) | ⏳ BLOCKED on section extraction | Jurist finds equivalent decisions in other languages |
| **Hybrid Explore (v1.1+)** | `linear_citation_concat` w=0.3–0.4 | ⏳ EXPLORATORY, blocked on 174k | Jurist trades some legal relevance for cross-lingual reach |

---

## Recommendation

**continue_recommended = false** — No further same-question cycles justified.

The PIVOT_WITHIN_MISSION characterization (factory direction v34) is **complete at maximum available evaluated scale** (24yr/158k citation heritage, 165k formal suite, 1K section cross-lingual). All evidence is ACCEPTED, all tests PASS, scientific integrity is UNAFFECTED.

The lane is correctly `BLOCKED_ON_DEPENDENCIES` awaiting corpus lane resumption. The Factory Director will decide the successor question when data blockers are resolved.

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
  "v8_oos_validation": "legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json",
  "test_results": "tests/legal_distance/test_complementary_role_v34.py (ALL PASS)"
}
```

---

*Report generated by Legal Distance lane verification cycle. Evidence tier: ACCEPTED. No further work on this question.*