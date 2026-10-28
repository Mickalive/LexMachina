# AUDIT INTAKE — product run 40763434744

Machine-readable target:

```json
{
 "audit_target_ref": "origin/cycle/core/product/40763434744/team",
 "audit_target_head": null,
 "audit_target_head_source": "unpublished_at_intake_generation",
 "team_ref_present": false,
 "local_head_at_generation": "85dfea227c77bc7ac3e91ae452c067ae18ad5c73",
 "accepted_ref": "origin/lab/product",
 "accepted_head": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83",
 "state_accepted_commit": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83",
 "resumed_run_id": "40750177292",
 "resumed_snapshot_head": "85dfea227c77bc7ac3e91ae452c067ae18ad5c73",
 "resumed_diagnosis": "results/product/orchestration/CYCLE_40750177292_resume_diagnosis.json",
 "report_of_record": "reports/product/CYCLE_40763434744.md",
 "resumed_head_is_not_audit_target": true
}
```

AUDIT ROUTE BRIEF — product snapshot for run 40763434744
============================================================
NEXT DISPATCH MUST BE THE INDEPENDENT AUDIT of this snapshot.
The producer side is complete; prior audits of this lineage died
at the 2700 s work quantum without consuming the cheap checks
below.

AUDIT TARGET (team ref): origin/cycle/core/product/40763434744/team
AUDIT TARGET HEAD:        NOT PUBLISHED YET in this checkout.
LOCAL HEAD AT GENERATION: 85dfea227c77bc7ac3e91ae452c067ae18ad5c73
Resolve the pushed team ref in the audit checkout:
  git rev-parse origin/cycle/core/product/40763434744/team
ACCEPTED HEAD:            7be4480ed3ca623b77ea082404ca3b5b7ac5ee83
RESUMED PREDECESSOR:      40750177292 at 85dfea227c77bc7ac3e91ae452c067ae18ad5c73
DO NOT audit the resumed predecessor head: a producer resume
commits its own delta on top of it.

RUN THIS FIRST (measured cost in parentheses):
  1. python3 product/state_contract.py --check --direction-version 68 --json        (~0.1 s)
  2. python3 product/audit_readiness.py --verify results/product/audit_readiness/CYCLE_40763434744_audit_readiness.json   (~1 s)
  3. python3 product/audit_route.py --run-id 40763434744 --out /tmp/route.json          (full route, ~2-4 min measured)

THEN read, in this order (short files first):
  - reports/product/CYCLE_40763434744.md                     (report of record)
  - results/product/orchestration/CYCLE_40750177292_resume_diagnosis.json
  - the `audit_route` + `next_recommendation` fields of state/product.json

DO NOT re-derive discharged findings (see route artifact do_not_re_derive).
Gate path: results/audit/product/CYCLE_<run_id>_GATE.json (UPPERCASE).

The vertical slice stays complete and locally runnable; both DO-NOT-SERVE
orders stand; no owner session is staged while either frozen bar is unmet.
