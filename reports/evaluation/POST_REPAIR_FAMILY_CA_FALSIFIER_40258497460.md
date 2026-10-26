# Post-repair family precondition gate + CA falsifier — run 40258497460

- Falsifier verdict: **SOUND_COUNTER_ROW_PRESENT** (exit 0), falsification_proven=False
- Ordered item (2) precondition (a) rejection/incumbent leg: **LANDED**
- Ordered item (2) precondition (b) full flagship family regenerated: **False**
- Ordered item (2) full protocol status: **NOT_YET_DISCRIMINATING (ordered item (2) protocol not executed: member-for-member regeneration of the named frozen family is 14/15; no synthetic stand-in is substituted, d2_path_scope_probe is not re-run as the ordered re-measure, packet-of-record 39319405429 is not scored and the standing falsification is not re-run)**
- Direction: v68
- Product mount head: `5fb312e4a71c99dce0ed6fbd2d3fce9a88ad6e68` (accepted cycle 40247189361)

**Freeze-ordering provenance.** The freeze record's `freeze_recorded_at_utc` field reads `2026-10-26T02:31:00Z` because of a generator-clock typo. The actual freeze commit is `3b36f3eb69c3950669d8ed9980f927baac63411f` at `2026-10-26T02:28:46Z`, five seconds before this record's `generated_at_utc` (`2026-10-26T02:28:51Z`). The frozen bytes were not edited after execution: this record pins the freeze sha `984a616981ba4a2c5ae3e04106901b9bdfbebe63ce3ff752361555f89630e5cb`. The commit timestamp, not the typo'd field, proves freeze-first ordering.

## 1. Precondition set relation (requirement 16: sets, never cardinalities)

- Frozen probe family members: 15
- Post-repair bundles found: 49
- Intersection by path: 0 (path identity is expected to be 0 while the baseline is preserved)
- Frozen-family-only (missing post-repair counterpart): 15
- Post-repair-only (roles absent from the frozen family): 49
- Member-for-member regeneration: 14/15 ({"offline/business-judgment-rule": 0, "offline/corporate-criminal-liability": 0, "offline/petty-theft-dismissal": 0, "offline/rent-default": 11, "server/served": 3})
- Every frozen role has a post-repair bundle: True; per-role multiplicity parity: False
- Roles frozen family: `{"offline/rent-default": 11, "server/served": 4}`
- Roles post-repair: `{"offline/business-judgment-rule": 10, "offline/corporate-criminal-liability": 9, "offline/petty-theft-dismissal": 9, "offline/rent-default": 18, "server/served": 3}`

### Product's own family claim

- Claim: "Full flagship offline/server slice family (4 offline + 1 server) regenerated with fix; 49 fixed-path bundles / 4,900 decisions / 55 verified / 0 verified+defective; ordered_work_2_full_success_rule.met = true"
- Source: reports/product/CYCLE_40247189361.md §3 and /tmp/lex_accepted/product/results/product/counter_content_family/CYCLE_40247189361.json, read at freeze time; product's own claim, not this run's measurement
- Product's claimed family (4 offline query bundles + 1 server bundle) and the direction's named family (the frozen 15-member probe family: 11 offline rent-default + 4 server served) are DIFFERENT SETS. Member-for-member regeneration of the named family is 14/15; every frozen role has a post-repair bundle=True; per-role multiplicity parity=False; Product's own 4+1 claim is satisfied by the present bytes=True. Both readings are published; neither is silently preferred, and no 'all of the family' claim is made from a cardinality.

### Leg markers (file:line at mount head)

- file: `product/query/counter_evidence_span.py` sha256 `82cea13122b13a60e4da746072af4a185f9e4b2e0ef51853d6273acb7a1bb6ce`
- `_content_rejection_sweep`: found=True lines=[809, 903, 1033]
- `n_incumbent_downgraded`: found=True lines=[915, 1035, 1068]
- `REJECTION/INCUMBENT`: found=True lines=[899, 965]
- `Content quality filter`: found=True lines=[385, 450, 1077]

## 2. Falsifier on the post-repair bytes

| bundle | family | enriched | n_dec | surface n_issued | verified scored | defective | sound |
|---|---|---|---|---|---|---|---|
| offline_rent_default_20261024T185212Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_rent_default_20261024T185255Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_petty_theft_dismissal_20261024T185257Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_corporate_criminal_liability_20261024T185300Z | offline_slice | True | 100 | 1 | 1 | 0 | 1 |
| offline_business_judgment_rule_20261024T185303Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_rent_default_20261024T235221Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_rent_default_20261025T004717Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_rent_default_20261025T005703Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_business_judgment_rule_20261025T010046Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_petty_theft_dismissal_20261025T010052Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_corporate_criminal_liability_20261025T010108Z | offline_slice | True | 100 | 1 | 1 | 0 | 1 |
| offline_rent_default_20261025T015155Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_rent_default_20261025T031500Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_petty_theft_dismissal_20261025T033046Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_corporate_criminal_liability_20261025T033055Z | offline_slice | True | 100 | 1 | 1 | 0 | 1 |
| offline_rent_default_20261025T035854Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_business_judgment_rule_20261025T040208Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_petty_theft_dismissal_20261025T040216Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_corporate_criminal_liability_20261025T040222Z | offline_slice | True | 100 | 1 | 1 | 0 | 1 |
| offline_rent_default_20261025T045400Z | offline_slice | True | 100 | 3 | 2 | 0 | 2 |
| offline_business_judgment_rule_20261025T045404Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_petty_theft_dismissal_20261025T045412Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_corporate_criminal_liability_20261025T045414Z | offline_slice | True | 100 | 6 | 6 | 0 | 6 |
| offline_rent_default_20261025T070356Z | offline_slice | True | 100 | 3 | 2 | 0 | 2 |
| offline_petty_theft_dismissal_20261025T070400Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_corporate_criminal_liability_20261025T070402Z | offline_slice | True | 100 | 6 | 6 | 0 | 6 |
| offline_business_judgment_rule_20261025T070406Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_rent_default_20261025T152238Z | offline_slice | True | 100 | 3 | 2 | 0 | 2 |
| offline_rent_default_20261025T174808Z | offline_slice | True | 100 | 3 | 2 | 0 | 2 |
| offline_rent_default_20261025T181726Z | offline_slice | True | 100 | 3 | 2 | 0 | 2 |
| offline_business_judgment_rule_20261025T181736Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_rent_default_20261025T182837Z | offline_slice | True | 100 | 3 | 2 | 0 | 2 |
| offline_business_judgment_rule_20261025T182847Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_rent_default_20261025T195050Z | offline_slice | True | 100 | 3 | 2 | 0 | 2 |
| offline_petty_theft_dismissal_20261025T195059Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_corporate_criminal_liability_20261025T195106Z | offline_slice | True | 100 | 6 | 6 | 0 | 6 |
| offline_business_judgment_rule_20261025T195114Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_rent_default_20261025T204600Z | offline_slice | True | 100 | 3 | 2 | 0 | 2 |
| offline_petty_theft_dismissal_20261025T204610Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_corporate_criminal_liability_20261025T204620Z | offline_slice | True | 100 | 6 | 6 | 0 | 6 |
| offline_business_judgment_rule_20261025T204630Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_rent_default_20261025T205046Z | offline_slice | True | 100 | 3 | 2 | 0 | 2 |
| offline_business_judgment_rule_40247189361-business-judgment-rule | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_corporate_criminal_liability_40247189361-corporate-criminal-liability | offline_slice | True | 100 | 6 | 6 | 0 | 6 |
| offline_petty_theft_dismissal_40247189361-petty-theft-dismissal | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_rent_default_40247189361-rent-default | offline_slice | True | 100 | 4 | 3 | 0 | 3 |
| server_served_20261024T185740Z | server_slice | True | 100 | 1 | 0 | 0 | 0 |
| server_served_40143042888 | server_slice | True | 100 | 1 | 0 | 0 | 0 |
| server_served_40247189361 | server_slice | True | 100 | 1 | 0 | 0 | 0 |
| control_not_enriched_server_first_page_40247189361 | server_slice | False | 100 | 0 | 0 | 0 | 0 |

- Defect histogram (post-repair): `{}`
- Distinct defective decision ids: []
- BEFORE 40105794124: `{"D2_letterhead_zone": 2, "D3_markup_residue": 2, "D4_language_marker_mismatch": 1}`
- BEFORE 40062917685: `{"D2_letterhead_zone": 10, "D3_markup_residue": 4, "D4_language_marker_mismatch": 4}`

### Standing surface-gate result and BEFORE/AFTER caveats (negative/partial, not hidden)

- **Surface gate `n_issued == 1` is FALSE on 15/49 enriched bundles.** Those 15 bundles issue 3, 4 or 6 counter-authority rows (`offline_rent_default_20261025T045400Z`, `...070356Z`, `...152238Z`, `...174808Z`, `...181726Z`, `...182837Z`, `...195050Z`, `...204600Z`, `...205046Z`, the `40247189361-rent-default` bundle, and five `corporate-criminal-liability` bundles). Every one of the 49 bundles has 0 empty-evidence rows, 0 missing decision IDs/URLs and 0 duplicate decision IDs. The `n_issued == 1` clause is a standing-falsifier invariant calibrated on the earlier 7-bundle population; it is not a content-defect signal. Under the frozen verdict rule it cannot promote SOUND and does not block SOUND, but it does block any claim that the whole 49-bundle family passes the standing surface gate. No such claim is made.
- **BEFORE/AFTER is NOT a paired comparison.** The BEFORE baselines (40105794124: 2/2/1 over 5 verified rows; 40062917685: 10/4/4 over 14 verified rows) are on older, byte-frozen bundles. The AFTER histogram `{}` is on the 49 NEW post-repair bundles. The 15-member baseline family is byte-identical and was NOT re-scored here; the benchmark-of-record 4 defective verified rows remain exactly as accepted. What is new is that the new post-repair bytes carry 55 verified rows and 0 frozen-predicate defects, not that the old defective rows were repaired in place.
- **Independent corroboration, not adoption:** the 49 selected paths are set-identical to Product's `results/product/counter_content_family/CYCLE_40247189361.json` fixed_path_family, and this run's per-bundle `n_counter_evidence_verified_scored_rows` / `n_defective_verified_scored_rows` match Product's `n_verified` / `n_verified_defective` on all 49 bundles (55/0 totals). Product's totals are reported as a consistency check; the measurement is this run's frozen D1-D4 classification.

## 3. Product-facing success criteria (REPORT-ONLY, never a frozen bar)

- defect_histogram_zero: **True**
- defect_histogram: **{}**
- sound_row_preserved: **True**
- zero_false_rejects: **True**
- path_scope_residual_cleared: **True**
- note: **REPORT-ONLY product-facing success criteria from v68 ordered item (2), computed and published, NEVER scored as a frozen bar and NEVER able to move one.**

## 4. False-reject and PATH_SCOPE sweeps

- Downgrade records inspected: 40
- False rejects: 0 (zero_false_rejects=True)
- PATH_SCOPE_RESIDUAL rows: 0 (cleared=True)
- Sound row bstger_SK.2023.49 preserved: **True**

## 5. Controls and pins

- C1_frozen_predicate_instrument_sha: holds=True
- C2_clean_synthetic_row_must_pass: holds=True
- C3_blanked_synthetic_row_must_fail: holds=True
- C4_empty_bundle_must_have_zero_issued: holds=True
- pins before: True; pins after: True
- numeric environment: `{"numpy": "NOT_IMPORTABLE", "platform": "Linux-6.17.0-1022-azure-x86_64-with-glibc2.39", "python": "3.12.3", "scipy": "NOT_IMPORTABLE", "sklearn": "NOT_IMPORTABLE", "thread_env": {"MKL_NUM_THREADS": null, "OMP_NUM_THREADS": null, "OPENBLAS_NUM_THREADS": null}}`

## 6. Ordered-work status and claim ceiling

- item_1_correction_of_record: DISCHARGED (accepted cycle 40133253347, gate PASS with NON-BLOCKING CC6/CC7 mount-history note)
- item_2_conditional_remeasure: NOT_YET_DISCRIMINATING (ordered item (2) protocol not executed: member-for-member regeneration of the named frozen family is 14/15; no synthetic stand-in is substituted, d2_path_scope_probe is not re-run as the ordered re-measure, packet-of-record 39319405429 is not scored and the standing falsification is not re-run)
- item_2_leg_half: LANDED
- item_3_standing_falsification_record: UNCHANGED; benchmark of record PRODUCT_FALSIFIED on packet-of-record 39319405429 still stands and is superseded only by a NEW pre-registered falsification on NEW bytes
- item_4_non_blocking_required_fixes_of_CYCLE_39965089504: reported wherever this lane quotes those counts: D1 wording 6-vs-7 tests, D2 wording new-vs-appended test file, D3 environment skip variance 172/1309/20 vs 172/1308/21 - all non-blocking, gate PASS

Two narrowly scoped things only: (1) a SET-RELATION re-adjudication of the v68 item-(2) precondition against the CURRENT committed product bytes (leg markers with file:line, post-repair bundle inventory, frozen-15-member-family coverage, Product's own family claim); (2) a NEW pre-registered FAST-MVP counter-authority falsification on the CURRENT post-repair bundle bytes, reusing the frozen D1-D4 predicates and the accepted relation engine BY HASH-VERIFIED IMPORT. It (a) does NOT discharge ordered item (2) unless the frozen 15-member family is member-for-member regenerated; (b) does NOT re-run, replace, weaken or move the benchmark of record PRODUCT_FALSIFIED on packet-of-record 39319405429, which is NOT read for scoring here; (c) does NOT re-run d2_path_scope_probe as the ordered item-(2) re-measure; (d) edits NO frozen bar, rubric, threshold, predicate, tokeniser, stoplist or verdict contract; (e) issues NO serve verdict, lifts NO DO-NOT-SERVE order, admits NO packet; (f) makes NO claim that the map helps a jurist; (g) runs NO universal-174k benchmark; (h) makes NO recall claim against a live baseline. Posture stays fail-closed: packet_admitted=false, machine_gate_ready=false, human_gate_ready=false, ready_for_owner_session=false, owner_decision_required=false.

- Posture: packet_admitted=false, machine_gate_ready=false, human_gate_ready=false, ready_for_owner_session=false, owner_decision_required=false.

