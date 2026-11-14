# Operational resume — evaluation lane, direction v68

Run: `43565032175` (resumes snapshot `43559166421`)
Snapshot head: `c40cd9288bbcab02a5489bd768e2a329f4dea218` (62-file delta from
`35d8d64941b76ab59f931915f1f59ac97e07041f`)
Lane: evaluation · Direction: 68 · Mode: `OPERATIONAL_RESUME`

**Status: `PENDING_INDEPENDENT_AUDIT`; `accepted_as_evidence=false`.**
This is a producer-authored verification, not an audit verdict, not a promotion
and not a new product claim.

Read first: `reports/evaluation/AUDIT_BRIEF_43559166421.md` and
`results/evaluation/operational_resume_43559166421/AUDIT_INDEX.json`.
Fast read-only check:
`python3 -m evaluation.operational_resume_43559166421 --phase verify`.

## 1. What failed, and why this is a resume

Run `43559166421` did **not** fail as a producer:

- team job: `success`, 04:57:42–05:24:14Z (1592 s); Run lane cycle, state
  validation, junk cleanup, write-scope enforcement and snapshot persistence all
  succeeded;
- audit job: `failure`, 05:24:17–06:10:18Z (2761 s), failing only at
  **“Independent audit”**, with `LEX_WORK_QUANTUM_EXPIRED seconds=2700` and
  `Process completed with exit code 78`;
- “Enforce audit scope and read gate” and “Persist audit snapshot” were
  `skipped`; `integrate` was `skipped`; no audit ref or gate exists.

Failure class: `ORCHESTRATION_AUDIT_WORK_QUANTUM_EXPIRED`. The same class has
now consumed `43531218191`, `43542378874`, `43550420112`, `43554928192` and
`43559166421`. The producer cannot edit `.github/**`; this run reduces audit
work (compact index + read-only fast verify) and does **not** assert the quantum
problem is fixed. `43541879339` (zero-delta guard, rc 67) and `43542234373`
(launch failure, exit 1) are preserved as separate negative results.

## 2. Snapshot verification (H1–H3)

- **H1 — diagnosis.** Team success end-to-end; audit quantum expiry as above;
  persistence reached the snapshot head; gate/persist/integrate skipped; no
  audit gate. Record:
  `results/evaluation/operational_resume_43559166421/diagnosis_43559166421.json`.
- **H2 — recurrence.** Five team-success/audit-exit-78 runs; no audit gate for
  any; zero-delta and launch-failure runs preserved. Record:
  `.../diagnosis_chain_43565032175.json`.
- **H3 — preservation and replay.** The snapshot delta is exactly 62 files,
  all 33 frozen pins re-hash, and no auditor-namespace path is written. The
  deliverable of record remains `PRODUCT_FALSIFIED` (exit `1`, packet
  `39319405429`, direction `68`, 3 questions, 0 counter-authority rows issued).
  A fresh out-of-tree replay reproduces every measurement-bearing field **under
  a socket guard** (network forbidden). Standing records `43397701490` and
  `43531218191`, and the ordered item (1) correction of record, are byte-intact.
  The replay is classified `OPERATIONAL_REEXECUTION_NOT_NEW_CLAIM`. Record:
  `.../deliverable_verification_43565032175.json`.

## 3. Ordered v68 work (H4)

- item (1): **PRESENT_AND_VERIFIED** —
  `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md`,
  `results/evaluation/bypass_clause_correction/40144816305.json`.
- item (2): **`NOT_YET_DISCRIMINATING`** — mount `7be4480e` (direction names
  `8b5b08dd`); 50/50 fixed-path bundles byte-identical to already-measured
  bytes (zero delta); full named 15-member family not regenerated
  (server/served 3 vs 4; offline/rent-default 18 vs 11); member-for-member
  ceiling 14/15. **No conditional re-measure was run.** Record:
  `.../ordered_work_43565032175.json` and
  `results/evaluation/v68_item2_family_gate/43565032175.json`.
- item (3): **STANDING_RECORD_UNTOUCHED** (`43397701490`, `43531218191`).
- item (4): **REPORT_ONLY_WHERE_QUOTED**.
- item (5): **HONOURED_OPERATIONAL** — this cycle is operational verification,
  not a new same-question measurement.

## 4. Audit readiness (H5)

The resumed snapshot is checked by the state-integrity gate, the nested
evidence-ref guard, the live write-scope classifier, the evaluation lane suite,
and the selected reusable suites under `evaluation/no_pytest_runner.py`
(`pytest` is absent in the producer image). The lane suite records the pytest
sub-check as a skip, not a pass. Observed: state integrity `ALL_CHECKS_PASS`;
nested refs `0` unresolved; write scope `SCOPE_CLEAN` with `0`
auditor-namespace paths; lane suite `overall_pass=true`; reusable suites
7/7 (fast-MVP recall), 8/8 (minimal CA), 9 passed + 3 unsupported (counter-
authority v68), 10/10 (this resume); H5 instrument runtime 158.5 s. Exact
verdicts are in `.../audit_readiness_43565032175.json` and
`.../summary_43565032175.json`.

Non-gating reds, preserved rather than hidden:

- `tests/evaluation/test_operational_resume_43554928192.py` fails by design
  after this resume because it hard-codes `github_run=43559166421`; it is kept
  unmodified as a historical lock.
- `tests/evaluation/test_mount_provenance_gate.py`: 8 pass / 1 fail / 4
  unsupported under the shim; pre-existing and not introduced here.

## 5. State and provenance

Both `state/evaluation.json` and `evaluation/state/evaluation.json` advance
additively to `github_run=43565032175`, keep `accepted_run_id=40265377500`, and
disclose `PENDING_INDEPENDENT_AUDIT` with `accepted_as_evidence=false`.
`continue_recommended=false`. The accepted-state index on `origin/main` still
reports `40258497460`; the authoritative accept commit `ea98384e` and PASS gate
`results/audit/evaluation/CYCLE_40265377500_GATE.json` are the basis for
keeping `40265377500`, and the discrepancy is disclosed rather than edited.

The only network calls in this resume were unauthenticated reads of public
GitHub Actions run/job/check-run metadata, captured before the instrument ran;
the instrument itself makes zero network calls. Capture provenance:
`.../api/CAPTURE_MANIFEST.json`.

## 6. Claim ceiling

This report proves that the persisted snapshot is internally consistent,
byte-pinned, replay-reproducible and audit-ready. It does **not** prove a
product measurement, does not move or re-derive any frozen bar, does not
re-score a family, does not admit a packet, does not issue a serve verdict, and
does not claim the map helps a jurist. Promotion requires an independent audit
verdict.
