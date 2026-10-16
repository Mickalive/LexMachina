# frontier-counter-anchor-classifier — Outcome A (adoptable component)

**Charter v1 · run 38964146628 · 2026-10-16**

## Verdict

**OUTCOME A — ADOPTABLE COMPONENT.** A sentence-anchored, abstain-first label
decision function raises counter-label **support from 5/65 = 0.0769 (incumbent)
to 5/5 = 1.0 among the labels it emits**, with **INVERTED == 0**, on the same
65 rows of the same 3 bundles under the **FROZEN** rubric. It cuts yield from 65
to 5 and converts the 60 unsupported labels into **counted abstentions**. The
trade is published side by side (support rate, abstention count, yield), not
hidden. Acceptance tests (1)–(8) pass.

## What was built (not a memo)

A runnable, drop-in decision function plus its scoring harness and tests:

- `frontier/frontier-counter-anchor-classifier/frontier_counter_anchor_classifier/counter_anchor_classifier.py`
  — `decide_label(row, frozen_rules, anchor_profile) -> LabelDecision`.
  Emits `{supporting, contrary, limiting}` ONLY when the row's own cited
  passage carries both a DOMAIN anchor to the question and a frozen
  counter-intent marker in the decision's own language, and is not a fragment,
  not a procedural formula without a marker, and not a polarity-inverted
  construction; the PIVOT anchor, expected language and non-foreign legal_area
  must also hold. Otherwise it emits a COUNTED `ABSTAIN` with the
  frozen-precedence reason code and a deterministic uncertainty.
- `frontier/.../run_head_to_head.py` — one run, same rows, same frozen rubric:
  reproduces the incumbent, runs the candidate, proves non-vacuity.
- `frontier/.../vendored/` — the frozen-rubric scoring modules
  (`normalize`, `rules`, `rubric`, `extract`, `injection`) vendored
  **byte-identically** from the accepted cycle branch that produced
  LABEL_HALF.json. No rubric, lexicon, bar or threshold re-authored.
- `tests/frontier/frontier-counter-anchor-classifier/` — 22 tests pinning the
  ABSTAIN contract (empty evidence can never be confident; the 16 accepted
  `evidence_absent` rows at uncertainty 0.95–1.0 all abstain; the 5 accepted
  SUPPORTED rows all emit; both controls strictly below).

## Freeze-first (acceptance 1)

`RULES_LABEL.json` copied byte-identically to
`results/frontier/frontier-counter-anchor-classifier/RULES_LABEL.json`;
sha256 re-proved before any scoring:

```
4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608  == frozen
```

## Head-to-head on the same 65 rows in the same run (acceptance 3, 4)

| | incumbent (reproduced) | candidate |
|---|---|---|
| labels emitted | 65 | 5 |
| supported (frozen rubric) | 5 | 5 |
| **support rate** | **0.0769** | **1.0 (among emitted)** |
| INVERTED | 0 | 0 |
| abstentions | — (shipped as labels) | **60** |
| yield | 65 | 5 |

- **Incumbent reproduced byte-identically**: this run re-scored the bundle's
  issued labels under the vendored frozen rubric and matched LABEL_HALF.json on
  all 65 rows (0 divergent, 0 only-in-either). The accepted 5/65 = 0.0769 is
  reproduced, not explained away.
- **Candidate is strictly better on support** (0.0769 → 1.0) with INVERTED == 0.
- Per bundle (incumbent): de 25/2, fr 15/0, it 25/3.
- Candidate abstention reasons: `evidence_absent` 16, `pivot_absent` 38,
  `no_intent_marker` 4, `no_domain_anchor` 2 — each matching the frozen
  harness's per-row reason code exactly (0 mismatches).

## Non-vacuity proven, not asserted (acceptance 5)

Two controls scored under the **same** frozen rubric, both **strictly below** the
candidate (1.0):

- **Inverted-label control** (frozen injection rows INV-INV-01/02, appeal
  rejected / lower ruling confirmed labelled counter): support **0/2 = 0.0**.
  The candidate's gate abstains on both (`polarity_inverted`).
- **Swapped-evidence control** (the candidate's 5 emitted rows with their cited
  evidence swapped cross-bundle for another decision's text): support **0/5 =
  0.0**. The candidate's gate abstains on all 5 (`no_intent_marker`).

A tie would void the run; the controls do not tie.

## Integration contract (acceptance 7)

`results/frontier/frontier-counter-anchor-classifier/INTEGRATION_CONTRACT.json`
states the drop-in path, the required bundle fields (`counter_status`,
`counter_evidence`, `title`, `regeste`, `language`, `legal_area`, `rank`,
`decision_id` + the question anchor profile + the frozen rules), what happens to
yield (65→5) and to the visible counter ring (5 evidence-backed counters; the
other 60 stay visible as ordinary/unevidenced rows), and the claim ceiling with
the machine-checkable forbidden construction patterns copied from the accepted
snapshot. **Core Product remains the integrator and decides adoption or
decline.**

## Claim ceiling

The component measures and decides the **support of counter labels as issued**
under the frozen rubric. It **never asserts that a specific decision IS
supporting, contrary or limiting**; those remain the product's labels. See
`results/frontier/frontier-counter-anchor-classifier/CLAIM_CEILING.json`.

## Out-of-scope writes (acceptance 8)

Nothing under `product/`, `evaluation/`, `results/product/`,
`state/product.json`, `.github/`, or any UI asset. The component is a pure
decision function; rendering the abstain marker is Product's job.

## continue_recommended

**false.** Outcome A is reached; the charter's stop-promote rule terminates it
here. No further cycle under the same charter is justified — the rubric is
frozen and post-hoc tuning would invalidate it. Adoption is Product's decision.
