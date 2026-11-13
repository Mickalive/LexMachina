# Operational Resume — Evaluation Lane, Run 43378111582

**Run:** 43379403095 (direction v68, FAST MVP MODE, operational resume)
**Snapshot resumed:** `refs/heads/cycle/core/evaluation/43378111582/team` = `6c45cf2a`
**Freeze-first:** hypothesis + freeze committed as `e806e660` before any verification execution
**Claim ceiling:** operational-resume diagnosis, deliverable verification, precondition
re-adjudication and audit-ready snapshot assembly. It creates no new product
measurement, moves no frozen bar, rubric, threshold or verdict contract, issues no
serve or admission verdict, and is **not an independent audit** of run 43378111582 or
of this run.

## 1. Why the last six runs issued no verdict

All six runs are diagnosed from committed public artifacts (GitHub run/job
envelopes and check-run annotations captured under
`results/evaluation/operational_resume_43379403095/api/`, plus the persisted
snapshot itself). Workflow job logs are HTTP 403 without a token, so no log line
is quoted; conclusions rest on job-step metadata, annotations and git.

| run | team | audit | class of record |
|---|---|---|---|
| 43365313827 | failure, exit 1 at `Run lane cycle` | skipped | `LANE_CYCLE_EXECUTION_FAILURE` |
| 43365482535 | **success** (produced the FAST-MVP deliverable) | failure, exit 78 `LEX_WORK_QUANTUM_EXPIRED seconds=2700` at `Independent audit` | `AUDIT_QUANTUM_EXPIRY_NO_GATE` — never reached `Enforce audit scope and read gate`, no gate of record |
| 43371040309 | failure, exit 1 at `Run lane cycle` | skipped | `LANE_CYCLE_EXECUTION_FAILURE` |
| 43371186416 | failure, exit 67 `LEX_ZERO_DELTA_REPAIR` | skipped | `LEX_ZERO_DELTA_REPAIR` |
| 43371675511 | **success** (state-provenance pin) | failure, exit 78 `LEX_WORK_QUANTUM_EXPIRED seconds=2700` at `Independent audit` | `AUDIT_QUANTUM_EXPIRY_NO_GATE` — no gate of record |
| 43378111582 (resumed) | failure, exit 1 after `LEX_MODEL_AUTH_FAILURE model=opencode/big-pickle; quarantining for this run` then `LEX_WORK_QUANTUM` rotation `LEX_MODEL_ROTATE selected=opencode/beam-free index=3 pool_size=4` | skipped | `LANE_CYCLE_EXECUTION_FAILURE_PROVIDER_ROTATION` — factory-wide requirement 20: a provider-rotation/auth failure is **not a verdict, not a product defect and not a human-gate problem** |

Run 43378111582 failed only at `Run lane cycle`; `Validate active MVP producer
state` and `Enforce lane write scope` were skipped, audit and integrate were
skipped, no `/audit` ref exists for any of 43365482535, 43371675511 or
43378111582, and its persisted delta adds **exactly eleven lane-namespace
diagnostic paths** (a ref probe and API envelopes under
`results/evaluation/operational_resume_43378111582/`) with **zero
audit-namespace paths** — it is not a write-scope violation. The audit job is
gated on `needs.team.result == 'success'`; the two audit expiries therefore
starved promotion of the two team-successful runs. `.github/**` is
control-plane scope: recorded here, not edited.

Diagnosis records: `diagnosis_43378111582.json` (13/13 checks) and
`diagnosis_chain_43379403095.json` (35/35 checks) in
`results/evaluation/operational_resume_43379403095/`.

## 2. The snapshot's FAST-MVP deliverable is preserved and verified

The completed deliverable of the snapshot is run **43365482535** — the
minimal-ca-falsify / mapping-free falsifier on packet-of-record `39319405429`:

- wrapper `results/evaluation/minimal_ca_falsify_benchmark/43365482535.json`
  sha256 `2873ef05…`, engine record `4aebbc9b…`, report `60d30fc3…` — all three
  still re-hash to the pins frozen in
  `evaluation/OPERATIONAL_RESUME_43379403095_FREEZE_V1.json`;
- verdict **PRODUCT_FALSIFIED**, exit 1, 18 gates (11 pass / 4 fail / 3
  reported), the four named `mf::` failed gates, `run_valid=true`, no input
  drift, product mount head `7be4480e`;
- non-vacuity battery all holds; wrapper/engine/report agree
  (`deliverable_verification_43379403095.json`, 17/17 checks, verdict
  `DELIVERABLE_VERIFIED`);
- a fresh out-of-tree scratch replay of the accepted wrapper
  `evaluation.minimal_ca_falsify_benchmark` **reproduces all 41
  measurement-bearing fields** (`REPLAY_REPRODUCES`, zero differing); the
  claim-bearing original was not rewritten (its frozen sha is re-checked in the
  same verification);
- field-identical outside the seven named volatile fields to the previously
  verified twin `43342851837` on the same product head (`RECORDS_MATCH`,
  41 compared / 0 differing; only the host `numeric_environment.platform`
  label differs).

No 174k rerun was performed; the universal-174k benchmarks stay obsolete and
were not restarted.

## 3. Ordered item (2) is still NOT_YET_DISCRIMINATING

Re-run of `evaluation.v68_item2_family_gate` at unchanged accepted product head
`7be4480ed3ca623b77ea082404ca3b5b7ac5ee83`: status
**NOT_YET_DISCRIMINATING**, product fixed-path family byte-identical to the set
accepted run 40258497460 already measured (50/50 byte-identical, zero
differing), named family regenerated only 14/15 under the frozen role rule
(`server/served` current 3 < frozen 4), role parity false. `lab/product` has
not advanced since accepted adjudication. Record:
`item2_family_gate_43379403095.json`.

## 4. Ordered work items and standing orders

- **Item (1)** — discharged elsewhere (bypass-clause correction note); not re-opened.
- **Item (2)** — reported as NOT_YET_DISCRIMINATING above; no conditional
  re-measure is triggered.
- **Item (3)** — the falsification record of 43365482535 is kept untouched and
  is not re-adjudicated.
- **Item (4)** — report-only, satisfied by this document.
- **Item (5)** — applied here as OPERATIONAL, not as evidence.
- Both **DO-NOT-SERVE** orders stand; **admission stays fail-closed**;
  `human_gate_ready` stays false; `continue_recommended` stays **false**.
- No new same-question evidence cycle was run.

## 5. State, scope and validation

State update (`evaluation/state_update_43379403095.py`) is additive only:
`github_run` / `proposed_run_id` → 43379403095 in both state files, outgoing
values preserved append-only, `resumed_run_id` → 43378111582, `resume_chain`
appended, a new `operational_resume_43379403095` block with
`audit_status = PENDING_INDEPENDENT_AUDIT` / `accepted_as_evidence = false`,
`evidence_refs` appended with `evidence_refs_n` re-derived, and the prior
`next_recommendation` text preserved verbatim after `PRESERVED PRIOR TEXT:`.
`accepted_run_id` (40265377500), `direction_version` (68), `evidence_tier`,
`cycle_status`, `continue_recommended`, `human_gate_ready` and every prior
run's block and refs are untouched.

Validation performed by `evaluation/operational_resume_43379403095.py`:

- write-scope repro of the resumed run's eleven-path delta: **SCOPE_CLEAN**
  (`write_scope_repro_43378111582.json`, 0 bad paths);
- live producer write scope for this run: **SCOPE_CLEAN**
  (`write_scope_live_43379403095.json`, every entry allowed); no file under
  `results/audit/` or `reports/audit/` is added, modified or deleted by this
  run (the snapshot itself added zero audit-namespace paths);
- state-integrity gate, lane suite (`--skip-pytest`) and root/lane identity
  agreement are executed by the final phase; their verdicts live in
  `state_integrity_gate_43379403095.json`, `lane_suite_43379403095.json` and
  `verification_43379403095.json` in
  `results/evaluation/operational_resume_43379403095/`, with the post-final
  integrity re-run at `state_integrity_gate_final_43379403095.json`;
- targeted tests run under the lane's disclosed `evaluation.no_pytest_runner`
  shim (pytest absent in the producer image — standing disclosure; the shim is
  not pytest and counts anything it cannot execute as not-run): record
  `pytest_targeted_43379403095.json`. The known pre-existing failure of
  `test_mount_provenance_gate::test_check_provenance_on_the_committed_tree_does_not_re_derive`
  (`n_do_not_re_derive` 3 vs 4, the pinned finding of record for run
  39231573047) is preserved as-is in
  `pytest_mount_provenance_known_failure_43379403095.json` together with the
  same failure reproduced at the untouched snapshot `6c45cf2a` — none of it is
  introduced by this cycle, and negative results remain evidence. Class-based
  `unittest.TestCase` files (e.g. `test_disclosure_provenance_crosscheck.py`)
  are not discovered by the shim and contribute zero executed cases; they are
  disclosed here rather than counted as passed.

Provenance: every measurement above is re-derived from committed artifacts
pinned in `evaluation/OPERATIONAL_RESUME_43379403095_FREEZE_V1.json`
(10 repo pins, deliverable/engine/report pins, twin, prior-resume artifacts,
state-at-freeze, API envelope shas); the freeze was committed (`e806e660`)
before any hypothesis execution.

## 6. Claim ceiling

This report and its records establish only that the persisted snapshot of run
43378111582 is **diagnosed, its completed FAST-MVP deliverable is verified
unchanged, ordered work is re-adjudicated, and the snapshot is audit-ready by
in-lane-only writes**. They are **producer-authored**; they are **not an
independent audit** of any run, promote no run to evidence
(`accepted_as_evidence = false`), and create no serve or admission verdict.
Independent audit of this resume is pending; `continue_recommended = false`.
