# Evaluation Lane — Cycle Completion Report

**Lane:** evaluation
**Direction:** v68 (mounted from `main`)
**Run ID:** 40162507752 (verification re-run of audited cycle 40153908549)
**Status:** AUDIT COMPLETE + VERIFICATION RE-RUN

---

## Summary

The evaluation lane deliverable — **the smallest executable retrieval/counter-authority benchmark that can falsify the product** — is **complete, independently audited, and verified**.

### What Was Delivered

| Component | Status | Location |
|-----------|--------|----------|
| FAST-MVP recall@20 benchmark instrument | ✅ Complete | `evaluation/fast_mvp_retrieval_recall_benchmark.py` |
| Contract tests (7 tests, AST guard for def-order) | ✅ 7/7 PASS | `tests/evaluation/test_fast_mvp_retrieval_recall_benchmark.py` |
| Frozen hypothesis (V1) + V1_1 + V1_2 amendments | ✅ Byte-stable | `evaluation/FAST_MVP_RETRIEVAL_RECALL_BENCHMARK_40149704173_*.json` |
| Frozen spec (24-cell multilingual OCL cache) | ✅ SHA-pinned | `evaluation/retrieval_gate/frozen_retrieval_benchmark.json` |
| Primary measurement (audited) | ✅ PASS | `results/evaluation/fast_mvp_retrieval_recall_benchmark/40153908549.json` |
| Verification re-run (producer 40162507752) | ✅ Identical claim result | `results/evaluation/minimal_ca_benchmark_40162507752.json` |
| Independent audit gate | ✅ PASS | `results/audit/evaluation/CYCLE_40153908549_GATE.json` |
| Audit report | ✅ Written | `reports/audit/evaluation/CYCLE_40153908549.md` |
| F-3B disposition (restored + re-homed) | ✅ Proved by re-hash | `results/evaluation/fast_mvp_retrieval_recall_benchmark/40152672734.json`, `40153096228.json`, `40153096228_PROVENANCE.json` |

---

## Measurement Result

**Verdict:** `PRODUCT_FALSIFIED_RECALL_LOSS` (exit_code=1)

The product reranker **loses ground-truth authorities that its own input order kept**:

| Metric | Value |
|--------|-------|
| Discriminating cells | 10/24 |
| Aggregate product_hits @20 | 15 |
| Aggregate input_hits @20 | 17 |
| **Loss (product < input)** | **YES** |

**Cell-level losses:**
- `baseline:business-judgment-rule:de` — input retention 1.0 → product retention **0.0** (5 authorities dropped: `bger_4A_219_2015`, `bger_4A_259_2016`, `bger_4A_603_2014`, `bger_4A_626_2013`, `bger_4A_62_2024`)
- `counter:petty-theft-dismissal:fr` — input retention 1.0 → product retention **0.667** (1 authority dropped: `ge_gerichte_CAPH_107_2004`)

**Language leg failures:**
- French: 4→3 → **FAILS**
- German: 12→11 → **FAILS**
- Italian: 1→1 → holds

---

## Dual Reading (V1_2 Amendment)

Both readings published per amendment:

| Rule Set | Verdict | Exit Code |
|----------|---------|-----------|
| V1_2 (C7b reported-only) | `PRODUCT_FALSIFIED_RECALL_LOSS` | 1 |
| Original V1 (C7b blocking) | `NOT_MEASURED_VACUOUS` | 2 |

Claim numbers **identical** under both.

---

## Audit Verification

- **Gate file:** `results/audit/evaluation/CYCLE_40153908549_GATE.json`
- **Gate verdict:** `PASS`
- **Safe to integrate:** `true`
- **Required fixes:** `[]`
- **Freeze discipline:** Verified (hypothesis, spec, amendments all match pins; rehash before/after identical)
- **Controls:** 10 executed, 9 blocking controls pass (C7b duplicate collisions are REPORTED_ONLY per V1_2)
- **F-3B disposition:** Restored overwritten artifact, re-homed defective rewrite with provenance sidecar; nothing deleted; proved by re-hash

---

## Orchestration Diagnosis

The prior producer run 40153096228 failed at the agent invocation step (UnboundLocalError in instrument), so its team job returned non-success and the audit job (gated on `needs.team.result == success`) never ran. The operational resume cycle 40153908549:
1. Repaired the instrument (def-order fix, no predicate changes)
2. Re-executed against the same frozen inputs
3. Executed F-3B disposition on the overwritten artifact
4. Produced a reproducible measurement that passed independent audit

The subsequent producer run 40162507752 independently re-ran the benchmark and reproduced the identical claim-bearing result (only timing variance), confirming reproducibility.

---

## State Update

`state/evaluation.json` updated to reflect:
- `audit_status`: `AUDIT_PASSED` (was `PENDING_INDEPENDENT_AUDIT`)
- `accepted_run_id`: `40153908549` (was `40143419165`)
- `github_run`: `40162507752` (verification re-run)
- `evidence_refs_n`: 26 (was 23) — added audit gate, audit report, verification artifact
- All 26 evidence refs resolve in worktree
- `continue_recommended`: `false` — benchmark complete, falsifies correctly, successor question is Factory Director's

---

## Direction v68 Item (2) — Conditional Re-Measure

**Status: NOT_YET_DISCRIMINATING**

Accepted product mount `e53662be` contains the rejection/incumbent handling code but **no regenerated 15-bundle flagship family** for the frozen probe to measure against. This is Product's ordered work, not an evaluation measurement gap.

---

## Compliance

- ✅ No universal-174k benchmarks rerun
- ✅ No network calls (deterministic offline cache replay only)
- ✅ Frozen hypothesis/spec/amendments byte-stable (no post-hoc changes)
- ✅ Negative result preserved (`PRODUCT_FALSIFIED_RECALL_LOSS`)
- ✅ Provenance preserved (F-3B disposition proved by re-hash)
- ✅ Audit artifacts written to correct relative paths (`results/audit/...`, `reports/audit/...`)
- ✅ Gate filename uppercase `_GATE.json` per requirement 14

---

## Next Steps

The evaluation lane has discharged its current factory-direction question. The FAST-MVP benchmark exists, runs reproducibly, falsifies the product, and has been independently audited. Per `RESEARCH_PROTOCOL.md` §20, `continue_recommended=false` — the successor question is the Factory Director's to set.

The remaining binding residual is **Product's ordered work** (direction v68 item 2: rejection/incumbent handling and 15-bundle flagship regeneration), not an evaluation measurement.