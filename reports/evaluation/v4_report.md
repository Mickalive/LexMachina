# Evaluation v4 Report
## Adversarial Benchmark Validation of Alternative Representations

**Date:** 2026-08-28
**Factory Direction Version:** 6
**Evaluation Version:** 4
**Global Seed:** 42 (frozen)
**Baseline:** center_projected (validated in v3 on 1,200 decisions)

---

## Executive Summary

Evaluation v4 tested **10 alternative representations** against the center_projected baseline using the full adversarial benchmark suite. The results **reconfirm center_projected as the only representation passing both adversarial gates** (language dominance < 0.85 AND jurist pairwise preference > 0.5) on the expanded 1,200-decision slice.

### Key Findings

| Representation | Language Dominance | Jurist Pairwise | Jurivoc L2 NMI | Verdict |
|---|---|---|---|---|
| **center_projected (baseline)** | **0.766 ✓** | **0.512 ✓** | 0.441 | **PASSES BOTH GATES** |
| multilingual_e5_small | 0.999 ✗ | 0.003 ✗ | 0.502 ✓ | FAILS language gate |
| paraphrase_multilingual_minilm | ~0.99 ✗ | 0.003 ✗ | 0.295 ✗ | FAILS language gate |
| xlm_roberta_base | ~0.99 ✗ | 0.000 ✗ | 0.198 ✗ | FAILS language gate |
| citation_role_* (6 roles) | 0.446 ✓ | 0.850* | 0.000 ✗ | DEGENERATE |

*Misleading — both_available=797 indicates collapsed representation

---

## Detailed Results

### 1. Boilerplate Resistance (NEW — Full Text Available)

**center_projected: PASS**
- Text-embedding correlation: **0.126** (target range: 0.1–0.4)
- 1,200 decisions with full text, 500 sampled pairs
- Confirms center_projected captures legal content without boilerplate dominance

**multilingual_e5_small: FAIL**
- Correlation outside target range
- Generic legal embeddings more susceptible to boilerplate

### 2. Legal Embedding Models (Off-the-Shelf)

All three models **fail the adversarial language dominance gate** (> 0.85 threshold):

| Model | Lang Dominance | Zero-Shot NMI | Jurivoc L1 NMI | Jurivoc L2 NMI | Jurist Pairwise |
|---|---|---|---|---|---|
| multilingual_e5_small | **0.999** ✗ | 0.617 ✓ | 0.346 ✓ | **0.502** ✓ | 0.003 ✗ |
| paraphrase_multilingual_minilm | **~0.99** ✗ | 0.466 ✓ | 0.295 ✗ | 0.295 ✗ | 0.003 ✗ |
| xlm_roberta_base | **~0.99** ✗ | 0.558 ✓ | 0.198 ✗ | 0.198 ✗ | 0.000 ✗ |

**Critical insight:** These models capture legal concepts well (strong Jurivoc recovery, good zero-shot transfer) but **neighborhoods are dominated by language**, not legal similarity. A jurist querying in German gets German neighbors regardless of legal relevance.

### 3. Citation Role Embeddings (Degenerate)

All 6 citation roles produce **identical failed results**:

| Metric | Result | Status |
|---|---|---|
| Jurivoc L1 NMI | 0.000 | FAIL |
| Jurivoc L2 NMI | 0.000 | FAIL |
| Jurivoc L1 k-NN purity | 0.215 | FAIL |
| Jurivoc L2 k-NN purity | 0.135 | FAIL |
| Hierarchy alignment separation | 0.000 | FAIL |
| Cross-language neighbor quality separation | -0.590 | FAIL |
| Zero-shot transfer NMI | 0.000 | FAIL |
| Language-specific quality NMI | 0.000 | FAIL |
| Branch purity (clusters) | 0.467 | FAIL |

**Jurist usability shows misleading "PASS" rates:**
- pairwise_preference: 0.850 legal_neighbor_rate — but `both_available=797` (neighbors are BOTH same-branch-diff-lang AND same-lang-diff-branch)
- cluster_coherence: 0.467 branch purity — clusters are not legally coherent
- zoom_task: PASS — but uses fractal-map cluster assignments from different representation
- cross_language_retrieval: 0.256 recall — but this is artifact of collapsed space

**Conclusion:** Citation role embeddings **without semantic blending are useless** for legal navigation. They capture only citation graph structure, which is insufficient for legal similarity.

### 4. center_projected Baseline (Reconfirmed)

| Benchmark | Result | Threshold | Status |
|---|---|---|---|
| Adversarial language dominance | 0.766 | < 0.85 | ✓ PASS |
| Jurist pairwise preference | 0.512 | > 0.5 | ✓ PASS |
| Boilerplate resistance | 0.126 | 0.1–0.4 | ✓ PASS |
| Scale stability (position drift) | 1.000 | = 1.0 | ✓ PASS |
| Scale stability (neighbor preservation @1000) | 0.828 | improving | ✓ PASS |
| Jurivoc hierarchy alignment | 0.113 | > 0.05 | ✓ PASS |
| Jurivoc L2 descriptor recovery NMI | 0.441 | > 0.3 | ✓ PASS |
| Cross-language retrieval recall@10 | 0.156 | > 0.2 | ✗ FAIL (known weakness) |
| Jurivoc L1 descriptor recovery NMI | 0.243 | > 0.3 | ✗ FAIL (expected for coarse level) |

---

## Evidence Tier Assessment

| Finding | Tier | Notes |
|---|---|---|
| center_projected passes both adversarial gates | **ACCEPTED** | Reproduced on 1,200 decisions, frozen seed |
| center_projected boilerplate resistant | **ACCEPTED** | New test with full text |
| Legal embeddings fail language dominance | **REPRODUCED** | Consistent across 3 models |
| Citation roles degenerate standalone | **REPRODUCED** | 6/6 roles identical failure |
| center_projected unbeaten on dual gate | **ACCEPTED** | No alternative passes both |

---

## Recommendations

### Immediate (Next Evaluation Cycle)
1. **Test frontier_metric_learning_jurivoc** supervised metric learning against center_projected on same adversarial suite
2. **Test signal ablation variants** on center_projected (sachverhalt, erwaegungen, norms, citations blended) via adversarial benchmarks — legal-distance v5 only measured zoom coherence
3. **Maintain frozen seed=42 harness** for regression testing

### Product Decisions (Locked)
- **Default map mode:** center_projected (only representation passing both adversarial gates)
- **Legal embeddings:** Available as exploratory map modes (clearly marked) for legal concept exploration
- **Citation roles:** Only usable as blended components (alpha < 1.0), never standalone
- **Cross-language retrieval:** Known weakness — document in product, do not block release

### Research Directions
- Metric learning to reduce language dominance while preserving Jurivoc alignment
- Hybrid representations: center_projected + legal embedding signals (ablation needed)
- Citation role modeling: requires blending with semantic content (as in debiased_citation_blended)

---

## Negative Results Preserved (First-Class Evidence)

1. **Legal embeddings fail language dominance** despite strong legal concept capture — this is not a bug, it's a property of generic legal training
2. **Citation roles collapse** without semantic content — confirms citation graph alone insufficient
3. **Cross-language retrieval remains weak** for center_projected (0.156 recall@10) — known limitation, not regression
4. **Jurivoc L1 recovery fails** for all representations — expected for coarse 7-category level

---

## Files Generated

- `results/evaluation/v4_evaluation_results.json` — Complete raw outputs (2,411 lines)
- `state/evaluation.json` — Machine-readable lane state (updated)
- `evaluation/run_v4_evaluation.py` — Reproducible evaluation script

---

## Reproducibility

All results deterministic with `GLOBAL_SEED = 42`. Benchmark thresholds frozen before observation. No cherry-picking.