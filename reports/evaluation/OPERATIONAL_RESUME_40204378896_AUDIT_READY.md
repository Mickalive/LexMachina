# Operational resume 40204378896 — audit-ready snapshot

- Lane: evaluation
- Direction: v68
- Status: **AUDIT_READY_PENDING_INDEPENDENT_AUDIT**
- Producer run: `40204378896` (operational resume of `40198184759`)
- Resumed team snapshot under audit: `251a6f5967c653d3ca93bf0a2d3ad7a1dd3f875e`
- Prior resume run: `40198184759` (its base snapshot was `ef0285cc175c9f337463945f3a0c2eefa02afd86`; its own persisted snapshot is `251a6f59`)
- Accepted evaluation cycle: `40159747851`
- Accepted product cycle: `40159523259` (mount head `29a5c4a548ba0ab8b6a8f574de1e732d17f3d109`)
- Continue recommended: **false** (no new same-question cycle)
- Claim ceiling: operational-resume verification only. No quality measurement, no bar movement, no serve verdict, no admission, no new falsification.

## 1. Why this resume exists

Run `40198184759`'s team job succeeded and persisted its snapshot. Its independent-audit job failed before writing an audit branch or gate:

- Team job: success, `13:34:01Z` → `14:07:51Z`; every producer step passed, including state validation, clean-junk, write-scope and snapshot persist.
- Audit job: failure, `14:07:54Z` → `14:53:40Z` (2746s).
- Failing step: `Independent audit`, `14:08:34Z` → `14:53:38Z` = **2704s**.
- Steps `Enforce audit scope and read gate` and `Persist audit snapshot` were skipped; `integrate` was skipped; `resilience` succeeded and dispatched run `40204378896`.
- No audit branch exists for `40198184759` (`git ls-remote` shows only `.../team` and `.../team-attempt-1`).

The same failure occurred on `40192868113` and `40187594111`: the independent-audit step ran **2704s**, then failed, and no audit branch or gate was written. That is three consecutive runs with the identical audit-step duration and no audit artifact.

`origin/main:.github/scripts/run-ox-with-retry.sh` sets `WORK_QUANTUM_SECONDS="${LEX_AGENT_QUANTUM_SECONDS:-2700}"` (line 22), prints `LEX_WORK_QUANTUM_EXPIRED` (line 183) and exits `78` (line 223). The 2704s audit-step duration is 4s past the 2700s quantum, three times in a row. Classification: **ORCHESTRATION_WORK_QUANTUM_EXPIRED**, high confidence on mechanism.

This is not proven from the log text: GitHub's job-log endpoint returns HTTP 403 `Must have admin rights to Repository.` and `GH_TOKEN` is unset. The evidence is the public jobs JSON plus the checked-in wrapper, not a quoted crash line. It is also not a producer/gate failure: every producer validation step succeeded.

This resume does **not** edit `.github/**`, the workflow prompt, or the audit quantum. A durable fix (smaller audit scope, split audit, or a larger quantum) is a control-plane decision outside this lane's write scope.

## 2. Snapshot integrity

The prior manifest `results/evaluation/operational_resume_40192868113/manifest_40192868113.json` listed 22 files. Two of them are the lane's own state files (`state/evaluation.json` and `evaluation/state/evaluation.json`), which a resume necessarily advances. This resume therefore verifies:

- **20/20 immutable prior-manifest artifacts** are byte-identical at the resumed snapshot.
- **both prior state-file blobs** match the manifest at their own snapshot `ef0285cc` (run `40192868113`); they also remain retrievable at `251a6f59`, but the hash check uses the commit the manifest actually hashed. Their contents advancing in this resume is expected and disclosed, not treated as preservation failure.
- **33 old claim-bearing paths** are byte-identical to the prior snapshot (no historical result, report, frozen bar, audit gate or accepted state block was rewritten).
- frozen pins are unchanged: `RULES_LABEL.json` = `4457e971…`, `RULES_GEOMETRY.json` = `a7452748…`.
- accepted run `40159747851` and its accept commit `9be8a7d5b3a4b84eb45da6160bf90620f7d81d40` are unchanged.

This is stricter and more honest than claiming “22/22 byte-identical” while silently freezing the state files: an audit can check both the immutable artifacts and the historical state bytes.

## 3. Item (1): correction of record — preserved and re-verified

The correction note `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md`, its follow-up citation `reports/evaluation/CORRECTION_FOLLOWUP_CITATION_40198184759.md`, and machine record `results/evaluation/bypass_clause_correction/40144816305.json` are preserved byte-identically.

The prior deliverable verification was re-executed at the current mount: **51/51 checks pass** (`REEXECUTED_AT_CURRENT_MOUNT`). This replays the prior verification; it does not create a new measurement. The measurement of record remains unchanged:

- `SOUND_COUNTER_ROW_PRESENT`, `falsification_proven=false`
- 4/5 enriched bundles carry frozen content defects (D2=2, D3=2, D4=1 over 4 distinct decisions)
- exactly one sound row: `bstger_SK.2023.49`

The historical CC6/CC7 failure is preserved as history. At this resume the named objects verify directly:

- `51d306c`'s diff is inspectable and removes the old combined fixture-gate condition.
- `8b5b08dd -> 85e816f -> 51d306c` is the accepted chain; `product/query/pipeline.py` line 1339 is the `if adversarial_retrieval:` gate at both `51d306c` and `8b5b08dd`.
- `git merge-base --is-ancestor 8b5b08dd 29a5c4a5` returns 1 because `29a5c4a5` is the shallow graft root; no ancestry through the graft is claimed. The object-level chain at the named accepted head is exactly the correction's assertion.

**Provenance repair disclosure.** The product mount is a shallow worktree and initially lacked `51d306c`, `85e816f` and `8b5b08dd` as objects. This resume fetched those three **exact full commit ids** from `origin` (one `git fetch --no-tags`; no OpenCaseLaw, retrieval or model call), as permitted by the lane's `S5_no_network_except_pin_fetch` rule. The fetch is recorded in `results/evaluation/operational_resume_40204378896/provenance_fetch_record_40204378896.json`. It changes object availability only; it does not re-score the measurement or move a bar. The verifier also performs this pin fetch automatically if an audit mount lacks the objects, and records it in the replay artifact.

## 4. Item (2): still NOT_YET_DISCRIMINATING

The post-repair record `results/evaluation/post_repair_family_ca_falsifier/40162507752.json` remains **NOT_MEASURED_VACUOUS** (exit 2): its frozen expected mount head was `8e58724b`, while the current mount is `29a5c4a5`. Its producer-attested diagnostics are not accepted as a fresh result.

Fresh precondition coverage is unchanged:

- frozen probe family: **15** members (11 offline rent-default + 4 server served)
- post-repair bundles carrying `provenance.counter_evidence_span.content_filter`: **21**
- member-for-member matching: **10/15**
- per-role multiplicity parity: **false**
- every frozen role has at least one post-repair bundle: **true**
- H1 rejection/incumbent leg landed: **true**
- H2 full frozen family regenerated: **false**

The ordered item-(2) protocol requires member-for-member regeneration of the named 15-member family. Role coverage is not member coverage. No synthetic stand-in is substituted, and the packet of record is not scored. Item (2) therefore remains **NOT_YET_DISCRIMINATING**.

The legacy `v68_correction.item_2_status=NOW_DISCRIMINATING` is preserved verbatim as history but is not adopted for the current mount; `v68_item_2_reconciliation_40192868113` remains authoritative.

## 5. Frozen pins and standing posture

- bundle of record = `6eee1149b3c0ec23124746af482e15d9298c2120ee25de4bc4dd7e1cf7d93fa9`
- product measurement of record = `results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json`: **PRODUCT_FALSIFIED**, 4/18 failed gates (concept coverage on `de-kapitalverletzung`; counter-authority surfaces on `de-kapitalverletzung`, `fr-bail-entretien`, `it-responsabilita-medica`), zero counter rows on those three questions, no input drift
- gate-falsifiability instrument = `results/evaluation/retrieval_counter_authority_benchmark/40175266143.json`: **BENCHMARK_VALID_NO_FALSIFICATION**; it proves the gate can falsify, not that the product passes
- `human_gate_ready=false`, `machine_gate_ready=false`, admission fail-closed
- both DO-NOT-SERVE orders stand
- no universal-174k benchmark rerun
- no new same-question cycle; `continue_recommended=false`
- owner decision required: false
- network calls in this resume: **one pin fetch of three product commits**; no benchmark, retrieval, OpenCaseLaw or model call. The state's historical `no_network_calls` posture is corrected to `false` for this resume with this disclosure.

## 6. Executable verification (audit entrypoint)

Run from the repository root. All checks are offline after the optional pin fetch, and stdlib-only except the targeted shim runner. The verifier uses fixed timestamp `2026-10-25T14:53:49Z`; reruns at the same HEAD are byte-identical. The snapshot-integrity record intentionally captures HEAD at generation time, so after the resume snapshot commit it will show the producer snapshot as the parent of HEAD rather than equal to HEAD; that is why the check is “ancestor or head”, not “equal”.

1. `python3 evaluation/operational_resume_40204378896.py prepare`
   - may perform the disclosed pin fetch if the shallow product mount lacks the three commits
   - expected exit 0: diagnosis **11/11**, snapshot integrity **9/9**, deliverable replay **51/51**
   - replay status `REEXECUTED_AT_CURRENT_MOUNT`
2. `python3 -m evaluation.no_pytest_runner --run-id 40204378896 --test-file tests/evaluation/test_minimal_retrieval_ca_benchmark.py --test-file tests/evaluation/test_nested_evidence_refs_guard.py --test-file tests/evaluation/test_state_integrity_gate.py --test-file tests/evaluation/test_post_repair_family_ca_falsifier.py --out results/evaluation/operational_resume_40204378896/pytest_targeted_40204378896.json`
   - expected `SHIM_PASS`: **39 passed, 0 failed, 0 skipped, 12 unsupported** (environment-disclosed, not failures)
3. `python3 evaluation/nested_evidence_refs_guard.py --run-id 40204378896 --out-dir results/evaluation/operational_resume_40204378896/nested_refs`
   - expected `NESTED_REFS_RESOLVED`, 0 top-level and 0 nested unresolved
4. `python3 -m evaluation.state_integrity_gate --run-id 40204378896 --out results/evaluation/operational_resume_40204378896/state_integrity_gate_40204378896.json`
   - expected `ALL_CHECKS_PASS`, 11/11
5. `python3 -m evaluation.snapshot_audit.write_scope --lane evaluation --out results/evaluation/operational_resume_40204378896/write_scope_40204378896.json`
   - expected `SCOPE_CLEAN`, 0 bad paths (pre-state observation: 13 entries, 0 bad)
6. `python3 evaluation/operational_resume_40204378896.py finalize`
   - expected exit 0; status `AUDIT_READY_PENDING_INDEPENDENT_AUDIT`; writes `summary_40204378896.json` and hash-indexed `AUDIT_INDEX_40204378896.json`

The compact audit entry point is `results/evaluation/operational_resume_40204378896/AUDIT_INDEX_40204378896.json`. The audit should focus on five things: (a) the 2704s/2700s quantum diagnosis and no-audit-branch fact; (b) item (1)'s measurement unchanged, the historical CC6/CC7 failure, and its direct object-level resolution plus pin-fetch disclosure; (c) item (2) 10/15 coverage and the vacuous producer record; (d) no frozen bar/bundle movement and the product measurement of record unchanged; (e) no new claim, no same-question cycle, no 174k rerun, no scope violation.

## 7. Risks and non-claims

- The audit job may still hit the same 2700s quantum if the independent auditor re-derives the whole correction history. This audit pack is deliberately compact; if the provider still expires, the durable fix is control-plane (split/reduce audit scope or raise the quantum), not another producer cycle.
- The product mount is shallow/grafted at `29a5c4a5`; a merge-base path from older accepted head `8b5b08dd` through the graft is unavailable. The object-level `8b5b08dd -> 85e816f -> 51d306c` chain and the `51d306c` diff are directly verified; no ancestry through the graft is claimed.
- This report does not claim the map helps a jurist, does not meet LABEL_SOUND or GEOMETRY_SOUND, does not discharge item (2), does not lift either DO-NOT-SERVE order, and does not turn the producer snapshot into an independent audit.
- The report itself is not independent audit evidence; it is the producer's audit-ready map. The independent auditor must still issue the gate.
