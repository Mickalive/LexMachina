# Operational Resume — Evaluation Lane, Run 43357838904

**Current run:** `43359487892` (direction v68, `LEX_REQUIRE_DELTA=1`)
**Resumed run:** `43357838904` → whose persisted snapshot is run `43349645400` (`fe99ef6a`) → whose base is run `43344048907` (`f97a5656`)
**Mode:** OPERATIONAL RESUME. Not a new same-question evidence cycle.
**Verdict:** `RESUME_VERIFIED_AUDIT_READY` — all five frozen hypotheses hold, 0 failed checks.
**Independent audit of the resumed run:** DOES NOT EXIST. This report is a producer instrument and is **not** an audit.

## 1. Why the last two runs issued no verdict

**Run 43357838904** failed at team-job step 6, `Run lane cycle`, and persisted no delta. Its
snapshot ref `refs/heads/cycle/core/evaluation/43357838904/team` is byte-for-byte the head of
run 43349645400 (`fe99ef6a`); `git diff fe99ef6a..43357838904/team` is empty. Step 7
`Validate active MVP producer state` and step 9 `Enforce lane write scope` were skipped, and the
`audit` and `integrate` jobs were skipped. No `.../43357838904/audit` ref exists. This is a
`LANE_CYCLE_EXECUTION_FAILURE_ZERO_DELTA` class. Job logs are HTTP 403 without a GH token; the
diagnosis is from public job-step metadata plus the persisted snapshot, and no log line,
provider error or mechanism is invented.

**Run 43349645400** completed `Run lane cycle` and `Validate active MVP producer state`, then
failed at step 9, `Enforce lane write scope` (exit 3). Its snapshot added exactly two paths, and
both are outside the producer-allowed set:

```
reports/audit/evaluation/CYCLE_43349645400.md
results/audit/evaluation/CYCLE_43349645400_GATE.json
```

`audit` and `integrate` were skipped, and no audit ref exists for any of `43342851837`,
`43344048907`, `43349645400` or `43357838904`. This is the recurring
`WRITE_SCOPE_VIOLATION_PRODUCER_AUDIT_NAMESPACE` class already recorded for runs 38982176936,
39470495546, 40167904552, 40186604273 and 40232590665. The `.github/**` control plane is
read-only from this lane; the class is recorded, not patched.

## 2. The accumulated FAST-MVP deliverable is preserved and verified

The claim-bearing record remains `results/evaluation/minimal_ca_falsify_benchmark/43342851837.json`
(`sha256 8c0178a2…`), produced by the accepted wrapper
`evaluation.minimal_ca_falsify_benchmark` → `evaluation.mapping_free_recall_falsifier.run()` on
packet-of-record `39319405429`. No field was rewritten.

- verdict `PRODUCT_FALSIFIED`, exit 1
- 18 gates: 11 passed, 4 failed, 3 reported
- failed gates: `mf::concept_coverage::39319405429::de-kapitalverletzung` and
  `mf::counter_authority_surface::…` on the DE, FR and IT questions
- all 10 repo pins and all 14 mount pins re-hash unchanged
- `run_valid=true`, `input_drift=[]`, non-vacuity battery 4/4 controls hold
- record, engine record and lane report agree on verdict, exit, gate counts, failed gates and
  product mount head `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83`
- a **fresh scratch replay** (out-of-tree, run id `43359487892_replay`) reproduces all **41**
  measurement-bearing fields with zero differences; the only disclosure divergence is the
  host platform label (`…-1016-aws…` vs `…-1019-azure…`), which is not a measurement. The
  original record's digest is unchanged after replay.

Standing negative findings are preserved, not softened: the product issues **zero
counter-authority rows** on all three served questions and 2 of 8 German core concepts retrieve
zero served rows. Those are the falsification, not a defect to be harmonised away.

## 3. Ordered item (2) is still NOT_YET_DISCRIMINATING

The accepted precondition instrument (`evaluation.v68_item2_family_gate`, rule reused unchanged
from accepted run 40258497460) was re-run at the current accepted product mount:

- product head `7be4480e…`; `lab/product` unchanged at `7be4480e…`
- current fixed-path family is byte-identical to the set already measured: 50/50 identical,
  0 differing, 0 missing → a re-measure is zero-delta
- role cardinality is not regenerated: `server/served` is 3 against the frozen requirement of 4,
  so member-for-member matching is capped at **14/15**

No D1–D4 content is re-scored and no synthetic stand-in is substituted. Item (1) remains
discharged at `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md`; item (3)
is kept unchanged and not re-run; item (4) is report-only; item (5) — no new same-question cycle —
is applied here as an operational resume.

## 4. Inherited producer pseudo-audit files — append-only disposition

Four tracked files sit in the independent auditor's namespace. All four were committed by
`lex-evaluation-team <lex-team@autonomous.local>`, not by an auditor, and every audit job that
could have reviewed them was skipped. They are **producer-authored** and must never be quoted as
an independent audit in either direction.

| file | commit | producer |
|---|---|---|
| `reports/audit/evaluation/CYCLE_43342851837.md` | `a886bf2a` | lex-evaluation-team |
| `results/audit/evaluation/CYCLE_43342851837_GATE.json` | `a886bf2a` | lex-evaluation-team |
| `reports/audit/evaluation/CYCLE_43349645400.md` | `fe99ef6a` | lex-evaluation-team |
| `results/audit/evaluation/CYCLE_43349645400_GATE.json` | `fe99ef6a` | lex-evaluation-team |

Disposition: byte-identical copies under
`results/evaluation/audit_namespace_recovery_43359487892/`, originals **retained, not deleted and
not rewritten in place**, with `originals_retained=true`, `originals_deleted=false`,
`originals_edited=false`, `independent_audit_provenance=false`. No file under `results/audit/` or
`reports/audit/` is added, modified or deleted by this run.

Recorded contradictions in the pseudo-audit files (published in the relocation record):

1. `CYCLE_43349645400_GATE.json` self-certifies `gate=PASS, safe_to_integrate=true` although its
   own audit job was skipped; a producer cannot pass itself.
2. The same file claims run `43344048907`'s verification was complete, while that run's own team
   job **failed at `Run lane cycle`** and its validation/scope steps and audit/integrate jobs were
   skipped. A producer self-report on a failed run is not a gate.
3. `CYCLE_43342851837_GATE.json` says `REVISE / safe_to_integrate=false`; the later
   `CYCLE_43349645400_GATE.json` says `PASS / true` on the same underlying deliverable bytes, with
   no new measurement, no new evidence and no independent audit — a silent producer status upgrade.
4. The files read as auditor findings, but no auditor executed anything for any of the four runs.

## 5. State, scope and validation

- both state files advance `github_run` to `43359487892`, keep `accepted_run_id=40265377500` and
  `direction_version=68`, and carry an explicit `PENDING_INDEPENDENT_AUDIT` /
  `accepted_as_evidence=false` disclosure for this run
- `evidence_refs_n == len(evidence_refs)` in both files; every added ref resolves
- live producer write scope is `SCOPE_CLEAN`; the run writes only `evaluation/*`,
  `tests/evaluation/*`, `results/evaluation/*`, `reports/evaluation/*` and `state/evaluation.json`
- state-integrity gate: `ALL_CHECKS_PASS`
- lane suite (`--skip-pytest`): `PASS`
- the lane image has no `numpy`/`scipy`/`sklearn` and no `pytest`; the benchmark engine is
  stdlib-only, so the replay above is a real execution, and the regression test runs under the
  lane's no-pytest shim

## 6. Claim ceiling

Operational-resume verification only. This report creates no new product measurement, moves or
re-derives no frozen bar, rubric, threshold or verdict contract, lifts no DO-NOT-SERVE order,
certifies no packet admission, claims no jurist utility, and is **not** an independent audit of
run 43357838904 or of this run. `continue_recommended=false`; `human_gate_ready` and
`machine_gate_ready` stay false. A future independent auditor must write its own
`results/audit/evaluation/CYCLE_43359487892_GATE.json` from the audit-job checkout.
