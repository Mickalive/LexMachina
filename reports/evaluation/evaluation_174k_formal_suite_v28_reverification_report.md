# Evaluation Lane — 174k Formal Suite Re-verification Report (Factory Direction v28)

**Date:** 2026-09-27  
**Config Hash:** `b51701f5a9c11692` (frozen)  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** BLOCKED_ON_DEPENDENCIES / MONITORING  
**Run ID:** `eval_174k_formal_suite_tfidf_complete_20260927_v28_reverified`

---

## Executive Summary

The evaluation lane has completed a full re-verification of the three machine-executable sub-questions defined in factory direction v28 for the TF-IDF family at 174k scale. All three sub-questions are **COMPLETE** and **REPRODUCED** with exact configuration hash match.

| Sub-question | Status | Key Result |
|--------------|--------|------------|
| (1) Full 12-benchmark formal suite at 174k on 8 TF-IDF reps | ✅ COMPLETE | 5/8 PASS both adversarial gates (HNSW artifact fixed via exact k-NN on stratified subsample n=2000) |
| (2) Citation heritage benchmark on frozen 2,040 pair pool | ✅ COMPLETE | All 8 TF-IDF reps FAIL recall@10 (>0.2 threshold); AUC 0.49-0.90 |
| (3) v17b label normalization on 174k fine-grained legal_area labels | ✅ COMPLETE | Differential effect CONFIRMED: citation-based reps improve 1.04-1.10x, text-based reps degrade zoom_fine 0.66-0.70x |

**Lane remains BLOCKED_ON_DEPENDENCIES** for full 174k dense embeddings (legal-distance: only 3/26 years ACCEPTED; years 2003-2015 pending audit).

---

## 1. Formal Suite Re-verification (12 Benchmarks)

### Configuration (FROZEN)
- **Global seed:** 42
- **Adversarial thresholds:** language_dominance ≤ 0.85, jurist_pairwise ≥ 0.5
- **Cross-language thresholds:** recall ≥ 0.2, cluster_coherence ≥ 0.7
- **HNSW artifact fix:** Exact k-NN on fixed stratified subsample (n=2000, stratified by branch, seed=42)
- **Full-corpus benchmarks:** HNSW on subsamples (temporal: 30k, hierarchy: 15k)

### Results Summary (Exact Reproduction)

| Representation | Verdict | Lang Dom | LD Status | Jurist Pref | JP Status | Both Adv Pass |
|----------------|---------|----------|-----------|-------------|-----------|---------------|
| cited_decisions_tfidf_outcome_hybrid_0.5 | **PASS** | 0.5164 | ✅ | 0.8055 | ✅ | ✅ |
| cited_decisions_tfidf | **PASS** | 0.5295 | ✅ | 0.8020 | ✅ | ✅ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | **PASS** | 0.5238 | ✅ | 0.7975 | ✅ | ✅ |
| outcome_tfidf | **PASS** | 0.4527 | ✅ | 0.7255 | ✅ | ✅ |
| regeste_tfidf | **PASS** | 0.4835 | ✅ | 0.6090 | ✅ | ✅ |
| full_text_tfidf_light | **FAIL** | 1.0000 | ❌ | 0.0000 | ❌ | ❌ |
| regeste_full_text_hybrid_0.5 | **FAIL** | 1.0000 | ❌ | 0.0000 | ❌ | ❌ |
| regeste_full_text_hybrid_0.7 | **FAIL** | 1.0000 | ❌ | 0.0000 | ❌ | ❌ |

**Best representation (passing both gates):** `cited_decisions_tfidf_outcome_hybrid_0.5` (production default)  
**Config hash match:** `b51701f5a9c11692` ✅ exact match across re-runs

### Universal Failures at 174k (Corpus/Label Limitations)
All 8 representations FAIL on these benchmarks — these are **not representation defects**:
- **Hierarchy coherence** — Level 0 NMI ~0.003-0.04, Level 1 NMI ~0.03-0.17, nesting < 0.5
- **Legal area clustering** — Fine-grained labels (164 normalized) too sparse for coherence
- **Temporal stability** — Mean neighbor overlap 0.0-0.78 (HNSW backend variance)
- **Boilerplate resistance** — Resistance scores -0.57 to -0.87 (procedural neighbors dominate)

### Key Benchmark Details

| Benchmark | Production Default (cited_outcome_hybrid_0.5) | Best (cited_decisions_tfidf) |
|-----------|-----------------------------------------------|------------------------------|
| Cross-language retrieval (subsample) | PASS (0.2295) | PASS (0.2497) |
| Cross-language retrieval (full 15k) | PASS (0.2227) | PASS (0.2276) |
| Zero-shot cross-language transfer | FAIL (transfer_gap=0.022) | FAIL (transfer_gap=-0.003) |
| Language-specific quality | FAIL (mean_nmi=0.09) | FAIL (mean_nmi=0.13) |
| Cluster coherence (16 clusters) | FAIL (branch_purity=0.40) | FAIL (branch_purity=0.45) |

---

## 2. Citation Heritage Benchmark Re-verification

### Frozen Pair Pool (Regenerated 2026-09-27)
- **Source:** `/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/citation_graph_resolved.json`
- **Total citations:** 2,105 | **Resolved:** 2,019 (95.9%)
- **Decisions with outgoing citations in 174k:** 174 (0.1%)
- **Positive pairs (direct + shared citations):** 1,020
- **Negative pairs (no citation relation, balanced sampling):** 1,020
- **Seed:** 42 (frozen)

### Results (All 8 TF-IDF Representations FAIL recall@10)

| Representation | AUC | Recall@10 | Recall@5 | Recall@20 | Recall@50 | AP | Status |
|----------------|-----|-----------|----------|-----------|-----------|-----|--------|
| full_text_tfidf_light | 0.8985 | 0.0520 | 0.0363 | 0.0676 | 0.1039 | 0.9222 | FAIL |
| regeste_full_text_hybrid_0.5 | 0.8731 | 0.0353 | 0.0265 | 0.0480 | 0.0735 | 0.8998 | FAIL |
| regeste_full_text_hybrid_0.7 | 0.8517 | 0.0343 | 0.0255 | 0.0471 | 0.0686 | 0.8731 | FAIL |
| cited_decisions_tfidf | 0.7892* | 0.0480* | 0.0324 | 0.0657 | 0.0892 | 0.8172 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 0.7749 | 0.0520 | 0.0353 | 0.0725 | 0.1049 | 0.8056 | FAIL |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 0.7597 | 0.0510 | 0.0382 | 0.0598 | 0.0863 | 0.7813 | FAIL |
| outcome_tfidf | 0.6575 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.6287 | FAIL |
| regeste_tfidf | 0.4861 | 0.0020 | 0.0010 | 0.0029 | 0.0039 | 0.5317 | FAIL |

*\*cited_decisions_tfidf errored at k=100 (HNSW ef/M too small); AUC computed at k=50*

**Key finding:** Citation proximity is preserved in similarity space (AUC 0.49-0.90) but **not recovered in top-10 neighbors** at 174k scale/density for any TF-IDF representation. This pattern is consistent with dense embedding partial evaluations (AUC ~0.90, recall@10 ~0.0).

**Thresholds:** AUC_min=0.65, recall_at_10_min=0.2 (frozen)

---

## 3. v17b Label Normalization Re-verification

### Normalization Statistics (Exact Reproduction)
- **Raw unique legal_area labels:** 214 → **Normalized:** 164 (23.4% reduction)
- **Labels changed:** 85,819 / 173,963 decisions (49.3%)
- **Cross-lingual concepts merged:** 32 (e.g., "Vertragsrecht" + "droit des contrats" → single concept)
- **Avg decisions per raw label:** 428.1 → **Per normalized label:** 559.5

### Differential Effect (Reproduced Across All 8 Reps)

| Representation | Hierarchy Purity Ratio | Zoom Fine Purity Ratio | Legal Area Purity Ratio | Type |
|----------------|------------------------|------------------------|------------------------|------|
| cited_decisions_tfidf | 1.0568 | 1.0381 | 1.0616 | **Citation-based** |
| outcome_tfidf | 1.0458 | 1.0829 | 1.0437 | **Citation-based** |
| regeste_tfidf | 1.0000 | 1.1031 | 1.0173 | **Citation-based** |
| cited_decisions_tfidf_outcome_hybrid_0.5 | 1.0558 | 1.0366 | 1.0627 | **Citation-based** |
| cited_decisions_tfidf_outcome_hybrid_0.7 | 1.0530 | 1.0461 | 1.0583 | **Citation-based** |
| full_text_tfidf_light | 1.0000 | **0.6683** | 0.9732 | **Text-based** |
| regeste_full_text_hybrid_0.5 | 1.0000 | **0.6607** | 0.9694 | **Text-based** |
| regeste_full_text_hybrid_0.7 | 1.0001 | **0.6952** | 0.9634 | **Text-based** |

**Interpretation:**
- **Citation-based representations** (cited_decisions, outcome, hybrids): Benefit from normalization — hierarchy and zoom_fine purity improve 3-10%
- **Text-based representations** (full_text, regeste_full_text hybrids): **Degrade** on zoom_fine (30-34% loss) — normalization merges distinct legal concepts that full_text embeddings had separated
- **Even normalized:** Best hierarchy purity = 0.55 (cited_decisions_tfidf) < 0.7 threshold

---

## 4. Infrastructure Readiness for Next Representations

| Component | Status | Notes |
|-----------|--------|-------|
| Formal suite script | ✅ OPERATIONAL | Re-verified 2026-09-27T21:28:43Z |
| Scalable NN (exact k-NN + HNSW) | ✅ OPERATIONAL | sklearn_exact for adversarial, HNSW for full-corpus |
| Citation heritage pipeline | ✅ READY | Frozen 2,040 pairs, 95.9% resolution |
| v17b normalization pipeline | ✅ READY | Differential effect reproduced |
| Metadata 174k | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% |
| Monitor script | ✅ ACTIVE | check_count=172, last_check 2026-09-27T21:32:23Z |

---

## 5. Blockers and Dependencies

### Critical Path: Legal-Distance 174k Dense Embeddings
| Status | Years | Decisions | Notes |
|--------|-------|-----------|-------|
| **ACCEPTED** | 2000-2002 (3/26) | ~19,441 | Only fully accepted dense embeddings |
| **PENDING AUDIT** | 2003-2019 (17/26) | ~99k | In checkpoints, not promoted to accepted |
| **NOT PROCESSED** | 2020-2025 (6/26) | ~55k | Not yet executed |

**Awaited representations (12):**
- Dense: `center_projected_768dim/128dim/64dim_174k`, `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1`, `hybrid_v2_epoch3`
- Citation roles: `citation_role_citing/following/criticizing_174k`
- Linear hybrids: `linear_citation_concat`, `linear_hybrid05_concat`

### External Dependency
- **Jurist human study:** Framework ready; requires 5-10 Swiss jurists (repository owner responsibility)

---

## 6. Recommendation

**continue_recommended = FALSE** for same-question cycles.  
All three machine-executable sub-questions are **COMPLETE and REPRODUCED** at 174k scale for the TF-IDF family. No additional discriminating purpose exists for another cycle under the same factory direction question.

**Next action:** Factory Director decision on successor question. Lane remains in MONITORING mode — will auto-evaluate awaited representations as they land from legal-distance.

---

## 7. Evidence References (Immutable)

### Formal Suite
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_latest.json` (config hash `b51701f5a9c11692`)
- `evaluation/results/174k/formal_suite/evaluation_174k_formal_suite_20260927_213201.json` (timestamped)

### Citation Heritage
- `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` (frozen 2,040 pairs)
- `evaluation/results/174k_citation_heritage/citation_heritage_174k_embeddings_20260927_213414.json` (re-run on new pool)

### v17b Label Normalization
- `evaluation/results/174k_label_normalization/v17b_label_normalization_174k_latest.json` (all 8 reps, differential effect)

### Infrastructure Scripts
- `evaluation/run_174k_formal_suite.py` (frozen harness v3 + HNSW fix)
- `evaluation/validate_citation_heritage_174k.py` (pair pool generation)
- `evaluation/run_citation_heritage_174k_embeddings.py` (embedding evaluation)
- `evaluation/run_v17b_label_normalization_174k.py` (normalization test)
- `evaluation/monitor_and_evaluate_174k.py` (monitoring)

---

**Report Path:** `reports/evaluation/evaluation_174k_formal_suite_v28_reverification_report.md`  
**State Files:** `evaluation/state/evaluation.json`, `evaluation/state/evaluation_state.json`  
**Monitor State:** `evaluation/state/monitor_174k_state.json` (check_count=172)

---

*End of report — all claim-bearing results frozen, negative results preserved, provenance maintained.*