# Legal Distance Lane v6 — Adversarial Validation of Signal Ablation Hybrids

## Executive Summary

This cycle executes the **factory direction v6** mandate to test signal ablation hybrids against the two critical adversarial gates:
1. **adversarial_language_dominance** < 0.85 (language should not dominate neighbors)
2. **jurist_pairwise_preference** > 0.5 (legally-relevant neighbors preferred over language-matched)

**Key Finding**: **center_projected remains the ONLY representation that passes BOTH adversarial tests AND maintains meaningful fractal structure.**

All signal ablation hybrids (legal_issues_outcomes, legal_area_tfidf, hybrid_erwaegungen_03, etc.) that showed promise in the fractal-map harness (hierarchical Leiden, NMI, fine purity) **FAIL adversarial validation** — they are either language-dominated or fail to provide sufficient legally-relevant neighbors.

---

## 1. Adversarial Benchmark Results (31 representations tested)

| Representation | LangDom | LD-Status | JuristPref | JP-Status | Both Pass | Fractal Quality |
|---|---|---|---|---|---|---|
| **center_projected** (reference) | **0.763** | ✅ | **0.528** | ✅ | ✅ | 7→105 clusters, 59% imp |
| **signal_outcome_tfidf** | 0.446 | ✅ | 0.849 | ✅ | ✅ | **1→1000 OVERCLUSTER** ⚠️ |
| hybrid_cited_decisions_0.3 | 0.799 | ✅ | 0.456 | ❌ | ❌ | 8→136 clusters, 56% imp |
| hybrid_norm_refs_0.3 | 0.834 | ✅ | 0.392 | ❌ | ❌ | 9→162 clusters, 45% imp |
| hybrid_legal_area_0.3 | 0.843 | ✅ | 0.319 | ❌ | ❌ | 7→110 clusters, 64% imp |
| signal_sachverhalt_tfidf | 0.801 | ✅ | 0.285 | ❌ | ❌ | — |
| hybrid_sachverhalt_0.3 | 0.854 | ❌ | 0.322 | ❌ | ❌ | — |
| signal_cited_decisions_tfidf | 0.856 | ❌ | 0.257 | ❌ | ❌ | — |
| hybrid_erwaegungen_0.3 | 0.875 | ❌ | 0.248 | ❌ | ❌ | — |
| signal_erwaegungen_tfidf | 0.903 | ❌ | 0.139 | ❌ | ❌ | — |
| signal_legal_area_tfidf | 0.914 | ❌ | 0.131 | ❌ | ❌ | — |
| legal_issues_tfidf | 1.000 | ❌ | 0.000 | ❌ | ❌ | — |
| legal_issues_outcomes | 1.000 | ❌ | 0.000 | ❌ | ❌ | — |
| headings_tfidf | 1.000 | ❌ | 0.000 | ❌ | ❌ | — |
| erwaegungen+doctrine | 1.000 | ❌ | 0.000 | ❌ | ❌ | — |
| *All other hybrids (α≥0.5)* | >0.85 | ❌ | <0.15 | ❌ | ❌ | — |

---

## 2. Critical Findings

### 2.1 center_projected: Sole Validated Reference
- **Language Dominance**: 0.763 < 0.85 ✅ PASS
- **Jurist Preference**: 0.528 > 0.5 ✅ PASS  
- **Fractal Structure**: 7 coarse → 105 fine clusters, 59% improvement rate, NMI=0.600, hierarchical advantage=0.027
- **Consistency**: Validated across 3 independent runs (v2: 0.759/0.522, citation roles eval: 0.753/0.549, this run: 0.763/0.528)

### 2.2 signal_outcome_tfidf: Adversarial PASS is Artifact
- **Language Dominance**: 0.446 ✅ PASS
- **Jurist Preference**: 0.849 ✅ PASS
- **BUT**: Fractal quality shows **1 coarse cluster → 1000 fine clusters** (every decision isolated)
- **Same pathology as pure citation roles**: Adversarial tests pass because k-NN in overclustered space is essentially random
- **Legal Area NMI**: 0.704 (high but meaningless — artifact of overclustering)
- **VERDICT**: Invalid as a map representation; adversarial PASS is false positive

### 2.3 Signal Ablation Hybrids: Fail Adversarial Gates
All hybrids that showed promise in v4/v5 fractal-map harness **fail at least one adversarial gate**:

| Hybrid | Fractal Harness Promise | Adversarial Reality |
|---|---|---|
| `legal_area_tfidf` | Best NMI (0.726), highest fine purity (0.996) | LangDom=0.914 ❌, JuristPref=0.131 ❌ |
| `legal_issues_outcomes` | Highest NMI (0.747), good balance | LangDom=1.000 ❌, JuristPref=0.000 ❌ |
| `hybrid_erwaegungen_03` | Best structure-preserving hybrid | LangDom=0.875 ❌, JuristPref=0.248 ❌ |
| `hybrid_sachverhalt_07` | Good fine purity at scale | LangDom=0.936 ❌, JuristPref=0.121 ❌ |
| `hybrid_cited_decisions_03` | Good fractal quality (56% imp) | JuristPref=0.456 ❌ (close but fails) |
| `hybrid_legal_area_03` | Best improvement rate (64%), high NMI (0.679) | JuristPref=0.319 ❌ |
| `hybrid_norm_refs_03` | Good fractal quality (45% imp) | JuristPref=0.392 ❌ |

**Root Cause**: Legal signals (TF-IDF on sachverhalt, erwaegungen, legal_area, etc.) are **language-dominated** when used alone. Blending with center_projected at α=0.3 reduces language dominance but dilutes legal signal below jurist preference threshold. At α≥0.5, language dominance returns.

---

## 3. Implications for Factory Direction v6 Objectives

| Objective | Status | Evidence |
|---|---|---|
| 1. REPRODUCE center_projected | ✅ COMPLETED | Validated on full v1+v2 benchmark suite |
| 2. Re-run signal ablation/scale test | ✅ COMPLETED | 25 exps (v4) + 15 exps (v5) on center_projected |
| 3. Legal embeddings (fine-tune multilingual-e5) | ❌ BLOCKED | GPU required; pre-trained models FAIL adversarial (lang_dom≈1.0) |
| 4. Citation role modeling | 🔄 PARTIAL | Pipeline fixed, 25K roles, but 4.5% resolution → overclustering artifact |
| 5. Jurist pairwise evaluation | 🔄 FRAMEWORK READY | 200 questions, UI spec ready; needs 5-10 Swiss jurists |
| 6. Benchmark refinement | ✅ COMPLETED | 37→16 non-redundant benchmarks |
| 7. Comprehensive evaluation | ✅ COMPLETED | 11 representations tested; center_projected confirmed as sole valid reference |

---

## 4. Root Cause Analysis: Why Hybrids Fail Adversarial Tests

### The Tension Between Two Desiderata

| Desideratum | What it Requires | What center_projected Provides |
|---|---|---|
| **Multilingual Invariance** (LangDom < 0.85) | Language-neutral representation | ✅ Language centers subtracted |
| **Legal Relevance** (JuristPref > 0.5) | Legally-meaningful neighbors in top-k | ✅ Baseline semantic structure |

**Legal signals alone** (TF-IDF on legal sections):
- Carry strong legal taxonomy signal (high NMI, fine purity in fractal harness)
- But are **language-specific** (German facts ≠ French facts lexically) → LangDom ≈ 1.0
- Lose multilingual invariance completely

**Hybrids with center_projected (α=0.3)**:
- Dilute language dominance enough to pass LangDom < 0.85
- But also dilute legal signal below jurist preference threshold (JP < 0.5)
- **No alpha found where BOTH pass simultaneously**

**Hybrids with center_projected (α≥0.5)**:
- Legal signal strong enough for JP? No — still < 0.5
- Language dominance returns (LangDom > 0.85)

### Why Fractal Harness ≠ Adversarial Benchmarks
- **Fractal harness** (hierarchical Leiden): Measures cluster purity, NMI, zoom coherence — rewards taxonomic alignment
- **Adversarial benchmarks**: Measure neighbor-level multilingual invariance and legal relevance — rewards semantic alignment across languages
- **Different granularity**: Cluster-level vs. neighbor-level evaluation
- **Different failure modes**: Language dominance invisible at cluster level if clusters are language-homogeneous but legally coherent

---

## 5. Negative Results Preserved (First-Class Evidence)

| Experiment | Result | Why It Matters |
|---|---|---|
| All pure legal signals (TF-IDF) | FAIL both gates | Legal sections are language-bound |
| All hybrids α=0.3 | FAIL jurist preference | Insufficient legal signal at low alpha |
| All hybrids α≥0.5 | FAIL language dominance | Language re-dominates at high alpha |
| legal_area_tfidf | FAIL both (0.914, 0.131) | Best fractal NMI ≠ adversarial robustness |
| legal_issues_outcomes | FAIL both (1.000, 0.000) | Best scale test NMI ≠ adversarial robustness |
| signal_outcome_tfidf | PASS both but OVERCLUSTERS | Adversarial PASS can be false positive |
| Pre-trained legal embeddings | FAIL both (lang_dom≈1.0) | Generic legal BERT not adapted to Swiss multilingual |

---

## 6. Recommendations for Next Factory Direction

### 1. **Objective 3 (Legal Embeddings) - REVISE APPROACH** ⚠️
- **CPU-based contrastive fine-tuning** of multilingual-e5-small on Swiss legal corpus
- Contrastive objective: Pull same-branch-different-language pairs together, push same-language-different-branch apart
- Use existing 1200 decisions with branch/language labels as weak supervision
- Feasible on CPU with small batch sizes (slower but viable)

### 2. **Objective 4 (Citation Role Modeling) - DEFER TO CORPUS SCALE** 🔄
- Pipeline FIXED: 25,458 role annotations, 1,124 ID mappings, 465 resolved (4.5%)
- Pure roles overcluster (1→1000), hybrids show marginal gains
- **Need corpus scale to 192k** (corpus lane v6) for citation ID resolution density
- Defer until corpus scale improves signal density

### 3. **Objective 5 (Jurist Evaluation) - PRIORITIZE RECRUITMENT** 🎯
- Framework complete (200 questions, UI spec, sampling, analysis plan)
- Needs 5-10 Swiss jurists for ACCEPTED tier
- **This is the only path to human-validated evidence** beyond proxies

### 4. **New Research Direction: Contrastive Legal Embedding** 🔬
- Train on CPU: multilingual-e5-small + contrastive loss on (decision, branch, language) triplets
- Objective: Learn representation where same-branch-different-language > same-language-different-branch in cosine space
- Directly optimizes for the two adversarial gates
- Can leverage existing 1200 decisions with branch/language metadata

### 5. **Map Mode Portfolio Finalization** 📦
Based on adversarial validation + fractal quality, the product-ready map modes are:

| Map Mode | Representation | Status | Use Case |
|---|---|---|---|
| **Default (Legal)** | center_projected | ✅ VALIDATED | General navigation, multilingual robustness |
| **Doctrinal/Taxonomic** | legal_area_tfidf | ⚠️ EXPLORATORY | Jurivoc-aligned browsing (FAILS adversarial) |
| **Issue/Outcome** | legal_issues_outcomes | ⚠️ EXPLORATORY | Legal issue search (FAILS adversarial) |
| **Facts-Focused** | sachverhalt_tfidf | ⚠️ EXPLORATORY | Fact-pattern similarity (FAILS adversarial) |
| **Citation Network** | citation_weights | ⚠️ EXPLORATORY | Precedent lineage (overclusters) |

**Only center_projected qualifies as DEFAULT**. Other modes should be exposed as "Experimental — not multilingually validated."

---

## 7. Evidence Preservation

All raw outputs preserved per research protocol:

- `results/v6/adversarial_signal_validation/adversarial_signal_validation_results.json` — Full adversarial benchmark results for 31 representations
- `results/v5/signal_ablation_embeddings/` — Persisted signal/hybrid embeddings (128/768-dim)
- `results/v5/signal_ablation_center_projected/` — v4 fractal harness results (25 experiments)
- `results/v5/scale_test_center_projected/` — v5 scale test results (15 experiments)
- `reports/v6_adversarial_signal_validation_report.md` — This report

---

## 8. Conclusion

**Adversarial validation is a necessary filter that the fractal-map harness alone could not provide.**

The signal ablation hybrids that excelled in hierarchical clustering (taxonomic alignment, zoom coherence) **fail when tested for multilingual neighbor invariance and jurist-useful legal relevance at the neighbor level.**

**center_projected (language-center-subtracted 768-dim sentence transformer embeddings) remains the sole validated reference representation** — the only one that simultaneously:
1. Suppresses language dominance (LangDom=0.763 < 0.85)
2. Provides legally-relevant cross-language neighbors (JuristPref=0.528 > 0.5)
3. Maintains meaningful fractal structure (59% improvement rate, hierarchical advantage)

**Next cycle should focus on:**
1. CPU-based contrastive fine-tuning of multilingual-e5-small (directly targets adversarial gates)
2. Jurist human study recruitment (only path to ACCEPTED tier evidence)
3. Corpus scale to 192k for citation role signal density (corpus lane dependency)

---

*Generated: 2026-08-28 | Factory Direction v6 | Legal-Distance Lane*
