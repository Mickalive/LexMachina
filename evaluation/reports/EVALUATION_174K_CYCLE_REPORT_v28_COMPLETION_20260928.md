# Evaluation Lane — Cycle Completion Report (Factory Direction v28)

**Date**: 2026-09-28  
**Lane**: evaluation  
**Factory Direction Version**: 28  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: MONITORING  
**Accepted Run ID**: `eval_174k_formal_suite_v28_monitoring_20260928`  
**Monitor Check Count**: 198 (as of 2026-09-28T12:30:31)

---

## Executive Summary

**ALL THREE SUB-QUESTIONS OF FACTORY DIRECTION v28 COMPLETE FOR TF-IDF FAMILY AT 174K SCALE**

The evaluation lane has successfully executed the machine-executable 174k formal suite on all 8 TF-IDF production representations. No new production representations have landed from legal-distance since the last evaluation cycle. The lane remains in active MONITORING mode with concrete discriminating purpose: auto-evaluate awaited representations (dense embeddings, citation roles, linear hybrids) as they land in accepted state.

---

## Factory Direction v28 — Question Status

| Sub-Question | Status | Details |
|--------------|--------|---------|
| **1. Full 12-benchmark formal suite at 174k on all production representations (frozen harness v3, thresholds unchanged)** | ✅ **COMPLETE** | V25 formal suite (frozen protocol, config hash `4323f833fa72366a`) executed on all 8 TF-IDF representations at 173,963 decisions. HNSW artifact fixed via exact k-NN on stratified subsample (n=2000, seed=42). Fundamental two-mode tradeoff REPRODUCED. |
| **2. Validate citation_heritage benchmark using 174k citation-ID resolution (2,019/2,105 resolved, 95.9%)** | ✅ **COMPLETE** | Dedicated citation_heritage benchmark re-run on regenerated frozen 2,040 pair pool (1,020 positive direct+shared citations, 1,020 negative, balanced sampling from resolved citation graph, seed=42). All 8 TF-IDF representations evaluated. |
| **3. Test v17b label normalization (15-25% purity gain, REPRODUCED across 4 seeds) generalization to 174k fine-grained legal_area labels** | ✅ **COMPLETE** | v17b conservative cross-lingual canonical mapping applied to 85,819 labels (214→164 unique areas). Differential effect CONFIRMED at 174k: citation-based reps improve 1.04-1.10x on hierarchy-family metrics; text-based reps DEGRADE zoom_fine 0.66-0.70x. Uniform improvement FALSE. |

---

## Representations Evaluated — TF-IDF Family (8/8 Complete)

| Representation | V25 Suite (12 benchmarks) | Citation Heritage | v17b Normalization | Notes |
|----------------|---------------------------|-------------------|-------------------|-------|
| `cited_decisions_tfidf` | 6 PASS / 5 FAIL / 1 SKIP | AUC=0.973 PASS, recall@10=0.487 | Citation-based: hierarchy +4.8%, zoom +2.2% | Production default component |
| `outcome_tfidf` | 3 PASS / 9 FAIL | AUC=0.720 PASS, recall@10=0.003 | Text-based: hierarchy stable, zoom -30% | Weak legal signal alone |
| `regeste_tfidf` | 5 PASS / 7 FAIL | AUC=0.486 FAIL, recall@10=0.000 | Citation-based: hierarchy +52%, zoom +0% | Regeste-only weak on citations |
| `full_text_tfidf_light` | 7 PASS / 5 FAIL | AUC=0.844 PASS, recall@10=0.438 | Text-based: hierarchy stable, zoom -33% | **FAIL adversarial** (LangDom=0.999) |
| `cited_outcome_hybrid_0.5` | 6 PASS / 5 FAIL / 1 SKIP | AUC=0.919 PASS, recall@10=0.476 | Citation-based: hierarchy +8.8%, zoom +3.2% | **Production default** |
| `cited_outcome_hybrid_0.7` | 6 PASS / 6 FAIL | AUC=0.960 PASS, recall@10=0.490 | Citation-based: hierarchy +8.6%, zoom +3.1% | Strongest citation signal |
| `regeste_full_text_hybrid_0.5` | 7 PASS / 5 FAIL | AUC=0.850 PASS, recall@10=0.444 | Text-based: hierarchy stable, zoom -34% | **FAIL adversarial** (LangDom=0.998) |
| `regeste_full_text_hybrid_0.7` | 7 PASS / 5 FAIL | AUC=0.865 PASS, recall@10=0.445 | Text-based: hierarchy stable, zoom -30% | **FAIL adversarial** (LangDom=0.999) |

---

## Critical Findings (Reproduced at 174k)

### 1. Fundamental Two-Mode Tradeoff Persists at 174k
- **Citation-based representations** (`cited_decisions_tfidf`, `cited_outcome_hybrid_*`): PASS adversarial gates (LangDom < 0.85, Jurist > 0.3), PASS multilingual invariance, PASS citation_heritage AUC, **FAIL** branch_knn/tf_metadata/hierarchy_coherence/legal_area_clustering
- **Text-based representations** (`full_text_tfidf_light`, `regeste_full_text_hybrid_*`): PASS branch_knn/tf_metadata, **FAIL** adversarial gates (LangDom ≈ 0.999), FAIL multilingual/cross-language, PASS zoom_coherence

### 2. Citation Heritage Negative at 174k
- **ALL 8 TF-IDF representations FAIL** citation_heritage recall@10 threshold (recall@10 < 0.2)
- Best recall@10: `cited_decisions_tfidf` = 0.487 (but this is nn_citation_rate, not the formal benchmark)
- Citation graph coverage: only 0.1% of corpus (174/173,963) has direct/shared citations in pair pool
- Citation-independent retrieval near-zero for citation signals; text signals achieve AUC 0.85-0.90 at smaller scale but collapse on adversarial gates at full scale

### 3. v17b Label Normalization — Differential Effect Confirmed
- 49.3% labels normalized (85,819/173,963, 214→164 unique areas)
- **Citation-based signals**: uniform 4-10% purity gains across hierarchy_coherence, zoom_coherence, legal_area_clustering
- **Text-based signals**: hierarchy/legal_area stable but **zoom_fine DEGRADES 30-34%**
  - `full_text_tfidf_light`: 0.67x zoom_fine
  - `regeste_full_text_hybrid_0.5`: 0.66x zoom_fine  
  - `regeste_full_text_hybrid_0.7`: 0.70x zoom_fine
- Uniform improvement claim **FALSE** at 174k scale (mirrors 1200-scale finding)

### 4. HNSW Artifact Fixed and Verified
- Exact k-NN on stratified subsample (n=2000, seed=42) avoids HNSW masking representation differences
- Production default `cited_decisions_tfidf_outcome_hybrid_0.5` re-verified: **LangDom=0.5164 PASS, Jurist=0.8055 PASS**
- V25 suite uses HNSW with fixed params (M=16, ef_construction=200, ef_search=100) for scalability; adversarial benchmarks use exact k-NN on valid subset

### 5. Dense Embeddings Scale Dependency
- Evaluated at 12k scale (3 accepted years 2000-2002): **FAIL adversarial gates** (LangDom~0.98-1.0)
- **PASS cross-language transfer** (zero-shot NMI~0.46-0.48) and cluster coherence (branch_purity~0.89)
- Root cause: 18.3% metadata coverage, partial corpus center-projection, raw multilingual-e5 language clustering at 12k vs full 174k TF-IDF
- Full 174k dense embeddings **NOT YET AVAILABLE** in accepted state (only 3/26 years ACCEPTED)

---

## Awaited Representations (Legal-Distance Dependency)

| Category | Representations | Status |
|----------|-----------------|--------|
| **Dense embeddings (174k)** | center_projected_768dim, center_projected_64dim, center_projected_128dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | ⏳ **3/26 years ACCEPTED (2000-2002)**; 17/26 years (2003-2019) in checkpoints **PENDING AUDIT**; years 2020-2025 not yet processed |
| **Citation roles (174k)** | citation_role_citing_alpha0.3, citation_role_following_alpha0.3, citation_role_criticizing_alpha0.3 | ❌ Not available |
| **Linear hybrids (174k)** | linear_citation_concat, linear_hybrid05_concat | ❌ Not available |

**Per factory direction v28**: "ACCEPTED DENSE PROGRESS: 3/26 years (2000-2002, ~19,441 decisions). PENDING AUDIT: progress.json shows 20/26 years (2000-2019, ~99k decisions) but this result has NOT passed audit gate; cannot be cited as accepted fact."

---

## Infrastructure Status (All Verified Operational)

| Component | Status | Verification |
|-----------|--------|--------------|
| Adversarial benchmarks | ✅ VERIFIED | Exact k-NN on n=2000 subsample; production default reproduces LangDom=0.5164 PASS, Jurist=0.8055 PASS (config hash `b51701f5a9c11692`) |
| Citation heritage pipeline | ✅ VERIFIED | Frozen 2,040 pairs; re-run on new pair pool; 95.9% citation-ID resolution |
| v17b normalization pipeline | ✅ VERIFIED | Differential effect reproduced across all 8 TF-IDF representations |
| HNSW artifact fix | ✅ CONFIRMED | Exact k-NN avoids masking; HNSW used only for scalable full-corpus citation heritage |
| V25 formal suite runner | ✅ VERIFIED | Frozen protocol v25 executed on all 8 TF-IDF reps at 174k; config hash `4323f833fa72366a` |
| Monitor script | ✅ ACTIVE | check_count=198; last_check=2026-09-28T12:30:31Z; no new awaited representations |
| Scalable NN | ✅ OPERATIONAL | sklearn exact k-NN for adversarial (n=2000), HNSW for full-corpus citation heritage |
| Metadata_174k | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% coverage |

---

## Blockers (External Dependencies)

1. **Legal-distance 174k dense embeddings**: Final concatenation and 174k evaluation PENDING. Only 3/26 years ACCEPTED. Monitor scans only final concatenated directories in accepted state, not checkpoints.

2. **Legal-distance citation role embeddings**: Not yet available at 174k scale.

3. **Legal-distance linear hybrid embeddings**: Not yet available at 174k scale.

4. **Fractal-map lane**: Blocked on legal-distance 174k dense embeddings (single remaining dependency per factory direction v28).

5. **Product lane**: Blocked on legal-distance 174k dense embeddings for production default switch.

6. **Jurist human study**: Framework ready (simulation infrastructure in `evaluation/tests/jurist_usability.py`). Requires 5-10 Swiss jurists for validation. Not blocked on technical infrastructure.

---

## Continue Recommendation

**continue_recommended = TRUE**

Monitoring has concrete discriminating purpose: auto-evaluate awaited representations (dense embeddings, citation roles, linear hybrids) as they land in accepted state from legal-distance. No additional same-question cycle is justified for the TF-IDF family — the evaluation is complete, reproduced, and frozen.

The Factory Director should promote legal-distance to complete 174k dense embeddings (audit promotion of years 2003-2019, then processing years 2020-2025, then final concatenation) as the critical path unblocking fractal-map and product lanes.

---

## Evidence References (Machine-Readable)

- `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` — Complete V25 suite results for all 8 TF-IDF representations
- `results/evaluation/v25_174k_citation_heritage/` — Dedicated citation heritage results per representation
- `results/evaluation/v25_174k_v17b/` — v17b label normalization comparison (raw vs normalized) per representation
- `results/evaluation/v25_174k_formal_suite/partial_dense_results/center_projected_768dim_partial_2000_2002.json` — 3-year dense partial evaluation
- `evaluation/state/monitor_174k_state.json` — Monitoring state (check_count=198, infrastructure status, dense progress)
- `evaluation/state/evaluation.json` — Lane state (evidence_tier=REPRODUCED, cycle_status=MONITORING)

---

## Negative Results Preserved (Per Anti-Noise Principle)

- TF-IDF text-based representations **FAIL** adversarial falsification at 174k (LangDom ≈ 0.999)
- ALL TF-IDF representations **FAIL** citation_heritage recall@10 threshold
- ALL TF-IDF representations **FAIL** hierarchy_coherence (Jurivoc proxy) at 174k
- v17b normalization **DEGRADES** zoom_fine for text-based representations (30-34% loss)
- Dense embeddings **FAIL** adversarial gates at 12k (LangDom ~0.98-1.0)
- Boilerplate resistance **NEGATIVE** for all TF-IDF (resistance_score ≈ -0.57 to -0.80)

These negative results are first-class evidence and must not be discarded or explained away.

---

## Next Actions

1. **No action required** for evaluation lane — monitoring is active and will auto-trigger when new representations land
2. **Legal-distance priority**: Complete 174k dense embeddings (audit promotion + remaining years + final concatenation)
3. **Legal-distance priority**: Deliver citation role embeddings at 174k
4. **Legal-distance priority**: Deliver linear hybrid embeddings at 174k
5. **Factory Director**: Consider successor question for evaluation lane once dense embeddings land (e.g., "Does dense embedding mode break the two-mode tradeoff at 174k?")

---

*Report generated automatically by evaluation lane monitoring infrastructure. All results reproducible from frozen protocols and accepted state artifacts.*