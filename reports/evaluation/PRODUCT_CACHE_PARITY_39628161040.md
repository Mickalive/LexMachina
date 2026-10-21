# Product-cache retrieval/counter-authority parity — run 39628161040

> **Amended (repair round 1, run 39631600439):** the finding of this run is **restated** below — the verdict stands, its attribution does not. The original text of this report is preserved verbatim; see [Finding restatement](#finding-restatement-repair-round-1-run-39631600439).


- Schema: `lex-evaluation-product-cache-parity/1`
- Direction: v61 (derived from state/evaluation.json)
- Hypothesis: `evaluation/PRODUCT_CACHE_PARITY_HYPOTHESIS_V1.json` sha256 `0e80f0de66fd...` (frozen BEFORE execution; pre-freeze reconnaissance disclosed in-file)
- Product pool: `/tmp/lex_accepted/product/results/product/query_cache` identity-matched envelopes (33 of 465 cache files)
- Primary comparator: same-query plain OpenCaseLaw rows (named per D2 correction)
- Verdict: **FAIL_PRODUCT_CACHE_PARITY** (exit 1)
- Falsifier gates failed: **7**
- Non-vacuity: **True**
- Multilingual/provenance reuse leg (V3): **PARTIAL_MISS** (0/3 qids row_ok)
- Elapsed: 1.225 s

## Cells (identity mapping; hits of frozen id sets)

| slug | product pool rows | comparator rows | authority hits (prod/base) | counter hits (prod/base) | parity authority | parity counter |
|---|---|---|---|---|---|---|
| rent-default | 264 | 240 | n/a | 0/9 | NOT_MEASURED | FAIL (0 vs ['bge_BGE_117_II_415', 'gr_gerichte_PKG_2010_20', 'zh_mietgericht_MB170006-L']) |
| corporate-criminal-liability | 266 | 240 | 1/2 | 1/6 | FAIL (1 vs ['bge_BGE_142_IV_333', 'bger_6B_124_2016']) | FAIL (1 vs ['bge_BGE_146_IV_68', 'bger_6B_7_2014', 'so_gerichte_BKBES.2026.74', 'so_gerichte_STBER.2011.32']) |
| business-judgment-rule | 308 | 240 | 0/5 | 0/4 | FAIL (0 vs ['bger_4A_219_2015', 'bger_4A_259_2016', 'bger_4A_603_2014']) | FAIL (0 vs ['zh_handelsgericht_HG120149']) |
| petty-theft-dismissal | 95 | 240 | 0/2 | 1/9 | FAIL (0 vs ['bger_4A_177_2017']) | FAIL (1 vs ['ar_gerichte_KG_ARGVP_2005_3462', 'bge_BGE_121_III_467', 'bge_BGE_124_III_25', 'bge_BGE_130_III_28', 'bge_BGE_138_I_113', 'ge_gerichte_CAPH_107_2004', 'so_gerichte_ZZ.1990.7']) |

## Language reach (REPORTED-ONLY; never gated)

- `rent-default`: executed ['baseline/fr']; not executed ['baseline/de', 'baseline/it', 'counter/de', 'counter/fr', 'counter/it']
- `corporate-criminal-liability`: executed ['baseline/fr']; not executed ['baseline/de', 'baseline/it', 'counter/de', 'counter/fr', 'counter/it']
- `business-judgment-rule`: executed ['baseline/fr']; not executed ['baseline/de', 'baseline/it', 'counter/de', 'counter/fr', 'counter/it']
- `petty-theft-dismissal`: executed ['baseline/fr']; not executed ['baseline/de', 'baseline/it', 'counter/de', 'counter/fr', 'counter/it']

## Falsifier gates that failed

- `parity::same_query_counter_not_below_baseline::rent-default` — product 0 < same-query plain comparator 3 of 9 frozen counter ids: the product retrieval layer returns strictly LESS of the frozen set than the plain OpenCaseLaw response to the identical query
- `parity::same_query_authority_not_below_baseline::corporate-criminal-liability` — product 1 < same-query plain comparator 2 of 2 frozen authority ids: the product retrieval layer returns strictly LESS of the frozen set than the plain OpenCaseLaw response to the identical query
- `parity::same_query_counter_not_below_baseline::corporate-criminal-liability` — product 1 < same-query plain comparator 4 of 6 frozen counter ids: the product retrieval layer returns strictly LESS of the frozen set than the plain OpenCaseLaw response to the identical query
- `parity::same_query_authority_not_below_baseline::business-judgment-rule` — product 0 < same-query plain comparator 3 of 5 frozen authority ids: the product retrieval layer returns strictly LESS of the frozen set than the plain OpenCaseLaw response to the identical query
- `parity::same_query_counter_not_below_baseline::business-judgment-rule` — product 0 < same-query plain comparator 1 of 4 frozen counter ids: the product retrieval layer returns strictly LESS of the frozen set than the plain OpenCaseLaw response to the identical query
- `parity::same_query_authority_not_below_baseline::petty-theft-dismissal` — product 0 < same-query plain comparator 1 of 2 frozen authority ids: the product retrieval layer returns strictly LESS of the frozen set than the plain OpenCaseLaw response to the identical query
- `parity::same_query_counter_not_below_baseline::petty-theft-dismissal` — product 1 < same-query plain comparator 7 of 9 frozen counter ids: the product retrieval layer returns strictly LESS of the frozen set than the plain OpenCaseLaw response to the identical query

## Reason

the product's own cached retrieval responses to the frozen queries recall strictly fewer frozen ids than the plain OpenCaseLaw response to the identical query text: retrieval-first parity is falsified on the named cells

## Claim ceiling

This benchmark can establish ONE thing and nothing more: on the product's own cached retrieval responses to the frozen questions' exact query texts, how many of the frozen controlling-authority ids and frozen known counter-authority ids the PRODUCT's retrieval layer reaches compared with the plain OpenCaseLaw client's responses to the identical texts. It does NOT score any served bundle or packet (it therefore touches no packet-of-record byte and lifts no order); it does NOT re-classify any decision as supporting/contrary/limiting; it does NOT re-score, meet or move the frozen absolute LABEL_SOUND / GEOMETRY_SOUND bars (they stay REPORTED-ONLY); it does NOT lift the accepted DO-NOT-SERVE order on packet 38839347028 nor DO-NOT-SERVE-UNCHANGED on rebuilt-39027045675; it does NOT certify admission of any packet; it does NOT claim the map helps a jurist; it does NOT re-issue the retracted 39111232991 parity claim; it does NOT rebuild or re-dispatch any Frontier component (counter-anchor classifier accept d236f599, relevance_ordered geometry accept be5eba7f/dc3ffc6c and counter-label-emission accept 44d4904b stay closed). human_gate_ready, machine_gate_ready, packet_admitted and ready_for_owner_session all stay false; owner_decision_required stays false. NOT_MEASURED / NOT_APPLICABLE is never a pass.

Machine record: `results/evaluation/product_cache_parity/39628161040.json`

## Finding restatement (repair round 1, run 39631600439)

The verdict `FAIL_PRODUCT_CACHE_PARITY` (exit 1) **stands as the verdict of the
frozen success rule**. What is restated here is its **attribution**, which the
independent audit of cycle 39628161040 (gate `REVISE`, required fix F1)
recomputed and found mis-stated in the section above.

**The comparator above is the union of six plain-OpenCaseLaw answers per
question, while the product's cache executed only `baseline/fr` (1 of the 6
frozen texts per question; 33 of 465 cache envelopes).** On the text the
product actually executed, the product's cached answer reaches **at least** the
plain-OpenCaseLaw answer in **all 7 parity cells** (product vs executed-text
comparator: `0/0, 1/0, 1/1, 0/0, 0/0, 0/0, 1/0`), and **all 18 comparator-only
ids come exclusively from texts the product never executed**.

**Honest characterization:** a **multilingual/counter-channel retrieval-COVERAGE
deficit** (1 of 6 frozen texts per question), **not** a same-query
retrieval-quality regression.

The per-(channel, language) comparator decomposition, the executed-text-only
comparison, the two gated families (`parity::same_query_*` PASS 7/7,
`coverage::union_frozen_texts_*` FAIL 7/7) and the 1:1 preservation proof of
every V1 falsifier measurement are published in the repair record
`results/evaluation/product_cache_parity/39631600439.json` (report
`reports/evaluation/PRODUCT_CACHE_PARITY_39631600439.md`, repair record
`results/evaluation/repair_39628161040/39631600439_parity_attribution_repair.json`).
The V1 hypothesis, V1 freeze record and both V1 measurement records are
byte-preserved (digests re-pinned in
`evaluation/PRODUCT_CACHE_PARITY_FREEZE_RECORD_V2.json`).

> **Superseded wording (preserved verbatim):** "the product's own cached
> retrieval responses to the frozen queries recall strictly fewer frozen ids
> than the plain OpenCaseLaw response to the identical query text:
> retrieval-first parity is falsified on the named cells" — superseded as a
> *characterization* by the restatement above; the original sentence is
> retained verbatim and is not deleted.
