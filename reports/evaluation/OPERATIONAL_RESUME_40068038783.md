# Operational Resume — evaluation cycle 40068038783 (resume of zero-delta run 40067656881)

**Direction:** v66 · **Lane:** evaluation · **Date:** 2026-10-24
**Base:** `origin/cycle/core/evaluation/40067656881/team` @ `24e24bfc` (lab/evaluation tip, clean tree)
**Freeze:** `evaluation/OPERATIONAL_RESUME_40068038783_HYPOTHESIS.json` committed BEFORE claim-bearing work.

## 1. Orchestration diagnosis (V1)

Runs **40064635075** and **40067656881** ("Core evaluation dirV66 repair0") both
concluded `failure` at the **"Run lane cycle"** step; audit and integrate were
skipped; the team snapshots (and `team-attempt-1`) of both runs point at
`24e24bfc` — **zero durable delta**, identical to the accepted lab/evaluation
tip. Job logs require authentication (HTTP 403), so the precise producer exit
code is unreadable; provider-death (requirement 20) and rc-78/rc-67 classes
(requirement 10) are both consistent and the attribution is **hedged**.
Classification: **ORCHESTRATION** — not evidence, not product, not human-gate.
Zero work lost (there was no committed work to lose). Full record:
`results/evaluation/orchestration/40068038783_failure_chain_diagnosis.json`.

Notable timing fact: Core Product's accept `3495c1336` (cycle **40064639100**,
the v66 **P0 content-quality filter landing**) landed 05:32:55Z, *during*
40064635075's lifetime; that run did not survive to measure it. This resume
does.

## 2. Item (1) hygiene of blocked run 40047820460 (V2, ordered first)

- **(a) pointers:** VERIFIED ACCEPTED-BASE. `minimal_ret_ca_benchmark.
  latest_confirmation_record` = `results/evaluation/
  minimal_ret_ca_benchmark/40034814235.json`; **no reference to run
  40047820460 exists anywhere** in the canonical state (the blocked run never
  landed). No revert needed.
- **(b) nested refs:** the new guard (`evaluation/nested_evidence_refs_guard.
  py`, item-(1)(c) deliverable) walked every ref-shaped string in
  `state/evaluation.json` — 380 values, top-level 228/228 resolving — and
  found **5 unresolved NESTED refs** (pre-fix artifact
  `..._prefx_nested_evidence_refs.json`):
  1. ×4 `results/evaluation/orchestration/40011795717/producer_work_state_and_next_move.txt`
     — **directory typo**: the artifact was committed by cycle 40012474431
     under the sibling `.../40006151200/` directory; the `40011795717/` path
     never existed. Corrected in state with disclosure.
  2. ×1 `results/evaluation/orchestration/40062917685_counter_evidence_quality_pytest_shim.json`
     — **phantom record** (requirement-33 class): the accepted cycle
     40062917685's state claimed a pytest shim that was committed **nowhere**.
     Re-derived under THIS run id (`40068038783_pytest_shims.json`,
     19/19 living-suite tests pass with real pytest 9.1.1); the state pointer
     is re-pointed with full disclosure of the phantom.
- **(c) guard extension:** landed — the guard resolves nested values against
  the worktree, the accepted cross-lane mounts and fetched git history
  (branch-scoped historical artifacts such as `CYCLE_40017649220_GATE.json`
  resolve as `RESOLVED_BRANCH_HISTORY`).
- **(d) index re-derivation:** `evidence_index_resolving_refs_n` re-derived
  and tied to the post-fix guard artifact.

## 3. Item (4) CONDITIONAL RE-MEASURE (V3) — triggered, executed

**Trigger:** product accept `3495c1336` (cycle 40064639100, PASS gate) landed
the P0 content-quality filter in `product/query/counter_evidence_span.py`
(`passes_content_filter`, `detect_letterhead_zone`, markup and language-marker
predicates; `content_filter=True` default).

**Instrument:** `evaluation/counter_evidence_quality_remeasure.py` — re-runs
the FROZEN item-(2) predicates (imported by value; frozen instrument sha
`aac86527…` pinned and re-verified at runtime, control C4) over (a) the
accepted 15-bundle baseline population and (b) the NEW head's shipped slice
`20261024T024341Z` (sha `9de09a28…`), with controls C1–C3 re-run.

**Result — REPAIR_NOT_CONFIRMED (exit 1):**

| class | baseline (of record 40062917685) | new head | eligible rows | verdict |
|---|---|---|---|---|
| D2_letterhead_zone | 10 | **1** | 1 | **STILL-DEFECTIVE** |
| D3_markup_residue | 4 | 0 | 1 | CONFIRMED-REPAIRED |
| D4_language_marker_mismatch | 4 | 0 | 1 | CONFIRMED-REPAIRED |

- Baseline re-probe **NORMALIZED-IDENTICAL** to the accepted baseline of
  record (14/14 defective, D2=10 D3=4 D4=4, 2 distinct decisions).
- The surviving D2 is the same known decision **`gr_gerichte_ERZ 2010 25`**,
  evidence grounded in `full_text` at **offset 0** (court letterhead in three
  languages) on the new head's own shipped offline slice. The P0 filter has
  **not** cleaned the shipped-slice emission for this row.
- Artifact: `results/evaluation/counter_evidence_quality_remeasure/40068038783.json`;
  report: `reports/evaluation/COUNTER_EVIDENCE_QUALITY_REMEASURE_40068038783.md`.

## 4. Item (3) FROZEN-SCORER PATH RECONCILIATION (V4) — executed

**Instrument:** `evaluation/scorer_path_reconciliation.py`, side by side on
the packet-of-record 39319405429 exact bytes at the same product head:

- **Side A (frozen scorer):** `mf::counter_authority_surface`
  (`mapping_free_recall_falsifier.py:305-317`, statuses from
  `RULES_LABEL.json rubric.scored_statuses`, re-hashed REPORTED-ONLY
  `4457e971…`) → **n_issued = 0** on served bytes (all three languages).
- **Side B (product span seam, exact harness arm code path):** baseline 0 /
  unguarded **6** / guarded **1** — **identical** to the accepted pre-filter
  measurement of record (`CYCLE_39986094168_span_selection.json`). The P0
  filter has **no packet-level emission effect**.
- **Contract question answered:** the guarded emitted row
  (`bge_136 III 196`, fr, `candidate-limiting`, 286-char evidence, **zero**
  frozen D2/D3/D4 defects) is **INSIDE** the frozen scorer's input contract by
  shape — when the frozen predicate is applied to the **post-transform**
  bytes it returns **n_issued = 1**. The scorer's contract is the bundle
  **bytes as written**; the span seam is a **pre-scorer stage whose output is
  absent from the served packet**. The requirement-36 divergence is a
  **TRANSFORM-PATH** divergence, resolved here with **zero scorer edits**.
- Artifact: `results/evaluation/scorer_path_reconciliation/40068038783.json`;
  report: `reports/evaluation/SCORER_PATH_RECONCILIATION_40068038783.md`.

## 5. Tests (V5)

Living suites, real pytest 9.1.1: **19 passed / 0 failed**
(`test_counter_evidence_quality_benchmark.py` 7, remeasure 4, reconciliation 4,
nested-refs guard 4). The accepted historical guard suite
`test_operational_resume_40044626742.py` is **cycle-pinned** (expects
direction 65 / its own history base) and reports 3 pin-failures against the
new state — **disclosed, not charged, not edited** (see
`40068038783_pytest_shims.json`).

## 6. Standing posture (unchanged, fail-closed)

Both DO-NOT-SERVE orders stand · packet admission fail-closed ·
`human_gate_ready=false` · `machine_gate_ready=false` ·
`ready_for_owner_session=false` · comparative map-vs-ranked-list **VACUOUS**
(served-bytes n_issued=0) · frozen bars/rubrics re-hashed REPORTED-ONLY and
unmet on the v3 bytes · no 174k benchmark rerun · no bar/rubric/threshold/
verdict-contract edit · no historical record overwritten ·
`owner_decision_required=false`.

## 7. Recommendation

**CONTINUE** under the same v66 question. Discriminating purpose: the re-measure
falsified full repair (D2 persists on the shipped slice) and the reconciliation
shows the packet path unchanged; any accepted product change to the shipped
counter-evidence emission path triggers an immediate re-run of the frozen
item-(2) probe protocol under a NEW run id.
