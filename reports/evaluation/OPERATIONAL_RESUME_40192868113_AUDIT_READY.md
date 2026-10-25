# Operational Resume 40192868113 — Audit-Ready Producer Snapshot

- Lane: `evaluation`
- Direction: v68
- Run under resume: `40187594111`
- Current run: `40192868113`
- Snapshot resumed: `14ee2d1e` (`evaluation cycle 40187594111 repair 0`)
- Status: **AUDIT_READY_PENDING_INDEPENDENT_AUDIT**
- Accepted run unchanged: `40159747851`
- `continue_recommended` unchanged: `false`

This report is the human-readable companion to
`results/evaluation/operational_resume_40192868113/diagnosis_40187594111.json`,
`.../audit_ref_absence_40187594111.json`,
`.../reproducibility_check_40192868113.json` and the verification records in
the same directory. It records an operational resume and a test-infrastructure
repair, not a new product claim.

## 1. Why the predecessor failed

Run `40187594111` did **not** fail because of a measurement, a frozen-input
change, a product verdict or a gate rejection.

- Its `team` job completed **all** steps with conclusion `success`, including
  `Persist team snapshot`; the producer snapshot is
  `14ee2d1e` on `cycle/core/evaluation/40187594111/team`.
- Its `audit` job completed with conclusion `failure`. Step 5,
  `Independent audit`, failed. Steps 6 (`Enforce audit scope and read gate`)
  and 7 (`Persist audit snapshot`) were skipped.
- No audit branch, no `CYCLE_40187594111_GATE.json` and no audit report exist.
  The `integrate` job is skipped as a consequence. The `resilience` job
  succeeded.
- The audit job's logs are not downloadable from this image
  (`403 Must have admin rights to Repository.`; `GH_TOKEN` is unset), so the
  specific crash inside the audit step is **not** inferred. What is established
  is the step-level failure and the total absence of an audit artifact.

The failure class is therefore **ORCHESTRATION_PROVIDER_FAILURE** (factory
requirement 20), not a producer defect and not a gate `REVISE`/`BLOCKED`
verdict. No verdict was issued.

Machine evidence:
`.../jobs_40187594111_final.json`, `.../run_record_40187594111_final.json`,
`.../audit_ref_absence_40187594111.json`.

## 2. What this run preserved and what it added

Preserved unchanged:

- every committed measurement, frozen hypothesis/freeze and claim-bearing
  record, including the `40162507752` vacuous post-repair result;
- the accepted-tip lineage (`origin/lab/evaluation` = `9be8a7d5`,
  `accept evaluation cycle 40159747851`);
- the historical `v68_correction` block, including its
  `item_2_status: NOW_DISCRIMINATING` value. It is not rewritten; §5 explains
  why it does not apply to the current mount.

Added by this run (all inside the evaluation lane scope):

- `results/evaluation/operational_resume_40192868113/`:
  diagnosis, audit-ref absence, public run/job snapshots, reproducibility check,
  test-repair record, scratch wrapper/engine records and all verification
  records;
- `reports/evaluation/OPERATIONAL_RESUME_40192868113_AUDIT_READY.md`: this
  report;
- a repair of `tests/evaluation/test_post_repair_family_ca_falsifier.py` that
  points its historical mount-head pin at the historical tree named by the
  hypothesis and converts four `tmp_path` tests to executable stdlib tests
  (§4).

## 3. Reproducibility of the committed falsification

The committed record of record is

- `results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json`
  (sha256 `fd29a395…`), and
- `..._engine_mapping_free_recall_falsifier.json`
  (sha256 `7870ba35…`).

A scratch re-execution at accepted mount head
`29a5c4a548ba0ab8b6a8f574de1e732d17f3d109` produced
`.../scratch_40192868113_wrapper.json` and `..._engine.json`. After stripping
only run identity, timestamp and path fields:

- wrapper normalized equal: **true**;
- engine normalized equal: **true**;
- gates equal: **true**; failed-gate set equal: **true**;
- non-vacuity controls, per-question payloads and rehash maps equal: **true**;
- `input_drift`: `[]`; `run_valid`: **true**.

The reproduced verdict is `PRODUCT_FALSIFIED`: 18 gates, 11 passed, 4 failed,
3 reported. The failed gates are `mf::concept_coverage` on
`de-kapitalverletzung` and `mf::counter_authority_surface` on
`de-kapitalverletzung`, `fr-bail-entretien` and `it-responsabilita-medica`.
This is a verification re-execution, not a second independent falsification and
not a re-score.

Record: `.../reproducibility_check_40192868113.json`.

## 4. Test repair: historical post-repair mount pin

`tests/evaluation/test_post_repair_family_ca_falsifier.py` had one red test on
the snapshot. It re-hashed the **live** accepted mount against the
**historical** mount-head pin `8e58724b` from hypothesis `40134202991`; the live
accepted head is `29a5c4a5`.

The repair does **not** waive or weaken the pin:

1. The historical hypothesis and freeze bytes are unchanged.
2. On the live mount, every frozen bundle, baseline-family member and
   instrument byte must still match; only the documented head advance is
   allowed.
3. The historical head pin is verified against the historical tree at
   `8e58724b`, the commit the hypothesis itself names, via a temporary `git`
   worktree.
4. The four synthetic sweep tests used the pytest-only `tmp_path` fixture and
   were previously counted `UNSUPPORTED`. They now use `tempfile` and actually
   execute under the stdlib shim.

Before (HEAD bytes, genuine re-run):
`SHIM_FAIL` — 9 passed, 1 failed, 4 unsupported.
After: `SHIM_PASS` — **14 passed, 0 failed, 0 unsupported**.

Records: `.../pytest_post_repair_before_40192868113.json`,
`.../pytest_post_repair_40192868113.json`,
`.../test_repair_post_repair_pin_40192868113.json`.

## 5. Item (2) status: NOT_YET_DISCRIMINATING

The historical `v68_correction.item_2_status = NOW_DISCRIMINATING` belongs to
run `40144816305` and is preserved as history. It is **not** the current status.

The current post-repair measurement is run `40162507752`:

- verdict `NOT_MEASURED_VACUOUS`, exit 2, because the frozen mount-head pin is
  `8e58724b` while the live accepted mount is `29a5c4a5`;
- precondition H1 (product rejection/incumbent leg landed): **true**;
- precondition H2 (full frozen family regenerated): **false**;
- member-for-member matching: **10/15**; per-role multiplicity parity:
  **false**;
- every frozen role does have at least one post-repair bundle (role coverage
  true; 4 offline roles + 1 server role);
- producer diagnostics: defect histogram 0, sound row `bstger_SK.2023.49`
  preserved, zero false rejects, path-scope residual cleared.

The accepted product claim of a “full flagship family (4 offline + 1 server)”
is therefore satisfied at **role** level, but it is not 15/15
**member-for-member**. The ordered item-(2) protocol requires the latter. No
synthetic stand-in is substituted. A corrected-pin re-run would still fail H2,
so it is not executed and is not turned into a new same-question cycle.

Current status: **NOT_YET_DISCRIMINATING**. The `40162507752` diagnostics are
producer-attested, not accepted, and have no independent audit/accept commit.
Machine record:
`state/evaluation.json#v68_item_2_reconciliation_40192868113`.

## 6. Verification results

| Check | Command | Result | Record |
|---|---|---|---|
| State integrity gate | `python3 -m evaluation.state_integrity_gate --run-id 40192868113` | **ALL_CHECKS_PASS** — 11/11, 0 failed | `.../state_integrity_gate_40192868113.json` |
| Lane suite | `python3 -m evaluation.lane_suite --skip-pytest` | **PASS** — 88/88, 0 skipped, 164.769 s, 20/20 falsification families broken | `.../lane_suite_40192868113.json` |
| Minimal benchmark tests (stdlib shim) | `python3 -m evaluation.no_pytest_runner --test-file tests/evaluation/test_minimal_retrieval_ca_benchmark.py` | **SHIM_PASS** — 21 passed, 0 failed | `.../pytest_minimal_40192868113.json` |
| Guard tests (stdlib shim) | same, `test_nested_evidence_refs_guard.py` + `test_state_integrity_gate.py` | **SHIM_PASS** — 4 passed, 0 failed, 12 unsupported (fixture/parametrisation only) | `.../pytest_guards_40192868113.json` |
| Post-repair tests (stdlib shim) | same, `test_post_repair_family_ca_falsifier.py` | **SHIM_PASS** — 14 passed, 0 failed, 0 unsupported | `.../pytest_post_repair_40192868113.json` |
| Nested evidence refs | `python3 evaluation/nested_evidence_refs_guard.py --run-id 40192868113` | **NESTED_REFS_RESOLVED** — 182 worktree, 9 cross-lane, 2 branch-history, 2 disclosed-historical, **0 unresolved** | `.../40192868113_nested_evidence_refs.json` |
| Write scope | `python3 evaluation/snapshot_audit/write_scope.py --lane evaluation` | **SCOPE_CLEAN** — 24 entries, 0 bad, 0 junk | `.../write_scope_40192868113.json` |

The shim is not pytest. Cases needing fixtures or parametrisation are counted
`UNSUPPORTED`/not-run, never passed; the 12 unsupported guard cases are
disclosed rather than hidden. The post-repair suite no longer has any
unsupported case.

## 7. Audit readiness

This is a producer snapshot, not an audit. The independent audit job must write:

- `results/audit/evaluation/CYCLE_40192868113_GATE.json`
- `reports/audit/evaluation/CYCLE_40192868113.md`

against its own checkout. No audit verdict is claimed here. The previous run's
audit failed before writing either path; this run's job must not repeat that
failure. `state/evaluation.json` keeps
`current_cycle_audit_status = PENDING_INDEPENDENT_AUDIT`.

## 8. Claim ceiling and negative results

- No new claim-bearing measurement, no re-score, no acceptance, no product
  promotion and no audit verdict.
- The prior audit failure is preserved as a negative operational result; its
  cause is not guessed.
- The `40162507752` result remains `NOT_MEASURED_VACUOUS` with H2 false; it is
  not upgraded by this resume.
- Item (2) remains `NOT_YET_DISCRIMINATING`; the 15-member family is 10/15.
- `continue_recommended` remains `false`.

## 9. Evidence index

All paths are relative to the repository root.

- `results/evaluation/operational_resume_40192868113/diagnosis_40187594111.json`
- `.../audit_ref_absence_40187594111.json`
- `.../run_record_40187594111_final.json`, `.../jobs_40187594111_final.json`
- `.../run_record_40192868113.json`, `.../jobs_40192868113.json`
- `.../reproducibility_check_40192868113.json`
- `.../pytest_post_repair_before_40192868113.json`
- `.../pytest_post_repair_40192868113.json`
- `.../test_repair_post_repair_pin_40192868113.json`
- `.../pytest_minimal_40192868113.json`, `.../pytest_guards_40192868113.json`
- `.../lane_suite_40192868113.json`
- `.../40192868113_nested_evidence_refs.json`
- `.../state_integrity_gate_40192868113.json`
- `.../write_scope_40192868113.json`
- `.../scratch_40192868113_wrapper.json`, `.../scratch_40192868113_engine.json`
- `.../manifest_40192868113.json` (convenience hash index)
