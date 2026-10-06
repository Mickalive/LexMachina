# Legal Distance Lane — Run 37410790522 Verification Report

**Lane**: legal-distance  
**Factory Direction Version**: 34  
**Evidence Tier**: ACCEPTED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Continue Recommended**: false  
**Run ID**: 37410790522  
**Date**: 2026-10-06  

---

## Verification Summary

All 8 complementary role characterization tests **RE-VERIFIED PASS** for GitHub run 37410790522. The PIVOT_WITHIN_MISSION characterization of dense embedding complementary views is **COMPLETE** at ACCEPTED evidence tier.

---

## Test Results

| Test | Status | Key Finding |
|------|--------|-------------|
| `test_citation_heritage_superiority` | ✅ PASS | Dense AUCs 0.79-0.85 > TF-IDF citation baseline 0.71-0.74; cp64 gap=0.410 vs raw gap=0.063 |
| `test_citation_heritage_minimal_scale` | ✅ PASS | 21yr/137k decisions, 100 positive pairs, raw AUC=0.8455, cp64 AUC=0.8182 |
| `test_section_crosslingual_hierarchy` | ✅ PASS | Sachverhalt (0.282) > Dispositiv (0.150) > Erwaegungen (0.094); cp64 gaps 0.187 < 0.397 < 0.452 |
| `test_linear_hybrid_optimal_weight` | ✅ PASS | TF-IDF JP=0.784; w=0.3 JP=0.672, w=0.4 JP=0.673 (both PASS adversarial); cross-lang 0.160 > 0.124 |
| `test_two_mode_tradeoff_fundamental` | ✅ PASS | Dense JP=0.426/LD=0.832, TF-IDF JP=0.784/LD=0.483, Hybrid JP=0.672/LD=0.654 — no single dominates all three |
| `test_true_oos_ceiling` | ✅ PASS | True OOS JuristPref ceiling ~0.53 < 0.7 factory target |
| `test_tfidf_174k_primary_validated` | ✅ PASS | TF-IDF citation hybrid LangDom=0.579 PASS; beats semantic baseline JP 0.78 vs 0.43 |
| `test_data_blockers_identified` | ✅ PASS | 24 completed years (2000-2023), failed=['2024','2025','2026'], missing=['2024','2025','2026'] |

---

## Characterization Complete: Three Complementary Dense Modes

### 1. Citation Heritage View — **Dense SUPERIOR to TF-IDF**
- **Minimal scale**: 21-year / 137k decisions (2000-2020) with ≥100 positive citation pairs
- **Best representation**: `center_projected_64dim` (AUC 0.79-0.85 at 21-24yr)
- **Acceptance criterion**: AUC > 0.75 — **PASSED** at 21-24yr
- **Product role**: "Doctrinal Proximity" map mode — shows decisions sharing doctrinal lineage through citations

### 2. Section Cross-Lingual View — **Dense NECESSARY** (TF-IDF cannot do this)
- **Minimal scale**: 1K sample (359 Sachverhalt, 538 Dispositiv, 510 Erwaegungen)
- **Hierarchy**: Sachverhalt (facts) > Dispositiv (holding) > Erwaegungen (reasoning)
- **Acceptance criteria**: cross_lang_same_branch > 0.2 (Sachverhalt: 0.282 ✅), > 0.1 (Dispositiv: 0.150 ✅, Erwaegungen: 0.094 ❌)
- **Full corpus**: **BLOCKED** pending section extraction at 174k scale
- **Product role**: "Cross-Lingual Navigation" mode — enables French/Italian/German jurists to find legally similar decisions across languages

### 3. Linear Hybrid Complement — **Dense ADDS cross-lingual benefit**
- **Minimal scale**: 19-year / 122k decisions (2000-2018)
- **Optimal weight**: w=0.3-0.4 (30-40% dense, 60-70% TF-IDF) — scale shifts weight toward semantic
- **Adversarial gates**: PASS at 19yr+ (w=0.3-0.4)
- **Jurist preference**: 0.61-0.67 — **BELOW TF-IDF baseline** (0.78-0.79)
- **Cross-lingual improvement**: 0.124 → 0.160 (+29%)
- **Product role**: Optional "Semantic + Citation" blend mode; NOT a replacement for TF-IDF primary mode

---

## Two-Mode Tradeoff: FUNDAMENTAL

| Metric | TF-IDF Citation Hybrids | Dense (center_projected) | Linear Hybrids (opt) |
|--------|------------------------|-------------------------|---------------------|
| Language Dominance (↓) | **0.48** ✅ | 0.83-0.98 ❌ | 0.58-0.80 |
| Jurist Preference (↑) | **0.78** ✅ | 0.05-0.43 ❌ | 0.61-0.67 |
| Citation Independence (↑) | 0.14 | **0.37** ✅ | 0.25-0.35 |

**No single representation dominates all three metrics at any scale.**

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Resolution |
|---------|--------|------------|
| **bge_ ↔ bger_ ID mapping** | Cannot align canonical (published BGE) corpus with evaluation (unpublished bger) corpus | Corpus lane coordination |
| **Missing parquet 2024-2026** | ~15.5k decisions (9%) missing from 174k target | Corpus lane acquisition |
| **Section extraction not at scale** | Sachverhalt/Erwaegungen/Dispositiv dense embeddings only at 1K sample | Full corpus text access + CPU/GPU section encoding |

---

## Recommendation

**PIVOT_WITHIN_MISSION EXECUTED — No further same-question cycles justified.**

1. **Product v1.0**: Ship with TF-IDF citation hybrids as PRIMARY navigation mode (JP 0.78 vs 0.43 semantic baseline)
2. **Dense integration v1.1+**: 
   - Citation Heritage view (when 174k dense available)
   - Cross-Lingual view (when 174k section extraction available)
   - Linear Hybrid Complement (exploratory mode)
3. **Corpus lane**: Resume for bge_↔bger_ mapping, 2024-2026 parquet, section extraction at 174k
4. **No new Frontier team** — portfolio v7 confirmed, all teams TERMINATED (true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria)

---

## Evidence References

All evidence from `state/legal-distance.json` evidence_refs (31 references):
- Citation heritage evaluations at 21yr, 22yr, 24yr
- Section cross-lingual evaluation (1K sample, all 3 sections)
- Linear combination weight sweeps at 19yr, 22yr
- 22-year center_projected evaluation
- TF-IDF 174k formal suite (8/8 PASS)
- v8 holdout zero-shot validation (true OOS ceiling)
- v17b label normalization, v18 coarse hierarchy
- Progress checkpoints (24 completed years, 3 genuinely missing)

---

*Verification completed 2026-10-06 | Factory Direction v34 | Legal-Distance Lane | Run 37410790522*