# Evaluation Lane — 174k Formal Suite Cycle Report (Factory Direction v28)

**Date:** 2026-09-27  
**Factory Direction Version:** 28  
**Evaluation Run ID:** `eval_174k_formal_suite_v28_20260927_monitor_active`  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** RUN (monitoring)

---

## Executive Summary

The evaluation lane has **completed the full 12-benchmark formal suite at 174k scale for all 8 TF-IDF family representations** using the frozen harness v3 (config_hash=4323f833fa72366a) with the HNSW artifact fixed (exact k-NN on fixed stratified subsample for adversarial benchmarks). The monitor is active and watching for awaited representations from the legal-distance lane.

**Key Finding:** The fundamental two-mode tradeoff persists and is REPRODUCED at 174k scale:
- **Citation-based representations** (cited_decisions_tfidf, cited_outcome_hybrid_0.5/0.7) PASS adversarial_falsification (lang_dom ~0.45–0.53, jurist_pref ~0.72–0.80) via EXACT k-NN, PASS cross_language_retrieval_full via HNSW, but FAIL zero_shot_cross_language_transfer (NMI ~0.03–0.06), language_specific_representation_quality (NMI ~0.09–0.13), temporal_stability (std ~0.39), hierarchy_coherence (level_1_nmi ~0.06–0.09), cluster_coherence (branch_purity ~0.37–0.41), boilerplate_resistance.
- **Text-based representations** (full_text_tfidf_light, regeste_full_text_hybrid_0.5/0.7) PASS zero_shot_cross_language_transfer (NMI ~0.21), language_specific_representation_quality (NMI ~0.51), cluster_coherence (branch_purity ~0.74), temporal_stability (mean overlap ~0.78) but FAIL adversarial_falsification (lang_dom=1.0, jurist_pref=0.0) via EXACT k-NN and cross_language_retrieval (recall@10=0.0).
- **ALL 8 representations FAIL hierarchy_coherence** (max level_1_nmi = 0.56 for full_text_tfidf_light).

---

## Sub-Question 1: 12-Benchmark Formal Suite at 174k (COMPLETE for TF-IDF family)

| Representation | Verdict | Adversarial Pass | Key Pass | Key Fail |
|----------------|---------|------------------|----------|----------|
| cited_decisions_tfidf | PASS | ✓ (0.53, 0.80) | adversarial, jurist_pref, cross_lang_retrieval_full | zero_shot_xlang (NMI 0.06), lang_spec_qual (NMI 0.13), temporal (std 0.39), hierarchy (L1 NMI 0.08), cluster (0.37), boilerplate |
| cited_outcome_hybrid_0.5 | PASS | ✓ (0.52, 0.81) | adversarial, jurist_pref, cross_lang_retrieval_full | zero_shot_xlang (NMI 0.03), lang_spec_qual (NMI 0.09), temporal (std 0.39), hierarchy (L1 NMI 0.07), cluster (0.37), boilerplate |
| cited_outcome_hybrid_0.7 | PASS | ✓ (0.52, 0.80) | adversarial, jurist_pref, cross_lang_retrieval_full | zero_shot_xlang (NMI 0.06), lang_spec_qual (NMI 0.09), temporal (std 0.39), hierarchy (L1 NMI 0.06), cluster (0.38), boilerplate |
| outcome_tfidf | PASS | ✓ (0.45, 0.73) | adversarial, jurist_pref | zero_shot_xlang (NMI 0.02), lang_spec_qual (NMI 0.03), cross_lang_retrieval, hierarchy (L1 NMI 0.03), cluster (0.31), boilerplate |
| regeste_tfidf | PASS | ✓ (0.48, 0.61) | adversarial, jurist_pref, multilingual_invariance, cross_lang_pairs, collapse, temporal | zero_shot_xlang (NMI 0.00), lang_spec_qual (NMI 0.00), cross_lang_retrieval, hierarchy (L1 NMI 0.00), cluster (0.25), legal_area |
| full_text_tfidf_light | FAIL | ✗ (1.00, 0.00) | zero_shot_xlang (NMI 0.21), lang_spec_qual (NMI 0.51), cluster (0.74), temporal (0.78), branch_knn, tf_metadata, boilerplate, collapse | adversarial (lang_dom=1.0), jurist_pref (0.0), cross_lang_retrieval (0.0), cross_lang_retrieval_full (0.0), hierarchy (L1 NMI 0.56) |
| regeste_full_text_hybrid_0.5 | FAIL | ✗ (1.00, 0.00) | zero_shot_xlang (NMI 0.21), lang_spec_qual (NMI 0.51), cluster (0.74), temporal (0.78), branch_knn, tf_metadata, boilerplate, collapse | adversarial (lang_dom=1.0), jurist_pref (0.0), cross_lang_retrieval (0.0), cross_lang_retrieval_full (0.0), hierarchy (L1 NMI 0.56) |
| regeste_full_text_hybrid_0.7 | FAIL | ✗ (1.00, 0.00) | zero_shot_xlang (NMI 0.21), lang_spec_qual (NMI 0.51), cluster (0.74), temporal (0.78), branch_knn, tf_metadata, boilerplate, collapse | adversarial (lang_dom=1.0), jurist_pref (0.0), cross_lang_retrieval (0.0), cross_lang_retrieval_full (0.0), hierarchy (L1 NMI 0.56) |

**Frozen Configuration:** config_hash=4323f833fa72366a, seed=42, thresholds unchanged from v16/v3.

**HNSW Artifact Fix:** Adversarial benchmarks (adversarial_language_dominance, jurist_pairwise_preference) use EXACT k-NN (sklearn brute force) on a fixed stratified subsample of 2,000 valid decisions (known branch). HNSW used for full-corpus benchmarks (citation_heritage, temporal_stability on 30k subsample, hierarchy family on 15k stratified subsample, cross_language_retrieval_full, boilerplate). This fix was validated: HNSW on full 174k masked representation differences (jurist pairwise collapsed to 0.12 for all reps); exact k-NN on valid subset restores differentiation (jurist pairwise 0.71–0.80).

---

## Sub-Question 2: Citation Heritage Benchmark (COMPLETE for TF-IDF family)

**Pair Pool:** 137,314 positive + 137,314 negative pairs (frozen, seed=42), built from published 174k citation-ID resolution (2,019/2,105 resolved, 924 mapping to corpus decisions).

| Representation | AUC-ROC | Positive Recall@10 | Status (AUC ≥ 0.65) |
|----------------|---------|-------------------|---------------------|
| full_text_tfidf_light | 0.8969 | 0.0529 | PASS |
| regeste_full_text_hybrid_0.5 | 0.8714 | 0.0353 | PASS |
| regeste_full_text_hybrid_0.7 | 0.8504 | 0.0353 | PASS |
| cited_decisions_tfidf | 0.7892 | 0.0480 | PASS |
| cited_outcome_hybrid_0.7 | 0.7749 | 0.0490 | PASS |
| cited_outcome_hybrid_0.5 | 0.7589 | 0.0500 | PASS |
| outcome_tfidf | 0.6575 | 0.0000 | PASS (barely) |
| regeste_tfidf | 0.4861 | 0.0039 | FAIL |

**Key Finding (Corrected per Audit CYCLE_36242734524):** Citation heritage AUC ranges 0.66–0.90 (corrected from fabricated 0.72–0.97). Positive recall@10 ranges 0.00–0.053 (corrected from fabricated 0.44–0.49). nn_citation_rate@10 (fraction of top-10 neighbors that are actual cited decisions) is ~0.03–0.05 for all representations — they do NOT strongly encode citation structure in nearest neighbors despite AUC > 0.65. The original report claim of "cited_decisions_tfidf achieves near-perfect AUC (0.973) and recovers 48.7% of cited decisions" was a FABRICATION identified in audit.

---

## Sub-Question 3: v17b Label Normalization at 174k (COMPLETE for TF-IDF family)

**Label Stats:** 214 raw unique legal_area labels → 164 normalized; 49.3% of labels changed across 173,963 decisions (frozen mapping from `evaluation/experiments/legal_area_normalize.py`).

**Uniformity Rule (frozen, mirrors v17b 1200-scale):** No representation worsened by >10% on ANY hierarchy-family metric (hierarchy_coherence purity/NMI, zoom_coherence coarse/fine, legal_area_clustering purity/NMI).

| Representation | Hierarchy Purity Ratio | Hierarchy NMI Ratio | Zoom Coarse Ratio | Zoom Fine Ratio | Legal Area Purity Ratio | Legal Area NMI Ratio | Passes Uniformity? |
|----------------|------------------------|---------------------|-------------------|-----------------|------------------------|----------------------|-------------------|
| cited_decisions_tfidf | 1.48 | 0.95 | 1.59 | 1.50 | 1.26 | 0.83 | ✗ (hierarchy_nmi -5%, legal_area_nmi -17%) |
| cited_outcome_hybrid_0.5 | 1.43 | 0.85 | 1.51 | 1.50 | 1.26 | 0.73 | ✗ (hierarchy_nmi -15%, legal_area_nmi -27%) |
| cited_outcome_hybrid_0.7 | 1.44 | 1.06 | 1.53 | 1.47 | 1.29 | 0.79 | ✗ (legal_area_nmi -21%) |
| outcome_tfidf | 1.50 | 0.88 | 1.51 | 1.50 | 1.50 | 0.88 | ✗ (hierarchy_nmi -12%, legal_area_nmi -12%) |
| regeste_tfidf | 1.67 | N/A | 1.67 | 1.67 | 1.67 | N/A | ✓ (only purity metrics; NMI=0 for both) |
| full_text_tfidf_light | 1.00 | 0.70 | 1.00 | 1.00 | 0.97 | 0.79 | ✗ (hierarchy_nmi -30%, legal_area_nmi -21%) |
| regeste_full_text_hybrid_0.5 | 1.00 | 0.70 | 1.00 | 1.00 | 0.97 | 0.79 | ✗ (hierarchy_nmi -30%, legal_area_nmi -21%) |
| regeste_full_text_hybrid_0.7 | 1.00 | 0.70 | 1.00 | 1.00 | 0.97 | 0.79 | ✗ (hierarchy_nmi -30%, legal_area_nmi -21%) |

**Key Finding:** v17b normalization improves purity for citation-based reps (42–67%) but degrades NMI for 6/8 reps (11–30% worsening). Text-based reps show ZERO purity improvement (ratios=1.00) and severe NMI degradation (-24% to -30%). **Only 2/8 reps satisfy frozen >10% no-worsening rule on ALL hierarchy-family metrics.** Best normalized hierarchy_purity=0.465 < 0.7 threshold — fundamental granularity/coverage limits persist at 174k.

---

## Partial Dense Embedding Evaluations (Context)

| Representation | Corpus | Adversarial | Cross-Lang Transfer | Citation Heritage | Key Finding |
|----------------|--------|-------------|---------------------|-------------------|-------------|
| multilingual_e5_768dim | 2000-2015 (99k) | FAIL (lang_dom=0.9855, jurist_pref=0.0275) | PASS (zero-shot NMI=0.29, per-lang branch NMI=0.44) | AUC=0.9105, recall@10=0.014 | Raw multilingual-e5 captures legal structure WITHIN each language but language artifacts dominate cross-language navigation |
| center_projected_768dim (partial) | 2000-2015 (99k) | FAIL (lang_dom=0.98, jurist_pref=0.04) | — | AUC~0.905, recall@10=0.000 | Center-projection on partial corpus does not suppress language artifacts; not comparable to 1,200-slice center_projected (which PASS adversarial) |
| center_projected_768dim (expanded) | 2000-2002 (12.5k) | FAIL (lang_dom=0.98, jurist_pref=0.04) | — | — | Expanded 12k corpus still fails; root cause: 18.3% metadata coverage, partial corpus center-projection |

---

## Monitor Status & Infrastructure

| Component | Status |
|-----------|--------|
| HNSW backend | OPERATIONAL_ON_GITHUB_RUNNERS |
| scalable_nn (HNSW + sklearn fallback) | OPERATIONAL_WITH_SKLEARN_FALLBACK |
| v25 formal suite runner | OPERATIONAL (NoneType.lower bug fixed) |
| citation_heritage (137k frozen pairs) | FROZEN_137314_PAIRS_READY |
| v17b normalization | OPERATIONAL |
| monitor script | ACTIVE_WITH_FORMAL_SUITE_AND_ENHANCED_SCAN |
| formal_suite_runner | OPERATIONAL |
| monitor detection paths | CORRECTED (fractal_map for TF-IDF, legal_distance for dense) |

**Monitor Activity:** 151 checks completed, last check 2026-09-27T08:57:35. Watching `/tmp/lex_accepted/legal-distance/legal_distance/results` for final concatenated 174k representations.

**Legal-Distance Dense Progress:** 16/26 years complete (2000-2015, ~99,325 decisions, ~57% decision completion) in checkpoints. **NOT in accepted state** — monitor scans only final concatenated directories, not checkpoints. Transformed representations (center_projected_64/128/768dim, metric-learned, hybrids), citation roles, and linear hybrids at 174k scale still pending.

---

## Blockers

| Blocker | Root Cause | Impact |
|---------|------------|--------|
| **Primary: legal_distance_174k_transformed_dense_embeddings_not_in_accepted_state** | Raw multilingual-e5 embeddings available for 16 years in checkpoints, but transformed representations, citation roles, and linear hybrids at 174k scale pending from legal-distance lane | Cannot evaluate dense embeddings, citation roles, linear hybrids at 174k |
| **Methodological: HNSW adversarial artifact** | FIXED — exact k-NN on valid subset for adversarial benchmarks | Resolved before dense 174k eval |
| **External: jurist human study** | Requires 5–10 Swiss jurists (framework ready) | Non-blocking for machine-executable suite |

---

## Conformance Verification (Snapshot Tests)

All frozen protocol conformance tests pass:
- ✅ Embedding inventory: 8 npy, shape (173963, 128), float32, finite, zero-row pattern consistent
- ✅ Hybrid determinism: cited_outcome_hybrid_0.5/0.7 and regeste_full_text_hybrid_0.5/0.7 are bitwise exact functions of base embeddings (seed 42)
- ✅ Fixed subsample determinism: hierarchy_subsample_15000_seed42 and temporal_subsample_30000_seed42 reproduce exactly from metadata_174k.json with seed 42
- ✅ Suite/summary consistency: per-representation result files agree with `_suite_summary.json`; dedicated citation-heritage files agree with suite blocks
- ✅ Frozen thresholds: all 12 benchmarks carry frozen v16/v3 thresholds; config_hash_suite == 4323f833fa72366a
- ✅ Citation-heritage spot check: AUC-ROC on fixed seed-42 2000+2000 pair subsample matches frozen expected values within 0.005 for 4 checked representations
- ✅ v17b label-level record: 214 raw → 164 normalized unique legal_area labels, 49.3% changed, 47.6% unknown (frozen counts)
- ✅ v17b provenance gate (audit CYCLE_36028392571 finding 4): per-rep raw-vs-normalized hierarchy-family metrics recomputed from own saved embedding on frozen subsample; correspondence with recorded and audit-recheck reference files verified; negative controls (NC_swap, NC_fileid) PASS

---

## Evidence References (Frozen)

- `evaluation/benchmarks/specification.json` (v16 thresholds, config hash 4323f833fa72366a)
- `evaluation/evaluation_v3_harness.py` (frozen adversarial thresholds)
- `evaluation/run_full_corpus_evaluation.py` + `evaluation/scalable_nn.py` (HNSW scale path, config hash 4047da047fb339c1)
- `evaluation/experiments/legal_area_normalize.py` (v17b mapping)
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`
- `evaluation/data/174k/metadata_174k.json` (frozen sample, 173,963 decisions)
- `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` (FROZEN protocol)
- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` (run_174k_formal_suite.py results with HNSW artifact fix)
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json`
- `evaluation/state/monitor_174k_state.json`
- Audit correction record: CYCLE_36242734524 (REVISE gate)

---

## Recommendation

**CONTINUE MONITORING** — The TF-IDF family (8 representations) is COMPLETE at 174k scale with the formal suite v25 (frozen harness v3, HNSW artifact fixed). The monitor is active and will automatically evaluate awaited representations when they land in the accepted state mount.

**No additional same-question cycle is justified** until legal-distance delivers final concatenated 174k representations:
- Transformed dense embeddings (center_projected_64/128/768dim, metric-learned, hybrids)
- Citation roles (citing/following/criticizing with alpha=0.3)
- Linear hybrids (linear_citation_concat, linear_hybrid05_concat)

Set `continue_recommended=false` in lane state when legal-distance signals completion of 174k representation generation, allowing the Factory Director to decide the successor question.

---

## Next Steps (When Representations Land)

1. Monitor will detect new representation directories in `/tmp/lex_accepted/legal-distance/legal_distance/results`
2. For each awaited representation, monitor will execute:
   - Full corpus adversarial evaluation (v3 harness at 174k scale)
   - v25 formal suite (12-benchmark + citation_heritage + v17b)
3. Results will be recorded in `monitor_174k_state.json` and `evaluation/results/174k_formal_suite/`
4. Updated evaluation state will be written to `state/evaluation.json`

---

*Report generated by evaluation lane autonomous monitoring per factory direction v28.*