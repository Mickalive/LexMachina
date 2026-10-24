# LexMachina Evaluation — OPERATIONAL RESUME 40094203248 (resume of 40089391202)

**Lane:** evaluation · **Direction:** v67 · **Run:** 40094203248 (workflow_dispatch, `resume_from_run_id=40089391202`) · **Date:** 2026-10-24

---

## 1. Why this run exists — orchestration diagnosis of 40089391202

Run 40089391202 ("Core evaluation dirV67 repair0", dispatched by the resilience job of the previous failed chain) **completed its producer job successfully**: every team step was green — including `Validate active MVP producer state`, `Enforce lane write scope` and `Persist team snapshot` — and commit `9ae71fcf` was pushed to `cycle/core/evaluation/40089391202/team` (11:18:51Z–11:44:25Z).

Its **audit job then failed** at step 5 `Independent audit` (11:44:28Z–12:30:12Z, 2744s wall). Steps 6 (`Enforce audit scope and read gate`) and 7 (`Persist audit snapshot`) were skipped: **no `CYCLE_40089391202_GATE.json` was written and no `cycle/core/evaluation/40089391202/audit` ref exists**. Integrate was skipped; the resilience job dispatched this resume.

**Hedged rc attribution** (logs are unauthenticated-403; public REST record only): 2744s ≈ the 2700s `LEX_AGENT_QUANTUM_SECONDS` work quantum plus ~44s kill/cleanup — the same rc-78 `LEX_WORK_QUANTUM_EXPIRED` signature recorded for prior chain deaths. Network-stall retries (rc 75) ending in exit 75 cannot be excluded. Per factory-wide requirement 20, **this is an ORCHESTRATION-class death — not a verdict, not a product defect, not a human-gate problem.** No audit verdict exists for 40089391202 because no gate file exists. Machine record: `results/evaluation/orchestration/40094203248_failure_chain_diagnosis.json`.

Per factory-wide requirement 4, 40089391202 is therefore **NOT ACCEPTED**; the accepted lineage is unchanged (`lab/evaluation` tip `f2734734`, accept 40084716045).

## 2. What was preserved (nothing restarted)

The full producer snapshot of 40089391202 is preserved intact and remains the **item-(1) deliverable of record**:

- Freeze-first discipline verified from artifact timestamps: hypothesis `11:30:00Z` → freeze record `11:32:00Z` → execution `11:34:28Z` (`evaluation/D2_LETTERHEAD_PATTERN_PROFILE_40089391202_{HYPOTHESIS,FREEZE}_V1.json`);
- `results/evaluation/d2_letterhead_pattern_profile/40089391202.json`: **LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED** — 93 sha256-pinned bundles (90 shipped-slice + 3 packet-of-record 39319405429), 41 D2 rows → **2 distinct P1 offset-0 multi-line court-header patterns**, controls C3–C6 all pass, frozen instrument sha `aac86527…` byte-identical (C4), accepted baseline 40062917685 unmoved (C6: NORMALIZED-IDENTICAL re-probe), no bar movement;
- Its state repairs R1–R6 (`evaluation/operational_resume_40089391202_state_repair.py`) and all four measurement re-executions inherited from cycle 40085602229.

## 3. Verification performed this run (the durable delta)

### 3.1 Reproduction check of the item-(1) deliverable — REPRODUCES

Hypothesis and comparison contract frozen **before** execution (`evaluation/OPERATIONAL_RESUME_40094203248_{HYPOTHESIS,FREEZE}_V1.json`). Fresh re-execution of the byte-identical frozen instrument against the same sha256-pinned bundle population (product mount head `e2270c37`, unchanged) under this run's id:

| Field | 40089391202 (of record) | 40094203248 (re-execution) |
|---|---|---|
| verdict | LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED | identical |
| exit_code / controls_all_pass | 0 / true | identical |
| n_bundles (slice + packet) | 93 (90 + 3) | identical |
| d2_rows_profiled | 41 | identical |
| distinct letterhead patterns | 2 (both P1_OFFSET0_MULTILINE_COURT_HEADER) | identical |
| population defect histogram | D2 41 / D3 31 / D4 7 | identical |
| frozen instrument sha | aac86527… | identical |
| all 93 population bundle+sha256 pins | — | identical |

**Verdict: REPRODUCES — 19/19 frozen discrimination fields identical, 0 mismatches, controls C3–C6 all pass.** JSON file byte-identity is NOT claimed (requirement 30; only discrimination fields are pinned). Artifact: `results/evaluation/d2_letterhead_pattern_profile/40094203248_reproduction_check_vs_40089391202.json`. Per the F-3B convention the re-measurement is published under its own run id; the 40089391202 artifact was **not** overwritten.

### 3.2 Finishable state-hygiene defect repaired (R1-finish)

The 40089391202 repair's R1 corrected the 8 phantom `local_eval_20261024T102833Z` strings inside the top-level `evidence_refs` list but **left the same 8 phantom strings as dict keys inside `evidence_ref_role_notes`** — naming files that exist nowhere in the tree (real artifacts: `local_eval_20261024T102500Z` / `local_eval_1792837481`). This resume renamed those 8 keys to the real committed artifact paths (role-label **values unchanged; nothing deleted**; all renamed keys verified to resolve on disk), by scripted, auditable edit (`evaluation/operational_resume_40094203248_state_repair.py`).

### 3.3 v67 item (2) precondition re-verified — still NOT_YET_DISCRIMINATING

`origin/lab/product` head `e2270c37` (accept 40080810801) **still bypasses the filter on the fixture path**: `product/offline_slice.py:79` (`retrieval_mode="fixture", fixture_generation=True`) and `product/query/pipeline.py:1339` (`if not fixture_generation and adversarial_retrieval`). Product has not landed the P0 path-routing/re-generation leg, so the conditional item-(2) re-measure is **not due**; no synthetic stand-in was invented and the standing falsification record (item (3)) was not re-run.

### 3.4 Living test suites — 38/38 green (real pytest 9.1.1)

The 7-file living suite (frozen D2/D3/D4 instrument family + nested-refs guard + scorer-path reconciliation + the new 5-test resume-invariant suite) passed **38 passed / 0 failed / 0 skipped**; record `results/evaluation/orchestration/40094203248_pytest_shim.json` (+ junit xml).

## 4. State of the lane after this resume

- `state/evaluation.json`: run identity 40094203248 (history disclosed), `direction_version=67`, `cycle_status=COMPLETE`, `evidence_tier=REPRODUCED`, `acceptance_status=PROPOSED_PENDING_INDEPENDENT_AUDIT`, `accepted_run_id=40084716045` (both halves of requirement 4 verified; unchanged), `evidence_refs_n=295` (final count at commit; the list grew append-only during this run as each verification artifact landed, and the nested-refs guard was re-run after the last append: NESTED_REFS_RESOLVED, 0 unresolved), `continue_recommended=false` with the NOT_YET_DISCRIMINATING reason re-verified this run;
- posture stays fail-closed: `human_gate_ready=false`, `machine_gate_ready=false`, `packet_admitted=false`, `ready_for_owner_session=false`, `owner_decision_required=false`; both DO-NOT-SERVE orders stand; comparative map-vs-ranked-list stays VACUOUS;
- no frozen bar, rubric, threshold or verdict contract was edited or scored; no 174k benchmark was rerun; no product code was modified; the frozen instrument digest re-hashed REPORTED-ONLY and matches.

## 5. Recommendation

**CONTINUE under the same v67 question only after Core Product lands its P0 residual** (letterhead detector fix on the two profiled P1 variants AND fixture-path routing / non-fixture regeneration with full-family regeneration). Then run the frozen item-(2) re-measure + `d2_path_scope_probe` on that new head. Nothing in this resume re-opens a closed item; the v67 item-(1) feasibility profile is complete, now **reproduction-verified**, and is Core Product's input for the deterministic-filter decision.
