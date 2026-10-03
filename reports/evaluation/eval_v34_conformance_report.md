# Evaluation Lane Conformance Report — Factory Direction v34

## Mission Status: COMPLETE (ACCEPTED)

**Lane**: evaluation  
**Direction Version**: 34  
**Evidence Tier**: ACCEPTED  
**Cycle Status**: RUN → COMPLETE  
**Continue Recommended**: FALSE  
**Accepted Run ID**: `eval_174k_v34_acceptance_criteria_20261003`

---

## Summary

The evaluation lane has successfully completed its work for factory direction v34:

1. **TF-IDF 174k evaluation FROZEN as production baseline** — All 8 TF-IDF representations evaluated at 173,963 decisions on frozen harness v3. Best production default: `cited_decisions_tfidf_outcome_hybrid_0.5` (LangDom=0.4895, JP=0.7265). Citation-based modes dominate jurist preference; text-based modes fail adversarial language dominance (~0.999).

2. **Dense embedding acceptance criteria VALIDATED** against 22-year/144k legal-distance evidence:
   - Citation heritage AUC 0.79 **PASS** (>0.75 threshold) — dense embeddings EXCEL vs TF-IDF citation-based (AUC 0.71-0.74)
   - Section cross-lingual sachverhalt 0.282 **PASS** (>0.2 threshold)
   - Section cross-lingual dispositiv 0.148 **PASS** (>0.1 threshold)
   - Section cross-lingual erwaegungen 0.093 **FAIL** (<0.1 threshold)
   - Jurist pairwise preference 0.39-0.42 **FAIL** at ALL scales (<0.5 threshold)
   - Cross-language retrieval recall@10 ~0.04-0.11 **FAIL** (threshold 0.2)

   **Conclusion**: Dense embeddings are **COMPLEMENTARY VIEWS ONLY** (citation heritage recovery, cross-lingual alignment for sachverhalt/dispositiv). Not suitable as primary navigation mode.

3. **No 174k dense embeddings available** — blocked on corpus lane deliverables:
   - bge_/bger_ ID mapping (canonical corpus uses bge_ IDs, evaluation uses bger_ IDs)
   - Parquet generation for years 2022-2026 (29,520 decisions missing)

4. **No additional same-question cycle justified** until 174k dense embeddings land.

---

## Conformance Test Results

All conformance tests for the v25 174k formal-suite snapshot **PASS**:

| Test | Status | Details |
|------|--------|---------|
| Embedding inventory | ✅ PASS | 8 npy files, shape (173963, 128), float32, finite, zero-row pattern consistent |
| Hybrid exact reconstruction | ✅ PASS | All 4 hybrids bitwise exact functions of 4 base embeddings (seed 42, sklearn L2-normalize) |
| Fixed subsample determinism | ✅ PASS | `hierarchy_subsample_15000_seed42` and `temporal_subsample_30000_seed42` reproduce exactly from metadata |
| Suite/summary consistency | ✅ PASS | Per-rep results agree with `_suite_summary.json`; dedicated CH files agree with suite CH benchmark |
| Frozen thresholds | ✅ PASS | All 12 benchmarks carry frozen v16/v3 thresholds; `config_hash_suite == 4323f833fa72366a` |
| Citation heritage spot check | ✅ PASS | Independent AUC-ROC on seed-42 2000+2000 pair subsample matches frozen values within 0.005 for 4 checked reps |
| v17b label-level record | ✅ PASS | 214 raw → 164 normalized unique legal_area labels, 49.3% changed, 47.6% unknown (frozen counts) |
| v17b provenance gate | ✅ PASS | GATE_OVERALL=PASS (P1/P2/P4 PASS, P3 warnings confined to degenerate triple, NC_swap/NC_fileid PASS) |

---

## Adversarial Gate Results (Frozen Harness v3)

| Representation | Language Dominance (<0.85) | Branch Coherence (>0.3) | Both Gates |
|----------------|---------------------------|------------------------|------------|
| cited_decisions_tfidf | 0.6018 ✅ | 0.3540 ✅ | **PASS** |
| cited_outcome_hybrid_0.5 | 0.5785 ✅ | 0.3520 ✅ | **PASS** |
| cited_outcome_hybrid_0.7 | 0.5690 ✅ | 0.3560 ✅ | **PASS** |
| regeste_tfidf | 0.7568 ✅ | 0.6153 ✅ | **PASS** |
| outcome_tfidf | 0.5099 ✅ | 0.1462 ❌ | FAIL |
| full_text_tfidf_light | 0.9999 ❌ | 0.7420 ✅ | FAIL |
| regeste_full_text_hybrid_0.5 | 0.9982 ❌ | 0.9562 ✅ | FAIL |
| regeste_full_text_hybrid_0.7 | 0.9994 ❌ | 0.9608 ✅ | FAIL |

**Production baseline**: `cited_decisions_tfidf_outcome_hybrid_0.5` (best jurist preference among PASSing modes)

---

## Dense Embedding Acceptance Criteria Validation

| Criterion | Threshold | Evidence (22-year/144k) | Status |
|-----------|-----------|------------------------|--------|
| Citation heritage AUC | > 0.75 | 0.7916–0.7941 (center_projected 64/128/768dim) | ✅ PASS |
| Cross-lang same-branch (sachverhalt) | > 0.2 | 0.2816 (center_projected 64/768dim) | ✅ PASS |
| Cross-lang same-branch (dispositiv) | > 0.1 | 0.1481–0.1502 | ✅ PASS |
| Cross-lang same-branch (erwaegungen) | > 0.1 | 0.0925–0.0941 | ❌ FAIL |
| Jurist pairwise preference | > 0.5 | 0.389–0.418 (165k) | ❌ FAIL |
| Cross-language retrieval recall@10 | > 0.2 | ~0.04–0.11 | ❌ FAIL |

---

## Critical Findings

### TF-IDF 174k Production Baseline Frozen
- All 8 representations evaluated at full 173,963 decisions
- 4/8 PASS both adversarial gates (citation-based + hybrids)
- Best: `cited_decisions_tfidf_outcome_hybrid_0.5` (JP=0.7265)
- Fundamental tradeoff: citation-based → jurist preference; text-based → language dominance

### Dense Embedding Complementary Role Confirmed
- **Citation heritage recovery**: Dense AUC 0.79 vs TF-IDF citation-based 0.71-0.74 → dense WINS
- **Section cross-lingual hierarchy**: Sachverhalt > Dispositiv > Erwaegungen (facts align best)
- **Jurist preference**: Dense FAILS at all scales (JP 0.39-0.42) → NOT primary navigation
- **Boilerplate resistance**: Dense FAILS (boilerplate neighbor rate ~0.94)

### v17b Label Normalization at 174k
- Tested on 15k subsample (213 → 111 labels)
- Purity ratios 5x–10x but NMI decreases on normalized labels
- Different regime from v17b 1K scale; does NOT generalize in same-magnitude sense

### v18 Coarse Hierarchy: NEGATIVE
- Even at 4-label branch level: best purity 0.65 < 0.7 threshold
- NMI ~0.004–0.30
- Fundamental hierarchy limitation for TF-IDF/citation representations

---

## Evidence References

1. `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — Full 12-benchmark suite for 8 reps
2. `results/evaluation/v25_174k_citation_heritage/cited_decisions_tfidf.json` — Dedicated citation heritage validation
3. `results/evaluation/v17b_174k_generalization/v17b_174k_generalization_latest.json` — Label normalization generalization test
4. `results/evaluation/v18_coarse_hierarchy/v18_coarse_hierarchy_latest.json` — Coarse hierarchy negative result
5. `results/evaluation/partial_dense_2000_2002/evaluation_partial_dense_latest.json` — 3-year dense + 22-year evidence synthesis
6. `legal_distance/results/174k/dense_165k_formal_suite/evaluation_165k_dense_formal_suite_latest.json` — 165k dense formal suite
7. `legal_distance/results/174k_dense_embeddings/citation_heritage_eval/citation_heritage_22year_latest.json` — 22-year citation heritage
8. `legal_distance/results/174k_dense_embeddings/section_crosslingual_eval/section_crosslingual_eval_latest.json` — Section cross-lingual alignment

---

## Next Recommendation

**TF-IDF 174k evaluation FROZEN as production baseline. Dense embedding acceptance criteria VALIDATED. No additional same-question cycle justified until corpus lane delivers 174k dense embeddings (bge_/bger_ ID mapping + parquet 2022-2026).**

The Factory Director will determine the successor evaluation question when the data blocker is resolved.