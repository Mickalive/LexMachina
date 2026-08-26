# LexMachina Factory Architecture

## Control plane
`main` owns mission, agents, workflows, directives and factory direction. Persistent lab branches execute the latest control plane from `main`; stale role definitions on lab branches are not authoritative. The Ox launcher itself must self-pin to the current `main` version before execution, and an hourly reconciliation workflow repairs persistent lab branches that missed a launcher update.

## Accepted branches
- `lab/corpus`
- `lab/legal-distance`
- `lab/fractal-map`
- `lab/evaluation`
- `lab/product`
- dynamic `lab/frontier/<team_id>`

A cycle works on an isolated cycle branch. An independent audit gates promotion. Rejected work never silently becomes accepted state.

## Core lanes
### Corpus
Acquire/normalize Federal Supreme Court decisions from 2000 onward; preserve provenance, metadata and structure; support user corpus import.

### Legal Distance
Discover and benchmark representations/distances: semantic, legal issue, reasoning, facts, norms, citations, doctrine, outcome and hybrids.

### Fractal Map
Convert accepted similarity/distance evidence into stable multi-resolution regions and zoomable map structures.

### Evaluation
Build falsification harnesses, Jurivoc/TF weak-supervision benchmarks, neighbor tests, boilerplate tests, multilingual tests, stability tests and jurist-usefulness evaluation.

### Product
Continuously build a usable end-to-end application: TF base map, zoom/navigation, map modes, decision inspection, corpus import, persisted recomputation artifacts.

## Dynamic Frontier teams
The Factory Director may create, continue, pause, kill or promote specialized Frontier teams when concrete evidence opens a product-relevant path. More credible independent paths may justify more teams in parallel. Every charter must identify a product capability, precise question, why-now evidence, non-duplication rationale and acceptance test. Frontier exploration is elastic in means but never in mission.

`state/frontier_portfolio.json` is an append-only charter ledger by `(team_id, charter_version)`. Once a charter version has been dispatched, its substantive fields must never be rewritten or deleted. A successor hypothesis is a new `charter_version`; the old entry changes only lifecycle status such as RUN → PAUSE / TERMINATE / PROMOTE / SUPERSEDED. This preserves the exact charter for in-flight team runs, later audits and historical reproducibility.

## Output layout
- lane implementation: `corpus/`, `legal_distance/`, `fractal_map/`, `evaluation/`, `product/`
- tests: `tests/<lane>/`
- immutable outputs: `results/<lane>/`
- reports: `reports/<lane>/`
- accepted lane state: `state/<lane>.json`
- lane directives: `directives/lanes/<lane>.md`
- dynamic Frontier: `frontier/<team>/`, `results/frontier/<team>/`, `state/frontier/<team>.json`

## Invariants
- At most one active run per core lane or Frontier team.
- PASS required for accepted promotion.
- Audit REVISE means concrete same-cycle repair; BLOCKED/REJECT prevents dishonest loops.
- Supervisor dispatch must be idempotent.
- Transient Ox/network failures retry; scientific/product failures remain failures.
- A repair cannot succeed with zero durable delta.
- Accepted results are mirrored to `main/results/` without deleting history.
- Product runs continuously but exploratory science does not silently become a default.
- A dispatched Frontier charter is immutable forever at its exact version.
