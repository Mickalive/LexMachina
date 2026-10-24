# Post-repair family precondition gate + CA falsifier — run 40134202991

- Falsifier verdict: **SOUND_COUNTER_ROW_PRESENT** (exit 0), falsification_proven=False
- Ordered item (2) precondition (a) rejection/incumbent leg: **LANDED**
- Ordered item (2) precondition (b) full flagship family regenerated: **False**
- Ordered item (2) full protocol status: **NOT_YET_DISCRIMINATING (ordered item (2) protocol not executed: member-for-member regeneration of the named frozen family is 3/15; no synthetic stand-in is substituted, d2_path_scope_probe is not re-run as the ordered re-measure, packet-of-record 39319405429 is not scored and the standing falsification is not re-run)**
- Direction: v68
- Product mount head: `8e58724bcd3382c5cf533e81cb8b6a8cbced4199` (accepted cycle 40128639259)

## 1. Precondition set relation (requirement 16: sets, never cardinalities)

- Frozen probe family members: 15
- Post-repair bundles found: 6
- Intersection by path: 0 (path identity is expected to be 0 while the baseline is preserved)
- Frozen-family-only (missing post-repair counterpart): 15
- Post-repair-only (roles absent from the frozen family): 6
- Member-for-member regeneration: 3/15 ({"offline/business-judgment-rule": 0, "offline/corporate-criminal-liability": 0, "offline/petty-theft-dismissal": 0, "offline/rent-default": 2, "server/served": 1})
- Every frozen role has a post-repair bundle: True; per-role multiplicity parity: False
- Roles frozen family: `{"offline/rent-default": 11, "server/served": 4}`
- Roles post-repair: `{"offline/business-judgment-rule": 1, "offline/corporate-criminal-liability": 1, "offline/petty-theft-dismissal": 1, "offline/rent-default": 2, "server/served": 1}`

### Product's own family claim

- Claim: "Full flagship offline/server slice family (4 offline + 1 server) regenerated with fix"
- Source: /tmp/lex_accepted/product/state/product.json (v68 next_recommendation block), read at freeze time
- Product's claimed family (4 offline query bundles + 1 server bundle) and the direction's named family (the frozen 15-member probe family: 11 offline rent-default + 4 server served) are DIFFERENT SETS. Member-for-member regeneration of the named family is 3/15; every frozen role has a post-repair bundle=True; per-role multiplicity parity=False; Product's own 4+1 claim is satisfied by the present bytes=True. Both readings are published; neither is silently preferred, and no 'all of the family' claim is made from a cardinality.

### Leg markers (file:line at mount head)

- file: `product/query/counter_evidence_span.py` sha256 `b749e43556874d5dfe7966a40205a81dd3c1345c6f352bca6f3e0e72e97873a1`
- `_content_rejection_sweep`: found=True lines=[513, 607, 737]
- `n_incumbent_downgraded`: found=True lines=[619, 739, 772]
- `REJECTION/INCUMBENT`: found=True lines=[603, 669]
- `Content quality filter`: found=True lines=[385, 450, 781]

## 2. Falsifier on the post-repair bytes

| bundle | family | enriched | n_dec | surface n_issued | verified scored | defective | sound |
|---|---|---|---|---|---|---|---|
| offline_rent_default_20261024T185212Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_rent_default_20261024T185255Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_petty_theft_20261024T185257Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| offline_corporate_20261024T185300Z | offline_slice | True | 100 | 1 | 1 | 0 | 1 |
| offline_business_judgment_20261024T185303Z | offline_slice | True | 100 | 1 | 0 | 0 | 0 |
| server_served_20261024T185740Z | server_slice | True | 100 | 1 | 0 | 0 | 0 |
| server_first_page_20261024T185740Z | server_slice | False | 100 | 0 | 0 | 0 | 0 |

- Defect histogram (post-repair): `{}`
- Distinct defective decision ids: []
- BEFORE 40105794124: `{"D2_letterhead_zone": 2, "D3_markup_residue": 2, "D4_language_marker_mismatch": 1}`
- BEFORE 40062917685: `{"D2_letterhead_zone": 10, "D3_markup_residue": 4, "D4_language_marker_mismatch": 4}`

## 3. Product-facing success criteria (REPORT-ONLY, never a frozen bar)

- defect_histogram_zero: **True**
- defect_histogram: **{}**
- sound_row_preserved: **True**
- zero_false_rejects: **True**
- path_scope_residual_cleared: **True**
- note: **REPORT-ONLY product-facing success criteria from v68 ordered item (2), computed and published, NEVER scored as a frozen bar and NEVER able to move one.**

## 4. False-reject and PATH_SCOPE sweeps

- Downgrade records inspected: 5
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
- item_2_conditional_remeasure: NOT_YET_DISCRIMINATING (ordered item (2) protocol not executed: member-for-member regeneration of the named frozen family is 3/15; no synthetic stand-in is substituted, d2_path_scope_probe is not re-run as the ordered re-measure, packet-of-record 39319405429 is not scored and the standing falsification is not re-run)
- item_2_leg_half: LANDED
- item_3_standing_falsification_record: UNCHANGED; benchmark of record PRODUCT_FALSIFIED on packet-of-record 39319405429 still stands and is superseded only by a NEW pre-registered falsification on NEW bytes
- item_4_non_blocking_required_fixes_of_CYCLE_39965089504: reported wherever this lane quotes those counts: D1 wording 6-vs-7 tests, D2 wording new-vs-appended test file, D3 environment skip variance 172/1309/20 vs 172/1308/21 - all non-blocking, gate PASS

Two narrowly scoped things only: (1) a SET-RELATION adjudication of the v68 item-(2) precondition against committed product bytes (leg markers with file:line, post-repair bundle inventory, frozen-probe-family coverage, Product's own family claim); (2) a NEW pre-registered FAST-MVP counter-authority falsification on the NEW post-repair bundle bytes, reusing the frozen D1-D4 predicates and the accepted relation engine BY HASH-VERIFIED IMPORT. It (a) does NOT discharge ordered item (2): the frozen 15-member probe family is the named family and this run reports its coverage, it does not silently substitute a different family; (b) does NOT re-run, replace, weaken or move the benchmark of record PRODUCT_FALSIFIED on packet-of-record 39319405429, which is NOT read for scoring here; (c) does NOT re-run d2_path_scope_probe as the ordered item-(2) re-measure; (d) edits NO frozen bar, rubric, threshold, predicate, tokeniser, stoplist or verdict contract; (e) issues NO serve verdict, lifts NO DO-NOT-SERVE order, admits NO packet; (f) makes NO claim that the map helps a jurist; (g) runs NO universal-174k benchmark; (h) makes NO recall claim against a live baseline. Posture stays fail-closed: packet_admitted=false, machine_gate_ready=false, human_gate_ready=false, ready_for_owner_session=false, owner_decision_required=false.

- Posture: packet_admitted=false, machine_gate_ready=false, human_gate_ready=false, ready_for_owner_session=false, owner_decision_required=false.

