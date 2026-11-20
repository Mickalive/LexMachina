# Operational resume of run 44642554373 (run 44642744588)

- Lane: evaluation; direction v68; mode OPERATIONAL_RESUME
- Snapshot: `ea98384e54d31d2e694c418a1d1ce5769fc6c32f` ('accept evaluation cycle 40265377500')
- Product mount: `/tmp/lex_accepted/product` at `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83` (accept cycle 40284658455)
- Verdict: **RESUME_VERIFIED_AND_AUDIT_READY**

## What happened

Run 44642554373 failed at the producer step, not at validation. The public REST capture and job-page annotation show:

- run conclusion `failure`, event `workflow_dispatch`, head `b132288c`;
- team job `135977000346` step 6 `Run lane cycle` failed after 16s with `Process completed with exit code 1.`;
- `audit` and `integrate` were **skipped**; `resilience` succeeded;
- no `cycle/core/evaluation/44642554373/audit` ref, no gate, no report, and no verdict were produced;
- the persisted team snapshot remained `ea98384e` byte-identical.

This is `ORCHESTRATION_RC1_NONZERO_EXIT`, not the rc-67 zero-delta guard, not a 64-77 preflight, not rc-78 work-quantum, and not the step-9 write-scope check (skipped). Log download is still HTTP 403 without admin rights; mechanism attribution beyond the checked-in wrapper is not claimed.

## v68 ordered item (1): correction of record

The correction report `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md` (`b10eeb3a720c`) and machine record `results/evaluation/bypass_clause_correction/40144816305.json` (`2e691dd02c7b`) are present and internally consistent. The accepted bundle `20261024T142517Z/rent-default.bundle.json` is `6eee1149b3c0` and its span provenance still shows `applied=true`, `n_selected=0`, abstained id `gr_gerichte_ERZ 2010 25`, reason `pivot_absent`. The current mount routes `apply_verified_span_selection` under `if adversarial_retrieval:` (apply line 1404, guard line 1400); the old combined gate is absent; `offline_slice.py` still passes `fixture_generation=True`. The 4 defective rows and the 1 sound row remain `counter_evidence_verified=true` because the incumbent was left in place.

## v68 ordered item (2): precondition only, NOT executed

Frozen `precondition_gate` on the current mount: **H1 leg landed = True**, **H2 full family regenerated = False**, member-for-member **14/15**.

- post-repair roles: `{"offline/business-judgment-rule": 10, "offline/corporate-criminal-liability": 9, "offline/petty-theft-dismissal": 9, "offline/rent-default": 18, "server/served": 3}`
- matched per role: `{"offline/business-judgment-rule": 0, "offline/corporate-criminal-liability": 0, "offline/petty-theft-dismissal": 0, "offline/rent-default": 11, "server/served": 3}`
- Product's own 4-offline + 1-server claim is satisfied, but that is a different set from the direction's named 15-member family and is not substituted.

**Status: `NOT_YET_DISCRIMINATING`.** No packet-of-record 39319405429 scoring, no `d2_path_scope_probe` replay, no synthetic stand-in, and no full item-(2) re-measure was run. A READY status would have required a separately frozen claim-bearing cycle.

## Standing falsification record

`results/evaluation/fast_mvp_current_head_ca_falsifier/40105794124.json` (`fd25345b02da`) is read as committed evidence only. Verdict `SOUND_COUNTER_ROW_PRESENT`, exit 0, `falsification_proven=false`, 5 verified rows, 4 defective over 4 distinct decisions (D2 2 / D3 2 / D4 1), one sound row `bstger_SK.2023.49`. The engine was **not** re-executed.

## State reconciliation

`accepted_run_id` advances `40258497460 -> 40265377500` on **both halves** (`CYCLE_40265377500_GATE.json` gate PASS and accept commit `ea98384e54d31d2e694c418a1d1ce5769fc6c32f`). `github_run`/`proposed_run_id` become `44642744588` pending independent audit. The stale proposed run `40261335674` never acquired an audit gate or accept commit and is superseded as the pointer; it is preserved as history, not promoted.

## Controls

- `C1_snapshot_mutation_detected`: HOLD - flipping the head sha makes the relation false
- `C2_annotation_mutation_detected`: HOLD - exit code 1 -> 67 makes the metadata check false
- `C3_span_mutation_detected`: HOLD - n_selected 0 -> 1 is reported as a divergence
- `C4_measurement_mutation_detected`: HOLD - n_defective 4 -> 3 diverges from the freeze pin
- `C5_no_falsifier_reexecution`: HOLD - instrument source imports/invokes none of the falsifier engine
- `C6_item2_rule_consistency`: HOLD - READY requires H1+H2+15/15; NOT_YET requires a shortfall
- `C7_state_pointer_bridge`: HOLD - accepted_run_id==40265377500, gate exists, accept subject matches
- `C8_write_scope`: HOLD - all current producer paths are in-scope; a producer audit gate path is rejected

## Claim ceiling

Operational provenance and state reconciliation over committed accepted artifacts plus a read-only re-derivation of the frozen item-(2) precondition. It adds no quality measurement, moves no bar, issues no serve or admission verdict, and makes no legal-usefulness or human-gate claim.

## Reproduce

```bash
python3 evaluation/operational_resume_44642744588.py --mount /tmp/lex_accepted/product
python3 -m pytest -q tests/evaluation/test_operational_resume_44642744588.py
python3 evaluation/operational_resume_44642744588.py --apply-state
python3 -m evaluation.state_integrity_gate
python3 -m evaluation.snapshot_audit.write_scope --lane evaluation
python3 -m evaluation.nested_evidence_refs_guard
```
