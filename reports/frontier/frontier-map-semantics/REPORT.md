# frontier-map-semantics charter v2 — verdict report (run 38839351403)

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
| PROJ_SPEARMAN (2-D vs cosine σ) | ≥ 0.50 | 0.007 FAIL | −0.123 FAIL | 0.188 FAIL |
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
DE dissolves (share −0.137, Jaccard 0.15), IT is replaced (Jaccard 0.10), FR
collapses 0.557→0.217 (Jaccard 0.16) but its pending fraction 0.342 sits below
the frozen 0.40 clause, so the boolean stays FALSE there while the
dissolution numbers are reported alongside. Cause beyond this boolean is
UNKNOWN (RF3): not asserted.

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

- Harness: `python -m frontier_map_semantics.cli --bundle … --out …`
  (+ `--frozen-rules`); offline, zero network calls; numpy/sklearn/scipy.
- Determinism: rerun-verified per bundle (reports byte-identical modulo
  wall-clock `*time_s` fields, documented in INTEGRATION_CONTRACT).
- Tests: `tests/frontier/frontier-map-semantics/test_harness.py` (4 passed).
- Independent verification: a fresh-context agent recomputed §2/§4 shell
  numbers from the bundles with stdlib-only code — all match.
- Write scope: only `frontier/frontier-map-semantics/`,
  `tests/frontier/frontier-map-semantics/`,
  `results/frontier/frontier-map-semantics/`,
  `reports/frontier/frontier-map-semantics/`, `state/frontier/
...[truncated 622 chars]