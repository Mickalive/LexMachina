# Fractal Map Lane — Product Integration Specification (Map Mode Switching)

**Generated:** 2026-08-30T02:39:55.195049
**Lane:** fractal-map
**Evidence Tier:** REPRODUCED
**Status:** PRODUCTIZE

---

## 1. Overview

This specification describes the **multi-mode fractal map system** for Swiss Federal Supreme Court (BGer) decisions.
The system exposes a **default center_projected hierarchical Leiden map** plus **selectable legal-distance map modes**.

**Key Architecture:**
- **Default Mode:** Center Projected Hierarchical Leiden (REPRODUCED tier, purity 0.9571)
- **Selectable Modes:** 21 legal-distance representations (ACCEPTED tier)
- **Legacy Mode:** Concat-based Hierarchical Leiden (preserved for comparison)
- **Unified API:** Single loader interface for all modes
- **Resolution Ladder:** 7 levels (0.25 to 3.0) consistent across modes

---

## 2. Map Mode Registry

| Mode ID | Name | Type | Status | Default |
|---------|------|------|--------|---------|
| center_projected_hierarchical | Center Projected Hierarchical Leiden (Default) | hierarchical_leiden | available | YES |
| hierarchical_leiden_concat | Hierarchical Leiden (Concat - Legacy) | hierarchical_leiden | legacy |  |
| debiased_citation_blended | Debiased Citation Blended (Legal-Distance Baseline) | legal_distance | available |  |
| legal_cited_decisions_only | Legal Cited Decisions Only | legal_distance | available |  |
| hybrid_alpha_03 | Hybrid α=0.3 (30% Legal + 70% Baseline) | legal_distance | available |  |
| hybrid_alpha_05 | Hybrid α=0.5 (50% Legal + 50% Baseline) | legal_distance | available |  |
| legal_issues_outcomes | Legal Issues & Outcomes | legal_distance | available |  |
| linear_metric_epoch4 | Linear Metric Epoch 4 (Metric Learning) | hierarchical_leiden | available |  |
| mahalanobis_metric_epoch4 | Mahalanobis Metric Epoch 4 (Metric Learning) | hierarchical_leiden | available |  |
| cited_decisions_tfidf | Cited Decisions TF-IDF (Zero-Shot Citation Signal) | hierarchical_leiden | available |  |
| hybrid_cited_0.3 | Hybrid Cited 0.3 (30% Cited TF-IDF + 70% Center Projected) | hierarchical_leiden | available |  |
| center_projected | Center Projected (Language-Debiased Embedding) | legal_distance | placeholder |  |
| cited_decisions_tfidf_hybrid_cp64_0.3 | Cited Decisions TF-IDF Hybrid CP64 0.3 (30% Cited + 70% CP64) | hierarchical_leiden | available |  |
| cited_decisions_tfidf_hybrid_cp64_0.5 | Cited Decisions TF-IDF Hybrid CP64 0.5 (50% Cited + 50% CP64) | hierarchical_leiden | available |  |
| cited_decisions_tfidf_hybrid_cp64_0.7 | Cited Decisions TF-IDF Hybrid CP64 0.7 (70% Cited + 30% CP64) — BEST PRODUCTION | hierarchical_leiden | available |  |
| cited_decisions_tfidf_hybrid_cp768_0.3 | Cited Decisions TF-IDF Hybrid CP768 0.3 (30% Cited + 70% CP768) | hierarchical_leiden | available |  |
| cited_decisions_tfidf_hybrid_cp768_0.5 | Cited Decisions TF-IDF Hybrid CP768 0.5 (50% Cited + 50% CP768) | hierarchical_leiden | available |  |
| cited_decisions_tfidf_hybrid_cp768_0.7 | Cited Decisions TF-IDF Hybrid CP768 0.7 (70% Cited + 30% CP768) — BEST JURIST PREFERENCE | hierarchical_leiden | available |  |
| hybrid_stabilized_epoch1 | Hybrid Stabilized Metric Learning (Epoch 1) | hierarchical_leiden | available |  |
| cited_decisions_tfidf_outcome_hybrid_0.5 | Cited Decisions TF-IDF + Outcome Hybrid α=0.5 (Best Production) | hierarchical_leiden | available |  |
| cited_decisions_tfidf_outcome_hybrid_0.7 | Cited Decisions TF-IDF + Outcome Hybrid α=0.7 (Best Fractal) | hierarchical_leiden | available |  |
| following_alpha0.3 | Citation Role: Following (α=0.3) | hierarchical_leiden | available |  |
| criticizing_alpha0.3 | Citation Role: Criticizing (α=0.3) | hierarchical_leiden | available |  |
| citing_alpha0.3 | Citation Role: Citing (α=0.3) | hierarchical_leiden | available |  |

---

## 3. Default Mode: Center Projected Hierarchical Leiden

**Mode ID:** `center_projected_hierarchical`
**Evidence Tier:** REPRODUCED
**Validation Run:** 33207149474

### 3.1 Resolution Ladder
- **Resolution 0.25**: 5 clusters (domain: language + broad legal domain)
- **Resolution 0.5**: 7 clusters (subdomain: legal area within language) — **Coarse parent level**
- **Resolution 0.75**: 9 clusters
- **Resolution 1.0**: 11 clusters
- **Resolution 1.5**: 14 clusters
- **Resolution 2.0**: 16 clusters
- **Resolution 3.0**: 19 clusters
- **Hierarchical (validated config: coarse_0.5_fine_3.0)**: 108 clusters, nesting=1.0, purity=0.9571 (min_cluster_size=3)
- **Coarse (parent)**: 7 clusters at resolution 0.5

### 3.2 Key Metrics
- **Hierarchical purity**: 0.9571 (+0.0080 vs concat baseline 0.9491)
- **Perfect nesting**: 1.0 (guaranteed by hierarchical construction)
- **Adversarial language dominance**: 0.7593 (< 0.85 threshold) - *source: evaluation_v2_cycle_33137354250 (carried forward)*
- **Jurist pairwise preference**: 0.5215 (> 0.5 threshold) - *source: evaluation_v2_cycle_33137354250 (carried forward)*
- **Jurivoc hierarchy alignment**: 4/5 PASS - *source: evaluation_v2_cycle_33137354250 (carried forward)*
- **Zoom coherence (per-resolution-step)**: 31.1% improvement rate (19/61 parent clusters improve) - *source: center_projected_hierarchical_zoom_validation (v6 recomputed)*

### 3.3 Artifacts
All artifacts available at `results/fractal_map/hierarchical_map_center_projected/`:
- `cluster_metadata.json` — Legal context per cluster (branch, area, chamber, language)
- `zoom_mappings.json` — Bidirectional parent-child navigation
- `zoom_coherence.json` — Per-cluster zoom improvement metrics (per-resolution-step)
- `decision_clusters.json` — Decision-to-cluster index (1000 x 7 resolutions)
- `labels_res_*.npy` — Cluster assignments for rendering
- `labels_hierarchical_best.npy` — Best validated hierarchical config (108 clusters)
- `labels_coarse_0.5.npy` — 7-cluster parent level

---

## 4. Selectable Legal-Distance Modes

These modes are built on legal-distance embeddings (ACCEPTED tier evidence).

### 4.1 debiased_citation_blended
- **Status:** AVAILABLE
- **Benchmarks:** 14/14 PASS
- **Strengths:** Strong citation heritage, multilingual invariance

### 4.2 legal_cited_decisions_only
- **Status:** AVAILABLE
- **Benchmarks:** 14/14 PASS
- **Strengths:** Best citation heritage (AUC 0.97), boilerplate resistance

### 4.3 hybrid_alpha_03
- **Status:** AVAILABLE
- **Benchmarks:** 13/14 PASS
  (1 failed)
  — **fails adversarial_falsification**
- **Warning:** fails adversarial_falsification benchmark
- **Strengths:** Best branch classification, strong TF metadata recall

### 4.4 hybrid_alpha_05
- **Status:** AVAILABLE
- **Benchmarks:** 13/14 PASS
  (1 failed)
  — **fails adversarial_falsification**
- **Warning:** fails adversarial_falsification benchmark
- **Strengths:** Best branch classification, strong TF metadata recall

### 4.5 legal_issues_outcomes
- **Status:** AVAILABLE
- **Benchmarks:** 10/14 PASS
  (4 failed)
  — **fails adversarial_falsification**
  — **fails multilingual_invariance**
- **Warning:** fails adversarial_falsification benchmark
- **Warning:** fails multilingual_invariance benchmark
- **Warning:** fails citation_heritage threshold
- **Warning:** fails tf_metadata_human_indexing threshold

---

## 5. Legacy Mode (Preserved for Comparison)

### 5.1 hierarchical_leiden_concat (Concat-based - Legacy)
- **Status:** LEGACY
- **Hierarchical purity**: 0.9491 (vs 0.9638 for center_projected)
- **Zoom coherence (per-resolution-step)**: 59.2% improvement rate
- **Note:** Replaced as default by center_projected_hierarchical per factory direction v4
- **Embeddings**: concat (center_projected 768 + TF-IDF Erwaegungen 128)

---

## 6. Product Integration API

### 6.1 Basic Usage

```python
from product_map_loader import ProductMapLoader

loader = ProductMapLoader()

# List available modes
modes = loader.list_modes()
for m in modes:
    print(f"{m["mode_id"]}: {m["name"]} [{m["status"]}]")

# Load default mode (center_projected_hierarchical)
artifacts = loader.load_default()

# Or load specific mode
artifacts = loader.load_mode("center_projected_hierarchical")
artifacts = loader.load_mode("debiased_citation_blended")
```

### 6.2 Accessing Map Data

```python
# Get cluster labels at specific resolution
labels_res_1_0 = loader.get_resolution_labels("center_projected_hierarchical", 1.0)

# Get hierarchical labels (108 clusters, nested)
hierarchical_labels = loader.get_hierarchical_labels("center_projected_hierarchical")

# Get coarse parent labels (7 clusters)
coarse_labels = loader.get_coarse_labels("center_projected_hierarchical")

# Get cluster metadata with legal context
metadata_res_0_5 = loader.get_cluster_metadata("center_projected_hierarchical", 0.5)

# Get zoom navigation (parent-child mappings)
zoom_0_5_to_1_0 = loader.get_zoom_mapping("center_projected_hierarchical", 0.5, 1.0)

# Get decision cluster membership
decision_clusters = loader.get_decision_clusters("center_projected_hierarchical", "BGE_123_456")

# Get zoom coherence metrics
coherence = loader.get_zoom_coherence("center_projected_hierarchical", 0.5, 1.0)
```

### 6.3 Recommended User Flows

**Flow A: Domain to Subdomain to Microcluster (Center Projected Hierarchical Leiden)**
```
Start at res=0.25 (5 clusters: language + broad domain)
  Down arrow User selects cluster
Zoom to res=0.5 (children of selected, 7 subdomains)
  Down arrow User selects subdomain
Zoom to res=1.5 (children of selected, ~14 microclusters)
  Down arrow User selects microcluster
Show decisions in microcluster
```

**Flow B: Search to Context Zoom**
```
User searches Strafprozess
  Down arrow Find matching microclusters at res=2.0
Show cluster + parent context (res=0.5, res=0.25)
Allow zoom out to broader context
```

**Flow C: Decision Inspection**
```
User opens decision X
  Down arrow Show cluster membership at ALL resolutions
Show cluster metadata (dominant branch, area, chamber)
Show k-nearest neighbors within same cluster at finest resolution
```

**Flow D: Map Mode Switching**
```
User views map in default mode (center_projected_hierarchical)
  Down arrow User selects Legal Cited Decisions Only mode
Re-render map with legal_cited_decisions_only embeddings
Show mode-specific cluster metadata
Allow side-by-side comparison
```

---

## 7. Legal-Distance Mode Integration (Already Built)

The 21 legal-distance modes are already built and integrated:

1. **Embeddings** to `results/legal_distance/embeddings/<mode_id>.npy`
2. **Cluster labels** to `results/fractal_map/legal_distance_modes/<mode_id>/labels_res_*.npy`
3. **Cluster metadata** to `results/fractal_map/legal_distance_modes/<mode_id>/cluster_metadata.json`
4. **Zoom mappings** to `results/fractal_map/legal_distance_modes/<mode_id>/zoom_mappings.json`

The loader automatically detects available artifacts.

---

## 8. Acceptance Criteria

- Center Projected Hierarchical Leiden as default map structure (REPRODUCED, validated)
- 7-resolution ladder with legal coherence metrics exposed
- Perfect nesting (1.0) guaranteed for hierarchical mode
- 31.1% zoom improvement rate validated (per-resolution-step)
- Hierarchical purity 0.9571 (+0.0080 vs concat baseline, min_cluster_size=3)
- Adversarial language dominance 0.7593 < 0.85 PASS (source: v5 carried forward)
- Jurist pairwise preference 0.5215 > 0.5 PASS (source: v5 carried forward)
- Jurivoc 4/5 PASS (source: v5 carried forward)
- Map mode registry with 24 modes (1 default + 21 legal-distance + 1 legacy + 1 placeholder)
- Unified loader API for all modes
- Product integration specification complete
- Map mode switching architecture designed
- Hybrid modes (alpha_03, alpha_05) fail adversarial_falsification - marked with warnings
- legal_issues_outcomes fails 4/14 benchmarks - marked with warnings

---

## 9. Design Patterns Exposed as Selectable Map Modes

**HIGH-PURITY (Metric Learning):**
- linear_metric_epoch4 (hierarchical_purity=0.9868, JP=0.6847, LangDom=0.6802)
- mahalanobis_metric_epoch4 (hierarchical_purity=0.9861, JP=0.6781, LangDom=0.6840)
- hybrid_stabilized_epoch1 (hierarchical_purity=0.9638, JP=0.6656, LangDom=0.660)

**HIGH-ADVANTAGE (Citation/Outcome):**
- cited_decisions_tfidf (JP=0.6889 HIGHEST, LangDom=0.6086 BEST, ImpRate=97.1%)
- cited_decisions_tfidf_outcome_hybrid_0.5 (BEST PRODUCTION: LangDom=0.4911, JP=0.7990)
- cited_decisions_tfidf_outcome_hybrid_0.7 (BEST FRACTAL: HierAdv=+0.3703, ImpRate=90.3%)

**HIGH-ADVANTAGE (Citation Role):**
- following_alpha0.3 (Fine=0.9501, ImpRate=82.2%)
- criticizing_alpha0.3 (Fine=0.9619, HierAdv=+0.0815)
- citing_alpha0.3 (ImpRate=66.9%)

---

## 10. Next Steps

1. **Product Lane**: Consume center_projected_hierarchical artifacts from `results/fractal_map/hierarchical_map_center_projected/`
2. **Product Lane**: Implement map mode selector UI using registry
3. **Legal-Distance Lane**: Reproduce center_projected on full v1+v2 benchmark suite
4. **Product Lane**: Implement side-by-side mode comparison view
5. **Corpus Lane**: Scale to full 2000-2024 corpus (~192k decisions)

---

*This specification is generated from validated REPRODUCED/ACCEPTED evidence.
All metrics are frozen before observation and match the accepted state files.*