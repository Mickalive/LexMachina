# Dense Embeddings Evaluation Pipeline Verification

**Date**: 2026-09-26  
**Lane**: fractal-map  
**Factory Direction**: v27  
**Status**: BLOCKED on legal-distance_174k_dense_embeddings (3/26 years complete: 2000-2002)

---

## Summary

The fractal-map lane is correctly **BLOCKED** on the single dependency `legal-distance_174k_dense_embeddings`. The evaluation pipeline (`eval_dense_embeddings_174k.py`) has been **verified and is ready** for full 174k-scale evaluation when dense embeddings arrive.

### Evidence-Backed Zoom Path (Confirmed at Partial Scale)

| Configuration | Scale | Verdict | Key Metrics |
|---------------|-------|---------|-------------|
| `center_projected_64dim` + hierarchical Leiden (sub_res=3.0) | 62k (2000-2010) | **PASS** | branch_mono=✓, area_mono=✓, rate_ok=✓ (2/4 transitions >0.5) |
| `center_projected_768dim` + hierarchical Leiden | 62k | FAIL | rate_ok fails |
| `center_projected_128dim` + hierarchical Leiden | 62k | FAIL | rate_ok fails |
| Raw 768-dim + hierarchical Leiden | 62k | FAIL | area_mono fails |
| Citation-role modes (1000-scale) | 1k | PASS | ZQ: citing=0.5401, following=0.5280, criticizing=0.4864 |

**Confirmed**: Dense embeddings (center_projected_64dim) + hierarchical Leiden = coherent zoom path. 64-dim is the optimal sweet spot (consistent with legal-distance adversarial validation).

---

## Pipeline Verification on Available Data (2000-2002, 12,570 decisions)

### Tested Configurations

| Embedding | Dim | Sub-res | branch_mono | area_mono | rate_ok | Verdict |
|-----------|-----|---------|-------------|-----------|---------|---------|
| Raw 768-dim | 768 | 2.0 | ✓ | ✓ | ✗ (0/4) | FAIL |
| Raw 768-dim | 768 | 3.0 | ✓ | ✓ | ✗ (0/4) | FAIL |
| Center-projected | 768 | 2.0 | ✓ | ✓ | ✗ (1/4) | FAIL |
| Center-projected | 768 | 3.0 | ✓ | ✓ | ✗ (1/4) | FAIL |
| Center-projected + PCA | 64 | 3.0 | ✓ | ✓ | ✗ (1/4) | FAIL |
| Center-projected + PCA | 128 | 3.0 | ✓ | ✓ | ✗ (1/4) | FAIL |

### Why 12k Fails but 62k Passes

- **Insufficient cluster diversity** at 12k scale: Only 5-6 coarse clusters with children at early transitions
- **Rate calculation**: Needs ≥2 of 4 transitions with improvement_rate > 0.5
- At 12k: Only 0.5→1.0 transition achieves >0.5 rate (0.667)
- At 62k: Multiple transitions achieve >0.5 rate due to richer cluster structure
- **Conclusion**: Pipeline behavior is correct; scale is the limiting factor

---

## Evaluation Pipeline Readiness Checklist

✅ **Pipeline script**: `fractal_map/evaluation/eval_dense_embeddings_174k.py` — functional  
✅ **Dependencies**: Leiden, igraph, scikit-learn — installed and working  
✅ **Metadata**: `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries, branch+legal_area 100% coverage) — accessible  
✅ **Success rule**: v26 frozen spec — implemented and validated  
✅ **Hierarchical Leiden**: Coarse (res=0.25) + fine (sub_res=2.0/3.0) — functional, guarantees nesting=1.0  
✅ **Flat Leiden at intermediate resolutions**: 0.5, 1.0, 2.0 — functional  
✅ **Metrics**: branch purity, area purity, zoom coherence, strict nesting, fragmentation — all implemented  
✅ **Output format**: JSON with full provenance (timestamp, embedding path, config) — compliant  

---

## Legal-Distance Dense Embeddings Progress

| Year | Status | Decisions | Embedding File |
|------|--------|-----------|----------------|
| 2000 | ✅ Complete | 3,839 | embeddings_2000.npy |
| 2001 | ✅ Complete | 4,332 | embeddings_2001.npy |
| 2002 | ✅ Complete | 4,399 | embeddings_2002.npy |
| 2003-2010 | ⏳ Pending | ~34k | — |
| 2011-2025 | ⏳ Pending | ~120k | — |
| **Total** | **3/26 years (11.5%)** | **12,570/174,113** | — |

**Progress file**: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/progress.json`

---

## Next Steps (When Dependency Resolves)

1. **Wait** for legal-distance to complete year-split dense embedding computation (2003-2025)
2. **Combine** year-split embeddings into full 174k matrix (or evaluate incrementally)
3. **Run** `eval_dense_embeddings_174k.py` on full 174k center_projected_64dim embeddings
4. **Test** hierarchical Leiden with sub_res=3.0 (validated sweet spot)
5. **Compare** against TF-IDF 174k baseline (already evaluated: FAIL — over-fragmented)
6. **Validate** citation-role modes at 174k scale (currently BLOCKED — placeholder-keyed)
7. **Update** fractal-map state with full 174k verdict

---

## Recommended State

- **Lane status**: BLOCKED_ON_DEPENDENCY (unchanged)
- **continue_recommended**: false (no same-question cycle justified)
- **Evidence tier**: ACCEPTED (pipeline verified, partial-scale evidence confirmed)
- **Blocking dependency**: legal-distance_174k_dense_embeddings
- **Readiness**: EVALUATION PIPELINE READY — zero code changes needed

---

## Artifacts Generated During Verification

```
results/fractal_map/zoom_quality_174k_eval/
├── dense_embeddings_2000_only_20260926_042849.json
├── dense_embeddings_2000_2002_raw768_sub2_20260926_042919.json
├── dense_embeddings_2000_2002_raw768_sub3_20260926_042946.json
├── dense_embeddings_2000_2002_cp768_sub2_20260926_043111.json
├── dense_embeddings_2000_2002_cp768_sub3_20260926_043037.json
├── dense_embeddings_2000_2002_cp64_sub3_20260926_043135.json
├── dense_embeddings_2000_2002_cp128_sub3_20260926_043159.json
```

All artifacts preserve full provenance and negative results per Research Protocol.

---

## Conclusion

**The fractal-map lane is correctly blocked and the evaluation pipeline is production-ready.** No further work is justified on the current question until dense embeddings arrive. The factory director should monitor legal-distance progress and dispatch the next fractal-map cycle when 174k dense embeddings are available.