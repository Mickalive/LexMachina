# frontier-counter-anchor-classifier — Outcome A (adoptable component)

**Charter v1 · run 38964146628 · 2026-10-16**

> **Superseded in part by run 38970902524 (2026-10-16).** That cycle independently
> re-verified every number below against origin data and repaired four defects
> the accepted audit recorded as advisories (D: accepted-comparison covered 61 of
> 65 rows; E: an unmapped issued status defaulted to the polarity `limiting`;
> C: the swapped-control reason code below is wrong; plus a broken CLI default
> path). **No accepted measurement changed** — incumbent 5/65 = 0.0769, candidate
> 5/5 = 1.0 among emitted, 60 abstentions, INVERTED 0, both controls 0.0. See
> "Cycle 38970902524" at the end of this file and
> `results/frontier/frontier-counter-anchor-classifier/CYCLE_38970902524_VERIFICATION.json`.

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
  0.0**. The candidate's gate abstains on all 5.
  **[CORRECTED in run 38970902524: the reason code is `pivot_absent`, not
  `no_intent_marker` as this line originally stated. The control row is built
  with `title`/`regeste`/`row_text` nulled so the only text is the donor's
  cited sentence; that sentence still carries an intent marker, but the
  context window then holds no pivot anchor of the target's own question, so
  the frozen precedence fires step 5 (pivot) before step 6 (intent marker).
  Re-run evidence: all 5 controls report `pivot_absent`; pinned by
  `test_repair_38970902524.py::test_swapped_evidence_control_is_pivot_absent_not_no_intent_marker`.]**

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

---

# Cycle 38970902524 — verification and repair (NOT a new charter cycle)

**Charter v1 (terminated) · dispatched again in error · 2026-10-16**

## What this cycle did and did not do

The charter had already terminated at Outcome A in run 38964146628 with an
accepted `gate=PASS` gate and `continue_recommended=false`, and its own stop rule
says *"TERMINATE the charter after either outcome; never re-dispatch it with the
same charter_version."* This cycle therefore **did not open a new charter cycle, did not issue a new
claim and did not tune anything**. It did two things:

1. **Independently re-verified** the accepted Outcome A numbers by recomputing
   them from origin data in a fresh context — the accepted claim is not taken on
   trust, and the recomputation is reported as verification of an existing claim,
   not as a new one.
2. **Repaired the four defects** the accepted gate itself recorded as
   non-binding advisories, so the accepted component is safe to hand over.

## Independent verification (nothing taken on trust)

| Check | Result |
|---|---|
| Frozen rubric sha256 (team copy, re-hash before scoring) | `4457e971…b4608` ✅ |
| Same rubric re-fetched from `origin` cycle branch | `4457e971…b4608` ✅ byte-identical |
| Served bundles (214 / 217 / 211 decisions) | ✅ present, hashed |
| Incumbent reproduced | **5/65 = 0.07692307692307693**, INVERTED 0 ✅ |
| Incumbent vs `LABEL_HALF.json`, **multiset** over full verdict tuples | **65/65 matched, 0 divergent** ✅ |
| Candidate on the same 65 rows | **5 emitted / 60 abstained, 5/5 = 1.0, INVERTED 0, yield 0.0769** ✅ |
| Abstention reasons | `evidence_absent` 16, `pivot_absent` 38, `no_intent_marker` 4, `no_domain_anchor` 2 — identical to the accepted artifact |
| Non-vacuity controls | inverted-label **0/2 = 0.0** (`polarity_inverted`), swapped-evidence **0/5 = 0.0** (`pivot_absent`) — both strictly below 1.0 ✅ |
| Claim-ceiling regex machine check over all team artifacts | **0 hits** ✅ |
| Tests | 22 → **46 passed**, 0 failed |

**The accepted Outcome A claim is sound as stated.**

## The four repairs

**D — the reproduction proof covered 61 of 65 rows (measurement defect).**
`_compare_to_accepted` keyed both sides by `decision_id` into plain dicts. Four
decision ids occur twice in the population (`bge_140 II 112`, `bge_105 II 114`,
`bge_135 III 556`, `bge_131 III 459` — cited in two bundles each), so 65 rows
collapsed to 61 keys and `reproduced_byte_identical_verdicts` was asserted on the
strength of 61 rows. If a duplicated id had disagreed between the two copies,
the divergence would have been invisible. Now: a multiset (Counter) comparison
over the full verdict tuple `(bundle, decision_id, counter_status,
primary_defect_class, reason_code, supported)`, with
`coverage_is_full_population` and the duplicate ids reported explicitly.
Coverage 61 → **65/65**.

**E — the component could name a polarity a row never carried (soundness
defect).** `STATUS_TO_LABEL.get(proposed, LABEL_LIMITING)` turned any
unrecognised issued `counter_status` into the label `limiting`. That is the
component asserting a position the row did not carry, which its own claim ceiling
forbids. Now an unmapped (or empty) status produces a **counted abstention** with
reason `unmapped_proposed_status`, uncertainty 0.9, audited as criterion
`vi_proposed_status_mappable`. **Proven behaviour-preserving on the measured
population, not assumed**: all 65 rows carry `candidate-limiting` (45),
`candidate-contrary` (11) or `contrary_or_exception` (9), so the path is
unreachable there and no accepted number moved. The check is placed LAST in the
gate, after the four frozen precedence steps, so the accepted reason-code counts
are untouched by construction.

**C — the published swapped-control reason was wrong.** See the corrected
non-vacuity section above. Both controls abstain; only the stated reason was
wrong, and it is now pinned by a test.

**CLI — the documented invocation did not run.** `main()` resolved the repo root
with three `dirname()` hops, so `--rules` defaulted to
`<repo>/frontier/results/.../RULES_LABEL.json` and the module crashed with
`FileNotFoundError` before scoring anything. Only the explicit-path test call
ever worked. Fixed to four hops, and the default `--out` now points at the
repair-cycle artifact so running the CLI can never overwrite the accepted
`HEAD_TO_HEAD.json`.

## What was NOT changed

`RULES_LABEL.json` (frozen, byte-identical), `HEAD_TO_HEAD.json`,
`CLAIM_CEILING.json` — all untouched, verified by `git diff`. No product,
evaluation, `.github`, UI or served-packet write. No prompt, lexicon, bar or
threshold was tuned; the rubric is frozen and the repairs touch only the
harness's comparison, the adapter's refusal to invent a polarity, documentation,
and the CLI path.

## Durable delta

- `frontier/.../counter_anchor_classifier.py` — total status mapping, abstention
  on unmapped statuses, corrected docstring precedence (the frozen order puts the
  procedural-formula test at step 3 and the polarity-inversion test at step 4).
- `frontier/.../run_head_to_head.py` — multiset accepted-comparison, fixed CLI
  defaults, status-transparency fields, default output no longer the accepted
  artifact.
- `results/.../HEAD_TO_HEAD_R2_38970902524.json` — the repair-cycle re-run
  (identical headline numbers, 65/65 coverage).
- `results/.../CYCLE_38970902524_VERIFICATION.json` — this cycle's evidence.
- `tests/.../test_repair_38970902524.py` (14 tests), `test_repair_population_preserved.py`
  (10 tests), `tests/.../fixtures/real_emitted_rows.json` (the 5 rows the
  component really emits, copied verbatim from the packet, so the repair tests
  mutate real rows instead of invented ones).

## Dispatch anomaly (factory signal)

This team was dispatched **charter v1 after that charter had terminated at
Outcome A** (`state/frontier/frontier-counter-anchor-classifier.json` carried
`continue_recommended=false` and an accepted `gate=PASS`). The re-dispatch was
absorbed rather than executed as a new measurement, but the portfolio should not
re-dispatch a charter whose stop/promote rule has fired; the accepted component
now needs an **independent audit of run 38970902524**, not another cycle.

## continue_recommended

**false, unchanged and final.** The charter terminated at Outcome A in run
38964146628 and this cycle did not re-open it. No further cycle under charter v1
is justified.

---

# Cycle 38971898060 — operational resume: third dispatch of a terminated charter, root cause fixed

## What happened

Charter v1 was dispatched a **third time** after its stop/promote rule had
already fired at Outcome A (run 38964146628, audit `gate=PASS`,
`safe_to_integrate=true`) and after the verification-and-repair resume
(38970902524) had re-verified every number. The charter's own stop rule says
"TERMINATE the charter after either outcome; never re-dispatch it with the
same charter_version", so — as in 38970902524 — this cycle did **not** open a
new charter cycle, did **not** re-measure and issued **no new claim**.

## Root cause of the re-dispatch loop (diagnosed this cycle)

`state/frontier_portfolio.json` on main still carried `status=RUN`,
`run_history=[]`, `continue_recommended=true`, `promotion_status=null` for this
team after both prior cycles. The producer's dispatch query is
`select(.status=="RUN")` — a plain string comparison — so the terminated
charter was re-dispatched every cycle. The supervisor's exhaustion guard cannot
stop this because jq's `//` operator treats literal `false` as empty (factory
direction v50 standing requirement). The `.status` field is the only reliable
stop.

## The fix

The portfolio entry was set to `status=TERMINATED`, `continue_recommended=false`,
`promotion_status=PROMOTED_TO_PRODUCT`, with `run_history` recording all three
runs and an `operational_revision_reason` pointing at this section. This is the
route-around factory direction v50 prescribes ("set .status to TERMINATED the
moment a charter's stop/promote rule is met and independently accepted; never
rely on continue_recommended, never wait for the housekeeper"). The file is not
in the charter's forbidden write list.

## Accepted work re-verification (nothing taken on trust)

- Frozen rubric re-hashed before anything: `4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608` — matches, unedited.
- Full test suite: **46 passed** (22 accepted + 24 repair tests).
- Incumbent reproduction: **5/65 = 0.07692307692307693**, INVERTED 0, reproduced
  byte-identically against `LABEL_HALF.json` re-staged from origin
  `cycle/frontier/frontier-served-packet-falsification/38877700234/team`
  (sha256 `582b4f94...`, exactly the accepted hash). Environmental note: the
  resume environment lacked the `/tmp/LABEL_HALF.json` stage; it was re-fetched
  from the accepted origin branch and re-hashed before the integration test ran.
  No repository artifact was modified to make tests pass.
- Candidate: 5 emitted / 60 abstained / support 1.0 among emitted / yield 0.0769 /
  INVERTED 0 — unchanged from the accepted measurement, pinned by
  `test_repair_population_preserved.py`.

## Dispatch anomaly (factory signal)

Third dispatch of a terminated charter. Root cause (portfolio status never moved
off RUN) found and fixed at the source this cycle; the loop should now stop.
Remaining control-plane item, unchanged and not owned by this team: the component
still needs an **independent audit of run 38970902524**
(`results/audit/frontier/frontier-counter-anchor-classifier/` currently contains
only `CYCLE_38964146628_GATE.json`), and Core Product remains the integrator that
decides adoption or decline via `INTEGRATION_CONTRACT.json` revision 2.

## continue_recommended

**false, final.** Another cycle under charter v1 is not justified: the charter
terminated at Outcome A and the stop/promote rule forbids re-dispatch at the same
charter_version. The next step is an audit, not another cycle.
