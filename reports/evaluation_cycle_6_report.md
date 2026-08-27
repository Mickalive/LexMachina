# Evaluation Cycle 6: Fractal-Map Representation Comparison

## Hypothesis
Fractal-map's section-based and combined representations will outperform
the baseline on citation proximity and legal area clustering, but may fail
on citation graph neighborhood due to loss of cross-document signal.

## Frozen Before Observation
- Sample: All decisions with fractal-map embeddings
- Benchmarks: citation_graph_neighborhood, legal_area_clustering, citation_proximity
- Targets: citation_graph AUC > 0.7, legal_area NMI > 0.3, legal_area purity > 0.7

## Results Summary

| Representation | Dim | CG AUC | LA NMI | LA Purity | CP AUC | Targets |
|---|---|---|---|---|---|---|
| baseline | 768 | 0.5000 | 0.2831 | 0.5700 | 0.5373 | 0/4 |
| section_sachverhalt | 768 | 0.5000 | 0.4782 | 0.8571 | 0.6184 | 2/4 |
| section_erwaegungen | 768 | 0.5000 | 0.2436 | 0.6607 | 0.6860 | 0/4 |
| section_dispositiv | 768 | 0.5000 | 0.1291 | 0.5893 | 0.5809 | 0/4 |
| section_full_text | 768 | 0.5000 | 0.2964 | 0.6786 | 0.5507 | 0/4 |
| section_combined | 768 | 0.5000 | 0.4782 | 0.8571 | 0.6184 | 2/4 |
| section_erwaegungen_dispositiv | 768 | 0.5000 | 0.2436 | 0.6607 | 0.6860 | 0/4 |
| language_debiased_pca2 | 768 | 0.5000 | 0.4373 | 0.7200 | 0.5961 | 2/4 |
| citation_blended | 64 | 0.5000 | 0.2509 | 0.5700 | 0.5752 | 0/4 |
| citation_graph_only | 64 | 0.5000 | 0.2440 | 0.5600 | 0.5917 | 0/4 |

## Detailed Results

### baseline
- Description: sentence-transformers/paraphrase-multilingual-mpnet-base-v2 (768-dim)
- Embeddings: 1000 decisions, 768d
- Duration: 1.1s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.5000
- **legal_area_clustering**: FAILED
  - nmi: 0.2831
  - purity: 0.5700
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 37, np.str_('oeffentliches_recht'): 13, np.str_('strafrecht'): 29, np.str_('zivilrecht'): 21}
- **citation_proximity**: FAILED
  - auc_roc: 0.5373
  - positive_mean_sim: 0.9016
  - negative_mean_sim: 0.9003
- **Targets:**
  - citation_graph_auc: 0.5000 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.5373 vs 0.75 -> FAIL
  - legal_area_nmi: 0.2831 vs 0.3 -> FAIL
  - legal_area_purity: 0.5700 vs 0.7 -> FAIL

### section_sachverhalt
- Description: TF-IDF on Sachverhalt (facts) section only
- Embeddings: 63 decisions, 768d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.5000
- **legal_area_clustering**: PASSED
  - nmi: 0.4782
  - purity: 0.8571
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 30, np.str_('strafrecht'): 14, np.str_('zivilrecht'): 12}
- **citation_proximity**: FAILED
  - auc_roc: 0.6184
  - positive_mean_sim: 0.5484
  - negative_mean_sim: 0.4699
- **Targets:**
  - citation_graph_auc: 0.5000 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.6184 vs 0.75 -> FAIL
  - legal_area_nmi: 0.4782 vs 0.3 -> PASS
  - legal_area_purity: 0.8571 vs 0.7 -> PASS

### section_erwaegungen
- Description: TF-IDF on Erwaegungen (reasoning) section only
- Embeddings: 63 decisions, 768d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.5000
- **legal_area_clustering**: FAILED
  - nmi: 0.2436
  - purity: 0.6607
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 30, np.str_('strafrecht'): 14, np.str_('zivilrecht'): 12}
- **citation_proximity**: FAILED
  - auc_roc: 0.6860
  - positive_mean_sim: 0.8263
  - negative_mean_sim: 0.7765
- **Targets:**
  - citation_graph_auc: 0.5000 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.6860 vs 0.75 -> FAIL
  - legal_area_nmi: 0.2436 vs 0.3 -> FAIL
  - legal_area_purity: 0.6607 vs 0.7 -> FAIL

### section_dispositiv
- Description: TF-IDF on Dispositiv (disposition) section only
- Embeddings: 63 decisions, 768d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.5000
- **legal_area_clustering**: FAILED
  - nmi: 0.1291
  - purity: 0.5893
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 30, np.str_('strafrecht'): 14, np.str_('zivilrecht'): 12}
- **citation_proximity**: FAILED
  - auc_roc: 0.5809
  - positive_mean_sim: 0.8401
  - negative_mean_sim: 0.8165
- **Targets:**
  - citation_graph_auc: 0.5000 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.5809 vs 0.75 -> FAIL
  - legal_area_nmi: 0.1291 vs 0.3 -> FAIL
  - legal_area_purity: 0.5893 vs 0.7 -> FAIL

### section_full_text
- Description: TF-IDF on full text
- Embeddings: 63 decisions, 768d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.5000
- **legal_area_clustering**: FAILED
  - nmi: 0.2964
  - purity: 0.6786
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 30, np.str_('strafrecht'): 14, np.str_('zivilrecht'): 12}
- **citation_proximity**: FAILED
  - auc_roc: 0.5507
  - positive_mean_sim: 0.9162
  - negative_mean_sim: 0.9115
- **Targets:**
  - citation_graph_auc: 0.5000 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.5507 vs 0.75 -> FAIL
  - legal_area_nmi: 0.2964 vs 0.3 -> FAIL
  - legal_area_purity: 0.6786 vs 0.7 -> FAIL

### section_combined
- Description: TF-IDF on Sachverhalt + Erwaegungen + Dispositiv
- Embeddings: 63 decisions, 768d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.5000
- **legal_area_clustering**: PASSED
  - nmi: 0.4782
  - purity: 0.8571
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 30, np.str_('strafrecht'): 14, np.str_('zivilrecht'): 12}
- **citation_proximity**: FAILED
  - auc_roc: 0.6184
  - positive_mean_sim: 0.5484
  - negative_mean_sim: 0.4699
- **Targets:**
  - citation_graph_auc: 0.5000 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.6184 vs 0.75 -> FAIL
  - legal_area_nmi: 0.4782 vs 0.3 -> PASS
  - legal_area_purity: 0.8571 vs 0.7 -> PASS

### section_erwaegungen_dispositiv
- Description: TF-IDF on Erwaegungen + Dispositiv
- Embeddings: 63 decisions, 768d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.5000
- **legal_area_clustering**: FAILED
  - nmi: 0.2436
  - purity: 0.6607
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 30, np.str_('strafrecht'): 14, np.str_('zivilrecht'): 12}
- **citation_proximity**: FAILED
  - auc_roc: 0.6860
  - positive_mean_sim: 0.8263
  - negative_mean_sim: 0.7766
- **Targets:**
  - citation_graph_auc: 0.5000 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.6860 vs 0.75 -> FAIL
  - legal_area_nmi: 0.2436 vs 0.3 -> FAIL
  - legal_area_purity: 0.6607 vs 0.7 -> FAIL

### language_debiased_pca2
- Description: Baseline with language debiasing (PCA 2 components removed)
- Embeddings: 1000 decisions, 768d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.5000
- **legal_area_clustering**: PASSED
  - nmi: 0.4373
  - purity: 0.7200
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 37, np.str_('oeffentliches_recht'): 13, np.str_('strafrecht'): 29, np.str_('zivilrecht'): 21}
- **citation_proximity**: FAILED
  - auc_roc: 0.5961
  - positive_mean_sim: 0.9226
  - negative_mean_sim: 0.9172
- **Targets:**
  - citation_graph_auc: 0.5000 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.5961 vs 0.75 -> FAIL
  - legal_area_nmi: 0.4373 vs 0.3 -> PASS
  - legal_area_purity: 0.7200 vs 0.7 -> PASS

### citation_blended
- Description: Blended citation + semantic embeddings
- Embeddings: 1000 decisions, 64d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.5000
- **legal_area_clustering**: FAILED
  - nmi: 0.2509
  - purity: 0.5700
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 37, np.str_('oeffentliches_recht'): 13, np.str_('strafrecht'): 29, np.str_('zivilrecht'): 21}
- **citation_proximity**: FAILED
  - auc_roc: 0.5752
  - positive_mean_sim: 0.1106
  - negative_mean_sim: 0.0418
- **Targets:**
  - citation_graph_auc: 0.5000 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.5752 vs 0.75 -> FAIL
  - legal_area_nmi: 0.2509 vs 0.3 -> FAIL
  - legal_area_purity: 0.5700 vs 0.7 -> FAIL

### citation_graph_only
- Description: Citation graph embeddings only
- Embeddings: 1000 decisions, 64d
- Duration: 0.0s
- **citation_graph_neighborhood**: FAILED
  - auc_roc: 0.5000
- **legal_area_clustering**: FAILED
  - nmi: 0.2440
  - purity: 0.5600
  - branch_distribution: {np.str_('sozialversicherungsrecht'): 37, np.str_('oeffentliches_recht'): 13, np.str_('strafrecht'): 29, np.str_('zivilrecht'): 21}
- **citation_proximity**: FAILED
  - auc_roc: 0.5917
  - positive_mean_sim: 0.1114
  - negative_mean_sim: 0.0367
- **Targets:**
  - citation_graph_auc: 0.5000 vs 0.7 -> FAIL
  - citation_proximity_auc: 0.5917 vs 0.75 -> FAIL
  - legal_area_nmi: 0.2440 vs 0.3 -> FAIL
  - legal_area_purity: 0.5600 vs 0.7 -> FAIL

## Key Findings

- Best citation_graph_neighborhood_auc_roc: **baseline** (0.5000)
- Best citation_proximity_auc_roc: **section_erwaegungen** (0.6860)
- Best citation_proximity_negative_mean_sim: **language_debiased_pca2** (0.9172)
- Best citation_proximity_positive_mean_sim: **language_debiased_pca2** (0.9226)
- Best legal_area_clustering_nmi: **section_sachverhalt** (0.4782)
- Best legal_area_clustering_purity: **section_sachverhalt** (0.8571)

## Negative Results

- baseline failed: citation_graph_auc, citation_proximity_auc, legal_area_nmi, legal_area_purity
- section_sachverhalt failed: citation_graph_auc, citation_proximity_auc
- section_erwaegungen failed: citation_graph_auc, citation_proximity_auc, legal_area_nmi, legal_area_purity
- section_dispositiv failed: citation_graph_auc, citation_proximity_auc, legal_area_nmi, legal_area_purity
- section_full_text failed: citation_graph_auc, citation_proximity_auc, legal_area_nmi, legal_area_purity
- section_combined failed: citation_graph_auc, citation_proximity_auc
- section_erwaegungen_dispositiv failed: citation_graph_auc, citation_proximity_auc, legal_area_nmi, legal_area_purity
- language_debiased_pca2 failed: citation_graph_auc, citation_proximity_auc
- citation_blended failed: citation_graph_auc, citation_proximity_auc, legal_area_nmi, legal_area_purity
- citation_graph_only failed: citation_graph_auc, citation_proximity_auc, legal_area_nmi, legal_area_purity

## Recommendation

NO representation passes all targets.
Legal-distance lane should focus on:
1. Citation-aware representations (citation graph AUC is hardest target)
2. Hybrid methods combining semantic + citation + legal-area signals
   - Best for citation_graph_auc: baseline (0.5000)
   - Best for citation_proximity_auc: section_erwaegungen (0.6860)
   - Best for legal_area_nmi: section_sachverhalt (0.4782)
   - Best for legal_area_purity: section_sachverhalt (0.8571)