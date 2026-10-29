# AUDIT INTAKE — product run 40783679367

Machine-readable target:

```json
{
 "audit_target_ref": "origin/cycle/core/product/40783679367/team",
 "audit_target_head": "c73d9d848018e56d2d2ec3a5d53f9791688ae376",
 "audit_target_head_source": "team_ref",
 "team_ref_present": true,
 "local_head_at_generation": "c73d9d848018e56d2d2ec3a5d53f9791688ae376",
 "accepted_ref": "origin/lab/product",
 "accepted_head": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83",
 "state_accepted_commit": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83",
 "resumed_run_id": "40772551540",
 "resumed_snapshot_head": null,
 "resumed_diagnosis": "results/product/orchestration/CYCLE_40783679367_resume_diagnosis.json",
 "report_of_record": "reports/product/CYCLE_40783679367.md",
 "resumed_head_is_not_audit_target": true
}
```

AUDIT ROUTE BRIEF — product snapshot for run 40783679367
============================================================
NEXT DISPATCH MUST BE THE INDEPENDENT AUDIT of this snapshot.
The producer side is complete; prior audits of this lineage died
at the 2700 s work quantum without consuming the cheap checks
below.

WORKSPACE CONTRACT (read first)
-------------------------------
The audit job's own CWD is the ACCEPTED BASE checkout (origin/lab/product).
The producer snapshot under audit is mounted at: /tmp/lex_team
Run EVERY command below as: cd /tmp/lex_team && <command>
Relative commands in the accepted-base tree either fail (product/audit_route.py
is absent there) or silently regenerate ANOTHER tree's claims
(product/audit_readiness.py and product/state_contract.py exist on both trees).
First command (the workflow installs no python deps): cd /tmp/lex_team && bash product/bootstrap_query_env.sh
  (pins numpy 2.5.4 / scipy 1.18.1 / scikit-learn 1.9.1 / pytest 9.1.1)

AUDIT TARGET (team ref): origin/cycle/core/product/40783679367/team
AUDIT TARGET HEAD:        c73d9d848018e56d2d2ec3a5d53f9791688ae376 (team ref)
ACCEPTED HEAD:            7be4480ed3ca623b77ea082404ca3b5b7ac5ee83

RUN THIS FIRST (measured cost in parentheses; every command runs
from the producer mount: cd /tmp/lex_team && …):
  0. cd /tmp/lex_team && bash product/bootstrap_query_env.sh                      (~40 s once; no deps otherwise)
  1. cd /tmp/lex_team && python3 product/state_contract.py --check --direction-version 68 --json        (~0.1 s)
  2. cd /tmp/lex_team && python3 product/audit_readiness.py --verify results/product/audit_readiness/CYCLE_40783679367_audit_readiness.json   (~1 s)
  3. cd /tmp/lex_team && python3 product/audit_route.py --run-id 40783679367 --out /tmp/route.json          (full route, ~2-4 min measured)

THEN read, in this order (short files first; all under /tmp/lex_team):
  - reports/product/CYCLE_40783679367.md                     (report of record)
  - results/product/orchestration/CYCLE_40783679367_resume_diagnosis.json
  - the `audit_route` + `next_recommendation` fields of state/product.json

DO NOT re-derive discharged findings (see route artifact do_not_re_derive).
Gate path: results/audit/product/CYCLE_<run_id>_GATE.json (UPPERCASE), written from the audit-job checkout, NOT from /tmp/lex_team.

The vertical slice stays complete and locally runnable; both DO-NOT-SERVE
orders stand; no owner session is staged while either frozen bar is unmet.
COMMITTED MEASUREMENTS (already run by the producer):

- route results/product/audit_readiness/CYCLE_40783679367_AUDIT_ROUTE.json: status=PASS total=98.777s budget_fraction=0.0366 failed_steps=[]
- route workspace: mount=/tmp/lex_team root_is_producer_mount=False instrument_root=/home/runner/work/LexMachina/LexMachina (generated on the producer's CI checkout; a rerun from cd /tmp/lex_team && … reports root_is_producer_mount=True)
- dossier results/product/audit_readiness/CYCLE_40783679367_audit_readiness.json: status=PASS n_checked=9 failed_checks=[] skipped_checks=[]
