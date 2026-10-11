# Product lane — query-map fast path

Ship the shortest runnable path to the canonical query-map MVP in `docs/product/QUERY_MAP_MVP.md`, while minimizing repository-owner attention.

## REUSE-FIRST mandate
Before writing replacement infrastructure, inspect the existing `lab/product` implementation and accepted peer mounts. Reuse working components whenever they shorten time-to-clickable-product. In particular, prefer adapting the existing:
- stdlib threaded HTTP server and response cache;
- search / decision-detail / citation / neighbor API patterns;
- WebGL + Canvas frontend;
- clustering / Leiden / UMAP utilities;
- map loading, navigation, LOD / culling and spatial-index patterns;
- multilingual robustness and proximity/evaluation utilities.

Do NOT rebuild these just because the product mission changed. Delete/replace code only when the old global-174k assumptions make reuse slower than adaptation.

## Product fast path
The first priority is a runnable vertical slice, not a report.

A valid producer cycle must materially advance executable code toward:
question -> OpenCaseLaw retrieval/cache -> query result bundle -> free reranking -> sourced generative answer -> independent counter-authority pass -> query-specific clickable map.

For the first clickable slice, simple and correct beats sophisticated:
- target roughly 100–300 retrieved decisions;
- TF-IDF/BM25 + citation expansion is acceptable;
- simple deterministic clustering/projection is acceptable;
- reuse the current frontend rather than redesigning it;
- 2D is acceptable; 3D is explicitly NOT a blocker;
- a cached OpenCaseLaw fixture is acceptable for deterministic tests while live retrieval remains available.

## Anti-overengineering
Do NOT spend an MVP cycle on:
- universal 174k alignment;
- rebuilding the Swiss corpus/citation graph;
- dense 174k embedding generation;
- global fractal hierarchy;
- custom model training;
- requiring the owner to provision paid inference for development/testing;
- cosmetic redesign;
- broad architecture prose before a vertical slice exists.

## Cycle output requirement
Every normal product cycle must leave runnable code or tests. A cycle that produces only plans/reports/specs is REVISE unless execution is genuinely externally blocked.

The first successful product cycle should, at minimum, allow a developer to run one local command/server, submit or select a real Swiss-law query fixture, and see a source-linked clickable result map. Generative answer/counter-authority functionality should be added in the same cycle if feasible; otherwise it is the immediate next delta.

Do not involve the owner during ordinary implementation/debugging. Continue autonomously through retries, narrower slices and repairs until there is a genuinely clickable end-to-end artifact worth testing, or an unavoidable owner-level decision.

## Owner-attention rule
Agent cycles are cheap; owner attention is expensive. There is no fixed cycle limit while executable progress continues. If a cycle stalls, diagnose and reroute autonomously. Do not ask the owner to choose technical details or babysit failures. The next normal owner interaction should be a usable product test.

## Parallel integration rule
Three human-authorized Frontier engineering teams may produce retrieval, generative-audit, and query-map UI components in parallel. Do NOT wait for all teams. At the start of every product cycle, inspect ACCEPTED mounts under /tmp/lex_accepted/frontier and immediately absorb any component that passes its integration contract.

Product remains responsible for the end-to-end app and may implement the same missing seam itself if a Frontier team is slow. Frontier teams are accelerators, not dependencies.

Until the product state explicitly records `human_gate_ready: true` with a locally runnable question -> sourced answer -> counter-authority -> clickable map path, keep `continue_recommended: true`. A partial milestone is not a reason for the lane to stop.
