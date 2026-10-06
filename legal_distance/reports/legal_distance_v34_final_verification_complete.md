# Legal Distance v34: Final Verification Complete

**Factory Direction v34 | Legal-Distance Lane | ACCEPTED Evidence Tier**

---

## Summary

The factory direction v34 question has been **fully answered and verified**:

> **"What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?"**

**Answer**: Three specific dense embedding modes at characterized minimal scales:

| Complementary View | Minimal Scale | Dense Mode | Acceptance Criterion | Status |
|---|---|---|---|---|
| **Citation Heritage Recovery** | 21 years / 137k decisions (2000–2020) | `center_projected_64dim` | AUC > 0.75 | ✅ **PASSED** at 21–24yr (137k–158k) |
| **Section Cross-Lingual Alignment** | 1K sample with sections | Section-specific `center_projected_64dim` | Sachverhalt > 0.2; Dispositiv > 0.1 | ✅ **PASSED** at sample; **BLOCKED** full corpus |
| **Linear Hybrid Complement** | 19 years / 122k decisions (2000–2018) | `linear_citation_concat` / `linear_hybrid05_concat` at w=0.3–0.4 | PASS both adversarial gates | ✅ **PASSED** at 19yr+; **NOT primary** |

---

## Verification Evidence

### 1. Citation Heritage — Verified at Maximum Scale (24yr / 158k)

| Variant | AUC-ROC | Status | Positive Pairs |
|---|---|---|---|
| `center_projected_64dim` | 0.7667 | ✅ PASSED | 730 |
| `center_projected_128dim` | 0.7669 | ✅ PASSED | 730 |
| `center_projected_768dim` | 0.7696 | ✅ PASSED | 730 |

- **Minimal sufficient scale**: 21yr / 137k (100 positive pairs, AUC 0.8182 cp64)
- **Density driver**: Citation pair density requires recent years (2019+)
- **Superiority over TF-IDF**: Dense 0.77–0.85 vs TF-IDF citation 0.71–0.74 vs TF-IDF text 0.50–0.63
- **Center projection effect**: 6.5× similarity gap improvement (raw gap=0.063 → cp64 gap=0.383)

### 2. Section Cross-Lingual — Verified at Sample Scale (1K)

| Section | n | cp64 `cross_lang_same_branch` | cp64 `invariance_gap` | Threshold | Status |
|---|---|---|---|---|---|
| Sachverhalt (Facts) | 359 | **0.282** | 0.187 | > 0.2 | ✅ |
| Dispositiv (Holding) | 538 | **0.150** | 0.397 | > 0.1 | ✅ |
| Erwaegungen (Reasoning) | 510 | 0.094 | 0.452 | > 0.1 | ❌ |

- **Hierarchy confirmed**: Sachverhalt > Dispositiv > Erwaegungen
- **Center projection improvement**: 16–38% gap reduction across sections
- **Full corpus BLOCKED**: Section extraction at 174k scale not yet run (corpus lane dependency)

### 3. Linear Hybrid Complement — Verified at 22yr / 144k

| Config | Weight | JP | LangDom | Both Gates | Cross-Lang |
|---|---|---|---|---|---|
| `linear_citation_concat` | 0.4 | 0.6725 | 0.6539 | ✅ PASS | 0.160 |
| `linear_hybrid05_concat` | 0.3 | 0.6605 | 0.6395 | ✅ PASS | 0.143 |
| TF-IDF `cited_decisions_tfidf` | — | 0.7840 | 0.4826 | ✅ PASS | 0.124 |

- **Minimal scale**: 19yr / 122k (first scale PASS both gates)
- **Scale dependency**: Optimal weight shifts toward semantic at larger scale (w=0.3 → 0.4)
- **Fundamental tradeoff**: Hybrids PASS adversarial but remain BELOW TF-IDF baseline on JP (0.61–0.67 vs 0.78–0.79)

### 4. Two-Mode Tradeoff — Fundamental and Reproduced at All Scales

| Representation | Jurist Preference | Language Dominance | Citation Independence |
|---|---|---|---|
| **TF-IDF Citation Hybrids** | **0.78–0.79** ✅ | **0.48** ✅ | ~14% |
| **Dense (center_projected)** | 0.05–0.43 ❌ | 0.83–0.98 ❌ | **~37%** ✅ |
| **Linear Hybrids (optimal)** | 0.61–0.67 ⚠️ | 0.58–0.80 ⚠️ | Intermediate |

**No single representation dominates all three metrics at any scale tested.**

### 5. True OOS Ceiling — Confirmed

- **True OOS JuristPref ceiling**: ~0.53 (v8 holdout validation)
- **Factory target**: 0.7
- **Achievable**: **NO** — dense embeddings cannot be primary for jurist navigation

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Status |
|---|---|---|
| BGE/bger ID mapping | Cannot align published (BGE) and unpublished (bger) IDs | **BLOCKED** |
| Parquet 2024–2026 | 15,536 decisions missing | **BLOCKED** |
| Section extraction 174k | No Sachverhalt/Erwaegungen/Dispositiv at scale | **BLOCKED** |

**Note**: 2022–2023 embeddings EXIST and PASS citation heritage quality check (AUC > 0.75 at 24yr/158k). Only 2024–2026 are genuinely missing.

---

## Test Verification

All assertions validated by `test_complementary_role_v34.py` — **ALL TESTS PASSED**:

```
✅ Citation Heritage: Dense AUCs > 0.75, cp64 gap 6.5× raw
✅ Minimal Scale: 21yr (137k) n_pairs=100, AUC > 0.75
✅ Cross-lingual Hierarchy: Sachverhalt > Dispositiv > Erwaegungen
✅ Linear Hybrid: PASS adversarial at w=0.3–0.4, JP < TF-IDF baseline
✅ Two-Mode Tradeoff: Fundamental, no single representation dominates
✅ True OOS Ceiling: ~0.53 < 0.7 factory target
✅ TF-IDF 174k Primary: LangDom=0.5785 PASS, beats semantic baseline
✅ Data Blockers: Completed years=24 (2000-2023), Failed=['2024','2025','2026']
```

---

## Product Integration Contracts (Frozen)

| View | Representation | Status | User Intent |
|---|---|---|---|
| **Primary Navigation** | `cited_outcome_hybrid_0.5_174k` (TF-IDF) | **PRODUCTION v1.0** | Jurist finds legally relevant neighbors |
| **Citation Heritage** | `center_projected_64dim` | **READY v1.1+** | Jurist explores doctrinal lineage |
| **Cross-Lingual** | Section-specific `center_projected_64dim` | **BLOCKED v1.1+** | Jurist finds cross-language equivalents |
| **Hybrid Complement** | `linear_citation_concat_w0.4` | **EXPLORATORY v1.1+** | Jurist trades relevance for cross-lingual reach |

---

## Recommendation

**CONTINUE = FALSE** — No further same-question cycles justified.

**PIVOT_WITHIN_MISSION = COMPLETE** — The complementary role characterization is complete at maximum available evaluated scale.

**Lane Status**: BLOCKED_ON_DEPENDENCIES (awaiting corpus lane for BGE/bger mapping, 2024–2026 parquet, 174k section extraction)

---

## Next Actions (Dependent on Corpus Lane)

1. **Corpus lane resumption**: BGE/bger mapping + 2024–2026 parquet + 174k section extraction
2. **When unblocked**: Compute 174k dense embeddings for all three complementary views
3. **Evaluation lane**: Apply frozen acceptance criteria for dense view promotion
4. **Product lane**: Ship v1.0 with TF-IDF primary; dense complementary views as v1.1+ milestones

---

**Report Status**: FINAL — Complementary role characterization complete. Awaiting corpus lane unblocking for 174k deployment.

**Verification Timestamp**: 2026-10-06
**GitHub Run**: 37473566313
**Factory Direction**: v34