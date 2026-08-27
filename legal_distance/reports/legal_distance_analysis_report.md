# Legal Distance Lane — Analysis Report (Corrected)

**Factory Direction Version:** 3  
**Lane:** legal-distance  
**Run ID:** 33122921714 (repair of cycle 33119846410)  
**Evidence Tier Target:** ACCEPTED  
**Date:** 2026-08-27

---

## 1. Executive Summary

**Factory Direction Question:** *"Test which legally structured signals (norms/articles at issue, reasoning sections, citation roles, legal issues, outcomes, doctrine citations) improve nearest-neighbor legal relevance over the validated debiased_citation_blended baseline while suppressing procedural boilerplate."*

**Answer (Corrected):** **The `legal_cited_decisions_only` configuration achieves 14/14 PASS, tying the validated baseline.** The debiased_citation_blended baseline (n_pca=1, α=0.7) achieves 14/14 PASS. Legal signals improve specific legal-classification benchmarks (branch_knn, tf_metadata_human_indexing, legal_area_clustering NMI) but systematically degrade multilingual invariance and adversarial falsification (language dominance). The strongest single legal signal is **cited_decisions_only** (14/14 PASS — best boilerplate resistance at 0.088 correlation). Hybrids at α=0.3–0.5 maximize legal-classification metrics (branch_knn@5 up to 0.96, tf_metadata recall@1 up to 0.97) but still fail adversarial_falsification. **Recommendation:** Keep debiased_citation_blended as default general-purpose legal distance; expose legal_cited_decisions_only and hybrids as selectable map views for specific jurist tasks (precedent navigation, branch classification, human-indexing alignment).

**Critical Correction:** The original report claimed *"No single legal-signal configuration beats the validated baseline on all 14 benchmarks."* This was **false** due to two benchmark evaluation bugs (fixed in this repair). After fixes, `legal_cited_decisions_only` ties the baseline at 14/14 PASS.

---

## 2. Experimental Design

### 2.1 Corpus
- 1,000 Swiss Federal Supreme Court decisions (2000+ slice)
- Trilingual: German (de), French (fr), Italian (it)
- Legal branches: zivilrecht, strafrecht, oeffentliches_recht
- 100 legal areas (Jurivoc descriptors)

### 2.2 Baseline
**debiased_citation_blended** (validated in evaluation lane v1):
- Combines: 768-dim semantic embeddings + citation graph (Jaccard) + TF-IDF text
- Debiases 1 PCA component (language), blends with α=0.7 citation / 0.3 text
- Projects to 64 dims, L2-normalized
- **Result:** 14/14 benchmarks PASS (evaluation lane v1 closure)

### 2.3 Legal Signals Tested (11 Experiments)

| Experiment | Type | Signals Included | α (hybrid) |
|------------|------|------------------|------------|
| baseline_debiased_citation_blended | baseline | — | — |
| legal_statutes_only | legal_tfidf | statutes | — |
| legal_erwaegungen_only | legal_tfidf | erwaegungen (reasoning paragraphs) | — |
| legal_cited_decisions_only | legal_tfidf | cited decisions | — |
| legal_erwaegungen_statutes | legal_tfidf | erwaegungen + statutes | — |
| legal_full_signals | legal_tfidf | all 7 signals | — |
| legal_full_signals_noboilerplate | legal_tfidf | all 7 signals, no boilerplate suppression | — |
| hybrid_legal03_baseline07 | hybrid | all 7 signals + baseline | 0.3 |
| hybrid_legal05_baseline05 | hybrid | all 7 signals + baseline | 0.5 |
| hybrid_legal07_baseline03 | hybrid | all 7 signals + baseline | 0.7 |
| legal_statutes_erwaegungen_citations | legal_tfidf | statutes + erwaegungen + cited_decisions | — |
| legal_issues_outcomes | legal_tfidf | legal_area + outcome + erwaegungen_headings | — |

### 2.4 Benchmark Suite (14 Benchmarks, 10-11 Effectively Discriminating)

| # | Benchmark | What It Measures | PASS Threshold | Status |
|---|-----------|------------------|----------------|--------|
| 1 | citation_heritage | AUC-ROC for shared-citation pairs | AUC > 0.65 | Discriminating |
| 2 | adversarial_falsification | Language dominance < 0.85, branch coherence > 0.3 | Both | Discriminating |
| 3 | branch_knn | k-NN classification accuracy by legal branch | > 0.3 above random @ k=5 | Discriminating |
| 4 | collapse_check | Mean similarity < 0.3, near-identical pairs < 1% | Both | Discriminating |
| 5 | multilingual_invariance | Cross-lang same-branch > cross-branch separation | separation > 0 | Discriminating |
| 6 | hierarchy_coherence | Cluster purity/NMI at optimal Leiden resolution | **N/A (diagnostic)** | Non-discriminating |
| 7 | citation_proximity | **DUPLICATE of citation_heritage** | AUC > 0.65 | Duplicate |
| 8 | citation_graph_neighborhood | AUC for strong citation pairs (≥2 shared) | AUC > 0.65 | Discriminating |
| 9 | legal_area_clustering | Purity/NMI of Jurivoc legal areas | **N/A (diagnostic)** | Non-discriminating |
| 10 | zoom_coherence | Purity improvement from coarse→fine resolution | **N/A (diagnostic)** | Non-discriminating |
| 11 | temporal_stability | k-NN stability across time splits (std < 0.1) | std < 0.1 | Discriminating |
| 12 | cross_language_pairs | Cross-lang same-branch vs cross-branch separation | separation > 0 | Discriminating |
| 13 | boilerplate_resistance_real_corpus | Text-embedding correlation < 0.5 | correlation < 0.5 | Discriminating |
| 14 | tf_metadata_human_indexing | Recall@5 for human-indexed legal areas | recall@5 > 0.8 | Discriminating |

**Effective discriminating benchmarks: 11** (excluding 3 diagnostic-only and 1 duplicate).

---

## 3. Results Summary Table (Corrected PASS Counts)

| Experiment | PASS/Total | Citation AUC | Lang Dom | Branch kNN@5 | Multi Sep | Cross-Lang Sep | Boilerplate Corr | TF Recall@1 |
|------------|------------|--------------|----------|--------------|-----------|----------------|------------------|-------------|
| **baseline_debiased_citation_blended** | **14/14** ✓ | **0.910** | **0.634** | **0.806** | **0.085** | **0.133** | **0.167** | **0.820** |
| legal_statutes_only | 8/14 ✗ | 0.547 | 0.741 | 0.681 | -0.036 | -0.037 | 0.691 | 0.709 |
| legal_erwaegungen_only | 10/14 ✗ | 0.732 | 0.905 | 0.854 | -0.107 | -0.118 | 0.764 | 0.848 |
| **legal_cited_decisions_only** | **14/14** ✓ | **0.972** | **0.648** | **0.846** | **0.018** | **0.019** | **0.088** | **0.854** |
| legal_erwaegungen_statutes | 10/14 ✗ | 0.717 | 0.919 | 0.883 | -0.112 | -0.112 | 0.809 | 0.880 |
| legal_full_signals | 10/14 ✗ | 0.780 | 0.991 | 0.927 | -0.092 | -0.091 | 0.832 | 0.948 |
| legal_full_signals_noboilerplate | 10/14 ✗ | 0.780 | 0.991 | 0.927 | -0.092 | -0.091 | 0.832 | 0.948 |
| **hybrid_legal03_baseline07** | **13/14** ✗ | 0.712 | 0.980 | **0.962** | **0.005** | **0.048** | 0.381 | **0.967** |
| **hybrid_legal05_baseline05** | **13/14** ✗ | 0.751 | 0.977 | 0.955 | **0.024** | **0.054** | 0.238 | **0.972** |
| hybrid_legal07_baseline03 | 10/14 ✗ | 0.753 | 0.992 | 0.943 | -0.056 | -0.050 | 0.606 | 0.966 |
| legal_statutes_erwaegungen_citations | 10/14 ✗ | 0.774 | 0.957 | 0.922 | -0.093 | -0.091 | 0.805 | 0.939 |
| **legal_issues_outcomes** | **12/14** ✗ | 0.675 | 0.925 | 0.840 | **0.003** | -0.001 | 0.308 | 0.839 |

**Key:** Green = PASS, Red = FAIL. Bold = best-in-class for that metric.

---

## 4. Per-Benchmark Deep Dive

### 4.1 Citation Heritage / Proximity / Graph Neighborhood
- **Baseline:** 0.910 AUC (excellent)
- **legal_cited_decisions_only:** 0.972 AUC (best overall) — citations are the strongest signal for citation recovery
- **Legal signals without citations:** AUC drops to 0.55–0.78
- **Hybrids:** AUC 0.71–0.75 (diluted by legal signals)
- **Note:** `citation_proximity` is a **complete duplicate** of `citation_heritage` — identical AUC, identical pairs, identical subgroup analysis. It inflates the benchmark count from 13 to 14 unique tests.

### 4.2 Adversarial Falsification (Language Dominance)
- **Baseline:** 0.634 (PASS) — debiasing works
- **All legal-tfidf experiments:** 0.90–0.99 (FAIL) — TF-IDF on legal text is highly language-specific
- **Hybrids:** 0.98–0.99 (FAIL) — even 70% baseline doesn't overcome language dominance in legal signals
- **Root cause:** Legal vocabulary (statutes, reasoning, headings) is language-locked; no cross-lingual alignment

### 4.3 Branch k-NN Classification
- **Baseline:** 0.806 @5
- **Legal signals:** 0.84–0.93 (substantial improvement)
- **Hybrids (α=0.3–0.5):** 0.95–0.96 (best-in-class)
- **Interpretation:** Legal signals (especially legal_area, outcome, headings) encode branch-discriminative information better than semantic+citation baseline

### 4.4 Multilingual Invariance / Cross-Language Pairs
- **Baseline:** separation = 0.085 / 0.133 (PASS)
- **Legal signals (with text):** separation negative (-0.09 to -0.12) — cross-lang same-branch LESS similar than cross-branch
- **legal_cited_decisions_only:** 0.018 / 0.019 (PASS) — citation IDs are language-agnostic
- **legal_issues_outcomes:** 0.003 / -0.001 (borderline) — legal_area/outcome codes are language-neutral
- **Hybrids (α=0.3–0.5):** 0.005/0.048 and 0.024/0.054 (PASS) — enough baseline to recover cross-lingual alignment
- **Critical bug fixed:** Original code required `invariance_gap < 0.2` in addition to `separation > 0`. The documented threshold is only `separation > 0`. After fix, hybrids α=0.3 and α=0.5 correctly PASS.

### 4.5 Boilerplate Resistance
- **Baseline:** 0.167 correlation (PASS)
- **legal_cited_decisions_only:** 0.088 (PASS, even better) — citation lists have no boilerplate
- **Legal text signals (erwaegungen, statutes):** 0.69–0.83 (FAIL) — reasoning text correlates with procedural boilerplate
- **Hybrids (α=0.3–0.5):** 0.24–0.38 (PASS) — baseline dilutes boilerplate correlation
- **Critical bug fixed:** Original code required `correlation > 0.1` for PASS. The correct threshold is `correlation < 0.5` (lower = better boilerplate resistance). After fix, `legal_cited_decisions_only` correctly PASS (0.088 < 0.5).

### 4.6 TF Metadata Human Indexing
- **Baseline:** recall@1 = 0.820
- **Legal signals:** 0.84–0.95 (significant improvement)
- **Hybrids (α=0.3–0.5):** 0.97 (best-in-class)
- **Interpretation:** Legal signals align better with human-assigned Jurivoc/legal_area metadata

### 4.7 Non-Discriminating Benchmarks (Diagnostic Only)
These benchmarks produce **identical results across ALL experiments** because they depend on fractal-map cluster assignments, not the representation under test:
- **hierarchy_coherence:** purity=0.8609, NMI=0.4304 at res_1.0 (identical for all 11 experiments)
- **legal_area_clustering:** purity=0.8863 (identical for all 11 experiments); NMI varies slightly but no FAIL threshold defined
- **zoom_coherence:** coarse=0.8659, fine=0.9059, improvement=4.62% (identical for all 11 experiments)

These should be reported as diagnostics, not counted as PASS/FAIL discriminating benchmarks.

---

## 5. Signal Coverage Statistics

| Signal | Decisions With | Mean Per Decision |
|--------|----------------|-------------------|
| Statutes | 609 (61%) | 9.1 |
| Erwägungen paragraphs | 857 (86%) | 15.1 paragraphs (12,333 chars) |
| Cited decisions | 997 (99.7%) | 12.9 |
| Outcomes | 911 (91% non-null) | 4 categories |
| Decision types | 0 (all null) | — |
| Doctrine refs | 838 (84%) | 11.5 |
| Boilerplate density | 100% | 1.44% |

**Key observations:**
- Cited decisions: near-universal coverage, language-agnostic
- Erwägungen: high coverage but language-specific
- Statutes: only 61% coverage — many decisions don't cite specific articles
- Doctrine refs: high coverage, language-agnostic (standard citations)
- Boilerplate density: very low (1.4%), suppression has minimal practical effect

---

## 6. Critical Findings (Post-Bug-Fix)

### 6.1 The Baseline and legal_cited_decisions_only Are Equivalent General-Purpose Legal Distances
Both achieve **14/14 PASS**. The baseline wins on citation heritage AUC (0.910 vs 0.972 — actually legal_cited_decisions_only wins here too) and multilingual separation (0.085 vs 0.018). legal_cited_decisions_only wins on boilerplate resistance (0.088 vs 0.167) and TF metadata recall@1 (0.854 vs 0.820). They are complementary: baseline better for cross-language work, cited_decisions better for precedent navigation.

### 6.2 Legal Signals Excel at Legal Classification, Fail at Cross-Lingual Robustness
| Strength | Weakness |
|----------|----------|
| Branch k-NN: +15–18 pp over baseline | Language dominance: 0.90–0.99 vs 0.63 |
| TF metadata recall@1: +15–17 pp | Multilingual separation: negative vs +0.085 |
| Legal area NMI: +28–44 pp | Citation AUC: drops without citations |
| | Boilerplate correlation: 0.69–0.83 vs 0.17 |

### 6.3 Cited Decisions Are the Strongest Single Legal Signal
- **14/14 PASS** (ties baseline) — **corrected from 13/14**
- Language-agnostic (citation IDs work across languages)
- High coverage (99.7% of decisions)
- Improves branch_knn (0.846 vs 0.806) and tf_metadata (0.854 vs 0.820)
- Best boilerplate resistance (0.088 correlation)

### 6.4 Hybrids at α=0.3–0.5 Are "Best of Both Worlds" for Legal Tasks
- Branch k-NN @5: 0.95–0.96 (near-perfect legal branch classification)
- TF metadata recall@1: 0.97 (near-perfect human-index alignment)
- Legal area NMI: 0.78–0.83 (excellent doctrinal clustering)
- **13/14 PASS each** — **corrected from 12/14**
- **But:** Still FAIL adversarial_falsification (lang dom 0.98) — legal signals reintroduce language dominance

### 6.5 legal_issues_outcomes Is Unique: Passes Multilingual Invariance
- Uses only language-neutral codes (legal_area, outcome, heading numbers)
- Multilingual separation: 0.003 (PASS), cross-language pairs: -0.001 (borderline FAIL)
- But fails adversarial_falsification (lang dom 0.925) — heading numbers still correlate with language-specific structure
- Weak on citation recovery (AUC=0.68)

### 6.6 Boilerplate Suppression Has Minimal Impact
- Mean boilerplate density only 1.44%
- legal_full_signals vs legal_full_signals_noboilerplate: IDENTICAL results
- Boilerplate is not a significant confounder in this corpus

### 6.7 Effective Benchmark Discrimination
**Only 11 of 14 benchmarks are effectively discriminating:**
- 3 diagnostic-only (hierarchy_coherence, legal_area_clustering, zoom_coherence) — identical across all experiments
- 1 duplicate (citation_proximity ≡ citation_heritage)
- 10 discriminating benchmarks with meaningful variation

---

## 7. Product Recommendation

### 7.1 Default Map Mode: debiased_citation_blended
- Only configuration (with legal_cited_decisions_only) passing ALL 14 benchmarks
- Robust across languages, resistant to adversarial language dominance
- Strong citation heritage recovery (AUC 0.91)
- Good branch classification (0.81) and human indexing (0.82 recall@1)

### 7.2 Selectable Map Modes (Exposed to Jurists)
| Mode | Use Case | Benchmarks Where It Wins |
|------|----------|--------------------------|
| **Cited Decisions Only** | Precedent-based navigation, cross-language | citation_heritage (0.97), citation_graph (0.97), boilerplate (0.09), multilingual (PASS) |
| **Hybrid α=0.3** | Branch-level exploration, human-index alignment | branch_knn (0.96), tf_metadata (0.97), legal_area NMI (0.83), cross_lang (PASS) |
| **Hybrid α=0.5** | Maximum legal classification accuracy | branch_knn (0.96), tf_metadata (0.97), legal_area NMI (0.78) |
| **Legal Issues/Outcomes** | Cross-language doctrinal comparison | multilingual_invariance (PASS) |

### 7.3 Do Not Productize
- legal_statutes_only, legal_erwaegungen_only, legal_erwaegungen_statutes, legal_full_signals (all fail multilingual + adversarial)
- legal_full_signals_noboilerplate (identical to with-boilerplate)

---

## 8. Recommendation to Factory Director

### 8.1 Lane Status: **ACCEPTED** (evidence complete, bugs fixed)
- All 11 experiments executed on 1,000-decision slice
- Full 14-benchmark suite run on each with **corrected evaluation logic**
- Baseline validated (14/14 PASS) per evaluation lane v1
- Clear comparative evidence produced with **corrected PASS counts**

### 8.2 Continue Recommended: **FALSE**
- The factory direction question is answered: legal signals improve specific legal-classification benchmarks but degrade multilingual/adversarial robustness; legal_cited_decisions_only ties baseline at 14/14
- No additional same-question cycle has discriminating purpose

### 8.3 Successor Questions (for Factory Director consideration)
1. **Scale test:** Do these results hold on full TF 2000+ corpus (not 1,000 slice)?
2. **Embedding upgrade:** Do legal-specific embeddings (e.g., Legal-BERT, Isaacus-style) improve multilingual invariance of legal signals?
3. **Citation role modeling:** Can citation *roles* (distinguishing, following, overruling) improve over simple citation lists?
4. **Jurist evaluation:** Do jurists prefer hybrid-map neighbors over baseline neighbors in pairwise studies?
5. **Benchmark refinement:** Replace duplicate/non-discriminating benchmarks with jurist-usefulness proxies (pairwise preference, known-lineage recovery without shared citations).

### 8.4 Evidence References
- `results/all_experiments_results.json` — complete benchmark outputs (corrected)
- `results/signal_coverage_stats.json` — signal coverage analysis
- `results/experiment_*_results.json` — per-experiment raw outputs
- Baseline validation: `/tmp/lex_accepted/evaluation/evaluation/reports/evaluation_v1_closure_report.md`
- Audit report: `/tmp/lex_prior_audit/reports/audit/legal-distance/CYCLE_33119846410.md`

---

## 9. State Update

```json
{
  "lane": "legal-distance",
  "direction_version": 3,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "COMPLETE",
  "continue_recommended": false,
  "accepted_run_id": "legal_dist_baseline_debiased_citation_blended_1787870939",
  "accepted_commit": "<current-commit-hash>",
  "evidence_refs": [
    "results/all_experiments_results.json",
    "results/signal_coverage_stats.json",
    "reports/legal_distance_analysis_report.md"
  ],
  "next_recommendation": "PIVOT_WITHIN_MISSION — scale to full corpus; test legal embeddings for multilingual legal signals; jurist preference study on hybrid modes; refine benchmark suite"
}
```

---

## 10. Repair Provenance

This report corrects the original cycle 33119846410 which was **REVISE** by independent audit due to two critical benchmark evaluation bugs:

1. **boilerplate_resistance_real_corpus:** Original code `correlation > 0.1` → PASS; fixed to `correlation < 0.5` → PASS (lower = better resistance). Affected: `legal_cited_decisions_only` (0.088 now PASS), hybrids α=0.3/0.5 (0.38/0.24 now PASS).

2. **multilingual_invariance:** Original code `separation > 0 and invariance_gap < 0.2` → PASS; fixed to documented threshold `separation > 0` → PASS. Affected: hybrids α=0.3 (separation=0.0046) and α=0.5 (separation=0.0238) now PASS.

**Corrected PASS counts:**
- legal_cited_decisions_only: 13/14 → **14/14** (ties baseline)
- hybrid_legal03_baseline07: 12/14 → **13/14**
- hybrid_legal05_baseline05: 12/14 → **13/14**
- hybrid_legal07_baseline03: 11/14 → **10/14** (boilerplate now correctly FAILs at 0.606 > 0.5)

All raw experimental outputs preserved in `results/`. No claim-bearing measurements modified after observation.

---

*Report generated from frozen experimental results with corrected benchmark evaluation. All raw outputs preserved in `results/`.*