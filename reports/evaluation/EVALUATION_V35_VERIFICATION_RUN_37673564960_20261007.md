# Evaluation Lane — Factory Direction v35 Verification Run

**Run ID:** EVALUATION_V35_VERIFICATION_RUN_37673564960_20261007  
**GitHub Run:** 37673564960  
**Date:** 2026-10-07  
**Evidence Tier:** ACCEPTED  
**Cycle Status:** COMPLETE (lane frozen, continue_recommended=false)  

---

## Executive Summary

This verification run confirms the evaluation lane remains in its **COMPLETE** state per Factory Direction v35. No new work is justified for the current question; the lane awaits 174k dense embeddings delivery (blocked on corpus lane).

**Key Verification Results:**
1. **Monitor Check #323:** No new awaited 174k representations detected
2. **Adversarial Re-verification:** Working directory TF-IDF production baseline **CONFIRMED INTACT** (LangDom=0.4895 PASS, JuristPref=0.7265 PASS)
3. **Accepted Lane Embeddings:** Still MUTATED post-freeze (JP=0.5560, Δ=-0.1785) — working directory is the canonical frozen baseline
4. **Dense Embedding Criteria:** Validated against 24-year/158k checkpoint evidence; UNVALIDATED at full 174k scale

---

## 1. Monitor Check #323 Results

| Category | Representation | Status |
|----------|----------------|--------|
| **COMPLETED TF-IDF (8/8)** | cited_decisions_tfidf | ✅ Present |
| | outcome_tfidf | ✅ Present |
| | cited_decisions_tfidf_outcome_hybrid_0.5 | ✅ Present |
| | cited_decisions_tfidf_outcome_hybrid_0.7 | ✅ Present |
| | regeste_tfidf | ✅ Present |
| | full_text_tfidf_light | ✅ Present |
| | regeste_full_text_hybrid_0.5 | ✅ Present |
| | regeste_full_text_hybrid_0.7 | ✅ Present |
| **AWAITED Dense (8/8)** | center_projected_768dim | ❌ Not concatenated |
| | center_projected_64dim | ❌ Not concatenated |
| | center_projected_128dim | ❌ Not concatenated |
| | linear_metric_epoch4 | ❌ Not computed |
| | mahalanobis_metric_epoch4 | ❌ Not computed |
| | hybrid_stabilized_epoch1 | ❌ Not computed |
| | hybrid_v2_epoch3 | ❌ Not computed |
| **AWAITED Citation Roles (3/3)** | citation_role_citing_alpha0.3 | ❌ Not at 174k |
| | citation_role_following_alpha0.3 | ❌ Not at 174k |
| | citation_role_criticizing_alpha0.3 | ❌ Not at 174k |
| **AWAITED Linear Hybrids (2/2)** | linear_citation_concat | ❌ Not at 174k |
| | linear_hybrid05_concat | ❌ Not at 174k |

**Legal-Distance Checkpoint Status:** 24/26 years (2000-2023) in checkpoints (~158k decisions). Years 2021-2023 embeddings EXIST and PASS citation heritage quality check (center_projected AUC > 0.75 at 24yr/158k). Only 2024-2026 genuinely missing (no parquet, no embeddings). Center-projected concatenation of 24 years NOT YET PERFORMED. Blockers: bge_<->bger_ ID mapping missing, parquet 2024-2026 missing.

---

## 2. Adversarial Re-verification (Working Directory Embeddings)

**Method:** Exact k-NN on fixed stratified subsample (n=2000, seed=42) — HNSW artifact fix applied

**Production Default:** `cited_decisions_tfidf_outcome_hybrid_0.5` (173,963 decisions, 128-dim)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Language Dominance (k=20) | 0.4895 | < 0.85 | ✅ PASS |
| Jurist Pairwise Preference (k=10) | 0.7265 | > 0.5 | ✅ PASS |
| **Both Gates** | — | — | ✅ **PASS** |

**Configuration Hash:** `b51701f5a9c11692` (exact reproduction of frozen harness v3)

**Comparison with Frozen Baseline (2026-10-02):**

| Metric | Frozen Baseline | This Verification | Delta |
|--------|-----------------|-------------------|-------|
| Language Dominance | 0.4895 | 0.4895 | 0.0000 |
| Jurist Preference | 0.7265 | 0.7265 | 0.0000 |

**WORKING DIRECTORY embeddings reproduce FROZEN baseline exactly.**

---

## 3. Accepted Lane Embeddings Mutation (Confirmed Ongoing)

| Source | Jurist Preference | Delta vs Frozen |
|--------|-------------------|-----------------|
| Frozen Baseline (working dir) | 0.7265 | — |
| ACCEPTED mount (`/tmp/lex_accepted/fractal-map/.../legal_tfidf_embeddings/`) | 0.5560 | -0.1785 |

**Implication:** The ACCEPTED lane embeddings were mutated after the v34 freeze. The working directory embeddings remain the canonical frozen baseline. Product serving must use working directory artifacts.

---

## 4. Dense Embedding Complementary Criteria Status (Frozen)

| Criterion | Threshold | 24yr/158k Evidence | Status | 174k Validation |
|-----------|-----------|-------------------|--------|-----------------|
| Citation Heritage AUC | > 0.75 | 0.792 [0.762, 0.824] | ✅ PASS | BLOCKED |
| Cross-lang Sachverhalt | > 0.20 | 0.282 [0.267, 0.296] | ✅ PASS | BLOCKED |
| Cross-lang Dispositiv | > 0.10 | 0.150 [0.141, 0.160] | ✅ PASS | BLOCKED |
| Cross-lang Erwaegungen | > 0.10 | 0.094 [0.086, 0.102] | ❌ FAIL | BLOCKED |

**Source:** Bootstrap 95% CIs on 24-year/158k legal-distance ACCEPTED checkpoint evidence.

---

## 5. Data Blockers (Unchanged)

| Blocker | Impact | Resolution Required |
|---------|--------|---------------------|
| BGE/bger ID mapping | Cannot align dense embeddings (bge_ IDs) with evaluation metadata (bger_ IDs) | Corpus lane: produce canonical mapping |
| Parquet 2024-2026 | 3 years missing; cannot compute 174k dense embeddings | Corpus lane: generate parquet |
| Section extraction 174k | Cross-lingual validation needs sections at 174k scale | Corpus lane: run section extraction |

---

## 6. Recommendation

**CONTINUE_RECOMMENDED = false** (unchanged)

The evaluation lane has:
- ✅ Frozen TF-IDF 174k evaluation as production baseline (ACCEPTED)
- ✅ Defined and frozen dense embedding complementary view acceptance criteria
- ✅ Verified working directory baseline integrity (this run)
- ✅ Documented accepted lane mutation (ongoing issue)
- ✅ Identified precise data blockers

**Factory Director action required:** Resume corpus lane for BGE/bger ID mapping + parquet 2024-2026 + section extraction at 174k scale. Once dense embeddings are delivered at 174k, a **new evaluation cycle** (not same-question) will validate them against the frozen criteria.

---

## 7. Artifacts Updated

- `evaluation/state/evaluation.json` — Machine-readable lane state (monitor_check_count=323, latest_verification updated)
- `evaluation/state/monitor_174k_state.json` — Monitor state (check_count=323, auto-updated by monitor script)
- This report — Human-readable verification record

All negative results preserved. No claim-bearing outputs overwritten.