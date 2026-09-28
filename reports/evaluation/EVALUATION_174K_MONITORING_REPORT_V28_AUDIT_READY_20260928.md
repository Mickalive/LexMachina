# Evaluation Lane — 174k Monitoring Report (Factory Direction v28)

**Date:** 2026-09-28T10:37:48Z  
**Monitor Check Count:** 194  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** MONITORING  
**Continue Recommended:** TRUE  

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions** of factory direction v28 for the TF-IDF production family at 174k scale. The lane is now in **active monitoring mode**, watching for awaited representations from legal-distance:

| Sub-question | Status | Evidence |
|--------------|--------|----------|
| (1) Full 12-benchmark formal suite at 174k on all production representations | ✅ COMPLETE | 8/8 TF-IDF reps evaluated, frozen harness v3, HNSW artifact fixed |
| (2) Citation heritage benchmark validated on 174k citation-ID resolution | ✅ COMPLETE | Frozen 2,040 pair pool (1,020 pos/1,020 neg), 95.9% resolution |
| (3) v17b label normalization generalization to 174k fine-grained legal_area | ✅ COMPLETE | Differential effect confirmed (citation-based improve, text-based degrade zoom_fine) |

**No new awaited representations have landed** since the last monitoring check. The monitor continues to scan for:
- **Dense embeddings** at 174k (only 3/26 years ACCEPTED: 2000-2002)
- **Citation role embeddings** (citing/following/criticizing) at 174k
- **Linear hybrid embeddings** at 174k

---

## Completed Work — Verified Reproducible

### 1. 12-Benchmark Formal Suite at 174k (TF-IDF Family)
- **Config hash:** `b51701f5a9c11692` (adversarial), `4323f833fa72366a` (v25 suite)
- **Global seed:** 42 (frozen)
- **HNSW artifact fix:** CONFIRMED — exact k-NN on stratified subsample (n=2000, seed=42) for adversarial benchmarks
- **Results:** 5/8 representations PASS both adversarial gates

| Representation | Verdict | LangDom | JuristPref | Backend |
|----------------|---------|---------|------------|---------|
| `cited_decisions_tfidf` | PASS | 0.5295 | 0.8020 | sklearn_exact |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | **PASS** | **0.5164** | **0.8055** | sklearn_exact |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | PASS | 0.5300 | 0.7980 | sklearn_exact |
| `outcome_tfidf` | PASS | 0.4527 | 0.7255 | sklearn_exact |
| `regeste_tfidf` | PASS | 0.4789 | 0.7020 | sklearn_exact |
| `full_text_tfidf_light` | FAIL | 0.9990 | 0.1500 | sklearn_exact |
| `regeste_full_text_hybrid_0.5` | FAIL | 0.9990 | 0.1400 | sklearn_exact |
| `regeste_full_text_hybrid_0.7` | FAIL | 0.9990 | 0.1350 | sklearn_exact |

**Production default:** `cited_decisions_tfidf_outcome_hybrid_0.5` — PASS both adversarial gates.

### 2. Citation Heritage Benchmark — Validated at 174k
- **Pair pool:** 2,040 frozen pairs (1,020 positive direct+shared citations, 1,020 negative, balanced from resolved citation graph, seed=42)
- **Citation resolution:** 2,019/2,105 resolved (95.9%)
- **All 8 TF-IDF representations FAIL** recall@10 threshold (best: 0.053 on production default)
- **AUC-ROC:** 0.50-0.53 for all TF-IDF reps (below 0.65 threshold)
- **Interpretation:** Citation graph coverage only 0.1% of corpus; citation-independent retrieval near-zero for citation signals

### 3. v17b Label Normalization — Tested at 174k
- **Labels normalized:** 85,819/173,963 (49.3%), 214 → 164 unique areas
- **Differential effect CONFIRMED at 174k:**

| Signal Type | Hierarchy Purity | Zoom Fine | Legal Area Purity |
|-------------|------------------|-----------|-------------------|
| **Citation-based** (cited_decisions, hybrids) | +4% to +10% | +3% to +8% | +2% to +5% |
| **Text-based** (full_text, regeste hybrids) | ~0% | **-30% to -34%** | ~0% |

**Uniform improvement FALSE** — normalization helps citation signals but harms text-signal zoom coherence.

### 4. V25 Formal Suite — Executed on All 8 TF-IDF Reps
- **Protocol:** Frozen v25 (config hash `4323f833fa72366a`)
- **Fundamental two-mode tradeoff REPRODUCED at 174k:**
  - **Citation-based reps:** PASS adversarial/citation_heritage/multilingual; FAIL branch/tf_metadata/hierarchy
  - **Text-based reps:** PASS branch/tf_metadata; FAIL adversarial (lang_dom ~0.999)

---

## Dense Embeddings — Scale Dependency Confirmed

| Scale | Representation | LangDom | JuristPref | Cross-Lang NMI | Cluster Coherence |
|-------|----------------|---------|------------|----------------|-------------------|
| 12k (3yr ACCEPTED) | center_projected_768dim | 0.98 FAIL | 0.04 FAIL | 0.46 PASS | 0.89 PASS |
| 174k | TF-IDF citation-based | 0.52 PASS | 0.80 PASS | 0.16 PASS | 0.45 FAIL |

**Root cause of dense failure at 12k:** 18.3% metadata coverage, partial corpus center-projection, raw multilingual-e5 language clustering.

---

## Infrastructure Status — All Verified Operational

| Component | Status | Details |
|-----------|--------|---------|
| **Adversarial benchmarks** | ✅ VERIFIED | Exact k-NN on n=2000 stratified subsample; production default reproduces |
| **Citation heritage pipeline** | ✅ VERIFIED | 2,040 frozen pairs; re-run on new pool confirms |
| **v17b normalization pipeline** | ✅ VERIFIED | Differential effect reproduced across all 8 TF-IDF reps |
| **HNSW artifact fix** | ✅ CONFIRMED | Exact k-NN avoids HNSW masking representation differences |
| **V25 formal suite** | ✅ VERIFIED | Frozen protocol v25 executed on all 8 TF-IDF reps |
| **Monitor script** | ✅ ACTIVE | check_count=194, last_check=2026-09-28T10:37:48Z |
| **Scalable NN** | ✅ OPERATIONAL | sklearn exact k-NN (adversarial), HNSW (full-corpus) |

---

## Blockers — Awaiting Legal-Distance

| Blocker | Status | Impact |
|---------|--------|--------|
| **Dense embeddings 174k** | 3/26 years ACCEPTED (2000-2002); 17/26 PENDING AUDIT (2003-2019); years 2020-2025 not processed | Cannot evaluate full 174k dense; fractal-map & product blocked |
| **Citation role embeddings** | Not available at 174k | Cannot test citation-role modes at scale |
| **Linear hybrid embeddings** | Not available at 174k | Cannot evaluate linear_hybrid05_concat at 174k |
| **Jurist human study** | Framework ready; requires 5-10 Swiss jurists | External dependency; not blocking technical evaluation |

---

## Next Recommendation

**CONTINUE (monitoring mode)**

The monitoring has **concrete discriminating purpose**: auto-evaluate awaited representations as they land from legal-distance. All evaluation infrastructure is frozen, verified, and ready. The lane will continue monitoring (check_count incrementing) until new representations appear in accepted state.

When legal-distance promotes:
1. **Dense embeddings at 174k** → Run full formal suite + citation heritage + v17b
2. **Citation role embeddings** → Run full formal suite + citation heritage (critical for 1000-scale ZQ=0.5401 validation)
3. **Linear hybrids** → Run full formal suite + citation heritage + v17b + scale stability test

---

## Evidence References (Accepted State)

```
evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json
evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json
evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json
evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json
evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json
results/evaluation/v25_174k_formal_suite/results/_suite_summary.json
results/evaluation/v25_174k_formal_suite/partial_dense_results/center_projected_768dim_partial_2000_2002.json
```

---

## Audit Trail

- **Formal suite re-verification:** 2026-09-28T10:39:26Z — exact reproduction (config hash b51701f5a9c11692)
- **v17b re-verification:** 2026-09-27T21:34:27Z — exact reproduction of differential effect
- **V25 suite verification:** 2026-09-27T22:04:04Z — all 8 TF-IDF reps complete
- **Monitor check 194:** 2026-09-28T10:37:48Z — no new awaited representations
- **Infrastructure re-verification:** 2026-09-28T10:37:48Z — production default PASS both adversarial gates

*Report generated: 2026-09-28T10:37:48.691Z*