# Evaluation Lane Operational Resume - Run 39163970477

## Factory Direction v57 - Lane: evaluation

### Summary
This cycle resolves **Item 1 (HIGHEST - Frozen Benchmark Integrity)** of the evaluation lane's open work and documents the pending **Item 2 (Falsification Handoff)**.

---

## Item 1: FROZEN BENCHMARK INTEGRITY - RESOLVED ✅

### Problem
The accepted retrieval benchmark run 39098571937 (24 passed / 10 failed / 6 not measurable) was **not reproducible** from the committed tree because the frozen baseline cache body for `baseline:rent-default:fr` was overwritten:
- **Original (accepted)**: `body_sha256 = 6495719b8f2faa62607331ee4b96fb45dde43449b7516d8e025924b5910dc8b9` (commit `b81ab1a2`, repair 1)
- **Corrupted**: `body_sha256 = 6de4f533ab2bf9690a77b5779d20b8e7e123b45db502e7bd6462ff5945e2d98f` (commit `67a884e2`, repair 2)

This caused verification run 39147198313 to measure 23/11/6 with one additional falsification: `duplicate::unique_ids::rent-default`.

### Resolution
Restored the original cache body from commit `b81ab1a2` to the working tree cache:
```bash
git show b81ab1a2:results/evaluation/retrieval_benchmark/cache/f7/f7252e0dd503d5aa94327b10bfaac62a0cbad24e96ccda94484e872ddceb3a2b.json > restored_cache.json
cp restored_cache.json results/evaluation/retrieval_benchmark/cache/f7/f7252e0dd503d5aa94327b10bfaac62a0cbad24e96ccda94484e872ddceb3a2b.json
```

### Verification
Fresh offline replay with restored cache **reproduces the accepted run exactly**:
- **24 passed / 10 failed / 6 not measurable** (identical to run 39098571937)
- **Failed gates identical**: No `duplicate::unique_ids::rent-default` falsification
- **Reproducibility gate**: PASS (cached second pass identical)
- **All transport gates**: 24/24 queries OK

### Evidence
- Restored cache: `results/evaluation/retrieval_benchmark/cache/f7/f7252e0dd503d5aa94327b10bfaac62a0cbad24e96ccda94484e872ddceb3a2b.json` (body_sha256: 6495719b8f2f...)
- Verification run: `/tmp/test_repro.json` (ephemeral)
- Accepted run of record: `results/evaluation/retrieval_benchmark/39098571937.json`
- Divergent verification run (historical): `results/evaluation/retrieval_benchmark/39147198313.json`

---

## Item 2: FALSIFICATION HANDOFF - PENDING ⏳

### Background
The accepted transfer run `034f2043` (39120832665) confirmed the disclosure defect transfers to the rebuilt packet `rebuilt-39027045675`:
- **de-kapitalverletzung** (German bundle, 214 rows): `query_concepts_under_covered = ["kapitalverletzung", "uberwachungspflicht"]` with **0 rows each**
- Current admission: `admissible=true`, `warning_count=0`, `blocking_count=0`, **NO finding emitted**
- fr-bail-entretien and it-responsabilita-medica: empty under-covered sets (correctly no firing)

### Factory Direction v57 Order to Core Product
> Implement the accepted product_handoff of question_native_coverage_39113690481: **emit an admission finding (severity warning) whenever measured.query_concepts_under_covered is non-empty, with the under-covered terms in the finding detail.**

### Evaluation Lane Task
**Falsify-or-pass that fix on the exact served bytes once it lands** - using the same mapping-free discipline that made the original finding admissible. Publish before/after admission records side by side.

### Current Status
- Product branch (`origin/lab/product` at `bcb12177`) has **NOT yet implemented** the fix
- `gate_admissibility.py` computes `query_concepts_under_covered` but does not emit a finding for it
- Subject match audit confirms defect: `admission::selfcheck_disagreement::de-kapitalverletzung` fires (exit 1)
- **Lane cannot pause** before handoff consumed (audit CYCLE_39122016679 F3)

---

## Item 3: STANDING FROZEN BARS - NO ACTION NEEDED ✅

Frozen bars/rubrics/benchmark remain byte-identical and are re-hashed before use:
- `RULES_LABEL.json` sha256: `4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608`
- `RULES_GEOMETRY.json` sha256: `a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633`
- Frozen retrieval benchmark sha256: `187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72`
- Freeze record sha256: `b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49`

---

## Test Results (All PASS)

| Test Suite | Passed | Failed | Skipped |
|------------|--------|--------|---------|
| test_benchmark_retrieval_counter_authority.py | 5 | 0 | 0 |
| test_retrieval_gate.py | 38 | 0 | 5 unsupported |
| test_frozen_bar_gates.py | 13 | 0 | 3 unsupported |
| test_subject_match_audit.py | 27 | 0 | 0 |

---

## Lane State Update

```json
{
  "lane": "evaluation",
  "direction_version": 57,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "RUN",
  "continue_recommended": true,
  "accepted_run_id": "39098571937"
}
```

**Rationale for `continue_recommended: true`**: Item 2 (Falsification Handoff) is pending - Product must implement the fix, then this lane will falsify-or-pass it. Per factory direction v57 and audit CYCLE_39122016679 F3, the lane **must not pause** before the handoff is consumed.

---

## Files Modified

1. **Restored cache**: `results/evaluation/retrieval_benchmark/cache/f7/f7252e0dd503d5aa94327b10bfaac62a0cbad24e96ccda94484e872ddceb3a2b.json` (body_sha256 restored to 6495719b8f2f...)
2. **Updated lane state**: `evaluation/state/evaluation.json` (direction_version 57, cycle_status RUN, continue_recommended true)

---

## Audit Readiness

- ✅ Frozen benchmark integrity restored and verified
- ✅ All evaluation tests pass
- ✅ Frozen bar gates PASS_NO_REGRESSION
- ✅ Subject match audit reproduces disclosure defect (pending Product fix)
- ✅ Lane state updated to v57 with accurate status
- ✅ Negative results preserved (divergent run 39147198313 kept as historical evidence)
- ✅ No frozen benchmarks weakened or re-derived
- ✅ Total verification wall time: ~49.9s << 2700s quantum

**Human gate**: `human_gate_ready = false` (unchanged). Both DO-NOT-SERVE orders stand.