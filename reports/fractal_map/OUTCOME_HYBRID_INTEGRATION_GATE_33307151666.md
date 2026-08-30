# Outcome Hybrid Integration Gate Report
**Run**: 33307151666  
**Timestamp**: 2026-08-30  
**Direction Version**: 10  
**Gate**: PASS  
**Recommendation**: PRODUCTIZE

## Summary

Verified that `cited_decisions_tfidf_outcome_hybrid_0.5` (BEST PRODUCTION) and `cited_decisions_tfidf_outcome_hybrid_0.7` (BEST FRACTAL) fractal-map artifacts are complete, valid, and ready for product integration.

## Frozen Evaluation

- **Sample**: 1000 BGer decisions (2020-2024) — same baseline as all prior fractal-map work
- **Metric**: nesting consistency, zoom coherence, artifact integrity, integration summary
- **Success Rule**: nesting=1.0, zoom_coherence>0, 7-resolution ladder complete, ACCEPTED evidence tier

## Results

### cited_decisions_tfidf_outcome_hybrid_0.5 (BEST PRODUCTION)

| Check | Result | Value |
|-------|--------|-------|
| Artifact completeness | PASS | All 8 required files + 7 resolution labels present |
| Nesting consistency | PASS | 1.0000 (29 fine → 14 coarse, all consistent) |
| Hierarchical purity | INFO | 0.8680 (config: coarse_0.5_fine_3.0) |
| Zoom coherence | PASS | 0.1944 improvement rate (28 improvements, 29 deteriorations, 144 evaluated) |
| Integration summary | PASS | evidence_tier=ACCEPTED, 14/14 benchmarks PASS |
| Product artifacts | PASS | All required files present, nesting=1.0, n_decisions=1000 |

**Cluster counts**: 11→14→18→22→22→24→29 (7-resolution ladder)  
**Legal-distance benchmarks**: JP=0.7990, LangDom=0.4911, adversarial_both_pass=True

### cited_decisions_tfidf_outcome_hybrid_0.7 (BEST FRACTAL)

| Check | Result | Value |
|-------|--------|-------|
| Artifact completeness | PASS | All 8 required files + 7 resolution labels present |
| Nesting consistency | PASS | 1.0000 (29 fine → 15 coarse, all consistent) |
| Hierarchical purity | INFO | 0.9030 (config: coarse_0.5_fine_3.0) |
| Zoom coherence | PASS | 0.2759 improvement rate (40 improvements, 32 deteriorations, 145 evaluated) |
| Integration summary | PASS | evidence_tier=ACCEPTED, 14/14 benchmarks PASS |
| Product artifacts | PASS | All required files present, nesting=1.0, n_decisions=1000 |

**Cluster counts**: 10→15→16→19→22→25→29 (7-resolution ladder)  
**Legal-distance benchmarks**: JP=0.7907, LangDom=0.4907, adversarial_both_pass=True

## Architecture Note

The fractal-map lane built these representations using flat multi-resolution Leiden at 7 resolutions (0.25–3.0), producing 29 fine clusters at the finest resolution. The product lane's `build_cited_outcome_hybrids.py` additionally runs hierarchical Leiden (coarse_0.5/fine_3.0), producing 339 (α=0.5) / 250 (α=0.7) fine clusters. Both are valid implementations; the product version provides richer hierarchical decomposition.

The fractal-map artifacts are internally consistent and meet all quality thresholds. Product integration is authorized.

## Integration Path

The product lane's `map_loader.py` already has `_load_cited_outcome_hybrid_0_5()` and `_load_cited_outcome_hybrid_0_7()` methods that load from `product/results/fractal_map/cited_outcome_hybrid_{0.5,0.7}/`. Product artifacts exist at `/tmp/lex_accepted/product/product/results/fractal_map/`. The remaining gap is the product.json state file update (product lane responsibility).

## Evidence Refs

- `results/fractal_map/legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.5/` — fractal-map artifacts
- `results/fractal_map/legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7/` — fractal-map artifacts
- `results/fractal_map/evaluation/verify_outcome_hybrid_integration_33307151666.json` — verification report
- `/tmp/lex_accepted/product/product/results/fractal_map/cited_outcome_hybrid_{0.5,0.7}/` — product artifacts
