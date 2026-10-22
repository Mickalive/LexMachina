# Minimal Retrieval / Counter-authority Benchmark — run 39873360672 provenance/state repair

- Verdict: **REPAIR_VERIFIED_AUDIT_READY** (exit 0)
- Direction: v63
- Resumed snapshot: run 39872787455 @ `a07602e4858920902d926e75267619642261e0b1`
- Rejected cycle repaired: 39870661520 (audit gate REVISE, D1-D3)
- Measurement origin run: 39870661520 (records preserved verbatim)
- Accepted byte-duplicate: 39854748616
- Benchmark re-executed: **False** (metadata-only provenance rebind, per audit instruction)
- Gates: 9/9 passed
- Controls: 5/5 hold
- Failed gates: none
- Product mount head: `fe219a197e4bfb129984a732ab9adca917556eac`

## What this cycle establishes

The audit of cycle 39870661520 verified the measurement layer but rejected the snapshot on
D1 (machine records mislabeled `run_id=local_verification`), D2 (`state/evaluation.json` not
updated) and D3 (undisclosed byte-duplicate of accepted run 39854748616). Round-1 repair run
39872787455 failed at its producer step and persisted a byte-identical snapshot. This cycle
resumes it and discharges D1-D3 without re-running the benchmark:

- **D1** — both machine records are re-published as dispatch-bound rebind records
  (`results/evaluation/minimal_retrieval_ca_benchmark/39873360672.json`, `results/evaluation/minimal_retrieval_ca_benchmark/39873360672_engine_mapping_free_recall_falsifier.json`) with `run_id=39873360672` and
  `measurement_origin_run_id=39870661520`; the `local_verification` artifacts are
  preserved byte-for-byte and named by sha256 in the rebind records.
- **D2** — `state/evaluation.json` now carries the RESEARCH_PROTOCOL fields for this dispatch,
  `accepted_run_id=39866970583`, the new evidence refs, and
  `continue_recommended=false` with explicit re-open triggers.
- **D3** — the duplicate lineage is published: the wrapper record differs from accepted
  39854748616 only on `{run_id, generated_at_utc, engine_record_path}`; the engine record
  differs from accepted 39806933576 only on `{run_id, generated_at_utc, product_mount_head}`.
  All three re-open triggers are adjudicated NOT FIRED on the accepted base.

## Measurement of record (adopted, not re-measured)

- Verdict: **PRODUCT_FALSIFIED** (exit 1), 18 gates = 11 passed / 4 failed / 3 reported.
- Failed gates: `mf::concept_coverage::39319405429::de-kapitalverletzung` and
  `mf::counter_authority_surface` on de/fr/it.
- `run_valid=true`, `input_drift=[]`, non-vacuity battery 4/4 hold.
- The frozen falsification of runs 39852758814/39854748616 stands unchanged.

## Orchestration diagnosis of run 39872787455

Public REST job facts (captured in `results/evaluation/orchestration/39872787455_diagnosis.json`): team job **failure**,
failed step **Run lane cycle**; `Validate active MVP producer state` and
`Enforce lane write scope` were skipped; audit/integrate skipped; resilience succeeded.
The persisted team branch is byte-identical to the rejected 39870661520 tree. The exact job
log is not retrievable without repository admin rights (HTTP 403), so the mechanism
attribution (`LEX_REQUIRE_DELTA` / `LEX_ZERO_DELTA_REPAIR`, exit 67) is recorded as an
explicit INFERENCE, not as log-confirmed fact. This was a producer-step failure, not a
validation-step rejection.

## Controls

- **C1_planted_digest_drift_is_detected**: holds=True
- **C2_planted_duplicate_diff_is_detected**: holds=True
- **C3_planted_state_ref_break_is_detected**: holds=True
- **C4_planted_rebind_run_id_mismatch_is_detected**: holds=True
- **C5_planted_measurement_tamper_is_detected**: holds=True

## Claim ceiling

This instrument establishes exactly one thing: that the rejected cycle 39870661520 snapshot can be made audit-ready by discharging its three packaging defects (D1 provenance, D2 state, D3 duplicate disclosure) with a metadata-only rebind that re-runs no benchmark and preserves every claim-bearing artifact verbatim. It is NOT a new falsification and NOT a new retrieval/counter-authority/label/geometry/serve measurement; it does not move or meet LABEL_SOUND or GEOMETRY_SOUND (both stay REPORTED-ONLY and unmet on the v3 bytes), lifts no DO-NOT-SERVE order, certifies no packet admission, does not claim jurist usefulness, keeps human_gate_ready and machine_gate_ready false, and runs no obsolete universal-174k benchmark. The PRODUCT_FALSIFIED finding remains the finding of runs 39852758814/39854748616 and is adopted unchanged.

## Provenance

- Cycle record: `results/evaluation/operational_resume/39873360672.json`
- Diagnosis: `results/evaluation/orchestration/39872787455_diagnosis.json`
- Hypothesis: `evaluation/OPERATIONAL_RESUME_39873360672_HYPOTHESIS_V1.json`
- Freeze record: `evaluation/OPERATIONAL_RESUME_39873360672_FREEZE.json`
- Rebind wrapper: `results/evaluation/minimal_retrieval_ca_benchmark/39873360672.json`
- Rebind engine: `results/evaluation/minimal_retrieval_ca_benchmark/39873360672_engine_mapping_free_recall_falsifier.json`
- Preserved source wrapper: `results/evaluation/minimal_retrieval_ca_benchmark/local_verification.json` (sha256 d52a77c4a9c7f65b58c4faaa7e7d0e25c13c2d2c5448740c8364d9a21c3c5822)
- Preserved source engine: `results/evaluation/minimal_retrieval_ca_benchmark/local_verification_engine_mapping_free_recall_falsifier.json` (sha256 2ebaf282b7c1330cda96dcca7e7713bca002bbecdff30ac431c52db1f993e671)
- Preserved source report: `reports/evaluation/RETRIEVAL_CA_BENCHMARK_local_verification.md` (sha256 d946630b5b33d1a7fd8ec25bc9d34fff3d7b4b0950b7ce923b7a9ec9e5459cd2)

No frozen file, test input, rubric, bar or threshold was edited; no benchmark was re-run;
no universal-174k benchmark was run.
