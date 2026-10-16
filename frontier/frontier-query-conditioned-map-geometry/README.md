# frontier-query-conditioned-map-geometry

Query-conditioned geometry variants for the served query map, delivered behind the
`query_result_bundle` seam. **No rendering, no UI, no shader, no cluster colour.**

Charter v1. Outcome **A (component)** — the `relevance_ordered` variant is strictly
better than the accepted incumbent under the frozen geometry rule.

## Headline result

Frozen rule `RULES_GEOMETRY.json`
(sha256 `a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633`),
applied byte-identically to the three served bundles:

| Bundle | Incumbent | `hydrate_then_cluster` (V1) | `relevance_ordered` (V2) |
|---|---|---|---|
| de-kapitalverletzung | 6/11 | 6/11 | **7/11** |
| fr-bail-entretien | 5/11 | 7/11 | **8/11** |
| it-responsabilita-medica | 5/11 | 7/11 | **7/11** |
| **total** | **16/33** | 20/33 | **22/33** |

V2 has **zero regressions** against the incumbent on any bundle, so it is the
promoted, adoptable variant. V1 is strictly better in total but regresses
`OUTLIER_VALIDITY` on de and fr, so it is **not** promoted.

## What the variants do

- **V1 `hydrate_then_cluster`** — cluster and project only over rows that are
  hydrated (have retrievable text). Un-hydrated citation *shells* are kept as
  explicitly-marked unclustered context (unique negative `cluster_id`,
  `unclustered=true`, no cluster record) rather than being allowed to inflate a
  cluster.
- **V2 `relevance_ordered`** — same clustering, but the layout puts points on a
  **rerank-score axis** (x) with **query-language bands** (y), and cluster ids
  are renumbered by descending mean relevance. This makes `PROJ_*` no longer
  accidents of embedding variance.

Both emit `cluster_id`, `x`, `y`, `label`, `size` and `member_ids` in exactly the
shape `product/query/qmap.py` already emits, so **adoption requires no rendering
change**.

## Run it

```bash
export PYTHONPATH=frontier/frontier-query-conditioned-map-geometry
PACKET=/path/to/results/product/gate_packet/38839347028/questions

python3 -m qmap_geometry.cli \
  --rules results/frontier/frontier-query-conditioned-map-geometry/RULES_GEOMETRY.json \
  --packet-questions "$PACKET" \
  --out /tmp/qcmmg-out \
  --github-run-id "$GITHUB_RUN_ID"
```

Free models only, no network. ~8 s end to end for all three bundles and both
variants, well inside the frozen `budget.geometry_seconds_max = 2.0` per bundle.

## Test it

```bash
PYTHONPATH=frontier/frontier-query-conditioned-map-geometry \
python3 -m unittest discover -s frontier/frontier-query-conditioned-map-geometry/tests -v
```

15 stdlib-only tests (no pytest dependency). They pin the frozen-rule hash, the
refusal to score a tampered bar, the keyword-only seam signature, determinism,
the no-drop/no-duplicate and `member_ids[:50]` truncation contracts, and the
non-vacuity divergence described below. Run 38978981369 added 5 more for the
renderer precondition (20 total).

## Blocking precondition for adoption — read this before dropping it in

Found in producer run **38978981369**. The variants mark un-hydrated shells
with a **unique negative `cluster_id`**, and the live query-map renderer indexes
its colour palette by that id:

```js
const COLORS = [ …8 entries… ];                                      // query.html:141
ctx.fillStyle = COLORS[(p.cluster_id??0)%COLORS.length];            // query.html:188
```

JavaScript's `%` truncates toward zero, so `cluster_id = -1` gives index `-1` and
`COLORS[-1]` is `undefined`. Assigning `undefined` to `ctx.fillStyle` is an
invalid value that the canvas **ignores**, leaving the previous point's colour
in place. Every unclustered-shell point is therefore painted in whatever colour
was drawn before it — **47/214 (de), 49/217 (fr), 47/211 (it)**.

The accepted `INTEGRATION_CONTRACT.json` says "nothing else changes" for the
rendering path. That holds for `x`, `y`, `is_outlier` and the cluster records,
but the negative id is a value class the page has never received. **The
original artifact is left byte-identical for provenance**; the correction is
`results/frontier/frontier-query-conditioned-map-geometry/RENDERER_PRECONDITION.json`,
regenerated on every run by `qmap_geometry/renderer_precondition.py`.

This team writes no rendering code and touches no cluster colour, so the one-line
fix belongs to `frontier-query-map-ui` / Core Product — e.g. a non-negative
lookup, or paint shells from the variant's own additive `unclustered` flag.
It is also **not** worked around on the variant side: giving the shells one
shared non-negative id would change how vendored `structure()` splits intra- vs
inter-cluster pairs and therefore move the frozen `STRUCTURE_SEP` score, which
this charter may not do after the scores are seen.

## Provenance now proven, not just asserted

Run 38978981369 proved the vendored scorer's byte-identity by **git blob hash**
against the evaluation lane's canonical frozen reference
(`evaluation/frozen_bars/vendored/frontier_map_semantics_reference`, commit
`59fde886`): `metrics.py` → `3fc32b55…`, `textgeo.py` → `425e70fa…`, both
identical to the team's vendored copies. It also added `ENVIRONMENT.json`
recording the numeric stack behind the scores, which no earlier artifact carried.

## Known divergence — charter check (4), read this before promoting

Charter acceptance check (4) asks for a second control in which **shuffled
coordinates must fail `PROJ_RANK` / `PROJ_SPEARMAN`**.

**That control is unsatisfiable as written, and this run reports it as
unsatisfied rather than redefining it as a pass.** The frozen scorer computes
`PROJ_RANK` from the retrieval `rank` field and the TF-IDF cosine distance to the
query vector — it never reads `x`/`y`. Permuting coordinates therefore cannot
change it, for any candidate geometry. `STRUCTURE_SEP` is coordinate-invariant for
the same reason. This was verified empirically across all six variant×bundle
cases: bit-identical values under a seeded coordinate permutation.

`PROJ_SPEARMAN` and `PROJ_KNN10` *do* read coordinates and move sharply
(e.g. 0.483 → 0.007), which is the positive evidence the harness is not vacuous.
They do not flip their verdict only because both variants already sit below bar.

Non-vacuity is instead proven against the **binding frozen rule's own clause**
(`RULES_GEOMETRY.json → non_vacuity`), which asks for one control — the
`cluster_id`/label permutation — and requires ≥2 verdict flips. That is met:
`fr-bail-entretien` flips `COHERENCE_QUERY_LANG` and `COHERENCE_QUERY_TERM`.

Full record with the code citations and the probe data:
`results/frontier/frontier-query-conditioned-map-geometry/NON_VACUITY_DIVERGENCE.json`.

## Operational history

| Run | What happened |
|---|---|
| 38964153228 | First producer run. Produced the artifact set; artifacts are committed. |
| 38969741834 | **Crashed**: the `variant_fn` seam was declared positionally while `score_variant` calls `variant_fn(bundle, query_language=...)`. Fixed in `d971e67`. |
| 38970483941 | This resume. Found a *second* defect: the reproducibility check compared the first scoring pass — which is annotated in place with a `schema` key — against a bare second pass, so it always reported non-reproducible and silently flipped the charter outcome from **A to B**. The geometry and scores are deterministic (confirmed across independent processes). Also declared the charter (4) divergence above. |
| 38973386164 | Independent audit: **PASS**, `safe_to_integrate: true`; integrator accepted the lab branch at `be5eba7f`. |
| 38976645446 | **Duplicate dispatch** of the already-terminated charter (the portfolio still reads `status=RUN`). No new variant and no fourth variant; re-ran the component on the byte-identical frozen rule and served bundles, reproduced all 16 claim-bearing artifacts and the OUTCOME A result, and added `REVERIFICATION_38976645446.json`. `continue_recommended` stays `false`. |
| 38978981369 | **Duplicate dispatch again.** Re-verified OUTCOME A (20/20 tests, every criterion byte-identical). Found and closed one adoption blocker: the negative `cluster_id` renderer hazard above. Added `renderer_precondition.py`, 5 tests, `RENDERER_PRECONDITION.json`, `ENVIRONMENT.json`, `REVERIFICATION_38978981369.json`. No score, bar, control or variant changed. |

## Claim ceiling

This run does **not** claim the map is useful to a jurist. Usefulness is the human
product gate's question and is not answered here. It also does **not** claim the
shipped map is now fixed: **0 of 3 bundles pass all 11 criteria** under the promoted
variant, exactly as under the incumbent. See `CLAIM_CEILING.json`.