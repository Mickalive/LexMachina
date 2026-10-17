# Retrieval / counter-authority falsification benchmark — run 39027041693

- Schema: `lex-evaluation-retrieval-ca-benchmark/1`
- Direction: v52 (derived from state/evaluation.json at run time; operational resume lineage of run 38986445355)
- Engine: `python -m evaluation.frozen_bars.run_bar_gates` (accepted entry point, reused as subprocess)
- Combined verdict: **BENCHMARK_VALID_NO_FALSIFICATION** (exit 0)
- Falsification proven: **True**
- Elapsed: 28.246 s

## Legs

### served_baseline — OK

- exit 0 (expected 0)
- verdict: `PASS_NO_REGRESSION`
- label: {'n_scored': 65, 'n_supported': 5, 'support_rate': 0.07692307692307693, 'classes': {'OFF-DOMAIN': 38, 'UNBACKED': 22, 'SUPPORTED': 5}, 'regression_verdict': 'PASS_NO_REGRESSION', 'gate_blocks_build': False, 'absolute_status': 'LABEL_UNSOUND'}
- geometry: {'per_bundle_counts': {'de-kapitalverletzung': 6, 'fr-bail-entretien': 5, 'it-responsabilita-medica': 5}, 'regression_verdict': 'PASS_NO_REGRESSION', 'regressed_qids': [], 'gate_blocks_build': False, 'absolute_status': 'GEOMETRY_UNSOUND', 'n_bundles_pass_all_11': 0}
- negative_controls_all_proven: True

### geometry_falsification_hostile — OK

- exit 1 (expected 1)
- verdict: `FAIL_REGRESSION`
- label: {'n_scored': 65, 'n_supported': 5, 'support_rate': 0.07692307692307693, 'classes': {'OFF-DOMAIN': 38, 'UNBACKED': 22, 'SUPPORTED': 5}, 'regression_verdict': 'PASS_NO_REGRESSION', 'gate_blocks_build': False, 'absolute_status': 'LABEL_UNSOUND'}
- geometry: {'per_bundle_counts': {'de-kapitalverletzung': 4, 'fr-bail-entretien': 4, 'it-responsabilita-medica': 5}, 'regression_verdict': 'FAIL_REGRESSION', 'regressed_qids': ['de-kapitalverletzung', 'fr-bail-entretien'], 'gate_blocks_build': True, 'absolute_status': 'GEOMETRY_UNSOUND', 'n_bundles_pass_all_11': 0}
- negative_controls_all_proven: True

### label_falsification_blanked_evidence — OK

- exit 1 (expected 1)
- verdict: `FAIL_REGRESSION`
- label: {'n_scored': 65, 'n_supported': 0, 'support_rate': 0.0, 'classes': {'UNBACKED': 65}, 'regression_verdict': 'FAIL_REGRESSION', 'gate_blocks_build': True, 'absolute_status': 'LABEL_UNSOUND'}
- geometry: {'per_bundle_counts': {'de-kapitalverletzung': 6, 'fr-bail-entretien': 5, 'it-responsabilita-medica': 5}, 'regression_verdict': 'PASS_NO_REGRESSION', 'regressed_qids': [], 'gate_blocks_build': False, 'absolute_status': 'GEOMETRY_UNSOUND', 'n_bundles_pass_all_11': 0}
- negative_controls_all_proven: True

## Reason

served packet passes regression and both deliberately regressed inputs make the gates fail — the benchmark can falsify

## Claim ceiling

This benchmark proves only that (a) the served packet currently does not regress below the recomputed incumbents and (b) both frozen gates can fail a deliberately regressed input. It does NOT prove jurist usefulness, does NOT meet the absolute LABEL_SOUND / GEOMETRY_SOUND bars, and does NOT unblock the human gate (standing accepted DO-NOT-SERVE order).

Machine record: `results/evaluation/retrieval_counter_authority_benchmark/39027041693.json`
