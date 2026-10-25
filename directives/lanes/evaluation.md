# Evaluation lane — query-map MVP

Be adversarial, but optimize for the fastest falsification of the canonical query-map MVP.

## Scope
Build the smallest frozen benchmark that can tell product whether retrieval and counter-authority discovery are good enough to justify the visual UX test.

Required checks:
- known relevant-authority recall;
- known contrary/limiting-authority recall where feasible;
- source/URL/decision-ID validity;
- FR/DE/IT query robustness;
- duplicate suppression;
- cached reproducibility;
- latency;
- basic cluster stability.

Baseline should be the same OpenCaseLaw search/result set without the additional query-map/counter-authority machinery where practical.

## REUSE-FIRST
Reuse all useful accepted LexMachina evaluation assets, especially:
- jurist-preference methodology;
- language-dominance / cross-language tests;
- boilerplate resistance;
- frozen-query / deterministic-seed discipline;
- provenance and negative-result conventions.

Do NOT rerun obsolete universal-174k geometry benchmarks merely because they exist.

## Speed rule
Evaluation must not block the first clickable product slice. Prefer a small honest benchmark with several strong queries over a large benchmark assembled before the product exists.

A normal evaluation cycle must produce executable fixtures/tests/results, not only methodology prose.
