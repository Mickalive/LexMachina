# Verification 38850765576 — frontier-counter-label-integrity (no-change, TERMINATE)

Eighth dispatch of a TERMINATED, charter-exhausted team under the SAME charter
(charter_version 1). Operational resume from persisted producer snapshot
38850302366 (commit ff80bef, clean tree at mount).

## What this run did

Verification only. The charter's sole continuation clause was invoked and SPENT
in run 38848314260 (harness defect repaired, adversarially reviewed, hardened,
96/0). This run found no new concrete defect in the team's own harness, no
post-repair artifact, no population change. Nothing re-scored, nothing
re-frozen, no threshold touched, no verdict changed, no historical artifact
edited or deleted.

## Checks (all pass)

- Artifacts re-hashed to state-file claims: RULES.json `4457e971df3dc5d1…`,
  REPORT.json `e97a4e9c9377d858…`, NON_VACUITY.json `0ad7c65de575df51…`,
  FREEZE_PROOF.json `7ca4d133810897f9…` — all match.
- Test suite: **96 passed / 0 failed** (class-aware audit-contract repair holds).
- REPORT.json reproduced **byte-identically** via `cli --all` to a `/tmp` out dir
  (primary 0/7, secondary 0/39, LABEL_UNSOUND).
- NON_VACUITY.json reproduced **byte-identically** via `cli --non-vacuity-only`
  (7/7 classes, 5 defect criteria).
- Single-bundle CLI form (`--bundle fr-bail-entretien`) correctly returns
  INSUFFICIENT_POPULATION (1 of required 7) per charter rule (7) — the specified
  behaviour on a partial population, not a defect.
- Frozen inputs re-hashed: 9/9 match frozen sha256 on the accepted mount;
  3/3 admissibility siblings match; 5/5 fixture exclusions match.
- Primary population unchanged: 7 candidate-limiting rows (DE 3, FR 1, IT 3).
- Post-repair probe negative: no `product/query/adversarial_retrieval.py` and no
  `results/product/adversarial_retrieval/` on the workspace or the accepted
  mount; no new accepted live bundles.
- Freeze: RULES.json hash unchanged and FREEZE_PROOF.json byte-identical;
  ordering (416c2aec → 0849f6ed, 388 s margin) stands on the re-proofs recorded
  in runs 38845649012 / 38846758718 / 38848314260 — the per-commit history is
  not present in this squashed mount and was not re-derived.

## Operational diagnosis

Not a measurement failure and not a charter failure. The lane re-dispatched a
TERMINATED charter-exhausted team whose continuation clause was already spent.
This is the eighth dispatch under an empty charter-side run_history. The
re-dispatch loop is a lane-scheduling condition (a terminated charter with an
empty charter-side run_history keeps looking dispatchable), not missing
evidence or an open defect.

## Disposition

Verdict unchanged: **LABEL_UNSOUND** (primary 0/7, combined 0/46).
`continue_recommended: false`, `cycle_status: TERMINATE`. A before/after pair
against a promoted repair is a NEW charter for the director to raise, not a
continuation of this one. This cycle does not self-commit; it leaves an
in-scope uncommitted delta for the workflow's persist step.
