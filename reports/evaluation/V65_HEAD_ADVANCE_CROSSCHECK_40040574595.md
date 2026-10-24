# V65 Head-Advance Cross-Check v2 — run 40040574595

- Direction: v65
- Product mount head: `e4f72a8e6c0460bc52dc625ff3e2da86161e2564` (accept product cycle 40032389983)
- Packet of record: 39319405429 (bytes re-hashed, unchanged)
- Frozen rules re-hashed REPORTED-ONLY: RULES_LABEL `4457e971df3dc5d1…`, RULES_GEOMETRY `a7452748d40c511a…`
- Verdict: **PASS_NO_FALSIFICATION** (exit 0)
- Executed at: 2026-10-24T00:12:55Z
- H2 shipped-slice counter-evidence probe: **H2_FALSIFIED** (14 of 14 verified rows carry a frozen defect)

## Re-open trigger

- Accepted product head advanced `f9618377` (accept 40005362253) → `e4f72a8e` (accept 40032389983). Requirement-4 lineage: 40025340938, 40032389983.
- Cycles **40018153655** (gate REVISE, no accept commit) and **40028750240** (gate PASS but NO accept commit) are frozen as NON-lineage and verified excluded: True.

## Ordered item 1 — currency cross-check

- Quantities: 39 — CONFIRMED 36, DIVERGENT 0, NOT_FOUND 0, CONFIRMED_LAG (disclosed) 2, NOT_REEXECUTED_THIS_CYCLE 1
- Headline (applied precision-matched, 5e-4): **ALL_CONFIRMED**

### Float-comparison disclosure (accepted D-A dual-verdict convention)

- Frozen-literal 1e-6: **ALL_CONFIRMED** (CONFIRMED 36, DIVERGENT 0).
- Applied precision-matched 5e-4: **ALL_CONFIRMED**.

- ✅ `os_224250_verified`: published `True` vs found `True` → **CONFIRMED**
- ✅ `os_224250_page_contract`: published `True` vs found `True` → **CONFIRMED**
- ✅ `os_224250_page_contract_detail`: published `PASS 67 assertions` vs found `PASS 67 assertions` → **CONFIRMED**
- ✅ `os_224250_n_decisions`: published `100` vs found `100` → **CONFIRMED**
- ✅ `os_224250_n_clusters`: published `8` vs found `8` → **CONFIRMED**
- ✅ `os_224250_largest_cluster`: published `35` vs found `35` → **CONFIRMED**
- ✅ `os_224250_cited_decision_ids`: published `4` vs found `4` → **CONFIRMED**
- ✅ `os_224250_counter_status_bearing_rows`: published `5` vs found `5` → **CONFIRMED**
- ✅ `os_224250_answer_status`: published `ready` vs found `ready` → **CONFIRMED**
- ✅ `os_224250_geometry_preserved`: published `True` vs found `True` → **CONFIRMED**
- ✅ `os_224250_network`: published `none` vs found `none` → **CONFIRMED**
- ✅ `os_224250_n_candidates`: published `165` vs found `165` → **CONFIRMED**
- ✅ `os_224250_rows_with_source_url`: published `100` vs found `100` → **CONFIRMED**
- ✅ `ss_224255_n_checks`: published `10` vs found `10` → **CONFIRMED**
- ✅ `ss_224255_all_checks_pass`: published `True` vs found `True` → **CONFIRMED**
- ✅ `ss_224255_n_decisions`: published `100` vs found `100` → **CONFIRMED**
- ✅ `ss_224255_n_clusters`: published `8` vs found `8` → **CONFIRMED**
- ✅ `ss_224255_n_cited`: published `2` vs found `2` → **CONFIRMED**
- ✅ `ss_224255_counter_authorities`: published `1` vs found `1` → **CONFIRMED**
- ✅ `ss_224255_rows_with_source_url`: published `100` vs found `100` → **CONFIRMED**
- ✅ `ss_224255_geometry_preserved`: published `True` vs found `True` → **CONFIRMED**
- ✅ `sv_224250_host_mcp_opencaselaw`: published `100` vs found `100` → **CONFIRMED**
- ✅ `sv_224250_cited_ids_resolve`: published `True` vs found `True` → **CONFIRMED**
- ✅ `sv_224250_cache_writes_zero`: published `0` vs found `0` → **CONFIRMED**
- ✅ `os_prior_190402_n_decisions`: published `100` vs found `100` → **CONFIRMED**
- ✅ `os_prior_190402_counter_status_bearing_rows`: published `5` vs found `5` → **CONFIRMED**
- ✅ `state_rows_with_source_url`: published `100` vs found `100` → **CONFIRMED**
- ✅ `state_offline_slice_legs_passed`: published `4` vs found `4` → **CONFIRMED**
- ✅ `state_page_contract_assertions`: published `67` vs found `67` → **CONFIRMED**
- ✅ `state_served_checks_passed`: published `10/10` vs found `10/10` → **CONFIRMED**
- ✅ `state_human_gate_ready_stays_false`: published `False` vs found `False` → **CONFIRMED**
- ✅ `state_machine_gate_ready_stays_false`: published `False` vs found `False` → **CONFIRMED**
- ✅ `state_packet_admitted_stays_false`: published `False` vs found `False` → **CONFIRMED**
- ✅ `state_ready_for_owner_session_stays_false`: published `False` vs found `False` → **CONFIRMED**
- ✅ `gate_40025340938_pass`: published `PASS` vs found `PASS` → **CONFIRMED**
- ✅ `gate_40032389983_pass`: published `PASS` vs found `PASS` → **CONFIRMED**
- 📌 `state_accepted_run_id_pointer_lag`: published `40000001926` vs found `40000001926` → **CONFIRMED_LAG**
- 📌 `state_current_run_pointer_lag`: published `40005362253` vs found `40005362253` → **CONFIRMED_LAG**
- 🚫 `state_claim_ceiling_188_mvp_tests`: published `All 188 MVP tests pass` vs found `None` → **NOT_REEXECUTED_THIS_CYCLE**

## Ordered item 2 — shipped-slice counter-evidence probe (H2)

- Verdict: **H2_FALSIFIED**
- Bundles: 15/15 present (3 scoping-inspected, disclosed)
- Verified rows: 14; with a frozen defect: 14
- Defect histogram: {'D2_letterhead_zone': 10, 'D3_markup_residue': 4, 'D4_language_marker_mismatch': 4}
- **This probe scores no frozen bar.** Its population is the product's own shipped slice bundles, not the RULES_LABEL population; the frozen rubrics are re-hashed REPORTED-ONLY (factory-wide requirement 22).

- `results/product/offline_slice/20261023T202433Z/rent-default.bundle.json`: verified 0, defective 0 → PROBE_NO_VERIFIED_ROWS
- `results/product/offline_slice/20261023T202440Z/rent-default.bundle.json`: verified 1, defective 1 → PROBE_FAIL ids=['gr_gerichte_ERZ 2010 25']
    - `gr_gerichte_ERZ 2010 25` (de, candidate-limiting): **D2_letterhead_zone** grounded_in=full_text offset=0 markup=[] evidence_head=`Kantonsgericht von Graubünden
Dretgira chantunala dal Grischun
Tribunale cantona`
- `results/product/offline_slice/20261023T203316Z/rent-default.bundle.json` (scoping-inspected): verified 1, defective 1 → PROBE_FAIL ids=['gr_gerichte_ERZ 2010 25']
    - `gr_gerichte_ERZ 2010 25` (de, candidate-limiting): **D2_letterhead_zone** grounded_in=full_text offset=0 markup=[] evidence_head=`Kantonsgericht von Graubünden
Dretgira chantunala dal Grischun
Tribunale cantona`
- `results/product/offline_slice/20261023T212530Z/rent-default.bundle.json`: verified 1, defective 1 → PROBE_FAIL ids=['gr_gerichte_ERZ 2010 25']
    - `gr_gerichte_ERZ 2010 25` (de, candidate-limiting): **D2_letterhead_zone** grounded_in=full_text offset=0 markup=[] evidence_head=`Kantonsgericht von Graubünden
Dretgira chantunala dal Grischun
Tribunale cantona`
- `results/product/offline_slice/20261023T214943Z/rent-default.bundle.json`: verified 1, defective 1 → PROBE_FAIL ids=['gr_gerichte_ERZ 2010 25']
    - `gr_gerichte_ERZ 2010 25` (de, candidate-limiting): **D2_letterhead_zone** grounded_in=full_text offset=0 markup=[] evidence_head=`Kantonsgericht von Graubünden
Dretgira chantunala dal Grischun
Tribunale cantona`
- `results/product/offline_slice/20261023T220629Z/rent-default.bundle.json`: verified 1, defective 1 → PROBE_FAIL ids=['gr_gerichte_ERZ 2010 25']
    - `gr_gerichte_ERZ 2010 25` (de, candidate-limiting): **D2_letterhead_zone** grounded_in=full_text offset=0 markup=[] evidence_head=`Kantonsgericht von Graubünden
Dretgira chantunala dal Grischun
Tribunale cantona`
- `results/product/offline_slice/20261023T222223Z/rent-default.bundle.json`: verified 1, defective 1 → PROBE_FAIL ids=['gr_gerichte_ERZ 2010 25']
    - `gr_gerichte_ERZ 2010 25` (de, candidate-limiting): **D2_letterhead_zone** grounded_in=full_text offset=0 markup=[] evidence_head=`Kantonsgericht von Graubünden
Dretgira chantunala dal Grischun
Tribunale cantona`
- `results/product/offline_slice/20261023T223903Z/rent-default.bundle.json`: verified 1, defective 1 → PROBE_FAIL ids=['gr_gerichte_ERZ 2010 25']
    - `gr_gerichte_ERZ 2010 25` (de, candidate-limiting): **D2_letterhead_zone** grounded_in=full_text offset=0 markup=[] evidence_head=`Kantonsgericht von Graubünden
Dretgira chantunala dal Grischun
Tribunale cantona`
- `results/product/offline_slice/20261023T224023Z/rent-default.bundle.json`: verified 1, defective 1 → PROBE_FAIL ids=['gr_gerichte_ERZ 2010 25']
    - `gr_gerichte_ERZ 2010 25` (de, candidate-limiting): **D2_letterhead_zone** grounded_in=full_text offset=0 markup=[] evidence_head=`Kantonsgericht von Graubünden
Dretgira chantunala dal Grischun
Tribunale cantona`
- `results/product/offline_slice/20261023T224250Z/rent-default.bundle.json` (scoping-inspected): verified 1, defective 1 → PROBE_FAIL ids=['gr_gerichte_ERZ 2010 25']
    - `gr_gerichte_ERZ 2010 25` (de, candidate-limiting): **D2_letterhead_zone** grounded_in=full_text offset=0 markup=[] evidence_head=`Kantonsgericht von Graubünden
Dretgira chantunala dal Grischun
Tribunale cantona`
- `results/product/server_slice/20261023T223109Z/served.bundle.json`: verified 1, defective 1 → PROBE_FAIL ids=['bge_BGE_121_III_260']
    - `bge_BGE_121_III_260` (it, candidate-limiting): **D3_markup_residue+D4_language_marker_mismatch** grounded_in=snippet offset=0 markup=['<mark>', '</mark>'] evidence_head=`Regeste Resolutiv bedingter <mark>Mietvertrag</mark>; Anfechtung der Kündigung; `
- `results/product/server_slice/20261023T223909Z/served.bundle.json`: verified 1, defective 1 → PROBE_FAIL ids=['bge_BGE_121_III_260']
    - `bge_BGE_121_III_260` (it, candidate-limiting): **D3_markup_residue+D4_language_marker_mismatch** grounded_in=snippet offset=0 markup=['<mark>', '</mark>'] evidence_head=`Regeste Resolutiv bedingter <mark>Mietvertrag</mark>; Anfechtung der Kündigung; `
- `results/product/server_slice/20261023T224031Z/served.bundle.json`: verified 1, defective 1 → PROBE_FAIL ids=['bge_BGE_121_III_260']
    - `bge_BGE_121_III_260` (it, candidate-limiting): **D3_markup_residue+D4_language_marker_mismatch** grounded_in=snippet offset=0 markup=['<mark>', '</mark>'] evidence_head=`Regeste Resolutiv bedingter <mark>Mietvertrag</mark>; Anfechtung der Kündigung; `
- `results/product/server_slice/20261023T224255Z/served.bundle.json` (scoping-inspected): verified 1, defective 1 → PROBE_FAIL ids=['bge_BGE_121_III_260']
    - `bge_BGE_121_III_260` (it, candidate-limiting): **D3_markup_residue+D4_language_marker_mismatch** grounded_in=snippet offset=0 markup=['<mark>', '</mark>'] evidence_head=`Regeste Resolutiv bedingter <mark>Mietvertrag</mark>; Anfechtung der Kündigung; `
- `results/product/offline_slice/20261023T190402Z/rent-default.bundle.json`: verified 1, defective 1 → PROBE_FAIL ids=['gr_gerichte_ERZ 2010 25']
    - `gr_gerichte_ERZ 2010 25` (de, candidate-limiting): **D2_letterhead_zone** grounded_in=full_text offset=0 markup=[] evidence_head=`Kantonsgericht von Graubünden
Dretgira chantunala dal Grischun
Tribunale cantona`

## Ordered item 3 — falsification re-run (same frozen rule set, new head)

- Verdict: **PRODUCT_FALSIFIED** (exit 1)
- Falsification proven: True
- Failed gates: ['mf::concept_coverage::39319405429::de-kapitalverletzung', 'mf::counter_authority_surface::39319405429::de-kapitalverletzung', 'mf::counter_authority_surface::39319405429::fr-bail-entretien', 'mf::counter_authority_surface::39319405429::it-responsabilita-medica']
- Equals accepted 4-gate set: True
- Gates 11/18 passed; n_questions=3
- Engine input_drift: []
- wrapper/engine direction_version 61/57 vs lane 65; wrapper/engine versions are historical fixture pins, disclosed not repaired

## Ordered item 4 — planner-remedy + degradation pin (new run id)

- Overall: **CONFIRMED**
- `planner_sha256`: **CONFIRMED**
- `remedy_a_ordering`: **CONFIRMED**
- `pipeline_sha256_new_baseline_of_record`: **CONFIRMED**
- `degradation_pin_e_emission_writer_abort`: **CONFIRMED**
- `frozen_product_pins_rehash`: **DRIFT_REPORTED**

## Controls

- `C1_planted_currency_divergence_is_detected`: PASS
- `C2_probe_classifies_planted_letterhead_mid_and_markup`: PASS
- `C3_probe_detects_language_marker_mismatch`: PASS
- `C4_frozen_rules_rehash_holds_reported_only`: PASS
- `C5_packet_of_record_bytes_unchanged`: PASS

## Ordered item 5 — coverage v2 re-freeze

- NOT EXECUTED — conditional on the coverage family being resumed; it is NOT resumed this cycle.

## Required fixes D1/D2/D3 of CYCLE_39965089504_GATE.json (quoted-count disclosure)

- Reported here only because this lane quotes those counts: the CYCLE_39965089504 audit returned three NON-BLOCKING required fixes D1/D2/D3; they were discharged by the product lane before the heads cross-checked here. No new D-fix count is asserted.

## Claim ceiling

- This instrument cross-checks published product quantities against their own committed artifacts on the newest accepted head, audits the counter-evidence quality of the product's own newly shipped slice bundles under frozen (non-bar) definitions, and re-executes the accepted mapping-free falsification benchmark on unchanged packet-of-record bytes under the same frozen rules re-hashed REPORTED-ONLY. It scores no frozen bar, re-derives no threshold, classifies no decision under the frozen rubric, and asserts no serve or human-gate readiness. Both DO-NOT-SERVE orders stand; admission stays fail-closed; the comparative map-versus-ranked-list half is NOT scored while zero counter rows are evidenced (factory-wide requirement 22).
