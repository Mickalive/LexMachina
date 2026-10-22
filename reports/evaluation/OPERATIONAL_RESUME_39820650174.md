# Operational resume and audit readiness — run 39820650174

- Lane: evaluation; direction v62
- Run of record: `39820650174` (GitHub team job `119970760382`)
- Resumed snapshot: `39820233238` (team job `119969302346`)
- Producer snapshot: `39813664201` (team job `119946362236`)
- Snapshot ref: `c87a33bcfc5cfd81fdbfb1c2b2f540e8a1c65ad3` (both)
- Verdict: **RESUME_VERIFIED_AND_AUDIT_READY** (exit 0)
- Evidence tier: EXPLORATORY; all admission/human flags remain false
- Result: `results/evaluation/operational_resume/39820650174_v2.json`, sha256 `36b39458cb6b1b2fa5c583a085562a5f40a549b614b250ada07e23b3a1121c4d`
- Frozen before execution: `evaluation/OPERATIONAL_RESUME_39820650174_HYPOTHESIS_V2.json` (`a1ce5d30...`), `evaluation/OPERATIONAL_RESUME_39820650174_FREEZE_V2.json`, `evaluation/operational_resume_verification_v2.py` (`ae33fc9e...`), committed at `bd2c75e9` (17:33:03Z)

## What happened to the two failed workflows

**Producer `39813664201`.** The team job ran 2700 s and the runner ended the agent quantum cleanly (`LEX_WORK_QUANTUM_EXPIRED seconds=2700 pid=2302`), then the workflow exited 78 and the snapshot step ran. Commits `a6f1ae0a`, `e421365f`, `cc30b1c4`, `c87a33bc` were pushed. Audit, integrate and state validation were skipped. This was a quantum boundary, not a lane verdict.

**Resume `39820233238`.** The snapshot was pushed byte-identically to `c87a33bc`. Because the evaluation lane sets `LEX_REQUIRE_DELTA=1`, `.github/scripts/run-ox-with-retry.sh:216` exited 67 (`LEX_ZERO_DELTA_REPAIR`) when the head did not move. A pure-verification resume therefore cannot pass under the current guard.

**Current run `39820650174`.** Head `4fe03f1d`; this cycle's job is the repair and audit-readiness pass.

Raw job logs are not readable without repository admin rights. The diagnosis above uses public run/job/annotation/step metadata, pinned at `results/evaluation/operational_resume/39820650174_job_evidence.json`.

## Producer work verified (no re-run)

| Evidence | Verdict | sha256 |
|---|---|---|
| `results/evaluation/shipped_planner_remedy_verification/39813664201.json` | `SHIPPED_PLANNER_MATCHES_VERIFIED_REMEDY` (exit 0) | `1f8a6675...` |
| `results/evaluation/coverage_remediation_crosscheck/39813664201.json` | `COVERAGE_EVIDENCE_REPRODUCES` (exit 0) | `03eba8ed...` |
| `..._fresh_offline_replay.json` | fresh replay | `f425bb3f...` |

Coverage unions recompute independently: 23 live, 16 offline, 23 fresh — no reach loss. The shipped planner hash at the producer and at the accepted mount is `9764a37e...`.

## State reconciliation

The lane's state files were stale relative to the newest in-tree audited gate (`results/audit/evaluation/CYCLE_39806933576_GATE.json`, PASS; `400-ft` = `39806933576`). Both files are now identical: `accepted_run_id=39806933576`, `github_run=39820650174`, `direction_version=62`, `cycle_status=COMPLETE`, `evidence_tier=EXPLORATORY`, and all admission/human flags false. `evaluation/state_integrity_gate.py` returned `ALL_CHECKS_PASS`.

## Resume V1 and why V2 exists

V1 was frozen at 17:26:04Z and executed at 17:31:46Z. It returned `RESUME_DIVERGENCE` (exit 1). Only R5 failed:

- the shipped planner hash did match exactly (`9764a37e...`);
- the accepted mount is a **shallow single-commit clone**, so producer head `44330212` is absent locally;
- `git merge-base --is-ancestor` returned 128 (bad object), and V1 collapsed "unmeasurable" to False.

V1 is preserved verbatim (`55ffdba8...`, verdict `RESUME_DIVERGENCE`, exit 1) and is re-hashed by control C6. The public compare API (`44330212...fe219a19`) shows `status=ahead`, `ahead_by=5`, `behind_by=0`, `merge_base_commit=44330212...`. That response is pinned as a committed input (`8a89e43a...`), so V2 executes with zero network.

V2 distinguishes three ancestry states:

| State | Meaning | R5 |
|---|---|---|
| `MEASURED_ANCESTOR` | object present locally; merge-base says ancestor | pass |
| `MEASURED_NOT_ANCESTOR` | object present locally; says not ancestor | fail (evidence cannot override) |
| `NOT_MEASURABLE_SHALLOW_MOUNT` | object absent; pinned evidence required | pass only if evidence attests base/merge_base == producer head, head == mount head, `behind_by == 0`, `status in {ahead, identical}` |

Absent or unreadable evidence is exit 2, not a product verdict.

## V2 gates and controls

Observed ancestry state: `NOT_MEASURABLE_SHALLOW_MOUNT`; source `pinned_github_compare`; planner match true.

| Gate | Result |
|---|---|
| R1 snapshot identity and scope | pass |
| R2 freeze pins hold | pass |
| R3 recorded results internally consistent | pass |
| R4 coverage unions recompute without reach loss | pass |
| R5 shipped planner unchanged at current mount | pass |
| R6 state reconciled and resolvable | pass |

| Control | Result |
|---|---|
| C1 planted pin drift detected | holds |
| C2 planted reach loss detected | holds |
| C3 planted planner mismatch detected | holds |
| C4 wrong run id is exit 2 | holds |
| C5 planted non-ancestor evidence fails R5 | holds |
| C6 V1 result preserved verbatim | holds |

## Provenance and limits

- The producer freeze records carry internal `frozen_at_utc` values (`17:35:00Z`, `17:38:00Z`) that postdate their commits (`16:58:38Z`). Freeze-first ordering is established by git commit order and the results' `generated_at_utc`; the discrepancy is disclosed and the records were not edited.
- The DDC V2 freeze's first committed timestamp (`17:29:00Z`) postdated its commit (`17:28:45Z`); it was corrected to `17:28:40Z` in `ac1d9f96` before execution, with gates and pins unchanged.
- The accepted mount is shallow, so ancestry is established from public compare evidence, not local git. A later non-shallow mount would re-measure it directly.
- Claim ceiling: this verifies that the producer snapshot's completed v62 ordered-item-(1)/(2) work is in-scope, pin-clean, internally reproducible from committed artifacts, and that the planner it verified is still the shipped planner at the current mount. It is **not** a new counter-authority, retrieval, label, geometry, live-answer or serve measurement; it does not move either frozen bar (both remain REPORTED-ONLY/unmet on the v3 bytes), lifts no DO-NOT-SERVE order, and keeps every admission/human flag false.

## Next

The snapshot is audit-ready and the lane state is reconciled. The next substantive cycle should spend its delta on the product's critical path (query-specific counter-authority retrieval and the visual map), not on another resume/verification-only pass. A pure-verification resume needs the `LEX_REQUIRE_DELTA` guard resolved separately; it is an orchestration constraint, not an evaluation finding.
