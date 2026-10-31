# Addendum — operational resume 41196128050 (direction v68)

**Status:** post-run provenance addendum. It changes **no verdict, gate, frozen expectation,
success rule or claim ceiling**. The generated report and audit index remain the primary
artifacts; this file records two pre-run verifier fixes that the generated prose does not name,
and the one historical pointer that is preserved-and-disclosed rather than rewritten.

Final run: **RESUME_VERIFIED_AUDIT_READY**, exit 0. All gates green. No audit gate minted.

## 1. Freeze chain and the two disclosed amendments

The freeze was written before the claim-bearing run, as required. Two verifier defects were found
only by executing it; each fix is a pre-run amendment with the prior attempt archived byte-for-byte.
No frozen expectation, gate threshold, success rule or claim ceiling was changed, and the
self-check test is unchanged (`8d31bd15…`).

| Version | Script sha256 | Trigger (observed) | Change |
|---|---|---|---|
| V1 | `4d1d09d4…` | `nested_refs = UNRESOLVED_REFS_PRESENT` for `$.self_check_41192962507.artifact`; self-check `SHIM_FAIL` 13/1 | none (first run) |
| V1_1 | `68725cc19…` | nested pointer is a second occurrence of the same never-committed filename, distinct from the removed top-level ref | formal disclosure via the guard's supported key, historical value preserved |
| V1_2 | `6b2aa1d8…` | `validate_step_replay.passes_without_state_advance=false` on re-run because a prior attempt had advanced `github_run`, although `would_pass=true` | compute the vacuity flag from the predicate truth; report `this_run_advanced_state` separately |

Freeze files: `evaluation/OPERATIONAL_RESUME_41196128050_FREEZE_V1.json`,
`…_FREEZE_V1_1.json`, `…_FREEZE_V1_2.json` (the record and index cite **V1_2**).

Both defects are the same class as the inherited 41192962507 false negatives: a provenance or
pointer flag was conflated with a measurement/predicate result.

## 2. Nested historical pointer (preserved, not rewritten)

- Top-level ref `results/evaluation/orchestration/41192962507_self_check_pytest_shim.json` was
  **removed** from both state files and the real path
  `results/evaluation/orchestration/41187766812_self_check_pytest_shim.json` (run_id
  `41192962507`, sha256 `8fd59632…`) was added. No bytes were created, deleted or overwritten.
- The historical nested value `$.self_check_41192962507.artifact` **still names the
  never-committed filename**. It is left intact as provenance and **formally disclosed** under
  `nested_evidence_refs_disclosed_known_unresolvable` (`disclosed_by_run 41196128050`). The
  nested-refs guard honours a disclosure only while the path is unresolved, so it cannot mask a
  live ref.
- Evidence: `results/evaluation/operational_resume/41196128050_evidence_ref_correction.json`
  (`nested_pointer_disclosure`) and
  `results/evaluation/orchestration/41196128050_nested_evidence_refs.json`
  (`disclosed_known_unresolvable`).

## 3. Preserved attempts

- `results/evaluation/operational_resume/41196128050_preflight/attempt1/` — V1 run (nested
  unresolved, no disclosure yet). Contains result, gates, diagnostic, report/brief/index,
  `state_after.json`, `lane_state_after.json`, `run.log`.
- `results/evaluation/operational_resume/41196128050_preflight/attempt2/` — V1_1 run (nested
  resolved, validate flag false). Same file set.

The V1 and V1_1 freeze files pin these archives by sha256. Each attempt was copied out
**before** the next run regenerated the live main-path artifacts, so the archived bytes are
immutable. No historical accepted artifact was deleted or overwritten.

## 4. What this addendum does not assert

- It does not reclassify the producer failure: still `PRODUCER_WORK_QUANTUM_EXPIRED_rc78`
  (exit 78, 2704.0 s vs 2700 s), inner mechanism **UNOBSERVED** (logs 403).
- It does not execute the item-(2) protocol: still **NOT_YET_DISCRIMINATING_HEAD_UNCHANGED**
  (mount `7be4480e`, 14/15).
- It does not score, re-run or promote any benchmark, packet, serve verdict, D2 profile, bypass
  diagnosis, `d2_path_scope_probe`, standing falsification or the universal-174k benchmark.
- It does not accept anything: posture flags are all false, `PENDING_INDEPENDENT_AUDIT`.
