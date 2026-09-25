# OPERATIONAL VERIFICATION — RUN 36174553152
## Factory Direction v27 | Fractal-Map Lane | GitHub Run 36174553152

**Timestamp:** 2026-09-25T18:45:00Z  
**Direction Version:** 27  
**Lane Status:** BLOCKED_ON_DEPENDENCY (correctly reflected in workspace state)  
**Factory Direction Status:** RUN (orchestration discrepancy — supervisor reads ephemeral control plane)  
**Continue Recommended:** false — no same-question cycle justified  

---

## Verification Summary

### Test Suite Execution
All **195 tests PASS** (0 failures, 0 errors):
- `tests/fractal_map/test_verify.py`: 184/184 PASS
- `tests/fractal_map/test_zoom_quality_174k_eval.py`: 4/4 PASS  
- `tests/fractal_map/test_zoom_quality_174k_v26_eval.py`: 7/7 PASS

All freeze-protected negative results remain intact:
- v25 TF-IDF 174k zoom-quality: **FAIL** (over-fragmented, median cluster size 1, no monotonic zoom refinement)
- v26 TF-IDF 174k completion: **FAIL** generalized to all 4 decision-mappable modes
- Census classification and alignment probe corruption confirmed
- NESTING_METRIC_DEFECT_v1 claim ceiling enforced

### Dense Embeddings Dependency Status
**Blocked on:** `legal-distance_174k_dense_embeddings` (single dependency)  
**Progress:** 11/26 years complete (2000–2010) — 42% of years, ~4.4% of decisions by volume  
**Checkpoints:** `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/`  
**Progress.json:** Clean — `completed_years: ["2000".."2010"]`, `failed_years: []`  

**Year-split embeddings available:** 11 years (embeddings_YYYY.npy + metadata_YYYY.json)  
**Full concatenation pending:** All 26 years required for 174k fractal map build  

### Evaluation Infrastructure Readiness
**VERIFIED AND READY** (confirmed run 36158377781, re-verified this run):
- `fractal_map/evaluation/evaluate_174k_dense_embeddings.py` — frozen v25/v26 success rule
- `fractal_map/hierarchical/build_dense_hierarchical_artifacts.py` — parameterized builder for dense embeddings
- Accepted metadata: `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.jsonl` (173,963 entries, 100% branch+legal_area coverage)
- Corpus year-split JSONL: 37 files at `/tmp/lex_accepted/corpus/corpus/normalization/canonical/bger_20*.jsonl`

### Evidence-Backed Zoom Path (Unchanged)
| Mode | Zoom Quality (1000-scale) | Evidence Tier |
|------|---------------------------|---------------|
| `citing_alpha0.3` | **0.5401** | ACCEPTED |
| `following_alpha0.3` | 0.5280 | ACCEPTED |
| `criticizing_alpha0.3` | 0.4864 | ACCEPTED |
| `outcome_hybrid_0.5` (prod default) | 0.2798 | ACCEPTED |

TF-IDF 174k modes encode strong legal structure (branch purity 0.51–0.55 vs 0.25 random; legal_area purity 0.24–0.31 vs ~0.005 random) but **fail all three monotonic zoom-refinement checks**; fine ladder over-fragmented (median cluster size 1.0, singleton fraction >99%).

### Mount Path & Artifact Status
| Artifact | Expected Path | Status |
|----------|---------------|--------|
| Corpus year-split JSONL | `/tmp/lex_accepted/corpus/corpus/normalization/canonical/` | ✅ EXISTS |
| Metadata 174k (product) | `/tmp/lex_accepted/product/product/results/fractal_map/hierarchical_map_174k/metadata_174k.json` | ✅ EXISTS |
| Dense embeddings checkpoints | `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/` | ✅ 11/26 years |

**Factory Direction v27 Note:** The direction's autonomous remediation items (mount path symlink, metadata generation) are **ALREADY RESOLVED** — paths exist and artifacts present. Direction contains stale status.

### Orchestration Discrepancy (Re-confirmed)
**60+ documented occurrences** since run 33339971167: Supervisor reads ephemeral `/tmp/lex_control/state/factory_direction.json` (fractal-map.status=RUN) instead of persistent workspace `state/fractal-map.json` (BLOCKED_ON_DEPENDENCY, continue_recommended=false). Factory Director must update supervisor dispatch logic to read workspace state.

---

## Key Findings (No Change from Prior Accepted State)

1. **TF-IDF 174k zoom-quality evaluation COMPLETE** — honest FAIL, freeze-protected
2. **Dense embeddings evaluation infrastructure VERIFIED AND READY** — zero work needed until delivery
3. **Lane correctly BLOCKED on legal-distance_174k_dense_embeddings** — single dependency
4. **continue_recommended=false** — no same-question cycle justified
5. **NESTING_METRIC_DEFECT_v1 enforced** — nesting_score≥0.99 claims prohibited for compressed-family modes
6. **Compressed 5-level ladder validated** — 100% purity delta retention, identical zoom navigation at shared resolutions; NOT universally valid for strict nesting
7. **Product multi-view zoom UI with citation-role views VERIFIED IMPLEMENTED** — audit recommendation #4 satisfied

---

## Recommendation

**BLOCKED** — Resume when legal-distance delivers 174k dense embeddings (all 26 years concatenated). No same-question cycle justified. Next cycle should only dispatch when dense embeddings are available.

**Next Recommendation:** `BLOCKED on legal-distance_174k_dense_embeddings. Resume when dense embeddings delivered. No same-question cycle justified.`

---

## State Update

This verification updates the lane state with current GitHub run ID while preserving the accepted run ID (no new accepted work performed — verification only).

```json
{
  "lane": "fractal-map",
  "direction_version": 27,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED_ON_DEPENDENCY",
  "continue_recommended": false,
  "accepted_run_id": "36158377781",
  "github_run": "36174553152",
  "resume_from_run_id": "36161811441",
  "timestamp": "2026-09-25T18:45:00.000000+00:00",
  "blocked_on": "legal-distance_174k_dense_embeddings",
  "blocked_since": "2026-09-24T01:55:00Z",
  "next_recommendation": "BLOCKED on legal-distance_174k_dense_embeddings. Resume when dense embeddings delivered. No same-question cycle justified."
}
```

---

## Provenance

- Test execution: `python -m pytest tests/fractal_map/ -v` (195/195 PASS)
- Dense embeddings progress: `/tmp/lex_accepted/legal-distance/legal_distance/results/174k_dense_embeddings/checkpoints/progress.json`
- Accepted metadata verification: 173,963 entries, branch+legal_area 100% coverage
- All evidence refs preserved from prior accepted state (200+ entries)
