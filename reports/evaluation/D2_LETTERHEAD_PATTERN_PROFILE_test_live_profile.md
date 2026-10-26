# D2 Letterhead Pattern Heterogeneity Profile — 40246705199

- run_id: 40246705199
- producing commit: `0deec9ddcaf631a56045e06154dfb1d93d301741` (clean worktree at execution: True) — the tree the instrument ran on; this report and `results/evaluation/d2_letterhead_pattern_profile/40246705199.json` are committed in the follow-up commit whose message names run 40246705199
- direction_version: 68 — v68 is the CONTROLLING mounted control-plane direction; scope = **OPERATIONAL_POPULATION_EXTENSION_NO_ORDERED_ITEM_DISCHARGED** (v68 ordered item (5): a further cycle that repeats the D2 profile is zero delta and is recorded as OPERATIONAL, not as evidence) — accepted baseline 40062917685 UNMOVED
- product mount: `/tmp/lex_eval_mount_3de8431d` head `3de8431d46bfe757469720682253e63f0d763c4b`
- packet-of-record: 39319405429 (labelled; verified rows under frozen predicate: 0)
- verdict: **LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED** (exit 0)
- controls: ALL PASS (C3=PASS, C4=PASS, C5=PASS, C7=PASS, C6=PASS)

## Ordered-item status (direction v68)

- item (1) report-only correction of record: DISCHARGED_ELSEWHERE - accepted in the base tree as reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md; not re-derived here
- item (2) conditional re-measure: **NOT_YET_DISCRIMINATING** — the rejection/incumbent leg IS landed at the pinned head 3de8431d (product/query/counter_evidence_span.py:385-394 present; measured content_filter payload on 44 bundles of this population), BUT the 15-bundle flagship family pinned in results/evaluation/counter_evidence_quality_benchmark/40062917685.json (all 20261023T2* dirs) has NOT been regenerated at a rejection-leg head - the newest slice dirs are single-query bundles - so the precondition is UNMET and no re-measure, synthetic stand-in or standing-falsification rerun is executed
- item (3) standing falsification record: KEPT, unchanged, not re-run
- item (5) no zero-delta cycle: APPLIED HERE - recorded as OPERATIONAL

## Finding

Population-extension profile over 144 named sha256-pinned bundles (141 shipped-slice + 3 packet-of-record 39319405429): 44 D2_letterhead_zone rows collapse into 2 distinct letterhead pattern(s) (P1_OFFSET0_MULTILINE_COURT_HEADER). Slice verified rows 126 (75 defective); packet-of-record verified rows 0 under the frozen predicate (accepted requirement 36/42 expectation: 0 on served bytes - labelled, not an error).

## Letterhead pattern inventory

D2 rows profiled: 44 — distinct patterns: 2

### pattern `9000e8885f099066…` — P1_OFFSET0_MULTILINE_COURT_HEADER

- n_rows: 39; languages: ['de']
- decisions: ['gr_gerichte_ERZ 2010 25']
- bundles (39): `results/product/offline_slice/20261020T172114Z/rent-default.bundle.json`, `results/product/offline_slice/20261021T021147Z/rent-default.bundle.json`, `results/product/offline_slice/20261021T033430Z/rent-default.bundle.json`, `results/product/offline_slice/20261021T043137Z/rent-default.bundle.json`, `results/product/offline_slice/20261021T043531Z/rent-default.bundle.json`, `results/product/offline_slice/20261021T201333Z/rent-default.bundle.json`, `results/product/offline_slice/20261022T104548Z/rent-default.bundle.json`, `results/product/offline_slice/20261022T105527Z/rent-default.bundle.json` …
- families: ['offline_accept_40025340938', 'offline_accept_40032389983', 'offline_slice_other_20261020T172114Z', 'offline_slice_other_20261021T021147Z', 'offline_slice_other_20261021T033430Z', 'offline_slice_other_20261021T043137Z', 'offline_slice_other_20261021T043531Z', 'offline_slice_other_20261021T201333Z', 'offline_slice_other_20261022T104548Z', 'offline_slice_other_20261022T105527Z', 'offline_slice_other_20261022T142043Z', 'offline_slice_other_20261022T165438Z', 'offline_slice_other_20261022T170046Z', 'offline_slice_other_20261022T211706Z', 'offline_slice_other_20261022T212101Z', 'offline_slice_other_20261022T212152Z', 'offline_slice_other_20261023T004550Z', 'offline_slice_other_20261023T012737Z', 'offline_slice_other_20261023T041949Z', 'offline_slice_other_20261023T061232Z', 'offline_slice_other_20261023T074335Z', 'offline_slice_other_20261023T120954Z', 'offline_slice_other_20261023T125701Z', 'offline_slice_other_20261023T132709Z', 'offline_slice_other_20261023T140339Z', 'offline_slice_other_20261023T150834Z', 'offline_slice_other_20261023T_warm_verify', 'offline_slice_other_20261024T024341Z', 'offline_slice_other_20261024T123044Z', 'offline_slice_other_20261024T130306Z', 'offline_slice_other_20261024T142517Z', 'prior_cycle_control']
- full_text offsets: [0]
- line structure: 4 lines, lengths [29, 32, 32, 24]
- evidence preview: 'Kantonsgericht von Graubünden Dretgira chantunala dal Grischun Tribunale cantonale dei Grigioni ________________________'
- reachability (MEASURED): ['span_provenance_absent MEASURED on this bundle at product head 3de8431d46bfe757469720682253e63f0d763c4b: no provenance.counter_evidence_span payload is committed on these bytes, so seam reachability is NOT MEASURED here (bundle predates the seam; absence is reported as absence, never inferred as a bypass). Seam call product/query/pipeline.py:1400-1407 is gated only on `if adversarial_retrieval:` ("Run even in fixture mode so the shipped offline/slice path exercises the filter."); the `if not fixture_generation:` at product/query/pipeline.py:1408 guards apply_counter_emission_repair ONLY. The pre-51d306c fixture-bypass reachability clause is SUPERSEDED AS EXPLANATION (supersession block in this artifact; correction of record reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md). Per accepted PATH_SCOPE_RESIDUAL ARM2 (40070818687) the unmodified filter would ABSTAIN pivot_absent on the known offset-0 trilingual header if routed - cited, not re-run.', 'span_seam_applied MEASURED on this bundle at product head 3de8431d46bfe757469720682253e63f0d763c4b: provenance.counter_evidence_span applied=true, n_candidates=1, n_selected=0, abstained_ids=[\'gr_gerichte_ERZ 2010 25\'], abstention_reasons={\'pivot_absent\': 1}. Seam call product/query/pipeline.py:1400-1407 is gated only on `if adversarial_retrieval:` ("Run even in fixture mode so the shipped offline/slice path exercises the filter."); the `if not fixture_generation:` at product/query/pipeline.py:1408 guards apply_counter_emission_repair ONLY. The pre-51d306c fixture-bypass reachability clause is SUPERSEDED AS EXPLANATION (supersession block in this artifact; correction of record reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md). Per accepted PATH_SCOPE_RESIDUAL ARM2 (40070818687) the unmodified filter would ABSTAIN pivot_absent on the known offset-0 trilingual header if routed - cited, not re-run.']
- defect classes on these rows: {'D2_letterhead_zone': 39}

### pattern `41a185c481e9d493…` — P1_OFFSET0_MULTILINE_COURT_HEADER

- n_rows: 5; languages: ['de']
- decisions: ['bge_BGE_110_II_391']
- bundles (5): `results/product/offline_slice/20261018T095434Z/business-judgment-rule.bundle.json`, `results/product/offline_slice/20261018T095500Z/business-judgment-rule.bundle.json`, `results/product/offline_slice/20261018T101000Z/business-judgment-rule.bundle.json`, `results/product/offline_slice/20261019T145002Z/business-judgment-rule.bundle.json`, `results/product/offline_slice/20261023T121515Z/business-judgment-rule.bundle.json`
- families: ['offline_slice_other_20261018T095434Z', 'offline_slice_other_20261018T095500Z', 'offline_slice_other_20261018T101000Z', 'offline_slice_other_20261019T145002Z', 'offline_slice_other_20261023T121515Z']
- full_text offsets: [0]
- line structure: 3 lines, lengths [11, 10, 97]
- evidence preview: 'Urteilskopf 110 II 391 75. Auszug aus dem Urteil der I. Zivilabteilung vom 10. April 1984 i.S. X. gegen Immorest AG (Ber'
- reachability (MEASURED): ['span_provenance_absent MEASURED on this bundle at product head 3de8431d46bfe757469720682253e63f0d763c4b: no provenance.counter_evidence_span payload is committed on these bytes, so seam reachability is NOT MEASURED here (bundle predates the seam; absence is reported as absence, never inferred as a bypass). Seam call product/query/pipeline.py:1400-1407 is gated only on `if adversarial_retrieval:` ("Run even in fixture mode so the shipped offline/slice path exercises the filter."); the `if not fixture_generation:` at product/query/pipeline.py:1408 guards apply_counter_emission_repair ONLY. The pre-51d306c fixture-bypass reachability clause is SUPERSEDED AS EXPLANATION (supersession block in this artifact; correction of record reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md). Per accepted PATH_SCOPE_RESIDUAL ARM2 (40070818687) the unmodified filter would ABSTAIN pivot_absent on the known offset-0 trilingual header if routed - cited, not re-run.']
- defect classes on these rows: {'D2_letterhead_zone': 5}

## Detectability summary

- P1 offset-0 multi-line court headers: 2
- P2 mid-document headers: 0
- P3 other letterhead-zone forms: 0

## Measured span-seam provenance (per bundle, at the pinned head)

- product head: `3de8431d46bfe757469720682253e63f0d763c4b`
- bundles: 144 — span_state_counts: `{'span_provenance_absent': 96, 'span_seam_applied': 40, 'span_seam_ran_applied_false': 8}`
- bundles with a committed provenance.counter_evidence_span payload: 48 (applied=true 40, applied=false 8, absent 96)
- bundles carrying the v68 rejection/incumbent-leg payload (content_filter present): 44
- summed provenance counters: n_candidates=40, n_selected=0, n_downgraded=36
- abstained_ids: `{'bge_BGE_110_II_391': 9, 'bge_BGE_121_III_260': 2, 'bstger_SK.2023.49': 8, 'gr_gerichte_ERZ 2010 25': 21}`; abstention_reasons: `{'no_intent_marker': 2, 'pivot_absent': 38}`
- D2 profiled rows by span state: `{'span_provenance_absent': 42, 'span_seam_applied': 2}`
- scope caveat: counts are bundle-level provenance fields summed across the named population; they are descriptive seam telemetry, NOT a frozen-bar result and NOT a class-level repair verdict

## Supersession of the pre-51d306c reachability clause

- status: **SUPERSEDED_AS_EXPLANATION**
- superseded clause (by reference): the pre-51d306c fixture-bypass reachability clause that earlier runs of this instrument published as current state for slice-family D2 rows (the wording that blamed a fixture-only gate on the span seam)
- published by (left byte-untouched, F-3B disposition item 4): `results/evaluation/d2_letterhead_pattern_profile/40089391202.json`, `results/evaluation/d2_letterhead_pattern_profile/40094203248.json`, `results/evaluation/d2_letterhead_pattern_profile/40096174340.json`, `results/evaluation/d2_letterhead_pattern_profile/40099481633.json`, `results/evaluation/d2_letterhead_pattern_profile/test_live_profile.json`
- disposition: those five artifacts are NAMED RUN artifacts and are left byte-untouched per the binding F-3B disposition item 4 (a file named for run X holds run X's measurement; nothing is deleted from history). The clause they carry is superseded here and in the dedicated correction note rather than by editing them.
- superseding note: `reports/evaluation/D2_REACHABILITY_CLAUSE_SUPERSESSION_OF_RECORD_40246705199.md`
- correction of record: `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md`
- product citation (span_seam_call): product/query/pipeline.py:1400-1407 - `if adversarial_retrieval:` -> apply_verified_span_selection, in-code comment "Run even in fixture mode so the shipped offline/slice path exercises the filter."
- product citation (fixture_gate): product/query/pipeline.py:1408 - `if not fixture_generation:` guards apply_counter_emission_repair ONLY, never the span seam
- product citation (rejection_incumbent_leg): product/query/counter_evidence_span.py:385-394 - direction v68 P0 rejection/incumbent leg ("REPLACE it (direction v68 P0 rejection/incumbent leg)")
- product citation (correction_of_record): reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md
- measurement unchanged: supersession is provenance/mechanism only; every measurement number in this artifact is unchanged from the pinned-head measurement of record

## Feasibility reading for Core Product (descriptive, claim ceiling)

All observed D2 letterhead forms fall into the mechanically detectable classes (P1/P2). On this named population the deterministic letterhead-filter branch remains mechanically viable. Reachability is MEASURED on these very bytes, not assumed: 40 of 144 bundles carry provenance.counter_evidence_span.applied=true and 44 carry the rejection/incumbent-leg payload, so the pre-51d306c fixture-bypass clause is SUPERSEDED as explanation (supersession section above). The ARM2 abstention finding (pivot_absent on the known offset-0 trilingual header when routed) still binds the filter's own detector. This lane asserts no repair requirement of its own: rejection/incumbent handling is Core Product's ordered work under direction v68, and ordered item (2) stays NOT_YET_DISCRIMINATING until the pinned 15-bundle flagship family is regenerated at a rejection-leg head.

## Posture

Both DO-NOT-SERVE orders stand; admission stays fail-closed (PACKET_ADMITTED=FALSE, MACHINE_GATE_READY=FALSE, HUMAN_GATE_READY=FALSE, READY_FOR_OWNER_SESSION=FALSE); comparative map-versus-ranked-list stays VACUOUS; owner_decision_required=false; no frozen bar, rubric, threshold or verdict contract was edited; no 174k benchmark was rerun.
