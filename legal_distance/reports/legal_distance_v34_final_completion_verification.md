# Legal Distance Lane v34 — Final Completion Verification

**Date:** 2026-10-07  
**Factory Direction Version:** 34  
**Lane:** legal-distance  
**GitHub Run:** 37577737138  
**Status:** COMPLETE — BLOCKED_ON_DEPENDENCIES (correctly)  
**Evidence Tier:** ACCEPTED  
**Continue Recommended:** FALSE  

---

## Question Answered

> **What minimal dense embedding scale and which specific dense modes (citation heritage, section cross-lingual, linear hybrid complement) are necessary and sufficient for the product's non-jurist-preference views?**

**ANSWERED** with ACCEPTED evidence at maximum available evaluated scale (24yr/158k citation heritage, 174k formal suite, 1K section cross-lingual).

---

## Summary of Findings (All ACCEPTED/REPRODUCED)

### 1. Citation Heritage View — NECESSARY & SUFFICIENT
| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Minimal scale | 21yr / 137k decisions (2000-2020) | — | ✅ |
| Sufficient scale | 22yr / 144k (344 positive pairs) | — | ✅ |
| Best mode | `center_projected_64dim` | — | ✅ |
| Raw 768dim AUC | 0.7946 (22yr), 0.7696 (24yr) | > 0.75 | ✅ |
| CP64 AUC | 0.7922 (22yr), 0.7667 (24yr) | > 0.75 | ✅ |
| TF-IDF citation baseline AUC | 0.71-0.74 | — | Dense **SUPERIOR** |
| Similarity gap (CP64) | 0.410 | — | 6.5× raw gap |

**Product Integration:** View `citation_heritage`, default `center_projected_64dim`, **READY at 144k**.

---

### 2. Section Cross-Lingual View — NECESSARY, SUFFICIENT AT SAMPLE, BLOCKED AT FULL CORPUS
| Section | n (sample) | CP64 cross_lang_same_branch | Threshold | Invariance Gap | Status |
|---------|------------|-----------------------------|-----------|----------------|--------|
| Sachverhalt (facts) | 359 | **0.282** | > 0.2 | 0.187 | ✅ PASS |
| Dispositiv (holding) | 538 | **0.150** | > 0.1 | 0.397 | ✅ PASS |
| Erwaegungen (reasoning) | 510 | 0.094 | > 0.1 | 0.452 | ❌ FAIL |

**Hierarchy confirmed:** Sachverhalt > Dispositiv > Erwaegungen (facts align best cross-lingually; reasoning most language-specific).

**Center projection improves all sections:** 16-38% gap reduction vs raw 768dim.

**Product Integration:** View `cross_lingual`, default `center_projected_64dim` per section, **SAMPLE ONLY — BLOCKED** pending 174k section extraction.

---

### 3. Linear Hybrid Complement — SUFFICIENT FOR CROSS-LINGUAL BENEFIT
| Scale | Optimal Weight | JP | LangDom | Both Gates | TF-IDF Baseline JP |
|-------|----------------|-----|---------|------------|-------------------|
| 15yr (92k) | — | 0.473 | 0.809 | ❌ FAIL | — |
| 19yr (122k) | w=0.3 | 0.637-0.647 | 0.626-0.662 | ✅ PASS | 0.724 |
| 22yr (144k) | w=0.3-0.4 | 0.612-0.673 | 0.639-0.748 | ✅ PASS | 0.784-0.789 |

**Cross-lingual improvement:** Hybrid w=0.4 cross_lang_same_branch = 0.160 vs TF-IDF 0.124 (+29%).

**Critical:** Does **NOT** beat TF-IDF on jurist preference — marked **exploratory mode**.

**Product Integration:** View `hybrid_complement`, default `linear_citation_concat_w0.4` (22yr), **READY at 144k**.

---

### 4. Two-Mode Tradeoff — FUNDAMENTAL (Reproduced at ALL Scales)
| Representation | LangDom | JP | CiteIndep |
|----------------|---------|-----|-----------|
| TF-IDF citation hybrids | ~0.48 | ~0.78 | ~14% |
| Dense semantic (CP) | 0.83-0.98 | 0.05-0.43 | ~37% |
| Linear hybrids | 0.58-0.80 | 0.61-0.67 | ~25-35% |

**Conclusion:** NO single representation dominates all three metrics at any scale. TF-IDF = PRIMARY (jurist preference, branch clustering). Dense = COMPLEMENTARY (citation heritage, cross-lingual, hybrid complement).

---

### 5. True OOS JuristPref Ceiling
- **Ceiling:** ~0.53 (v8 holdout zero-shot validation)
- **Factory target:** 0.7
- **Achievable:** **FALSE** — no representation reaches target under true OOS conditions

---

## Data Blockers (Require Corpus Lane Resumption)

| Blocker | Impact | Status |
|---------|--------|--------|
| BGE/bger ID mapping | Canonical corpus uses bge_ IDs, evaluation uses bger_ IDs — no mapping exists | ❌ UNRESOLVED |
| Parquet 2024-2026 | ~15.5k decisions missing (3 years) | ❌ UNRESOLVED |
| 174k section extraction | Sachverhalt/Erwaegungen/Dispositiv not extracted at 174k scale | ❌ UNRESOLVED |

**Note:** 2021-2023 embeddings EXIST and PASS citation heritage quality check (CP AUC > 0.75 at 24yr/158k with 730 positive pairs). Only 2024-2026 are genuinely missing.

---

## Test Results (All 8/8 PASS)

```
✅ test_citation_heritage_superiority
✅ test_citation_heritage_minimal_scale
✅ test_section_crosslingual_hierarchy
✅ test_linear_hybrid_optimal_weight
✅ test_two_mode_tradeoff_fundamental
✅ test_true_oos_ceiling
✅ test_tfidf_174k_primary_validated
✅ test_data_blockers_identified
```

---

## State File Verification

```json
{
  "lane": "legal-distance",
  "direction_version": 34,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "LEGAL_DISTANCE_V34_COMPLEMENTARY_ROLE_FINAL_20261006_37412982439",
  "tests_passed": 8
}
```

---

## Strategic Pivot Confirmed (Per Factory Direction v34)

| Mode | Role | Status |
|------|------|--------|
| TF-IDF citation hybrids | **PRIMARY** (jurist preference, branch clustering) | ✅ OPERATIONAL at 174k |
| Dense embeddings | **COMPLEMENTARY** (citation heritage, cross-lingual, hybrid complement) | ✅ CHARACTERIZED |
| Linear hybrids | EXPLORATORY (cross-lingual benefit only) | ✅ DEFINED |

**Product v1.0:** TF-IDF citation hybrids as primary navigation mode (JP 0.78 vs semantic baseline 0.43)  
**Product v1.1+:** Dense embedding integration for citation-heritage view and cross-lingual view

---

## Recommendation

**NO FURTHER SAME-QUESTION CYCLES JUSTIFIED.** The question has been fully answered with ACCEPTED evidence. The lane is correctly BLOCKED_ON_DEPENDENCIES awaiting corpus lane resolution of:
1. BGE/bger ID mapping
2. Parquet generation for 2024-2026
3. 174k section extraction

When corpus lane delivers these, the NEXT question for legal-distance would be: **174k-scale validation of characterized complementary modes** (citation heritage at 174k, section cross-lingual at full corpus density, linear hybrid complement at 174k).

---

## Evidence References

- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_21year_latest.json`
- `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_24year_latest.json`
- `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json`
- `legal_distance/results/174k_dense_embeddings/linear_combinations_weight_sweep_22year/weight_sweep_22year_latest.json`
- `legal_distance/results/174k_dense_embeddings/evaluation_22year_center_projected/combined_results.json`
- `legal_distance/results/dense_complementary_characterization/scale_characterization_results.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `/tmp/lex_accepted/evaluation/results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_results.json`
- `legal_distance/results/v8/holdout_zero_shot_validation_fixed/holdout_zero_shot_validation_fixed.json`
- `legal_distance/results/174k_dense_embeddings/checkpoints/progress.json`

---

**Verification Complete.** The legal-distance lane has fulfilled its v34 mission. All characterizations are ACCEPTED and reproducible. The strategic pivot to TF-IDF primary / dense complementary is evidence-backed and documented.