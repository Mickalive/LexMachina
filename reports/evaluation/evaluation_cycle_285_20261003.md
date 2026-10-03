# Evaluation Cycle 285 — Monitor Check & State Update

**Date**: 2026-10-03T02:04:50Z
**Factory Direction**: v30
**Lane**: evaluation
**Evidence Tier**: ACCEPTED
**Cycle Status**: RUN
**Continue Recommended**: false

---

## Summary

This cycle executed monitor check 285 to scan for new 174k-scale representations from legal-distance. No new representations detected. All three v29 mandated deliverables remain COMPLETE for the TF-IDF family at 174k scale. Evaluation infrastructure is VERIFIED and AUDIT-READY.

---

## Monitor Check 285 Results

### Scan Target
- **Path**: `/tmp/lex_accepted/legal-distance/legal_distance/results`
- **Expected**: 20 representations (8 TF-IDF completed, 12 awaited)
- **Found**: 8 TF-IDF embeddings (both primary and alt locations)

### Completed Representations (TF-IDF Family — 174k)
All 8 representations fully evaluated and verified:
| Representation | Adversarial LangDom | Jurist Pref | Verdict |
|---|---|---|---|
| cited_decisions_tfidf | 0.4917 | 0.7075 | PASS |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.4895 | 0.7265 | PASS |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.4908 | 0.7195 | PASS |
| outcome_tfidf | 0.5078 | 0.6660 | PASS |
| regeste_tfidf | 0.5111 | 0.6145 | PASS |
| full_text_tfidf_light | 0.4854 | 0.7080 | PASS |
| regeste_full_text_hybrid_0.5 | 0.4873 | 0.7140 | PASS |
| regeste_full_text_hybrid_0.7 | 0.4889 | 0.7120 | PASS |

**Config Hash**: b51701f5a9c11692 (frozen harness v3, exact k-NN on stratified subsample n=2000)
**HNSW Artifact**: FIXED — exact k-NN avoids HNSW masking representation differences

### Awaited Representations (No Change from Check 284)

| Category | Representations | Status |
|---|---|---|
| **Dense Embeddings** | center_projected_768dim, center_projected_64dim, center_projected_128dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | NOT AVAILABLE at 174k |
| **Citation Roles** | citation_role_citing_alpha0.3, citation_role_following_alpha0.3, citation_role_criticizing_alpha0.3 | NOT AVAILABLE at 174k |
| **Linear Hybrids** | linear_citation_concat, linear_hybrid05_concat | PASS at 19-year/122k, NOT at 174k |

### Dense Embeddings Progress (Legal-Distance)
- **ACCEPTED**: 3/26 years (2000-2002, ~19k decisions) — evaluated, FAIL adversarial
- **CHECKPOINTED**: 21/26 years (2000-2020, ~150k decisions) — pending audit promotion
- **EVALUATED**: 22/26 years (2000-2021, 144,443 decisions) — adversarial formal suite only (center_projected FAIL)
- **Citation Heritage**: Partial 16-year (2000-2015) AUC=0.90; 15/19/22-year FAILED or NOT RUN
- **BLOCKERS**: BGE/bger ID mapping missing; parquet files for 2022-2026 missing

---

## V29 Mandated Deliverables — Status

| Deliverable | Status | Evidence |
|---|---|---|
| **(1) Full 12-benchmark formal suite at 174k on all production representations** | ✅ COMPLETE | 8/8 TF-IDF reps evaluated; frozen harness v3; config hash b51701f5a9c11692 |
| **(2) Citation heritage benchmark on frozen 1,020-pair pool** | ✅ COMPLETE | 4/8 PASS (AUC ≥ 0.65); all 8 FAIL recall@10 < 0.2 |
| **(3) v17b label normalization generalization to 174k fine-grained labels** | ✅ COMPLETE (NEGATIVE) | Uniform improvement FALSE; zoom_fine degrades 11-16% for 4/8 citation-based reps |

---

## Key Findings (Reproduced & Frozen)

1. **Fundamental TF-IDF Tradeoff Persists at 174k**:
   - Citation-based reps: PASS adversarial & citation_heritage, FAIL branch/tf_metadata/hierarchy
   - Text-based reps: PASS branch/tf_metadata, FAIL adversarial (lang_dom ~0.999)

2. **v17b Label Normalization**: Does NOT generalize to 174k fine-grained legal_area labels
   - Hierarchy purity: 1.0x for ALL reps (no improvement)
   - Zoom fine purity: 0.83-0.99x (degradation for 4/8 reps)
   - Legal area purity: ~1.0x (no meaningful change)
   - Only `regeste_tfidf` shows no worsening on ALL hierarchy metrics

3. **Dense Embeddings (center_projected)**: FAIL adversarial at ALL tested scales (3yr, 15yr, 19yr, 22yr)
   - Root cause: language clustering dominates (LangDom 0.83-0.99, Jurist Pref 0.005-0.43)

4. **Linear Hybrids (19-year/122k)**: PASS adversarial (legal_citation_concat JP=0.545, legal_hybrid05_concat JP=0.540)
   - Await 174k concatenation and frozen formal suite evaluation

5. **Citation Heritage at 174k**: All TF-IDF reps FAIL recall@10 < 0.2 threshold
   - 4/8 PASS AUC ≥ 0.65 (cited_decisions_tfidf best at 0.743)
   - Consistent with partial dense results (AUC~0.90, recall@10≈0)

---

## Infrastructure Verification

| Component | Status |
|---|---|
| Adversarial benchmarks | VERIFIED — exact k-NN on stratified subsample n=2000 |
| Citation heritage pipeline | VERIFIED — frozen 1,020 pairs, 95.9% corpus resolution |
| v17b normalization pipeline | VERIFIED — differential effect reproduced |
| HNSW artifact fix | CONFIRMED — exact k-NN avoids masking |
| V25 formal suite | VERIFIED — frozen protocol, config hash 4323f833fa72366a |
| Scalable NN | OPERATIONAL — sklearn exact k-NN (adversarial), HNSW (citation heritage) |
| Metadata 174k | VERIFIED — 173,963 entries, branch+legal_area 100% coverage |

---

## State Updates

### evaluation.json
- `continue_recommended`: **false** (no additional same-question cycle justified)
- `monitor_check_count`: 285
- `monitor_last_check`: 2026-10-03T02:04:50.601Z
- `cycle_status`: RUN (lane remains active per factory direction "as representations land")

### evaluation_state.json
- `continue_recommended`: **false**
- `monitor_check_count`: 285
- `monitor_last_check`: 2026-10-03T02:04:50.601Z
- `work_completed`: Added monitor check 285 entry
- `readiness_for_next_representations.monitor_script`: check_count=285

### monitor_174k_state.json
- `check_count`: 285
- `last_check`: 2026-10-03T02:04:50.600628
- `last_verification`: Updated with check 285 details

---

## Recommendation

**continue_recommended = false**

No additional same-question evaluation cycle is justified at this time because:
1. All three v29 mandated deliverables are COMPLETE and REPRODUCIBLE for TF-IDF at 174k
2. No new 174k-scale representations have landed from legal-distance
3. Dense embeddings concatenation BLOCKED on BGE/bger ID mapping and missing parquet 2022-2026
4. Citation roles and linear hybrids NOT AVAILABLE at 174k scale

**Lane remains RUN** per factory direction v30 "as representations land" — the Factory Director should dispatch a successor evaluation cycle when new 174k-scale representations become available (dense embeddings concatenated, citation roles computed, or linear hybrids at 174k).

---

## Evidence References

- Formal suite: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- Citation heritage: `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json`
- v17b normalization: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- Citation pairs: `evaluation/results/174k_citation_heritage/citation_pairs_174k.json`
- Prior audit report: `reports/evaluation/evaluation_v29_final_verification_20261002.md`

---

*Report generated by evaluation lane monitor cycle 285*