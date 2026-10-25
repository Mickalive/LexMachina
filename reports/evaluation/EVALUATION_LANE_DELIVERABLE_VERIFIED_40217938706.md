# Evaluation Lane Deliverable Verified — Operational Resume Run 40217938706

## Summary

The evaluation lane deliverable — the **smallest executable retrieval/counter-authority benchmark that can falsify the product** — has been verified and is audit-ready.

**Lane State (state/evaluation.json):**
- `cycle_status`: COMPLETE
- `continue_recommended`: false
- `accepted_run_id`: 40159747851 (independently audited, gate PASS)
- `current_cycle_audit_status`: PENDING_INDEPENDENT_AUDIT (operational resume run 40217938706)
- `evidence_tier`: ACCEPTED

## Deliverable Components

### 1. FAST-MVP Retrieval Recall@K Benchmark
**File:** `evaluation/fast_mvp_retrieval_recall_benchmark.py`
**Tests:** `tests/evaluation/test_fast_mvp_retrieval_recall_benchmark.py` (7 tests, all pass)

**What it measures:**
- Coverage: how much of frozen ground truth OpenCaseLaw search returns
- Recall@K: |gt in top K| / |gt| for INPUT order (OCL relevance) and PRODUCT order (product reranker)
- Retention@K: |gt in top K| / |gt present in corpus| — isolates reranker from search layer

**Frozen protocol:** 24 cells (4 questions × 2 channels × 3 languages FR/DE/IT)
**Claim:** Product reranker must not drop frozen known-relevant/known-counter authorities that its own candidate input kept in top-20
**Verdict on current product mount:** `PRODUCT_FALSIFIED_RECALL_LOSS` (exit 1)
- 10 discriminating cells
- 2 cells lose ground-truth authorities: `baseline:business-judgment-rule:de` (retention 1.0→0.0) and `counter:petty-theft-dismissal:fr` (retention 1.0→0.667)
- Aggregate: product_hits=15 < input_hits=17
- Language legs: FR fails (4→3), DE fails (12→11), IT holds (1→1)

**Key properties:**
- Zero network calls, deterministic offline replay only
- No universal-174k benchmarks
- No new thresholds invented
- Frozen hypothesis + spec + amendments pinned by SHA256
- V1_2 amendment publishes BOTH verdict readings (original C7-blocking and amended C7a-only)

### 2. FAST-MVP Current-Head Counter-Authority Falsifier
**File:** `evaluation/fast_mvp_current_head_ca_falsifier.py`
**Tests:** `tests/evaluation/test_fast_mvp_current_head_ca_falsifier.py` (8 tests, all pass)

**What it measures:**
- Whether counter-authority rows on NEW product bundles carry frozen D1-D4 content defects vs. genuine counter reasoning
- Reuses frozen predicates from `counter_evidence_quality_benchmark.py` and `mapping_free_recall_falsifier.py`
- Uses frozen `scored_statuses` vocabulary from `RULES_LABEL.json`

**Frozen protocol:** 6 bundles (5 enriched + 1 not-enriched control) at current accepted product head
**Verdict on current product mount:** `NOT_MEASURED_VACUOUS` (exit 2) — pins don't match (product mount advanced since hypothesis freeze)
**Content findings (descriptive, not gated):**
- 5 enriched bundles with verified scored rows
- 4/5 carry frozen D1-D4 defects: D2_letterhead_zone (2), D3_markup_residue (2), D4_language_marker_mismatch (1)
- 1/5 has sound counter reasoning (`bstger_SK.2023.49`)
- `v67 item (2)` status: NOT_YET_DISCRIMINATING (unchanged)

**Key properties:**
- No new thresholds, predicates, rubrics, or verdict contracts
- Does NOT re-run/replace the benchmark of record (packet-of-record 39319405429)
- Fail-closed posture: packet_admitted=false, machine_gate_ready=false, human_gate_ready=false

### 3. Accepted Retrieval Benchmark (Reused)
**File:** `tests/evaluation/test_retrieval_benchmark.py` (38 tests, all pass)

Covers: retrieval coverage, counter-authority recall structure, source validity, multilingual robustness (FR/DE/IT), duplicate suppression, cached reproducibility, latency, cluster stability, integrated pipeline.

## Test Results Summary

| Test Module | Tests | Passed | Failed |
|-------------|-------|--------|--------|
| test_fast_mvp_retrieval_recall_benchmark.py | 7 | 7 | 0 |
| test_fast_mvp_current_head_ca_falsifier.py | 8 | 8 | 0 |
| test_retrieval_benchmark.py | 38 | 38 | 0 |
| test_stand_ready_multilingual_probe.py | 16 | 16 | 0 |
| test_counter_evidence_quality_benchmark.py | 7 | 7 | 0 |
| test_mapping_free_recall_falsifier.py | 24 | 24 | 0 |
| test_disclosure_provenance_crosscheck.py | 24 | 24 | 0 |
| test_nested_evidence_refs_guard.py | 4 | 4 | 0 |
| **Total** | **128** | **128** | **0** |

## Orchestration/Validation Failure Diagnosis

**Failure Class:** `ORCHESTRATION_WORK_QUANTUM_EXPIRED`

The operational resume run 40217938706 completed its producer work successfully (all 6 hypotheses passed, 0 failed). However, the **independent audit job** failed at step "Independent audit" after 2704.0s on the FIFTH consecutive run, against a 2700s work quantum in `.github/scripts/run-ox-with-retry.sh`.

**This is NOT:**
- A producer measurement failure
- A gate REVISE/BLOCKED verdict
- A product defect
- A validation failure

**This IS:**
- An infrastructure timeout (work quantum = exact multiple of 15s poll interval)
- The audit issued NO verdict (no gate file, no audit branch)
- The producer snapshot is preserved and AUDIT_READY_PENDING_INDEPENDENT_AUDIT

## Append-Only Remediation (Run 40217938706)

Run 40217938706 additionally remediated an append-only violation from run 40213041041:
- 15 claim-bearing artifacts overwritten in place were restored with SHA256 proof
- Rewritten content preserved and re-homed under run 40217938706's directory
- Nothing deleted (per AGENTS.md items 5-6 / Factory-wide requirement 34)

## Reuse-First Compliance

All benchmarks reuse accepted LexMachina assets:
- `product.query.adversarial_retrieval` — adversarial pass logic
- `product.query.bundle` — bundle construction/validation
- `product.query.qmap` — clustering/projection
- `product.query.retrieval` — TF-IDF retrieval
- `product.answer_reliability` — measurement protocol
- `frontier/frontier-query-retrieval/ocl_adapter/fixtures` — offline replay
- `frontier/frontier-query-retrieval/ocl_adapter/bundle` — product bridge
- `frontier/frontier-query-retrieval/ocl_adapter/expansion` — multilingual variants
- `frontier/frontier-query-retrieval/ocl_adapter/dedupe` — duplicate suppression
- Frozen bars: `RULES_LABEL.json` (sha 4457e971...), `RULES_GEOMETRY.json` (sha a7452748...)

## No Universal-174k Benchmarks

Confirmed: `no_universal_174k_benchmarks: true` in all benchmark records.

## Audit Readiness

The snapshot from run 40217938706 is **AUDIT_READY_PENDING_INDEPENDENT_AUDIT**:
- All producer work completed and verified
- All frozen pins re-verified (where applicable)
- All contract tests pass (128/128)
- Benchmarks executable from committed tree
- Negative results preserved (PRODUCT_FALSIFIED_RECALL_LOSS, NOT_MEASURED_VACUOUS)
- Provenance chain intact (evidence_refs all resolve, nested refs resolved)
- Append-only remediation documented with SHA256 proofs

## Next Steps

1. **Independent audit** of run 40217938706 (infrastructure responsibility, not lane work)
2. No further same-question evaluation cycles needed (`continue_recommended: false`)
3. Product lane consumes these falsification results for its P0 content-quality filter work
4. Both DO-NOT-SERVE orders stand; admission remains fail-closed

---

**Verification completed:** 2026-10-25T19:15:00Z
**Verified by:** evaluation lane operational resume verification
**Claim ceiling:** This verification confirms executable benchmarks exist and falsify the product on frozen protocols. It does NOT claim the visual map helps a jurist, serve any packet, lift any DO-NOT-SERVE order, or admit any packet.