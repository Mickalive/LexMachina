# Minimal Retrieval / Counter-authority Falsification Benchmark — run 40171237606

- Schema: `lex-evaluation-minimal-ca-benchmark/1`
- Direction: v68 (derived from state/evaluation.json at run time; operational resume lineage of run 38986445355, adapted for V3 packet 39319405429)
- Engine: `python -m evaluation.frozen_bars.run_bar_gates` (accepted entry point, reused as subprocess)
- Packet: questions (V3 packet-of-record)
- Combined verdict: **BENCHMARK_VALID_NO_FALSIFICATION** (exit 0)
- Falsification proven: **True**
- Elapsed: 8.92 s

## Legs

### served_baseline_provenance — OK

- exit 2 (expected 2)
- verdict: `ENVIRONMENT_ERROR`
- label: {'n_scored': None, 'n_supported': None, 'support_rate': None, 'classes': None, 'regression_verdict': None, 'gate_blocks_build': None, 'absolute_status': None}
- geometry: {'per_bundle_counts': None, 'regression_verdict': None, 'regressed_qids': None, 'gate_blocks_build': None, 'absolute_status': None, 'n_bundles_pass_all_11': None}

### geometry_falsification_hostile — OK

- exit 1 (expected 1)
- verdict: `FAIL_REGRESSION`
- label: {'n_scored': 0, 'n_supported': 0, 'support_rate': None, 'classes': {}, 'regression_verdict': 'NOT_APPLICABLE', 'gate_blocks_build': False, 'absolute_status': 'LABEL_UNSOUND'}
- geometry: {'per_bundle_counts': {'de-kapitalverletzung': 4, 'fr-bail-entretien': 3, 'it-responsabilita-medica': 5}, 'regression_verdict': 'FAIL_REGRESSION', 'regressed_qids': ['de-kapitalverletzung', 'fr-bail-entretien'], 'gate_blocks_build': True, 'absolute_status': 'GEOMETRY_UNSOUND', 'n_bundles_pass_all_11': 0}
- negative_controls_all_proven: True

### label_falsification_blanked_evidence — OK

- exit 1 (expected 1)
- verdict: `FAIL_REGRESSION`
- label: {'n_scored': 0, 'n_supported': 0, 'support_rate': None, 'classes': {}, 'regression_verdict': 'NOT_APPLICABLE', 'gate_blocks_build': False, 'absolute_status': 'LABEL_UNSOUND'}
- geometry: {'per_bundle_counts': {'de-kapitalverletzung': 3, 'fr-bail-entretien': 4, 'it-responsabilita-medica': 4}, 'regression_verdict': 'FAIL_REGRESSION', 'regressed_qids': ['de-kapitalverletzung', 'fr-bail-entretien', 'it-responsabilita-medica'], 'gate_blocks_build': True, 'absolute_status': 'GEOMETRY_UNSOUND', 'n_bundles_pass_all_11': 0}
- negative_controls_all_proven: True

## Reason

both deliberately regressed inputs make the gates fail — the benchmark can falsify

## Claim ceiling

This benchmark proves only that (a) the frozen bar gates can fail a deliberately regressed input on the V3 packet-of-record, and (b) the benchmark is not vacuous. It does NOT prove jurist usefulness, does NOT meet the absolute LABEL_SOUND / GEOMETRY_SOUND bars, and does NOT unblock the human gate (standing accepted DO-NOT-SERVE order).

Machine record: `results/evaluation/minimal_retrieval_ca_benchmark/40171237606.json`
