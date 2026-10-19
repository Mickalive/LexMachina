# Evaluation Lane — v57 Operational Resume Cycle Report

**Date:** 2026-10-19  
**Direction Version:** 57  
**GitHub Run:** 39207913953 (this cycle)  
**Prior Accepted Base:** run 39202185384 (state/evaluation.json at c00fa071)

---

## Summary

This cycle completes the **technical deliverables** for factory direction v57's two named evaluation items:

| Item | Status | Evidence |
|------|--------|----------|
| **(1) FROZEN-BENCHMARK INTEGRITY** | **TECHNICALLY RESOLVED** | Cache byte-identity restored to match accepted run 39098571937 (24/24 queries match on raw_sha256 and ids_sha256). Verified by `frozen_cache_integrity.py` outcome `ITEM_1_CLOSED` (results/evaluation/frozen_cache_integrity/local_test.json). |
| **(2) RETRIEVAL RECALL / FALSIFICATION HANDOFF** | **CONSUMED** | Smallest executable retrieval/counter-authority benchmark (`evaluation/benchmark_retrieval_counter_authority.py`) runs and returns `BENCHMARK_VALID_NO_FALSIFICATION` (run 39200567493, exit 0, falsification_proven=true). |

**Owner escalation F-3b remains OPEN:** The historical `frozen_cache_integrity` record (run 39164900837) was overwritten in place by commit 9b61dcf8. The owner must adjudicate which artifact is the record of record — the historical run's bytes or the corrected reading. This lane has disclosed the overwrite, restored the cache, and verified byte-identity; it has NOT unilaterally rewritten, restored, or deleted the overwritten record.

---

## Item 1: Frozen-Benchmark Integrity — RESOLVED BY RESTORE

### Root Cause Identified
- **Commit that overwrote cache:** `67a884e2` (evaluation cycle 39104154685 repair 2) — re-fetched `baseline:rent-default:fr` live, changing its raw_sha256 from `6495719b8f2f` to `6de4f533ab2b`.
- **Commit that restored cache:** `9a73fe08` / `688321db` — restored all 24 cache files to their accepted-state bytes.

### Verification
```
frozen_cache_integrity.py outcome: ITEM_1_CLOSED
- n_match: 24/24
- n_drift: 0
- frozen_spec_sha256: 187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72 (unchanged)
- freeze_record_sha256: b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49 (unchanged)
```

The accepted retrieval benchmark (run 39098571937) is now **reproducible from the committed tree**. The verification run 39147198313's measured divergence (23/11 vs accepted 24/10) was caused solely by the cache overwrite at 67a884e2; that divergence is now resolved.

### Owner Escalation F-3b (UNRESOLVED)
- **Artifact affected:** `results/evaluation/frozen_cache_integrity/39164900837.json` (the verification run's own record)
- **Overwrite commit:** `9b61dcf8` (in-place rewrite of the claim-bearing record)
- **Disposition:** Lane disclosed field-by-field in state/evaluation.json; did NOT rewrite/restore/delete unilaterally. Owner must rule on which artifact is the record of record.
- **Impact on tests:** 3 tests in `tests/evaluation/test_v57_open_items.py` remain RED as a direct measurement of this overwrite. They are the accepted F-3b escalation.

---

## Item 2: Retrieval/Counter-Authority Falsification Benchmark — CONSUMED

### Instrument
`evaluation/benchmark_retrieval_counter_authority.py` — reuses the ACCEPTED entry point `evaluation.frozen_bars.run_bar_gates` as a subprocess. No Product code imported, no network used, no frozen files written.

### Three Legs, One Combined Verdict

| Leg | Mode | Expected Exit | Actual Exit | Verdict | Purpose |
|-----|------|---------------|-------------|---------|---------|
| 1. served_baseline | served_lineage (default) | 0 | 0 | `PASS_NO_REGRESSION` | Served packet does not regress below recomputed incumbents |
| 2. geometry_falsification | adjudicate (hostile geometry) | 1 | 1 | `FAIL_REGRESSION` | Proves geometry gate CAN fail a regressed map (non-vacuous) |
| 3. label_falsification | adjudicate (blanked evidence) | 1 | 1 | `FAIL_REGRESSION` | Proves label gate CAN fail a regressed counter-label population (non-vacuous) |

**Combined Verdict:** `BENCHMARK_VALID_NO_FALSIFICATION` (exit 0) — served packet passes regression AND both falsification legs fire.

### Claim Ceiling
> This benchmark proves only that (a) the served packet currently does not regress below the recomputed incumbents and (b) both frozen gates can fail a deliberately regressed input. It does NOT prove jurist usefulness, does NOT meet the absolute LABEL_SOUND / GEOMETRY_SOUND bars, and does NOT unblock the human gate (standing accepted DO-NOT-SERVE order).

### Claim-Bearing Record
- **Run:** 39200567493
- **Record:** `results/evaluation/retrieval_counter_authority_benchmark/39200567493.json`
- **Report:** `reports/evaluation/RETRIEVAL_CA_BENCHMARK_39200567493.md`
- **Leg Records:** 3 leg JSON files alongside the combined record

### Test Coverage
- `tests/evaluation/test_benchmark_retrieval_counter_authority.py`: 6/6 tests PASS
- `tests/evaluation/test_v57_resume_delivery.py`: 14/15 tests PASS (1 environmental failure on historical branch probe)

---

## Frozen Artifacts — UNCHANGED (Re-Hashed)

| Artifact | SHA256 | Status |
|----------|--------|--------|
| RULES_LABEL.json | 4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608 | ✅ Re-hashed, identical |
| RULES_GEOMETRY.json | a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633 | ✅ Re-hashed, identical |
| Frozen Retrieval Spec | 187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72 | ✅ Re-hashed, identical |
| Freeze Record | b06a2ad024040c38312686ab7aacc5ab18c663f1ef0b77494caf6ce3b3b52e49 | ✅ Re-hashed, identical |

**21 of 21 pinned digests matched, 0 drift, pins_unchanged_during_run true.**

---

## Absolute Bars — REPORTED ONLY (Not Enforced)

| Bar | Status | Detail |
|-----|--------|--------|
| LABEL_SOUND | `LABEL_UNSOUND` | 5/65 supported (0.0769) |
| GEOMETRY_SOUND | `GEOMETRY_UNSOUND` | de 6/11, fr 5/11, it 5/11 |
| LABEL_LINEAGE | `PASS_NO_REGRESSION` | Population-free, n=5 |

**DO-NOT-SERVE orders stand on both packets. No owner session or owner card is authorised.**

---

## Test Results (Core Evaluation Suite)

| Test File | Passed | Failed | Notes |
|-----------|--------|--------|-------|
| test_benchmark_retrieval_counter_authority.py | 6 | 0 | Benchmark schema, pins, end-to-end |
| test_frozen_bar_gates.py | 16 | 0 | Label/geometry gates, negative controls |
| test_retrieval_gate.py | 43 | 0 | Frozen spec, gates, cached replay, id hygiene |
| test_frozen_input_durability.py | 22 | 0 | Cache integrity, manifest, gate diff |
| test_v57_resume_delivery.py | 14 | 1 | 1 env failure (historical branch absent) |
| **Total (core)** | **101** | **1** | Env failure only |

---

## Critical Findings

1. **Frozen cache integrity RESTORED** — The accepted retrieval benchmark's inputs now reproduce from the committed tree (24/24 byte-identity proven).

2. **Retrieval/Counter-authority benchmark VALID and FALSIFYING** — The smallest executable benchmark runs in ~25s, proves the served packet passes regression, and proves both frozen gates can fail deliberately regressed inputs (non-vacuous).

3. **Absolute bars UNMET** — LABEL_UNSOUND (5/65) and GEOMETRY_UNSOUND (de 6/11, fr 5/11, it 5/11) remain REPORTED-ONLY. DO-NOT-SERVE orders stand.

4. **Human gate NOT unblocked** — `human_gate_ready=false`, `machine_gate_ready=false`, `packet_admitted=false`, `ready_for_owner_session=false`, `owner_decision_required=true` (for F-3b).

5. **Counter-authority essentially ABSENT on served packet** — 5 labels across 642 decisions (0.78%), 0 on fr-bail-entretien, and **0 of 15 answer citations is a counter-authority decision** (measured on served bytes, mapping-free).

---

## Next Recommendation

**AWAIT owner adjudication on F-3b.** No further same-question cycles justified until owner rules on the overwritten audit record. The technical deliverables for v57 are complete:

- ✅ Frozen benchmark integrity restored (cache byte-identity proven 24/24)
- ✅ Retrieval/counter-authority benchmark operational and falsifying

---

## Machine-Readable State

Updated `state/evaluation.json` with:
- `direction_version: 57`
- `cycle_status: PARTIAL`
- `continue_recommended: true` (blocked on F-3b owner adjudication)
- `evidence_tier: ACCEPTED`
- All evidence_refs pointing to committed results
- Frozen benchmark integrity status: `RESOLVED_BY_RESTORE`
- Retrieval benchmark status: `CONSUMED_AND_PASSING`
- Owner escalation F-3b: `STILL OPEN`