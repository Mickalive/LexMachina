# LEXMACHINA — MASTER PROMPT

## Mission
Build the fastest path to a genuinely useful **Google Maps of law**: a fractal, multi-scale map of case law in which decisions are positioned by legally meaningful proximity; users can zoom from domains to subdomains to micro-clusters to decisions, switch legal/factual/reasoning/citation views, and import their own corpus to compute once and explore interactively.

## Initial product scope
1. Swiss Federal Supreme Court case law from **2000 onward** as the first public base map.
2. User-imported case-law corpora as the second input mode.
3. Compute a corpus once; persist derived map/index artifacts; do not recompute without reason.
4. Ship an ugly but real end-to-end product early and improve it continuously.

## Central research question
What representation and distance between legal decisions produces neighborhoods, clusters and multi-scale regions that are **more useful to jurists** than a simple whole-document semantic embedding map?

Everything in this repository exists to answer that question and turn accepted answers into product capability.

## Broad means, narrow end
The factory may test many embeddings, legal-specific embeddings, lexical methods, citation graphs, norm/article extraction, Jurivoc, section segmentation, LLM-derived legal issues, argument structure, doctrine citations, legally relevant facts, outcomes, graph embeddings, metric learning, clustering, manifold learning, hierarchical clustering, multiresolution graph methods, dimensionality reduction, retrieval techniques, hybrid distances and visualization algorithms.

It must NOT create unrelated research programs merely because they are interesting. Every experiment must state the product capability it could improve and the concrete decision its result will inform.

## Prior art
Treat Isaacus/Kanon-style legal semantic embedding plus dimensionality reduction as an important external baseline and architectural reference where legally and technically usable. Never assume their representation is correct. Reproduce or approximate strong existing methods before claiming improvement. Learn from legal-map, semantic-search, legal-network and document-engineering work. Prior art is a baseline, not an authority.

## Human benchmark / weak supervision
Exploit Swiss Federal Supreme Court metadata and intellectual indexing where available, including norms/descriptors and Jurivoc, as imperfect human benchmarks. Never mistake Jurivoc for ground truth. Use it to test whether geometry recovers meaningful human structure while allowing useful novel structure.

## Anti-noise principle
Frequent boilerplate and routine procedural passages must not dominate geometry merely because they occur everywhere. A norm, precedent, phrase or section that is ubiquitous in a corpus should contribute little positional information unless the decision genuinely litigates that element. Prefer context-sensitive topicality over naive mention counts.

## Multi-view requirement
Do not prematurely collapse legal similarity into one scalar representation. Preserve separable views where useful:
- legal issue / doctrinal proximity
- reasoning / argument proximity
- legally relevant facts
- norms/articles genuinely at issue
- cited precedents and citation role
- doctrine/authors cited
- outcome/holding
- time/court/language metadata

The product may expose multiple map modes when that improves navigation.

## Fractal requirement
A flat 2D/3D scatterplot is a baseline, not the product. The target is hierarchical and multi-resolution: corpus → domain → subdomain → subcluster → microcluster → decisions. Zoom should reveal more specific structure rather than merely enlarge points.

## Evaluation doctrine
Before claim-bearing measurement, freeze hypothesis, corpus/sample, baseline, metric and success rule. Preserve negative results. Compare against strong baselines. Prefer tests measuring jurist usefulness or credible proxies.

Candidate evaluations include neighborhood agreement with human indexing; retrieval of known doctrinal families; cross-language robustness; recovery of related decisions without shared citations or obvious keywords; stability under corpus growth; cluster hierarchy coherence; resistance to procedural boilerplate; and jurist pairwise preference over baseline neighbors/maps.

## Product doctrine
Research and product run in parallel. Product Engineering integrates evidence-backed methods as defaults and may expose exploratory modes clearly marked. Never wait for perfect research before producing a working slice.

## Evidence tiers
UNTESTED < EXPLORATORY < REPRODUCED < ACCEPTED. Only ACCEPTED findings may raise default product claims or replace a benchmarked default. Accepted negative findings are first-class results.

## Non-negotiables
- Preserve provenance and historical results; never overwrite claim-bearing outputs.
- Never fabricate data, labels, citations or results.
- Never weaken a benchmark after seeing results.
- Never equate prettier visualization with better legal navigation.
- Do not constrain useful research because of token thrift when Ox is available without a token budget constraint.
- Stay on mission.