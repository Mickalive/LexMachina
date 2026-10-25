# Follow-up citation: correction of record 40105794124 (v68)

- Follow-up for: `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md`
- Original note sha256 (this snapshot): computed by the resume verifier in `results/evaluation/operational_resume_40198184759/deliverable_verification_40198184759.json`
- Accepted gate that requires this citation: `results/audit/evaluation/CYCLE_40133253347_GATE.json` — PASS, `safe_to_integrate=true`, one NON-BLOCKING CC6/CC7 provenance fix ("Document the gap in any follow-up citation of this correction").
- Purpose: supply the explicit `file:line` citation required by v68 ordered item (1) without editing the accepted historical correction note.

## Explicit file:line citation

At the current accepted product mount (`29a5c4a548ba0ab8b6a8f574de1e732d17f3d109`):

- `product/query/pipeline.py:1339` — `if adversarial_retrieval:` (the seam is gated on adversarial retrieval alone; the old `not fixture_generation` condition is gone)
- `product/query/pipeline.py:1343` — `audited = apply_verified_span_selection(`
- `product/query/pipeline.py:1347` — `if not fixture_generation:` followed by `apply_counter_emission_repair(audited)` (separate repair gate remains for counter emission)

The accepted correction note already records the bundle of record and the executed-but-abstained seam provenance:

- Bundle: `results/product/offline_slice/20261024T142517Z/rent-default.bundle.json`
- sha256: `6eee1149b3c0ec23124746af482e15d9298c2120ee25de4bc4dd7e1cf7d93fa9`
- `provenance.counter_evidence_span.applied = true`, `n_selected = 0`, `n_candidates = 1`, `n_abstained = 1`
- `abstained_ids = ["gr_gerichte_ERZ 2010 25"]`, `abstention_reasons = {"pivot_absent": 1}`
- `gr_gerichte_ERZ 2010 25` remains `counter_evidence_verified = true`; the remaining defect is rejection/incumbent handling, not a seam bypass.

## CC6/CC7 provenance: historical gap and its resolution

At the time of run `40144816305`, the then-current product mount could not resolve `51d306c` or `8b5b08dd`, so CC6/CC7 failed and the accepted gate made the gap a NON-BLOCKING follow-up citation. That historical failure is preserved in `results/evaluation/bypass_clause_correction/40144816305.json`. The machine verdict remains `CORRECTION_NOT_CONFIRMED` (exit 1); this follow-up does not turn it into a pass.

At this resume's mount (`29a5c4a548ba0ab8b6a8f574de1e732d17f3d109`), the commit objects **are present** and the claim is now directly verified:

- `51d306ca4b52c6d8ea1200c306cfb33e44e487ac` exists. Its diff on `product/query/pipeline.py` removes `if not fixture_generation and adversarial_retrieval:` and replaces it with `if adversarial_retrieval:`, and moves `apply_counter_emission_repair(audited)` under a separate `if not fixture_generation:`.
- At `51d306c`, the file has `if adversarial_retrieval:` at line 1339, `apply_verified_span_selection(` at 1343, and `if not fixture_generation:` at 1347.
- `8b5b08dd`'s parent is `85e816f`; `85e816f`'s parent is `51d306c`. The accepted integrated unit therefore carries the change: `8b5b08dd -> 85e816f -> 51d306c`.
- The same line numbers hold at accepted head `8b5b08dd`.

`git merge-base --is-ancestor 8b5b08dd 29a5c4a5` returns 1 because `29a5c4a5` is the shallow graft root. That graft prevents a merge-base path through the current head, but it does not contradict the object-level chain at the named accepted head `8b5b08dd`, which is exactly what the correction asserts. No ancestry through the graft is claimed.

## Invariants

- The `40105794124` measurement of record is unchanged: `SOUND_COUNTER_ROW_PRESENT`, `falsification_proven=false`, 4/5 enriched bundles defective (D2 2 / D3 2 / D4 1 over 4 distinct decisions), 1 sound row `bstger_SK.2023.49`.
- No falsifier was re-executed; no frozen bar, rubric, threshold, predicate or verdict contract was edited; no 174k benchmark was run.
- Both DO-NOT-SERVE orders remain in effect. Admission stays fail-closed. `human_gate_ready=false`, `machine_gate_ready=false`, `owner_decision_required=false`.
- Claim ceiling: provenance/mechanism citation only; no quality measurement, serve verdict, admission or jurist-usefulness claim.
