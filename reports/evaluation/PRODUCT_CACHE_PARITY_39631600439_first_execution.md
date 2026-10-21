# Product-cache retrieval/counter-authority parity — run 39631600439

- Schema: `lex-evaluation-product-cache-parity/1`
- Direction: v61 (derived from state/evaluation.json)
- Hypothesis: `evaluation/PRODUCT_CACHE_PARITY_HYPOTHESIS_V2.json` sha256 `c994487886bf...` (frozen BEFORE execution; pre-freeze disclosure of the known V1 outcome disclosed in-file)
- Superseded V1 spec: `evaluation/PRODUCT_CACHE_PARITY_HYPOTHESIS_V1.json` sha256 `0e80f0de66fd...` — BYTE-PRESERVED, not modified
- Product pool: `/tmp/lex_accepted/product/results/product/query_cache` identity-matched envelopes (33 of 465 cache files)
- Comparators (both named, both gated): `executed_text_same_query` (the text(s) the product's cache actually ran) and `union_all_frozen_texts` (all six frozen texts the plain OpenCaseLaw client answered)
- Verdict: **FAIL_PRODUCT_CACHE_PARITY** (exit 1), driven by: **coverage**
- Same-text parity family: **PASS** (0 of 7 gates failed)
- Coverage family (union of all frozen texts): **FAIL** (7 of 7 gates failed)
- Falsifier gates failed: **7**
- Non-vacuity: **True**
- Multilingual/provenance reuse leg (V3): **PARTIAL_MISS** (0/3 qids row_ok)
- Elapsed: 1.257 s

## Cells (identity mapping; hits of frozen id sets)

| slug | product pool rows | comparator rows (executed text) | comparator rows (all 6 texts) | texts executed | authority hits (prod/exec/base-union) | counter hits (prod/exec/base-union) | same-text authority | same-text counter | coverage authority | coverage counter |
|---|---|---|---|---|---|---|---|---|---|---|
| rent-default | 264 | 50 | 240 | 1/6 (baseline/fr) | n/a | 0/9/0/3 | NOT_MEASURED | PASS (0 vs 0) | NOT_MEASURED | FAIL (0 vs 3) |
| corporate-criminal-liability | 266 | 50 | 240 | 1/6 (baseline/fr) | 1/2/0/2 | 1/6/1/4 | PASS (1 vs 0) | PASS (1 vs 1) | FAIL (1 vs 2) | FAIL (1 vs 4) |
| business-judgment-rule | 308 | 50 | 240 | 1/6 (baseline/fr) | 0/5/0/3 | 0/4/0/1 | PASS (0 vs 0) | PASS (0 vs 0) | FAIL (0 vs 3) | FAIL (0 vs 1) |
| petty-theft-dismissal | 95 | 50 | 240 | 1/6 (baseline/fr) | 0/2/0/1 | 1/9/0/7 | PASS (0 vs 0) | PASS (1 vs 0) | FAIL (0 vs 1) | FAIL (1 vs 7) |

## Per-(channel, language) comparator decomposition (all gated cells)

Every gated cell is decomposed by the (channel, language) group of the plain OpenCaseLaw baseline record that produced each hit. `E` marks the texts the product's cache actually executed.

| slug | kind | frozen ids | product hits | executed-text comparator | union comparator | comparator-only ids (attribution) |
|---|---|---|---|---|---|---|
| rent-default | authority | 0 | 0 | 0 | 0 | — |
| rent-default | counter | 9 | 0 | 0 | 3 | bge_BGE_117_II_415 -> counter/fr; gr_gerichte_PKG_2010_20 -> baseline/de; zh_mietgericht_MB170006-L -> counter/de |
| corporate-criminal-liability | authority | 2 | 1 | 0 | 2 | bger_6B_124_2016 -> baseline/de/counter/de |
| corporate-criminal-liability | counter | 6 | 1 | 1 | 4 | bge_BGE_146_IV_68 -> baseline/de/counter/de; so_gerichte_BKBES.2026.74 -> counter/de; so_gerichte_STBER.2011.32 -> baseline/de/counter/de |
| business-judgment-rule | authority | 5 | 0 | 0 | 3 | bger_4A_219_2015 -> baseline/de; bger_4A_259_2016 -> counter/de; bger_4A_603_2014 -> baseline/de/counter/de |
| business-judgment-rule | counter | 4 | 0 | 0 | 1 | zh_handelsgericht_HG120149 -> baseline/de/counter/de |
| petty-theft-dismissal | authority | 2 | 0 | 0 | 1 | bger_4A_177_2017 -> baseline/de |
| petty-theft-dismissal | counter | 9 | 1 | 0 | 7 | ar_gerichte_KG_ARGVP_2005_3462 -> baseline/de; bge_BGE_121_III_467 -> baseline/it/counter/de; bge_BGE_124_III_25 -> counter/fr; bge_BGE_130_III_28 -> baseline/it/counter/fr/counter/it; bge_BGE_138_I_113 -> baseline/de/baseline/it/counter/de; so_gerichte_ZZ.1990.7 -> baseline/de/counter/de |

## Per-(channel, language) hit counts

- `rent-default` / authority: `baseline/de` 0 hits, `baseline/fr` 0 hits (E), `baseline/it` 0 hits, `counter/de` 0 hits, `counter/fr` 0 hits, `counter/it` 0 hits
- `rent-default` / counter: `baseline/de` 1 hits, `baseline/fr` 0 hits (E), `baseline/it` 0 hits, `counter/de` 1 hits, `counter/fr` 1 hits, `counter/it` 0 hits
- `corporate-criminal-liability` / authority: `baseline/de` 2 hits, `baseline/fr` 0 hits (E), `baseline/it` 0 hits, `counter/de` 2 hits, `counter/fr` 0 hits, `counter/it` 0 hits
- `corporate-criminal-liability` / counter: `baseline/de` 2 hits, `baseline/fr` 1 hits (E), `baseline/it` 0 hits, `counter/de` 3 hits, `counter/fr` 0 hits, `counter/it` 0 hits
- `business-judgment-rule` / authority: `baseline/de` 2 hits, `baseline/fr` 0 hits (E), `baseline/it` 0 hits, `counter/de` 2 hits, `counter/fr` 0 hits, `counter/it` 0 hits
- `business-judgment-rule` / counter: `baseline/de` 1 hits, `baseline/fr` 0 hits (E), `baseline/it` 0 hits, `counter/de` 1 hits, `counter/fr` 0 hits, `counter/it` 0 hits
- `petty-theft-dismissal` / authority: `baseline/de` 1 hits, `baseline/fr` 0 hits (E), `baseline/it` 0 hits, `counter/de` 0 hits, `counter/fr` 0 hits, `counter/it` 0 hits
- `petty-theft-dismissal` / counter: `baseline/de` 3 hits, `baseline/fr` 0 hits (E), `baseline/it` 3 hits, `counter/de` 3 hits, `counter/fr` 3 hits, `counter/it` 1 hits

## Language reach (REPORTED-ONLY; never gated)

- `rent-default`: executed ['baseline/fr']; not executed ['baseline/de', 'baseline/it', 'counter/de', 'counter/fr', 'counter/it']
- `corporate-criminal-liability`: executed ['baseline/fr']; not executed ['baseline/de', 'baseline/it', 'counter/de', 'counter/fr', 'counter/it']
- `business-judgment-rule`: executed ['baseline/fr']; not executed ['baseline/de', 'baseline/it', 'counter/de', 'counter/fr', 'counter/it']
- `petty-theft-dismissal`: executed ['baseline/fr']; not executed ['baseline/de', 'baseline/it', 'counter/de', 'counter/fr', 'counter/it']

## Comparator-only id attribution (why the coverage deficit is not a same-text regression)

- comparator-only ids (union comparator, not reached by the product): **18**
- of those, ids that ONLY texts the product never executed produced: **18**
- ids that an executed text produced but the product still missed: **0**
- therefore all comparator-only ids come exclusively from texts the product never executed: **True**
- frozen texts executed by the product cache: **4 of 24**

## V1 preservation (nothing weakened)

- run 39628161040 (`results/evaluation/product_cache_parity/39628161040.json` sha256 `c38d6c9dc600...`): 8 V1 falsifier gates -> V2 coverage gates, measurements identical: **True**
- run 39619144928 (`results/evaluation/product_cache_parity/39619144928.json` sha256 `9ba862fc39ef...`): 8 V1 falsifier gates -> V2 coverage gates, measurements identical: **True**

## Gated gates that failed

- `coverage::union_frozen_texts_counter_not_below_baseline::rent-default` — product 0 < union-of-all-frozen-texts plain comparator 3 of 9 frozen counter ids: the product's cached retrieval executed only 1 of 6 frozen texts (['baseline/fr']; not executed ['baseline/de', 'baseline/it', 'counter/de', 'counter/fr', 'counter/it']), so the measured deficit is a multilingual/counter-channel QUERY-COVERAGE deficit, NOT a same-text retrieval-quality regression
- `coverage::union_frozen_texts_authority_not_below_baseline::corporate-criminal-liability` — product 1 < union-of-all-frozen-texts plain comparator 2 of 2 frozen authority ids: the product's cached retrieval executed only 1 of 6 frozen texts (['baseline/fr']; not executed ['baseline/de', 'baseline/it', 'counter/de', 'counter/fr', 'counter/it']), so the measured deficit is a multilingual/counter-channel QUERY-COVERAGE deficit, NOT a same-text retrieval-quality regression
- `coverage::union_frozen_texts_counter_not_below_baseline::corporate-criminal-liability` — product 1 < union-of-all-frozen-texts plain comparator 4 of 6 frozen counter ids: the product's cached retrieval executed only 1 of 6 frozen texts (['baseline/fr']; not executed ['baseline/de', 'baseline/it', 'counter/de', 'counter/fr', 'counter/it']), so the measured deficit is a multilingual/counter-channel QUERY-COVERAGE deficit, NOT a same-text retrieval-quality regression
- `coverage::union_frozen_texts_authority_not_below_baseline::business-judgment-rule` — product 0 < union-of-all-frozen-texts plain comparator 3 of 5 frozen authority ids: the product's cached retrieval executed only 1 of 6 frozen texts (['baseline/fr']; not executed ['baseline/de', 'baseline/it', 'counter/de', 'counter/fr', 'counter/it']), so the measured deficit is a multilingual/counter-channel QUERY-COVERAGE deficit, NOT a same-text retrieval-quality regression
- `coverage::union_frozen_texts_counter_not_below_baseline::business-judgment-rule` — product 0 < union-of-all-frozen-texts plain comparator 1 of 4 frozen counter ids: the product's cached retrieval executed only 1 of 6 frozen texts (['baseline/fr']; not executed ['baseline/de', 'baseline/it', 'counter/de', 'counter/fr', 'counter/it']), so the measured deficit is a multilingual/counter-channel QUERY-COVERAGE deficit, NOT a same-text retrieval-quality regression
- `coverage::union_frozen_texts_authority_not_below_baseline::petty-theft-dismissal` — product 0 < union-of-all-frozen-texts plain comparator 1 of 2 frozen authority ids: the product's cached retrieval executed only 1 of 6 frozen texts (['baseline/fr']; not executed ['baseline/de', 'baseline/it', 'counter/de', 'counter/fr', 'counter/it']), so the measured deficit is a multilingual/counter-channel QUERY-COVERAGE deficit, NOT a same-text retrieval-quality regression
- `coverage::union_frozen_texts_counter_not_below_baseline::petty-theft-dismissal` — product 1 < union-of-all-frozen-texts plain comparator 7 of 9 frozen counter ids: the product's cached retrieval executed only 1 of 6 frozen texts (['baseline/fr']; not executed ['baseline/de', 'baseline/it', 'counter/de', 'counter/fr', 'counter/it']), so the measured deficit is a multilingual/counter-channel QUERY-COVERAGE deficit, NOT a same-text retrieval-quality regression

## Reason

the product's cached retrieval executed only 4 of 24 frozen query texts; on the text(s) it executed it reaches at least as many frozen controlling/counter ids as the plain OpenCaseLaw answer to that same text (same-text family PASS), but the plain client answered every frozen text and reaches more frozen ids on the union comparison (coverage family FAIL). The measured deficit is a multilingual/counter-channel QUERY-COVERAGE deficit, NOT a same-text retrieval-quality regression.

## Claim ceiling

This benchmark can establish TWO things and nothing more: (1) on the frozen query text(s) the product's own cached retrieval actually executed, how many of the frozen controlling-authority ids and frozen known counter-authority ids the PRODUCT's retrieval layer reaches compared with the plain OpenCaseLaw client's response to that same text; and (2) how much of what the plain OpenCaseLaw client reached when it answered ALL the frozen texts (baseline+counter channels x fr/de/it) the product's cached retrieval reaches at all, i.e. the multilingual/counter-channel QUERY-COVERAGE deficit. It does NOT claim that the product's retrieval quality is worse than plain OpenCaseLaw on the text it ran (that is the separately gated same-text family, reported beside the coverage family); it does NOT score any served bundle or packet (it therefore touches no packet-of-record byte and lifts no order); it does NOT re-classify any decision as supporting/contrary/limiting; it does NOT re-score, meet or move the frozen absolute LABEL_SOUND / GEOMETRY_SOUND bars (they stay REPORTED-ONLY); it does NOT lift the accepted DO-NOT-SERVE order on packet 38839347028 nor DO-NOT-SERVE-UNCHANGED on rebuilt-39027045675; it does NOT certify admission of any packet; it does NOT claim the map helps a jurist; it does NOT re-issue the retracted 39111232991 parity claim; it does NOT rebuild or re-dispatch any Frontier component (counter-anchor classifier accept d236f599, relevance_ordered geometry accept be5eba7f/dc3ffc6c and counter-label-emission accept 44d4904b stay closed). human_gate_ready, machine_gate_ready, packet_admitted and ready_for_owner_session all stay false; owner_decision_required stays false. NOT_MEASURED / NOT_APPLICABLE is never a pass.

Machine record: `results/evaluation/product_cache_parity/39631600439.json`
