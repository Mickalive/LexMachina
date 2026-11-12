# Correction of record — vertical_slice_report_20261112T160000Z.md

**Correction written by:** product cycle `43189571965` (operational resume of
producer snapshot `43180882004`). **Append-only:** the historical report is
preserved byte-identically
(sha256 `de5471d649fd2511149e130ce5c2daed8c015b052f2df70c77a22b6b6ed39a36`);
nothing in it was edited.

## Withdrawn claim 1 — "All QUERY_MAP_MVP core requirements satisfied"

**Withdrawn.** The run executed an **offline/cache** slice in fixture mode. It
did not exercise live OpenCaseLaw retrieval, it did not evaluate a frozen gate,
and it makes no legal-usefulness claim. The only correct ceiling for those
bytes is:

> OFFLINE WIRING EVIDENCE ONLY: runnable vertical-slice check of query ->
> bundle -> sourced answer -> counter-authority pass -> clickable map from
> recorded envelopes; no frozen gate is evaluated and no legal-usefulness
> claim is made.

The corrected run-scoped artifact is
`results/product/vertical_slice/CYCLE_43189571965/summary.json`, whose
`claim_ceiling` carries exactly that text. The historical artifacts
(`results/product/bundle_20261112T160000Z.json`,
`results/product/vertical_slice_results_20261112T160000Z.json`) are preserved
byte-identically and re-derived by
`product/tests/test_cycle_43189571965.py`.

## Withdrawn claim 2 — "State: /tmp/lex_control/state/product.json"

**Withdrawn.** That path is not a committed artifact and did not exist at the
time of the run (the mounted control plane carries `state/factory_direction.json`,
`state/frontier_portfolio.json` and `state/model_health.json` only). The lane
state is `state/product.json`, and this resume records the cycle there.

## Unchanged, re-derived numbers

The snapshot's measured numbers are reproducible from the committed tree under
an armed `socket.connect` trap: 120 decisions, 8 clusters, 11 relations,
counter-status distribution `{'cited': 2, 'candidate-limiting': 4, 'none': 114}`,
content coverage `{'full_text': 25, 'regeste': 68, 'snippet': 16, 'pointer': 11}`,
answer ready with 2 cited decision IDs, and a deterministic row signature equal
to the committed bundle's. The report's `1.211s` local latency is
environment-dependent and is not restated as a performance claim (this resume
measured a different wall time on the same bytes).

## Orchestration status of the snapshot

The snapshot is **UNADJUDICATED**, not accepted and not rejected. Its team job
was green (10/10 steps, including state validation, write-scope enforcement and
snapshot persistence); its independent-audit job exhausted the workflow's
2700 s work quantum (public check-run annotation
`LEX_WORK_QUANTUM_EXPIRED seconds=2700`, exit 78) before writing a gate, so the
gate/scope/persist steps were skipped, no `/audit` ref exists and integration
was skipped. This correction writes no gate and makes no verdict.
