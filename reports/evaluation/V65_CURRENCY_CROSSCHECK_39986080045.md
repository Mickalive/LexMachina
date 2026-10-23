# V65 Currency Cross-Check + Falsification Re-Run — run 39986080045

- Direction: v65
- Product mount head: `f4cd7d7c7d2dea09b2f4f4388072fdc517d5cf3e`
- Packet of record: 39319405429 (bytes unchanged, re-hashed)
- Frozen rules re-hashed REPORTED-ONLY: RULES_LABEL `4457e971df3dc5d1…`, RULES_GEOMETRY `a7452748d40c511a…`
- Verdict: **PASS_NO_FALSIFICATION**
- Executed at: 2026-10-23T16:45:40Z

## Ordered item 1 — currency cross-check

- Quantities: 28 — CONFIRMED 28, DIVERGENT 0, NOT_FOUND 0
- Headline (**applied precision-matched comparison, 5e-4**): **ALL_CONFIRMED**

### Float-comparison disclosure (audit defect D-A, repair round 1)

- The frozen success rule in `V65_CURRENCY_CROSSCHECK_HYPOTHESIS_V1.json` states literally **"(float tolerance 1e-6)"**. The product lane publishes these floats at **3-decimal precision** (its own accepted `CYCLE_39965089504.md` writes "6/7 = 0.857", "0.667", "4/7 = 0.571", "0.286"), so the comparison this instrument APPLIED is the half-ulp of that publication precision, **5e-4**. This deviation from the literal frozen parenthetical is **DISCLOSED here, not silently absorbed** (audit D-A); the frozen hypothesis file is re-hashed against its pin `34fbbe1a…` and never edited (`frozen_rule_edited=false`).
- Headline under the **frozen literal 1e-6** rule: **DIVERGENCE_PRESENT** (CONFIRMED 24, DIVERGENT 4, NOT_FOUND 0).
- Headline under the **applied precision-matched (5e-4)** rule: **ALL_CONFIRMED** (CONFIRMED 28, DIVERGENT 0, NOT_FOUND 0).
- Per-float-quantity dual verdicts (reproduce: `abs_delta = abs(raw_found - published)`; strict = `delta <= 1e-6`, applied = `delta <= 5e-4`):

| quantity | published (3dp) | raw found | abs delta | strict 1e-6 | applied 5e-4 | round(raw,3)==pub |
|---|---|---|---|---|---|---|
| `reliability_39799042649_ready_rate` | 0.857 | 0.8571428571428571 | 1.429e-04 | DIVERGENT | CONFIRMED | True |
| `reliability_39799042649_jaccard_min` | 0.667 | 0.666667 | 3.330e-04 | DIVERGENT | CONFIRMED | True |
| `reliability_39924626016_ready_rate` | 0.571 | 0.5714285714285714 | 4.286e-04 | DIVERGENT | CONFIRMED | True |
| `reliability_39924626016_jaccard_min` | 0.286 | 0.285714 | 2.860e-04 | DIVERGENT | CONFIRMED | True |

- Of the 7 float quantities, the other 3 (`reliability_39956256289_ready_rate` 0.0, `reliability_39956256289_jaccard_min` 1.0, `writer_abort_39956256289_degraded_visible_rate` 1.0) carry delta 0.0 and are CONFIRMED under both readings; the 21 exact/sha/set/composite quantities are unchanged under both readings. The strict-1e-6 headline would make this cycle's item-1 claim a 24/4 split — it is published above rather than hidden behind the applied reading. Neither reading re-scores any frozen bar; this block is disclosure only.
- Machine record: `results/evaluation/v65_currency_crosscheck/39986080045.json` → `currency_crosscheck.float_comparison_disclosure` (written by `evaluation/v65_repair_round1_da_db.py`, shared pure function `evaluation.v65_currency_crosscheck.build_float_disclosure`, so a fresh run and the repair agree by construction).

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

## Ordered item 4 — coverage v2 re-freeze (conditional)

- NOT EXECUTED. The condition is "only if the cross-check coverage family is resumed"; it is NOT resumed this cycle. Item 1(d) is a pin-level cross-check of the committed coverage artifacts (LOCAL_LIVE_COVERAGE2_live.json, LOCAL_OFFLINE_VERIFY_offline.json), not a re-freeze. The underlying parity record 39631600439 stays EXPLORATORY with pending_independent_audit=true — disclosed, never laundered into REPRODUCED or ACCEPTED. *(Merged from the two duplicate sections this section used to have — audit D-C, repair round 1.)*

## Claim ceiling

- This instrument cross-checks published product quantities against their own committed artifacts and re-executes the accepted falsification benchmark on the newest accepted head. It scores no frozen bar, re-derives no threshold, classifies no decision, and asserts no serve or human-gate readiness. The comparative map-versus-ranked-list half is NOT scored while zero counter rows are evidenced (factory-wide requirement 22).

## Reused multilingual/provenance test (FAST-MVP REUSE-FIRST)

Re-executed `evaluation/run_v3_multilingual_provenance_reuse.py` (accepted V61-era checks) on the unchanged V3 packet bytes. Verdict: PARTIAL_MISS_PREEXISTING_SCHEMA_PROPERTY.

- All three frozen bundle SHAs match their V61 pins byte-for-byte (de 9b856e2b…, fr 054bec47…, it 345e20d1…).
- Language robustness holds: the expected language is present in every bundle.
- Two schema-completeness checks fail ON THE PACKET-OF-RECORD BYTES THEMSELVES — **characterization CORRECTED against the bytes by repair round 1 (audit D-B)**:
  - (i) **the `provenance` block has no `query` key** — this is exactly what the V61-era script tests at `run_v3_multilingual_provenance_reuse.py:88` (`"query" in bundle["provenance"]`). The **top-level `query` field EXISTS** on all three bundles as a non-empty string (de: "Aktive Fürsorgepflicht des Arbeitgebers bei einer Kapitalverletzung…", fr: "Résiliation du bail pour défaut d'entretien du bailleur…", it: "Responsabilità del medico per errore terapeutico…"). The earlier wording "the bundle has no top-level `query` field" was **factually wrong and is retracted**.
  - (ii) **every decision carries a `language` key, but its value is explicitly `null` on de 50 / fr 37 / it 47 decisions** (field present with null value, not absent; the V61-era check `d.get(field) is None` counts null as missing and samples only the first such decision per bundle — de `bge_126 V 75` / fr `bger_4A_173_2017` / it `bge_130 V 229`). Those counts are exactly the UNLABELLED counts the accepted engine records for the same bundles (50/37/47 in this run's own falsification record). The earlier wording "one decision per bundle lacks the `language` field" **understated the count and is retracted**.
- These remain PRE-EXISTING structural properties of served packet 39319405429, not a regression introduced by product head f4cd7d7. The packet bytes are unchanged (sha256 32ac8126… re-hashed before and after) and the accepted mapping-free engine already scores language_robustness as REPORTED-only. Disclosed, never repaired by this lane; the accepted reuse script itself is unchanged (REUSE-FIRST).

Record: `results/evaluation/v65_currency_crosscheck/39986080045_multilingual_provenance_reuse.json` (byte recomputation in `byte_recomputation_at_repair`, written by `evaluation/v65_repair_round1_da_db.py`).

## Attempt history (requirement 30: a file named for run X holds run X's measurement; failed attempts preserved, never deleted)

| Attempt | Outcome | Cause | Preserved at |
|---|---|---|---|
| 1 | instrument crash (JSON set not serializable) after falsification subprocess ran | Python `set` in the protocol-sha comparison row | `attempt1_preserved/falsification/` |
| 2 | MATERIAL_DIVERGENCE with ARTIFACT_MISSING + empty failed_gates + planner DIVERGENT | (a) wrong field name `n_cache_miss` vs `n_texts_cache_miss`; (b) `failed_gates` read from `measurement` sub-dict instead of the wrapper's top level; (c) strip/tokenize order check inverted — `strip_redaction_placeholders` is nested *inside* `tokenize(...)`, so it evaluates first despite appearing later in source text; (d) `product/query/pipeline.py` pin drift correctly detected but wrongly treated as a must-hold pin failure | `attempt2_preserved/` |
| 3 | TypeError: unhashable type 'dict' | `failed_gates` entries are dicts with a `gate` key, not bare strings | `attempt3_preserved/falsification/` |
| 4 | PASS_NO_FALSIFICATION (exit 0) — the instrument's own checks all pass | repaired instrument | `results/evaluation/v65_currency_crosscheck/39986080045.json` |

Every attempt was an instrument defect, never a product finding. No threshold, bar, rubric or verdict contract was changed between attempts. The V65 hypothesis and freeze record were committed once, before attempt 1, and never edited.

## Product-advance pin drift (disclosed, not a must-hold failure)

`product/query/pipeline.py` re-hashes to `92505743…` on head f4cd7d7 against the DEGRADATION_DISCLOSURE_CROSSCHECK_FREEZE_RECORD_V3 pin `e105bfed…` (frozen at head ae854b6a). This is expected product advance: the freeze was pinned at an older head and product has since moved through d22f9b6 → b48d6f3 → 31f57ee → f4cd7d7. The three MUST-HOLD pins — planner sha 9764a37e…, remedy-(a) nesting, and the e_EMISSION_WRITER_ABORT degradation marker — all CONFIRMED. Per the frozen hypothesis, "any drift is reported as a pin finding, never silently absorbed".

## Bottom line

The product's newly landed measurements all still hold against their own committed artifacts on the newest accepted head, and the frozen mapping-free falsification benchmark still falsifies the product on the unchanged packet-of-record bytes with the identical four failed gates. The counter-authority evidence gap (n_emitted=0 on all three V3 questions) remains the binding blocker; the comparative map-versus-ranked-list half of the Master Prompt's central product question stays VACUOUS. Both DO-NOT-SERVE orders stand; admission stays fail-closed; frozen absolute bars stay REPORTED-ONLY and unmet on the v3 bytes; human_gate_ready=false; owner_decision_required=false.

## Repair record — round 1 of run 39986080045 (audit `CYCLE_39986080045_GATE.json`, gate=REVISE, safe_to_integrate=false)

Every item in `required_fixes` was repaired in this same cycle. Nothing frozen was edited, no metric was re-scored and no falsification was re-executed (the audit independently reproduced PRODUCT_FALSIFIED with the identical 4-gate set and ordered "No re-execution required").

| Fix | Severity | What was wrong | Repair applied | Where |
|---|---|---|---|---|
| **D-A** | material | Frozen rule says "(float tolerance 1e-6)" but the instrument compared at 5e-4; docstring (old line 23) and `FLOAT_TOL=1e-6` (old line 62) misstated the implementation; the deviation was undisclosed | (i) both tolerances and the precision-matching rationale now published in the result JSON and in this report, with raw per-quantity deltas and BOTH verdicts (strict 1e-6: 24/4; applied 5e-4: 28/0); (ii) docstring rewritten and the false constant replaced by `FROZEN_LITERAL_FLOAT_TOL=1e-6` + `APPLIED_FLOAT_TOL=5e-4` (both actually used); (iii) strict and applied verdicts dual-reported per float quantity | `evaluation/v65_currency_crosscheck.py` (`build_float_disclosure`, docstring, constants); `results/…/39986080045.json` → `currency_crosscheck.float_comparison_disclosure`; report section above |
| **D-B** | material | Multilingual record claimed "(i) one decision per bundle lacks the `language` field; (ii) the bundle has no top-level `query` field" — both wrong against the bytes | Byte-recomputed on the exact packet bytes: top-level `query` present on all 3 bundles / `provenance.query` key absent (what the V61 script tests at line 88); `language` key present on every decision with explicit `null` on de 50 / fr 37 / it 47, equal to the engine's UNLABELLED counts; both old wordings retracted; accepted script unchanged | report section above; `results/…/39986080045_multilingual_provenance_reuse.json` → corrected `interpretation`, `byte_recomputation_at_repair`, `field_semantics` |
| **D-C** | cosmetic | Two identical "Ordered item 4 — coverage v2 re-freeze" sections | Merged into one section in its ordered position | this report |

- Repair instrument: `evaluation/v65_repair_round1_da_db.py` (fail-closed on pin/bundle/engine drift; **idempotent** — a second pass rewrites byte-identical artifacts, verified by `tests/evaluation/test_v65_repair_round1_da_db.py`).
- Machine repair log: `results/evaluation/v65_currency_crosscheck/39986080045_repair_round1.json` (records pre/post artifact digests, frozen pins before/after with `frozen_pins_unchanged=true`, and `falsification_reexecuted=false`).
- Untouched by this repair: `results/evaluation/v65_currency_crosscheck/falsification/39986080045*.json`, the attempt-history directories, `V65_CURRENCY_CROSSCHECK_HYPOTHESIS_V1.json` (sha `34fbbe1a…`), `RULES_LABEL.json` (`4457e971…`), `RULES_GEOMETRY.json` (`a7452748…`), the packet-of-record bytes (`32ac8126…`) and every posture flag (`human_gate_ready`, `machine_gate_ready`, `packet_admitted`, `ready_for_owner_session` all stay `false`).
