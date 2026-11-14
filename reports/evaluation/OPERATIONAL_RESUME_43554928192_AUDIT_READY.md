# Operational Resume — Snapshot 43554928192 (direction v68, run 43559166421)

- **Lane**: evaluation
- **Mode**: OPERATIONAL_RESUME (not a new product cycle)
- **Resumed snapshot**: run `43554928192`, branch `cycle/core/evaluation/43554928192/team`, head `35d8d64941b76ab59f931915f1f59ac97e07041f`
- **Current run**: `43559166421`
- **Direction version**: 68
- **Accepted run id (unchanged)**: `40265377500`
- **Status**: `PENDING_INDEPENDENT_AUDIT` / `accepted_as_evidence=false`
- **Producer-authored, not an independent audit**

## 1. What actually failed

Run `43554928192` did **not** fail in the producer. Its `team` job succeeded end
to end — `Run lane cycle`, `Validate active MVP producer state`, `Clean
generated junk`, `Enforce lane write scope` and `Persist team snapshot` all
report `success` — and it committed a real five-file delta (below). Its
`audit` job then failed only at `Independent audit` after **2750 s** with:

- `LEX_WORK_QUANTUM_EXPIRED seconds=2700`
- `Agent quantum ended cleanly; workflow must snapshot and resume rather than hang.`
- `Process completed with exit code 78.`

`Enforce audit scope and read gate` and `Persist audit snapshot` were
`skipped`, `integrate` was `skipped`, the `resilience` job succeeded, and no
`cycle/core/evaluation/43554928192/audit` ref exists. The snapshot therefore
never received an audit verdict.

**Failure class**: `ORCHESTRATION_AUDIT_WORK_QUANTUM_EXPIRED`. This is an
orchestration/audit-starvation defect, not a producer, validation, gate or
product failure.

Job logs are HTTP 403 without an admin token. Every claim above is recomputed
from the public check-run annotations and job metadata captured under
`results/evaluation/operational_resume_43554928192/api/` plus `git ls-remote`.

The only network access in this resume is unauthenticated public GitHub Actions
metadata (runs, jobs and check-run annotations) for the six runs in the chain;
it is disclosed in state as `network_calls_this_resume_43559166421`. No
OpenCaseLaw, retrieval, model, product or benchmark network call was made.

## 2. The recurrence

The same audit work-quantum expiry consumed four consecutive producer
snapshots. Each `team` job succeeded; each `audit` job died at ~2700 s with exit
78 before it could write a gate:

| Run | Team | Audit | Audit duration | Audit ref | Gate file |
|---|---|---|---|---|---|
| `43531218191` | success | failure | 2749 s | absent | absent |
| `43542378874` | success | failure | 2754 s | absent | absent |
| `43550420112` | success | failure | 2749 s | absent | absent |
| `43554928192` | success | failure | 2750 s | absent | absent |

The two intervening resumes added no durable delta: `43541879339` correctly hit
`LEX_ZERO_DELTA_REPAIR` / exit 67, and `43542234373` died at `Run lane cycle`
with exit 1 and no retryable `LEX_*` signature. The loop is audit-side, not
producer- or product-side.

## 3. The preserved producer delta

`git diff --name-status d835bad4..35d8d649` is exactly five files, all present
and byte-identical to the committed snapshot:

| Status | Path |
|---|---|
| M | `evaluation/smallest_ca_benchmark.py` |
| A | `reports/evaluation/SMALLEST_CA_BENCHMARK_43554928192.md` |
| A | `reports/evaluation/SMALLEST_CA_BENCHMARK_test_run_43554928192.md` |
| A | `results/evaluation/smallest_ca_benchmark/43554928192.json` |
| A | `results/evaluation/smallest_ca_benchmark/test_run_43554928192.json` |

The machine record is `PRODUCT_FALSIFIED`, exit `1`, on packet `39319405429`,
direction 68, 3 questions, **zero** issued counter-authority rows. The
out-of-tree replay (`results/evaluation/operational_resume_43554928192/scratch/`)
reproduces every measurement-bearing field with zero network calls; only
`run_id`, `generated_at_utc` and `elapsed_s` differ.

**Classification**: `OPERATIONAL_REEXECUTION_NOT_NEW_CLAIM`. The prior run's
smallest-CA re-execution does **not** supersede the standing falsification
record and is not promoted as evidence.

## 4. Ordered v68 work

| Item | Status | Basis |
|---|---|---|
| (1) report-only correction of record | `PRESENT_AND_VERIFIED` | `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md` and `results/evaluation/bypass_clause_correction/40144816305.json` byte-intact |
| (2) conditional re-measure | `NOT_YET_DISCRIMINATING` | full named 15-member family not regenerated (`14/15`, zero-delta); rejection/incumbent leg remains open at the direction's accepted product `8b5b08dd`; no re-measure executed |
| (3) standing falsification record | `STANDING_RECORD_UNTOUCHED` | `43397701490.json` and `43531218191.json` byte-intact; re-execution recorded as operational only |
| (4) report-only fixes | `REPORT_ONLY_WHERE_QUOTED` | no frozen bar, rubric, threshold or verdict contract edited |
| (5) no new same-question cycle | `HONOURED_OPERATIONAL` | this cycle is diagnosis + verification + state hygiene, not a new measurement |

**Mount lag disclosed**: `/tmp/lex_accepted/product` is `7be4480e`, one
accepted cycle behind the direction's accepted product head `8b5b08dd`. The
family gate therefore reads the older mount and still reports
`NOT_YET_DISCRIMINATING` (`member_for_member_ceiling=14/15`, zero-delta). Even
on the newer head, the direction records the rejection/incumbent leg as open,
so no conditional re-measure is justified.

## 5. Audit-readiness (in-lane writes only)

| Check | Result |
|---|---|
| `evaluation.state_integrity_gate` | `ALL_CHECKS_PASS` (11/11) |
| `evaluation.nested_evidence_refs_guard` | `NESTED_REFS_RESOLVED`, 0 unresolved |
| live write scope | `SCOPE_CLEAN`, 0 auditor-namespace paths |
| `evaluation.lane_suite` | exit 0 |
| state parity | both state files agree: `accepted_run_id=40265377500`, `direction_version=68`, `github_run=43559166421` |
| disclosure | `PENDING_INDEPENDENT_AUDIT`, `accepted_as_evidence=false` |

No file under `results/audit/evaluation/**` or `reports/audit/evaluation/**` was
written. No frozen bar, rubric, threshold, predicate or verdict contract was
edited. No universal-174k benchmark was run.

## 6. Negative results preserved

- The smallest-CA record remains `PRODUCT_FALSIFIED`; this resume did not turn
  it into a pass.
- The standing 18-gate falsifier (`43397701490`: 11 pass / 4 fail / 3 reported)
  is unchanged and is still the record of record.
- The v68 item-(2) gate remains `NOT_YET_DISCRIMINATING`; the missing member is
  the fourth `server/served` bundle, and no synthetic stand-in was substituted.
- The mount lag is disclosed rather than repaired from the evaluation lane.

## 7. Recommendation

Do **not** dispatch another same-question evaluation cycle. Item (2) stays
`NOT_YET_DISCRIMINATING` until Product lands the P0 rejection/incumbent leg
**and** regenerates the full named 15-member family. The factory-level blocker
is the audit work quantum: four producer snapshots have now starved at 2700 s /
exit 78. Audit needs a snapshot/resume path or a smaller quantum before any
producer snapshot can be promoted.

## 8. Artifacts

- Hypothesis/freeze: `evaluation/OPERATIONAL_RESUME_43554928192_HYPOTHESIS_V1.json`, `evaluation/OPERATIONAL_RESUME_43554928192_FREEZE_V1.json`
- Instrument: `evaluation/operational_resume_43554928192.py`
- Diagnosis: `results/evaluation/operational_resume_43554928192/diagnosis_43554928192.json`
- Chain: `results/evaluation/operational_resume_43554928192/diagnosis_chain_43559166421.json`
- Verification: `results/evaluation/operational_resume_43554928192/deliverable_verification_43559166421.json`
- Ordered work: `results/evaluation/operational_resume_43554928192/ordered_work_43559166421.json`
- Audit readiness: `results/evaluation/operational_resume_43554928192/audit_readiness_43559166421.json`
- State update: `results/evaluation/operational_resume_43554928192/state_update_43559166421.json`
- API captures: `results/evaluation/operational_resume_43554928192/api/`
- Regression test: `tests/evaluation/test_operational_resume_43554928192.py`
