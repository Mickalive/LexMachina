# Evaluation Lane — Verification Report (Factory Direction v28)

**Date:** 2026-09-27  
**Lane:** evaluation  
**Direction Version:** 28  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false

---

## Executive Summary

The evaluation lane has **completed all three machine-executable sub-questions** for the TF-IDF family at 174k scale per factory direction v28. The lane is correctly blocked waiting for legal-distance to deliver full 174k dense embeddings (only 3/26 years ACCEPTED; years 2003-2019 pending audit).

This verification run confirms:
1. **Formal suite reproducibility**: `run_174k_formal_suite.py` executed successfully, `cited_decisions_tfidf` reproduced exactly (lang_dom=0.5295 PASS, jurist_pref=0.8020 PASS, verdict=PASS).
2. **Monitor infrastructure operational**: `monitor_and_evaluate_174k.py` correctly detects 8/8 TF-IDF representations completed, 0/12 awaited representations available.
3. **HNSW artifact fix validated**: Exact k-NN on stratified subsample (n=2000) produces consistent adversarial benchmark results.

---

## Completed Sub-Questions (All COMPLETE)

### 1. Full 12-Benchmark Formal Suite at 174k Scale ✅

| Representation | Verdict | Lang Dominance | Jurist Preference | Both Adv. Pass |
|----------------|---------|----------------|-------------------|----------------|
| cited_decisions_tfidf | **PASS** | 0.5295 (PASS) | 0.8020 (PASS) | ✅ |
| outcome_tfidf | **PASS** | 0.4527 (PASS) | 0.7255 (PASS) | ✅ |
| regeste_tfidf | **PASS** | 0.4835 (PASS) | 0.6090 (PASS) | ✅ |
| cited_outcome_hybrid_0.5 | **PASS** | 0.5164 (PASS) | 0.8055 (PASS) | ✅ |
| cited_outcome_hybrid_0.7 | **PASS** | 0.5238 (PASS) | 0.7975 (PASS) | ✅ |
| full_text_tfidf_light | FAIL | 1.0000 (FAIL) | 0.0000 (FAIL) | ❌ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 (FAIL) | 0.0000 (FAIL) | ❌ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 (FAIL) | 0.0000 (FAIL) | ❌ |

**Key findings:**
- 5/8 representations PASS both adversarial gates (language dominance < 0.85, jurist preference > 0.5)
- Best representation: `cited_decisions_tfidf` (highest jurist preference)
- Production default: `cited_outcome_hybrid_0.5` (balanced citation + outcome signals)
- 3 full-text/regeste hybrid representations FAIL due to language dominance = 1.0 (language artifacts dominate)
- Universal failures across all representations: hierarchy_coherence, legal_area_clustering, temporal_stability, boilerplate_resistance — these are corpus/label limitations, not representation defects

**Config hash:** `b51701f5a9c11692` (frozen harness v3 thresholds unchanged)

### 2. Citation Heritage Benchmark Validated ✅

- **Citation graph source:** 174k citation-ID resolution (2,019/2,105 resolved, 95.9%)
- **Frozen pair pool:** 137k pairs (1,020 positive, 1,020 negative)
- **Thresholds:** AUC ≥ 0.65, Recall@10 ≥ 0.2

| Representation | AUC | Recall@10 | Status |
|----------------|-----|-----------|--------|
| cited_decisions_tfidf | 0.7892 | 0.048 | FAIL |
| outcome_tfidf | 0.6575 | 0.000 | FAIL |
| regeste_tfidf | 0.4861 | 0.004 | FAIL |
| full_text_tfidf_light | 0.8969 | 0.053 | FAIL |
| cited_outcome_hybrid_0.5 | 0.7589 | 0.050 | FAIL |
| cited_outcome_hybrid_0.7 | 0.7749 | 0.049 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.8714 | 0.035 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.8504 | 0.035 | FAIL |

**Key finding:** All TF-IDF representations FAIL recall@10 threshold despite some passing AUC. Benchmark infrastructure ready for 174k dense embeddings when available.

### 3. v17b Label Normalization Tested at 174k ✅

- **Raw unique labels:** 214 → **Normalized:** 164 (23.4% reduction)
- **Labels changed:** 85,819 decisions
- **Decisions with legal_area:** 91,193
- **Cross-lingual concepts merged:** 32

**Differential effect confirmed:**
- Citation-based reps: hierarchy purity improves 1.05-1.06x
- Text-based reps (full-text/regeste): zoom_fine purity degrades 0.66-0.69x
- Even normalized, best hierarchy purity = 0.47 < 0.7 threshold

---

## Partial Dense Embeddings Evaluated (Informational)

### 3-Year Partial (2000-2002, ~12k decisions)
- All 3 center_projected variants FAIL adversarial (lang_dom ~0.98, jurist_pref ~0.04)
- Root cause: 18.3% metadata coverage, partial corpus center-projection, raw multilingual-e5 language clustering
- **Not comparable** to 1,200-slice center_projected (which PASS adversarial)

### 16-Year Partial (2000-2015, ~99k decisions) — Significant Improvement
| Representation | Lang Dominance | Jurist Preference | Both Adv. Pass |
|----------------|----------------|-------------------|----------------|
| center_projected_768dim | 0.8774 (FAIL) | 0.297 (FAIL) | ❌ |
| center_projected_64dim | **0.868** (FAIL) | **0.327** (FAIL) | ❌ |
| center_projected_128dim | 0.8746 (FAIL) | 0.302 (FAIL) | ❌ |

**Trajectory:** Language dominance dropped from ~0.98 → ~0.87 (approaching 0.85 threshold); jurist preference rose from ~0.04 → ~0.30 (still below 0.5). Center-projection on larger corpus substantially reduces language artifacts. **Full 174k center-projected evaluation needed for definitive verdict.**

---

## Infrastructure Status

| Component | Status |
|-----------|--------|
| Metadata 174k symlink | ✅ VERIFIED |
| Corpus canonical path (bger_YYYY.jsonl 2003-2025) | ✅ VERIFIED |
| Evaluation harness (frozen v3) | ✅ OPERATIONAL |
| HNSW artifact fix (exact k-NN n=2000) | ✅ CONFIRMED |
| Formal suite script | ✅ OPERATIONAL (verified 2026-09-27T19:29:23Z) |
| Monitor script | ✅ ACTIVE (check_count=162) |
| Test suite | ✅ PASSING |

---

## Blocked Dependencies

| Dependency | Status | Details |
|------------|--------|---------|
| legal-distance: 174k dense embeddings | **BLOCKED** | Only 3/26 years (2000-2002) ACCEPTED; 17/26 years (2003-2019) in checkpoints PENDING AUDIT; years 2020-2025 not yet processed |
| Citation role embeddings (174k) | NOT STARTED | Evaluated at 1200-scale only (v7, v12) |
| Linear hybrids (174k) | NOT STARTED | Evaluated at 1200-scale only (v7, v12) |
| Jurist human study | EXTERNAL BLOCK | 5-10 Swiss jurists needed; framework ready |

---

## Recommendation

**No additional same-question cycle justified.** The evaluation lane has answered its factory direction v28 question completely for available representations. 

- `continue_recommended = false` (correctly set)
- Lane remains `BLOCKED_ON_DEPENDENCIES` until legal-distance promotes full 174k dense embeddings to accepted state
- Monitor script will auto-detect and evaluate new representations when they land in accepted mounts

**Next action:** Factory Director to prioritize legal-distance 174k dense embedding concatenation and audit promotion for years 2003-2019.

---

## Evidence References

All results preserved in:
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` (formal suite)
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` (citation heritage)
- `evaluation/results/v17b_174k_tfidf/v17b_174k_tfidf_latest.json` (v17b normalization)
- `evaluation/state/evaluation.json` (machine-readable lane state)
- `evaluation/state/monitor_174k_state.json` (monitor state)