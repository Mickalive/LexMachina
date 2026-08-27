# Evaluation Cycle 7: Fixed Citation Graph + Zoom Coherence

## Hypothesis
Fixing the citation graph benchmark to use shared citation heritage (>=2 shared
references) instead of direct citation links will produce valid AUC scores. Adding
zoom coherence as a formal benchmark will validate the fractal architecture hypothesis.

## Frozen Before Observation
- Sample: All fractal-map embeddings (10 representations)
- Benchmarks: citation_graph_neighborhood (fixed), citation_proximity, legal_area_clustering, zoom_coherence
- Targets: citation_graph AUC > 0.7, citation_proximity AUC > 0.75, legal_area NMI > 0.3, legal_area purity > 0.7, zoom_coherence improvement_rate > 0.5

## Results Summary

| Representation | Dim | CG AUC | CP AUC | LA NMI | LA Purity | Zoom Rate | Targets |
|---|---|---|---|---|---|---|---|
| baseline | 768 | 0.6518 | 0.4833 | 0.2831 | 0.5700 | 1.0000 | 1/5 |
| section_sachverhalt | 768 | 0.6835 | 0.5225 | 0.4782 | 0.8571 | 1.0000 | 3/5 |
| section_erwaegungen | 768 | 0.6061 | 0.6562 | 0.2436 | 0.6607 | 1.0000 | 1/5 |
| section_dispositiv | 768 | 0.5808 | 0.6066 | 0.1291 | 0.5893 | 1.0000 | 1/5 |
| section_full_text | 768 | 0.6253 | 0.4790 | 0.2964 | 0.6786 | 1.0000 | 1/5 |
| section_combined | 768 | 0.6835 | 0.5225 | 0.4782 | 0.8571 | 1.0000 | 3/5 |
| section_erwaegungen_dispositiv | 768 | 0.6057 | 0.6562 | 0.2436 | 0.6607 | 1.0000 | 1/5 |
| language_debiased_pca2 | 768 | 0.7046 | 0.5263 | 0.4373 | 0.7200 | 1.0000 | 4/5 |
| citation_blended | 64 | 0.6837 | 0.5794 | 0.2509 | 0.5700 | 1.0000 | 1/5 |
| citation_graph_only | 64 | 0.5987 | 0.5545 | 0.2440 | 0.5600 | 1.0000 | 1/5 |

## Detailed Results

### baseline
- Description: sentence-transformers/paraphrase-multilingual-mpnet-base-v2 (768-dim)
- Embeddings: 1000 decisions, 768d
- Duration: 1.1s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.6518
  - positive_mean_sim: 0.9164
  - negative_mean_sim: 0.8957
  - mean_gap: 0.0207
- **legal_area_clustering**: FAILED
  - nmi: 0.2831
  - purity: 0.5700
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 37, np.str_('zivilrecht'): 21, np.str_('oeffentliches_recht'): 13, np.str_('strafrecht'): 29}
- **citation_proximity**: FAILED
  - auc_roc: 0.4833
  - positive_mean_sim: 0.8970
  - negative_mean_sim: 0.9003
- **zoom_coherence**: PASSED
  - overall_improvement_rate: 1.0000
  - best_coarse_to_fine_improvement_pct: 0.0000
  - best_fine_ratio: 1.0854
  - flat_baseline_best_ratio: 0.4920
  - mean_improvement_rate: 836.4578
- **Targets:**
  - citation_graph_auc: 0.6518 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.4833 vs 0.75 -> FAIL
  - legal_area_nmi: 0.2831 vs 0.3 -> FAIL
  - legal_area_purity: 0.5700 vs 0.7 -> FAIL
  - zoom_coherence_improvement_rate: 1.0000 vs 0.5 -> PASS

### section_sachverhalt
- Description: TF-IDF on Sachverhalt (facts) section only
- Embeddings: 63 decisions, 768d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.6835
  - positive_mean_sim: 0.5855
  - negative_mean_sim: 0.4758
  - mean_gap: 0.1097
- **legal_area_clustering**: PASSED
  - nmi: 0.4782
  - purity: 0.8571
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 30, np.str_('zivilrecht'): 12, np.str_('strafrecht'): 14}
- **citation_proximity**: FAILED
  - auc_roc: 0.5225
  - positive_mean_sim: 0.4874
  - negative_mean_sim: 0.4699
- **zoom_coherence**: PASSED
  - overall_improvement_rate: 1.0000
  - best_coarse_to_fine_improvement_pct: 0.0000
  - best_fine_ratio: 1.0854
  - flat_baseline_best_ratio: 0.4920
  - mean_improvement_rate: 836.4578
- **Targets:**
  - citation_graph_auc: 0.6835 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.5225 vs 0.75 -> FAIL
  - legal_area_nmi: 0.4782 vs 0.3 -> PASS
  - legal_area_purity: 0.8571 vs 0.7 -> PASS
  - zoom_coherence_improvement_rate: 1.0000 vs 0.5 -> PASS

### section_erwaegungen
- Description: TF-IDF on Erwaegungen (reasoning) section only
- Embeddings: 63 decisions, 768d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.6061
  - positive_mean_sim: 0.8135
  - negative_mean_sim: 0.7814
  - mean_gap: 0.0321
- **legal_area_clustering**: FAILED
  - nmi: 0.2436
  - purity: 0.6607
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 30, np.str_('zivilrecht'): 12, np.str_('strafrecht'): 14}
- **citation_proximity**: FAILED
  - auc_roc: 0.6562
  - positive_mean_sim: 0.8166
  - negative_mean_sim: 0.7765
- **zoom_coherence**: PASSED
  - overall_improvement_rate: 1.0000
  - best_coarse_to_fine_improvement_pct: 0.0000
  - best_fine_ratio: 1.0854
  - flat_baseline_best_ratio: 0.4920
  - mean_improvement_rate: 836.4578
- **Targets:**
  - citation_graph_auc: 0.6061 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.6562 vs 0.75 -> FAIL
  - legal_area_nmi: 0.2436 vs 0.3 -> FAIL
  - legal_area_purity: 0.6607 vs 0.7 -> FAIL
  - zoom_coherence_improvement_rate: 1.0000 vs 0.5 -> PASS

### section_dispositiv
- Description: TF-IDF on Dispositiv (disposition) section only
- Embeddings: 63 decisions, 768d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.5808
  - positive_mean_sim: 0.8545
  - negative_mean_sim: 0.8324
  - mean_gap: 0.0221
- **legal_area_clustering**: FAILED
  - nmi: 0.1291
  - purity: 0.5893
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 30, np.str_('zivilrecht'): 12, np.str_('strafrecht'): 14}
- **citation_proximity**: FAILED
  - auc_roc: 0.6066
  - positive_mean_sim: 0.8561
  - negative_mean_sim: 0.8165
- **zoom_coherence**: PASSED
  - overall_improvement_rate: 1.0000
  - best_coarse_to_fine_improvement_pct: 0.0000
  - best_fine_ratio: 1.0854
  - flat_baseline_best_ratio: 0.4920
  - mean_improvement_rate: 836.4578
- **Targets:**
  - citation_graph_auc: 0.5808 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.6066 vs 0.75 -> FAIL
  - legal_area_nmi: 0.1291 vs 0.3 -> FAIL
  - legal_area_purity: 0.5893 vs 0.7 -> FAIL
  - zoom_coherence_improvement_rate: 1.0000 vs 0.5 -> PASS

### section_full_text
- Description: TF-IDF on full text
- Embeddings: 63 decisions, 768d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.6253
  - positive_mean_sim: 0.9188
  - negative_mean_sim: 0.9062
  - mean_gap: 0.0126
- **legal_area_clustering**: FAILED
  - nmi: 0.2964
  - purity: 0.6786
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 30, np.str_('zivilrecht'): 12, np.str_('strafrecht'): 14}
- **citation_proximity**: FAILED
  - auc_roc: 0.4790
  - positive_mean_sim: 0.9064
  - negative_mean_sim: 0.9115
- **zoom_coherence**: PASSED
  - overall_improvement_rate: 1.0000
  - best_coarse_to_fine_improvement_pct: 0.0000
  - best_fine_ratio: 1.0854
  - flat_baseline_best_ratio: 0.4920
  - mean_improvement_rate: 836.4578
- **Targets:**
  - citation_graph_auc: 0.6253 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.4790 vs 0.75 -> FAIL
  - legal_area_nmi: 0.2964 vs 0.3 -> FAIL
  - legal_area_purity: 0.6786 vs 0.7 -> FAIL
  - zoom_coherence_improvement_rate: 1.0000 vs 0.5 -> PASS

### section_combined
- Description: TF-IDF on Sachverhalt + Erwaegungen + Dispositiv
- Embeddings: 63 decisions, 768d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.6835
  - positive_mean_sim: 0.5855
  - negative_mean_sim: 0.4758
  - mean_gap: 0.1097
- **legal_area_clustering**: PASSED
  - nmi: 0.4782
  - purity: 0.8571
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 30, np.str_('zivilrecht'): 12, np.str_('strafrecht'): 14}
- **citation_proximity**: FAILED
  - auc_roc: 0.5225
  - positive_mean_sim: 0.4874
  - negative_mean_sim: 0.4699
- **zoom_coherence**: PASSED
  - overall_improvement_rate: 1.0000
  - best_coarse_to_fine_improvement_pct: 0.0000
  - best_fine_ratio: 1.0854
  - flat_baseline_best_ratio: 0.4920
  - mean_improvement_rate: 836.4578
- **Targets:**
  - citation_graph_auc: 0.6835 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.5225 vs 0.75 -> FAIL
  - legal_area_nmi: 0.4782 vs 0.3 -> PASS
  - legal_area_purity: 0.8571 vs 0.7 -> PASS
  - zoom_coherence_improvement_rate: 1.0000 vs 0.5 -> PASS

### section_erwaegungen_dispositiv
- Description: TF-IDF on Erwaegungen + Dispositiv
- Embeddings: 63 decisions, 768d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.6057
  - positive_mean_sim: 0.8135
  - negative_mean_sim: 0.7814
  - mean_gap: 0.0320
- **legal_area_clustering**: FAILED
  - nmi: 0.2436
  - purity: 0.6607
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 30, np.str_('zivilrecht'): 12, np.str_('strafrecht'): 14}
- **citation_proximity**: FAILED
  - auc_roc: 0.6562
  - positive_mean_sim: 0.8166
  - negative_mean_sim: 0.7766
- **zoom_coherence**: PASSED
  - overall_improvement_rate: 1.0000
  - best_coarse_to_fine_improvement_pct: 0.0000
  - best_fine_ratio: 1.0854
  - flat_baseline_best_ratio: 0.4920
  - mean_improvement_rate: 836.4578
- **Targets:**
  - citation_graph_auc: 0.6057 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.6562 vs 0.75 -> FAIL
  - legal_area_nmi: 0.2436 vs 0.3 -> FAIL
  - legal_area_purity: 0.6607 vs 0.7 -> FAIL
  - zoom_coherence_improvement_rate: 1.0000 vs 0.5 -> PASS

### language_debiased_pca2
- Description: Baseline with language debiasing (PCA 2 components removed)
- Embeddings: 1000 decisions, 768d
- Duration: 0.0s
- **citation_graph_neighborhood**: PASSED
  - auc_roc: 0.7046
  - positive_mean_sim: 0.9327
  - negative_mean_sim: 0.9153
  - mean_gap: 0.0173
- **legal_area_clustering**: PASSED
  - nmi: 0.4373
  - purity: 0.7200
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 37, np.str_('zivilrecht'): 21, np.str_('oeffentliches_recht'): 13, np.str_('strafrecht'): 29}
- **citation_proximity**: FAILED
  - auc_roc: 0.5263
  - positive_mean_sim: 0.9174
  - negative_mean_sim: 0.9172
- **zoom_coherence**: PASSED
  - overall_improvement_rate: 1.0000
  - best_coarse_to_fine_improvement_pct: 0.0000
  - best_fine_ratio: 1.0854
  - flat_baseline_best_ratio: 0.4920
  - mean_improvement_rate: 836.4578
- **Targets:**
  - citation_graph_auc: 0.7046 vs 0.7 -> PASS
  - citation_proximity_auc: 0.5263 vs 0.75 -> FAIL
  - legal_area_nmi: 0.4373 vs 0.3 -> PASS
  - legal_area_purity: 0.7200 vs 0.7 -> PASS
  - zoom_coherence_improvement_rate: 1.0000 vs 0.5 -> PASS

### citation_blended
- Description: Blended citation + semantic embeddings
- Embeddings: 1000 decisions, 64d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.6837
  - positive_mean_sim: 0.2124
  - negative_mean_sim: 0.0295
  - mean_gap: 0.1829
- **legal_area_clustering**: FAILED
  - nmi: 0.2509
  - purity: 0.5700
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 37, np.str_('zivilrecht'): 21, np.str_('oeffentliches_recht'): 13, np.str_('strafrecht'): 29}
- **citation_proximity**: FAILED
  - auc_roc: 0.5794
  - positive_mean_sim: 0.1294
  - negative_mean_sim: 0.0418
- **zoom_coherence**: PASSED
  - overall_improvement_rate: 1.0000
  - best_coarse_to_fine_improvement_pct: 0.0000
  - best_fine_ratio: 1.0854
  - flat_baseline_best_ratio: 0.4920
  - mean_improvement_rate: 836.4578
- **Targets:**
  - citation_graph_auc: 0.6837 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.5794 vs 0.75 -> FAIL
  - legal_area_nmi: 0.2509 vs 0.3 -> FAIL
  - legal_area_purity: 0.5700 vs 0.7 -> FAIL
  - zoom_coherence_improvement_rate: 1.0000 vs 0.5 -> PASS

### citation_graph_only
- Description: Citation graph embeddings only
- Embeddings: 1000 decisions, 64d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.5987
  - positive_mean_sim: 0.1637
  - negative_mean_sim: 0.0322
  - mean_gap: 0.1315
- **legal_area_clustering**: FAILED
  - nmi: 0.2440
  - purity: 0.5600
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 37, np.str_('zivilrecht'): 21, np.str_('oeffentliches_recht'): 13, np.str_('strafrecht'): 29}
- **citation_proximity**: FAILED
  - auc_roc: 0.5545
  - positive_mean_sim: 0.1384
  - negative_mean_sim: 0.0367
- **zoom_coherence**: PASSED
  - overall_improvement_rate: 1.0000
  - best_coarse_to_fine_improvement_pct: 0.0000
  - best_fine_ratio: 1.0854
  - flat_baseline_best_ratio: 0.4920
  - mean_improvement_rate: 836.4578
- **Targets:**
  - citation_graph_auc: 0.5987 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.5545 vs 0.75 -> FAIL
  - legal_area_nmi: 0.2440 vs 0.3 -> FAIL
  - legal_area_purity: 0.5600 vs 0.7 -> FAIL
  - zoom_coherence_improvement_rate: 1.0000 vs 0.5 -> PASS

## Key Findings

- Best citation_graph_neighborhood_auc_roc: **language_debiased_pca2** (0.7046)
- Best citation_graph_neighborhood_mean_gap: **citation_blended** (0.1829)
- Best citation_graph_neighborhood_negative_mean_sim: **language_debiased_pca2** (0.9153)
- Best citation_graph_neighborhood_positive_mean_sim: **language_debiased_pca2** (0.9327)
- Best citation_proximity_auc_roc: **section_erwaegungen** (0.6562)
- Best citation_proximity_negative_mean_sim: **language_debiased_pca2** (0.9172)
- Best citation_proximity_positive_mean_sim: **language_debiased_pca2** (0.9174)
- Best legal_area_clustering_nmi: **section_sachverhalt** (0.4782)
- Best legal_area_clustering_purity: **section_sachverhalt** (0.8571)
- Best zoom_coherence_best_coarse_to_fine_improvement_pct: **baseline** (0.0000)
- Best zoom_coherence_best_fine_ratio: **baseline** (1.0854)
- Best zoom_coherence_flat_baseline_best_ratio: **baseline** (0.4920)
- Best zoom_coherence_mean_improvement_rate: **baseline** (836.4578)
- Best zoom_coherence_overall_improvement_rate: **baseline** (1.0000)

## Negative Results

- baseline failed: citation_graph_auc, citation_proximity_auc, legal_area_nmi, legal_area_purity
- section_sachverhalt failed: citation_graph_auc, citation_proximity_auc
- section_erwaegungen failed: citation_graph_auc, citation_proximity_auc, legal_area_nmi, legal_area_purity
- section_dispositiv failed: citation_graph_auc, citation_proximity_auc, legal_area_nmi, legal_area_purity
- section_full_text failed: citation_graph_auc, citation_proximity_auc, legal_area_nmi, legal_area_purity
- section_combined failed: citation_graph_auc, citation_proximity_auc
- section_erwaegungen_dispositiv failed: citation_graph_auc, citation_proximity_auc, legal_area_nmi, legal_area_purity
- language_debiased_pca2 failed: citation_proximity_auc
- citation_blended failed: citation_graph_auc, citation_proximity_auc, legal_area_nmi, legal_area_purity
- citation_graph_only failed: citation_graph_auc, citation_proximity_auc, legal_area_nmi, legal_area_purity

## Recommendation

NO representation passes all targets.
Legal-distance lane should focus on:
1. Citation-aware representations (citation proximity AUC is hardest target)
2. Hybrid methods combining semantic + citation + legal-area signals
   - Best for citation_graph_auc: language_debiased_pca2 (0.7046)
   - Best for citation_proximity_auc: section_erwaegungen (0.6562)
   - Best for legal_area_nmi: section_sachverhalt (0.4782)
   - Best for legal_area_purity: section_sachverhalt (0.8571)
   - Best for zoom_coherence_improvement_rate: baseline (1.0000)