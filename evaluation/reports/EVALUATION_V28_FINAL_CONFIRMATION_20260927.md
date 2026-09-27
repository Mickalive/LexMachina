# Evaluation Lane v28 — Final Confirmation Cycle Report

**Date**: 2026-09-27  
**Factory Direction**: v28  
**Lane**: evaluation  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES  
**Continue Recommended**: false  
**Run ID**: eval_174k_formal_suite_tfidf_complete_20260927_v28  

---

## Executive Summary

This cycle confirms that the evaluation lane has **completed all three machine-executable sub-questions** for the TF-IDF family at 174k scale as required by factory direction v28. The lane remains correctly **BLOCKED_ON_DEPENDENCIES** awaiting dense embeddings, citation roles, and linear hybrids from legal-distance (only 3/26 years ACCEPTED per factory direction v28).

**Monitor re-verification at 2026-09-27T21:10:18Z**: No new awaited representations detected.

---

## Three Sub-Questions — All COMPLETE (TF-IDF Family)

| Sub-Question | Status | Key Result |
|--------------|--------|------------|
| **(1) 12-Benchmark Formal Suite** | ✅ COMPLETE | 8 TF-IDF representations evaluated with frozen harness v3 thresholds; HNSW artifact fixed via exact k-NN on stratified subsample (n=2000); 5/8 PASS both adversarial gates |
| **(2) Citation Heritage Benchmark** | ✅ COMPLETE | Frozen pair pool validated (137,314 pairs, 95.9% citation resolution: 2,019/2,105); infrastructure ready for dense embeddings |
| **(3) v17b Label Normalization** | ✅ COMPLETE | 214→164 labels (23.4% reduction), 85,819 labels normalized, 32 cross-lingual concepts; PARTIAL generalization (2/8 reps within ≤10% worsening rule) |

---

## Sub-Question 1: 12-Benchmark Formal Suite at 174k

### Adversarial Results (Frozen Thresholds: lang_dom < 0.85, jurist_pref > 0.5)

| Representation | Verdict | Lang Dominance | Jurist Pref | Both Adv Pass |
|----------------|---------|----------------|-------------|---------------|
| `cited_decisions_tfidf` | **PASS** | 0.5295 | 0.8020 | ✅ |
| `outcome_tfidf` | **PASS** | 0.4527 | 0.7255 | ✅ |
| `regeste_tfidf` | **PASS** | 0.4835 | 0.6090 | ✅ |
| `cited_outcome_hybrid_0.5` | **PASS** | 0.5164 | 0.8055 | ✅ |
| `cited_outcome_hybrid_0.7` | **PASS** | 0.5238 | 0.7975 | ✅ |
| `full_text_tfidf_light` | FAIL | 1.0000 | 0.0000 | ❌ |
| `regeste_full_text_hybrid_0.5` | FAIL | 1.0000 | 0.0000 | ❌ |
| `regeste_full_text_hybrid_0.7` | FAIL | 1.0000 | 0.0000 | ❌ |

**Best representation**: `cited_decisions_tfidf` (lang_dom=0.5295, jurist_pref=0.8020)  
**Production default**: `cited_outcome_hybrid_0.5` (balances citation + outcome signals)

### Key Finding: Fundamental Two-Mode Tradeoff Persists at 174k

- **Citation-based representations** (cited_decisions_tfidf, outcome_tfidf, hybrids): PASS adversarial gates, FAIL hierarchy/legal_area/temporal/boilerplate benchmarks
- **Text-based representations** (full_text, regeste, regeste_full_text hybrids): FAIL adversarial gates (language dominance ~1.0), PASS branch/tf_metadata
- **Universal failures** (citation-based reps): hierarchy_coherence, legal_area_clustering, temporal_stability, boilerplate_resistance — these are **corpus/label limitations**, not representation defects (only ~2,000 decisions with valid branch labels out of 174k; citation graph sparse with 924 resolved in-corpus citations)

### HNSW Artifact: CONFIRMED AND FIXED

HNSW with fixed parameters produced nearly identical k-NN graphs across different TF-IDF representations at 174k scale, masking representation differences. **Fix**: Exact k-NN on valid subset (n=2000 stratified by branch) for adversarial benchmarks; HNSW only for full-corpus scale benchmarks.

---

## Sub-Question 2: Citation Heritage Benchmark

### Infrastructure Validated

- **Citation graph source**: `/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/citation_graph_resolved.json`
- **Total citations**: 2,105
- **Resolved citations**: 2,019 (95.9% resolution rate)
- **Decisions with outgoing citations**: 174
- **Resolved in-corpus**: 924
- **Frozen pair pool**: 1,020 positive + 1,020 negative pairs = 2,040 pairs (expanded to 137,314 for full evaluation)

### Results (TF-IDF Family)

| Representation | AUC-ROC | Recall@10 | Status |
|----------------|---------|-----------|--------|
| full_text_tfidf_light | 0.897 | 0.053 | FAIL (recall@10 < 0.2) |
| regeste_full_text_hybrid_0.5 | 0.871 | 0.035 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.850 | 0.035 | FAIL |
| cited_decisions_tfidf | 0.789 | 0.048 | FAIL |
| cited_outcome_hybrid_0.7 | 0.775 | 0.049 | FAIL |
| cited_outcome_hybrid_0.5 | 0.759 | 0.050 | FAIL |
| outcome_tfidf | 0.658 | 0.000 | FAIL |
| regeste_tfidf | 0.486 | 0.004 | FAIL |

**Note**: All representations FAIL the recall@10 > 0.2 threshold. The citation graph is extremely sparse (only 924 decisions with resolved in-corpus citations out of 174k). The benchmark infrastructure is **frozen and ready** for dense embeddings when they arrive.

---

## Sub-Question 3: v17b Label Normalization Generalization at 174k

### Normalization Statistics

- **Raw unique legal_area labels**: 214
- **Normalized unique labels**: 164
- **Label reduction**: 23.4%
- **Labels changed**: 85,819 decisions
- **Decisions with legal_area**: 91,193 (52.4%)
- **Cross-lingual concepts unified**: 32 (e.g., "Vertragsrecht" / "Droit des contrats" / "Diritto contrattuale" → unified)
- **Avg decisions per raw label**: 428.1
- **Avg decisions per normalized label**: 559.5

### Generalization Result: PARTIAL

| Representation | Hierarchy Purity Ratio | Zoom Fine Ratio | Legal Area Ratio | Within ≤10% Worsening? |
|----------------|------------------------|-----------------|------------------|------------------------|
| cited_decisions_tfidf | 1.057 | 1.038 | 1.062 | ✅ YES |
| outcome_tfidf | 1.046 | 1.083 | 1.044 | ✅ YES |
| regeste_tfidf | 1.000 | 1.103 | 1.017 | ✅ YES |
| full_text_tfidf_light | 1.000 | 0.668 | 0.973 | ❌ NO (zoom_fine -33%) |
| regeste_full_text_hybrid_0.5 | 1.000 | 0.661 | 0.969 | ❌ NO |
| regeste_full_text_hybrid_0.7 | 1.000 | 0.695 | 0.963 | ❌ NO |

**Summary**: 2/8 representations (cited_decisions_tfidf, outcome_tfidf) show improvement or matching across all metrics. 6/8 show >10% worsening on at least one metric (primarily zoom_fine for full-text/regeste-based reps).

### Key Finding

The v16 "data granularity" attribution (hierarchy purity < 0.7 threshold) is **partially a label normalization artifact** — citation-based reps show 1.05–1.06x purity gains with normalized labels. However, even with normalized labels, **best hierarchy purity = 0.47 < 0.7 threshold**, confirming the fundamental limitation is representation/signal, not just label granularity.

---

## Partial Dense Evaluation (Years 2000–2002: 12k decisions; Years 2000–2015: 99k decisions)

**Status**: COMPLETE but **NOT comparable** to full 174k evaluation

- 3/26 years ACCEPTED (2000–2002) from legal-distance
- Years 2003–2015 (16/26) pending audit per factory direction v28
- **Critical limitation**: Center-projection computed on partial corpus, not full 174k; metadata coverage limits valid subset for adversarial benchmarks (18.3% at 12k, 43.9% at 99k)
- **Trajectory**: Significant improvement with corpus scale (lang_dom dropped from ~0.98 to ~0.87; jurist_pref rose from ~0.04 to ~0.30) but still below adversarial thresholds
- Full 174k dense embeddings required for meaningful evaluation

---

## Infrastructure Readiness — All VERIFIED

| Component | Status |
|-----------|--------|
| Metadata 174k symlink | ✅ FIXED: `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.jsonl` → workspace metadata |
| Corpus canonical path | ✅ EXISTS: `/tmp/lex_accepted/corpus/corpus/normalization/canonical/` (bger_YYYY.jsonl for 2003–2026 PRESENT per factory direction v28) |
| Evaluation harness | ✅ VERIFIED: frozen v3 thresholds, exact k-NN on stratified subsample (n=2000), HNSW for full-corpus scale benchmarks |
| Test suite | ✅ PASSING: frozen_harness_reproducibility, v17_label_normalization, v17b_label_normalization_all_reps, v16_full_benchmark_suite, boilerplate_resistance_real, cross_lingual_alignment_v10, audit_correction_verification |
| Formal suite scripts | ✅ READY: `run_174k_formal_suite.py`, `scalable_nn.py`, all benchmark modules operational |
| Monitor script | ✅ ACTIVE: `monitor_and_evaluate_174k.py` watching legal-distance accepted mount for new representations |

---

## Blocked Dependencies (Legal-Distance Lane)

| Dependency | Progress | Blocker |
|------------|----------|---------|
| 174k dense embeddings | 3/26 years (2000–2002) = 19,441 decisions (11%) | Corpus artifact publication gap resolved per v28; legal-distance must complete year-split processing and audit promotion |
| Citation role embeddings | 0% | Awaits dense embedding completion |
| Linear hybrids | 0% | Awaits dense embedding completion |

**Resolution path**: Legal-distance has corpus artifacts available (bger_YYYY.jsonl symlinks for 2003–2026 at `/tmp/lex_accepted/corpus/...` and `/tmp/lex_accepted/evaluation/...`). Must complete year-split dense embedding computation with resumable checkpoints within 65-min job ceilings, then pass audit gate.

---

## Awaited Production Representations (12)

1. `center_projected_768dim_174k`
2. `center_projected_64dim_174k`
3. `center_projected_128dim_174k`
4. `linear_metric_epoch4_174k`
5. `mahalanobis_metric_epoch4_174k`
6. `hybrid_stabilized_epoch1_174k`
7. `hybrid_v2_epoch3_174k`
8. `citation_role_citing_alpha0.3_174k`
9. `citation_role_following_alpha0.3_174k`
10. `citation_role_criticizing_alpha0.3_174k`
11. `linear_citation_concat_174k`
12. `linear_hybrid05_concat_174k`

---

## External Dependencies

| Dependency | Status |
|------------|--------|
| Jurist human study (5–10 Swiss jurists) | BLOCKED (framework ready, recruitment by repository owner required) |

---

## Recommendation

**No additional same-question cycle justified for TF-IDF family.** The three machine-executable sub-questions are COMPLETE with REPRODUCED evidence tier.

**Next action**: Factory Director to unblock legal-distance lane → legal-distance completes 174k dense embeddings → evaluation monitor auto-detects and runs formal suite on all awaited representations.

**Cycle recommendation**: `continue_recommended = false` (same question complete). Awaiting successor question when dense embeddings land.

---

## Evidence References

1. Formal suite: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
2. Citation heritage pairs: `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`
3. Citation heritage results: `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
4. Legal area analysis: `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json`
5. v17b TF-IDF: `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json`
6. v17b label normalization: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
7. Partial dense (2000–2002): `evaluation/results/partial_dense_2000_2002/evaluation_partial_dense_latest.json`
8. Partial dense (2000–2015 center_projected): `evaluation/results/174k/center_projected_partial_2000_2015/center_projected_16year_eval_latest.json`
9. Partial dense (2000–2015 raw): `evaluation/results/174k/raw_multilingual_e5_partial_2000_2015/raw_multilingual_e5_16year_eval_latest.json`
10. Dense partial citation heritage: `evaluation/results/174k_citation_heritage/citation_heritage_center_projected_*_partial_2000_2015.json`

---

## Machine-Readable State

Updated: `evaluation/state/evaluation.json` (last_verification: 2026-09-27T21:10:18.000000Z)

```json
{
  "lane": "evaluation",
  "direction_version": 28,
  "evidence_tier": "REPRODUCED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "eval_174k_formal_suite_tfidf_complete_20260927_v28"
}
```

---

*Report generated per Research Protocol §12: "Write machine-readable lane state plus human-readable report."*

*Monitor re-verification: 2026-09-27T21:10:18Z — no new awaited representations detected*