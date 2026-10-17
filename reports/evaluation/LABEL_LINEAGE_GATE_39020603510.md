# CYCLE 39020603510 — counter-label LINEAGE regression gate

lane=evaluation · direction v50 · run 39020603510 · GitHub run 39020603510

## 0. What this cycle is, in one paragraph

Direction v50 gave this lane the two executable frozen-bar gates and they are
accepted and green. The gap this cycle closes is narrower and concrete: **the
counter-label gate could not see a counter-label-support collapse on any packet
the product can actually ship.** Its regression predicate was pinned to the
incumbent's 65-row population, so every packet whose scored-row count differed —
which is *every* rebuilt packet — was returned `NOT_APPLICABLE` with
`gate_blocks_build=false`. Accepted packet `38799024807`, which scores **0
supported of 7** (rate 0.0), was admitted by the label gate while the geometry
gate blocked the very same packet. This cycle adds one executable gate that
applies direction v50's **own** predicate ("label support below 5/65") on the
qid-set lineage the geometry gate already uses, proves it on real accepted bytes
in both directions, and emits the machine-readable two-bar packet-admission
input that Product direction obligation (1) requires. It invents no threshold.

## 1. Hypothesis (frozen BEFORE execution)

`results/evaluation/label_lineage_gate/freeze/FROZEN_HYPOTHESIS_39020603510.json`
(commit `757bcb2c`, written before the new module existed).

The prediction is unusually strong because it is arithmetic on numbers that were
**already frozen in accepted records**: pooled per-packet support rates from
`39004097533` and per-bundle geometry counts from `38993062549`. The hypothesis
could only fail if those accepted records are wrong or `5/65` means something
other than what it says.

Two defects in my own freeze prose were found by executing it and are corrected
by erratum, never by editing the freeze:
`results/evaluation/label_lineage_gate/freeze/FREEZE_ERRATA_39020603510.json`.

## 2. The gap, as accepted evidence of record

| accepted finding (enforced, holds=true) | content |
|---|---|
| `L2_gate_admits_total_label_collapse` | packet `38799024807` scores 0/7 (rate 0.0) and is admitted, `gate_blocks_build=false`, while the geometry gate blocks it |
| `L3_gate_population_predicate_is_confounded` | only **1 of 3** accepted-lineage packets could receive any regression verdict at all |
| `L4_rate_and_count_semantics_disagree` | the count reading would FAIL `38812599575`, whose rate 1/9 is **strictly better** than the incumbent 5/65 |
| `naive_consumer_trap` (`VERDICT_CONTRACT.json`) | `exit 0 + blocks false + n_supported == 0` is reachable — it falsifies any consumer rule of the form "no block ⇒ the label bar was met" |

Direction v50 mandates a **rate** predicate. The accepted code applied a
**count** predicate at a pinned population. Those are different predicates, and
L4 proves the implemented one is the wrong reading of the mandated number.

## 3. What was built

| file | role |
|---|---|
| `evaluation/frozen_bars/label_lineage_gate.py` | the gate (598 lines, stdlib only) |
| `evaluation/frozen_bars/LABEL_LINEAGE_VERDICT.json` | verdict contract, own digest pin `016bffe5…` |
| `evaluation/frozen_bars/run_label_lineage_gate.py` | entry point, `sweep` + `adjudicate`, exit 0/1/2 |
| `tests/evaluation/test_label_lineage_gate.py` | 25 tests incl. breaking fixtures |
| `results/evaluation/label_lineage_gate/39020603510_sweep.json` | claim-bearing record |
| `results/evaluation/label_lineage_gate/adjudications/*.json` | 5 per-packet two-bar verdicts |

**Enforced predicate** — the only number, derived at runtime, never re-typed:

```python
PREDICATE_RATE = label_gate.INCUMBENT["n_supported"] / label_gate.INCUMBENT["n_scored"]  # 5/65
FAIL_REGRESSION := lineage AND n_scored > 0 AND support_rate < 5/65   # strict; equality passes
lineage         := set(bundles) == {de-kapitalverletzung, fr-bail-entretien, it-responsabilita-medica}
```

The accepted gate, the accepted geometry gate, `run_bar_gates.py` and
`VERDICT_CONTRACT.json` are **untouched**; the accepted verdicts are published
side by side so every previously accepted statement stays computable.

## 4. Result — every operative prediction held

`frozen_prediction_verification.verdict = ALL_PREDICTIONS_HELD`, all 8 evaluated
checks PASS (P1 ×3 packets, P2, P3, P4, P5, P6).

### Blocking matrix (measured, from `39020603510_sweep.json`)

| packet | scored | supported | rate | **lineage gate** | accepted label gate | accepted geometry gate |
|---|---|---|---|---|---|---|
| `38799024807` | 7 | 0 | 0.0 | **FAIL — blocks** | NOT_APPLICABLE, no block | FAIL (it 4<5) — blocks |
| `38812599575` | 9 | 1 | 0.1111 | PASS — no block | NOT_APPLICABLE, no block | FAIL (fr 4<5) — blocks |
| `38839347028` (incumbent) | 65 | 5 | 0.0769 | PASS — no block | PASS — no block | PASS — no block |
| `38838116453` | — | — | — | NOT_APPLICABLE (2 of 3 qids) | — | — |
| `offline_machinery_rehearsal` | — | — | — | NOT_APPLICABLE (0 of 3 qids) | — | — |

- **L2 closed**: the 0/7 total collapse now blocks. Label non-incumbent blocks **0 → 1**.
- **L3 closed**: admissible in-scope packets **1 → 3 of 3**.
- **L4 now measured, not asserted**: the count-without-population-pin
  counterfactual diverges from the enforced rate reading on **exactly
  `38812599575`** — the strictly-better-rate packet L4 names.
- **naive-consumer trap closed**: `n_supported == 0` with no block is unreachable on lineage.
- **Incumbent reproduced byte-exactly**: 5/65, classes `OFF-DOMAIN 38 / UNBACKED 22 / SUPPORTED 5 / INVERTED 0`, geometry `de 6 / fr 5 / it 5`.

### Non-vacuity, both directions

1. **Minimal delta** — one field (`counter_evidence`) on **one** row:
   `n_scored 65 → 65` (unchanged), `n_supported 5 → 4`, rate `0.076923 → 0.061538`,
   `PASS_NO_REGRESSION → FAIL_REGRESSION`, blocks=true. Breaking fixture: with
   `PREDICATE_RATE` forced to 0 the control correctly reports not-proven.
2. **Label-only attribution** — all scored evidence blanked: label `5/65 → 0/65`
   blocks, while the accepted geometry gate stays `PASS_NO_REGRESSION` at
   `de 6 / fr 5 / it 5`. The two-bar input therefore carries **independent**
   label content, which the accepted gate could not.
3. **No false block** — no accepted packet at or above the incumbent rate is
   blocked. `38812599575` (rate 0.1111 > 0.0769, count 1 < 5) passes, which is
   precisely the artifact the count reading would have falsely blocked.

### Two-bar admission input (`schema lex-evaluation-admission-input/2`)

`block_reasons` names which bar fired: `38799024807` → both;
`38812599575` → geometry only; `38839347028` → none, exit 0.

## 5. Two honest negatives — what this does NOT close

1. **The geometry incumbent is not a floor** (accepted `F2_INCUMBENT_NOT_A_FLOOR`,
   now **computed** from the rows rather than restated): minimum over the accepted
   population is `de 6 / fr 4 / it 4` against enforced incumbent `de 6 / fr 5 /
   it 5`. The gate still blocks those packets, but "PASS_NO_REGRESSION" must not
   be read as "no geometry defect exists anywhere". Direction v50 fixes the
   incumbent; this lane does not move it and invents no alternative floor.
2. **Label and geometry are not at parity, and should not be.** The freeze's P1
   prose claimed "2 of 2 … matching the geometry gate's 2 of 2"; its own predicted
   table and the measurement both say **1 of 2**. The divergence is on
   `38812599575`: geometry-deficient (fr criterion count 4) while its label rate
   is fine. These are two **different measures** — pooled support *rate* vs
   per-bundle criterion *count* — so a divergence is expected, not a defect. No
   gate was altered to manufacture agreement; the divergence is reported.
   Corrected by erratum E1, not by editing the freeze.

Also **stated, not patched**: the enforced predicate is a rate with no
minimum-sample floor, because inventing one is forbidden. A packet with very few
scored rows can carry a high rate on a small sample.

Preserved unresolved by design: **`L5`** — the frozen rubric's declared primary
population is still not the gate's incumbent population. Re-pointing or
re-freezing `RULES_LABEL.json` is out of this lane's scope.

## 6. Exit-code design (why a sweep cannot be permanently red)

The accepted population legitimately **contains** packets below the incumbent on
both bars. A sweep that exited 1 whenever any population member regressed would
be permanently red by construction — the never-green/never-red loop direction v50
exists to break. So:

- `sweep` → exit 0 when the measurement completed and the frozen predictions held.
- `adjudicate` → exit 0 / 1 / 2 on **one** packet: the build-blocking decision
  Product actually needs.
- exit 2 is now split into two *distinguishable* verdicts: `NOT_APPLICABLE`
  (genuinely off-lineage, e.g. `38838116453` at 2 of 3 qids) vs
  `ENVIRONMENT_ERROR` (broken input). A consumer must read the field, not the code.

## 7. Nothing accepted was moved

| check | result |
|---|---|
| `RULES_LABEL.json` | `4457e971…` identical |
| `RULES_GEOMETRY.json` | `a7452748…` identical |
| `VERDICT_CONTRACT.json` | `b9cdb894…` identical, unmodified |
| reality benchmark / contract | `ff57f556…` / `06781743…` identical, not re-run |
| retrieval benchmark | `187b0e54…` identical, not re-run |
| vendored rubric bytes | 14/14 unchanged |
| `git status` on all frozen + accepted gate files | **empty** |
| accepted `run_bar_gates` | still exit 0, labels 5/65, geometry 6/5/5 |
| 174k suite | closed, not run |
| lane suite | **PASS 47/47** (was 43/43; +4 new digest checks) |
| active lane pytest | **214 passed**, 0 failed |
| new tests | 25 passed with mount; 13 passed + 11 by-design skips without it |
| entry point without the mount | exit 2 `ENVIRONMENT_ERROR`, never a verdict (same as the accepted entry point) |

### Two defects in this cycle's own new code, found and repaired in-cycle

1. **Population discovery looked for bundles in the packet root, not under
   `questions/`** — the first sweep silently found 0 in-scope packets and would
   have reported vacuous success. Fixed to probe both, with the resolved
   directory recorded. A parity claim over an empty population is now `null`,
   never `true` (breaking test included).
2. **The L4 divergence was keyed to the wrong reading** — it first fired on
   `38799024807` (where the *population-pinned* count reading is merely blind)
   instead of on `38812599575` (where the rate/count question is actually
   isolated). Fixed to key L4 to the pin-removed counterfactual; both flags are
   now reported separately and explicitly not conflated.

## 8. Product decision unlocked

The two accepted bar verdicts are now a **complete machine-readable admission
input over the whole accepted packet lineage**, so Product direction obligation
(1) no longer has to rely on the accepted label gate's `gate_blocks_build`,
which was structurally unable to observe a collapse. The standing accepted
**DO-NOT-SERVE** order on packet `38839347028` is unchanged and is now
machine-reproducible: it adjudicates `PASS_NO_REGRESSION` on both bars with
`absolute_bars_enforced=false` — i.e. **not blocked on regression, still blocked
on the two absolute bars**, which stay red and reported-not-enforced.

## 9. Claim ceiling

At most, and verified by recomputation: the counter-label regression gate blocks
every accepted-lineage packet whose pooled support rate is strictly below the
incumbent `5/65`, including the `0/7` collapse the accepted gate admitted; it
reproduces every accepted incumbent number exactly; it uses no number but the
incumbent; and it says **nothing** about the absolute bars, retrieval or
counter-authority recall, source validity, the served packet's admissibility, or
whether the map is useful to a jurist. **human_gate_ready stays false.**

## 10. Recommendation

`continue_recommended = true` for exactly one same-question successor:
adjudicate the **rebuilt** served packet the moment Product ships one (any sha
change), because that is the first input on which this gate's value is actually
tested — today it has only been proven against historical packets. Nothing else
in this question is open. Not re-run: the four frozen reality legs, the
retrieval/counter-authority gates, the 174k suite, and both Frontier candidates
(evidence-anchored counter classifier, query-conditioned geometry), which are
explicitly not re-measured here.

Control-plane items recorded, not patched (`.github/**` is out of lane scope):
the supervisor `continue_recommended` guard remains dead code (factory-wide
requirement 9), and `tests/evaluation/test_frozen_bar_gates.py` is **not** in
`evaluation/lane_suite.py`'s pytest scope, so those 16 pins run only when that
file is invoked directly.