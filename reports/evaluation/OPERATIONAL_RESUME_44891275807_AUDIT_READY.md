# Operational Resume 44891377897 (prior snapshot 44891275807 / cycle 40265377500)

- Lane: evaluation
- Direction: v68
- Resume run: 44891377897
- Prior snapshot run: 44891275807 (remote team head ea98384e54d31d2e694c418a1d1ce5769fc6c32f)
- Snapshot verdict: **AUDIT_READY_PENDING_INDEPENDENT_AUDIT**

## What was found

- The persisted snapshot HEAD `ea98384e` is present locally and matches `origin/cycle/core/evaluation/44891275807/team`.
- Producer deliverable artifacts for `test_40265377500` exist in-lane: wrapper, engine record, and report.
- Artifact integrity checks pass: frozen hypothesis/freeze/spec hashes re-verify; wrapper/engine run_id/verdict/exit/mount/input_drift agree; engine record path resolves; no 174k rerun; human_gate_ready=false; packet_admitted=false.
- `CYCLE_40265377500_GATE.json` is present but **mismatches** the committed `test_40265377500` artifacts (gate: BENCHMARK_VALID_NO_FALSIFICATION exit 0, 4 questions, cached-bundle claim; artifacts: PRODUCT_FALSIFIED exit 1, 18 gates, 4 failed, mapping_free_recall_falsifier). The gate is preserved as historical audit artifact but is **not** cited as evidence for the test_40265377500 deliverable.
- Write-scope reproduction for `9fe9d714 -> ea98384e` reports SCOPE_VIOLATION for the two audit-namespace files added by the accept/integrator commit; this is recorded as an orchestration/provenance namespace mismatch, not silently ignored.
- `state/evaluation.json` had no 40265377500/test_40265377500 evidence refs before this resume; state integrity gate passes (11/11).

## Deliverable status

| Artifact | Verdict | Exit | Dir v | Input drift | Run valid | Mount head |
|---|---:|---:|---:|---|---|---|
| `test_40265377500.json` | PRODUCT_FALSIFIED | 1 | 68 | [] | True | `f9b0db254dc2` |
| `test_40265377500_engine_mapping_free_recall_falsifier.json` | PRODUCT_FALSIFIED | 1 | 57 | [] | None | `f9b0db254dc2` |

## Measurement (preserved, not re-run)

- Packet: `39319405429` (V3 packet-of-record exact bytes).
- Engine: `evaluation.mapping_free_recall_falsifier.run()` via minimal_retrieval_ca_benchmark wrapper.
- Verdict: **PRODUCT_FALSIFIED** (exit 1). 18 gates, 11 passed, 4 failed, 3 reported.
- Failed gates: mf::concept_coverage::39319405429::de-kapitalverletzung, mf::counter_authority_surface::39319405429::de-kapitalverletzung, mf::counter_authority_surface::39319405429::fr-bail-entretien, mf::counter_authority_surface::39319405429::it-responsabilita-medica
- No universal-174k rerun. No frozen bar/rubric/threshold/verdict contract edited. No serve verdict. No packet admission. human_gate_ready=false.

## Audit readiness

- This resume does **not** create an audit gate and does **not** claim acceptance.
- The mismatched CYCLE_40265377500_GATE.json is preserved in place; independent audit must not treat it as evidence for test_40265377500.
- Current working tree write scope is clean after this resume adds only evaluation-lane artifacts.
- State integrity gate: ALL_CHECKS_PASS (11/11).
