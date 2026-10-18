# Evaluation Lane Verification Run 39147198313

**Factory Direction:** v56  
**Date:** 2026-10-18  
**Purpose:** Verify the minimal gate-able evaluation deliverable executes within the 2700s work quantum, confirming audit readiness.

---

## Summary

All evaluation components execute successfully and reproducibly in **~22 seconds total** (<< 2700s quantum). The orchestration/validation failure (audit starvation from LEX_WORK_QUANTUM_EXPIRED kills at ~2704s) was **discharged with accepted evidence** in run 39098571937. This verification run confirms the deliverable remains executable and audit-ready.

| Component | Verification Run | Original Accepted Run | Wall Time | Verdict |
|-----------|------------------|----------------------|-----------|---------|
| Frozen Retrieval Benchmark (offline replay) | 39147198313 | 39098571937 | 0.086s | Reproduced: cached reproducibility PASS, transport OK, expected falsifications on FR/IT authority recall & duplicates |
| Frozen Bar Gates (label + geometry) | 39147198313 | 39098571937 | 5.56s | Reproduced: PASS_NO_REGRESSION, negative controls proven, absolute bars reported not enforced |
| Label Lineage Gate Sweep | 39147198313 | 39020603510 | 12.9s | Reproduced: ALL_PREDICTIONS_HELD, 4 in-scope packets |
| Retrieval/Counter-Authority Falsification Benchmark | 39147198313 | 39098571937 | ~3s | Reproduced: BENCHMARK_VALID_NO_FALSIFICATION |
| Rebuild Preflight | 39147198313 | 39033797087 | ~22s | Reproduced: Legs A-D as predicted, Leg E falsification documented |

**Total verification wall time: ~22 seconds**

---

## Component Details

### 1. Frozen Retrieval Benchmark (`evaluation.retrieval_gate.run_retrieval_benchmark`)

**Frozen Spec:** `evaluation/retrieval_gate/frozen_retrieval_benchmark.json` (sha256: `187b0e54b03b...`, direction v49)

- **Questions:** 4 (rent-default, corporate-criminal-liability, business-judgment-rule, petty-theft-dismissal)
- **Languages:** FR, DE, IT
- **Channels:** baseline, counter
- **Total queries:** 24
- **Mode:** Offline replay from cached responses

**Key Findings (reproduced from accepted run):**
- ✅ Cached reproducibility: PASS (identical raw sha256 + ordered ID lists)
- ✅ Transport: All 24 queries OK
- ❌ Authority recall FR/IT: FAIL for 3/4 questions (corporate-criminal-liability, business-judgment-rule, petty-theft-dismissal) — **expected falsification** of plain OpenCaseLaw baseline
- ❌ Duplicate IDs: FAIL for 3/4 questions (corporate-criminal-liability, business-judgment-rule, petty-theft-dismissal)
- ❌ Counter limiting marker: FAIL for corporate-criminal-liability
- ⚠️ Latency: Not measurable in offline mode (requires live pass)

**Claim Ceiling:** Measures retrieval reachability, source validity, duplicate suppression, cross-language robustness, counter reachability, latency and cached reproducibility. Cannot show map usefulness, never re-classifies decisions.

### 2. Frozen Bar Gates (`evaluation.frozen_bars.run_bar_gates`)

**Frozen Rules:** 
- RULES_LABEL.json (sha256: `4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608`)
- RULES_GEOMETRY.json (sha256: `a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633`)

**Input Bundle SHAs (verified against accepted LABEL_HALF):**
- de-kapitalverletzung: `2441ff2b16722afcd22dca9ad39eafcbeb079b2dfc367d763fbe53fce1356f9c` ✅
- fr-bail-entretien: `6c5ea31d4b9af4abfa39e9f8025cfa3d34279ff1f04d0f643e571e27b23a2618` ✅
- it-responsabilita-medica: `76e7f7ad998f3878e7b08635663e2d594a7a77bdaeb33bcf5fa52d0af00b7aff` ✅

**Label Gate:**
- n_scored: 65 (incumbent: 65) ✅
- n_supported: 5 (incumbent: 5) ✅
- support_rate: 0.076923 (incumbent: 5/65) ✅
- Classes: OFF-DOMAIN 38, UNBACKED 22, SUPPORTED 5 ✅
- Regression verdict: PASS_NO_REGRESSION ✅
- Negative control (blanked evidence): FAIL_REGRESSION, gate_blocks_build=true ✅

**Geometry Gate:**
- Per-bundle counts: de 6, fr 5, it 5 (matches incumbent) ✅
- Engine/oracle cells: 33/33 match ✅
- Regression verdict: PASS_NO_REGRESSION ✅
- Negative control (hostile geometry): FAIL_REGRESSION on de/fr, gate_blocks_build=true ✅

**Absolute Bars (reported, not enforced per direction v50):**
- Labels: LABEL_UNSOUND
- Geometry: GEOMETRY_UNSOUND

### 3. Label Lineage Gate Sweep (`evaluation.frozen_bars.run_label_lineage_gate`)

**Population:** 4 in-scope packets (38799024807, 38812599575, 38839347028, rebuilt-39027045675)

**Frozen Prediction Verification:**
- P1 (label gate parity on accepted lineage): PASS on all 3 packets
- P2 (accepted findings L2/L3/L4 closed): PASS
- P3 (minimal delta non-vacuity): PASS (flipped to red, population unchanged, blocks after)
- P4 (no false blocks): PASS
- P5 (off-lineage recorded): PASS (2 out-of-scope packets with reasons)
- P6 (frozen identity re-verified): PASS

**Verdict:** ALL_PREDICTIONS_HELD ✅

**Statement Defects (preserved from freeze, corrected by erratum):**
- P1 statement prose claimed "2 of 2 non-incumbent packets block" but predicted table blocks 1
- P4 predicted divergence against population-pinned count reading; actual divergence is against pin-removed counterfactual

### 4. Retrieval/Counter-Authority Falsification Benchmark (`evaluation.benchmark_retrieval_counter_authority`)

**Three legs, combined verdict: BENCHMARK_VALID_NO_FALSIFICATION**

| Leg | Expected Exit | Actual Exit | Verdict | Matches |
|-----|---------------|-------------|---------|---------|
| Served Baseline | 0 | 0 | PASS_NO_REGRESSION | ✅ |
| Geometry Falsification (hostile) | 1 | 1 | FAIL_REGRESSION | ✅ |
| Label Falsification (blanked evidence) | 1 | 1 | FAIL_REGRESSION | ✅ |

**Falsification Proven:** True — both deliberately regressed inputs make the gates fail.

### 5. Rebuild Preflight (`evaluation.rebuild_preflight`)

**Five legs, executed via two accepted entry points:**
- `run_bar_gates --adjudicate` (accepted 38971202786, LABEL half population-pinned at 65 rows)
- `run_label_lineage_gate --adjudicate` (accepted 39020603510, population-free rate predicate)

| Leg | Prediction | Result | As Predicted |
|-----|------------|--------|--------------|
| A_identity_control | exit 0, PASS_NO_REGRESSION | exit 0, PASS_NO_REGRESSION | ✅ |
| B_population_plus_one | label NOT_APPLICABLE, geometry PASS | label NOT_APPLICABLE, geometry PASS | ✅ |
| C_preserved_population_blanked_evidence | exit 1, FAIL_REGRESSION | exit 1, FAIL_REGRESSION | ✅ |
| D_geometry_still_enforcing | geometry enforces on changed population | geometry enforces | ✅ |
| E_refusal_negative_control | both exits non-zero | run_bar_gates exits [2, 0] | ❌ **Falsified** |

**Leg E Falsification:** The frozen hypothesis predicted both run_bar_gates exits would be non-zero on empty/zero-counter-row packets. Measured: empty packet exits 2 (ENVIRONMENT_ERROR), zero-counter-row packet exits 0 (PASS_NO_REGRESSION). This falsification is **documented and published** per the freeze's own success rule: *"a confirmed vacuity (prediction) and a falsified vacuity (prediction wrong) are both acceptable preflight results."*

**Key Measured Enforcement Envelope (two-bar, instrument-qualified):**
- run_bar_gates LABEL half: enforces ONLY on exact 65-row incumbent population (NOT_APPLICABLE off-population)
- label_lineage_gate: enforces on ANY three-frozen-qid lineage packet with n_scored > 0 and support_rate < 5/65
- Geometry gate: enforces on qid-set lineage (no population pin)
- Zero-counter-row packet: NEITHER label instrument blocks (NOT_APPLICABLE / NOT_MEASURED), NEITHER certifies sound

---

## Audit Readiness Checklist

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Frozen benchmark executes in < 2700s | ✅ PASS | ~22s total |
| Cached reproducibility verified | ✅ PASS | Retrieval benchmark pass B identical |
| Frozen rules SHA256 verified | ✅ PASS | All 4 frozen inputs match |
| Negative controls proven | ✅ PASS | Blanked evidence & hostile geometry |
| Frozen predictions verified | ✅ PASS | ALL_PREDICTIONS_HELD |
| Falsifications documented | ✅ PASS | Retrieval authority recall, duplicates, counter marker; preflight leg E |
| No universal-174k benchmarks rerun | ✅ PASS | Only query-specific components used |
| Provenance preserved | ✅ PASS | All evidence_refs traceable to accepted runs |
| Results written to canonical paths | ✅ PASS | results/evaluation/*, reports/evaluation/* |

---

## Next Recommendation

**NO further same-question cycles justified.** The evaluation lane deliverable is:
1. **Complete** — minimal gate-able benchmark shipped and verified
2. **Audit-ready** — all components executable, frozen inputs verified, results reproducible
3. **Within quantum** — ~22s << 2700s

The factory director may now decide the successor question. The standing accepted DO-NOT-SERVE order on packet 38839347028 remains in effect (owner_decision_required=FALSE per frontier-rebuilt-packet-serve-audit verdict).

---

## Machine-Readable State

Updated: `evaluation/state/evaluation.json` with `verification_run_id: "39147198313"` and `audit_ready: true`.