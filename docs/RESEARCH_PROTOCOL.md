# Research Protocol

Every research cycle answers one bounded question that can change a product or research decision.

1. Read the Master Prompt, current factory direction and lane directive.
2. Inspect relevant ACCEPTED evidence from other lanes/frontiers.
3. State hypothesis, baseline and product decision unlocked.
4. Freeze claim-bearing sample, metric and success rule before observing result.
5. Implement the smallest rigorous discriminating experiment.
6. Run it; preserve raw outputs and failures.
7. Compare with baseline and report uncertainty/failure modes.
8. Write machine-readable lane state plus human-readable report.
9. Recommend CONTINUE, PIVOT_WITHIN_MISSION, BLOCKED, PRODUCTIZE or PAUSE.

Preferred baselines include whole-document generic embedding, legal embedding/Isaacus-style baseline where accessible, lexical retrieval, citation-only, norms-only and simple hybrids before complex learned methods.

Core evaluation families: Jurivoc/human-index agreement where available; nearest-neighbor legal relevance; known-lineage recovery; no-explicit-citation lineage recovery; boilerplate resistance; multilingual invariance; corpus-scale stability; hierarchy coherence; and human preference.

## Mandatory accepted-state fields
Every core research lane must keep `state/<lane>.json` machine-readable and set at least: `lane`, `direction_version`, `evidence_tier`, `cycle_status`, `continue_recommended`, `accepted_run_id` (or proposed run id before audit), `evidence_refs`, and `next_recommendation`. `continue_recommended=true` means another cycle under the SAME factory-direction question has a concrete discriminating purpose; it is not a generic request to keep running. When no additional same-question cycle is justified, set it false so the Factory Director can decide the successor question.

Frontier states must analogously preserve `team_id`, `charter_version`, `evidence_tier`, `cycle_status`, `continue_recommended`, provenance/evidence references and the charter stop/promote recommendation.

## Product-engineering cycles
Product and engineering Frontier cycles are not required to manufacture a scientific hypothesis when the task is implementation. They must instead state the concrete capability/integration contract, reuse available accepted components, produce runnable code/tests/fixtures, and verify the acceptance contract.

For the query-map MVP, do not require obsolete universal-174k metrics to gate query-specific components. Evaluate the capability actually being shipped.

## Owner-attention / continuation
Autonomous cycles may continue while they produce measurable executable progress. Do not use `continue_recommended=false` on Product merely because one intermediate milestone completed. Product should remain `continue_recommended=true` until it records `human_gate_ready=true` for a locally runnable end-to-end product, unless the current direction is genuinely superseded or structurally blocked.

Technical failures, provider failures, library choices and ordinary implementation decisions are not human blockers. Retry, rotate, narrow or reroute autonomously.
