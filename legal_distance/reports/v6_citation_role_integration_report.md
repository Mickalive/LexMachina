# Legal Distance Lane v6 — Citation Role Embeddings Integration: NEGATIVE RESULT

## Executive Summary

**The 2,988 citation role embeddings (following, distinguishing, overruling, criticizing, citing, all_weighted) are ALL ZERO MATRICES.** 

This is a **negative result** — not a methodological failure, but a data pipeline gap. The citation role extraction (v5) produced valid role annotations (2,988 roles across 200 decisions), but the embedding construction failed to link citations to internal decision_ids because:

- **Citation targets** in text: BGE/ATF format (e.g., "BGE 149 IV 9", "ATF 147 IV 73")
- **Metadata decision_ids**: Internal format (e.g., "bger_5A_604_2024", "bger_7B_189_2023")
- **No mapping existed** between BGE/ATF citations and internal decision_ids at the time v5 ran

The v6 citation ID resolution pipeline was built to address this but only resolves **court decision citations** (1,124/5,828 resolved), not BGE/ATF citations (2,180 unresolved).

---

## Root Cause Analysis

### v5 Citation Role Extraction (Completed)
- **Input**: 200 decisions from 1000-slice
- **Method**: Pattern matching on citation contexts in Erwägungen section
- **Output**: 2,988 role annotations with confidence scores
- **Role distribution**: citing=2,427, following=311, distinguishing=174, criticizing=58, overruling=18
- **Status**: ✅ Role extraction WORKED — annotations are valid and multilingual

### v5 Embedding Construction (FAILED — Silent Zero Matrices)
```python
# In build_citation_role_matrix():
target = role_obj.target_decision  # e.g., "BGE 149 IV 9"
if target in id_to_idx:  # id_to_idx has keys like "bger_5A_604_2024"
    # NEVER MATCHES — BGE format != internal format
    j = id_to_idx[target]
```

**Result**: Zero edges in citation matrix → Zero embeddings from SVD → All 6 role embedding files are identical zero matrices (1000×64, all zeros).

### v6 Citation ID Resolution Pipeline (Partial)
- Built mapping for **court decision citations**: `7B_189/2023` → `bger_7B_189_2023` ✅
- **Resolved**: 1,124 / 5,828 court decision citations (19.3%)
- **BGE citations**: 2,180 — NOT resolved (requires full-text parsing + external BGE index)
- **Other formats**: 472 — NOT resolved

---

## Experimental Results (v6_citation_role_integration.py)

### Adversarial Benchmarks
| Experiment | Language Dominance (<0.85) | Jurist Preference (>0.5) | Both Pass |
|------------|---------------------------|-------------------------|-----------|
| **center_projected_64 (baseline)** | **0.7529** ✅ | **0.5485** ✅ | ✅ |
| following (zero emb) | 0.4326 ✅ | 0.8488 ✅ | ✅ |
| distinguishing (zero emb) | 0.4326 ✅ | 0.8488 ✅ | ✅ |
| overruling (zero emb) | 0.4326 ✅ | 0.8488 ✅ | ✅ |
| criticizing (zero emb) | 0.4326 ✅ | 0.8488 ✅ | ✅ |
| citing (zero emb) | 0.4326 ✅ | 0.8488 ✅ | ✅ |
| all_weighted (zero emb) | 0.4326 ✅ | 0.8488 ✅ | ✅ |
| **All hybrids (α=0.3,0.5,0.7)** | 0.7529 ✅ | 0.5485 ✅ | ✅ |

**Note**: The "excellent" adversarial scores for zero embeddings (0.4326 lang dom, 0.8488 jurist pref) are **artifacts** of how the benchmark code handles zero matrices — not meaningful results. All role embeddings produce IDENTICAL scores because they are IDENTICAL zero matrices. Hybrids collapse to baseline because `0.3 * zeros + 0.7 * baseline = baseline`.

### Fractal-Map Harness
| Experiment | Coarse | Fine | ImpRate | NMI | Verdict |
|------------|--------|------|---------|-----|---------|
| **center_projected_64** | 0.913 | 0.967 | 57.7% | 0.599 | PASS |
| following (zero) | 0.271 | 1.000 | 100% | 0.704 | PASS* |
| all role variants (zero) | 0.271 | 1.000 | 100% | 0.704 | PASS* |
| **All hybrids** | 0.913 | 0.967 | 57.7% | 0.599 | PASS |

*Overclustering: 1 coarse → 1000 fine clusters (one per decision) = memorization artifact

---

## Key Findings

1. **Role extraction WORKS**: 2,988 multilingual role annotations extracted successfully with meaningful distribution (citing dominant, following substantial, distinguishing/criticizing/overruling rare but present)

2. **Embedding construction FAILED silently**: Zero matrices produced because citation target format (BGE/ATF) ≠ metadata decision_id format (internal)

3. **All 6 role embeddings are identical zeros**: following ≡ distinguishing ≡ overruling ≡ criticizing ≡ citing ≡ all_weighted

4. **Hybrids with center_projected are identical to baseline**: Zero matrices contribute nothing to blending

5. **Adversarial benchmarks produce artifact scores on zero matrices**: The evaluation code likely computes default/fallback values for degenerate inputs

6. **Citation ID resolution pipeline (v6) only solves court decision citations**, not BGE/ATF citations which constitute 27% of all citations

---

## Required Fixes for Citation Role Integration

### Option A: Resolve BGE/ATF Citations (Complete Fix)
- Parse full_text of all decisions for BGE/ATF patterns
- Cross-reference with external BGE database or published volume metadata
- Map BGE citations to internal decision_ids where the same decision exists in corpus
- **Effort**: High — requires external BGE index or full-text BGE reference extraction

### Option B: Use Court Decision Citations Only (Partial Fix)
- Use the 1,124 resolved court decision citations from v6 pipeline
- Build role embeddings only from `outgoing_citations` with role annotations
- **Effort**: Low — mapping already exists in `citation_to_decision_id.json`
- **Coverage**: Limited to 19% of citations

### Option C: Citation Graph from Resolved IDs Only (Current Best Path)
- Use `citation_to_decision_id.json` (1,124 resolved court citations)
- Filter role annotations to only those with resolved targets
- Rebuild role matrices with actual connectivity
- **Effort**: Medium — requires re-running v5_citation_roles.py with ID resolution

---

## Recommendation to Factory Director

### Status Update: Objective 4 — PARTIAL (Blocked by Citation Format Mismatch)

| Sub-task | Status |
|----------|--------|
| Extract citation roles (2,988 annotations) | ✅ COMPLETED |
| Build citation ID resolution pipeline | ✅ COMPLETED (court decisions only) |
| **Resolve BGE/ATF citations to decision_ids** | ❌ **BLOCKED** — requires external data/full-text parsing |
| Build role embeddings with resolved IDs | ❌ **BLOCKED** — depends on above |
| Evaluate role embeddings on benchmarks | ⚠️ **ARTIFACT RESULTS** — embeddings are zeros |

### Next Steps

1. **Document this negative result** — Preserve as evidence (per Research Protocol: "Accepted negative findings are first-class results")

2. **Option C is recommended**: Re-run citation role embedding construction using the v6 resolved court decision citations (1,124 edges). This yields a partial but valid signal.

3. **Defer BGE resolution** to corpus lane scaling (192k decisions) where more BGE-referenced decisions may be in-corpus

4. **Do not productize** citation role map modes until non-zero embeddings are validated

---

## Evidence Preservation

Per Research Protocol, all raw outputs preserved:

- `results/v5/citation_roles/citation_roles_sample.json` — 2,988 role annotations (VALID)
- `results/v5/citation_roles/citation_roles_summary.json` — Extraction summary
- `results/v5/citation_roles/citation_role_*.npy` — **ALL ZERO MATRICES** (evidence of pipeline gap)
- `results/v6/citation_id_resolution/citation_to_decision_id.json` — 1,124 resolved court citations
- `results/v6/citation_id_resolution/resolution_stats.json` — Resolution statistics
- `results/v6/citation_role_integration/citation_role_integration_all_results.json` — This evaluation

---

## Conclusion

**Citation role modeling is not ready for productization.** The role extraction pipeline works excellently (2,988 multilingual annotations), but the embedding construction silently failed due to citation format mismatch. The v6 citation ID resolution pipeline partially addresses this for court decision citations (19% coverage) but BGE/ATF citations (27%) remain unresolved.

**Honest assessment**: This is a data engineering gap, not a research failure. The fix is well-scoped: re-run embedding construction with resolved citation IDs. When corpus lane scales to 192k decisions, more BGE-referenced decisions will be in-corpus, improving resolution rate.

*Generated: 2026-08-28 | Factory Direction v6 | Legal-Distance Lane*