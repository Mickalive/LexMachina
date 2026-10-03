# Dense Embedding Integration Contract for Fractal Map Lane

**Version:** 1.0
**Lane:** fractal-map
**Factory Direction:** v34
**Date:** 2026-10-03
**Status:** ACCEPTED — Ready for implementation when data blocker resolves

---

## 1. Context and Strategic Pivot

Per Factory Direction v34 (RUN_37093485135), the original hypothesis that dense embeddings would beat TF-IDF on jurist preference at scale has been **falsified** by ACCEPTED evidence:

| Metric | Dense (center_projected) | TF-IDF (cited_outcome_hybrid_0.5) | Baseline Target |
|--------|-------------------------|-----------------------------------|-----------------|
| Jurist Preference (JP) | 0.05–0.43 (FAILS all scales) | 0.78–0.79 (DOMINATES) | > 0.7 |
| True OOS JP Ceiling | ~0.53 | — | < 0.7 factory target |
| Linear Hybrid (w=0.3–0.4) | 0.66–0.67 | 0.78–0.79 | Below TF-IDF |

**However**, dense embeddings **EXCEL at complementary capabilities**:
- **Citation heritage recovery**: AUC 0.79–0.85 > TF-IDF 0.71–0.74
- **Section cross-lingual alignment**: Sachverhalt gap 0.187 vs 0.452 (TF-IDF)
- **Hierarchical structure at scale**: 12k/28k/144k validate multi-level protocol PASS (nesting=1.0, zero fragmentation)

**Strategic Pivot:**
1. **TF-IDF citation hybrids** = PRIMARY product mode (jurist preference, branch clustering)
2. **Dense embeddings** = COMPLEMENTARY modes (citation heritage view, cross-lingual view, linear hybrid complement)
3. **Data blocker** moved to corpus lane resumption criteria

---

## 2. Required Dense Embedding Capabilities

### 2.1 Citation Heritage View
**Purpose:** Navigate legal decisions by citation lineage and precedent heritage
**ACCEPTED Evidence:** Dense embeddings recover citation heritage at scale (AUC 0.79–0.85) BETTER than TF-IDF citation-based (AUC 0.71–0.74)

**Acceptance Criteria:**
- Citation heritage AUC > 0.75 at 174k scale
- Recovers known doctrinal families without shared explicit citations
- Stable under corpus growth (validated at 12k, 28k, 144k)

### 2.2 Cross-Lingual View
**Purpose:** Enable navigation across German/French/Italian decisions by legally meaningful factual/reasoning alignment
**ACCEPTED Evidence:** Section cross-lingual hierarchy: Sachverhalt > Dispositiv > Erwaegungen (facts align best cross-lingually)

**Acceptance Criteria:**
- Cross-lang same-branch (Sachverhalt) > 0.2
- Cross-lang same-branch (Dispositiv) > 0.1
- Cross-lang same-branch (Erwaegungen) > 0.05 (expected lower)

### 2.3 Linear Hybrid Complement
**Purpose:** Combine TF-IDF jurist-preference strength with dense embedding complementary signals
**ACCEPTED Evidence:** Linear hybrids PASS adversarial at optimal weight (w=0.3–0.4) but REMAIN BELOW TF-IDF baseline (JP 0.66–0.67 vs 0.78–0.79)

**Acceptance Criteria:**
- Hybrid JP > 0.65 (adversarial PASS threshold)
- Hybrid JP < TF-IDF baseline (confirmed complementary, not replacement)
- Weight sweep identifies stable optimal range

---

## 3. Multi-Level Protocol Requirements for Dense Embeddings

The fractal map requires **hierarchical, multi-resolution** structure. Dense embeddings must satisfy:

| Check | Threshold | Rationale |
|-------|-----------|-----------|
| `all_nesting_ge_0.95` | ≥ 0.95 | Perfect parent-child containment |
| `all_singleton_lt_0.01` | < 0.01 | No over-fragmentation (TF-IDF fails at 0.99) |
| `all_median_gt_3` | > 3 | Meaningful cluster sizes |
| `monotonic_branch_improvement` | True | Each zoom level increases branch purity |
| `monotonic_area_improvement` | True | Each zoom level increases area purity |
| `some_subdivision` | True | Each level refines |
| `level1_branch_gt_0.5` | > 0.5 | Domain-level legal coherence |
| `level2_area_gt_0.15` | > 0.15 | Subdomain legal-area separation |
| `level3_area_gt_0.2` | > 0.2 | Microcluster legal-area separation |
| `fine_branch_purity` | > 0.90 | Leaf-level legal coherence |

**ACCEPTED Validation:**
- 12k dense: 4 levels, nesting=1.0, zero fragmentation, hierarchical builder SUCCESS (39→412)
- 28k dense: fixed configs achieve >0.5 improvement_rate, zero fragmentation
- 144k dense: fine_branch_purity ~0.97, improvement_rate 0.48–0.65 branch / 0.75–0.76 area, strict_nesting ≥0.99

---

## 4. Scale Requirements

| Scale | Status | Notes |
|-------|--------|-------|
| 12k (3 years, 2000–2002) | ACCEPTED | Full multi-level protocol PASS |
| 28k (5 years, 2000–2004) | VALIDATED | Scale extrapolation confirmed |
| 144k (22 years, 2000–2021) | PENDING AUDIT | Checkpoint validation complete, awaits audit |
| 174k (full corpus) | REQUIRED | **Blocked on data blocker** |

**Dense embeddings must be computed at full 174k scale** for multi-view deployment.

---

## 5. Data Blocker Dependencies (Corpus Lane)

The following **must be resolved by corpus lane** before legal-distance can deliver 174k dense embeddings:

1. **BGE/bger ID Mapping**
   - Canonical corpus uses `bge_` IDs
   - Evaluation uses `bger_` IDs
   - **No mapping exists** — required for joining embeddings to metadata

2. **Parquet Generation for Years 2022–2026**
   - 29,520 decisions missing from parquet
   - Required for complete 174k corpus coverage

3. **Section Extraction (Sachverhalt/Erwaegungen/Dispositiv)**
   - At 174k scale
   - Required for cross-lingual evaluation

---

## 6. Integration Architecture

### 6.1 Map Mode Registry Extension
```
Map Modes (v1.0+):
├── Primary (TF-IDF)
│   ├── cited_outcome_hybrid_0.5_174k (DEFAULT)
│   ├── cited_decisions_tfidf_174k
│   └── regeste_full_text_hybrid_0.5_174k
│
├── Complementary — Dense Embeddings (v1.1+)
│   ├── dense_citation_heritage_174k
│   ├── dense_cross_lingual_sachverhalt_174k
│   ├── dense_cross_lingual_dispositiv_174k
│   └── dense_linear_hybrid_w03_174k
│
└── Exploratory (marked as such)
    └── ...
```

### 6.2 API Contract for Dense Modes
Each dense map mode must provide:
- `cluster_metadata.json` — legal context per cluster (branch, area, chamber, language)
- `zoom_mappings.json` — parent-child navigation at all resolution pairs
- `zoom_coherence.json` — validation metrics per coarse cluster
- `decision_clusters.json` — fast decision-to-cluster lookup
- `labels_res_*.npy` — label arrays for rendering (7 resolutions minimum)
- `labels_hierarchical_best.npy` — best validated hierarchical config

### 6.3 Product Integration Points
```python
# Map mode selection
from fractal_map.hierarchical.map_mode_registry import MapModeRegistry

registry = MapModeRegistry()

# Primary modes (TF-IDF) — available now
primary_modes = registry.get_modes(category='primary')

# Complementary modes (dense) — available after data blocker resolves
dense_modes = registry.get_modes(category='complementary')

# User-facing: mode selector in UI with clear labeling
# "Primary: Jurist Preference (TF-IDF)"
# "Complementary: Citation Heritage (Dense)"
# "Complementary: Cross-Lingual (Dense)"
```

---

## 7. Validation Gates for Dense Embedding Delivery

### Gate 1: 174k Dense Embeddings Computed (Legal-Distance Lane)
- [ ] Full 174,113 decisions embedded (768-dim)
- [ ] Checkpoint verification: 26/26 years complete
- [ ] Metadata alignment with `bge_` IDs

### Gate 2: Multi-Level Protocol PASS (Fractal-Map Lane)
- [ ] All structural checks PASS (nesting ≥0.95, singleton <0.01, etc.)
- [ ] All threshold checks PASS (level1 branch >0.5, level2 area >0.15, level3 area >0.2)
- [ ] Fine branch purity > 0.90
- [ ] 7+ resolution levels with meaningful subdivision

### Gate 3: Complementary Capability Validation (Evaluation Lane)
- [ ] Citation heritage AUC > 0.75
- [ ] Cross-lang same-branch (Sachverhalt) > 0.2
- [ ] Cross-lang same-branch (Dispositiv) > 0.1
- [ ] Linear hybrid w=0.3–0.4 PASS adversarial gates

### Gate 4: Product Integration (Product Lane)
- [ ] WebGL rendering <3s at 174k
- [ ] 16/16 scale simulation tests PASS
- [ ] Map mode selector with clear primary/complementary labeling
- [ ] Decision inspection with multi-view context

---

## 8. Timeline and Milestones

| Milestone | Target | Owner | Dependencies |
|-----------|--------|-------|--------------|
| Corpus lane: BGE/bger mapping + 2022–2026 parquet | TBD | Corpus | — |
| Legal-distance: 174k dense embeddings (26 years) | After corpus | Legal-Distance | Corpus lane |
| Fractal-map: Multi-level protocol validation | After dense | Fractal-Map | Legal-Distance |
| Evaluation: Complementary capability benchmarks | After fractal-map | Evaluation | Fractal-Map |
| Product: v1.1 multi-view deployment | After evaluation | Product | All above |

---

## 9. Negative Results Preserved

The following **negative results are first-class ACCEPTED evidence** and must not be discarded:

1. Dense embeddings FAIL jurist gate at ALL scales tested (JP 0.05–0.43)
2. Linear hybrids PASS adversarial but BELOW TF-IDF baseline (JP 0.66–0.67 vs 0.78–0.79)
3. True OOS JuristPref ceiling ~0.53 < 0.7 factory target
4. v18 coarse hierarchy NEGATIVE (max branch purity 0.65 < 0.7)
5. Citation heritage recall@10: NEGATIVE (max 0.0066)
6. TF-IDF calibration FAILS (thresholds too aggressive for signal density)

These findings **define the boundaries** of what dense embeddings can and cannot do — they are essential for the integration contract.

---

## 10. Sign-Off

This contract is **ACCEPTED** based on:
- Factory Direction v34 strategic pivot
- ACCEPTED evidence from v28, v29, v30, v31, v32, v33 cycles
- 12k/28k/144k dense embedding validation
- 174k TF-IDF production readiness confirmation

**Implementation proceeds when data blocker resolves.** No further same-question cycles justified.

---

*Generated from ACCEPTED evidence. All metrics frozen before observation. Provenance preserved in `/tmp/lex_control/state/fractal_map.json` and referenced results directories.*