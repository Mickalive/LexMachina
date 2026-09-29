# Evaluation Lane - 174k Readiness Report (Factory Direction v28)

**Date:** 2026-09-29  
**Lane:** evaluation  
**Direction Version:** 28  
**Evidence Tier:** REPRODUCED  
**Cycle Status:** MONITORING  
**Continue Recommended:** true

---

## Executive Summary

The evaluation lane has **completed all three mandated tasks** from factory direction v28 for the currently available production representations (TF-IDF family, 8 representations at 174k scale). The lane is now in **MONITORING mode**, actively watching for new representations from legal-distance to evaluate autonomously as they land.

### Factory Direction v28 Evaluation Question (Three Parts) - STATUS

| Task | Description | Status |
|------|-------------|--------|
| **(1)** | Full 12-benchmark formal suite at 174k scale on all production representations (frozen harness v3 thresholds) | ✅ **COMPLETE** - All 8 TF-IDF reps evaluated; RE-VERIFIED 2026-09-28 (config hash `b51701f5a9c11692` adversarial, `4323f833fa72366a` v25 suite); RE-VERIFIED 2026-09-29T08:39:58; formal suite runner verified operational 2026-09-29T10:40:58 |
| **(2)** | Validate citation_heritage benchmark using 174k citation-ID resolution (2,019/2,105 resolved, 95.9%) | ✅ **COMPLETE** - Frozen 2,040 pair pool validated; executed on all 8 TF-IDF reps at 174k; all FAIL recall@10 (< 0.2 threshold); best recall@10 = 0.044-0.049 |
| **(3)** | Test v17b label normalization generalization to 174k fine-grained legal_area labels (15-25% purity gain reproduced across 4 seeds) | ✅ **COMPLETE** - 49.3% labels normalized (85,819/173,963, 214→164 unique areas); **differential effect REPRODUCED**: citation-based reps show modest gains (3-10%), text-based reps show degradation on zoom_fine (30-34% loss); re-verified 2026-09-28 across 4 seeds |

---

## Current Representation Landscape

### ✅ COMPLETED at 174k (Evaluated)
**TF-IDF Family (8 representations)** - All evaluated with v25 formal suite, citation heritage, v17b normalization:
- `cited_decisions_tfidf`
- `outcome_tfidf`
- `cited_decisions_tfidf_outcome_hybrid_0.5` (production default)
- `cited_decisions_tfidf_outcome_hybrid_0.7`
- `regeste_tfidf`
- `full_text_tfidf_light`
- `regeste_full_text_hybrid_0.5`
- `regeste_full_text_hybrid_0.7`

### ⏳ AWAITED from Legal-Distance (Not yet available at 174k)
| Category | Representations | Status |
|----------|----------------|--------|
| **Dense embeddings (8)** | `center_projected_768dim`, `center_projected_64dim`, `center_projected_128dim`, `linear_metric_epoch4`, `mahalanobis_metric_epoch4`, `hybrid_stabilized_epoch1`, `hybrid_v2_epoch3` | 25/26 years in checkpoints (2000-2024); only 3/26 years (2000-2002, ~19k decisions) ACCEPTED; final concatenation PENDING |
| **Citation roles (3)** | `citation_role_citing_alpha0.3`, `citation_role_following_alpha0.3`, `citation_role_criticizing_alpha0.3` | Not yet delivered at 174k |
| **Linear hybrids (2)** | `linear_citation_concat`, `linear_hybrid05_concat` | Not yet delivered at 174k |

---

## Key Findings (Reproduced at 174k)

### 1. Fundamental Two-Mode Tradeoff Persists
- **Citation-based reps** (e.g., `cited_decisions_tfidf`): PASS adversarial (LangDom=0.516, Jurist=0.806), FAIL citation_heritage recall@10 (0.044)
- **Text-based reps** (e.g., `full_text_tfidf_light`): FAIL adversarial (LangDom≈0.999), PASS citation_heritage AUC (0.85-0.90) but FAIL recall@10
- **Production default** (`cited_decisions_tfidf_outcome_hybrid_0.5`): Best citation-based balance (LangDom=0.516, Jurist=0.806, CiteHeritage AUC=0.529)

### 2. Citation Heritage: Negative at 174k
- ALL 8 TF-IDF representations FAIL recall@10 threshold (0.2)
- Best: `cited_decisions_tfidf` = 0.044, `cited_decisions_tfidf_outcome_hybrid_0.7` = 0.049
- Citation graph pair pool covers 2,936 unique decisions (~1.69% of 173,963)
- Citation-independent retrieval near-zero for citation signals

### 3. v17b Label Normalization: Differential Effect Confirmed
- **Citation-based reps**: Modest purity gains (3-10%, 1.03-1.10x) across hierarchy/zoom_fine/legal_area
- **Text-based reps**: Significant degradation on zoom_fine (30-34% loss, 0.66-0.70x), hierarchy/legal_area stable (~1.0x)
- **NMI metrics**: Modest degradation for both families
- **regeste_tfidf**: Only representation satisfying no-worsening on ALL hierarchy metrics
- **Prior report overstated gains by ~10x** - corrected per audit CYCLE_36527630008
- **Effect REPRODUCED across 4 seeds and re-verified 2026-09-28**

### 4. Dense Embeddings: Scale Dependency Confirmed (12k evaluation)
- V6 dense (years 2000-2002, 12,570 decisions): FAIL adversarial (LangDom=0.99, BranchCoherence=0.99) - language completely dominates neighbors
- FAIL hierarchy_coherence (purity=0.42 < 0.7), FAIL legal_area_clustering (purity=0.009)
- PASS cross-language transfer (zero-shot NMI~0.46-0.48), cluster coherence (branch_purity~0.89)
- V17b normalization: NO improvement (purity unchanged, NMI drops 0.59→0.45)
- **Root cause**: 18.3% metadata coverage, partial corpus center-projection, raw multilingual-e5 language clustering

### 5. HNSW Artifact FIXED
- Exact k-NN on stratified subsample (n=2000, seed=42) confirms fix
- 5/8 TF-IDF reps PASS both adversarial gates with exact k-NN
- Production default confirmed PASS (LangDom=0.5164, Jurist=0.8055)
- V25 suite uses HNSW (M=16, ef_construction=200, ef_search=100) for full-corpus scalability; citation_heritage uses exact k-NN on valid subset

### 6. Boilerplate Resistance: Negative (All Reps)
- All TF-IDF reps FAIL (resistance_score ≈ -0.57 to -0.80)
- Confirms language dominance/cross-lingual alignment failure, not procedural boilerplate

### 7. Hierarchy Coherence: Low (All Reps)
- All TF-IDF reps FAIL Jurivoc proxy (level_0_nmi < 0.3, level_1_nmi < 0.2)
- Best level_1_nmi: `full_text_tfidf_light`=0.563 (but FAIL adversarial)
- Dense at 12k: level_1_nmi ~0.59-0.68 but purity very low (0.42)

---

## Infrastructure Verification (All OPERATIONAL)

| Component | Status | Verification |
|-----------|--------|--------------|
| **run_174k_formal_suite.py** | ✅ OPERATIONAL | Verified 2026-09-29T10:40:58 - exact k-NN on 90,632 valid decisions, adversarial subsample n=2000 |
| **run_v25_174k_suite.py** | ✅ OPERATIONAL | Frozen protocol v25; config hash `4323f833fa72366a`; executed on all 8 TF-IDF + v6 dense 12k |
| **validate_citation_heritage_174k.py** | ✅ OPERATIONAL | Frozen 2,040 pair pool (1,020 pos + 1,020 neg, balanced, seed=42); 95.9% citation resolution |
| **v17b label normalization** | ✅ OPERATIONAL | Differential effect reproduced across all 8 TF-IDF reps + v6 dense 12k |
| **Scalable NN infrastructure** | ✅ OPERATIONAL | sklearn exact k-NN for adversarial (n=2000 subsample); HNSW for full-corpus citation heritage |
| **Monitor script** | ✅ ACTIVE | check_count=221, last_check=2026-09-29T10:38:43Z; no new awaited representations detected |
| **Metadata 174k** | ✅ VERIFIED | 173,963 entries, branch+legal_area 100% coverage |

---

## Blockers (External Dependencies)

| Blocker | Description | Impact |
|---------|-------------|--------|
| **legal_distance_dense_174k** | 25/26 years in checkpoints; final concatenation (center_projected, PCA) and 174k evaluation PENDING. Only 3/26 years ACCEPTED. | Cannot evaluate dense embeddings at 174k until legal-distance promotes checkpoints to accepted state |
| **legal_distance_citation_roles** | Citation-role specific embeddings not yet available at 174k | Cannot evaluate citation role representations |
| **legal_distance_linear_hybrids** | Linear hybrid families at 174k not yet delivered | Cannot evaluate linear_citation_concat, linear_hybrid05_concat at 174k |
| **fractal_map_blocked** | Blocked on legal-distance 174k dense embeddings (single remaining dependency per factory direction v28) | Fractal map lane cannot proceed with dense embedding modes |
| **product_blocked** | Blocked on legal-distance 174k dense embeddings for production default switch | Product lane cannot switch from TF-IDF to dense defaults |

---

## Monitor State

```json
{
  "check_count": 221,
  "last_check": "2026-09-29T10:38:43.605106Z",
  "completed_evaluations": 15,
  "detected_representations": 2,
  "last_verification": "monitor_check221_20260929T1038_confirmed_no_new_awaited_representations"
}
```

The monitor correctly identifies:
- 8/8 TF-IDF representations: ✅ COMPLETE (no evaluation needed)
- 12/12 awaited representations: ❌ NOT YET AVAILABLE

---

## Next Steps / Recommendations

### Immediate (Current Cycle)
- **Continue MONITORING** - The lane is correctly in monitoring mode; `continue_recommended=true` means another cycle under the SAME factory-direction question has a concrete discriminating purpose (evaluating new representations as they land)
- **No action needed** - All infrastructure verified; monitor active; awaiting legal-distance deliveries

### When New Representations Land
The monitor will automatically trigger evaluation for:
1. **Dense embeddings 174k** (when final concatenation promoted to accepted state)
2. **Citation role embeddings 174k**
3. **Linear hybrid embeddings 174k**

Each will receive:
- Full v25 174k formal suite (12 benchmarks)
- Citation heritage benchmark (frozen 2,040 pair pool)
- v17b label normalization test
- Adversarial benchmarks with exact k-NN (HNSW artifact fix)

### Jurist Human Study
- Framework ready (`evaluation/tests/jurist_usability.py`)
- Requires 5-10 Swiss jurists for validation
- Not blocked on technical infrastructure

---

## Evidence References

1. `evaluation/state/monitor_174k_state.json` - Monitor state (check_count=221)
2. `results/evaluation/v25_174k_formal_suite/results/_suite_summary.json` - V25 suite summary
3. `results/evaluation/v25_174k_citation_heritage/` - Citation heritage results (8 TF-IDF reps)
4. `results/evaluation/v25_174k_v17b/` - v17b label normalization results
5. `results/evaluation/v25_174k_formal_suite/partial_dense_results/` - V6 dense 12k evaluation
6. `evaluation/benchmarks/specification.json` - Frozen benchmark specification
7. `evaluation/reports/EVALUATION_174K_CYCLE_REPORT_v28_COMPLETION_20260928.md` - Prior completion report

---

## Conclusion

The evaluation lane has **successfully executed the machine-executable 174k formal suite** on all currently available production representations (TF-IDF family, 8 representations). All three mandated tasks from factory direction v28 are **COMPLETE and REPRODUCED**.

The lane is now in **MONITORING mode** with `continue_recommended=true`, actively watching for new representations from legal-distance. All evaluation infrastructure is **verified operational** and ready to autonomously evaluate new representations as they land.

**No blockers on evaluation infrastructure.** The only blockers are external dependencies on legal-distance delivering 174k dense embeddings, citation roles, and linear hybrids.

---

*Report generated 2026-09-29T10:42:00Z*