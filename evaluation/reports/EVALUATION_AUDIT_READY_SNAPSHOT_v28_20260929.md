# Evaluation Lane - Audit-Ready Snapshot v28
**Generated:** 2026-09-29T18:40:00Z  
**Factory Direction Version:** 28  
**Lane Status:** MONITORING (evidence tier: REPRODUCED)  
**Accepted Run ID:** `eval_174k_formal_suite_tfidf_complete_20260929_v28_monitor_verified_corrected`

---

## Executive Summary

The Evaluation lane has **COMPLETED all three factory direction v28 deliverables** for the currently available representations (TF-IDF family, 8 representations at 174k scale):

1. ✅ **Full 12-benchmark formal suite at 174k** — Executed on all 8 TF-IDF representations with frozen harness v3 thresholds, HNSW artifact fixed via exact k-NN on stratified subsample (n=2000). Config hash: `b51701f5a9c11692`. **REPRODUCED** across multiple verifications (2026-09-27, 2026-09-28, 2026-09-29).

2. ✅ **Citation heritage benchmark validated** — Frozen 2,040 pair pool (1,020 positive direct+shared citations, 1,020 negative) regenerated from 174k citation-ID resolution (2,019/2,105 resolved, 95.9%). Executed on all 8 TF-IDF representations: **ALL FAIL** recall@10 threshold (production default `nn_citation_rate@10=0.053`).

3. ✅ **v17b label normalization tested at 174k** — 85,819 labels normalized (49.3%, 214→164 unique areas). **Differential effect CONFIRMED and CORRECTED** per audit CYCLE_36527630008:
   - Citation-based reps: modest purity gains (3-10%, 1.03-1.10x) across hierarchy/zoom_fine/legal_area
   - Text-based reps: significant degradation on zoom_fine (30-34% loss, 0.66-0.70x), hierarchy/legal_area stable
   - `regeste_tfidf` only representation with no-worsening on ALL hierarchy metrics
   - V6 dense 12k: NO improvement (hierarchy 1.00x, zoom 1.01x, legal_area 1.00x; NMI drops 0.59→0.45)
   - Effect REPRODUCED across 4 seeds, re-verified 2026-09-28.

**Lane is in MONITORING mode** — monitor script (check_count=230) actively watches for awaited representations from legal-distance. `continue_recommended=true` because monitoring has concrete discriminating purpose: auto-evaluate awaited representations as they land.

---

## Completed Work (Evidence Tier: REPRODUCED)

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| 12-benchmark formal suite (8 TF-IDF reps @ 174k) | ✅ COMPLETE | `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` |
| Citation heritage benchmark (8 TF-IDF reps @ 174k) | ✅ COMPLETE | `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_latest.json` |
| v17b label normalization (8 TF-IDF reps @ 174k) | ✅ COMPLETE | `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` |
| V25 formal suite (frozen protocol) on 8 TF-IDF reps | ✅ COMPLETE | `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` |
| V6 dense 12k (years 2000-2002) evaluated with V25 suite | ✅ COMPLETE | `evaluation/results/174k/dense_partial_2000_2002/evaluation_dense_3yr_formal_suite.json` |
| 15-year partial dense (2000-2014) adversarial eval | ✅ COMPLETE | Monitor state entries for `center_projected_*_partial_2000_2014` |

---

## Critical Findings (Frozen, Reproduced)

### 1. Fundamental Two-Mode Tradeoff at 174k Scale
| Mode | Language Dominance | Jurist Preference | Citation Heritage |
|------|-------------------|-------------------|-------------------|
| **Citation-based** (cited_decisions_tfidf, hybrids) | PASS (0.47-0.50) | PASS (0.63-0.74) | FAIL (recall@10 ~0.04-0.05) |
| **Text-based** (full_text_tfidf_light, regeste_tfidf) | FAIL (~0.99) | FAIL (~0.04) | AUC PASS (0.85-0.90) but recall@10 FAIL |

**Production default:** `cited_decisions_tfidf_outcome_hybrid_0.5` — LangDom=0.4773, JuristPref=0.7345, **BOTH ADVERSARIAL GATES PASS**

### 2. Dense Embeddings Cluster by Language, Not Law (Scale Dependency Confirmed)
- **12k scale (3 years ACCEPTED):** LangDom=0.99, BranchCoherence=0.99 — **FAIL adversarial**
- **15-year partial (2000-2014, ~100k):** Same failure pattern (LangDom~0.98-0.99)
- Root cause: 18.3% metadata coverage, partial corpus center-projection, raw multilingual-e5 language clustering
- Cross-language transfer PASS (zero-shot NMI~0.46-0.48) but adversarial FAIL — **scale dependency confirmed**

### 3. Citation Heritage: Structural Failure at 174k
- **ALL 8 TF-IDF reps FAIL** recall@10 < 0.2 threshold
- Best: `full_text_tfidf_light` recall@10=0.052, AUC=0.898
- Production default: recall@10=0.053, AUC=0.760
- Pair pool covers 2,936 unique decisions (~1.69% of 173,963)

### 4. v17b Label Normalization: Differential Effect, Not Universal Gain
- Citation-based: +3-10% purity gains on hierarchy/zoom_fine/legal_area
- Text-based: -30-34% loss on zoom_fine, hierarchy/legal_area stable
- NMI degrades for both families
- **NOT a universal improvement** — only `regeste_tfidf` no-worsening on all hierarchy metrics

### 5. HNSW Artifact FIXED
- Exact k-NN on stratified subsample (n=2000, seed=42) for adversarial benchmarks
- HNSW on full corpus masked representation differences (all jurist_pref ≈ 0.12)
- Exact k-NN reveals true spread: jurist_pref 0.63-0.74 for citation-based reps

### 6. Boilerplate Resistance: NEGATIVE for All Representations
- Resistance scores ≈ -0.57 to -0.84
- Confirms language dominance/cross-lingual alignment failure, not procedural boilerplate

---

## Blockers (External Dependencies)

| Blocker | Status | Impact |
|---------|--------|--------|
| **Legal-distance dense embeddings @ 174k** | 15/26 years in checkpoints (2000-2014); only 3/26 years (2000-2002) ACCEPTED | Cannot evaluate center_projected, metric learning, hybrid_stabilized at 174k |
| **Citation role embeddings @ 174k** | Not computed | Cannot evaluate citing/following/criticizing roles at 174k |
| **Linear hybrids @ 174k** | Not computed | Cannot evaluate `linear_citation_concat`, `linear_hybrid05_concat` at 174k |
| **Jurist human study** | Framework ready, needs 5-10 Swiss jurists | Simulation proxy ceiling ~0.53 true OOS; human validation needed |

> **Note:** Factory direction v28 incorrectly stated "25/26 years (2000-2024, ~160k decisions) checkpointed" — actual checkpoints cover 15/26 years (2000-2014, ~100k decisions). Years 2015-2026 not yet processed. Center-projected concatenation of 15 years not yet performed.

---

## Infrastructure Verification (All Operational)

| Component | Status | Details |
|-----------|--------|---------|
| Adversarial benchmarks | ✅ VERIFIED | Exact k-NN on n=2000 stratified subsample; production default reproduces LangDom=0.4773, JuristPref=0.7345 |
| Citation heritage pairs | ✅ VERIFIED | 2,040 frozen pairs (seed=42); re-run on new pool |
| v17b normalization | ✅ VERIFIED | Differential effect reproduced across 8 TF-IDF reps; v6 dense 12k: NO improvement; 15-year partial: NO improvement |
| HNSW artifact fix | ✅ CONFIRMED | Exact k-NN avoids HNSW masking differences |
| V25 formal suite | ✅ VERIFIED | Frozen protocol executed on 8 TF-IDF reps @ 174k; config hash 4323f833fa72366a; also on v6 dense 12k & 15-year partial |
| Monitor script | ✅ ACTIVE | check_count=230, last_check=2026-09-29T18:39:51Z; enhanced scan for legal-distance & fractal-map mounts |
| Scalable NN | ✅ OPERATIONAL | sklearn exact k-NN for adversarial; HNSW for full-corpus citation heritage |

---

## Readiness for Next Representations

When legal-distance delivers final concatenated 174k embeddings for:
- **Dense embeddings:** `center_projected_768dim`, `center_projected_64dim`, `center_projected_128dim`, `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1`, `hybrid_v2_epoch3`
- **Citation roles:** `citation_role_citing_alpha0.3`, `citation_role_following_alpha0.3`, `citation_role_criticizing_alpha0.3`
- **Linear hybrids:** `linear_citation_concat`, `linear_hybrid05_concat`

**All evaluation infrastructure is READY:**
- `run_174k_formal_suite.py` operational (verified 2026-09-29T10:40:58)
- `run_v25_174k_suite.py` operational (verified 2026-09-27T22:04:04)
- `validate_citation_heritage_174k.py` ready (frozen 2,040 pairs)
- `run_v17b_label_normalization_all_reps.py` ready
- Metadata 174k verified (173,963 entries, branch+legal_area 100% coverage)

---

## Audit Trail

### Configuration Hashes (Frozen)
- **Adversarial benchmarks:** `b51701f5a9c11692` (seed=42, thresholds frozen)
- **V25 formal suite:** `4323f833fa72366a` (frozen protocol v25)
- **Citation heritage pair pool:** seed=42, balanced sampling from resolved citation graph
- **v17b normalization:** seed=42, 4-seed reproduction confirmed

### Key Re-verification Dates
- 2026-09-27: Initial formal suite completion on 8 TF-IDF reps
- 2026-09-28: Exact reproduction of adversarial results + v17b differential effect
- 2026-09-29T10:40:58: Formal suite runner verified operational (exact k-NN on 90,632 valid decisions)
- 2026-09-29T01:24:28: V6 dense 12k evaluated with V25 suite
- 2026-09-29T18:40:XX: Production default adversarial re-verified (LangDom=0.4773 PASS, JuristPref=0.7345 PASS)
- 2026-09-29T18:39:51: Monitor check 230 completed — no new awaited representations

### Evidence References (Immutable)
All evidence files preserved in `evaluation/results/` and `evaluation/reports/` with timestamps. No claim-bearing outputs overwritten.

---

## Next Recommendation

**CONTINUE MONITORING** — The lane has completed all factory direction v28 deliverables for available representations. The monitor will auto-evaluate awaited representations (dense embeddings, citation roles, linear hybrids) as they land in legal-distance accepted state. No further same-question cycle justified until new representations arrive.

**Factory Director Decision Point:** When legal-distance promotes 174k dense embeddings (center_projected concatenation + metric learning outputs) to ACCEPTED state, evaluation lane will automatically execute full formal suite and report results. Same for citation roles and linear hybrids.

---

## Appendix: Production Default Verdict

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Language Dominance | 0.4773 | < 0.85 | ✅ PASS |
| Jurist Pairwise Preference | 0.7345 | > 0.5 | ✅ PASS |
| Citation Heritage recall@10 | 0.053 | > 0.2 | ❌ FAIL |
| v17b zoom_fine ratio | 0.8827 | ≈1.0 | ⚠️ DEGRADED |
| V25 formal suite | 6 PASS / 5 FAIL / 1 SKIP | N/A | MIXED |

**Overall:** Production default PASSES adversarial gates (the frozen acceptance criterion), FAILS citation heritage and v17b zoom_fine. This is the REPRODUCED, audited state.