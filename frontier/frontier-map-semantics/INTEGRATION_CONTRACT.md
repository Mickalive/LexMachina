# frontier-map-semantics → product integration contract (narrow)

Consumer: product backlog item (4) (adopt verdict as input, do not wait).
This package changes NO product code and requires NO product import.

## What product reads (stable files, JSON, sort_keys)

- `results/frontier/frontier-map-semantics/RULES.json`
  Frozen inputs (bundle paths + file sha256), metric definitions, every
  PASS/FAIL bar, query-term lexicons, non-vacuity rule, ablation predicate.
  Committed at `c6d6c1e7` BEFORE any measurement; byte-identical since.
- `results/frontier/frontier-map-semantics/<bundle>/report.json`
  Per bundle: `overall` (PASS/FAIL), `criteria` (11 × {value, bar, pass}),
  `detail` (per-cluster coherence, projection/structure/label/outlier/
  relation diagnostics), `ablation` (side-by-side + ARTIFACT boolean +
  predicate note), `nonvacuity` (per-control flips + values).
  `ablation.side_by_side` carries three panels of the same nine numbers —
  `shipped_fields` (all rows, SHIPPED x/y + cluster assignment: the fields the
  frozen criteria read), `all_rows` and `hydrated_only` (identical vendored
  pipeline recomputed on their own row set) — so the un-hydrated-row exclusion
  effect can be read without confusing it with shipped-vs-recompute drift.
  No bar lives in this block; verdicts come from `criteria` only.
- `results/frontier/frontier-map-semantics/<bundle>/alternatives.json`
  A1/A2/A3 overall + per-criterion verdicts + measured wall time + budget flag.
- `results/frontier/frontier-map-semantics/DECISION.txt`
  Exactly one geometry-decision sentence, machine-checked by
  `frontier/frontier-map-semantics/check_decision.py` (exit 0 recorded).
- `reports/frontier/frontier-map-semantics/REPORT.md`
  Human-readable verdict + tables + negative-result closure.

## What product must NOT depend on

- No import of `frontier_map_semantics` (PYTHONPATH trick is harness-local).
- No absolute `/tmp` paths: inputs vendored under
  `results/frontier/frontier-map-semantics/inputs/` with sha256 in RULES.
- No thresholds from prose: only `RULES.json` bars are binding.

## Recompute (offline, zero network calls)

```
PYTHONPATH=frontier/frontier-map-semantics python -m frontier_map_semantics.cli \
  --bundle results/frontier/frontier-map-semantics/inputs/<bundle>.bundle.json \
  --out <dir> --rules results/frontier/frontier-map-semantics/RULES.json \
  --bundle-key <de-kapitalverletzung|fr-bail-entretien|it-responsabilita-medica|additional> \
  [--alternatives]
```

`--alternatives` additionally evaluates A1/A2/A3 under the identical frozen
rule and writes `<out>/alternatives.json` (needed to reproduce that file; the
bare command writes only `report.json`).

Byte-identical `report.json` on rerun in the same environment (asserted in
`tests/frontier/frontier-map-semantics/test_harness.py`; wall-clock
`*time_s`/`elapsed_s`/`hydrated_time_s`/`recompute_all_time_s` fields excluded
— environment-dependent by nature, always < §9A 2 s budget and asserted as
such). Across runner environments, three projection floats move without
changing any verdict; the exact old/new pairs are recorded in
`results/frontier/frontier-map-semantics/VERIFICATION_38840496500.json`.
