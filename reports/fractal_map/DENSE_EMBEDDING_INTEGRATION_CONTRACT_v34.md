# Dense Embedding Integration Contract for Fractal Map v1.1+

**Factory Direction Version:** 34
**Lane:** fractal-map
**Status:** CONTRACT DEFINED — Awaiting legal-distance 174k dense embeddings delivery
**Date:** 2026-10-03

---

## 1. Purpose

This contract defines the acceptance criteria, validation requirements, and integration specifications for dense embeddings into the fractal map product. Per factory_direction v34, TF-IDF citation hybrids are the PRIMARY product mode (v1.0). Dense embeddings are COMPLEMENTARY modes for v1.1+ providing:

1. **Citation Heritage View** — doctrinal proximity via citation graph recovery
2. **Cross-Lingual View** — language-invariant factual/holding alignment
3. **Linear Hybrid Complement** — semantic enhancement of TF-IDF baselines

---

## 2. Required Dense Embedding Modes

| Mode | Source | Purpose | Minimum Scale |
|------|--------|---------|---------------|
| `center_projected_64` | legal-distance (multilingual-e5 + center projection) | Citation heritage + cross-lingual base | 174k (full corpus) |
| `center_projected_128` | legal-distance (multilingual-e5 + center projection) | Higher-dim citation heritage | 174k (full corpus) |
| `citation_role_dense` (citing/following/criticizing) | legal-distance (role-specific) | Fine-grained citation heritage | 174k (full corpus) |
| `section_dense_sachverhalt` | legal-distance (section extraction) | Cross-lingual facts view | 174k (full corpus) |
| `section_dense_dispositiv` | legal-distance (section extraction) | Cross-lingual holdings view | 174k (full corpus) |
| `section_dense_erwaegungen` | legal-distance (section extraction) | Cross-lingual reasoning view | 174k (full corpus) |
| `linear_hybrid_03` / `linear_hybrid_04` | legal-distance (TF-IDF + dense concat) | Hybrid complement to TF-IDF | 174k (full corpus) |

**Non-negotiable:** All modes must be computed on the **same bger_ ID space** as the 174k TF-IDF corpus (173,963 decisions, 2000-2026). The BGE/bger ID mapping and parquet for 2022-2026 are hard prerequisites.

---

## 3. Acceptance Criteria (Frozen Before Evaluation)

### 3.1 Citation Heritage View (Primary Complementary Mode)

**Metric:** AUC on frozen citation heritage pair pool (1,020 positive/negative pairs from 174k citation-ID resolution)

| Threshold | Requirement |
|-----------|-------------|
| AUC > 0.75 | **MUST PASS** — dense embeddings must exceed TF-IDF citation-based (AUC 0.71-0.74) |
| AUC > 0.80 | TARGET — matches 21-22yr checkpoint evidence (0.79-0.85) |

**Validation:** `evaluate_174k_dense_embeddings.py` citation heritage module on frozen pair pool.

### 3.2 Cross-Lingual View (Section-Specific)

**Metric:** `cross_lang_same_branch` at fine resolution (coarse=0.5, fine=2.0, min_cluster=20) on section embeddings

| Section | Threshold | Evidence Basis |
|---------|-----------|----------------|
| `sachverhalt` (facts) | > 0.20 | 1K sample: cp_64 = 0.282, gap = 0.187 |
| `dispositiv` (holdings) | > 0.10 | 1K sample: cp_64 = 0.150, gap = 0.397 |
| `erwaegungen` (reasoning) | MONITOR ONLY | 1K sample: cp_64 = 0.094, gap = 0.452 (known weak) |

**Validation:** Multi-level hierarchical protocol on section embeddings at 174k.

### 3.3 Linear Hybrid Complement

**Metric:** Jurist Preference (JP) and Language Dominance (LangDom) on frozen adversarial harness v3

| Threshold | Requirement |
|-----------|-------------|
| JP > 0.50 | **MUST PASS** — adversarial gate |
| LangDom < 0.85 | **MUST PASS** — adversarial gate |
| JP > 0.65 | TARGET — optimal weight w=0.3-0.4 per 22yr scale evidence |

**Note:** Linear hybrids at 22yr (144k) achieved JP=0.66-0.67 at optimal weight but REMAIN BELOW TF-IDF baseline (JP=0.78-0.79). This is ACCEPTED — hybrids are COMPLEMENTARY, not primary.

### 3.4 Hierarchical Structure (All Dense Modes)

**Protocol:** Multi-level recursive purity-aware protocol (same as TF-IDF validation)

| Metric | Threshold |
|--------|-----------|
| strict_nesting | ≥ 0.99 |
| fragmentation (singleton_fraction) | < 0.05 (relaxed from TF-IDF 0.01 due to scale) |
| fine_branch_purity (legal_structure_branch) | > 0.5 |
| zoom improvement_rate (branch) | > 0.5 |
| zoom improvement_rate (area) | > 0.5 |

**Validation:** `evaluate_174k_dense_embeddings.py` + `build_dense_hierarchical_artifacts.py` with multi-level protocol.

---

## 4. Integration Specifications

### 4.1 Map Mode Registration

Each accepted dense mode registers in `map_mode_registry.py` with:

```python
{
    "mode_id": "center_projected_64_174k",
    "display_name": "Citation Heritage (Dense)",
    "view_category": "citation_heritage",  # or "cross_lingual", "hybrid_complement"
    "evidence_tier": "ACCEPTED",
    "hierarchical_protocol": "multi_level_recursive",
    "zoom_levels": 7,
    "projection": "umap",  # preferred; PCA fallback documented
    "dependencies": ["legal_distance_174k_dense"],
    "acceptance_criteria_ref": "DENSE_EMBEDDING_INTEGRATION_CONTRACT_v34.md#3.1"
}
```

### 4.2 Product UI Exposure

| View Category | UI Entry Point | Default Zoom |
|---------------|----------------|--------------|
| citation_heritage | "Citation Heritage" map mode switch | Level 2 (subdomain) |
| cross_lingual | "Cross-Lingual: Facts/Holdings/Reasoning" submenu | Level 3 (subcluster) |
| hybrid_complement | "Hybrid Enhanced" toggle on TF-IDF modes | Same as base TF-IDF |

### 4.3 API Endpoints

New endpoints added alongside existing TF-IDF endpoints:
- `GET /api/map/modes?category=citation_heritage`
- `GET /api/map/modes?category=cross_lingual`
- `GET /api/map/modes?category=hybrid_complement`
- `GET /api/cluster/{id}/cross_lingual_neighbors` (section-dense modes)

---

## 5. Validation Pipeline (Run on Delivery)

```bash
# 1. Evaluate all dense modes on frozen 174k harness
python fractal_map/hierarchical/evaluate_174k_dense_embeddings.py \
    --modes-dir /path/to/174k_dense_embeddings \
    --metadata /tmp/lex_accepted/evaluation/results/fractal_map/hierarchical_map_174k/metadata_174k_full.json \
    --output results/fractal_map/dense_174k_evaluation/

# 2. Build hierarchical artifacts for accepted modes
python fractal_map/hierarchical/build_dense_hierarchical_artifacts.py \
    --eval-results results/fractal_map/dense_174k_evaluation/ \
    --output results/fractal_map/dense_hierarchical_artifacts_174k/

# 3. Run multi-level protocol validation
python fractal_map/hierarchical/run_multi_level_protocol_174k_dense.py \
    --artifacts results/fractal_map/dense_hierarchical_artifacts_174k/ \
    --output results/fractal_map/multi_level_174k_dense/

# 4. Register accepted modes
python fractal_map/hierarchical/update_registry.py \
    --new-modes results/fractal_map/dense_hierarchical_artifacts_174k/ \
    --contract DENSE_EMBEDDING_INTEGRATION_CONTRACT_v34.md
```

---

## 6. Evidence References (Pre-Commitment)

| Finding | Source | Status |
|---------|--------|--------|
| Citation heritage AUC 0.79-0.85 at 21-22yr (137k-144k) | legal-distance checkpoints | PENDING AUDIT PROMOTION |
| Section cross-lingual: Sachverhalt > Dispositiv > Erwaegungen | legal-distance 1K sample | REPRODUCED (needs 174k) |
| Linear hybrid optimal w=0.3-0.4, JP=0.66-0.67 | legal-distance 19yr/22yr | REPRODUCED (needs 174k) |
| Multi-level protocol PASS at 12k (ACCEPTED dense) | fractal-map preparatory | ACCEPTED |
| Scale extrapolation 28k → 144k → 174k stable | fractal-map checkpoints | EXPLORATORY |

---

## 7. Blockers (Must Resolve Before Integration)

1. **BGE/bger ID mapping** — canonical corpus uses `bge_` IDs, evaluation uses `bger_` IDs; no mapping exists
2. **Parquet for 2022-2026** — 29,520 decisions missing from checkpointed 144k (2000-2021)
3. **Section extraction at 174k** — sachverhalt/erwaegungen/dispositiv not extracted at full corpus scale
4. **Corpus lane resumption** — currently PAUSED at v17 snapshot

**Resolution path:** Corpus lane must resume for (1) and (2). Section extraction pipeline must be built for (3). legal-distance lane cannot deliver 174k dense embeddings without these.

---

## 8. Success Definition for v1.1+ Release

The fractal map v1.1+ releases when **ALL THREE** complementary views have at least one mode meeting acceptance criteria:

- [ ] Citation Heritage: ≥1 mode with AUC > 0.75 on frozen 174k pair pool
- [ ] Cross-Lingual: sachverhalt cross_lang_same_branch > 0.20 at 174k
- [ ] Hybrid Complement: ≥1 linear hybrid mode PASSING both adversarial gates at 174k

**TF-IDF v1.0 modes remain the primary navigation default.** Dense modes are additive enhancements for specific legal navigation tasks.

---

## 9. Sign-Off

| Role | Status |
|------|--------|
| Fractal Map Lane (this contract) | DEFINED |
| Legal Distance Lane (delivery) | BLOCKED ON DEPENDENCIES |
| Evaluation Lane (validation) | CRITERIA FROZEN |
| Product Lane (integration) | SPECIFIED |

**Next Action:** Factory Director decision on corpus lane resumption / Frontier team for data acquisition per factory_direction v34 director_note.

---

*This contract is immutable once dense embeddings delivery begins. Any criterion change requires new factory_direction version and new contract version.*