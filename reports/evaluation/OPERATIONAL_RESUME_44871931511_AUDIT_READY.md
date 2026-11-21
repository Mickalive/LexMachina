# Operational Resume — Evaluation Lane (run 44871931511)

- **Lane**: evaluation
- **Resume run**: 44871931511 (GitHub Actions, `LEX Core Lane`, `resume_from_run_id=44871041590`, `repair_round=0`)
- **Resumed run**: 44871041590
- **Resumed snapshot**: `f0d00438db90436898d98624727b24f79aa731ef` (`origin/cycle/core/evaluation/44871041590/team`)
- **Direction version**: 68 (v68, unchanged)
- **Accepted base**: `origin/lab/evaluation` = `ea98384e` (`accept evaluation cycle 40265377500`)
- **Accepted evaluation state**: `accepted_run_id=40258497460`, `cycle_status=COMPLETE`, `continue_recommended=false`, `evidence_tier=ACCEPTED` — **not advanced** by this resume (nothing is accepted this run)
- **Product mount head (verify)**: `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83` (`/tmp/lex_accepted/product`)
- **Verdict of this resume**: `VERIFICATION_PASS` (10/10 checks), snapshot scope-clean, `AUDIT_READY_PENDING_INDEPENDENT_AUDIT`

## 1) Failure diagnosis of run 44871041590 (orchestration/validation, not measurement)

**Failure class**: `PRODUCER_WRITE_SCOPE_GUARD_CATCH22_ON_AUDIT_NAMESPACE_DELETION` (high confidence on step/mechanism; the exact printed path list is an inference — see below).

Read from the GitHub REST record (public repo, unauthenticated):

| run | team failed step | exit | audit | integrate | coincident producer delta |
|---|---|---|---|---|---|
| 44869867193 | Enforce lane write scope | 3 | skipped | skipped | added `results/audit/evaluation/CYCLE_44869867193_GATE.json` (`f6401f60`) |
| 44870225032 | Enforce lane write scope | 3 | skipped | skipped | added `reports/audit/evaluation/CYCLE_44869867193.md` (`41f01308`) |
| 44870538384 | Run lane cycle | 1 | skipped | skipped | none (branch unchanged) |
| 44870660846 | Enforce lane write scope | 3 | skipped | skipped | added 4 audit-namespace files (`9329f39a`) |
| 44870941002 | Run lane cycle | 1 | skipped | skipped | none (branch unchanged at `9329f39a`) |
| **44871041590** | **Enforce lane write scope** | **3** | **skipped** | **skipped** | **relocated the 4 audit-namespace files as R100 renames (`f0d00438`)** |

For 44871041590 specifically, every substantive step SUCCEEDED before the failure: `Validate lane and initialize working base`, `Mount accepted peer evidence`, `Install Ox/OpenCode`, **`Run lane cycle`**, **`Validate active MVP producer state`**, `Clean generated junk`. The only failing step is `Enforce lane write scope`, with annotations `Process completed with exit code 3.` and `lane crossed protected scope:`. `Persist team snapshot` then ran `if: always()`, committed the dirty state as `f0d00438` and force-pushed the team branch. `audit` and `integrate` were **skipped** (`needs: team; if needs.team.result == 'success'`), and `resilience` dispatched this resume one second later (run created `2026-11-21T05:40:01Z`).

**Mechanism (the catch-22).** The guard is:

```bash
while IFS= read -r line; do
  p="${line:3}"
  case "$p" in evaluation/*|tests/evaluation/*|results/evaluation/*|reports/evaluation/*|state/evaluation.json|data/evaluation/*|"") ;; *) BAD+="$p\n" ;; esac
done < <(git status --porcelain -uall)
[[ -z "$BAD" ]] || exit 3
```

It rejects **every** porcelain line whose path is outside producer scope — including `D ` deletions and `R  old -> new` rename lines. Because `Persist team snapshot` commits exactly the dirty state the guard saw, `git diff --name-status 9329f39a..f0d00438` is a complete capture of what the guard saw: four R100 renames whose OLD paths are all under `reports/audit/evaluation/` and `results/audit/evaluation/` (out of scope), plus new files under `reports/evaluation/` and `results/evaluation/` (in scope). The non-empty `BAD` set is therefore exactly those four audit-namespace paths. **The remediation itself trips the guard**: a producer that owns out-of-scope audit-namespace files can only become scope-clean by deleting or moving them, and both operations produce out-of-scope porcelain lines.

**Hedge on provenance**: job logs are HTTP 403 unauthenticated (`GH_TOKEN`/`GITHUB_TOKEN` unset, `gh` not logged in), so the step identity, exit code and annotation messages are READ facts while the exact `BAD` path list is an INFERENCE from the committed delta plus the guard source. Full record: `results/evaluation/operational_resume_44871931511/diagnosis_44871041590.json`.

**What this is not**: not a gate verdict (no `cycle/core/evaluation/44871041590/audit` ref exists anywhere; none of the six runs in the chain issued a verdict), not a measurement failure, not a product defect, not a provider/model failure, not a zero-delta rc-67. `.github/**` is control-plane scope and is **recorded, not edited**; the suggested upstream fix (exempt pure deletions, or evaluate scope as the tree diff versus `origin/lab/<lane>`) is in the diagnosis record.

## 2) Remediation applied (audit-ready, catch-22 avoided)

Two audit-namespace files that `f0d00438` still carried — and that the accepted base `origin/lab/evaluation` does **not** contain — are re-homed **byte-identically** (AGENTS.md items 5/6 and the F-3B append-only-evidence convention; nothing is deleted):

| source (removed from audit namespace) | re-homed copy | sha256 (worktree = relocated = introducing commit) |
|---|---|---|
| `reports/audit/evaluation/CYCLE_44869867193.md` (19300 B, from `41f01308`, run 44870225032) | `results/evaluation/operational_resume_44871931511/CYCLE_44869867193.relocated.md` | `6ac0aeefaa5f09425b89490f1d83c671ccd8f20b10f9007cd63718b5d59990f1` |
| `results/audit/evaluation/CYCLE_44869867193_GATE.json` (2734 B, from `f6401f60`, run 44869867193) | `results/evaluation/operational_resume_44871931511/CYCLE_44869867193_GATE.relocated.json` | `a05ee14be2d3f2249824c9a11ad43afb9e2612cbfea7330591d7a7249a088db8` |

Record: `results/evaluation/operational_resume_44871931511/RELOCATION_RECORD.json`.

**The removal is COMMITTED inside the agent phase** (commit `41da77e8`), so `git status --porcelain -uall` carries no out-of-scope line when the workflow guard runs. Leaving these deletions uncommitted is exactly what made run 44871041590 exit 3.

**Provenance disclosure**: the re-homed GATE carries `gate=REVISE, safe_to_integrate=true` but was authored in the PRODUCER namespace; no `/audit` ref exists for 44869867193, so it was never an independent-audit product of the workflow. It is preserved as provenance of what that producer committed, is **not** treated as an independent audit verdict and is **not** quotable as a gate of record.

**Tree-level result**: `git diff --name-only origin/lab/evaluation HEAD` now contains **zero** paths under `reports/audit/` or `results/audit/` — the snapshot's entire delta against the accepted base is inside producer scope.

## 3) Deliverable verification (FAST-MVP retrieval/counter-authority benchmark)

The smallest executable falsification benchmark was re-executed on the frozen instrument (sha256 `d06909e9…` wrapper / `58a2e77a…` engine) against the V3 packet-of-record `39319405429` and product mount `7be4480e`:

```
python -m evaluation.minimal_ca_falsify_benchmark --run-id 44871931511_verify \
  --out-dir results/evaluation/operational_resume_44871931511 \
  --report-dir results/evaluation/operational_resume_44871931511
```

- exit 1, **`PRODUCT_FALSIFIED`**, `falsification_proven=true`, `run_valid=true`, `input_drift=[]`
- 18 gates / 11 passed / 4 failed, **identical failed-gate set** to committed records `44870660846`, `44870538384` and smoke `44871041590_smoke`:
  - `mf::concept_coverage::39319405429::de-kapitalverletzung`
  - `mf::counter_authority_surface::39319405429::de-kapitalverletzung`
  - `mf::counter_authority_surface::39319405429::fr-bail-entretien`
  - `mf::counter_authority_surface::39319405429::it-responsabilita-medica`
- product mount head unchanged (`7be4480ed3ca623b77ea082404ca3b5b7ac5ee83`), claim ceiling byte-equal to the committed record
- **Claim ceiling**: verification re-execution of an already-frozen instrument. This is **not** a second independent falsification, not a re-score and not a serve verdict.

Test harness: `python evaluation/no_pytest_runner.py --test-file tests/evaluation/test_minimal_ca_falsify_benchmark.py` → **SHIM_PASS 8 passed / 0 failed / 0 skipped / 0 unsupported** (pytest is not installed in this image; the established no-pytest runner is used, as in prior resumes).

Machine record: `results/evaluation/operational_resume_44871931511/verification_44871931511.json` → **`VERIFICATION_PASS`, 10/10 checks**, covering: reproduction equality against all three committed records, expected failed-gate set, claim-ceiling equality + fail-closed markers, freeze-pin re-hash (instruments, comparison targets, both relocated files), relocation byte-identity with source removal, tree-diff audit-namespace emptiness, guard-predicate simulation (`n_bad=0`), item-(1) correction-of-record presence, posture fail-closed, and the direction-version pin `68`.

## 4) v68 ordered-work status (no overclaim)

- **Item 1 (report-only correction of record, 40105794124 bypass clause)**: `PRESENT_AND_VERIFIED` — `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md` (sha256 `b10eeb3a…`, matches the prior resume's inventory) and `results/evaluation/bypass_clause_correction/40113448025.json` both present. Not re-run, not changed.
- **Item 2 (conditional re-measure)**: `NOT_YET_DISCRIMINATING` — Core Product has not landed the rejection/incumbent leg plus a regenerated full flagship family as the v68 acceptance target. No synthetic stand-in, no substitute re-run of the standing falsification.
- **Item 3 (standing falsification record)**: **UNCHANGED** — `PRODUCT_FALSIFIED` on packet-of-record `39319405429` remains the record of record; superseded only by a NEW pre-registered falsification on NEW bytes. The counter-authority yield negative (2/4 frozen questions with zero candidate counter labels under the frozen marker rule) stays recorded as a measurement of the frozen marker rule's lexical yield on **this lane's own producer**, never Core Product's counter channel, in either direction.
- **Item 4**: report-only / unchanged — the three non-blocking required fixes of `CYCLE_39965089504_GATE.json` are reported only where those counts are quoted.
- **Item 5**: honoured — this resume is operational scope remediation plus verification; it re-derives no closed work and is recorded as **operational, not as new evidence**.

## 5) Posture / claim ceiling

- Both DO-NOT-SERVE orders stand. No serve verdict issued or re-run.
- `human_gate_ready=false`, `machine_gate_ready=false`, `packet_admitted=false`, `ready_for_owner_session=false`, `owner_decision_required=false`. No posture flag flipped.
- No frozen bar, rubric, threshold, predicate or verdict contract edited; no measurement record overwritten; no 174k benchmark rerun.
- `frontier-counter-evidence-content-filter` remains TERMINATED and is not consulted, adopted or re-verified; the counter-anchor classifier build stays closed.
- The comparative map-versus-ranked-list half remains unscored while zero sound counter rows are evidenced on a serviceable packet.
- `continue_recommended=false` in `state/evaluation.json` remains correct: no further same-question cycle has a discriminating purpose until Product lands the rejection/incumbent leg and regenerates the full flagship family.
- `accepted_run_id` stays `40258497460`. This resume advances no acceptance pointer; it is `AUDIT_READY_PENDING_INDEPENDENT_AUDIT`, `accepted_as_evidence=false`, `evidence_tier=EXPLORATORY` for its own operational record.

## 6) Files touched by this resume

- Added: `evaluation/OPERATIONAL_RESUME_44871931511_{HYPOTHESIS,FREEZE}_V1.json`, `evaluation/operational_resume_44871931511.py`, `evaluation/state_update_44871931511.py`
- Added: `results/evaluation/operational_resume_44871931511/*` (diagnosis, relocation record, verification, benchmark re-execution records, no-pytest shim record, summary, nested-refs guard record, write-scope record)
- Added: `reports/evaluation/OPERATIONAL_RESUME_44871931511_AUDIT_READY.md`, `reports/evaluation/RETRIEVAL_CA_BENCHMARK_44871931511_verify.md`
- Re-homed (byte-identical, committed in-agent): the two files in §2 moved out of `reports/audit/evaluation/` and `results/audit/evaluation/`
- Updated additively: `state/evaluation.json` and `evaluation/state/evaluation.json` (new resume record, appended `evidence_refs`, new `next_recommendation`; pinned identity fields untouched)
- No changes to frozen instruments, measurements, thresholds, rubrics, bars or serve posture.
