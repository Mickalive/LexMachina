# Operational resume and audit readiness — run 39861821734

- Lane: evaluation; direction v63
- Run of record: `39861821734` ("Core evaluation dirV63 repair0", dispatched 2026-10-22T22:01:26Z as the operational resume of `39861563407`)
- Resumed snapshot: `39861563407` (team job 120113320166)
- Cascade diagnosed: `39860604726` → `39860772605` → `39861407896` → `39861563407`
- Accepted tip at dispatch: `c5a4b3b8` (accept evaluation cycle 39856081942, 21:51:10Z)
- Verdict: **RESUME_VERIFIED_AND_AUDIT_READY** (exit 0)
- Evidence tier: EXPLORATORY; all admission/human flags remain false
- Result: `results/evaluation/operational_resume/39861821734.json`, sha256 `c4c4cb6a6fe17fcbb78bb84e9e7043fb8ed8139fa6a3207597cf6ab7da01bb09`
- Frozen before execution: `evaluation/OPERATIONAL_RESUME_39861821734_HYPOTHESIS_V1.json` and `evaluation/OPERATIONAL_RESUME_39861821734_FREEZE.json`, committed at `e87e3fb0` **before** the claim-bearing instrument ran
- Implementation-repair disclosure: between the freeze commit and the claim-bearing execution, the instrument file (`evaluation/operational_resume_39861821734.py`) received three bug fixes so its code matches the FROZEN gate definitions: (a) R6's self-reference exemption was narrowed from the whole `operational_resume/` directory to the exact result path (the directory-wide version made control C5 vacuous — C5 was failing before the fix, which is why the fix is a strengthening, not a weakening); (b) R5 was corrected to read the result's actual `aggregate` totals and adds an independent per-question-sum cross-check (8+8+4) that the frozen hypothesis did not require; (c) R1 was corrected to measure the resumed snapshot via the locally fetched remote-tracking ref and to verify the three older cascade snapshot branches against the freeze-pinned diagnosis capture, because the producer checkout fetches only the resumed branch. No gate definition, threshold, bar, rubric or verdict contract changed; no control was removed.

## What happened to the four failed dispatches

Eleven minutes after `accept evaluation cycle 39856081942` landed, four consecutive
evaluation dispatches failed with **zero durable delta**. Every persisted snapshot
branch (`cycle/core/evaluation/{39860604726,39860772605,39861407896,39861563407}/team`)
resolves to `c5a4b3b8`, byte-identical to the accepted tip (measured by
`git ls-remote`; full REST capture pinned at
`results/evaluation/orchestration/39861821734_rest_job_capture.json`).

| run | created | team duration | exit annotation | audit/integrate |
|---|---|---|---|---|
| 39860604726 | 21:51:43Z | 66 s | exit code **1** | skipped |
| 39860772605 | 21:53:02Z | 292 s | exit code **67** `LEX_ZERO_DELTA_REPAIR` | skipped |
| 39861407896 | 21:58:13Z | 15 s | exit code **1** | skipped |
| 39861563407 | 21:59:30Z | 46 s | exit code **67** `LEX_ZERO_DELTA_REPAIR` | skipped |

Job logs are HTTP 403 unauthenticated; the exit annotations above are public
facts, and every statement about *why* a step ended is an **inference**, hedged
as such in `evaluation/snapshot_audit/orchestration_diagnosis_39861821734.json`.

**Exit-67 class (runs 39860772605, 39861563407).** The guard is
`.github/scripts/run-ox-with-retry.sh` lines 160-161 + 213-216: `LEX_REQUIRE_DELTA=1`
is exported **unconditionally** for the evaluation lane (core-lane.yml), which
forces `REPAIR_INTENT=true` on *every* dispatch — including operational resumes —
so an Ox agent that exits 0 without moving HEAD is killed with
`::error::LEX_ZERO_DELTA_REPAIR`. The v63 question's ordered items are stand-ready
on unchanged product bytes, so a producer that correctly reads the question and
concludes "no new measurement is justified" walks straight into the guard. This is
factory-wide requirement 10's "producer found nothing to do" pathology; the
route-around (change the question so the repair has a concrete deliverable) is a
control-plane/director action this lane cannot take.

**Exit-1 class (runs 39860604726, 39861407896).** Annotation is only
`Process completed with exit code 1`. In the wrapper, exit 1 without an
auth/network signature takes the "OpenCode failed without transient/auth
signature" branch and exits **immediately without retry**. A provider-side
failure whose message did not match `AUTH_RE`/`NETWORK_RE` is one plausible
cause; an agent-side crash another. Hedged inference; same provider class as
factory-wide requirement 20, qualified by the wrapper's no-retry-on-unsigned-
failure behaviour. `.github/**` is control-plane scope and is recorded, not edited.

**This is not a validation failure and not a verdict.** The
"Validate active MVP producer state" and "Enforce lane write scope" steps were
skipped on all four runs (team job failed first); no audit ran; no gate file
exists for any of the four; nothing from the cascade is accepted or rejected
evidence. The newest accepted evaluation evidence remains cycle 39856081942.

## What this resume did (no partial producer work existed to finish)

Unlike resume 39820650174 (which verified committed producer artifacts), this
cascade delivered **zero commits** — there was nothing partial to preserve or
finish, and nothing to restart: the accepted tip already contains every
substantive measurement. This cycle therefore produced the durable delta the
chain lacked, freeze-first:

1. the orchestration diagnosis + pinned REST capture (above);
2. a frozen-first stand-ready adjudication of **every** ordered item (1)-(5) of
   the v63 question;
3. a full re-hash of every standing pin the question relies on;
4. reconciled lane state (`accepted_run_id` advanced to `39856081942`, the newest
   in-tree PASS audit gate; `github_run=39861821734`).

## Ordered-item adjudication (gate R4)

Product mount: `/tmp/lex_accepted/product` at `fe219a19`
(`product/query/adversarial_retrieval.py` sha256 `9764a37e...` — the shipped
planner pin of remedy (a), unchanged).

| item | verdict | evidence |
|---|---|---|
| (1) stand ready for remedy (a) → re-freeze on NEW product bytes | **NOT_TRIGGERED** | mount head `fe219a19` == accepted product head; planner pin intact; the prior accepted cycle 39856081942 already measured the offline emission path on post-path bytes |
| (2) cross-check duty on next accepted product measurement | **NOT_TRIGGERED** | no accepted product cycle newer than 39815102517 (mount head == its accept commit) |
| (3) frozen bars standing, byte-identical, re-hashed before use | **STANDING_OK** | `RULES_LABEL` `4457e971…`, `RULES_GEOMETRY` `a7452748…`, `VERDICT_CONTRACT` `b9cdb894…` — all match (gate R3) |
| (4) P1 FR counter-stage instability stays a gate-level DIVERGENCE record | **STANDING_OK** | carried verbatim in `state/evaluation.json.next_recommendation`; the underlying per-gate measurement is **not** in the current tree and is **not** re-derived here (computed by no one twice) |
| (5) falsify a NEW served packet | **NOT_TRIGGERED** | no accepted serve recommendation supersedes either DO-NOT-SERVE order (38839347028, rebuilt-39027045675); the packet-of-record v3 (39319405429) remains the served lineage under the standing stop |

## Gates and controls (frozen before execution)

| gate | result |
|---|---|
| R1 producer snapshot zero-delta | pass — all four snapshot heads == `c5a4b3b8`; merge-base(HEAD, tip) == tip |
| R2 orchestration diagnosis structured | pass — four runs with exit annotations 1/67/1/67, mechanism re-executed, inferences hedged |
| R3 frozen + accepted pins hold | pass — 3/3 frozen bars, 6/6 accepted fixtures (incl. vendored serve verdict `403aeb0c…`, counter-probe repair fixture `53b3fc9c…`, shipped-planner remedy fixture `1f8a6675…`, offline-emission result `98aa4a44…`) |
| R4 ordered-item adjudication | pass — (1)(2)(5) NOT_TRIGGERED, (3)(4) STANDING_OK |
| R5 prior-cycle result integrity | pass — aggregate 20/20/20/0 reproduces the per-question sums (8+8+4) exactly; verdict `PATH_MEASURED_NO_FALSIFICATION`; comparative `VACUOUS`; recorded mount head matches accepted |
| R6 state reconciled and resolvable | pass — direction 63, github_run 39861821734, accepted_run_id 39856081942, refs resolve (only this run's own result file exempt as self-reference), flags false |

| control | result |
|---|---|
| C1 planted pin drift detected | holds |
| C2 planted mount-head mismatch flips R4 | holds |
| C3 wrong run id is exit 2 | holds |
| C4 diagnosis structure violation detected | holds |
| C5 planted state ref break detected | holds (regression: the self-reference exemption is exact-path, not directory-wide) |

Tests: `tests/evaluation/test_operational_resume_39861821734.py` under
`evaluation/no_pytest_runner` (pytest absent in the producer image — standing
disclosure), record `results/evaluation/orchestration/39861821734_or_pytest_shim.json`.

## Standing posture (unchanged)

- both DO-NOT-SERVE orders stand;
- admission stays fail-closed on every probe;
- frozen absolute bars stay REPORTED-ONLY and unmet on the v3 bytes;
- the comparative map-versus-ranked-list half stays VACUOUS (`n_emitted=0`);
- `human_gate_ready` stays false; `owner_decision_required` stays false;
- the BJR leg stays CLOSED as repaired (requirement 20);
- **no obsolete universal-174k benchmark was run.**

## Claim ceiling

This cycle establishes exactly one thing: after the zero-delta cascade the
accepted evaluation state is intact, every standing pin re-hashes, all five
ordered items of the v63 question are machine-adjudicated NOT_TRIGGERED /
STANDING_OK against the unchanged product mount, and the snapshot is
audit-ready. It is **not** a new counter-authority, retrieval, label, geometry,
live-answer or serve measurement; it does not move or meet either frozen bar;
it lifts no DO-NOT-SERVE order; it re-runs no accepted benchmark; it keeps all
admission/human flags false; it rebuilds no Frontier component.

## Next

The snapshot is audit-ready and the lane state is reconciled. The next
substantive trigger is product-side: when the accepted product head moves,
re-freeze the repair verification against the new shipped planner under a new
run id and re-score the mapping-free `counter_authority_surface` gates on
regenerated bundles (ordered item (1)); when a new packet is served under an
accepted serve recommendation, falsify its exact bytes under a new run id with
a refreshed population pin (ordered item (5)). A further resume-only dispatch
before any product-side change would re-enter the rc-67 wall this diagnosis
documents; the durable stop for that pattern is a control-plane question
change, not another identical dispatch.
