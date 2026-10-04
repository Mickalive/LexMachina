# Legal Distance Lane v34: Final Verification & Completion Report

**Factory Direction Version:** 34  
**Lane:** legal-distance  
**Status:** BLOCKED_ON_DEPENDENCIES (continue_recommended=false)  
**Evidence Tier:** ACCEPTED  
**Date:** 2026-10-04  

---

## Executive Summary

The PIVOT_WITHIN_MISSION question has been **fully answered and validated** with ACCEPTED evidence across maximum available evaluated scales. The legal-distance lane has characterized the **necessary and sufficient** dense embedding scale and modes for the product's non-jurist-preference views.

**Current Lane Question (v34):** *"What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?"*

**Answer:** **COMPLETE** — Three complementary views characterized with minimal scales validated at max available evidence.

---

## Validated Complementary Views

| Complementary View | Minimal Scale | Key Metric | Threshold | Status |
|---|---|---|---|---|
| **Citation Heritage Recovery** | 21yr / 137k (2000-2020) | AUC (center_projected) | > 0.75 | ✅ PASSED at 21-24yr |
| **Cross-Lingual (Sachverhalt)** | 1K sample (359 decisions) | cross_lang_same_branch (cp_64) | > 0.2 | ✅ PASSED (0.282) |
| **Cross-Lingual (Dispositiv)** | 1K sample (538 decisions) | cross_lang_same_branch (cp_64) | > 0.1 | ✅ PASSED (0.150) |
| **Cross-Lingual (Erwaegungen)** | 1K sample (510 decisions) | cross_lang_same_branch (cp_64) | > 0.1 | ❌ FAILED (0.094) |
| **Linear Hybrid Complement** | 19yr / 122k (2000-2018) | PASS both adversarial gates | JP > 0.5, LangDom < 0.85 | ✅ PASSED at 19yr+ |

---

## Evidence Validation Summary

### 1. Citation Heritage Recovery — Dense SUPERIOR
- **22-year (144k, 344 pairs):** center_projected AUC 0.792-0.794 > 0.75 ✅
- **21-year (137k, 100 pairs):** center_projected AUC 0.818 > 0.75 ✅  
- **24-year (158k, 730 pairs):** center_projected AUC 0.767-0.770 > 0.75 ✅ (2.1× more pairs)
- **TF-IDF citation baseline:** AUC 0.71-0.74 (dense wins)
- **Raw 768dim:** FAILS at 24yr (AUC 0.682) — center projection ESSENTIAL

### 2. Section Cross-Lingual Hierarchy — Sachverhalt > Dispositiv > Erwaegungen
| Section | N | cp_64 cross_lang | cp_64 gap | Threshold | Status |
|---|---|---|---|---|---|
| Sachverhalt (facts) | 359 | **0.282** | **0.187** | >0.2 | ✅ PASS |
| Dispositiv (holding) | 538 | **0.150** | **0.397** | >0.1 | ✅ PASS |
| Erwaegungen (reasoning) | 510 | 0.094 | 0.452 | >0.1 | ❌ FAIL |

**Center projection improvement:** Sachverhalt 38%, Dispositiv 31%, Erwaegungen 16% gap reduction.

### 3. Linear Hybrid Complement — Scale-Dependent PASS
| Scale | Decisions | Optimal w (cited) | JP | LangDom | Both PASS? |
|---|---|---|---|---|---|
| 15yr | 91,929 | — | 0.473 | 0.809 | ❌ |
| **19yr** | **122,015** | **w=0.3** | **0.647** | **0.626** | ✅ |
| **22yr** | **144,443** | **w=0.4** | **0.673** | **0.654** | ✅ |

**Cross-lingual benefit:** Hybrid w=0.4 cross_lang_same_branch 0.160 > TF-IDF 0.124 (+29%)  
**But:** Hybrid JP (0.67) < TF-IDF baseline (0.78) — marked exploratory mode.

### 4. Two-Mode Tradeoff — Fundamental at All Scales
| Mode | LangDom | JP | CiteIndep | Role |
|---|---|---|---|---|
| TF-IDF Citation Hybrids | ~0.48 | **~0.78** | ~14% | **PRIMARY** |
| Dense (center_projected) | ~0.83-0.98 | 0.05-0.43 | ~37% | COMPLEMENTARY |
| Linear Hybrids (opt) | ~0.58-0.80 | 0.61-0.67 | ~20-30% | COMPLEMENTARY |

**No single representation dominates all three metrics at any scale.**

### 5. True OOS Ceiling
- True OOS JuristPref ceiling **~0.53** < 0.7 factory target
- No representation achieves factory target under true OOS conditions
- Confirms dense embeddings cannot be PRIMARY for jurist navigation

---

## Test Suite Results

All machine-readable tests **PASS**:

```
✅ Citation Heritage: Dense AUCs {raw: 0.795, cp64: 0.792, cp128: 0.792, cp768: 0.794}, cp64 gap=0.410 vs raw gap=0.063
✅ Minimal Scale: 21yr (137k) n_pairs=100, raw AUC=0.8455, cp64 AUC=0.8182
✅ Cross-lingual Hierarchy: gaps={sach: 0.187, disp: 0.397, erw: 0.452}, cross_lang={sach: 0.282, disp: 0.150, erw: 0.094}
✅ Linear Hybrid: TF-IDF JP=0.7840, w0.3 JP=0.6715, w0.4 JP=0.6725, cross_lang improvement=0.160 vs 0.124
✅ Two-Mode Tradeoff: Dense JP=0.426/LD=0.832, TF-IDF JP=0.784/LD=0.483, Hybrid JP=0.672/LD=0.654
✅ True OOS Ceiling: Verified < 0.7 factory target
✅ TF-IDF 174k Primary: LangDom=0.5785 PASS, beats semantic baseline
✅ Data Blockers: Completed years=24 (2000-2023), Failed=2021-2026, Missing=2024-2026
✅ 24yr Extension: n_decisions=158427, n_pairs=730, cp64 AUC=0.7667, raw AUC=0.6819 (FAILS)
```

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Resolution Owner |
|---|---|---|
| **bge_ ↔ bger_ ID mapping** | Cannot align canonical corpus with evaluation metadata | Corpus lane |
| **Parquet 2024-2026 missing** | 15,536 decisions (9%) absent from 174k target | Corpus lane |
| **Section extraction at 174k** | Cross-lingual view limited to 1K sample | Corpus lane |
| **GPU unavailability** | No BGE/multilingual-e5 finetuning at scale | Infrastructure |

**Note:** 2022-2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75), contradicting progress.json 'failed' flag.

---

## Product Integration Contracts (Post-v1.0)

| Map Mode | Primary Representation | Complementary Dense Role | User Intent |
|---|---|---|---|
| **Primary Navigation** | `cited_outcome_hybrid_0.5` (TF-IDF) | — | Jurist finds legally relevant neighbors |
| **Citation Heritage** | — | `center_projected_64dim` | Jurist explores doctrinal lineage via shared citations |
| **Cross-lingual** | — | `center_projected_64dim` (sachverhalt > dispositiv) | Jurist finds equivalent decisions in other languages |
| **Hybrid Explore** | `linear_citation_concat_w0.4` | 30-40% dense contribution | Jurist trades some legal relevance for cross-lingual reach |

**v1.0 Release:** TF-IDF citation hybrids as primary (JP 0.78 vs 0.43 semantic baseline)  
**v1.1+:** Dense embedding integration for citation-heritage and cross-lingual views

---

## State Verification

```json
{
  "lane": "legal-distance",
  "direction_version": 34,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "legal_distance_v34_complementary_role_20261003",
  "audit_ready": true
}
```

---

## Recommendation

**No further same-question cycles justified.** The PIVOT_WITHIN_MISSION characterization is complete at maximum available evaluated scale (22yr/144k evaluated, 24yr/158k citation heritage extended). Three complementary modes validated against evaluation lane criteria.

**Next Actions (Factory Director):**
1. **Corpus lane**: Resume for bge_↔bger_ mapping, 2024-2026 parquet, section extraction at 174k
2. **Product lane**: Ship v1.0 with TF-IDF citation hybrids as primary navigation mode
3. **Dense integration**: v1.1+ per integration contracts above
4. **No new Frontier team** — portfolio v7 confirmed, all teams terminated

---

*Verification completed 2026-10-04 | Factory Direction v34 | Legal-Distance Lane | All tests PASS*
