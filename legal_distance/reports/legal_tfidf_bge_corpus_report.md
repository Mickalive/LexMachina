# Legal TF-IDF from bge_ Corpus (Published Decisions) - Evaluation Report

**Lane**: legal-distance  
**Factory Direction**: v29  
**Run ID**: legal_tfidf_bge_corpus_20261002  
**Date**: 2026-10-02  
**Evidence Tier**: EXPLORATORY

---

## Executive Summary

Tested whether **legally structured signals** (statutes, reasoning paragraphs, cited decisions, legal areas, outcomes, doctrine citations) extracted from the **bge_ corpus (published BGE volumes only, ~6,243 decisions)** can produce TF-IDF representations that outperform the validated `debiased_citation_blended` baseline on the adversarial benchmark suite.

**Result: NEGATIVE** — All legal TF-IDF variants **FAIL** the full adversarial suite (6-8/14 benchmarks PASS vs 14/14 for baseline). The fundamental issue is a **corpus mismatch**: signals extracted from bge_ (published decisions) do not transfer to the evaluation corpus (bger_ 1000-decision slice from 2024).

---

## Experimental Setup

### Corpus
- **Signal source**: bge_ corpus (published BGE volumes), years 2000-2021
- **Decisions with signals**: 6,243 (from bge_2000.jsonl through bge_2021.jsonl)
- **Evaluation corpus**: bger_ 1000-decision slice (from 2024, different ID system)
- **Baseline**: `debiased_citation_blended` (n_pca=1, alpha=0.7) on 1000 decisions

### Legal Signals Extracted
| Signal | Decisions With | Mean Per Decision |
|--------|---------------|-------------------|
| Statutes | 6,024 (96%) | 12.4 |
| Erwägungen paragraphs | 3,974 (64%) | 7.5 paragraphs |
| Cited decisions | 4 (0.06%) | 0.007 |
| Legal area | 6,243 (100%) | 1.0 |
| Outcome | 0 (all null) | 0 |
| Doctrine refs | 5,936 (95%) | 12.5 |
| Boilerplate density | 6,243 (100%) | 0.022% |

**Critical gaps**: Almost no cited decisions, no outcomes, limited Erwägungen coverage.

---

## Benchmark Results Summary

| Experiment | PASS/14 | Citation AUC | Lang Dom | Branch kNN@5 | Key Failure Modes |
|------------|---------|--------------|----------|--------------|-------------------|
| **Baseline (debiased_citation_blended)** | **14/14** ✓ | **0.9089** | **0.638** | **0.8018** | — |
| legal_statutes_only | 7/14 ✗ | 0.5034 | 0.4892 | 0.3944 | Citation heritage, branch kNN, multilingual, cross-lang |
| legal_erwaegungen_only | 8/14 ✗ | 0.4913 | 0.4905 | 0.3353 | Citation heritage, branch kNN, cross-lang |
| legal_cited_decisions_only | 6/14 ✗ | 0.5000 | 0.5002 | 0.2623 | Citation heritage, branch kNN, collapse, multilingual, cross-lang |
| legal_erwaegungen_statutes | 7/14 ✗ | 0.4985 | 0.4962 | 0.3724 | Citation heritage, branch kNN, multilingual, cross-lang |
| legal_full_signals | 7/14 ✗ | 0.5147 | 0.4967 | 0.3724 | Citation heritage, branch kNN, multilingual, cross-lang |
| legal_full_signals_noboilerplate | 7/14 ✗ | 0.5147 | 0.4967 | 0.3724 | Same as above |
| legal_statutes_erwaegungen_citations | 7/14 ✗ | 0.4985 | 0.4959 | 0.3724 | Citation heritage, branch kNN, multilingual, cross-lang |
| legal_issues_outcomes | 6/14 ✗ | 0.5003 | 0.4984 | 0.2653 | Citation heritage, branch kNN, collapse, multilingual, cross-lang |

---

## Key Findings

### 1. **Legal TF-IDF FAILS Citation Heritage (AUC ≈ 0.5)**
All legal signal variants achieve AUC ~0.5 (random baseline), while baseline achieves 0.9089. Legal signals from published decisions **do not capture citation proximity** in the full corpus.

### 2. **Legal TF-IDF FAILS Branch Classification (kNN@5 ≈ 0.26-0.39)**
Baseline achieves 0.8018. Legal signals cannot classify decisions into court branches (zivilrecht, strafrecht, etc.).

### 3. **Legal TF-IDF PASSES Language Dominance (Lang Dom ≈ 0.49-0.50)**
**Positive signal**: All legal TF-IDF variants have low language dominance (threshold: <0.85), meaning they are **not language-dominated** — unlike full-text TF-IDF (Lang Dom ≈ 0.99). This confirms legal signals are **cross-lingual by nature**.

### 4. **Legal TF-IDF FAILS Multilingual Invariance & Cross-Language Pairs**
Despite low language dominance, separation metrics are negative/near-zero. Cross-language legal equivalents are not recovered.

### 5. **Boilerplate Suppression Has No Effect**
`legal_full_signals` vs `legal_full_signals_noboilerplate` are identical (boilerplate density is negligible in BGE volumes: 0.022%).

### 6. **Hierarchy Coherence, Legal Area Clustering, Zoom Coherence PASS**
These benchmarks depend only on metadata alignment, not embedding quality. All representations PASS because they inherit the baseline's metadata structure.

---

## Root Cause Analysis

### Corpus Mismatch (Fundamental Blocker)
- **bge_ corpus**: Published BGE volumes only (~300-700 decisions/year), IDs like `bge_BGE_126_I_122`
- **bger_ corpus**: All decisions including unpublished (~4,000-7,800 decisions/year), IDs like `bger_4P.253_1999`
- **No ID mapping exists** between the two systems
- Dense embeddings (144k) were computed from bger_ corpus but **full text no longer available**
- The 1000-decision evaluation slice is from bger_ 2024

### Signal Coverage Deficits in bge_ Corpus
| Signal | Coverage | Problem |
|--------|----------|---------|
| Cited decisions | 0.06% | BGE volumes strip citation metadata |
| Outcomes | 0% | Not recorded in bge_ |
| Erwägungen | 64% | Section extraction imperfect |
| Statutes/Doctrine | 95%+ | Good coverage but not discriminative alone |

---

## Implications for Legal Distance Lane

### What This Experiment Proves
1. **Legal signals from published-only corpus don't generalize** to full corpus
2. **Citation signals are essential** for citation heritage (TF-IDF on cited decisions alone FAILS because coverage is near-zero)
3. **Statutes + doctrine alone are insufficient** for legal similarity (AUC ~0.5)
4. **Reasoning text (Erwägungen) alone is insufficient** (AUC ~0.49)

### What Remains Unexplored (Blocked)
- Legal signals from **full bger_ corpus** (144k decisions) — **no full text available**
- Linear combinations of **legal TF-IDF + dense embeddings** at 144k scale — **no aligned signals**
- Section-specific embeddings (Sachverhalt/Erwägungen/Dispositiv) at scale — **no section extraction at scale**
- Citation role embeddings — **no citation metadata at scale**

---

## Recommendation: PIVOT_WITHIN_MISSION

**No further cycles on bge_ corpus legal TF-IDF.** The corpus mismatch is fundamental and unfixable without upstream corpus-lane coordination.

### Required Upstream Fixes (Corpus Lane)
1. **Provide bger_ full-text corpus** for years 2000-2026 (or at least 2000-2021 matching dense embeddings)
2. **Create bge_ ↔ bger_ ID mapping** to align published/unpublished decisions
3. **Enable section extraction at 174k scale** (Sachverhalt/Erwägungen/Dispositiv)

### Alternative Paths (Within Current Constraints)
1. **Test dense embedding linear combinations** at 144k (already done: linear_citation_concat PASS at 19yr/22yr but below TF-IDF baseline)
2. **Test metric learning on dense embeddings** at 144k (v9/v10/v11 experiments exist)
3. **Run v8 holdout validation** on existing representations (already done: minimal leakage confirmed)
4. **Focus on citation-heritage recovery** by dense embeddings (NEW FINDING: AUC 0.79-0.85 at 21-22yr)

---

## Evidence Artifacts

| Artifact | Path |
|----------|------|
| Legal signals (22 years) | `legal_distance/results/174k_dense_embeddings/legal_signals_144k/legal_signals_YYYY.jsonl` |
| Signal coverage stats | `legal_distance/results/174k_dense_embeddings/legal_signals_144k/signal_coverage_stats_144k.json` |
| Experiment results | `legal_distance/results/174k_dense_embeddings/legal_tfidf_bge/all_experiments_results.json` |
| Individual experiment results | `legal_distance/results/174k_dense_embeddings/legal_tfidf_bge/experiment_*_results.json` |

---

## Conclusion

**Legal TF-IDF from bge_ corpus is not a viable path** for improving legal distance at scale. The published-decisions-only corpus lacks the citation density, outcome data, and coverage needed to capture legal proximity in the full corpus.

The **two-mode tradeoff** observed at all scales remains:
- **Citation/Outcome mode** (TF-IDF hybrids): JP ≈ 0.73, Lang Dom ≈ 0.48
- **Semantic mode** (center_projected): JP ≈ 0.05-0.40, Lang Dom ≈ 0.84-0.98  
- **Hybrid mode** (linear combinations): JP ≈ 0.54, Lang Dom ≈ 0.77

**Dense embeddings recover citation heritage at scale (AUC 0.79-0.85)** — a novel finding at 21-22yr scale — but fail the jurist gate due to language dominance.

**Next cycle should focus on**: (a) corpus-lane coordination for bger_ full text, or (b) metric learning / citation role integration on existing 144k dense embeddings.

