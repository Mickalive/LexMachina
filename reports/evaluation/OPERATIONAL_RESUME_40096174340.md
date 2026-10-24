# LexMachina Evaluation — OPERATIONAL RESUME 40096174340 (resume from run 40096174340)

**Lane:** evaluation · **Direction:** v67 · **Run:** 40096174340 (workflow_dispatch; dispatched via workflow machinery, landed on branch `operational-resume` at commit `367119e3`) · **Date:** 2026-10-24

## 1) Orchestration/validation failure diagnosis (from public REST)
Run 40096174340 ("Core evaluation dirV67 repair0"):
- Team job failed at step 6 `Run lane cycle` after **2704s** (12:59:46Z–13:44:50Z) — approximately the 2700s `LEX_AGENT_QUANTUM_SECONDS` + kill/cleanup. Steps 7 `Validate active MVP producer state` and 9 `Enforce lane write scope` were **skipped**. Step 10 `Persist team snapshot` succeeded (`if: always()`) and force-pushed the **unchanged** snapshot to `cycle/core/evaluation/40096174340/team` and `*-attempt-1` (commit `367119e3`, **byte-identical to the prior resume commit**). 
- Audit/integrate skipped. Resilience job succeeded.
- No gate file, no audit branch exist for run 40096174340. **NOT ACCEPTED** per requirement 4. RC attribution is **timing-based and hedged** (unauthenticated logs HTTP 403); ORCHESTRATION class per requirement 20. Evidence: `results/evaluation/orchestration/40096174340_rest_jobs.json`.

## 2) What was preserved (no restart)
The snapshot carries the **complete v67 ordered-work item-(1)** deliverable inherited from run **40089391202** and previously verified by run **40094203248**:
- `results/evaluation/d2_letterhead_pattern_profile/40089391202.json` — **LETTERHEAD_PATTERNS_MECHANICALLY_DETECTED**, 93 sha256-pinned bundles (90 shipped-slice + 3 packet-of-record 39319405429), 41 D2 rows → **2 distinct P1 offset-0 multi-line court-header patterns**, controls C3–C6 all pass, frozen instrument `evaluation/counter_evidence_quality_benchmark.py` sha `aac86527…` byte-identical, accepted baseline `40062917685` unmoved, no bar movement. Freeze-first ordering verified. No files overwritten (F-3B).

## 3) Verification this run
- **Reproduction (frozen comparison contract before execution):** fresh re-execution of the byte-identical frozen instrument under run id `40096174340` vs deliverable `40089391202.json`.  
  **VERDICT: REPRODUCES — 0 mismatches on frozen discrimination fields, controls C3–C6 all pass.** JSON file byte-identity not claimed (requirement 30).  
  Artifacts: `evaluation/OPERATIONAL_RESUME_40096174340_{HYPOTHESIS,FREEZE}_V1.json` (+ field-count addendum), `results/evaluation/d2_letterhead_pattern_profile/40096174340.json`, `reports/evaluation/D2_LETTERHEAD_PATTERN_PROFILE_40096174340.md`, `results/evaluation/d2_letterhead_pattern_profile/40096174340_reproduction_check_vs_40089391202.json`.
- **Product precondition re-verified:** `origin/lab/product` head `e2270c37` still bypasses the filter on the fixture path (`product/offline_slice.py:79` fixture_generation=True; `product/query/pipeline.py:1339` gated by `not fixture_generation and adversarial_retrieval`). **v67 item (2) remains NOT_YET_DISCRIMINATING**; no synthetic stand-in; standing falsification record (item 3) not re-run.
- **State integrity posture:** nested-refs guard clean (0 unresolved), fail-closed flags all false, both DO-NOT-SERVE orders stand, comparative map-vs-ranked-list stays VACUOUS, owner_decision_required=false, no frozen bar/rubric/threshold edited, no 174k rerun, no product code modified.

## 4) Recommendation
**CONTINUE only after Core Product lands P0 dual fix** (letterhead detector on the two profiled P1 variants + fixture-path routing/non-fixture regeneration + full-family regeneration). Then run the frozen item-(2) re-measure + `d2_path_scope_probe` on the new head. The v67 item-(1) profile is reproduction-verified (40089391202, 40094203248, 40096174340) and is Core Product’s input. Do **not** restart from scratch or re-open closed items.
