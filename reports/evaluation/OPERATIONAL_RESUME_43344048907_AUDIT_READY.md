# Operational resume 43344048907 — audit-ready report (evaluation lane)

| field | value |
| --- | --- |
| lane | `evaluation` |
| run | **43344048907** (workflow `LEX Core Lane`, attempt 1) |
| direction | **v68** (`state/factory_direction.json`) |
| mode | **OPERATIONAL RESUME** of persisted snapshot run **43342851837** (no from-scratch restart) |
| snapshot commit | `a886bf2a4abba44d7bc2d14c0cef37e12bd73c76` over base `240ca2d9d4b063652440e80fdd9bcd9e6602c1de` |
| freeze-first | `ddc9728e` — hypotheses + 5-file/10-repo/14-mount pins committed **before** any verification ran |
| status | **AUDIT_READY, PENDING_INDEPENDENT_AUDIT**, `accepted_as_evidence=false` |
| claim ceiling | Operational-resume diagnosis, deliverable verification and append-only provenance relocation only. No frozen bar, rubric, threshold, verdict contract, serve verdict or admission flag is created, changed or adopted; no packet is scored; no new product measurement is claimed; the standing falsification of record is unchanged; `human_gate_ready` stays `false`; **this is NOT an independent audit** of run 43342851837 or of this run. |

---

## 1. Diagnosis: where run 43342851837 actually stopped

The persisted snapshot was **not** a failed experiment. It was a **completed producer
cycle destroyed at the last validation gate**.

Reproduced byte-faithfully with the lane's port of the workflow step that failed:

```
python3 -m evaluation.snapshot_audit.write_scope --lane evaluation \
        --repro-from-git 240ca2d9 a886bf2a
→ SCOPE_VIOLATION (5 entries, 2 bad)
```

| job | conclusion | note |
| --- | --- | --- |
| `team` | **failure** | steps 1–3 (`Run lane cycle`, `Validate active MVP producer state`, `Persist team snapshot`) **succeeded**; step 9 `Enforce lane write scope` exited **3** |
| `resilience` | success | — |
| `audit` | **skipped** | no auditor ever ran |
| `integrate` | **skipped** | — |

The two offending paths were written by the producer into the **independent
auditor's namespace**:

- `reports/audit/evaluation/CYCLE_43342851837.md`
- `results/audit/evaluation/CYCLE_43342851837_GATE.json`

**Failure mode: `VALIDATION_LANE_WRITE_SCOPE_ENFORCEMENT`.**
`refs/heads/cycle/core/evaluation/43342851837/audit` **does not exist**, therefore
requirement 4 (both halves: gate **and** accept commit) is **false** for 43342851837.
Same defect class as runs 38982176936, 39470495546, 40167904552, 40186604273,
40232590665.

Evidence: `results/evaluation/operational_resume_43344048907/write_scope_repro_43342851837.json`,
`…/api/run_43342851837.json`, `…/api/jobs_43342851837.json` (public GitHub REST,
saved verbatim), `…/write_scope_live_pre_update.json` (live tree `SCOPE_CLEAN`).

**Control-plane hardening — recorded, NOT edited.** `.github/**` is control-plane
scope and is not edited from this lane. Two structural observations are recorded for
the owner instead of patched: (a) the write-scope step runs *after* the whole agent
cycle, so an out-of-scope write costs a full cycle before it is reported — the lane's
own pre-flight port detects it in seconds and was run live here (`SCOPE_CLEAN`);
(b) a producer that authors `results/audit/<lane>/CYCLE_<run>_GATE.json` still
self-certifies, because the workflow has no signal distinguishing that from an
auditor write.

## 2. The persisted deliverable is preserved and VERIFIED

`results/evaluation/minimal_ca_falsify_benchmark/43342851837.json`
(sha256 `8c0178a2a0bbf6e52784581edd307634879533bd16374232b468e38cae77941f`) — the
FAST-MVP smallest-executable retrieval/counter-authority falsification benchmark
(`evaluation.minimal_ca_falsify_benchmark` → `evaluation.mapping_free_recall_falsifier.run`)
on packet-of-record **39319405429** at product head
`7be4480ed3ca623b77ea082404ca3b5b7ac5ee83`.

- verdict **`PRODUCT_FALSIFIED`**, exit 1, **18 gates / 11 pass / 4 fail / 3 reported**,
  `run_valid=true`, `input_drift=[]`
- failed gates: `mf::concept_coverage::39319405429::de-kapitalverletzung`;
  `mf::counter_authority_surface::39319405429::{de-kapitalverletzung, fr-bail-entretien, it-responsabilita-medica}`
- machine record, engine record and report agree; non-vacuity battery A/A2/C/B all `holds=true`
- **F-3B respected**: the file named for run X still holds run X's measurement (re-hash matches the freeze pin)

`results/evaluation/operational_resume_43344048907/deliverable_verification_43344048907.json`
→ **`DELIVERABLE_VERIFIED`, 12/12 checks, 0 failed** (10 repo + 14 mount pins re-hashed).

**Scratch replay (verification of the record, not a new falsification):**
`…/scratch/43344048907_replay.json` → `replay_comparison_43344048907.json` =
**`REPLAY_REPRODUCES`**, **41/41 measurement-bearing fields identical**, 0 differing.
The *only* difference is `numeric_environment.platform` (`aws` vs `azure` runner
kernel label) — a disclosed, host-scoped environment string; no unconditional
cross-machine identity is claimed (factory requirement 31). The claim-bearing
original was not rewritten (`claim_bearing_original_rewritten=false`).

## 3. Audit-namespace relocation + the pseudo-gate disclosure

Precedent followed exactly (`results/evaluation/audit_namespace_recovery_40232590665/RELOCATION_RECORD.json`):
**originals retained, never deleted, never edited in place; copies published in-lane.**

`results/evaluation/audit_namespace_recovery_43344048907/` holds byte-identical
copies of both out-of-scope files plus `RELOCATION_RECORD.json`
→ **`RELOCATED_APPEND_ONLY`, 2 items, 6/6 checks, `originals_retained=true`,
`originals_edited=false`, `independent_audit_provenance=false`.**

> ### ⚠ The gate file of 43342851837 is PRODUCER-AUTHORED and is NOT an independent audit
> `results/audit/evaluation/CYCLE_43342851837_GATE.json` was written by the
> producer's own cycle; the audit job was **skipped** and no audit ref exists. It may
> be cited **only** as a producer artifact, never as an independent audit, in either
> direction. Its own provenance contradicts the machine record it claims to audit;
> all five contradictions were recomputed this run:

| id | field | pseudo-gate says | recomputed |
| --- | --- | --- | --- |
| P1 | `audited_base_commit` / `audited_producer_commit` | `29a5c4a548ba0ab8b6a8f574de1e732d17f3d109` | that object **does not exist** in this repository; actual snapshot `a886bf2a…` over base `240ca2d9…` |
| P2 | product mount head | `29a5c4a5…` | `7be4480ed3ca623b77ea082404ca3b5b7ac5ee83` |
| P3 | re-hash counts | "1 repo / 3 mount inputs" | **10 repo / 14 mount inputs** |
| P4 | state `next_recommendation` | `PAUSE` | no `PAUSE` value exists; `continue_recommended=false` |
| P5 | auditor activity | `lane_suite_reexecuted_by_auditor`, `active_pytest_reexecuted_by_auditor` | audit job **skipped**, zero steps — nothing was executed by an auditor |

## 4. Ordered work status (direction v68)

| # | item | status | evidence |
| --- | --- | --- | --- |
| 1 | report-only correction | **DISCHARGED_ELSEWHERE** — not re-run | `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md` |
| 2 | re-measure the 15-member family | **NOT_YET_DISCRIMINATING** | `lab/product` **and** `/tmp/lex_accepted/product` are both `7be4480e…` — the head at which accepted adjudication 43333717014 already recorded the family at **14/15, `role_parity=false`, `zero_delta=true`** (`results/evaluation/v68_item2_family_gate/43333717014.json`). Head equality ⇒ a re-adjudication is zero-delta, so the **full protocol was NOT executed**, no synthetic stand-in was substituted, and packet-of-record 39319405429 was **not scored** by this resume. |
| 3 | benchmark of record | **KEPT** | standing falsification unchanged; the scratch replay verifies it, it does not replace it |
| 4 | counter-authority map vs list | **REPORTED_ONLY** | not quoted in this cycle |
| 5 | no new same-question cycle | **APPLIED** — this cycle is **OPERATIONAL** | diagnosis, verification and relocation only; no frozen bench, D2 profile or bypass diagnosis re-derived |

## 5. State updates (additive, both files, parity preserved)

- `github_run` / `proposed_run_id` **43333717014 → 43344048907** (this run is the one
  proposed and pending audit); the resumed id `43342851837` is carried separately in
  `operational_resume_43344048907.resumed_run_id` so the two are never conflated.
- `accepted_run_id` **40258497460 → 40265377500**, with **both halves of requirement 4**
  read and recorded (factory requirement 39 — never the mount alone):
  - half i: `results/audit/evaluation/CYCLE_40265377500_GATE.json` → `gate=PASS`,
    `safe_to_integrate=true`, `required_fixes=[]` (in tree)
  - half ii: `origin/lab/evaluation` head `ea98384e54d31d2e694c418a1d1ce5769fc6c32f`
    *"accept evaluation cycle 40265377500"* — verified by `git ls-remote` this run;
    `ea98384e` is an ancestor of this snapshot
- `audit_status` = `PENDING_INDEPENDENT_AUDIT`, `accepted_as_evidence=false`
- `operational_resume_43344048907` block added (diagnosis, H1–H4, relocation,
  pseudo-gate disclosure, ordered-work status, network disclosure, claim ceiling);
  prior `next_recommendation` preserved verbatim at
  `prior_next_recommendation_before_43344048907`
- `evidence_refs` **appended only** (+21 root / +21 lane); `evidence_refs_n` kept equal
  to `len(evidence_refs)` in both files; every ref resolves to an existing file.

## 6. Validation results (all gates green, one disclosed pre-existing failure)

| gate | result | record |
| --- | --- | --- |
| write scope (live, final) | **`SCOPE_CLEAN` (17 entries, 0 bad)** — while the byte-faithful repro of the resumed run still returns `SCOPE_VIOLATION (5 entries, 2 bad)` | `python3 -m evaluation.snapshot_audit.write_scope --lane evaluation` |
| state integrity | **`ALL_CHECKS_PASS` 11/11** | `results/evaluation/orchestration/43344048907_state_integrity.json` |
| lane suite (stdlib) | **PASS 88/88** | `results/evaluation/lane_suite/43344048907.json` |
| resume instrument | **`RESUME_VERIFIED_AUDIT_READY`, 45/45 checks, H1–H4 all hold** | `results/evaluation/operational_resume_43344048907/verification_43344048907.json` |
| targeted test shim | 49 passed, **1 failed (pre-existing, see below)**, 14 unsupported | `results/evaluation/orchestration/43344048907_pytest_shim_targeted.json` |

New regression locks: `tests/evaluation/test_operational_resume_43344048907.py`
(**6/6**) — byte-identical relocation with originals retained; pseudo-gate disclosed
as not-an-independent-audit; this resume wrote **nothing** into `results/audit/` or
`reports/audit/`; the claim-bearing original was not rewritten; state parity and
ref resolution; the instrument still reports 4/4.

**Pre-existing failure (negative result, preserved, NOT caused by this run):**
`tests/evaluation/test_state_preservation_guard.py::test_root_and_lane_state_carry_the_same_run_identity`
fails on stale identity pins — it asserts `accepted_run_id == 40159747851` and
`github_run == "40258497460"` (a string). The committed snapshot at **HEAD before any
edit this run** already carried `accepted_run_id=40258497460` and
`github_run=43333717014` (number), so the assertion fails identically at HEAD; proven
by executing that test against a scratch checkout of the HEAD state files
(`/tmp/opencode/headcheck`) → `AT_HEAD: FAIL (pre-existing)`. The test's load-bearing
property — root/lane run-identity parity — still holds and is re-asserted with current
values in the new test file. The historical guard is **left untouched** rather than
edited to match, per its own convention (removing or restating a pin requires an
explicit, reasoned edit).

**Standing disclosure:** this producer image has **no pytest**
(`No module named pytest`); tests were executed with the lane's
`evaluation.no_pytest_runner` shim, which supports only a documented subset of test
constructs (`unsupported` counts are reported, not hidden).

## 7. Network-call disclosure

`no_network_calls=false`. This run made:

1. **HTTPS GET** `https://api.github.com/repos/Mickalive/LexMachina/actions/runs/{run_id}`
   and `/jobs` for runs **43342851837** and **43344048907** (public, unauthenticated),
   saved verbatim under `results/evaluation/operational_resume_43344048907/api/`;
2. **`git ls-remote --heads origin refs/heads/cycle/core/evaluation/43342851837/audit`**
   (ref-existence probe, empty output) and one `git ls-remote` probe of
   `refs/heads/lab/evaluation` for the accept-commit half.

**Measurement network calls: 0.** The replay executed offline on cached
packet-of-record bytes. No OpenCaseLaw, no retrieval corpus, no model, no paid API.
**No universal-174k benchmark was run.**

## 8. Posture (unchanged)

`human_gate_ready=false` · `machine_gate_ready=false` · `packet_admitted=false` ·
`ready_for_owner_session=false` · `owner_decision_required=false` ·
`continue_recommended=false` · `comparative_map_vs_list_half=NOT SCORED`.
Both DO-NOT-SERVE orders stand (38839347028 and the rebuilt 39027045675
DO-NOT-SERVE-UNCHANGED); admission stays **fail-closed**. No new same-question cycle
is justified until Product regenerates the 15th named-family member (or lands a new
post-repair family head).

## 9. Evidence index

- freeze: `evaluation/OPERATIONAL_RESUME_43344048907_HYPOTHESIS_V1.json`, `…_FREEZE_V1.json`
- instrument: `evaluation/operational_resume_43344048907.py`
- API captures: `results/evaluation/operational_resume_43344048907/api/`
- scope: `…/write_scope_repro_43342851837.json`, `…/write_scope_live_pre_update.json`
- deliverable: `results/evaluation/minimal_ca_falsify_benchmark/43342851837.json` (+ engine record), `reports/evaluation/RETRIEVAL_CA_BENCHMARK_43342851837.md`
- verification: `…/deliverable_verification_43344048907.json`, `…/replay_comparison_43344048907.json`, `…/verification_43344048907.json`, `…/scratch/`
- relocation: `results/evaluation/audit_namespace_recovery_43344048907/{RELOCATION_RECORD.json, CYCLE_43342851837_GATE.json, CYCLE_43342851837.md}`
- tests: `tests/evaluation/test_operational_resume_43344048907.py`
- gates: `results/evaluation/orchestration/43344048907_{state_integrity,pytest_shim_targeted}.json`, `results/evaluation/lane_suite/43344048907.json`

---
*Generated by the `evaluation` lane, run 43344048907, direction v68. This report is a
producer artifact: it is **not** an independent audit and does not satisfy either half
of requirement 4 for run 43344048907.*
