# V65 Currency Cross-Check + Falsification Re-Run — run 39986080045

- Direction: v65
- Product mount head: `f4cd7d7c7d2dea09b2f4f4388072fdc517d5cf3e`
- Packet of record: 39319405429 (bytes unchanged, re-hashed)
- Frozen rules re-hashed REPORTED-ONLY: RULES_LABEL `4457e971df3dc5d1…`, RULES_GEOMETRY `a7452748d40c511a…`
- Verdict: **PASS_NO_FALSIFICATION**
- Executed at: 2026-10-23T16:45:40Z

## Ordered item 1 — currency cross-check

- Quantities: 28 — CONFIRMED 28, DIVERGENT 0, NOT_FOUND 0
- Headline: **ALL_CONFIRMED**

- ✅ `reliability_39799042649_ready_rate`: published `0.857` vs found `0.8571428571428571` → **CONFIRMED**
- ✅ `reliability_39799042649_jaccard_min`: published `0.667` vs found `0.666667` → **CONFIRMED**
- ✅ `reliability_39799042649_claim_false`: published `False` vs found `False` → **CONFIRMED**
- ✅ `reliability_39924626016_ready_rate`: published `0.571` vs found `0.5714285714285714` → **CONFIRMED**
- ✅ `reliability_39924626016_jaccard_min`: published `0.286` vs found `0.285714` → **CONFIRMED**
- ✅ `reliability_39924626016_claim_false`: published `False` vs found `False` → **CONFIRMED**
- ✅ `reliability_39956256289_ready_rate`: published `0.0` vs found `0.0` → **CONFIRMED**
- ✅ `reliability_39956256289_jaccard_min`: published `1.0` vs found `1.0` → **CONFIRMED**
- ✅ `reliability_39956256289_claim_false`: published `False` vs found `False` → **CONFIRMED**
- ✅ `reliability_protocol_sha_identical_all_three`: published `418c516f537618655c920c2de321c100add372d7e09c4d74c9f3738d87dce3b1` vs found `418c516f537618655c920c2de321c100add372d7e09c4d74c9f3738d87dce3b1` → **CONFIRMED**
- ✅ `writer_abort_39956256289_degraded_visible_rate`: published `1.0` vs found `1.0` → **CONFIRMED**
- ✅ `writer_abort_39956256289_n_degraded_legs`: published `7` vs found `7` → **CONFIRMED**
- ✅ `writer_abort_39956256289_n_legs_executed`: published `7` vs found `7` → **CONFIRMED**
- ✅ `counter_surface_known_reached_n`: published `24` vs found `24` → **CONFIRMED**
- ✅ `counter_surface_known_n`: published `28` vs found `28` → **CONFIRMED**
- ✅ `counter_surface_cap8_n_signalled_total`: published `42` vs found `42` → **CONFIRMED**
- ✅ `counter_surface_cap24_n_signalled_total`: published `70` vs found `70` → **CONFIRMED**
- ✅ `counter_surface_cap8_n_hydrated`: published `32` vs found `32` → **CONFIRMED**
- ✅ `counter_surface_cap24_n_hydrated`: published `93` vs found `93` → **CONFIRMED**
- ✅ `coverage_live_n_texts_executed`: published `24` vs found `24` → **CONFIRMED**
- ✅ `coverage_live_n_frozen_ids_reached`: published `23` vs found `23` → **CONFIRMED**
- ✅ `coverage_live_n_texts_cache_miss`: published `0` vs found `0` → **CONFIRMED**
- ✅ `coverage_offline_n_texts_executed`: published `20` vs found `20` → **CONFIRMED**
- ✅ `coverage_offline_n_cache_hits`: published `56` vs found `56` → **CONFIRMED**
- ✅ `coverage_offline_n_network_calls`: published `0` vs found `0` → **CONFIRMED**
- ✅ `planner_sha256`: published `9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9` vs found `9764a37e8bc7c8c31a329ba15db89657e8ee47dde8ada924fa55d5e755fd06a9` → **CONFIRMED**
- ✅ `reliability_protocol_sha_set`: published `['418c516f537618655c920c2de321c100add372d7e09c4d74c9f3738d87dce3b1']` vs found `['418c516f537618655c920c2de321c100add372d7e09c4d74c9f3738d87dce3b1']` → **CONFIRMED**
- ✅ `writer_abort_39956256289_7of7_degraded_zero_counter`: published `{'n_degraded': 7, 'n_legs': 7, 'all_n_counter_rows_zero': True}` vs found `{'n_degraded': 7, 'n_legs': 7, 'all_n_counter_rows_zero': True, 'statuses': ['DEGRADED_WRITER_ABORT', 'DEGRADED_WRITER_ABORT', 'DEGRADED_WRITER_ABORT', 'DEGRADED_WRITER_ABORT', 'DEGRADED_WRITER_ABORT', 'DEGRADED_WRITER_ABORT', 'DEGRADED_WRITER_ABORT']}` → **CONFIRMED**

## Ordered item 2 — falsification re-run (same frozen rule set, new head)

- Verdict: **PRODUCT_FALSIFIED** (exit 1)
- Falsification proven: True
- Failed gates: ['mf::concept_coverage::39319405429::de-kapitalverletzung', 'mf::counter_authority_surface::39319405429::de-kapitalverletzung', 'mf::counter_authority_surface::39319405429::fr-bail-entretien', 'mf::counter_authority_surface::39319405429::it-responsabilita-medica']
- Equals accepted 4-gate set: True
- Superset of accepted: True
- Gates 11/18 passed; n_questions=3
- Engine input_drift: []
- wrapper/engine direction_version 61/57 vs lane 65; wrapper/engine versions are historical fixture pins and are disclosed, not repaired

## Ordered item 3 — planner-remedy + degradation pin

- Overall: **CONFIRMED**
- `planner_sha256`: **CONFIRMED**
- `remedy_a_ordering`: **CONFIRMED**
- `degradation_pin_e_emission_writer_abort`: **CONFIRMED**
- `frozen_product_pins_rehash`: **DRIFT_REPORTED**

## Ordered item 5 — D1/D2/D3 disclosure (CYCLE_39965089504_GATE.json)

- Gate: PASS, safe_to_integrate=True, required_fixes=3 (all NON-BLOCKING)
- D1: wording: reports/product/CYCLE_39965089504.md section 6 says test_state_cycle_39965089504.py passes 6/6, but the committed file has 7 tests (7th added in follow-up commit e0c9e32); state/product.json is internally inconsistent
- D2: wording: results/product/orchestration/CYCLE_39965089504_resume_diagnosis.json durable_delta calls product/tests/test_counter_surface_known.py '(new, 90 lines)', but the file existed on accepted base b48d6f3 (created by cycle 39949461593 with 4 tests)
- D3: environment disclosure: producer suite artifact records base 172/1309/20 and head 171/1325/20; an auditor environment with identical package versions reproduces 172/1308/21 and 171/1324/21 - one mount/data-dependent skip-to-pass variance present identically

## Controls

- `C1_planted_currency_divergence_is_detected`: PASS
- `C2_frozen_rules_rehash_holds`: PASS
- `C3_packet_bytes_unchanged`: PASS

## Ordered item 4 — coverage v2 re-freeze

- NOT EXECUTED — conditional on the coverage family being resumed; it is NOT resumed this cycle.

## Claim ceiling

- This instrument cross-checks published product quantities against their own committed artifacts and re-executes the accepted falsification benchmark on the newest accepted head. It scores no frozen bar, re-derives no threshold, classifies no decision, and asserts no serve or human-gate readiness. The comparative map-versus-ranked-list half is NOT scored while zero counter rows are evidenced (factory-wide requirement 22).
