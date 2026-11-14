# Operational Resume — Evaluation Lane, Run 43542378874

**Run:** 43542378874 (direction v68, FAST MVP MODE, operational resume of 43542234373)
**Snapshot base:** `refs/heads/cycle/core/evaluation/43542234373/team` = `8c07cacab54e12a008cf50f207898154d43f5926`
(identical to `cycle/core/evaluation/43531218191/team` — empty durable delta from the resumed run)
**Claim ceiling:** verification, diagnosis and durable persistence of already-produced work.
No product number is re-scored, no frozen bar/rubric/threshold is touched and no
claim-bearing original is rewritten. This document is **producer-authored; it is
not an independent audit**.

## 1. Why the resumed run issued no verdict

Run 43542234373 ("Core evaluation dirV68 repair0", workflow_dispatch, head
`602f671f`) failed at workflow step `Run lane cycle` after **77 seconds** with
the single failure annotation `Process completed with exit code 1.` and **NO
retryable `LEX_*` annotation**. Failure class:
**`ORCHESTRATION_AGENT_LAUNCH_FAILURE_EXIT_1_NO_RETRYABLE_SIGNATURE`** — the
same recorded class as run 43404561250.

Mechanism (from `.github/scripts/run-ox-with-retry.sh`, control plane, read-only):
when the agent process exits non-zero and the log contains neither an
auth signature (`AUTH_RE`) nor a network signature (`NETWORK_RE`), the wrapper
prints `OpenCode failed without transient/auth signature (rc=$rc)` and exits
with that raw code **without retrying**. Exit 1 therefore is not a product,
evidence, validation or human-gate problem (factory-wide requirement 20 class);
the agent-side cause cannot be read because job logs are HTTP 403 without an
admin token — disclosed as inference from run metadata + job steps + check-run
annotations only.

Steps that succeeded: checkout, lane init, peer mount, Ox install, clean
generated junk, persist team snapshot, complete job.
Steps that failed: `Run lane cycle`.
Steps skipped: `Validate active MVP producer state`, `Enforce lane write scope`.
Jobs: team=failure, resilience=success, audit=skipped, integrate=skipped.
No audit ref `cycle/core/evaluation/43542234373/audit` exists.
Durable delta: **empty** — team, team-attempt-1 and base 43531218191 all hash
to `8c07caca`.

Evidence (committed under
`results/evaluation/operational_resume_43542378874/api/`):
`run_43542234373.json`, `jobs_43542234373.json`,
`annotations_43542234373_team.json`.
Reproduction record:
`results/evaluation/operational_resume_43542378874/diagnosis_43542234373.json`
(14/14 checks, all hold).

## 2. Chain root cause (H2) — audit-side starvation plus resume failures

All recomputed from the committed public job/annotation captures:

| Run | Team | Audit | Failure class | Delta |
|-----|------|-------|---------------|-------|
| **43531218191** (producer) | SUCCESS end-to-end (lane cycle, state validation, write scope) | **FAILURE** after 2749s at `Independent audit`: `LEX_WORK_QUANTUM_EXPIRED seconds=2700` / exit **78** | audit-side quantum starvation | committed `8c07caca` with the FAST-MVP deliverable |
| **43541879339** (resume 1) | FAILURE | skipped | `ORCHESTRATION_ZERO_DELTA_REPAIR` / exit **67** (correctly empty delta — deliverable already committed) | empty |
| **43542234373** (resume 2) | FAILURE | skipped | `ORCHESTRATION_AGENT_LAUNCH_FAILURE_EXIT_1_NO_RETRYABLE_SIGNATURE` / exit **1** | empty |
| **43542378874** (this run) | in progress | pending | OPERATIONAL RESUME of the above | this report's delta |

No audit ref exists for any of the three; no gate file exists for any of the
three. Root cause string of record:
`AUDIT_SIDE_STARVATION_PLUS_RESUME_FAILURE_LOOP` — the snapshot's completed,
validation-passing deliverable has **never received an independent audit
verdict**, and every resume that adds no delta re-fails the same way.

This instrument breaks the loop by producing a real, in-scope delta
(diagnosis, verification, ordered-work re-adjudication, audit-readiness) so the
team job can pass and the independent audit can finally run on the snapshot
that already carries the deliverable.

Record: `results/evaluation/operational_resume_43542378874/diagnosis_chain_43542378874.json`
(15/15 checks, all hold).

## 3. The snapshot's FAST-MVP deliverable is verified (H3), not re-claimed

- Snapshot verification record
  `results/evaluation/minimal_ca_falsify_benchmark/43531218191.json`
  (sha256 `ab187272ff3eb4f6eda65614462b31dd5ef1d3181a81dc38aae4bfe923c17edd`):
  verdict **PRODUCT_FALSIFIED**, exit 1, 18 gates = 11 passed / 4 failed /
  3 reported, product mount head `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83`,
  direction_version 68, `input_drift=[]`, `run_valid=true`.
- Claim-bearing chain record
  `results/evaluation/minimal_ca_falsify_benchmark/43397701490.json`
  (sha256 `461c3b0499aafdd86afb472e8bcb7799c7f64fd91f46ef0d7c6f1587d5598cad`)
  intact and still PRODUCT_FALSIFIED — **not rewritten**.
- Twin comparison 43531218191 vs 43397701490: 48 fields compared, differing
  fields are exactly `{run_id, engine_record_path, generated_at_utc}`
  (the disclosed volatile set); **zero** differences outside volatile fields.
- All 10 frozen pins in
  `evaluation/OPERATIONAL_RESUME_43542378874_FREEZE_V1.json`
  re-hash byte-identically (freeze sha256 `7bc05a47952a0564219a0983d7308bd8ce2f405066b6f69e3b35ff5e45a83366`).
- Fresh out-of-tree scratch replay of
  `python3 -m evaluation.minimal_ca_falsify_benchmark` reproduces every
  measurement-bearing field (only `{run_id, engine_record_path,
  generated_at_utc}` differ); exit 1 as expected for a falsifying instrument.
- Report of the verification record:
  `reports/evaluation/RETRIEVAL_CA_BENCHMARK_43531218191.md`
  (sha256 `a9ae734d0a1cc8e3d0cdba20a7905251c2323acb8bdcd2cebe0efb1701e019c0`).

**This is OPERATIONAL verification of an already-frozen instrument, not new
evidence.** `43397701490` remains the claim-bearing FAST-MVP record of the
chain. Record:
`results/evaluation/operational_resume_43542378874/deliverable_verification_43542378874.json`
(12/12 checks, all hold).

## 4. Ordered items (v68) and standing orders (H4)

- **Item (1)** — PRESENT_AND_VERIFIED.
  `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md`
  sha256 `b10eeb3a720cd6352fbc7eabbf8d3430989b52d90193d0f948e69908ef5dc48d`
  re-checked unchanged; falsifier NOT re-run for it.
- **Item (2)** — NOT_YET_DISCRIMINATING.
  `lab/product` and the accepted product mount are both unchanged at
  `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83`.
  Family gate
  `results/evaluation/v68_item2_family_gate/43542378874.json`:
  member-for-member ceiling **14/15** (server/served current 3 < frozen
  required 4; offline/rent-default current 18 vs frozen 11), role parity
  false, zero-delta against the family already measured by accepted run
  40258497460. No conditional re-measure executed; no synthetic stand-in;
  packet-of-record 39319405429 not scored; standing falsification not re-run.
  The rejection/incumbent leg IS landed in product code at this head
  (`product/query/counter_evidence_span.py`), but the named 15-member family
  has not been regenerated, so the direction's precondition is unmet.
- **Item (3)** — STANDING RECORD UNTOUCHED.
  Benchmark of record: mapping-free falsifier PRODUCT_FALSIFIED on
  packet-of-record 39319405429. Standing freeze pin
  `evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD_V1.json` =
  `ff466aa8ff16d5767c498587a6755103ed212088876f1aa43f2d04120e29e9fe`
  unchanged. Not re-run as a new claim.
- **Item (4)** — REPORT_ONLY_WHERE_QUOTED. The three non-blocking required
  fixes of `CYCLE_39965089504_GATE.json` are reported only where this lane
  quotes those counts; not quoted in this cycle's measurements.
- **Item (5)** — HONOURED. This cycle is OPERATIONAL, not a new same-question
  measurement. No universal-174k benchmark was rerun.

## 5. Freeze-first provenance

- Hypothesis frozen before execution:
  `evaluation/OPERATIONAL_RESUME_43542378874_HYPOTHESIS_V1.json`
  (sha256 `6fedc2642161096e3dc68b960d69d4d1e2e3a47dc96a57c036c0d2b1f1758dd0`),
  5 hypotheses H1–H5.
- Freeze record with input pins:
  `evaluation/OPERATIONAL_RESUME_43542378874_FREEZE_V1.json`
  (sha256 `7bc05a47952a0564219a0983d7308bd8ce2f405066b6f69e3b35ff5e45a83366`).
- Instrument:
  `evaluation/operational_resume_43542378874.py`
  (sha256 `6d3a5433c8e99922461916ca6a37f650bcf882a6d5593bbe83472d6e34ee3177`).
- Prepare-phase summary:
  `results/evaluation/operational_resume_43542378874/prepare_43542378874.json`
  — H1–H4 all hold, `hypotheses_failed=[]`.

## 6. Audit-readiness (H5) and claim limits

- State integrity: `python -m evaluation.state_integrity_gate` — expected
  ALL_CHECKS_PASS 11/11 after this cycle's additive state update
  (record written by the final phase).
- Nested evidence refs: `python -m evaluation.nested_evidence_refs_guard` —
  expected NESTED_REFS_RESOLVED with 0 unresolved.
- Write scope: live + delta `SCOPE_CLEAN`, **zero** paths in the independent
  auditor's namespace (`results/audit/evaluation/**`,
  `reports/audit/evaluation/**`). This lane does not write the auditor
  namespace.
- Lane suite: `python -m evaluation.lane_suite` — expected PASS with the
  standing pytest-absent skip disclosed.
- Both state files agree on `accepted_run_id=40265377500`,
  `direction_version=68`, `github_run=43542378874`; this run is disclosed
  `audit_status=PENDING_INDEPENDENT_AUDIT`, `accepted_as_evidence=false`.
- Posture: `human_gate_ready=false`, `machine_gate_ready=false`,
  `ready_for_owner_session=false`, `owner_decision_required=false`.
  Both DO-NOT-SERVE orders stand. Admission fail-closed.
  The comparative map-versus-ranked-list half is NOT scored.

**continue_recommended=false**: no same-question cycle is justified until Core
Product lands the rejection/incumbent leg **and** regenerates the full flagship
family (then item (2)'s conditional re-measure becomes discriminating).
Control-plane items recorded, not edited: `.github/**` remains control-plane
scope; the audit job's 2700s quantum and the non-retry exit-1 path are the
orchestration defects this lane works around, not patches.

## 7. Files in this cycle's delta (in-scope only)

- `evaluation/OPERATIONAL_RESUME_43542378874_{HYPOTHESIS,FREEZE}_V1.json`
- `evaluation/operational_resume_43542378874.py`
- `results/evaluation/operational_resume_43542378874/**` (api captures,
  diagnosis, verification, ordered work, prepare/summary, audit-readiness)
- `results/evaluation/v68_item2_family_gate/43542378874.json`
- `reports/evaluation/OPERATIONAL_RESUME_43542378874_AUDIT_READY.md`
- `tests/evaluation/test_operational_resume_43542378874.py`
- additive updates to `state/evaluation.json` and `evaluation/state/evaluation.json`

Independent audit of run 43542378874 has **not** yet happened; this document is
producer-authored. Snapshot is audit-ready pending that independent audit.
