# Operational resume 40209360877 — audit-ready snapshot

- Lane: evaluation
- Direction: v68
- Status: **AUDIT_READY_PENDING_INDEPENDENT_AUDIT** (this file is producer-authored; no audit branch, no gate file, no verdict)
- Producer run: `40209360877` (operational resume of `40204378896`, dispatched by run `40204378896`'s resilience job with `resume_from_run_id=40204378896`)
- Resumed team snapshot under audit: `14b9e9cf9d8c4d88f378fd8ae4281d3cbb18c2f5` (`evaluation cycle 40204378896 repair 0`)
- Prior snapshot: `251a6f5967c653d3ca93bf0a2d3ad7a1dd3f875e` (`evaluation cycle 40198184759 repair 0`)
- Accepted evaluation cycle: `40159747851` (gate `results/audit/evaluation/CYCLE_40159747851_GATE.json`, unchanged)
- Accepted product cycle: `40159523259` (mount head `29a5c4a548ba0ab8b6a8f574de1e732d17f3d109`)
- Continue recommended: **false**. No new same-question cycle, no universal-174k rerun, both DO-NOT-SERVE orders stand, item (2) `NOT_YET_DISCRIMINATING`.
- Claim ceiling: operational-resume verification and an orchestration diagnosis only. No quality measurement, no bar movement, no serve verdict, no admission, no acceptance.

## 1. Why this resume exists — the failure is orchestration, not the deliverable

Run `40204378896`'s **producer team job succeeded end to end** and persisted snapshot `14b9e9cf`. Its independent-audit job failed before writing an audit branch or a gate. The same signature now repeats on **four consecutive runs**:

| run | `Independent audit` step | step duration | later audit steps | integrate | resilience |
|---|---|---|---|---|---|
| `40187594111` | `11:37:56Z` → `12:23:00Z` (failure) | **2704.0s** | `Enforce audit scope and read gate` + `Persist audit snapshot` skipped | skipped | success → dispatched next |
| `40192868113` | `12:48:42Z` → `13:33:46Z` (failure) | **2704.0s** | skipped | skipped | success → dispatched next |
| `40198184759` | `14:08:34Z` → `14:53:38Z` (failure) | **2704.0s** | skipped | skipped | success → dispatched next |
| `40204378896` | `15:12:03Z` → `15:57:07Z` (failure) | **2704.0s** | skipped | skipped | success → dispatched **this** run |

On all four runs the team job is `success` and the audit job is `failure`; `git ls-remote --heads origin` shows **no** `refs/heads/cycle/core/evaluation/<run>/audit` for any of them (only `.../team` and `.../team-attempt-1`). **Those four runs issued no verdict.**

Mechanism (recorded, never edited — `.github/**` is control-plane scope): `origin/main:.github/scripts/run-ox-with-retry.sh:22` sets `WORK_QUANTUM_SECONDS="${LEX_AGENT_QUANTUM_SECONDS:-2700}"`; lines 180-187 are `sleep 15` then `now-start >= WORK_QUANTUM_SECONDS → kill_agent_group → return 78`. The quantum (2700) is an **exact multiple of the 15s poll**, so the boundary test first fires exactly 2700s after the agent session starts; the GitHub step clock also carries ~4s of step setup → the observed **2704.0s**. Four identical durations are the signature of a programmatic kill, not random provider behaviour.

**Evidence class.** GitHub's job-log endpoint returns HTTP 403 unauthenticated and `GH_TOKEN` is unset in this producer job, so **no log line is quoted anywhere in this pack**. The mechanism is inferred from (a) public run/jobs JSON committed under `results/evaluation/operational_resume_40209360877/api/`, (b) the checked-in wrapper, and (c) arithmetic. It is labelled inference in `diagnosis_40204378896.json` (`failure_class_confidence: high`, `log_evidence_available: false`). Failure class: **`ORCHESTRATION_WORK_QUANTUM_EXPIRED`**. This is not a producer failure, not a validation failure, not a gate `REVISE`/`BLOCKED` and not a product defect.

**Control-plane hardening, recorded not edited:** (1) raise `LEX_AGENT_QUANTUM_SECONDS` for the independent-auditor agent, split the audit into a short first pass, or hand the auditor a pre-verified pack — *this run publishes exactly that pack*; (2) export per-step durations publicly or grant the auditor an `actions:read` token so the next starvation is log-quotable instead of inferred.

## 2. Snapshot integrity — the prior pack is byte-preserved

`prior_pack_integrity_40209360877.json` → **`PACK_PRESERVED`, 5/5 checks**:

- `snapshot_preserved_as_head_or_ancestor` — `HEAD == 14b9e9cf` on branch `operational-resume`.
- `prior_pack_inventory_all_byte_identical` — **14/14** artifacts inventoried by `AUDIT_INDEX_40204378896.json` re-hash byte-identically (the prior hypothesis, freeze, instrument, API envelopes, diagnosis, snapshot-integrity, deliverable-replay, gate/shim records and the prior audit-ready report).
- `frozen_pins_and_measurement_of_record_unchanged` — `RULES_LABEL.json` = `4457e971…`, `RULES_GEOMETRY.json` = `a7452748…`, measurement of record `results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json` = `fd29a395…`.
- `freeze_pinned_inputs_unchanged` — **all 8** inputs this run froze before inspecting outcomes still hash to their frozen values at HEAD (both frozen rule pins, the measurement of record, the prior pack's `AUDIT_INDEX`/`summary`/report, and the falsifier's own frozen hypothesis and freeze record).
- `accepted_cycle_gate_in_tree` — accepted cycle `40159747851` gate present.

`state/evaluation.json` and `evaluation/state/evaluation.json` are **deliberately excluded** from byte identity: a resume necessarily advances them. Their prior bytes remain readable at `14b9e9cf`.

## 3. The frozen falsifier re-executes and reproduces

Instrument (pre-registered in `evaluation/OPERATIONAL_RESUME_40209360877_HYPOTHESIS_V1.json`, frozen in `..._FREEZE_V1.json`):

```
python3 -m evaluation.minimal_retrieval_ca_benchmark --run-id 40209360877 \
  --out-dir results/evaluation/operational_resume_40209360877/falsifier_replay_postfreeze \
  --report-dir results/evaluation/operational_resume_40209360877/falsifier_replay_postfreeze
```

which invokes `evaluation.mapping_free_recall_falsifier.run()`. Result: exit **1 = `PRODUCT_FALSIFIED`** (exit 1 is the VERDICT_CONTRACT here: 0 would be `PASS_NO_FALSIFICATION`, 2 vacuous), 18 gates / 11 passed / **4 failed**, the same four failed gate ids as the committed measurement of record, **byte-equal** `gates` and `per_question` payloads, `input_drift=[]`, product mount head `29a5c4a5`. `falsifier_replay_comparison_40209360877.json` → **`REPRODUCES`, 24/24 compared fields equal**. This re-executes an already-frozen measurement; it creates no new measurement and moves no bar.

**Execution-order disclosure (never back-dated).** `..._FREEZE_V1.json` records every pre-freeze observation: the public API envelopes were fetched while orienting; one exploratory falsifier pass and the four baseline gate/shim runs ran before the freeze. The recorded claim artifact is the **post-freeze** pass under `falsifier_replay_postfreeze/`; the pre-freeze pass is retained at `falsifier_replay/` and labelled. The comparison records that the two differ in exactly one field, `engine_record_path` (the output directory pointer), i.e. `identical_ignoring_output_directory_pointer: true`. Nothing about the gate predicates, thresholds or output names was chosen after seeing an outcome: the falsifier's own hypothesis (`d1135f9f…`) and freeze (`431aa87b…`) predate this run, and the engine re-hashes every frozen pin before and after execution inside the run.

## 4. This run's own gates (all pass at the state update)

| check | verdict | record |
|---|---|---|
| state integrity | `ALL_CHECKS_PASS` 11/11 | `state_integrity_gate_40209360877.json` |
| nested evidence refs | `NESTED_REFS_RESOLVED`, 0 unresolved | `nested_refs/40209360877_nested_evidence_refs.json` |
| lane write scope | `SCOPE_CLEAN`, 0 bad | `write_scope_40209360877.json` |
| targeted shim (reuse-first slice) | `SHIM_PASS` 39 passed, 0 failed, 12 unsupported | `pytest_targeted_40209360877.json` |
| multilingual/provenance shim | `SHIM_PASS` 26 passed, 0 failed, 2 unsupported | `pytest_multilingual_provenance_40209360877.json` |

The **record of record** for runtimes is `command_runtimes_40209360877.json`, written by the final `verify` pass, and it supersedes any wall-clock figure quoted here. The pass that preceded the state update measured the six commands at **2.314s in total** (falsifier 0.286s, state gate 0.041s, nested guard 0.117s, write scope 0.052s, targeted shim 1.474s, multilingual shim 0.344s); verdicts, counts and failed-gate ids are deterministic across passes, only wall-clock and `generated_at_utc` move. Disclosed for honesty: the *first, cold* execution of the targeted shim alone in a fresh image measured **91s** (page cache and bytecode cold) — even at that figure the whole pack re-executes in roughly two minutes, still an order of magnitude below the 2700s work quantum that starved four audits. That is the point of this pack: an auditor can re-verify it inside one short step.

**Standing disclosures, not withdrawn.** `pytest` is absent in the producer image; `SHIM_PASS` is produced by `evaluation.no_pytest_runner.py`, which counts unsupported cases as NOT-RUN and never as passed, so the counts are an upper bound on what pytest would execute, and the snapshot-audit READY verdict stays conditional on that absence. `test_cross_lingual_alignment_v10.py` reports `ModuleNotFoundError: No module named 'numpy'`; `test_disclosure_provenance_crosscheck.py` executed 0 cases (class-based, not collected by the shim) — neither is counted as a pass. A negative result outside this run's targeted set is preserved as evidence: `tests/evaluation/test_operational_resume_40094203248.py` scores `SHIM_FAIL` (4 passed, 1 failed) **at the resumed snapshot**, because `state/evaluation.json` carries no `run_identity_history` key for `test_state_run_identity_and_posture` to assert against. That defect is pre-existing (this run did not remove the field) and outside the pre-registered command set; it is recorded here rather than hidden.

## 5. Posture is unchanged

- `accepted_run_id` = `40159747851`, `direction_version` = `68`, `evidence_tier` = `ACCEPTED`, `cycle_status` = `COMPLETE`.
- `continue_recommended` = `false`, `human_gate_ready` = `false`, `machine_gate_ready` = `false`; **both DO-NOT-SERVE orders stand**.
- Item (1) `PRESENT_AND_VERIFIED`, measurement unchanged (`SOUND_COUNTER_ROW_PRESENT`, `falsification_proven=false`, 4/5 enriched bundles defective, exactly 1 sound row `bstger_SK.2023.49`).
- Item (2) `NOT_YET_DISCRIMINATING` (10/15 member-for-member, multiplicity parity false, post-repair record `NOT_MEASURED_VACUOUS`).
- No new same-question cycle, no universal-174k rerun, no frozen bar moved, no serve verdict issued, no admission flag flipped.

## 6. Network disclosure

`no_network_calls` was already `false` before this run. This run added only: (a) unauthenticated HTTPS `GET https://api.github.com/repos/Mickalive/LexMachina/actions/runs/<id>[/jobs]` for the five runs named in §1, and (b) five `git ls-remote --heads origin refs/heads/cycle/core/evaluation/<run>/audit` probes. **No OpenCaseLaw, retrieval corpus, benchmark data or model call.** The envelopes are committed under `results/evaluation/operational_resume_40209360877/api/`, so the diagnosis re-derives offline from them plus the wrapper.

## 7. Where everything is

- Instrument: `evaluation/operational_resume_40209360877.py` (`prepare` → `verify` → `finalize`)
- State updater: `evaluation/state_update_40209360877.py`
- Hypothesis / freeze: `evaluation/OPERATIONAL_RESUME_40209360877_HYPOTHESIS_V1.json`, `..._FREEZE_V1.json`
- Diagnosis: `results/evaluation/operational_resume_40209360877/diagnosis_40204378896.json`
- Prior-pack integrity: `.../prior_pack_integrity_40209360877.json`
- Replay comparison: `.../falsifier_replay_comparison_40209360877.json`
- Runtimes (record of record): `.../command_runtimes_40209360877.json`
- Summary + hash index: `.../summary_40209360877.json`, `.../AUDIT_INDEX_40209360877.json`

### Auditor's three-command checklist (identical to `auditor_shortcut` in `AUDIT_INDEX_40209360877.json`)

```bash
python3 evaluation/operational_resume_40209360877.py verify     # six pre-registered commands, expected exits pre-registered
python3 evaluation/operational_resume_40209360877.py prepare   # diagnosis + pack integrity + replay comparison
python3 evaluation/operational_resume_40209360877.py finalize  # 24 final checks -> status
sha256sum -c <(python3 -c "import json;[print(f\"{r['sha256']}  {r['path']}\") for r in json.load(open('results/evaluation/operational_resume_40209360877/AUDIT_INDEX_40209360877.json'))['artifact_inventory']]")
git ls-remote --heads origin 'refs/heads/cycle/core/evaluation/*/audit'   # still absent for the four starved runs
```

`prepare` and `verify` re-stamp `generated_at_utc`, so a re-run intentionally produces a *fresh* record with a different byte hash. The `diagnosis_sha256` / `prior_pack_integrity_sha256` / `falsifier_replay_comparison_sha256` fields in the state block authenticate the **committed** bytes; after a re-run compare the check verdicts and the check lists field-by-field rather than the file hash. The `sha256sum -c` line above is the byte-level check and must be run against the committed index, before any re-run.

## 8. What this pack does NOT claim

No independent audit was performed by this run; no `/audit` branch, no gate file and no verdict is created here — only the independent auditor produces those. No frozen absolute LABEL_SOUND / GEOMETRY_SOUND bar is re-scored or moved. No serve verdict, no admission, no acceptance, no new same-question cycle, no 174k benchmark. A `DIVERGENCE` intermediate from an early `finalize` (before the state update carried `github_run=40209360877`) is overwritten in-run by the final `AUDIT_READY_PENDING_INDEPENDENT_AUDIT` pass and is not committed; the committed artifacts are the final ones.
