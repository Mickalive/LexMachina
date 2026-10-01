# Dense vs TF-IDF Hierarchical_v1 Comparison at 12k/174k Scale

## Executive Summary

**CRITICAL DISCRIMINATING FINDING**: Dense embeddings (ACCEPTED, years 2000-2002, n=12,570) achieve **near-perfect legal structure purity** at coarse resolution (branch_purity=0.957, area_purity=0.854) but **FAIL the hierarchical_v1 zoom-quality protocol** due to over-fragmentation and poor zoom coherence. This is the **opposite failure mode** from TF-IDF flat Leiden at 174k.

---

## Results Comparison

| Metric | Dense 12k (ADAPTIVE) | Dense 12k (FIXED) | TF-IDF 174k Best (full_text_tfidf_light) | TF-IDF 174k Production (cited_outcome_hybrid_0.5) |
|--------|---------------------|-------------------|------------------------------------------|--------------------------------------------------|
| **Sample size** | 12,570 | 12,570 | 173,963 | 91,189 |
| **Coarse clusters** | 33 | 33 | 19 | 31 |
| **Fine clusters** | 424 | 508 | 365 | 285 |
| **Nesting** | 1.0 ✓ | 1.0 ✓ | 1.0 ✓ | 1.0 ✓ |
| **Coarse branch purity** | 0.957 | 0.957 | 0.766 | 0.523 |
| **Fine branch purity** | **0.997** | **0.997** | 0.930 | 0.633 |
| **Branch purity delta** | +0.039 | +0.039 | +0.164 | +0.110 |
| **Fine area purity** | **0.904** | **0.907** | 0.659 | 0.269 |
| **Area purity delta** | +0.050 | +0.052 | +0.189 | +0.023 |
| **Singleton fraction** | **0.066** ✗ | **0.093** ✗ | 0.000 ✓ | 0.000 ✓ |
| **Median cluster size** | 23 | 19 | 352 | 130 |
| **Improvement rate** | **0.273** ✗ | **0.212** ✗ | 0.714 ✓ | 0.710 ✓ |
| **Mean improvement** | 0.057 | 0.050 | 0.188 | 0.114 |
| **Legal structure branch** | ✓ (0.997 >> 0.5) | ✓ (0.997 >> 0.5) | ✓ (0.930 >> 0.5) | ✓ (0.633 >> 0.5) |
| **Legal structure area** | ✓ (0.904 >> 0.018) | ✓ (0.907 >> 0.018) | ✓ (0.659 >> 0.018) | ✓ (0.269 >> 0.018) |
| **hierarchical_v1 verdict** | **FAIL** | **FAIL** | **PASS** | **PASS** |

---

## Failure Mode Analysis

### Dense Embeddings: "Too Pure Too Early"
- Coarse resolution (0.25) already achieves **95.7% branch purity** — near ceiling
- Fine subdivision fragments already-pure clusters without legal justification
- 6-9% singletons at fine level (vs <1% for TF-IDF)
- Only 21-27% of coarse clusters show purity improvement (vs 58-75% for TF-IDF)
- **Root cause**: Dense embedding space has tight, well-separated legal clusters that don't benefit from further subdivision

### TF-IDF Embeddings: "Meaningful Refinement"
- Coarse resolution achieves moderate purity (52-77% branch)
- Fine subdivision meaningfully improves purity (+11-16% branch delta)
- Near-zero fragmentation by construction (min_cluster_size=10)
- 58-75% of coarse clusters show improvement
- **Trade-off**: Lower absolute purity but genuine hierarchical structure

---

## Protocol Verdicts

### hierarchical_v1 Protocol (frozen v29)
**Requires ALL 7 checks PASS:**
1. fragmentation_ok (singleton_fraction < 0.01) — Dense FAIL, TF-IDF PASS
2. nesting_perfect (1.0 by construction) — Both PASS
3. branch_purity_improves — Both PASS
4. area_purity_improves — Both PASS
5. zoom_coherence_ok (improvement_rate > 0.5) — Dense FAIL, TF-IDF PASS
6. legal_structure_branch (fine > 2×random) — Both PASS easily
7. legal_structure_area (fine > 2×random) — Both PASS easily

**Result**: Dense FAILS (2/7), TF-IDF 6/8 modes PASS

---

## Implications for Fractal Map Product

### For Dense Modes (when 174k embeddings land):
1. **Current hierarchical_v1 protocol is mismatched** for dense embedding geometry
2. Need **dense-specific hierarchical protocol** that:
   - Detects "already pure" coarse clusters and stops subdivision
   - Uses purity-aware stopping criteria (e.g., don't subdivide if coarse_purity > 0.9)
   - Measures zoom quality by semantic coherence, not purity delta
3. **Evidence-backed zoom path** from 1k citation-role dense (ZQ 0.48-0.54) remains valid but untested at 174k

### For TF-IDF Modes (currently operational at 174k):
1. hierarchical_v1 protocol **well-matched** to TF-IDF geometry
2. 3 production modes PASS at 174k (cited_decisions_tfidf, cited_outcome_hybrid_0.5/0.7)
3. Product default (cited_outcome_hybrid_0.5) validated

### For Product Integration:
- **TF-IDF fallback mode** (cited_outcome_hybrid_0.5 + hierarchical Leiden) is production-ready at 174k
- **Dense modes require protocol redesign** before 174k deployment
- Scale dependency CONFIRMED: dense works at 1k/12k/28k with different protocol needs

---

## Recommendation

**PIVOT_WITHIN_MISSION**: The fractal-map lane should design a **dense-specific hierarchical protocol** that:
1. Uses purity-aware adaptive stopping (stop subdividing pure clusters)
2. Evaluates zoom quality by semantic/legal coherence, not purity delta
3. Is validated at 12k/28k ACCEPTED dense scales before 174k attempt

**No further same-question cycles justified** while blocked on 174k dense embeddings. The fundamental geometric difference is now characterized with ACCEPTED evidence at 12k scale.

---

## Evidence Artifacts

- `/results/fractal_map/dense_12k_hierarchical_v1/dense_12k_hierarchical_v1_results.json` (ADAPTIVE)
- `/results/fractal_map/dense_12k_hierarchical_v1/dense_12k_hierarchical_v1_FIXED_results.json` (FIXED)
- `/results/fractal_map/hierarchical_v1_174k_tfidf/hierarchical_v1_174k_tfidf_verdict_20261001_102442.json` (TF-IDF 174k)
- `/state/fractal-map.json` (updated with this finding)