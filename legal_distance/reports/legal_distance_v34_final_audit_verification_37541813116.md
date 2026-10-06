# Legal Distance v34 — Final Audit Verification (GitHub Run 37541813116)

**Factory Direction v34 | Legal-Distance Lane | 2026-10-06**

---

## Verification Summary

**Status**: ✅ **FINAL_AUDIT_VERIFICATION_COMPLETE**

All 8/8 `test_complementary_role_v34.py` assertions **PASSED**. Scale characterization experiment (`characterize_dense_complementary_views.py`) reproduced on 12k ACCEPTED dense embeddings.

---

## Key Findings Reproduced

| Finding | Evidence | Status |
|---------|----------|--------|
| **Citation Heritage**: Dense AUC > 0.75 at 21-24yr (cp64: 0.7667-0.8182) | `citation_heritage_22year_latest.json`, `citation_heritage_21year_latest.json`, `citation_heritage_24year_latest.json` | ✅ |
| **Minimal Scale**: 21yr/137k with 100+ positive pairs | 21yr raw AUC 0.8455, cp64 0.8182 | ✅ |
| **Cross-lingual Hierarchy**: Sachverhalt 0.282 > 0.2, Dispositiv 0.150 > 0.1, Erwaegungen 0.094 < 0.1 | `section_crosslingual_eval_latest.json` | ✅ |
| **Linear Hybrid**: PASS adversarial at w=0.3-0.4, JP 0.61-0.67 < TF-IDF 0.78-0.79 | `weight_sweep_22year_latest.json` | ✅ |
| **Two-Mode Tradeoff**: Fundamental, no single representation dominates | 22yr evaluation + weight sweep | ✅ |
| **True OOS Ceiling**: ~0.53 < 0.7 factory target | `v8/holdout_zero_shot_validation_fixed.json` | ✅ |
| **TF-IDF 174k Primary**: LangDom=0.5785 PASS, beats semantic baseline | `/tmp/lex_accepted/evaluation/v25_174k_formal_suite` | ✅ |
| **Data Blockers**: 2000-2023 complete, 2024-2026 missing | `progress.json` checkpoints | ✅ |

---

## Test Results (Run 37541813116)

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

## Characterization Complete (No Further Cycles)

The **NEW factory direction v34 question** has been answered:

> **"What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?"**

### Answer

| Complementary View | Minimal Scale | Dense Mode | Acceptance Criterion | Status |
|---|---|---|---|---|
| **Citation Heritage Recovery** | 21yr/137k (2000-2020) | `center_projected_64dim` | AUC > 0.75 | ✅ **PASSED** at 21-24yr |
| **Section Cross-Lingual (Sachverhalt)** | 1K sample (n=359) | Section-specific `cp_64` | cross_lang_same_branch > 0.2 | ✅ **PASSED** (0.282) |
| **Section Cross-Lingual (Dispositiv)** | 1K sample (n=538) | Section-specific `cp_64` | cross_lang_same_branch > 0.1 | ✅ **PASSED** (0.150) |
| **Section Cross-Lingual (Erwaegungen)** | 1K sample (n=510) | Section-specific `cp_64` | cross_lang_same_branch > 0.1 | ❌ **FAILED** (0.094) |
| **Linear Hybrid Complement** | 19yr/122k (2000-2018) | `linear_citation_concat` w=0.3-0.4 | PASS adversarial + cross-lang improvement | ✅ **PASSED** at 19yr+ |

**Two-mode tradeoff is fundamental**: No single representation dominates jurist preference, language dominance, AND citation independence simultaneously.

- **TF-IDF citation hybrids** = PRIMARY product mode (jurist preference ~0.78, branch clustering)
- **Dense embeddings** = COMPLEMENTARY modes (citation heritage, cross-lingual, hybrid complement)

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Resolution Owner |
|---------|--------|------------------|
| **BGE/bger ID mapping** | Cannot align evaluation corpus with canonical corpus | Corpus lane |
| **Parquet 2024-2026** | 15,536 decisions missing from 174k target | Corpus lane |
| **Section extraction at 174k** | Cross-lingual section evaluation blocked at full corpus density | Corpus lane |

**Note**: 2022-2023 embeddings EXIST and PASS citation heritage quality check (AUC > 0.75). Only 2024-2026 are genuinely missing.

---

## Lane State

- **Cycle Status**: BLOCKED_ON_DEPENDENCIES
- **Continue Recommended**: FALSE (no further same-question cycles justified)
- **Evidence Tier**: ACCEPTED
- **Audit Ready**: TRUE

---

## Next Actions (Dependent on Corpus Lane)

1. **Corpus lane resumption**: BGE/bger mapping + 2024-2026 parquet + 174k section extraction
2. **When unblocked**: Compute 174k dense embeddings for all three complementary views
3. **Evaluation lane**: Freeze TF-IDF 174k as production baseline; apply acceptance criteria for dense view promotion
4. **Product lane**: Ship v1.0 with TF-IDF primary; dense complementary views as v1.1+ milestones

---

*Verification completed for GitHub run 37541813116. Operational resume from run 37529695342 verified complete.*