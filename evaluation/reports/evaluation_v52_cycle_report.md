# Evaluation Lane v52 Cycle Verification Report

**Date**: 2026-09-25T23:30:00Z  
**Factory Direction Version**: 27  
**Lane Status**: BLOCKED_ON_DEPENDENCIES  
**Evidence Tier**: REPRODUCED  
**Continue Recommended**: false (for TF-IDF family)

---

## Executive Summary

The evaluation lane has completed its **v52 verification cycle**. All three machine-executable sub-questions for the TF-IDF family are **CONFIRMED COMPLETE** at 174k scale with frozen thresholds and no tuning after results. The lane remains correctly **BLOCKED_ON_DEPENDENCIES** awaiting legal-distance 174k dense embeddings (center_projected, metric learning, hybrid objectives, citation roles, linear hybrids).

**Key Finding**: Evaluation infrastructure is **fully operational and ready for auto-evaluation** when dense embeddings land. The monitor script (`monitor_and_evaluate_174k.py`) actively scans the legal-distance accepted state (check #91) and will automatically execute the full frozen v25 protocol (12-benchmark suite + citation_heritage + v17b label normalization) for each newly detected representation via `run_formal_suite_v25()`.

---

## Verification Results

### 1. 174k Formal Suite (run_174k_formal_suite.py) — RE-VERIFIED OPERATIONAL
- **HNSW Artifact Fix CONFIRMED**: Exact k-NN on fixed stratified subsample (n=2000, decisions with known branch) for adversarial/cross-language/jurist benchmarks
- **All 8 TF-IDF representations evaluated** at 174k scale (173,963 decisions, 128-dim)
- **Results match v25 frozen suite exactly**:
  - **5/8 PASS both adversarial gates**: `cited_decisions_tfidf`, `cited_outcome_hybrid_0.5`, `cited_outcome_hybrid_0.7`, `outcome_tfidf`, `regeste_tfidf`
  - **3 FAIL** (language dominance ~1.0): `full_text_tfidf_light`, `regeste_full_text_hybrid_0.5`, `regeste_full_text_hybrid_0.7`
- **BEST representation**: `cited_decisions_tfidf_outcome_hybrid_0.5` (LangDom=0.5164 PASS, Jurist=0.8055 PASS)
- **PRODUCTION DEFAULT CONFIRMED**: `cited_outcome_hybrid_0.7` (LangDom=0.5238 PASS, Jurist=0.7975 PASS) — zero-shot TF-IDF, no GPU required
- **Config hash**: `b51701f5a9c11692`, seed=42, factory direction v27

### 2. v25_174k Formal Suite Runner — CONFIRMED OPERATIONAL
- **Config hash**: `4323f833fa72366a` (frozen)
- All 8 TF-IDF representations fully evaluated at 173,963 decisions
- `_suite_summary.json` verified with 8 entries
- Production default `cited_outcome_hybrid_0.7`: 6 PASS / 5 FAIL / 1 SKIP
- Citation heritage AUC=0.9605, nn_citation_rate@10=0.490

### 3. Citation Heritage Benchmark (validate_citation_heritage_174k.py) — INFRASTRUCTURE RE-VERIFIED
- Citation graph validated from `resolved_full`: 2,019/2,105 resolved = **95.9%**
- 174 decisions with outgoing citations in 174k corpus (0.1%)
- 924 resolved citations map to 174k corpus decisions
- **1,020 positive pairs** (direct + shared citations) + **1,020 negative pairs** sampled
- Frozen pair pool ready: `citation_pairs_174k_full.json` (137,314 pairs)
- Benchmark ready for 174k embeddings when available

### 4. v17b Label Normalization Test — OPERATIONAL AT 174K
- 213 raw unique legal_area labels → 163 normalized (23.5% reduction)
- 49.3% of labels changed (85,819 decisions)
- 32 cross-lingual canonical concepts
- **PARTIAL generalization CONFIRMED**:
  - 2/8 reps within ≤10% worsening rule: `cited_decisions_tfidf`, `regeste_tfidf`
  - 6/8 exceed on hierarchy NMI (-10.8% to -27.6%)
  - 1/8 exceeds on zoom_coherence: `cited_outcome_hybrid_0.5` (-16.0%)
- Normalized hierarchy purity gains: 1.5-1.6x for citation-based reps
- Even normalized, best hierarchy purity=0.47 < 0.7 threshold (corpus/label limitation)

### 5. Legal-Distance Dense Embeddings — IN PROGRESS
- **Year-split computation**: 11/26 years complete (2000-2010) in checkpoints
- **Decisions processed**: ~62,645 (~36% of 173,963)
- **Filesystem verified**: `embeddings_YYYY.npy` + `metadata_YYYY.json` for years 2000-2010
- **Progress.json**: `completed_years: [2000-2010]`, `failed_years: []`
- **Final concatenated embeddings** await years 2011-2025
- **GitHub run**: 36096850301 IN_PROGRESS
- **Monitor scans**: 174k_dense_embeddings root directory only (excludes checkpoints subdirectory)

### 6. Evaluation Infrastructure — END-TO-END VERIFIED
| Component | Status | Config Hash |
|-----------|--------|-------------|
| `run_174k_formal_suite.py` | OPERATIONAL | `b51701f5a9c11692` |
| `v25_174k_formal_suite` runner | OPERATIONAL | `4323f833fa72366a` |
| `validate_citation_heritage_174k.py` | OPERATIONAL | `4047da047fb339c1` |
| v17b label normalization | OPERATIONAL | frozen canonical map |
| `monitor_and_evaluate_174k.py` | ACTIVE (91 checks) | enhanced with `run_formal_suite_v25()` |
| HNSW backend (hnswlib) | OPERATIONAL on GitHub runners | sklearn exact fallback for <10k |
| Scalable NN (scalable_nn.py) | OPERATIONAL | batched adversarial benchmarks |

All config hashes **frozen and verified** against accepted dense embeddings from legal-distance (v5-v6) with exact metric match.

### 7. Monitor Auto-Evaluation Pipeline — READY
- `monitor_and_evaluate_174k.py` enhanced with `run_formal_suite_v25()` function
- Copies new embedding `.npy` files to v25 suite embeddings directory
- Invokes full frozen v25 protocol for each newly detected representation
- Scan targets: 174k_dense_embeddings root directory for final concatenated embeddings
- **Check #91 completed** — no dense embeddings detected yet

### 8. Jurist Human Study — BLOCKED
- External dependency: 5-10 Swiss jurists recruitment by repository owner
- Framework ready per v25 protocol
- Does not block machine-executable suite

---

## TF-IDF Family — COMPLETE (No Additional Cycle Justified)

Per Research Protocol: **continue_recommended=false** for TF-IDF family.

**All three machine-executable sub-questions COMPLETE**:
1. ✅ 12-benchmark formal suite at 174k scale (frozen harness v3 thresholds)
2. ✅ Citation heritage benchmark validated (137,314 frozen pairs)
3. ✅ v17b label normalization generalization tested

**Negative results preserved** (corpus/label limitations, not representation defects):
- Universal FAIL: `hierarchy_coherence` (purity 0.08-0.47 < 0.7)
- Universal FAIL: `legal_area_clustering` (purity 0.003-0.08 < 0.5)
- Universal FAIL: `temporal_stability`, `boilerplate_resistance` at 174k scale

---

## Evidence Preservation

All artifacts preserved and versioned:
- v25 suite results: `results/evaluation/v25_174k_formal_suite/`
- Citation heritage: `results/174k_citation_heritage/`
- v17b analysis: `results/174k_label_analysis/`
- Formal suite: `evaluation/results/174k/formal_suite/`
- Monitor state: `evaluation/state/monitor_174k_state.json` (91 checks)
- Config hashes: frozen and verified

---

## Next Steps

1. **Await legal-distance 174k dense embeddings** (years 2011-2025 completion)
2. **Monitor will auto-evaluate** when final concatenated embeddings land in `174k_dense_embeddings/` root
3. **No further same-question cycles** for TF-IDF family (continue_recommended=false)
4. **Jurist human study** remains external dependency

---

## Configuration Hashes (Frozen)

| Component | Hash |
|-----------|------|
| v3 Harness | `a31c443a9b0e992e` |
| v16 Benchmark Suite | `4323f833fa72366a` |
| Full Corpus Evaluation | `4047da047fb339c1` |
| Formal Suite (HNSW fix) | `b51701f5a9c11692` |
| Global Seed | 42 |
| Factory Direction | v27 |

---

**Status**: TF-IDF FAMILY COMPLETE — ALL INFRASTRUCTURE OPERATIONAL — MONITOR ACTIVE (91 checks) — AWAITING LEGAL-DISTANCE 174K DENSE EMBEDDINGS (year-split 11/26 years in checkpoints, 42% complete) — JURIST STUDY BLOCKED — AUTO-EVALUATION PIPELINE READY