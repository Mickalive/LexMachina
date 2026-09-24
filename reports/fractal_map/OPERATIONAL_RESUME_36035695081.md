# Operational Resume + 174k Evaluation Completion — Run 36035695081

**Lane**: fractal-map | **Direction v25** | **Date**: 2026-09-24
**Status**: Operational resume from persisted zero-delta snapshot of run 36034386649. Deliverable **completed and audit-ready**: frozen 174k build census + alignment audit (census_v26), frozen v26 evaluation on **all 4 decision-mappable 174k modes** (verdict **FAIL, 0/4** — v25 negative **generalized**), citation-role 174k validation recorded **BLOCKED by evidence**, multi-view zoom UI re-verified, 195/195 tests PASS. Blocker unchanged: `legal-distance_174k_dense_embeddings`.

---

## 1. Diagnosis: why run 36034386649 produced nothing

- `operational-resume` branch tracks `origin/cycle/core/fractal-map/36034386649/team` @ `4aa51c95` — **byte-identical** to the predecessor cycle 36029852715's team commit. Run 36034386649 (and attempt-1) therefore produced **zero durable delta**; per the launcher, a zero-delta run does not create an audit branch (no audit branch exists for either 36029852715 or 36034386649).
- Launcher evidence (`.github/scripts/run-ox-with-retry.sh`): hard-fail conditions `LEX_NO_HEALTHY_FREE_TOOL_MODEL` (model-health gating) and `LEX_REQUIRE_DELTA` (zero-delta repair guard).
- Model-health evidence (`/tmp/lex_control/state/model_health.json`): free-model probes failing (nemotron 503/Nvidia overload, permission auto-reject), `resolved_model: opencode/big-pickle`, `using_fallback: true`.
- Conclusion (artifact-and-code based; no gh API access): the failed cycles were orchestration/validation failures — no healthy free tool model at dispatch, so the resumed cycle exited without work. **Valid prior work was preserved** (commit 4aa51c95 from 36029852715 intact, v25 artifacts frozen).

## 2. What was done (real executable work, this run)

1. **Frozen test suite with complete deps**: `pytest tests/fractal_map/` → **188/188 PASS** (1.37s; igraph 1.0.0 + leidenalg 0.12.0 installed).
2. **Frozen 174k build census + provenance audit** (freeze-before-compute: `174k_CENSUS_v26_frozen_spec.json` → `census_v26.json`, `alignment_probe_v26.json`):
   - 12 directories with "174k" in name classified:
     - **4 TRUE decision-mappable 174k** (decision_clusters 174,126 real `bger_*` keys; full overlap with accepted metadata): `cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25` (production default), `cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25`, `cited_decisions_tfidf_outcome_hybrid_0.5_174k` (byte-same maps as v25 variant — reproducibility confirmation), `regeste_tfidf_174k`.
     - **2 placeholder-keyed true-174k** (175,440 `bger_placeholder_*` keys, NOT decision-mappable): `cited_decisions_tfidf_174k_compressed_v25` — **this is the citation-role mode** — and `outcome_tfidf_174k_compressed_v25`.
     - **6 misnamed 21k builds** (21,228 keys).
   - Metadata provenance: `metadata_174k_full_175k.json` **all-placeholder corruption** confirmed (175,440 entries, placeholder IDs regenerated without corpus).
   - **Alignment probe 1** (embedding row order vs ACCEPTED eval metadata): candidate agreement **0.4264** vs 0.3120 shuffled vs ~1.0 expected → **REJECTED** — row→id alignment is NOT recoverable from accepted metadata alone.
   - **Alignment probe 2** (cluster_metadata row→id reconstruction): 175,440 rows, **1003 duplicate IDs, 1314 extra rows** → **CORRUPTED** — cluster_metadata is not a reliable row→id map.
3. **Frozen v26 evaluation completed** (freeze-before-compute: `v26_frozen_spec.json` → `v26_verdict.json`; independent evaluator `zoom_quality_174k_all_modes_v26.py`, semantics = canonical builder `compute_zoom_coherence` translated to decision-ID space; success rule **identical to v25**):
   - All **4 decision-mappable modes** evaluated vs ACCEPTED metadata (join 173,963/173,963; 90,632 branch-labeled / 91,193 area-labeled), with purity + zoom + nesting (recomputed from labels) + fragmentation.
   - **Per-mode verdicts: FAIL / FAIL / FAIL / FAIL** → **OVERALL VERDICT: FAIL (0/4)** — no landed TF-IDF 174k representation supports monotonic zoom refinement.
   - Crosscheck vs frozen v25 (primary mode): purity **bit-equal** on all 5 resolutions (0.5525/0.5128/0.5324/0.5140/0.5273); zoom claim-level identical (rate>0.5 count 1 vs 1; branch monotonic False vs False); zoom micro-deviations recorded (≤2 parents, ΔMI ≤0.006; t1 exact). The inline v25 producer script was never committed (only its outputs), so this is the closest reproducible variant — deviation is documented, not hidden.
4. **Citation-role 174k zoom validation — BLOCKED (recorded, not skipped)**: `cited_decisions_tfidf_174k_compressed_v25` and `outcome_tfidf_174k_compressed_v25` are placeholder-keyed (0 real decision ids); row→id alignment unrecoverable without the full corpus JSONL (`bger_*.jsonl` — only slices/samples mounted in the accepted corpus checkout; full bge side exists). Closest executable proxy evaluated instead: **citation-signal probe inside v26** (hybrids containing cited_decisions vs regeste-only: both fail monotonicity; regeste zoom rates 0.0/0.0/1.0/0.4).
5. **Multi-view zoom UI re-verified at product accepted peer** (`/tmp/lex_accepted/product/product/static/index.html`): CITATION ROLE VIEWS optgroup (following/criticizing/citing_alpha0.3), zoom controls + zoom-level select + zoom-coherence badge, split-view (multi-view), 65 webgl references.
6. **Guard tests added**: `tests/fractal_map/test_zoom_quality_174k_v26_eval.py` (7 tests) protecting v26 verdict FAIL, all four per-mode FAIL, baseline pins, v25 freeze protection, census classification (4/2/6), and alignment probe verdicts → **195/195 PASS**.

## 3. Results (freeze-protected; negatives preserved)

| mode | branch res0.25 -> res3.0 | area res0.25 -> res3.0 | zoom rates (4 transitions) | per-mode verdict |
|---|---|---|---|---|
| cited_decisions_tfidf_outcome_hybrid_0.5_174k_v25 | 0.5525 -> 0.5273 ▼ | 0.3134 -> 0.2622 ▼ | 0.31 / 0.48 / 0.56 / 0.42 | **FAIL** |
| cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed_v25 | 0.5491 -> 0.5204 ▼ | 0.2956 -> 0.2310 ▼ | 0.36 / 0.54 / 0.44 / 0.43 | **FAIL** |
| cited_decisions_tfidf_outcome_hybrid_0.5_174k | 0.5525 -> 0.5273 ▼ | 0.3134 -> 0.2622 ▼ | 0.31 / 0.48 / 0.56 / 0.42 | **FAIL** |
| regeste_tfidf_174k | 0.3452 -> 0.3434 ▼ | 0.0790 -> 0.0794 ▲ | 0.0 / 0.0 / 1.0 / 0.4 | **FAIL** |

- Baseline random: branch 0.25, area 1/213 ≈ 0.0047 (pinned in verdict). Structure signal remains strong (all modes >> random) — TF-IDF 174k **encodes** legal structure but does **not refine** it monotonically via the compressed ladder.
- (area numbers for the two secondary modes come from v26 verdict; primary area purity bit-equal to v25.)
- Nesting (strict, recomputed from labels) + fragmentation per mode are in `v26_verdict.json` (e.g. production default fine-level median size 1 — over-fragmented).

## 4. Conclusions & state delta

- **v25 negative GENERALIZED**: the claim "no landed TF-IDF 174k mode supports monotonic zoom refinement at 174k" now rests on all 4 decision-mappable modes, not just the production default. Zoom-refinement at 174k for TF-IDF-only representations: **NOT established** (FAIR).
- **Citation-role/dense 174k path BLOCKED by evidence** — rebuild requires (a) full corpus JSONL for row→id alignment of the placeholder-keyed 174k builds, or (b) legal-distance lane's 174k dense embeddings. Blocker unchanged: `legal-distance_174k_dense_embeddings`.
- Orchestration defect documented (60th+ occurrence family): supervisor re-dispatch from ephemeral control plane while lane state says COMPLETED/BLOCKED; this run's zero-delta chain (36034386649) adds model-health gating as the concrete failure mechanism.
- `continue_recommended=false` remains correct — single remaining external dependency.

## 5. Artifacts

- `results/fractal_map/zoom_quality_174k_eval/v26_frozen_spec.json`, `v26_verdict.json`
- `fractal_map/evaluation/zoom_quality_174k_all_modes_v26.py`
- `results/fractal_map/legal_distance_modes/{174k_CENSUS_v26_frozen_spec.json, census_v26.json, alignment_probe_v26.json}`
- `fractal_map/hierarchical/audit_174k_builds_36035695081.py`
- `tests/fractal_map/test_zoom_quality_174k_v26_eval.py`
- `results/fractal_map/audit/CYCLE_36035695081_GATE.json`
- `state/fractal-map.json` (updated), this report.
- v25 artifacts (`v25_frozen_spec.json`, `v25_raw_purity.json`, `v25_raw_zoom.json`, `v25_verdict.json`) untouched.

## 6. Verification

- `195/195` tests PASS (188 frozen incl. the 4 v25 guard tests + 7 new v26/census guards).
- Census classifications deterministic on immutable historical artifacts (rerun verified).
- Crosscheck v25: purity bit-equal; zoom claim-level identical; micro-deviations documented.