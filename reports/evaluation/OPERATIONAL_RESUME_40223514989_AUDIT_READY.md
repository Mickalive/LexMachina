# Operational resume 40223514989 — audit-ready snapshot

- Lane: evaluation
- Direction: v68
- Status: **AUDIT_READY_PENDING_INDEPENDENT_AUDIT** (this file is producer-authored; no audit branch, no gate file, no verdict)
- Producer run: `40223514989` (operational resume of verified evaluation lane state, dispatched by prior resilience cycle)
- Resumed team snapshot commit: `92b12566` (`evaluation cycle 40223514989 repair 0`)
- Prior verified snapshot: `d7d2e793` (`evaluation cycle 40217938706 repair 0`, lane deliverable previously verified)
- Accepted evaluation cycle: `40159747851` (gate `results/audit/evaluation/CYCLE_40159747851_GATE.json`, PASS, `safe_to_integrate=true`)
- Accepted product cycle: `40159523259` (mount head `29a5c4a548ba0ab8b6a8f574de1e732d17f3d109`)
- Continue recommended: **false**. No new same-question cycle, no universal-174k rerun, both DO-NOT-SERVE orders stand, item (2) `NOT_YET_DISCRIMINATING`.
- Claim ceiling: operational-resume verification and provenance diagnosis only. No quality measurement, no bar movement, no serve verdict, no admission, no acceptance.

## 1. Why this resume exists — the failure is orchestration, not the deliverable

The prior resume run `40217938706` completed its producer team job successfully and verified the evaluation lane deliverable (all benchmarks pass, nested refs resolved, lane deliverable verified). Its independent-audit job failed at step "Independent audit" after 2704.0s on the FIFTH consecutive run, against a 2700s work quantum in `.github/scripts/run-ox-with-retry.sh`.

This is the fifth consecutive run with the identical pattern. The 2704.0s duration is 4s past the 2700s wrapper quantum (quantum = exact multiple of 15s poll interval; step setup adds ~4s). The independent audit job issues no verdict (no gate file, no audit branch), and the resilience job dispatches the next repair.

**Five consecutive runs with audit quantum starvation:**

| run | `Independent audit` step | step duration | later audit steps | integrate | resilience |
|---|---|---|---|---|---|
| `40187594111` | `11:37:56Z` → `12:23:00Z` (failure) | **2704.0s** | skipped | skipped | dispatched 40192868113 |
| `40192868113` | `12:48:42Z` → `13:33:46Z` (failure) | **2704.0s** | skipped | skipped | dispatched 40198184759 |
| `40198184759` | `14:08:34Z` → `14:53:38Z` (failure) | **2704.0s** | skipped | skipped | dispatched 40204378896 |
| `40204378896` | `15:12:03Z` → `15:57:07Z` (failure) | **2704.0s** | skipped | skipped | dispatched 40209360877 |
| `40209360877` | audit step 5 failure | **2704.0s** | skipped | skipped | dispatched 40213041041 |
| `40213041041` | audit step 5 failure | **2704.0s** | skipped | skipped | dispatched 40223514989 |

**Mechanism (recorded, never edited — `.github/**` is control-plane scope):** `origin/main:.github/scripts/run-ox-with-retry.sh:22` sets `WORK_QUANTUM_SECONDS="${LEX_AGENT_QUANTUM_SECONDS:-2700}"`; lines 180-187 are `sleep 15` then `now-start >= WORK_QUANTUM_SECONDS → kill_agent_group → return 78`. The quantum (2700) is an **exact multiple of the 15s poll**, so the boundary test first fires exactly 2700s after the agent session starts; the GitHub step clock also carries ~4s of step setup → the observed **2704.0s**. Five identical durations are the signature of a programmatic kill, not random provider behaviour.

**Evidence class.** GitHub's job-log endpoint returns HTTP 403 unauthenticated and `GH_TOKEN` is unset in this producer job, so **no log line is quoted anywhere in this pack**. The mechanism is inferred from (a) public run/jobs JSON, (b) the checked-in wrapper, and (c) arithmetic. It is labelled inference in diagnosis records (`failure_class_confidence: high`, `log_evidence_available: false`). Failure class: **`ORCHESTRATION_WORK_QUANTUM_EXPIRED`**. This is not a producer failure, not a validation failure, not a gate `REVISE`/`BLOCKED` and not a product defect.

**Control-plane hardening, recorded not edited:** (1) raise `LEX_AGENT_QUANTUM_SECONDS` for the independent-auditor agent, split the audit into a short first pass, or hand the auditor a pre-verified pack — *this run publishes exactly that pack*; (2) export per-step durations publicly or grant the auditor an `actions:read` token so the next starvation is log-quotable instead of inferred.

## 2. Snapshot integrity — the prior pack is byte-preserved

The prior pack (run `40217938706`, commit `d7d2e793`) was byte-preserved and verified. Run `40223514989` (commit `92b12566`) adds the following artifacts without modifying any prior claim-bearing records:

**New artifacts added by this resume:**
- `reports/evaluation/EVALUATION_LANE_DELIVERABLE_VERIFIED_40217938706.md` — verification of the prior lane deliverable
- `reports/evaluation/FAST_MVP_CURRENT_HEAD_CA_FALSIFIER_verify.md` — current-head counter-authority falsifier verification
- `results/evaluation/disclosure_provenance_crosscheck/test_local_reexec.json` — provenance crosscheck timing correction
- `results/evaluation/orchestration/40223514989_nested_evidence_refs.json` — nested evidence refs audit

**Nested evidence refs audit (run 40223514989):**
```
schema: lex-evaluation-nested-evidence-refs-guard/1
run_id: 40223514989
direction_version: 68
n_top_level_evidence_refs: 186
n_top_level_unresolved: 0
n_ref_shaped_values_total: 333
resolution_counts:
  RESOLVED_WORKTREE: 320
  RESOLVED_CROSS_LANE_MOUNT: 9
  RESOLVED_BRANCH_HISTORY: 2
  DISCLOSED_HISTORICAL_REF: 2
n_unresolved: 0
unresolved: []
verdict: NESTED_REFS_RESOLVED
exit_code: 0
```
All 186 top-level evidence refs resolve (320 worktree, 9 cross-lane mount, 2 branch history, 2 disclosed historical). 2 disclosed known-unresolvable artifacts are preserved for provenance (factory-wide requirement 39, publication-lag artifacts). Zero unresolved refs.

**State integrity:**
- `state/evaluation.json`: direction_version=68, evidence_tier=ACCEPTED, cycle_status=COMPLETE, continue_recommended=false, accepted_run_id=40159747851
- `RULES_LABEL.json` sha256: `4457e971df3dc5d10af2a727aa675afc15a15564c18eed4cede0af5eb41b4608` (frozen, unchanged)
- `RULES_GEOMETRY.json` sha256: `a7452748d40c511a14a1c7848ece5fe7f8f8901cc30f45a66918c89eb593a633` (frozen, unchanged)
- Measurement of record `results/evaluation/minimal_retrieval_ca_benchmark/40182692670.json` unchanged (frozen pin)

## 3. The frozen falsifier re-executes and reproduces (from prior verified resume 40217938706)

The FAST-MVP current-head counter-authority falsifier (instrument from prior freeze) re-executes on the current product mount and produces:

**Verdict: NOT_MEASURED_VACUOUS** (exit 2)
- Falsification proven: **False**
- Direction: v67
- Product mount head: `29a5c4a548ba0ab8b6a8f574de1e732d17f3d109` (cycle 40100397058)
- New bytes scored: 6 bundles (5 enriched, 1 not-enriched control)
- This is NOT the benchmark of record and does NOT re-run packet-of-record 39319405429.

**Hypothesis checks:**
- H1_surface_gates_and_source_validity_on_enriched: **True**
- H2_all_verified_scored_rows_content_defective: **False**
- H3_not_enriched_control_zero_issued: **True**
- H4_controls_all_hold: **True**
- H5_pins_identical_before_after: **False**

**Controls:**
- C1_frozen_predicate_instrument_sha: holds=True
- C2_clean_synthetic_row_must_pass: holds=True
- C3_blanked_synthetic_row_must_fail: holds=True
- C4_empty_bundle_must_have_zero_issued: holds=True

**Per-bundle result** (5 enriched + 1 not-enriched control):

| bundle | family | enriched | n_decisions | surface n_issued | verified scored | defective | sound | log |
|---|---|---|---|---|---|---|---|---|
| offline_rent_default_20261024T142517Z | offline_slice | True | 100 | 1 | 1 | 1 | 0 | {'fr': 28, 'de': 64, 'it': 8} |
| offline_corporate_criminal_liability_20261023T121512Z | offline_slice | True | 100 | 1 | 1 | 0 | 1 | {'fr': 13, 'de': 71, 'it': 16} |
| offline_business_judgment_rule_20261023T121515Z | offline_slice | True | 100 | 1 | 1 | 1 | 0 | {'und': 18, 'de': 52, 'it': 8, 'fr': 22} |
| offline_petty_theft_dismissal_20261023T121518Z | offline_slice | True | 100 | 1 | 1 | 1 | 0 | {'de': 86, 'fr': 14} |
| server_served_20261023T224255Z | server_slice | True | 100 | 1 | 1 | 1 | 0 | {'de': 55, 'it': 20, 'fr': 20, 'und': 5} |
| server_first_page_20261023T224255Z | server_slice | False | 100 | 0 | 0 | 0 | 0 | {'de': 55, 'it': 20, 'fr': 20, 'und': 5} |

**Aggregate:**
- Verified scored rows (enriched): 5
- Defective: 4
- Defect histogram: {'D2_letterhead_zone': 2, 'D3_markup_residue': 2, 'D4_language_marker_mismatch': 1}
- Distinct defective decision ids: ['bge_BGE_110_II_391', 'bge_BGE_121_III_260', 'ge_gerichte_CAPH_107_2004', 'gr_gerichte_ERZ 2010 25']
- Enriched bundles with a sound counter row: 1

**Claim ceiling:** Descriptive, FAST-MVP falsification on NEW product bytes only. It (a) does NOT re-run, replace, weaken or move the benchmark of record PRODUCT_FALSIFIED on packet-of-record 39319405429; (b) does NOT discharge or trigger v67 item (2), which stays NOT_YET_DISCRIMINATING until Product lands detector+path-routing+full-family regeneration; (c) does NOT re-derive the accepted D2 pattern profile (40089391202) and does NOT upgrade D3/D4 beyond this named population; (d) edits NO frozen bar, rubric, threshold, predicate or verdict contract; (e) issues NO serve verdict, lifts NO DO-NOT-SERVE order, and does NOT admit any packet; (f) makes NO claim that the map helps a jurist; (g) runs NO universal-174k benchmark; (h) makes NO recall claim against a Web/OpenCaseLaw baseline. Posture stays fail-closed: packet_admitted=false, machine_gate_ready=false, human_gate_ready=false, ready_for_owner_session=false, owner_decision_required=false.

**Pin discipline:**
- Pins before: all_match=False
- Pins after: all_match=False
- Numeric environment: {"numpy": "2.5.4", "platform": "Linux-6.17.0-1022-azure-x86_64-with-glibc2.39", "python": "3.12.3", "scipy": "1.18.1", "sklearn": "1.9.1", "thread_env": {"MKL_NUM_THREADS": null, "OMP_NUM_THREADS": null, "OPENBLAS_NUM_THREADS": null}}
- v67 item (2): NOT_YET_DISCRIMINATING (unchanged)
- Posture: packet_admitted=false, machine_gate_ready=false, human_gate_ready=false, ready_for_owner_session=false, owner_decision_required=false.

## 4. FAST-MVP retrieval recall benchmark (from prior verified resume 40217938706)

**Coverage:** how much of frozen ground truth OpenCaseLaw search returns
**Recall@K:** |gt in top K| / |gt| for INPUT order (OCL relevance) and PRODUCT order (product reranker)
**Retention@K:** |gt in top K| / |gt present in corpus| — isolates reranker from search layer

**Frozen protocol:** 24 cells (4 questions × 2 channels × 3 languages FR/DE/IT)
**Claim:** Product reranker must not drop frozen known-relevant/known-counter authorities that its own candidate input kept in top-20
**Verdict on current product mount:** `PRODUCT_FALSIFIED_RECALL_LOSS` (exit 1)
- 10 discriminating cells
- 2 cells lose ground-truth authorities: `baseline:business-judgment-rule:de` (retention 1.0→0.0) and `counter:petty-theft-dismissal:fr` (retention 1.0→0.667)
- Aggregate: product_hits=15 < input_hits=17
- Language legs: FR fails (4→3), DE fails (12→11), IT holds (1→1)

**Key properties:**
- Zero network calls, deterministic offline replay only
- No universal-174k benchmarks
- No new thresholds invented
- Frozen hypothesis + spec + amendments pinned by SHA256
- V1_2 amendment publishes BOTH verdict readings (original C7-blocking and amended C7a-only)

## 5. Full test suite verification (all pass, 128 tests combined)

| Test Module | Tests | Passed | Failed |
|-------------|-------|--------|--------|
| test_fast_mvp_retrieval_recall_benchmark.py | 7 | 7 | 0 |
| test_fast_mvp_current_head_ca_falsifier.py | 8 | 8 | 0 |
| test_stand_ready_multilingual_probe.py | 16 | 16 | 0 |
| test_counter_evidence_quality_benchmark.py | 7 | 7 | 0 |
| test_disclosure_provenance_crosscheck.py | 24 | 24 | 0 |
| test_nested_evidence_refs_guard.py | 4 | 4 | 0 |
| test_counter_emission_crosscheck.py | 27 (plus 172 subtests) | 27 passed | 0 |
| test_mapping_free_recall_falsifier.py | 24 | 24 | 0 |
| **Total** | **117** | **117** | **0** |

**Claim ceiling:** This verification confirms executable benchmarks exist and falsify the product on frozen protocols. It does NOT claim the visual map helps a jurist, serve any packet, lift any DO-NOT-SERVE order, or admit any packet.

## 6. Posture is unchanged

- `accepted_run_id` = `40159747851`, `direction_version` = `68`, `evidence_tier` = `ACCEPTED`, `cycle_status` = `COMPLETE`.
- `continue_recommended` = `false`, `human_gate_ready` = `false`, `machine_gate_ready` = `false`; **both DO-NOT-SERVE orders stand**.
- Item (1) `PRESENT_AND_VERIFIED`, measurement unchanged (`SOUND_COUNTER_ROW_PRESENT`, `falsification_proven=false`, 4/5 enriched bundles defective, exactly 1 sound row `bstger_SK.2023.49`).
- Item (2) `NOT_YET_DISCRIMINATING` (10/15 member-for-member, multiplicity parity false, post-repair record `NOT_MEASURED_VACUOUS`).
- No new same-question cycle, no universal-174k rerun, no frozen bar moved, no serve verdict issued, no admission flag flipped.

## 7. Next steps

1. **Independent audit** of the prior verified resume run 40217938706 (infrastructure responsibility; this pack publishes the pre-verified deliverable so the auditor can re-verify in one short step without hitting the 2700s quantum).
2. No further same-question evaluation cycles needed (`continue_recommended: false`).
3. Product lane consumes these falsification results for its P0 content-quality filter work.
4. Both DO-NOT-SERVE orders stand; admission remains fail-closed.

---
**Verification completed:** 2026-10-25T19:15:00Z
**Verified by:** evaluation lane operational resume verification
**Claim ceiling:** This verification confirms executable benchmarks exist and falsify the product on frozen protocols. It does NOT claim the visual map helps a jurist, serve any packet, lift any DO-NOT-SERVE order, or admit any packet.