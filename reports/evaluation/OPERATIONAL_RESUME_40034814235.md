# Operational-resume cycle 40034814235 — evaluation lane, direction v65

- **Run**: `40034814235` (`Core evaluation dirV65 repair1`, workflow input
  `resume_from_run_id=40034534808`, `repair_round=1`)
- **Mode**: OPERATIONAL RESUME of the persisted producer snapshot of run
  `40034534808` (team branch tip `b8d526bc`)
- **Hypothesis/freeze record**: `evaluation/OPERATIONAL_RESUME_40034814235_HYPOTHESIS_V1.json`
  (freeze commit `da2fadea2`, committed `2026-10-23T22:54:29Z`, **before** the
  claim-bearing execution which began `22:54:34Z` — a 5-second margin, stated
  here rather than glossed)
- **Diagnosis record**: `results/evaluation/orchestration/40034814235_failure_chain_diagnosis.json`
- **Verification record**: `results/evaluation/orchestration/40034814235_verification_of_repair_40017649220_r1.json`

## 1. What was resumed, and why the chain died

The work on the snapshot is **repair round 1 of audit gate REVISE
`CYCLE_40017649220`** (required fixes F1/F2/F3). Producer run `40023576675`
completed that discharge and committed it (`b9870cb9` at 21:43:52Z, plus
`b8d526bc` at 21:46:42Z from leftover working tree, committed by the workflow
snapshot step), then died **~2 seconds after its last commit** with
`rc=78 LEX_WORK_QUANTUM_EXPIRED` (2700 s quantum). Because the team job failed,
the audit job was skipped and the repair was never audited.

Five subsequent operational resumes then died **zero-delta** (`rc=67
LEX_ZERO_DELTA_REPAIR`), each pushing a byte-identical snapshot:

| run | dispatched | died | cause |
|---|---|---|---|
| `40023576675` | 21:00:42Z | 21:46:40Z | rc-78 quantum, **after** committing the repair |
| `40029231841` | 21:46:56Z | 21:49:18Z | rc-67; final tool call requested `external_directory` (`/home/runner/work/_temp/_github_workflow/*`) — auto-rejected |
| `40029524205` | 21:49:32Z | 22:24:24Z | rc-67 after a ~28-minute read-only session (even drafted a diagnosis in transcript; never wrote a file) |
| `40033424089` | 22:24:39Z | 22:26:15Z | rc-67; final tool call requested `external_directory` (`/home/runner/*`) — auto-rejected |
| `40033628306` | 22:26:30Z | 22:34:40Z | rc-67 after reading the full control plane/repo; nothing written |
| `40034534808` | 22:34:55Z | 22:37:18Z | rc-67; token-probe tool call under `/home/runner/work/_temp/*` auto-rejected (`permission requested: external_directory …; auto-rejecting` at 22:37:06Z) |
| **`40034814235`** | 22:37:31Z | in flight | this run |

**Work-loss assessment: ZERO.** All six failed runs' team snapshot branches
were fetched and compared: every tip is byte-identical at
`b8d526bc12cf3b5384524b31036d01d20e27bb21`. The five resume producers wrote no
file at all. The repair work of `40023576675` is fully preserved.

**Diagnosis class**: ORCHESTRATION, not evidence. `rc-78` is the 2700 s
work-quantum guard and `rc-67` is the zero-delta guard meaning "the producer
found nothing to do" — factory-wide requirements 10/12 record that neither is a
product, evidence or human-gate problem. A recurring anti-pattern is recorded
for the control plane: 3 of 6 producers burned their only session on
auto-rejected token probes under `/home/runner/work/_temp`. Lane producers never
need a GitHub token; `.github/**` is control-plane scope and is not edited here.

## 2. Verification of the F1/F2/F3 discharge (independently re-executed)

All three committed test suites were re-executed at this run id under the
committed pytest-free shim (`evaluation/no_pytest_runner.py`
`c12097da…`, pytest absent in this image; `UNSUPPORTED` counted NOT-RUN):

- `test_minimal_ret_ca_benchmark.py` → **SHIM_PASS 4 / 0 / 0, 1 UNSUPPORTED**
  (`results/evaluation/orchestration/40034814235_minimal_ret_ca_pytest_shim.json`)
- multilingual + provenance reuse set (`test_stand_ready_multilingual_probe`,
  `test_f3b_restore_disposition`, `test_v59_stand_ready_verification`,
  `test_packet_of_record_stand_ready`) → **SHIM_PASS 73 / 0 / 0 / 0**
  (`…40034814235_multiling_prov_pytest_shim.json`)
- the repair's own suite `test_repair_40017649220_r1.py` → **SHIM_PASS 32 / 0 / 0 / 0**
  (`…40034814235_repair_r1_suite_shim.json`)

Every count matches the committed `40017649220` R1 records (F1). All three
suites were re-executed a second time **after** the final state update and
re-passed with identical counts (no state field they read was disturbed).

**F2 (evidence index)**: re-derived — at repair time `evidence_refs_n ==
len(evidence_refs) == 173`; all nine claim-bearing artifacts of run
`40017649220` are indexed and exist on disk; 172/173 refs resolve, the one
unresolvable ref and one duplicated ref are both inherited from before
`40017649220` and disclosed. One truthful correction applied: the
inherited-defect detail text for the duplicated ref (`39875239812_diagnosis.json`)
wrongly said it "does not resolve to a committed file"; it does resolve
(DUPLICATE_ONLY, as its own `kinds` field says). The ref list itself is
unchanged. After this run appended its 14 new artifacts, the index re-derives
at `evidence_refs_n == len(evidence_refs) == 187` and every appended ref
resolves on disk.

**F3 (ordering/provenance record)**: `evaluation/MINIMAL_RET_CA_40017649220_CYCLE_HYPOTHESIS_V1.json`
re-checked — declares `NOT_FREEZE_FIRST` with the true timeline, cites the
inherited frozen spec, and its no-post-hoc-tuning proof re-verified: instrument
`70f8158c…` identical to accepted base `b8265afb`; `v65_eval_40017649220` vs
`verify_v65` equal modulo run id/time; vs `test_run_1` differing only in the
runtime-derived `direction_version` 63→65 note.

## 3. Freeze-first claim-bearing re-executions

- **2-leg minimal retrieval/counter-authority benchmark** (the FAST-MVP
  deliverable) executed at `22:54:34Z–22:54:46Z`, after the freeze commit:
  **exit 0 `BENCHMARK_VALID_NO_FALSIFICATION`**, leg 1 `PASS_NO_REGRESSION`
  (label 65 scored / 5 supported / 0.076923, `LABEL_UNSOUND`; geometry 6/5/5
  incumbents, 0/3 bundles pass all 11), leg 2 `FAIL_REGRESSION` (de+fr
  regressed, negative controls proven). Served bundle sha256 equal the frozen
  pins; the record is **normalized-identical to the measurement of record
  `v65_eval_40017649220`**. Records:
  `results/evaluation/minimal_ret_ca_benchmark/40034814235{,_leg1_served_baseline,_leg2_hostile_geometry}.json`,
  report `reports/evaluation/RETRIEVAL_CA_BENCHMARK_40034814235.md`.
- **Multilingual/provenance reuse instrument** re-executed in a scratch cwd:
  **PARTIAL_MISS 0/3** reproduced with raw output **byte-identical**
  (sha256 `82ae91b5…`) to the committed historical record and the rehome pin.
  Carried as accepted negative, never repaired.
- **Frozen-input integrity after execution**: all ten pinned inputs re-hash
  identical (`RULES_LABEL 4457e971…`, `RULES_GEOMETRY a7452748…`,
  `VERDICT_CONTRACT b9cdb894…`, `run_bar_gates 41b83842…`,
  `label_gate 640abd8b…`, `geometry_gate 934d5cca…`, instrument `70f8158c…`,
  tests `49c94f7b…`/`01024e9d…`, shim `c12097da…`). Zero frozen files edited;
  zero historical records overwritten; no obsolete universal-174k benchmark run.

## 3b. Committed guard test for this cycle

`tests/evaluation/test_operational_resume_40034814235.py` (15 no-parameter
tests, shim-compatible) locks this run's claims to its committed artifacts:
freeze-record ordering + pin re-hash, the six-failure diagnosis chain
(rc-78 × 1, rc-67 × 5, "ZERO WORK LOST"), benchmark verdict/legs/pins and
normalized identity with `v65_eval_40017649220`, the three shim-suite count
agreements with the R1 records, the multilingual byte-identity pin, frozen-input
re-hash, state run identity + posture-false flags, evidence-index coverage of
this run's artifacts, repair-discharge pointers, and the corrected defect
detail. Executed after the final state update: **SHIM_PASS 15 / 0 / 0 / 0**
(`results/evaluation/orchestration/40034814235_self_suite_shim.json`).

## 4. Claim ceiling and posture (unchanged)

This cycle establishes only that (a) the un-audited F1/F2/F3 repair discharge
holds at the operational-resume head under independent re-execution, and (b) the
frozen 2-leg benchmark still executes with the same verdict on the pinned served
packet `38839347028` inputs. It does **not** meet the absolute LABEL (1.0) or
all-11 GEOMETRY bars — both stay REPORTED-ONLY and unmet; the comparative
map-vs-ranked-list half stays **VACUOUS** (`n_emitted=0` on all three V3
questions; the `PRODUCT_FALSIFIED` counter-authority gap carries forward); both
**DO-NOT-SERVE orders stand**; packet admission stays fail-closed;
`human_gate_ready=false`, `machine_gate_ready=false`,
`ready_for_owner_session=false`, `owner_decision_required=false`.

## 5. Recommendation

**CONTINUE** under the same v65 question (next accepted product head
cross-check; coverage-v2 re-freeze only if the coverage family is resumed).
The independent auditor of run `40034814235` should audit the team tip: the
repair discharge, this run's verification records and the updated state. No
owner decision is required.
