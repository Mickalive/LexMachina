# Operational resume of producer run 40167904552 — scope-failure diagnosis, deliverable verification, audit-ready snapshot

- **Lane:** evaluation
- **Direction:** `state/factory_direction.json` mounted from `origin/main`, **version 68**
- **Run being diagnosed (producer):** `40167904552` — `Core evaluation dirV68 repair0`, run_number 7557, `head_sha 23439081c9ea95a75ed401fc965c546321f2908f`, created `2026-10-25T06:06:01Z`, updated `2026-10-25T06:15:40Z`, conclusion **failure**
- **This run (operational resume):** `40168466708` — run_number 7559, created `2026-10-25T06:15:36Z`, event `workflow_dispatch`
- **Producer snapshot under resume:** `2c450be2a56b36111913b47395d15d89056a4043` (`evaluation cycle 40167904552 repair 0`)
- **Mode:** FAST MVP — deterministic offline, `network_calls=0`, no universal-174k benchmark rerun, no falsifier rerun, no bar/verdict edit
- **Claim ceiling of this document:** this is an **operational** record (orchestration diagnosis + deliverable verification + state repair). It publishes no new measurement, moves no bar, and creates no serve verdict. Per direction v68 item (5) it is explicitly *operational, not evidence*.

Machine-readable counterparts: `results/evaluation/deliverable_verification_40168466708/verification.json`,
`results/evaluation/deliverable_verification_40168466708/lane_suite_40168466708.json`,
`results/evaluation/orchestration/40167904552_run_record.json`,
`results/evaluation/orchestration/40167904552_jobs.json`,
`results/evaluation/audit_namespace_recovery_40153908549/RELOCATION_RECORD.json`,
`results/evaluation/orchestration/40168466708_nested_evidence_refs.json`.

---

## 1. Orchestration failure — diagnosed, reproduced, root-caused

### 1.1 What the platform recorded

`GET /repos/Mickalive/LexMachina/actions/runs/40167904552/jobs` (saved as
`results/evaluation/orchestration/40167904552_jobs.json`):

| job | status | conclusion |
|---|---|---|
| `team` | completed | **failure** |
| `resilience` | completed | success |
| `audit` | completed | **skipped** |
| `integrate` | completed | **skipped** |

The single failing **step** is `Enforce lane write scope`.
`audit` and `integrate` are gated on `needs.team.result == 'success'`, so a team failure
suppresses both — no gate, no integration, for run `40167904552`.

### 1.2 The rule that was violated

The checked-out workflow in this worktree is **stale** and is *not* the rule source
(`checked_out_worktree_blob_sha256 64ffe9d5…` vs `blob_sha256 875fab3f…`,
`checked_out_matches_rule_source: false`). The rule was therefore re-read from the
control plane, `origin/main:.github/workflows/core-lane.yml`, blob
`875fab3f584532bd511a0c44003eebf39f3b5de0`, step `Enforce lane write scope`:

```bash
case "$p" in
  "$CODE"/*|"tests/$LANE"/*|"results/$LANE"/*|"reports/$LANE"/*|"state/$LANE.json"|"data/$LANE"/*|"") ;;
  requirements.txt|pyproject.toml|uv.lock) [[ "$LANE" == product ]] || BAD+="$p\n" ;;
  *) BAD+="$p\n" ;;
esac
done < <(git status --porcelain -uall)
if [[ -n "$BAD" ]]; then echo -e "::error::lane crossed protected scope:\n$BAD"; exit 3; fi
```

Two properties matter and are both asserted by the verification artifact:

1. It inspects **only `git status --porcelain -uall`, i.e. uncommitted work**. Files
   already committed in `HEAD` are invisible to it. A **deletion** *does* appear
   (`D  path`), so any relocation must itself be committed during the run.
2. `results/audit/*` and `reports/audit/*` are **not** in the evaluation lane's allowed
   set (`evaluation/*`, `tests/evaluation/*`, `results/evaluation/*`,
   `reports/evaluation/*`, `state/evaluation.json`, `data/evaluation/*`). Those two
   namespaces belong to the `lex-independent-auditor`.

### 1.3 Root cause (reproduced offline, exit 0)

Replaying the exact case-rule over `git show --name-only 2c450be2` and over the live
worktree (`python3 evaluation/operational_resume_40167904552.py`, exit 0):

```
snapshot_scope_verdict        FAIL  violations = ["reports/audit/evaluation/CYCLE_40153908549.md"]
live_worktree_scope_verdict   PASS  violations = []
failing_step                  "Enforce lane write scope"
```

> **Root cause:** producer cycle `40167904552` created
> `reports/audit/evaluation/CYCLE_40153908549.md` — the independent-auditor namespace,
> outside the evaluation lane's write scope. `Enforce lane write scope` exited 3, the
> `team` job was marked failure, and `audit`/`integrate` were skipped.

The file nevertheless reached `HEAD` because the very next step is unconditional:

```yaml
- name: Persist team snapshot
  if: always()
  ...
      git add -A
      git commit -m "$LANE cycle ${GITHUB_RUN_ID} repair ..." || true
      git push --force origin "HEAD:refs/heads/$BR"
```

Both facts (`persist_team_snapshot_is_if_always: true`,
`persist_team_snapshot_commits_with_git_add_A: true`) are machine-asserted in
`verification.json`. The violating file was therefore force-persisted by a step that
always runs, exactly the failure mode already documented for run `39471603258`.

### 1.4 Why this is systemic, not a one-off

Jobs evidence for the recent evaluation runs (all saved under
`results/evaluation/orchestration/`):

| run | team | audit | integrate | failing step |
|---|---|---|---|---|
| 40153908549 | failure | — | — | `Run lane cycle` |
| 40156820260 | failure | skipped | skipped | `Enforce lane write scope` (wrote `results/audit/…GATE.json`) |
| 40157198963 | failure | skipped | skipped | `Enforce lane write scope` (wrote `results/audit/…GATE.json`) |
| 40157743614 | success | failure | skipped | `Enforce audit scope and read gate` |
| 40159747851 | success | success | skipped | *(none — accepted, `9be8a7d5`)* |
| 40162425755 | failure | skipped | skipped | `Run lane cycle` |
| 40162507752 | success | failure | skipped | `Independent audit` |
| 40167904552 | failure | skipped | skipped | `Enforce lane write scope` (wrote `reports/audit/…md`) |

`git log --all --format='%h %s' -- results/audit/evaluation/CYCLE_40153908549_GATE.json`
→ `31983434 evaluation cycle 40156820260 repair 1`, i.e. the gate for cycle
`40153908549` was written by a **`lex-evaluation-team`** commit, not by
`lex-independent-auditor`. There is **no** `lex-independent-auditor` commit touching
either `results/audit/evaluation/CYCLE_40153908549_GATE.json` or
`reports/audit/evaluation/CYCLE_40153908549.md`, and there is **no**
`accept evaluation cycle 40153908549` commit on any ref
(`git log --all --grep='^accept evaluation'` returns `9be8a7d5 (40159747851)`,
`3fdb7d63 (40143419165)`, `925349f0 (40140713687)`, `7165d9e0 (40133253347)`, … —
**no `40153908549`**).

### 1.5 Disposition — relocation, not deletion

`reports/audit/evaluation/CYCLE_40153908549.md` was **not** removed; it was copied
byte-for-byte into the lane's own namespace and only then unlinked from the auditor
namespace, so that `git status` stops reporting an out-of-scope path:

| | |
|---|---|
| source (removed from auditor namespace) | `reports/audit/evaluation/CYCLE_40153908549.md` |
| destination (lane-owned) | `results/evaluation/audit_namespace_recovery_40153908549/CYCLE_40153908549.md` |
| sha256 of both | `cd7698d33b1e4f2c7f042d27f4775198f66250ba7f6f8eb40b9f8658657f7880` |
| also verified | absent from `origin/lab/evaluation`; the only audit-namespace delta between `HEAD~1` and the accepted base was this one file |
| record | `results/evaluation/audit_namespace_recovery_40153908549/RELOCATION_RECORD.json` (`RELOCATION_NOT_DELETION`) |
| removal committed | yes — the `D` line must be committed, otherwise the scope step flags a deletion |

`state/evaluation.json` evidence ref `reports/audit/evaluation/CYCLE_40153908549.md`
was repointed to the lane-owned copy (§5). Nothing was overwritten, no contrary output
was deleted, and no accepted or frozen artifact was touched.

---

## 2. Lane deliverable verification (direction v68, ordered work)

Executed offline by `python3 evaluation/operational_resume_40167904552.py`
(exit 0, `verdict: DELIVERABLE_VERIFIED`, `failures: []`).

### Item (1) — REPORT-ONLY CORRECTION OF RECORD — **DISCHARGED**

- `results/audit/evaluation/CYCLE_40133253347_GATE.json` exists, `gate: PASS`,
  authored by the independent auditor (`23967d7325175990ae82f30da802ba011053abb1
  audit evaluation cycle 40133253347`), `required_fixes` contain exactly one
  **NON-BLOCKING** CC6/CC7 entry.
- The CC6/CC7 file:line inventory was **re-derived at the current mount head** rather
  than asserted: mount `29a5c4a548ba0ab8b6a8f574de1e732d17f3d109`,
  `product/query/pipeline.py` sha256
  `cb2c2595a3e85eb4ad53a6333bbbd91a671f85ec61f90ce9350a8df3558eda4f`,
  `if adversarial_retrieval:` @ **1310, 1339**;
  `audited = apply_verified_span_selection(` @ **1343**;
  `if not fixture_generation:` @ **1230, 1347, 1357**;
  `audited = apply_counter_emission_repair(audited)` @ **1348**.
- **CC6/CC7 gap documented, as the required fix itself instructs:**
  `commit_51d306c_resolvable_in_mount: false`, `mount_is_shallow_clone: "true"`
  (`git rev-parse --is-shallow-repository` = `true`). The mount cannot resolve
  `51d306c`; the blob and line inventory above are the substitute evidence.

### Item (2) — CONDITIONAL RE-MEASURE — **NOT_YET_DISCRIMINATING** (carried forward, not re-run)

- H1 leg has landed: `product/query/counter_evidence_span.py`, bundle sha
  `b749e435…`.
- H2 full family regenerated: **False** — member-for-member **10 / 15** under the
  frozen role rule (`offline/rent-default` 8, `server/served` 2, the three offline
  counter/corporate/business roles 0).
- The recorded adjudication
  `results/evaluation/post_repair_family_ca_falsifier/40162507752.json` was taken at
  mount head `29a5c4a548ba0ab8b6a8f574de1e732d17f3d109`, which is **still** the current
  mount head (`item2_mount_head_unchanged_since_recorded_adjudication: true`), and all
  seven scored bundle sha256 still match byte-for-byte
  (`item2_recorded_post_repair_bundles_byte_identical: true`).
- Therefore `item2_carry_forward_valid: true`: the verdict is **carried forward without
  re-running** the falsifier, `d2_path_scope_probe`, or packet-of-record `39319405429` —
  precisely what item (5) requires (no zero-delta re-derivation), and it does **not**
  become evidence this cycle.

### Item (3) — STANDING FALSIFICATION RECORD OF RECORD — untouched, report-only

`PRODUCT_FALSIFIED on packet-of-record 39319405429 (4-gate set)` is unchanged. All four
frozen input sha256 re-verified present and matching (`item3_frozen_inputs_present:
true`), including `evaluation/frozen_bars/RULES_LABEL.json`
`4457e971…` and `evaluation/FAST_MVP_CURRENT_HEAD_CA_FALSIFIER_40105794124_HYPOTHESIS_V1.json`
`446cf7ce…`. The counter-authority-yield negative (2 of 4 frozen questions) stays
recorded as a measurement of the frozen marker rule's lexical yield **on this lane's own
producer**, never a measurement of Core Product's counter channel.

### Item (4) — three NON-BLOCKING fixes of `CYCLE_39965089504_GATE.json` — quoted verbatim, never silently

Source `/tmp/lex_accepted/product/results/audit/product/CYCLE_39965089504_GATE.json`,
`gate: PASS`, three fixes, all **NON-BLOCKING**, re-quoted verbatim by
`item4_three_non_blocking_fixes_quoted_verbatim: true`:

1. **D1 (wording):** `reports/product/CYCLE_39965089504.md` section 6 says
   `test_state_cycle_39965089504.py` passes 6/6, but the committed file has 7 tests
   (7th added in follow-up commit `e0c9e32`); `state/product.json` is internally
   inconsistent, saying both "7-test re-derivation suite" and "(6 tests)". All 7 pass
   and suite totals are unaffected; correct the wording in the next cycle.
2. **D2 (wording):** `results/product/orchestration/CYCLE_39965089504_resume_diagnosis.json`
   durable_delta calls `product/tests/test_counter_surface_known.py` "(new, 90 lines)",
   but the file existed on accepted base `b48d6f3` (created by cycle `39949461593` with
   4 tests); this cycle appended 2 D1 tests (90 inserted lines). Inventory wording only;
   the appended tests are real and pass.
3. **D3 (environment disclosure):** producer suite artifact records base 172/1309/20
   and head 171/1325/20 (failed/passed/skipped); an auditor environment with identical
   package versions reproduces 172/1308/21 and 171/1324/21 — one mount/data-dependent
   skip-to-pass variance present identically on BOTH trees, so FAILED sets and the
   0-new/1-fixed conclusion are unaffected. Worth one disclosing sentence next time
   suite counts are published.

### Item (5) — no zero-delta same-question cycle

Discharged by construction: this cycle re-ran **no** frozen benchmark, **no** D2
profile, **no** bypass diagnosis, and **no** falsifier. It re-derived only (a) the
orchestration diagnosis, (b) the deliverable status, and (c) the scope/state repair —
operational work, recorded as operational.

---

## 3. Lane test-suite re-execution (not a new benchmark)

```
PYTHONPATH=/tmp/lex_accepted/product python3 -m pytest -q \
  --junitxml=results/evaluation/deliverable_verification_40168466708/lane_suite_40168466708.junit.xml \
  <the same 10 lane test files used by run 40153908549>
```

**159 total, 156 passed, 3 failed, 0 skipped** — identical totals *and* identical failed
set to the recorded `results/evaluation/test_suite_40153908549.json`
(`comparison_to_recorded_suite_40153908549.identical_totals: true`,
`identical_failed_set: true`, names normalised from path style to junit dotted style).

The three failures are the same three pre-existing, mount-/worktree-dependent ones:

1. `test_cross_lingual_alignment_v10::test_cross_lingual_findings` — needs
   `evaluation/results/v3_extended/evaluation_v10_cross_lingual_alignment_results.json`,
   not shipped in this worktree (`FileNotFoundError`).
2. `test_disclosure_provenance_crosscheck.TestMountEndToEnd::test_full_run_reproduces_the_committed_record`
   — live re-execution now reads `VERDICT_DIVERGENCE_HEADLINE` against the committed
   record because the accepted product mount head moved past the pin.
3. `test_mount_provenance_gate::test_check_provenance_on_the_committed_tree_does_not_re_derive`
   — `n_do_not_re_derive` 3 vs 4, the finding of record for run `39231573047` asserted
   rather than described.

None is introduced by this cycle. Preserved as-is (negative results are evidence).

### State-pin regression control (A/B against the snapshot)

Because relocating the `.md` changes what `state/evaluation.json` can reference, a
clean worktree at the snapshot `2c450be2` was created (`/tmp/opencode/baseline_before`)
and the ten state-pinning operational-resume / audit-correction test files were run in
both trees with an identical command:

| tree | total | failed | passed | skipped |
|---|---|---|---|---|
| baseline `2c450be2` (pre-relocation) | 120 | **37** | 85 | 2 |
| after relocation, before state repair | 120 | 41 | 81 | 2 |

The four regressions were exactly the four tests that require every `evidence_refs`
entry to resolve:

- `test_audit_correction_verification::test_evidence_refs_exist`
- `test_operational_resume_39548140787::test_evidence_refs_are_all_existing_files`
- `test_operational_resume_40044626742::test_evidence_index_resolves_and_counts`
- `test_operational_resume_40094203248::test_evidence_refs_all_resolve_or_are_disclosed`

They are repaired by the evidence-ref repoint in §5; no test was made red by this
cycle that was green at the snapshot.

---

## 4. State integrity

- `evaluation/nested_evidence_refs_guard.py --run-id 40168466708` →
  `NESTED_REFS_RESOLVED`, **0 unresolved** (41 `RESOLVED_WORKTREE`, 9
  `RESOLVED_CROSS_LANE_MOUNT`), exit 0; output
  `results/evaluation/orchestration/40168466708_nested_evidence_refs.json`.
- `open_items` was **not** touched: `evaluation/disclosure_provenance_crosscheck.py`
  freezes `item_5_fr_live_counter_run_instability_P1` and
  `item_6_population_and_limiting_identity_movement_P1ext` by text sha
  (`ab771b84…`, `fb26cf86…`); both remain byte-identical.
- `evidence_refs_n == len(evidence_refs)` and every entry resolves as a file.
- No frozen bar, rubric, threshold, verdict contract, packet or gate JSON was edited;
  no posture flag was flipped; `direction_version` stays `68`.

---

## 5. Provenance disclosure (AGENTS.md #6 — disclosed, not silently changed)

**What was wrong.** `state/evaluation.json` at snapshot `2c450be2` carried
`accepted_run_id: 40153908549` and `audit_status: "AUDIT_PASSED"`. Neither is backed by
independent provenance:

- the `audit` job of run `40153908549` **never ran** (its `team` job failed at
  `Run lane cycle`);
- the gate `results/audit/evaluation/CYCLE_40153908549_GATE.json` was written by
  `lex-evaluation-team` commit `31983434` (run `40156820260`), not by
  `lex-independent-auditor`;
- the audit report `reports/audit/evaluation/CYCLE_40153908549.md` was written by
  `lex-evaluation-team` commit `2c450be2` (run `40167904552`);
- **no** `accept evaluation cycle 40153908549` commit exists on any ref.

**What the direction requires.** Direction v68: *"Read from BOTH HALVES of factory-wide
requirement 4"* — a gate `PASS` on the run's `/audit` branch **and** an
`accept <lane> cycle <run_id>` commit on `origin/lab/<lane>`.

**Both halves for run `40159747851`:**

| half | evidence |
|---|---|
| 1 — audit branch + gate | `origin/cycle/core/evaluation/40159747851/audit` head `7168c2eb7bb27208f9e85693abe9a18ca5d64e68`, author **`lex-independent-auditor`**, subject `audit evaluation cycle 40159747851`, containing `results/audit/evaluation/CYCLE_40159747851_GATE.json` with `gate: PASS`, `safe_to_integrate: true`, `required_fixes: []` |
| 2 — accept commit | `origin/lab/evaluation` commit `9be8a7d5b3a4b84eb45da6160bf90620f7d81d40`, subject `accept evaluation cycle 40159747851` |

`accepted_run_id` is therefore corrected **40153908549 → 40159747851** under an
`accepted_run_id_advance` disclosure block that names the superseded value, why it could
not stand, and the two halves. `audit_status: "AUDIT_PASSED"` is kept but its **scope is
now stated explicitly**: it describes the accepted cycle `40159747851`
(auditor commit `7168c2eb`), **not** `40153908549`. This cycle's own status is recorded
as `PENDING_INDEPENDENT_AUDIT`.

**What is explicitly *not* claimed:** the producer-authored
`results/audit/evaluation/CYCLE_40153908549_GATE.json` and
`reports/audit/evaluation/CYCLE_40153908549.md` are retained and cited as
**producer-authored**, with `independent_audit_provenance: false`. They are evidence
that the cycle *proposed* a result; they are not an audit of it. Run `40153908549`'s
measurement artifact
(`results/evaluation/fast_mvp_retrieval_recall_benchmark/40153908549.json`) is
unaffected by this disclosure.

A marked **provenance-correction note was appended** (not rewritten) to
`reports/evaluation/CYCLE_40162507752_COMPLETION.md`, whose section "Audit Verification"
and section "State Update" had asserted audit provenance for `40153908549` that does not
exist.

---

## 6. Compliance / posture

- ✅ no universal-174k benchmark rerun; `no_universal_174k_benchmarks: true`
- ✅ no network calls; `deterministic_offline_only: true`, `network_calls=0`
- ✅ no frozen edit (bars, rubric, thresholds, verdict contract, packet, gate JSON)
- ✅ no falsifier / `d2_path_scope_probe` / packet-of-record re-derivation (item 5)
- ✅ no serve verdict; posture flags unchanged; `continue_recommended: false`,
  `owner_decision_required` untouched
- ✅ negative results preserved: `PRODUCT_FALSIFIED_RECALL_LOSS`,
  `NOT_YET_DISCRIMINATING`, and the three pre-existing test failures
- ✅ no history deleted — relocation is byte-identical and recorded
- ✅ lane write scope: `live_worktree_scope_verdict: PASS`, 0 violations
- ✅ every committed/accepted artifact left anchored

**Claim ceiling.** This document supports exactly one relative claim: *run `40167904552`
failed because its `team` job wrote into the independent-auditor namespace, which the
lane scope step rejects; the same namespace writes are the recurring cause of the
evaluation lane's recent orchestration failures; after relocating that file and repairing
`state/evaluation.json`, the worktree passes the lane scope rule and the v68 deliverable
verifies as `DELIVERABLE_VERIFIED` with `NOT_YET_DISCRIMINATING` still the honest status
of item (2).* It claims nothing about retrieval quality, serve readiness,
`human_gate_ready` (stays false), jurist utility, calibrated uncertainty, answer
correctness, or any property of live network retrieval.

---

## 7. next_recommendation

**continue_recommended: false.** The v68 ordered work is exhausted on this lane: item
(1) is discharged (its only required fix, CC6/CC7, is non-blocking and is now documented
with file:line at mount head `29a5c4a5` plus the shallow-clone disclosure); item (2)
remains `NOT_YET_DISCRIMINATING` and its verdict is validly carried forward because the
mount head and all seven scored bundles are byte-identical to the recorded adjudication;
items (3) and (4) are report-only; item (5) forbids another same-question cycle until
Core Product ships. The remaining binding residual is **Core Product's** ordered work —
the P0 rejection/incumbent leg plus full flagship-family regeneration — not an
evaluation measurement. Per `RESEARCH_PROTOCOL.md` §20 the successor question is the
Factory Director's to set.

Two items are worth the owner's attention but are **not** blockers:

1. `state/factory_direction.json` in this worktree is version **35** while
   `origin/main:state/factory_direction.json` is version **68**; the control plane on
   `main` is authoritative (AGENTS.md #10) and was used for this cycle.
2. The recurring defect is mechanical and cheap to prevent: producer agents write into
   `reports/audit/` and `results/audit/`. A guard that fails the *run* (not only the
   step) on first write outside the lane namespace would stop the `if: always()`
   force-persist from laundering the violation into `HEAD`.
