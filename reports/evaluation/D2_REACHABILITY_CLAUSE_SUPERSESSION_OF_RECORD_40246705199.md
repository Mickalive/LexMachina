# Supersession of record: pre-51d306c fixture-bypass reachability clause (cycle 40246705199 repair round 2)

- Direction: **v68** (controlling mounted control-plane direction), scope = `OPERATIONAL_POPULATION_EXTENSION_NO_ORDERED_ITEM_DISCHARGED`
- Repairs: evaluation cycle `40246705199` (gate REVISE, audit `required_fixes` **R1** false reachability/P0 claims, **R2** run artifact naming/traceability, **R3** direction pin + operational label + ordered item (2) status)
- Superseding artifact: `results/evaluation/d2_letterhead_pattern_profile/40246705199.json`
- Superseding report: `reports/evaluation/D2_LETTERHEAD_PATTERN_PROFILE_40246705199.md` and `reports/evaluation/D2_LETTERHEAD_PATTERN_PROFILE_test_live_profile.md` (same run, stamped content)
- Supersession is **explanation/provenance only**; no measurement number changes (see *Measurement unchanged* below)

## Status

`SUPERSEDED_AS_EXPLANATION`.

## The superseded clause (by reference)

The pre-51d306c fixture-bypass reachability clause that earlier runs of
`evaluation/d2_letterhead_pattern_profile.py` published as **current state**
for slice-family `D2_letterhead_zone` rows — the wording that blamed a
fixture-only gate on the span seam and asserted the filter was never reached
on the shipped slice path. Its three distinctive wordings, as they appeared in
the rejected artifact:

1. `pipeline.py:1339` (a line number that no longer names the seam call)
2. `the filter never runs` (the false reachability claim itself)
3. `BOTH legs per v67` (an asserted product repair requirement that this lane
   has no authority to publish)

## What published it (all left byte-untouched, per F-3B disposition item 4)

A file named for run X holds run X's measurement. Nothing below is edited,
rewritten, deleted or re-run:

| artifact | sha256 |
|---|---|
| `results/evaluation/d2_letterhead_pattern_profile/40089391202.json` | `f5fade6d11ebf14e3004d5beebf2f959444720fc3152e4e5b0b479a644d3cab7` |
| `results/evaluation/d2_letterhead_pattern_profile/40094203248.json` | `3253130ed64334bebf540c593cf24c4d1cc804850221bfdb6b650dc4a9cfca6b` |
| `results/evaluation/d2_letterhead_pattern_profile/40096174340.json` | `5821361694bcaf1ad1e3add25129e4a3b1cde1eb199b7261f85c619f17524ee9` |
| `results/evaluation/d2_letterhead_pattern_profile/40099481633.json` | `e914af08ddd54acbcd563a455e6ca1b8fe7cd62397b98ac06cab9da606da9cb6` |
| `results/evaluation/d2_letterhead_pattern_profile/test_live_profile.json` | `bd53b3b7d71fae6c9913e206570f68d082a690fca4c8d87fd249871fd797d1a8` |

Disposition: those five remain historical record of the runs they are named
for. The clause they carry is superseded here and by the instrument's
`supersession` block, never by editing them. New measurement = new run-id file.

## Corrected statement (measured, not asserted)

Reachability of the span seam on this population is **measured per bundle**
from each bundle's own committed `provenance.counter_evidence_span` payload at
the pinned product head, and published under
`population[].counter_evidence_span_provenance`, `span_state_counts` and
`d2_row_span_states`. Where a bundle carries no payload, that is published as
`span_provenance_absent` — **absence is reported as absence, never inferred as
a bypass**.

Measured over the 144-bundle named population at head
`3de8431d46bfe757469720682253e63f0d763c4b`:

- `span_provenance_absent = 96`
- `span_seam_applied = 40`
- `span_seam_ran_applied_false = 8`
- bundles carrying the v68 rejection/incumbent-leg payload (`content_filter`
  present) = **44**
- summed provenance telemetry: `n_candidates = 40`, `n_selected = 0`,
  `n_downgraded = 36`; `abstention_reasons = {pivot_absent: 38,
  no_intent_marker: 2}`
- D2 profiled rows by span state: `span_provenance_absent = 42`,
  `span_seam_applied = 2`

## Corrected product citations (file:line verified at the pinned head)

- **Seam call** — `product/query/pipeline.py:1400-1407`: the seam is invoked
  under `if adversarial_retrieval:` alone, with the in-code comment *"Run even
  in fixture mode so the shipped offline/slice path exercises the filter."*
- **Fixture gate** — `product/query/pipeline.py:1408`: `if not fixture_generation:`
  guards `apply_counter_emission_repair` **only**, never the span seam.
- **Rejection/incumbent leg** — `product/query/counter_evidence_span.py:385-394`:
  the direction v68 P0 rejection/incumbent leg (*"REPLACE it (direction v68 P0
  rejection/incumbent leg)"*), present at the pinned head.
- **Correction of record (upstream)** —
  `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md`.

The rejected artifact cited `pipeline.py:1339`, which does not name the seam
call at this head, and asserted `the filter never runs` on the fixture path;
both are false at `3de8431d` and are not restated as current anywhere in the
superseding artifact or report.

## Measurement unchanged (R1)

Supersession is provenance/mechanism only. Every number in the superseding
artifact is identical to the measurement of record:

- `n_bundles = 144` (`141` shipped-slice + `3` packet-of-record)
- `n_verified_rows_shipped_slice = 126`, `n_verified_with_defects = 75`
- `population_defect_histogram = {D2_letterhead_zone: 44, D3_markup_residue: 31,
  D4_language_marker_mismatch: 7}`
- `d2_rows_profiled = 44`, `n_distinct_letterhead_patterns = 2`
- 144/144 population sha256 pins identical to the pinned-head run of record
- `verdict = LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED`, controls all pass
- frozen instrument sha256 `aac86527e5e54f0f9c527daac7ff1016d5124731b8ce673797520ff3dd53067d`
  unchanged; no frozen bar, rubric, threshold or verdict contract edited; no
  174k benchmark rerun

## ARM2 retained, not re-run (R1)

The `pivot_absent` abstention finding remains **cited** from accepted cycle
`40070818687` (PATH_SCOPE_RESIDUAL ARM2) and is not re-executed here. The
superseding artifact's labels carry *"Per accepted PATH_SCOPE_RESIDUAL ARM2
(40070818687) the unmodified filter would ABSTAIN pivot_absent on the known
offset-0 trilingual header if routed — cited, not re-run."*

## Direction v68 status (R3)

- Item (1) report-only correction of record: **DISCHARGED_ELSEWHERE** —
  accepted in the base tree as
  `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md`.
- Item (2) conditional re-measure: **`NOT_YET_DISCRIMINATING`** — the
  rejection/incumbent leg IS landed at `3de8431d`, but the 15-bundle flagship
  family pinned in
  `results/evaluation/counter_evidence_quality_benchmark/40062917685.json`
  (all `20261023T2*` dirs) has not been regenerated at a rejection-leg head,
  so the precondition is unmet. No re-measure, no synthetic stand-in, no
  standing-falsification rerun is executed.
- Item (3) standing falsification record: **KEPT**, unchanged, not re-run.
- Item (5) no zero-delta cycle: **APPLIED HERE** — this run is labelled
  `OPERATIONAL_POPULATION_EXTENSION_NO_ORDERED_ITEM_DISCHARGED` and is
  recorded as operational, not as evidence.

**Claim ceiling:** provenance/mechanism correction and operational labelling
only. Adds no quality measurement, no admission/serve verdict, no
human-gate claim, and publishes no product-facing repair requirement. Both
DO-NOT-SERVE orders stand; `owner_decision_required` stays `false`.
