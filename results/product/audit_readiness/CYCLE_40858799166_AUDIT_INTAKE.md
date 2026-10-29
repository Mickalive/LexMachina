# AUDIT INTAKE — product run 40858799166

Machine-readable target:

```json
{
 "audit_target_ref": "origin/cycle/core/product/40858799166/team",
 "audit_target_head": null,
 "audit_target_head_source": "unpublished_at_intake_generation",
 "team_ref_present": false,
 "local_head_at_generation": "50591be777c47f64e73488b91e335b941e531cd3",
 "accepted_ref": "origin/lab/product",
 "accepted_head": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83",
 "state_accepted_commit": "7be4480ed3ca623b77ea082404ca3b5b7ac5ee83",
 "resumed_run_id": "40858206250",
 "resumed_snapshot_head": "50591be777c47f64e73488b91e335b941e531cd3",
 "resumed_diagnosis": "results/product/orchestration/CYCLE_40858206250_resume_diagnosis.json",
 "report_of_record": "reports/product/CYCLE_40858799166.md",
 "cycle_block_key": "cycle_40858799166_operational_resume",
 "cycle_block_present": true,
 "self_label_status": "MISSING_ARTIFACTS",
 "artifact_paths": {
  "report": "reports/product/CYCLE_40858799166.md",
  "diagnosis": "results/product/orchestration/CYCLE_40858206250_resume_diagnosis.json",
  "dossier": "results/product/audit_readiness/CYCLE_40858799166_audit_readiness.json",
  "route": "results/product/audit_readiness/CYCLE_40858799166_AUDIT_ROUTE.json",
  "intake": "results/product/audit_readiness/CYCLE_40858799166_AUDIT_INTAKE.md"
 },
 "artifact_present": {
  "report": true,
  "diagnosis": true,
  "dossier": true,
  "route": false,
  "intake": false
 },
 "missing_artifacts": [
  "route",
  "intake"
 ],
 "self_label_verdict": "NOT_ADDRESSABLE_BY_RUN_ID: a run-id-keyed audit would start from an absent artifact; repair before dispatch",
 "resumed_head_is_not_audit_target": true
}
```

AUDIT ROUTE BRIEF — product snapshot for run 40858799166
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

SNAPSHOT SELF-LABEL GUARD — DO NOT START FROM A MISSING PATH
------------------------------------------------------------
status=MISSING_ARTIFACTS
cycle block: cycle_40858799166_operational_resume (present=True)
missing artifacts: route, intake
The producer snapshot is NOT addressable by this run id. An
auditor that reads the paths implied by this id would spend its
quantum on absent files or on another cycle's artifacts. Record
this as an audit-readiness defect (not a product rejection) and
require the producer to repair the run-id labels before a gate
is written.

AUDIT TARGET (team ref): origin/cycle/core/product/40858799166/team
AUDIT TARGET HEAD:        NOT PUBLISHED YET in this checkout.
LOCAL HEAD AT GENERATION: 50591be777c47f64e73488b91e335b941e531cd3
Resolve the pushed team ref in the audit checkout:
  git rev-parse origin/cycle/core/product/40858799166/team
ACCEPTED HEAD:            7be4480ed3ca623b77ea082404ca3b5b7ac5ee83
RESUMED PREDECESSOR:      40858206250 at 50591be777c47f64e73488b91e335b941e531cd3
DO NOT audit the resumed predecessor head: a producer resume
commits its own delta on top of it.

RUN THIS FIRST (measured cost in parentheses; every command runs
from the producer mount: cd /tmp/lex_team && …):
  0. cd /tmp/lex_team && bash product/bootstrap_query_env.sh                      (~40 s once; no deps otherwise)
  1. cd /tmp/lex_team && python3 product/state_contract.py --check --direction-version 68 --json        (~0.1 s)
  2. cd /tmp/lex_team && python3 product/audit_readiness.py --verify results/product/audit_readiness/CYCLE_40858799166_audit_readiness.json   (~1 s)
  3. cd /tmp/lex_team && python3 product/audit_route.py --run-id 40858799166 --out /tmp/route.json          (full route, ~2-4 min measured)

THEN read, in this order (short files first; all under /tmp/lex_team; ABSENT is stated, never implied readable):
  - reports/product/CYCLE_40858799166.md  (report of record; PRESENT)
  - results/product/orchestration/CYCLE_40858206250_resume_diagnosis.json  (run diagnosis; PRESENT)
  - results/product/audit_readiness/CYCLE_40858799166_audit_readiness.json  (committed audit-readiness dossier; PRESENT)
  - the `audit_route` + `next_recommendation` fields of state/product.json

DO NOT re-derive discharged findings (see route artifact do_not_re_derive).
Gate path: results/audit/product/CYCLE_<run_id>_GATE.json (UPPERCASE), written from the audit-job checkout, NOT from /tmp/lex_team.

The vertical slice stays complete and locally runnable; both DO-NOT-SERVE
orders stand; no owner session is staged while either frozen bar is unmet.
COMMITTED MEASUREMENTS (already run by the producer):

- route CYCLE_40858799166_AUDIT_ROUTE.json: ABSENT (regenerate with cd /tmp/lex_team && python3 product/audit_route.py --run-id 40858799166 --out results/product/audit_readiness/CYCLE_40858799166_AUDIT_ROUTE.json)
- dossier results/product/audit_readiness/CYCLE_40858799166_audit_readiness.json: status=PASS n_checked=9 failed_checks=[] skipped_checks=[]
