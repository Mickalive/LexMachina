# LexMachina — Query Map MVP

Status: CANONICAL PRODUCT TARGET
Date: 2026-10-11

## 1. Product purpose

LexMachina is a legal research interface, not a project to discover one universal geometry of all Swiss case law.

The user asks a legal research question. LexMachina must return:

1. a sourced AI answer;
2. the relevant cases used to support that answer;
3. a visual map of the broader retrieved jurisprudence;
4. an explicit adversarial search for cases that contradict, limit, distinguish, or create exceptions to the provisional answer.

The visual map exists to help a jurist see structure that a ranked text list can hide: minority lines, isolated cases, alternative doctrinal branches, and unexpected bridges between groups.

## 2. Core product loop

For a query Q:

1. Retrieve broadly from OpenCaseLaw.
2. Expand around strong candidates using citations where useful.
3. Preserve a high-recall candidate pool.
4. Rank / filter to a tractable map set (target: 100–300 decisions for the first MVP).
5. Independently search for contrary / limiting / distinguishing authorities.
6. Build a query-specific similarity / relation graph.
7. Cluster and project that graph into an interactive map.
8. Generate concise cluster labels with provenance.
9. Produce a sourced AI answer.
10. Let the user inspect any decision, cluster, relation, or contrary authority.

The same decision may occupy a different position for a different query. This is expected.

## 3. Data source

Primary Swiss public source: OpenCaseLaw public REST/MCP infrastructure.

Requirements:
- no paid API key;
- no login dependency for core public endpoints;
- cache retrieved records locally for reproducibility;
- preserve source URLs / decision IDs;
- fail gracefully if the remote service is unavailable;
- do not rebuild OpenCaseLaw's national corpus or citation graph unless a product-critical capability is missing.

The legacy 174k corpus and its artifacts remain preserved as research evidence and optional fallback/test data, but are no longer the critical path.

## 4. Owner-time invariant

The scarce resource is **the repository owner's attention**, not agent compute.

For development and testing, the canonical path must work without requiring the owner to buy or provision paid inference. Prefer:
- OpenCaseLaw public API / MCP;
- OpenCode free models / healthy free fallbacks;
- locally runnable open-source models;
- open-source Python/JS libraries;
- existing repository artifacts.

This is a development/test constraint, NOT a permanent product architecture constraint. A future production service may use paid or hosted LLM/embedding/reranking infrastructure if that improves the product and has a viable business case.

The factory must not trade away product quality or create needless engineering solely to avoid hypothetical future inference cost.

Owner-attention rules:
- technical failures auto-retry or reroute;
- implementation choices inside the canonical mission are made autonomously;
- do not ask the owner to choose libraries, embeddings, layouts, thresholds, or repair strategies;
- do not ask for manual data preparation that agents can perform;
- surface a human gate only when a clickable product is ready for judgment, or when an unavoidable product/business/legal/external-access choice genuinely requires the owner.

## 5. Retrieval-first doctrine

A visualizer cannot reveal a case that retrieval never found.

Therefore the first product metric is retrieval coverage, not map beauty.

The pipeline should combine free techniques as useful:
- OpenCaseLaw lexical / filtered search;
- query expansion in DE/FR/IT;
- exact norm / citation retrieval;
- citation-neighborhood expansion;
- TF-IDF / BM25 reranking;
- existing accepted LexMachina representations where they help;
- optional open-source multilingual embeddings if they improve retrieval on frozen tests without paid inference.

Do not build a new universal 174k embedding space merely to satisfy this MVP.

## 6. Adversarial / counter-authority pass

After drafting a provisional answer, run an independent retrieval pass whose instruction is to find authorities that could:

- contradict the provisional conclusion;
- narrow it;
- distinguish the factual/legal situation;
- reveal an exception;
- show a minority or older line;
- expose a language-specific branch;
- undermine the apparent consensus.

These cases must be retained in the map even when their initial relevance score is lower.

The UI must distinguish "supporting", "limiting", "contrary/exception", and "unclassified" only when the classification is actually supported. Uncertain classifications must remain uncertain.

## 7. Query-specific map

The map is generated from the retrieved set, not from a claim that all Swiss cases possess one canonical global position.

Minimum map semantics:
- point = decision;
- spatial proximity = query-conditioned similarity / relation strength;
- cluster = locally coherent result group;
- visible outliers = isolated or weakly connected decisions;
- citation/relation edges available on selection;
- counter-authorities visually discoverable;
- cluster labels explain why the group exists.

2D or 3D is an implementation choice. 3D is useful only if it increases comprehension. A beautiful 3D point cloud with no readable legal structure fails.

## 8. AI answer

The AI answer and the map are complementary.

Answer requirements:
- answer the legal question;
- cite decisions actually retrieved from the source;
- separate strong propositions from uncertainty;
- mention material counter-authorities / exceptions surfaced by the adversarial pass;
- provide links / identifiers so the user can inspect the underlying decision.

The map must remain available after the answer so the user can independently audit what the AI said.

## 9. MVP UI

One page is enough.

Required:
- search / question input;
- sourced answer panel;
- interactive map;
- result count;
- cluster labels;
- decision detail panel;
- toggle / emphasis for counter-authorities;
- relation edges on selection;
- search within current result set;
- reset / fit view.

Nice-to-have, not MVP blockers:
- 3D terrain;
- animation;
- full corpus browse mode;
- custom corpus import;
- multiple legal views.

## 10. Reuse from existing LexMachina

Reuse only when it reduces time-to-test:
- existing TF-IDF / lexical tooling;
- multilingual robustness tests;
- clustering / hierarchy code;
- WebGL / Canvas rendering;
- LOD / culling;
- decision detail / navigation components;
- benchmark discipline and negative results.

Do NOT block the MVP on:
- global 174k id→cluster alignment;
- global citation-graph reconstruction;
- dense 174k embeddings;
- universal fractal hierarchy;
- BGE/bger crosswalk work beyond what the new query pipeline actually needs.

## 10A. Reuse-first inventory

The product pivot does **not** invalidate the month of prior LexMachina work. Reuse existing implementation before replacing it.

Known reusable assets on `lab/product` include:
- `product/server.py`: threaded stdlib HTTP server, response cache, rate limiting, health/error patterns and API routing;
- `product/static/index.html`: existing interactive WebGL/Canvas map UI, search/filter controls and decision/cluster interaction patterns;
- `product/app/navigation.py`: navigation/search/decision/neighbor/citation API patterns;
- `product/app/map_loader.py`: representation/map loading contracts;
- existing clustering/projection tooling based on scikit-learn, NetworkX, igraph/Leiden and UMAP;
- existing spatial-index, LOD/culling, proximity-explanation and import patterns;
- accepted evaluation work on multilingual robustness, jurist preference, boilerplate resistance and deterministic benchmarking.

Reuse rule:
1. adapt before rewriting;
2. preserve historical artifacts and negative results;
3. if an old global-174k assumption blocks adaptation, isolate it behind a new query-bundle adapter rather than replacing the whole server/UI;
4. the preferred new abstraction is a `query_result_bundle` consumed by the existing product shell.

Suggested minimum `query_result_bundle` fields:
- query;
- generated_answer + cited decision IDs;
- retrieval metadata/provenance;
- decisions[];
- per-decision retrieval/rerank scores;
- counter_authority_status with uncertainty;
- cluster_id / cluster_label;
- x/y (and optional z) projection;
- typed relations/citations;
- source URL / citation string.

## 10B. Autonomous execution / anti-drift rule

The MVP should not need another open-ended research program, but **there is no arbitrary limit on free autonomous agent cycles**.

Preferred milestone sequence:
- first usable vertical slice: real OpenCaseLaw/cached query -> query_result_bundle -> source-linked clickable map using reused UI/server;
- next: sourced generative answer + independent counter-authority pass integrated into that same UI;
- then: autonomous fixes driven by evaluation until the product is ready for the human product gate.

Agents may iterate as long as they are making measurable progress. Repeated cycles with no executable delta must trigger autonomous diagnosis, rerouting or narrower implementation — not a request for owner intervention.

The relevant cost metric is owner attention:
- zero owner involvement during routine implementation/debugging;
- one owner checkpoint when a genuinely usable end-to-end product is ready;
- additional owner involvement only for a true product decision that autonomous evidence cannot resolve.

## 11. Automated evaluation

Create a small frozen set of real Swiss legal research questions with known useful authorities and at least some known limiting / contrary authority where feasible.

Measure:
- recall of known relevant authorities;
- recall of known counter-authorities;
- duplication rate;
- language robustness;
- source validity;
- cluster stability;
- latency;
- deterministic reproducibility of cached runs.

Do not pretend these automated tests prove UX usefulness.

## 12. Human product gate

The MVP earns further investment only if a jurist can use it on real research questions and answer YES to at least two of the following:

1. The map exposed a relevant branch / case / exception that was less visible in the ranked list or AI answer.
2. The map made the structure of the jurisprudence easier to understand.
3. The map increased confidence that contrary authority had not simply been hidden by the answer.
4. The combined answer + map was preferable to a conventional answer + result list.

If this does not happen on a small set of real research tasks, STOP investing in LexMachina as a standalone product.

## 13. Immediate implementation order

### Milestone A — end-to-end free query pipeline
OpenCaseLaw query → cached candidate set → free reranking → AI answer → JSON result bundle.

### Milestone B — adversarial retrieval
Independent counter-authority search → merge/deduplicate → classify conservatively → expose in result bundle.

### Milestone C — clickable query map
100–300 decisions → similarity/relation graph → clusters → projection → interactive browser UI.

### Milestone D — product evaluation
Frozen benchmark queries + human test. Only after this gate should the factory spend effort on more sophisticated geometry, 3D, dense embeddings, or large-scale custom infrastructure.

## 14. Kill rule

If repeated autonomous work cannot produce a clickable end-to-end prototype without consuming repeated owner attention, record that as a failure of the autonomous-development approach and simplify/reroute before asking the owner to intervene.

The substantive kill rule is product usefulness: if a working prototype shows that the visual layer does not materially improve legal research over answer + ranked list, stop the standalone product.
