# Operational resume 45978008218 of run 45977830089 — audit-ready

- Lane: `evaluation`; authoritative control plane: v68 (`/tmp/lex_control/state/factory_direction.json`).
- Persisted snapshot: `origin/cycle/core/evaluation/45977830089/team` @ `9aea0dbeb6ce26bcaccd17e818a9efb6c404fbdf` — preserved, **zero new commits**, not restarted.
- Accepted product mount: `/tmp/lex_accepted/product` @ `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83`.
- Result: **AUDIT_READY_PENDING_INDEPENDENT_AUDIT**. The producer does not create an audit gate.

## Orchestration failure diagnosed

Public GitHub HTML shows `Core evaluation dirV68 repair0 #24621` concluded **Failure**. The team job failed in **1m 5s** with one annotation on step 6 **`Run lane cycle`** (`Process completed with exit code 1`); audit and integrate were skipped and resilience succeeded. The persisted ref is byte-identical to the inherited base `9aea0dbeb6ce26bcaccd17e818a9efb6c404fbdf` (parent `daa7c3592082e726cd48281a560a247d4e2a7582`), and no `CYCLE_45977830089_GATE.json` exists in the tree or any ref, and no audit ref exists.

Under the frozen 2700 s classification rule carried from `evaluation/quantum_death_ledger.py`, 65 s < 2700 s, so this is **`PRODUCER_STEP_ORCHESTRATION_DEATH`** — a producer-side orchestration death, **not** a quantum death, **not** an audit-side death, **not** a write-scope violation, **not** a `REVISE`/`BLOCKED` verdict and **not** a product defect. Job logs require sign-in/admin and were not read; REST was HTTP 403 rate-limited; no provider/model root cause is claimed. Control-plane hardening items are recorded, not patched (`.github/**` is out of lane scope).

## Deliverable verified

Fresh socket-blocked offline replay of `python3 -m evaluation.minimal_retrieval_ca_benchmark --run-id 45978008218 --product-mount /tmp/lex_accepted/product --packets 39319405429` reproduced the committed benchmark `28/28` checks PASS (`DELIVERABLE_VERIFIED`):

- verdict `PRODUCT_FALSIFIED`, exit 1, `run_valid=true`, `input_drift=[]`;
- 18 gates = 11 pass / 4 fail / 3 reported, with the identical four concept/counter-authority failures;
- packet-of-record `39319405429`, direction 68, zero network attempts;
- `REPLAY_REPRODUCES`: 0 differences over 569 fields after the five pre-frozen environment/identity exclusions;
- pins: `PINS_ALL_MATCH` (14/14).

The FAST recall-loss instrument still cannot be re-executed here (numpy/sklearn absent under Python 3.14.4); this remains a preserved negative environment result, not a verdict.

## v68 conditional re-measure

`v68_conditional_gate_status_45978008218.json` records factually that the accepted product mount carries incumbent-rejection/D2-D3-D4 filter code and an accepted product gate (`CYCLE_40284658455_GATE.json`, gate=PASS), but **this operational-resume run does not execute the conditional re-measure**: it is a new pre-registered scientific measurement requiring its own freeze-first record, histograms and controls. The served-packet falsification of record stands unchanged; no serve verdict is re-issued.

## Gates

```json
{
  "state_integrity": {
    "returncode": 0,
    "verdict": "ALL_CHECKS_PASS"
  },
  "nested_refs": {
    "returncode": 0,
    "verdict": "NESTED_REFS_RESOLVED"
  },
  "write_scope": {
    "returncode": 0,
    "verdict": null
  }
}
```

Additive-state proofs: `state/evaluation.json=ADDITIVE_ONLY, evaluation/state/evaluation.json=ADDITIVE_ONLY`.
Write-scope proof: `IN_LANE_ONLY` (8 entries at proof time); final independent write-scope check: `SCOPE_CLEAN` (21 entries, 0 bad, 0 out of lane).

## Executable acceptance test

`python3 -m unittest tests.evaluation.test_operational_resume_45978008218 -v` — 10 standard-library tests lock the freeze-first record, snapshot zero-delta, diagnosis class, 28/28 verification, replay/pins, conditional-gate non-execution, state parity/additivity, all guards, index hashes and lane scope.

## Boundaries

All writes are in the evaluation lane (`evaluation/`, `tests/evaluation/`, `results/evaluation/`, `reports/evaluation/`, `state/evaluation.json`). No `results/audit/`, `reports/audit/`, `.github/`, product state or frozen bar was modified. Frozen hypothesis and freeze records precede claim-bearing execution. `continue_recommended=false`; no same-question cycle, no 174k rerun, no packet admission, no human gate, no change to either DO-NOT-SERVE order. The audit index is `results/evaluation/operational_resume_45978008218/AUDIT_INDEX_45978008218.json`.
