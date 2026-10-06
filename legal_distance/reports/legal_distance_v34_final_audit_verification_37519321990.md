# Legal Distance v34: Final Audit Verification — GitHub Run 37519321990

**Factory Direction v34 | Legal-Distance Lane | ACCEPTED Evidence Tier**

---

## Summary

This run completes the **operational resume from persisted producer snapshot of run 37517956960** and performs **final audit verification** for GitHub run 37519321990.

**Status**: ✅ **ALL TESTS PASSED — Snapshot Audit-Ready**

---

## What Was Verified

### 1. Test Suite: `test_complementary_role_v34.py` — 8/8 PASSED

| Test | Result | Key Evidence |
|---|---|---|
| `test_citation_heritage_superiority` | ✅ | Dense AUCs 0.79-0.85 > 0.75; cp64 gap 6.5× raw |
| `test_citation_heritage_minimal_scale` | ✅ | 21yr/137k: 100 pairs, AUC 0.8455/0.8182 > 0.75 |
| `test_section_crosslingual_hierarchy` | ✅ | Sachverhalt 0.282 > 0.2, Dispositiv 0.150 > 0.1, Erwaegungen 0.094 < 0.1 |
| `test_linear_hybrid_optimal_weight` | ✅ | w=0.3-0.4 PASS adversarial; JP 0.61-0.67 < TF-IDF 0.78 |
| `test_two_mode_tradeoff_fundamental` | ✅ | No single representation dominates JP+LangDom+CiteIndep |
| `test_true_oos_ceiling` | ✅ | v8 holdout: ~0.53 < 0.7 factory target |
| `test_tfidf_174k_primary_validated` | ✅ | LangDom=0.5785 PASS; beats semantic baseline |
| `test_data_blockers_identified` | ✅ | 2024-2026 missing; 2021-2023 exist & pass quality |

### 2. Scale Characterization Experiment — Reproduced on 12k ACCEPTED Embeddings

The `characterize_dense_complementary_views.py` experiment on 12k ACCEPTED dense embeddings (2000-2002) confirms scale curves consistent with full-corpus evaluations at 19yr-24yr.

### 3. Evidence Files — All Accessible and Consistent

- **Citation Heritage** (21yr, 22yr, 24yr): `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/`
- **Section Cross-Lingual** (1K sample): `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/`
- **Linear Hybrid Weight Sweep** (22yr): `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/`
- **v8 Holdout OOS**: `legal_distance/results/v8/holdout_zero_shot_validation_fixed/`
- **TF-IDF 174k Formal Suite**: `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/`
- **Scale Characterization**: `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json`
- **Progress Checkpoint**: `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json` (24 completed years, 3 failed)

---

## Answer to Factory Direction v34 Question

> **"What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?"**

### ✅ ANSWERED — Three Complementary Modes at Characterized Minimal Scales

| Complementary View | Minimal Scale | Dense Mode | Acceptance Criterion | Status |
|---|---|---|---|---|
| **Citation Heritage Recovery** | 21yr / 137k (2000-2020) | `center_projected_64dim` | AUC > 0.75 on frozen citation pair pool | ✅ **PASSED** at 21-24yr (137k-158k) |
| **Section Cross-Lingual Alignment** | 1K sample with sections (359 Sachverhalt, 538 Dispositiv, 510 Erwaegungen) | Section-specific `center_projected_64dim` | Sachverhalt `cross_lang_same_branch` > 0.2; Dispositiv > 0.1 | ✅ **PASSED** at sample scale; **BLOCKED** at full corpus |
| **Linear Hybrid Complement** | 19yr / 122k (2000-2018) | `linear_citation_concat` / `linear_hybrid05_concat` at w=0.3-0.4 | PASS both adversarial gates | ✅ **PASSED** at 19yr+; **NOT primary** (JP < TF-IDF baseline) |

### ❗ Critical Data Blockers (Require Corpus Lane Resumption)

1. **BGE/bger ID mapping** — Cannot align published (BGE) and unpublished (bger) decision IDs
2. **Parquet 2024-2026** — 15,536 decisions missing embeddings
3. **Section extraction at 174k** — No Sachverhalt/Erwaegungen/Dispositiv at scale for cross-lingual view

**Note**: 2022-2023 embeddings **EXIST and PASS** citation heritage quality check (AUC > 0.75 at 24yr/158k with 730 positive pairs). Only 2024-2026 are genuinely missing.

---

## Product Integration Contracts (Frozen)

| View | Representation | Status | User Intent |
|---|---|---|---|
| **Primary Navigation** | `cited_outcome_hybrid_0.5` (TF-IDF) | **PRODUCTION v1.0** | Jurist finds legally relevant neighbors |
| **Citation Heritage** | `center_projected_64dim` | **READY v1.1+** | Jurist explores doctrinal lineage via shared citations |
| **Cross-Lingual** | `center_projected_64dim` per section | **BLOCKED v1.1+** | Jurist finds equivalent decisions in other languages |
| **Hybrid Explore** | `linear_citation_concat_w0.4` / `linear_hybrid05_concat_w0.3` | **EXPLORATORY v1.1+** | Jurist trades some legal relevance for cross-lingual reach |

---

## Accepted Negative Findings (First-Class Evidence)

- Dense embeddings FAIL jurist gate at ALL scales (JP 0.05-0.43)
- True OOS JuristPref ceiling ~0.53 < 0.7 factory target
- v18 coarse hierarchy max purity 0.65 < 0.7 threshold
- Citation heritage recall@10 max 0.0066 (ranking signal only, not retrieval)
- Raw 768dim FAILS citation heritage at 24yr (AUC 0.68); center projection required
- Full-text dense cross-lingual inflated at small scale (0.656 at 1K → 0.10 at 165k)

---

## Recommendation

**`continue_recommended = false`** — No further same-question cycles justified.

The complementary role characterization is **complete at maximum available evaluated scale** (24yr/158k citation heritage, 165k formal suite, 1K section cross-lingual).

### Next Actions (Dependent on Corpus Lane)

1. **Corpus lane**: Resume for bge_↔bger_ mapping, 2024-2026 parquet, section extraction at 174k
2. **Product lane**: Ship v1.0 with TF-IDF citation hybrids as primary (JP 0.78 vs 0.43 semantic baseline)
3. **Dense integration**: v1.1+ for citation-heritage view and cross-lingual view (contracts defined and frozen)
4. **No new Frontier team** — portfolio v7 confirmed, all teams TERMINATED (true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria)

---

## State Updates

- `state/legal-distance.json`: Updated `current_run=37519321990`, `final_verification_run=37519321990`, `audit_timestamp=2026-10-06T19:30:00Z`
- `legal_distance/legal-distance.json`: Updated `current_run=37519321990`, added verification run entry
- All evidence preserved; no overwrites of historical results

---

## Verification

```
✅ Citation Heritage: Dense AUCs > 0.75, cp64 gap 6.5× raw
✅ Minimal Scale: 21yr (137k) n_pairs=100, AUC > 0.75
✅ Cross-lingual Hierarchy: Sachverhalt > Dispositiv > Erwaegungen
✅ Linear Hybrid: PASS adversarial at w=0.3-0.4, JP < TF-IDF baseline
✅ Two-Mode Tradeoff: Fundamental, no single representation dominates
✅ True OOS Ceiling: ~0.53 < 0.7 factory target
✅ TF-IDF 174k Primary: LangDom=0.5785 PASS, beats semantic baseline
✅ Data Blockers: 2000-2023 complete, 2024-2026 missing
```

**Report Status**: FINAL — Complementary role characterization complete. Awaiting corpus lane unblocking for 174k deployment.