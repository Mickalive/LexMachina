# Evaluation Lane - 174k Infrastructure Verification Report
**Factory Direction v28 | Lane: evaluation | Date: 2026-09-27**

## Executive Summary
All evaluation infrastructure for the 174k formal suite has been **verified operational and reproducible**. The TF-IDF family (8 representations) has been fully evaluated at 174k scale with frozen harness v3 (HNSW artifact fixed via exact k-NN on stratified subsample n=2000). No new ACCEPTED representations have landed from legal-distance since the last evaluation (dense embeddings only 3/26 years ACCEPTED). Lane status correctly remains **BLOCKED_ON_DEPENDENCIES** with `continue_recommended=false`.

---

## Verification Results

### 1. Monitor Script (`monitor_and_evaluate_174k.py`)
- **Status**: OPERATIONAL
- **Check count**: 165 (incremented from 162)
- **Last check**: 2026-09-27T19:51:13.490Z
- **Detection**: Correctly identifies 8/8 TF-IDF representations as COMPLETE, 12/12 awaited representations as NOT AVAILABLE in accepted state
- **Dense embeddings progress**: 20/26 years (2000-2019) in checkpoints (~99k decisions, 79%); only 3/26 years (2000-2002) ACCEPTED per factory direction v28

### 2. Formal Suite (`run_174k_formal_suite.py`) - **FULL REPRODUCTION**
- **Config hash**: `b51701f5a9c11692` (matches previous verification exactly)
- **Global seed**: 42
- **HNSW artifact fix**: CONFIRMED - exact k-NN on stratified subsample (n=2000) for adversarial benchmarks
- **Results reproduced identically**:

| Representation | Verdict | LangDom | LD-Pass | JuristPref | JP-Pass | Both |
|---|---|---|---|---|---|---|
| cited_decisions_tfidf_outcome_hybrid_0.5 | PASS | 0.5167 | ✓ | 0.8050 | ✓ | ✓ |
| cited_decisions_tfidf | PASS | 0.5295 | ✓ | 0.8010 | ✓ | ✓ |
| cited_decisions_tfidf_outcome_hybrid_0.7 | PASS | 0.5237 | ✓ | 0.8000 | ✓ | ✓ |
| outcome_tfidf | PASS | 0.4920 | ✓ | 0.7250 | ✓ | ✓ |
| regeste_tfidf | PASS | 0.5240 | ✓ | 0.5775 | ✓ | ✓ |
| full_text_tfidf_light | FAIL | 1.0000 | ✗ | 0.0000 | ✗ | ✗ |
| regeste_full_text_hybrid_0.5 | FAIL | 1.0000 | ✗ | 0.0000 | ✗ | ✗ |
| regeste_full_text_hybrid_0.7 | FAIL | 1.0000 | ✗ | 0.0000 | ✗ | ✗ |

- **Production default**: `cited_decisions_tfidf_outcome_hybrid_0.5` - **PASS** (lang_dom=0.5167, jurist_pref=0.8050)
- **Fundamental tradeoff confirmed**: Citation-based reps PASS adversarial, FAIL branch/tf_metadata/hierarchy; Text-based reps PASS branch/tf_metadata, FAIL adversarial (lang_dom~0.999)

### 3. Citation Heritage Benchmark (`validate_citation_heritage_174k.py`)
- **Status**: OPERATIONAL
- **Citation graph**: 2,105 total citations, 2,019 resolved (95.9%)
- **Frozen pair pool generated**: 2,040 pairs (1,020 positive direct+shared, 1,020 negative balanced, seed=42)
- **Output**: `evaluation/results/174k_citation_heritage/citation_pairs_174k.json`
- **Ready for 174k embeddings when available**

### 4. v17b Label Normalization at 174k (`run_v17b_174k_tfidf.py`)
- **Status**: OPERATIONAL
- **Labels normalized**: 85,819/173,963 (49.3%)
- **Unique areas reduced**: 214 → 164 (23.4% reduction via cross-lingual normalization)
- **Differential effect REPRODUCED at 174k**:
  - Citation-based reps: hierarchy_purity improves 1.04-1.67x
  - Text-based reps: hierarchy_purity and NMI degrade
  - Uniform improvement: **False** (NMI degrades for most reps)
- **Consistent with 1,200-slice results**: "citation-based reps improve (1.04-1.10x hierarchy, 1.03-1.08x zoom_fine), text-based reps degrade zoom_fine (0.66-0.69x)"

### 5. v25 Formal Suite Runner (`run_v25_174k_suite.py`)
- **Status**: OPERATIONAL
- **Test run**: `cited_decisions_tfidf` completed in 63.7s
- **Result**: 6 PASS / 5 FAIL / 1 SKIP (matches frozen protocol v16 semantics)
- **Frozen config hash**: `4323f833fa72366a`
- **Ready for new representations when they land**

---

## Accepted Evidence State (from factory direction v28)

### Completed at 174k (TF-IDF family):
- ✅ Full 12-benchmark formal suite on 8 representations (frozen harness v3)
- ✅ Citation heritage benchmark on frozen 2,040 pair pool - all 8 TF-IDF FAIL recall@10
- ✅ v17b label normalization on 174k fine-grained legal_area labels - differential effect confirmed

### Awaiting from legal-distance (not yet ACCEPTED at 174k):
- ❌ Dense embeddings: only 3/26 years ACCEPTED (2000-2002, ~19k decisions); 17/26 years in checkpoints PENDING AUDIT
- ❌ Citation role embeddings: not available at 174k
- ❌ Linear hybrid embeddings: not available at 174k
- ❌ Jurist human study: framework ready, requires 5-10 Swiss jurists (external dependency)

---

## Readiness for Next Representations

| Component | Status | Notes |
|---|---|---|
| Formal suite script | ✅ VERIFIED | `run_174k_formal_suite.py` operational, exact reproduction |
| Scalable NN infrastructure | ✅ READY | exact k-NN (adversarial), HNSW (full-corpus) |
| Citation heritage pipeline | ✅ READY | frozen 2,040 pair pool, 95.9% resolution |
| v17b normalization pipeline | ✅ READY | differential effect reproduced at 174k |
| Metadata 174k | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% coverage |
| v25 formal suite runner | ✅ OPERATIONAL | frozen protocol, HNSW-backed, 12-benchmark + citation_heritage + v17b |

---

## Recommendation

**No additional same-question cycle justified.** The evaluation lane has completed all machine-executable work for the current factory direction question. The lane is correctly blocked on dependencies from legal-distance:

1. **Critical path**: legal-distance must deliver ACCEPTED 174k dense embeddings (concatenated 2000-2025, audit-promoted)
2. **Secondary**: citation role embeddings at 174k
3. **Secondary**: linear hybrid embeddings at 174k

The monitor script will automatically detect and evaluate new representations when they appear in the accepted state mount (`/tmp/lex_accepted/legal-distance/legal_distance/results/`).

**Next action**: Factory Director decision on successor question once legal-distance promotes 174k dense embeddings to ACCEPTED state.

---

## Files Updated
- `state/evaluation.json` - Updated `last_verification` to 2026-09-27T19:57:06.300Z, monitor check_count to 165, dense embeddings progress to 20/26 years