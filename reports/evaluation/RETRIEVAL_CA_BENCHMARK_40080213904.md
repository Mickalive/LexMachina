# Minimal D2 Letterhead Zone Falsification Benchmark — run 40080213904

- Schema: `lex-evaluation-minimal-d2-letterhead-benchmark/1`
- Direction: v67 (factory direction v67, derived from state/evaluation.json at run time)
- Engine: `python -m evaluation.mapping_free_recall_falsifier` invoked as the accepted entry point (full provenance layer restored, audit F5)
- Packet: 39319405429 (V3 packet-of-record exact bytes: 39319405429)
- Combined verdict: **PRODUCT_FALSIFIED** (exit 1)
- Falsification proven: **True**
- Input drift: none (run_valid=True)
- Product mount head: N/A
- Questions measured: 3
- Gates: 18 total, 11 passed, 4 failed, 3 reported
- Failed gates: mf::concept_coverage::39319405429::de-kapitalverletzung, mf::counter_authority_surface::39319405429::de-kapitalverletzung, mf::counter_authority_surface::39319405429::fr-bail-entretien, mf::counter_authority_surface::39319405429::it-responsabilita-medica

## D2 Letterhead Zone

- Expected D2 defects (from H2 probe): 10
- D2 defects detected by gates: False
- D2 failed gate details: none

## Claim ceiling

This instrument establishes exactly one thing: on the exact accepted packet bytes, whether the served bundles satisfy the frozen mapping-free gates. It does NOT meet, move or re-derive the frozen absolute LABEL_SOUND or GEOMETRY_SOUND bars, which stay REPORTED-ONLY. It does NOT lift the accepted DO-NOT-SERVE order on packet 38839347028 nor DO-NOT-SERVE-UNCHANGED on rebuilt-39027045675. It does NOT certify admission of any packet; admission stays fail-closed. It does NOT claim the map helps a jurist; that remains the human product gate's question. It does NOT re-issue the retracted 39111232991 parity claim. It builds and re-scores no candidate for Frontier team frontier-query-concept-recall. human_gate_ready stays false. It runs no obsolete universal-174k geometry benchmark.

## Provenance (restored layer)
- Frozen hypothesis SHA256: d1135f9f919140a30dd31250cdb2e782fc3b32a74e39472a24d31560d7de009d
- Freeze record SHA256: 431aa87b8abeaec3b849d66bce7c0d6b1bcb1ea0fdd5f31bef4b3da122d229f5
- Engine record: `results/evaluation/minimal_d2_letterhead_benchmark/40080213904_engine_mapping_free_recall_falsifier.json`
- Re-hash before execution: 10 repo / 14 mount inputs
- Re-hash after execution: drift=none
- Numeric environment disclosed: yes (factory requirement 30)
- Analyst mapping not consumed: True

Machine record: `40080213904.json`
Report: `RETRIEVAL_CA_BENCHMARK_40080213904.md`
