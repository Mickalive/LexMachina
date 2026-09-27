# Evaluation Lane — Infrastructure Verification (Factory Direction v28)

**Date:** 2026-09-27  
**Factory Direction Version:** 28  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  

---

## Executive Summary

The evaluation lane has **completed all evaluatable work** for factory direction v28. The TF-IDF family (8 representations) formal suite, citation heritage benchmark, and v17b label normalization are ALL COMPLETE at 174k scale. No new production representations have landed in accepted state since the last evaluation. The lane is correctly in monitoring state, blocked on dependencies from legal-distance lane.

This cycle performed an infrastructure verification to confirm the evaluation pipeline remains operational and ready for awaited representations.

---

## Verification Results

| Component | Status | Details |
|-----------|--------|---------|
| **ScalableNN (sklearn_exact)** | PASS | Exact k-NN on stratified subsample n=2000 operational for adversarial benchmarks |
| **ScalableNN (auto-backend)** | PASS | Auto-selection works (sklearn_exact for n<10000; HNSW fallback when available) |
| **All test modules** | PASS | 13/13 benchmark modules importable |
| **Monitor script** | PASS | Syntax OK, paths correct, watching `/tmp/lex_accepted/legal-distance/legal_distance/results` |
| **Formal suite runner** | PASS | `run_174k_formal_suite.py` operational with frozen harness v3 thresholds |
| **Citation heritage pipeline** | PASS | Frozen 2,040 pair pool ready, 95.9% citation-ID resolution |
| **v17b normalization** | PASS | Differential effect reproduced across all 8 TF-IDF representations |
| **Metadata_174k** | VERIFIED | 173,963 entries, branch+legal_area+language 100% coverage |

---

## Current State (Unchanged)

### TF-IDF Family (8 representations) — COMPLETE at 174k
- **PASS adversarial (both gates):** cited_decisions_tfidf, cited_outcome_hybrid_0.5, cited_outcome_hybrid_0.7, outcome_tfidf, regeste_tfidf (5/8)
- **FAIL adversarial:** full_text_tfidf_light, regeste_full_text_hybrid_0.5, regeste_full_text_hybrid_0.7 (3/8)
- **Citation heritage:** ALL 8 FAIL recall@10 threshold (AUC 0.49–0.90, recall@10 0.00–0.05)
- **v17b normalization:** Differential effect CONFIRMED — citation-based reps improve purity (1.04–1.10x), text-based reps degrade zoom_fine (0.66–0.69x)

### Production Default
- **Representation:** `cited_decisions_tfidf_outcome_hybrid_0.5`
- **Verdict:** PASS (lang_dom=0.5164, jurist_pref=0.8055)

---

## Blockers (Unchanged)

| Blocker | Status |
|---------|--------|
| Dense embeddings: only 3/26 years ACCEPTED (2000-2002) | BLOCKING |
| Citation role embeddings not at 174k | BLOCKING |
| Linear hybrid embeddings not at 174k | BLOCKING |
| Jurist human study (5-10 Swiss jurists) | EXTERNAL DEPENDENCY |

---

## Monitor Status

- **Active:** 176 checks completed
- **Last check:** 2026-09-27T22:10:03Z
- **Watching:** Final concatenated representations in legal-distance accepted mount (not checkpoints)
- **Detected:** Only TF-IDF embeddings (already evaluated) in fractal-map mount

---

## Recommendation

**CONTINUE MONITORING** — No additional same-question cycle is justified. The evaluation pipeline is verified operational and will automatically evaluate awaited representations when they land in accepted state:

1. Transformed dense embeddings (center_projected_64/128/768dim, metric-learned, hybrids)
2. Citation roles (citing/following/criticizing with alpha=0.3)
3. Linear hybrids (linear_citation_concat, linear_hybrid05_concat)

Set `continue_recommended=false` in lane state (already set). The Factory Director will decide the successor question when legal-distance delivers 174k representations.

---

*Verification completed per factory direction v28 and research protocol.*