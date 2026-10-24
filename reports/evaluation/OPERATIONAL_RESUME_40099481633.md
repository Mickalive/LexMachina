# Operational resume of rejected evaluation cycle 40099481633 — round-1 repair record

- **Rejected cycle (repairs target):** GitHub run `40099481633`, workflow
  "Core evaluation dirV67 repair0", audit gate
  `results/audit/evaluation/CYCLE_40099481633_GATE.json` — verdict **REVISE**
  with four required fixes (F1–F4).
- **Repair run (this record, makes the claims):** GitHub run
  **`40101127061`**, branch head lineage `0b4963a0` (inherited audit head)
  → `7adbc31f` (F1 + F2 freeze, committed BEFORE re-execution)
  → `c1c9b61e` (F2 re-execution + F3 test repair + F1–F4 invariant tests)
  → final repair commit (state advance, pytest records, this report, guard).
- **Non-movement scope (F4):** no frozen rubric/threshold/verdict-contract,
  instrument, benchmark baseline or success rule was edited, weakened or
  re-scored; no obsolete universal-174k benchmark rerun; no product code
  modified; both DO-NOT-SERVE orders stand; all five fail-closed posture
  flags remain `false`; `accepted_run_id` stays **`40084716045`** until a
  future both-halves promotion. A zero-delta round-1 repair is invalid —
  this repair's durable delta is the four fixes themselves plus the frozen,
  run-attributed re-execution and the repaired living suite at a green head.

## F1 — durable delta (why run 40099481633 produced no delta and what this run adds)

Artifacts (all committed, run-attributed):

- `results/evaluation/orchestration/40099481633_rest_jobs.json` — public
  REST snapshot of run `40099481633`: head `e281fc6f`, all four jobs
  (`team`/`audit`/`integrate`/`resilience`) `success` (team job
  120888501704, 13:45:11Z→13:52:27Z, 436s; every step succeeded, including
  the state-validation step that requires `direction_version == 67` and
  `cycle_status != INITIALIZED`). Fetched by repair run `40101127061`.
- `results/evaluation/orchestration/40099481633_failure_chain_diagnosis.json`
  — verdict `ZERO_DURABLE_DELTA_UNDER_SUCCESS`. The LEX_REQUIRE_DELTA guard
  (`.github/scripts/run-ox-with-retry.sh:161,213-216`) was satisfied only by
  **adopting the inherited head `0b4963a0`** (HEAD moved
  `f2734734` → `0b4963a0` with a clean porcelain); no artifact in the
  worktree referenced run `40099481633` before this repair (count 0), and
  the canonical state still carried `github_run == 40096174340`. The same
  artifact records the **current v67 work posture** in the same breath:
  - item (1) D2 letterhead pattern profile: `DISCHARGED-AND-INHERITED`
    (deliverable of record is the 40089391202 freeze; re-verified under
    this repair, see F2);
  - item (2) conditional 174k re-measure: `NOT_YET_DISCRIMINATING` —
    product head `e2270c373a8f26c6b826053e8527a216a3304e8b` ("accept product
    cycle 40080810801") still carries `fixture_generation=True`
    (`product/offline_slice.py:79`) and the pipeline gate
    `if not fixture_generation and adversarial_retrieval:`
    (`product/query/pipeline.py:1339`) still short-circuits under fixture
    generation, so no product claim is licensed;
  - item (3) standing falsification record: unchanged, not re-run;
  - posture unchanged: both DO-NOT-SERVE orders stand; no frozen edit; no
    174k rerun; no product code modified.

## F2 — freeze-first re-execution of the inherited item-(1) deliverable

Freeze committed **before** execution (order proven in
`tests/evaluation/test_operational_resume_40099481633.py::test_f2_freeze_
committed_before_reexecution_and_pins_inventory` via commit ancestry):

- `evaluation/OPERATIONAL_RESUME_40099481633_HYPOTHESIS_V1.json` — decision
  rule frozen before execution (`REPRODUCES` iff all 19 discrimination
  fields of the deliverable of record match and controls pass).
- `evaluation/OPERATIONAL_RESUME_40099481633_FREEZE_V1.json` — pins the
  19-item inventory (verbatim from
  `evaluation/OPERATIONAL_RESUME_40096174340_FREEZE_V1_ADDENDUM_FIELD_COUNT.json`),
  instrument sha256
  `aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d`
  (`evaluation/counter_evidence_quality_benchmark.py`, REPORTED-ONLY, never
  edited), deliverable sha256
  `f5fade6d11ebf14e3004d5beebf2f959444720fc3152e4e5b0b479a644d3cab7`
  (`results/evaluation/d2_letterhead_pattern_profile/40089391202.json`),
  baseline sha256
  `948a8929817f265236c87bbc1b3a17559fa7db2bd03ee4ccddc36332977ac717`.

Re-execution under run id `40099481633` with the frozen profile instrument
(`evaluation/d2_letterhead_pattern_profile.py`, sha256
`63a48854e9500544ce970dd9a98765d077a7e5dace6500fdf5bc79a93ff918c8`):

- `results/evaluation/d2_letterhead_pattern_profile/40099481633.json` —
  93 sha256-pinned bundles, 41 D2_letterhead_zone rows, 2 distinct
  letterhead patterns (P1_OFFSET0_MULTILINE_COURT_HEADER), verdict
  `LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED`, controls C3–C6 all pass.
- `reports/evaluation/D2_LETTERHEAD_PATTERN_PROFILE_40099481633.md`.
- `results/evaluation/d2_letterhead_pattern_profile/40099481633_reproduction_
  check_vs_40089391202.json` — verdict **`REPRODUCES`**, 19/19 fields,
  **0 mismatches**, controls all pass, `deliverable_untouched: true`,
  `file_byte_identity_claimed: false` (requirement 30 respected: the
  comparison is on discrimination fields, not a byte-identity claim),
  execution provenance disclosed (`repair_run_id: 40101127061`).
- Canonical state advanced with disclosure:
  `github_run: 40096174340 → 40101127061` via `github_run_advance`
  (`repair_of_run: 40099481633`, `repair_round: 1`), new block
  `repair_round1_40099481633` with the audit's required-fixes text preserved
  verbatim, and **`accepted_run_id` kept at `40084716045`**.

## F3 — stale identity pin repaired (history preserved) + fresh real-pytest record

The failing pins
`test_operational_resume_40094203248.py::test_state_run_identity_and_posture`
(`github_run == "40094203248"`, `operational_resume_of == "40089391202"`)
went stale when later cycles legitimately advanced the canonical state
(the state carried `40096174340` when this audit recomputed it). Repaired
by **widening the pins to the append-only `run_identity_history` chain**:

- every state run identity must appear in `run_identity_history`
  (`40096174340`, `40099481633`, `40101127061`);
- the historical run ids the test originally pinned stay asserted
  (`40094203248`, `40089391202` in history; `inherited_deliverable_of_record
  == "40089391202"`);
- `accepted_run_id`, `direction_version == 67`, `cycle_status == COMPLETE`,
  all five posture flags and the `evidence_refs_n` invariant are unchanged.

Nothing was deleted: history is preserved, and the repaired function passes
at the advanced state. Fresh real-pytest (9.1.1) records at the repaired
head (paths under `results/evaluation/orchestration/`):

- `40101127061_pytest_shim.json` + `40101127061_pytest_living.junit.xml` —
  7-file living suite (profile / nested-refs guard / benchmark / re-measure
  / path-scope probe / scorer reconciliation / operational-resume-40094203248):
  **38 passed, 0 failed** (pre-repair: 1 failed / 37 passed).
- `40101127061_pytest_repair_invariants.json` +
  `40101127061_repair_invariants.junit.xml` — new F1–F4 invariant suite
  (`tests/evaluation/test_operational_resume_40099481633.py`,
  10 tests): **10 passed, 0 failed**.
- `40101127061_multiling_prov_pytest.json` +
  `40101127061_multiling_prov.junit.xml` — 4-file multilingual/provenance
  reuse suite: **73 passed, 0 failed** (no state pins; unchanged reuse
  posture).

## F4 — non-movements re-verified after the repair (post-execution re-hash)

| Path | Expected sha256 | Result |
| --- | --- | --- |
| `evaluation/frozen_bars/RULES_LABEL.json` | `4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608` | unchanged |
| `evaluation/frozen_bars/RULES_GEOMETRY.json` | `a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633` | unchanged |
| `evaluation/frozen_bars/VERDICT_CONTRACT.json` | `b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c` | unchanged |
| `evaluation/counter_evidence_quality_benchmark.py` | `aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d` | unchanged |
| `evaluation/d2_letterhead_pattern_profile.py` | `63a48854e9500544ce970dd9a98765d077a7e5dace6500fdf5bc79a93ff918c8` | unchanged |
| `results/evaluation/d2_letterhead_pattern_profile/40089391202.json` | `f5fade6d11ebf14e3004d5beebf2f959444720fc3152e4e5b0b479a644d3cab7` | unchanged (untouched) |
| `results/evaluation/counter_evidence_quality_benchmark/40062917685.json` | `948a8929817f265236c87bbc1b3a17559fa7db2bd03ee4ccddc36332977ac717` | unchanged (baseline unmoved) |

Post-execution re-hash run: `evaluation/repair_40099481633_round1.py verify`
(all `matches: true`). Posture flags: all five `false`. Both DO-NOT-SERVE
orders stand. No obsolete universal-174k benchmark rerun was performed
(item (2) remains `NOT_YET_DISCRIMINATING`, re-verified against product head
`e2270c37`). No product code was modified by this repair (write scope:
`evaluation/`, `tests/evaluation/`, `results/evaluation/`,
`reports/evaluation/`, `state/evaluation.json` only).

## Nested evidence-refs guard (final)

`python3 -m evaluation.nested_evidence_refs_guard --run-id 40099481633
--out-dir results/evaluation/orchestration` →
`results/evaluation/orchestration/40099481633_nested_evidence_refs.json` —
verdict **`NESTED_REFS_RESOLVED`**, exit code **0**, `n_unresolved: 0`,
`n_top_level_unresolved: 0` (537 refs resolved in the worktree, 5 via the
accepted cross-lane mounts, 2 via fetched branch history — including the
historical audit gate `results/audit/evaluation/CYCLE_40017649220_GATE.json`
on `cycle/core/evaluation/40017649220/audit`, 3 disclosed historical refs,
1 self-output pending write — the guard's own output, written at the end of
that very process). This resolves on the same mechanism (fetched branch
history) the previously accepted cycles' guard records used.

## Claim ceiling

This repair establishes only that the four required fixes for rejected
cycle `40099481633` are discharged with committed, machine-verifiable,
run-attributed records at a green test head, and that no frozen input,
instrument, test, bar, rubric, threshold or success rule changed. It
re-measures nothing about the product, serves nothing, and makes no legal
usefulness claim. Both DO-NOT-SERVE orders stand. The canonical state
remains fail-closed (`human_gate_ready`, `machine_gate_ready`,
`packet_admitted`, `ready_for_owner_session`, `owner_decision_required`
all `false`; `continue_recommended: false`; evidence tier
`REPRODUCED`).
