# Operational resume of evaluation snapshot 39929883261

Run: `39936790420` · lane: evaluation · direction v63 · resume of `39929883261`
Snapshot commit: `5cc6a326cdc77b821f73f7819acb6bd3b3303a1e`
True accepted base: `3eeced9a25d486356870755e48422f8473a5f90c`
Verdict: **RESUME_VERIFIED_AND_AUDIT_READY** (see `results/evaluation/operational_resume/39936790420.json`)

## 1. Why this resume exists

The producer team job for `39929883261` started at `2026-10-23T09:10:09Z` and was
cancelled at `2026-10-23T10:06:51Z` (3402 s) by
`factory-supervisor.yml` → `cancel_stale_agent_jobs` (`STALE_JOB_SECONDS=3300`).
The measured job steps are:

| # | step | result |
|---|---|---|
| 6 | Run lane cycle | **cancelled** |
| 7 | Validate active MVP producer state | **skipped** |
| 9 | Enforce lane write scope | **skipped** |
| 10 | Persist team snapshot | success |

The `audit` and `integrate` jobs were cancelled with zero steps; the `resilience`
job succeeded and dispatched this resume run at `10:07:01Z`. So the snapshot was
persisted without the state-validation and write-scope checks, and without an
audit gate.

## 2. Two defects found on resume

### 2.1 Unaudited promotion of `lab/evaluation`

`refs/heads/lab/evaluation` points at the unaudited snapshot `5cc6a326`. No
`cycle/core/evaluation/39929883261/audit` ref and no
`CYCLE_39929883261_GATE.json` exist. The true audit base is `3eeced9a` (the
snapshot's parent and the accept commit of the PASS gate
`CYCLE_39927760701_GATE.json`). The mechanism that advanced `lab/evaluation` is
not observable from the lane or the REST data and is recorded as a control-plane
defect, not attributed to the evaluation lane.

### 2.2 The accepted product advanced during the producer run

The producer measured product head `ae854b6a` (accept cycle `39909013473`). The
accepted product advanced to `d22f9b63` (accept cycle `39925932945`) at
`2026-10-23T09:46:52Z`, **before** the snapshot commit at `10:01:27Z`. The
snapshot's `continue_recommended=false` and its "no newer accepted product
measurement" statement were therefore false at commit time.

The advance is bounded: the V3 packet-of-record `39319405429` is byte-identical
at the two product heads (`git diff --stat ae854b6a d22f9b63 --
results/product/gate_packet/39319405429/` is empty; the three bundle hashes are
unchanged), and the planner pin is unchanged at
`9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9`. The
falsification evidence is therefore not invalidated, but the standing re-open
duty fired. This resume discharges it with a frozen re-measurement on
`d22f9b63` (R6 below), not by rewriting the historical record.

## 3. Freeze-first and the preserved V1 attempt

The V1 hypothesis, freeze record, diagnosis and REST capture were committed at
`78705894` **before** any claim-bearing execution. The V1 run found two
gate-implementation defects:

* R4 read a top-level wrapper field `packet` that the wrapper does not publish
  (the published field is `packets_measured=[39319405429]`);
* the state already referenced this run's own test file before it was written,
  which made the pre-existing state-ref test red (87/3/6 instead of 88/2/6).

The V1 result (`RESUME_DIVERGENCE`) and all V1 output records are preserved under
`*_attempt1*` names. V2 changes only those two implementation details and
re-freezes before execution; no threshold, bar, rubric, verdict contract or
historical record is changed.

## 4. V2 gates

| gate | result | evidence |
|---|---|---|
| R1 snapshot preserved and in scope | PASS | `5cc6a326` parent `3eeced9a`; exactly the six declared paths; five artifacts re-hash to their frozen pins |
| R2 diagnosis and REST capture structured | PASS | step 6 cancelled, 7/9 skipped, 10 success; audit/integrate cancelled; resilience success; lab and product-advance facts present |
| R3 frozen and accepted pins | PASS | four frozen bars, accepted gate/records/fixtures, product head `d22f9b63`, planner `9764a37e`, three V3 bundle hashes |
| R4 lineage byte identity | PASS | wrapper 583/583 leaves, engine 558/558, **0 non-identity diffs**; 4 failed gates, input drift empty, non-vacuity 4/4 |
| R5 shim + inherited red | PASS | 88 passed / 2 failed / 6 unsupported; same per-file/per-case shape as the snapshot record; the same 1+7 failing cases are red at a detached `3eeced9a` worktree |
| R6 product-advance re-open | PASS | unchanged packet bytes; frozen re-measurement on `d22f9b63` = `PRODUCT_FALSIFIED`, 11/18 passed, same four failed gates, no drift, non-vacuity 4/4 |
| R7 state and refs | PASS | direction 63; `github_run`/`proposed_run_id` `39936790420`; accepted `39927760701`; all flags false; 125 refs resolve |

Controls C1–C5 (planted frozen-pin drift, lineage drift, wrong run id, diagnosis
violation, state-ref break) all detect their planted drift.

## 5. What changed in the lane state

* `github_run` and `proposed_run_id` advanced to `39936790420`;
  `accepted_run_id` stays `39927760701`;
  `acceptance_status` stays `PROPOSED_PENDING_INDEPENDENT_AUDIT`.
* `continue_recommended` is now `true`, with the product-advance reason. The
  previous `false` was based on the pre-advance product head.
* `minimal_retrieval_ca_benchmark` now records the frozen re-open measurement
  (`39936790420`, product head `d22f9b63`); the `39929883261` block is preserved
  verbatim under `previous_measurement_39929883261`.
* `product_advance_after_snapshot_measurement` discloses the advance, the
  unchanged packet bytes and the unchanged planner pin.
* `operational_resume_39936790420` records the diagnosis, the lab anomaly and the
  freeze-first provenance.
* `benchmark_result` now carries a legacy-alias note pointing to the
  authoritative minimal-retrieval block; its historical fields are not rewritten.

## 6. Claim ceiling

This resume proves preservation, reproducibility, pin integrity, inherited-red
isolation, the product-advance re-open measurement and state reconciliation. It
does not move any bar, does not certify admission, does not lift either
DO-NOT-SERVE order and does not claim jurist usefulness. All admission/human
flags stay false. No universal-174k benchmark was run.

## 7. Reproduction prerequisites (important for the independent audit)

The checkpoint is at `5cc6a326`; the audit job checks out `main` at `fetch-depth: 1`
and then fetches `lab/evaluation` and the team branch. That produces a shallow
repository. The two history tests in
`tests/evaluation/test_minimal_retrieval_ca_benchmark.py`
(`test_freeze_first_ordering_on_the_historical_claim_bearing_record` and
`test_state_freeze_commit_is_where_the_hypothesis_landed`) need the commits that
first added the historical claim-bearing record and the frozen hypothesis.
Without history they fail spuriously with messages of the form
`historical record was added by '5cc6a326', expected b1015e7b`.

This resume hit that exact environment failure on its first shim attempt
(86 passed / 3 failed / 6 unsupported). After deepening, the shim reproduced the
snapshot's exact 88 / 2 / 6. The audit should run, before the shim:

```bash
git fetch --deepen=600 origin lab/evaluation
# or: git fetch --unshallow origin
python3 evaluation/no_pytest_runner.py --run-id <audit-run> --repo-root . \
  --test-file tests/evaluation/test_minimal_retrieval_ca_benchmark.py \
  --test-file tests/evaluation/test_mapping_free_recall_falsifier.py \
  --test-file tests/evaluation/test_stand_ready_multilingual_probe.py \
  --test-file tests/evaluation/test_mount_provenance_gate.py \
  --test-file tests/evaluation/test_repair_39338699604_provenance.py \
  --out <scratch>/shim.json
```

The remaining 2 failed files (1 + 7 cases) are red at the true accepted base
`3eeced9a` and are documented case-by-case in
`results/evaluation/orchestration/39936790420_inherited_red_3eeced9a.json`.
They are not caused by the snapshot. The audit must not attribute them to this
resume, and must not treat the shallow-checkout failures as new evidence.
