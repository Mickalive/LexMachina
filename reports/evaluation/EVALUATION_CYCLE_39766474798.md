# Evaluation Cycle 39766474798 — Query-Map Cached-Bundle Falsification Benchmark

## Summary

Executed the smallest executable retrieval/counter-authority benchmark for the query-map MVP (direction v62, lane=evaluation). The benchmark tests whether real cached OpenCaseLaw input can produce source-linked, duplicate-free, geometry-stable bundles that satisfy the accepted harness contract, and whether the falsification legs correctly reject regressed inputs.

## Benchmark: `evaluation.query_map.run_cached_bundle_benchmark`

**Run ID**: 39766474798  
**Verdict**: `BENCHMARK_VALID_NO_FALSIFICATION` (exit 0)  
**Falsification Proven**: True  
**Frozen Spec**: `evaluation/retrieval_gate/frozen_retrieval_benchmark.json` (sha256 `187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72`, re-hashed before/after, unchanged)  
**Cache**: 24 raw OpenCaseLaw HTTP 200 envelopes, all 24 matched to frozen query texts

## Three-Leg Structure

| Leg | Purpose | Result |
|-----|---------|--------|
| 1. Producer Baseline | Build bundles from cache; all harness checks must pass | **PASS** (4/4 questions) |
| 2. Falsification: Blanked Counter Evidence | Strip `counter_evidence`; `counter_classifications_supported` must go FALSE | **FIRED** (4/4 questions) |
| 3. Falsification: Broken Source URL | Repoint one `canonical_url` off `mcp.opencaselaw.ch`; `source_urls_valid` must go FALSE | **FIRED** (4/4 questions) |

## Per-Question Results

| Question | Decisions | Clusters | Counter Candidates | Dup Suppressed | Leg1 | Leg2 | Leg3 |
|----------|-----------|----------|-------------------|----------------|------|------|------|
| rent-default | 223 | 7 | 16 | 17 | PASS | ✓ | ✓ |
| corporate-criminal-liability | 218 | 11 | 0 | 22 | PASS | ✓ | ✓ |
| business-judgment-rule | 221 | 13 | 0 | 19 | PASS | ✓ | ✓ |
| petty-theft-dismissal | 205 | 8 | 4 | 35 | PASS | ✓ | ✓ |

## Counter-Authority Yield (NEGATIVE RESULT)

**COUNTER-AUTHORITY DISCOVERY IS EMPTY FOR 2/4 FROZEN QUESTIONS** on the cached input: `['corporate-criminal-liability', 'business-judgment-rule']`.

- Per-question candidate counts: `{"rent-default": 16, "corporate-criminal-liability": 0, "business-judgment-rule": 0, "petty-theft-dismissal": 4}`
- The counter channel returns rows, but the frozen `marker_rule` (a norm_token AND a limitation_token in title+regeste+snippet) selects none of them for 2 questions.
- This is a NEGATIVE RESULT about the data plane's counter-authority capability measured on real OpenCaseLaw rows — the map's counter layer would be empty for half the query set.
- **Not claimed**: this measures lexical marker yield under the frozen rule on cached rows; it is NOT a measurement of a learned or adjudicated counter classifier, and the Frontier recall component is a separate build.

## Recall (Measured, NOT Thresholded)

| Question | Known Relevant | Known Counter Reach | Counter IDs Also Labelled |
|----------|----------------|---------------------|---------------------------|
| rent-default | 0/0 (n/a) | 3/9 (0.333) | 0/9 |
| corporate-criminal-liability | 2/2 (1.000) | 4/6 (0.667) | 0/6 |
| business-judgment-rule | 3/5 (0.600) | 1/4 (0.250) | 0/4 |
| petty-theft-dismissal | 1/2 (0.500) | 6/9 (0.667) | 1/9 |

## Test Suite Results (no_pytest_runner shim)

| Test File | Passed | Failed | Skipped | Unsupported | Verdict |
|-----------|--------|--------|---------|-------------|---------|
| test_frozen_bar_gates.py | 13 | 0 | 0 | 3 | SHIM_PASS |
| test_query_map_bundle_producer.py | 25 | 0 | 0 | 0 | SHIM_PASS |
| test_benchmark_retrieval_counter_authority.py | 5 | 0 | 0 | 1 | SHIM_PASS |
| test_mapping_free_recall_falsifier.py | 22 | 0 | 0 | 2 | SHIM_PASS |
| test_minimal_ca_benchmark.py | 10 | 0 | 0 | 1 | SHIM_PASS |
| test_counter_probe_anchor_falsifier.py | 25 | 0 | 0 | 0 | SHIM_PASS |
| test_state_integrity_gate.py | 2 | 0 | 0 | 10 | SHIM_PASS |
| test_audit_correction_verification.py | 3 | 1 | 0 | 0 | SHIM_FAIL* |

*SHIM_FAIL is expected: one test shells out to pytest which is absent in the producer image. This is a known shim limitation, not a logic failure.

**Total**: 105 passed, 1 failed (expected), 17 unsupported (NOT-RUN)

## Evidence Artifacts

- Machine record: `results/evaluation/query_map_cached_bundle_benchmark/39766474798.json`
- Human report: `reports/evaluation/QUERY_MAP_CACHED_BUNDLE_39766474798.md`
- Test shim records: `results/evaluation/orchestration/39766474798_*.json`

## Claim Ceiling

This benchmark proves only that REAL cached OpenCaseLaw rows carry the fields the query_result_bundle contract needs (decision_id, canonical_url on mcp.opencaselaw.ch, language, citation strings, statutes, a frozen-marker-rule text surface) and that the ACCEPTED harness rejects a regressed bundle. It does NOT prove that Product builds such a bundle, that the map is useful to a jurist, that counter labels are calibrated (counter_uncertainty is a fixed fixture constant), that the coordinates are a good layout (they are a deterministic fixture layout, not a geometry claim), or anything about the absolute LABEL_SOUND / GEOMETRY_SOUND bars. Recall figures are measured, not thresholded.

## Next Recommendation

**CONTINUE, bounded, same question (v62).** The query_map_cached_bundle_benchmark run 39766474798 confirms the data plane produces valid bundles with proven falsification legs, but counter-authority discovery remains empty for 2/4 frozen questions (corporate-criminal-liability, business-judgment-rule) under the frozen marker rule. This is a NEGATIVE RESULT on the data plane, not the product. Stand-ready duties unchanged: remedy (a) NOT landed at the accepted product head 48969821 (planner pin 57b6a6f9 re-verified); when product bytes change, re-freeze the repair verification under a new run id and re-score the mapping-free counter_authority_surface gates; cross-check the product lane's four deliverables as they land. No universal-174k benchmark run. human_gate_ready, machine_gate_ready, packet_admitted, ready_for_owner_session, owner_decision_required all stay false.

## State Update

Updated `state/evaluation.json`:
- `evidence_refs_n`: 108 → 118 (10 new refs added)
- `github_run`: 39766474798
- Added `benchmark_result_39766474798` with full results
- Added `test_suite_39766474798` with shim results
- Updated `next_recommendation`

