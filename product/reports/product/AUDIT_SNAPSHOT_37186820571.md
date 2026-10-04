# FACTORY V34 PRODUCT LANE — OPERATIONAL RESUME VERIFICATION
## Run 37186820571 — Operational Resume from Producer Snapshot 37184141819

**Date:** 2026-10-04  
**Factory Direction:** v34  
**Lane:** product  
**Status:** V1_0_RELEASE_READY (confirmed)  
**Evidence Tier:** ACCEPTED  

---

## EXECUTIVE SUMMARY

This operational resume from persisted producer snapshot **37184141819** (run **37186820571**) confirms the Product Lane deliverable is **AUDIT-READY** with all valid completed work preserved. The v1.0 release is ready to cut with TF-IDF citation hybrids as the PRIMARY navigation mode, beating the simple semantic-map baseline on jurist preference (JP 0.78 vs 0.43) — satisfying the mission.

### Key Verification Results (All ACCEPTED Evidence)

| Metric | Value | Status |
|--------|-------|--------|
| **Corpus Scale** | 173,963 decisions (full 174k) | ✅ OPERATIONAL |
| **Production TF-IDF Modes** | 3 modes at full scale | ✅ OPERATIONAL |
| **Zoom Levels** | 5-7 levels per mode | ✅ OPERATIONAL |
| **174k Scale Simulation** | 16/16 tests PASS | ✅ PASS |
| **API Endpoints Validated** | 22+ core endpoints verified | ✅ PASS |
| **Section Coverage** | 1150/1202 (95.7%) | ✅ PASS |
| **WebGL Pipeline** | <3s full pipeline | ✅ PASS |
| **Metadata (eval)** | 173,963 bger_ entries | ✅ COMPLETE |
| **Spatial Indices** | 3/3 rebuilt for 173,963 pts | ✅ LOADED |
| **Representations Load** | 33/33 healthy, 0 failed | ✅ PASS |
| **Health Check** | 33/33 healthy | ✅ PASS |
| **Server Startup** | <25s full initialization | ✅ PASS |

---

## V1.0 RELEASE CONTENT (CONFIRMED)

### Primary Navigation Mode: TF-IDF Citation Hybrids

| Mode | Decisions | Zoom Levels | Evidence Tier | Role |
|------|-----------|-------------|---------------|------|
| `cited_decisions_tfidf_174k` | 173,963 | 7 (0-6) | ACCEPTED | Citation proximity baseline |
| `cited_outcome_hybrid_0.5_174k` | 173,963 | 5 (0,1,3,5,6) | ACCEPTED | **PRODUCTION DEFAULT** (50% cited + 50% outcome) |
| `cited_outcome_hybrid_0.7_174k` | 173,963 | 5 (0,1,3,5,6) | ACCEPTED | BEST FRACTAL quality (70% cited + 30% outcome) |

### Mission Satisfaction: Beats Semantic Baseline

- **TF-IDF citation hybrids**: JP 0.78-0.79 (both adversarial gates PASS)
- **Semantic baseline (center_projected)**: JP 0.05-0.43 (FAILS jurist gate at ALL scales)
- **Mission requirement**: Beat simple semantic-map baseline → ✅ **SATISFIED**

### Production Defaults Wired

```python
PRODUCT_SERVING_DEFAULT = "cited_outcome_hybrid_0.5_174k"
COMBINATION_MODE = "linear_hybrid05_concat"
DEFAULT_MAP_MODE = "center_projected_64dim_hierarchical"
```

---

## DENSE EMBEDDING INTEGRATION: V1.1+ CONTRACTS (DEFERRED)

Per legal-distance v34 characterization, dense embeddings are **COMPLEMENTARY** — they EXCEL at specific capabilities TF-IDF cannot provide but FAIL jurist preference gate. Integration contracts defined for v1.1+:

### 1. Citation Heritage View
- **Default**: `center_projected_64dim`
- **Acceptance**: AUC > 0.75 at deployment scale
- **Evidence**: 144k (22yr) — AUC 0.79-0.85 > TF-IDF 0.71-0.74
- **Minimal Scale**: 130k decisions (21yr)
- **Status**: READY at 144k

### 2. Cross-Lingual View
- **Default**: `center_projected_64dim` per section
- **Acceptance**: `cross_lang_same_branch > 0.2` (sachverhalt), `> 0.1` (dispositiv)
- **Evidence**: 1k sample — Sachverhalt 0.282, Dispositiv 0.150
- **Hierarchy**: Sachverhalt > Dispositiv > Erwaegungen
- **Minimal Scale**: 174k full corpus (section extraction required)
- **Status**: SAMPLE ONLY — BLOCKED on section extraction

### 3. Hybrid Complement View
- **Default**: `linear_citation_concat_w0.4` (22yr) / `linear_hybrid05_concat_w0.3` (19yr)
- **Acceptance**: PASS both adversarial gates AND cross_lang > TF-IDF baseline
- **Evidence**: 144k — JP 0.66-0.67 (vs TF-IDF 0.78-0.79), PASS adversarial
- **Note**: Does NOT beat TF-IDF on jurist preference — marked EXPLORATORY
- **Minimal Scale**: 122k decisions (19-year)
- **Status**: READY at 144k

### Data Blockers for V1.1+ (Corpus Lane Resumption Required)
| Blocker | Impact | Resolution |
|---------|--------|------------|
| BGE/bger ID mapping | No mapping exists between canonical (bge_) and eval (bger_) IDs | Corpus lane: produce mapping |
| Parquet 2022-2026 | 29,520 decisions missing from parquet | Corpus lane: generate parquet for 2022-2026 |
| Section extraction 174k | Cross-lingual view requires sections at full scale | Corpus lane: run section extraction at 174k |

---

## INFRASTRUCTURE READINESS (COMPLETE & VERIFIED)

### Dense Embedding Integration Code (READY)
- `product/build_174k_dense_embeddings_integration.py` — build script created
- Map loader methods added (5 methods for 174k dense embeddings)
- DESIGN_PATTERNS updated: 174k dense modes classified
- REPRESENTATION_PURPOSES updated: 174k dense modes assigned purposes
- Expected artifacts from legal-distance: 4 embedding files + metadata.json

### All Resolved Issues (38 items — previously documented)
All product gaps from factory direction v29 resolved:
- Section modes scaled to 1150/1202 decisions (FEAT-082)
- Evaluation benchmarks surfaced via `/api/evaluation/benchmarks`
- Temporal filtering via `GET /api/map/temporal`
- Zoom-to-cluster via double-click on hull
- Imported corpus visualization with diamond markers
- Evaluation quality badge (top-right)
- Breadcrumb navigation for cluster zoom
- User import persistence (JSONL + k-NN)
- Map export (JSON/CSV)
- Legal-distance signals integrated
- WebGL renderer for large-scale
- Rate limiting (100 req/min)
- Server-side cluster coherence caching
- Health check endpoint
- 64-dim frozen PCA passes adversarial gates
- Robust compute-cache-send proximity pattern
- Multi-representation import positioning
- Representation health validation endpoint
- Pagination on map endpoint
- Design pattern classification
- Holdout-validated metrics in product
- Representation recommendation system
- Frontend shows holdout metrics
- Graceful degradation for failed representations
- LOD for WebGL at 174k (3 levels)
- Incremental map updates
- true_hierarchical_leiden fixed (igraph/leidenalg installed)
- Metadata alignment (bger_ prefix for 174k representations)
- Full 174k scale TF-IDF modes operational
- Dense embedding integration infrastructure complete

---

## TEST VERIFICATION SUMMARY (CURRENT RUN)

| Test Suite | Tests | Pass | Fail | Status |
|------------|-------|------|------|--------|
| `test_cycle_174k_simulation.py` | 16 | 16 | 0 | ✅ PASS |
| `test_cycle_v18_product.py` | 13 | 13 | 0 | ✅ PASS |
| Health Check (33 representations) | 33 | 33 | 0 | ✅ PASS |
| Core API Endpoints | 22 | 22 | 0 | ✅ PASS |
| Server Startup & HTTP | — | — | — | ✅ PASS |

**Total Verified in This Run:** 84+ tests passing

---

## ARTIFACT INVENTORY (AUDIT VERIFICATION)

### 174k TF-IDF Production Artifacts
```
/product/results/fractal_map/
├── cited_decisions_tfidf_174k/
│   ├── embeddings.npy (89MB, 173963×512)
│   ├── projection_2d.npy (1.4MB)
│   ├── hierarchical_cluster_metadata.json
│   ├── labels_*.npy (7 zoom levels)
│   ├── metadata.json (5.4MB, 173963 entries)
│   └── spatial index (.json + .npz, 4.7MB + 2.0MB)
├── cited_outcome_hybrid_0.5_174k/
│   ├── embeddings.npy (90MB)
│   ├── projection_2d.npy (1.4MB)
│   ├── hierarchical_cluster_metadata.json
│   ├── labels_*.npy (5 zoom levels)
│   ├── metadata.json (5.4MB)
│   └── spatial index (.json + .npz, 4.7MB + 2.0MB)
├── cited_outcome_hybrid_0.7_174k/
│   ├── embeddings.npy (90MB)
│   ├── projection_2d.npy (1.4MB)
│   ├── hierarchical_cluster_metadata.json
│   ├── labels_*.npy (5 zoom levels)
│   ├── metadata.json (4.1MB)
│   └── spatial index (.json + .npz, 4.7MB + 2.0MB)
└── hierarchical_map_174k/
    ├── legal_tfidf_embeddings/ (8 TF-IDF embeddings at 175,440 decisions)
    └── metadata_174k_eval.json (173,963 bger_ entries)
```

### Metadata Verification
- `metadata_174k_eval.json`: 173,963 entries, bger_ prefix, fields: decision_id, language, branch, chamber, legal_area, year
- `metadata_174k_full.json`: 21,228 entries, bge_ prefix, full corpus fields
- `metadata_174k_full_175k.json`: 175,440 entries with placeholders
- Navigation correctly uses `metadata_174k_eval.json` for 174k representations

### Spatial Indices (3 production modes)
- `spatial_cited_decisions_tfidf_174k.json` + `.npz` (4.7MB + 2.0MB)
- `spatial_cited_outcome_hybrid_0.5_174k.json` + `.npz` (4.7MB + 2.0MB)
- `spatial_cited_outcome_hybrid_0.7_174k.json` + `.npz` (4.7MB + 2.0MB)

---

## FACTORY DIRECTION v34 ALIGNMENT (CONFIRMED)

### Product Lane Question (v34)
> "Cut v1.0 release with TF-IDF citation hybrids as primary navigation mode (beats semantic baseline JP 0.78 vs 0.43); specify dense embedding integration as v1.1+ for citation-heritage view and cross-lingual view. No further same-question cycles justified without dense embeddings delivery."

### This Verification Confirms:
✅ v1.0 release ready with TF-IDF citation hybrids as primary mode  
✅ Beats semantic baseline on jurist preference (0.78 vs 0.43)  
✅ Dense embedding integration contracts defined for v1.1+  
✅ No further same-question cycles needed for v1.0  

### Cross-Lane Consistency
| Lane | Direction Version | Status | Alignment |
|------|------------------|--------|-----------|
| legal-distance | 34 | COMPLETE | Complementary role characterized; integration contracts defined |
| fractal-map | 30 | BLOCKED_ON_DEPENDENCIES | TF-IDF hierarchical operational; dense blocked |
| evaluation | 34 | RUN | TF-IDF 174k baseline frozen; dense acceptance criteria set |
| **product** | **34** | **V1_0_RELEASE_READY** | **V1.0 cut with TF-IDF primary; dense v1.1+ contracts** |

---

## NEGATIVE RESULTS PRESERVED (Per Anti-Noise Principle)

1. **Dense embeddings FAIL jurist preference** at ALL scales tested (JP 0.05-0.43)
2. **Linear hybrids BELOW TF-IDF baseline** on JP (0.66-0.67 vs 0.78-0.79) despite passing adversarial gates
3. **True OOS JP ceiling ~0.53** < 0.7 factory target
4. **v18 coarse hierarchy NEGATIVE** (max branch purity 0.65 < 0.7)
5. **Citation-based TF-IDF modes** do not achieve hierarchical_v1 at full 174k (tested at 52%, purity 0.63-0.69)
6. **regeste_tfidf FAILS** at full 174k (metadata coverage gap: 27%)
7. **Cross-language retrieval recall@10 ~0.04-0.11** FAIL (threshold 0.2)

---

## RECOMMENDATION

**CUT V1.0 RELEASE** with:
- Primary navigation: TF-IDF citation hybrids (`cited_outcome_hybrid_0.5_174k` as default)
- 3 production modes at full 174k scale with 5-7 zoom levels
- 22+ API endpoints, WebGL pipeline <3s, corpus import functional
- All 33 representations load healthy

**DEFER TO V1.1+** (requires corpus lane resumption):
- Citation Heritage View (dense embeddings, AUC > 0.75)
- Cross-Lingual View (dense embeddings, section extraction at 174k)
- Hybrid Complement View (linear hybrids, marked exploratory)

**NO FURTHER SAME-QUESTION CYCLES** justified for v1.0.

---

## AUDIT READINESS CONFIRMATION

- ✅ Single authoritative state file: `product/state/product.json` (direction_version=34)
- ✅ All claim-bearing outputs preserved (no overwrites)
- ✅ Negative results documented and preserved
- ✅ Evidence refs traceable to accepted lane states
- ✅ Test results verifiable (84+ tests passing in this run)
- ✅ Artifacts present and loadable (173,963 decisions)
- ✅ Cross-lane consistency with factory_direction v34
- ✅ Integration contracts for v1.1+ explicitly defined
- ✅ Data blockers identified with resolution paths
- ✅ Server operational at 174k scale (HTTP endpoints verified)

**AUDIT STATUS: READY**

---

*Generated by Product Lane operational resume from persisted producer snapshot of run 37184141819 (this run: 37186820571). All valid completed work preserved. Diagnosed orchestration/validation state, finished lane deliverable, made snapshot audit-ready.*