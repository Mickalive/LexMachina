# Operational Resume 40187341166 — Audit-Ready Producer Snapshot

- Lane: `evaluation`
- Direction: v68
- Run under resume: `40187341166`
- Current run: `40187594111`
- Snapshot resumed: `2eee3a16` (`evaluation cycle 40186604273 repair 0`)
- Status: **AUDIT_READY_PRODUCER_SNAPSHOT**
- Current-cycle audit: **PENDING_INDEPENDENT_AUDIT**
- Accepted run unchanged: `40159747851`
- `continue_recommended` unchanged: `false`

This report is the human-readable companion to
`results/evaluation/operational_resume_40187341166/diagnosis.json`,
`.../reproducibility_check_40187594111.json`,
`.../evidence_ref_correction.json` and
`results/evaluation/audit_namespace_recovery_40182692670/RELOCATION_RECORD.json`.
It records a resume, not a new product claim.

## 1. Why the predecessor failed

Run `40187341166` did **not** fail because of a measurement, a frozen-input
change, or a product verdict. Its `team` job failed at step 6, `Run lane cycle`;
steps 7 (`Validate active MVP producer state`) and 9 (`Enforce lane write scope`)
were skipped. The `audit` and `integrate` jobs were skipped because they depend
on `team`.

The same snapshot had already produced a scope failure one run earlier. Run
`40186604273` failed at `Enforce lane write scope` because the evaluation
producer wrote outside the lane's write scope:

- `results/audit/evaluation/CYCLE_40182692670_GATE.json`
- `reports/audit/evaluation/CYCLE_40182692670.md`

Those paths belong to the independent-auditor namespace. The producer's
`Persist team snapshot` step in `40187341166` succeeded, but `git add -A`
found no changes after the failed agent step; the commit was a no-op and the
branch was re-pushed at the same head. The `resilience` job succeeded and woke
the supervisor, which dispatched this run.

The important orchestration fact is therefore: **no durable work was lost and no
new commit was created by the failed run.** The snapshot `2eee3a16` is
byte-identical to `origin/cycle/core/evaluation/40186604273/team`. Restarting
from scratch would have discarded valid prior work for no reason.

## 2. What this run preserved and what it added

Preserved unchanged:

- every committed measurement and claim-bearing record;
- every prior result/report, including contrary and defective outputs;
- the producer-authored audit artifacts, which are **not deleted**;
- the accepted-tip lineage (`origin/lab/evaluation` = `9be8a7d5`,
  `accept evaluation cycle 40159747851`).

Added by this run (all inside the evaluation lane scope):

- `results/evaluation/orchestration/40187341166_*` and `40187594111_*`:
  public runs/jobs API snapshots for the failed run and this run;
- `results/evaluation/operational_resume_40187341166/diagnosis.json`:
  failure chain, branch identity, preservation decision;
- `.../reproducibility_check_40187594111.json` and two scratch records:
  normalized byte-identity check against `40182692670`;
- `.../evidence_ref_correction.json`: proof that the removed evidence refs were
  phantom and where the real artifacts are;
- `results/evaluation/audit_namespace_recovery_40182692670/`:
  byte-identical copies of the producer-authored gate/report plus a relocation
  record; originals remain in place;
- `.../pytest_shim_40187594111.json`, `.../state_integrity_gate_40187594111.json`,
  `.../lane_suite_40187594111.json`, `.../40187594111_nested_evidence_refs.json`,
  `.../gate_entry_point_repeat_invariance.json` and `.../write_scope_40187594111.json`:
  the final verification records;
- `reports/evaluation/OPERATIONAL_RESUME_40187341166_AUDIT_READY.md`: this
  report.

No file outside `evaluation/*`, `tests/evaluation/*`, `results/evaluation/*`,
`reports/evaluation/*`, `state/evaluation.json` or `data/evaluation/*` was
written. The out-of-scope originals were left untouched, which is the only
scope-safe way to disclose them.

## 3. Evidence-index correction (the 40174940149 phantom artifacts)

Before this run, `state/evaluation.json` cited:

- `results/evaluation/retrieval_counter_authority_benchmark/40174940149.json`
- `reports/evaluation/RETRIEVAL_CA_BENCHMARK_40174940149.md`

Neither file exists in the worktree, the accepted mounts, or **any** git ref.
`git rev-list --all --objects` finds only the producer-authored audit gate and
report that *name* the run id:

- `results/audit/evaluation/CYCLE_40174940149_GATE.json`
- `reports/audit/evaluation/CYCLE_40174940149.md`

The gate claims a `PASS` and points at the two missing artifacts. That makes the
gate unusable as evidence that the benchmark artifacts existed. The real
gate-falsifiability artifacts are run `40175266143`:

- `results/evaluation/retrieval_counter_authority_benchmark/40175266143.json`
- `reports/evaluation/RETRIEVAL_CA_BENCHMARK_40175266143.md`

Those artifacts are kept. The two phantom strings are removed from
`evidence_refs` and preserved verbatim, with the git-object proof, in
`evidence_ref_correction.json`. This is an index correction, not a deletion of
contrary evidence.

The same correction adds the real product measurement record to the index:
`results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json`, its engine
record, and its human report. It also adds the operational-resume artifacts.

## 4. Reproducibility verification

Command (scratch directories only; no committed record was rewritten):

```text
PYTHONPATH=/tmp/lex_accepted/product python3 -m evaluation.minimal_retrieval_ca_benchmark \
  --run-id local_40187594111 \
  --out-dir /tmp/opencode/eval_resume/out \
  --report-dir /tmp/opencode/eval_resume/reports
```

Result:

- verdict: `PRODUCT_FALSIFIED`
- exit code: `1`
- `run_valid`: `true`
- `input_drift`: `[]`
- product mount head: `29a5c4a548ba0ab8b6a8f574de1e732d17f3d109`
- gates: 18 total, 11 passed, 4 failed, 3 reported
- failed gates:
  - `mf::concept_coverage::39319405429::de-kapitalverletzung` (2/8 core
    concepts retrieve zero rows)
  - `mf::counter_authority_surface::39319405429::de-kapitalverletzung` (0 rows)
  - `mf::counter_authority_surface::39319405429::fr-bail-entretien` (0 rows)
  - `mf::counter_authority_surface::39319405429::it-responsabilita-medica` (0 rows)

After stripping run identity, timestamp and path fields, the scratch wrapper
record and the committed `40182692670` record are **identical**; the engine
records are identical too. The comparison covers every gate predicate, measured
payload, bundle digest, re-hash map, non-vacuity control and verdict. See
`reproducibility_check_40187594111.json`.

This is a verification re-execution of a frozen instrument. It does **not**
create a second independent falsification and it does not move a bar.

## 5. Claims corrected, not silently rewritten

### 5.1 `next_recommendation` conflated two benchmarks

The prior state said:

> Minimal CA benchmark: BENCHMARK_VALID_NO_FALSIFICATION (both regressed-input
> legs fire, gates can fail).

That sentence is true only of run `40175266143`, the **gate-falsifiability**
benchmark. It is false as a description of the product measurement. The product
records `40179932344` and `40182692670` both say `PRODUCT_FALSIFIED` with the
same four failed gates.

The state's `next_recommendation` now begins with a marked correction and keeps
the original sentence verbatim after `ORIGINAL TEXT PRESERVED VERBATIM:`. The
measurement files themselves were not edited.

### 5.2 The 40182692670 gate is producer-authored

The gate contains an `auditor_scope_note` that says it was written to the
audit-job checkout. Git records the author as `lex-evaluation-team` on commit
`2eee3a16` (`evaluation cycle 40186604273 repair 0`). It is a producer-authored
artifact, not an independent audit. Its four findings are reproducible — this
run independently reproduced the retrieval/CA measurements — but its `REVISE`
status is not adopted as an audit verdict. The independent audit job for this run
must produce its own gate under `results/audit/evaluation/`.

The gate and report are retained byte-for-byte under
`results/evaluation/audit_namespace_recovery_40182692670/`, with the original
paths still present.

## 6. Test repair: historical wrapper pin

`tests/evaluation/test_minimal_retrieval_ca_benchmark.py` contained an inherited
red assertion that re-hashed the **live** wrapper against a **historical**
fixture digest. The wrapper legitimately changed in accepted cycle
`40159747851` (dynamic direction-version lookup), so the assertion pinned a
moving target.

The repair keeps the digest assertion unchanged and moves its anchor to the
historical source commit the fixture itself names
(`HISTORICAL_BLOCK_SOURCE_COMMIT` = `1dbd9a3a`). It does not weaken any frozen
rule, threshold or claim check. The live wrapper is deliberately not pinned by
this 2026-10-20 fixture; a live digest belongs in a live claim record.

## 7. Verification results

All five independent checks are green, and each has a machine record:

| Check | Command | Result | Record |
|---|---|---|---|
| Minimal benchmark tests (stdlib shim; pytest absent) | `python3 -m evaluation.no_pytest_runner --run-id 40187594111 --test-file tests/evaluation/test_minimal_retrieval_ca_benchmark.py` | **SHIM_PASS** — 21 passed, 0 failed, 0 skipped, 0 unsupported | `results/evaluation/operational_resume_40187341166/pytest_shim_40187594111.json` |
| State integrity gate | `python3 -m evaluation.state_integrity_gate --run-id 40187594111` | **ALL_CHECKS_PASS** — 11/11, 0 failed | `results/evaluation/operational_resume_40187341166/state_integrity_gate_40187594111.json` |
| Lane suite | `python3 -m evaluation.lane_suite --skip-pytest` | **PASS** — 88/88 checks, 236.037 s, 20/20 falsification families broken | `results/evaluation/operational_resume_40187341166/lane_suite_40187594111.json` |
| Write scope (in-lane pre-flight) | `python3 evaluation/snapshot_audit/write_scope.py --lane evaluation` | **SCOPE_CLEAN** — 26 entries, 0 bad, 0 junk | `results/evaluation/operational_resume_40187341166/write_scope_40187594111.json` |
| Nested evidence-ref guard | `python3 evaluation/nested_evidence_refs_guard.py --run-id 40187594111` | **NESTED_REFS_RESOLVED** — 79 top-level refs, 0 unresolved, 155 ref-shaped strings; 2 disclosed historical | `results/evaluation/operational_resume_40187341166/40187594111_nested_evidence_refs.json` |

The state-integrity gate was failing 4/11 before this run:

- `evidence_refs_n_matches` on `state/evaluation.json` (56 vs 57)
- `evidence_refs_n_matches` on `evaluation/state/evaluation.json` (19 vs 18)
- `evidence_refs_resolve` on `state/evaluation.json` (the two phantom refs)
- `root_lane_parity` on both files (`accepted_run_id`/`github_run` divergence)

After the index correction, count repair and parity alignment, all 11 pass.
The guard change is narrow: `removed_refs` is now a disclosure parent key, so
preserved historical phantom paths are counted as disclosed rather than
unresolved. It does not suppress any current ref.
The root state now cites 79 top-level evidence refs, every one of which resolves; the nested walk finds 0 unresolved refs. The two preserved phantom strings live under the explicit `removed_refs` disclosure key and are classified `DISCLOSED_HISTORICAL_REF`, not charged as current refs.

A legacy instrument note: `evaluation/report_claim_check.py` is hard-coded
to the older `reports/evaluation/CYCLE_39200567493_REPAIR.md` and its shim.
Run against this report it returns `pass:false` because this report has no
copy of that report's evidence table and its counts belong to a different
record; that is an instrument-scope mismatch, not a failed claim. This run
does not use it as a gate and does not adjust the report to satisfy it.

The lane suite's 88/88 includes the frozen reality and retrieval benchmarks,
the gate-contract checks, the 20-family falsification matrix and the
repeat-invariance checks. It says nothing about the product score; its own
claim ceiling is preserved in the record.

## 8. What an independent auditor should check

1. Re-run the minimal benchmark in a scratch directory and compare the
   normalized record to `40182692670`; the four failed gates should reproduce.
2. Confirm that `40174940149` still has no result/report object on any ref and
   that the state now points at `40175266143`.
3. Confirm that the originals under `results/audit/` and `reports/audit/` are
   untouched and that the copies are byte-identical.
4. Confirm that the `40182692670` gate's git author is not
   `lex-independent-auditor`.
5. Confirm that the test repair only changes the historical anchor and does not
   relax a frozen assertion.
6. Confirm that no claim-bearing measurement file was edited.

## 9. Remaining open items (not blockers for audit)

- **Bypass-clause correction CC6/CC7**: `CORRECTION_NOT_CONFIRMED` against the
  shallow accepted mount. Commit `51d306c` is absent and the mount head is
  `29a5c4a5`. The measurement itself is unchanged; this is a provenance
  limitation, not a new defect. See
  `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md`.
- **No pytest in the image**: tests run through the stdlib shim; the lane suite
  skips its pytest sub-check. This is an environment fact, disclosed rather
  than scored as a pass.
- **Actions logs unavailable unauthenticated**: job/step provenance is read from
  the public runs/jobs API; log bodies are not available.
- **Product action still required**: the frozen benchmark falsifies the product
  on the V3 packet-of-record exact bytes. The product lane must emit
  counter-authority rows for all three language bundles and cover the two
  missing German concepts before a re-score is meaningful. This run does not
  fix the product.

## 10. Claim ceiling

This resume establishes orchestration state, evidence-index hygiene,
reproducibility of the frozen benchmark, and the producer/audit provenance of
the `40182692670` gate. It does **not** re-score the product, move a frozen bar,
lift a DO-NOT-SERVE order, certify packet admission, or claim the map helps a
jurist. `human_gate_ready` stays `false`; the product verdict remains
`PRODUCT_FALSIFIED` on the V3 packet-of-record exact bytes.
