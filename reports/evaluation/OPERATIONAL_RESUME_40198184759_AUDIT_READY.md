# Operational resume 40198184759 — audit-ready snapshot

- Lane: evaluation
- Direction: v68
- Status: **AUDIT_READY_PENDING_INDEPENDENT_AUDIT**
- Producer run: `40198184759` (operational resume of `40192868113`)
- Resumed team snapshot: `ef0285cc175c9f337463945f3a0c2eefa02afd86`
- Prior snapshot: `14ee2d1ef38b191c869f4e68fd4958870361f5f2`
- Accepted evaluation cycle: `40159747851`
- Accepted product cycle: `40159523259` (mount head `29a5c4a548ba0ab8b6a8f574de1e732d17f3d109`)
- Continue recommended: **false** (no new same-question cycle)
- Claim ceiling: operational-resume verification only. No quality measurement, no bar movement, no serve verdict, no admission, no new falsification.

## 1. Why this resume exists

Run `40192868113`'s team job succeeded and persisted its snapshot. Its independent-audit job failed before writing an audit branch or gate:

- Team job: success, `12:23:15Z` → `12:48:02Z`; every producer step passed, including state validation, clean-junk, write-scope and snapshot persist.
- Audit job: failure, `12:48:05Z` → `13:33:48Z` (2743s).
- Failing step: `Independent audit`, `12:48:42Z` → `13:33:46Z` = **2704s**.
- Steps `Enforce audit scope and read gate` and `Persist audit snapshot` were skipped; `integrate` skipped; `resilience` succeeded and dispatched run `40198184759`.
- No audit branch exists for `40192868113` (`git ls-remote` shows only `.../team` and `.../team-attempt-1`).

The same failure occurred on `40187594111`: audit step 5 ran **2704s**, then failed, and no audit branch/gate was written.

`origin/main:.github/scripts/run-ox-with-retry.sh` sets `WORK_QUANTUM_SECONDS="${LEX_AGENT_QUANTUM_SECONDS:-2700}"` (line 22), prints `LEX_WORK_QUANTUM_EXPIRED` (line 183) and exits `78` (line 223). The 2704s audit-step duration is 4s past the 2700s quantum, twice in a row. Classification: **ORCHESTRATION_WORK_QUANTUM_EXPIRED**, high confidence on mechanism.

This is not proven from the log text: GitHub's job-log endpoint returns HTTP 403 `Must have admin rights to Repository.` and `GH_TOKEN` is unset. The evidence is the public jobs JSON plus the checked-in wrapper, not a quoted crash line. It is also not a producer/gate failure: every producer validation step succeeded.

This resume does **not** edit `.github/**`, the workflow prompt, or the audit quantum. A durable fix (smaller audit scope, split audit, or a larger quantum) is a control-plane decision outside this lane's write scope.

## 2. Snapshot integrity

The resumed snapshot manifest (`results/evaluation/operational_resume_40192868113/manifest_40192868113.json`) lists 22 files. All 22 exist in this snapshot and all sha256/byte checks match. The current resume artifacts are in `results/evaluation/operational_resume_40198184759/` and include fresh final jobs JSON for both failed runs, the diagnosis, the deliverable verification, targeted-test results, state-integrity, nested-refs and lane-suite records.

No historical result, report, frozen bar, audit gate or accepted state block was overwritten.

## 3. Item (1): correction of record — verified

The correction note `reports/evaluation/BYPASS_CLAUSE_CORRECTION_OF_RECORD_40105794124_v68.md` is present and preserves the `40105794124` measurement. Its machine record `results/evaluation/bypass_clause_correction/40144816305.json` has:

- `measurement_unchanged=true`, `falsifier_reexecuted=false`
- all 5 controls hold
- CC1–CC5 hold
- CC6/CC7 failed in that historical run because the then-current mount could not resolve `51d306c`/`8b5b08dd`; that failure is preserved as history
- at this resume the objects are present, the `51d306c` diff and the `8b5b08dd -> 85e816f -> 51d306c` chain verify directly (see below)
- CC11 records `NOT_YET_DISCRIMINATING`; it is superseded by the later product rejection/incumbent landing, not a live contradiction
- gate `results/audit/evaluation/CYCLE_40133253347_GATE.json`: PASS, `safe_to_integrate=true`, one NON-BLOCKING CC6/CC7 provenance fix

The machine verdict remains **`CORRECTION_NOT_CONFIRMED`** (exit 1): CC6/CC7 failed on the then-mount and CC11 did not meet its then-current precondition. The accepted gate treated the provenance gap as NON-BLOCKING because the measurement is unchanged and the fix was disclosure; this resume preserves that verdict and does not turn it into a pass.

The follow-up citation `reports/evaluation/CORRECTION_FOLLOWUP_CITATION_40198184759.md` supplies the explicit file:line citation and records both the historical CC6/CC7 gap and its resolution, without editing the accepted note:

- `product/query/pipeline.py:1339` — `if adversarial_retrieval:`
- `product/query/pipeline.py:1343` — `apply_verified_span_selection(`
- `product/query/pipeline.py:1347` — `if not fixture_generation:` / counter-emission repair gate
- bundle `results/product/offline_slice/20261024T142517Z/rent-default.bundle.json`, sha256 `6eee1149b3c0ec23124746af482e15d9298c2120ee25de4bc4dd7e1cf7d93fa9`
- `provenance.counter_evidence_span.applied=true`, `n_candidates=1`, `n_selected=0`, `abstained_ids=["gr_gerichte_ERZ 2010 25"]`, `abstention_reasons={"pivot_absent":1}`
- `gr_gerichte_ERZ 2010 25` still `counter_evidence_verified=true`; the residual is **rejection/incumbent handling**, not a seam bypass

The `40105794124` measurement is unchanged: `SOUND_COUNTER_ROW_PRESENT`, `falsification_proven=false`, 4/5 enriched bundles carry frozen content defects (D2 2 / D3 2 / D4 1 over 4 distinct decisions), exactly 1 sound row (`bstger_SK.2023.49`). The 4 defective rows and the sound row are still verified at the current mount; no frozen predicate was re-scored for this claim.

**Provenance closure:** at this mount, `51d306c`'s diff is inspectable and removes the old `if not fixture_generation and adversarial_retrieval:` gate, replacing it with `if adversarial_retrieval:` and a separate `if not fixture_generation:` around the emission repair. At `51d306c` and at accepted head `8b5b08dd`, the line numbers are 1339/1343/1347. `8b5b08dd`'s parent is `85e816f`; `85e816f`'s parent is `51d306c`. `git merge-base --is-ancestor 8b5b08dd 29a5c4a5` returns 1 because `29a5c4a5` is the shallow graft root, so no ancestry through the graft is claimed; the object-level chain at the named accepted head is exactly the correction's assertion. This closes the accepted gate's NON-BLOCKING follow-up citation. The historical `40144816305` CC6/CC7 failure remains recorded as an environment/pin-time limitation, and the measurement is unchanged.

## 4. Item (2): still NOT_YET_DISCRIMINATING

The post-repair record `results/evaluation/post_repair_family_ca_falsifier/40162507752.json` is **NOT_MEASURED_VACUOUS** (exit 2) because its frozen expected mount head was `8e58724b`, while the mount is now `29a5c4a5`. Its producer-attested diagnostics are not accepted.

Fresh precondition coverage on the current mount is unchanged:

- frozen probe family: **15** members (11 offline rent-default + 4 server served)
- post-repair bundles carrying `provenance.counter_evidence_span.content_filter`: **21**
- member-for-member matching: **10/15**
- per-role multiplicity parity: **false**
- every frozen role has at least one post-repair bundle: **true**
- H1 rejection/incumbent leg landed: **true**
- H2 full frozen family regenerated: **false**

The ordered item-(2) protocol requires member-for-member regeneration of the named 15-member family. Role coverage is not member coverage. No synthetic stand-in is substituted, and the packet of record is not scored. Therefore item (2) remains **NOT_YET_DISCRIMINATING**. No same-question cycle is run.

The legacy `v68_correction.item_2_status=NOW_DISCRIMINATING` is preserved verbatim as history but is not adopted for the current mount; `v68_item_2_reconciliation_40192868113` is authoritative.

## 5. Frozen pins and standing posture

- `evaluation/frozen_bars/RULES_LABEL.json` = `4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608`
- `evaluation/frozen_bars/RULES_GEOMETRY.json` = `a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633`
- bundle of record = `6eee1149b3c0ec23124746af482e15d9298c2120ee25de4bc4dd7e1cf7d93fa9`
- product measurement of record = `results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json`: **PRODUCT_FALSIFIED**, 4/18 failed gates (concept coverage on `de-kapitalverletzung`; counter-authority surfaces on `de-kapitalverletzung`, `fr-bail-entretien`, `it-responsabilita-medica`), zero counter rows on those three questions, no input drift
- gate-falsifiability instrument = `results/evaluation/retrieval_counter_authority_benchmark/40175266143.json`: **BENCHMARK_VALID_NO_FALSIFICATION**; it proves the gate can falsify, not that the product passes
- `human_gate_ready=false`, `machine_gate_ready=false`, admission fail-closed
- both DO-NOT-SERVE orders stand
- no universal-174k benchmark rerun
- no new same-question cycle; `continue_recommended=false`
- owner decision required: false

## 6. Executable verification (audit entrypoint)

Run from the repository root. All are offline and stdlib-only except the optional lane suite. The verifier uses the fixed snapshot timestamp `2026-10-25T13:33:55Z`; reruns are byte-identical, so the artifact hashes recorded in state remain valid.

1. `python3 evaluation/operational_resume_40198184759.py`
   - expected exit 0; status `AUDIT_READY_PENDING_INDEPENDENT_AUDIT`
   - 9/9 diagnosis checks; 51/51 deliverable checks (including the product measurement of record and the gate-falsifiability instrument)
2. `python3 -m evaluation.state_integrity_gate --run-id 40198184759`
   - expected `ALL_CHECKS_PASS`, 11/11
3. `python3 evaluation/nested_evidence_refs_guard.py --run-id 40198184759`
   - expected `NESTED_REFS_RESOLVED`, 0 unresolved
4. `python3 -m evaluation.no_pytest_runner --run-id 40198184759 --test-file tests/evaluation/test_minimal_retrieval_ca_benchmark.py --test-file tests/evaluation/test_nested_evidence_refs_guard.py --test-file tests/evaluation/test_state_integrity_gate.py --test-file tests/evaluation/test_post_repair_family_ca_falsifier.py`
   - expected `SHIM_PASS`: 39 passed, 0 failed, 0 skipped, 12 unsupported (environment-disclosed, not failures)
5. `python3 -m evaluation.snapshot_audit.write_scope --lane evaluation`
   - expected PASS on the lane's written paths
6. Optional, not needed for the claim: `python3 -m evaluation.lane_suite --skip-pytest`
   - expected `lane suite: PASS (88/88 checks)`; observed runtime 182.364s

The audit should focus on five things: (a) the 2704s/2700s quantum diagnosis and no-audit-branch fact; (b) item (1)'s measurement unchanged, the historical CC6/CC7 failure, and its direct object-level resolution; (c) item (2) 10/15 coverage and the vacuous producer record; (d) no frozen bar/bundle movement and the product measurement of record is unchanged; (e) no new claim, no same-question cycle, no 174k rerun, no scope violation.

## 7. Risks and non-claims

- The audit job may still hit the same 2700s quantum if the independent auditor re-derives the whole correction history. This audit pack is deliberately compact; if the provider still expires, the durable fix is control-plane (split/reduce audit scope or raise the quantum), not another producer cycle.
- The product mount is shallow/grafted at `29a5c4a5`; a merge-base path from older accepted head `8b5b08dd` through the graft is unavailable. The object-level `8b5b08dd -> 85e816f -> 51d306c` chain and the `51d306c` diff are directly verified; no ancestry through the graft is claimed.
- This report does not claim the map helps a jurist, does not meet LABEL_SOUND or GEOMETRY_SOUND, does not discharge item (2), does not lift either DO-NOT-SERVE order, and does not turn the producer snapshot into an independent audit.
