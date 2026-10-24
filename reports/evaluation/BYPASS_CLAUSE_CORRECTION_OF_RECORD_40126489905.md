# Correction of record (v68 item 1) — bypass clause superseded

Run id (this cycle): 40126489905  
Direction version: 68  
Lane: evaluation  
Packet-of-record: 39319405429  
Accepted product head (referenced): 8b5b08dd (accept 40100397058)  
Accepted bundle provenance (committed): results/product/offline_slice/20261024T142517Z/rent-default.bundle.json (sha256 6eee1149b3c0ec23124746af482e15d9298c2120ee25de4bc4dd7e1cf7d93fa9)  

## What changed (supersession)
- The v67 explanatory clause "fixture_generation bypasses the filter" is **SUPERSEDED AS EXPLANATION** by the committed accepted bundle at 8b5b08dd.
- Path-routing leg landed: commit 51d306c removed the `not fixture_generation` gate around `apply_verified_span_selection` and the seam now runs on the shipped offline/slice path even when `fixture_generation=True` (product/query/pipeline.py lines ~1343-1360).
- The bundle carries `provenance.counter_evidence_span.applied = true`, `n_candidates = 244` (as observed), `n_selected = 0`, `abstained_ids = ['gr_gerichte_ERZ 2010 25']`, `abstention_reasons = {"pivot_absent": 1}`. The row remains `counter_evidence_verified = true` with the trilingual Graubünden letterhead because the seam abstains (`pivot_absent`) and the incumbent is left in place.

## Measurement unchanged
- FAST-MVP falsifier 40105794124 (accept bcb4520a) measurement on 8b5b08dd remains unchanged: 4/5 enriched bundles carry a frozen content defect (D2_LETTERHEAD_ZONE 2, D3_MARKUP_RESIDUE 2, D4_LANGUAGE_MARKER_MISMATCH 1) over 4 distinct decisions; exactly 1 sound row (bstger_SK.2023.49). The frozen counter_authority_surface gate is content-blind and issues on all five.
- The remaining mechanism is **rejection/incumbent handling** when the seam abstains, not a bypass.

## File:line citations
- `/tmp/lex_accepted/product/product/query/pipeline.py:1343-1360` (apply_verified_span_selection called unconditionally when adversarial_retrieval; apply_counter_emission_repair only if not fixture_generation; apply_anchor_labels only if not fixture_generation) — path routed.
- `/tmp/lex_accepted/product/product/query/counter_evidence_span.py` — span selection/seam logic.
- Committed bundle: `/tmp/lex_accepted/product/results/product/offline_slice/20261024T142517Z/rent-default.bundle.json` (sha256 6eee1149b3c0ec23124746af482e15d9298c2120ee25de4bc4dd7e1cf7d93fa9), field `provenance.counter_evidence_span`.

## Conclusion
This is a report-only correction of record (no frozen edit, no bar movement, no re-measurement of the falsifier). The bypass explanation is superseded; the binding residual is incumbent/rejection handling on abstention paths. Both DO-NOT-SERVE orders remain in effect.
