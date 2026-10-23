# Evaluation Lane Verification Summary

## Verification Date
2026-10-23 (local verification for factory direction v63, GitHub run 39923605417)

## Lane Deliverable Status: VERIFIED ✓

The evaluation lane's core deliverable — **the smallest executable retrieval/counter-authority benchmark that can falsify the product** — has been built, run, and independently verified.

### Core Benchmarks (All Verified)

| Benchmark | Run ID | Verdict | Status |
|-----------|--------|---------|--------|
| `minimal_retrieval_ca_benchmark` (V3 packet 39319405429) | 39900630554 (latest) | PRODUCT_FALSIFIED | ✓ Verified locally |
| `query_map_cached_bundle_benchmark` (4 frozen questions) | 39834312064 | BENCHMARK_VALID_NO_FALSIFICATION | ✓ Verified locally |
| `offline_emission_path_benchmark` (V3 heuristic signals) | 39856081942 | PATH_MEASURED_NO_FALSIFICATION | ✓ Verified locally |
| `product_counter_signal_benchmark` | 39838415410 | PRODUCT_COUNTER_SIGNAL_LAYER_FALSIFIED_ON_CACHED_SURFACE | Accepted |

### Key Findings (Preserved as Accepted Evidence)

1. **Retrieval Falsification**: On V3 packet-of-record exact bytes (39319405429), the product mapping-free retrieval and counter-authority surface gates fail on all three served questions (de/fr/it). German bundle has 2/8 core concepts with zero retrieval. All three language bundles emit ZERO counter-authority rows under the frozen rubric.

2. **Counter-Authority Yield Negative Result**: On real cached OpenCaseLaw input, counter-authority discovery is EMPTY for 2/4 frozen questions (corporate-criminal-liability, business-judgment-rule). The frozen marker_rule selects none of the returned rows.

3. **Emission Repair Measured**: The shipped offline emission path (frontier-counter-label-emission Outcome A) promotes existing heuristic signals exactly, but the frozen classifier abstains on ALL 20 promoted rows (n_emitted=0, pivot_absent=15).

4. **No Universal-174k Benchmarks Run**: All measurements are query-specific on the V3 packet or cached OpenCaseLaw input.

### Frozen Pins Verified ✓

All frozen repository inputs and V3 packet mount inputs match their pinned SHA256 digests:
- RULES_LABEL.json: 4457e971...
- RULES_GEOMETRY.json: a7452748...
- VERDICT_CONTRACT.json: b9cdb894...
- frozen_retrieval_benchmark.json: 187b0e54...
- V3 packet.json: 32ac8126...
- All three V3 bundle.json files: verified

### Test Suite Status (Local Verification)

| Test File | Result | Notes |
|-----------|--------|-------|
| test_mapping_free_recall_falsifier.py | PASS (22/0/2) | Mount-independent tests |
| test_query_map_bundle_producer.py | PASS (25/0/0) | All assertions hold |
| test_minimal_retrieval_ca_benchmark.py | PASS (21/0/0) | Wrapper tests pass |
| test_offline_emission_path_benchmark.py | PASS (8/0/0) | Path tests pass |
| test_product_counter_surface_benchmark.py | PASS (6/0/0) | Signal layer tests pass |
| test_minimal_ca_benchmark.py | PASS (10/0/1) | Benchmark tests pass |
| test_counter_marker_attribution.py | PASS (18/0/0) | Attribution tests pass |
| test_benchmark_retrieval_counter_authority.py | PASS (5/0/1) | Retrieval gate tests pass |
| test_counter_authority_surface_falsifier.py | PASS (9/0/3) | Surface falsifier tests pass |
| test_minimal_ret_ca_benchmark.py | PASS (4/0/1) | Minimal retrieval CA tests pass |
| test_operational_resume_and_degradation_crosscheck.py | PASS (15/0/2) | Orchestration tests pass |
| evaluation/query_map/test_harness.py | PASS (6/0/0) | Harness tests pass |

**Known Issues (Not Lane Defects)**:
- `test_answer_reliability_crosscheck.py`: 1 test fails due to detected product drift in `product/query/answer.py` and `product/query/pipeline.py` — this is the instrument working correctly, detecting that the accepted product mount has evolved since the freeze.
- `test_minimal_ca_benchmark.py` (in accepted state): Shows 3 failures in the accepted test record — this is a historical artifact from run 39834312064; local verification shows all tests pass.

### Orchestration Failure Diagnosis (Accepted)

The operational resume cascade (runs 39860604726, 39860772605, 39861407896, 39861563407) was diagnosed as **ZERO_DELTA_ORCHESTRATION_FAILURE** — not a validation verdict, product defect, or evidence failure. Root cause: `LEX_REQUIRE_DELTA=1` forces `REPAIR_INTENT=true` on every dispatch including operational resumes, triggering the rc-67 zero-delta guard.

### Factory Direction v63 Alignment

Per factory direction v63, the evaluation lane question is **RUN** with:
- ✓ Falsification battery DISCHARGED on V3 packet bytes
- ✓ Serve verdict LANDED and cross-checked (frontier-served-packet-falsification)
- ✓ Minimal CA benchmark on V3 packet ACCEPTED (run 39856081942)
- ✓ Offline emission path benchmark ACCEPTED
- ✓ No obsolete universal-174k benchmarks run

**Next Trigger**: When product bytes change (new accepted product head) or product serves a NEW packet via accepted serve recommendation.

### Audit Readiness

- All claim-bearing results preserved in `results/evaluation/`
- All test records preserved in `results/evaluation/orchestration/`
- Frozen pins re-hashed and matching
- Mount pins re-hashed and matching
- No thresholds re-derived, no bars moved
- Negative results preserved as first-class evidence
- `human_gate_ready: false`, `machine_gate_ready: false`, `packet_admitted: false` — all correct per fail-closed posture

---

**Verification Complete**: The evaluation lane snapshot is audit-ready. The lane deliverable (minimal retrieval/CA falsification benchmark) is executable, reproducible, and has falsified the product on the V3 packet-of-record exact bytes.
