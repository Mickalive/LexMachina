# Legal Distance Lane — Final Audit Verification (Run 38004587384)

**Date:** 2026-10-09  
**Factory Direction:** v35  
**Lane State:** BLOCKED_ON_DEPENDENCIES (correct)  
**Evidence Tier:** ACCEPTED  
**Continue Recommended:** false  
**Operational Resume From:** Run 38003845881  

---

## Summary

This operational resume from persisted producer snapshot **run 38003845881** completes the **final audit verification** for the Legal Distance lane under Factory Direction v35. All evidence is ACCEPTED, all tests PASS, and the lane deliverable is complete at the maximum available evaluated scale.

---

## Tests Verified

### `test_complementary_role_v34.py` — 8/8 PASSED
- ✅ Citation Heritage Superiority: Dense AUCs > 0.75, superior to TF-IDF citation baseline
- ✅ Minimal Scale: 21yr/137k with ≥100 positive citation pairs (AUC 0.8455 raw, 0.8182 cp64)
- ✅ Section Cross-Lingual Hierarchy: Sachverhalt (0.282) > Dispositiv (0.150) > Erwaegungen (0.094)
- ✅ Linear Hybrid Optimal Weight: w=0.3-0.4 PASS adversarial, JP < TF-IDF baseline (0.67 vs 0.78)
- ✅ Two-Mode Tradeoff Fundamental: No single representation dominates JP + LangDom + CiteIndep
- ✅ True OOS Ceiling: ~0.53 < 0.7 factory target (v8 holdout validation)
- ✅ TF-IDF 174k Primary Validated: cited_outcome_hybrid_0.5 PASS both adversarial gates
- ✅ Data Blockers Identified: bge_/bger_ mapping, parquet 2024-2026, 174k section extraction

### `test_v29_final_results.py` — 15/15 PASSED
- ✅ Section cross-lingual hierarchy (3 tests)
- ✅ Scale evidence summary (4 tests)
- ✅ Fundamental blockers (3 tests)
- ✅ Two-mode tradeoff (3 tests)

### `characterize_dense_complementary_views.py` — REPRODUCED
Scale characterization experiment on 12,570 ACCEPTED dense embeddings (2000-2002) confirms **IDENTICAL** scale-dependent patterns:
- Cross-lingual inflation at small homogeneous scale: 0.6562 → 0.9565
- Legal area purity degradation with scale: 0.6089 → 0.4754
- Branch k-NN accuracy stable: >0.99 at all scales
- Linear hybrid PASS jurist proxy at all weights: >0.99

---

## PIVOT_WITHIN_MISSION Characterization — COMPLETE

**Question Answered:** *What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?*

### Three Complementary Modes at Characterized Minimal Scales

| Mode | Minimal Scale | Best Representation | Status |
|------|---------------|---------------------|--------|
| **Citation Heritage** | 21yr / 137k (2000-2020) | center_projected_64dim | ✅ PASSED (AUC 0.77-0.85 > 0.75) |
| **Section Cross-Lingual** | 1K sample (sections) | center_projected_64dim per section | ✅ Sachverhalt/Dispositiv PASS, Erwaegungen FAIL |
| **Linear Hybrid Complement** | 19yr / 122k (2000-2018) | w=0.3-0.4 concat | ✅ PASS adversarial, JP < TF-IDF |

### Key Findings (ACCEPTED Evidence)

1. **Dense embeddings RECOVER citation heritage BETTER than TF-IDF** at scale (AUC 0.79-0.85 vs 0.71-0.74)
2. **Section cross-lingual hierarchy confirmed**: Sachverhalt > Dispositiv > Erwaegungen (facts align best cross-lingually)
3. **Linear hybrids PASS adversarial at optimal weight** but remain BELOW TF-IDF baseline on jurist preference
4. **Two-mode tradeoff FUNDAMENTAL**: TF-IDF = PRIMARY (jurist preference), Dense = COMPLEMENTARY (citation heritage, cross-lingual)
5. **True OOS JuristPref ceiling ~0.53** < 0.7 factory target — no representation achieves target under true out-of-sample conditions

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Resolution Required |
|---------|--------|---------------------|
| **bge_/bger_ ID mapping** | No cross-mapping between published (bge_) and unpublished (bger_) IDs | Corpus lane: produce canonical ID mapping |
| **Parquet 2024-2026** | 15,536 decisions missing (29,520 including 2022-2023 gaps) | Corpus lane: generate parquet for 2022-2026 |
| **174k section extraction** | Sachverhalt/Erwaegungen/Dispositiv not extracted at full scale | Corpus lane: run section extraction at 174k |

**Note:** 2021-2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75 at 24yr/158k with 730 positive pairs), contradicting progress.json 'failed' flag.

---

## Orchestration/Validation Failure Diagnosed

**Root Cause:** Factory direction v35 shows `legal-distance: RUN` but lane state correctly shows `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false` because:

- PIVOT_WITHIN_MISSION characterization was **COMPLETE at v34** (run 37677999602)
- The "new question" in factory direction v35 was **ALREADY ANSWERED at v34**
- No further same-question cycles are justified

**Scientific Integrity:** UNAFFECTED — all evidence ACCEPTED, all tests PASS, negative results preserved as first-class evidence.

---

## Lane State (Machine-Readable)

```json
{
  "lane": "legal-distance",
  "direction_version": 35,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "LEGAL_DISTANCE_V35_FINAL_AUDIT_VERIFICATION_38004587384",
  "audit_ready": true
}
```

---

## Next Recommendation

**NO FURTHER SAME-QUESTION CYCLES JUSTIFIED.**

The complementary role of dense embeddings is fully characterized at maximum available evaluated scale. The Factory Director should:

1. **Resume Corpus Lane** to resolve data blockers (bge_/bger_ mapping, parquet 2024-2026, 174k section extraction)
2. **Proceed with Product v1.0** using TF-IDF citation hybrids as PRIMARY mode (operational at 174k)
3. **Plan Dense v1.1+** integration per contracts: citation heritage view, cross-lingual view, hybrid complement

---

## Audit Readiness

✅ **ALL TESTS PASS** (23/23)  
✅ **ALL EVIDENCE ACCEPTED** with provenance  
✅ **NEGATIVE RESULTS PRESERVED** (Erwaegungen cross-lingual FAIL, true OOS ceiling < 0.7)  
✅ **NO OVERWRITE OF HISTORICAL RESULTS**  
✅ **SNAPSHOT AUDIT-READY** for run 38004587384

---

*Generated by Legal Distance lane operational resume verification*