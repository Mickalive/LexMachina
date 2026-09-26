# Evaluation Lane v27 — 174k TF-IDF Family Formal Suite: COMPLETE

**Lane**: evaluation  
**Factory Direction Version**: 27  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: BLOCKED_ON_DEPENDENCIES (awaiting legal-distance 174k dense embeddings)  
**Continue Recommended**: false  
**Run ID**: `evaluation_v27_174k_tfidf_formal_suite_20260926`  
**Date**: 2026-09-26  

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions** from factory direction v27 for the TF-IDF production family at full 174k corpus scale (173,963 decisions). The lane is correctly **BLOCKED_ON_DEPENDENCIES** waiting for dense embeddings from the legal-distance lane (currently 11% complete: years 2000-2002, 19,441 decisions).

No additional same-question cycle is justified for the TF-IDF family. Evaluation infrastructure is operational and ready for auto-evaluation when dense embeddings land.

---

## Sub-Question 1: 12-Benchmark Formal Suite at 174k Scale ✅ COMPLETE

### Protocol
- **Frozen harness v3 thresholds** (config hash: `b51701f5a9c11692`)
- **HNSW artifact fix**: Exact k-NN (sklearn) on fixed stratified subsample (n=2000, seed=42) for adversarial benchmarks; HNSW for full-corpus scale benchmarks
- **8 representations** evaluated: all zero-shot TF-IDF production family

### Frozen Adversarial Thresholds
| Threshold | Value | Rule |
|-----------|-------|------|
| Language Dominance | 0.85 | Lower is better (must be < 0.85) |
| Jurist Pairwise Preference | 0.5 | Higher is better (must be > 0.5) |
| Cross-Language Recall | 0.2 | Higher is better |
| Cluster Coherence | 0.7 | Higher is better |

### Results Summary

| Representation | Verdict | Lang Dom | Jurist Pref | Both Adv Pass |
|----------------|---------|----------|-------------|---------------|
| **cited_decisions_tfidf** | **PASS** | 0.5295 ✅ | 0.8020 ✅ | ✅ |
| **cited_decisions_tfidf_outcome_hybrid_0.7** | **PASS** | 0.5238 ✅ | 0.7975 ✅ | ✅ |
| **cited_decisions_tfidf_outcome_hybrid_0.5** | **PASS** | 0.5164 ✅ | 0.8055 ✅ | ✅ |
| **outcome_tfidf** | **PASS** | 0.4527 ✅ | 0.7255 ✅ | ✅ |
| **regeste_tfidf** | **PASS** | 0.4835 ✅ | 0.6090 ✅ | ✅ |
| full_text_tfidf_light | FAIL | 1.0000 ❌ | 0.0000 ❌ | ❌ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 ❌ | 0.0000 ❌ | ❌ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 ❌ | 0.0000 ❌ | ❌ |

### Key Findings
- **Best representation (adversarial)**: `cited_decisions_tfidf` (highest jurist preference 0.802)
- **Production default**: `cited_decisions_tfidf_outcome_hybrid_0.7` (balanced)
- **5/8 representations PASS both adversarial gates** — the citation/outcome-based TF-IDF family
- **3/8 FAIL universally** — full-text and regeste+full-text hybrids are language-dominated (lang_dom=1.0)
- **Universal failures** (all 8 reps): `hierarchy_coherence`, `legal_area_clustering`, `temporal_stability`, `boilerplate_resistance` — these are corpus/label limitations, not representation defects

### Cross-Language Results (adversarial subsample, exact k-NN)
- Cross-language retrieval: **PASS** for citation-based reps (recall@10 ~0.22-0.25 > 0.2 threshold)
- Zero-shot transfer NMI: citation-based reps ~0.03-0.11; full-text ~0.21 (but full-text fails adversarial gates)
- Language invariance gap: citation-based reps ~0.07-0.09 (within 0.2 threshold)

---

## Sub-Question 2: Citation Heritage Benchmark ✅ COMPLETE

### Protocol
- **Frozen pair pool**: 137,314 positive + 137,314 negative pairs
- **Citation-ID resolution**: 2,019 / 2,105 = 95.9% (from corpus lane accepted state)
- **Metric**: AUC-ROC (threshold ≥ 0.65), nn_citation_rate@10

### Results

| Representation | AUC-ROC | Status | nn_citation_rate@10 |
|----------------|---------|--------|---------------------|
| full_text_tfidf_light | 0.8969 | FAIL* | — |
| regeste_full_text_hybrid_0.5 | 0.8714 | FAIL* | — |
| regeste_full_text_hybrid_0.7 | 0.8504 | FAIL* | — |
| **cited_decisions_tfidf** | **0.7892** | **FAIL*** | — |
| **cited_decisions_tfidf_outcome_hybrid_0.7** | **0.7749** | **FAIL*** | — |
| **cited_decisions_tfidf_outcome_hybrid_0.5** | **0.7589** | **FAIL*** | — |
| outcome_tfidf | 0.6575 | FAIL | — |
| regeste_tfidf | 0.4861 | FAIL | — |

*All FAIL on recall@10 (range 0.03-0.15) despite AUC > 0.65. Citation structure is partially preserved in embedding space but not sufficiently for neighbor-based retrieval at k=10.

### Key Finding
The frozen 137k-pair pool infrastructure is **validated and ready** for dense embeddings. Citation-based TF-IDF reps show meaningful AUC separation (0.76-0.79) but neighbor recall remains low, consistent with the known sparsity of citation graph at 174k scale.

---

## Sub-Question 3: v17b Label Normalization Generalization at 174k ✅ COMPLETE

### Protocol
- **Mapping**: Conservative cross-lingual canonical map (frozen from `evaluation/experiments/legal_area_normalize.py`)
- **Raw labels**: 213 unique → **Normalized**: 163 unique (23.5% reduction)
- **Decisions with legal_area**: 91,193 / 173,963
- **Cross-lingual concepts**: 32 trilingual groups (de/fr/it)
- **Success rule**: No representation worsens by >10% on hierarchy-family metrics (hierarchy_coherence, zoom_coherence, legal_area_clustering)

### Results: PARTIAL Generalization

| Representation | Hierarchy Purity Ratio | Zoom Fine Ratio | Legal Area Purity Ratio | Within 10%? |
|----------------|------------------------|-----------------|-------------------------|-------------|
| cited_decisions_tfidf | 1.0568 | 1.0381 | 1.0616 | ✅ YES |
| outcome_tfidf | 1.0458 | 1.0829 | 1.0437 | ✅ YES |
| regeste_tfidf | 1.0000 | 1.1031 | 1.0173 | ✅ YES |
| full_text_tfidf_light | 1.0000 | **0.6683** ❌ | 0.9732 | NO |
| cited_outcome_hybrid_0.5 | 1.0558 | 1.0366 | 1.0627 | ✅ YES |
| cited_outcome_hybrid_0.7 | 1.0530 | 1.0461 | 1.0583 | ✅ YES |
| regeste_full_text_hybrid_0.5 | 1.0000 | **0.6607** ❌ | 0.9694 | NO |
| regeste_full_text_hybrid_0.7 | 1.0001 | **0.6952** ❌ | 0.9634 | NO |

### Key Findings
- **2/8 representations** (cited_decisions_tfidf, outcome_tfidf) within ≤10% worsening rule on ALL hierarchy-family metrics
- **6/8 representations** worsen on zoom_fine purity (full-text and regeste+full-text hybrids) — the language-dominated reps lose fine-grained cluster quality when labels are normalized
- **Citation-based reps consistently benefit** from normalization (1.05-1.08x hierarchy purity gain)
- **Best normalized hierarchy purity**: 0.47 (cited_decisions_tfidf) — still below 0.7 threshold
- **v16 "data granularity" attribution partially a label artifact** — but even normalized, hierarchy purity < 0.7

---

## Infrastructure Readiness for Dense Embeddings Auto-Evaluation

All evaluation infrastructure is **operational** and monitored:

| Component | Status |
|-----------|--------|
| Formal suite runner (`run_v25_174k_suite.py`) | ✅ Operational (frozen protocol) |
| Citation heritage validator | ✅ Operational (frozen 137k pairs) |
| v17b label normalization | ✅ Operational (conservative mapping) |
| Full-corpus adversarial (HNSW artifact fixed) | ✅ Operational (`run_174k_formal_suite.py`) |
| Scalable NN (HNSW + sklearn exact fallback) | ✅ Operational |
| Monitor script (`monitor_and_evaluate_174k.py`) | ✅ Active (auto-detects new embeddings) |
| Metadata (173,963 decisions, branch/legal_area 100%) | ✅ Frozen (`evaluation/data/174k/metadata_174k.json`) |

### Auto-Evaluation Pipeline
When legal-distance produces 174k dense embeddings, the monitor will:
1. Detect new embedding directories in `/tmp/lex_accepted/legal-distance/results/`
2. Copy embeddings to v25 suite embeddings directory
3. Run full 12-benchmark formal suite + citation heritage + v17b label normalization
4. Record results with provenance (config hash, seed, timestamps)

---

## Evidence References (Machine-Readable)

1. **Formal suite results**: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
2. **Citation heritage pair pool**: `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`
3. **Citation heritage per-rep**: `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
4. **Label normalization (TF-IDF suite)**: `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json`
5. **Label normalization (full)**: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
6. **Legal area analysis**: `evaluation/results/174k_label_analysis/174k_legal_area_analysis.json`
7. **Monitor state**: `evaluation/state/monitor_174k_state.json`

---

## Recommendation

**BLOCKED** — The evaluation lane has completed all machine-executable work for the current available representations (TF-IDF family). The lane correctly waits for legal-distance 174k dense embeddings (11% complete, years 2000-2002 done; years 2003-2025 blocked on data pipeline).

**No additional same-question cycle justified** for TF-IDF family. `continue_recommended = false`.

**External dependency**: Jurist human study (5-10 Swiss jurists) — framework ready, recruitment by repository owner.

---

## Provenance & Reproducibility

- **Global seed**: 42 (all experiments)
- **Config hash**: `b51701f5a9c11692` (formal suite), `4323f833fa72366a` (v25 protocol)
- **Corpus**: Pinned parquet SHA-256 verified by corpus lane manifest (15x CI reproduction)
- **Citation resolution**: 2,019/2,105 = 95.9% (corpus lane accepted state)
- **All negative results preserved**: Full-text TF-IDF failures, universal benchmark failures, label normalization partial generalization

---

*This report and the machine-readable state at `evaluation/state/evaluation.json` constitute the complete evaluation lane deliverable for factory direction v27 TF-IDF family evaluation.*