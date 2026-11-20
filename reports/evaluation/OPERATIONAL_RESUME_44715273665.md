# Operational Resume — evaluation snapshot 44708758013 (run 44715273665)

- **Lane:** evaluation · **Direction:** v68 · **Mode:** operational resume / fast MVP
- **Snapshot resumed:** run 44708758013, commit `7de561aaadecdc08d92df8cb59a5a05077857834`
  ("evaluation cycle 44708758013 repair 0"), HEAD of this worktree, tracked tree identical.
- **Claim-bearing run:** 44715273665 (this run) · **Accepted run:** 40265377500 (unchanged)
- **Verdict:** `SNAPSHOT_AUDIT_READY` — final gates `AUDIT_READY`, all rules pass,
  self-test **13/13 passed (0 failed)** at its run point in phase state-update,
  audit index written last with `all_entries_exist=true` (23 rows, 0 stale).
- **Claim ceiling:** operational provenance and residual closure only. No quality
  measurement, no frozen edit, no serve verdict, no packet admission, no human-gate
  claim, no universal-174k benchmark.

## 1. Failure diagnosis (lane item: diagnose orchestration/validation failure)

**Class: `ORCHESTRATION_PRODUCER_QUANTUM_EXPIRY_RC78`** — record
`results/evaluation/operational_resume_44715273665/run_44708758013_producer_quantum_diagnosis.json`,
captured from the public GitHub REST run/jobs/annotations endpoints
(`.../run_44708758013_jobs_rest_capture.json`, `..._team_annotations.json`; log
bodies are HTTP 403 unauthenticated and are never quoted).

| Fact | Value |
|---|---|
| Failing step | team job step 6 `Run lane cycle` |
| Ran | 09:13:25Z → 09:58:30Z = **2705 s** |
| Quantum | `LEX_WORK_QUANTUM_EXPIRED seconds=2700` + `Process completed with exit code 78.` (both annotations confirmed) |
| Step 7 `Validate active MVP producer state` | **SKIPPED** (not failed) |
| Step 9 `Enforce lane write scope` | **SKIPPED** (not failed) |
| Audit / integrate / gate | skipped; **no** `CYCLE_44708758013_GATE.json`, **no** `/audit` ref |
| State at snapshot | `direction_version=68`, `cycle_status=COMPLETE` → **step 7 would have passed** |

Ruled out: rc-67 zero-delta (the lane requires a delta but rc-67 only fires on rc-0
with empty porcelain; this run exited 78 with a populated workspace and a persisted
snapshot commit), validation failure (skipped, not failed), write-scope failure
(skipped), gate REVISE/BLOCKED (no gate exists at all), product defect (the killed
work is evaluation-lane operational provenance, not product code).

The kill happened **~15 minutes after** the producer pack reached
`AUDIT_READY` (final gates 09:43:58Z, regression 09:45:03Z, latent-red
disclosure 09:56:00Z) — budget exhaustion at the end of the cycle, not a
producer work failure.

## 2. Preservation — no restart, byte-identical prior pack

Record: `results/evaluation/operational_resume_44715273665/44708758013_pack_byte_identity_at_resume.json`.
18 files of the 44708758013 pack were pinned **at intake, before this run wrote
anything**, and all 18 still match (`all_match=true`). No prior file was modified
(`git diff --name-only HEAD` empty; only new files under this run's namespace were
added). The prior pack's own final gates say `AUDIT_READY, passed=true,
2026-11-20T09:43:58Z` — the pack was complete before the kill.

Prior pack verdict: `AUDIT_READY`. Prior audit index: **preserved, not rewritten**
(it carries 5 stale rows — disclosed in §3/R3 and in the byte-identity record).

## 3. Residual closure (what the hard kill left open)

Record: `.../44708758013_residual_closure.json`.

- **R1 — regression record identical to attempt1; planned exclusion never executed.**
  Disclosed, prior files preserved. This run **re-executed** the reused battery under
  its own run id with the frozen rule "the only permitted failure is the disclosed
  inherited latent red", so the negative stays visible as evidence and the record is
  adjudicable (`44715273665_regression_guard.json`).
- **R2 — prior final gates `R6` cites `.../44708758013_nested_evidence_refs.json`,
  which does not exist** (only the `_runidlabel_attempt1` file exists).
  `DISCLOSED_NOT_FABRICATED`: a file named for run 44708758013 must hold that run's
  own measurement, and no corrected record of that run exists on any ref — this run
  therefore does **not** author one. It re-executed the same guard under its own run
  id (`.../44715273665_nested_evidence_refs.json`) on the same state.
- **R3 — prior audit index stale by construction** (index written before the result
  record was stamped): 5 stale rows (report `exists:false` at index time, canonical
  nested missing, result sha `a744bc0c…` ≠ actual `f7a54982…`, plus freeze and
  instrument rows). Prior index **not rewritten**. This run writes its index as the
  **last** artifact, after every referenced file exists and after the result record
  is stamped, and asserts `all_entries_exist` before exit.
- **R4 — no independent audit gate for 44708758013.** Audit/integrate are workflow
  scope; this run makes the snapshot adjudicable instead (fastest verification path
  below).

## 4. Ordered work (v68) — no re-derivation

| # | Item | Status this cycle |
|---|---|---|
| 1 | Report-only correction of stale bypass clause | `DISCHARGED_ELSEWHERE_HASH_VERIFIED_NOT_RERUN` (report `b10eeb3a…` + record `2e691dd0…` re-hashed; not re-run) |
| 2 | Conditional re-measure | **`NOT_YET_DISCRIMINATING`** — frozen 15-member family 14/15; no full protocol, no packet-of-record scoring. Unchanged. |
| 3 | Falsification record of record | `KEPT_NOT_RERUN` — benchmark of record 40105794124, sha `fd25345b…`, `PRODUCT_FALSIFIED` on packet 39319405429; re-hashed only |
| 4 | Report-only fixes | `REPORTED_ONLY_WHERE_QUOTED` (not quoted this cycle) |
| 5 | Frozen work honoured | `HONOURED` — no frozen bench/D2/bypass re-derivation; no universal-174k benchmark; RULES_LABEL `4457e971…`, RULES_GEOMETRY `a7452748…`, fast-MVP instrument `fa5aa9a5…` all re-hashed unedited |

## 5. Battery and self-test (negative results preserved)

`44715273665_regression_guard.json` — 5 frozen files under the documented no-pytest
shim: **35 passed, 1 failed, 6 unsupported (fixtures/parametrisation), 0 absent**.

- The single failing case is the disclosed pre-existing latent red
  `test_mount_provenance_gate.py::test_check_provenance_on_the_committed_tree_does_not_re_derive`
  (root cause: commit `8fe862e8` / cycle 39548140787 removed the state root block
  `mapping_free_recall_falsifier`; `results/evaluation/orchestration/39884405570_diagnosis.json`).
  Rule: **pass**. `excluded_from_record=[]`, `negative_result_preserved=true`.
- **Environment limitation (disclosed):** `test_cross_lingual_alignment_v10.py`
  raises `IMPORT_ERROR: No module named 'numpy'` (0 cases executed). numpy is absent
  in this image; run 40217938706 recorded the **identical** import error and still
  passed `SHIM_PASS`.
- **Freeze amendments (both disclosed, both before final gates):**
  - `OPERATIONAL_RESUME_44715273665_FREEZE_V1_1_AMENDMENT.json` — after the first
    battery run, import errors were admitted **only** for the pre-declared
    numpy-absent file (file list, failing-case rule and case outcomes unchanged;
    pre-amendment battery record preserved as
    `44715273665_regression_guard_pre_amendment.json`).
  - `OPERATIONAL_RESUME_44715273665_FREEZE_V1_2_AMENDMENT.json` — the first
    final-gates self-test ran 11/13 (2 × `KeyError operational_resume_44715273665`)
    because the self-test asserts this run's state block, which phase state-update
    writes after final-gates by design; the self-test was moved to run inside
    state-update, after the state exists and before the audit index is written.
    No test outcome, gate criterion or file selection changed.
- Final self-test: `.../44715273665_selftest.json` (runs in state-update, before
  the index; asserted `n_failed == 0` by the phase exit condition).

## 6. Final gates and verification

`.../44715273665_final_gates.json` → **`AUDIT_READY`, passed=true**:

| Rule | Result |
|---|---|
| freeze_inputs (hypothesis/instrument/test pins, frozen bars unedited) | pass |
| snapshot_and_prior_pack (HEAD=`7de561aa`, tracked tree identical, 18/18 pins) | pass |
| R5 regression inherited-red-only | pass |
| R6 nested + state (guard 0 unresolved pre- and post-state; state gate 11/11) | pass |
| R7 write scope (`SCOPE_CLEAN`, n_bad=0) | pass |
| R8 residuals disclosed | pass |

State update (both files, additive, parity kept): `state/evaluation.json` and
`evaluation/state/evaluation.json` gain block `operational_resume_44715273665`;
`accepted_run_id=40265377500` unchanged, `direction_version=68`,
`github_run=44715273665` on both, `evidence_refs_n == len(evidence_refs)`,
every ref resolves. Record: `.../44715273665_state_update.json`, including the
post-state verification (nested guard, state gate, write scope on the **final**
state).

**Fastest independent verification (read-only)**

```bash
# 18 prior-pack pins still hold
sha256 of the 18 files pinned in .../44708758013_pack_byte_identity_at_resume.json
python3 -m evaluation.nested_evidence_refs_guard --run-id 44715273665 --out-dir <tmp>   # 0 unresolved
python3 -m evaluation.state_integrity_gate --run-id 44715273665 --out <tmp>             # 11/11
python3 evaluation/no_pytest_runner.py --run-id 44715273665 \
    --test-file tests/evaluation/test_operational_resume_44715273665.py --out <tmp>     # 13/13
# every row of .../44715273665_AUDIT_INDEX.json re-hashes to its declared sha256
```

Re-running a phase **rewrites that phase's records** (by design); a full
re-run is the ordered sequence `prestate → battery → final-gates → report →
state-update`, and `state-update` must stay last because it writes the audit
index as the final artifact.

Audit index: `.../44715273665_AUDIT_INDEX.json` — written **last**, every row
re-hashed after the result record was stamped, `all_entries_exist=true`,
`missing_entries=[]`.

## 7. Posture

`packet_admitted=false`, `machine_gate_ready=false`, `human_gate_ready=false`,
`ready_for_owner_session=false`, `owner_decision_required=false`,
`continue_recommended=false`. Independent audit of this pack is workflow scope
(R4); the pack is staged for it.
