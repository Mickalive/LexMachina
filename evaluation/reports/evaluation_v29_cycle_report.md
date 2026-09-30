# Evaluation Lane - Cycle Report (Factory Direction v29)

**Date**: 2026-09-30  
**Direction Version**: 29  
**Evidence Tier**: REPRODUCED  
**Cycle Status**: COMPLETE  
**Continue Recommended**: FALSE  

---

## Executive Summary

This cycle executed three machine-executable evaluation tasks as specified in factory direction v29:

1. **v17b label normalization test at 174k scale** on TF-IDF family (8 representations)
2. **Citation heritage benchmark validation** at 174k scale using resolved citation graph
3. **Review of existing dense embedding evaluations** (3-year ACCEPTED, 15-year checkpointed)

All tasks completed successfully. Key finding: **v17b label normalization effect (15-25% purity gain at smaller scale) does NOT reproduce at 174k scale** — hierarchy/legal_area purity ratios = 1.0 (no change), zoom_fine purity DEGRADED for 4/8 representations.

---

## Task 1: v17b Label Normalization at 174k Scale

### Method
- Tested 8 TF-IDF family representations at full 174k (173,963 decisions)
- Compared raw legal_area labels (214 unique) vs. normalized (164 unique, cross-lingual canonical mapping)
- 49.3% of labels normalized (85,819/173,963)
- Metrics: hierarchy_coherence, zoom_coherence, legal_area_clustering purity ratios (normalized/raw)

### Results Summary

| Representation | Hierarchy Ratio | Zoom Fine Ratio | Legal Area Ratio |
|----------------|-----------------|-----------------|------------------|
| cited_decisions_tfidf | 1.0000 | **0.8869** | 1.0000 |
| outcome_tfidf | 1.0000 | 0.9968 | 1.0000 |
| regeste_tfidf | 1.0000 | 0.9885 | 1.0018 |
| full_text_tfidf_light | 1.0000 | **0.8352** | 0.9997 |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 1.0000 | **0.8827** | 0.9997 |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 1.0000 | **0.8861** | 1.0000 |
| regeste_full_text_hybrid_0.5 | 1.0000 | 0.9060 | 1.0024 |
| regeste_full_text_hybrid_0.7 | 1.0000 | 0.9647 | 1.0016 |

**Uniform improvement/matching: FALSE** — 4 representations show >10% degradation on zoom_fine.

### Key Finding
- **NO purity gain** on hierarchy_coherence or legal_area_clustering at 174k (ratio = 1.0)
- **Degradation** on zoom_coherence fine_purity for citation-based representations
- The 15-25% purity gain reported at smaller scale (v17b) **does not generalize to 174k**
- Legal area normalization reduces label count 214→164 but clustering quality unchanged

### Interpretation
At 174k scale, the cross-lingual label duplication artifact is no longer the limiting factor for hierarchy/legal_area purity. The fundamental limitation is embedding quality (TF-IDF signals don't capture fine-grained legal_area structure), not label noise. Normalization helps label consistency but cannot create signal that isn't in the embeddings.

---

## Task 2: Citation Heritage Validation at 174k

### Method
- Loaded resolved citation graph from corpus normalization (2,019/2,105 citations resolved = 95.9%)
- Mapped to 174k metadata (173,963 decisions)
- Built positive pairs (direct citations + shared citations) and negative pairs (no citation relation)

### Results
- **Decisions in citation graph**: 174 / 173,963 = **0.1%**
- **Decisions with outgoing citations**: 174 = **0.1%**
- **Resolved citations mapping to corpus**: 924
- **Positive pairs (direct + shared)**: 1,020
- **Negative pairs (sampled)**: 1,020
- Benchmark infrastructure: READY

### Key Finding
Citation graph coverage is **extremely sparse** (0.1% of corpus). The citation_heritage benchmark can only evaluate a tiny fraction of the map. This confirms the factory direction note: "citation graph only covers 174/174k decisions (0.1%)".

### Implication
Citation_heritage is not a viable full-corpus benchmark at 174k. It may be useful for targeted evaluation of citation-dense regions but cannot measure general map quality.

---

## Task 3: Dense Embedding Evaluation Status

### ACCEPTED (3 years: 2000-2002, ~12,570 decisions)
Existing evaluation (`evaluation_dense_3yr_formal_suite.json`) shows:

| Representation | Language Dominance | Jurist Preference | Verdict |
|----------------|-------------------|-------------------|---------|
| center_projected_768 | 0.997 (FAIL) | 0.008 (FAIL) | FAIL |
| center_projected_128 | 0.980 (FAIL) | 0.041 (FAIL) | FAIL |
| center_projected_64 | 0.978 (FAIL) | 0.045 (FAIL) | FAIL |

**All FAIL both adversarial gates** (LangDom threshold 0.85, JP threshold 0.5).
- Language dominance ~0.98-1.0: neighbors are almost entirely same-language
- Jurist preference ~0.01-0.04: virtually no legally-relevant neighbors found

This confirms factory direction: "center_projected baselines FAIL jurist gate at 174k (JP=0.39-0.42) per CYCLE_36518989087" — at 12k scale it's even worse (JP~0.04).

### CHECKPOINTED (15 years: 2000-2014, ~100k decisions) — PENDING AUDIT
Embeddings exist in `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` for years 2000-2014. Not yet evaluated by evaluation lane — awaiting audit promotion to ACCEPTED.

### NOT YET PROCESSED (11 years: 2015-2026)
No dense embeddings computed yet.

---

## TF-IDF Family at 174k (COMPLETE)

From `evaluation_174k_formal_suite_latest.json` (8 representations):

### Adversarial Gates (ALL PASS)
- Language dominance: 0.47-0.50 (threshold 0.85) ✓
- Jurist pairwise preference: 0.63-0.73 (threshold 0.5) ✓

### Full-Corpus Benchmarks (MOSTLY FAIL)
| Benchmark | Status | Note |
|-----------|--------|------|
| Temporal stability | FAIL (0.0-0.78) | Only full_text_tfidf_light passes (0.78) |
| Hierarchy coherence | FAIL (NMI 0.001-0.03) | Level 0 (4 branches): ~0.001-0.009; Level 1 (16 areas): ~0.01-0.03 |
| Cluster coherence | FAIL (branch purity 0.28-0.36) | Language purity 0.59-0.62 dominates |
| Cross-language retrieval | FAIL (recall@10 0.12-0.15) | Threshold 0.2 |
| Boilerplate resistance | FAIL (score -0.78 to -0.84) | Procedural neighbors dominate |

### Two-Mode Tradeoff Confirmed
- **Citation-based** (cited_decisions_tfidf, hybrids): Better LangDom, better JP, LOW citation-independent retrieval
- **Text-based** (regeste_tfidf, full_text_tfidf_light): Better cross-lang transfer, but still FAIL cross-lang retrieval
- **No single representation excels at all dimensions**

---

## Evidence Tier Assessment

| Finding | Tier | Notes |
|---------|------|-------|
| TF-IDF formal suite at 174k | REPRODUCED | Multiple runs, frozen harness v3 |
| v17b label normalization at 174k | REPRODUCED | Single run, deterministic (seed=42), negative result |
| Citation heritage infrastructure | REPRODUCED | Infrastructure ready, coverage limitation documented |
| Dense embeddings (3yr) FAIL adversarial | REPRODUCED | Consistent across 768/128/64 dim |
| v18 coarse hierarchy NEGATIVE | ACCEPTED (legal-distance) | Max branch purity 0.65 < 0.7 threshold |

---

## Recommendations

### Immediate (Evaluation Lane)
1. **PAUSE** evaluation lane — no further 174k formal suite runs until legal-distance delivers ACCEPTED dense embeddings
2. **Monitor** legal-distance audit progress for 15-year checkpointed embeddings (2000-2014)
3. **Do NOT** run citation_heritage benchmark at 174k until coverage improves (currently 0.1%)

### For Legal-Distance Lane
1. **Priority**: Complete audit of 15-year checkpointed dense embeddings (2000-2014)
2. **Priority**: Compute remaining 11 years (2015-2026) dense embeddings
3. **Investigate**: Why center_projected fails so badly at 12k (JP~0.04) vs. reported 174k JP~0.39 — scale dependency or evaluation difference?

### For Product Lane
1. **Current production default** (cited_decisions_tfidf_outcome_hybrid_0.5) is best available at 174k
2. **No dense embedding mode** ready for production — all fail adversarial gates
3. **Two map modes needed**: citation-based (legal navigation) + text-based (cross-language)

### For Fractal Map Lane
1. **Hierarchical clustering** on TF-IDF: zoom quality FAILS at 174k (flat Leiden >99% singletons, constrained Leiden 1/4 modes pass branch purity >0.5)
2. **Dense embeddings needed** for fractal map quality — current TF-IDF insufficient for multi-resolution structure

---

## Provenance

- **v17b label normalization results**: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- **Citation heritage pairs**: `evaluation/results/174k_citation_heritage/citation_pairs_174k.json`
- **TF-IDF formal suite**: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- **Dense 3yr evaluation**: `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json`
- **Legal-distance state**: `/tmp/lex_accepted/legal-distance/legal_distance/legal-distance.json`
- **Factory direction**: `/tmp/lex_control/state/factory_direction.json` (v29)

---

## Acceptance Criteria Met

- [x] v17b label normalization tested at 174k on all 8 TF-IDF representations
- [x] Citation heritage benchmark validated at 174k using resolved citation graph
- [x] Dense embedding evaluation status documented (ACCEPTED 3yr FAIL, 15yr checkpointed pending)
- [x] Results preserved with full provenance
- [x] Negative results documented (v17b gain not reproduced, citation coverage 0.1%)
- [x] State updated to direction_version 29
- [x] Next recommendation aligned with factory direction v29