# Fast MVP Evaluation Cycle — 2026-10-24

## Summary
Executed the smallest executable retrieval/counter-authority benchmark suite that can falsify the product on the V3 packet-of-record (39319405429). All benchmarks reuse existing accepted LexMachina evaluation assets per REUSE-FIRST doctrine.

## Benchmarks Executed

### 1. Minimal Retrieval/Counter-Authority Benchmark (`minimal_ret_ca_benchmark`)
- **Run ID**: local_test_1
- **Verdict**: BENCHMARK_VALID_NO_FALSIFICATION (exit 0)
- **Falsification Proven**: true
- **Engine**: `evaluation.frozen_bars.run_bar_gates` (accepted entry point)
- **Legs**:
  - Leg 1 (served_baseline): PASS_NO_REGRESSION (exit 0) — served packet does not regress
  - Leg 2 (geometry_falsification_hostile): FAIL_REGRESSION (exit 1) — hostile geometry makes gate fail
- **Direction Version**: 67
- **Packet**: 39319405429 (V3 packet-of-record)

### 2. Minimal Retrieval CA Benchmark (`minimal_retrieval_ca_benchmark`) — Mapping-Free Falsifier
- **Run ID**: local_test_3
- **Verdict**: PRODUCT_FALSIFIED (exit 1)
- **Falsification Proven**: true
- **Engine**: `evaluation.mapping_free_recall_falsifier` (via wrapper)
- **Failed Gates (4/18)**:
  - mf::concept_coverage::39319405429::de-kapitalverletzung
  - mf::counter_authority_surface::39319405429::de-kapitalverletzung
  - mf::counter_authority_surface::39319405429::fr-bail-entretien
  - mf::counter_authority_surface::39319405429::it-responsabilita-medica
- **Finding**: German bundle has 2/8 core concepts with zero retrieval; all three language bundles emit ZERO counter-authority rows under frozen rubric
- **Non-vacuity Controls**: All 4 hold
- **Direction Version**: 63 (historical fixture direction)

### 3. Counter Evidence Quality Benchmark (`counter_evidence_quality_benchmark`)
- **Run ID**: local_test_4
- **Verdict**: H2_FALSIFIED (exit 1)
- **Defect Histogram**:
  - D2_letterhead_zone: 10
  - D3_markup_residue: 4
  - D4_language_marker_mismatch: 4
- **Defective Decisions**: 2 distinct (bge_BGE_121_III_260, gr_gerichte_ERZ 2010 25)
- **Finding**: 14 of 14 counter_evidence_verified rows carry frozen defects
- **Direction Version**: 66

### 4. D2 Path Scope Probe (`d2_path_scope_probe`)
- **Finding**: PATH_SCOPE_RESIDUAL
- **Arm 0 (Static Analysis)**: Shipped offline/server slice path never reaches accepted content filter (`fixture_generation=True` bypasses span seam)
- **Arm 1 (Regeneration)**: Regenerated bundle reproduces letterhead evidence; span seam still absent
- **Arm 2 (Routed Filter Diagnostic)**: If routed, filter would FILTER_LEAVES_ROW (reason: pivot_absent)
- **Product-Facing Finding**: Residual D2 is structural path scope, not staleness. Regenerating artifacts alone cannot clear it.
- **Direction Version**: 66

### 5. Fast MVP Current Head CA Falsifier (`fast_mvp_current_head_ca_falsifier`)
- **Verdict**: Content-blind surface gate on new bytes — counter authority emission path still not discriminating
- **Item (2)**: NOT_YET_DISCRIMINATING against current product head
- **Controls**: All hold
- **Posture**: Fail-closed maintained

## Test Suite Results
- **Total Tests**: 89 passed across 10 test modules
- **Key Test Modules**:
  - test_minimal_ret_ca_benchmark.py: 5 passed
  - test_minimal_retrieval_ca_benchmark.py: 21 passed
  - test_mapping_free_recall_falsifier.py: 24 passed
  - test_counter_evidence_quality_benchmark.py: 7 passed
  - test_d2_path_scope_probe.py: 7 passed
  - test_fast_mvp_current_head_ca_falsifier.py: 8 passed
  - test_counter_evidence_quality_remeasure.py: 4 passed
  - test_scorer_path_reconciliation.py: 4 passed
  - test_nested_evidence_refs_guard.py: 4 passed
  - test_measure_current_head_slices.py: 5 passed

## Frozen Bar Status
- **LABEL_SOUND (1.0 support rate)**: NOT MET — 5/65 supported (0.076923)
- **GEOMETRY_SOUND (all 11 bundles pass)**: NOT MET — 0/3 bundles pass
- **Both DO-NOT-SERVE Orders**: STAND
- **Admission**: FAIL-CLOSED
- **Human Gate Ready**: FALSE
- **Machine Gate Ready**: FALSE

## Recommendations (per v67 factory direction)

### Item (1) — Minimal CA Benchmark Freeze-First Re-verification
**Status**: DISCHARGED — re-verified FROZEN-FIRST under run 40099481633 (REPRODUCES, 19/19, 0 mismatches, controls C3-C6 pass)

### Item (2) — Fast MVP Current Head CA Falsifier
**Status**: NOT_YET_DISCRIMINATING — blocked on Core Product landing P0 dual fix:
1. Letterhead detector fix for two profiled P1 offset-0 multi-line court-header patterns
2. Route offline/slice path through filter (fixture_generation bypass prevents execution)

**Next discriminating cycle**: Only when Core Product lands both fixes and regenerates full-family slices, then re-run frozen item-(2) post-repair re-measure + d2_path_scope_probe.

### Item (3) — Scorer Path Reconciliation
**Status**: DISCHARGED — RECONCILIATION_COMPLETE (run 40068038783). The divergence is TRANSFORM-PATH (frozen scorer never receives transformed bytes), not contract-shape exclusion.

### Item (4) — Conditional Re-measure
**Status**: STANDING — awaits Product P0 dual fix

## Evidence References (Machine Records)
- results/evaluation/minimal_ret_ca_benchmark/local_test_1.json
- results/evaluation/minimal_retrieval_ca_benchmark/local_test_3.json
- results/evaluation/counter_evidence_quality_benchmark/local_test_4.json
- results/evaluation/d2_path_scope_probe/local_test_1.json
- results/evaluation/fast_mvp_current_head_ca_falsifier/local_test_1.json

## Human-Readable Reports
- reports/evaluation/RETRIEVAL_CA_BENCHMARK_local_test_1.md
- reports/evaluation/RETRIEVAL_CA_BENCHMARK_local_test_3.md
- reports/evaluation/COUNTER_EVIDENCE_QUALITY_BENCHMARK_local_test_4.md
- reports/evaluation/D2_PATH_SCOPE_PROBE_local_test_1.md
- reports/evaluation/FAST_MVP_CURRENT_HEAD_CA_FALSIFIER_local_test_1.md

## Claim Ceiling (Binding)
This evaluation cycle:
- Does NOT meet, move, or re-derive the frozen absolute LABEL_SOUND or GEOMETRY_SOUND bars (they stay REPORTED-ONLY)
- Does NOT lift the accepted DO-NOT-SERVE order on packet 38839347028 nor DO-NOT-SERVE-UNCHANGED on rebuilt-39027045675
- Does NOT certify admission of any packet; admission stays fail-closed
- Does NOT claim the map helps a jurist; that remains the human product gate's question
- Runs NO obsolete universal-174k geometry benchmarks

## Continue Recommended
**FALSE** — Another cycle under the SAME factory-direction question becomes discriminating only when Core Product lands its P0 dual fix (detector + path routing + full-family slice regeneration). Until then, re-running would re-derive closed work.

## Lane State
- **Lane**: evaluation
- **Direction Version**: 67
- **Evidence Tier**: REPRODUCED
- **Cycle Status**: COMPLETE
- **Accepted Run ID**: 40084716045
- **Proposed Run ID**: local_test_1 (this cycle)
- **Human Gate Ready**: false
- **Machine Gate Ready**: false
- **Packet Admitted**: false
- **Ready For Owner Session**: false