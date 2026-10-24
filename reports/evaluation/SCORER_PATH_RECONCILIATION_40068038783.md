# Frozen-Scorer / Span-Seam Path Reconciliation (item 3) — run 40068038783

- Packet of record: 39319405429 (exact bytes)
- Product head: `3495c13361dd` (expected 3495c13361dd, match: True)
- Verdict: **RECONCILIATION_COMPLETE** (exit 0)
- Side A on SERVED bytes: n_issued total = 0
- Side A on GUARDED TRANSFORMED bytes: n_issued total = 1
- Side B arm totals (n_emitted): {'baseline': 0, 'candidate_unguarded': 6, 'candidate': 1}
- Identity vs accepted pre-filter measurement of record: **True**
- Contract answer: INSIDE by shape, OUTSIDE by path. Every guarded emitted row carries a counter_status in rubric.scored_statuses and non-empty counter_evidence (shape check: True); when the frozen predicate is applied ...

## Per-qid

| qid | served n_issued | baseline | unguarded | guarded | guarded-transformed n_issued |
|---|---|---|---|---|---|
| de-kapitalverletzung | 0 | 0 | 2 | 0 | 0 |
| fr-bail-entretien | 0 | 0 | 4 | 1 | 1 |
| it-responsabilita-medica | 0 | 0 | 0 | 0 | 0 |

## Claim ceiling

Side-by-side measurement of the frozen mapping-free predicate and the product span-seam arms on identical packet-of-record bytes under the NEW head; scores no frozen bar, applies no verdict contract, edits no scorer; the frozen rubrics are re-hashed REPORTED-ONLY. Both DO-NOT-SERVE orders stand; admission stays fail-closed; the comparative map-versus-ranked-list half is NOT scored while served-bytes emission stays zero.
