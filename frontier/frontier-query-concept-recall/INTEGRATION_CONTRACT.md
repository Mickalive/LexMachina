# SUPERSEDED — do not integrate from this file

**This document is dead. Do not copy its code into `product/`.**

Superseded bytes: `sha256 709599e621d33499d0b6a187c3bec5f08aed034a7a11ac1e6c6acf7ec37c9cdc`
(207 lines). Provenance: `results/frontier/frontier-query-concept-recall/artifact_hygiene_39179862363.json`.

This file lived in the **hyphenated** directory `frontier/frontier-query-concept-recall/`.
A directory name containing `-` is not a Python package target, so
`python -m` can never load the sibling code — this whole directory is an
un-importable duplicate of the canonical package
`frontier/frontier_query_concept_recall/`.

## Why it was withdrawn

Three defects, each mechanically demonstrated by
`python -m frontier_query_concept_recall.contract_check`:

1. **It names four symbols that have never existed.** §1 of this document told
   the integrating lane to run
   `from ...expansion import ExpansionConfig, build_variants, search_variants, QueryVariant`.
   The shipped module exports `CorpusSample`, `Expansion`, `build_expansion`,
   `blanked`, `shuffled`, `compound_stems`, `norm`, `tokens` — and **none** of
   the four documented names. A paste of §1 into `product/query/pipeline.py`
   is an `ImportError` at first call.

2. **Its drop-in seam is not the seam the measured contract names.** This
   document points at `run_query_initial()` (line ~534) and describes
   pre-retrieval query construction. The canonical contract names
   `enrich_query_bundle(initial_bundle=...)` (line 800), the strictly additive
   post-retrieval seam the layer was actually measured against. These are
   different integration points with different blast radius on the served
   bundle.

3. **It is not measured.** §7 is an unfilled "to be filled after harness run"
   table. The layer it describes was measured and returned
   `OUTCOME_B_BOUNDED_NEGATIVE`: 0 of 6 failing FR/IT authority cells improved,
   0 of 3 served questions' under-covered concepts reduced, and 10 of 15 added
   searches over the frozen per-search latency budget (max 83.5 s against
   < 30 s). **Do not adopt this component.** See the canonical contract.

## Where the real contract is

| You want | Read this |
|---|---|
| The executable handoff record (machine-checked) | `results/frontier/frontier-query-concept-recall/integration_contract_39179862363.json` |
| Proof the handoff matches the code, the product seam and the frozen ceiling | `results/frontier/frontier-query-concept-recall/contract_check_results_39179862363.json` (10/10 pass) |
| Proof the superseded contract fails those same checks | `results/frontier/frontier-query-concept-recall/contract_check_results_superseded_39179862363.json` (3 fail) |
| The measured record it is derived from | `results/frontier/frontier-query-concept-recall/harness_results_39179862363.json` |
| The runnable code | `frontier/frontier_query_concept_recall/` (importable package) |
| The harness | `python -m frontier_query_concept_recall.cli --bundle <path> --out <dir> [--offline]` |

Verify the real contract before you integrate it:

```
cd frontier
python -m frontier_query_concept_recall.contract_check \
  --contract ../results/frontier/frontier-query-concept-recall/integration_contract_39179862363.json \
  --harness   ../results/frontier/frontier-query-concept-recall/harness_results_39179862363.json \
  --out ../results/frontier/frontier-query-concept-recall --label verify
```

Exit code 0 means every claim in the contract is executable as written.

## Claim ceiling (verbatim, still in force)

> No artifact may assert that a map helps a jurist, that any authority is
> absent from the corpus, that any frozen bar is met or moved, or that any
> packet is fit to serve. Usefulness remains the human product gate's question
> and admission remains fail-closed. Concept-coverage counts are lexical
> coverage of a retrieved set, not a legal conclusion, and a zero count is a
> retrieval signal, not proof of corpus absence.

Product remains the integrator and must record an adopt/decline decision;
silent non-consumption is not an outcome the contract permits of itself.