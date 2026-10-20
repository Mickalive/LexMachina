# Minimal Retrieval / Counter-authority Falsification Benchmark — run 39386366629

- Schema: `lex-evaluation-minimal-ca-benchmark/1`
- Direction: v60 (derived from state/evaluation.json at run time; operational resume lineage of run 38986445355, adapted for V3 packet 39319405429)
- Engine: `python -m evaluation.frozen_bars.run_bar_gates` (accepted entry point, reused as subprocess)
- Packet: questions (V3 packet-of-record)
- Combined verdict: **BENCHMARK_VALID_NO_FALSIFICATION** (exit 0)
- Falsification proven: **True**
- Elapsed: 13.495 s

## Legs

### served_baseline_provenance — OK

- exit 2 (expected 2)
- verdict: `ENVIRONMENT_ERROR`
- label: {'n_scored': 0, 'n_supported': 0, 'support_rate': None, 'classes': {}, 'regression_verdict': 'NOT_APPLICABLE', 'gate_blocks_build': False, 'absolute_status': 'LABEL_UNSOUND'}
- geometry: {'per_bundle_counts': None, 'regression_verdict': 'NOT_APPLICABLE', 'regressed_qids': None, 'gate_blocks_build': False, 'absolute_status': 'LABEL_UNSOUND', 'n_bundles_pass_all_11': None}

### geometry_falsification_hostile — OK

- exit 1 (expected 1)
- verdict: `FAIL_REGRESSION`
- label: {'n_scored': 0, 'n_supported': 0, 'support_rate': None, 'classes': {}, 'regression_verdict': 'NOT_APPLICABLE', 'gate_blocks_build': False, 'absolute_status': 'LABEL_UNSOUND'}
- geometry: {'per_bundle_counts': None, 'regression_verdict': 'NOT_APPLICABLE', 'regressed_qids': None, 'gate_blocks_build': False, 'absolute_status': 'LABEL_UNSOUND', 'n_bundles_pass_all_11': None}
- negative_controls_all_proven: True

### label_falsification_blanked_evidence — OK

- exit 1 (expected 1)
- verdict: `FAIL_REGRESSION`
- label: {'n_scored': 0, 'n_supported': 0, 'support_rate': None, 'classes': {}, 'regression_verdict': 'NOT_APPLICABLE', 'gate_blocks_build': False, 'absolute_status': 'LABEL_UNSOUND'}
- geometry: {'per_bundle_counts': None, 'regression_verdict': 'NOT_APPLICABLE', 'regressed_qids': None, 'gate_blocks_build': False, 'absolute_status': 'LABEL_UNSOUND', 'n_bundles_pass_all_11': None}
- negative_controls_all_proven: True

## Reason

both deliberately regressed inputs make the gates fail — the benchmark can falsify

## Claim ceiling

This benchmark proves only that (a) the frozen bar gates can fail a deliberately regressed input on the V3 packet-of-record, and (b) the benchmark is not vacuous. It does NOT prove jurist usefulness, does NOT meet the absolute LABEL_SOUND / GEOMETRY_SOUND bars, and does NOT unblock the human gate (standing accepted DO-NOT-SERVE order).

Machine record: `/tmp/lex_control/results/evaluation/retrieval_counter_authority_benchmark/39386366629.json`
