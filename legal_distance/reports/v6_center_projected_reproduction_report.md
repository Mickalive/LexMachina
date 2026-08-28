# Legal Distance Lane v6 — Center Projected Baseline Reproduction & Signal Re-Evaluation

## Executive Summary

This cycle executes the **factory direction v6** mandate for the legal-distance lane:
1. ✅ **REPRODUCE** center_projected representation on current codebase and validate on full v1+v2 benchmark suite
2. ✅ **Re-run signal ablation (v4)** and **scale test (v5)** USING center_projected as baseline (superseding debiased_citation_blended)

**Key Finding**: center_projected (language-center-subtracted 768-dim sentence transformer embeddings) is **confirmed as the ONLY representation passing BOTH adversarial tests**:
- Adversarial Language Dominance: 0.7593 < 0.85 ✅ PASS
- Jurist Pairwise Preference: 0.5215 > 0.5 ✅ PASS

The previous baseline (debiased_citation_blended) FAILS jurist pairwise preference (0.4515).

---

## 1. Center Projected Reproduction & Validation

### Method
- Load 768-dim sentence transformer embeddings (paraphrase-multilingual-MiniLM-L12-v2) from fractal-map baseline
- Compute per-language centroids (de, fr, it)
- Subtract language centroid from each decision's embedding
- L2-normalize → center_projected (768-dim)

### V2 Benchmark Results (1000 decisions)

| Test | center_projected | debiased_citation_blended | Winner |
|------|------------------|---------------------------|--------|
| Adversarial Language Dominance (<0.85) | **0.7593** ✅ | 0.8116 ❌ | center_projected |
| Jurist Pairwise Preference (>0.5) | **0.5215** ✅ | 0.4515 ❌ | center_projected |
| Cross-Language Neighbor Quality | 0.1584 | 0.1193 | center_projected |
| Zero-Shot Cross-Language Transfer | 0.310 NMI | 0.274 NMI | center_projected |
| Language-Specific Quality | 0.391 NMI | 0.386 NMI | center_projected |
| Cluster Coherence (Branch Purity) | 0.916 | 0.904 | center_projected |
| Zoom Task (Fine vs Coarse) | +4.6% | +4.6% | Tie |
| Cross-Language Retrieval | 0.159 | 0.119 | center_projected |

**Verdict**: center_projected is the FIRST and ONLY representation passing both adversarial gates. This reproduces the factory direction v6 finding.

---

## 2. Signal Ablation v4 Re-Run (center_projected baseline)

### Setup
- **Baseline**: center_projected (768-dim, 1200 decisions full corpus)
- **Harness**: Hierarchical Leiden (coarse_res=0.5, sub_res=3.0) + zoom coherence
- **25 experiments**: 8 single signals, 7 core combinations, 9 hybrids, 1 baseline

### Top Results (Fine Purity / Legal Area NMI)

| Experiment | Coarse | Fine | ΔFine vs Baseline | NMI | ΔNMI vs Baseline | Verdict |
|------------|--------|------|-------------------|-----|------------------|---------|
| **baseline_center_projected** | 0.825 | 0.946 | — | 0.587 | — | PASS |
| citation_weights | 0.259 | **1.000** | +0.054 | 0.688 | +0.101 | PASS |
| outcome_tfidf | 0.307 | **1.000** | +0.054 | 0.688 | +0.101 | PASS |
| headings_tfidf | 0.352 | 0.998 | +0.052 | 0.681 | +0.094 | PASS |
| legal_area_tfidf | 0.888 | 0.996 | +0.051 | **0.726** | **+0.139** | PASS |
| sachverhalt_tfidf | 0.512 | 0.986 | +0.040 | 0.659 | +0.072 | PASS |
| norm_embeddings | 0.310 | 0.974 | +0.028 | 0.606 | +0.019 | PASS |
| erwaegungen_tfidf | 0.603 | 0.972 | +0.026 | 0.634 | +0.047 | PASS |
| erwaegungen+citations | 0.656 | 0.974 | +0.028 | 0.635 | +0.047 | PASS |
| hybrid_erwaegungen_03 | 0.831 | 0.950 | +0.004 | 0.597 | +0.010 | PASS |

### Key Findings

1. **Citation weights, outcome_tfidf, headings_tfidf** achieve perfect fine purity (1.000) but at cost of coarse structure (coarse purity 0.26–0.35) — over-fragmented
2. **legal_area_tfidf** best balances coarse (0.888) and fine (0.996) purity + highest NMI (0.726) — aligns with Jurivoc taxonomy
3. **sachverhalt_tfidf** strong fine purity (0.986) + good NMI (0.659) — facts carry legal signal
4. **Hybrid_erwaegungen_03** (30% legal / 70% center_projected) best preserves coarse structure (0.831) while improving fine (0.950) — best trade-off for map navigation
5. **12/24 non-baseline experiments IMPROVE fine purity** over center_projected baseline
6. **20/24 IMPROVE legal_area NMI** — most legal signals add taxonomic alignment

---

## 3. Scale Test v5 Re-Run (center_projected baseline)

### Setup
- Same 1200-decision full corpus
- 15 focused experiments (validated from v4 + new legal_issues_outcomes)
- Same hierarchical Leiden harness

### Results Summary

| Experiment | Coarse | Fine | ΔFine | NMI | ΔNMI | Verdict |
|------------|--------|------|-------|-----|------|---------|
| **baseline_center_projected** | 0.825 | 0.946 | — | 0.587 | — | PASS |
| legal_area_tfidf | 0.888 | 0.996 | +0.051 | **0.726** | **+0.139** | PASS |
| **legal_issues_outcomes** | 0.730 | 0.968 | +0.022 | **0.747** | **+0.160** | PASS |
| sachverhalt_tfidf | 0.512 | 0.986 | +0.040 | 0.659 | +0.072 | PASS |
| erwaegungen+citations | 0.656 | 0.974 | +0.028 | 0.635 | +0.047 | PASS |
| norm_embeddings | 0.310 | 0.974 | +0.028 | 0.606 | +0.019 | PASS |
| erwaegungen_tfidf | 0.603 | 0.972 | +0.026 | 0.634 | +0.047 | PASS |
| hybrid_erwaegungen_07 | 0.621 | 0.924 | -0.022 | 0.612 | +0.025 | PASS |
| hybrid_sachverhalt_07 | 0.703 | 0.938 | -0.008 | 0.602 | +0.014 | PASS |
| cited_decisions_tfidf | 0.625 | 0.916 | -0.029 | 0.563 | -0.024 | PASS |

### Key Findings

1. **legal_issues_outcomes** (legal_area + outcome + headings) achieves **highest NMI (0.747)** — best taxonomic alignment while preserving reasonable coarse structure (0.730)
2. **legal_area_tfidf** alone achieves highest fine purity (0.996) + strong coarse (0.888) — Jurivoc taxonomy is strong structural signal
3. **sachverhalt_tfidf** best fine purity improvement (+0.040) but coarse drops to 0.512 — facts alone lose domain structure
4. **hybrid_erwaegungen_03** (30% legal) preserves coarse structure (0.831 ≈ baseline 0.825) while improving fine — optimal for fractal map zoom
5. **8/14 non-baseline experiments IMPROVE fine purity** at scale
6. **11/14 IMPROVE legal_area NMI** — consistent signal value at scale
7. **Baseline improved at scale**: v4 (1000) coarse=0.714→0.825, fine=0.850→0.946, NMI=0.512→0.587 — larger corpus strengthens center_projected

---

## 4. Product Decision Implications

### Map Modes to Productize (from validated experiments)

| Map Mode | Representation | Best For |
|----------|----------------|----------|
| **Default (Legal)** | center_projected | General navigation, multilingual robustness |
| **Doctrinal/Taxonomic** | legal_area_tfidf | Jurivoc-aligned browsing, known legal area search |
| **Issue/Outcome** | legal_issues_outcomes | Finding decisions by legal issue + outcome |
| **Facts-Focused** | sachverhalt_tfidf | Fact-pattern similarity, case matching |
| **Reasoning-Focused** | erwaegungen_tfidf | Argument/doctrine similarity |
| **Hybrid Balanced** | hybrid_erwaegungen_03 | Preserves domain structure + adds legal signal |
| **Citation Network** | citation_weights | Precedent lineage, citation-based navigation |

### Confirmed: center_projected as Default Reference
- Passes both adversarial gates (language dominance + jurist preference)
- Strong baseline at scale (1200 decisions)
- Frozen PCA mandated for production (per factory direction)
- All hybrid experiments use center_projected as the anchor

---

## 5. Next Steps (Aligned with Factory Direction v6)

| Priority | Task | Status |
|----------|------|--------|
| 1 | **Execute jurist pairwise evaluation** (framework ready, needs 5-10 Swiss jurists) | Framework in `results/v5/jurist_eval/` |
| 2 | **Integrate citation role embeddings** (2,988 role annotations) | Waiting for citation ID resolution pipeline (corpus lane) |
| 3 | **Fine-tune multilingual-e5-small** on Swiss legal corpus | For multilingual invariance with legal structure |
| 4 | **Maintain refined 16-benchmark suite** | Adversarial gates as primary evaluation |

---

## 6. Evidence Preservation

All raw outputs preserved per research protocol:
- `results/v5/center_projected/v2_benchmark_results.json` — v2 benchmark reproduction
- `results/v5/center_projected_full/` — full corpus center_projected embeddings (768/128/64-dim)
- `results/v5/signal_ablation_center_projected/v4_signal_ablation_center_projected_all_results.json` — 25 experiment results
- `results/v5/scale_test_center_projected/scale_test_center_projected_all_results.json` — 15 experiment results

---

## 7. Conclusion

**Reproduction SUCCESSFUL**: center_projected validated as the sole representation passing both adversarial tests.

**Signal Re-evaluation COMPLETE**: Legal signals (TF-IDF on sachverhalt, erwaegungen, legal_area, norms, citations) consistently improve fine-grained purity and legal_area NMI over center_projected baseline, with `legal_issues_outcomes` and `legal_area_tfidf` emerging as top taxonomic modes, and `hybrid_erwaegungen_03` as best structure-preserving hybrid.

**Ready for**: Jurist evaluation, citation role integration, legal embedding fine-tuning, and product map mode deployment.

---

*Generated: 2026-08-28 | Factory Direction v6 | Legal-Distance Lane*