# Product-advance cross-check — run 39916358347

- Combined verdict: **PRODUCT_STILL_FALSIFIED_WITH_DELIVERABLE_DRIFT** (exit 1)
- Accepted product head expected: `ae854b6a9ff4df4429d36725e364e721cb73096b`
- Product mount head: `ae854b6a9ff4df4429d36725e364e721cb73096b` (matches expected=True)
- Direction: v63
- Machine record: `results/evaluation/product_advance_crosscheck/39916358347.json`

## Headline

- A_mapping_free_falsification: PRODUCT_FALSIFIED
- E_answer_reliability_currency: RELIABILITY_MEASUREMENT_STALE_ON_PRODUCT_ADVANCE

## Legs

| leg | exit | verdict | record |
|---|---|---|---|
| A_mapping_free_falsification | 1 | PRODUCT_FALSIFIED | `results/evaluation/mapping_free_recall_falsifier/39916358347_engine_mapping_free_recall_falsifier.json` |
| B_shipped_planner_remedy | 0 | SHIPPED_PLANNER_MATCHES_VERIFIED_REMEDY | `results/evaluation/shipped_planner_remedy_verification/39916358347.json` |
| C_degradation_disclosure | 0 | DEGRADATION_DISCLOSURE_VISIBLE_AT_COMPLETE_BUNDLE_STAGE | `results/evaluation/degradation_disclosure_crosscheck/39916358347.json` |
| D_coverage_remediation_pins | 0 | COVERAGE_PINS_STILL_HOLD | `evaluation/COVERAGE_REMEDIATION_CROSSCHECK_FREEZE_RECORD_V1.json` |
| E_answer_reliability_currency | 1 | RELIABILITY_MEASUREMENT_STALE_ON_PRODUCT_ADVANCE | `evaluation/ANSWER_RELIABILITY_CROSSCHECK_FREEZE_RECORD_V1.json` |

## Leg A — mapping-free retrieval / counter-authority

- Failed gates: mf::concept_coverage::39319405429::de-kapitalverletzung, mf::counter_authority_surface::39319405429::de-kapitalverletzung, mf::counter_authority_surface::39319405429::fr-bail-entretien, mf::counter_authority_surface::39319405429::it-responsabilita-medica
- Failed set equals the accepted set: True
- Non-vacuity all hold: True
- Input drift: none
- V3 bundle bytes identical to accepted 39909449668: True
  - de-kapitalverletzung: identical=True sha256=9b856e2b1b3e4675f8d4d135cd5d1ad23f0baa63fcb2e4cc7bc45182c012881b
  - fr-bail-entretien: identical=True sha256=054bec47ae8e5a0f98593902c2c7bd09f7f52761be1c85225328853f34d3213b
  - it-responsabilita-medica: identical=True sha256=345e20d1f352fd4e907cac144c8dbbae296f3a9132605d4354f12e7a783e6e3b

## Leg B — shipped planner remedy (a)

- Verdict: SHIPPED_PLANNER_MATCHES_VERIFIED_REMEDY (exit 0)
- Gate failures: []
- Control failures: []
- Pins before/after all ok: True / True

## Leg C — writer-abort degradation disclosure

- Verdict: DEGRADATION_DISCLOSURE_VISIBLE_AT_COMPLETE_BUNDLE_STAGE (exit 0)
- Gate failures: []
- Control failures: []
- Product pins before/after all hold: True / True

## Leg D — query-coverage remediation pins

- Verdict: COVERAGE_PINS_STILL_HOLD (exit 0)
- the pinned product code and evidence files are byte-identical, so the accepted offline replay is not re-executed and no new reach claim is issued

## Leg E — live-answer reliability currency

- Verdict: RELIABILITY_MEASUREMENT_STALE_ON_PRODUCT_ADVANCE (exit 1)
- Measurement artifact pins ok: True
- Drifting product sources: ['product/query/answer.py', 'product/query/pipeline.py']
- Product state disclaims re-measurement: True
- the accepted 0.857 figure is not restated as current for head ae854b6a

## Controls

- C1_planted_product_pin_drift_is_detected: holds=True
- C2_planted_bundle_hash_mismatch_is_detected: holds=True
- C3_frozen_leg_inputs_exist_and_rehash: holds=True

## Orchestration diagnosis (run 39915124469)

- Conclusion: **ZERO_DELTA_ORCHESTRATION_FAILURE**
- Run 39915124469 produced no producer commit: its team branch is byte-identical to the team snapshot of run 39910387854 (81b4f131), no audit branch exists, and the accepted lab/evaluation tip is 95675eda. The workflow's validation/write-scope steps never ran because the team step did not complete successfully; this is an orchestration/zero-delta failure, NOT a validation verdict and NOT a product or evidence defect. The valid completed producer work already on the snapshot (39909449668 falsification re-confirmation + 39910387854 audit-log recovery) is preserved and re-verified below, not overwritten.

## Claim ceiling

This instrument establishes only whether the accepted evaluation findings still hold on the new accepted product head ae854b6a and whether the product's four ordered deliverable claims remain current. It is NOT a new counter-authority recall measurement (no probe is executed against OpenCaseLaw), NOT a serve recommendation, NOT a re-score of any frozen absolute bar (LABEL_SOUND and GEOMETRY_SOUND stay REPORTED-ONLY and unmet), NOT a jurist-usefulness claim and NOT a human-gate readiness claim. Both DO-NOT-SERVE orders stand; admission stays fail-closed; human_gate_ready, machine_gate_ready, packet_admitted and ready_for_owner_session stay false. It re-derives no threshold, bar, rubric or verdict contract, builds or re-scores no Frontier candidate, and runs no obsolete universal-174k benchmark.
