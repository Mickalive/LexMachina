# Evaluation Lane v29 - Final Confirmation Report

**Date**: 2026-10-02  
**Factory Direction Version**: 29  
**Lane Status**: COMPLETE  
**Evidence Tier**: REPRODUCED  
**Continue Recommended**: false  
**Next Recommendation**: PAUSE

## Summary

The evaluation lane has fully addressed the factory direction v29 question: *"Run the machine-executable 174k formal suite autonomously as representations land."*

All three required tasks are COMPLETE for available representations:

### Task 1: Full 12-Benchmark Formal Suite at 174k Scale ✅
- **8 TF-IDF representations** evaluated with frozen harness v3 (exact k-NN on valid subset for adversarial benchmarks)
- **All 8 PASS both adversarial gates** (language dominance < 0.85, jurist pairwise preference > 0.5)
- **Production default validated**: `cited_decisions_tfidf_outcome_hybrid_0.5`
  - Language dominance: 0.4895 (PASS)
  - Jurist preference: 0.7265 (PASS)
  - Both adversarial gates: PASS
- Full-corpus benchmarks: temporal_stability PASS (0.78 for full_text_tfidf_light), hierarchy/cluster/boilerplate FAIL

### Task 2: Citation Heritage Validation at 174k ✅
- **1,020 positive + 1,020 negative pairs** from resolved citation graph (2,019/2,105 citations resolved)
- **4/8 PASS** at frozen threshold AUC≥0.65
  - `cited_decisions_tfidf`: AUC=0.7426
  - `cited_decisions_tfidf_outcome_hybrid_0.7`: AUC=0.7290
  - `cited_decisions_tfidf_outcome_hybrid_0.5`: AUC=0.7163
  - `regeste_full_text_hybrid_0.7`: AUC=0.6595
- **Fundamental two-mode tradeoff confirmed**: Citation-based signals recover citation heritage; text-based signals do not (regeste_tfidf AUC=0.503 ~random)

### Task 3: v17b Label Normalization Generalization Test ✅
- **v17b at 1k scale**: 15-25% hierarchy purity gain REPRODUCED across 4 seeds (ratios 1.15-1.24)
- **v17b at 174k scale (15k subsample)**: NEGATIVE — different regime
  - 213 raw labels → 111 normalized (vs 104→54 at 1k)
  - Purity ratios 4-10x but **NMI decreases on normalized labels**
  - Conclusion: v17b method REPRODUCED but does not generalize in same-magnitude sense

## Additional Confirmed Negative Results

| Benchmark | Result | Details |
|-----------|--------|---------|
| v18 coarse hierarchy | NEGATIVE | Best branch-level (4 labels) purity 0.65 < 0.7 threshold |
| Cross-language retrieval | UNIVERSAL FAIL | Best recall@10 = 0.14 < 0.2 threshold |
| Cluster coherence | UNIVERSAL FAIL | Best branch purity = 0.36 < 0.7 threshold |
| Hierarchy coherence (Jurivoc) | UNIVERSAL FAIL | Best NMI = 0.03 < 0.3 threshold |
| Boilerplate resistance | UNIVERSAL FAIL | Best resistance score = -0.79 < 0 |
| Legal area clustering | UNIVERSAL FAIL | Best purity = 0.08 < 0.5 threshold |

## Dense Embeddings Status

- **15-year (91,929 decisions)**: center_projected FAILS jurist gate (LangDom~0.89, JP~0.27-0.29); linear hybrids FAIL jurist gate (JP~0.47-0.48)
- **19-year (122,015 decisions)**: center_projected FAILS jurist gate (LangDom~0.86, JP~0.34-0.37); **linear_citation_concat and linear_hybrid05_concat PASS both gates** (JP~0.54)
- **174k dense**: BLOCKED — only 3/26 years ACCEPTED (2000-2002); 15/26 years checkpointed pending audit; 11/26 years not processed

## Readiness for New Representations

The evaluation infrastructure is **operational and ready**:
- ✅ Formal suite harness (frozen harness v3, exact k-NN adversarial)
- ✅ Citation heritage benchmark (frozen 1,020 pair pool)
- ✅ v17b normalization pipeline (tested and documented)
- ✅ v18 coarse hierarchy test (validated as negative result)
- ⏳ Awaiting from legal-distance: 174k dense embeddings, metric learning, citation roles, linear hybrids, section-specific embeddings

## Provenance Compliance

- ✅ Hypothesis frozen before observation
- ✅ Negative results preserved (v17b generalization FAIL, v18 FAIL, universal failures)
- ✅ Strong baselines used (TF-IDF family, center_projected, linear hybrids)
- ✅ Machine-readable state written (state/evaluation.json)
- ✅ Human-readable reports written (multiple)
- ✅ Provenance preserved
- ✅ No benchmark weakening

## Next Action

**PAUSE** — Factory direction v29 question fully addressed for available representations. Lane should PAUSE until legal-distance delivers 174k dense embeddings, metric learning, citation roles, and linear hybrids. Factory Director to decide successor question.

---
*Verification timestamp: 2026-10-02T21:48:00Z*
*All results independently re-verified against stored artifacts*
