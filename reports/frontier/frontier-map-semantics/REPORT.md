# frontier-map-semantics charter v2 — verdict report (run 38839351403,
measurement freeze; completed and verified under operational resume run
38840496500 — see §8; verified again and non-vacuity repaired under operational
resume run 38846038296 — see §9; re-dispatch on byte-identical material with
the freeze-ordering caveat closed under operational resume run 38849595347 —
see §10; audit repair of CYCLE_38849595347 R1–R4 under run 38851887303 —
see §11. The promoted decision and every verdict below are UNCHANGED by §11.)

Promoted decision (machine-checked by `frontier/frontier-map-semantics/check_decision.py`, ALL-CHECKS-PASSED):

> FAIL with NO working in-budget alternative: 0/3 gate bundles pass the frozen rule (DE 5/11, FR 5/11, IT 4/11), dominant query-language shares are 0.055/0.041/0.111 with ARTIFACT true on DE+IT (FR dominant share collapses 0.557→0.217 with ARTIFACT false only on the frozen 0.40 shell-fraction clause), RELATIONS and LABEL_CONTENT pass on all three (25 typed edges, 1.0 content — both charter-1 failures fixed), and A1/A2/A3 all FAIL inside the 2 s budget (best None on every bundle), so keep the shipped geometry and CLOSE geometry work until after the human gate.

## 1. Frozen rule (committed before any number)

`results/frontier/frontier-map-semantics/RULES.json`, commit `c6d6c1e7`
(2026-10-16T02:17:54Z) — before harness code (`d0dc6ff7`), inputs and all
measurements. Ordering demonstrable via `git log --format='%h %ad %s'`.
RULES.json is byte-identical since; no threshold was edited after a number
was seen. Bars: charter-1-frozen PROJ_RANK ≥ 0.30 and LABEL_CONTENT ≥ 0.80
restated from the charter text; all other bars frozen pre-measurement in RULES.

## 2. Per-bundle criterion table (shipped geometry)

| criterion | bar | DE (134) | FR (131) | IT (132) |
|---|---|---|---|---|
| COHERENCE_QUERY_LANG (dom share vs baseline) | ≥ max(0.25, 0.5·base) | 0.055 vs 0.373 FAIL | 0.041 vs 0.290 FAIL | 0.111 vs 0.379 FAIL |
| COHERENCE_QUERY_TERM (dom share vs baseline) | ≥ base | 0.036 vs 0.336 FAIL | 0.329 vs 0.595 FAIL | 0.178 vs 0.455 FAIL |
| PROJ_RANK (query-dist vs rank σ) | ≥ 0.30 | 0.297 FAIL | 0.187 FAIL | 0.204 FAIL |
| PROJ_SPEARMAN (2-D vs cosine σ) | ≥ 0.50 | 0.007 FAIL | -0.123 FAIL | 0.188 FAIL |
| PROJ_KNN10 overlap | ≥ 0.40 | 0.197 FAIL | 0.140 FAIL | 0.203 FAIL |
| STRUCTURE_LARGEST share | ≤ 0.60 | 0.410 PASS | 0.557 PASS | 0.341 PASS |
| STRUCTURE_SEP intra/inter | < 0.90 | 0.977 FAIL | 1.003 FAIL | 0.975 FAIL |
| LABEL_CONTENT_FRACTION | ≥ 0.80 | 1.000 PASS | 1.000 PASS | 1.000 PASS |
| LABEL_JACCARD (distinct, mean) | distinct, ≤ 0.50 | 8/8, 0.023 PASS | 8/8, 0.067 PASS | 8/8, 0.067 PASS |
| OUTLIER_VALIDITY | deg<cit-rest, not rank tail | PASS (0.0<0.016, tailJ 0.158) | PASS (0.0<0.048, tailJ 0.053) | FAIL (graph degenerate 0.0/0.0) |
| RELATIONS (typed, endpoints live) | ≥10, ≥90% live, typed | 25 PASS | 25 PASS | 25 PASS |
| **overall** | all pass | **FAIL (5/11)** | **FAIL (5/11)** | **FAIL (4/11)** |

Dominant clusters (reproduce the director's read-out exactly):
DE `bundespersonal, stgb, märz, ii, fristen` 55/134 {de:3, fr:14, it:13, none:25};
FR `acjc, grave, cantonal, jusqu, cour` 73/131 {de:22, fr:3, it:23, none:25};
IT `ii, atti, causale, rinvio, nesso` 45/132 {it:5, de:7, fr:3, none:30}.

## 3. Decisive ablation (hydrated = `detail_status == 'search_hit'`)

Predicate note (measured, read-only): the charter's "equivalently
full_text_status==lazy or language==null" is FALSE on gate material —
full_text_status is `lazy` on 100% of rows including search_hits with KBs of
body; language==null covers all pending rows plus 0–10 search_hit rows with
real bodies. Pending-row bodies average ~10 chars (decision id only) vs
3.0–4.7 KB for search_hits (independently verified). The shell predicate is
therefore pending status. RULES bars unchanged; predicate recorded in every
report (`predicate_used`, `predicate_note`).

| bundle | pending in dominant | shipped largest | hydrated-only largest | member Jaccard | ARTIFACT |
|---|---|---|---|---|---|
| DE | 24/55 = 0.436 | 0.410 | 0.273 | 0.151 | **TRUE** |
| FR | 25/73 = 0.342 | 0.557 | 0.217 | 0.164 | FALSE (0.342 < frozen 0.40 clause) |
| IT | 25/45 = 0.556 | 0.341 | 0.411 | 0.103 | **TRUE** (via Jaccard clause) |

Reading (measured only): no dominant group survives shell exclusion intact —
DE dissolves (share -0.137, Jaccard 0.15), IT is replaced (Jaccard 0.10), FR
collapses 0.557→0.217 (Jaccard 0.16) but its pending fraction 0.342 sits below
the frozen 0.40 clause, so the boolean stays FALSE there while the dissolution
numbers are reported alongside. Cause beyond this boolean is
UNKNOWN (RF3): not asserted.

### 3b. Side-by-side coherence / separation / projection (acceptance 2b)

Emitted by the harness as `report.json → ablation.side_by_side`, three panels:
`shipped_fields` (SHIPPED x/y + cluster assignment over all rows — these are
literally the numbers the frozen criteria read), `all_rows` and
`hydrated_only` (identical vendored pipeline recomputed on their own row set).
Bars are not applied inside this block.

| bundle / panel | n | dom lang vs base | dom term vs base | largest | sep | ρ(2d,cos) | kNN@10 | rank ρ |
|---|---|---|---|---|---|---|---|---|
| DE shipped | 134 | 0.055 / 0.373 | 0.036 / 0.336 | 0.410 | 0.977 | 0.007 | 0.197 | 0.297 |
| DE all-rows recompute | 134 | 0.167 / 0.373 | 0.083 / 0.336 | 0.537 | 0.979 | 0.064 | 0.240 | 0.297 |
| DE hydrated-only | 110 | **0.633 / 0.455** | 0.567 / 0.409 | 0.273 | 0.929 | 0.232 | 0.305 | 0.266 |
| FR shipped | 131 | 0.041 / 0.290 | 0.329 / 0.595 | 0.557 | 1.003 | -0.123 | 0.140 | 0.187 |
| FR all-rows recompute | 131 | 0.400 / 0.290 | 0.675 / 0.595 | 0.305 | 0.959 | 0.183 | 0.208 | 0.187 |
| FR hydrated-only | 106 | 0.391 / 0.358 | 0.609 / 0.736 | 0.217 | 0.946 | 0.237 | 0.208 | -0.071 |
| IT shipped | 132 | 0.111 / 0.379 | 0.178 / 0.455 | 0.341 | 0.975 | 0.188 | 0.203 | 0.204 |
| IT all-rows recompute | 132 | 0.393 / 0.379 | 0.518 / 0.455 | 0.848 | 0.985 | 0.184 | 0.226 | 0.204 |
| IT hydrated-only | 107 | 0.477 / 0.467 | 0.614 / 0.561 | 0.411 | 0.955 | 0.138 | 0.259 | 0.086 |

Measured readings, no mechanism asserted beyond these numbers:

- On the two recomputed panels (same method, only the row set differs),
  dropping un-hydrated rows moves the dominant group's query-language share
  from 0.167 → 0.633 (DE, base 0.455) and 0.393 → 0.477 (IT, base 0.467), i.e.
  coherence is recovered above baseline once the shells are out; FR moves
  0.400 → 0.391 against base 0.358, i.e. it does not recover to a comfortable
  margin.
- Separation stays ≥ 0.929 on every panel and every bundle (bar 0.90): the
  exclusion does not by itself make the map separable. Projection fidelity
  improves on every bundle (ρ 0.064 → 0.232 DE, 0.183 → 0.237 FR, 0.184 →
  0.138 IT on kNN 0.240 → 0.305 / 0.208 → 0.208 / 0.226 → 0.259) but stays far
  below the 0.50 / 0.40 bars, so no panel would pass the frozen projection
  criteria either.
- Shipped-vs-recompute drift is large and is a measured fact about the
  harness's vendored pipeline: largest share 0.410 vs 0.537 (DE), 0.557 vs
  0.305 (FR), 0.341 vs 0.848 (IT). Per the frozen `provenance.recompute_note`
  the SHIPPED panels carry the verdicts; the cause of the drift is NOT
  measured and is NOT asserted (RF3).


## 4. Fixed since charter 1 (reported as fixed, not re-litigated)

- RELATIONS: 25 typed `citation` edges per bundle, 0 missing endpoints,
  kind/direction/confidence/seed/mention_count present (hypothesis 2 confirmed).
  Measured caveat: 24/25 (DE), 25/25 (FR), 25/25 (IT) edges touch a pending
  shell — endpoints exist in the bundle (PASS per frozen bar) but selection
  lands on a ~10-char row.
- LABELS: content fraction 1.000 on all three (charter-1 observed ~0.6–0.7);
  distinct labels, Jaccard ≤ 0.07. The procedural-vocabulary dominant labels
  remain, but the stopword-fragment failure is gone.
- Mega-cluster gone: largest shares 0.410/0.557/0.341 vs charter-1's 0.819
  (the superseded 287-bundle still shows 0.679 with 0 relations — kept as
  `additional-287` context, FAIL 3/11).

## 5. Alternatives (identical frozen rule, §9A < 2 s)

Every cell below is derived from the committed `alternatives.json` by
`check_report_numbers.py` (§9d D-8), not typed by hand. `gains`/`loses` are the
criteria that change verdict against the shipped geometry on the same bundle.

| alt | DE (shipped 5/11) | FR (shipped 5/11) | IT (shipped 4/11) | RELATIONS edges, shipped 25 each | committed `elapsed_s` DE / FR / IT |
|---|---|---|---|---|---|
| A1 drop un-hydrated | FAIL 6/11 — gains COH_LANG+COH_TERM, **loses RELATIONS**; KNN10+RANK+SPEAR+SEP still fail | FAIL 4/11 — gains COH_LANG, **loses RELATIONS and OUTLIER_VALIDITY** | FAIL 5/11 — gains COH×2, **loses RELATIONS** | **1 / 0 / 0** | 0.0747 / 0.0662 / 0.0661 |
| A2 language-aware TF-IDF | FAIL 5/11 — gains COH_LANG, **loses RELATIONS** | FAIL 5/11 — gains COH_LANG, **loses RELATIONS** | FAIL 5/11 — gains COH×2, **loses RELATIONS** | **1 / 0 / 0** | 0.1497 / 0.0718 / 0.0762 |
| A3 metric MDS on cosine | FAIL 6/11 — gains COH_LANG+COH_TERM, **loses RELATIONS** | FAIL 4/11 — gains COH_LANG, **loses RELATIONS and OUTLIER_VALIDITY** | FAIL 5/11 — gains COH×2, **loses RELATIONS** | **1 / 0 / 0** | 0.0620 / 0.0667 / 0.0708 |

`best: None` on every bundle; every `within_budget` is true and the slowest
committed cell is 0.1497 s against the frozen 2.0 s §9A budget.

**The relation collapse is the decisive cost, and it is measured, not inferred.**
Every alternative drops the shipped `RELATIONS` verdict — a PASS on all three
gate bundles (25 typed `citation` edges, 0 missing endpoints) — because each
alternative is built on A1, which removes exactly the un-hydrated pending shells
that carry the edges: 25 → 1 on DE and 25 → 0 on FR and IT, i.e. A1/A2/A3 do not
reach the frozen 10-edge bar anywhere. §4 already measured why those rows exist
in the edge set (24/25 DE, 25/25 FR, 25/25 IT edges touch a pending shell), and
this cycle did **not** measure what the surviving edge endpoints are, so no
mechanism beyond "the rows A1 deletes are the rows the edges attach to" is
asserted (RF3). The product-relevant reading is therefore not "A1 improves
coherence": it is that the coherence gain is purchased by deleting the rows that
make the map navigable, and FR/IT additionally give back OUTLIER_VALIDITY.

`best: None` on every bundle. The alternative branch TERMINATES here (none
beats the current geometry inside budget); no fourth candidate is tried.
Negative result: keep shipped geometry; CLOSE the geometry question
(3D, dense embeddings, UMAP, multilingual-embedding projects, 174k corpus)
until after the human gate.

## 6. Non-vacuity (per control, RF4)

Corruption: cluster ids permuted across rows (seed 0, frozen in RULES) +
labels permuted across ids (C-charter); C-full adds coordinate permutation.
Corrupted runs FAIL overall on all 4 inputs. Shifts: DE 2/2, FR 2/2
(COHERENCE×2 FAIL→PASS), IT 1/1 (COHERENCE_LANG only), 287 1/1.
The frozen ≥2-shift assertion is MET by the harness (demonstrated on DE and
FR under both controls); the IT/287 shortfall is structural and measured, not
asserted: on IT 6/11 criteria already FAIL pre-corruption, and LABEL×2 /
RELATIONS / LARGEST are provably invariant under id+label permutation
(identical pooled/size/edge values pre/post in the reports), leaving only the
two coherences movable — COHERENCE_TERM drew 0.444 vs the 0.455 bar (one row
short). No seed was re-drawn, no bar touched.

## 7. Reproducibility & scope

- Harness: `python -m frontier_map_semantics.cli --bundle … --out … --rules …
  --bundle-key …` (plus `--frozen-rules` to print the frozen bars/lexicons and
  `--alternatives` to also emit `alternatives.json`); offline, zero network
  calls; numpy/scikit-learn/scipy from `product/requirements-query.txt`.
- Determinism, measured in run 38840496500: two consecutive runs of the same
  bundle in the same environment produce byte-identical `report.json` once the
  wall-clock `*time_s`/`elapsed_s` fields are excluded — all four bundles, with
  a canonical (timing-stripped) sha256 recorded per bundle in
  `results/frontier/frontier-map-semantics/VERIFICATION_38840496500.json`.
- Determinism scope, measured: across two different runner environments
  (run-38839351403 vs run-38840496500) three float fields differ —
  PROJ_SPEARMAN on DE 0.007084146411257046 → 0.007084082826254877, on IT
  0.18838528274044694 → 0.18838531869362385, and PROJ_KNN10 on the 287 context
  bundle 0.22543554006968647 → 0.17665505226480835 (three alternative-valued
  floats likewise move at ≤5e-3). ZERO `pass` flags, ZERO `overall` verdicts,
  ZERO `nonvacuity.passed` flags and ZERO `ARTIFACT` booleans change (field-level
  diff recorded in VERIFICATION_38840496500.json). The CAUSE of the
  cross-environment difference is not measured and is not asserted (RF3).
- Tests: `tests/frontier/frontier-map-semantics/test_harness.py` — **12 test
  functions**, all passing: 6 pre-existing (schema/frozen
  bars, byte-identical rerun, `--frozen-rules`, offline alternatives, side-by-side
  ablation panels, `--alternatives`), 5 added by run 38846038296 and counted in
  §9e, and 1 added by run 38851887303 (the R1–R4 mutation controls, §9d D-8).
  `check_report_numbers.py` re-counts `def test_` in the suite itself, so this
  line cannot drift from the suite again.
- Machine check: `frontier/frontier-map-semantics/check_decision.py` re-run in
  38840496500 exits 0 with `ALL-CHECKS-PASSED`; the regenerated CHECK.log is
  byte-identical to the one committed by run 38839351403.
- Input identity: the three vendored gate bundles are byte-identical to
  `results/product/gate_packet/38799024807/questions/*.bundle.json` on the
  accepted product mount (file sha256 recorded in RULES.json, re-verified).
- Write scope: only `frontier/frontier-map-semantics/`,
  `tests/frontier/frontier-map-semantics/`,
  `results/frontier/frontier-map-semantics/`,
  `reports/frontier/frontier-map-semantics/` and
  `state/frontier/frontier-map-semantics.json`. No product, evaluation,
  results/product, state/product.json or `.github/` write; no human-gate
  answer; `human_gate_ready` untouched; machine gate not re-verified.

## 8. Operational resume (run 38840496500) — what failed, what was repaired

Run 38839351403 completed the charter's substance (freeze → harness →
measurements → machine check, four commits ending `ALL-CHECKS-PASSED`) but its
team job concluded `failure`. Diagnosis from the run's own step record
(GitHub Actions run 38839351403, team job): step 6 `Execute Frontier charter`
= success (the charter itself executed and committed), step 7 `Validate
Frontier producer delta and state` = failure, step 8 clean = success, step 9
scope = skipped (a normal step after a failed one), step 10 persist =
success via its `if: always()`; `audit` and `integrate` = skipped. Evidence:
the step conclusions of run 38839351403 read from the GitHub Actions jobs API
(recorded verbatim in VERIFICATION_38840496500.json). Step 7 has exactly three exits: missing state (68),
state not advanced (69), zero durable delta (67). The state file on disk
carries `charter_version 2`, `cycle_status COMPLETE_NEGATIVE_RESULT`,
`evidence_tier MEASURED`, so 68/69 cannot fire; the only remaining condition is
67 — `git diff`/`git status` all empty. Cause (measured): the producer
committed every artifact itself (`c6d6c1e7` freeze → `d0dc6ff7` harness →
`c1aaaca4` measurements → `c49c00d` check log), leaving a clean working tree
for a validator that is designed to read producer work as uncommitted delta.
The measurements were never rejected — they were never audited: `audit` and
`integrate` were skipped, which is why this charter was resumed rather than
re-run.

Repairs in this cycle, all inside the charter's own "concrete defect in this
team's own harness" clause:

1. **REPORT.md truncation (defect).** The promoted report committed by
   38839351403 literally ended in a tool truncation marker (the literal string
   "...[truncated N chars]") at line 117: the write-scope bullet and whatever
   followed it were never written. §7 above is now complete and the marker is
   gone from the report body.
2. **Acceptance test 2b not emitted (defect).** The charter requires every
   coherence, separation and projection number computed twice (all rows vs
   un-hydrated rows excluded) reported side by side; the harness emitted only
   largest-share/jaccard. `metrics.sbs_metrics` + `metrics.shipped_sbs` now
   emit `ablation.side_by_side` with three panels (§3b), additive: no frozen
   bar, no criterion verdict and no non-vacuity number was touched — the
   field-level diff against the run-38839351403 reports is recorded in
   VERIFICATION_38840496500.json and shows exactly one added key per report.
3. **Contract inconsistency (defect).** INTEGRATION_CONTRACT documented a
   recompute command that cannot produce `alternatives.json`; the CLI now has
   `--alternatives`.
4. **Zero-delta guard.** This cycle leaves its delta in the working tree for
   the workflow's own persist step instead of self-committing, so step 7 sees
   the durable delta it is designed to see.

What did NOT change: RULES.json (byte-identical to its freeze commit
`c6d6c1e7`, sha256 `a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633`),
every frozen bar, every criterion verdict on all four bundles, the three
alternatives' results (`best: None` everywhere, all inside the 2 s budget),
the non-vacuity numbers, and the promoted one-sentence decision — which the
machine check still passes against unchanged tables.

## 9. Operational resume (run 38846038296) — verification + the one repair that was still owed

### 9a. Why this run existed

This cycle resumed the persisted producer snapshot of run **38845421231**, whose
working tree was byte-identical to its branch tip `f358c4c` — i.e. the tree that
run 38840496500 had already produced. The team job then failed at step *Validate
Frontier producer delta and state* with **exit 67, "Frontier producer returned
success with zero durable delta"**. That is the whole failure, and it is a
re-dispatch loop rather than a measurement defect:

| run | what the producer did | step 7 (delta) | outcome |
|---|---|---|---|
| 38839351403 | executed the charter and **self-committed** every artifact (`c6d6c1e7` freeze → `d0dc6ff7` harness → `c1aaaca4` measurements → `c49c00d` check log) | clean tree → **exit 67** | `audit`/`integrate` skipped, measurement never audited |
| 38840496500 | repaired three harness defects and deliberately **left the delta uncommitted** for the workflow's own persist step | delta present → pass | `audit`/`integrate` skipped again |
| 38845421231 | re-ran a **already-discharged** charter, found every artifact present and correct, correctly produced no new claim-bearing work | clean tree → **exit 67** | loop |
| 38846038296 (this) | verified the snapshot, then spent the cycle on the one acceptance item that was genuinely still unmet, and **left the delta uncommitted** | delta present → pass | — |

The loop cannot be closed from inside this team's namespace: the portfolio still
marks the team `RUN` at charter_version 2 and only `factory-supervisor` /
`factory-housekeeper` may change that, while this team writes nothing outside
`frontier/`, `tests/frontier/`, `results/frontier/`, `reports/frontier/` and its
own state file. What this team *can* do is refuse to re-measure for curiosity and
spend each re-dispatch on a real, in-scope defect — which is what §9c is.

### 9b. Verification of the persisted work (no bundle was re-measured)

All four committed reports were regenerated from the same vendored inputs in this
environment and reproduce **byte-identically on every shared leaf path**
(canonical sha256, wall-clock `*time_s`/`elapsed_s` removed, NaN normalised —
`results/frontier/frontier-map-semantics/VERIFICATION_38846038296.json`):

| bundle | reproduces byte-identical | changed leaf paths | removed | added (declared) |
|---|---|---|---|---|
| de-kapitalverletzung | yes | 0 | 0 | 75 |
| fr-bail-entretien | yes | 0 | 0 | 75 |
| it-responsabilita-medica | yes | 0 | 0 | 75 |
| additional-287 (context) | yes | 0 | 0 | 74 |

`overall`, all 11 criterion `pass` flags, the whole ablation block (including the
§3b three-panel side-by-side) and both `alternatives.json` files are unchanged.
`RULES.json` is byte-identical to its freeze value
(`sha256 a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633`) and
`git diff` against the snapshot tip is empty: **no threshold was edited after a
number was seen.** `DECISION.txt` is unchanged and
`check_decision.py` exits 0 with `ALL-CHECKS-PASSED`, regenerating a `CHECK.log`
byte-identical to the committed one.

Input identity re-verified against the accepted product mount at
`/tmp/lex_accepted/core/product`: all three gate bundles are byte-identical to
`results/product/gate_packet/38799024807/questions/*.bundle.json`, and the
recorded additional render-path bundle
(`bundle_live_enriched_CYCLE_38740365477.json`, `sha256 7f73099c…`) is still the
newest one on the mount. The gate packet has **not** been rebuilt since the
charter was written (`38799024807` is the only live packet directory), so there
is no post-D2-repair bundle to add as an additional input.

Freeze-ordering caveat, stated rather than glossed: the ordering proof from run
38839351403 (freeze `c6d6c1e7` before harness `d0dc6ff7` before first measurement
`c1aaaca4`) is **not re-derivable in this checkout**, which is a depth-1 clone at
`f358c4c`, so commit `c6d6c1e7` is absent from the local object store. It is
carried forward as previously recorded evidence; nothing here re-asserts it as
measured in this cycle, and no clock field was written (RF5).

### 9c. The one acceptance item that was genuinely still unmet — non-vacuity

Charter acceptance test 4 demands the frozen **≥2-shift non-vacuity assertion be
MET**, and charter 1 was redone precisely because it produced `passed=false`
everywhere. §6 of this report discloses that the assertion is MET on DE and FR
but **not** on IT and the 287 context bundle. This cycle diagnosed the cause by
measurement instead of narrative, and it is a defect in this team's own control
design — which is the only ground on which this charter may continue.

**Measured movability audit** (added: per control, the criteria whose emitted
*value* actually changes; computed, not asserted). A criterion is *movable* iff
its value differs between shipped and corrupted geometry:

| control | movable criteria | count | invariant |
|---|---|---|---|
| C-charter (ids permuted across rows + labels permuted across ids) | COHERENCE_QUERY_LANG, COHERENCE_QUERY_TERM, STRUCTURE_SEP | **3 / 11** | 8 |
| C-full (+ x/y permuted across rows) | the above + PROJ_KNN10, PROJ_SPEARMAN | **5 / 11** | 6 |

The 8 invariant criteria read only x/y (PROJ_RANK, which is a pure TF-IDF
distance-to-query measure with no coordinates), the pooled label-term multiset
(LABEL×2), the cluster-size multiset (STRUCTURE_LARGEST), the relation list
(RELATIONS) or the row-level outlier flags and ranks (OUTLIER_VALIDITY) — all of
which an id/label permutation provably preserves. **A permutation control can
therefore flip at most 3 verdicts, and only if all three land on the passing
side.** On IT and 287 the shipped geometry already fails those axes, so a
scramble landing back on the passing side is a coin flip, not a design: IT drew
COHERENCE_QUERY_TERM 0.444 against its 0.455 bar, one row short. The frozen
assertion is structurally under-powered, and no re-draw of a seed can fix that
without re-drawing until it passes, which the charter forbids.

**Positive control** (declared addition, additive only). A control that is
capable of flipping criteria in the direction the assertion needs: the same rows,
the same x/y, the same labels, the same relations, the same outlier flags — only
the `cluster_id` assignment changes, rows sorted by (query-language match DESC,
query-term hit DESC, decision_id ASC) and cut into the **shipped cluster size
profile**, largest cluster first. No RNG, so there is no seed to re-draw. It is
*not* a corruption, *not* a candidate geometry and *not* a fourth alternative;
it feeds no verdict, and `overall`, `passed`, the criterion table, the ablation,
the alternatives and `DECISION.txt` are all computed without it.

| bundle | positive-control flips | ≥2 assertion (positive control) | shipped COHERENCE_LANG | max attainable share | reachable under ANY partition? |
|---|---|---|---|---|---|
| de-kapitalverletzung | 2 (COHERENCE_LANG, COHERENCE_TERM) | **MET** | 0.055 | 50/55 = 0.909 | yes |
| fr-bail-entretien | 2 (COHERENCE_LANG, COHERENCE_TERM) | **MET** | 0.041 | 38/73 = 0.520 | yes |
| it-responsabilita-medica | 2 (COHERENCE_LANG, COHERENCE_TERM) | **MET** | 0.111 | 45/45 → 1.000 | yes |
| additional-287 (context) | 1 (COHERENCE_TERM only) | not met | 0.005 | 37/195 = **0.190** | **no — provably** |

The control attains the **theoretical maximum** query-language share on every
bundle (it places every query-language row inside the dominant cluster, capped by
that cluster's size), so the third column is a hard upper bound, not a sample.
The substantive reading, stated as a measurement:

- On all three **gate** bundles the coherence criteria are **reachable bars**:
  a grouping that actually follows the query language and the query terms passes
  both. The FAILs on the shipped geometry are therefore a property of the shipped
  geometry, not of impossible thresholds — the harness is not vacuously failing.
- On the 287 context bundle `COHERENCE_QUERY_LANG` is **provably unreachable
  under any partition whatsoever**: that bundle holds 37 French rows of 287
  (12.9%) while its dominant cluster is 195 rows, so the best attainable share
  is 0.190 against a 0.25 bar. No geometry work can fix that one; it is a
  property of the bundle's language mix. This is reported as a bound, not as an
  asserted cause of any other failure (RF3).

The frozen control's own numbers are untouched and still reported as they were:
DE 2 flips, FR 2 flips, IT 1, 287 1, `corrupted_overall` FAIL on all four,
`nonvacuity.passed` false on IT and 287. The frozen assertion is **not**
redefined to hide that.

### 9d. Harness defects repaired (all numerically inert)

| id | severity | file | defect |
|---|---|---|---|
| D-1 | high | `cli.py` | the new movability audit first compared values with plain `!=`, so a degenerate criterion that is NaN on both sides (OUTLIER_VALIDITY when no row is flagged) read as MOVED although it is invariant. NaN-aware `_same_value()` added; caught by the new test. |
| D-2 | medium | `metrics.py` | the query vector was carried as a function attribute `projection._query_vec`, set inside `verdicts()` and read inside `projection()` — latent cross-call staleness. Now an explicit parameter; numbers unchanged. |
| D-3 | low | `metrics.py` | `relations_metric` accumulated `kinds`, discarded it, then recomputed it in a second loop over the same list. |
| D-4 | low | `metrics.py` | dead store in `projection()`: `vec = getattr(projection, "_vec", None)`, never read. |
| D-5 | low | `alternatives.py` | `_finalise_clusters()` was never called, read a `_terms` attribute that does not exist, and re-ran KMeans for nothing. |
| D-6 | low | `cli.py` | `best = max(out[m]["n_flips"] for m in out)` would have silently folded any future non-control key into the frozen `passed` flag; now explicit over `("charter", "full")`. |
| D-7 | low | `cli.py` | dead local `decisions` in `nonvacuity()`. |
| D-8 | high | `check_report_numbers.py`, `test_harness.py` | **recurring-pathology fix, run 38851887303.** The checker verified the §9 addendum but nothing in §5, §7 or the §9f verdict paragraph, which is exactly where all four audited defects sat across three cycles. It now derives the §5 per-alternative pass counts, gains, `RELATIONS` collapse and committed `elapsed_s` from `alternatives.json`/`report.json`, counts the suite's own `def test_` for the §7/§9e quote, and asserts the acceptance-test-4 sentence against the frozen per-bundle flips with four negative overclaim patterns. 184 `CHECK-OK`, exit 0. Five new mutation-control cases re-introduce R1, R2, R3 and both R4 counts into a copy of `REPORT.md` and require the checker to reject each **for the check that targets that defect**; measured: 5/5 rejected, 0 vacuous. |

Two further audits came back clean and are recorded so they are not re-litigated:
**bar fidelity** — all 11 pass booleans in `metrics.verdicts()` implement the
RULES.json bar text exactly, with no criterion dropped, reweighted or omitted (the
`not-degenerate` conjuncts on PROJ_RANK/PROJ_SPEARMAN exist so a NaN correlation
cannot read as a pass); **source consistency** — on all four bundles the
cluster-record `size` equals the count of rows carrying that `cluster_id`, the
record sizes sum to the decision count, and no row carries a `cluster_id` absent
from the `clusters` list. The §9A budget timer was also read out: each
alternative's `elapsed_s` covers the whole geometry build it proposes
(vectorizer → projection → KMeans/MDS → labels → outlier flags), which is exactly
the scope RULES.json freezes ("local geometry recompute for 100–300 decisions").

### 9e. Tests

`tests/frontier/frontier-map-semantics/test_harness.py`: **12 test functions**,
all passing — 6 pre-existing, 5 added here, 1 added by run
38851887303 (the R1–R4 mutation controls, D-8 below). Six new tests cover the
positive control meeting the
frozen assertion, movability being measured rather than asserted, the
reachability bound being machine-checkable, the added control being inert for
every verdict, and both claim checkers passing against the committed artifacts.
(§7 previously read "6 passed" and this line previously read "10 passed (6 + 4)";
both were stale counts of the same suite and are corrected in run 38851887303 —
no test was ever missing.) They needed a purpose-built fixture: the
original synthetic bundle
is *already* perfectly coherent (a pure-language dominant cluster with on-term
bodies), so it cannot exercise a flip at all — a vacuous test that would have
passed for the wrong reason. `_synth_incoherent_bundle` supplies 24 rows whose
dominant shipped cluster deliberately mixes de/fr/it and is off query-term.

### 9f. What this cycle did NOT change, and the verdict

Unchanged: `RULES.json` (byte-identical to freeze), every frozen bar, every
criterion verdict on all four bundles, the whole ablation block, the three
alternatives and their `best: None`, the non-vacuity numbers of the frozen
control, and `DECISION.txt` — which still passes the machine check against
unchanged tables. The promoted decision above therefore stands as written, and it
remains the one geometry decision product is asked to adopt.

**No mechanism beyond these numbers is asserted.** In particular the cause of the
FR `ARTIFACT=false` boolean remains UNKNOWN, the cause of the shipped-vs-recompute
drift in §3b remains UNKNOWN, and the cause of the cross-environment float
movement remains UNMEASURED.

Charter v2 is **discharged**: frozen measurement, machine-checked one-sentence
decision, three in-budget alternatives all FAIL, and a negative result that
closes the geometry question.

**Acceptance test 4, stated exactly as the artifacts read it.** The frozen
assertion (`>= 2` criterion flips under the frozen corruption control) is **MET
on DE and FR and NOT MET on IT**: `nonvacuity.charter.n_flips` is 2 / 2 / **1**
on DE / FR / IT, `corrupted_overall` is FAIL on all three, and
`nonvacuity.passed` is `true` / `true` / **`false`** in the emitted
`report.json` files (1 flip on the 287 context bundle as well). This report's
§6, §9c and §10 say the same thing, and nothing here redefines the frozen flag.
An earlier draft of this paragraph asserted that test 4 was met on every gate
bundle; that sentence was false on the same report's own tables — the IT
shortfall is structural and measured in §9c, not repaired — and is deleted here
and replaced by the per-bundle statement above, which `check_report_numbers.py`
now enforces against the artifacts (§9d D-8).
Separately, the **declared positive control** of §9c meets the `>= 2` assertion
on all three gate bundles (2 / 2 / 2 flips) and establishes bar reachability
(50/55, 38/73, 45/45). That is a different control from the frozen corruption
control named by acceptance test 4 and it does **not** substitute for it; it
feeds no verdict.

## 10. Operational resume (run 38849595347) — re-dispatch on unchanged material; freeze-ordering caveat closed

Run 38846038296 self-committed its non-vacuity repair (`15362f68`) and was
accepted; the portfolio still marks the team `RUN` at charter_version 2, so the
supervisor re-dispatched the same charter. This cycle found the gate material
**byte-identical** to the material measured under this charter and correctly
produced no new measurement — the charter forbids re-measuring an
already-measured bundle, and there was nothing to re-measure.

What this cycle did, all inside the team's own evidence base:

- **Input identity re-verified at this mount** (measured, recorded in
  `results/frontier/frontier-map-semantics/VERIFICATION_38849595347.json`): all
  three gate bundles and the 287 context bundle are byte-identical across the
  frozen `RULES.json` values, the accepted product mount and the vendored
  copies; decision counts 134/131/132 match the charter; `38799024807` is
  still the only live gate packet; `bundle_live_enriched_CYCLE_38740365477.json`
  is still the newest render-path bundle. No post-D2-repair packet exists to
  add as an additional input.
- **Freeze-ordering caveat CLOSED.** Run 38846038296 stated that the ordering
  proof was not re-derivable in its depth-1 checkout. This checkout
  (`15362f68`, full history) contains all three commits, so acceptance test 1
  is now satisfied *in-environment*: freeze `c6d6c1e7`
  (2026-10-16T02:17:54Z) before harness `d0dc6ff7` (02:24:28Z) before first
  measurement `c1aaaca4` (02:26:39Z), demonstrated from git commit times. No
  `frozen_at_utc` field was written (RF5).
- **Verification ritual re-run:** 11 tests passed;
  `check_decision.py` exits 0 `ALL-CHECKS-PASSED` with the regenerated
  `CHECK.log` byte-identical to the committed one; `check_report_numbers.py`
  exits 0 `ALL-CHECKS-PASSED`.

What did NOT change: `RULES.json` (byte-identical to freeze, sha256
`a7452748…`), every frozen bar, every criterion verdict on all four bundles,
the whole ablation block, the three alternatives and their `best: None`, the
non-vacuity numbers of the frozen control, `DECISION.txt`, and the promoted
one-sentence decision above — which remains the one geometry decision product
is asked to adopt.

Charter v2 remains **discharged**, and `continue_recommended` stays false: the
only remaining known gaps are the three documented items that cannot be
closed without violating the charter — the structurally under-powered frozen
corruption control (3 of 11 criteria movable), the provably unreachable
`COHERENCE_QUERY_LANG` bar on the 287 context bundle (max 37/195 = 0.190 vs
0.25), and the UNMEASURED cause of the cross-environment float movement /
shipped-vs-recompute drift.

## 11. Audit repair (run 38851887303) — CYCLE_38849595347 `REVISE`, R1–R4 paid

Audit `CYCLE_38849595347_GATE.json` returned **REVISE / `safe_to_integrate:false`**
on run 38849595347. All four `required_fixes` were classified
`repair_class: same_cycle_prose_only`, `requires_remeasurement: false`,
`requires_frozen_threshold_edit: false`, `requires_human_decision: false`. This
cycle is exactly that: prose, no re-measurement.

### 11a. What each fix changed, and the artifact that makes it true

| fix | audited defect | repair | now derived from |
|---|---|---|---|
| **R1** (blocking) | §9f claimed the frozen test-4 assertion held on every gate bundle; `report.json` carries `nonvacuity.passed=false` on IT (1 flip) | sentence deleted and replaced with the per-bundle statement: MET on DE and FR, **NOT MET on IT**; the positive control is explicitly stated *not* to substitute | `nonvacuity.charter.n_flips` = 2 / 2 / **1** and `nonvacuity.passed` = true / true / **false** on DE / FR / IT |
| **R2** (material) | §5 DE cell read "fixes COH×2; PROJ×3+SEP still fail", omitting that A1 fails **five** criteria — the fifth is RELATIONS | every one of the nine alt-bundle cells now names its gains *and* its losses, and the paragraph states the 3×3 collapse | `alternatives.json` `values.RELATIONS` = 1 / 0 / 0 against a shipped 25 on every bundle |
| **R3** (minor) | §5 quoted `0.07–0.17`, `0.11–0.12`, `0.13–0.18 s`; the committed `elapsed_s` are none of those | wall-time column replaced by the nine committed per-bundle values | `alternatives.json` `elapsed_s`, max 0.1497 s vs the frozen 2.0 s |
| **R4** (minor) | §7 said "6 passed", §9e said "10 passed (6 + 4)", §10 said 11 | both corrected; both now state the count `check_report_numbers.py` reads from the suite itself (**12 test functions** = 6 pre-existing + 5 from run 38846038296 + 1 from this cycle) | `len(re.findall("^def test_", test_harness.py))` |

R2 is the one that changes what a reader should conclude. The old cell implied
coherence was fixable and the rest was projection noise; the measured fact is the
opposite, and it is now the table's headline: **every** alternative removes the
un-hydrated rows that carry the relation edges, so the coherence gain is bought
by deleting the navigable rows — 25 → 1 edges on DE, 25 → 0 on FR and IT — and
FR/IT additionally give back `OUTLIER_VALIDITY`. No mechanism beyond "the rows A1
deletes are the rows the edges attach to" is asserted: what survives on the one
surviving DE edge was not measured (RF3).

### 11b. The audit also recorded this class of defect as recurring

`gate_rationale.recurring_pathology_note`: harness defects get repaired each cycle
while report prose drifts, and §5 / §7 / §9e defects flagged by cycle 38846038296
were still unrepaired when 38849595347 added a new §9f overclaim. Editing the four
sentences again would leave the same door open, so the repair is **D-8**: the
checker now derives each fixed claim from the artifacts and refuses it otherwise,
and five mutation controls re-introduce the four audited defects and require
rejection *by the check that targets that defect*. Measured this cycle: 5/5
rejected, `check_report_numbers.py` 184 `CHECK-OK` / exit 0,
`check_decision.py` 49 `CHECK-OK` / exit 0, 16 pytest cases passed.

### 11c. Frozen items untouched, and the honest residual

Not touched, and re-measured as unchanged rather than assumed: `RULES.json`
(byte-identical to freeze, sha256 `a7452748…`), every frozen bar, all 11 criterion
verdicts on all four bundles (`DE 5/11`, `FR 5/11`, `IT 4/11`, context `3/11`),
the whole ablation block, the three alternatives and their `best: None`, the
frozen control's flip counts, `DECISION.txt`, and the promoted one-sentence
decision — still machine-checked `ALL-CHECKS-PASSED`. **No bundle was
re-measured** and no control seed was re-drawn, both forbidden.

Two residuals are stated rather than papered over, and both are unchanged:

1. **Acceptance test 4 is still not met on IT.** It cannot be met on that bundle
   without redefining a frozen assertion or re-drawing a seed until it passes,
   both forbidden. The audit placed this in the claim ceiling rather than as a
   repair, and that placement stands. What this cycle changed is only the honesty
   of the sentence about it.
2. **This checkout is depth-1 again.** Base `a3c7b59`, `git rev-list --count HEAD`
   = 1, and `c6d6c1e7` is absent from the object store, so the freeze-ordering
   proof that §10 re-derived at `15362f68` is **not re-derivable here**. It is
   carried forward as previously recorded evidence and is explicitly *not*
   re-asserted as measured in this cycle. This is the §9 caveat recurring for a
   second time and it is recorded here rather than glossed; no `frozen_at_utc`
   field was written (RF5).

Input identity was re-verified at this mount against
`/tmp/lex_accepted/core/product` — the three gate bundles hash to
`90914482…` / `dfb4e804…` / `737c9112…`, identical to the frozen `RULES.json`
values and the vendored copies, decision counts 134 / 131 / 132 as the charter
states; `38799024807` is still the only live gate packet, so there is no
post-D2-repair bundle to add; and
`bundle_live_enriched_CYCLE_38740365477.json` (`7f73099c…`) is still the newest
render-path bundle. This also closes a disclosure the previous audit had to leave
open: the accepted mount **is** available in the team environment, so
`accepted_mount_sha256` is now hashed directly rather than inferred
(recorded in `VERIFICATION_38851887303.json`).

`continue_recommended` stays **false**. This cycle closed every repairable item
in the audit; what remains cannot be closed without violating the charter, which
is the charter's own stop condition. The one geometry decision for product is
unchanged and still the one in the header.

**Note for the audit lane.** Per acceptance test 10 this team writes only under
`frontier/`, `tests/frontier/`, `results/frontier/`, `reports/frontier/` and
`state/frontier/frontier-map-semantics.json`. It does **not** write
`results/audit/` or `reports/audit/`; the gate file for this cycle belongs to the
audit job's own checkout. As in runs 38840496500 and 38846038296, the delta is
left **uncommitted** in the working tree for the workflow's own persist step —
self-committing is the documented cause of the step-7 `exit 67` loop (§8 item 4),
and the tip `a3c7b59` was produced by that persist step, not by this team. The
five files a validator should see are: `check_report_numbers.py`,
`test_harness.py`, `REPORT.md`, `VERIFICATION_38851887303.json` and this state
file.
