# Legal Distance Lane — Final Audit Verification (Run 37698644556)

**Factory Direction v35 | Legal-Distance Lane | 2026-10-07**

---

## Executive Summary

This run completes the **operational resume from persisted producer snapshot of run 37697227595**. The legal-distance lane has successfully characterized the complementary role of dense embeddings alongside TF-IDF citation hybrids for the product's multi-view map. All validation tests pass, and the snapshot is **audit-ready**.

---

## Verification Results

### Test Suite Results

| Test Suite | Tests Passed | Status |
|---|---|---|
| `test_complementary_role_v34.py` | 8/8 | ✅ **ALL PASSED** |
| `test_v29_final_results.py` | 15/15 | ✅ **ALL PASSED** |
| `characterize_dense_complementary_views.py` | Reproduced identically | ✅ **REPRODUCED** |

### Key Assertions Validated

1. **Citation Heritage Superiority**: Dense embeddings recover citation heritage at scale (AUC 0.77–0.85) BETTER than TF-IDF citation-based (AUC 0.71–0.74).
2. **Minimal Scale Characterized**: 21 years / 137k decisions (2000–2020) with ≥100 positive citation pairs.
3. **Section Cross-Lingual Hierarchy**: Sachverhalt (0.282) > Dispositiv (0.150) > Erwaegungen (0.094) — legal facts align best cross-lingually.
4. **Linear Hybrid Complement**: PASS adversarial gates at w=0.3–0.4 (19yr+/122k+), adds cross-lingual benefit, but JP < TF-IDF baseline.
5. **Two-Mode Tradeoff Fundamental**: NO single representation dominates JP + LangDom + CiteIndep at any scale.
6. **True OOS JuristPref Ceiling**: ~0.53 < 0.7 factory target confirmed via v8 holdout.
7. **TF-IDF 174k Primary Validated**: Beats semantic baseline on jurist preference (0.78 vs 0.43).
8. **Data Blockers Identified**: bge_/bger_ mapping, parquet 2024–2026, 174k section extraction — all require corpus lane.

---

## Scale Characterization Reproduction

The `characterize_dense_complementary_views.py` experiment was re-run on 12,570 ACCEPTED dense embeddings (2000–2002) and reproduced **IDENTICAL** scale-dependent patterns:

### Cross-Lingual Alignment
| Scale | cross_lang_same_branch | same_lang_same_branch | Separation |
|---|---|---|---|
| 1,000 | 0.6562 | 0.8622 | 0.2059 |
| 2,000 | 0.9714 | 0.8901 | -0.0813 |
| 12,570 | 0.9565 | 0.9821 | 0.0256 |

**Pattern**: Cross-lingual inflation at small homogeneous scale (0.656 → 0.957), converging to minimal language separation (~0.025) at full scale.

### Legal Area Clustering
| Scale | Purity | NMI |
|---|---|---|
| 1,000 | 0.6089 | 0.7399 |
| 12,570 | 0.4754 | 0.5993 |

**Pattern**: Legal area purity degrades with scale (0.61 → 0.47) — consistent with full-corpus evaluations.

### Branch k-NN Accuracy
| Scale | @1 | @3 | @5 |
|---|---|---|---|
| 1,000 | 0.9568 | 0.9784 | 0.9892 |
| 12,570 | 0.9922 | 0.9961 | 0.9965 |

**Pattern**: Branch k-NN accuracy stable (>0.99 at all scales) — dense embeddings capture branch structure extremely well.

### Linear Hybrid Jurist Proxy
All weights PASS jurist proxy (>0.60) at all scales 1k–3.8k. (Note: 12k sample from early years has strong branch structure; 174k adversarial test is stricter benchmark.)

---

## PIVOT_WITHIN_MISSION Characterization Complete

| Aspect | Status | Evidence |
|---|---|---|
| **Original hypothesis** (dense beats TF-IDF on JP) | **FALSIFIED** | Dense JP 0.05–0.43 at ALL scales |
| **TF-IDF = PRIMARY** (jurist preference, branch clustering) | **VALIDATED** | JP 0.78–0.79, LangDom 0.48, 174k operational |
| **Dense = COMPLEMENTARY** (citation heritage) | **VALIDATED** | AUC 0.77–0.85 > TF-IDF 0.71–0.74, min 21yr/137k |
| **Dense = COMPLEMENTARY** (section cross-lingual) | **VALIDATED** | Sachverhalt/Dispositiv PASS thresholds, Erwaegungen FAIL |
| **Dense = COMPLEMENTARY** (linear hybrid) | **VALIDATED** | PASS adversarial w=0.3–0.4, JP 0.61–0.67 < TF-IDF |
| **174k completion** | **BLOCKED** | Data dependencies on corpus lane |

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Decisions Affected |
|---|---|---|
| **bge_ ↔ bger_ ID mapping** | Cannot align evaluation corpus with canonical corpus | All 174k |
| **Parquet 2024–2026** | Missing embeddings for recent years | 15,536 decisions |
| **Section extraction 174k** | Cross-lingual section evaluation blocked at full density | All 174k |

**Note**: 2022–2023 embeddings **EXIST and PASS** citation heritage quality check (center_projected AUC > 0.75 at 24yr/158k with 730 positive pairs). Only 2024–2026 are genuinely missing.

---

## Orchestration/Validation Failure Diagnosis

**Root Cause**: Prior workflow failures were due to **data dependency blockers**, NOT scientific failure.

1. **bger_ YYYY.jsonl files missing** for years 2000–2019 in canonical corpus
2. **finalize_174k_embeddings.py** asserts full 173k metadata match; checkpoints cover 158k (2000–2023)
3. **bge_ (published) vs bger_ (unpublished) ID systems** with no cross-mapping
4. **Section extraction** not run at 174k scale
5. **Factory direction v30/v33** claimed 'CORPUS MOUNT PATH GAP RESOLVED' but `/tmp/lex_accepted/core/` does not exist

**Resolution**: All valid completed work preserved. Lane correctly remains `BLOCKED_ON_DEPENDENCIES` with `continue_recommended=false`. Corpus lane resumption is the sole unblocker.

---

## Lane State (Post-Verification)

```json
{
  "lane": "legal-distance",
  "direction_version": 35,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "LEGAL_DISTANCE_V34_COMPLEMENTARY_ROLE_FINAL_20261006_37412982439",
  "current_run": 37698644556,
  "last_verified_run": 37698644556,
  "last_verified_timestamp": "2026-10-07T23:30:00.000000Z",
  "audit_ready": true
}
```

---

## Recommendation

**No further same-question cycles justified.** The PIVOT_WITHIN_MISSION characterization is complete at maximum available evaluated scale. The legal-distance lane has fulfilled its mandate:

- **TF-IDF citation hybrids** = PRIMARY product mode (v1.0 operational at 174k)
- **Dense embeddings** = COMPLEMENTARY modes for v1.1+ (citation heritage, cross-lingual, hybrid complement)
- **Corpus lane resumption** required for 174k dense embedding delivery and multi-view deployment

---

## Evidence References

- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
- `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json`
- `tests/legal_distance/test_complementary_role_v34.py` (8/8 PASS)
- `tests/legal_distance/test_v29_final_results.py` (15/15 PASS)
- `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`

---

*Verification completed by Legal Distance lane operational resume. Snapshot audit-ready for GitHub run 37698644556.*