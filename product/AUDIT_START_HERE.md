# AUDIT START HERE — product snapshot (run 41204598789)

This file is written by the **producer** for the **independent auditor**. It is
not an audit verdict, not a gate and not an acceptance claim.

## What happened before this snapshot

Run `41199556067` resumed `41193662357` and committed a verified served slice,
but its **audit job again expired the 2700 s work quantum** (`Independent audit`
ran 2704.0 s, exit `78`, annotation `LEX_WORK_QUANTUM_EXPIRED seconds=2700`).
The gate-reader and audit-persist steps were skipped, so no `/audit` ref and no
gate exist. Evidence:

- `results/product/orchestration/CYCLE_41199556067_team_step_raw.json`
- `results/product/orchestration/CYCLE_41199556067_orchestration.json`
- `results/product/orchestration/CYCLE_41199556067_resume_diagnosis.json`

The diagnosis for that failure is **snapshot-chain accumulation**, not a product
defect: the persisted team ref carried **10 unaccepted commits and 103 changed
files / 74,122 inserted lines** over the accepted base `7be4480e`, so each
audit was asked to re-derive a whole unadjudicated chain and ran out of time.

## What this snapshot is

This cycle re-bases the work on the accepted base and carries only what the
current run needs. It is a **single current-run commit over the accepted base**,
plus one artifact commit for this packet. The prior snapshots are preserved,
unmodified, on their own `cycle/core/product/<run>/team` refs; they are **not**
part of this snapshot's audit scope and must not be re-derived.

## Audit in this order (bounded)

From the mounted producer workspace (`/tmp/lex_team`):

```bash
cd /tmp/lex_team
python3 product/audit_chain.py --verify --run-id 41204598789     # ~1 s, stdlib only
python3 product/audit_readiness.py --run-id 41204598789 \
    --out /tmp/lex_audit_readiness.json                         # ~75 s, full re-derivation
python3 -m pytest product/tests/test_cycle_41204598789.py -q    # cycle claims
```

`audit_chain.py` is the scope manifest: it names the accepted base, labels every
commit as `CURRENT_CYCLE` or `CARRIED_UNJUDICATED`, inventories the changed
paths, rejects out-of-scope or auditor-namespace writes, and re-checks local
artifact presence. `audit_readiness.py` is the full bounded dossier (state
contract, accepted pointer, the resumed-run diagnosis, v68 claim artifacts,
shipped progressive socket smoke, and the 170-test MVP core set). Its
`bounded_plan` records measured seconds against the 2700 s quantum.

## Claim ceiling of the producer delta

The executable lane deliverable is re-verified at this head:

- `results/product/server_slice/41204598789/summary.json` — **PASS 10/10**,
  fixture mode, non-loopback socket trap armed, **100 decisions / 8 clusters**,
  every row with coordinates, cluster id and source URL, 2 cited decisions,
  counter definitions published broad beside narrow, 71 page-contract
  assertions, no network.
- This is **fixture-mode served wiring evidence only**. It makes no live
  OpenCaseLaw latency, answer-quality, legal-usefulness, frozen-bar, serve,
  packet-admission or human-gate claim.

Direction v68 ordered work (the rejection/incumbent leg and full-family
regeneration) is **consumed REPORTED-ONLY** from accepted evidence
(`v68_delivery.status=LANDED`, family `CYCLE_40257275384`: 49 bundles / 4900
decisions / 55 verified / 0 verified-and-defective / 0 false rejects). It is not
re-measured here, no bundle bytes are written and no frozen rule is touched.

## Out of scope — do not spend the quantum here

- Do not re-audit the preserved `41152471808 … 41199556067` chain commits.
- Do not re-derive accepted evaluation `40070818687`, `40068038783`,
  `40105794124` or the D2 profile `40089391202`.
- Do not regenerate the offline/server slice family.
- Do not edit, re-tune or re-run any frozen gate, rubric, threshold or bar.
- The producer wrote no `results/audit/**` or `reports/audit/**` path and minted
  no gate.
