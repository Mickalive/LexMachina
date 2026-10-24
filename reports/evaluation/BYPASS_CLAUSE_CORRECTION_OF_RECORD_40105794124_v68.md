# Correction of record: v67 bypass clause vs accepted product head 8b5b08dd

- Direction: v68  
- Corrects: FAST-MVP current-head CA falsifier run 40105794124 (accepted bcb4520a)  
- Instrument result: `results/evaluation/bypass_clause_correction/40113448025.json` (verdict CORRECTION_NOT_CONFIRMED; measurement unchanged; no bar moved)  
- Product mount head: `8b5b08dddeda482961ecfd432a5b5b40675b92ab` (accept 40100397058, commit 8b5b08dd)  
- Integrated unit: e2270c37..85e816f carries 51d306c (cycle 40093776552) and 85e816f (cycle 40100397058)  
- Recompute: `python3 -m evaluation.bypass_clause_correction --run-id 40113448025 --out-dir results/evaluation/bypass_clause_correction`

## What changed (provenance)

**Path-routing leg is CLOSED.** Commit 51d306c removed the `not fixture_generation` gate around `apply_verified_span_selection` in `product/query/pipeline.py`; the seam now runs on the shipped offline/slice path even in fixture mode (gated on `adversarial_retrieval` alone). The committed accepted bundle from head 8b5b08dd confirms:

- Bundle (claims population): `results/product/offline_slice/20261024T142517Z/rent-default.bundle.json` (sha256 `6eee1149b3c0ec23124746af482e15d9298c2120ee25de4bc4dd7e1cf7d93fa9`)  
- `provenance.counter_evidence_span.applied = true`  
- `n_candidates = 1`, `n_selected = 0`, `n_abstained = 1`  
- `abstained_ids = ["gr_gerichte_ERZ 2010 25"]`, `abstention_reasons = {"pivot_absent": 1}`  
- `frozen_rules_sha256 = 4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608` (frozen gate untouched)

The v67 reading note's clause "because the product path still sets `fixture_generation=True` and bypasses the landed filter" is therefore **superseded as explanation**.

## Remaining residual (rejection/incumbent handling)

The seam **executed and abstained** on the trilingual Graubünden letterhead row. The incumbent counter evidence remains in place: in `rent-default.bundle.json` row `gr_gerichte_ERZ 2010 25` still has `counter_evidence_verified = true`, `counter_status = candidate-limiting`, `counter_uncertainty = 0.2`, with evidence head at offset 0 (`Kantonsgericht von Graubünden ...`), class `D2_letterhead_zone`. The span seam only filters/selects candidate spans that reach it; it does not automatically reject or downgrade a defective incumbent that is left verified. The frozen `counter_authority_surface` gate remains content-blind and issues on enriched bundles.

## Measurement unchanged

The 40105794124 falsifier measurement stands exactly as frozen:
- Verdict: `SOUND_COUNTER_ROW_PRESENT` (exit 0), falsification_proven=false  
- 4/5 enriched bundles carry verified scored rows with frozen content defects (D2 2, D3 2, D4 1) over 4 distinct decisions  
- 1 sound row: `bstger_SK.2023.49` (COUNTER_REASONING, zero defects)  
- Defect histogram unchanged; no bar moved; no frozen edit; no 174k rerun  
- Both DO-NOT-SERVE orders remain in effect; posture flags unchanged

## Correct statement of record

The bypass leg is closed at head 8b5b08dd. The binding residual is **rejection/incumbent handling** on the abstention/pivot_absent path (D2 offset-0 multi-line court headers including trilingual Graubünden, D3 markup residue, D4 language-marker mismatch). Fixing only candidate-span filtering is insufficient. Full-family regeneration is required before any class-level re-measure; D3/D4 are confirmed-repaired only on class-eligible rows per prior accepted findings, not on the full family.

**Claim ceiling:** Provenance/mechanism correction only; adds no quality measurement, no admission/serve verdict, no human-gate claim.
