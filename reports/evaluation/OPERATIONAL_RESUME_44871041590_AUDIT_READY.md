# Operational Resume — Evaluation Lane (run 44871041590)

- **Lane**: evaluation
- **Resume run**: 44871041590 (GitHub Actions, core-lane operational-resume)
- **Resumed run**: 44870941002
- **Resumed snapshot**: `9329f39a9f5b8643f90ea6f0dbd23b837953cc68` (`origin/cycle/core/evaluation/44870941002/team`, also team-attempt-1)
- **Prior equivalent snapshot**: same commit also published as `44870660846/team`
- **Direction version**: 68 (v68, unchanged)
- **Accepted evaluation state**: `accepted_run_id=40258497460`, `cycle_status=COMPLETE`, `continue_recommended=false` (state/evaluation.json, unchanged by this resume except as not required; no state change made)
- **Product mount head (verify)**: `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83` (`/tmp/lex_accepted/product`, accept 40284658455)

## 1) Failure diagnosis (orchestration/validation, not measurement)

**Failure class**: `PRODUCER_WRITE_SCOPE_VIOLATION_AUDIT_NAMESPACE` (high confidence).

The persisted producer snapshot for 44870941002 is commit `9329f39a` and contains 13 files. Four of those files are in independent-auditor namespaces, which are outside producer write scope:

- `reports/audit/evaluation/CYCLE_44870538384.md`
- `reports/audit/evaluation/CYCLE_44870660846.md`
- `results/audit/evaluation/CYCLE_44870538384_GATE.json`
- `results/audit/evaluation/CYCLE_44870660846_GATE.json`

Core-lane producer scope allows only `evaluation/**`, `tests/evaluation/**`, `results/evaluation/**`, `reports/evaluation/**`, `state/evaluation.json`, `data/evaluation/**`. The workflow “Enforce lane write scope” step rejects audit-namespace paths in producer snapshots, causing validation/orchestration failure before independent audit/integrate can complete. This is **not** a product defect, **not** a measurement defect, and **not** a REVISE/BLOCKED gate verdict.

Evidence: `git show --name-only 9329f39a`, git refs for 44870941002/44870660846/44870538384, and core-lane workflow scope rules. GitHub job logs were not fetched (`GH_TOKEN`/`GITHUB_TOKEN` unset in producer env; `gh auth` unavailable); diagnosis is based on committed tree and control-plane scope.

## 2) Remediation applied (audit-ready)

- Preserved byte-identical provenance copies under `results/evaluation/operational_resume_44871041590/`:
  - `CYCLE_44870538384.relocated.md`
  - `CYCLE_44870660846.relocated.md`
  - `CYCLE_44870538384_GATE.relocated.json`
  - `CYCLE_44870660846_GATE.relocated.json`
- Removed the four out-of-scope files from audit namespaces in the working tree/snapshot.
- Recorded diagnosis in `results/evaluation/operational_resume_44871041590/diagnosis_44870941002.json` and summary in `results/evaluation/operational_resume_44871041590/summary_44871041590.json`.

**Important**: relocated gate files are provenance copies from the producer snapshot; they are **not** independent-audit gates produced by an audit job. This resume creates no audit branch and no gate.

## 3) Deliverable verification (no measurement change)

The minimal retrieval/counter-authority falsification benchmark deliverable is present and reproducible on the accepted V3 packet-of-record bytes (39319405429):

- Existing preserved records: `44870660846` and `44870538384` both `PRODUCT_FALSIFIED`, 18 gates / 11 passed / 4 failed, same 4 failed gates (concept coverage de-kapitalverletzung; counter-authority surface empty on de/fr/it). Product mount head `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83`.
- Smoke rerun (scratch out): `python -m evaluation.minimal_ca_falsify_benchmark --run-id 44871041590_smoke --out-dir /tmp/lex_smoke_eval --report-dir /tmp/lex_smoke_eval` -> exit 1, `PRODUCT_FALSIFIED`, 18/11/4, same 4 failed gates, `run_valid=true`, `input_drift=[]`, same product mount head. Matches prior measurement.

## 4) v68 ordered-work status (no overclaim)

- **Item 1 (report-only correction of record, 40105794124 bypass clause)**: `PRESENT_AND_VERIFIED` as previously recorded (`reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md`, `results/evaluation/bypass_clause_correction/40113448025.json`). Not re-run, not changed.
- **Item 2 (conditional re-measure)**: `NOT_YET_DISCRIMINATING` for this resume — no new full-family post-repair product regeneration landed as the v68 P0 acceptance target; this resume does not synthesize a stand-in and does not re-run the standing falsification as a substitute.
- **Item 3 (standing falsification record)**: preserved; PRODUCT_FALSIFIED on packet 39319405429 remains the record of record; counter-authority yield negative is a frozen-marker-rule measurement on evaluation’s producer, not Core Product’s counter channel.
- **Item 4**: report-only / unchanged.
- **Item 5**: no new same-question cycle that re-derives closed work; this resume is operational/scope remediation only.

## 5) Posture / claim ceiling

- Both DO-NOT-SERVE orders stand. No serve verdict issued.
- `human_gate_ready=false`, `machine_gate_ready=false`. No posture flag flipped.
- No frozen bar, rubric, threshold, or verdict contract edited. No 174k benchmark rerun.
- frontier-counter-evidence-content-filter remains TERMINATED and is not consulted/adopted/re-verified.
- The comparative map-versus-ranked-list question remains vacuous until evidenced sound counter rows exist on a serviceable packet.
- `continue_recommended=false` in state/evaluation.json remains correct; this is an operational resume to make the snapshot audit-ready, not a same-question measurement cycle.

## 6) Files touched by this resume

- Added: `results/evaluation/operational_resume_44871041590/*` (diagnosis, relocated provenance copies, summary)
- Added: `reports/evaluation/OPERATIONAL_RESUME_44871041590_AUDIT_READY.md`
- Removed from audit namespaces (out-of-scope in producer snapshot): the four files listed in §1/§2.
- No changes to frozen instruments, measurements, thresholds, or state/evaluation.json.
