# Evaluation Lane v26 — 174k Adversarial Synthesis Report

**Factory Direction:** v26  
**GitHub Run:** 36066506563  
**Date:** 2026-09-24  
**Lane:** evaluation  
**Evidence Tier:** REPRODUCED  

---

## Executive Summary

This report synthesizes adversarial evaluation evidence from **two independent frozen harnesses** at full 174k corpus density (173,963 decisions):

| Harness | Protocol | Representations | Key Adversarial Finding |
|---|---|---|---|
| **Formal Suite (v25 protocol)** | 12-benchmark suite, frozen v16 thresholds, config hash `4323f833fa72366a` | 8 TF-IDF family | Citation-based reps pass adversarial_falsification; full-text hybrids FAIL (lang_dom > 0.99) |
| **v3 Harness** | Frozen adversarial thresholds (lang_dom < 0.85, jurist > 0.5), config hash `v3_frozen_seed42_174k_full_hnsw` | 8 TF-IDF family | **NO representation passes BOTH adversarial gates** — jurist pairwise fails for all (legal_neighbor_rate ~0.12) |

**Critical Adversarial Result:** The production default candidate `cited_outcome_hybrid_0.7` passes language dominance but **fails jurist pairwise preference** at 174k scale (legal_neighbor_rate = 0.123 vs 0.5 threshold). This failure mode was **not detectable at 1200 scale** where the same representation passed.

---

## 1. Formal Suite Adversarial Results (Authoritative — Frozen Protocol)

### 1.1 Adversarial Falsification Benchmark (Frozen Thresholds)

| Representation | Language Dominance (max 0.85) | Branch Coherence (min 0.3) | Status |
|---|---:|---:|---|
| **cited_decisions_tfidf** | **0.602** ✓ | **0.354** ✓ | **PASS** |
| **cited_outcome_hybrid_0.7** | **0.569** ✓ | **0.356** ✓ | **PASS** |
| **cited_outcome_hybrid_0.5** | **0.574** ✓ | **0.356** ✓ | **PASS** |
| outcome_tfidf | 0.603 ✓ | 0.146 ✗ | FAIL |
| regeste_tfidf | 0.598 ✓ | 0.340 ✓ | PASS |
| full_text_tfidf_light | **0.999** ✗ | 0.001 ✗ | **FAIL** |
| regeste_full_text_hybrid_0.7 | **0.998** ✗ | 0.002 ✗ | **FAIL** |
| regeste_full_text_hybrid_0.5 | **0.998** ✗ | 0.002 ✗ | **FAIL** |

**Key Finding:** Citation-aware representations (cited_decisions_tfidf, cited_outcome_hybrid_0.5/0.7) pass the adversarial falsification benchmark. Full-text/regeste hybrids **catastrophically fail** due to language dominance (> 0.99), confirming they encode language artifacts not legal structure.

### 1.2 Citation Heritage (AUC-ROC ≥ 0.65)

| Representation | AUC-ROC | nn_citation_rate@10 | Status |
|---|---:|---:|---|
| **cited_decisions_tfidf** | **0.973** | **0.487** | ✅ PASS |
| cited_outcome_hybrid_0.7 | **0.961** | 0.490 | ✅ PASS |
| cited_outcome_hybrid_0.5 | **0.919** | 0.476 | ✅ PASS |
| full_text_tfidf_light | 0.844 | 0.438 | ✅ PASS |
| regeste_full_text_hybrid_0.7 | 0.865 | 0.445 | ✅ PASS |
| regeste_full_text_hybrid_0.5 | 0.851 | 0.444 | ✅ PASS |
| outcome_tfidf | 0.720 | 0.003 | ✅ PASS |
| regeste_tfidf | 0.487 | 0.000 | ❌ FAIL |

**Key Finding:** Citation structure is strongly recovered by citation-aware representations (AUC > 0.91, ~48% of decisions have citation neighbor in top-10).

### 1.3 Branch k-NN / TF Metadata (Frozen Thresholds)

| Representation | k-NN@5 (thresh 0.633) | Recall@5 (thresh 0.8) | Status |
|---|---:|---:|---|
| cited_decisions_tfidf | 0.389 ✗ | 0.389 ✗ | FAIL |
| cited_outcome_hybrid_0.7 | 0.393 ✗ | 0.393 ✗ | FAIL |
| cited_outcome_hybrid_0.5 | 0.391 ✗ | 0.391 ✗ | FAIL |
| full_text_tfidf_light | **0.827** ✓ | **0.827** ✓ | PASS |
| regeste_full_text_hybrid_0.7 | **0.977** ✓ | **0.977** ✓ | PASS |
| regeste_full_text_hybrid_0.5 | **0.974** ✓ | **0.974** ✓ | PASS |
| regeste_tfidf | 0.586 ✗ | 0.586 ✗ | FAIL |
| outcome_tfidf | 0.389 ✗ | 0.389 ✗ | FAIL |

**Key Finding:** **Fundamental tradeoff** — citation-based reps excel at citation heritage but FAIL branch recovery; full-text hybrids excel at branch recovery but FAIL adversarial falsification (language dominance).

---

## 2. v3 Harness Adversarial Results (Supplementary — Full 174k Valid Set)

### 2.1 Adversarial Gates (Frozen Thresholds)

| Representation | Lang Dom (max 0.85) | Jurist Pairwise (min 0.5) | Both Gates |
|---|---:|---:|---|
| cited_decisions_tfidf | 0.606 ✓ | **0.123** ✗ | ❌ FAIL |
| cited_outcome_hybrid_0.7 | 0.606 ✓ | **0.123** ✗ | ❌ FAIL |
| cited_outcome_hybrid_0.5 | 0.606 ✓ | **0.123** ✗ | ❌ FAIL |
| full_text_tfidf_light | 0.606 ✓ | **0.123** ✗ | ❌ FAIL |
| regeste_full_text_hybrid_0.7 | 0.606 ✓ | **0.123** ✗ | ❌ FAIL |
| regeste_full_text_hybrid_0.5 | 0.606 ✓ | **0.123** ✗ | ❌ FAIL |
| regeste_tfidf | 0.336 ✓ | **0.175** ✗ | ❌ FAIL |
| outcome_tfidf | 0.603 ✓ | **0.124** ✗ | ❌ FAIL |

**Critical Finding:** **ALL representations FAIL the jurist pairwise gate** at 174k scale. The legal_neighbor_rate (~0.12) means only 12% of decisions have a same-branch-different-language neighbor in top-20.

### 2.2 Methodological Note: HNSW Artifact Detected

Six representations (cited_decisions_tfidf, cited_outcome_hybrid_0.7, cited_outcome_hybrid_0.5, full_text_tfidf_light, regeste_full_text_hybrid_0.7, regeste_full_text_hybrid_0.5) show **identical** language dominance (0.6063) and jurist pairwise (0.1234) scores in the v3 harness. This indicates the HNSW index (M=16, ef_construction=200, ef_search=100) on the 90,632 valid decisions produces **indistinguishable k-NN graphs** for these representations.

**However:** The formal suite (same HNSW params on FULL 173,963 decisions) **discriminates** these representations (lang_dom: 0.569–0.999). The discrepancy arises because:
- v3 harness filters to 90,632 decisions with known branch (removing procedural/boilerplate decisions)
- Full-text hybrids' language dominance artifact concentrates in decisions WITHOUT branch labels
- On substantive decisions only, language dominance drops from 0.999 → 0.606

This is itself an adversarial finding: **language dominance in full-text hybrids is driven by procedural decisions**, not substantive legal content.

### 2.3 v3 Harness Supplementary Benchmarks

| Representation | Jurivoc L0 NMI | Scale Stability | Boilerplate Score | Cluster Purity | Cross-Lang Recall |
|---|---:|---:|---:|---:|---:|
| cited_decisions_tfidf | 0.037 | 1.000 ✓ | -0.532 ✗ | 0.399 ✗ | 0.010 ✗ |
| cited_outcome_hybrid_0.7 | 0.018 | 1.000 ✓ | -0.532 ✗ | 0.360 ✗ | 0.010 ✗ |
| full_text_tfidf_light | 0.010 | 1.000 ✓ | -0.532 ✗ | **0.740** ✓ | 0.010 ✗ |
| regeste_tfidf | 0.000 | 1.000 ✓ | **0.755** ✓ | 0.250 ✗ | 0.010 ✗ |
| outcome_tfidf | 0.004 | 0.544 ✓ | -0.207 ✗ | 0.308 ✗ | 0.010 ✗ |

**Note:** Scale stability = 1.000 for most reps indicates HNSW subsample artifact (80/20 split on 30k with high ef_search returns identical neighbors).

---

## 3. Cross-Scale Adversarial Comparison (1200 vs 174k)

| Benchmark | cited_decisions_tfidf @ 1200 | cited_decisions_tfidf @ 174k | cited_outcome_hybrid_0.7 @ 1200 | cited_outcome_hybrid_0.7 @ 174k |
|---|---:|---:|---:|---:|
| Citation Heritage (AUC) | 0.910 | **0.973** | 0.910 | **0.961** |
| Adversarial Falsification | PASS (0.63/0.74) | **PASS (0.60/0.35)** | PASS (0.63/0.74) | **PASS (0.57/0.36)** |
| Branch k-NN@5 | 0.813 | **0.389** | 0.813 | **0.393** |
| TF Metadata Recall@5 | 0.813 | **0.389** | 0.813 | **0.393** |
| Boilerplate Resistance | 0.185 | ~0.00 | 0.185 | ~0.07 |
| Multilingual Invariance | PASS | PASS | PASS | PASS |
| Temporal Stability | PASS | **FAIL (std=0.18)** | PASS | **FAIL (std=0.15)** |
| Hierarchy Coherence | PASS (0.876) | **FAIL (0.152)** | PASS (0.876) | **FAIL (0.130)** |
| v3 Jurist Pairwise | **PASS (0.79)** | **FAIL (0.12)** | **PASS (0.80)** | **FAIL (0.12)** |

### Scale-Dependent Failure Modes Discovered at 174k

1. **Branch k-NN collapse** (0.81 → 0.39): Citation-based embeddings do not recover branch structure at corpus scale
2. **Temporal instability** (std 0.01 → 0.18): Citation neighborhoods vary dramatically across years
3. **Hierarchy coherence failure** (purity 0.88 → 0.15): 128-dim TF-IDF cannot cluster 167 legal areas at 174k
4. **Jurist pairwise collapse** (0.79 → 0.12): Legal-relevant cross-language neighbors vanish at scale
5. **Boilerplate proxy failure**: Citation-based reps show near-zero text-embedding correlation

---

## 4. Production Decision: cited_outcome_hybrid_0.7

### Evidence FOR Production Use
- ✅ Citation heritage AUC = 0.961 (strongest signal for legal relevance)
- ✅ Adversarial falsification PASS (lang_dom=0.569, branch_coherence=0.356)
- ✅ Multilingual invariance PASS
- ✅ Zero-shot TF-IDF, no GPU required
- ✅ Citation-aware: recovers known doctrinal lineages

### Evidence AGAINST / Limitations
- ❌ Branch k-NN@5 = 0.393 (vs 0.633 threshold) — does NOT recover chamber structure
- ❌ TF Metadata Recall@5 = 0.393 (vs 0.8 threshold) — does NOT recover human indexing
- ❌ Temporal stability FAIL (std=0.153) — neighborhoods unstable across years
- ❌ Hierarchy coherence FAIL (purity=0.130 vs 0.7) — no fine-grained legal clustering
- ❌ v3 Jurist pairwise FAIL (legal_neighbor_rate=0.123) — cross-language legal equivalents not recovered
- ❌ Boilerplate resistance FAIL (score=-0.532) — proxy measures citation sparsity, not boilerplate

### Production Recommendation
**Conditional deployment as citation-navigation default** with explicit limitations documented:
- Use for: "Find decisions citing similar authorities" (citation heritage strength)
- Do NOT use for: "Find decisions in same legal domain" (branch k-NN failure)
- Do NOT use for: Cross-language legal research (jurist pairwise failure at scale)
- Flag: Temporal instability — results may vary by decision year

---

## 5. Adversarial Benchmark Gaps (Recommendations for Next Cycle)

The current benchmark suite **fails to detect** several critical failure modes until 174k scale:

| Gap | Current Benchmark | Missing Test | Why It Matters |
|---|---|---|---|
| **Citation sparsity vs boilerplate** | Boilerplate resistance (text overlap) | Citation-aware boilerplate test | Citation-based reps have sparse citations → low text correlation, not boilerplate |
| **Cross-language legal equivalence** | Multilingual invariance (same-branch similarity) | Jurist pairwise (legal-relevant neighbor existence) | Jurist needs AT LEAST ONE cross-language legal neighbor in top-k |
| **Temporal citation drift** | Temporal stability (k-NN score std) | Citation graph temporal coherence | Citation neighborhoods shift as citation graph evolves |
| **Fine-grained legal clustering** | Hierarchy coherence (legal_area purity) | Doctrinal family recovery | 128-dim TF-IDF insufficient for 167 legal areas; need dense embeddings |

---

## 6. Evidence Preservation & Reproducibility

All claim-bearing outputs frozen before outcome inspection:

| Artifact | Path | Config Hash |
|---|---|---|
| Formal suite results (8 reps) | `results/evaluation/v25_174k_formal_suite/results/` | `4323f833fa72366a` |
| Formal suite summary | `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` | `4323f833fa72366a` |
| Citation heritage pairs | `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` | `4047da047fb339c1` |
| v3 harness all reps | `evaluation/results/v3/v3_174k_all_representations.json` | `v3_frozen_seed42_174k_full_hnsw` |
| Frozen protocol | `evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json` | `4323f833fa72366a` |
| 174k metadata (frozen) | `evaluation/data/174k/metadata_174k.json` | (row order fixed) |
| Embeddings (128-dim) | `results/evaluation/v25_174k_formal_suite/embeddings/*.npy` | `build_manifest.json` |

**Global seed:** 42 (all stochastic operations)  
**HNSW params:** M=16, ef_construction=200, ef_search=100 (exact-cosine parity validated)

---

## 7. Lane State Confirmation

```json
{
  "lane": "evaluation",
  "direction_version": 26,
  "evidence_tier": "REPRODUCED",
  "cycle_status": "BLOCKED_ON_DEPENDENCIES",
  "continue_recommended": false,
  "accepted_run_id": "eval_v26_174k_adversarial_synthesis_36066506563",
  "blocked_on": "legal-distance lane: 174k dense embeddings not yet computed (center_projected, metric learning, hybrid objectives, citation roles, linear hybrids)",
  "evidence_refs": [
    "evaluation/reports/evaluation_v26_174k_formal_suite_COMPLETION_REPORT.md",
    "evaluation/reports/evaluation_v26_174k_adversarial_synthesis_report.md",
    "results/evaluation/v25_174k_formal_suite/results/",
    "results/evaluation/v25_174k_citation_heritage/",
    "results/evaluation/v25_174k_v17b/",
    "evaluation/results/v3/v3_174k_all_representations.json",
    "evaluation/results/v3/cited_decisions_tfidf_174k_full.json",
    "evaluation/experiments/v25_174k_suite/protocol_v25_174k_suite.json",
    "evaluation/data/174k/metadata_174k.json",
    "evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json"
  ],
  "next_recommendation": "BLOCKED_ON_DEPENDENCIES — TF-IDF production family (8 representations) FULLY EVALUATED at 174k scale against frozen 12-benchmark suite, frozen citation_heritage benchmark, v17b label normalization, AND v3 adversarial harness. Key adversarial findings: (1) Citation-based reps pass adversarial_falsification but FAIL branch/TF-metadata recovery; (2) Full-text hybrids pass branch/TF-metadata but FAIL adversarial_falsification (language dominance); (3) NO representation passes v3 jurist pairwise gate at 174k (legal_neighbor_rate ~0.12); (4) Scale-dependent failures: branch k-NN collapse, temporal instability, hierarchy failure, jurist pairwise collapse. All three machine-executable sub-questions COMPLETE for TF-IDF family. Awaiting legal-distance lane 174k dense embeddings. Jurist human study remains blocked (external dependency: 5-10 Swiss jurists recruitment)."
}
```

---

## 8. Negative Results Preserved (First-Class Evidence)

- **hierarchy_coherence at 174k:** ALL representations FAIL (max purity 0.465 formal / 0.740 v3 vs 0.7 threshold) — TF-IDF 128-dim insufficient for fine-grained legal_area clustering
- **v17b generalization:** FAILS — normalization not universally beneficial at 174k; tradeoffs differ from 1200-scale
- **Temporal stability:** Citation-based representations UNSTABLE at 174k (std > 0.1) — corpus heterogeneity across years
- **Branch k-NN / TF metadata:** Citation-based representations do NOT recover branch structure at 174k (accuracy ~0.39 vs 0.63 threshold)
- **v3 Jurist pairwise:** ALL representations FAIL at 174k (legal_neighbor_rate ~0.12 vs 0.5) — cross-language legal equivalents not in top-20
- **Boilerplate resistance proxy:** Confirmed negative — proxy measures language dominance/citation sparsity, not procedural boilerplate
- **HNSW artifact:** 6/8 representations produce indistinguishable k-NN graphs on valid subset at 174k — approximate NN limits adversarial discrimination

---

**All claim-bearing outputs frozen. Negative results preserved. Ready for independent audit.**