# AUDIT INTAKE — product run 40863791646

Machine-readable target:

```json
{
 "audit_target_ref": "origin/cycle/core/product/40863791646/team",
 "audit_target_head": null,
 "audit_target_head_source": "unpublished_at_intake_generation",
 "team_ref_present": false,
 "local_head_at_generation": "0023cfa9fe5c3fa45049edb48c8dae28a30c3b3b",
 "accepted_ref": "origin/lab/product",
 "accepted_head": null,
 "state_accepted_commit": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83",
 "resumed_run_id": "40858799166",
 "resumed_snapshot_head": "0023cfa9fe5c3fa45049edb48c8dae28a30c3b3b",
 "resumed_diagnosis": "results/product/orchestration/CYCLE_40858799166_resume_diagnosis.json",
 "report_of_record": "reports/product/CYCLE_40863791646.md",
 "cycle_block_key": "cycle_40863791646_operational_resume",
 "cycle_block_present": true,
 "self_label_status": "ALIGNED",
 "artifact_paths": {
  "report": "reports/product/CYCLE_40863791646.md",
  "diagnosis": "results/product/orchestration/CYCLE_40858799166_resume_diagnosis.json",
  "dossier": "results/product/audit_readiness/CYCLE_40863791646_audit_readiness.json",
  "route": "results/product/audit_readiness/CYCLE_40863791646_AUDIT_ROUTE.json",
  "intake": "results/product/audit_readiness/CYCLE_40863791646_AUDIT_INTAKE.md"
 },
 "artifact_present": {
  "report": true,
  "diagnosis": true,
  "dossier": true,
  "route": true,
  "intake": true
 },
 "missing_artifacts": [],
 "self_label_verdict": "ALIGNED: the snapshot's committed state block and the run-id-named report/diagnosis/dossier/route/intake all resolve",
 "resumed_head_is_not_audit_target": true
}
```

AUDIT ROUTE BRIEF — product snapshot for run 40863791646
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

AUDIT TARGET (team ref): origin/cycle/core/product/40863791646/team
AUDIT TARGET HEAD:        NOT PUBLISHED YET in this checkout.
LOCAL HEAD AT GENERATION: 0023cfa9fe5c3fa45049edb48c8dae28a30c3b3b
Resolve the pushed team ref in the audit checkout:
  git rev-parse origin/cycle/core/product/40863791646/team
ACCEPTED HEAD:            None
RESUMED PREDECESSOR:      40858799166 at 0023cfa9fe5c3fa45049edb48c8dae28a30c3b3b
DO NOT audit the resumed predecessor head: a producer resume
commits its own delta on top of it.

RUN THIS FIRST (measured cost in parentheses; every command runs
from the producer mount: cd /tmp/lex_team && …):
  0. cd /tmp/lex_team && bash product/bootstrap_query_env.sh                      (~40 s once; no deps otherwise)
  1. cd /tmp/lex_team && python3 product/state_contract.py --check --direction-version 68 --json        (~0.1 s)
  2. cd /tmp/lex_team && python3 product/audit_readiness.py --verify results/product/audit_readiness/CYCLE_40863791646_audit_readiness.json   (~1 s)
  3. cd /tmp/lex_team && python3 product/audit_route.py --run-id 40863791646 --out /tmp/route.json          (full route, ~2-4 min measured)

THEN read, in this order (short files first; all under /tmp/lex_team; ABSENT is stated, never implied readable):
  - reports/product/CYCLE_40863791646.md  (report of record; PRESENT)
  - results/product/orchestration/CYCLE_40858799166_resume_diagnosis.json  (run diagnosis; PRESENT)
  - results/product/audit_readiness/CYCLE_40863791646_audit_readiness.json  (committed audit-readiness dossier; PRESENT)
  - the `audit_route` + `next_recommendation` fields of state/product.json

DO NOT re-derive discharged findings (see route artifact do_not_re_derive).
Gate path: results/audit/product/CYCLE_<run_id>_GATE.json (UPPERCASE), written from the audit-job checkout, NOT from /tmp/lex_team.

The vertical slice stays complete and locally runnable; both DO-NOT-SERVE
orders stand; no owner session is staged while either frozen bar is unmet.
COMMITTED MEASUREMENTS (already run by the producer):

- route results/product/audit_readiness/CYCLE_40863791646_AUDIT_ROUTE.json: status=PASS total=101.344s budget_fraction=0.0375 failed_steps=[]
- route workspace: mount=/tmp/lex_team root_is_producer_mount=False instrument_root=/home/runner/work/LexMachina/LexMachina (generated on the producer's CI checkout; a rerun from cd /tmp/lex_team && … reports root_is_producer_mount=True)
- dossier results/product/audit_readiness/CYCLE_40863791646_audit_readiness.json: status=PASS n_checked=9 failed_checks=[] skipped_checks=[]
