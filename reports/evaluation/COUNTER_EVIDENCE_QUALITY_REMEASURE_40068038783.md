# Counter-Evidence Content-Quality RE-MEASURE (item 4) — run 40068038783

- Trigger: product accept `3495c13361dd` (cycle 40064639100) landed the P0 filter
- Frozen protocol instrument sha256: `aac86527e5e54f0f...` (expected match: True)
- BEFORE histogram (accepted baseline population re-probe): {'D2_letterhead_zone': 10, 'D3_markup_residue': 4, 'D4_language_marker_mismatch': 4} (14/14 defective)
- AFTER histogram (new head shipped slice): {'D2_letterhead_zone': 1} (1/1 defective)
- Verdict: **REPAIR_NOT_CONFIRMED** (exit 1)

## Per-class verdicts

| class | baseline | new head | eligible rows (new) | verdict |
|---|---|---|---|---|
| D2_letterhead_zone | 10 | 1 | 1 | STILL-DEFECTIVE |
| D3_markup_residue | 4 | 0 | 1 | CONFIRMED-REPAIRED |
| D4_language_marker_mismatch | 4 | 0 | 1 | CONFIRMED-REPAIRED |

## Controls

- `C1_probe_classifies_planted_letterhead_mid_and_markup`: PASS
- `C2_probe_detects_language_marker_mismatch`: PASS
- `C3_frozen_rules_rehash_holds_reported_only`: PASS
- `C4_frozen_instrument_digest_unchanged`: PASS

## Baseline stability

- normalized-identical to accepted baseline of record 40062917685: **True**

## Reason

Per-class: D2_letterhead_zone -> STILL-DEFECTIVE; D3_markup_residue -> CONFIRMED-REPAIRED; D4_language_marker_mismatch -> CONFIRMED-REPAIRED. Overall REPAIR_NOT_CONFIRMED.

## Claim ceiling

Re-measurement of the FROZEN D2/D3/D4 content-quality predicates on the new head's own shipped slice artifacts versus the accepted baseline population; scores no frozen bar, edits no rubric, classifies no decision as supporting/contrary under the frozen rubric and changes no serve verdict. Both DO-NOT-SERVE orders stand; admission stays fail-closed; the comparative map-versus-ranked-list half is NOT scored while emission on a serviceable packet stays zero.
