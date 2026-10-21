# Parity-attribution repair — run 39631600439

- Repaired cycle: `39628161040` (audit gate `REVISE`)
- Required fixes complete: **True** (23/23 checks passed)
- V2 hypothesis sha256 `c994487886bf...`, V2 record sha256 `b8482edfd10b...`
- The FAIL verdict is **not** withdrawn; its **attribution** is corrected and machine-published.

## F1 — COMPLETE

*publish the per-(channel,language) comparator decomposition and the executed-text-only comparison for all 7 parity gates and restate the finding (the verdict may stand, the same-query-regression characterization may not)*

| check | holds | detail |
|---|---|---|
| `F1.decomposition_published_for_every_gated_cell` | yes | 8 (slug, kind) decomposition rows, each with the per-(channel, language) hit table, the executed-text-only comparison and the comparator-only id attribution |
| `F1.executed_text_only_comparison_for_all_7_parity_gates` | yes | 7 measurable same-text gates carry the executed-text-only comparison (product_hits vs comparator_hits) |
| `F1.comparator_only_ids_attributed_to_never_executed_texts` | yes | 18 comparator-only ids, 18 of them produced only by texts the product never executed |
| `F1.executed_text_comparison_never_below_product` | yes | on the executed text the product reaches >= the plain comparator in all 7 same-text cells (0/0, 1/0, 1/1, 0/0, 0/0, 0/0, 1/0) |
| `F1.verdict_still_fail_but_attributed_to_coverage` | yes | the FAIL verdict of the frozen success rule stands; the verdict_scope is coverage and the same-text family PASSes |
| `F1.restated_in_reports/evaluation/PRODUCT_CACHE_PARITY_39619144928.md` | yes | the finding is restated with the per-(channel, language) decomposition pointer and the honest characterization |
| `F1.restated_in_reports/evaluation/PRODUCT_CACHE_PARITY_39628161040.md` | yes | the finding is restated with the per-(channel, language) decomposition pointer and the honest characterization |
| `F1.restated_in_operational_resume_report` | yes | the operational-resume report carries the corrected attribution and preserves the superseded sentence verbatim |
| `F1.restated_in_state_note` | yes | state/evaluation.json product_cache_parity.note no longer claims a same-query retrieval-layer regression |
| `F1.decomposition_in_v2_report` | yes | the V2 report publishes the decomposition and the attribution table |

## F2 — COMPLETE

*do not ship a measurement that contradicts the frozen rule governing it: either restrict the primary comparator to the executed text or publish a versioned hypothesis with a new freeze record and a pre-freeze disclosure that makes the coverage asymmetry an explicit gated quantity*

| check | holds | detail |
|---|---|---|
| `F2.versioned_hypothesis_frozen_before_execution` | yes | V2 hypothesis + V2 freeze record exist, are versioned and are pinned by digest |
| `F2.pre_freeze_disclosure_present` | yes | the V2 hypothesis discloses in-file that it is a re-specification authored after the V1 outcome was observed, and states the expected outcome |
| `F2.coverage_asymmetry_is_an_explicit_gated_quantity` | yes | the gate list contains BOTH families: the like-for-like same-text family and the explicitly gated union-of-all-frozen-texts coverage family |
| `F2.frozen_rules_and_ids_unchanged` | yes | no new threshold, no changed id set, no changed matcher; the gated comparisons grow 7 -> 14 while the failing comparisons stay 7 |
| `F2.v1_chain_byte_preserved` | yes | the V1 hypothesis, the V1 freeze record and both V1 measurement records re-hash to the digests pinned by the V2 freeze record |
| `F2.v1_failures_not_downgraded` | yes | every V1 falsifier gate maps 1:1 onto a V2 coverage gate with identical measurements, and the same 7 comparisons still fail |

## F3 — COMPLETE

*add a synthetic case with a comparator pool containing texts the product never executed and assert that the gate cannot silently convert non-executed coverage into a same-text falsification*

| check | holds | detail |
|---|---|---|
| `F3.asymmetric_fixture_present` | yes | the synthetic fixture builds a comparator pool that contains a text the product never executed |
| `F3.asymmetric_test_executes_and_passes` | yes | the asymmetric-case test function ran and its assertions held |
| `F3.instrument_pins_the_asymmetry` | yes | the instrument's own non-vacuity battery carries the C3 control that re-scores the executed-text pool and forbids a same-text falsification |

## F4 — COMPLETE

*correct the disposition wording of the inherited team-authored files to 'preserved in this branch snapshot with digests recorded in the lane machine record, removed at promotion by the integrate step's audit-directory checkout'*

| check | holds | detail |
|---|---|---|
| `F4.record_disposition_corrected` | yes | every out-of-scope entry carries the corrected disposition wording |
| `F4.superseded_wording_preserved_verbatim` | yes | the superseded disposition string is preserved verbatim beside the correction (no deletion, no silent rewrite) |
| `F4.report_wording_corrected` | yes | the operational-resume report states the corrected disposition |
| `F4.state_wording_corrected` | yes | state/evaluation.json operational_resume.diagnosis states the corrected disposition |

## Lane-suite regression delta (supporting evidence, NOT an audit required fix)

- record: `results/evaluation/orchestration/39631600439_shim_regression.json` sha256 `871cb1d75f30...`
- baseline: pre-repair tree at commit ae039b9c (detached worktree)
- current: repair round 1 tree of run 39631600439
- verdict: **SHIM_NO_NEW_FAILURE** — new failures **0**, no longer failing **4**
- supporting evidence, NOT one of the four audit required fixes: the lane suite under the no-pytest shim is NOT green in this rejected branch snapshot and is not claimed to be. The delta against the pre-repair tree at commit ae039b9c is 0 new failures; the pre-existing failures stay visible as pre-existing failures and UNSUPPORTED / SKIPPED cases are counted as NOT-RUN, never as passes.

## First execution of this cycle (preserved)

- `results/evaluation/product_cache_parity/39631600439_first_execution.json` sha256 `5c744460d826...` — preserved verbatim.
- differing keys vs the re-executed record: `elapsed_s, generated_at_utc, v1_preservation`
- claim-bearing quantities identical: **True**
- the first execution of this cycle is preserved verbatim; the only differences to the re-executed record are the timestamp, the elapsed time and the strengthened v1_preservation proof (the V1 records of that cycle store hit COUNTS, the first execution compared only the keys they both carried, which made the proof vacuous for one of the two V1 records)

## Claim ceiling

This record proves only that the four required fixes of the independent audit of cycle 39628161040 are DISCHARGED and machine-checked against the committed artifacts: (F1) the per-(channel, language) comparator decomposition, the executed-text-only comparison for all 7 parity gates and the honest restatement of the finding are published, while the FAIL_PRODUCT_CACHE_PARITY verdict of the frozen success rule stands; (F2) the frozen-rule contradiction is removed by a versioned V2 hypothesis with its own freeze record and an in-file pre-freeze disclosure, with no new threshold, no changed id set, no changed matcher and the same 7 failing comparisons; (F3) the asymmetric synthetic case is executable and forbids a non-executed text's coverage from becoming a same-text falsification; (F4) the disposition wording of the inherited team-authored files is corrected, with the superseded wording preserved verbatim. It does NOT prove that the product's retrieval quality is worse than plain OpenCaseLaw on the text it ran (the like-for-like same-text family PASSes 7/7); it does NOT lift either DO-NOT-SERVE order, does NOT move the frozen absolute bars (REPORTED-ONLY), does NOT certify any packet, does NOT assert that any decision is supporting/contrary/limiting, and authorises NO owner question. This repair is NOT self-certified: an independent audit of THIS cycle is still owed and the evidence tier stays EXPLORATORY.

Machine record: `results/evaluation/repair_39628161040/39631600439_parity_attribution_repair.json`
