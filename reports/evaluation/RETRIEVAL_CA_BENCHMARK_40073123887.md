# Minimal Retrieval / Counter-authority Falsification Benchmark — run 40073123887 (REPAIRED)

- Wrapper schema: `lex-evaluation-minimal-retrieval-ca-benchmark/1`
- Direction: v66 (factory direction v66; prior report erroneously stated v61)
- Engine: `evaluation.mapping_free_recall_falsifier.run()` invoked as the accepted entry point (full provenance layer restored)
- Packet: 39319405429 (V3 packet-of-record exact bytes)
- Combined verdict: **PRODUCT_FALSIFIED** (exit 1)
- Engine verdict before drift guard: **PRODUCT_FALSIFIED** (exit 1)
- Falsification proven: **True**
- Input drift: none (run_valid=True)
- Product mount head: 6b5827a10881d4b05a518b58551a090ee5884999 (mount currency; last re-measured head was 3495c1336)
- Questions measured: 3
- Gates: 18 total, 11 passed, 4 failed, 3 reported
- Failed gates: mf::concept_coverage::39319405429::de-kapitalverletzung, mf::counter_authority_surface::39319405429::de-kapitalverletzung, mf::counter_authority_surface::39319405429::fr-bail-entretien, mf::counter_authority_surface::39319405429::it-responsabilita-medica

## Non-vacuity battery

- **A_blanked_pool_must_fail_concept_coverage**: holds=True — a deliberately BLANKED pool leaves 8/8 core concepts of de-kapitalverletzung uncovered; a gate that passed it would be vacuous
- **A2_blanked_row_must_fail_source_validity**: holds=True — a served row with no decision_id and no canonical_url fails source validity
- **C_oracle_pool_must_pass_concept_coverage**: holds=True — an oracle pool built from the 8 core concepts of de-kapitalverletzung covers 8/8; the concept rule can go green, so a zero is a real signal and not an artefact of a broken rule
- **B_admissibility_predicate_must_reject_a_subject_swapped_pair**: holds=True — every ordered (frozen text, served question) swap across the served question set must be rejected by the predicate; if any swap is admitted the predicate is vacuous

## Claim ceiling

This instrument establishes exactly one thing: on the exact accepted packet bytes, whether the served bundles satisfy the frozen mapping-free gates. It does NOT meet, move or re-derive the frozen absolute LABEL_SOUND or GEOMETRY_SOUND bars, which stay REPORTED-ONLY (identity re-hash only). The frozen RULES_LABEL.json scored_statuses vocabulary IS consumed by the engine as the accepted scoring contract for the counter_authority_surface gate; the absolute bars are never used as thresholds. It does NOT lift the accepted DO-NOT-SERVE order on packet 38839347028 nor DO-NOT-SERVE-UNCHANGED on rebuilt-39027045675. It does NOT certify admission of any packet; admission stays fail-closed. It does NOT claim the map helps a jurist; that remains the human product gate's question. It does NOT re-issue the retracted 39111232991 parity claim. It builds and re-scores no candidate for Frontier team frontier-query-concept-recall. human_gate_ready stays false. It runs no obsolete universal-174k geometry benchmark.

## Provenance (restored layer)

- Frozen hypothesis SHA256: d1135f9f919140a30dd31250cdb2e782fc3b32a74e39472a24d31560d7de009d
- Freeze record SHA256: 431aa87b8abeaec3b849d66bce7c0d6b1bcb1ea0fdd5f31bef4b3da122d229f5
- Engine record: `results/evaluation/minimal_retrieval_ca_benchmark/40073123887_engine_mapping_free_recall_falsifier.json`
- Re-hash before execution: 10 repo / 14 mount inputs
- Re-hash after execution: drift=none
- Numeric environment disclosed: yes (factory requirement 30)
- Analyst mapping not consumed: True

Machine record: `40073123887.json`
Report: `RETRIEVAL_CA_BENCHMARK_40073123887.md`