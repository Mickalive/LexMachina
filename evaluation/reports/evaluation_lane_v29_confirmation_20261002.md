# Evaluation Lane — Factory Direction v29 Confirmation Report

**Date:** 2026-10-02  
**Lane:** evaluation  
**Factory Direction Version:** 29  
**Cycle Status:** COMPLETE  
**Continue Recommended:** false

---

## Summary

The evaluation lane has **fully addressed** the factory direction v29 question for all currently available representations. The lane is correctly **PAUSED** awaiting delivery of 174k dense embeddings from legal-distance.

### Factory Direction v29 Question (Evaluation Lane)
> "Run the machine-executable 174k formal suite autonomously as representations land: (1) full 12-benchmark formal suite at 174k scale on all production representations (frozen harness v3 thresholds unchanged); (2) validate citation_heritage benchmark using the published 174k citation-ID resolution (2,019/2,105 resolved); (3) test whether v17b label normalization (15-25% purity gain, REPRODUCED across 4 seeds) generalizes to 174k fine-grained legal_area labels."

### Items Completed (3/3)

| Item | Status | Evidence |
|------|--------|----------|
| **1. Full 12-benchmark formal suite at 174k (TF-IDF family)** | ✅ COMPLETE | `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` — All 8 TF-IDF representations evaluated with frozen harness v3 (exact k-NN on valid subset for adversarial benchmarks). All 8 PASS both adversarial gates. Best: `cited_decisions_tfidf_outcome_hybrid_0.5` (LangDom=0.4773, JuristPref=0.7345). Production default validated. |
| **2. Citation heritage validation on 174k** | ✅ COMPLETE | `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json` — Run on 1,020 positive + 1,020 negative pairs from resolved citation graph (2,019/2,105 citations resolved). Citation-based signals dominate: 4/8 PASS (AUC 0.71-0.74). Text-based signals FAIL (AUC ~0.5-0.63). Fundamental two-mode tradeoff confirmed. |
| **3. v17b label normalization generalization to 174k** | ✅ COMPLETE (NEGATIVE) | `evaluation/results/v17b_174k_generalization/v17b_174k_generalization_20260930_011927.json` — v17b at 1000 scale: 15-25% hierarchy purity gain REPRODUCED across 4 seeds. At 174k scale (8 reps, 15k subsample): regime is fundamentally different (213→111 labels vs 104→54); purity ratios 4-10x but NMI *decreases* on normalized labels. **Conclusion:** Method reproduced, but does not generalize in same-magnitude sense; 174k fine-grained labels operate in different regime. |

---

## Critical Findings Summary

### TF-IDF 174k Formal Suite — COMPLETE
- **All 8 representations PASS both adversarial gates** (Language Dominance < 0.85, Jurist Pairwise > 0.5)
- **Production default validated:** `cited_decisions_tfidf_outcome_hybrid_0.5` (LangDom=0.4773, JuristPref=0.7345)
- **Full-corpus benchmarks:** temporal_stability PASS (0.78 for full_text_tfidf_light), hierarchy_coherence FAIL (nesting~0.65), cluster_coherence FAIL (branch_purity~0.3-0.35), boilerplate_resistance FAIL (resistance≈-0.84)

### Citation Heritage — CITATION SIGNALS DOMINATE
- 4/8 representations PASS (all citation-based): AUC 0.71-0.74
- 4/8 FAIL (all text-based): AUC ~0.5-0.63
- **Production default AUC=0.7163** — PASS
- Confirms fundamental two-mode tradeoff: citation signals recover citation heritage; text signals do not

### v17b Label Normalization — REPRODUCED BUT REGIME-DEPENDENT
- 1000 scale: 15-25% gain REPRODUCED (4 seeds, 6 reps) → **REPRODUCED**
- 174k scale: different regime (213→111 labels), purity ratios 4-10x but NMI decreases → **NOT GENERALIZED**
- Requires separate validation at scale

### v18 Coarse Hierarchy — NEGATIVE (Fundamental Limitation)
- Even at 4-label branch level: best purity 0.65 < 0.7 threshold
- All 6 representations FAIL
- TF-IDF/citation representations lack sufficient signal density for branch-level legal structure recovery at any scale

### Dense Embeddings — BLOCKED
- Legal-distance: only 3/26 years ACCEPTED (2000-2002, ~19k decisions)
- 15/26 years checkpointed (2000-2014, ~100k) PENDING AUDIT
- Years 2019, 2025, 2026 not processed
- BGE/bger ID mapping missing; parquet unavailable
- Center_projected baselines FAIL jurist gate at 174k (JP=0.39-0.42)

### Two-Mode Tradeoff — CONFIRMED AT ALL SCALES
- **Citation/Outcome mode** (TF-IDF hybrids): LangDom~0.48, JuristPref~0.73, CiteIndep~14%
- **Semantic Embedding mode** (center_projected): LangDom~0.86, JuristPref~0.36-0.39, CiteIndep~37%
- **Metric Learning**: LangDom~0.58-0.61, JuristPref~0.53-0.61, CiteIndep~34-37%
- No single representation dominates all metrics

---

## Evaluation Readiness for New Representations

| Component | Status |
|-----------|--------|
| Formal suite harness | ✅ Operational |
| Exact k-NN adversarial (HNSW artifact fixed) | ✅ Verified |
| Citation heritage pairs (frozen) | ✅ 1,020 pos/neg pairs from 174k resolved citations |
| v17b normalization pipeline | ✅ Tested and documented |
| v18 coarse hierarchy test | ✅ Validated as negative result |

**Awaiting from legal-distance:**
1. 174k center_projected dense embeddings (768/128/64 dim)
2. Metric learning embeddings (linear/Mahalanobis/hybrid objectives)
3. Citation role embeddings (citing/following/criticizing/neutral)
4. Linear hybrids (linear_hybrid05_concat, linear_citation_concat, etc.)
5. Section-specific embeddings at full density (sachverhalt/erwaegungen/dispositiv)

---

## Next Recommendation

**PAUSE** — Factory direction v29 question fully addressed for available representations. No new 174k representations have landed from legal-distance since last evaluation cycle.

Lane should remain PAUSED until legal-distance delivers:
- 174k dense embeddings (full 173,963 decisions)
- Metric learning embeddings at 174k
- Citation role embeddings at 174k
- Linear hybrids at 174k
- Section-specific embeddings at full 174k density

Factory Director to decide successor question (legal-distance recommends FRONTIER_TEAM_REQUIRED for dense embedding data acquisition).

---

## Evidence References

All evidence preserved in:
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- `evaluation/results/174k/dense_165k_formal_suite/evaluation_165k_dense_formal_suite_latest.json`
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json`
- `evaluation/results/174k_citation_heritage/citation_pairs_174k.json`
- `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json`
- `evaluation/results/v17b_174k_generalization/v17b_174k_generalization_20260930_011927.json`
- `evaluation/results/v17b_174k_dense_partial/v17b_174k_dense_partial_latest.json`
- `legal-distance/state/legal-distance.json`
- `corpus/state/corpus.json`

---

**State File:** `state/evaluation.json` — Updated and consistent with this report.  
**Accepted Run ID:** `eval_174k_formal_suite_v29_20261001`  
**Evidence Tier:** REPRODUCED