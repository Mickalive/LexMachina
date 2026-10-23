# FAST-MVP Acceptance Battery - run 39884405570

- Schema: `lex-evaluation-fast-mvp-acceptance/1`
- Direction: v63 (cycle field; wrapper instrument field direction_version=61 is the accepted wrapper's own frozen value)
- Battery verdict: **BATTERY_EXECUTED_PINS_HELD** (exit 0)
- Generated: 2026-10-23T02:40:42Z

## Benchmark step (accepted instrument, invoked unchanged)

- Verdict: **PRODUCT_FALSIFIED** (exit 1), run_valid=True, input_drift=[]
- Gates: 11/18 passed, 4 failed, 3 reported
- Failed gates: ['mf::concept_coverage::39319405429::de-kapitalverletzung', 'mf::counter_authority_surface::39319405429::de-kapitalverletzung', 'mf::counter_authority_surface::39319405429::fr-bail-entretien', 'mf::counter_authority_surface::39319405429::it-responsabilita-medica']
- falsification_reproduced=True | failed_gate_set_matches_accepted=True | non_vacuity_all_hold=True
- Product mount head measured: 7a70953e6efff535464fcdedc820dea02b4deb8d

## Battery step (7 suites under the disclosed no-pytest shim)

- Verdict: **SHIM_PASS** - passed=77 failed=0 skipped=0 unsupported(NOT-RUN, never passed)=6 absent=0 across 7 files
- Record: `results/evaluation/orchestration/39884405570_fast_mvp_battery_pytest_shim.json`
- NOT pytest: a SHIM_PASS does not withdraw the standing disclosure that pytest is absent from the producer image.

### Per-file

- `tests/evaluation/test_minimal_retrieval_ca_benchmark.py`: status=PASS passed=21 failed=0 skipped=0 unsupported=0
- `tests/evaluation/test_mapping_free_recall_falsifier.py`: status=PASS passed=22 failed=0 skipped=0 unsupported=2
- `tests/evaluation/test_stand_ready_multilingual_probe.py`: status=PASS passed=16 failed=0 skipped=0 unsupported=0
- `tests/evaluation/test_mount_provenance_gate.py`: status=PASS passed=9 failed=0 skipped=0 unsupported=4
- `tests/evaluation/test_disclosure_provenance_crosscheck.py`: status=PASS passed=0 failed=0 skipped=0 unsupported=0
- `tests/evaluation/test_boilerplate_resistance_real.py`: status=PASS passed=1 failed=0 skipped=0 unsupported=0
- `tests/evaluation/test_offline_emission_path_benchmark.py`: status=PASS passed=8 failed=0 skipped=0 unsupported=0

## Pin discipline (re-hashed before and after; identity only)

- Drift: NONE (all pins identical before/after and matching expected)

## Ordered-item adjudication (v63)

- **(1)_remedy_a_re_freeze**: NOT_TRIGGERED - condition: mount planner sha256 != the pin already re-frozen by accepted run 39813664201 (SHIPPED_PLANNER_MATCHES_VERIFIED_REMEDY)
- **(2)_cross_check_next_product_measurement**: TRIGGERED - condition: mount HEAD != accepted product anchor fe219a19 (no newer accepted product cycle)
- **(3)_frozen_bars_standing**: STANDING_OK - condition: RULES_LABEL/RULES_GEOMETRY/VERDICT_CONTRACT/frozen retrieval benchmark re-hash match (identity re-hash only, never re-derived)
- **(4)_p1_fr_counter_stage_divergence**: STANDING_OK - condition: carry-forward reference to the accepted P1 FR divergence record in state/evaluation.json; NOT re-derived, NOT re-measured by this run
- **(5)_falsify_new_served_packet**: NOT_TRIGGERED - condition: any accepted serve_recommendation in mount frontier_verdicts or the vendored serve verdict that does not carry a DO-NOT-SERVE marker (markers frozen in the hypothesis: do-not-serve, do_not_serve, do not serve, bounded-negative, withheld_pending_serve, built_not_served)

## Latency (REPORTED-ONLY, no threshold)

- benchmark: 0.286s | battery: 1.945s | pin re-hash total: 0.008s

## Prior-session disclosure

- A prior session of this same GitHub run executed the benchmark at 2026-10-23T01:34:55Z under id local_eval_1792719295 (artifacts results/evaluation/minimal_retrieval_ca_benchmark/local_eval_1792719295*.json and reports/evaluation/RETRIEVAL_CA_BENCHMARK_local_eval_1792719295.md, uncommitted at freeze time); those bytes are preserved verbatim and are NOT this run's claim-bearing record - this record and results/evaluation/minimal_retrieval_ca_benchmark/39884405570.json are.

## Claim ceiling

- This battery establishes exactly three things: (a) the accepted smallest executable retrieval/counter-authority falsification benchmark still runs end-to-end under this run's environment on the unchanged accepted pins and, per its own embedded verdict, whether the accepted falsification of the packet-of-record v3 bytes reproduced; (b) the lane's multilingual/provenance/benchmark test battery is executable and green (or honestly not-green) under the disclosed no-pytest shim, whose UNSUPPORTED constructs are NOT-RUN never passed; (c) the standing frozen pins and the ordered-item trigger conditions hold as machine-checked. It does NOT meet, move or re-derive the frozen absolute LABEL_SOUND or GEOMETRY_SOUND bars; it does NOT lift either DO-NOT-SERVE order; it does NOT certify packet admission; it does NOT claim the map helps a jurist; it does NOT make the comparative map-versus-ranked-list question non-vacuous; it adds NO threshold, gate, rubric or verdict contract; it runs NO obsolete universal-174k benchmark; human_gate_ready stays false.

## Provenance

- Hypothesis: `evaluation/FAST_MVP_ACCEPTANCE_HYPOTHESIS_V1.json` sha256 afda10794943fa701af07daeadf8eac4dae3244ef9a3f6a235c995b932f51a46
- Freeze record: `evaluation/FAST_MVP_ACCEPTANCE_FREEZE_RECORD_V1.json` sha256 813ade2fb9ff7a496a9b4299a07ae145da6ce3458693504b81d8d645e3b3cc0f
- Machine record: `results/evaluation/fast_mvp_acceptance/39884405570.json`
