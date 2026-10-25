# Counter-Evidence Content-Quality Falsification Benchmark — run 40171237606

- Schema: `lex-evaluation-counter-evidence-quality-benchmark/1`
- Direction: v68 (derived from state/evaluation.json)
- Product mount head: `e4f72a8e6c0460bc52dc625ff3e2da86161e2564`
- Packet of record: 39319405429
- Hypothesis sha256: `734a447dffd86a36...` (frozen from accepted v65 crosscheck)
- Combined verdict: **H2_FALSIFIED** (exit 1)
- H2 verdict: **H2_FALSIFIED**
- Verified rows: 14; with defects: 14
- Defect histogram: {'D2_letterhead_zone': 10, 'D3_markup_residue': 4, 'D4_language_marker_mismatch': 4}
- Distinct defective decisions: 2
- Elapsed: 0.066 s

## Controls

- `C1_probe_classifies_planted_letterhead_mid_and_markup`: PASS
- `C2_probe_detects_language_marker_mismatch`: PASS
- `C3_frozen_rules_rehash_holds_reported_only`: PASS

## Bundles

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

## Reason

14 of 14 counter_evidence_verified rows across 15 bundles carry a frozen defect ({'D2_letterhead_zone': 10, 'D3_markup_residue': 4, 'D4_language_marker_mismatch': 4}) over 2 distinct decision(s). The counter-evidence extractor emits letterhead/markup/language-mismatch content on the product's own flagship slice artifacts.

## Claim ceiling

descriptive evidence audit of the product's own shipped slice artifacts under frozen mechanical defect predicates; scores no frozen bar, classifies no decision as supporting/contrary under the frozen rubric, and changes no verdict. Both DO-NOT-SERVE orders stand; admission stays fail-closed; the comparative map-versus-ranked-list half is NOT scored while counter-evidence content defects persist (factory-wide requirement 22/37).

Machine record: `results/evaluation/counter_evidence_quality_benchmark/40171237606.json`
