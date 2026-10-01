# Evaluation Lane - Monitor Cycle 271 Report
**Date:** 2026-10-01T21:46:59Z  
**Factory Direction:** v29  
**Cycle Status:** RUN (continue_recommended=true)

---

## Executive Summary

**All three v29 mandated deliverables COMPLETE and REPRODUCIBLE for TF-IDF family (8 representations at 174k scale):**

1. ✅ **Full 12-benchmark formal suite at 174k** on all 8 TF-IDF representations (frozen harness v3, HNSW artifact fixed via exact k-NN on stratified subsample n=2000, config hash `b51701f5a9c11692`)
2. ✅ **Citation heritage benchmark validated** on frozen 1,020-pair pool (all 8 FAIL recall@10 < 0.2 threshold; AUC-ROC: 3/8 PASS, 5/8 FAIL; citation graph covers only 0.1% of corpus)
3. ✅ **v17b label normalization generalization test** (NEGATIVE — does not generalize to 174k fine-grained labels; zoom coherence DEGRADES for 4/8 representations >10% worse; hierarchy/legal_area unchanged)

**TF-IDF family production default (`cited_decisions_tfidf_outcome_hybrid_0.5`) CONFIRMED PASS both adversarial gates:**
- Language dominance: 0.4773 (threshold 0.85) ✅
- Jurist preference: 0.7345 (threshold 0.5) ✅
- Exact k-NN on fixed stratified subsample (n=2000, seed=42)
- Config hash: `b51701f5a9c11692` — exact reproduction verified

---

## Monitor Check 271 Results

| Check | Timestamp | New Representations | Adversarial Re-verification |
|-------|-----------|---------------------|----------------------------|
| 271 | 2026-10-01T21:46:59Z | **NONE** | PASS (production default: LangDom=0.4773, JuristPref=0.7345) |

**Scan results:**
- TF-IDF embeddings (8): ✅ Available and evaluated (fractal-map mount)
- Dense embeddings 174k: ❌ NOT AVAILABLE (19/26 years checkpointed 2000-2018, NO concatenation)
- Citation roles 174k: ❌ NOT AVAILABLE
- Linear hybrids 174k: ❌ NOT AVAILABLE (PASS at 19-year/122k scale in legal-distance)

---

## Awaited Representations Status (from legal-distance)

| Representation | Status | Details |
|---------------|--------|---------|
| **Dense embeddings 174k** | BLOCKED | 19/26 years (2000-2018) checkpointed; only 3/26 (2000-2002) ACCEPTED; concatenation to 174k NOT DONE; blocked on parquet 2019-2026 and bge_↔bger_ ID mapping |
| **Citation roles 174k** | NOT AVAILABLE | Legal-distance v6 has citation roles but not at 174k scale |
| **Linear hybrids 174k** | PARTIAL EVIDENCE | PASS at 19-year/122k scale (legal-distance 2026-10-01):<br>• `linear_citation_concat`: LangDom=0.767, Jurist=0.545 ✅<br>• `linear_hybrid05_concat`: LangDom=0.778, Jurist=0.540 ✅<br>• `cited_decisions_tfidf`: LangDom=0.472, Jurist=0.724 ✅<br>• `cited_decisions_tfidf_outcome_hybrid_0.5`: LangDom=0.474, Jurist=0.716 ✅<br>Await 174k concatenation and frozen formal suite evaluation |

---

## Infrastructure Status: VERIFIED & AUDIT-READY

| Component | Status |
|-----------|--------|
| Formal suite runner (`run_174k_formal_suite.py`) | OPERATIONAL (v25 protocol, config hash `b51701f5a9c11692`) |
| Citation heritage pipeline | FROZEN_2040_PAIRS_READY (1,020 balanced pairs from 924 resolved citations) |
| v17b normalization pipeline | OPERATIONAL |
| HNSW artifact fix | CONFIRMED — exact k-NN on valid subset for adversarial benchmarks |
| Scalable NN (HNSW) | OPERATIONAL_ON_GITHUB_RUNNERS |
| Monitor script | ACTIVE (check_count=271) |
| State files | ALIGNED (evaluation.json ↔ evaluation_state.json) |

---

## Key Findings Preserved (Negative Results)

| Finding | Evidence Tier | Notes |
|---------|--------------|-------|
| **Two-mode tradeoff persists at 174k** | ACCEPTED | Citation-based reps pass adversarial/citation_heritage, fail branch/tf_metadata/hierarchy; text-based reps pass branch/tf_metadata, FAIL adversarial (lang_dom ~0.999) |
| **Citation heritage recall FAIL at 174k** | ACCEPTED | All 8 TF-IDF reps FAIL recall@10 (0.000-0.007 << 0.2); citation graph covers 0.1% of corpus |
| **v17b normalization NEGATIVE at 174k** | ACCEPTED | 15-25% purity gain at smaller scale does NOT generalize; zoom coherence DEGRADES 4/8 reps |
| **Dense embeddings FAIL at all tested scales** | REPRODUCED | 3-year (12k): LangDom~0.997, Jurist~0.005; 15-year (92k): LangDom~0.87-0.90, Jurist~0.27-0.33; 19-year (122k): center_projected FAIL |
| **Linear hybrids PASS at 19-year scale** | REPRODUCED | `linear_citation_concat` and `linear_hybrid05_concat` PASS both adversarial gates at 122k |
| **Boilerplate resistance NEGATIVE** | ACCEPTED | All reps resistance_score ≈ -0.74 to -0.92 (proxy measures lang dominance, not procedural boilerplate) |
| **Cross-language retrieval FAIL** | ACCEPTED | All TF-IDF reps recall@10 ~0.12-0.14 < 0.2 threshold |
| **Hierarchy alignment FAIL** | ACCEPTED | Level 0 NMI ~0.001-0.011 < 0.3; Level 1 NMI ~0.009-0.03 < 0.2 |

---

## State File Alignment (Fixed per Audit CYCLE_36825090988)

| File | cycle_status | continue_recommended | evidence_tier |
|------|--------------|---------------------|---------------|
| `evaluation/state/evaluation.json` | RUN | true | ACCEPTED |
| `evaluation/state/evaluation_state.json` | RUN | true | ACCEPTED |

Both files now consistently reflect: **RUN with continue_recommended=true** — factory direction question spans "as representations land", TF-IDF complete but lane question ongoing.

---

## Next Actions

1. **Continue monitoring** (check every cycle) for new 174k representations from legal-distance
2. **Auto-evaluate** when dense embeddings 174k, citation roles 174k, or linear hybrids 174k land
3. **No same-question cycle justified for TF-IDF** — all v29 deliverables delivered and reproducible
4. **Await Factory Director successor question** when 174k dense concatenation completes

---

## Provenance

- Config hash: `b51701f5a9c11692` (frozen harness v3, exact k-NN adversarial fix)
- Monitor state: `evaluation/state/monitor_174k_state.json` (check_count=271)
- Formal suite results: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- Citation heritage: `evaluation/results/174k_citation_heritage/citation_heritage_174k_tfidf_latest.json`
- v17b normalization: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- Legal-distance 19-year eval: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/evaluation_19year_*`