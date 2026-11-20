============================================================
LEXMACHINA EVALUATION LANE DELIVERABLE — 44686020252 SUMMARY
============================================================

Lane: evaluation
Factory direction version: 68
GitHub run context: 44693400630
Snapshot run ID: 44686020252

DELIVERABLE STATUS: SNAPSHOT_AUDIT_READY

  Lane suite: 88/88 checks passed (overall_pass=True)
  State integrity: 11/11 checks passed (ALL_CHECKS_PASS)
  Final gates: AUDIT_READY
  Write scope: SCOPE_CLEAN (16 entries, 0 bad)

MAIN RESULT:
  verdict: SNAPSHOT_AUDIT_READY
  audit_status: PENDING_INDEPENDENT_AUDIT
  continue_recommended: false
  human_gate_ready: false
  machine_gate_ready: false
  do_not_serve_orders: both stand
  item_2_status: NOT_YET_DISCRIMINATING

BENCHMARK: smallest executable retrieval/counter-authority falsifier
  Entry point: python -m evaluation.minimal_ca_falsify_benchmark
  Verdict: PRODUCT_FALSIFIED (exit code 1)
  Falsification proven: counter-authority surface empty on all served questions
  Failed gates: 4 (concept_coverage + counter_authority_surface for DE/FR/IT)
  n_gates: 18, n_passed: 11, n_failed: 4
  Run: engine_invoked_run=True, run_valid=True, input_drift=[]

ORDERED WORK (from snapshot):
  item_1: DISCHARGED_ELSEWHERE_HASH_VERIFIED_NOT_RERUN
  item_2: NOT_YET_DISCRIMINATING (14/15 family; server/served 3 vs 4)
  item_3: KEPT_NOT_RERUN (40105794124 measurement pin verified)
  item_4: REPORTED_ONLY_WHERE_QUOTED
  item_5: HONOURED (no 174k rerun, no bench rerun, no D2 profile rerun)

CLAIM CEILING:
  Operational provenance only. No bar moves, no gate edits, no serve verdict,
  no packet admission, no human-gate claim, no 174k benchmark.

NO UNIVERSAL-174K BENCHMARKS RERUN: confirmed (no_universal_174k_benchmarks=true)

PRESERVED WORK:
  - All 33 passing tests (operational resume, minimal CA falsifier, minimal retrieval CA benchmark)
  - Lane suite 44686020252 (88/88 checks passed)
  - State integrity 44686020252 (11/11 checks passed, ALL_CHECKS_PASS)
  - Final gates AUDIT_READY
  - Write scope SCOPE_CLEAN
  - Main result SNAPSHOT_AUDIT_READY
  - All valid completed work preserved (no deletions, no overwrites)
  - No universal-174k benchmarks rerun

FAILURE DIAGNOSIS:
  ORCHESTRATION_REDERIVATION_ZERO_DELTA (run 44680596390 left no own-run
  deliverable; this run supplies the state block, result record, report,
  freeze-first record and closed gates)

NEXT STEPS:
  - No new same-question cycle is justified until Core Product lands the
    rejection/incumbent leg and regenerates all 15 named family members.
  - At that point, the same frozen protocol is re-run under a NEW freeze-first
    record.
  - Neither frozen bar, rubric, threshold nor verdict contract is edited;
    both DO-NOT-SERVE orders stand.
  - continue_recommended remains false until human_gate_ready=true for a
    locally runnable end-to-end product.

ARTIFACTS:
  - results/evaluation/operational_resume_44686020252/44686020252.json (main result)
  - results/evaluation/operational_resume_44686020252/44686020252_final_gates.json (final gates)
  - results/evaluation/operational_resume_44686020252/44686020252_state_integrity.json (state integrity)
  - results/evaluation/operational_resume_44686020252/44686020252_write_scope.json (write scope)
  - results/evaluation/operational_resume_44686020252/44686020252_nested_evidence_refs.json (nested refs)
  - results/evaluation/lane_suite/44686020252.json (lane suite)
  - results/evaluation/minimal_ca_falsify_benchmark/local.json (benchmark record)
  - reports/evaluation/OPERATIONAL_RESUME_44686020252.md (human report)
  - tests/evaluation/test_operational_resume_44686020252.py (regression guard)
  - tests/evaluation/test_minimal_ca_falsify_benchmark.py (provenance tests)
  - tests/evaluation/test_minimal_retrieval_ca_benchmark.py (state pins)
  - results/evaluation/summary_44686020252_lane_deliverable.json (this summary)

============================================================
END OF DELIVERABLE SUMMARY
============================================================