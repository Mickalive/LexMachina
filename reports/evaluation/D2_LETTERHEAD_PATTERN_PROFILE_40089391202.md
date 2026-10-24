# D2 Letterhead Pattern Heterogeneity Profile — 40089391202

- direction_version: 67 (v67 ordered work item (1), population extension, separate named run — accepted baseline 40062917685 UNMOVED)
- product mount: `/tmp/lex_accepted/product` head `e2270c373a8f26c6b826053e8527a216a3304e8b`
- packet-of-record: 39319405429 (labelled; verified rows under frozen predicate: 0)
- verdict: **LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED** (exit 0)
- controls: ALL PASS (C3=PASS, C4=PASS, C5=PASS, C6=PASS)

## Finding

Population-extension profile over 93 named sha256-pinned bundles (90 shipped-slice + 3 packet-of-record 39319405429): 41 D2_letterhead_zone rows collapse into 2 distinct letterhead pattern(s) (P1_OFFSET0_MULTILINE_COURT_HEADER). Slice verified rows 77 (72 defective); packet-of-record verified rows 0 under the frozen predicate (accepted requirement 36/42 expectation: 0 on served bytes - labelled, not an error).

## Letterhead pattern inventory

D2 rows profiled: 41 — distinct patterns: 2

### pattern `9000e8885f099066…` — P1_OFFSET0_MULTILINE_COURT_HEADER

- n_rows: 36; languages: ['de']
- decisions: ['gr_gerichte_ERZ 2010 25']
- bundles (36): `results/product/offline_slice/20261020T172114Z/rent-default.bundle.json`, `results/product/offline_slice/20261021T021147Z/rent-default.bundle.json`, `results/product/offline_slice/20261021T033430Z/rent-default.bundle.json`, `results/product/offline_slice/20261021T043137Z/rent-default.bundle.json`, `results/product/offline_slice/20261021T043531Z/rent-default.bundle.json`, `results/product/offline_slice/20261021T201333Z/rent-default.bundle.json`, `results/product/offline_slice/20261022T104548Z/rent-default.bundle.json`, `results/product/offline_slice/20261022T105527Z/rent-default.bundle.json` …
- families: ['offline_accept_40025340938', 'offline_accept_40032389983', 'offline_latest_20261024T024341Z', 'offline_slice_other_20261020T172114Z', 'offline_slice_other_20261021T021147Z', 'offline_slice_other_20261021T033430Z', 'offline_slice_other_20261021T043137Z', 'offline_slice_other_20261021T043531Z', 'offline_slice_other_20261021T201333Z', 'offline_slice_other_20261022T104548Z', 'offline_slice_other_20261022T105527Z', 'offline_slice_other_20261022T142043Z', 'offline_slice_other_20261022T165438Z', 'offline_slice_other_20261022T170046Z', 'offline_slice_other_20261022T211706Z', 'offline_slice_other_20261022T212101Z', 'offline_slice_other_20261022T212152Z', 'offline_slice_other_20261023T004550Z', 'offline_slice_other_20261023T012737Z', 'offline_slice_other_20261023T041949Z', 'offline_slice_other_20261023T061232Z', 'offline_slice_other_20261023T074335Z', 'offline_slice_other_20261023T120954Z', 'offline_slice_other_20261023T125701Z', 'offline_slice_other_20261023T132709Z', 'offline_slice_other_20261023T140339Z', 'offline_slice_other_20261023T150834Z', 'offline_slice_other_20261023T_warm_verify', 'prior_cycle_control']
- full_text offsets: [0]
- line structure: 4 lines, lengths [29, 32, 32, 24]
- evidence preview: 'Kantonsgericht von Graubünden Dretgira chantunala dal Grischun Tribunale cantonale dei Grigioni ________________________'
- reachability: ['fixture_bypass_only (emitted on the fixture path: product/offline_slice.py fixture_generation=True gates the span seam at product/query/pipeline.py:1339; the filter never runs). Per accepted PATH_SCOPE_RESIDUAL ARM2 (40070818687) the unmodified filter would ABSTAIN pivot_absent on the known offset-0 trilingual header if routed - cited, not re-run.']
- defect classes on these rows: {'D2_letterhead_zone': 36}

### pattern `41a185c481e9d493…` — P1_OFFSET0_MULTILINE_COURT_HEADER

- n_rows: 5; languages: ['de']
- decisions: ['bge_BGE_110_II_391']
- bundles (5): `results/product/offline_slice/20261018T095434Z/business-judgment-rule.bundle.json`, `results/product/offline_slice/20261018T095500Z/business-judgment-rule.bundle.json`, `results/product/offline_slice/20261018T101000Z/business-judgment-rule.bundle.json`, `results/product/offline_slice/20261019T145002Z/business-judgment-rule.bundle.json`, `results/product/offline_slice/20261023T121515Z/business-judgment-rule.bundle.json`
- families: ['offline_slice_other_20261018T095434Z', 'offline_slice_other_20261018T095500Z', 'offline_slice_other_20261018T101000Z', 'offline_slice_other_20261019T145002Z', 'offline_slice_other_20261023T121515Z']
- full_text offsets: [0]
- line structure: 3 lines, lengths [11, 10, 97]
- evidence preview: 'Urteilskopf 110 II 391 75. Auszug aus dem Urteil der I. Zivilabteilung vom 10. April 1984 i.S. X. gegen Immorest AG (Ber'
- reachability: ['fixture_bypass_only (emitted on the fixture path: product/offline_slice.py fixture_generation=True gates the span seam at product/query/pipeline.py:1339; the filter never runs). Per accepted PATH_SCOPE_RESIDUAL ARM2 (40070818687) the unmodified filter would ABSTAIN pivot_absent on the known offset-0 trilingual header if routed - cited, not re-run.']
- defect classes on these rows: {'D2_letterhead_zone': 5}

## Detectability summary

- P1 offset-0 multi-line court headers: 2
- P2 mid-document headers: 0
- P3 other letterhead-zone forms: 0

## Feasibility reading for Core Product (descriptive, claim ceiling)

All observed D2 letterhead forms fall into the mechanically detectable classes (P1/P2). On this named population the deterministic letterhead-filter branch remains mechanically viable; reachability remains fixture_bypass_only for slice rows and the ARM2 abstention finding (pivot_absent on the known offset-0 trilingual header when routed) still binds the filter's own detector — product's P0 repair must fix BOTH legs per v67.

## Posture

Both DO-NOT-SERVE orders stand; admission stays fail-closed (PACKET_ADMITTED=FALSE, MACHINE_GATE_READY=FALSE, HUMAN_GATE_READY=FALSE, READY_FOR_OWNER_SESSION=FALSE); comparative map-versus-ranked-list stays VACUOUS; owner_decision_required=false; no frozen bar, rubric, threshold or verdict contract was edited; no 174k benchmark was rerun.
