# Evaluation Lane v25 — Infrastructure Final Validation & Bug Fix

**Factory Direction:** v25  
**Lane:** evaluation  
**GitHub Run:** 35961790798  
**Status:** BLOCKED_ON_DEPENDENCIES (awaiting legal-distance 174k representations)  
**Evidence Tier:** ACCEPTED  

---

## Executive Summary

This cycle completed the **final infrastructure validation** for the 174k formal evaluation suite and fixed a **critical bug** that would have prevented 174k-scale evaluation. All evaluation infrastructure is now **FROZEN, VALIDATED, and AUDIT-READY** for immediate execution when legal-distance delivers 174k representations.

**Key Accomplishments:**
1. ✅ Fixed `assign_branch` bug in frozen harness v3 (handles None chamber in 174k metadata)
2. ✅ Verified 174k metadata compatibility: 173,963 decisions, 90,632 with known branches
3. ✅ Confirmed citation heritage infrastructure at full 174k scale: 137,314 positive + 137,314 negative pairs
4. ✅ Confirmed v17b label normalization at 174k: 213→163 labels (23.5% reduction), 32 cross-lingual concepts
5. ✅ Created autonomous monitor script for automatic evaluation when representations land
6. ✅ All three frozen config hashes re-verified (no drift)

**Blocker Status:** UNCHANGED — Legal-distance lane (gh run 35935612800) is actively computing 174k representations year-split. No 174k embeddings in accepted state yet.

---

## Bug Fix: `assign_branch` Handles None Chamber

### Issue
The 174k metadata (`evaluation/data/174k/metadata_174k.jsonl`) contains `null` (None) values for the `chamber` field for ~82,768 decisions (indices 840+). The frozen harness v3 `assign_branch()` function called `.lower()` on None, causing `AttributeError`.

### Fix Applied
```python
# evaluation/evaluation_v3_harness.py, line 231
def assign_branch(chamber: str) -> str:
    """Assign legal branch from chamber name.
    
    Handles None/empty chamber gracefully (returns 'unknown').
    """
    if not chamber:
        return "unknown"
    # ... rest unchanged
```

### Impact
- **Before fix:** Evaluation pipeline crashed on 174k metadata
- **After fix:** `prepare_metadata()` correctly filters to 90,632 decisions with known branches
- **Config hash impact:** NONE — config hash only covers thresholds/parameters/embedding hashes, not code logic
- **1200-scale evaluation:** Unaffected (all 1200 decisions have populated chambers)

### Validation
```
Loaded 173963 decisions
Valid decisions (known branch): 90632
Branches: oeffentliches_recht(31284), sozialversicherungsrecht(17347), strafrecht(16588), zivilrecht(25413)
Languages: de(54953), fr(30481), it(5198)
```

---

## Infrastructure Validation Summary

| Component | Status | Details |
|-----------|--------|---------|
| **Frozen Harness v3** | OPERATIONAL | Config hash `a31c443a9b0e992e` verified; bug fix applied; exact reproduction at 1200 confirmed |
| **Full Corpus Harness v3** | OPERATIONAL | Config hash `4047da047fb339c1` verified; HNSW backend validated at 174k scale (90k+ decisions) |
| **v16 Benchmark Suite** | IMPLEMENTED | Config hash `4323f833fa72366a` verified; all 12 benchmarks frozen |
| **Citation Heritage 174k** | READY | 137,314 positive + 137,314 negative pairs (full 174k); citation resolution 95.9% (2,019/2,105) |
| **v17b Label Normalization** | LABEL LEVEL CONFIRMED | 213→163 labels, 85,819 changed (49.3%), 32 cross-lingual canonical concepts |
| **Scalable NN (HNSW)** | OPERATIONAL | M=16, ef_construction=200, ef_search=100; batch_size=5000 |
| **Distributed Evaluation** | SUPPORTED | Model-level sharding via `DistributedEvaluator` |
| **Auto-Monitor Script** | CREATED | `evaluation/monitor_and_evaluate_174k.py` watches for representations |

---

## 174k Corpus Readiness

| Metric | Value |
|--------|-------|
| Total decisions | 173,963 |
| With known branch | 90,632 (52.1%) |
| With legal_area | 91,193 (52.4%) |
| Language distribution | de: 106,501, fr: 57,489, it: 9,973 |
| Known branch distribution | oeffentliches_recht: 31,284, zivilrecht: 25,413, sozialversicherungsrecht: 17,347, strafrecht: 16,588 |

---

## Citation Heritage Benchmark — Full 174k Scale

**Infrastructure:** FULLY VALIDATED

| Metric | Value |
|--------|-------|
| Positive pairs (full) | 137,314 |
| Negative pairs (full) | 137,314 |
| Citation resolution rate | 95.9% (2,019/2,105) |
| Positive pairs (known branch subset) | ~95% of sampled pairs map to valid indices |
| Artifacts | `evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json` |

**Note:** Previous test on cited_outcome_hybrid_0.5_174k (cycle branch, not accepted) returned FAIL (AUC=0.482, threshold=0.65). TF-IDF hybrids cannot recover citation proximity at 174k scale — dense embeddings required.

---

## v17b Label Normalization — 174k Label Level Confirmed

**Infrastructure:** FULLY VALIDATED at label level; **clustering test PENDING 174k embeddings**

| Metric | Value |
|--------|-------|
| Raw unique labels | 213 |
| Normalized unique labels | 163 |
| Label reduction | 23.5% |
| Labels changed | 85,819 (49.3% of decisions with legal_area) |
| Cross-lingual canonical concepts | 32 |
| Top normalized labels | criminal_procedure (11,803), invalidity_insurance (8,554), debt_enforcement_bankruptcy (6,849), family_law (6,610), contract_law (6,567) |

**Hypothesis (from 1200-scale REPRODUCED across 4 seeds):** Normalized labels improve hierarchy/zoom/legal_area clustering purity by 15-25% uniformly across all 6 production representations.

**Test Required:** Run hierarchy_coherence, zoom_coherence, legal_area_clustering benchmarks with normalized vs raw labels on 174k embeddings.

---

## Auto-Monitor Script Created

**File:** `evaluation/monitor_and_evaluate_174k.py`

**Capabilities:**
- Scans `/tmp/lex_accepted/legal-distance/legal_distance/results/v5` for 174k representation directories
- Detects newly appeared representations automatically
- Executes full corpus adversarial evaluation via `run_full_corpus_evaluation.py`
- Tracks state in `evaluation/state/monitor_174k_state.json`
- Logs to `evaluation/logs/monitor_174k.log`

**Usage:** Run periodically (cron) or as a background service to enable autonomous evaluation "as representations land" per factory direction v25.

---

## Frozen Configuration Hashes (Re-Verified)

| Harness | Config Hash | Seed | Factory Direction |
|---------|-------------|------|-------------------|
| Frozen Adversarial v3 | `a31c443a9b0e992e` | 42 | v6 (canonical) |
| Full Corpus v3 | `4047da047fb339c1` | 42 | v10 |
| v16 Benchmark Suite | `4323f833fa72366a` | 42 | v13 |

**All hashes match accepted state — no drift detected.**

---

## Negative Results Preserved (Per Research Protocol)

| Benchmark | Result | Note |
|-----------|--------|------|
| Boilerplate resistance | NEGATIVE (~ -0.9) | Measures language dominance, not procedural boilerplate |
| Hierarchy coherence | NEGATIVE | v18 confirmed fundamental branch-level limitation (purity ~0.65) |
| Zoom coherence | NEGATIVE | No improvement from coarse to fine at branch level |
| Legal area clustering | NEGATIVE | Fine-grained label granularity prevents purity > 0.5 |
| Citation heritage on TF-IDF | NEGATIVE (AUC=0.482) | TF-IDF cannot recover citation proximity at 174k scale |
| center_projected_768 | FAILS jurist gate | 0.4912 < 0.5 threshold, confirmed across all verifications |

---

## Production Decision Gates (From Factory Direction v25)

| Gate | Representation | Requirement |
|------|---------------|-------------|
| PRODUCT_SERVING_DEFAULT | cited_outcome_hybrid_0.5 | Must pass BOTH adversarial gates at 174k |
| COMBINATION_MODE | linear_hybrid05_concat | Must pass BOTH adversarial gates + stability test at 174k |
| DEFAULT Map Mode | center_projected_64dim_hierarchical | Must pass BOTH adversarial gates (validated at 1200) |

---

## External Blockers

| Blocker | Status | Notes |
|---------|--------|-------|
| Jurist human study | FRAMEWORK READY, EXTERNALLY BLOCKED | Requires 5-10 Swiss jurists recruited by repository owner |

---

## Next Recommendation

**BLOCKED_ON_DEPENDENCIES** — No additional same-question cycle justified.

All evaluation infrastructure is **FROZEN, VALIDATED, and AUDIT-READY** for 174k execution. The `assign_branch` bug fix ensures 174k metadata compatibility. The auto-monitor script enables autonomous execution when representations land.

**Three v25 sub-questions remain blocked on legal-distance 174k representations:**
1. Full 12-benchmark formal suite at 174k scale on all production representations
2. Citation heritage benchmark at 174k (137k+ pairs ready)
3. v17b label normalization clustering test at 174k (label level confirmed)

**Factory Director to await legal-distance delivery (gh run 35935612800) in accepted state before authorizing next evaluation cycle.**

---

## Evidence References

```
evaluation/evaluation_v3_harness.py (frozen harness v3, bug fix at line 231)
evaluation/scalable_nn.py (HNSW backend, config hash 4047da047fb339c1)
evaluation/run_full_corpus_evaluation.py (full corpus harness)
evaluation/experiments/run_v16_full_benchmark_suite.py (12 benchmarks)
evaluation/validate_citation_heritage_174k.py (citation pairs infrastructure)
evaluation/experiments/run_v17b_label_normalization_all_reps.py (label normalization)
evaluation/monitor_and_evaluate_174k.py (auto-monitor script)
evaluation/results/174k_citation_heritage/citation_pairs_174k_full.json (137k pairs)
evaluation/results/174k_label_analysis/174k_legal_area_analysis.json (v17b confirmed)
evaluation/data/174k/metadata_174k.jsonl (173,963 decisions)
/tmp/lex_accepted/corpus/corpus/normalization/canonical/resolved_full/ (citation resolution)
state/evaluation.json (updated with v25_infrastructure_final_validation_20260924b)
```

---

*Generated: 2026-09-24T06:20:00Z | Factory Direction v25 | Evaluation Lane: BLOCKED_ON_DEPENDENCIES*