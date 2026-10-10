# LEGAL DISTANCE LANE — FINAL AUDIT VERIFICATION
## GitHub Run 38017387070 | Factory Direction v35 | 2026-10-10

---

## EXECUTIVE SUMMARY

**VERIFICATION COMPLETE — ALL EVIDENCE CONFIRMED**

This operational resume verification from fresh context confirms:
- ✅ **All 23/23 tests PASSED** (test_complementary_role_v34.py 8/8 + test_v29_final_results.py 15/15)
- ✅ **Scale characterization experiment REPRODUCED** on 12,570 ACCEPTED dense embeddings (2000-2002) with IDENTICAL scale-dependent patterns
- ✅ **174k TF-IDF evaluation suite VERIFIED**: `cited_decisions_tfidf` (citation_heritage AUC 0.973, LangDom 0.602) and `cited_outcome_hybrid_0.5` (citation_heritage AUC 0.919, LangDom 0.578) PASS both adversarial gates at full 173,963 decisions
- ✅ **PIVOT_WITHIN_MISSION characterization COMPLETE** at maximum available evaluated scale
- ✅ **Lane correctly BLOCKED_ON_DEPENDENCIES** with `continue_recommended=false`
- ✅ **No further same-question cycles justified**

---

## VERIFICATION DETAILS

### 1. Test Suite Verification (23/23 PASS)

#### test_complementary_role_v34.py — 8/8 PASS
| Test | Result | Key Evidence |
|------|--------|--------------|
| Citation Heritage | ✅ PASS | Dense AUCs: raw=0.795, cp64=0.792, cp128=0.792, cp768=0.794 |
| Minimal Scale (21yr/137k) | ✅ PASS | 100 pairs, raw AUC=0.8455, cp64 AUC=0.8182 |
| Cross-lingual Hierarchy | ✅ PASS | Sachverhalt gap=0.187 (cp64 cross_lang=0.282 > 0.2), Dispositiv gap=0.397 (cp64 cross_lang=0.150 > 0.1), Erwaegungen gap=0.452 (cp64 cross_lang=0.094 < 0.1) |
| Linear Hybrid | ✅ PASS | TF-IDF JP=0.784, w0.3 JP=0.672, w0.4 JP=0.673, cross_lang improvement=0.160 vs 0.124 |
| Two-Mode Tradeoff | ✅ PASS | Dense JP=0.426/LD=0.832, TF-IDF JP=0.784/LD=0.483, Hybrid JP=0.672/LD=0.654 |
| True OOS Ceiling | ✅ PASS | Verified < 0.7 factory target |
| TF-IDF 174k Primary | ✅ PASS | LangDom=0.5785 PASS, beats semantic baseline |
| Data Blockers | ✅ PASS | 24 years complete (2000-2023), 2024-2026 missing |

#### test_v29_final_results.py — 15/15 PASS
All scale evidence, section cross-lingual hierarchy, two-mode tradeoff, and fundamental blocker tests pass.

### 2. Scale Characterization Reproduction (12,570 ACCEPTED embeddings)

| Metric | Scale 1K | Scale 12.5K | Pattern |
|--------|----------|-------------|---------|
| Cross-lingual same_branch | 0.6562 | 0.9565 | **Inflation** with scale (language dominates) |
| Legal area purity | 0.6089 | 0.4754 | **Degradation** with scale |
| Branch k-NN @1 | 0.9568 | 0.9922 | Stable > 0.99 at all scales |
| Linear hybrid JP (w=0.3) | 0.9915 | 0.9938 | **PASS at all weights** (>0.99) |

**IDENTICAL patterns to previous verification runs** — cross-lingual inflation, legal area purity degradation, branch k-NN stability, linear hybrid adversarial PASS.

### 3. Key Accepted Findings (Reverified)

| Finding | Evidence | Status |
|---------|----------|--------|
| **Citation Heritage Dense Superiority** | 21yr AUC 0.8455→24yr AUC 0.7696 (cp768), all > 0.75; TF-IDF citation baseline 0.71-0.74 | ✅ CONFIRMED |
| **Section Cross-Lingual Hierarchy** | Sachverhalt 0.282 > 0.2 ✅, Dispositiv 0.150 > 0.1 ✅, Erwaegungen 0.094 < 0.1 ❌ | ✅ CONFIRMED |
| **Linear Hybrids Scale Dependency** | 15yr FAIL (0.473) → 19yr PASS (0.637) → 22yr PASS (0.673); optimal w shifts 0.3→0.4 | ✅ CONFIRMED |
| **Two-Mode Tradeoff Fundamental** | NO single representation dominates JP + LangDom + CiteIndep | ✅ CONFIRMED |
| **Dense Fails Jurist Gate All Scales** | 3yr JP=0.39-0.42, 15yr=0.288, 19yr=0.369, 20yr=0.048, 22yr=0.427 | ✅ CONFIRMED |
| **True OOS JP Ceiling ~0.53** | v8 holdout: TF-IDF JP -0.015 to -0.020 leakage impact | ✅ CONFIRMED |
| **Legal TF-IDF bge_ Corpus NEGATIVE** | 6/14 PASS vs 14/14 baseline; citation heritage AUC ~0.5 | ✅ CONFIRMED |
| **v18 Coarse Hierarchy NEGATIVE** | Max purity 0.65 < 0.7 threshold | ✅ CONFIRMED |

### 4. Minimal Dense Scale Characterization — QUESTION ANSWERED

**NEW QUESTION (v34):** *What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?*

**ANSWER — THREE COMPLEMENTARY MODES AT CHARACTERIZED MINIMAL SCALES:**

| Complementary Mode | Minimal Scale | Acceptance Criterion | Status |
|--------------------|---------------|----------------------|--------|
| **CITATION HERITAGE** | 21yr / 137k decisions (2000-2020) | AUC > 0.75 | ✅ PASSED at 21-24yr (137k-158k) |
| **SECTION CROSS-LINGUAL (Sachverhalt)** | 1K sample (359 decisions) | cross_lang_same_branch > 0.2 | ✅ PASSED (0.282) |
| **SECTION CROSS-LINGUAL (Dispositiv)** | 1K sample (538 decisions) | cross_lang_same_branch > 0.1 | ✅ PASSED (0.150) |
| **SECTION CROSS-LINGUAL (Erwaegungen)** | 1K sample (510 decisions) | cross_lang_same_branch > 0.1 | ❌ FAILED (0.094) |
| **LINEAR HYBRID COMPLEMENT** | 19yr / 122k decisions (2000-2018) | PASS both adversarial gates | ✅ PASSED at 19yr+ (w=0.3-0.4) |

**Two-mode tradeoff fundamental:** TF-IDF = PRIMARY (jurist preference, branch clustering); Dense = COMPLEMENTARY (citation heritage view, cross-lingual view, linear hybrid complement).

### 5. 174k TF-IDF Production Baseline (Verified)

| Representation | Citation Heritage AUC | Adversarial LangDom | Multilingual Invariance | Cross-Lang Pairs | Collapse Check | Status |
|----------------|----------------------|---------------------|------------------------|------------------|----------------|--------|
| `cited_decisions_tfidf` | **0.973** ✅ | **0.602** ✅ | ✅ | ✅ | ✅ | **PRIMARY** |
| `cited_outcome_hybrid_0.5` | **0.919** ✅ | **0.578** ✅ | ✅ | ✅ | ✅ | **PRIMARY** |

Both PASS both adversarial gates at full 173,963 decisions. WebGL pipeline <3s. Product v1.0 RELEASED with these as defaults.

### 6. Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Status |
|---------|--------|--------|
| **bge_/bger_ ID mapping** | Cannot evaluate 174k dense JP; 2022-2023 embeddings exist but unaligned | ❌ UNRESOLVED |
| **Parquet 2024-2026** | 15,536 decisions missing from 174k target | ❌ UNRESOLVED |
| **174k Section Extraction** | Sachverhalt/Erwaegungen/Dispositiv not extracted at full scale | ❌ UNRESOLVED |

---

## LANE STATE CONSISTENCY CHECK

| Field | Factory Direction v35 | Lane State (legal-distance.json) | Consistent? |
|-------|----------------------|----------------------------------|-------------|
| Status | RUN | BLOCKED_ON_DEPENDENCIES | ⚠️ **Direction shows RUN but lane correctly BLOCKED** |
| continue_recommended | (implied) | false | ✅ No further cycles |
| evidence_tier | (implied ACCEPTED) | ACCEPTED | ✅ |
| Question | PIVOT_WITHIN_MISSION: characterize complementary role | MINIMAL DENSE SCALE CHARACTERIZATION COMPLETE | ✅ Answered |

**Note:** Factory direction v35 shows legal-distance RUN but lane state correctly BLOCKED_ON_DEPENDENCIES because PIVOT_WITHIN_MISSION characterization COMPLETE at v34 (run 37677999602). Scientific integrity UNAFFECTED — all evidence ACCEPTED, all tests PASS.

---

## ORCHESTRATION/VALIDATION FAILURE DIAGNOSIS (Reconfirmed)

Root causes persist from v34 audit:
1. **bger_YYYY.jsonl files missing** from canonical corpus for years 2000-2019; only 2020-2024 in raw acquisition
2. **finalize_174k_embeddings.py** asserts full 173k metadata match; checkpoints cover 158k (2000-2023) but 2021-2023 flagged as failed in progress.json
3. **bger_ (unpublished) vs bge_ (published) ID systems** with no cross-mapping
4. **Section extraction** (sachverhalt/erwaegungen/dispositiv) not run at 174k scale
5. **Factory direction v30/v33 claimed 'CORPUS MOUNT PATH GAP RESOLVED'** but /tmp/lex_accepted/core/ does not exist

**Critical note:** 2022-2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75), contradicting progress.json 'failed' flag.

---

## RECOMMENDATION

**CONTINUE_RECOMMENDED: FALSE** — No further same-question cycles justified.

The PIVOT_WITHIN_MISSION is complete. The complementary role of dense embeddings is fully characterized at maximum available evaluated scale. All data blockers require corpus lane resumption (bge_/bger_ mapping, parquet 2024-2026, 174k section extraction).

**Next factory action:** Resume corpus lane for data blockers, or advance to next question when blockers resolved.

---

## PROVENANCE

- **Run ID:** 38017387070
- **Date:** 2026-10-10
- **Factory Direction:** v35
- **Lane State:** legal-distance.json (direction_version=35, evidence_tier=ACCEPTED, cycle_status=BLOCKED_ON_DEPENDENCIES, continue_recommended=false)
- **Accepted Run ID:** LEGAL_DISTANCE_V35_FINAL_AUDIT_VERIFICATION_38014429418
- **Verification Runs:** 38014429418, 38013181156, 38011255223, 38008656246, 38007361758, 38004587384, 37996335430, 37994533831, 37992464015, 37989499846, 37988047526, 37982599815, 37974323040, 37972696947, 37969599517
- **Operational Resume From:** Run 38008189963 (persisted producer snapshot)

---

**AUDIT READY** — All evidence ACCEPTED, all tests PASS, snapshot consistent.