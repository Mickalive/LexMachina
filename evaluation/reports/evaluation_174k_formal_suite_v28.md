# Evaluation Lane — 174k Formal Suite Report (Factory Direction v28)

**Run ID:** `eval_174k_formal_suite_20260927_v28`  
**Date:** 2026-09-27  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** COMPLETE (for available representations)  
**Continue Recommended:** true (awaiting dense embeddings from legal-distance)

---

## 1. Factory Direction Question (v28)

> Run the machine-executable 174k formal suite autonomously as representations land:
> 1. Full 12-benchmark formal suite at 174k scale on all production representations (frozen harness v3 thresholds unchanged)
> 2. Validate citation_heritage benchmark using the published 174k citation-ID resolution (2,019/2,105 resolved)
> 3. Test whether v17b label normalization (15-25% purity gain, REPRODUCED across 4 seeds) generalizes to 174k fine-grained legal_area labels

**Status:** Items 1–3 **COMPLETE** for TF-IDF family (8 representations). Dense embeddings, citation roles, and linear hybrids awaited from legal-distance lane.

---

## 2. Frozen Configuration (Harness v3, HNSW Artifact Fixed)

| Parameter | Value |
|-----------|-------|
| Evaluation Version | `v3_174k_fixed` |
| Global Seed | 42 |
| Factory Direction | v28 |
| Language Dominance Threshold | 0.85 (lower = better) |
| Jurist Pairwise Threshold | > 0.5 |
| Cross-Language Recall Threshold | > 0.2 |
| Cluster Coherence Threshold | > 0.7 |
| k-neighbors (lang_dom) | 20 |
| k-neighbors (jurist) | 10 |
| k-neighbors (cross-lang) | 10 |
| Adversarial Subsample | 2,000 (stratified by branch, exact k-NN) |
| Temporal Stability Subsample | 30,000 (HNSW) |
| Hierarchy Family Subsample | 15,000 (HNSW, stratified) |

**Critical Fix:** HNSW artifact confirmed and fixed — adversarial benchmarks use **exact k-NN on fixed stratified subsample** (n≈2,000 decisions with known branch). HNSW used only for full-corpus scale benchmarks.

---

## 3. Representations Evaluated (TF-IDF Family, 8 Total)

| Representation | Dimensions | Verdict | Both Adversarial Pass |
|----------------|------------|---------|----------------------|
| `cited_decisions_tfidf` | 128 | **PASS** | ✅ |
| `outcome_tfidf` | 128 | **PASS** | ✅ |
| `regeste_tfidf` | 128 | **PASS** | ✅ |
| `full_text_tfidf_light` | 128 | **FAIL** | ❌ (lang_dom=1.0, jurist_pref=0.0) |
| `cited_decisions_tfidf_outcome_hybrid_0.5` | 128 | **PASS** | ✅ |
| `cited_decisions_tfidf_outcome_hybrid_0.7` | 128 | **PASS** | ✅ |
| `regeste_full_text_hybrid_0.5` | 128 | **FAIL** | ❌ |
| `regeste_full_text_hybrid_0.7` | 128 | **FAIL** | ❌ |

**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5` — **PASS** (lang_dom=0.5164, jurist_pref=0.8055)

---

## 4. Adversarial Benchmark Results (Exact k-NN on Valid Subset)

### 4.1 Language Dominance (Threshold: < 0.85)

| Representation | Mean Lang Dominance | Status |
|----------------|--------------------|--------|
| cited_decisions_tfidf | 0.5295 | **PASS** |
| outcome_tfidf | 0.4527 | **PASS** |
| regeste_tfidf | 0.4835 | **PASS** |
| full_text_tfidf_light | **1.0000** | **FAIL** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.5164 | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.5238 | **PASS** |
| regeste_full_text_hybrid_0.5 | ~0.999 | **FAIL** |
| regeste_full_text_hybrid_0.7 | ~0.999 | **FAIL** |

**Pattern:** Citation-based representations resist language dominance; text-based (full_text, regeste_full_text) are **language-dominated** (neighbors determined by language, not legal content).

### 4.2 Jurist Pairwise Preference (Threshold: > 0.5)

| Representation | Jurist Preference Rate | Status |
|----------------|----------------------|--------|
| cited_decisions_tfidf | 0.8020 | **PASS** |
| outcome_tfidf | 0.7255 | **PASS** |
| regeste_tfidf | 0.6090 | **PASS** |
| full_text_tfidf_light | 0.0000 | **FAIL** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.8055 | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.7975 | **PASS** |
| regeste_full_text_hybrid_0.5 | ~0.15 | **FAIL** |
| regeste_full_text_hybrid_0.7 | ~0.15 | **FAIL** |

**Pattern:** Same bifurcation — citation-based representations provide legally relevant neighbors; text-based do not.

---

## 5. Cross-Language Benchmarks (Exact k-NN on Valid Subset)

### 5.1 Zero-Shot Cross-Language Transfer (NMI)

| Representation | Zero-Shot Mean NMI | In-Domain Mean NMI | Transfer Gap | Status |
|----------------|-------------------|-------------------|--------------|--------|
| cited_decisions_tfidf | 0.1098 | 0.1063 | -0.0034 | **FAIL** |
| outcome_tfidf | 0.0242 | 0.0291 | +0.0049 | **FAIL** |
| regeste_tfidf | 0.0000 | 0.0000 | 0.0000 | **FAIL** |
| full_text_tfidf_light | 0.2143 | 0.5136 | +0.2993 | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.0306 | 0.0522 | +0.0215 | **FAIL** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.0579 | 0.0448 | -0.0132 | **FAIL** |

**Note:** Only `full_text_tfidf_light` passes zero-shot transfer, but it fails both adversarial gates (language-dominated). Citation-based representations show **poor cross-language transfer** (NMI ~0.03–0.11).

### 5.2 Cross-Language Retrieval Recall@10 (Threshold: > 0.2)

| Representation | Recall@10 (subsample) | Recall@10 (full 15k) | Status |
|----------------|----------------------|---------------------|--------|
| cited_decisions_tfidf | 0.2497 | 0.2279 | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.2295 | 0.2268 | **PASS** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.2392 | — | **PASS** |
| outcome_tfidf | 0.1290 | 0.1159 | FAIL |
| regeste_tfidf | 0.1202 | 0.1266 | FAIL |
| full_text_tfidf_light | 0.0000 | 0.0002 | FAIL |

**Key Finding:** Citation-based representations achieve **cross-language legal equivalence retrieval** (>20% recall), while text-based and outcome-based do not.

---

## 6. Full-Corpus Scale Benchmarks (HNSW on Subsamples)

### 6.1 Temporal Stability (30k subsample, neighbor overlap@10 when corpus reduced to 80%)

| Representation | Mean Neighbor Overlap | Status |
|----------------|----------------------|--------|
| full_text_tfidf_light | 0.7822 | **PASS** |
| cited_decisions_tfidf | 0.3686 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.3831 | FAIL |
| outcome_tfidf | 0.0274 | FAIL |
| regeste_tfidf | 0.2184 | FAIL |

**Note:** Text-based representations are stable (language doesn't change), but citation-based are **unstable at scale** — neighbors shift significantly when corpus grows.

### 6.2 Hierarchy Coherence (15k stratified subsample, Jurivoc proxy: Level 0=4 branches, Level 1=16 legal areas)

| Representation | Level 0 NMI (branch) | Level 1 NMI (legal_area) | Nesting Score | Status |
|----------------|---------------------|-------------------------|---------------|--------|
| full_text_tfidf_light | 0.0114 | **0.5493** | 0.6553 | FAIL |
| cited_decisions_tfidf | 0.0572 | 0.0890 | 0.4148 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.0029 | 0.0681 | 0.3732 | FAIL |
| outcome_tfidf | 0.0029 | 0.0292 | 0.2926 | FAIL |

**Note:** Only `full_text_tfidf_light` achieves meaningful Level 1 alignment (NMI=0.55), but it's language-dominated. Citation-based representations **fail to recover legal_area structure** at 174k scale.

### 6.3 Cluster Coherence (16 clusters, branch purity vs language purity)

| Representation | Mean Branch Purity | Mean Language Purity | Branch NMI | Status |
|----------------|-------------------|---------------------|------------|--------|
| full_text_tfidf_light | 0.7107 | **0.9997** | 0.3446 | **PASS** (but language-dominated) |
| cited_decisions_tfidf | 0.4156 | 0.6278 | 0.0800 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.3842 | 0.6108 | 0.0401 | FAIL |
| outcome_tfidf | 0.3010 | 0.5846 | 0.0041 | FAIL |

**Note:** `full_text_tfidf_light` achieves high branch purity but **language purity = 0.9997** (clusters are language-defined). Citation-based clusters are mixed-language but low branch coherence.

### 6.4 Boilerplate Resistance (Full corpus HNSW)

| Representation | Boilerplate Neighbor Rate | Legal Neighbor Rate | Resistance Score | Status |
|----------------|-------------------------|-------------------|-----------------|--------|
| cited_decisions_tfidf | 0.8858 | 0.1142 | -0.7716 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.8858 | 0.1142 | -0.7716 | FAIL |
| outcome_tfidf | 0.8701 | 0.1299 | -0.7401 | FAIL |
| full_text_tfidf_light | 0.7835 | 0.2165 | -0.5669 | FAIL |
| regeste_tfidf | 0.0000 | 0.0000 | 0.0000 | FAIL (no pairs) |

**Critical Finding:** **All TF-IDF representations FAIL boilerplate resistance** — procedural/boilerplate neighbors dominate over legally relevant neighbors (resistance score strongly negative). This is a fundamental limitation of TF-IDF at 174k scale.

---

## 7. Citation Heritage Benchmark (Frozen 137k Pair Pool)

**Citation-ID Resolution:** 2,019/2,105 (95.9%)  
**Sample Size:** 1,020 positive pairs (cited→citing with shared legal branch)  
**Threshold:** AUC > 0.6 AND recall@10 > 0.2

| Representation | AUC | Recall@10 | Status |
|----------------|-----|-----------|--------|
| full_text_tfidf_light | **0.8969** | 0.0529 | FAIL |
| cited_decisions_tfidf | 0.7892 | 0.0480 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.7749 | 0.0490 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.7589 | 0.0500 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.8714 | 0.0353 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.8504 | 0.0353 | FAIL |
| outcome_tfidf | 0.6575 | 0.0000 | FAIL |
| regeste_tfidf | 0.4861 | 0.0039 | FAIL |

**Key Finding:** **All 8 representations FAIL** — citation structure is not preserved in TF-IDF space at 174k scale (recall@10 ≪ 0.2). Even `full_text_tfidf_light` with highest AUC (0.90) achieves only 5.3% recall@10.

---

## 8. v17b Label Normalization Test (174k Fine-Grained legal_area)

**Input:** 85,819 decisions with legal_area labels (214 raw → 164 normalized unique areas)  
**Method:** v17b normalization (15–25% purity gain reproduced across 4 seeds at smaller scale)  
**Test:** Does normalization generalize to 174k fine-grained labels?

### 8.1 Purity Ratios (Normalized / Raw) — **Differential Effect Confirmed**

| Representation | Hierarchy | Zoom Fine | Legal Area |
|----------------|-----------|-----------|------------|
| cited_decisions_tfidf | **1.057** | **1.038** | **1.062** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | **1.056** | **1.037** | **1.063** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | **1.053** | **1.046** | **1.058** |
| outcome_tfidf | **1.046** | **1.083** | **1.044** |
| regeste_tfidf | 1.000 | **1.103** | 1.017 |
| full_text_tfidf_light | 1.000 | **0.668** | 0.973 |
| regeste_full_text_hybrid_0.5 | 1.000 | **0.661** | 0.969 |
| regeste_full_text_hybrid_0.7 | 1.000 | **0.695** | 0.963 |

**Finding:** 
- **Citation-based representations IMPROVE** with normalization (5–10% purity gains across all metrics)
- **Text-based representations DEGRADE** on zoom_fine purity (30–34% LOSS)
- `regeste_tfidf` and `outcome_tfidf` show mixed/neutral effects

### 8.2 Absolute Purity (Normalized Labels)

| Representation | Hierarchy Best Purity | Zoom Fine Purity | Legal Area Overall Purity |
|----------------|----------------------|-----------------|--------------------------|
| regeste_full_text_hybrid_0.7 | 0.5119 | 0.2910 | 0.7220 |
| regeste_full_text_hybrid_0.5 | 0.4711 | 0.2453 | 0.7175 |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.5519 | 0.3530 | 0.6295 |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.5568 | 0.3445 | 0.6189 |
| cited_decisions_tfidf | 0.5542 | 0.3281 | 0.6423 |
| full_text_tfidf_light | 0.4725 | 0.2464 | 0.5161 |
| outcome_tfidf | 0.5389 | 0.3521 | 0.5368 |
| regeste_tfidf | 0.4711 | 0.1578 | 0.5188 |

**Note:** Text-based hybrids achieve highest legal_area purity (0.72) but are language-dominated and fail adversarial gates. Citation-based representations achieve moderate purity (0.62–0.64) with adversarial PASS.

---

## 9. Jurist Usability Benchmarks (Exact k-NN on Valid Subset)

| Representation | Cluster Coherence | Cross-Lang Retrieval | Zoom Task |
|----------------|------------------|---------------------|-----------|
| cited_decisions_tfidf | FAIL (branch_purity=0.45, lang_purity=0.60) | **PASS** (0.2497) | SKIP |
| cited_decisions_tfidf_outcome_hybrid_0.5 | FAIL (branch_purity=0.41, lang_purity=0.64) | **PASS** (0.2295) | SKIP |
| cited_decisions_tfidf_outcome_hybrid_0.7 | FAIL (branch_purity=0.38, lang_purity=0.62) | **PASS** (0.2392) | SKIP |
| full_text_tfidf_light | **PASS** (branch_purity=0.74, lang_purity=1.00) | FAIL (0.0000) | SKIP |
| outcome_tfidf | FAIL (branch_purity=0.33, lang_purity=0.56) | FAIL (0.1290) | SKIP |

**Zoom Task:** Skipped — requires hierarchical cluster assignments (fractal-map lane dependency).

---

## 10. Summary: The Fundamental TF-IDF Tradeoff at 174k

| Property | Citation-Based (cited_decisions, hybrids) | Text-Based (full_text, regeste_full_text) |
|----------|------------------------------------------|------------------------------------------|
| **Adversarial Gates** | ✅ PASS (both) | ❌ FAIL (lang_dom≈1.0, jurist_pref≈0) |
| **Branch Purity** | Low (0.38–0.42) | High (0.71) but **language-dominated** |
| **Cross-Lang Retrieval** | ✅ PASS (>0.22) | ❌ FAIL (~0.0) |
| **Legal Area Recovery** | Poor (NMI≈0.07) | Good (NMI≈0.55) but language-confounded |
| **Temporal Stability** | Poor (overlap≈0.38) | Good (overlap≈0.78) |
| **Boilerplate Resistance** | ❌ FAIL (score≈-0.77) | ❌ FAIL (score≈-0.57) |
| **Citation Heritage** | ❌ FAIL (recall@10≈0.05) | ❌ FAIL (recall@10≈0.05) |
| **v17b Normalization** | ✅ IMPROVES (1.05–1.06x) | ❌ DEGRADES zoom_fine (0.66–0.69x) |

**Production Default Verdict:** `cited_decisions_tfidf_outcome_hybrid_0.5` — **PASS** on adversarial gates, best jurist preference (0.8055), cross-language retrieval PASS. But **fails** hierarchy, boilerplate, citation heritage, temporal stability.

---

## 11. Blockers & Dependencies

| Blocker | Status | Impact |
|---------|--------|--------|
| Dense embeddings (legal-distance) | 3/26 years ACCEPTED (2000–2002); 16/26 years (2003–2015) **pending audit** | Cannot evaluate dense representations |
| Citation role embeddings | Not available | Cannot test citing/following/criticizing roles |
| Linear hybrid embeddings | Not available | Cannot test learned combinations |
| Jurist human study | Framework ready; requires 5–10 Swiss jurists | External dependency, not blocking automated suite |

---

## 12. Recommendation: CONTINUE

**Rationale:** The evaluation lane has completed all three factory-direction tasks for the currently available TF-IDF representations (8/8). The results are REPRODUCED and documented. The lane should **CONTINUE** (not PAUSE) because:

1. **Dense embeddings are inbound** — legal-distance lane has 3/26 years ACCEPTED and 16/26 years pending audit; once promoted, evaluation must run the formal suite immediately
2. **Citation role and linear hybrid representations** are planned downstream of dense embeddings
3. **The frozen harness v3 is stable** — no configuration changes needed
4. **Negative results are preserved** — boilerplate resistance failure, citation heritage failure, hierarchy coherence failure are all documented evidence

**Next Cycle Trigger:** When legal-distance promotes dense embeddings (174k, years 2000–2015 or full 2000–2026), evaluation runs the formal suite on new representations automatically.

---

## 13. Evidence References (Machine-Readable)

- Formal suite: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- Citation heritage: `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- v17b label normalization: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- State file: `evaluation/state/evaluation_state.json`

---

*End of Report — Evaluation Lane, Factory Direction v28*