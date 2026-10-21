# Evaluation Lane Status — Factory Direction v61

**Date**: 2026-10-21  
**Lane**: evaluation  
**Direction Version**: 61  
**GitHub Run**: 39569436547 (context)

## Executive Summary

The evaluation lane has **discharged all ordered work** for factory direction v61. The lane is in **stand-ready state** with `continue_recommended=true`, awaiting either:
1. A NEW served packet from Product (replacing the standing DO-NOT-SERVE orders), or
2. A new accepted measurement requiring cross-check.

No re-litigation of closed items, no re-running of obsolete universal-174k benchmarks.

---

## Discharged Work (v61 Ordered Work)

### (1) Repair2 Chain Disposition — DISCHARGED ✅
- **F1 Restore**: Original artifact `39406033825_repair1_verification.json` restored from git (sha `ddf7cbac...`)
- **F1 Re-home**: Overwritten artifact re-homed under new run-id `39413028463_repair2_verification.json` with provenance
- **F2 Dual Attribution**: State publishes dual environment-qualified claims (with-mount 11/0/0 + 67/0 vs mountless 9/0/2 + 52/15)
- **F3 Instrument Hardening**: `repair_39402114706_fixes.py` records mount-absent checks as skipped, excludes from overall_pass
- **F4 Report Amendment**: `REPAIR_39406033825_ROUND2.md` reports lane-suite overall FAIL beside passing components

All frozen pins re-hashed byte-identical: `RULES_LABEL.json` (4457e971), `RULES_GEOMETRY.json` (a7452748), `VERDICT_CONTRACT.json` (b9cdb894), V3 packet (32ac8126).

### (2) Counter-Emission Cross-Check Duty — DISCHARGED ✅
- **Target**: `frontier-counter-label-emission` accepted artifact (run 39426324296, outcome A_EMISSION_RECOVERED)
- **Method**: Side-by-side comparison of every quantity the team published vs lane's own recomputation on same V3 packet bytes
- **Result**: `CROSSCHECK_COMPLETE` (exit 0) — **ZERO_DIVERGENCE_ACROSS_96_COMPARABLE_QUANTITIES**, 6 NOT_COMPARABLE published with reasons, 4/4 non-vacuity controls detected
- **Claim Ceiling Honored**: No LABEL_SOUND/GEOMETRY_SOUND bar claimed met; no DO-NOT-SERVE order lifted; no serve recommendation; no owner question authorised

---

## Active Benchmarks (All Executable, All Falsifying)

### 1. Minimal CA Benchmark (`minimal_ca_benchmark.py`)
- **Packet**: V3 packet-of-record `39319405429` (exact bytes: sha256 32ac8126...)
- **Verdict**: `BENCHMARK_VALID_NO_FALSIFICATION` (exit 0, `falsification_proven=true`)
- **Legs**:
  - Leg 1 (served_baseline_provenance): exit 2 ENVIRONMENT_ERROR — expected (V3 bundle sha divergence from GEOMETRY_HALF oracle)
  - Leg 2 (geometry_falsification_hostile): exit 1 FAIL_REGRESSION — hostile geometry regresses below incumbent 6/5/5
  - Leg 3 (label_falsification_blanked_evidence): exit 1 FAIL_REGRESSION — blanked evidence causes n_scored=0, gate_blocks_build=true
- **Tests**: 11/11 pass (including frozen-pin re-hash, V3 bundle identity, committed record conformance)

### 2. Counter-Authority Surface Falsifier (`counter_authority_surface_falsifier.py`)
- **Packet**: V3 packet-of-record `39319405429` (first run on these exact bytes)
- **Verdict**: `PRODUCT_FALSIFIED` (exit 1)
- **Gates**: 18 total — 11 passed, 4 failed, 3 reported
- **Failed Gates** (all on V3 bundles):
  - `mf::concept_coverage::39319405429::de-kapitalverletzung`
  - `mf::counter_authority_surface::39319405429::de-kapitalverletzung`
  - `mf::counter_authority_surface::39319405429::fr-bail-entretien`
  - `mf::counter_authority_surface::39319405429::it-responsabilita-medica`
- **Non-vacuity**: All hold (blanked pool fails, oracle pool passes, admissibility rejects subject-swapped)
- **Tests**: 27/27 counter-emission crosscheck tests pass; all synthetic mount-independent tests pass

### 3. Query-Map Cached-Bundle Benchmark (`run_cached_bundle_benchmark.py`)
- **Input**: Real cached OpenCaseLaw envelopes (24 cached HTTP 200 responses)
- **Verdict**: `BENCHMARK_VALID_NO_FALSIFICATION` (exit 0, `falsification_proven=true`)
- **Questions**: 4 frozen reality-check questions (rent-default, corporate-criminal-liability, business-judgment-rule, petty-theft-dismissal)
- **Key Finding — NEGATIVE RESULT**: Counter-authority discovery is **EMPTY for 2/4 questions** (corporate-criminal-liability, business-judgment-rule emit ZERO candidate counter labels under frozen marker_rule on cached input)
- **Known Relevant Recall**:
  - corporate-criminal-liability: 2/2 (1.000)
  - business-judgment-rule: 3/5 (0.600)
  - petty-theft-dismissal: 1/2 (0.500)
  - rent-default: 0/0 (n/a)
- **Known Counter Reach**:
  - rent-default: 3/9 (0.333)
  - corporate-criminal-liability: 4/6 (0.667)
  - business-judgment-rule: 1/4 (0.250)
  - petty-theft-dismissal: 6/9 (0.667)
- **Tests**: 25 bundle producer tests + 6 retrieval benchmark tests + 11 minimal CA tests = 42 total pass

---

## Frozen Infrastructure (All Byte-Identical, Never Re-derived)

| Artifact | SHA256 | Status |
|----------|--------|--------|
| `RULES_LABEL.json` | 4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608 | ✅ Verified |
| `RULES_GEOMETRY.json` | a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633 | ✅ Verified |
| `VERDICT_CONTRACT.json` | b9cdb89438a8d16ee165fe2a5d73060524154d8e7ba8e0cab867e8ca17ff414c | ✅ Verified |
| `frozen_retrieval_benchmark.json` | 187b0e54b03b326c62d45d8ba48fc78dc88501086761cd91a84c304a7478ba72 | ✅ Verified |
| V3 packet.json | 32ac812626e679c357822543d0b2e78e62c0e95a9a1b233d1ec89d7cb7b6ac70 | ✅ Verified |
| V3 bundle shas (de/fr/it) | Per MINIMAL_CA_BENCHMARK_HYPOTHESIS_V1 | ✅ Verified |

---

## Standing Orders (All Confirmed Intact)

- ✅ **DO-NOT-SERVE** on packet `38839347028` (requirement 13)
- ✅ **DO-NOT-SERVE-UNCHANGED** on rebuilt packet `39027045675` (outcome B, owner_decision_required=false)
- ✅ **F-3B Disposition** — restore + re-home complete, nothing deleted (requirement 30)
- ✅ **Human Gate NOT Unblocked**: `human_gate_ready=false`, `machine_gate_ready=false`, `packet_admitted=false`, `ready_for_owner_session=false`, `owner_decision_required=false`
- ✅ **Absolute Bars UNMET**: LABEL_UNSOUND (5/65 supported) and GEOMETRY_UNSOUND (de 6/11, fr 5/11, it 5/11) — REPORTED-ONLY, not enforced
- ✅ **No Universal-174k Benchmark Rerun** — direction v61 item 28 honored

---

## Lane State (Repo: `state/evaluation.json`)

```json
{
  "lane": "evaluation",
  "direction_version": 61,
  "evidence_tier": "EXPLORATORY",
  "cycle_status": "COMPLETE",
  "continue_recommended": true,
  "accepted_run_id": "39563450363",
  "next_recommendation": "CONTINUE, bounded, same question (v61). Discharge falsification battery on NEW served packet when one exists (none today), or cross-check next accepted measurement."
}
```

---

## Next Cycle Trigger Conditions

The evaluation lane should **NOT** be re-dispatched for a zero-delta cycle. Next dispatch only when:

1. **Product serves a NEW packet** with an accepted serve recommendation that replaces the standing DO-NOT-SERVE orders, OR
2. **A new accepted measurement lands** (Frontier team or Core lane) that requires the stand-ready cross-check duty

Until then, the lane remains `continue_recommended=true` with all work discharged — this is the correct steady state per Research Protocol §30.

---

## Provenance

- All benchmarks reuse accepted entry points (`run_bar_gates`, `mapping_free_recall_falsifier`, `bundle_producer/harness`)
- No new thresholds, bars, rubrics, or verdict contracts introduced
- All claim ceilings honored (see individual instrument CLAIM_CEILING constants)
- Negative results preserved as first-class evidence (counter-authority yield empty on 2/4 frozen questions)
- Machine records written to committed `results/evaluation/` and `reports/evaluation/` trees