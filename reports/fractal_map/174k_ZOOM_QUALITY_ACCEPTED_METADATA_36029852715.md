# 174k Zoom Quality vs ACCEPTED Evaluation Metadata — Run 36029852715

**Lane**: fractal-map | **Direction v25** | **Date**: 2026-09-24
**Status**: New claim-bearing evaluation delivered. Verdict: **FAIL on monotonic zoom-refinement** for TF-IDF 174k modes (honest negative result). `corpus_174k_metadata` blocker **CLEARED** by evidence; `legal-distance_174k_dense_embeddings` remains BLOCKED.

---

## 1. What was done (real executable work)

1. **Full frozen suite with complete deps**: installed `python-igraph 1.0.0` + `leidenalg 0.12.0` (numpy 2.5.3, scipy 1.18.1, scikit-learn 1.9.1, pytest 9.1.1) → `tests/fractal_map/test_verify.py` = **184/184 PASS** (1.39s). The 184th test (Leiden recompute guard) is now executed, not skipped.
2. **174k artifact census + provenance audit** of the 6 "true-174k" dirs in `results/fractal_map/legal_distance_modes/`:
   - **4 decision-mappable**: `cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25`, `cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25`, `cited_decisions_tfidf_outcome_hybrid_0.5_174k`, `regeste_tfidf_174k` — `decision_clusters.json` has 174,126 real `bger_*` IDs; full overlap with accepted metadata (173,963/173,963 of meta IDs present in builds; 163 build-only IDs are 2000-era BGE ids not in metadata).
   - **2 placement-only (NOT decision-mappable)**: `cited_decisions_tfidf_174k_compressed_v25`, `outcome_tfidf_174k_compressed_v25` — decision_clusters keys are `bger_placeholder_*` (175,440). These cannot serve real decision lookups; census note corrected.
   - **Provenance caveats recorded**: labels arrays are 175,440 rows while decision_clusters has 174,126 keys (labels from the 175,440-row placeholder embedding run; ID→cluster mapping authoritative artifact is `decision_clusters.json`, which the product's `map_mode_loader.get_decision_clusters` consumes). Small internal inconsistencies: decision_clusters vs cluster_metadata (63–321 decisions at fine resolutions), decision_clusters vs zoom_mappings (~0.02–0.13% at first transition). No rebuild possible this cycle (full corpus JSONL not mounted; dense 174k embeddings not in accepted state).
3. **Frozen claim-bearing experiment** (`results/fractal_map/zoom_quality_174k_eval/v25_frozen_spec.json`, frozen before computing outcomes):
   - Hypothesis: 5-level compressed ladder [0.25,0.5,1.0,2.0,3.0] on full-corpus TF-IDF representations recovers legal structure: purity w.r.t. ACCEPTED labels monotonically increases coarse→fine, and zoom transitions improve purity.
   - Data: `decision_clusters.json` (ID→cluster) × ACCEPTED `/tmp/lex_accepted/evaluation/evaluation/data/174k/metadata_174k.json` (173,963 entries; branch + legal_area 100% field coverage; 214 raw legal_areas; 83,331 'unknown' branch / 82,770 'unknown' area excluded from purity).
   - Metric: mean cluster purity per resolution (excl. unknown, clusters ≥3 labeled decisions), zoom mean_improvement + improvement_rate per transition (parents ≥3 labeled children).
   - Success rule (production default `cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25`): (a) branch purity res_3.0 > res_0.25; (b) area purity res_3.0 > res_0.25; (c) branch improvement_rate > 0.5 on ≥2 of 4 transitions.
4. **Computation** → raw outputs `v25_raw_purity.json`, `v25_raw_zoom.json`; verdict `v25_verdict.json`.

## 2. Results (freeze-protected, negative preserved)

Production default, vs ACCEPTED metadata (90,632 branch-labeled / 91,193 area-labeled of 173,963 joined):

| res | branch purity (n_clusters) | area purity (n_clusters) |
|---|---|---|
| 0.25 | 0.5525 (21) | 0.3134 (22) |
| 0.5  | 0.5128 (30) | 0.2732 (31) |
| 1.0  | 0.5324 (44) | 0.2648 (45) |
| 2.0  | 0.5140 (64) | 0.2438 (64) |
| 3.0  | 0.5273 (84) | 0.2622 (84) |

Zoom transitions (branch): mean_improvement +0.0386/+0.0336/+0.0257/+0.0190; improvement_rate 0.31/0.46/0.59/0.38. **All three frozen success checks FAIL** (area monotonicity fails, branch monotonicity fails, rate>0.5 on only 1/4 transitions). Verdict: **FAIL**.

**Structure signal is strong**: purity >> random baseline (branch ~0.51–0.55 vs 1/4≈0.25; area ~0.24–0.31 vs 1/214≈0.005) at ALL resolutions. TF-IDF 174k modes encode legal structure but do NOT refine it monotonically via the zoom ladder; zooming to fine resolutions does not deliver purer legal clusters.

**Fine-level fragmentation**: res_2.0=12,852 clusters, res_3.0=63,778 clusters, median cluster size 1 → the fine ladder levels are over-fragmented; zoom refinement is structurally unavailable in these TF-IDF 174k builds.

**Consistency with prior evidence**: citation_heritage_174k FAIL (AUC 0.482 vs 0.65, accepted eval state); 1000-scale zoom-quality diagnostic: citing ZQ=0.5401/following 0.5280/criticizing 0.4864 top, production default outcome_hybrid_0.5 ZQ=0.2798 ranked 21st; evaluation lane v17b clustering test still PENDING dense 174k embeddings.

## 3. Conclusions & state delta

- `corpus_174k_metadata` blocker **CLEARED**: evaluation lane delivered ACCEPTED `metadata_174k.json` (173,963, branch+area 100% coverage). This enabled the first **legal_area-level 174k zoom-quality evaluation against ACCEPTED labels**. Prior 174k `branch_coherence` in builds came from build-time metadata, not accepted 174k labels; no prior area-level 174k evaluation existed.
- `legal-distance_174k_dense_embeddings` remains **BLOCKED** (not in accepted state per evaluation v25 deps; dense/citation-role modes at 174k await it).
- Zoom-quality claim at 174k for TF-IDF-only modes: **NOT established** (FAIR, evidence: verdict JSON). Citation-role/dense modes remain the evidence-backed zoom path (top ZQ at 1000-scale, per accepted audit CYCLE_33342328845 rec #4).
- **Multi-view zoom UI with citation-role views** (audit rec #4): verified **implemented at product level** (`/tmp/lex_accepted/product/product/static/index.html` map-mode dropdown includes CITATION ROLE VIEWS optgroup: following/criticizing/citing_alpha0.3; zoom controls; webgl renderer multi-view; `section_modes.py` multi-view navigation). No additional fractal-map-side UI artifact required this cycle.
- continue_recommended=false remains correct (single blocker on dense embeddings).

## 4. Artifacts

- `results/fractal_map/zoom_quality_174k_eval/v25_frozen_spec.json`
- `results/fractal_map/zoom_quality_174k_eval/v25_raw_purity.json`
- `results/fractal_map/zoom_quality_174k_eval/v25_raw_zoom.json`
- `results/fractal_map/zoom_quality_174k_eval/v25_verdict.json`
- `tests/fractal_map/test_zoom_quality_174k_eval.py` (additive guard test)
- This report.

## 5. Verification

- `184/184` frozen tests PASS with igraph/leidenalg installed.
- Guard test passes: verdict artifact exists, checks flagged correct, verdict==FAIL, raw joins = 173,963, monotonicity booleans as recorded.