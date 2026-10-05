# Legal-Distance Lane — Final Verification (Factory Direction v34)

**Date:** 2026-10-05  
**Lane:** legal-distance  
**Direction Version:** 34  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false  

---

## Verification Summary

The legal-distance lane has **completed** the PIVOT_WITHIN_MISSION characterization of dense embeddings' complementary role alongside TF-IDF citation hybrids. All evidence is ACCEPTED and no further same-question cycles are justified.

### Verified Reproduction (2026-10-05)

| Experiment | Result | Matches Reported |
|---|---|---|
| 24-year citation heritage evaluation | ✅ Reproduced | Yes (AUC 0.767-0.770, 730 pairs) |
| 22-year citation heritage evaluation | ✅ Previously reproduced | Yes (AUC 0.79-0.85, 344 pairs) |
| Section cross-lingual (1K sample) | ✅ Previously reproduced | Yes (Sachverhalt 0.282, Dispositiv 0.150, Erwaegungen 0.094) |
| Linear hybrid weight sweep (22yr) | ✅ Previously reproduced | Yes (w=0.3-0.4 optimal) |

---

## Complementary Role Characterization — COMPLETE

### Three Validated Complementary Modes

| View | Minimal Scale | Best Dense Mode | Status | Blocker for 174k |
|---|---|---|---|---|
| **Citation Heritage** | 137k (21yr) | `center_projected_64dim` | ✅ READY at 158k | bge_/bger_ mapping + 2024-2026 parquet |
| **Section Cross-lingual** | 174k (full) | `center_projected_64dim` per section | ⚠️ SAMPLE ONLY (1K) | Section extraction at 174k + ID mapping |
| **Linear Hybrid Complement** | 122k (19yr) | `linear_citation_concat_w0.4` / `linear_hybrid05_concat_w0.3` | ✅ READY at 144k | bge_/bger_ mapping for hybrid construction |

### Key Findings (Reproduced at Maximum Available Scale)

1. **Citation Heritage Recovery**: Dense embeddings AUC 0.77-0.85 > TF-IDF citation-based 0.71-0.74. Emerges at ~130k decisions when sufficient recent-year citation pairs exist (2019+). Reinforced at 24yr/158k with 730 positive pairs (2.1× 22yr).

2. **Section Cross-lingual Hierarchy**: Sachverhalt (facts) > Dispositiv (holdings) > Erwaegungen (reasoning). Center projection reduces invariance gap by 16-38%. Full corpus density blocked pending section extraction.

3. **Linear Hybrid Complement**: PASS adversarial gates at 19yr+ with w=0.3-0.4 (30-40% dense). Adds cross-lingual recall (0.124 → 0.160) but remains BELOW TF-IDF baseline on jurist preference (0.61-0.67 vs 0.78-0.79).

4. **Fundamental Two-Mode Tradeoff**: No single representation dominates Language Dominance, Jurist Preference, and Citation Independence simultaneously at any scale.

5. **True OOS Ceiling**: JuristPref ceiling ~0.53 < 0.7 factory target — dense embeddings cannot be PRIMARY for jurist navigation.

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Decisions Affected |
|---|---|---|
| **bge_ ↔ bger_ ID mapping** | Cannot align TF-IDF (bge_) with dense (bger_) for hybrids, jurist gate eval, evaluation | All 174k |
| **Parquet 2024-2026 missing** | 15,536 decisions missing from 174k target | Years 2024-2026 |
| **Section extraction at 174k** | Cross-lingual view limited to 1K sample | All sections |
| **progress.json false failures** | 2022-2023 embeddings incorrectly flagged; actually PASS quality gates | Years 2022-2023 |

**Note**: 2022-2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75 at 24yr). The progress.json "failed" flag is a tracking bug, not a quality failure.

---

## Product Integration Contracts (for v1.1+)

| Map Mode | Primary | Complementary Dense Role |
|---|---|---|
| **Primary Navigation** | `cited_outcome_hybrid_0.5` (TF-IDF) | — |
| **Citation Heritage** | — | `center_projected_64dim` (AUC 0.77-0.85) |
| **Cross-lingual** | — | `center_projected_64dim` per section (Sachverhalt > Dispositiv) |
| **Hybrid Explore** | `linear_citation_concat_w0.4` | 30-40% dense contribution |

---

## Acceptance Criteria Status

| View | Metric | Threshold | 22yr/144k | 24yr/158k | Status |
|---|---|---|---|---|---|
| Citation Heritage | AUC-ROC | > 0.75 | 0.79-0.85 ✅ | 0.767-0.770 ✅ | PASS |
| Cross-lingual (Sachverhalt) | cross_lang_same_branch | > 0.2 | 0.282 (1K) | — | SAMPLE PASS |
| Cross-lingual (Dispositiv) | cross_lang_same_branch | > 0.1 | 0.150 (1K) | — | SAMPLE PASS |
| Hybrid Complement | Both adversarial gates | PASS | PASS (w=0.3-0.4) | — | PASS |

---

## Next Actions (Factory Director)

1. **Corpus lane**: Resume for bge_↔bger_ mapping, 2024-2026 parquet, section extraction at 174k, correct progress.json
2. **Product lane**: Ship v1.0 with TF-IDF citation hybrids as primary (JP 0.78 vs 0.43 semantic baseline)
3. **Dense integration**: v1.1+ for citation-heritage view (ready at 158k) and cross-lingual view (blocked)
4. **No new Frontier team** — portfolio v7 confirmed, all teams terminated (true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all acceptance criteria)

---

## Conclusion

**The legal-distance lane question is ANSWERED at maximum available evidence scale.** The complementary role of dense embeddings is characterized with REPRODUCED/ACCEPTED evidence. The lane is correctly BLOCKED_ON_DEPENDENCIES with `continue_recommended=false`. No further work on this question is possible or justified until corpus lane unblocks the data dependencies.

*Verification completed 2026-10-05 by legal-distance lane researcher.*