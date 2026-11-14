# Operational resume `43570632816` → `43570757974` — audit-ready report

Status: **PRODUCER SNAPSHOT READY FOR INDEPENDENT AUDIT — NOT ACCEPTED**
(`audit_status=PENDING_INDEPENDENT_AUDIT`, `accepted_as_evidence=false`).

Snapshot head: `c79dae10ef9591e4448c4a7e426c81e4686a180c`; accepted working base
parent `c40cd9288bbcab02a5489bd768e2a329f4dea218`; delta 41 files.

## Fast path

```bash
python3 -m evaluation.operational_resume_43570632816 --phase verify
```

Read-only (0 writes). Expected exit `0`, runtime well under 60 s. Full index:
`results/evaluation/operational_resume_43570632816/AUDIT_INDEX.json`.

## Why run `43570632816` produced no delta

The `team` job failed in **Run lane cycle** after 16 s with exit code 1 and the
annotation `Process completed with exit code 1.` Every later validation and
write-scope step was skipped; the `if: always()` persistence step succeeded and
force-published the unchanged accepted working base; `audit` and `integrate`
were skipped and no audit ref or gate exists. This is
`ORCHESTRATION_LAUNCH_FAILURE_RC1`, the same signature as `43542234373` and the
chain-prior `43570515880` (both 16 s, exit 1). It is distinct from the
zero-delta repair `43541879339` (136 s, exit 67, `LEX_ZERO_DELTA_REPAIR`) and
from audit-quantum expiry (audit exit 78). Step logs are not captured: the
public logs endpoint is HTTP 403 without an admin token, so the diagnosis uses
job step conclusions, timings and check-run annotations only.

## What is verified

- **H1 holding**: the launch-failure signature above, plus its distinction from
  the zero-delta and quantum classes, on captured public metadata.
- **H2 holding**: HEAD is the resumed snapshot with parent `c40cd928`, the
  delta is 41 files with zero auditor-namespace paths, all 33 pins from the
  prior completed resume re-hash, and that resume's read-only verify returned
  `all_hold=true` before this run advanced state.
- **H3 holding**: the deliverable of record is unchanged — `PRODUCT_FALSIFIED`,
  exit `1`, packet `39319405429`, direction `68`, 3 questions, 0
  counter-authority rows issued. A fresh out-of-tree replay reproduces every
  measurement field under a socket guard (no network). Standing records
  `43397701490`/`43531218191` and the ordered item (1) correction of record are
  byte-intact. Classification: operational re-execution, not a new claim.
- **H4 holding**: ordered item (2) stays `NOT_YET_DISCRIMINATING`. Mount
  `7be4480e` (direction names `8b5b08dd`), 50/50 measured bundles byte-identical
  to already-measured bytes, member-for-member ceiling 14/15, role parity false,
  full named 15-member family not regenerated. No re-measure was run.
- **H5 holding**: state integrity, nested evidence refs, live write scope, the
  lane suite and reusable test shims pass; state identity is this run with
  `accepted_run_id=40265377500` unchanged and `PENDING_INDEPENDENT_AUDIT`
  disclosed.

## Claim ceiling

Producer-authored diagnosis and verification of a persisted snapshot, not an
independent audit. No new same-question measurement, no universal-174k
benchmark, no frozen bar/rubric/threshold/verdict-contract edit, no serve or
admission verdict, no promotion. `PRODUCT_FALSIFIED` and both DO-NOT-SERVE
orders stand; `human_gate_ready` and `machine_gate_ready` remain false.

## Known non-gating reds

- `tests/evaluation/test_operational_resume_43559166421.py` fails by design
  after this resume: it hard-codes `github_run=43565032175`. Preserved
  unmodified; not a gate.
- `tests/evaluation/test_mount_provenance_gate.py`: pre-existing shim/fixture
  limitation and committed-tree provenance drift check; disclosed, not used as
  evidence.
- `pytest` is absent in the producer image; the lane suite records that
  sub-check as a skip.
