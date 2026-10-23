# V65 Product-Advance Cross-Check — run 40012474431 (operational resume)

- Direction: v65
- Product mount head: `f9618377f67d8a79205fab86646d724f9739a339`
- Packet of record: 39319405429 (bytes unchanged, re-hashed)
- Frozen rules re-hashed REPORTED-ONLY: RULES_LABEL `4457e971df3dc5d1…`, RULES_GEOMETRY `a7452748d40c511a…`
- Verdict: **PASS_NO_FALSIFICATION**
- Executed at: 2026-10-23T19:56:10Z
- Resume lineage: rc-67 producer runs 40006151200 / 40011795717 scoped but never committed this work; their plans are preserved under results/evaluation/orchestration/ and executed here.

## Requirement-4 lineage of the two newly accepted product cycles

- **40000001926**: gate half OK ({'gate': 'PASS', 'safe_to_integrate': True, 'required_fixes': []}); accept half OK (['beb227a6 accept product cycle 40000001926']); both halves: **True**
- **40005362253**: gate half OK ({'gate': 'PASS', 'safe_to_integrate': True, 'required_fixes': []}); accept half OK (['f9618377 accept product cycle 40005362253']); both halves: **True**

## Ordered item 1 — currency cross-check

- Quantities: 57 — CONFIRMED 57, DIVERGENT 0, NOT_FOUND 0, CONFIRMED_CORRECTED (disclosed) 1
- Headline (applied precision-matched, 5e-4): **ALL_CONFIRMED**

### Float-comparison disclosure (accepted D-A dual-verdict convention)

- Headline under the **frozen literal 1e-6** rule: **DIVERGENCE_PRESENT** (CONFIRMED 54, DIVERGENT 2, NOT_FOUND 0).
- Headline under the **applied precision-matched** rule: **ALL_CONFIRMED** (CONFIRMED 57, DIVERGENT 0, NOT_FOUND 0).

| quantity | published (3dp) | raw found | abs delta | strict 1e-6 | applied 5e-4 | round(raw,3)==pub |
|---|---|---|---|---|---|---|
| `reliability_40000001926_ready_rate` | 0.857 | 0.8571428571428571 | 1.429e-04 | DIVERGENT | CONFIRMED | True |
| `reliability_40000001926_citation_validity` | 1.0 | 1.0 | 0.000e+00 | CONFIRMED | CONFIRMED | True |
| `reliability_40000001926_source_validity` | 1.0 | 1.0 | 0.000e+00 | CONFIRMED | CONFIRMED | True |
| `reliability_40000001926_language_match_rate` | 1.0 | 1.0 | 0.000e+00 | CONFIRMED | CONFIRMED | True |
| `reliability_40000001926_prose_citation_validity` | 0.982 | 0.9818181818181818 | 1.818e-04 | DIVERGENT | CONFIRMED | True |
| `reliability_40000001926_degradation_visible_rate` | 1.0 | 1.0 | 0.000e+00 | CONFIRMED | CONFIRMED | True |
| `reliability_40000001926_stability_jaccard_min` | 1.0 | 1.0 | 0.000e+00 | CONFIRMED | CONFIRMED | True |
| `span_selection_candidate_guarded_yield` | 0.05 | 0.05 | 0.000e+00 | CONFIRMED | CONFIRMED | True |
| `span_selection_candidate_unguarded_yield` | 0.3 | 0.3 | 0.000e+00 | CONFIRMED | CONFIRMED | True |
| `counter_precision_baseline_yield_guarded` | 0.142857 | 0.142857 | 0.000e+00 | CONFIRMED | CONFIRMED | False |
| `counter_precision_baseline_yield_unguarded` | 0.261905 | 0.261905 | 0.000e+00 | CONFIRMED | CONFIRMED | False |
| `counter_precision_delta_yield_guarded` | 0.071429 | 0.071429 | 0.000e+00 | CONFIRMED | CONFIRMED | False |
| `counter_precision_delta_yield_unguarded` | 0.142857 | 0.142857 | 0.000e+00 | CONFIRMED | CONFIRMED | False |

- ✅ `reliability_40000001926_ready_rate`: published `0.857` vs found `0.8571428571428571` → **CONFIRMED**
- ✅ `reliability_40000001926_citation_validity`: published `1.0` vs found `1.0` → **CONFIRMED**
- ✅ `reliability_40000001926_source_validity`: published `1.0` vs found `1.0` → **CONFIRMED**
- ✅ `reliability_40000001926_language_match_rate`: published `1.0` vs found `1.0` → **CONFIRMED**
- ✅ `reliability_40000001926_prose_citation_validity`: published `0.982` vs found `0.9818181818181818` → **CONFIRMED**
- ✅ `reliability_40000001926_degradation_visible_rate`: published `1.0` vs found `1.0` → **CONFIRMED**
- ✅ `reliability_40000001926_stability_jaccard_min`: published `1.0` vs found `1.0` → **CONFIRMED**
- ✅ `reliability_40000001926_n_degraded_legs`: published `1` vs found `1` → **CONFIRMED**
- ✅ `reliability_40000001926_n_legs_executed`: published `7` vs found `7` → **CONFIRMED**
- ✅ `reliability_40000001926_claim_false`: published `False` vs found `False` → **CONFIRMED**
- ✅ `reliability_40000001926_protocol_sha`: published `418c516f537618655c920c2de321c100add372d7e09c4d74c9f3738d87dce3b1` vs found `418c516f537618655c920c2de321c100add372d7e09c4d74c9f3738d87dce3b1` → **CONFIRMED**
- ✅ `span_selection_baseline_n_scored`: published `20` vs found `20` → **CONFIRMED**
- ✅ `span_selection_baseline_n_emitted`: published `0` vs found `0` → **CONFIRMED**
- ✅ `span_selection_candidate_guarded_n_emitted`: published `1` vs found `1` → **CONFIRMED**
- ✅ `span_selection_candidate_guarded_yield`: published `0.05` vs found `0.05` → **CONFIRMED**
- ✅ `span_selection_candidate_unguarded_n_emitted`: published `6` vs found `6` → **CONFIRMED**
- ✅ `span_selection_candidate_unguarded_yield`: published `0.3` vs found `0.3` → **CONFIRMED**
- ✅ `span_selection_unguarded_de_emitted`: published `2` vs found `2` → **CONFIRMED**
- ✅ `span_selection_unguarded_fr_emitted`: published `4` vs found `4` → **CONFIRMED**
- ✅ `span_selection_unguarded_it_emitted`: published `0` vs found `0` → **CONFIRMED**
- ✅ `span_selection_guarded_emitted_id_fr`: published `['bge_136 III 196']` vs found `['bge_136 III 196']` → **CONFIRMED**
- ✅ `counter_precision_baseline_n_signals`: published `42` vs found `42` → **CONFIRMED**
- ✅ `counter_precision_baseline_n_evidenced_guarded`: published `6` vs found `6` → **CONFIRMED**
- ✅ `counter_precision_baseline_yield_guarded`: published `0.142857` vs found `0.142857` → **CONFIRMED**
- ✅ `counter_precision_baseline_yield_unguarded`: published `0.261905` vs found `0.261905` → **CONFIRMED**
- ✅ `counter_precision_delta_n_signals`: published `28` vs found `28` → **CONFIRMED**
- ✅ `counter_precision_delta_n_evidenced_guarded`: published `2` vs found `2` → **CONFIRMED**
- ✅ `counter_precision_delta_yield_guarded`: published `0.071429` vs found `0.071429` → **CONFIRMED**
- ✅ `counter_precision_delta_yield_unguarded`: published `0.142857` vs found `0.142857` → **CONFIRMED**
- ✅ `counter_precision_known_reach_baseline`: published `8` vs found `8` → **CONFIRMED**
- ✅ `counter_precision_known_reach_broad`: published `11` vs found `11` → **CONFIRMED**
- ✅ `counter_precision_adjudication_verdict`: published `BROADER_BUDGET_ADDS_PROPORTIONAL_EVIDENCE` vs found `BROADER_BUDGET_ADDS_PROPORTIONAL_EVIDENCE` → **CONFIRMED**
- ✅ `counter_precision_profile_rent_default`: published `fr-bail-entretien` vs found `fr-bail-entretien` → **CONFIRMED**
- ✅ `counter_precision_profile_corporate_criminal`: published `responsabilite-penale-entreprise-102cp` vs found `responsabilite-penale-entreprise-102cp` → **CONFIRMED**
- ✅ `counter_precision_profile_bjr_domain_mismatch`: published `fr-bail-entretien` vs found `fr-bail-entretien` → **CONFIRMED**
- ✅ `counter_precision_profile_petty_theft_null`: published `None` vs found `None` → **CONFIRMED**
- ✅ `counter_precision_invariant_network_blocked`: published `True` vs found `True` → **CONFIRMED**
- ✅ `counter_precision_invariant_budgets_unchanged`: published `True` vs found `True` → **CONFIRMED**
- ✅ `absent_id_probe_n_probed`: published `3` vs found `3` → **CONFIRMED**
- ✅ `absent_id_probe_n_span_evidenced`: published `0` vs found `0` → **CONFIRMED**
- ✅ `verification_sweep_passed`: published `135` vs found `135` → **CONFIRMED**
- ✅ `verification_sweep_failed`: published `0` vs found `0` → **CONFIRMED**
- ✅ `cache_coverage_n_added`: published `15` vs found `15` → **CONFIRMED**
- ✅ `cache_coverage_n_cache_before`: published `764` vs found `764` → **CONFIRMED**
- ✅ `cache_coverage_n_cache_after`: published `779` vs found `779` → **CONFIRMED**
- ✅ `offline_slice_verified`: published `True` vs found `True` → **CONFIRMED**
- ✅ `offline_slice_answer_status`: published `ready` vs found `ready` → **CONFIRMED**
- ✅ `offline_slice_cited_decision_ids`: published `4` vs found `4` → **CONFIRMED**
- ✅ `offline_slice_counter_status_bearing_rows`: published `5` vs found `5` → **CONFIRMED**
- ✅ `offline_slice_n_decisions`: published `100` vs found `100` → **CONFIRMED**
- ✅ `offline_slice_n_clusters`: published `8` vs found `8` → **CONFIRMED**
- ✅ `planner_sha256`: published `9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9` vs found `9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9` → **CONFIRMED**
- ✅ `reliability_40000001926_leg_statuses`: published `{'n_legs': 7, 'n_measured': 6, 'n_degraded_writer_abort': 1, 'all_n_counter_rows_zero': True}` vs found `{'n_legs': 7, 'n_measured': 6, 'n_degraded_writer_abort': 1, 'all_n_counter_rows_zero': True, 'statuses': ['MEASURED', 'MEASURED', 'MEASURED', 'MEASURED', 'MEASURED', 'MEASURED', 'DEGRADED_WRITER_ABORT']}` → **CONFIRMED**
- 🔧 `span_selection_39986094168_report_arm_label_correction_landed`: published `{'report_table_labels_6_emission_arm': 'candidate', 'artifact_arm_emitting_6': 'candidate_unguarded', 'artifact_candidate_guarded_n_emitted': 1, 'correction_in_later_accepted_report': True}` vs found `{'report_labels_6_as_candidate': True, 'artifact_arm_names': ['baseline', 'candidate', 'candidate_unguarded'], 'guarded_n_emitted': 1, 'unguarded_n_emitted': 6, 'unguarded_yield': 0.3, 'guarded_yield': 0.05, 'correction_phrase_present': True}` → **CONFIRMED_CORRECTED**
- ✅ `absent_id_probe_per_row_reason_codes`: published `{'gr_gerichte_PZ_2006_125': 'pivot_absent', 'zh_mietgericht_MB170006-L': 'pivot_absent', 'ch_vb_JAAC_68.7__': 'no_frozen_anchor_profile_for_query', 'all_span_evidenced_false': True}` vs found `{'gr_gerichte_PZ_2006_125': 'pivot_absent', 'zh_mietgericht_MB170006-L': 'pivot_absent', 'ch_vb_JAAC_68.7__': 'no_frozen_anchor_profile_for_query'}` → **CONFIRMED**
- ✅ `cache_coverage_entries_partition`: published `{'n_entries': 15, 'all_status_200': True, 'all_key_consistent': True}` vs found `{'n_entries': 15, 'statuses': [200], 'all_key_consistent': True}` → **CONFIRMED**
- ✅ `offline_slice_page_contract_detail`: published `{'page_contract': True, 'detail': 'PASS 67 assertions', 'network': 'none'}` vs found `{'page_contract': True, 'detail': 'PASS 67 assertions', 'network': 'none'}` → **CONFIRMED**

## Ordered item 2 — falsification re-run (same frozen rule set, new head)

- Verdict: **PRODUCT_FALSIFIED** (exit 1)
- Falsification proven: True
- Failed gates: ['mf::concept_coverage::39319405429::de-kapitalverletzung', 'mf::counter_authority_surface::39319405429::de-kapitalverletzung', 'mf::counter_authority_surface::39319405429::fr-bail-entretien', 'mf::counter_authority_surface::39319405429::it-responsabilita-medica']
- Equals accepted 4-gate set: True
- Superset of accepted: True
- Gates 11/18 passed; n_questions=3
- Engine input_drift: []
- wrapper/engine direction_version 61/57 vs lane 65; wrapper/engine versions are historical fixture pins, disclosed not repaired

## Ordered item 3 — planner-remedy + degradation pin

- Overall: **CONFIRMED**
- `planner_sha256`: **CONFIRMED**
- `remedy_a_ordering`: **CONFIRMED**
- `degradation_pin_e_emission_writer_abort`: **CONFIRMED**
- `frozen_product_pins_rehash`: **DRIFT_REPORTED**

## Controls

- `C1_planted_currency_divergence_is_detected`: PASS
- `C2_frozen_rules_rehash_holds`: PASS
- `C3_packet_bytes_unchanged`: PASS

## Ordered item 5 — coverage v2 re-freeze

- NOT EXECUTED — conditional on the coverage family being resumed; it is NOT resumed this cycle.

## Claim ceiling

- This instrument cross-checks published product quantities against their own committed artifacts and re-executes the accepted falsification benchmark on the newest accepted head. It scores no frozen bar, re-derives no threshold, classifies no decision, and asserts no serve or human-gate readiness. Both DO-NOT-SERVE orders stand; admission stays fail-closed; the comparative map-versus-ranked-list half is NOT scored while zero counter rows are evidenced (factory-wide requirement 22).
