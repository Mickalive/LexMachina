# Minimal Retrieval / Counter-authority Falsification Benchmark — run 39929883261

- Wrapper schema: `lex-evaluation-minimal-retrieval-ca-benchmark/1`
- Direction: v63 (control-plane factory direction v63; the wrapper's embedded `direction_version=61` and the engine's `57` are instrument-era constants — see the direction-version disclosure below)
- Engine: `evaluation.mapping_free_recall_falsifier.run()` invoked as the accepted entry point (full provenance layer restored, audit F5)
- Packet: 39319405429 (V3 packet-of-record exact bytes)
- Combined verdict: **PRODUCT_FALSIFIED** (exit 1)
- Engine verdict before drift guard: **PRODUCT_FALSIFIED** (exit 1)
- Falsification proven: **True**
- Input drift: none (run_valid=True)
- Product mount head: ae854b6a9ff4df4429d36725e364e721cb73096b
- Questions measured: 3
- Gates: 18 total, 11 passed, 4 failed, 3 reported
- Failed gates: mf::concept_coverage::39319405429::de-kapitalverletzung, mf::counter_authority_surface::39319405429::de-kapitalverletzung, mf::counter_authority_surface::39319405429::fr-bail-entretien, mf::counter_authority_surface::39319405429::it-responsabilita-medica

## Non-vacuity battery

- **A_blanked_pool_must_fail_concept_coverage**: holds=True — a deliberately BLANKED pool leaves 8/8 core concepts of de-kapitalverletzung uncovered; a gate that passed it would be vacuous
- **A2_blanked_row_must_fail_source_validity**: holds=True — a served row with no decision_id and no canonical_url fails source validity
- **C_oracle_pool_must_pass_concept_coverage**: holds=True — an oracle pool built from the 8 core concepts of de-kapitalverletzung covers 8/8; the concept rule can go green, so a zero is a real signal and not an artefact of a broken rule
- **B_admissibility_predicate_must_reject_a_subject_swapped_pair**: holds=True — every ordered (frozen text, served question) swap across the served question set must be rejected by the predicate; if any swap is admitted the predicate is vacuous

## Claim ceiling

This instrument establishes exactly one thing: on the exact accepted packet bytes, whether the served bundles satisfy the frozen mapping-free gates. It does NOT meet, move or re-derive the frozen absolute LABEL_SOUND or GEOMETRY_SOUND bars, which stay REPORTED-ONLY. It does NOT lift the accepted DO-NOT-SERVE order on packet 38839347028 nor DO-NOT-SERVE-UNCHANGED on rebuilt-39027045675. It does NOT certify admission of any packet; admission stays fail-closed. It does NOT claim the map helps a jurist; that remains the human product gate's question. It does NOT re-issue the retracted 39111232991 parity claim. It builds and re-scores no candidate for Frontier team frontier-query-concept-recall. human_gate_ready stays false. It runs no obsolete universal-174k geometry benchmark.

## Provenance (restored layer)
- Frozen hypothesis SHA256: d1135f9f919140a30dd31250cdb2e782fc3b32a74e39472a24d31560d7de009d
- Freeze record SHA256: 431aa87b8abeaec3b849d66bce7c0d6b1bcb1ea0fdd5f31bef4b3da122d229f5
- Engine record: `results/evaluation/minimal_retrieval_ca_benchmark/39929883261_engine_mapping_free_recall_falsifier.json`
- Re-hash before execution: 10 repo / 14 mount inputs
- Re-hash after execution: drift=none
- Numeric environment disclosed: yes (factory requirement 30)
- Analyst mapping not consumed: True

Machine record: `39929883261.json`
Report: `RETRIEVAL_CA_BENCHMARK_39929883261.md`

## Byte-duplicate lineage disclosure (this cycle's honest framing)

This run's wrapper record and engine record are **byte-level reproductions** of the
accepted run 39927760701 (accept commit `3eeced9a`, audit gate PASS /
safe_to_integrate=true): recursive leaf-level comparison finds **0 non-identity
diffs** across 583 wrapper leaves and 558 engine leaves (only `run_id`,
`generated_at_utc` and `engine_record_path` differ). The product head is unchanged
(`ae854b6a`, accept product cycle 39909013473), so no re-open trigger fired.

Therefore this cycle adds **no new measurement evidence** on the falsification
axis. What it does add: (a) a third independent reproducibility confirmation of
the accepted falsification (product-advance-crosscheck leg A at 39916358347 →
accepted 39927760701 → this run); (b) the test-suite shim execution below;
(c) the frozen-bar re-hash below; (d) state reconciliation advancing
`accepted_run_id` to 39927760701. Full machine disclosure:
`results/evaluation/minimal_retrieval_ca_benchmark/39929883261_LINEAGE_DISCLOSURE.json`.

## Test-suite shim execution (FAST-MVP reuse: multilingual + provenance + benchmark families)

Executed under this run id via `evaluation/no_pytest_runner.py` (pytest absent in
the producer image; UNSUPPORTED constructs counted as not-run, never as passed):

| Test file | Verdict | passed | failed | unsupported |
|---|---|---|---|---|
| `test_minimal_retrieval_ca_benchmark.py` | PASS | 21 | 0 | 0 |
| `test_mapping_free_recall_falsifier.py` | PASS | 22 | 0 | 2 |
| `test_stand_ready_multilingual_probe.py` | PASS | 16 | 0 | 0 |
| `test_mount_provenance_gate.py` | FAIL | 8 | 1 | 4 |
| `test_repair_39338699604_provenance.py` | FAIL | 21 | 7 | 0 |

Combined: 88 passed / 2 failed files (8 failed cases) / 6 unsupported.
Both failing files are **inherited historical-state-pin tests** that are red at
the accepted tip `3eeced9a` before any change of this run (verified on the clean
working tree): `test_mount_provenance_gate.py` asserts the run-39231573047
finding-of-record against the live mount (head has since advanced), and
`test_repair_39338699604_provenance.py` pins run-39338699604-era state values
(`accepted_run_id==39334865522`). Same inherited-red class as the re-homed
historical block in `test_minimal_retrieval_ca_benchmark.py` (run 39732040165
precedent). RECORDED, not repaired here — re-homing historical state pins is a
separate provenance-repair deliverable and is not required by the v63 question.
The multilingual probe suite (16/0) and the two benchmark suites (21/0, 22/0)
are green.

## Frozen-bar re-hash (standing duty, v63 ordered item 3)

| Artifact | Required SHA256 | Re-hashed | Status |
|---|---|---|---|
| `evaluation/frozen_bars/RULES_LABEL.json` | `4457e971df3dc5d1…` | same | OK |
| `evaluation/frozen_bars/RULES_GEOMETRY.json` | `a7452748d40c511a…` | same | OK |
| `evaluation/frozen_bars/VERDICT_CONTRACT.json` | `b9cdb89438a8d16e…` | same | OK |
| `evaluation/retrieval_gate/frozen_retrieval_benchmark.json` | `187b0e54b03b326c…` | same | OK |

Zero new thresholds; no rubric, bar or verdict contract edited.

## Direction-version disclosure (non-blocking, disclosed not repaired)

`evaluation/minimal_retrieval_ca_benchmark.py` hardcodes `direction_version=61`
in the wrapper record; the engine records `57` (its frozen-hypothesis era). The
control-plane direction is **v63**. The wrapper's digest `7631c1a3…` is pinned by
the accepted historical fixture `HISTORICAL_STATE_BLOCK_39491098975.json` and
asserted by `test_wrapper_instrument_pin_matches_state` (run 39732040165 repair),
so the wrapper file is NOT edited here. No gate, predicate, threshold or verdict
depends on this field. The authoritative direction version for this run is the
state block's `direction_version=63`. Mirrors audit CYCLE_39927760701's
minor-observation disposition.
