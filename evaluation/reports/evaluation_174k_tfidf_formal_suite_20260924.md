# Evaluation Lane — 174k TF-IDF Formal Suite Execution Report

**Cycle**: Operational resume from producer snapshot (GitHub run 36046637281)  
**Factory Direction**: v26  
**Lane**: evaluation  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: MONITORING_DEPENDENCIES  
**Timestamp**: 2026-09-24T19:20:00.000000Z  
**Config Hash**: 4323f833fa72366a (v16 benchmark suite), 4047da047fb339c1 (full corpus harness)  
**Global Seed**: 42

---

## Executive Summary

The v25 TF-IDF evaluation question is **COMPLETED and REPRODUCED**. The full 12-benchmark formal suite has been executed at 174k scale (175,440 decisions) on all 8 TF-IDF-family representations. **All 8 representations PASS both adversarial gates** (language dominance < 0.85, jurist pairwise preference > 0.5).

The evaluation lane is now in **MONITORING_DEPENDENCIES** state, awaiting delivery of dense 174k embeddings from the legal-distance lane (GitHub run 35935612800, actively executing).

---

## Formal Suite Results — 8 TF-IDF Representations at 174k Scale

| Representation | Verdict | Language Dominance | Jurist Preference | Both Gates | Scale Stability | Boilerplate Resistance | Jurivoc L0 NMI |
|---|---|---|---|---|---|---|---|
| full_text_tfidf_light | **PASS** | 0.4976 ✓ | 0.8040 ✓ | ✓ | 0.7896 ✓ | -0.6180 ✗ | 0.0061 |
| regeste_full_text_hybrid_0.7 | **PASS** | 0.5002 ✓ | 0.8015 ✓ | ✓ | 0.7942 ✓ | -0.6281 ✗ | 0.0112 |
| cited_decisions_tfidf_outcome_hybrid_0.7 | **PASS** | 0.4850 ✓ | 0.7957 ✓ | ✓ | 0.5867 ✓ | -0.5706 ✗ | 0.0162 |
| cited_decisions_tfidf_outcome_hybrid_0.5 | **PASS** | 0.4843 ✓ | 0.7948 ✓ | ✓ | 0.5871 ✓ | -0.5735 ✗ | 0.0164 |
| regeste_full_text_hybrid_0.5 | **PASS** | 0.4983 ✓ | 0.7940 ✓ | ✓ | 0.7979 ✓ | -0.6243 ✗ | 0.0032 |
| cited_decisions_tfidf | **PASS** | 0.4874 ✓ | 0.7915 ✓ | ✓ | 0.5896 ✓ | -0.5746 ✗ | 0.0160 |
| outcome_tfidf | **PASS** | 0.4339 ✓ | 0.7381 ✓ | ✓ | 0.0537 ✗ | -0.5622 ✗ | 0.0153 |
| regeste_tfidf | **PASS** | 0.4889 ✓ | 0.7331 ✓ | ✓ | 0.2121 ✗ | -0.5507 ✗ | 0.0177 |

**Best representation**: `full_text_tfidf_light` (Jurist Preference = 0.8040, Language Dominance = 0.4976)

**Key observations**:
- All 8 representations pass **both frozen adversarial thresholds** (LD < 0.85, JP > 0.5)
- Regeste+full_text hybrids show superior scale stability (>0.79) vs cited_decisions hybrids (~0.59)
- All representations **FAIL** boilerplate resistance (negative scores) — this metric measures language dominance, not procedural boilerplate
- All representations **FAIL** Jurivoc alignment (L0 NMI ~0.01-0.02) — expected for TF-IDF at branch level
- Cross-language retrieval **FAIL** for all (recall < 0.2) — TF-IDF is language-bound

---

## Infrastructure Validation

| Component | Status | Details |
|---|---|---|
| Frozen Harness v3 | OPERATIONAL | Config hash `a31c443a9b0e992e` verified, exact reproduction confirmed |
| Scalable NN (HNSW) | OPERATIONAL | hnswlib available, validated at 174k scale |
| Full Corpus Harness | VALIDATED | Config hash `4047da047fb339c1`, exact adversarial match with frozen v3 at 1200 scale |
| v16 Benchmark Suite | IMPLEMENTED | 12 benchmarks, frozen thresholds, config hash `4323f833fa72366a` |
| Citation Heritage 174k | READY | 137,314 positive + 137,314 negative pairs at full 174k scale |
| v17b Normalization 174k | LABEL LEVEL CONFIRMED | 213→163 labels, 32 cross-lingual canonical concepts |
| Distributed Evaluation | SUPPORTED | Model-level sharding via DistributedEvaluator |
| Auto Monitor Script | OPERATIONAL | `evaluation/monitor_and_evaluate_174k.py` |

---

## Citation Heritage Benchmark — 174k Validation

- **Corpus decisions**: 173,963
- **Citation graph coverage**: 2,019/2,105 resolved (95.9%)
- **Benchmark pairs**: 137,314 positive + 137,314 negative (full scale, pre-computed)
- **Status**: Infrastructure ready, executable when dense 174k embeddings available
- **Artifact**: `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`

---

## v17b Label Normalization — 174k Confirmation

- **Raw labels**: 213 unique
- **Normalized labels**: 163 unique (23.5% reduction)
- **Cross-lingual canonical concepts**: 32 mapped across DE/FR/IT
- **Decisions with legal_area**: 91,193 / 173,963 (52.4%)
- **Status**: Label-level confirmed, clustering test **PENDING** dense embeddings
- **Artifact**: `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json`

---

## Negative Results Preserved (First-Class Evidence)

| Finding | Status | Note |
|---|---|---|
| Boilerplate resistance | NEGATIVE | Metric measures language dominance, not procedural boilerplate |
| Hierarchy coherence | NEGATIVE | v18 confirmed fundamental branch-level limitation (purity ~0.65) |
| Zoom coherence | NEGATIVE | No improvement from coarse to fine at branch level |
| Legal area clustering | NEGATIVE | Fine-grained label granularity prevents purity > 0.5 |
| Citation heritage on TF-IDF | NEGATIVE (AUC=0.482) | TF-IDF cannot recover citation proximity (SUPERSEDED by frozen-protocol: cited_outcome_hybrid_0.5 AUC=0.919 PASS) |
| center_projected_768 | FAILS JP gate | 0.4912 < 0.5, confirmed across all verifications |

---

## Production Decision Gates (from Factory Direction v26)

| Gate | Requirement | Status |
|---|---|---|
| `PRODUCT_SERVING_DEFAULT_cited_outcome_hybrid_0.5` | Pass BOTH adversarial gates at 174k | **PASS** (JP=0.7948, LD=0.4843) |
| `COMBINATION_MODE_linear_hybrid05_concat` | Pass BOTH adversarial gates + stability test at 174k | PENDING (needs dense embeddings) |
| `DEFAULT_map_mode_center_projected_64dim_hierarchical` | Re-verify at 174k (validated PASS at 1200) | PENDING (needs dense embeddings) |

---

## Dependencies & Blockers

### Active Dependencies (v26)

1. **legal_distance_174k_dense_embeddings** — ACTIVE
   - Legal-distance GitHub run 35935612800 executing year-split CPU computation
   - Priority 2 awaited: `center_projected_768dim`, `center_projected_64dim`, `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1`
   - Priority 3 awaited: `citation_role_citing/following/criticizing/distinguishing/overruling_alpha0.3`

2. **citation_heritage_174k_dense** — INFRASTRUCTURE READY
   - 137,314 positive + negative pairs pre-computed
   - Executable when dense embeddings land

3. **v17b_label_normalization_174k_dense** — LABEL LEVEL CONFIRMED
   - Clustering test pending dense embeddings

### External Blockers

- **Jurist human study**: Framework ready, externally blocked (requires 5-10 Swiss jurists recruited by repository owner)

---

## Artifacts & Evidence References

| Artifact | Path |
|---|---|
| Full corpus evaluation results (8 representations) | `evaluation/results/full_corpus_174k_tfidf/full_corpus_evaluation_results_worker0.json` |
| Citation heritage pairs (137k scale) | `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` |
| v17b label analysis | `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json` |
| v3 evaluation results (1200 scale, 6 dense modes) | `evaluation/results/v3/evaluation_v3_results.json` |
| Updated lane state | `state/evaluation.json` |

---

## Recommendation

**`continue_recommended: false`** for the TF-IDF question — no additional same-question cycle justified.

The evaluation lane remains **active in MONITORING_DEPENDENCIES** state. The Factory Director should await legal-distance delivery of dense 174k representations in accepted state before authorizing the next evaluation cycle on dense representations (Priority 2: center_projected_64/768, linear_metric, mahalanobis, hybrid_stabilized; Priority 3: citation roles).

All evaluation infrastructure is **FROZEN, VALIDATED, and AUDIT-READY**. Negative results are preserved as first-class evidence.

---

## Audit Trail

- **Prior accepted run**: `eval_v25_174k_formal_suite_36013963912` (TF-IDF formal suite)
- **Prior provenance gate**: `eval_v25_provenance_gate_36035803010` (12/12 pytest PASS)
- **Current operational resume**: GitHub run 36046637281
- **Factory direction**: v26 (unchanged from v25)
- **Legal-distance dependency**: GitHub run 35935612800 (actively executing)

No HUMAN_DECISION_REQUIRED states exist. Compute on free public runners is an operational constraint routed autonomously per Main Prompt anti-thrift clause.