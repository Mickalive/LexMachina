# Query-map cached-bundle falsification benchmark — run 39834312064

- Schema: `lex-evaluation-query-map-cached-bundle-benchmark/1`
- Verdict: **BENCHMARK_VALID_NO_FALSIFICATION** (exit 0)
- Falsification proven: **True**
- Frozen spec: `evaluation/retrieval_gate/frozen_retrieval_benchmark.json` sha256 `187b0e54b03b326c…` (re-hashed before and after execution, unchanged)
- Cache: 24 raw OpenCaseLaw envelopes, 24 matched to frozen query text

## Per-question results

| question | decisions | clusters | counter candidates | dup suppressed | leg1 | leg2 fires | leg3 fires |
|---|---|---|---|---|---|---|---|
| rent-default | 223 | 7 | 16 | 17 | PASS | True | True |
| corporate-criminal-liability | 218 | 11 | 0 | 22 | PASS | True | True |
| business-judgment-rule | 221 | 13 | 0 | 19 | PASS | True | True |
| petty-theft-dismissal | 205 | 8 | 4 | 35 | PASS | True | True |

## Counter-authority yield (NEGATIVE RESULT)

COUNTER-AUTHORITY DISCOVERY IS EMPTY FOR 2/4 FROZEN QUESTIONS on the cached input: ['corporate-criminal-liability', 'business-judgment-rule']. The counter channel returns rows, but the frozen marker_rule (a norm_token AND a limitation_token in title+regeste+snippet) selects none of them. This is a NEGATIVE RESULT about the product's counter-authority capability measured on real OpenCaseLaw rows, and it is the opposite of a pass: the map's counter layer would be empty for half the query set.

- per-question candidate counts: `{"rent-default": 16, "corporate-criminal-liability": 0, "business-judgment-rule": 0, "petty-theft-dismissal": 4}`
- not claimed: this measures lexical marker yield under the frozen rule on cached rows; it is NOT a measurement of a learned or adjudicated counter classifier, and the Frontier recall component is a separate build


## Recall (measured, NOT thresholded)

| question | known relevant | known counter reach | counter ids also labelled |
|---|---|---|---|
| rent-default | 0/0 (n/a) | 3/9 (0.333) | 0/9 |
| corporate-criminal-liability | 2/2 (1.000) | 4/6 (0.667) | 0/6 |
| business-judgment-rule | 3/5 (0.600) | 1/4 (0.250) | 0/4 |
| petty-theft-dismissal | 1/2 (0.500) | 6/9 (0.667) | 1/9 |

## Reason

real cached OpenCaseLaw input builds a source-linked, duplicate-free, geometry-stable bundle for every frozen question and both regressed inputs are rejected

## Claim ceiling

This benchmark proves only that REAL cached OpenCaseLaw rows carry the fields the query_result_bundle contract needs (decision_id, canonical_url on mcp.opencaselaw.ch, language, citation strings, statutes, a frozen-marker-rule text surface) and that the ACCEPTED harness rejects a regressed bundle. It does NOT prove that Product builds such a bundle, that the map is useful to a jurist, that counter labels are calibrated (counter_uncertainty is a fixed fixture constant), that the coordinates are a good layout (they are a deterministic fixture layout, not a geometry claim), or anything about the absolute LABEL_SOUND / GEOMETRY_SOUND bars. Recall figures are measured, not thresholded.

Machine record: `/home/runner/work/LexMachina/LexMachina/results/evaluation/query_map_cached_bundle_benchmark/39834312064.json`
