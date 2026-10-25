# Operational resume 40213041041 -> 40217938706 - audit-ready snapshot

- Lane: evaluation
- Direction: v68
- Status: **AUDIT_READY_PENDING_INDEPENDENT_AUDIT** (producer-authored; no audit branch, no gate file, no verdict)
- Producer run: `40217938706` (operational resume of `40213041041`, itself a resume of `40209360877`)
- Resumed team snapshot under audit: `c11aff55cc4acaca30f5c5fe33f61c1dc603a174` (`evaluation cycle 40213041041 repair 0`)
- Prior snapshot: `9c5db64d8eb283a7566be96a9823827668991c39` (`evaluation cycle 40209360877 repair 0`)
- Accepted evaluation cycle: `40159747851` (gate unchanged)
- Continue recommended: **false**. No new same-question cycle, no standing-falsification re-run, no universal-174k rerun, both DO-NOT-SERVE orders stand, item (2) `NOT_YET_DISCRIMINATING`.
- Claim ceiling: operational-resume verification and append-only provenance remediation only. No quality measurement, no bar movement, no serve verdict, no admission, no acceptance.

## 1. Why this resume exists - orchestration, not the deliverable

Run `40213041041`'s producer team job succeeded end to end and persisted snapshot `c11aff55cc4acaca30f5c5fe33f61c1dc603a174`. Its independent-audit job failed before writing an audit branch or a gate. The identical signature now repeats on **five consecutive runs**:

| run | `Independent audit` step duration | later audit steps | integrate | resilience | audit ref |
|---|---|---|---|---|---|
| `40187594111` | **2704.0s** | skipped | skipped | success | none |
| `40192868113` | **2704.0s** | skipped | skipped | success | none |
| `40198184759` | **2704.0s** | skipped | skipped | success | none |
| `40204378896` | **2704.0s** | skipped | skipped | success | none |
| `40213041041` | **2704.0s** | skipped | skipped | success | none |

Mechanism (recorded, never edited): `origin/main:.github/scripts/run-ox-with-retry.sh:22` sets `WORK_QUANTUM_SECONDS=2700`; lines 180-187 sleep 15s, kill at `now-start >= 2700`, return 78. The quantum is an exact multiple of the 15s poll, so the boundary fires exactly 2700s after agent start; GitHub step overhead adds ~4s -> the observed 2704.0s. Five identical durations are the signature of a programmatic kill.

**Verdict:** `DIAGNOSIS_CONFIRMED` - 13/13 checks. Job logs are HTTP 403 unauthenticated and `GH_TOKEN` is unset, so no log line is quoted; the mechanism is inference from public run/jobs JSON (committed under `results/evaluation/operational_resume_40213041041/api/`) plus the checked-in wrapper.

## 2. Append-only remediation of the persisted snapshot

Run `40213041041` had overwritten claim-bearing artifacts named for run `40209360877` in place. Under factory-wide requirement 34 / AGENTS.md items 5-6 this is an append-only-evidence violation. This run:

- restored **15** overwritten paths to their `9c5db64d8eb283a7566be96a9823827668991c39` bytes and proved each by sha256;
- preserved every rewritten byte under `results/evaluation/operational_resume_40213041041/preserved_40213041041_rewrites/`;
- re-homed the added `_corrected`/`_final` artifacts under `results/evaluation/operational_resume_40213041041/rehomed_40213041041/` with `40213041041` as the authoring run;
- deleted nothing; the prior 40204378896 pack inventory remains byte-identical (`14/14`).

**Verdict:** `REMEDIATED_APPEND_ONLY` - 8/8 checks.

## 3. Ordered item (1): present and verified without re-running the falsifier

- Correction note: `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md` (sha256 `b10eeb3a720cd6352fbc7eabbf8d3430989b52d90193d0f948e69908ef5dc48d`)
- Follow-up citation: `reports/evaluation/CORRECTION_FOLLOWUP_CITATION_40198184759.md` (sha256 `8c3750a580dbc6554bdb6b8fd18a2d055520fc2a9590ebb177baec7b84fa3174`)
- Bundle: `results/product/offline_slice/20261024T142517Z/rent-default.bundle.json` sha256 `6eee1149b3c0ec23124746af482e15d9298c2120ee25de4bc4dd7e1cf7d93fa9`; `applied=True`, `n_candidates=1`, `n_selected=0`, `n_abstained=1`, `abstained_ids=['gr_gerichte_ERZ 2010 25']`, `abstention_reasons={'pivot_absent': 1}`; row `gr_gerichte_ERZ 2010 25` still `counter_evidence_verified=True`.
- Code: `product/query/pipeline.py:1339` = `if adversarial_retrieval:`; `:1343` = `audited = apply_verified_span_selection(`.
- Measurement of record `40105794124` unchanged: sha256 `fd25345b02da6658edbd5ed8722c69c9b3c7dbbc22e7856740cfdd421c5c4592` (`SOUND_COUNTER_ROW_PRESENT`, 4/5 defective, 1 sound row). **Falsifier not re-executed.**
**Verdict:** `PRESENT_AND_VERIFIED` - 17/17 checks.

## 4. Ordered item (2): NOT_YET_DISCRIMINATING

The accepted product mount is `29a5c4a548ba0ab8b6a8f574de1e732d17f3d109`. The H1 rejection/incumbent leg is landed (`product/query/counter_evidence_span.py` markers present), but H2 member-for-member regeneration of the frozen 15-member family is **false** (10/15, per-role multiplicity parity false). Per the frozen protocol no synthetic stand-in is substituted, packet `39319405429` is not scored and the standing falsification is not re-run.

## 5. This run's gates

| check | verdict | record |
|---|---|---|
| orchestration diagnosis | `DIAGNOSIS_CONFIRMED` | `results/evaluation/operational_resume_40213041041/diagnosis_40213041041.json` |
| append-only remediation | `REMEDIATED_APPEND_ONLY` | `results/evaluation/operational_resume_40213041041/append_only_remediation_40217938706.json` |
| deliverable verification | `DELIVERABLE_VERIFIED` | `results/evaluation/operational_resume_40213041041/deliverable_verification_40217938706.json` |
| state integrity (final) | `ALL_CHECKS_PASS` | `results/evaluation/operational_resume_40213041041/state_integrity_gate_40217938706_final.json` |
| targeted shim | `SHIM_PASS` | `results/evaluation/operational_resume_40213041041/pytest_targeted_40217938706.json` |
| multilingual/provenance shim | `SHIM_PASS` | `results/evaluation/operational_resume_40213041041/pytest_multilingual_provenance_40217938706.json` |

Total measured verification time: **2.198s** (0.0 min), far below the 2700s audit quantum. `pytest` is absent in the producer image; the shims count unsupported cases as NOT-RUN, never as passed.

## 6. Standing disclosures

- `40105794124` remains `SOUND_COUNTER_ROW_PRESENT` / `falsification_proven=false`; the 4/5 defect histogram is unchanged (D2 2, D3 2, D4 1 over 4 distinct decisions), sound row `bstger_SK.2023.49`.
- The historical `40144816305` record keeps its own `CORRECTION_NOT_CONFIRMED` verdict; the follow-up citation resolves CC6/CC7 at object level and does not turn that record into a pass.
- Both DO-NOT-SERVE orders remain in effect. Admission stays fail-closed. `human_gate_ready=false`, `machine_gate_ready=false`, `owner_decision_required=false`.
- No audit gate file is created here. Only the independent auditor may write `results/audit/evaluation/CYCLE_40217938706_GATE.json`.
