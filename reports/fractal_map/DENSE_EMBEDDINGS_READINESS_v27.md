# Fractal-Map Lane: Dense Embeddings Readiness Report (Factory Direction v27)

**Date**: 2026-09-24  
**Lane**: fractal-map  
**Status**: BLOCKED on `legal-distance_174k_dense_embeddings` (single remaining dependency)  
**Direction Version**: 27  
**Evidence Tier**: ACCEPTED (v26 TF-IDF evaluation complete)

---

## Summary

The fractal-map lane has **completed all TF-IDF 174k work** and is **ready to consume 174k dense embeddings** from legal-distance when they arrive. The legal-distance lane is actively executing staged 174k CPU computation (gh run 36071928708), starting with TF-IDF/citation/outcome signals, then dense embeddings year-split.

### Key Accepted Findings (v26, run 36035695081)

| Finding | Status | Evidence |
|---------|--------|----------|
| TF-IDF 174k modes encode strong legal structure | CONFIRMED | Branch purity 0.51-0.55 vs 0.25 random; legal_area purity 0.24-0.31 vs ~0.005 random |
| TF-IDF 174k modes FAIL monotonic zoom refinement | CONFIRMED | 0/4 decision-mappable modes PASS v25 success rule |
| Fine ladder over-fragmented (median cluster size 1) | CONFIRMED | res_2.0: 12,852 clusters; res_3.0: 63,778 clusters; singleton >99% |
| Citation-role modes dominate zoom quality at 1000-scale | CONFIRMED | citing_alpha0.3 ZQ=0.5401, following_alpha0.3 ZQ=0.5280, criticizing_alpha0.3 ZQ=0.4864 |
| Production default (outcome_hybrid_0.5) ranks 21st in zoom quality | CONFIRMED | ZQ=0.2798 |
| NESTING_METRIC_DEFECT_v1 | CONFIRMED | nesting_score≥0.99 claims PROHIBITED for 7 compressed-family modes; honest strict nesting 0.39-0.96 |
| Compressed 5-level ladder validated | ACCEPTED | 100% purity delta retention, 0% nesting change vs 7-level ladder |
| Multi-view zoom UI with citation-role views | IMPLEMENTED | Product level verified (CITATION ROLE VIEWS optgroup, zoom controls, split-view) |

---

## Readiness Checklist for Dense Embeddings

### ✅ Parameterized Hierarchical Builder (COMPRESSED 5-Level Ladder)
**File**: `fractal_map/hierarchical/build_parameterized_legal_distance_map_compressed.py`

- [x] Works with dense embeddings (tested: center_projected 768-dim at 1000-scale)
- [x] Correctly derives branch from chamber (fixes corpus branch=null issue)
- [x] Excludes "unknown" branches from purity computation
- [x] Outputs standard artifacts: `labels_res_*.npy`, `hierarchical_map_results.json`, `zoom_mappings.json`, `zoom_coherence.json`, `decision_clusters.json`, `cluster_metadata.json`
- [x] Computes honest strict nesting (not majority-parent coverage)
- [x] Scales to arbitrary corpus size via `--corpus-size` parameter

### ✅ 174k Evaluation Harness
**File**: `fractal_map/evaluation/evaluate_174k_dense_embeddings.py`

- [x] Loads ACCEPTED 174k metadata (173,963 entries, branch+legal_area 100% coverage)
- [x] Implements v25/v26 success rule identically:
  - Branch purity res_3.0 > res_0.25 (monotonic)
  - Area purity res_3.0 > res_0.25 (monotonic)
  - Zoom improvement_rate > 0.5 on ≥ 2 of 4 transitions
- [x] Computes branch/area purity, zoom coherence, strict nesting, fragmentation
- [x] Cross-checks build-time nesting from `zoom_mappings.json`
- [x] Verified against v26 TF-IDF results (reproduces FAIL verdicts)
- [x] Ready for any new mode under `results/fractal_map/legal_distance_modes/<mode>/`

### ✅ Infrastructure
- [x] ACCEPTED 174k metadata at `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json`
- [x] Corpus directory at `/tmp/lex_accepted/corpus/corpus/normalization/canonical/` (37 year-split JSONL files)
- [x] Compressed 5-level resolution ladder [0.25, 0.5, 1.0, 2.0, 3.0] hardcoded and validated
- [x] Leiden clustering with k=15, seed=42 (reproducible)

---

## Expected Dense Embeddings from Legal-Distance

Per factory direction v27 and legal-distance state (REPRODUCED v14), the following dense embeddings are expected at 174k scale:

| Mode Category | Expected Modes | Priority |
|--------------|----------------|----------|
| **Center projected** | center_projected_64dim (validated, passes both adversarial gates) | HIGH |
| **Metric learning** | linear_metric_epoch4 (JP=0.605 holdout), mahalanobis_metric_epoch4 (JP=0.585) | HIGH |
| **Citation role** | citing_alpha0.3, following_alpha0.3, criticizing_alpha0.3 (top ZQ at 1000-scale) | HIGH |
| **Hybrid stabilized** | hybrid_stabilized_epoch1 (OOS validated, passes all clean gates) | MEDIUM |
| **Cited decisions TF-IDF** | cited_decisions_tfidf (first unsupervised signal passing both gates) | MEDIUM |
| **Cited+center_projected hybrids** | hybrid_cp64_0.7, hybrid_cp768_0.7 (best production hybrids) | MEDIUM |
| **Multilingual** | ft_multilingual_e5_small_pretrained (overclusters, needs hierarchy loss) | LOW |

---

## Execution Plan When Dense Embeddings Arrive

### Step 1: Build Hierarchical Maps (per mode)
```bash
# For each dense embedding .npy delivered by legal-distance:
python3 fractal_map/hierarchical/build_parameterized_legal_distance_map_compressed.py \
    --embedding-path /path/to/dense_embedding.npy \
    --mode-id <mode_id> \
    --corpus-size 174113 \
    --metadata-path /tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json \
    --output-dir results/fractal_map/legal_distance_modes/<mode_id> \
    --corpus-dir /tmp/lex_accepted/corpus/corpus/normalization/canonical \
    --metadata-has-branch  # metadata already has branch
```

### Step 2: Evaluate Zoom Quality (per mode)
```bash
python3 fractal_map/evaluation/evaluate_174k_dense_embeddings.py \
    --mode <mode_id> \
    --output results/fractal_map/zoom_quality_174k_eval/dense_174k_verdict_<mode_id>.json
```

### Step 3: Compare with TF-IDF Baselines
- Branch purity at each resolution
- Area purity at each resolution
- Zoom improvement rates across 4 transitions
- Strict nesting consistency per transition
- Fragmentation (cluster counts, median size, singleton fraction)

### Step 4: Product Integration
- Wire successful modes into product map mode registry
- Enable citation-role views for zoom navigation
- Expose both HIGH-ADVANTAGE (citation-based) and HIGH-PURITY (metric learning) map modes per legal-distance v14 recommendation

---

## Success Criteria for Dense Embeddings

A 174k dense embedding mode **PASSES** the fractal-map zoom-quality gate iff:

1. **Branch monotonic**: `branch_purity[res_3.0] > branch_purity[res_0.25]`
2. **Area monotonic**: `area_purity[res_3.0] > area_purity[res_0.25]`
3. **Zoom refinement**: `improvement_rate > 0.5` on **≥ 2 of 4** transitions

**Random baselines**: branch=0.25 (4 classes), area≈0.0047 (213 classes)

**TF-IDF 174k reference (FAILED)**: branch 0.51-0.55, area 0.24-0.31, zoom rates <0.5 on most transitions

**1000-scale citation-role reference (PROMISING)**: citing_alpha0.3 ZQ=0.5401 with +0.12 purity improvement across zoom transitions, 50-80% meaningful split rates

---

## Blockers & Dependencies

| Blocker | Status | Resolution Path |
|---------|--------|-----------------|
| `legal-distance_174k_dense_embeddings` | ACTIVE | legal-distance gh run 36071928708 executing year-split CPU computation |
| 174k metadata alignment | RESOLVED | ACCEPTED metadata_174k.json (173,963 entries) available |
| Citation-role 174k validation | BLOCKED | Placeholder builds; requires full corpus JSONL for row→id alignment |
| GPU availability | ENVIRONMENT CONSTRAINT | CPU-only computation on free public runners (accepted) |

---

## Next Actions

1. **MONITOR** legal-distance 174k dense embedding delivery (gh run 36071928708)
2. **EXECUTE** Steps 1-2 above for each delivered dense embedding mode
3. **REPORT** zoom-quality verdicts per mode
4. **INTEGRATE** passing modes into product map mode registry
5. **UPDATE** fractal-map state with new evidence tier (EXPLORATORY → REPRODUCED → ACCEPTED)

---

## Files Modified/Created This Cycle

| File | Purpose |
|------|---------|
| `fractal_map/hierarchical/build_parameterized_legal_distance_map_compressed.py` | Fixed branch derivation from chamber; excludes "unknown" from purity |
| `fractal_map/evaluation/evaluate_174k_dense_embeddings.py` | New: general 174k dense embedding evaluation harness |
| `results/fractal_map/legal_distance_modes/center_projected_768_1000_test/` | Test artifacts validating dense embedding pipeline |
| `results/fractal_map/zoom_quality_174k_eval/dense_174k_verdict_*.json` | Verification that evaluation reproduces v26 results |

---

**Recommendation**: `continue_recommended=false` — no additional same-question cycle justified. Lane remains BLOCKED on single dependency `legal-distance_174k_dense_embeddings`. Factory Director to resume when dense embeddings land.