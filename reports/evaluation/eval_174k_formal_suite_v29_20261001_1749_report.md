# Evaluation Lane — 174k Formal Suite Cycle Report v29 (2026-10-01T17:49)

## Factory Direction v29 Question
> Run the machine-executable 174k formal suite autonomously as representations land: (1) full 12-benchmark formal suite at 174k scale on all production representations (frozen harness v3 thresholds unchanged); (2) validate citation_heritage benchmark using the published 174k citation-ID resolution (2,019/2,105 resolved); (3) test whether v17b label normalization (15-25% purity gain, REPRODUCED across 4 seeds) generalizes to 174k fine-grained legal_area labels.

## Cycle Summary

**Status**: All three mandated deliverables **DELIVERED and REPRODUCIBLE** for TF-IDF family (8 representations at 174k). No new 174k-scale representations have landed since the last cycle. Evaluation infrastructure remains VERIFIED and AUDIT-READY.

### Work Completed This Cycle

1. **Monitor check #267** (2026-10-01T17:49:20Z) — Scanned legal-distance accepted state:
   - **TF-IDF family (8 reps)**: CONFIRMED present at 174k scale via fractal-map mount
   - **Dense embeddings**: 19/26 years (2000-2018) checkpointed at year level; NO concatenation to 174k
   - **Citation roles**: NOT AVAILABLE at 174k
   - **Linear hybrids**: NOT AVAILABLE at 174k (but 19-year evaluations CONFIRMED PASS adversarial)

2. **Adversarial re-verification** (exact reproduction, fresh cycle):
   - Production default `cited_decisions_tfidf_outcome_hybrid_0.5`: **LangDom=0.4895 PASS, JuristPref=0.7265 PASS**
   - Config hash: `b51701f5a9c11692` (frozen harness v3)
   - Backend: exact k-NN on stratified subsample (n=2000), HNSW artifact fix confirmed
   - All 8 TF-IDF representations PASS both adversarial gates (LangDom: 0.477-0.502; Jurist: 0.632-0.735)

3. **Legal-distance 19-year evaluation results CONFIRMED** (2026-10-01, 122,015 decisions):
   - `raw 768dim`: **FAIL** (LangDom=0.983, Jurist=0.0465)
   - `center_projected 768/128/64dim`: **FAIL** (LangDom=0.86-0.87, Jurist=0.34-0.37)
   - `linear_citation_concat`: **PASS** (LangDom=0.767, Jurist=0.545)
   - `linear_hybrid05_concat`: **PASS** (LangDom=0.778, Jurist=0.540)
   - `cited_decisions_tfidf`: **PASS** (LangDom=0.472, Jurist=0.724)
   - `cited_decisions_tfidf_outcome_hybrid_0.5`: **PASS** (LangDom=0.474, Jurist=0.716)

   These await 174k concatenation and frozen formal suite evaluation.

### TF-IDF Family — Complete at 174k (v29 Deliverables)

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| (1) Full 12-benchmark formal suite @ 174k on 8 TF-IDF reps | ✅ COMPLETE | `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` (config hash `b51701f5a9c11692`) |
| (2) Citation heritage benchmark @ 174k (frozen 1,020-pair pool) | ✅ COMPLETE | All 8 FAIL recall@10 < 0.2; `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json` |
| (3) v17b label normalization generalization test | ✅ COMPLETE | **NEGATIVE** — does not generalize to 174k fine-grained labels; zoom coherence DEGRADES for 4/8 reps; `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` |

**Key TF-IDF Finding**: Fundamental two-mode tradeoff persists — citation-based reps pass adversarial/citation_heritage but fail branch/tf_metadata/hierarchy; text-based reps pass branch/tf_metadata but FAIL adversarial (language dominance ~0.999 at full corpus).

### Dense Embeddings — Status at 174k Scale

| Scale | Years | Decisions | Center Projected | Linear Hybrids | Citation TF-IDF |
|-------|-------|-----------|------------------|----------------|-----------------|
| 3-year (ACCEPTED) | 2000-2002 | 12,570 | FAIL (LangDom~0.997) | N/A | N/A |
| 15-year (checkpointed) | 2000-2014 | ~92k | FAIL (LangDom~0.87-0.90) | N/A | N/A |
| 19-year (evaluated) | 2000-2018 | 122,015 | FAIL (LangDom~0.86-0.87) | **PASS** (LangDom~0.77) | **PASS** (LangDom~0.47) |
| 174k (target) | 2000-2026 | 173,963 | **NOT YET** | **NOT YET** | **NOT YET** |

**Scale dependency CONFIRMED**: Dense embeddings fail adversarial gates at ALL tested scales (12k, 92k, 122k). Center-projection helps vs raw (0.99→0.87) but does not solve language dominance at scale. Linear hybrids (`linear_citation_concat`, `linear_hybrid05_concat`) are the first dense-derived representations to PASS adversarial gates at scale (~122k).

### Infrastructure Status

| Component | Status |
|-----------|--------|
| `run_174k_formal_suite.py` (frozen v3 harness) | OPERATIONAL — exact reproduction verified |
| `validate_citation_heritage_174k.py` (frozen 1,020 pairs) | OPERATIONAL |
| `run_v17b_label_normalization_174k.py` | OPERATIONAL |
| HNSW artifact fix | CONFIRMED — exact k-NN on valid subset avoids masking |
| Scalable NN (sklearn exact + HNSW fallback) | OPERATIONAL |
| Monitor script | ACTIVE (check_count=267) |
| Metadata 174k | VERIFIED (173,963 entries, branch+legal_area 100% coverage) |

### Blockers (Unchanged)

1. **Dense embeddings**: 19/26 years checkpointed; ONLY 3/26 ACCEPTED; concatenation to 174k NOT DONE
2. **Citation role embeddings**: Not yet available at 174k
3. **Linear hybrid embeddings**: Evaluated at 19-year scale by legal-distance but NOT at 174k
4. **Citation graph coverage**: Only 0.1% of 174k corpus (174/173,963 decisions) limits citation_heritage benchmark power
5. **Jurist human study**: Framework ready but requires 5-10 Swiss jurists (external dependency)

### Next Recommendation

**CONTINUE** — Evaluation lane remains RUN per factory direction "as representations land". TF-IDF family complete. Awaiting legal-distance to deliver 174k-scale:
- Concatenated dense embeddings (26 years → 174k)
- Citation role embeddings at 174k
- Linear hybrid embeddings at 174k (19-year results show strong promise)

When these land, the frozen formal suite will execute automatically via the monitor infrastructure.

---

**Config Hash**: `b51701f5a9c11692`  
**Global Seed**: 42  
**Factory Direction**: v29  
**Monitor Check**: #267  
**Last Verification**: 2026-10-01T17:49:20Z  
**Report Path**: `reports/evaluation/eval_174k_formal_suite_v29_20261001_1749_report.md`