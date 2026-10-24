# Evaluation — operational resume of run 40040574595 (run 40044626742)

**Lane:** evaluation (query-map MVP falsifier) · **Direction:** v65 · **Run:** 40044626742
**Mode:** operational resume (`resume_from_run_id=40040574595`; branch `operational-resume` seeded at `e9f3f379`)
**Verdict:** `RESUME_VERIFIED_AND_AUDIT_READY` — the producer snapshot of 40040574595 **reproduces under independent re-execution, normalized-identical (0 diffs)**, and one state-pointer hygiene defect is corrected with disclosure.
**Freeze-first:** this run's hypothesis + pre-registered verification plan V1–V6 + orchestration diagnosis committed at `23459653` **before** any claim-bearing re-execution of this run.
**Posture (unchanged, fail-closed):** `human_gate_ready=false`, `machine_gate_ready=false`, `packet_admitted=false`, `ready_for_owner_session=false`, `owner_decision_required=false`. Both DO-NOT-SERVE orders stand. No bar, rubric, threshold or verdict contract was edited, applied or re-derived; no 174k benchmark rerun; no historical record overwritten.

---

## 1. Orchestration failure of run 40040574595 — diagnosed

All facts below are measured from git evidence; the rc attribution is hedged because job logs are not readable from this producer environment.

| fact | evidence |
|---|---|
| The producer froze correctly | commit `d2649360` (00:12:45Z, producer-authored): hypothesis + freeze record + instrument + guard tests, before any claim-bearing byte |
| The producer finished its work | result `generated_at=00:12:55Z`; `state/evaluation.json state_updated_at=00:18:03Z` |
| The producer never committed its results | the only commit carrying the 11 result/report/state files is `e9f3f379` (00:21:52Z) with the **workflow Persist-team-snapshot step's** mechanical message `"evaluation cycle 40040574595 repair 0"` and bot author `lex-evaluation-team` |
| The team job concluded non-success | audit runs only `if: needs.team.result == 'success'`; no `cycle/core/evaluation/40040574595/audit` branch exists; no `CYCLE_40040574595_GATE.json` exists anywhere; `lab/evaluation` still at `5c21f6bd` |
| The failing step was "Run lane cycle" | every other step would pass: state validation (direction 65, COMPLETE), write scope (leftovers all in-lane), persist snapshot (it demonstrably ran) |

**Most probable cause:** `rc-78 LEX_WORK_QUANTUM_EXPIRED` (the 2700 s wrapper guard — factory-wide requirement 10/12 class: **not** a product, evidence or human-gate problem). Timing fit: a team job starting within minutes of the preceding accept `5c21f6bd` (23:35:27Z) expires one quantum later, at ~00:21Z — matching the snapshot-persist timestamp 00:21:52Z, with the producer's freeze at T+37 m and state update at T+42 m. Alternative non-zero exits (rc-1 provider failure) are **not excluded** without logs. **Zero producer work was lost**: every byte was preserved by the workflow snapshot step. Full record: `results/evaluation/orchestration/40044626742_failure_chain_diagnosis.json`.

## 2. Verification (pre-registered at `23459653`, then executed)

### V1 — full instrument re-execution, normalized-IDENTICAL

The committed instrument `evaluation/v65_head_advance_crosscheck_v2.py` (sha `8a7e19c9…`, re-hashed identical first) was re-run unchanged with `--run-id 40044626742` against the same product mount (`e4f72a8e`, verified still the `lab/product` tip) and packet-of-record `39319405429`. After stripping run-id/paths/timestamps, the full record compares **quantity-for-quantity IDENTICAL to the producer's `40040574595.json` — 0 diffs**:

| quantity | value (both runs) |
|---|---|
| verdict / exit | `PASS_NO_FALSIFICATION` / 0 |
| currency | `ALL_CONFIRMED` — 36 confirmed / 0 divergent / 2 CONFIRMED_LAG / 1 NOT_REEXECUTED |
| H2 shipped-slice probe | **`H2_FALSIFIED`** — 14/14 `counter_evidence_verified` rows defective (D2 letterhead 10 · D3 markup 4 · D4 language-mismatch 4), 2 distinct decisions |
| falsification re-run | `PRODUCT_FALSIFIED`, identical accepted 4-gate set, empty `input_drift`, requirement-4 lineage `all_accepted=true` |
| planner pin / controls | `CONFIRMED` / **5/5** |

**Attempt-1 disclosure (preserved, not overwritten):** the first execution under this run returned `NOT_MEASURED_VACUOUS`/exit 2 on one leg only — the requirement-4 lineage grep, because main's upgraded workflow fetches `--depth=1` and the product mount therefore had exactly one commit. Every *measurement* leg was already identical. Repaired by `git fetch --depth=150 origin lab/product` (no mount worktree file written; HEAD stayed `e4f72a8e`); attempt-1 files are preserved under `*_attempt1_*` names (requirement 30).

### V2 — guard/reuse suites (shim; pytest ABSENT in this image)

| suite | result | vs producer record |
|---|---|---|
| `test_v65_head_advance_crosscheck_v2.py` (this cycle's guard) | **12/0/0/0** | identical |
| multilingual/provenance reuse (4 files) | **73/0/0/0** | identical |
| falsification family (4 files) | **51 passed / 0 failed / 21 UNSUPPORTED** | producer recorded 50/1/21 — the single failure was the evidence-index test tripping on the dangling ref `40011795717/producer_work_state_and_next_move.txt` **before** the producer's state update removed it; this re-run **clears it**, proving the producer's hygiene repair landed |
| this run's resume guard suite (`test_operational_resume_40044626742.py`) | **14/0/0/0** | new — every claim in the verification record re-derived from committed bytes |

### V3 — frozen pins

All 23 freeze-record file pins re-hash identical; the instrument's 25 pins (those 23 + `mount_head` + hypothesis) are `before == after` in both runs and `producer == resume`. Zero frozen/historical edits.

### V4/V5 — evidence index & freeze-first ordering

199/199 evidence refs resolved at resume time (re-checked post-update: see guard suite); the producer's freeze-first claim holds by git timestamps (`d2649360` 00:12:45Z → result 00:12:55Z → results commit 00:21:52Z).

### V6 — state hygiene correction (frozen in advance, disclosed)

`accepted_run_id` was `39986080045`. **No `accept evaluation cycle 39986080045` commit exists anywhere** (`git log --all`), so under factory-wide requirement 4 that run is not an accepted run of record despite its PASS gate file. The verified accept-commit lineage after `39936790420` is `40002636192 → 40012474431 → 40034814235`, each with both halves. State now carries `accepted_run_id=40034814235`; the prior advance block is preserved verbatim under `accepted_run_id_advance.superseded_advance`. Disclosed here, in the verification record, and in the state itself.

## 3. What this does and does not establish

This cycle **verifies** the unaudited 40040574595 cycle (currency cross-check, H2 negative result, falsification re-run, pin re-verify) by re-execution, and makes the snapshot audit-ready under run 40044626742. It adds **no new product measurement** beyond that verification and the disclosed state-pointer correction. It **scores no frozen bar**, lifts no DO-NOT-SERVE order, and the comparative map-versus-ranked-list half stays **VACUOUS** while zero counter rows are evidenced on the packet (requirement 22). The binding blocker is unchanged and now measured on the product's own flagship slice: **the counter-evidence extractor itself — 14/14 verified rows are letterhead / markup-residue / language-mismatch**.

## 4. Recommendation

**CONTINUE** under the same v65 question, sharpened exactly as the producer recorded: a further evaluation cycle under this question has a concrete discriminating purpose **only if Core Product lands a counter-evidence-extractor change**; the next useful work is that product-side repair. `continue_recommended=true` (the binding counter-authority evidence gap persists and the product head keeps moving); `evidence_tier=REPRODUCED` pending this run's independent audit.

## 5. Artifacts of record

| artifact | sha256 (first 16) |
|---|---|
| `evaluation/OPERATIONAL_RESUME_40044626742_HYPOTHESIS_V1.json` | *(committed at 23459653)* |
| `results/evaluation/orchestration/40044626742_failure_chain_diagnosis.json` | *(committed at 23459653)* |
| `results/evaluation/v65_head_advance_crosscheck/40044626742.json` | measurement of record (attempt 2) |
| `results/evaluation/v65_head_advance_crosscheck/40044626742_attempt1_shallow_mount_lineage_vacuous.json` | attempt-1 preservation |
| `results/evaluation/orchestration/40044626742_verification_of_40040574595.json` | verification record |
| `results/evaluation/operational_resume/40044626742.json` | resume cycle record |
| `results/evaluation/orchestration/40044626742_{self_suite,multiling_prov,falsification_family}_pytest_shim.json` | suite records |
| `evaluation/operational_resume_40044626742_update_state.py` | idempotent state updater |
| `tests/evaluation/test_operational_resume_40044626742.py` | guard suite tying claims to bytes |
| producer artifacts (byte-preserved) | `d2649360` + `e9f3f379`, run-40040574595 names untouched |
