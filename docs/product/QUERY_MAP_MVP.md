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

## 4. Zero-cost invariant

The MVP must incur **zero mandatory external API spend**.

Allowed:
- OpenCaseLaw public API / MCP;
- standard GitHub Actions runners on this public repository;
- OpenCode free models / currently healthy free fallback models;
- open-source Python/JS libraries;
- locally downloadable open-source models if they fit standard runner resources;
- existing repository artifacts.

Forbidden as required dependencies:
- paid embedding APIs;
- paid reranking APIs;
- paid LLM APIs;
- paid vector databases;
- paid search APIs;
- paid hosted inference.

A paid service may only be documented as an optional future benchmark, never used by the canonical MVP path.

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

If the factory cannot produce a clickable end-to-end prototype using only free dependencies, existing repository code, and OpenCaseLaw public infrastructure, the project is too operationally expensive relative to its differentiation and should be stopped.

If it produces the prototype but the visual layer does not materially improve legal research over answer + ranked list, stop the standalone product.
