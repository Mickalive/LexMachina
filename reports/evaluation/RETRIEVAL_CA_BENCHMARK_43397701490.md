# RETRIEVAL_CA_BENCHMARK_43397701490

**Run ID**: 43397701490  
**Lane**: evaluation  
**Direction version**: 68  
**Status**: AUDIT_READY  

## Benchmark Execution

The smallest executable retrieval/counter-authority benchmark (`minimal_ca_falsify_benchmark`) was executed against the V3 packet-of-record (39319405429) with 3 questions (FR/DE/IT).

**Command**:
```
python3 -m evaluation.minimal_ca_falsify_benchmark --run-id 43397701490 --out-dir results/evaluation/minimal_ca_falsify_benchmark/43397701490.json --report-dir reports/evaluation/RETRIEVAL_CA_BENCHMARK_43397701490.md
```

## Verdict

**PRODUCT_FALSIFIED** (exit code 1)

The benchmark falsifies the product by demonstrating that counter-authority surface discovery fails on all served questions:
- `mf::counter_authority_surface::39319405429::de-kapitalverletzung`: 0 counter-authority rows issued
- `mf::counter_authority_surface::39319405429::fr-bail-entretien`: 0 counter-authority rows issued
- `mf::counter_authority_surface::39319405429::it-responsabilita-medica`: 0 counter-authority rows issued

## Gate Results

- **11 of 18 gates passed**
- **4 gates failed** (all counter-authority surface discovery)
- **3 gates reported** (language robustness, noted as Frontier-owned defects not re-scored here)
- **1 gate neutral** (admission disclosure, passes by convention)

## Key Findings

1. **Counter-authority surface is empty** across all three language questions (DE, FR, IT)
2. **Concept coverage** varies: DE has 2/8 concepts with zero rows (kapitalverletzung, uberwachungspflicht); FR has 0/9 zero rows; IT has 0/13 zero rows
3. **Source validity**, **duplicate suppression**, and **admission disclosure** all pass
4. **Language robustness** defects are REPORTED-ONLY (owned by Frontier team frontier-query-concept-recall, not re-scored here)
5. **No universal-174k benchmarks** were run (deterministic offline only)
6. **No new thresholds or predicates** were re-derived (frozen rubric applied unchanged)

## Orchestration Failure Diagnosis (Previous Run 43391631838)

The prior operational resume (run 43391631838) diagnosed an **ORCHESTRATION_AGENT_LAUNCH_FAILURE_EXIT_1_NO_RETRYABLE_SIGNATURE**:
- Exit code 1 after 16 seconds
- No LEX_MODEL_AUTH_FAILURE, LEX_MODEL_ROTATE, LEX_ZERO_DELTA_REPAIR, or LEX_WORK_QUANTUM_EXPIRED annotations
- Immediate exit with no retry or model rotation
- Zero delta (no changes to committed artifacts)
- Diagnosis chain confirmed: all 11 consecutive runs shared the same failure pattern
- Verdict: RESUME_VERIFIED_AUDIT_READY

## Ordered Work (Run 43391631838)

All 15 ordered work checks held:
- Item 1: Bypass clause correction present and unchanged
- Item 2: Family gate NOT_YET_DISCRIMINATING (50/50 byte-identical, 14/15 role ceiling)
- Item 3: Falsification record pins unchanged (UNTOUCHED)
- Item 4: Report only (3 non-blocking CYCLE_39965089504 fixes)
- Item 5: Benchmark records honored (local.json preserved)

## Snapshot Audit-Ready Status

The snapshot is **AUDIT_READY**:
- All hypothesis checks hold (5/5)
- Deliverable verified (REPLAY_REPRODUCES, all 41 measurement fields match)
- State integrity confirmed (no unconditional byte-identity claims)
- No 174k rerun declared
- Write scope clean
- Product mount pins all match
- No fabricated claims
- Negative results preserved (4 failed gates recorded as evidence)

## Next Recommendation

**continue_recommended**: false

The product is already falsified by the existing benchmark (run 40179932344). No additional same-question cycle is justified. The factory director should proceed to the human product gate evaluation, or declare the lane complete if the visual UX test is not pursued.