# Operational resume 43570757974 -> 43576640503 (evaluation, direction v68)

**Status:** producer snapshot `dad966325661` is `PENDING_INDEPENDENT_AUDIT`. Producer-authored; not self-promoted.

## What failed (H1)

- team job: **success** (validation, write scope, snapshot persist all success)
- audit job: **failure**, failing step `Independent audit` after **2706 s**
- annotations: `exit code 78` and `LEX_WORK_QUANTUM_EXPIRED seconds=2700`
- audit gate and audit snapshot steps: **skipped**; `integrate`: **skipped**; no audit ref was written

This is an **independent-audit work-quantum expiry**, not a team launch failure and not a producer rejection.

| run | team | audit | failing step | audit s | exit 78 |
|---|---|---|---|---|---|
| 43531218191 | success | failure | Independent audit | 2705 | True |
| 43542378874 | success | failure | Independent audit | 2706 | True |
| 43550420112 | success | failure | Independent audit | 2705 | True |
| 43554928192 | success | failure | Independent audit | 2706 | True |
| 43559166421 | success | failure | Independent audit | 2705 | True |

Five prior audits plus this one are consecutive quantum expiries, so the blocker is systemic. A prior accepted audit (`CYCLE_43349645400_GATE.json`, gate PASS) proves the audit can pass when the surface is small.

## Snapshot (H2)

- head `dad9663256617ed4cb59c677687540106611f306`
- parent `c79dae10ef9591e4448c4a7e426c81e4686a180c`
- delta files **49**
- audit-namespace delta paths **0**
- prior freeze pins: **50/50 match**
- prior fast verify all_hold: **True**

## Deliverable and ordered work (H3/H4)

- deliverable `43554928192`: **PRODUCT_FALSIFIED**, packet `39319405429`, 3 questions, total issued **0**; fresh socket-guarded replay reproduces: **True**
- item (1): correction of record intact
- item (2): **NOT_YET_DISCRIMINATING**; zero delta 50 byte-identical bundles, role parity False, ceiling 14/15; **no re-measure executed**
- item (3): standing record untouched; item (4): report-only; item (5): honoured operational

## Audit budget (H5)

- fast verify: `python3 -m evaluation.operational_resume_43570757974 --phase verify` (~1 s, zero writes)
- state evidence refs: **40** (archive preserves 546)
- audit index primary rows: **29** (cap 40)
- full lane suite: ~238 s; recorded as a producer gate, **not** an audit discovery tool
- negative controls: **True** (one-byte mutation detected; dropped evidence row unresolved)

## Known non-gating reds

- prior resume regression test: fails by design (hard-codes github_run 43570757974); preserved unmodified
- mount provenance gate: pre-existing shim/fixture limitation, 8 pass / 1 fail / 4 unsupported, not introduced here
- pytest: absent in the producer image; lane suite records a skip

## Verdict

H1-H5: **ALL HOLD**. Claim ceiling: Producer-authored operational verification of the persisted snapshot dad96632. No new product claim, no new same-question measurement, no promotion/admission/serve, no frozen bar/rubric/threshold/predicate/verdict-contract edit, no universal-174k benchmark. H4 records that ordered item (2) remains NOT_YET_DISCRIMINATING under the accepted frozen rule.

