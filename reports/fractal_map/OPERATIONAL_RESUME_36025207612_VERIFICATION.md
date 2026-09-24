# Operational Resume Verification — Run 36025207612

## Summary
**Lane**: fractal-map  
**Factory Direction**: v25  
**GitHub Run**: 36025207612  
**Resume From**: 36023963893 (persisted producer snapshot, zero-delta repair run)  
**Previously REVISE-Gated**: 36018593628 (independent audit gate=REVISE)  
**Timestamp**: 2026-09-24  
**Producer Gate**: PASS (self-verification; independent audit for this run pending)

## What happened before this run (diagnosis)

1. **Run 36008005345** — producer died after persisting a 24-file snapshot (2 complete compressed-ladder builds) and before writing gate/report/state.
2. **Run 36014970673** — operational resume verified that snapshot, discovered and remediated `NESTING_METRIC_DEFECT_v1` (parameterized builders recorded majority-parent coverage as `mean_nesting_score`), quantified honest strict nesting for 46 modes (37 over-claims), corrected the 174k census (6 true-174k TF-IDF dirs), fixed both builders. Commit `0e7aaf4f`.
3. **Run 36018593628** — re-dispatched; producer produced **zero durable delta** (team ref byte-identical to `0e7aaf4f`). Independent audit issued **GATE=REVISE** with two required fixes: (1) correct/annotate the 9 ACCEPTED-tier `validation_metrics` `nesting_score=1.0` over-claims in `state/fractal-map.json` (honest values 0.3911–0.9632 + 2 by-construction annotations); (2) record the run's verification as a durable delta. Audit also warned: *"if the next repair round returns zero delta again the following audit must be BLOCKED"*.
4. **Run 36023963893** — dispatched as repair round 1 of the REVISE; **again produced zero durable delta**: `origin/cycle/core/fractal-map/36023963893/team` == `0e7aaf4f`, no file references the run, no audit branch was created. Under `run-ox-with-retry.sh`, `LEX_REQUIRE_DELTA=1` (set for repairs) turns a clean tree into exit code 67 `LEX_ZERO_DELTA_REPAIR`, failing the team job before the audit could run.
5. **Run 36025207612 (this run)** — operational resume from the persisted snapshot of 36023963893. Applied both REVISE fixes (below) with real durable delta.

## Root orchestration defect (unchanged, documented for the director)

The supervisor dispatcher reads the ephemeral mounted control-plane copy
`/tmp/lex_control/state/factory_direction.json` (`fractal-map.status=RUN`) instead of the
workspace lane state `state/fractal-map.json` (`cycle_status=COMPLETED`,
`continue_recommended=false`, `blocked_on=legal-distance_174k_dense_embeddings;corpus_174k_metadata`).
This has produced 60+ unnecessary resume/repair dispatches across the documented lineage
(59th+ occurrence recorded in prior key_findings; this run is the 60th+). The lane itself has
no missing scientific work: TF-IDF compressed-ladder modes are complete at available scale and
dense/citation-role work is genuinely blocked on legal-distance 174k embeddings.

## REVISE Fix 1 — state nesting over-claims corrected/annotated (audit of 36018593628)

Source of truth: `results/fractal_map/evaluation/resume_36014970673_nesting_audit.json`,
**bit-exactly reproduced** by this run (46 modes, 37 over-claims, 3 reference dirs, summary and
defect block identical; reproduction = `compute_honest_nesting_audit.py` re-executed into a
temp output and diffed). All edits are confined to the live claim surface
`state/fractal-map.json`; historical artifacts remain untouched.

| State entry (validation_metrics) | Old nesting_score | New honest value | Legacy preserved |
|---|---|---|---|
| full_text_tfidf_light_174k_compressed | 1.0 | **0.39106372080996143** | `legacy_recorded_nesting_score: 1.0` |
| cited_decisions_tfidf_174k_compressed | 1.0 | **0.783069252615662** | same |
| cited_decisions_tfidf_outcome_hybrid_0.7_174k_compressed | 1.0 | **0.853953700800777** | same |
| cited_decisions_tfidf_outcome_hybrid_0.5_21k_compressed | 1.0 | **0.9269594210012833** | same |
| regeste_full_text_hybrid_0.5_174k_compressed | 1.0 | **0.9294774877573337** | same |
| regeste_full_text_hybrid_0.7_174k_compressed | 1.0 | **0.9522750440181633** | same |
| regeste_tfidf_21k_compressed | 1.0 | **0.9631941086395874** | same |
| cited_decisions_tfidf_outcome_hybrid_0.5 (1000) | 1.0 (by-construction pair) | kept, annotated: `nesting_score_scope` + honest ladder mean **0.8722435769849564** | — |
| cited_decisions_tfidf_outcome_hybrid_0.7 (1000) | 1.0 (by-construction pair) | kept, annotated: `nesting_score_scope` + honest ladder mean **0.8644127756695815** | — |

Additional same-class over-claims corrected/annotated (beyond the 9 required but within the
audit's claim-ceiling prohibition "no claim of nesting >= 0.99 ... may stand uncorrected"):

- `metrics_summary.tfidf_modes_174k_compressed.all_nesting_perfect`: `true` → `false` with
  `honest_strict_nesting_by_mode` (0.3911–1.0), legacy preserved.
- `validation_metrics.compressed_resolution_ladder.nesting_change`: `0.0` → honest mean
  **-0.0036352876963673384** (range [-0.055580871370345175, 0.11496948923709871]) computed
  from the accepted `compressed_resolution_ladder_all_modes.json` (22 modes, honest formula);
  legacy `legacy_recorded_nesting_change: 0.0` preserved.
- `center_projected_hierarchical` (REPRODUCED): annotated by-construction scope +
  honest ladder mean 0.5006146996278574 (per audit reference-dir recomputation).
- `hierarchical_leiden_concat_legacy` (REPRODUCED): annotated by-construction
  best_config single-pair scope (not flagged by the honest audit).
- `metrics_summary.center_projected_hierarchical_experiment.nesting_score`: annotated scope +
  honest ladder mean.
- Top-level `metric_defect_notes.NESTING_METRIC_DEFECT_v1` added, pointing to the audit
  artifact and script.

Every corrected value is machine-checked by
`fractal_map/hierarchical/verify_state_nesting_fix.py` (53/53 checks PASS; artifact:
`results/fractal_map/evaluation/operational_resume_36025207612_state_nesting_fix.json`).

## REVISE Fix 2 — durable delta recorded

- `github_run`: 36025207612, `resume_from_run_id`: 36023963893,
  `operational_resume_id`: 36025207612, timestamp updated.
- REVISE chain recorded: `revise_gate_run: 36018593628`, `revise_gate: REVISE`,
  `repair_of: 36018593628` (legacy `35968700890` preserved as `legacy_repair_of`),
  `prior_zero_delta_repair_run: 36023963893`, `repair_round: 1`.
- Two new `key_findings` entries (36023963893 diagnosis + 36025207612 correction) prepended.

## Verification performed this run (before claim recording)

- Frozen suite `tests/fractal_map/test_verify.py`: **184/184 PASS** (1.36s, unchanged file —
  `git diff` vs accepted base confirms no test weakening).
- `compute_honest_nesting_audit.py` re-executed: output **bit-identical** to committed
  `resume_36014970673_nesting_audit.json` (46 modes, 37 over-claims, 3 reference dirs,
  summary, defect block).
- `verify_state_nesting_fix.py`: **53/53 PASS** (every state correction matches the honest
  audit artifact and the accepted ladder artifact).
- Tracked artifacts under `results/fractal_map`: **995** (git ls-files).
- Work preserved: 24-file snapshot from run 36008005345 (verified in 36014970673), all mode
  dirs and zoom routing tables (verified in 36018593628 audit; untouched here).

## Lane deliverable status

TF-IDF compressed 5-level ladder modes: COMPLETE at available scale (6 true-174k/175,440 +
21,228-scale builds + new v25 builds). Citation-role and dense-embedding modes and the
multi-view zoom UI remain **BLOCKED** on:
1. legal-distance 174k dense embeddings (citation-role modes `citing/following/criticizing`),
2. corpus 174k metadata (branch/legal_area/chamber).

`continue_recommended=false` — no additional same-question cycle is justified while blocked.

## Provenance

- Snapshot continued: commit `0e7aaf4f` (branch `operational-resume`, run 36023963893 team ref)
- State corrections: `state/fractal-map.json` (this run)
- Verification script: `fractal_map/hierarchical/verify_state_nesting_fix.py`
- Verification artifact: `results/fractal_map/evaluation/operational_resume_36025207612_state_nesting_fix.json`
- Honest nesting audit (bit-exact): `results/fractal_map/evaluation/resume_36014970673_nesting_audit.json`
- Producer gate: `results/fractal_map/audit/CYCLE_OPERATIONAL_RESUME_36025207612_GATE.json`
- Independent audit of prior cycle: `results/audit/fractal-map/CYCLE_36018593628_GATE.json`
  (gate=REVISE; lives on branch `cycle/core/fractal-map/36018593628/audit`, not this workspace)