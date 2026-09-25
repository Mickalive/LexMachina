# Evaluation v42 Cycle Report

**Date**: 2026-09-25T09:59:00Z  
**Factory Direction Version**: 27  
**Lane Status**: BLOCKED_ON_DEPENDENCIES  
**Evidence Tier**: REPRODUCED  
**GitHub Run**: local_verification_20260925_v42

---

## Summary

The evaluation lane completed verification cycle v42. No new 174k dense embeddings detected in legal-distance accepted state. TF-IDF family evaluation at 174k scale remains COMPLETE across all three machine-executable sub-questions. All evaluation infrastructure verified operational. Monitor active (check #64) with auto-evaluation capability for when dense embeddings land.

---

## Verifications Performed

### 1. Monitor Scan (Check #64)
- **Target**: `/tmp/lex_accepted/legal-distance/legal_distance/results` (v5-v14, fractal_map, 174k_dense_embeddings)
- **Result**: No 174k dense embeddings detected
- **Checkpoints Status**: Years 2000-2013 completed (7,652 decisions, ~4.4% of 173,963) in `174k_dense_embeddings/checkpoints/`; no final concatenated embeddings in parent directory
- **Blocker**: Years 2014-2025 failing (gh run 36096850301 IN_PROGRESS) — likely 65-min job ceiling/resource constraints on GitHub runners

### 2. Monitor Script Repair
- Fixed JSON syntax error in `monitor_174k_state.json` (extra closing brace)
- Monitor now loads/runs correctly

### 3. Full Corpus Adversarial Evaluation Infrastructure
- `run_full_corpus_evaluation.py` config hash `4047da047fb339c1` verified (matches frozen v3 harness exactly)
- `scalable_nn.py` HNSW backend OPERATIONAL (hnswlib available, `EXACT_NN_THRESHOLD=10000`)
- Production default `cited_outcome_hybrid_0.7` at full 174k scale (173,963 decisions): **PASS both adversarial gates** (LangDom=0.569<0.85, BranchCoherence=0.356>0.3), backend=hnswlib

### 4. v25 174k Formal Suite Runner
- Config hash `4323f833fa72366a` verified
- All 8 TF-IDF representations previously evaluated at 174k scale
- `suite_summary.json` exists with 8 entries
- `run_formal_suite_v25()` function operational — copies embeddings to v25 suite directory and executes full frozen protocol (12-benchmark + citation_heritage + v17b)

### 5. Citation Heritage Benchmark Infrastructure
- 137,314 frozen pairs in `citation_pairs_174k_full.json` ready
- 95.9% citation resolution from 2,019/2,105 resolved citations
- Production default `cited_outcome_hybrid_0.7`: AUC=0.9605, nn_citation_rate@10=0.490, **PASS** (threshold 0.65)

### 6. v17b Label Normalization Test Infrastructure
- 213 raw → 163 normalized labels (23.5% reduction), 32 cross-lingual canonical concepts
- `normalize_labels` function working, conservative cross-lingual canonical map frozen
- PARTIAL generalization confirmed at 174k across 8 TF-IDF reps: purity gains 1.5-1.6x for citation-based reps, NMI worsening >10% rule violated for 5/8 citation hybrids

### 7. Legal-Distance Pipeline Progress
- 14/26 years completed in checkpoints (2000-2013, 7,652 decisions)
- Final concatenation blocked on years 2014-2025
- Corpus artifacts verified available at expected paths:
  - `/tmp/lex_accepted/corpus/corpus/normalization/canonical/bge_YYYY.jsonl` (2000-2025)
  - `/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/metadata_174k.json`
- ARTIFACT PUBLICATION GAP noted in v37 was **incorrect** — paths exist and contain data

### 8. TF-IDF Family 174k Evaluation Status
- **CONFIRMED COMPLETE** across all three machine-executable sub-questions:
  1. 12-benchmark formal suite at 174k scale (frozen harness v3 thresholds)
  2. Citation heritage benchmark (137,314 pairs, frozen protocol)
  3. v17b label normalization generalization test at 174k
- No additional same-question cycle justified (`continue_recommended=false`)

### 9. External Dependencies
- **Jurist human study**: BLOCKED (requires 5-10 Swiss jurists recruitment by repository owner; framework ready)

### 10. Monitor Scope Note
- Monitor scans **legal-distance accepted state only** per factory direction
- TF-IDF 174k embeddings exist in product lane (`/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/` and `tfidf_embeddings/`) but are not in monitor scope
- This is correct — monitor watches for NEW representations from legal-distance lane

---

## Critical Findings (Unchanged from v41)

| Finding | Status |
|---------|--------|
| Production default confirmed | `cited_outcome_hybrid_0.7`: zero-shot TF-IDF, no GPU required, passes both adversarial gates at 174k |
| Scale extrapolation risk | TF-IDF jurist pairwise COLLAPSED 0.79→0.12 from 1200→174k (per factory direction v27 director note) — **NOTE**: v40 re-evaluation showed Jurist=0.6675 for production default at 174k; discrepancy under investigation |
| Universal 174k FAILs | `hierarchy_coherence` (purity 0.08-0.47 < 0.7), `legal_area_clustering` (purity 0.003-0.08 < 0.5), `boilerplate_resistance_real_corpus` (SKIP/FAIL) — corpus/label limitations |
| Universal 174k PASSes | `adversarial_falsification`, `multilingual_invariance`, `cross_language_pairs`, `collapse_check`, `temporal_stability` (for TF-IDF family) |
| Citation heritage | 7/8 TF-IDF reps PASS AUC≥0.65; best `cited_decisions_tfidf` AUC=0.9731 |
| v17b normalization | PARTIAL generalization: purity gains but NMI worsening >10% for citation hybrids |

---

## Next Steps

1. **Legal-distance lane**: Complete 174k dense embeddings (years 2014-2025, final concatenation)
2. **Evaluation lane**: Auto-evaluate via `run_formal_suite_v25()` when dense embeddings land in legal-distance accepted state
3. **Jurist study**: Recruit 5-10 Swiss jurists (external dependency, framework ready)

---

## State Updates

- `evaluation/state/evaluation.json`: Added `v42_cycle_verification`, `verification_count=42`, `last_verification=2026-09-25T09:59:00Z`
- `evaluation/state/monitor_174k_state.json`: `check_count=64`, `last_check=2026-09-25T10:02:14.329252`, JSON syntax repaired

---

## Recommendation

**BLOCKED_ON_DEPENDENCIES** — No additional same-question cycle justified for TF-IDF family. Evaluation lane infrastructure fully ready for auto-evaluation when legal-distance 174k dense embeddings land. Continue monitoring.