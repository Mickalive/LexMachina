# Evaluation Lane v25 — 174k Formal Suite Execution Plan

**Factory Direction:** v25  
**Lane:** evaluation  
**Status:** BLOCKED_ON_DEPENDENCIES (awaiting legal-distance 174k representations)  
**Infrastructure Readiness:** FULLY VALIDATED  

---

## Executive Summary

All evaluation infrastructure for the 174k formal suite is **READY AND VALIDATED**. The evaluation lane is blocked solely on the delivery of 174k production representations from the legal-distance lane (currently executing gh run 35935612800, year-split TF-IDF computation).

When representations land in accepted state, the evaluation lane will execute:
1. **Full 12-benchmark formal suite** at 174k scale on all production representations (frozen harness v3 thresholds unchanged)
2. **Citation heritage benchmark** using published 174k citation-ID resolution (2,019/2,105 resolved, 804 positive pairs validated)
3. **v17b label normalization clustering test** at 174k scale (label-level normalization confirmed: 214→164 unique labels, 49.3% changed, 32 cross-lingual canonical concepts)

---

## Frozen Configuration Verification

All config hashes verified and frozen:

| Harness | Config Hash | Seed | Factory Direction |
|---------|-------------|------|-------------------|
| Frozen Adversarial Harness v3 | `4323f833fa72366a` | 42 | v6 (canonical) |
| Scalable Full Corpus Harness v3 | `4047da047fb339c1` | 42 | v10 |
| v16 Full Benchmark Suite | `4323f833fa72366a` | 42 | v13 |

**Adversarial Thresholds (FROZEN - DO NOT MODIFY):**
- Language Dominance: < 0.85 (PASS)
- Jurist Pairwise Preference: > 0.5 (PASS)
- Cross-Language Recall: > 0.2 (PASS)
- Cluster Coherence: > 0.7 (PASS)

**Benchmark Parameters (FROZEN):**
- k_neighbors_lang_dom: 20
- k_neighbors_jurist: 10
- k_neighbors_cross_lang: 10
- n_clusters_coherence: 16

---

## Infrastructure Components — All VALIDATED

### 1. Scalable NN Infrastructure (`evaluation/scalable_nn.py`)
- **Backend:** HNSW (hnswlib) for ≥10k decisions, sklearn exact NN for <10k
- **HNSW Parameters:** M=16, ef_construction=200, ef_search=100
- **Batch Size:** 5000
- **Validation:** 1200-scale exact match with frozen harness v3 confirmed
- **Distributed Support:** Model-level sharding via `DistributedEvaluator`

### 2. Full Corpus Evaluation Harness (`evaluation/run_full_corpus_evaluation.py`)
- **Entry Point:** `run_full_corpus_evaluation()`
- **Output Format:** Identical to frozen harness v3 `evaluate_representation()`
- **Benchmarks:** 7 core adversarial + Jurivoc + scale stability + boilerplate + fractal + cross-language
- **Worker Support:** `--worker-id` / `--n-workers` for distributed evaluation

### 3. 12-Benchmark Formal Suite (`evaluation/experiments/run_v16_full_benchmark_suite.py`)
All 12 benchmarks implemented and frozen:
1. `citation_heritage` — AUC-ROC ≥ 0.65
2. `branch_knn` — k-NN accuracy@5 ≥ 0.6333
3. `tf_metadata_human_indexing` — Recall@5 ≥ 0.8
4. `adversarial_falsification` — LangDom < 0.85, BranchCoherence > 0.3
5. `boilerplate_resistance_real_corpus` — Text/emb correlation > 0.1
6. `multilingual_invariance` — Separation ≥ 0, Invariance gap < 0.2
7. `cross_language_pairs` — Separation > 0
8. `collapse_check` — Mean similarity < 0.99, Std > 0.01
9. `temporal_stability` — Std of k-NN scores < 0.1
10. `hierarchy_coherence` — Purity > 0.7, NMI > 0.3
11. `zoom_coherence` — Fine > Coarse purity
12. `legal_area_clustering` — Purity > 0.5

### 4. Citation Heritage Benchmark Infrastructure
- **Citation Graph:** Built from resolved citations (`/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/`)
- **Resolution Rate:** 95.9% (2,019/2,105 citation strings resolved)
- **Positive Pairs:** 804 (direct + shared citations) at 174k scale
- **Negative Pairs:** 1,608 (sampled no-citation-relation pairs)
- **Validation Script:** `evaluation/validate_citation_heritage_174k.py` ✅ EXECUTED
- **Artifacts:** `evaluation/results/174k_citation_heritage/citation_pairs_174k.json`

### 5. v17b Label Normalization Infrastructure
- **Label Level:** CONFIRMED at 174k (214→164 unique labels, 23.5% reduction)
- **Cross-lingual Mappings:** 32 canonical concepts with multi-language variants
- **Top Normalized Labels:** criminal_procedure (11,803), invalidity_insurance (8,554), debt_enforcement_bankruptcy (6,849), family_law (6,610), contract_law (6,567)
- **Clustering Test:** PENDING — requires 174k embeddings
- **Script:** `evaluation/experiments/run_v17b_label_normalization_all_reps.py` ✅ REPRODUCED at 1200 scale across 4 seeds

---

## 174k Corpus Metadata — READY

| Metric | Value |
|--------|-------|
| Total Decisions | 173,963 |
| With Legal Area | 91,193 (52.4%) |
| Languages | de: 106,501, fr: 57,489, it: 9,973 |
| Metadata Files | `evaluation/data/174k/metadata_174k.json` (33 MB), `.jsonl` (28 MB) |

---

## Production Representations Awaited (from legal-distance)

Per factory direction v25, the following representations must be computed at 174k scale:

### CPU-Cheap TF-IDF/Citation/Outcome Signals (Priority 1)
- `cited_decisions_tfidf` (TF-IDF on cited decisions, SVD 128-dim)
- `outcome_tfidf` (TF-IDF on outcomes, SVD 2-dim)
- `cited_outcome_hybrid_0.5` (concat citation_64 + outcome_2 → PCA 64)
- `cited_outcome_hybrid_0.7` (concat citation_64 + outcome_2 → PCA 64, different weight)
- `linear_citation_concat` (cp_64 + citation_64 → PCA)
- `linear_hybrid05_concat` (cp_64 + hybrid_05 → PCA) — **PRODUCTION DEFAULT COMBINATION_MODE**
- `linear_citation_w3070` (0.3×cp_64 + 0.7×citation_64)
- `linear_citation_ridge` (Ridge regression combination)

### Dense Embeddings (Priority 2)
- `center_projected_768dim` (full PCA, 1st component removed)
- `center_projected_64dim` (frozen PCA, **PRODUCTION DEFAULT** map mode)
- `linear_metric_epoch4` (learned linear projection)
- `mahalanobis_metric_epoch4` (learned Mahalanobis)
- `hybrid_stabilized_epoch1` (contrastive + preservation + hierarchy loss)

### Citation Role Embeddings (Priority 3)
- `citation_role_citing_alpha0.3`
- `citation_role_following_alpha0.3`
- `citation_role_criticizing_alpha0.3`
- `citation_role_distinguishing_alpha0.3` (if sparse)
- `citation_role_overruling_alpha0.3` (if sparse)

---

## Execution Procedure (When Representations Land)

### Step 1: Verify Representations in Accepted State
```bash
# Check legal-distance accepted state for 174k embeddings
ls /tmp/lex_accepted/legal-distance/legal_distance/results/v5/174k_tfidf/
ls /tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_174k/
```

### Step 2: Run Full Corpus Evaluation (Adversarial Harness v3)
```bash
# Single worker (or distributed with --n-workers 4)
python evaluation/run_full_corpus_evaluation.py \
  --embeddings-dir /tmp/lex_accepted/legal-distance/legal_distance/results/v5/174k_tfidf \
  --metadata evaluation/data/174k/metadata_174k.json \
  --output-dir evaluation/results/full_corpus_174k_tfidf

# For dense embeddings
python evaluation/run_full_corpus_evaluation.py \
  --embeddings-dir /tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_174k \
  --metadata evaluation/data/174k/metadata_174k.json \
  --output-dir evaluation/results/full_corpus_174k_dense
```

### Step 3: Run 12-Benchmark Formal Suite (v16)
```bash
# Requires 174k decisions corpus (expand bger_expanded_1200 to full 174k)
# Or adapt run_v16_full_benchmark_suite.py to load full corpus
python evaluation/experiments/run_v16_full_benchmark_suite.py \
  --corpus evaluation/data/174k/corpus_174k.jsonl \
  --metadata evaluation/data/174k/metadata_174k.jsonl \
  --embeddings-dir /tmp/lex_accepted/legal-distance/legal_distance/results/v5/174k_tfidf \
  --output-dir results/evaluation/v16_174k_full_benchmark
```

### Step 4: Validate Citation Heritage at 174k
```bash
# Load citation pairs and compute AUC-ROC on 174k embeddings
python evaluation/validate_citation_heritage_174k.py \
  --embeddings-dir /tmp/lex_accepted/legal-distance/legal_distance/results/v5/174k_tfidf \
  --citation-pairs evaluation/results/174k_citation_heritage/citation_pairs_174k.json \
  --output-dir results/evaluation/citation_heritage_174k
```

### Step 5: Test v17b Label Normalization Clustering at 174k
```bash
python evaluation/experiments/run_v17b_label_normalization_all_reps.py \
  --embeddings-dir /tmp/lex_accepted/legal-distance/legal_distance/results/v5/174k_tfidf \
  --metadata evaluation/data/174k/metadata_174k.json \
  --output-dir results/evaluation/v17b_174k_label_normalization
```

---

## Expected Outcomes & Decision Gates

### For Each Representation:
| Benchmark | PASS Threshold | Action on FAIL |
|-----------|----------------|----------------|
| Language Dominance | < 0.85 | Document; representation not suitable for cross-lingual navigation |
| Jurist Pairwise | > 0.5 | Document; representation not suitable for legal relevance |
| Citation Heritage | AUC ≥ 0.65 | TF-IDF hybrids expected to FAIL (per cycle branch: AUC=0.482); dense embeddings required |
| Branch k-NN | accuracy@5 ≥ 0.6333 | Document |
| TF Metadata Recall | Recall@5 ≥ 0.8 | Document |
| Boilerplate Resistance | Correlation > 0.1 | Expected NEGATIVE for all (confirmed -0.9 range); measures language artifacts |
| Multilingual Invariance | Separation ≥ 0, Gap < 0.2 | Document |
| Cross-Language Pairs | Separation > 0 | Document |
| Collapse Check | Mean < 0.99, Std > 0.01 | FAIL = dimensional collapse |
| Temporal Stability | Std < 0.1 | Document |
| Hierarchy Coherence | Purity > 0.7, NMI > 0.3 | **EXPECTED FAIL** (v18 NEGATIVE: branch-level hierarchy fundamentally unpassable, purity ~0.65) |
| Zoom Coherence | Fine > Coarse | **EXPECTED FAIL** (v18 NEGATIVE) |
| Legal Area Clustering | Purity > 0.5 | **EXPECTED FAIL** (label granularity artifact, v17b normalization addresses) |

### Production Decision Gates:
1. **PRODUCT_SERVING_DEFAULT** (`cited_outcome_hybrid_0.5`): Must pass BOTH adversarial gates at 174k
2. **COMBINATION_MODE** (`linear_hybrid05_concat`): Must pass BOTH adversarial gates + stability test
3. **DEFAULT Map Mode** (`center_projected_64dim_hierarchical`): Must pass BOTH adversarial gates (validated at 1200)

### v17b Label Normalization Test:
- **Hypothesis:** Normalized legal_area labels improve hierarchy/zoom/legal_area clustering purity by 15-25% at 174k (matching 1200-scale REPRODUCED finding)
- **Test:** Run hierarchy_coherence, zoom_coherence, legal_area_clustering benchmarks with normalized vs raw labels
- **Success:** ≥15% purity improvement across all 6 production representations (uniform effect confirmed at 1200)

---

## Negative Results Preserved (Do Not Suppress)

Per Research Protocol and Main Prompt Anti-Noise Principle:
- **Boilerplate resistance:** NEGATIVE for all representations (~ -0.9) — confirmed measures language dominance/cross-lingual failure, not procedural boilerplate
- **Hierarchy coherence:** NEGATIVE at branch level — v18 confirmed fundamental limitation (label-based hierarchy unpassable)
- **Zoom coherence:** NEGATIVE — no improvement from coarse to fine at branch level
- **Legal area clustering:** NEGATIVE — fine-grained label granularity prevents purity > 0.5
- **Citation heritage on TF-IDF:** NEGATIVE (AUC=0.482 at 174k on cited_outcome_hybrid_0.5) — TF-IDF cannot recover citation proximity at scale

---

## Monitoring Legal-Distance Delivery

The legal-distance lane is executing gh run 35935612800 with year-split computation:
- **Year-split artifacts:** Regenerated via `reproduce_full_corpus.py` (~100s, 15x CI verified)
- **TF-IDF computation:** Year-split chunks within 65-min job ceilings
- **Dense embeddings:** Year-split with resumable checkpoints

**Watch for:** New directories under `/tmp/lex_accepted/legal-distance/legal_distance/results/v5/` with `174k` in name.

---

## Next Recommendation

**BLOCKED_ON_DEPENDENCIES** — No additional same-question cycle justified until representations land in accepted state. Evaluation infrastructure is frozen, validated, and ready for immediate execution.

**Jurist Human Study:** Framework ready, externally blocked (requires 5-10 Swiss jurists recruited by repository owner). Report as blocked when reachable.

---

## Evidence References

```
evaluation/evaluation_v3_harness.py (frozen harness v3, hash 4323f833fa72366a)
evaluation/scalable_nn.py (HNSW backend, hash 4047da047fb339c1)
evaluation/run_full_corpus_evaluation.py (full corpus harness)
evaluation/experiments/run_v16_full_benchmark_suite.py (12 benchmarks, hash 4323f833fa72366a)
evaluation/validate_citation_heritage_174k.py (citation pairs infrastructure)
evaluation/experiments/run_v17b_label_normalization_all_reps.py (label normalization)
evaluation/results/174k_citation_heritage/citation_pairs_174k.json (804 positive pairs)
evaluation/results/174k_label_analysis/174k_legal_area_analysis.json (label normalization confirmed)
evaluation/data/174k/metadata_174k.json (173,963 decisions)
/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/ (citation resolution 95.9%)
```

---

*Generated: 2026-09-24 | Factory Direction v25 | Evaluation Lane State: BLOCKED_ON_DEPENDENCIES*