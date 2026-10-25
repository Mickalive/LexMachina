# FAST-MVP current-head counter-authority falsifier — run 40171237606

- Verdict: **SOUND_COUNTER_ROW_PRESENT** (exit 0)
- Falsification proven: **False**
- Direction: v68
- Product mount head: `29a5c4a548ba0ab8b6a8f574de1e732d17f3d109` (cycle 40159523259)
- New bytes scored: 6 bundles (5 enriched, 1 not-enriched control)
- This is NOT the benchmark of record and does NOT re-run packet-of-record 39319405429.

## Hypothesis checks

- H1_surface_gates_and_source_validity_on_enriched: **True**
- H2_all_verified_scored_rows_content_defective: **False**
- H3_not_enriched_control_zero_issued: **True**
- H4_controls_all_hold: **True**
- H5_pins_identical_before_after: **True**

## Controls

- C1_frozen_predicate_instrument_sha: holds=True
- C2_clean_synthetic_row_must_pass: holds=True
- C3_blanked_synthetic_row_must_fail: holds=True
- C4_empty_bundle_must_have_zero_issued: holds=True

## Per-bundle result

| bundle | family | enriched | n_decisions | surface n_issued | verified scored | defective | sound | log |
|---|---|---|---|---|---|---|---|---|
| offline_rent_default_20261024T142517Z | offline_slice | True | 100 | 1 | 1 | 1 | 0 | {'fr': 28, 'de': 64, 'it': 8} |
| offline_corporate_criminal_liability_20261023T121512Z | offline_slice | True | 100 | 1 | 1 | 0 | 1 | {'fr': 13, 'de': 71, 'it': 16} |
| offline_business_judgment_rule_20261023T121515Z | offline_slice | True | 100 | 1 | 1 | 1 | 0 | {'und': 18, 'de': 52, 'it': 8, 'fr': 22} |
| offline_petty_theft_dismissal_20261023T121518Z | offline_slice | True | 100 | 1 | 1 | 1 | 0 | {'de': 86, 'fr': 14} |
| server_served_20261023T224255Z | server_slice | True | 100 | 1 | 1 | 1 | 0 | {'de': 55, 'it': 20, 'fr': 20, 'und': 5} |
| server_first_page_20261023T224255Z | server_slice | False | 100 | 0 | 0 | 0 | 0 | {'de': 55, 'it': 20, 'fr': 20, 'und': 5} |

## Verified scored rows (frozen D1-D4 predicates)

- `offline_rent_default_20261024T142517Z` / `gr_gerichte_ERZ 2010 25` / candidate-limiting: **D2_letterhead_zone** (defects=['D2_letterhead_zone'], grounded_in=full_text, offset=0); head='Kantonsgericht von Graubünden\nDretgira chantunala dal Grischun\nTribunale cantonale dei Gri'
- `offline_corporate_criminal_liability_20261023T121512Z` / `bstger_SK.2023.49` / candidate-limiting: **COUNTER_REASONING** (defects=[], grounded_in=snippet, offset=0); head="Subsidiairement, les 4 versements suivants pour un montant total de USD 1'933'183.– et de "
- `offline_business_judgment_rule_20261023T121515Z` / `bge_BGE_110_II_391` / candidate-limiting: **D2_letterhead_zone** (defects=['D2_letterhead_zone'], grounded_in=full_text, offset=0); head='Urteilskopf\n110 II 391\n75. Auszug aus dem Urteil der I. Zivilabteilung vom 10. April 1984 '
- `offline_petty_theft_dismissal_20261023T121518Z` / `ge_gerichte_CAPH_107_2004` / candidate-limiting: **D3_markup_residue** (defects=['D3_markup_residue'], grounded_in=snippet, offset=0); head='<mark>Selon</mark> l’art. 337 CO, l’employeur et le travailleur peuvent résilier immédiate'
- `server_served_20261023T224255Z` / `bge_BGE_121_III_260` / candidate-limiting: **D3_markup_residue+D4_language_marker_mismatch** (defects=['D3_markup_residue', 'D4_language_marker_mismatch'], grounded_in=snippet, offset=0); head='Regeste Resolutiv bedingter <mark>Mietvertrag</mark>; Anfechtung der Kündigung; Erstreckun'

## Aggregate

- Verified scored rows (enriched): 5
- Defective: 4
- Defect histogram: {'D2_letterhead_zone': 2, 'D3_markup_residue': 2, 'D4_language_marker_mismatch': 1}
- Distinct defective decision ids: ['bge_BGE_110_II_391', 'bge_BGE_121_III_260', 'ge_gerichte_CAPH_107_2004', 'gr_gerichte_ERZ 2010 25']
- Enriched bundles with a sound counter row: 1

## Claim ceiling

Descriptive, FAST-MVP falsification on NEW product bytes only. It (a) does NOT re-run, replace, weaken or move the benchmark of record PRODUCT_FALSIFIED on packet-of-record 39319405429; (b) does NOT discharge or trigger v67 item (2), which was updated to NOW_DISCRIMINATING by the v68 correction; the remaining mechanism is rejection/incumbent handling; (c) does NOT re-derive the accepted D2 pattern profile (40089391202) and does NOT upgrade D3/D4 beyond this named population; (d) edits NO frozen bar, rubric, threshold, predicate or verdict contract; (e) issues NO serve verdict, lifts NO DO-NOT-SERVE order, and does NOT admit any packet; (f) makes NO claim that the map helps a jurist; (g) runs NO universal-174k benchmark; (h) makes NO recall claim against a Web/OpenCaseLaw baseline (the bundle is a served artifact, not a retrieval run). Posture stays fail-closed: packet_admitted=false, machine_gate_ready=false, human_gate_ready=false, ready_for_owner_session=false, owner_decision_required=false.

## Pin discipline

- Pins before: all_match=True
- Pins after: all_match=True
- Numeric environment: {"numpy": "NOT_IMPORTABLE", "platform": "Linux-6.17.0-1022-azure-x86_64-with-glibc2.39", "python": "3.12.3", "scipy": "NOT_IMPORTABLE", "sklearn": "NOT_IMPORTABLE", "thread_env": {"MKL_NUM_THREADS": null, "OMP_NUM_THREADS": null, "OPENBLAS_NUM_THREADS": null}}

- v67 item (2): **NOT_YET_DISCRIMINATING (unchanged)**
- Posture: packet_admitted=false, machine_gate_ready=false, human_gate_ready=false, ready_for_owner_session=false, owner_decision_required=false.

