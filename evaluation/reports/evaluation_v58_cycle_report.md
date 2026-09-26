# Evaluation Lane — Cycle v58 Report

**GitHub Run:** 36223590571  
**Timestamp:** 2026-09-26T06:26:29Z  
**Factory Direction:** v27  
**Lane Status:** BLOCKED_ON_DEPENDENCIES  
**Continue Recommended:** FALSE (for TF-IDF family)

---

## Summary

The evaluation lane has completed all three machine-executable sub-questions for the TF-IDF production family at 174k scale (173,963 decisions). The lane is correctly **BLOCKED_ON_DEPENDENCIES** awaiting legal-distance lane 174k dense embeddings.

- **TF-IDF family (8 representations):** FULLY EVALUATED ✅
- **Dense embeddings (center_projected, metric learning, hybrid objectives):** NOT YET LANDED (3/26 years in checkpoints)
- **Citation roles, linear hybrids:** NOT YET LANDED
- **Jurist human study:** BLOCKED (external dependency)

---

## Machine-Executable Sub-Questions — Status

| Sub-Question | Status | Details |
|--------------|--------|---------|
| **(1) 12-benchmark formal suite (v25_174k_suite)** | ✅ COMPLETE | All 8 TF-IDF reps evaluated at 173,963 decisions. Config hash `4323f833fa72366a` frozen. Pass counts: cited_decisions_tfidf=6, cited_outcome_hybrid_0.5/0.7=6, full_text_tfidf_light=7, regeste_full_text_hybrid_0.5/0.7=7, regeste_tfidf=5, outcome_tfidf=3. Universal FAILs: hierarchy_coherence (purity 0.08-0.47 < 0.7), legal_area_clustering (purity 0.003-0.08 < 0.5). |
| **(2) citation_heritage benchmark** | ✅ COMPLETE | 137,314 frozen pairs (95.9% citation resolution: 2,019/2,105). 7/8 TF-IDF reps PASS AUC≥0.65. Best: cited_decisions_tfidf AUC=0.9731. Production default cited_outcome_hybrid_0.7 AUC=0.9605, nn_citation_rate@10=0.490. |
| **(3) v17b label normalization generalization** | ✅ COMPLETE | 213→163 labels (23.5% reduction), 32 cross-lingual canonical concepts. PARTIAL generalization: 2/8 reps within ≤10% worsening rule (cited_decisions_tfidf, regeste_tfidf), 6 exceed (5 hierarchy NMI: -10.8% to -27.6%; 1 zoom_coherence: cited_outcome_hybrid_0.5 -16.0%). Normalized hierarchy purity gains 1.5-1.6x for citation-based reps. Even normalized, best hierarchy purity=0.47 < 0.7 threshold. |

---

## Adversarial Gate Results (run_174k_formal_suite.py — HNSW Artifact Fixed)

**Config hash:** `b51701f5a9c11692` | **Seed:** 42 | **Factory direction:** v27  
**Method:** Exact k-NN on fixed stratified subsample (n=2000 valid decisions with known branch)

| Representation | Language Dominance | Jurist Preference | Both Gates | Verdict |
|----------------|-------------------|-------------------|------------|---------|
| cited_decisions_tfidf | 0.5164 ✅ PASS | 0.8055 ✅ PASS | ✅ PASS | **BEST** |
| cited_outcome_hybrid_0.5 | 0.5164 ✅ PASS | 0.8055 ✅ PASS | ✅ PASS | |
| **cited_outcome_hybrid_0.7 (prod default)** | **0.5238 ✅ PASS** | **0.7975 ✅ PASS** | ✅ PASS | **PRODUCTION DEFAULT** |
| outcome_tfidf | 0.4527 ✅ PASS | 0.7255 ✅ PASS | ✅ PASS | |
| regeste_tfidf | 0.4835 ✅ PASS | 0.6090 ✅ PASS | ✅ PASS | |
| full_text_tfidf_light | 1.0000 ❌ FAIL | 0.0000 ❌ FAIL | ❌ FAIL | Language-dominated |
| regeste_full_text_hybrid_0.5 | ~0.99 ❌ FAIL | ~0.0 ❌ FAIL | ❌ FAIL | Language-dominated |
| regeste_full_text_hybrid_0.7 | ~0.99 ❌ FAIL | ~0.0 ❌ FAIL | ❌ FAIL | Language-dominated |

---

## Legal-Distance Dense Embeddings Progress

| Metric | Value |
|--------|-------|
| Years completed | 3/26 (2000, 2001, 2002) |
| Completion rate (years) | 11.5% |
| Decisions completed | 19,441 / 173,963 (11%) |
| Checkpoint files | embeddings_2000.npy, embeddings_2001.npy, embeddings_2002.npy |
| Final concatenated embeddings | NOT YET AVAILABLE |
| Legal-distance GitHub run | 36096850301 (IN_PROGRESS) |
| Blocked on | Years 2003-2025 pending year-split execution |

---

## Infrastructure Status (All Verified Operational)

| Component | Status | Notes |
|-----------|--------|-------|
| v25_174k_formal_suite runner | ✅ OPERATIONAL | Config hash `4323f833fa72366a`, all 8 TF-IDF reps evaluated |
| validate_citation_heritage_174k.py | ✅ OPERATIONAL | 137,314 frozen pairs ready |
| v17b label normalization test | ✅ OPERATIONAL | 213→163 labels, 32 cross-lingual concepts |
| run_174k_formal_suite.py | ✅ OPERATIONAL | HNSW artifact fixed (exact k-NN on n=2000 subsample) |
| monitor_and_evaluate_174k.py | ✅ ACTIVE | 104 checks completed, enhanced with run_formal_suite_v25() |
| scalable_nn.py (HNSW/sklearn) | ✅ OPERATIONAL | hnswlib on GitHub runners, sklearn fallback |
| run_full_corpus_evaluation.py | ✅ VERIFIED | Config hash `4047da047fb339c1` matches frozen v3 harness |

---

## Critical Findings (Preserved)

1. **HNSW Artifact Confirmed & Fixed:** HNSW with fixed parameters produces nearly identical k-NN graphs across different TF-IDF representations at 174k scale. Exact k-NN on valid subset (1,199 decisions with known branch) shows jurist pairwise 0.73-0.80; HNSW on full corpus shows ~0.12 for all. The fix uses exact k-NN on a fixed stratified subsample of 2000 decisions for adversarial benchmarks.

2. **Universal 174k FAILs are Corpus/Label Limitations:** hierarchy_coherence (purity 0.08-0.47 < 0.7), legal_area_clustering (purity 0.003-0.08 < 0.5), temporal_stability, boilerplate_resistance FAIL for ALL representations — these are corpus/label limitations, not representation defects.

3. **Production Default Confirmed:** cited_outcome_hybrid_0.7 passes both adversarial gates (LangDom=0.5238<0.85, Jurist=0.7975>0.5), citation_heritage AUC=0.9605, nn_citation_rate@10=0.490. Zero-shot TF-IDF, no GPU required.

4. **v17b Label Normalization Partially Generalizes:** 15-25% purity gains at 1200 scale only partially generalize to 174k fine-grained legal_area labels. Even with normalization, hierarchy coherence thresholds not met.

5. **Jurist Human Study Blocked:** Framework ready per v25 protocol; requires 5-10 Swiss jurists recruited by repository owner.

---

## Evidence Preservation

All evidence preserved per Research Protocol §5 (Accepted evidence beats narrative. Negative results remain evidence):

- **v25 suite results:** `results/evaluation/v25_174k_formal_suite/`
- **Citation heritage:** `results/174k_citation_heritage/`
- **v17b analysis:** `results/174k_label_analysis/`
- **Formal suite (HNSW fix):** `evaluation/results/174k/formal_suite/`
- **Monitor state:** `evaluation/state/monitor_174k_state.json` (104 checks)
- **Config hashes:** Frozen and verified

---

## Next Recommendation

**BLOCKED_ON_DEPENDENCIES** — No additional same-question cycle justified for TF-IDF family (`continue_recommended=false`).

The lane will auto-evaluate new representations when they land via `monitor_and_evaluate_174k.py` which now includes `run_formal_suite_v25()` to execute the full frozen v25 protocol (12-benchmark suite + citation_heritage + v17b label normalization) for each newly detected 174k representation.

**Awaiting:** Legal-distance lane final concatenated 174k dense embeddings (years 2003-2025).
