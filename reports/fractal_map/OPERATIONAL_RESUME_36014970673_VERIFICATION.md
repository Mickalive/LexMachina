# Operational Resume Verification — Run 36014970673

## Summary
**Lane**: fractal-map  
**Factory Direction**: v25  
**GitHub Run**: 36014970673  
**Resume From**: 36008005345 (failed producer run, repair_round 0)  
**Timestamp**: 2026-09-24T00:00:00Z  
**Audit Status**: PASS (operational resume; see honesty caveats below)

## Verification Results
- **Tests**: 184/184 PASS (frozen suite `tests/fractal_map/test_verify.py`, unchanged)
- **Resumed Snapshot**: 24 files from run 36008005345 preserved and verified (2 complete compressed-ladder mode builds, 12 files each)
- **Modes Audited**: 46 compressed-ladder mode dirs + 3 reference dirs
- **Tracked Artifacts under `results/fractal_map/`**: 993 (unchanged except +1 new audit JSON)
- **Compressed 5-Level Ladder**: 100% delta retention (unchanged); **nesting claims corrected** (see metric defect section)
- **BLOCKED ON**: legal-distance 174k dense embeddings; corpus 174k metadata (unchanged)

## Diagnosis of Failed Run 36008005345
Run 36008005345 persisted a valid team snapshot (commit `b94d231a`, 24 files: `full_text_tfidf_light` 21k build + `cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25` build) but died **before** producing the audit gate, verification report, and `state/fractal-map.json` update. No remote audit branch `cycle/core/fractal-map/36008005345/audit` exists. The exact failing workflow step is **not log-observable** (no `GH_TOKEN` in this environment — recorded blocker). The run-36014970673 resume mechanism in `core-lane.yml` (team-job timeout + `resume_from_run_id`) performed as designed: this lane cycle completed the missing deliverables.

## Preserved New Modes (from run 36008005345)

### 1. `full_text_tfidf_light` — 21,228 decisions (TRUE 21k scale)
- Path: `results/fractal_map/hierarchical_map_21k/legal_distance_modes/full_text_tfidf_light/`
- Embeddings: `results/fractal_map/hierarchical_map_21k/tfidf_embeddings/full_text_tfidf_light.npy`
- Clusters: 8 / 13 / 22 / 36 / 50 at [0.25, 0.5, 1.0, 2.0, 3.0]; labels complete (21,228/21,228)
- Branch purity: 0.0 (branch=null in 21k metadata — documented limitation; zoom_coherence parent_details empty)
- Recorded mean_nesting_score: 1.0 — **FALSE**; honest strict nesting mean: **0.063** (0.00 / 0.136 / 0.056 / 0.060)

### 2. `cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25` — 175,440 decisions (TRUE full corpus)
- Path: `results/fractal_map/legal_distance_modes/cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25/`
- Embeddings: `results/fractal_map/hierarchical_map_174k/legal_tfidf_embeddings/cited_decisions_tfidf_outcome_hybrid_0.7.npy`
- Clusters: 29 / 34 / 48 / 11,633 / 63,281 at [0.25, 0.5, 1.0, 2.0, 3.0]; labels complete (175,440/175,440)
- Mean branch purity all levels: 0.7254
- Recorded mean_nesting_score: 1.0 — **FALSE**; honest strict nesting mean: **0.7385** (0.500 / 0.458 / 0.996 / 0.999)

## CRITICAL NEGATIVE FINDING: Nesting Metric Defect (NESTING_METRIC_DEFECT_v1)

**What happened**: The parameterized legal-distance builders recorded `mean_nesting_score` as the mean of `nesting_consistency`, defined as the fraction of fine clusters whose **MAJORITY parent label is valid (>= 0)**. For two independent Leiden partitions this is ~1.0 by construction and is **not** nestedness.

**Honest definition** (reference: `fractal_map/hierarchical/hierarchical_leiden.py::compute_nesting_score`): a fine cluster is nested iff **ALL** of its (non −1) members share **ONE unique** coarse parent label.

**Impact**:
- 37 of 46 audited compressed-ladder modes over-claimed `mean_nesting_score = 1.0`; honest means span **0.04–1.0**.
- Zoom routing tables (`zoom_mappings.json` `child_to_parent` / `parent_to_children`) are **unaffected** — they remain correct majority-parent navigation data; only the **metric name/claim** was wrong.
- `outcome_tfidf_*` family and `criticizing_alpha0.3` are genuinely 1.0 even under the honest definition.
- `center_projected_hierarchical` `best_config.nesting_score=1.0` (coarse_0.5_fine_3.0) is legitimate by construction (sub-clusters built within coarse clusters); the same dir's `hierarchical_map_results.json` `mean_nesting_score=1.0` is the legacy metric (honest ladder mean: **0.5006**) — conflation documented.
- The accepted `compressed_resolution_ladder_all_modes.json` used the **honest** nesting formula (e.g., center_projected nesting 0.5006 full / 0.4570 compressed, change −0.0436); its prose reports claiming "0% nesting change" are contradicted by the file itself and are corrected here.

**Remediation** (this cycle, code only — historical artifacts intentionally NOT rewritten):
- `build_parameterized_legal_distance_map_compressed.py` and `build_parameterized_legal_distance_map.py` now emit:
  - `strict_nesting_consistency` per transition (+ `n_fine_clusters`, `n_strictly_consistent`)
  - `mean_nesting_score` = **honest** strict mean; `mean_majority_coverage_score` = legacy value kept transparently
  - `metric_definitions` documenting both
- Verified: fixed `build_nesting` matches `hierarchical_leiden.compute_nesting_score` **bit-exactly** on real 174k-v25 arrays; synthetic cases pass (nested=1.0, straddled=0.0, orphan-ignored=0.5).
- Full honest audit: `results/fractal_map/evaluation/resume_36014970673_nesting_audit.json` (reproducible via `fractal_map/hierarchical/compute_honest_nesting_audit.py`).

## Honest Nesting Table (selected modes)

| Mode | Corpus | Recorded | Honest | 0.25→0.5 | 0.5→1.0 | 1.0→2.0 | 2.0→3.0 |
|------|--------|----------|--------|-----------|---------|---------|---------|
| outcome_tfidf_174k_compressed_v25 | 175,440 | 1.0 | **1.0** | 1.000 | 1.000 | 1.000 | 1.000 |
| cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25 (NEW) | 175,440 | 1.0 | **0.7385** | 0.500 | 0.458 | 0.996 | 0.999 |
| cited_decisions_tfidf_174k_compressed_v25 | 175,440 | 1.0 | **0.67** | 0.360 | 0.324 | 0.996 | 0.999 |
| regeste_tfidf_174k | 175,440 | 1.0 | **0.9446** | 0.904 | 0.876 | 0.999 | 1.000 |
| full_text_tfidf_light (NEW, 21k) | 21,228 | 1.0 | **0.063** | 0.000 | 0.136 | 0.056 | 0.060 |
| regeste_full_text_hybrid_0.5 (21k v25) | 21,228 | 1.0 | **0.0398** | 0.071 | 0.000 | 0.040 | 0.048 |
| regeste_full_text_hybrid_0.7_21k_compressed | 21,228 | 1.0 | **0.9523** | 1.000 | 1.000 | 0.919 | 0.890 |
| citing_alpha0.3 (1000) | 1,000 | — | **0.8834** | 1.000 | 1.000 | 0.974 | 0.998 |
| following_alpha0.3 (1000) | 1,000 | — | **0.9996** | 1.000 | 1.000 | 0.998 | 1.000 |
| criticizing_alpha0.3 (1000) | 1,000 | — | **1.0** | 1.000 | 1.000 | 1.000 | 1.000 |
| center_projected_hierarchical (ref) | 1,000 | 1.0 | **0.5006** | 0.429 | 0.667 | 0.571 | 0.263 |

Product consequence: **zoom transitions are routed navigation (majority parent), not containment.** High-resolution transitions (1.0→2.0, 2.0→3.0) are clean (0.99+) on virtually all modes; coarse transitions on the full_text/regeste 21k v25 family are not nested at all — embeddings/seed deserve review before productizing those views.

## Corpus Census Correction (negative result on prior reports)
Prior reports (e.g., `OPERATIONAL_RESUME_35991127733_VERIFICATION.md`) listed all "174k" dirs at corpus=175,440. Audit of `corpus_size` across the 46 mode dirs:

| Corpus | Dir count | Dirs |
|--------|-----------|------|
| 175,440 (TRUE 174k) | 6 | `cited_decisions_tfidf_174k_compressed_v25`, `cited_decisions_tfidf_outcome_hybrid_0.5_174k`, `cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25`, `cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25` (NEW), `outcome_tfidf_174k_compressed_v25`, `regeste_tfidf_174k` |
| 21,228 (named `*_174k_compressed` — mislabeled) | 6 | `cited_decisions_tfidf_174k_compressed`, `cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed`, `full_text_tfidf_light_174k_compressed`, `outcome_tfidf_174k_compressed`, `regeste_full_text_hybrid_0.5_174k_compressed`, `regeste_full_text_hybrid_0.7_174k_compressed` |
| 21,228 (legitimately named 21k) | 8 | `*_21k_compressed` family |
| 21,228 (21k v25 full-scale, NEW) | 4 | `full_text_tfidf_light`, `regeste_full_text_hybrid_0.5`, `regeste_full_text_hybrid_0.7`, `regeste_tfidf` (under `hierarchical_map_21k/legal_distance_modes/`) |
| 1,000 / placeholder | rest | v6/v7/v9 baseline and legacy modes |

**Corrected TF-IDF scale claim**: TRUE-174k TF-IDF modes = **6** (not 10). The remaining `_174k_compressed` dirs are 21,228-scale engineering runs and must not be described as 174k.

## Blockers (unchanged)
| Blocker | Since | Required From |
|---------|-------|---------------|
| Citation role modes + dense hybrids (citing/following/criticizing_alpha0.3) | 2026-09-24 | legal-distance 174k dense embeddings |
| 174k metadata (branch/legal_area/chamber) | 2026-09-24 | corpus lane |

## Orchestration Notes
Run 36014970673 consumed the `resume_from_run_id=36008005345` input correctly (snapshot mounted, repair_round 0). The long-standing supervisor/ephemeral-state mismatch (`/tmp/lex_control/state/factory_direction.json` status=RUN vs workspace state) remains an orchestration issue outside this lane's write scope.

## Next Recommendation
- **continue_recommended=false** — no additional same-question cycle justified while BLOCKED.
- On unblock: (1) rebuild the 21k full_text/regeste v25 family with the **fixed** builder so honest nesting is recorded, and review embedding provenance/Leiden seed (honest nesting 0.04–0.13 is a genuine negative result); (2) scale dense modes with the fixed builder; (3) productize zoom UI using routing tables for navigation and nesting as a diagnostic.

## Provenance
- Resumed snapshot: commit `b94d231a` (branch `operational-resume`)
- Audit artifact: `results/fractal_map/evaluation/resume_36014970673_nesting_audit.json`
- Audit script: `fractal_map/hierarchical/compute_honest_nesting_audit.py`
- Builder fix: `build_parameterized_legal_distance_map_compressed.py`, `build_parameterized_legal_distance_map.py`
- Frozen tests: `tests/fractal_map/test_verify.py` (184 tests, unmodified)