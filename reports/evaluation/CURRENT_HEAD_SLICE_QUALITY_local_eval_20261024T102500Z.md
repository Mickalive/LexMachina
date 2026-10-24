# Current Head Slice Quality Benchmark — run local_eval_20261024T102500Z

- Schema: `lex-evaluation-current-head-slice-quality/1`
- Direction: v67 (derived from state/evaluation.json)
- Product mount head: `e2270c373a8f26c6b826053e8527a216a3304e8b`
- Packet of record: 39319405429
- Hypothesis sha256: `734a447dffd86a36...` (frozen from accepted v65 crosscheck)
- Combined verdict: **H2_FALSIFIED** (exit 1)
- H2 verdict: **H2_FALSIFIED**
- Verified rows: 2; with defects: 2
- Defect histogram: {'D2_letterhead_zone': 1, 'D3_markup_residue': 1, 'D4_language_marker_mismatch': 1}
- Distinct defective decisions: 2
- Elapsed: 0.011 s

## Controls

- `C1_probe_classifies_planted_letterhead_mid_and_markup`: PASS
- `C2_probe_detects_language_marker_mismatch`: PASS
- `C3_frozen_rules_rehash_holds_reported_only`: PASS

## Bundles

- `results/product/offline_slice/20261024T024341Z/rent-default.bundle.json` (offline_latest_20261024T024341Z): verified 1, defective 1 → PROBE_FAIL ids=['gr_gerichte_ERZ 2010 25']
    - `gr_gerichte_ERZ 2010 25` (de, candidate-limiting): **D2_letterhead_zone** grounded_in=full_text offset=0 markup=[] evidence_head=`Kantonsgericht von Graubünden
Dretgira chantunala dal Grischun
Tribunale cantona`
- `results/product/server_slice/39202428670/served.bundle.json` (server_latest_39202428670): verified 1, defective 1 → PROBE_FAIL ids=['bge_BGE_121_III_260']
    - `bge_BGE_121_III_260` (it, candidate-limiting): **D3_markup_residue+D4_language_marker_mismatch** grounded_in=snippet offset=0 markup=['<mark>', '</mark>'] evidence_head=`Regeste Resolutiv bedingter <mark>Mietvertrag</mark>; Anfechtung der Kündigung; `
- `results/product/server_slice/39202428670/first_page.bundle.json` (server_latest_39202428670): verified 0, defective 0 → PROBE_NO_VERIFIED_ROWS

## Reason

2 of 2 counter_evidence_verified rows across 3 bundles carry a frozen defect ({'D2_letterhead_zone': 1, 'D3_markup_residue': 1, 'D4_language_marker_mismatch': 1}) over 2 distinct decision(s). The counter-evidence extractor emits letterhead/markup/language-mismatch content on the current product head's flagship slice artifacts.

## Claim ceiling

descriptive evidence audit of the current product head's shipped slice artifacts under frozen mechanical defect predicates; scores no frozen bar, classifies no decision as supporting/contrary under the frozen rubric, and changes no verdict. Both DO-NOT-SERVE orders stand; admission stays fail-closed; the comparative map-versus-ranked-list half is NOT scored while counter-evidence content defects persist.

Machine record: `results/evaluation/current_head_slice_quality/local_eval_20261024T102500Z.json`
