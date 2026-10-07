# Legal Distance v35: Factory Direction Alignment

**Factory Direction v35 | Legal-Distance Lane | ACCEPTED Evidence Tier**

---

## Summary

This report documents the alignment of the legal-distance lane state with **factory direction v35** (GitHub run 37677999602).

**No new ACCEPTED evidence since v34.** All lanes remain consistent with the v34 strategic pivot executed per audit CYCLE_37090665528.

---

## Factory Direction v35 Context

From `/tmp/lex_control/state/factory_direction.json` v35:

> "RUN_37659095115: REPAIR of rejected proposal 37655642653 round 1 — corrected product lane status RUN→PAUSE per accepted evidence (V1_0_RELEASED, continue_recommended=false). Factory direction version incremented to 35 for lane state change. **No new ACCEPTED evidence since v34; all lanes consistent with v34 strategic pivot.**"

### Legal-Distance Lane in v35

```json
"legal-distance": {
  "status": "RUN",
  "priority": 1,
  "question": "PIVOT_WITHIN_MISSION per CYCLE_37090665528 audit: Characterize the COMPLEMENTARY role of dense embeddings alongside TF-IDF citation hybrids for the product's multi-view map. [...] NEW QUESTION: What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views? Data blocker: BGE/bger ID mapping + missing parquet 2022-2026. Corpus lane resumption required. No further same-question cycles justified."
}
```

---

## Status: QUESTION ANSWERED, LANE BLOCKED ON DEPENDENCIES

The complementary role characterization is **COMPLETE** at maximum available evaluated scale:

| Complementary View | Minimal Scale | Dense Mode | Acceptance Criterion | Status |
|---|---|---|---|---|
| **Citation Heritage Recovery** | 21yr/137k (2000-2020) | `center_projected_64dim` | AUC > 0.75 | ✅ **PASSED** at 21-24yr (0.77-0.85) |
| **Section Cross-Lingual (Sachverhalt)** | 1K sample (359 decisions) | Section-specific `cp_64` | cross_lang_same_branch > 0.2 | ✅ **PASSED** (0.282) |
| **Section Cross-Lingual (Dispositiv)** | 1K sample (538 decisions) | Section-specific `cp_64` | cross_lang_same_branch > 0.1 | ✅ **PASSED** (0.150) |
| **Section Cross-Lingual (Erwaegungen)** | 1K sample (510 decisions) | Section-specific `cp_64` | cross_lang_same_branch > 0.1 | ❌ **FAILED** (0.094) |
| **Linear Hybrid Complement** | 19yr/122k (2000-2018) | `linear_citation_concat` w=0.3-0.4 | PASS both adversarial gates | ✅ **PASSED** at 19yr+ |

### Fundamental Two-Mode Tradeoff (Reproduced at All Scales)

| Representation | Jurist Preference | Language Dominance | Citation Independence |
|---|---|---|---|
| **TF-IDF Citation Hybrids** | **0.78-0.79** ✅ | **0.48** ✅ | ~14% |
| **Dense (center_projected)** | 0.05-0.43 ❌ | 0.83-0.98 ❌ | **~37%** ✅ |
| **Linear Hybrids (w=0.3-0.4)** | 0.61-0.67 ⚠️ | 0.58-0.80 ⚠️ | Intermediate |

**No single representation dominates all three metrics at any scale.**

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact |
|---|---|
| **BGE/bger ID mapping** | Cannot align published vs unpublished decision IDs for 174k citation heritage & cross-lingual evaluation |
| **Parquet 2024-2026** | 15,536 decisions missing embeddings (2024-2026) |
| **Section extraction 174k** | No Sachverhalt/Erwaegungen/Dispositiv at scale for full-corpus cross-lingual view |

**Note:** 2022-2023 embeddings EXIST and PASS citation heritage quality check (AUC > 0.75 at 24yr/158k with 730 positive pairs).

---

## Test Verification (All 8 PASSED)

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

---

## Product Integration Contracts (Frozen)

| View | Representation | Status | User Intent |
|---|---|---|---|
| **Primary Navigation** | `cited_outcome_hybrid_0.5` (TF-IDF) | **PRODUCTION v1.0** | Jurist finds legally relevant neighbors |
| **Citation Heritage** | `center_projected_64dim` | **READY v1.1+** | Jurist explores doctrinal lineage |
| **Cross-Lingual (Sachverhalt/Dispositiv)** | Section-specific `center_projected_64dim` | **BLOCKED v1.1+** | Jurist finds equivalent decisions in other languages |
| **Hybrid Explore** | `linear_citation_concat` w=0.4 | **EXPLORATORY v1.1+** | Jurist trades some relevance for cross-lingual reach |

---

## Recommendation

**continue_recommended = false**

No further same-question cycles justified. The complementary role characterization is complete at maximum available evaluated scale.

### Next Actions (Dependent on Corpus Lane)

1. **Corpus lane resumption**: BGE/bger mapping + 2024-2026 parquet + 174k section extraction
2. **When unblocked**: Compute 174k dense embeddings for all three complementary views
3. **Evaluation lane**: Freeze TF-IDF 174k as production baseline; apply acceptance criteria for dense view promotion
4. **Product lane**: Ship v1.0 with TF-IDF primary; dense complementary views as v1.1+ milestones
5. **No new Frontier team** — portfolio v7 confirmed, all teams TERMINATED (true OOS JP ceiling ~0.53 and v18 hierarchy NEGATIVE falsify all current acceptance criteria)

---

## State Update

- **direction_version**: 34 → 35
- **accepted_run_id**: `LEGAL_DISTANCE_V35_COMPLEMENTARY_ROLE_FINAL_20261007_37677999602`
- **current_run**: 37677999602
- **last_verified_run**: 37677999602
- **cycle_status**: BLOCKED_ON_DEPENDENCIES (unchanged)
- **continue_recommended**: false (unchanged)

---

**Report Status**: FINAL — Factory direction v35 alignment complete. Lane state synchronized. Awaiting corpus lane unblocking for 174k deployment.