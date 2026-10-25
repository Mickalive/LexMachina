# Operational resume 40232590665 -> 40234421521 - audit-ready snapshot

- Lane: evaluation | Direction: **v68** | Mode: FAST MVP operational resume
- Status: **AUDIT_READY_PENDING_INDEPENDENT_AUDIT** (producer-authored; no audit branch, no gate file, no verdict for run `40234421521`)
- Resumed team snapshot: `0003921a0f35a35f516716eb10b3c3db99277f7d` (`evaluation cycle 40232590665 repair 0`)
- Prior snapshot: `bb75f263e7857a82f4c3f1322d12283d7365188e` (`evaluation cycle 40228275848 repair 0`)
- Accepted evaluation cycle: `40159747851` (unchanged)
- Continue recommended: **false** - no new same-question cycle, no standing-falsification re-run, no 174k rerun, both DO-NOT-SERVE orders stand, item (2) `NOT_YET_DISCRIMINATING`.

## 1. Diagnosis - a lane-scope validation failure, not a provider failure

**Verdict `DIAGNOSIS_CONFIRMED` - 18/18 checks.**

Run 40232590665 completed its producer lane cycle (Run lane cycle step success, 'Validate active MVP producer state' success, 'Clean generated junk' success) and FAILED at step 9 'Enforce lane write scope' (conclusion failure, sub-second). A byte-faithful re-execution of that step's classifier over the snapshot's own commit pair bb75f263 -> 0003921a reproduces exit 3 with exactly 3 bad paths, all three in the independent auditor's namespace (results/audit/evaluation/* and reports/audit/evaluation/*), while both FAST-MVP benchmark artifacts under results/evaluation/ classify IN scope. 'Persist team snapshot' runs with if: always(), so the snapshot was force-pushed; audit and integrate were skipped and no /audit ref exists for 40232590665, i.e. the run issued NO verdict. Root cause of the misplaced paths: evaluation/minimal_ca_falsify_benchmark.py defaulted its report dir to reports/audit/evaluation (the auditor's namespace), and the producer additionally authored a pseudo-audit gate there. This is a VALIDATION/LANE-SCOPE failure of the producer, not a provider failure, not a work-quantum starvation, not a gate REVISE/BLOCKED and not a product defect. The deliverable itself is intact.

| job | conclusion | note |
|---|---|---|
| team | failure | lane cycle + state validation + junk clean all **success**; step 9 `Enforce lane write scope` **failure** |
| audit | skipped | never started; no gate, no branch, **no verdict** |
| integrate | skipped | nothing promoted |
| resilience | success | dispatched this operational resume |

Byte-faithful re-execution of the failing step over this snapshot's own commit pair reproduces it exactly:

```
python -m evaluation.snapshot_audit.write_scope --lane evaluation \
  --repro-from-git bb75f263e7857a82f4c3f1322d12283d7365188e 0003921a0f35a35f516716eb10b3c3db99277f7d
-> SCOPE_VIOLATION, 3 bad paths:
   reports/audit/evaluation/CYCLE_40228275848.md
   reports/audit/evaluation/RETRIEVAL_CA_BENCHMARK_40228275848.md
   results/audit/evaluation/CYCLE_40228275848_GATE.json
```

Record: `results/evaluation/operational_resume_40234421521/write_scope_repro_40232590665.json`. The two FAST-MVP benchmark artifacts of that cycle classify **in scope**, i.e. the deliverable survived and only the namespace was wrong.

Root cause, fixed in this lane's own code (`.github/**` is control-plane scope and is NOT edited): `evaluation/minimal_ca_falsify_benchmark.py` defaulted `DEFAULT_REPORT_DIR` to `reports/audit/evaluation` - the independent auditor's namespace. Locked by `tests/evaluation/test_producer_scope_defaults.py` and by a strengthened `test_output_defaults_point_at_the_committed_tree`.

**Verdict `RELOCATED_APPEND_ONLY` - 5/5 relocation checks.** The three misplaced files are copied byte-for-byte under `results/evaluation/audit_namespace_recovery_40232590665/`, the benchmark report is additionally published at `reports/evaluation/RETRIEVAL_CA_BENCHMARK_40228275848.md`, and **nothing is deleted or rewritten in place** (AGENTS.md items 5-6; accepted precedent `audit_namespace_recovery_40182692670`).

> **Provenance warning.** `results/audit/evaluation/CYCLE_40228275848_GATE.json` claims `gate=PASS`, `safe_to_integrate=true`, `evidence_tier=ACCEPTED`. It is **producer-authored** on commit `0003921a0f35a35f516716eb10b3c3db99277f7d` and run `40228275848`'s own audit job **failed** at step `Independent audit` with no `/audit` ref. It does NOT satisfy factory-wide requirement 4 and must never be quoted as an independent audit of 40228275848.

## 2. Lane deliverable - verified, not re-derived

- Committed benchmark: `results/evaluation/minimal_ca_falsify_benchmark/40228275848.json` sha256 `5f5e4156976764be3cc40d79728a5ca11bfcee66bb41f8cbe13bcb26acc726c4` - **PRODUCT_FALSIFIED**, 18 gates, 11 passed, 4 failed.
- Frozen pins re-hashed after freeze: RULES_LABEL `4457e971df3dc5d1...`, RULES_GEOMETRY `a7452748d40c511a...`, mapping hypothesis `d1135f9f919140a3...`, wrapper freeze `431aa87b8abeaec3...` - all match.
- Fresh replay into scratch: **REPLAY_REPRODUCES** (6/6 checks, 0.3s, 0 input drift). Compared fields: 35; excluded with reason: run_id, generated_at_utc, engine_record_path, wrapper_instrument.sha256_commit_time.
- **Verdict `DELIVERABLE_VERIFIED` - 44/44 checks.**

## 3. Ordered item (1): PRESENT_AND_VERIFIED, measurement unchanged

- Correction note `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md`
- Follow-up citation `reports/evaluation/CORRECTION_FOLLOWUP_CITATION_40198184759.md`
- Machine record `results/evaluation/bypass_clause_correction/40144816305.json`
- Standing falsifier `results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json` re-hashed only - **not re-executed**.

## 4. Ordered item (2): NOT_YET_DISCRIMINATING at the CURRENT product head

The precondition was re-derived against the accepted product mount `02b1269d36928644d9be72512b543be00b341ff2` (pure set relation from the frozen instrument, two executions byte-equal):

- H1 rejection/incumbent leg landed: **true**
- H2 member-for-member family regeneration: **false** (`13/15` members, every frozen role covered=true, per-role multiplicity parity=false)
- Historical (accepted, product head `29a5c4a5`): **10/15** -> current: **13/15** - improved, still short; every frozen role is covered but `server/served` multiplicity is below the frozen family.

Per the frozen protocol the full item-(2) re-measure is **not** executed: no synthetic stand-in, no packet scored, no d2_path_scope_probe re-run, the standing falsification untouched. Status: **NOT_YET_DISCRIMINATING**.

## 5. This run's gates

| check | verdict | record |
|---|---|---|
| orchestration diagnosis | `DIAGNOSIS_CONFIRMED` | `results/evaluation/operational_resume_40234421521/diagnosis_40232590665.json` |
| audit-namespace relocation | `RELOCATED_APPEND_ONLY` | `results/evaluation/audit_namespace_recovery_40232590665/RELOCATION_RECORD.json` |
| deliverable verification | `DELIVERABLE_VERIFIED` | `results/evaluation/operational_resume_40234421521/deliverable_verification_40234421521.json` |
| benchmark replay | `REPLAY_REPRODUCES` | `results/evaluation/operational_resume_40234421521/benchmark_replay_comparison_40234421521.json` |
| item-(2) precondition | `NOT_YET_DISCRIMINATING` | `results/evaluation/operational_resume_40234421521/item2_precondition_40234421521.json` |
| command battery | `COMMANDS_PASS` (5/5) | `results/evaluation/operational_resume_40234421521/command_runtimes_40234421521.json` |
| state integrity (final) | `DEFERRED_TO_MACHINE_RECORD` | `results/evaluation/operational_resume_40234421521/state_integrity_gate_40234421521_final.json` |
| write scope, this run | `DEFERRED_TO_MACHINE_RECORD` | `results/evaluation/operational_resume_40234421521/write_scope_40234421521_final.json` |
| nested evidence refs, this run | `DEFERRED_TO_MACHINE_RECORD` | `results/evaluation/operational_resume_40234421521/nested_refs_final/40234421521_nested_evidence_refs.json` |
| state re-check after the final state write | `DEFERRED_TO_MACHINE_RECORD` | `python3 -m evaluation.state_integrity_gate --run-id 40234421521` |

This report is written before this run regenerates those four records, so it never restates a verdict it has not measured: the cell reads `DEFERRED_TO_MACHINE_RECORD` rather than a placeholder token. The authoritative results are the records named above, summarised in `results/evaluation/operational_resume_40234421521/AUDIT_INDEX_40234421521.json` under `final_state_gate` and in `state/evaluation.json` -> `operational_resume_40234421521.verification`.

Total measured verification time: **1.131s** (quantum 2700s). `pytest` is absent in the producer image; the shims count unsupported cases as NOT-RUN, never as passed.

## 6. Standing disclosures

- `40105794124` remains `SOUND_COUNTER_ROW_PRESENT` / `falsification_proven=false` (4/5 defective bundles, sound row `bstger_SK.2023.49`); the measurement is unchanged.
- Both DO-NOT-SERVE orders stand; admission stays fail-closed; `human_gate_ready=false`, `machine_gate_ready=false`, `owner_decision_required=false`.
- No frozen bar, rubric, threshold or verdict contract was read, moved or re-derived; RULES_LABEL/RULES_GEOMETRY are re-hashed only.
- The comparative map-vs-ranked-list half stays unscored while zero sound counter rows are evidenced on a serviceable packet.
- No audit gate file is created here: **only the independent auditor** may write `results/audit/evaluation/CYCLE_40234421521_GATE.json`.
- Network this cycle: public GitHub REST run/jobs metadata + one `ls-remote` probe per audit ref; no OpenCaseLaw, retrieval, model or benchmark-data call.

## 7. Recommended continuation

`continue_recommended=false` under the current v68 question: item (1) is discharged, item (2) stays non-discriminating until Core Product regenerates the frozen family member-for-member (`server/served` post-repair 2/4 at the accepted head), and the remaining ordered items are report-only. The Factory Director decides the successor question.
