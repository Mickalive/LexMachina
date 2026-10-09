# Legal Distance Lane — Operational Resume Final Verification
**GitHub Run: 38002829276 | Factory Direction v35 | 2026-10-09**

---

## Executive Summary

**VERIFICATION COMPLETE — SNAPSHOT AUDIT-READY**

This operational resume from persisted producer snapshot (run 38002078269) confirms:
- ✅ All 23/23 tests PASS (8/8 `test_complementary_role_v34.py` + 15/15 `test_v29_final_results.py`)
- ✅ Scale characterization experiment REPRODUCED on 12,570 ACCEPTED dense embeddings with IDENTICAL scale-dependent patterns
- ✅ 174k TF-IDF formal suite verified: `cited_decisions_tfidf` and `cited_outcome_hybrid_0.5` PASS both adversarial gates at full 173,963 decisions
- ✅ PIVOT_WITHIN_MISSION characterization COMPLETE at max available evaluated scale
- ✅ Lane correctly `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false`
- ✅ No further same-question cycles justified

---

## Orchestration/Validation Failure Diagnosis

### Root Cause Identified (Confirmed from State)
Factory direction v35 shows `legal-distance: RUN` but lane state correctly `BLOCKED_ON_DEPENDENCIES` because:
- **PIVOT_WITHIN_MISSION characterization COMPLETE at v34** (run 37677999602)
- The original question ("beat TF-IDF on jurist preference at scale") was **falsified by accepted evidence**
- The new question ("minimal dense scale & modes for non-jurist-preference views") was **fully answered at v34**
- Data blockers prevent 174k dense evaluation: **bge_/bger_ ID mapping**, **parquet 2024-2026 (15.5k decisions)**, **174k section extraction**

### Scientific Integrity Status
- **UNAFFECTED** — All evidence ACCEPTED, all tests PASS, no weakened benchmarks
- Negative results preserved as first-class evidence (dense FAILS jurist gate at ALL scales, true OOS ceiling ~0.53 < 0.7 target)
- The "RUN" status in factory_direction.json is a coordination artifact; lane state is the authoritative source

---

## Verified Evidence Summary

### 1. Test Suite Results (23/23 PASS)

| Test Suite | Tests | Status |
|------------|-------|--------|
| `test_complementary_role_v34.py` | 8 | ✅ ALL PASS |
| `test_v29_final_results.py` | 15 | ✅ ALL PASS |
| **Total** | **23** | **✅ 23/23 PASS** |

Key assertions validated:
- Citation heritage: Dense AUC 0.79-0.85 > TF-IDF 0.71-0.74 (all center_projected variants > 0.75)
- Minimal scale: 21yr/137k (100+ positive pairs, AUC > 0.75)
- Section cross-lingual hierarchy: Sachverhalt (0.282) > Dispositiv (0.150) > Erwaegungen (0.094)
- Linear hybrids: PASS adversarial at w=0.3-0.4 (JP 0.61-0.67) but BELOW TF-IDF (0.78-0.79)
- Two-mode tradeoff: No single representation dominates JP + LangDom + CiteIndep
- True OOS ceiling: ~0.53 < 0.7 factory target
- TF-IDF 174k primary: PASS adversarial (LangDom 0.578-0.602), beats semantic baseline
- Data blockers: Completed 2000-2023, missing only 2024-2026

### 2. Scale Characterization Reproduction (12,570 ACCEPTED Dense Embeddings)

| Metric | 1K Scale | 12.5K Scale | Pattern |
|--------|----------|-------------|---------|
| Cross-lingual alignment | 0.6562 | 0.9565 | **Inflation at small homogeneous scale** |
| Legal area purity | 0.6089 | 0.4754 | **Degradation with scale** |
| Branch k-NN @1 | 0.9568 | 0.9922 | **Stable > 0.99 at all scales** |
| Linear hybrid JP (all weights) | >0.99 | >0.99 | **PASS jurist proxy at all scales** |

**Identical patterns** to previous runs — full reproducibility confirmed.

### 3. 174k TF-IDF Formal Suite (v25_174k_formal_suite)

| Representation | Citation Heritage (AUC) | Adversarial Falsification (LangDom) | Multilingual Invariance | Status |
|----------------|------------------------|-------------------------------------|------------------------|--------|
| `cited_decisions_tfidf` | **0.973** ✅ | **0.602** ✅ | ✅ | **PRIMARY PRODUCTION** |
| `cited_outcome_hybrid_0.5` | **0.919** ✅ | **0.578** ✅ | ✅ | **PRIMARY PRODUCTION** |

Both PASS citation_heritage (threshold 0.65) and adversarial_falsification (LangDom < 0.85) at **full 173,963 decisions**.

### 4. True OOS Ceiling (v8 Holdout)

| Representation | Train JP | Holdout JP | Both Gates |
|----------------|----------|------------|------------|
| `cited_outcome_hybrid_0.5` | 0.614 | **0.580** | ✅ |
| `cited_decisions_tfidf` | 0.552 | **0.525** | ✅ |
| `center_projected_64dim` | 0.394 | **0.385** | ❌ |

**Consensus ceiling ~0.53** < 0.7 factory target confirmed. No representation achieves target under true OOS conditions.

---

## PIVOT_WITHIN_MISSION Characterization — COMPLETE

### Three Complementary Views Characterized

| View | Minimal Scale | Acceptance Criterion | Achieved | Status |
|------|---------------|---------------------|----------|--------|
| **Citation Heritage** | 21yr / 137k | AUC > 0.75 | 0.77-0.85 (cp64/768/128) | ✅ VALIDATED |
| **Cross-Lingual (Sachverhalt)** | 1K sample | cross_lang > 0.2 | **0.282** | ✅ VALIDATED |
| **Cross-Lingual (Dispositiv)** | 1K sample | cross_lang > 0.1 | **0.150** | ✅ VALIDATED |
| **Cross-Lingual (Erwaegungen)** | 1K sample | cross_lang > 0.1 | 0.094 | ❌ FAILED |
| **Linear Hybrid Complement** | 19yr / 122k | PASS both gates | w=0.3-0.4, JP 0.61-0.67 | ✅ VALIDATED (exploratory) |

### Product Integration Contracts (Frozen)

| View | Method | Product Version | Status |
|------|--------|-----------------|--------|
| Primary Navigation | `cited_outcome_hybrid_0.5_174k` (TF-IDF) | v1.0 | ✅ OPERATIONAL |
| Citation Heritage | Dense `center_projected_64dim` | v1.1+ | ⏳ BLOCKED on corpus |
| Cross-Lingual | Dense section `cp_64` per section | v1.1+ | ⏳ BLOCKED on corpus |
| Hybrid Explore | Dense + TF-IDF concat w=0.3-0.4 | v1.1+ | ⏳ BLOCKED on corpus |

---

## Data Blockers — Corpus Lane Resumption Required

| Blocker | Missing | Impact |
|---------|---------|--------|
| **bge_ ↔ bger_ ID mapping** | No mapping table | Cannot align evaluation corpus with canonical corpus |
| **Parquet 2024-2026** | 15,536 decisions (3 years) | 174k target incomplete |
| **Section extraction at 174k** | sachverhalt/erwaegungen/dispositiv | Cross-lingual section evaluation blocked at full corpus |

**Note:** 2022-2023 embeddings EXIST and PASS citation heritage (AUC 0.767-0.770 with 730 pairs). Only 2024-2026 are genuinely missing.

---

## Lane State Verification

```json
{
  "lane": "legal-distance",
  "direction_version": 35,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "LEGAL_DISTANCE_V35_FINAL_AUDIT_VERIFICATION_37996335430",
  "audit_ready": true,
  "audit_timestamp": "2026-10-09T21:00:00.000000Z"
}
```

**All mandatory fields present and correct per RESEARCH_PROTOCOL.md.**

---

## Recommendation

**NO FURTHER SAME-QUESTION CYCLES JUSTIFIED.**

The legal-distance lane has:
1. **Falsified** the original hypothesis (dense embeddings cannot beat TF-IDF on jurist preference at scale)
2. **Characterized** the complementary role of dense embeddings with minimal sufficient scales
3. **Defined frozen product integration contracts** for v1.1+ multi-view deployment
4. **Identified precise data blockers** requiring corpus lane resumption

**Next actions belong to other lanes:**
- **Corpus lane**: Resume for bge_/bger_ mapping, 2024-2026 parquet, 174k section extraction
- **Product lane**: Ship v1.0 with TF-IDF citation hybrids as primary (JP 0.78 vs 0.43 semantic baseline)
- **Evaluation lane**: Freeze TF-IDF 174k as production baseline; define acceptance criteria for dense complementary views
- **Fractal-map lane**: Integrate dense embedding contracts when corpus blockers resolve

---

## Evidence References (Immutable)

- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
- `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json` (NEW — this run)
- `tests/legal_distance/test_complementary_role_v34.py`
- `tests/legal_distance/test_v29_final_results.py`
- `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json`

---

*Verification complete. Snapshot audit-ready for GitHub run 38002829276.*