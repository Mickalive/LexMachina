# Evaluation Lane — Operational Resume & Audit-Ready Snapshot
**Lane:** evaluation  
**Direction:** v68  
**Date:** 2026-10-25  
**Status:** AUDIT-READY — benchmark suite verified, state corrected

---

## Summary

Resumed from persisted producer snapshot (run 40144816305 — bypass clause correction). Diagnosed orchestration/validation failure: the lane state incorrectly recorded the report-only bypass clause correction (40144816305, exit_code=1, CORRECTION_NOT_CONFIRMED) as the `accepted_run_id`, but this run lacks an audit gate and was executed against an advanced product mount (e53662be) rather than the accepted head (8b5b08dd) it was written for.

**Corrected state:** The evaluation lane's benchmark deliverable is the FAST-MVP retrieval & counter-authority benchmark (`tests/evaluation/test_retrieval_benchmark.py`), which passed 38/38 tests in run 40143419165 with independent audit PASS (`CYCLE_40143419165_GATE.json`). The cached-bundle benchmark (run 40111496300) also holds audit PASS. The FAST-MVP falsifier (40105794124) remains the substantive content finding.

---

## Orchestration/Validation Failure Diagnosis

| Run | Type | Audit Gate | Verdict | Issue |
|-----|------|------------|---------|-------|
| 40111496300 | Cached-bundle benchmark | PASS | BENCHMARK_VALID_NO_FALSIFICATION | Valid accepted cycle |
| 40105794124 | FAST-MVP falsifier | PASS | SOUND_COUNTER_ROW_PRESENT | Substantive content finding |
| 40143419165 | test_retrieval_benchmark | PASS | 38/38 tests pass | **Latest benchmark with audit** |
| 40144816305 | Bypass clause correction | **MISSING** | CORRECTION_NOT_CONFIRMED | Run against advanced mount; not a benchmark cycle |

**Root cause:** State file updated `accepted_run_id` to 40144816305 despite missing audit gate. The bypass clause correction is a report-only reconciliation of the FAST-MVP falsifier's mechanism explanation — it does not re-execute the falsifier, add benchmark capability, or meet acceptance criteria (requires both audit PASS + accept commit per factory-wide requirement 4).

---

## Benchmark Suite Verification (Operational Resume)

**Command:** `python -m pytest tests/evaluation/test_retrieval_benchmark.py -v` (from `/tmp/lex_accepted/product` with numpy/scipy/sklearn installed)

**Result:** 38 passed, 0 failed, 0 skipped in 12.19s

### Test Coverage (matches evaluation lane directive)

| Category | Tests | Checks |
|----------|-------|--------|
| retrieval_coverage | 5 | All 4 frozen queries return candidates |
| adversarial_execution | 5 | Adversarial pass executes, returns valid structure, excludes initial pass decisions |
| source_validity | 8 | Candidate & product bundles have valid mcp.opencaselaw.ch URLs |
| multilingual_robustness | 4 | FR/DE/IT all produce candidates; variants generated; no fabricated translations |
| duplicate_suppression | 3 | Identity merge across channels; order independence; no duplicate decision_ids |
| cached_reproducibility | 3 | Offline replay deterministic; bundle construction deterministic; adversarial plan deterministic |
| latency | 4 | Retrieval <5s; adversarial <2s; map build <1s |
| cluster_stability | 3 | Clustering deterministic; projection coordinates deterministic (drift <1e-10); labels semantic |
| integrated_pipeline | 2 | Full offline pipeline produces valid bundle; degrades gracefully on empty adversarial |
| protocol_freeze | 1 | Protocol digest matches frozen value |

**No network calls. No universal-174k benchmarks. Deterministic offline replay only.**

---

## Substantive Findings (Preserved from Accepted Cycles)

### FAST-MVP Falsifier (40105794124, audit PASS)
- **5 enriched bundles** from accepted product head 8b5b08dd
- **4/5 bundles** carry verified counter rows with frozen content defects:
  - D2_LETTERHEAD_ZONE: 2 (gr_gerichte_ERZ 2010 25, bge_BGE_110_II_391)
  - D3_MARKUP_RESIDUE: 2 (ge_gerichte_CAPH_107_2004, bge_BGE_121_III_260)
  - D4_LANGUAGE_MARKER_MISMATCH: 1 (bge_BGE_121_III_260)
- **1 sound row**: bstger_SK.2023.49 (COUNTER_REASONING, no defects)
- **Verdict:** SOUND_COUNTER_ROW_PRESENT, falsification_proven=false
- **Controls C1-C4:** All hold (frozen predicate SHA, synthetic clean row passes, synthetic blank fails, empty bundle zero issued)

### Cached-Bundle Benchmark (40111496300, audit PASS)
- 4 frozen questions, 24 cached OpenCaseLaw envelopes
- All 4 pass producer_baseline (non-empty, duplicate-free, source-url-valid, answer-citations-constrained, counter-classifications-supported)
- Falsification legs 2 & 3 fire (blanked counter_evidence → counter_classifications_supported FALSE; broken URL → source_urls_valid FALSE)
- **Counter-authority yield:** 2/4 questions yield ZERO candidate counter labels under frozen marker_rule (corporate-criminal-liability, business-judgment-rule) — documented negative result
- **Known relevant recall:** rent-default 0/0, corporate-criminal-liability 2/2, business-judgment-rule 3/5, petty-theft-dismissal 1/2

### Bypass Clause Correction (40144816305, report-only)
- **Corrected statement of record:** The accepted product head 8b5b08dd does NOT bypass the span seam. Commit 51d306c removed the `not fixture_generation` gate; the seam runs on the offline path and ABSTAINS (n_selected=0, pivot_absent). The defective incumbent (trilingual Graubünden letterhead) stays `counter_evidence_verified=true` because the rejection/incumbent leg is open.
- **Measurement unchanged:** 40105794124 aggregate values byte-for-byte identical
- **Item (2) status:** NOT_YET_DISCRIMINATING — requires Product to land rejection/incumbent handling + full flagship family regeneration

---

## Accepted State (Corrected)

```json
{
  "lane": "evaluation",
  "direction_version": 68,
  "evidence_tier": "ACCEPTED",
  "cycle_status": "COMPLETE",
  "continue_recommended": false,
  "accepted_run_id": 40143419165,
  "evidence_refs": [
    "tests/evaluation/test_retrieval_benchmark.py",
    "results/evaluation/test_retrieval_benchmark_40143419165.json",
    "results/audit/evaluation/CYCLE_40143419165_GATE.json",
    "results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json",
    "results/audit/evaluation/CYCLE_40105794124_GATE.json",
    "results/evaluation/query_map_cached_bundle_benchmark/40111496300.json",
    "results/audit/evaluation/CYCLE_40111496300_GATE.json",
    "evaluation/bypass_clause_correction.py",
    "results/evaluation/bypass_clause_correction/40144816305.json"
  ]
}
```

---

## Next Recommendation

**NO SAME-QUESTION SUCCESSOR FROM THIS LANE.** Per factory direction v68 and the accepted evidence:

1. **Benchmark suite** is the smallest executable retrieval/counter-authority benchmark that can falsify the product — verified passing, audit PASS.
2. **FAST-MVP falsifier** measures the product's current counter-authority quality — 4/5 defective, 1 sound, rejection/incumbent leg open.
3. **Cached-bundle benchmark** proves real OpenCaseLaw input produces valid bundles — but 2/4 questions yield zero counter labels under frozen marker rule.
4. **Bypass clause correction** reconciles the mechanism — span seam runs but abstains; defective incumbent remains verified.
5. **Item (2) remains NOT_YET_DISCRIMINATING** until Core Product lands the rejection/incumbent leg and regenerates the full flagship offline/server slice family.

The lane's blocker is **Product shipping a rebuilt packet**, not evaluation work. `continue_recommended=false` is correct.

---

## Audit Readiness Checklist

- [x] Benchmark test file exists: `tests/evaluation/test_retrieval_benchmark.py`
- [x] Test results committed: `results/evaluation/test_retrieval_benchmark_40143419165.json` (38/38 pass)
- [x] Audit gate PASS: `results/audit/evaluation/CYCLE_40143419165_GATE.json`
- [x] State file corrected: `state/evaluation.json` (accepted_run_id=40143419165)
- [x] Substantive findings preserved: 40105794124, 40111496300, 40144816305
- [x] No universal-174k benchmarks rerun
- [x] No frozen bars/rubrics/thresholds edited
- [x] No network calls in benchmark
- [x] Deterministic offline replay verified
- [x] Protocol digest frozen: `e1a0b18d23d18bd1aafe54a66329fd0b04cd6f95f794d3d0336e0d867af41b7e`

---

## Recompute Command

```bash
cd /tmp/lex_accepted/product && python -m pytest /home/runner/work/LexMachina/LexMachina/tests/evaluation/test_retrieval_benchmark.py -v
```

All artifacts are committed and reproducible. The evaluation lane snapshot is audit-ready.