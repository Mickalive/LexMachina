# Evaluation v3 Frozen Benchmark Specification

**Factory Direction Version:** 6
**Evaluation Version:** 3 (frozen as of v6 completion)
**Global Seed:** 42
**Status:** FROZEN — Do not modify without Factory Director approval
**Date:** 2026-08-28

---

## Purpose

This document defines the **frozen adversarial benchmark suite** for evaluating legal map representations. All claim-bearing evaluations must use this exact configuration. The suite is designed to falsify attractive maps by testing:

1. **Language dominance resistance** — Legal structure should not be confounded by language
2. **Jurist pairwise preference** — Legally-relevant neighbors should outrank language artifacts
3. **Jurivoc hierarchy alignment** — Geometry should recover human intellectual indexing
4. **Scale stability** — Representations must be stable under corpus growth (frozen PCA)
5. **Boilerplate resistance** — Routine procedural text must not dominate geometry

---

## Corpus & Slice Definition

| Parameter | Value |
|-----------|-------|
| **Corpus** | Swiss Federal Supreme Court (BGer/BGE/ATF) decisions |
| **Slice** | Expanded 1,200 decisions (2020-2024 balanced sample) |
| **Metadata file** | `evaluation/data/bger_expanded_1200_metadata.jsonl` |
| **Languages** | de (735), fr (402), it (62) |
| **Branches** | oeffentliches_recht (568), zivilrecht (310), strafrecht (306), sozialversicherungsrecht (15) |
| **Valid decisions** | 1,199 (after filtering unknown branches) |

---

## Baseline Representation

| Parameter | Value |
|-----------|-------|
| **Name** | `center_projected` |
| **Source** | legal-distance v5 center_projected_full |
| **File** | `/tmp/lex_accepted/legal-distance/legal_distance/results/v5/center_projected_full/embeddings_center_projected.npy` |
| **Dimensions** | 768 (pre-PCA) → 64 (post frozen PCA for scale test) |
| **Method** | Language-centered projection (debiased citation blended) |
| **Evidence Tier** | REPRODUCED |

**Critical Note:** The 64-dim PCA-reduced version (v3) PASSED both adversarial gates (lang_dom=0.766, pairwise=0.512). The 768-dim version FAILS jurist pairwise (0.491). **Fractal-map and Product MUST use the 64-dim frozen PCA version.**

---

## Frozen PCA Pipeline (Scale Stability)

```python
# FIT ONCE on full 1200-decision corpus (shuffled with seed=42)
pca_debias = PCA(n_components=1, random_state=42)
pca_debias.fit(full_embeddings_shuffled)

debiased_full = full_embeddings_shuffled - pca_debias.transform(full_embeddings_shuffled) @ pca_debias.components_

pca_64 = PCA(n_components=64, random_state=42)
pca_64.fit(debiased_full)

# APPLY FROZEN to any subset
def apply_frozen_pipeline(embeddings_subset):
    debiased = embeddings_subset - pca_debias.transform(embeddings_subset) @ pca_debias.components_
    reduced = pca_64.transform(debiased)
    return normalize(reduced, norm='l2')
```

**Expected Results (frozen PCA on center_projected):**
| Corpus Size | Position Drift (cosine) | Neighbor Preservation (k=10) | Cluster NMI |
|-------------|------------------------|------------------------------|-------------|
| 200 | 1.000000 | 0.1525 | 1.0000 |
| 400 | 1.000000 | 0.3163 | 1.0000 |
| 600 | 1.000000 | 0.4922 | 1.0000 |
| 800 | 1.000000 | 0.6569 | 1.0000 |
| 1000 | 1.000000 | 0.8255 | 1.0000 |

---

## Adversarial Benchmark Suite

### 1. Adversarial Language Dominance
**File:** `evaluation/tests/cross_language_benchmarks.py::adversarial_language_dominance`
**Threshold:** `mean_language_dominance < 0.85` (PASS = lower is better)
**k-NN:** 20
**Metric:** Fraction of top-20 neighbors sharing the same language as query

```python
def adversarial_language_dominance(embeddings, metadata, k=20):
    nn = NearestNeighbors(n_neighbors=k+1, metric='cosine')
    nn.fit(embeddings)
    _, indices = nn.kneighbors(embeddings)
    neighbors = indices[:, 1:]
    
    dominance_rates = []
    for i, m in enumerate(metadata):
        lang = m['language']
        neighbor_langs = [metadata[n]['language'] for n in neighbors[i]]
        same_lang = sum(1 for l in neighbor_langs if l == lang)
        dominance_rates.append(same_lang / k)
    
    return {
        'mean_language_dominance': np.mean(dominance_rates),
        'status': 'PASS' if np.mean(dominance_rates) < 0.85 else 'FAIL'
    }
```

**Baseline (center_projected 768-dim):** 0.7733 → **PASS**

---

### 2. Jurist Pairwise Preference Simulation
**File:** `evaluation/tests/jurist_usability.py::simulate_pairwise_preference`
**Threshold:** `legal_neighbor_rate > 0.5` (PASS = majority have legally-relevant neighbor)
**k-NN:** 10
**Simulation:** For each decision, check if top-10 contains:
- **Legal-relevant:** Same branch, different language
- **Language artifact:** Same language, different branch

```python
def simulate_pairwise_preference(embeddings, branches, languages, k=10):
    # ... build NN graph ...
    for i in range(n):
        has_legal = any(nb == branches[i] and nl != languages[i] 
                       for nb, nl in zip(neighbor_branches, neighbor_langs))
        has_lang_artifact = any(nb != branches[i] and nl == languages[i] 
                               for nb, nl in zip(neighbor_branches, neighbor_langs))
        # Count categories
    
    legal_neighbor_rate = (legal_relevant_only + both) / total
    return {'legal_neighbor_rate': legal_neighbor_rate, 'status': 'PASS' if legal_neighbor_rate > 0.5 else 'FAIL'}
```

**Baseline (center_projected 768-dim):** 0.4912 → **FAIL (borderline)**
**Baseline (center_projected 64-dim v3):** 0.512 → **PASS**

---

### 3. Jurist Cluster Coherence Rating
**File:** `evaluation/tests/jurist_usability.py::simulate_cluster_coherence_rating`
**Threshold:** `mean_branch_purity > 0.7` (PASS)
**Clusters:** 16 (KMeans, random_state=42)
**Metric:** Branch purity per cluster + NMI with branch labels

```python
kmeans = KMeans(n_clusters=16, random_state=42, n_init=10)
cluster_labels = kmeans.fit_predict(embeddings)
mean_purity = compute_branch_purity(cluster_labels, branches)
nmi = normalized_mutual_info_score(branches, cluster_labels)
```

**Baseline (center_projected 768-dim):** 0.8681 purity, 0.3774 NMI → **PASS**

---

### 4. Jurist Cross-Language Retrieval
**File:** `evaluation/tests/jurist_usability.py::simulate_cross_language_retrieval`
**Threshold:** `mean_cross_language_recall_at_k > 0.2` (PASS)
**k-NN:** 10
**Metric:** Recall of same-branch cross-language decisions in top-10

**Baseline (center_projected 768-dim):** 0.1456 → **FAIL**

---

### 5. Jurivoc Hierarchy Alignment
**File:** `evaluation/tests/jurivoc_benchmarks.py::JurivocBenchmarks.run_all`
**Thresholds:**
- L1 Descriptor Recovery NMI ≥ 0.3
- L2 Descriptor Recovery NMI ≥ 0.3
- L1 k-NN Purity ≥ 0.4
- L2 k-NN Purity ≥ 0.4
- Hierarchy Separation ≥ 0.05 (same_parent_mean_sim - diff_parent_mean_sim)

**Baseline (center_projected 768-dim):** 4/5 PASS (L1 NMI=0.274 FAIL, others PASS)

---

### 6. Scale Stability (Frozen PCA)
**File:** `evaluation/tests/scale_benchmarks_frozen.py::run_frozen_scale_benchmark`
**Method:** PCA fit ONCE on full corpus, applied to subsets
**Corpus sizes:** [200, 400, 600, 800, 1000]
**Metrics:** Position drift (cosine), Neighbor preservation (k=10), Cluster stability (NMI, k=10)
**Thresholds:** Position drift → 1.0 (perfect), Cluster NMI → 1.0 (perfect)

**Baseline (center_projected):** **PASS** — Perfect position drift (1.0) and cluster stability (1.0)

---

### 7. Boilerplate Resistance
**File:** `evaluation/tests/boilerplate_resistance.py`
**Status:** **SKIPPED** — Requires full decision text from corpus lane
**Note:** Not available in expanded slice metadata (metadata only). Requires corpus text for perturbation test.

---

## Success Rules (Frozen)

A representation **beats the baseline** if it achieves:

| Benchmark | Baseline (768-dim) | Target to Beat |
|-----------|-------------------|----------------|
| Language Dominance | 0.7733 (PASS) | < 0.85 (same) |
| Jurist Pairwise | 0.4912 (FAIL) | **> 0.5 (PASS)** |
| Cluster Coherence | 0.8681 (PASS) | > 0.7 (same) |
| Cross-Lang Retrieval | 0.1456 (FAIL) | > 0.2 (PASS) |
| Jurivoc L1 NMI | 0.274 (FAIL) | ≥ 0.3 (PASS) |
| Jurivoc L2 NMI | 0.430 (PASS) | ≥ 0.3 (same) |
| Jurivoc Hierarchy Sep | 0.0956 (PASS) | ≥ 0.05 (same) |
| Scale Stability | Perfect (PASS) | Perfect (same) |

**Minimum to claim improvement:** MUST pass BOTH adversarial gates (Language Dominance < 0.85 AND Jurist Pairwise > 0.5)

---

## Reproducibility Checklist

- [x] Global seed = 42 (numpy, sklearn)
- [x] Corpus slice fixed (expanded 1,200)
- [x] Baseline embeddings fixed (center_projected_full v5)
- [x] Frozen PCA components fixed (fit on full 1200)
- [x] All KMeans use random_state=42, n_init=10
- [x] All PCA use random_state=42
- [x] NearestNeighbors deterministic (no randomness)
- [x] Metadata branch/language mapping fixed
- [x] All thresholds pre-declared

---

## Signal Ablation Variants Tested (v6)

| Variant | Lang Dominance | Jurist Pairwise | Both Gates? | Notes |
|---------|---------------|-----------------|-------------|-------|
| center_projected (768) | 0.774 PASS | 0.491 FAIL | NO | Baseline |
| center_projected (64, v3) | 0.766 PASS | 0.512 PASS | **YES** | Use for product |
| sachverhalt_tfidf | 0.770 PASS | 0.269 FAIL | NO | v5 zoom winner |
| erwaegungen_tfidf | 0.904 FAIL | 0.103 FAIL | NO | Language dominated |
| norm_embeddings | 0.763 PASS | 0.273 FAIL | NO | |
| citation_weights | 0.459 PASS | 0.729 PASS | **YES** | **DEGENERATE** (single cluster, Jurivoc NMI=0.0) |
| sachverhalt+erwaegungen | 0.842 PASS | 0.143 FAIL | NO | |
| erwaegungen+norms | 0.868 FAIL | 0.159 FAIL | NO | |
| erwaegungen+citations | 0.891 FAIL | 0.172 FAIL | NO | |
| core_legal | 0.872 FAIL | 0.191 FAIL | NO | |
| hybrid_erwaegungen_03 | 0.810 PASS | 0.420 FAIL | NO | Best hybrid |
| hybrid_erwaegungen_05 | 0.832 PASS | 0.384 FAIL | NO | |
| hybrid_erwaegungen_07 | 0.865 FAIL | 0.331 FAIL | NO | |
| hybrid_core_03 | 0.821 PASS | 0.401 FAIL | NO | |
| hybrid_core_05 | 0.840 PASS | 0.362 FAIL | NO | |
| hybrid_core_07 | 0.875 FAIL | 0.298 FAIL | NO | |

**Conclusion:** NO signal ablation variant beats center_projected on both adversarial gates. The 64-dim center_projected (v3 version) remains the only representation passing both gates.

---

## Legal Embeddings Tested (v3/v4)

| Model | Lang Dominance | Jurist Pairwise | Jurivoc L2 NMI |
|-------|---------------|-----------------|----------------|
| multilingual-e5-small | 0.999 FAIL | — | 0.502 |
| paraphrase-multilingual-MiniLM | 0.972 FAIL | — | — |
| xlm-roberta-base | 0.999 FAIL | — | — |

**All FAIL language dominance gate (>0.85)** despite good Jurivoc recovery.

---

## Citation Role Embeddings Tested (v3/v4)

| Role | Result |
|------|--------|
| overruling | DEGENERATE |
| distinguishing | DEGENERATE |
| following | DEGENERATE |
| all_weighted | DEGENERATE |
| citing | DEGENERATE |
| criticizing | DEGENERATE |

**All 6 roles produce IDENTICAL embeddings:** Single cluster, branch_purity=0.467, branch_nmi=0.0, Jurivoc NMI=0.0. Useless standalone without semantic blending.

---

## Frontier Metric Learning Validation

**Status:** **BLOCKED** — No `frontier_metric_learning_jurivoc` team dispatched
**Directory:** `/tmp/lex_accepted/frontier/` — EMPTY
**Required:** Factory Director must dispatch team or remove from factory direction

---

## Next Steps for Factory Director

1. **Acknowledge evaluation v6 complete** with negative signal ablation result
2. **Direct legal-distance** to either:
   - Improve 64-dim center_projected baseline (e.g., better PCA, different debiasing)
   - Develop new signal combinations that pass both adversarial gates
3. **Direct fractal-map** to use 64-dim center_projected (v3 version), not 768-dim
4. **Either dispatch** `frontier_metric_learning_jurivoc` team **or remove** from factory direction
5. **Define successor evaluation question** focusing on:
   - Improving jurist pairwise preference for center_projected
   - Testing new hybrid formulations
   - Boilerplate resistance once corpus text available

---

## File References (Immutable)

| Artifact | Path |
|----------|------|
| v6 Signal Ablation Results | `results/evaluation/v6_signal_ablation/v6_signal_ablation_adversarial_results.json` |
| v6 Baseline Results | `results/evaluation/v6_signal_ablation/v6_baseline_center_projected_results.json` |
| v3 Evaluation Results | `results/evaluation/v3_evaluation_results.json` |
| v4 Evaluation Results | `results/evaluation/v4_evaluation_results.json` |
| v5 Evaluation Results | `results/evaluation/v5_evaluation_results.json` |
| v2 Verification Results | `results/evaluation/v2_verification_results.json` |
| Evaluation Harness | `evaluation/harness/evaluation_harness.py` |
| Cross-Language Benchmarks | `evaluation/tests/cross_language_benchmarks.py` |
| Jurist Usability | `evaluation/tests/jurist_usability.py` |
| Jurivoc Benchmarks | `evaluation/tests/jurivoc_benchmarks.py` |
| Scale Benchmarks (Frozen) | `evaluation/tests/scale_benchmarks_frozen.py` |
| Boilerplate Resistance | `evaluation/tests/boilerplate_resistance.py` |

---

**END OF FROZEN SPECIFICATION — DO NOT MODIFY WITHOUT FACTORY DIRECTOR APPROVAL**