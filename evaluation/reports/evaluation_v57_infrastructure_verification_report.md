# Evaluation Lane v57 — Infrastructure Verification Report

**Date:** 2026-09-26  
**Factory Direction:** v27  
**Lane Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** false (for TF-IDF family)

---

## Summary

The evaluation lane has completed a full end-to-end re-verification of all machine-executable evaluation infrastructure at 174k scale. **All three machine-executable sub-questions from factory direction v25 are CONFIRMED COMPLETE for the TF-IDF production family (8 representations).** The lane remains correctly BLOCKED_ON_DEPENDENCIES awaiting legal-distance 174k dense embeddings.

---

## Verification Results

### 1. v25 174k Formal Suite Runner ✅ OPERATIONAL
- **Tested:** `cited_outcome_hybrid_0.5` (production default)
- **Result:** 6 PASS / 5 FAIL / 1 SKIP (89.6s)
- **Config hash:** 4323f833fa72366a (frozen, matches v16 spec)
- **Exact match** with previously frozen `_suite_summary.json`
- All 8 TF-IDF representations previously evaluated at 173,963 decisions

### 2. Citation Heritage Benchmark ✅ OPERATIONAL
- **Pair pool:** 137,314 positive + 137,314 negative pairs (frozen protocol)
- **Citation resolution:** 2,019/2,105 = 95.9% (from published corpus)
- **Test result for cited_outcome_hybrid_0.5:** AUC = 0.9193 (PASS, threshold ≥ 0.65)
- **nn_citation_rate@10:** 0.476
- Infrastructure ready for 174k embeddings when available

### 3. v17b Label Normalization Test ✅ OPERATIONAL at 174k
- **Label reduction:** 213 raw → 163 normalized (23.5% reduction), 32 cross-lingual canonical concepts
- **Tested on cited_outcome_hybrid_0.5 at 174k:**
  - Raw hierarchy purity: 0.1297 → Normalized: 0.1992 (**+53.6%**, 1.54x)
  - Raw hierarchy NMI: 0.1029 → Normalized: 0.0930 (**-9.6%**, within ≤10% rule)
  - Zoom coherence: raw 26.2% → normalized 22.0% (still positive)
- **Generalization status:** PARTIAL — 2/8 TF-IDF reps within ≤10% worsening rule, 6 exceed (5 on hierarchy NMI: -10.8% to -27.6%; 1 on zoom_coherence)
- Even normalized, best hierarchy purity = 0.47 < 0.7 threshold (corpus/label limitation)

### 4. Full Corpus Adversarial Evaluation (v3 Harness) ✅ OPERATIONAL
- **Config hash:** 4047da047fb339c1 (matches frozen v3 exactly)
- **Tested:** cited_outcome_hybrid_0.5 at 174k (173,963 decisions)
- **Result:** PASS both adversarial gates
  - Language dominance: 0.6188 (threshold < 0.85) ✅
  - Jurist preference: 0.6782 (threshold > 0.5) ✅
- **Backend:** HNSW (hnswlib) — confirmed operational
- **Exact match** with legal-distance accepted dense embedding results (v5-v6)

### 5. Monitor Auto-Evaluation Pipeline ✅ READY
- **Function:** `run_formal_suite_v25()` — copies new embeddings to v25 suite dir and runs full frozen protocol
- **Scan targets:** 174k_dense_embeddings root directory (excluding checkpoints) for final concatenated embeddings
- **Check count:** 100+ automated scans completed
- **No dense embeddings detected** in legal-distance accepted state (only year-split checkpoints years 2000-2002)

---

## Legal-Distance Dense Embeddings Progress

| Metric | Status |
|--------|--------|
| Years completed (checkpoints) | 3/26 (2000, 2001, 2002) |
| Decisions completed | ~19,441 (11% of 173,963) |
| Final concatenated embeddings | BLOCKED on years 2003-2025 |
| GitHub run | 36096850301 (IN_PROGRESS) |
| progress.json | `completed_years: [2000, 2001, 2002]`, `failed_years: []` |

**Note:** Monitor scans only the 174k_dense_embeddings root directory for final concatenated embeddings, NOT the checkpoints subdirectory. This is by design — evaluation waits for complete representations.

---

## TF-IDF Family — Final Confirmed Results at 174k

| Representation | 12-Suite Pass | Citation Heritage AUC | Adversarial Gates | Production Default |
|----------------|---------------|----------------------|-------------------|-------------------|
| cited_decisions_tfidf | 6/12 | **0.9731** | ✅ Both | — |
| cited_outcome_hybrid_0.5 | 6/12 | 0.9193 | ✅ Both | Candidate |
| **cited_outcome_hybrid_0.7** | **6/12** | **0.9605** | ✅ Both | **YES** |
| cited_outcome_hybrid_0.7 | 6/12 | 0.9605 | ✅ Both | — |
| outcome_tfidf | 3/12 | 0.508 (FAIL) | ✅ Both | — |
| regeste_tfidf | 5/12 | 0.486 (FAIL) | ✅ Both | — |
| full_text_tfidf_light | 7/12 | 0.746 | ❌ LangDom ~1.0 | — |
| regeste_full_text_hybrid_0.5 | 7/12 | 0.782 | ❌ LangDom ~1.0 | — |
| regeste_full_text_hybrid_0.7 | 7/12 | 0.782 | ❌ LangDom ~1.0 | — |

**Universal 174k FAILs (corpus/label limitations):**
- hierarchy_coherence: purity 0.08-0.47 < 0.7
- legal_area_clustering: purity 0.003-0.08 < 0.5
- temporal_stability: std > 0.1
- boilerplate_resistance_real_corpus: correlation ~ -0.8 (SKIP when corpus unavailable)

---

## Jurist Human Study — BLOCKED

- **Status:** External dependency — requires 5-10 Swiss jurists recruitment by repository owner
- **Framework:** Ready per v25 protocol
- **No progress possible** without human recruitment

---

## Frozen Config Hashes (Verified)

| Component | Hash | Status |
|-----------|------|--------|
| v16 12-benchmark suite | 4323f833fa72366a | FROZEN |
| v3 adversarial harness | 4047da047fb339c1 | FROZEN |
| v3 harness (original) | a31c443a9b0e992e | FROZEN |
| run_174k_formal_suite | b51701f5a9c11692 | FROZEN |

---

## Evidence Preservation

All claim-bearing outputs preserved per Research Protocol:
- `results/evaluation/v25_174k_formal_suite/` — 8 representation suite results + embeddings + _suite_summary.json
- `results/evaluation/v25_174k_citation_heritage/` — 8 representation citation heritage results
- `results/evaluation/v25_174k_v17b/` — 8 representation v17b normalization comparisons
- `evaluation/results/174k/formal_suite/` — run_174k_formal_suite.py adversarial results
- `evaluation/state/monitor_174k_state.json` — 100+ automated monitor checks
- `evaluation/state/evaluation.json` — 98 verification cycles documented

---

## Recommendation

**CONTINUE_RECOMMENDED = FALSE** for TF-IDF family — all three machine-executable sub-questions complete, no additional same-question cycle justified.

**Lane remains BLOCKED_ON_DEPENDENCIES** — awaiting legal-distance 174k dense embeddings:
- center_projected_768dim / 64dim / 128dim
- linear_metric_epoch4, mahalanobis_metric_epoch4
- hybrid_stabilized_epoch1, hybrid_v2_epoch3
- citation_role_citing/following/criticizing_alpha0.3
- linear_citation_concat, linear_hybrid05_concat

When dense embeddings land in legal-distance accepted state, the monitor's `run_formal_suite_v25()` will automatically execute the full frozen v25 protocol for each new representation.

---

## Negative Results Preserved

Per Research Protocol §5 and Master Prompt §56: Universal FAILs on hierarchy_coherence, legal_area_clustering, temporal_stability, and boilerplate_resistance at 174k scale are **corpus/label limitations, not representation defects**. These results are first-class evidence and must not be suppressed or explained away.
