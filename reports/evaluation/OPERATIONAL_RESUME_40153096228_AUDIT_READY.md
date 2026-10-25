# Operational resume of run 40153096228 — audit-readiness report

- **Lane:** evaluation · **Direction:** v68 (workflow-mounted control plane from `main`)
- **Resumed run:** 40153096228 (producer snapshot `ed231f654e083fede185e638b2a93332149c9f65`)
- **Resuming run:** 40153908549 (this cycle), branch `operational-resume`
- **Report purpose:** record *why* run 40153096228 never reached audit, what is proven from the
  repository versus merely inferred, and what was done so the snapshot is audit-ready.
- **Evidence discipline:** every claim below is labelled **[ESTABLISHED]** (provable from the
  repository, the remote refs, or a measurement performed in this cycle) or **[INFERRED]**
  (ranked candidate that requires GitHub run logs, which are **not** available here — `gh` is
  present but unauthenticated, so no run log, step conclusion or job annotation could be read).

---

## 1. The observed failure

**[ESTABLISHED]** Run 40153096228 produced a team snapshot and nothing else:

| Artifact | Present? | Evidence |
|---|---|---|
| `refs/heads/cycle/core/evaluation/40153096228/team` | ✅ `ed231f65` | `git ls-remote --heads origin` |
| `refs/heads/cycle/core/evaluation/40153096228/team-attempt-1` | ✅ `ed231f65` | same (attempt 1 pushed once, to both refs) |
| `refs/heads/cycle/core/evaluation/40153096228/audit` | ❌ **absent** | same |
| `results/audit/evaluation/CYCLE_40153096228_GATE.json` | ❌ **absent** | absent from the tree **and** from `git log --all --` |
| `reports/audit/evaluation/CYCLE_40153096228.md` | ❌ **absent** | same |

**[ESTABLISHED]** In `.github/workflows/core-lane.yml` on `main` the `audit` job is gated
`if: needs.team.result == 'success'`, and `integrate` is gated `if: always() && needs.audit.result == 'success'`.
No audit branch ⇒ the `audit` job did not run ⇒ `needs.team.result` was **not** `success` ⇒
`integrate` did not run ⇒ **the run never reached `lab/evaluation`.**

**[ESTABLISHED]** The `Persist team snapshot` step carries `if: always()`, so it commits and
pushes even when an earlier step failed. Its existence therefore proves **only** that the
job reached that step — it is *not* evidence that the job succeeded.

---

## 2. Which dispatch path produced run 40153096228

The workflow on `main` (version live at the time: `002592f1`, pushed 2026-10-25 01:59:27Z,
i.e. before both 02:04:51Z and 02:09:51Z snapshots) offers three mutually exclusive bases in
step *Validate lane and initialize working base*:

1. `repair_from_run_id` → fetches **both** `…/$REPAIR_FROM/team` **and** `…/$REPAIR_FROM/audit`, then `git switch -C repair-base`;
2. `resume_from_run_id` → fetches **only** `…/$RESUME_FROM/team`, then `git switch -C operational-resume`;
3. neither → `lab/$LANE`.

**[ESTABLISHED] path 3 (fresh) is impossible:** `origin/lab/evaluation` is `3fdb7d63`, while
`ed231f65^` is `b9a01d22` — different commits, and `b9a01d22` is not reachable from
`lab/evaluation` (`git merge-base --is-ancestor` → no).

**[ESTABLISHED] path 1 (repair) is impossible:** it would have to fetch
`refs/heads/cycle/core/evaluation/40152672734/audit`, which does not exist. Measured directly
in this environment:

```
$ git fetch origin "refs/heads/main:refs/remotes/origin/main" \
    "refs/heads/cycle/core/evaluation/40152672734/audit:refs/remotes/origin/__probe2"
fatal: couldn't find remote ref refs/heads/cycle/core/evaluation/40152672734/audit
RC=128
```

With `set -euo pipefail` on that step, rc 128 aborts the job **before** the agent runs — and
the agent *did* run (the snapshot carries its work product). So the repair path cannot have
been taken.

**[ESTABLISHED] therefore path 2 (resume) was taken:** it fetches only the team ref, sets
HEAD to `b9a01d22` and creates branch `operational-resume` — exactly the observed parentage
`ed231f65^ == b9a01d22`. This is corroborated by the `resilience` job on `main`, which
re-dispatches a failed chain with
`-f resume_from_run_id="$GITHUB_RUN_ID" -f repair_round="$ROUND"` whenever the team snapshot
survives. The `repair 1` text in the commit message is `inputs.repair_round`, which the
resilience dispatcher passes through — **it is not evidence that the repair path was used.**

**Consequence [ESTABLISHED]:** run 40153096228 was *itself* an operational resume, of run
40152672734 — which was likewise a resume whose snapshot `b9a01d22` sits directly on
`57a78ec2` (run 40149704173's snapshot). The chain is therefore:

```
40149704173 (snapshot 57a78ec2) → 40152672734 (snapshot b9a01d22)
                                 → 40153096228 (snapshot ed231f65)
                                 → 40153908549 (this run, branch operational-resume)
```

Each hop is the `resilience` job recovering a `team != success`, so **the same latent failure
mode is inherited by every hop** until it is actually removed.

---

## 3. Which step failed in run 40153096228

The `team` job step order on `main` (relevant steps):

| # | Step | Gate |
|---|---|---|
| 1 | checkout `main` | — |
| 2 | Validate lane and initialize working base | `set -euo pipefail`; `exit 86` on direction mismatch |
| 3 | Mount accepted peer evidence | — |
| 4 | Install Ox/OpenCode | — |
| 5 | **Run lane cycle** (opencode via `run-ox-with-retry.sh`) | — |
| 6 | **Validate active MVP producer state** | lane is product/evaluation; `exit 68`/`exit 69` |
| 7 | Clean generated junk | `if: always()` |
| 8 | **Enforce lane write scope** | **no `if:`** — skipped when an earlier step failed |
| 9 | Persist team snapshot | `if: always()` |

Elimination:

- **[ESTABLISHED] Step 2 passed.** Its guard compares `inputs.direction_version` against
  `state/factory_direction.json` **on `main`** (= 68) and exits 86 on mismatch. Since step 5
  ran, the guard passed ⇒ the cycle ran at direction v68.
- **[ESTABLISHED] Step 6 passed.** At `b9a01d22`, `state/evaluation.json` reads
  `direction_version = 68`, `cycle_status = "COMPLETE"`, and is non-empty ⇒ `test -s` and the
  `jq -e` predicate both hold (the predicate fails only on `!= 68` or `== "INITIALIZED"`).
- **[ESTABLISHED] Step 8 did not fail.** `git add -A` in step 9 sweeps **every** uncommitted,
  non-ignored path into the snapshot. `ed231f65` contains exactly three paths, all in lane
  scope:
  `evaluation/fast_mvp_retrieval_recall_benchmark.py`,
  `reports/evaluation/CYCLE_40152672734.md`,
  `results/evaluation/fast_mvp_retrieval_recall_benchmark/40152672734.json`.
  Had step 8 rejected an out-of-scope path (`exit 3`), that path would be in the snapshot. It
  is not.
- **[ESTABLISHED] Step 9 succeeded** (both refs updated on origin).
- **[ESTABLISHED] Job timeout is ruled out.** `timeout-minutes: 65` on `main`; the parent
  snapshot landed 02:04:51Z and this one 02:09:51Z — roughly five minutes end to end.
- **[ESTABLISHED] Pre-agent wrapper failures are ruled out.** In
  `.github/scripts/run-ox-with-retry.sh`, `stage_control`, `validate_registry` (rc 64/66) and
  `resolve_model_args` (rc 76/77) all execute **before** the agent. Their failure would leave
  an untouched worktree, yet the snapshot carries substantive work product. The zero-delta
  guard (rc 67, `LEX_ZERO_DELTA_REPAIR`) is ruled out because a delta exists — note
  `LEX_REQUIRE_DELTA=1` is exported for the evaluation lane regardless of dispatch path.

**[ESTABLISHED] By elimination, step 5 — `Run lane cycle` — returned non-zero.**

---

## 4. Why step 5 returned non-zero — inferred, ranked

This is the part the repository cannot settle. **[INFERRED]**, in order of likelihood:

1. **The opencode child exited non-zero with no transient signature.**
   `run-ox-with-retry.sh` retries **only** when `rc == 75` or the log matches its
   `NETWORK_RE`; any other non-zero hits
   `OpenCode failed without transient signature (rc=$rc)` → `restore_overlay` → `exit $rc`
   with **no retry**. A single non-zero agent exit therefore fails the whole job even though
   the agent's file work is on disk and in scope.
2. A job-level cancellation/step kill after the agent finished — possible in principle, but
   the five-minute wall clock argues against it.
3. A `git`/workspace error inside the step's own shell (not observed in the resulting tree).

Ruled out by construction: registry/model-health failures (before the agent), zero-delta
(after a clean run with no delta), scope guard, state validation, snapshot push, timeout.

**[ESTABLISHED, for the parent run 40152672734] a second, independent defect:** its snapshot
`b9a01d22` is the **only** new commit on its team branch (`57a78ec2..b9a01d22` contains
exactly one commit), yet it contains two paths that belong to the **audit** job and are
outside the team lane write scope:

- `reports/audit/evaluation/CYCLE_40152672734.md`
- `results/audit/evaluation/CYCLE_40152672734_GATE.json`

Because no agent commit precedes the snapshot, those files were **uncommitted** when
`git add -A` swept them — i.e. the **producer agent wrote its own audit artifacts**. Two
consistent readings remain, indistinguishable from the repository: the agent exited non-zero
(steps 6 and 8 skipped), or the agent exited 0 and `Enforce lane write scope` failed with
`exit 3` on those two paths. Either way the job is non-success, which is why
`cycle/core/evaluation/40152672734/audit` was never created and why the repair path was
unavailable to the next run (§2).

**What is explicitly NOT claimed:** no run log, step conclusion, job annotation or timing was
read. `gh` is unauthenticated in this environment. The failure *mode* of step 5 is an
inference from elimination; only its *fact* is established.

---

## 5. What made the snapshot audit-ready

| # | Action | Proof |
|---|---|---|
| 1 | **Diagnosed the orchestration failure** without restarting; §2–§4 above | this report |
| 2 | **Repaired the instrument** so it can re-derive its own record (`UnboundLocalError` on `c3_ok_check`/`c4_ok_check` at line 689, defs after call site) | reproduced before the fix; repair recorded as a 3rd `CODE_FIX_AFTER_FREEZE` entry; no frozen predicate changed |
| 3 | **F-3B disposition**: restored `40152672734.json` from blob `b9a01d22` (sha re-hashed `ef039fbf…`), re-homed the producer's in-place rewrite verbatim as `40153096228.json` (sha `78f24980…`), wrote a provenance sidecar | `results/evaluation/fast_mvp_retrieval_recall_benchmark/40153096228_PROVENANCE.json` |
| 4 | **Published a reproducible measurement** of the frozen claim under run 40153908549 | `results/evaluation/fast_mvp_retrieval_recall_benchmark/40153908549.json`, sha `6d48e485…`; two runs identical except timing fields |
| 5 | **Repaired the lane state's frozen `open_items`** (dropped by `8fe862e8`), byte-exact against `FROZEN_TEXT_SHAS` | `state/evaluation.json` → `open_items_restoration.byte_exact_proof`, both `match: true` |
| 6 | **Published a test artifact** with a clean-tree baseline comparison | `results/evaluation/test_suite_40153908549.json` — 159 run / 156 pass / 3 fail, versus 38 / 26 / 12 at snapshot head `ed231f65` in a detached worktree |
| 7 | **Left the working tree clean and fully in lane scope** so `Enforce lane write scope` passes on this run | `git status --porcelain -uall` empty after commit |

Negative results preserved: the benchmark's own verdict is
**`PRODUCT_FALSIFIED_RECALL_LOSS`** (exit 1) with `C7b_duplicates_reported_only` failing as
reported-only, plus the original-V1 reading `NOT_MEASURED_VACUOUS` (exit 2) published beside
it; 14/24 cells are `n_cells_not_measured`; three pre-existing test failures remain
individually dispositioned in `reports/evaluation/CYCLE_40153908549.md` §4.

---

## 6. Standing risks for the next cycle

**[ESTABLISHED]** These are properties of the control plane, recorded and **not** edited here
(`.github/**`, `directives/**`, `state/factory_direction.json` are outside this lane's write
scope):

1. **The resume loop re-fires on the same latent cause.** `resilience` re-dispatches with
   `resume_from_run_id` for any `team != success`, suppressing duplicates only while another
   run is active. A single non-zero agent exit therefore produces an unbounded chain of
   resumes (40149704173 → 40152672734 → 40153096228 → 40153908549) until the underlying
   exit is fixed.
2. **`Persist team snapshot` masks failure.** With `if: always()` it makes every failed run
   look like a delivered snapshot; only the absent `audit` branch reveals the failure.
3. **Producer agents can be led into audit scope.** The `repair` prompt tells the producer to
   "read `/tmp/lex_prior_audit` and fix every `required_fixes` item"; when no audit branch
   exists the producer has no audit to read — yet run 40152672734 produced audit-lane files
   anyway, which can only fail the team scope guard.
4. **The branch's own control-plane copy is stale.** In this branch,
   `state/factory_direction.json` reads **version 35** and `directives/lanes/evaluation.md`
   has been reverted to legacy 2-line text (commit `57a78ec2`), while the workflow-mounted
   plane from `main` is **version 68** and is authoritative (AGENTS.md §10). Step 2 reads the
   guard from `main`, so the mismatch is not self-detected.
5. **`gh` is unauthenticated in the lane sandbox**, so a future cycle will be just as unable
   to read run logs unless that changes — the step-5 root cause in §4 stays unconfirmed.

**Owner attention is not required** for any of the above (`owner_decision_required=false`);
items 1–5 are control-plane observations for the Factory Director, not blockers for this
deliverable.
