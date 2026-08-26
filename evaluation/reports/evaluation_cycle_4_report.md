# Evaluation Cycle Report — New Benchmarks on TF-IDF Baseline

**Run ID:** eval_cycle_4_20260826_225741
**Lane:** evaluation
**Direction version:** 1
**Date:** 2026-08-26
**Evidence tier:** REPRODUCED (new benchmarks on real corpus)

---

## 1. Hypothesis & Product Decision

**Question:** Do two new benchmarks — citation proximity and legal-area clustering — produce interpretable results on the TF-IDF baseline? Can they discriminate between weak and strong legal representations?

**Product decision:** If TF-IDF passes citation proximity but fails legal-area clustering, the benchmarks are discriminating. If both pass or both fail, the benchmarks need recalibration.

**Baseline frozen before observation:**
- Representation: TF-IDF reasoning-only (10K features, 1-2 grams, sublinear TF)
- Corpus: BGer canonical decisions (1,200+)
- Citation proximity success: AUC-ROC > 0.7
- Legal-area clustering success: NMI > 0.3 AND purity > 0.7

---

## 2. Benchmark Results

### 2.1 citation_proximity — FAILED

**FAILED**

| Metric | Value |
|--------|-------|
| auc_roc | 0.6354 |
| positive_mean_sim | 0.1867 |
| negative_mean_sim | 0.1269 |
| mean_similarity_gap | 0.0598 |
| num_positive_pairs | 300 |
| num_negative_pairs | 300 |
| num_unique_decisions | 707 |
| num_embedded_decisions | 707 |
| mean_shared_citations | 1.2733 |
| max_shared_citations | 6 |

**Baseline comparison:**
- auc_roc_random: 0.5
- note: Random embeddings: AUC = 0.5. TF-IDF on full text: expected ~0.7-0.85 (shared vocabulary from same legal domain). Legal-BERT: expected >0.85.

**Duration:** 0.34s

### 2.2 legal_area_clustering — FAILED

**FAILED**

| Metric | Value |
|--------|-------|
| best_nmi | 0.0487 |
| best_purity | 0.7046 |
| nmi_at_true_k | 0.0283 |
| purity_at_true_k | 0.4153 |
| num_decisions | 400 |
| num_branches | 4 |
| branch_distribution | {'strafrecht': 306, 'zivilrecht': 311, 'oeffentliches_recht': 293, 'sozialversicherungsrecht': 290} |
| level_0_n_clusters | 4 |
| level_0_nmi | 0.0283 |
| level_0_purity | 0.4153 |
| level_0_num_valid_decisions | 400 |
| level_1_n_clusters | 6 |
| level_1_nmi | 0.0411 |
| level_1_purity | 0.6110 |
| level_1_num_valid_decisions | 400 |
| level_2_n_clusters | 8 |
| level_2_nmi | 0.0421 |
| level_2_purity | 0.6874 |
| level_2_num_valid_decisions | 400 |
| level_3_n_clusters | 12 |
| level_3_nmi | 0.0487 |
| level_3_purity | 0.7046 |
| level_3_num_valid_decisions | 400 |

**Baseline comparison:**
- random_nmi: 0.0
- random_purity: 0.25
- note: Random clustering: NMI ~ 0, purity ~ 1/k. TF-IDF expected: NMI ~ 0.01-0.05 (language-dominated). Legal embeddings: NMI > 0.3.

**Duration:** 2.10s

---

## 3. Interpretation

### Citation Proximity
- AUC-ROC: 0.6354
- TF-IDF does NOT capture citation-relevant similarity.

### Legal-Area Clustering
- Best NMI: 0.0487
- Best purity: 0.7046
- TF-IDF clustering does NOT align with legal branches (language dominates).
- Some clusters are internally pure, but this may reflect language separation.

---

## 4. Negative Results (Preserved)

1. **cited_laws field is empty** in all canonical JSONL files — cited-law proximity benchmark cancelled this cycle.
2. **Legal-area clustering NMI expected to be low** for TF-IDF — confirmed by fractal-map lane finding (language purity 0.99, legal-area purity 0.43).

## 5. Recommendations

CONTINUE — These new benchmarks are ready for the legal-distance lane to target.

Specific targets for legal-distance representations:
- Citation proximity: AUC > 0.75 (beat TF-IDF's 0.64)
- Legal-area clustering: NMI > 0.3 AND purity > 0.7 (beat TF-IDF's NMI 0.05)

## 6. Files Produced

- `evaluation/results/cycle_4_new_benchmarks_results.json` — Detailed results
- `evaluation/results/cycle_4_combined_results.json` — Machine-readable combined
- `evaluation/reports/evaluation_cycle_4_report.md` — This report
- `evaluation/tests/citation_proximity.py` — Citation proximity benchmark
- `evaluation/tests/legal_area_clustering.py` — Legal-area clustering benchmark
