# Operational resume: run 40423855962 → 40423990845

- Direction: v68 (evaluation lane, FAST MVP mode; control plane mounted from `origin/main`; the lab-branch `state/factory_direction.json` copy is stale v35 and is disclosed, not used)
- Resumed run: `40423855962` (Core evaluation dirV68 repair2, conclusion failure)
- Run head: `0c551b49a1c908d439702d477e192bb784865e1d`
- Persisted snapshot: `ea98384e54d31d2e694c418a1d1ce5769fc6c32f`
- Current accepted product mount: `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83`
- Overall: **AUDIT_READY**
- Frozen hypothesis: `evaluation/OPERATIONAL_RESUME_40423990845_HYPOTHESIS_V1.json`
- Freeze record: `evaluation/OPERATIONAL_RESUME_40423990845_FREEZE_V1.json`
- Audit index: `results/evaluation/operational_resume_40423990845/AUDIT_INDEX.json`

## 1. Why the run failed

Run 40423855962 failed at step 6 'Run lane cycle' in 1.0s, before the lane agent started. The run head 0c551b49 carries state/model_health.json with healthy=False, resolved_model=None and status='NO_TOOL_CAPABLE_FREE_MODEL' (last checked by run 40421365985). A byte-faithful re-execution of the wrapper's resolve_model_args predicate on those committed bytes exits 76 (LEX_NO_HEALTHY_FREE_TOOL_MODEL); the same predicate on the later control-plane head 4fd41970 exits 0 with 'opencode/beam-free'. The run's own direction is v68 and its agent registry is 7/7 clean, so neither the supersession guard nor the card guard fired. 'Clean generated junk' and 'if: always()' snapshot persistence succeeded; audit/integrate were skipped and no /audit ref exists, i.e. the run issued NO verdict. This is an ORCHESTRATION/MODEL-HEALTH provider failure, not a lane-scope validation failure, not a zero-delta repair, not a work-quantum starvation and not a gate REVISE/BLOCKED.

- Resolver at run head: exit `76` (`NO_TOOL_CAPABLE_FREE_MODEL`)
- Resolver at control-plane head 4fd41970: exit `0` (`opencode/beam-free`)
- Failed step duration: `1.0s`
- Job logs were unavailable unauthenticated (HTTP 403, admin rights required), so the exact wrapper stderr is an inference from the committed predicate, not a log capture.

## 2. Snapshot

- Verdict: **SNAPSHOT_PRESERVED_ON_ACCEPTED_BASE**
- Team branch == `ea98384e54d31d2e694c418a1d1ce5769fc6c32f`; accepted base == `ea98384e54d31d2e694c418a1d1ce5769fc6c32f`; tree diff empty.
- Snapshot subject: `accept evaluation cycle 40265377500`; parent: `9fe9d7143133dde25152e2babbe13438a661cfa1` (`evaluation cycle 40265377500 repair 0`).
- No commit from the failed run exists; nothing was lost or needs relocation.

## 3. Deliverable verification

- Verdict: **DELIVERABLE_VERIFIED_WITH_AUDIT_MISMATCH**
- Last clean accepted cycle: `40258497460` / accept `64208e15` / verdict `SOUND_COUNTER_ROW_PRESENT`. Gate and artifact agree; this remains the accepted pointer.
- Structurally accepted cycle `40265377500` (accept `ea98384e`): committed artifact `test_40265377500.json` is `PRODUCT_FALSIFIED` (3 served questions, 18 gates, 11 pass / 4 fail), but the in-tree audit gate is `BENCHMARK_VALID_NO_FALSIFICATION` on a 4-question cached-bundle benchmark. **AUDIT_ARTIFACT_MISMATCH**, `accepted_as_evidence=false`.
- Pending recall cycle `40261335674`: `PRODUCT_FALSIFIED_RECALL_LOSS`, no audit gate, no accept commit, not accepted evidence.
- Ordered item (1): `PRESENT_WITH_OPEN_MACHINE_PROVENANCE_CHECKS`; machine verdict `CORRECTION_NOT_CONFIRMED`, measurement unchanged `True`; CC6/CC7 open and disclosed.

## 4. Replay

- Verdict: **REPLAY_REPRODUCES** — replay elapsed `0.166s`, replay exit `1`, 4 differing top-level fields, all allowed environment fields: `['engine_record_path', 'generated_at_utc', 'product_mount', 'run_id']`.
- Gate records, per-question records and both re-hash maps are byte-equal.
- This reproduces the artifact; it does not cure the mismatched audit.

## 5. Ordered item (2) precondition

- Verdict: **NOT_YET_DISCRIMINATING** on product mount `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83`.
- Leg: `LANDED`; full-family regeneration: `False`; member-for-member `14/15`; server/served 3 of 4.
- No packet scored, no d2 probe re-run, no standing falsification re-run.

## 6. State and audit pointers

- Accepted pointer: `40258497460` (unchanged).
- `github_run`: `40423990845`; resumed: `40423855962`.
- `audit_status`: `AUDIT_READY_PENDING_INDEPENDENT_AUDIT`.
- The structurally accepted 40265377500 is NOT advanced because no verified independent audit covers the committed minimal falsifier.

## 7. Verification battery

- `state_integrity_gate`: exit `0`, observed `ALL_CHECKS_PASS`, expected `ALL_CHECKS_PASS` → PASS
- `nested_evidence_refs_guard`: exit `0`, observed `NESTED_REFS_RESOLVED`, expected `NESTED_REFS_RESOLVED` → PASS
- `write_scope`: exit `0`, observed `SCOPE_CLEAN`, expected `SCOPE_CLEAN` → PASS
- `lane_suite`: exit `0`, observed `SUITE_PASS`, expected `SUITE_PASS` → PASS
- `pytest_targeted`: exit `0`, observed `SHIM_PASS`, expected `SHIM_PASS` → PASS
- `pytest_multilingual_provenance`: exit `0`, observed `SHIM_PASS`, expected `SHIM_PASS` → PASS
- `pytest_snapshot_audit_preexisting_failure`: exit `1`, observed `PREEXISTING_FAILURE_REPRODUCED`, expected `PREEXISTING_FAILURE_REPRODUCED` → PASS
- `pytest_post_state`: exit `0`, observed `SHIM_PASS`, expected `SHIM_PASS` → PASS
- `state_integrity_gate`: exit `0`, observed `ALL_CHECKS_PASS`, expected `ALL_CHECKS_PASS` → PASS
- `nested_evidence_refs_guard`: exit `0`, observed `NESTED_REFS_RESOLVED`, expected `NESTED_REFS_RESOLVED` → PASS
- `write_scope`: exit `0`, observed `SCOPE_CLEAN`, expected `SCOPE_CLEAN` → PASS

Final `state_integrity_gate` and `nested_evidence_refs_guard` records are under `results/evaluation/operational_resume_40423990845/`.

The `pytest_snapshot_audit_preexisting_failure` row is a disclosed negative result, not a pass of the test: `tests/evaluation/test_snapshot_audit.py` fails on the stale accepted-base coverage record (`results/evaluation/accepted_base_gate_coverage_39043684319.json`, head 3506f0e4) both in this worktree and identically on the untouched execution base ea98384e. This resume does not rewrite that audit record; it records the pre-existing failure and its exact reproduction.

## What this does not establish

- It does not re-measure the product, move a frozen bar or admit a packet.
- It does not issue a serve verdict or stage a human gate; both DO-NOT-SERVE orders stand.
- It does not claim the map helps a jurist or that the minimal falsifier is fixed. The falsification stands: counter-authority surface empty on all served questions.
- It does not make the mismatched audit gate valid; the mismatch is disclosed as a finding for the independent auditor.

**Claim ceiling:** operational-resume diagnosis, snapshot/deliverable verification and in-lane state/audit-pack refresh only.
