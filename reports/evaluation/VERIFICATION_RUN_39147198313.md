# Evaluation Lane Verification Run 39147198313

**Factory Direction:** v56  
**Date:** 2026-10-18 (repair 1 of rejected cycle 39147198313; audit results/audit/evaluation/CYCLE_39147198313_GATE.json gate=REVISE)  
**Purpose:** Verify the minimal gate-able evaluation deliverable executes within the 2700s work quantum, confirming audit readiness.

---

## Summary

All evaluation components execute within **49.874 s total** (instrumented components; << 2700s quantum). The orchestration/validation failure (audit starvation from LEX_WORK_QUANTUM_EXPIRED kills at ~2704s) was **discharged with accepted evidence** in run 39098571937. This verification run confirms the deliverable remains executable and audit-ready.

**Repair-1 correction of record (audit F1):** the verification does **not** reproduce the accepted run of record for the frozen retrieval benchmark. This run measures **23 passed / 11 failed / 6 not_measurable**; the accepted run of record 39098571937 measured **24 / 10**. One **additional** falsification appears (`duplicate::unique_ids::rent-default`; rent-default per-slug `passed` flips True -> False), and duplicate-ID failures are **4/4 questions**, not 3/4. The accepted run of record is **not reproducible from the committed tree**: the retrieval cache generation for `baseline:rent-default:fr` moved `6495719b8f2f` (b81ab1a2, the generation 39098571937 was scored against) -> `6de4f533ab2b` (67a884e2, cycle 39104154685 repair 2, which carries no cycle report and no audit gate on this branch). The 23/11 reading is stable across 39101217095, 39115755033, 39117425713 and 39147198313. The earlier overwrite at b81ab1a2 is disclosed by accepted cycle 39101217095 (`repair_39101217095/F2_cache_provenance`: "20/24 cache files re-fetched live during run 39101217095"). Two findings **do** reproduce and are retained: cached-replay identity (identical raw sha256 + ordered ID lists, 24/24 queries) and transport (24/24 queries OK).

| Component | Verification Run | Original Accepted Run | Wall Time (re-derived from artefacts) | Verdict |
|-----------|------------------|----------------------|-----------|---------|
| Frozen Retrieval Benchmark (offline replay) | 39147198313 | 39098571937 | 0.086s (pass_a 0.044 + pass_b 0.042) | **NOT REPRODUCED — DIVERGENT (1 additional falsification)**: this run 23/11 vs accepted 24/10; duplicates 4/4 (rent-default FAIL); cached-replay identity and transport 24/24 DO reproduce |
| Frozen Bar Gates (label + geometry) | 39147198313 | 39098571937 | 5.563s (elapsed_s) | Reproduced (producer-context): PASS_NO_REGRESSION, negative controls proven, absolute bars reported not enforced |
| Label Lineage Gate Sweep | 39147198313 | 39020603510 | 10.907s (elapsed_s) | Reproduced (producer-context): ALL_PREDICTIONS_HELD, 4 in-scope packets |
| Retrieval/Counter-Authority Falsification Benchmark | 39147198313 | (no artefact of record at 39098571937; block re-pointed to this run) | 16.906s (elapsed_s) | Reproduced (producer-context): BENCHMARK_VALID_NO_FALSIFICATION |
| Rebuild Preflight | 39147198313 | 39033797087 | 16.412s (legs A+B+C 5.514+5.518+5.380; legs D/E not instrumented) | Reproduced (producer-context): Legs A–D as predicted, Leg E falsification documented |

**Total verification wall time: 49.874 s** (sum of the instrumented artefact fields above; derivation published in `evaluation/state/evaluation.json.total_verification_wall_derivation`).

---

## Environment-Dependency Disclosure (audit F3 — read before the checklist below)

1. **Four of the five verified components are NOT independently re-executable from the repository.** The served-lineage bar gates, the label-lineage gate sweep, the rebuild preflight and retrieval/counter-authority leg 1 all read the ephemeral out-of-repo mount `/tmp/lex_accepted/product/...`; CA legs 2 and 3 read ephemeral `/tmp/ca_bench_*` packets generated this cycle. Their "executed / reproduced" status above is **producer-context only**.
2. **The machine records already carry `packet_dir`** naming those paths; this report is deliberately not stronger than the records.
3. **Independently re-derivable from committed bytes:** (a) the retrieval benchmark cached replay (offline, content-addressed cache under `results/evaluation/retrieval_benchmark/cache`); (b) `python -m evaluation.frozen_bars.run_bar_gates --adjudicate` on the vendored rebuilt packet at `results/evaluation/rebuilt_packet_adjudication_39049030442/packet/questions`, which reproduces the sweep's recorded accepted_label_gate for rebuilt-39027045675 exactly (n_scored 5, n_supported 5, LABEL_SOUND) with the blanked-evidence negative control firing.

---

## Component Details

### 1. Frozen Retrieval Benchmark (`evaluation.retrieval_gate.run_retrieval_benchmark`)

**Frozen Spec:** `evaluation/retrieval_gate/frozen_retrieval_benchmark.json` (sha256: `187b0e54b03b...`, direction v49)

- **Questions:** 4 (rent-default, corporate-criminal-liability, business-judgment-rule, petty-theft-dismissal)
- **Languages:** FR, DE, IT
- **Channels:** baseline, counter
- **Total queries:** 24
- **Mode:** Offline replay from cached responses
- **This run's own record:** `results/evaluation/retrieval_benchmark/39147198313.json` — 23 passed / 11 failed / 6 not_measurable, overall_pass=false.

**Key Findings (from this run's record — supersedes the report's earlier restatement of the accepted run):**
- ✅ Cached reproducibility: PASS — `reproducible::cached_second_pass_identical`, identical raw sha256 + ordered ID lists on 24/24 queries (the accepted run of record also passed this; the finding reproduces)
- ✅ Transport: All 24 queries OK (reproduces)
- ❌ Authority recall FR/IT: FAIL for 3/4 questions (corporate-criminal-liability, business-judgment-rule, petty-theft-dismissal) — **expected falsification** of plain OpenCaseLaw baseline. rent-default authority recall is **not measurable**: the frozen reality benchmark carries no controlling-authority set for that question (authority_ids = []), and is never counted as a pass.
- ❌ Duplicate IDs: FAIL for **4/4** questions — rent-default (NEW falsification vs the accepted run of record, which passed this gate), corporate-criminal-liability, business-judgment-rule, petty-theft-dismissal
- ❌ Counter limiting marker: FAIL for corporate-criminal-liability
- ⚠️ Latency: Not measurable in offline mode (requires live pass)

**Why this run diverges from the accepted run of record (measured from committed bytes):** the retrieval cache is content-addressed by request URL. For `baseline:rent-default:fr` the pinned body moved `6495719b8f2f…` (commit b81ab1a2, cycle 39101217095 repair 1 — the generation accepted run 39098571937 was scored against) -> `6de4f533ab2b…` (commit 67a884e2, cycle 39104154685 repair 2 — no cycle report, no audit gate on that branch). The accepted 24/10 therefore is **not reproducible from the committed tree**; the current 23/11 reading (with the rent-default duplicate falsification) is stable across 39101217095, 39115755033, 39117425713 and 39147198313. Cross-reference: accepted `repair_39101217095/F2_cache_provenance` discloses the earlier b81ab1a2 overwrite (20/24 cache files re-fetched live during run 39101217095).

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

**Environment:** producer-context only — packet_dir `/tmp/lex_accepted/product/results/product/gate_packet/38839347028/questions`. The engine itself is independently exercisable in `--adjudicate` mode on the vendored rebuilt packet (see Environment-Dependency Disclosure, item 3).

### 3. Label Lineage Gate Sweep (`evaluation.frozen_bars.run_label_lineage_gate`)

**Population:** 4 in-scope packets (38799024807, 38812599575, 38839347028, rebuilt-39027045675)

**Frozen Prediction Verification:**
- P1 (label gate parity on accepted lineage): PASS on all 3 packets
- P2 (accepted findings L2/L3/L4 closed): PASS
- P3 (minimal delta non-vacuity): PASS (flipped to red, population unchanged, blocks after)
- P4 (no false blocks): PASS
- P5 (off-lineage recorded): PASS (2 out-of-scope packets with reasons)
- P6 (frozen identity re-verified): PASS

**Verdict:** ALL_PREDICTIONS_HELD ✅ (producer-context; reads the ephemeral mount)

**Statement Defects (preserved from freeze, corrected by erratum):**
- P1 statement prose claimed "2 of 2 non-incumbent packets block" but predicted table blocks 1
- P4 predicted divergence against population-pinned count reading; actual divergence is against pin-removed counterfactual

### 4. Retrieval/Counter-Authority Falsification Benchmark (`evaluation.benchmark_retrieval_counter_authority`)

**Three legs, combined verdict: BENCHMARK_VALID_NO_FALSIFICATION** (producer-context; leg 1 reads the ephemeral mount, legs 2–3 read ephemeral `/tmp/ca_bench_*` packets)

| Leg | packet_dir | Expected Exit | Actual Exit | Verdict | Matches |
|-----|-----------|---------------|-------------|---------|---------|
| Served Baseline | `/tmp/lex_accepted/product/.../38839347028/questions` | 0 | 0 | PASS_NO_REGRESSION | ✅ |
| Geometry Falsification (hostile) | `/tmp/ca_bench_geom_moys2occ/hostile_geometry` | 1 | 1 | FAIL_REGRESSION | ✅ |
| Label Falsification (blanked evidence) | `/tmp/ca_bench_label_eckalsdz/blanked_evidence` | 1 | 1 | FAIL_REGRESSION | ✅ |

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

**Timing note (audit F5):** legs A–C are instrumented (5.514 + 5.518 + 5.380 = 16.412s); legs D and E record no `elapsed_s` and are labelled **not-instrumented** — no end-to-end preflight figure is asserted.

---

## Audit Readiness Checklist

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Frozen benchmark executes in < 2700s | ✅ PASS | 49.874s instrumented total << 2700s |
| Cached reproducibility verified | ✅ PASS (qualified) | Retrieval benchmark pass B identical **from committed cache — independently re-derivable**; the mount-dependent legs' executed status is producer-context only |
| Frozen rules SHA256 verified | ✅ PASS | All 4 frozen inputs match (re-hashed this run; independently re-derivable) |
| Negative controls proven | ✅ PASS (qualified) | Blanked-evidence & hostile-geometry controls proven in producer context; the same controls re-derived from committed bytes on the vendored rebuilt packet (`run_bar_gates --adjudicate`) |
| Frozen predictions verified | ✅ PASS (qualified) | ALL_PREDICTIONS_HELD on the lineage sweep (producer-context); preflight leg-E falsification documented per the freeze's success rule |
| Falsifications documented | ✅ PASS | Retrieval authority recall (FR/IT), duplicates 4/4, counter marker; retrieval rent-default duplicate divergence vs the accepted run of record; preflight leg E |
| No universal-174k benchmarks rerun | ✅ PASS | Only query-specific components used |
| Provenance preserved | ✅ PASS | All evidence_refs in `evaluation/state/evaluation.json` re-derived against the tree — every entry exists (repair-1 fix for the dangling `retrieval_counter_authority_benchmark/39098571937.json`, replaced by this run's existing CA records and report) |
| Results written to canonical paths | ✅ PASS | results/evaluation/*, reports/evaluation/* |

---

## Next Recommendation

**NO further same-question cycles justified.** The evaluation lane deliverable is:
1. **Complete** — minimal gate-able benchmark shipped and verified executable within the quantum
2. **Audit-ready** — all components execute, frozen inputs verified, results reproducible where independently re-derivable (see the Environment-Dependency Disclosure for the exact scope)
3. **Within quantum** — 49.874s instrumented << 2700s

The factory director may now decide the successor question. The standing accepted DO-NOT-SERVE order on packet 38839347028 remains in effect (owner_decision_required=FALSE per frontier-rebuilt-packet-serve-audit verdict).

---

## Machine-Readable State

Updated: `evaluation/state/evaluation.json` —
- `frozen_retrieval_benchmark_verification_39147198313`: this run's 23/11 with its own wall-times; the accepted 39098571937 block is byte-restored (0.068/0.068) and carries no `verified_run_id` beside counts it did not produce (audit F2)
- `frozen_bar_gates_verification_39147198313`: re-execution record; accepted wall-time 7.417 restored (audit F2)
- `label_lineage_gate`: corrected elapsed 12.9 -> 10.907 from the artefact (audit F5)
- `retrieval_counter_authority_benchmark`: `run_id` re-pointed 39098571937 -> 39147198313, the run that has records of file (audit F2/F4)
- `total_verification_wall_seconds`: 22.0 -> 49.874, re-derived from the artefact fields with the derivation published (audit F5)
- `evidence_refs`: the dangling `results/evaluation/retrieval_counter_authority_benchmark/39098571937.json` (never existed in any commit) replaced by existing anchors — this run's CA report and leg records; the whole array re-derived against the tree (audit F4)
- `audit_ready_qualification` added: the audit job can run; four of five components' executed status is producer-context only (audit F3)
- Canonical additive block `verification_39147198313` added to `state/evaluation.json` (audit F6; no existing key altered); `state_updated_at` refreshed to this cycle's write time (audit R3)
