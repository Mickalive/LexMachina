# Legal Distance Lane v6 - Comprehensive Evaluation Report

**Date:** 2026-08-28  
**Factory Direction Version:** 6  
**Run ID:** v6_comprehensive_evaluation_20260828

## Executive Summary

Ran comprehensive evaluation of **11 representations** against the refined benchmark suite with focus on the two critical adversarial gates:
1. **adversarial_language_dominance** < 0.85 (language should not dominate neighbors)
2. **jurist_pairwise_preference** > 0.5 (legally-relevant neighbors preferred over language-matched)

**Key Finding:** `center_projected` remains the **only well-behaved representation** that passes both adversarial tests AND exhibits meaningful hierarchical structure.

---

## Results Summary

| Representation | Verdict | LangDom | JuristPref | Both Pass | ImpRate | NMI | HierAdv | Structure |
|---|---|---|---|---|---|---|---|---|
| center_projected | **PASS** | 0.763 ✓ | 0.528 ✓ | ✓ | 59.0% | 0.600 | **0.027** | 7→105 clusters |
| cite_distinguishing | PASS* | 0.446 ✓ | 0.849 ✓ | ✓ | 100% | 0.704 | 0.000 | 1→1000 (overcluster) |
| cite_overruling | PASS* | 0.446 ✓ | 0.849 ✓ | ✓ | 100% | 0.704 | 0.000 | 1→1000 (overcluster) |
| cite_criticizing | PASS* | 0.446 ✓ | 0.848 ✓ | ✓ | 100% | 0.703 | 0.000 | 1→997 (overcluster) |
| cite_following | PASS* | 0.445 ✓ | 0.843 ✓ | ✓ | 99.9% | 0.700 | 0.000 | 1→986 (overcluster) |
| cite_all_weighted | PASS* | 0.442 ✓ | 0.830 ✓ | ✓ | 100% | 0.687 | 0.000 | 1→922 (overcluster) |
| cite_citing | PASS* | 0.440 ✓ | 0.824 ✓ | ✓ | 100% | 0.688 | 0.000 | 1→928 (overcluster) |
| ft_multilingual_e5_small_pretrained | PASS* | 0.488 ✓ | 0.702 ✓ | ✓ | 100% | 0.704 | 0.000 | 1→1000 (overcluster) |
| legal_paraphrase_multilingual_minilm | FAIL | 0.972 ✗ | 0.058 ✗ | ✗ | 64.2% | 0.622 | 0.025 | 7→137 |
| legal_multilingual_e5_small | FAIL | 0.999 ✗ | 0.003 ✗ | ✗ | 22.9% | 0.680 | 0.015 | 13→293 |
| legal_xlm_roberta_base | FAIL | 1.000 ✗ | 0.003 ✗ | ✗ | 90.9% | 0.590 | 0.104 | 6→110 |

*PASS but overclusters (1 coarse cluster → ~1000 fine clusters, hierarchical_advantage = 0)

---

## Detailed Findings

### 1. center_projected (Reference Baseline) ✅
- **Adversarial Language Dominance:** 0.763 (PASS, threshold 0.85)
- **Jurist Pairwise Preference:** 0.528 (PASS, threshold 0.5)
- **Hierarchical Structure:** 7 coarse clusters → 105 fine clusters
- **Improvement Rate:** 59.0% (zoom reveals more specific legal structure)
- **Hierarchical Advantage:** 0.027 (hierarchical > flat clustering)
- **Legal Area NMI:** 0.600
- **Cluster Coherence:** PASS (mean branch purity 0.916)
- **Cross-language Retrieval:** FAIL (recall@10 = 0.158)

**Assessment:** The only representation with meaningful fractal structure that passes both adversarial gates. Confirmed as the reference representation to beat.

### 2. Pure Citation Role Embeddings (Overclustering Artifact) ⚠️
All 6 pure citation role embeddings (following, distinguishing, overruling, criticizing, citing, all_weighted) show:
- **Adversarial PASS** but with **1 coarse cluster** → **~1000 fine clusters** (every decision its own cluster)
- **Hierarchical Advantage = 0.0** (no benefit over flat clustering)
- **Jurist Preference artificially high** (0.82-0.85) because k-NN in overclustered space is essentially random
- **Cross-language retrieval passes** (recall@10 ~0.23) but this is also an artifact

**Root Cause:** Signal sparsity (4.5% citation ID resolution rate). With 25,458 role annotations but only 465 resolved court citations, the embeddings are nearly empty matrices causing each decision to be isolated.

### 3. Pre-trained Legal Embeddings (Language Dominated) ❌
- **xlm_roberta_base:** lang_dom=0.999, jurist_pref=0.003
- **paraphrase_multilingual_minilm:** lang_dom=0.972, jurist_pref=0.058  
- **multilingual_e5_small:** lang_dom=0.999, jurist_pref=0.003

All fail both adversarial gates. Language dominates the representation space completely. These results differ from v5 evaluation which used different metrics (language_dominance_ratio vs mean_language_dominance).

### 4. ft_multilingual_e5_small_pretrained (Overclustering) ⚠️
- Passes adversarial tests (lang_dom=0.488, jurist_pref=0.702) but overclusters (1→1000)
- Same pathology as pure citation roles - no meaningful hierarchical structure

---

## Cross-Validation with Previous Results

| Source | center_projected LangDom | center_projected JuristPref |
|---|---|---|
| Evaluation v2 (factory dir v6) | 0.7593 | 0.5215 |
| Citation roles rebuilt eval | 0.7529 | 0.5485 |
| **This evaluation** | **0.7632** | **0.5275** |

**Consistent:** center_projected reliably passes both adversarial gates across independent runs.

---

## Recommendations for Next Factory Direction

### 1. **Objective 3 (Legal Embeddings) - REVISE APPROACH**
- Pre-trained multilingual models FAIL adversarial tests on this metric
- Fine-tuning multilingual-e5-small on Swiss legal corpus (GPU blocked) remains the only viable path
- Consider: Contrastive learning with legal structure supervision on CPU (slower but feasible)
- Alternative: Test other pre-trained legal models (SwissBERT, Legal-bert variants)

### 2. **Objective 4 (Citation Role Modeling) - SCALE NEEDED**
- Pipeline FIXED (25,458 roles, 1,124 ID mappings, 465 resolved)
- Signal too sparse at 1,000 decisions (4.5% resolution)
- **Solution:** Corpus scale to 192k decisions (corpus lane v6) will dramatically improve resolution
- Hybrids with center_projected show marginal gains (criticizing_α=0.3: +0.007 fine purity)
- Recommend: Defer citation role hybrids until corpus scale improves signal density

### 3. **Objective 5 (Jurist Evaluation) - FRAMEWORK READY**
- Evaluation framework complete (200 questions, UI spec, sampling, analysis plan)
- Needs 5-10 Swiss jurists for ACCEPTED tier
- Recommend: Prioritize human study recruitment for next cycle

### 4. **Signal Ablation / Scale Test Hybrids - PROMISING PATH**
From v5 results (not re-evaluated here but preserved):
- `legal_issues_outcomes`: best NMI (0.747), good fine purity balance
- `legal_area_tfidf`: highest fine purity (0.996), best NMI (0.726)
- `hybrid_erwaegungen_03`: best structure-preserving hybrid
- These hybrids with center_projected as base warrant further exploration

---

## Evidence Artifacts

- **Raw Results:** `legal_distance/results/v6_comprehensive_evaluation/comprehensive_evaluation_results.json`
- **Experiment Script:** `legal_distance/experiments/v6_comprehensive_evaluation.py`
- **Lane State:** `state/legal-distance.json` (to be updated)

---

## Lane State Update

```json
{
  "lane": "legal-distance",
  "direction_version": 6,
  "evidence_tier": "REPRODUCED",
  "cycle_status": "COMPLETED",
  "continue_recommended": true,
  "accepted_run_id": "comprehensive_evaluation_20260828",
  "evidence_refs": [
    "legal_distance/results/v6_comprehensive_evaluation/comprehensive_evaluation_results.json",
    "legal_distance/experiments/v6_comprehensive_evaluation.py"
  ],
  "next_recommendation": "center_projected confirmed as sole well-behaved reference representation. Pure citation roles overcluster (artifact). Pre-trained legal embeddings language-dominated. Fine-tuning multilingual-e5-small requires GPU. Citation role signal needs corpus scale (192k). Jurist framework ready. Next cycle: (1) CPU-based contrastive fine-tuning of multilingual-e5-small; (2) Test signal ablation hybrids (legal_issues_outcomes, legal_area_tfidf, hybrid_erwaegungen_03) against adversarial gates; (3) Corpus scale to 192k for citation role resolution.",
  "critical_findings": {
    "center_projected_validated": "ONLY representation passing BOTH adversarial gates WITH meaningful hierarchical structure (improvement_rate=59%, hierarchical_advantage=0.027)",
    "citation_roles_overcluster": "All 6 pure roles: 1 coarse → ~1000 fine clusters, hierarchical_advantage=0.0, adversarial PASS is artifact",
    "legal_embeddings_fail": "xlm_roberta_base, paraphrase_multilingual_minilm, multilingual_e5_small all FAIL (lang_dom≈1.0, jurist_pref≈0.0)",
    "ft_e5_small_overcluster": "Pre-trained multilingual-e5-small passes adversarial but overclusters (1→1000)",
    "signal_ablation_hybrids_promising": "legal_issues_outcomes (NMI=0.747), legal_area_tfidf (fine_purity=0.996), hybrid_erwaegungen_03 (best structure) from v5 results"
  }
}
```

---

## Conclusion

The comprehensive evaluation confirms **center_projected as the validated reference representation** - the only one that passes both adversarial benchmarks while maintaining meaningful fractal structure. Pure citation role embeddings and ft_multilingual_e5_small_pretrained pass adversarial tests only through overclustering artifacts. Pre-trained legal embeddings fail completely on multilingual invariance.

**Next cycle should focus on:**
1. CPU-viable fine-tuning approaches for multilingual-e5-small
2. Testing v5 signal ablation hybrids against adversarial gates
3. Corpus scale to 192k to unlock citation role signal density
4. Jurist human study execution