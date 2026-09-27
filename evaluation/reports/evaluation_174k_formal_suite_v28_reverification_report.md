# Evaluation Lane — 174k Formal Suite Re-Verification Cycle Report

**Date:** 2026-09-27  
**Factory Direction:** v28  
**Lane:** evaluation  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** MONITORING  
**Config Hash:** `b51701f5a9c11692` (frozen harness v3)

---

## Executive Summary

All three machine-executable sub-questions from factory direction v28 are **COMPLETE** for the TF-IDF family (8 representations) at 174k scale:

1. **Full 12-benchmark formal suite** — COMPLETE, re-verified with exact reproduction
2. **Citation heritage benchmark** — COMPLETE, validated on frozen 2,040 pair pool
3. **v17b label normalization** — COMPLETE, differential effect re-verified

The evaluation lane remains in **MONITORING** mode, actively watching for 174k dense embeddings, citation role embeddings, and linear hybrid embeddings from the legal-distance lane. No new awaited representations have landed since the last verification.

---

## Sub-Question 1: Full 12-Benchmark Formal Suite at 174k Scale

### Status: ✅ COMPLETE & RE-VERIFIED

**Re-verification Date:** 2026-09-27T20:26:10Z  
**Configuration:** Frozen harness v3, exact k-NN on stratified subsample (n=2000), HNSW artifact fix confirmed

| Representation | Verdict | Language Dominance | Jurist Preference | Both Gates |
|---|---|---|---|---|
| cited_decisions_tfidf | **PASS** | 0.5295 ✓ | 0.8010 ✓ | ✓ |
| outcome_tfidf | **PASS** | 0.4527 ✓ | 0.7255 ✓ | ✓ |
| regeste_tfidf | **PASS** | 0.4835 ✓ | 0.6090 ✓ | ✓ |
| cited_outcome_hybrid_0.5 | **PASS** | 0.5164 ✓ | 0.8055 ✓ | ✓ |
| cited_outcome_hybrid_0.7 | **PASS** | 0.5238 ✓ | 0.7975 ✓ | ✓ |
| full_text_tfidf_light | FAIL | 1.0000 ✗ | 0.0000 ✗ | ✗ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 ✗ | 0.0000 ✗ | ✗ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 ✗ | 0.0000 ✗ | ✗ |

**Key Findings:**
- **5/8 representations PASS both adversarial gates** (language dominance < 0.85, jurist pairwise > 0.5)
- **3/8 text-based representations FAIL** due to language dominance ≈ 1.0 (language artifacts dominate)
- Production default `cited_outcome_hybrid_0.5` PASS (lang_dom=0.5164, jurist_pref=0.8055)
- Best representation: `cited_decisions_tfidf` (lang_dom=0.5295, jurist_pref=0.8010)
- Universal failures across ALL 8 reps: hierarchy_coherence, legal_area_clustering, temporal_stability, boilerplate_resistance (corpus/label limitations, not representation defects)

**HNSW Artifact Fix:** CONFIRMED — Exact k-NN on stratified valid subset (n≈1200 with known branch) produces discriminating results (jurist pairwise 0.73–0.80), while HNSW on full 174k corpus masked differences (jurist pairwise ≈ 0.12 for all).

---

## Sub-Question 2: Citation Heritage Benchmark Validation

### Status: ✅ COMPLETE

**Validation Date:** 2026-09-27T20:45:34Z  
**Citation Graph:** 2,105 total citations, 2,019 resolved (95.9%)  
**Frozen Pair Pool:** 2,040 pairs (1,020 positive direct+shared citations, 1,020 negative balanced, seed=42)

| Representation | AUC | Recall@10 | Status |
|---|---|---|---|
| cited_decisions_tfidf | 0.789 | 0.048 | FAIL |
| outcome_tfidf | 0.659 | 0.000 | FAIL |
| regeste_tfidf | 0.488 | 0.003 | FAIL |
| full_text_tfidf_light | 0.898 | 0.053 | FAIL |
| cited_outcome_hybrid_0.5 | 0.759 | 0.050 | FAIL |
| cited_outcome_hybrid_0.7 | 0.775 | 0.049 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.872 | 0.035 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.851 | 0.035 | FAIL |

**Thresholds (frozen):** AUC ≥ 0.65, Recall@10 ≥ 0.2  
**Result:** All 8 TF-IDF representations **FAIL** recall@10 threshold despite some passing AUC. Pattern consistent with partial dense evaluations (center-projected 64/128/768dim: AUC ~0.905, recall@10 = 0.000; raw multilingual-e5: AUC 0.911, recall@10 = 0.014).

**Infrastructure:** Pipeline ready for 174k dense embeddings when available.

---

## Sub-Question 3: v17b Label Normalization Generalization

### Status: ✅ COMPLETE & RE-VERIFIED

**Re-verification Date:** 2026-09-27T20:49:26Z  
**Labels:** 85,819 normalized (49.3% of 173,963 decisions), 214 → 164 unique legal_area labels (23.4% reduction)  
**Cross-lingual concepts merged:** 32 (e.g., `Verfahrensrecht/Procédure/Diritto processuale`)

### Differential Effect: CONFIRMED

| Representation | Hierarchy Ratio | Zoom Fine Ratio | Legal Area Ratio |
|---|---|---|---|
| **cited_decisions_tfidf** | **1.057** ✓ | **1.038** ✓ | **1.062** ✓ |
| **outcome_tfidf** | **1.046** ✓ | **1.083** ✓ | **1.044** ✓ |
| regeste_tfidf | 1.000 | **1.103** ✓ | 1.017 |
| **cited_outcome_hybrid_0.5** | **1.056** ✓ | **1.037** ✓ | **1.063** ✓ |
| **cited_outcome_hybrid_0.7** | **1.053** ✓ | **1.046** ✓ | **1.058** ✓ |
| full_text_tfidf_light | 1.000 | **0.668** ✗ | 0.973 |
| regeste_full_text_hybrid_0.5 | 1.000 | **0.661** ✗ | 0.969 |
| regeste_full_text_hybrid_0.7 | 1.000 | **0.695** ✗ | 0.963 |

**Interpretation:**
- **Citation-based representations IMPROVE** across all metrics (hierarchy +4–6%, zoom_fine +3–8%, legal_area +4–6%)
- **Text-based representations DEGRADE zoom_fine** by 30–34% (hierarchy unchanged, legal_area slightly degraded)
- Even normalized, best hierarchy purity (0.55) < 0.7 threshold — fine-grained legal_area labels remain insufficient for hierarchy benchmarks at 174k

---

## Monitoring Status

**Monitor Script:** `monitor_and_evaluate_174k.py`  
**Check Count:** 169  
**Last Check:** 2026-09-27T20:50:51Z  
**No new awaited representations detected**

### Awaited Representations (from legal-distance)

| Category | Representations | Status |
|---|---|---|
| Dense embeddings | center_projected_768dim, center_projected_64dim, center_projected_128dim, linear_metric_epoch4, mahalanobis_metric_epoch4, hybrid_stabilized_epoch1, hybrid_v2_epoch3 | ⏳ Not landed |
| Citation roles | citation_role_citing_alpha0.3, citation_role_following_alpha0.3, citation_role_criticizing_alpha0.3 | ⏳ Not landed |
| Linear hybrids | linear_citation_concat, linear_hybrid05_concat | ⏳ Not landed |

### Legal-Distance Dense Embeddings Progress

| Status | Years | Decisions | Notes |
|---|---|---|---|
| **ACCEPTED** | 2000–2002 (3/26) | ~19,441 | Only 3 years promoted to accepted state |
| **Checkpoints** | 2003–2019 (17/26) | ~137,325 | PENDING AUDIT — not citable as accepted fact |
| **Not started** | 2020–2025 (6/26) | — | Year-split execution pending |

**Per factory direction v28:** Monitor scans only final concatenated directories in accepted state, not checkpoints.

---

## Infrastructure Readiness (All Verified)

| Component | Status | Notes |
|---|---|---|
| Formal suite script | ✅ OPERATIONAL | `run_174k_formal_suite.py` verified 2026-09-27T20:26:10 |
| Scalable NN (exact k-NN + HNSW) | ✅ OPERATIONAL | Exact k-NN on stratified subsample for adversarial; HNSW for full-corpus |
| Citation heritage pipeline | ✅ READY | Frozen 2,040 pair pool, 95.9% resolution, re-verified |
| v17b normalization pipeline | ✅ READY | Differential effect reproduced across all 8 TF-IDF reps |
| Metadata 174k | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% coverage |
| Monitor script | ✅ ACTIVE | Enhanced scan paths, correct detection logic |

---

## Blockers (External Dependencies)

1. **Dense embeddings at 174k** — Blocked on legal-distance lane audit promotion (years 2003–2019 pending)
2. **Citation role embeddings** — Not yet computed at 174k scale
3. **Linear hybrid embeddings** — Not yet computed at 174k scale
4. **Jurist human study** — Framework ready; requires 5–10 Swiss jurists (repository owner responsibility)

---

## Recommendation

**CONTINUE MONITORING** — The evaluation lane has completed all machine-executable work for currently available representations. The monitor script will automatically detect and evaluate new 174k representations as they land in the legal-distance accepted state. No additional same-question cycle is justified until new representations are available.

**Next Action:** Wait for legal-distance lane to promote 174k dense embeddings (years 2003–2019 through audit) and/or produce citation role/linear hybrid embeddings at full 174k scale.

---

## Evidence References

- Formal suite results: `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json`
- Citation heritage pairs: `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json`
- Citation heritage embeddings: `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json`
- v17b normalization: `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json`
- Partial dense evaluations: `evaluation/results/174k/dense_partial_2000_2015/dense_partial_2000_2015_eval_latest.json`
- Monitor state: `evaluation/state/monitor_174k_state.json`

---

*Report generated: 2026-09-27T20:50:51Z*  
*Lane state: evaluation/state/evaluation_state.json*