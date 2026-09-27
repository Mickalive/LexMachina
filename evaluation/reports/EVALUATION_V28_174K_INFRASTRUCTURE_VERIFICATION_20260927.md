# Evaluation Lane v28 — Infrastructure Verification & Status Report

**Date**: 2026-09-27  
**Factory Direction**: v28  
**Lane Status**: BLOCKED_ON_DEPENDENCIES  
**Evidence Tier**: REPRODUCED  
**Cycle**: Infrastructure verification & readiness confirmation  

---

## Executive Summary

The evaluation lane has **completed all work possible at current factory direction v28**. The TF-IDF family (8 representations) formal suite, citation heritage benchmark, and v17b label normalization testing are **COMPLETE at 174k scale** with verified reproducibility. The lane is correctly **BLOCKED_ON_DEPENDENCIES** awaiting 174k-scale dense embeddings, citation role embeddings, and linear hybrid embeddings from the legal-distance lane.

**No additional same-question cycle is justified** without new 174k representations landing in accepted state.

---

## Completed Work (All Verified REPRODUCED)

### 1. TF-IDF Family Formal Suite at 174k Scale ✅
- **Script**: `run_174k_formal_suite.py` (frozen harness v3, HNSW artifact fixed via exact k-NN on stratified subsample n=2000)
- **Config hash**: `b51701f5a9c11692` (frozen, matches evaluation state)
- **Representations evaluated**: 8 TF-IDF family members
- **Adversarial gates**: Language dominance threshold 0.85, Jurist pairwise threshold 0.5

| Representation | Verdict | LangDom | Jurist Pref | Both Pass |
|---------------|---------|---------|-------------|-----------|
| cited_decisions_tfidf | **PASS** | 0.5295 | 0.8010 | ✅ |
| cited_decisions_tfidf_outcome_hybrid_0.5 | **PASS** | 0.5167 | 0.8050 | ✅ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | **PASS** | 0.5237 | 0.8000 | ✅ |
| outcome_tfidf | **PASS** | 0.4920 | 0.7250 | ✅ |
| regeste_tfidf | **PASS** | 0.5240 | 0.5775 | ✅ |
| full_text_tfidf_light | FAIL | 1.0000 | 0.0000 | ❌ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 | 0.0000 | ❌ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 | 0.0000 | ❌ |

**Production default**: `cited_decisions_tfidf_outcome_hybrid_0.5` — **PASS** (LangDom=0.5164, JuristPref=0.8055)

**Key finding**: Fundamental two-mode tradeoff persists:
- **Citation-based signals** (cited_decisions_tfidf family): Pass adversarial gates, fail branch/tf_metadata/hierarchy
- **Text-based signals** (full_text_tfidf, regeste hybrids): Pass branch/tf_metadata, FAIL adversarial (LangDom ~0.999)

### 2. Citation Heritage Benchmark at 174k ✅
- **Pair pool**: 2,040 frozen pairs (1,020 positive direct+shared citations, 1,020 negative, balanced, seed=42)
- **Citation-ID resolution**: 2,019/2,105 resolved (95.9%)
- **Result**: **ALL 8 TF-IDF representations FAIL** recall@10 threshold
- **AUC range**: ~0.50-0.53 (no better than random)

### 3. v17b Label Normalization at 174k ✅
- **Labels normalized**: 85,819 fine-grained legal_area labels (214 → 164 unique areas)
- **Differential effect CONFIRMED** across all 8 TF-IDF representations:
  - **Citation-based reps**: IMPROVE hierarchy_coherence (1.04-1.10x), zoom_fine (1.03-1.08x)
  - **Text-based reps**: DEGRADE zoom_fine (0.66-0.69x)

---

## Blockers (External Dependencies)

| Blocker | Status | Details |
|---------|--------|---------|
| **Dense embeddings at 174k** | ❌ BLOCKED | Only 3/26 years (2000-2002, ~12.5k decisions) ACCEPTED; years 2003-2019 (~99k, 79%) in checkpoints but **PENDING AUDIT** |
| **Citation role embeddings at 174k** | ❌ BLOCKED | Require dense embeddings delivery |
| **Linear hybrid embeddings at 174k** | ❌ BLOCKED | Require dense embeddings delivery |
| **Jurist human study** | ⚠️ EXTERNAL | Framework ready; requires 5-10 Swiss jurists |

**Legal-distance progress.json** shows 20/26 years (2000-2019, ~99k decisions) complete in checkpoints — **but only 3/26 years are ACCEPTED per factory direction v28 audit verification**.

---

## Infrastructure Verification (All OPERATIONAL)

| Component | Status | Verification |
|-----------|--------|--------------|
| **Formal suite script** | ✅ | Syntax OK, config hash `b51701f5a9c11692` matches frozen harness |
| **Scalable NN backend** | ✅ | Auto-backend selection works (sklearn_exact for n<10000, HNSW fallback); tested |
| **Adversarial benchmarks** | ✅ | Exact k-NN on stratified subsample n=2000; cited_decisions_tfidf reproduces LangDom=0.5295 PASS, JuristPref=0.8020 PASS |
| **Citation heritage pipeline** | ✅ | Frozen 2,040 pair pool generated from resolved citation graph; evaluation re-run verified |
| **v17b normalization pipeline** | ✅ | Differential effect reproduced across all 8 TF-IDF representations |
| **HNSW artifact fix** | ✅ | CONFIRMED — exact k-NN on valid subset avoids HNSW masking representation differences |
| **Monitor script** | ✅ | Operational, check_count=176, watching legal-distance accepted mount |

---

## 12k Dense Embeddings (ACCEPTED 3 Years: 2000-2002) — Not 174k Scale

**Status**: Available but **NOT at 174k scale** — factory direction question is specifically 174k

| Representation | Scale | Adversarial Gates | Hierarchical Zoom (fractal-map) |
|---------------|-------|-------------------|--------------------------------|
| center_projected_768dim | 12,570 | **FAIL** (LangDom=0.981, Jurist=0.04) | PASS (improvement_rate=0.33-0.55, zero fragmentation) |
| center_projected_64dim | 12,570 | **FAIL** (LangDom=0.978, Jurist=0.045) | PASS |
| center_projected_128dim | 12,570 | **FAIL** (LangDom=0.980, Jurist=0.041) | PASS |

**Critical finding**: Flat adversarial benchmarks FAIL on dense embeddings at 12k, but hierarchical Leiden (constrained, min_cluster_size) achieves zoom coherence improvement_rate 33-55% with zero fragmentation. **Scale dependency confirmed**: flat zoom FAILS at sub-62k scale; hierarchical works.

---

## Readiness for Next Representations

When 174k dense embeddings land in accepted state, the evaluation lane is **ready to execute immediately**:

1. **Formal suite script**: Operational, frozen harness v3, config hash verified
2. **Scalable NN infrastructure**: Ready (exact k-NN for adversarial, HNSW for full-corpus)
3. **Citation heritage pipeline**: Ready (frozen pair pool, 95.9% resolution)
4. **v17b normalization pipeline**: Ready
5. **Metadata 174k**: Verified (173,963 entries, branch+legal_area 100% coverage)

---

## Recommendation

**continue_recommended = FALSE** — No additional same-question cycle justified without new 174k representations.

The evaluation lane should **remain in monitoring mode** via `monitor_and_evaluate_174k.py`. When legal-distance promotes 174k dense embeddings (and subsequently citation roles, linear hybrids) to accepted state, the monitor will auto-detect and execute the full formal suite.

**Next actionable cycle**: Triggered by legal-distance audit promotion of 174k dense embeddings (20/26 years currently in checkpoints).

---

## Evidence References

- Formal suite results: `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json`
- Citation heritage: `results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- v17b normalization: `results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- 12k dense partial: `results/partial_dense_2000_2002/evaluation_partial_dense_latest.json`
- Infrastructure verification: `state/evaluation.json` (infrastructure_verification section)
- Monitor state: `evaluation/state/monitor_174k_state.json`

---

## Provenance

- **Run ID**: `eval_174k_formal_suite_tfidf_complete_20260927_v28`
- **Direction version**: 28
- **Evidence tier**: REPRODUCED (15x independent verification for corpus; formal suite reproduced across runs)
- **Config hash**: `b51701f5a9c11692` (frozen harness v3_174k_fixed)
- **Global seed**: 42