# Retrieval / Counter-authority Falsification Benchmark — run 39909449668

- Wrapper schema: `lex-evaluation-counter-authority-surface-falsifier/1`
- Direction: v63 (factory direction v63)
- Engine: `python -m evaluation.counter_authority_surface_falsifier` invoked as the accepted entry point (full provenance layer restored, audit F5)
- Packet: 39319405429 (V3 packet-of-record exact bytes)
- Combined verdict: **PRODUCT_FALSIFIED** (exit 1)
- Falsification proven: **True**
- Input drift: none (run_valid=True)
- Product mount head: 7a70953e6efff535464fcdedc820dea02b4deb8d
- Questions measured: 3
- Gates: 18 total, 11 passed, 4 failed, 3 reported

## Failed gates

- **mf::concept_coverage::39319405429::de-kapitalverletzung**: 2/8 core concepts of the served question retrieve ZERO served rows
- **mf::counter_authority_surface::39319405429::de-kapitalverletzung**: 0 counter-authority row(s) issued, 0 with empty evidence
- **mf::counter_authority_surface::39319405429::fr-bail-entretien**: 0 counter-authority row(s) issued, 0 with empty evidence
- **mf::counter_authority_surface::39319405429::it-responsabilita-medica**: 0 counter-authority row(s) issued, 0 with empty evidence

## Non-vacuity battery

- all_hold: True (all four controls passed: blanked pool fails, oracle pool passes, subject-swapped predicate rejects, blanked row fails source validity)

## Claim ceiling

This instrument establishes exactly one thing: on the packet-of-record V3's (39319405429) exact bytes, whether the served bundles satisfy the frozen mapping-free gates. It does NOT meet, move or re-derive the frozen absolute LABEL_SOUND or GEOMETRY_SOUND bars, which stay REPORTED-ONLY. It does NOT lift the accepted DO-NOT-SERVE order on packet 38839347028 nor DO-NOT-SERVE-UNCHANGED on rebuilt-39027045675, and it does NOT certify admission of any packet; admission stays fail-closed. It does NOT claim the map helps a jurist; that remains the human product gate's question. It does NOT build, tune, score or re-score any candidate for any Frontier team; where its numbers touch the accepted frontier-counter-label-emission numbers they are published BESIDE them with any divergence named as the headline. It runs no obsolete universal-174k benchmark. human_gate_ready stays false.

## Provenance (restored layer)

- Frozen hypothesis: evaluation/MAPPING_FREE_RECALL_FALSIFIER_HYPOTHESIS_V1.json
- Freeze record: evaluation/MAPPING_FREE_RECALL_FALSIFIER_FREEZE_RECORD.json
- Engine record: results/evaluation/counter_authority_surface_falsifier/39909449668.json
- Frozen spec: evaluation/retrieval_gate/frozen_retrieval_benchmark.json
- Frozen label rubric: evaluation/frozen_bars/RULES_LABEL.json

## Failed gate details

- mf::concept_coverage::39319405429::de-kapitalverletzung: 2/8 core concepts of the served question retrieve ZERO served rows
- mf::counter_authority_surface::39319405429::de-kapitalverletzung: 0 counter-authority row(s) issued, 0 with empty evidence
- mf::counter_authority_surface::39319405429::fr-bail-entretien: 0 counter-authority row(s) issued, 0 with empty evidence
- mf::counter_authority_surface::39319405429::it-responsabilita-medica: 0 counter-authority row(s) issued, 0 with empty evidence

## Summary

- The product's mapping-free retrieval and counter-authority surface discovery is INSUFFICIENT for the visual UX test on the V3 packet-of-record bytes (39319405429)
- All three language bundles (de/fr/it) emit ZERO counter-authority rows under the frozen rubric
- The German bundle has 2/8 core concepts with zero retrieval (kapitalverletzung, uberwachungspflicht)
- Four non-vacuity controls all hold, confirming the gate is not vacuous
- This confirms the product defect belongs to the product lane (adversarial_retrieval.py, query/adversarial_retrieval.py)
- The fix belongs to the product lane; evaluation confirms the falsification

Machine record: `results/evaluation/counter_authority_surface_falsifier/39909449668.json`
Report: `reports/evaluation/RETRIEVAL_CA_BENCHMARK_39909449668.md`