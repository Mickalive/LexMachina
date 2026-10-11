# LEXMACHINA — MASTER PROMPT

## Mission
Build the fastest path to a genuinely useful **visual legal research interface** for Swiss case law.

LexMachina is not required to discover one universal geometry of all jurisprudence. Its core product is query-specific:

> legal question → broad retrieval → sourced AI answer → visual map of the relevant jurisprudence → explicit search for contrary / limiting authority.

The map exists to help jurists see branches, minority lines, exceptions, isolated decisions and relationships that a ranked text list or a single AI answer can hide.

## Initial product scope
1. Swiss case law as the first public domain.
2. Use **OpenCaseLaw public infrastructure as the default data source** instead of rebuilding the national corpus and citation graph.
3. For each query, retrieve broadly, preserve high recall, then build a map over a tractable result set.
4. Keep the AI answer and the visual map side by side: the map is an audit/exploration layer for the answer.
5. Explicitly search for decisions that contradict, limit, distinguish or create exceptions to the provisional answer.
6. Ship a clickable end-to-end prototype before doing more fundamental representation research.
7. User-imported corpora remain a later capability, not the MVP critical path.

## Central product question
For a real legal research query, does **AI answer + visual query map** help a jurist discover and understand relevant jurisprudence — especially contrary or minority authority — better than an AI answer plus a conventional ranked list?

Everything in this repository exists to answer that question and turn a positive answer into product capability.

## Query-conditioned structure
Do not assume every decision has one globally correct position in a universal legal space.

The relevant structure is allowed to depend on the current research question, active relation layer and retrieved candidate set.

The same decision may occupy a different position for a different query. This is expected.

## Retrieval-first doctrine
A visualization cannot reveal an authority that retrieval failed to find.

Therefore:
- optimize recall before map aesthetics;
- search across FR/DE/IT;
- use norms, citations and query expansion where useful;
- preserve lower-ranked candidates that may represent contrary or minority lines;
- run an independent adversarial retrieval pass against the provisional answer.

## Adversarial research requirement
For every substantive research query, the product should attempt to find authority that could:
- contradict the provisional answer;
- narrow it;
- distinguish the facts or legal issue;
- reveal an exception;
- expose an older/minority line;
- reveal a language-specific branch.

These authorities must remain visible in the result set even when they are not top-ranked by the initial search.

Never classify a case as supporting/contrary/limiting unless the evidence supports that label.

## Visual map requirement
The map is a research interface, not decoration.

Minimum semantics:
- point = decision;
- proximity = query-conditioned similarity/relation;
- cluster = coherent group of retrieved decisions;
- outlier = weakly connected/isolated result worth inspecting;
- relations/citations can be revealed on selection;
- cluster labels explain why a group exists;
- counter-authorities are visually discoverable.

2D or 3D is an implementation choice. A 3D point cloud is not inherently better. Use 3D only if it improves comprehension.

## Data-source doctrine
Prefer open, maintained infrastructure over rebuilding commoditized components.

For Swiss public law research, OpenCaseLaw is the canonical first source for the MVP because it provides public search, decision records, laws and citation infrastructure.

Preserve the legacy LexMachina 174k corpus and all accepted/rejected research results as historical evidence and optional fallback/test data, but do not keep them on the critical path unless the new product actually needs them.

## Owner-time invariant
The scarce development resource is **the repository owner's attention**, not autonomous agent compute.

For development/testing, use free OpenCode models, local open-source models, OpenCaseLaw public infrastructure and existing repository assets so the owner is not required to provision paid APIs just to evaluate the MVP.

This does NOT constrain the eventual production stack: a deployed product may use paid/local/hosted LLM, embedding or reranking services when justified.

The factory must optimize for low owner involvement:
- retry/reroute technical failures autonomously;
- choose implementation details autonomously;
- reuse existing work before rebuilding;
- never ask the owner to supervise ordinary engineering;
- surface a human gate only for a ready-to-test product or a genuine product/business/legal/external-access decision.

## Broad means, narrow end
The factory may use lexical search, BM25/TF-IDF, multilingual query expansion, citation expansion, open-source embeddings, graph methods, reranking, clustering, projection, WebGL/Canvas, answer generation, counter-authority retrieval and other methods that directly improve the query-map product.

Do not launch broad research programs merely because they are scientifically interesting.

Do not rebuild:
- a national Swiss case-law corpus;
- a national citation graph;
- a universal 174k embedding space;
- a universal fractal hierarchy;

unless a concrete MVP capability cannot be built without it.

## Reuse doctrine
Reuse existing LexMachina work when it shortens time-to-product:
- TF-IDF / lexical tooling;
- multilingual robustness tests;
- clustering and hierarchy code;
- WebGL / Canvas rendering;
- LOD / culling;
- navigation / decision detail components;
- evaluation discipline;
- negative/null results.

Legacy join-alignment, dense-embedding and corpus-scale graph problems are not MVP blockers unless they directly affect the query-specific pipeline.

## Evaluation doctrine
Before claim-bearing measurement, freeze hypothesis, query set, baseline, metric and success rule. Preserve negative results. Never weaken a benchmark after seeing results.

Automated evaluation should cover:
- recall of known relevant authorities;
- recall of known contrary/limiting authorities;
- source validity;
- duplication;
- language robustness;
- reproducibility;
- latency;
- cluster stability.

Automated metrics do not prove that the visualization is useful.

## Human product gate
Further investment is justified only if real legal research tasks show that the visual layer materially improves the experience over answer + ranked list.

The key questions are:
1. Did the map expose a relevant branch, exception or decision that was less visible in the list/answer?
2. Did the map make the jurisprudential structure easier to understand?
3. Did the map increase confidence that contrary authority had not been hidden?
4. Was the combined answer + map preferable to the conventional interface?

If not, stop the standalone product.

## Product doctrine
Build the smallest clickable end-to-end slice first.

Canonical implementation order:
1. free OpenCaseLaw retrieval + caching;
2. free reranking / result bundle;
3. sourced AI answer;
4. independent counter-authority pass;
5. query-specific interactive map over roughly 100–300 decisions;
6. frozen automated tests;
7. human product test.

Only after this gate should the factory invest in more sophisticated global geometry, dense embeddings, custom corpus infrastructure or 3D.

The authoritative MVP specification is `docs/product/QUERY_MAP_MVP.md`.

## Evidence tiers
UNTESTED < EXPLORATORY < REPRODUCED < ACCEPTED. Only ACCEPTED findings may raise default product claims. Accepted negative findings are first-class results.

## Non-negotiables
- Preserve provenance and historical results; never overwrite claim-bearing outputs.
- Never fabricate data, labels, citations or results.
- Never weaken a benchmark after seeing results.
- Never equate prettier visualization with better legal navigation.
- Do not require the owner to provision paid APIs merely to develop/test the MVP; future production inference may be paid or local.
- Technical failures auto-retry/recover; dead ends reroute. Only a genuine human decision may stop the factory.
- Stay on the product mission.
