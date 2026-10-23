# Retrieval / counter-authority falsification benchmark — run v65_eval_40017649220

- Schema: `lex-evaluation-minimal-ret-ca-benchmark/1`
- Direction: v65 (derived from state/evaluation.json at run time; operational resume lineage, adapted for 2-leg minimal CA)
- Engine: `python -m evaluation.frozen_bars.run_bar_gates` (accepted entry point, reused as subprocess)
- Combined verdict: **BENCHMARK_VALID_NO_FALSIFICATION** (exit 0)
- Falsification proven: **True**
- Elapsed: 11.931 s

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

## Reason

served packet passes regression and the regressed input makes the gate fail — the benchmark can falsify

## Claim ceiling

This benchmark proves only that (a) the served packet currently does not regress below the recomputed incumbents and (b) both frozen gates can fail a deliberately regressed input. It does NOT prove jurist usefulness, does NOT meet the absolute LABEL_SOUND / GEOMETRY_SOUND bars, and does NOT unblock the human gate (standing accepted DO-NOT-SERVE order).

Machine record: `results/evaluation/minimal_ret_ca_benchmark/v65_eval_40017649220.json`

## Ordering / Provenance Disclosure (repair round 1 — F3)

Run 40017649220 is **NOT a freeze-first cycle** and must not be cited or
promoted as one: the claim-bearing execution ran at `2026-10-23T20:16:19Z` and
the cycle's only commit landed at `2026-10-23T20:37:19Z`. The hypothesis /
provenance record `evaluation/MINIMAL_RET_CA_40017649220_CYCLE_HYPOTHESIS_V1.json`
discloses the true ordering and was written in repair round 1; it does not
retroactively freeze anything. It also records the **inherited frozen spec**
(instrument commit `2e7d4fe566bf2ae7e80f0cfede09d0f0cb22cc83`, the frozen QIDs,
the frozen label and geometry incumbents, the combined-verdict rule and the
state claim ceiling) and the **no-post-hoc-tuning proofs**: instrument and test
byte-identical to accepted base `b8265afb`, output quantity-for-quantity
identical to the base-committed `test_run_1`/`final_check`, and no frozen file
edited by the cycle.
