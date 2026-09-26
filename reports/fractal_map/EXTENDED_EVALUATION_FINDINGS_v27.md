# Extended Fractal Map Evaluation Findings (Factory Direction v27)

**Date**: 2026-09-26  
**Lane**: fractal-map  
**Status**: BLOCKED_ON_DEPENDENCY (legal-distance_174k_dense_embeddings)  
**Run**: Extended evaluation beyond frozen v26

---

## Executive Summary

The fractal-map lane remains **BLOCKED** on dense embeddings at 174k scale (36% complete: 11/26 years). However, extended evaluation reveals critical nuances in the "negative result" from v26:

| Method | Scale | Success Rule | Fragmentation | Nesting | Verdict |
|--------|-------|--------------|---------------|---------|---------|
| TF-IDF flat Leiden | 174k | FAIL | Severe (99.6% singletons) | 0.18 | FAIL |
| TF-IDF hierarchical Leiden | 174k | **PASS** | Severe (88.9% singletons) | 0.45 | PASS* |
| Citation-role flat Leiden | 1k | FAIL | Severe (97-100% singletons) | ~1.0 | FAIL |
| Dense (center_projected) hierarchical Leiden | 1k | **PASS** | **None** (0% singletons) | 0.52-0.55 | **PASS** |
| Dense (center_projected) agglomerative | 1k | **PASS** | **None** (0-3% singletons) | 1.0 | **PASS** |

*PASS with caveat: formal success rule passes but fine level is over-fragmented (88.9% singletons).

---

## Key Findings

### 1. v26 Negative Result is Method-Specific, Not Representation-Specific

The v26 verdict (FAIL on all 4 decision-mappable TF-IDF 174k modes) used **flat multi-resolution Leiden** at all 5 resolutions. When the **same TF-IDF embeddings** are clustered with **hierarchical Leiden** (coarse global → fine within parents), the formal success rule **PASSES**:

- Branch monotonic: ✓ (0.3347 → 0.4430)
- Area monotonic: ✓ (0.1023 → 0.1990)  
- Improvement rate > 0.5 on ≥2/4 transitions: ✓ (3/4 transitions)
- **Overall: PASS**

**Caveat**: Fine level (res_3.0) has 5,308 clusters with median size 1.0 and 88.9% singletons. The hierarchy is structurally sound (nesting=1.0 for coarse→fine) but practically unusable for navigation at the finest level.

### 2. Citation-Role Modes at 1000-Scale: Monotonicity PASSES, Fragmentation FAILS

The 3 citation-role modes (citing/following/criticizing_alpha0.3) at 1000-scale:
- **Branch monotonic**: ✓ (0.4416 → 0.5556-0.7500)
- **Area monotonic**: ✓ (0.103 → 0.2222-0.5435)
- **Improvement rate**: ✗ (only 1-2/4 transitions > 0.5, first two transitions have None rate due to single-cluster coarse levels)
- **Nesting**: ✓ (~1.0, by construction of 7-level ladder)
- **Fragmentation**: Severe at res_2.0/res_3.0 (97-100% singletons)

The ZQ scores (0.5401/0.5280/0.4864) measure a different quality dimension than the v26 success rule.

### 3. Dense Embeddings + Hierarchical Clustering: The Evidence-Backed Path

At 1000-scale, **center_projected_768 (language-debiased) embeddings** with hierarchical Leiden:
- **PASS** all success rule checks
- **Zero fragmentation** at all resolutions (singleton_fraction = 0.0)
- **Mean nesting** ~0.52-0.55 (mixed hierarchical/flat; pure hierarchical would be 1.0)

Agglomerative clustering (Ward/Average/Complete) on the same embeddings:
- **PASS** all checks with **nesting=1.0 by construction**
- **Zero fragmentation** (median cluster size 7-14, singleton 0-3%)
- **Fine branch purity**: 0.8865-0.9447

**Conclusion**: Dense embeddings enable coherent zoom refinement. The method matters: agglomerative > hierarchical Leiden > flat Leiden.

### 4. Scale-Dependent Behavior

| Scale | Flat Leiden | Hierarchical Leiden |
|-------|-------------|---------------------|
| 1k | Works (with fragmentation at fine res) | Works, no fragmentation |
| 10k | Works (passes success rule) | Works |
| 50k | Works (passes success rule) | Not tested |
| 174k | FAILS (no monotonicity, severe fragmentation) | PASSES success rule but fine level fragmented |

The transition from 50k to 174k breaks flat Leiden but hierarchical Leiden maintains the success rule pass (at cost of fine-level fragmentation).

### 5. Compressed 5-Level Ladder Validation Extended

The compressed ladder [0.25, 0.5, 1.0, 2.0, 3.0] validated at 21k (100% purity delta retention, identical navigation at shared resolutions). At 174k:
- Flat Leiden: FAILS
- Hierarchical Leiden: PASSES but fine level unusable

**Implication**: The compressed ladder is a valid evaluation framework, but the clustering method must match the scale.

---

## Evaluation Pipeline Ready for Dense Embeddings

Created `/home/runner/work/LexMachina/LexMachina/fractal_map/evaluation/eval_dense_embeddings_174k.py`:

- Loads dense embeddings from year-split or combined .npy files
- Aligns with ACCEPTED 174k metadata (173,963 entries)
- Runs hierarchical Leiden (scalable to 174k)
- Evaluates with frozen v26 success rule
- Outputs machine-readable verdict JSON

**Tested on**: center_projected_768 (1000-scale) → PASS  
**Ready for**: 174k dense embeddings when legal-distance delivers them

---

## Recommendations

### Immediate (while blocked)
1. **No further TF-IDF 174k cycles needed** — all decision-mappable modes tested, negative result understood
2. **Monitor legal-distance dense embedding progress** — 11/26 years complete, ~36%
3. **Prepare product integration** for dense embedding map modes (center_projected_hierarchical is product default)

### When dense embeddings land (174k)
1. **Run eval_dense_embeddings_174k.py** on combined embeddings immediately
2. **Test multiple hierarchical configurations**: coarse_0.25_sub_2.0, coarse_0.25_sub_3.0, coarse_0.5_sub_3.0
3. **Compare hierarchical Leiden vs. sampled agglomerative** (e.g., 50k sample for agglomerative, full for hierarchical)
4. **Evaluate citation-role dense embeddings** if legal-distance computes them

### Product decisions
- **Default map mode**: center_projected_hierarchical (hierarchical Leiden on dense embeddings) — evidence-backed at 1000-scale
- **Fallback**: TF-IDF hybrid (cited_decisions_tfidf_outcome_hybrid_0.5) — available now, works at 174k for coarse navigation
- **Citation-role views**: Available at 1000-scale; await 174k dense citation-role embeddings

---

## Artifacts Produced

### Evaluation Results
- `results/fractal_map/zoom_quality_174k_eval/citation_role_1000_v26_rule_20260926_000301.json` — Citation-role 1000-scale v26 evaluation
- `results/fractal_map/zoom_quality_174k_eval/center_projected_1000_test_20260926_001551.json` — Dense hierarchical Leiden (sub_res=2.0)
- `results/fractal_map/zoom_quality_174k_eval/center_projected_1000_test_sub3_20260926_001600.json` — Dense hierarchical Leiden (sub_res=3.0)
- `results/fractal_map/zoom_quality_174k_eval/cited_decisions_tfidf_174k_hierarchical_20260926_002053.json` — TF-IDF hierarchical Leiden at 174k

### Evaluation Scripts
- `fractal_map/evaluation/zoom_quality_174k_all_12_modes.py` — Extended v26 evaluation (discovered placeholder-keyed modes)
- `fractal_map/evaluation/zoom_quality_citation_role_1000.py` — Citation-role 1000-scale v26 evaluation
- `fractal_map/evaluation/eval_dense_embeddings_174k.py` — Dense embeddings evaluation pipeline (ready for 174k)

---

## State Update for Fractal-Map Lane

```json
{
  "lane": "fractal-map",
  "direction_version": 27,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "BLOCKED_ON_DEPENDENCY",
  "continue_recommended": false,
  "blocked_on": "legal-distance_174k_dense_embeddings",
  "blocked_since": "2026-09-24T01:55:00Z",
  "key_findings": [
    "Extended evaluation: Hierarchical Leiden on TF-IDF 174k PASSES formal success rule (branch/area monotonic, 3/4 transitions >0.5) but fine level over-fragmented (88.9% singletons, median size 1.0)",
    "v26 negative result is method-specific (flat Leiden), not representation-specific (TF-IDF embeddings)",
    "Citation-role modes at 1000-scale: monotonicity PASSES, but fragmentation at fine resolutions breaks improvement_rate check",
    "Dense embeddings (center_projected_768) + hierarchical Leiden at 1000-scale: PASS with zero fragmentation — evidence-backed zoom path confirmed",
    "Agglomerative clustering on dense embeddings at 1000-scale: PASS, nesting=1.0, zero fragmentation, fine purity 0.89-0.94",
    "Dense embeddings evaluation pipeline ready and tested; awaits 174k delivery from legal-distance (36% complete)"
  ],
  "next_recommendation": "BLOCKED on legal-distance_174k_dense_embeddings. Resume when dense embeddings delivered. Run eval_dense_embeddings_174k.py immediately on arrival. No same-question cycle justified for TF-IDF."
}
```

---

## Appendix: Frozen v26 Verdict Remains Valid

The v26 frozen evaluation (flat Leiden on 4 decision-mappable TF-IDF modes) correctly reports **FAIL**. This extended evaluation does not weaken v26; it clarifies the boundary conditions:

- **Flat multi-resolution Leiden** at 174k: FAIL (no zoom refinement)
- **Hierarchical Leiden** at 174k: PASS (formal rule) but practically limited by fine-level fragmentation
- **Dense embeddings + hierarchical methods**: PASS at 1000-scale, predicted to work at 174k

The product should not ship flat Leiden TF-IDF 174k as a zoomable map. It should wait for dense embeddings or use coarse-only TF-IDF navigation.