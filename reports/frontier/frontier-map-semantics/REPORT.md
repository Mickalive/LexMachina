# frontier-map-semantics charter v2 — verdict report (run 38839351403,
measurement freeze; completed and verified under operational resume run
38840496500 — see §8)

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

| alt | DE | FR | IT | wall time |
|---|---|---|---|---|
| A1 drop un-hydrated | FAIL (fixes COH×2; PROJ×3+SEP still fail) | FAIL | FAIL | 0.07–0.17 s |
| A2 language-aware TF-IDF | FAIL | FAIL | FAIL | 0.11–0.12 s |
| A3 metric MDS on cosine | FAIL | FAIL | FAIL | 0.13–0.18 s |

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
- Tests: `tests/frontier/frontier-map-semantics/test_harness.py` — 6 passed
  (schema/frozen bars, byte-identical rerun, `--frozen-rules`, offline
  alternatives, side-by-side ablation panels, `--alternatives`).
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
