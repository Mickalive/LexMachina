# LexMachina Factory Architecture

## Current product architecture

LexMachina is a **query-specific visual legal-research system**.

Canonical data flow:

```
legal question
  -> OpenCaseLaw retrieval / citation expansion
  -> normalized query_result_bundle
  -> reranking / source packing
  -> generative sourced answer
  -> independent counter-authority pass
  -> query-conditioned clustering / projection
  -> interactive map + decision/source inspection
```

The product does NOT require one universal geometry for all Swiss case law.

OpenCaseLaw is the default Swiss public data plane. The legacy 174k LexMachina corpus, global-map artifacts and research results are preserved as reusable evidence/components, not as the MVP critical path.

## Central integration contract: query_result_bundle

All parallel work should converge on a small product-owned bundle contract rather than inventing incompatible pipelines.

Minimum conceptual fields:
- query + query variants/provenance;
- generated answer + cited decision IDs;
- decisions with stable decision_id, canonical URL/citation, court/date/language and retrieved text/snippets;
- retrieval/rerank scores and source provenance;
- counter-authority status + uncertainty/evidence;
- cluster ID/label;
- projection coordinates;
- citation/typed relations.

Product may evolve the exact schema while preserving backwards-compatible fixtures during the MVP.

## Reuse-first product shell

The accepted `lab/product` implementation is a component library, not discarded legacy.

Prefer adapting:
- threaded HTTP server, caching and error handling;
- search/navigation/decision/citation/neighbor API patterns;
- WebGL + Canvas rendering;
- cluster/decision inspection;
- spatial index, LOD and culling;
- TF-IDF / clustering / UMAP / Leiden utilities;
- multilingual/evaluation helpers.

Do not rebuild these unless old global-174k assumptions make adaptation slower than isolation behind the query_result_bundle seam.

## Parallel engineering topology

### Core Product — continuous integrator
Owns the runnable application and end-to-end contract. It:
- builds its own vertical slice continuously;
- inspects ACCEPTED Frontier mounts every cycle;
- absorbs useful components immediately;
- never waits for every Frontier team;
- keeps running until `human_gate_ready=true`.

### Core Evaluation — continuous falsifier
Owns compact executable benchmarks for retrieval, counter-authority recall, source validity, language robustness, answer citation validity, cluster stability, reproducibility and latency. It feeds concrete failures back to Product without blocking the first clickable slice.

### Human-authorized Frontier engineering teams
Current portfolio may run independent non-overlapping implementation tracks such as:
- OpenCaseLaw retrieval/cache adapter;
- generative answer + adversarial/counter-authority engine;
- query-map UI adapter.

Frontier artifacts live in their own namespace and are promoted only after independent audit. Product remains the integrator.

## Legacy core lanes

### Corpus
Historical corpus acquisition/normalization work is preserved and PAUSED. Reopen only for a concrete product capability missing from OpenCaseLaw.

### Legal Distance
Historical representation/distance research is preserved and PAUSED. Reopen only if query-specific retrieval/map tests expose a precise representation deficit.

### Fractal Map
Historical global hierarchy work is preserved and PAUSED. Reuse clustering/rendering code; do not repair the universal 174k map unless a query-specific product need proves it necessary.

## Control plane

`main` owns mission, agents, workflows, directives and factory direction. Persistent lab branches execute the latest control plane from `main`; stale role definitions on lab branches are not authoritative.

A cycle works on an isolated branch. Independent audit gates promotion. Rejected work never silently becomes accepted state.

Accepted branches:
- `lab/corpus`
- `lab/legal-distance`
- `lab/fractal-map`
- `lab/evaluation`
- `lab/product`
- dynamic `lab/frontier/<team_id>`

## Autonomous throughput doctrine

Repository-owner attention is the scarce resource; autonomous agent cycles are cheap.

Therefore:
- direction changes cancel superseded same-lane work;
- technical/network/model failures retry or rotate automatically;
- multiple healthy free OpenCode models should be load-balanced when available;
- independent engineering tracks run in parallel;
- Product integrates incrementally rather than waiting for portfolio completion;
- agents choose libraries/layouts/thresholds/repair strategies autonomously;
- human escalation is reserved for a ready-to-test product or an unavoidable owner-level product/business/legal/external-access decision.

## Output layout
- lane implementation: `corpus/`, `legal_distance/`, `fractal_map/`, `evaluation/`, `product/`
- tests: `tests/<lane>/`
- immutable outputs: `results/<lane>/`
- reports: `reports/<lane>/`
- accepted lane state: `state/<lane>.json`
- lane directives: `directives/lanes/<lane>.md`
- dynamic Frontier: `frontier/<team>/`, `results/frontier/<team>/`, `state/frontier/<team>.json`

## Invariants
- At most one active run per core lane or Frontier team, but different lanes/teams should run in parallel.
- Newer direction/charter work supersedes stale same-lane/team work.
- PASS required for accepted promotion.
- Audit REVISE means concrete repair; BLOCKED prevents dishonest loops.
- Supervisor dispatch is idempotent.
- A repair cannot succeed with zero durable delta.
- Historical accepted/negative evidence is preserved.
- Human-authorized Frontier charters remain active until their stop/promote rule is met or an ACCEPTED equivalent supersedes them.
- Product does not stop at a partial milestone; `human_gate_ready=true` is the normal handoff point.

## Active vs historical control state
`state/frontier_portfolio.json` contains only executable/current Frontier teams. Retired/superseded charters are moved intact to `state/archive/frontier_portfolio_history.json`; their full implementation/audit evidence remains on lab/cycle branches. Active blockers live only under `state/blockers/`; retired blockers belong under `state/archive/blockers/`.

`main` is deliberately lightweight. Full result arrays, parquet files, benchmark dumps and historical reports must NOT be mirrored to main. `results/accepted-state/` plus `results/ACCEPTED_CATALOG.json` are the compact accepted-state index; detailed artifacts live on the accepted lab branch that produced them.

## Progressive query execution
The UI should become useful in stages instead of blocking on one monolithic request:
1. retrieve/dedupe broad candidates;
2. render an initial query map;
3. enrich selected evidence and stream/generate the sourced answer;
4. run adversarial retrieval/classification;
5. patch counter-authorities/relations into the existing bundle/map.

The broad map pool and LLM evidence pack are deliberately different sizes. Query-specific mode must not load global 174k matrices on startup. Full-text decision bodies are lazy. Expensive geometry is cached by retrieval/config hash.
