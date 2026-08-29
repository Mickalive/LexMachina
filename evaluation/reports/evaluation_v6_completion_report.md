# Evaluation Lane v6 Completion Report

**Factory Direction Version:** 6  
**Evaluation Version:** v3 (frozen harness) + v6 signal ablation + cited_decisions adversarial validation  
**Global Seed:** 42 (FROZEN)  
**Config Hash:** `4323f833fa72366a`  
**GitHub Run:** 33237348146  
**Date:** 2026-08-29  

---

## Executive Summary

The Evaluation lane has **COMPLETED** all Factory Direction v6 objectives. The frozen evaluation harness (v3, seed=42, config_hash=4323f833fa72366a) has been **reproduced exactly** in this run, confirming all prior results. The evaluation validates the critical breakthroughs from legal-distance v6 and identifies the best representations for productization.

**Recommendation:** **PRODUCTIZE** — The evaluation lane's work for v6 is complete. The next factory direction should focus on corpus scale (192k), citation ID resolution, legal embeddings fine-tuning, jurist human study, and product hardening at scale.

---

## Frozen Harness Reproducibility: CONFIRMED ✅

| Metric | Original (GitHub 33232234741) | This Run | Status |
|--------|-------------------------------|----------|--------|
| Config Hash | `4323f833fa72366a` | `4323f833fa72366a` | ✅ IDENTICAL |
| Global Seed | 42 | 42 | ✅ IDENTICAL |
| center_projected_64dim Verdict | PASS | PASS | ✅ IDENTICAL |
| center_projected_64dim LangDom | 0.7664 | 0.7664 | ✅ IDENTICAL |
| center_projected_64dim Jurist | 0.5121 | 0.5121 | ✅ IDENTICAL |
| linear_metric_epoch4 Jurist | 0.6847 | 0.6847 | ✅ IDENTICAL |
| mahalanobis_metric_epoch4 Jurist | 0.6781 | 0.6781 | ✅ IDENTICAL |

**The frozen evaluation harness is fully reproducible.**

---

## Adversarial Gate Results (Frozen Thresholds)

**Thresholds (immutable):** Language Dominance < 0.85, Jurist Pairwise > 0.5

| Representation | LangDom | LD-Pass | Jurist | JP-Pass | Both Gates | Verdict |
|---|---|---|---|---|---|---|
| **cited_decisions_tfidf** | **0.6107** | ✅ | **0.6922** | ✅ | ✅ | **PASS** |
| linear_metric_epoch4 | 0.6805 | ✅ | 0.6847 | ✅ | ✅ | PASS |
| mahalanobis_metric_epoch4 | 0.6843 | ✅ | 0.6781 | ✅ | ✅ | PASS |
| hybrid_stabilized_epoch1 | 0.6704 | ✅ | 0.6656 | ✅ | ✅ | PASS |
| cited_decisions_tfidf_hybrid_cp768_0.7 | 0.6477 | ✅ | 0.6764 | ✅ | ✅ | PASS |
| cited_decisions_tfidf_hybrid_cp64_0.7 | 0.6518 | ✅ | 0.6564 | ✅ | ✅ | PASS |
| hybrid_v2_epoch3 | 0.7115 | ✅ | 0.5988 | ✅ | ✅ | PASS |
| cited_decisions_tfidf_hybrid_cp768_0.5 | 0.7062 | ✅ | 0.6105 | ✅ | ✅ | PASS |
| cited_decisions_tfidf_hybrid_cp64_0.5 | 0.6838 | ✅ | 0.6280 | ✅ | ✅ | PASS |
| cited_decisions_tfidf_hybrid_cp64_0.3 | 0.7483 | ✅ | 0.5346 | ✅ | ✅ | PASS |
| cited_decisions_tfidf_hybrid_cp768_0.3 | 0.7604 | ✅ | 0.5254 | ✅ | ✅ | PASS |
| **center_projected_64dim (production default)** | **0.7664** | ✅ | **0.5121** | ✅ | ✅ | **PASS** |
| center_projected_768 | 0.7738 | ✅ | 0.4912 | ❌ | ❌ | FAIL |

---

## Key Findings

### 1. **cited_decisions_tfidf: Best Overall Unsupervised Representation**
- **Highest jurist preference (0.6922)** — beats all supervised metric learning methods
- **Best language invariance (0.6107)** — lowest language dominance of all representations
- **Zero-shot citation signal** — no training required, pure TF-IDF on cited decisions
- **Best fractal improvement rate (91.7%)** — zoom reveals dramatically more specific legal structure
- **Competitive with supervised metric learning** (0.6922 vs 0.6847 linear_metric) without any training

### 2. **Metric Learning Breakthrough Confirmed**
- **linear_metric_epoch4**: JP=0.6847 (+33.7% relative improvement over center_projected_64dim)
- **mahalanobis_metric_epoch4**: JP=0.6781 (+32.4% relative improvement)
- Both pass **BOTH adversarial gates** with 18+ consecutive valid epochs (frozen harness v3 seed=42)
- Both achieve **strong Jurivoc Level 0 NMI** (0.6895, 0.7041) — first representations to pass Jurivoc alignment gate

### 3. **All 6 Hybrids of cited_decisions_tfidf + center_projected PASS Both Gates**
- Best production hybrid: **cited_decisions_tfidf_hybrid_cp64_0.7** (jurist=0.6564, lang_dom=0.6518, uses 64-dim frozen PCA)
- Hybrids combine zero-shot citation signal with dense semantic baseline
- All 6 configurations pass both adversarial gates — robust parameter region

### 4. **center_projected_64dim: ONLY Original Baseline Passing Both Gates**
- Confirms product lane finding: 768-dim FAILS jurist pairwise (0.4912)
- 64-dim frozen PCA is the validated production default
- Reference baseline for all future comparisons

### 5. **Signal Ablation Validation: CONFIRMED**
All 15 signal ablation variants on center_projected baseline **FAIL** jurist pairwise preference:
- legal_area_tfidf: lang_dom=0.914, jurist=0.131
- legal_issues_outcomes: lang_dom=1.000, jurist=0.000
- erwaegungen_tfidf: lang_dom=0.904, jurist=0.103
- sachverhalt_tfidf: lang_dom=0.770, jurist=0.269
- norm_embeddings: lang_dom=0.763, jurist=0.273
- hybrid variants: all FAIL adversarial gates

**Only metric learning (linear, Mahalanobis) and stabilized hybrid objectives produce valid adversarial-robust representations on center_projected.**

### 6. **Boilerplate Resistance: SYSTEMATIC LIMITATION**
| Test | Method | Result |
|---|---|---|
| Harness proxy (chamber/legal_area) | All representations | **NEGATIVE** (resistance_score ≈ -0.75 to -0.92) |
| Real text perturbation (TF-IDF) | Full text vs boilerplate-removed | **High neighbor preservation (0.89-0.93)** = neighbors stable |
| Language dominance proxy | Real text TF-IDF | **100% decisions** have >80% same-language neighbors |

**Interpretation:** Neighbors are NOT driven by procedural boilerplate (high preservation when boilerplate removed), but ARE dominated by language artifacts. This is a fundamental limitation of current embedding approaches for Swiss multilingual corpus.

### 7. **Scale Stability: GOOD**
All representations show 0.60-0.72 neighbor overlap under 80% corpus subsampling — stable geometry under corpus growth.

### 8. **Cross-Language Retrieval: Metric Learning + One Hybrid PASS**
| Representation | Cross-Lang Recall@10 | Threshold (0.2) |
|---|---|---|
| hybrid_stabilized_epoch1 | 0.2360 | ✅ PASS |
| hybrid_v2_epoch3 | 0.2269 | ✅ PASS |
| linear_metric_epoch4 | 0.2114 | ✅ PASS |
| mahalanobis_metric_epoch4 | 0.2083 | ✅ PASS |
| cited_decisions_tfidf | 0.2083 | ✅ PASS |
| cited_decisions_tfidf_hybrid_cp768_0.7 | 0.2068 | ✅ PASS |
| cited_decisions_tfidf_hybrid_cp64_0.7 | 0.1945 | ❌ FAIL |
| cited_decisions_tfidf_hybrid_cp768_0.5 | 0.1758 | ❌ FAIL |
| cited_decisions_tfidf_hybrid_cp64_0.5 | 0.1723 | ❌ FAIL |
| center_projected_64dim | 0.1558 | ❌ FAIL |

---

## Evidence Tier Assessment

| Finding | Evidence Tier | Provenance |
|---|---|---|
| Frozen harness reproducibility | **REPRODUCED** | GitHub runs 33232234741, 33235485388, this run |
| center_projected_64dim only baseline passing both gates | **REPRODUCED** | v3_evaluation_results.json, this run |
| Metric learning breakthrough (linear, mahalanobis) | **REPRODUCED** | v3_evaluation_results.json, legal-distance v6, this run |
| cited_decisions_tfidf best unsupervised | **REPRODUCED** | cited_decisions_validation, legal-distance v6, this run |
| All 6 hybrids pass both gates | **REPRODUCED** | cited_decisions_validation, this run |
| Signal ablation all FAIL | **REPRODUCED** | v6_signal_ablation, legal-distance v6, this run |
| Boilerplate resistance negative (harness) | **REPRODUCED** | v3_evaluation_results.json, this run |
| Boilerplate resistance real text test | **EXPLORATORY** | v3_boilerplate_real_results.json (this run) |
| Cross-language retrieval metric learning PASS | **REPRODUCED** | v3_evaluation_results.json, this run |
| Scale stability good | **REPRODUCED** | v3_evaluation_results.json, this run |

**No ACCEPTED negative findings contradicted.** All evidence is consistent.

---

## Recommendations for Next Factory Direction (v7)

Based on completed v6 evaluation and director note, the next evaluation cycle should address:

### 1. **Full Corpus Scale Evaluation (192k decisions)**
- Validate metric learning representations at 192k scale
- Test scale stability on full corpus (not subsampled)
- Evaluate fractal map quality at production scale

### 2. **Citation Role Modeling Evaluation**
- Once citation ID resolution pipeline is ready (corpus lane)
- Evaluate 2,988 role annotations (overruling, distinguishing, following)
- Test citation role embeddings against adversarial gates

### 3. **Legal Embeddings Fine-Tuning Evaluation**
- Test multilingual-e5-small fine-tuned on Swiss legal corpus
- Evaluate multilingual invariance with coarse legal structure
- Compare against center_projected_64dim baseline

### 4. **Jurist Human Study (Framework Ready)**
- Execute pairwise preference study with 5-10 Swiss jurists
- Validate simulated jurist proxy against real jurist judgments
- Test map mode preferences (legal issue vs reasoning vs citation views)

### 5. **Boilerplate Resistance: Deeper Investigation**
- Develop better boilerplate removal (section-aware)
- Test if metric learning representations improve boilerplate resistance
- Evaluate section-specific embeddings (sachverhalt, erwaegungen, dispositiv)

### 6. **User Corpus Import Evaluation**
- Validate map artifacts persist correctly for user-imported corpora
- Test recomputation triggers and incremental updates
- Evaluate schema validation robustness

---

## Artifacts Produced This Run

| Artifact | Path | Description |
|---|---|---|
| Evaluation v3 Results | `evaluation/results/v3/evaluation_v3_results.json` | Frozen harness on 6 representations |
| Cited Decisions Validation | `evaluation/results/cited_decisions_validation/cited_decisions_validation_all_results.json` | 9 representations (cited_decisions_tfidf + 6 hybrids + 2 baselines) |
| Real Boilerplate Resistance | `evaluation/results/v3_boilerplate_real/boilerplate_resistance_real_results.json` | TF-IDF signals on full text with boilerplate removal |
| Signal Ablation v6 | `evaluation/results/evaluation/v6_signal_ablation/v6_signal_ablation_adversarial_results.json` | 15 signal variants on center_projected baseline |
| Updated State | `state/evaluation.json` | Machine-readable lane state (already current) |

---

## Conclusion

The Evaluation lane has **successfully completed** Factory Direction v6. The frozen evaluation harness (v3, seed=42) is **fully reproducible**. All critical findings from legal-distance v6 (metric learning breakthrough, cited_decisions_tfidf discovery, signal ablation validation) have been **validated on the expanded 1,200-decision slice using adversarial benchmarks**.

**The evaluation lane recommends PRODUCTIZE with continue_recommended=false.** The next factory direction should advance to corpus scale (192k), citation ID resolution, legal embeddings fine-tuning, jurist human study, and product hardening at scale.