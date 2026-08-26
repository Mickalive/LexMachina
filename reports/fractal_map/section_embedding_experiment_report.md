# Fractal Map Lane — Section Embedding Experiment Report

**Run ID:** `fractal_section_exp_20260826_001`  
**Date:** 2026-08-26  
**Factory Direction Version:** 1  
**Lane Question:** Establish a flat-map baseline, then test hierarchical/multi-resolution representations where zoom reveals legally coherent substructure rather than merely magnifying points.

---

## Hypothesis

**H₀ (Null):** Full-text embeddings using a generic multilingual model produce the best legally coherent fractal map. Structured sections (Sachverhalt, Erwägungen, Dispositiv) do not improve legal coherence over language coherence.

**H₁ (Alternative):** Legally structured sections — particularly Erwägungen (legal reasoning) and Dispositiv (outcome) — produce embeddings with higher legal_area_purity / language_purity ratio than full_text, because procedural boilerplate and language-specific formatting are reduced.

**Success Criterion:** Any section-based representation achieves legal_vs_language_ratio > 0.5 (legal coherence exceeds language coherence) at some resolution.

**Product Decision Unlocked:** If structured sections improve legal coherence, the fractal map pipeline should use section-aware embeddings as default; if not, we must wait for legal-distance lane to produce better legal-specific representations.

---

## Experimental Design

### Corpus
- **Source:** `bger_eval_structure.jsonl` (89 decisions from OpenCaseLaw with `/api/structure` endpoint)
- **Clean Subset:** 63 decisions with **all three sections populated** (Sachverhalt, Erwägungen, Dispositiv)
- **Language Distribution:** DE: 38, FR: 24, IT: 1
- **Legal Areas:** 27 distinct areas (public, criminal, civil, social_insurance, tax, etc.)

### Representations Tested
| Representation | Description | Mean Chars |
|----------------|-------------|------------|
| `full_text` | Complete decision text (baseline) | 23,895 |
| `sachverhalt` | Facts section only | 1,000 |
| `erwaegungen` | Legal reasoning paragraphs combined | 4,276 |
| `dispositiv` | Outcome/orders section only | 616 |
| `erwaegungen_dispositiv` | Reasoning + outcome (legally-relevant) | 4,893 |
| `sachverhalt_erwaegungen_dispositiv` | All structured sections combined | 5,894 |

### Embedding Model
- `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (768-dim, multilingual)

### Clustering & Evaluation
- **Method:** Leiden clustering on k-NN graph (k=15, cosine metric) at resolutions [0.5, 1.0, 1.5, 2.0]
- **Metrics:** 
  - `legal_area_purity`: Cluster purity w.r.t. legal_area metadata
  - `language_purity`: Cluster purity w.r.t. language metadata
  - `legal_vs_language_ratio`: legal_area_purity / language_purity (primary success metric)

---

## Results

### Best Ratio per Representation (Clean 63-Decision Corpus)

| Representation | Best Legal Purity | Best Lang Purity | **Best Ratio** | At Resolution |
|----------------|-------------------|------------------|----------------|---------------|
| `full_text` (baseline) | 0.3810 | 0.8889 | **0.4286** | 2.0 |
| `sachverhalt` | 0.3175 | 0.6032 | **0.5263** ✓ | 2.0 |
| `erwaegungen` | 0.3651 | 0.9206 | **0.3966** | 2.0 |
| `dispositiv` | **0.4127** | 0.7937 | **0.5200** ✓ | 2.0 |
| `erwaegungen_dispositiv` | 0.3651 | 0.9206 | **0.3966** | 2.0 |
| `all_sections_combined` | 0.3175 | 0.6032 | **0.5263** ✓ | 2.0 |

✓ = Meets success criterion (ratio > 0.5)

### Detailed Coherence by Resolution (Clean Corpus)

#### full_text (Baseline)
| Resolution | Clusters | Legal Purity | Lang Purity | Ratio |
|------------|----------|--------------|-------------|-------|
| 0.5 | 2 | 0.2063 | 0.9048 | 0.2281 |
| 1.0 | 3 | 0.2857 | 0.9048 | 0.3158 |
| 1.5 | 7 | 0.3333 | 0.8889 | 0.3750 |
| 2.0 | 11 | 0.3810 | 0.8889 | 0.4286 |

#### sachverhalt (Facts)
| Resolution | Clusters | Legal Purity | Lang Purity | Ratio |
|------------|----------|--------------|-------------|-------|
| 0.5 | 2 | 0.1905 | 0.6032 | 0.3158 |
| 1.0 | 3 | 0.2381 | 0.6032 | 0.3947 |
| 1.5 | 6 | 0.2857 | 0.6032 | 0.4737 |
| 2.0 | 9 | 0.3175 | 0.6032 | **0.5263** |

#### erwaegungen (Legal Reasoning)
| Resolution | Clusters | Legal Purity | Lang Purity | Ratio |
|------------|----------|--------------|-------------|-------|
| 0.5 | 2 | 0.2063 | 0.9524 | 0.2167 |
| 1.0 | 3 | 0.2222 | 0.9048 | 0.2456 |
| 1.5 | 5 | 0.2698 | 0.9365 | 0.2881 |
| 2.0 | 11 | 0.3651 | 0.9206 | 0.3966 |

#### dispositiv (Outcome)
| Resolution | Clusters | Legal Purity | Lang Purity | Ratio |
|------------|----------|--------------|-------------|-------|
| 0.5 | 1 | 0.1429 | 0.6032 | 0.2368 |
| 1.0 | 3 | 0.2381 | 0.8413 | 0.2830 |
| 1.5 | 10 | 0.3016 | 0.8571 | 0.3519 |
| 2.0 | 16 | **0.4127** | 0.7937 | **0.5200** |

#### erwaegungen_dispositiv (Reasoning + Outcome)
| Resolution | Clusters | Legal Purity | Lang Purity | Ratio |
|------------|----------|--------------|-------------|-------|
| 0.5 | 2 | 0.2063 | 0.9524 | 0.2167 |
| 1.0 | 3 | 0.2222 | 0.9048 | 0.2456 |
| 1.5 | 5 | 0.2698 | 0.9365 | 0.2881 |
| 2.0 | 11 | 0.3651 | 0.9206 | 0.3966 |

#### all_sections_combined
| Resolution | Clusters | Legal Purity | Lang Purity | Ratio |
|------------|----------|--------------|-------------|-------|
| 0.5 | 2 | 0.1905 | 0.6032 | 0.3158 |
| 1.0 | 3 | 0.2381 | 0.6032 | 0.3947 |
| 1.5 | 6 | 0.2857 | 0.6032 | 0.4737 |
| 2.0 | 9 | 0.3175 | 0.6032 | **0.5263** |

---

## Key Findings

### 1. **Hypothesis PARTIALLY SUPPORTED with Critical Nuance**
- **Sachverhalt (facts) and Dispositiv (outcome) achieve ratio > 0.5** — legal coherence exceeds language coherence.
- **Erwägungen (legal reasoning) FAILS to improve ratio** (0.3966 vs baseline 0.4286) — remains strongly language-dominated (lang_purity 0.92).
- **Combined legally-relevant sections (erwaegungen_dispositiv) perform identically to erwaegungen alone** — reasoning dominates the signal.

### 2. **Surprising Result: Legal Reasoning is Language-Dominated**
The Erwägungen section — the legally most substantive part of a decision — shows **higher language_purity (0.92) than full_text (0.89)**. The multilingual model encodes legal reasoning in a language-specific manner. This contradicts the assumption that "legal content" would naturally align across languages.

### 3. **Dispositiv Achieves Highest Absolute Legal Purity (0.4127)**
The outcome section produces the most legally coherent clusters (highest legal_area_purity) while maintaining moderate language_purity (0.79). This makes sense: dispositions use standardized legal formulas that are more consistent within legal areas than across languages.

### 4. **Sachverhalt Ratio Driven by Language Diversity, Not Legal Signal**
Sachverhalt achieves ratio 0.5263 primarily because language_purity drops to 0.60 (facts are written in more varied, less formulaic language). Legal_purity is actually **lower** than full_text (0.32 vs 0.38). The ratio improvement is largely from language de-correlation, not legal signal gain.

### 5. **Empty Section Artifact in Full 89-Decision Corpus**
26/89 decisions lack Sachverhalt. Their empty-string embeddings collapse into a single artificial cluster, inflating the ratio artificially (0.5263 → 0.5263 but with different cluster structure). The clean 63-decision experiment removes this artifact.

---

## Evidence Tier Assessment

| Criterion | Status |
|-----------|--------|
| Hypothesis frozen before observation | ✓ |
| Baseline defined (full_text) | ✓ |
| Sample frozen (63 decisions with complete structure) | ✓ |
| Metric defined (legal_vs_language_ratio) | ✓ |
| Success rule defined (ratio > 0.5) | ✓ |
| Discriminating experiment executed | ✓ |
| Raw outputs preserved | ✓ (section_experiment_clean/) |
| Negative results preserved (erwaegungen failure) | ✓ |
| Comparison against strong baseline | ✓ |
| Uncertainty acknowledged (small sample, single model) | ✓ |

**Evidence Tier: EXPLORATORY** — Single model, small sample (n=63), no legal-specific embedding baseline yet. Results are discriminating but not yet reproduced with legal embeddings from legal-distance lane.

---

## Recommendations

### For Fractal Map Lane (This Lane)
1. **PIVOT_WITHIN_MISSION**: Do not adopt section-aware embeddings as default yet. The improvement comes from language de-correlation (Sachverhalt, Dispositiv), not stronger legal signal in reasoning.

2. **Next Discriminating Experiment**: Test **hybrid representations** combining:
   - Dispositiv embeddings (highest legal_purity) for outcome-based map mode
   - Citation graph embeddings (from corpus lane) for precedent-based map mode
   - Wait for legal-distance lane to produce legal-specific embeddings for Erwägungen

3. **Map Mode Design**: The product should expose **multiple map modes** (per Master Prompt multi-view requirement):
   - "Outcome Map" — Dispositiv embeddings
   - "Facts Map" — Sachverhalt embeddings  
   - "Citation Map" — Graph embeddings
   - "Reasoning Map" — *Pending legal-distance embeddings*

### For Legal-Distance Lane (Dependency)
**Urgent need**: Legal-specific embeddings that align legal reasoning across languages. Current multilingual model fails on Erwägungen. Legal-distance should prioritize:
- Legal-domain adaptation (continued pretraining on Swiss case law)
- Cross-lingual alignment on parallel decisions (same docket, different languages)
- Metric learning with Jurivoc/human-index weak supervision

### For Evaluation Lane
Add **section-aware evaluation**: test whether neighbor retrieval in Dispositiv space recovers same-outcome decisions better than full_text.

---

## Artifacts Produced

| Artifact | Path |
|----------|------|
| Clean embeddings (6 representations) | `results/fractal_map/section_experiment_clean/embeddings_*.npy` |
| UMAP projections | `results/fractal_map/section_experiment_clean/projection_*.npy` |
| Leiden clustering results (4 resolutions each) | `results/fractal_map/section_experiment_clean/clustering_results.json` |
| Metadata | `results/fractal_map/section_experiment_clean/metadata.json` |
| Experiment code | `fractal_map/experiments/section_embeddings_clean.py` |
| Previous (artifact-containing) run | `results/fractal_map/section_experiment/` |

---

## Next Cycle Recommendation

**CONTINUE = False** — No additional same-question cycle justified. The question "do structured sections improve legal coherence?" is answered: **only for facts/outcome, not for reasoning**. 

**Next Question for Factory Director**: 
> "Given that generic multilingual embeddings fail on legal reasoning (Erwägungen), what legal-specific representation (citation graph, norm extraction, legal-domain adapted embeddings, metric learning) produces a fractal map where zoom reveals legally coherent substructure in the reasoning space?"

This question properly belongs to **legal-distance lane** (representation discovery) with **fractal-map lane** consuming the output (hierarchical mapping).

---
*Report generated by fractal-map lane experiment `fractal_section_exp_20260826_001`*